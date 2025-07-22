import base64
import json
import os
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging
from azure.identity import DefaultAzureCredential

from conversation_store import ConversationStore
from utils.voice_utils import whisper_client
from foundry_agent import ask_foundry

conversation_router = APIRouter(prefix="/conversation")


# Model for a message
class Message(BaseModel):
    conversation_id: str
    id: str
    name: str
    role: str
    content: str


# A helper class that store and retrieve messages by conversation from an Azure Cosmos DB
key = DefaultAzureCredential()
db = ConversationStore(
    url=os.getenv("COSMOSDB_ENDPOINT"),
    key=key,
    database_name=os.getenv("COSMOSDB_DATABASE"),
    container_name=os.getenv("COSMOSDB_CONTAINER")
)


# Get all messages by conversation
@conversation_router.get("/{conversation_id}")
def get_messages(conversation_id: str):
    """Get all messages for a conversation."""
    conv = db.get_conversation(conversation_id) or []
    return conv.get("messages", [])


class MediaRequest(BaseModel):
    mimeType: str
    data: str


class MessageRequest(BaseModel):
    message: str
    media: Optional[list[MediaRequest]] = None


@conversation_router.post("/{conversation_id}")
def send_message(conversation_id: str, request: MessageRequest):
    """Send a message to an existing conversation."""
    
    print(f"[ROUTER] POST /{conversation_id} called with message: '{request.message[:50]}...'")
    
    # Get conversation history
    history = db.get_conversation(conversation_id) or {"messages": [], "variables": {}}
    messages = history.get("messages", [])
    variables = history.get("variables", {})
    
    message = _preprocess_request(request)
    history_count = len(messages)
    
    try:
        # Extract text from message
        text_message = message if isinstance(message, str) else getattr(message, 'text', str(message))
        
        # Get response from Azure AI Foundry agent with conversation context
        response = ask_foundry(text_message, conversation_id)
        
        # Add user message and assistant response to conversation
        messages.append({
            "role": "user",
            "content": text_message,
            "name": "user"
        })
        messages.append({
            "role": "assistant", 
            "content": response,
            "name": "foundry-agent"
        })
        
        # Save conversation
        db.save_conversation(conversation_id, {"messages": messages, "variables": variables})
        
        # Return new messages
        new_messages = messages[history_count:]
        return new_messages
        
    except Exception as e:
        logging.error(f"Azure AI Foundry agent error: {e}")
        raise Exception(f"Error processing message: {e}")


@conversation_router.post("/{conversation_id}/stream")
def send_message_stream(conversation_id: str, request: MessageRequest):
    """Send a message to an existing conversation with streaming response."""
    
    print(f"[ROUTER] POST /{conversation_id}/stream called with message: '{request.message[:50]}...'")
    
    # Get conversation history
    history = db.get_conversation(conversation_id) or {"messages": [], "variables": {}}
    messages = history.get("messages", [])
    variables = history.get("variables", {})
    
    message = _preprocess_request(request)
    
    logging.info(f"Starting conversation {conversation_id}")
    
    def _foundry_stream():
        try:
            # Extract text from message
            text_message = message if isinstance(message, str) else getattr(message, 'text', str(message))
            
            # Start marker
            yield json.dumps(["start", "foundry-agent"]) + "\n"
            
            # Get response from Azure AI Foundry agent with conversation context
            response = ask_foundry(text_message, conversation_id)
            
            # Stream the response
            yield json.dumps(["delta", {"content": response, "tool_calls": None}]) + "\n"
            
            # Add messages to conversation
            messages.append({
                "role": "user",
                "content": text_message,
                "name": "user"
            })
            messages.append({
                "role": "assistant", 
                "content": response,
                "name": "foundry-agent"
            })
            
            # End marker
            yield json.dumps(["result", "success"]) + "\n"
            
            # Save conversation
            clean_messages = [{"content": m["content"], "name": m.get("name"), "role": m["role"]} for m in messages]
            db.save_conversation(conversation_id, {"messages": clean_messages, "variables": variables})
            
        except Exception as e:
            logging.error(f"Azure AI Foundry agent streaming error: {e}")
            yield json.dumps(["error", str(e)]) + "\n"
            yield json.dumps(["result", "error"]) + "\n"
    
    return StreamingResponse(_foundry_stream(), media_type="text/event-stream")


def _preprocess_request(input_message: MessageRequest):
    """Preprocess the request message, handling media attachments."""
    if input_message.media is None:
        return input_message.message
    else:
        # Simple implementation - for now just return the text message
        # In the future, we can enhance this to handle images and audio with Azure AI Foundry
        text_content = input_message.message
        
        for m in input_message.media:
            if "audio" in m.mimeType:
                try:
                    # Transcribe audio using Whisper
                    transcription = whisper_client.audio.transcriptions.create(
                        model="whisper",
                        file=input_message.media.data
                    )
                    text_content = transcription.text
                except Exception as e:
                    logging.error(f"Audio transcription error: {e}")
            elif "image" in m.mimeType:
                # For now, just note that there's an image
                text_content += " [Image attached]"
        
        return text_content