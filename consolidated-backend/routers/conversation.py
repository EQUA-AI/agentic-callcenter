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
    tenant_id: Optional[str] = None  # Added for multi-tenant support

@conversation_router.post("/{conversation_id}")
def send_message(conversation_id: str, request: MessageRequest):
    """Send a message to an existing conversation with multi-tenant support."""
    
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
        
        # Multi-tenant agent selection
        agent_id = os.getenv('CURRENT_AGENT_ID', os.getenv('AGENT_ID', 'default'))
        tenant_id = request.tenant_id or os.getenv('CURRENT_TENANT_ID', 'default')
        
        # Get response from Azure AI Foundry agent with conversation context
        response = ask_foundry(text_message, conversation_id)
        
        # Add user message and assistant response to conversation
        messages.append({
            "role": "user",
            "content": text_message,
            "name": "user",
            "tenant_id": tenant_id
        })
        messages.append({
            "role": "assistant", 
            "content": response,
            "name": f"foundry-agent-{agent_id}",
            "tenant_id": tenant_id
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
def send_message_streaming(conversation_id: str, request: MessageRequest):
    """Send a message to an existing conversation and stream the response."""
    
    def stream_response():
        try:
            # Get conversation history
            history = db.get_conversation(conversation_id) or {"messages": [], "variables": {}}
            messages = history.get("messages", [])
            variables = history.get("variables", {})
            
            message = _preprocess_request(request)
            
            # Extract text from message
            text_message = message if isinstance(message, str) else getattr(message, 'text', str(message))
            
            # Multi-tenant support
            agent_id = os.getenv('CURRENT_AGENT_ID', os.getenv('AGENT_ID', 'default'))
            tenant_id = request.tenant_id or os.getenv('CURRENT_TENANT_ID', 'default')
            
            # Add user message
            messages.append({
                "role": "user",
                "content": text_message,
                "name": "user",
                "tenant_id": tenant_id
            })
            
            # Stream response from agent (simplified for now)
            response = ask_foundry(text_message, conversation_id)
            
            # Yield streaming chunks
            yield json.dumps(["chunk", response[:50]]) + "\n"
            yield json.dumps(["chunk", response[50:]]) + "\n"
            
            # Add assistant message
            messages.append({
                "role": "assistant",
                "content": response,
                "name": f"foundry-agent-{agent_id}",
                "tenant_id": tenant_id
            })
            
            # Save conversation
            db.save_conversation(conversation_id, {"messages": messages, "variables": variables})
            
            # Final result
            yield json.dumps(["result", messages[-2:]]) + "\n"
            
        except Exception as e:
            logging.error(f"Streaming error: {e}")
            yield json.dumps(["error", str(e)]) + "\n"
    
    return StreamingResponse(stream_response(), media_type="application/x-ndjson")

def _preprocess_request(request: MessageRequest):
    """Preprocess the incoming request - handle media, etc."""
    message_text = request.message
    
    # Handle media if present (audio transcription, etc.)
    if request.media:
        for media_item in request.media:
            if "audio" in media_item.mimeType:
                # Decode base64 audio and transcribe
                try:
                    audio_data = base64.b64decode(media_item.data)
                    transcription = whisper_client.audio.transcriptions.create(
                        model="whisper",
                        file=audio_data
                    )
                    message_text += f" [Audio transcription: {transcription.text}]"
                except Exception as e:
                    logging.error(f"Audio transcription error: {e}")
                    message_text += " [Audio file received but could not be transcribed]"
            elif "image" in media_item.mimeType:
                message_text += " [Image received - visual content analysis not implemented]"
    
    return message_text
