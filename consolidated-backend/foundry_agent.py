import os
import time
from typing import Optional, Dict
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

# Use DefaultAzureCredential for both local and production
_credential = DefaultAzureCredential()

# Global project clients storage (keyed by endpoint)
_project_clients = {}

# Global agent configuration (for backward compatibility)
AGENT_ID = os.environ.get("AGENT_ID")
DEFAULT_FOUNDRY_ENDPOINT = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")

# Thread storage for conversation persistence
_conversation_threads = {}

def get_project_client(foundry_endpoint: str = None) -> AIProjectClient:
    """Get or create a project client for the given endpoint"""
    endpoint = foundry_endpoint or DEFAULT_FOUNDRY_ENDPOINT
    
    if endpoint not in _project_clients:
        _project_clients[endpoint] = AIProjectClient(
            credential=_credential,
            endpoint=endpoint
        )
    
    return _project_clients[endpoint]

def ask_foundry(user_text: str, conversation_id: str = None, agent_id: str = None, foundry_endpoint: str = None) -> str:
    """
    Ask the Azure AI Foundry agent a question and return the response.
    
    Args:
        user_text: The user's input text
        conversation_id: The conversation ID to maintain context
        agent_id: The specific agent ID to use (defaults to AGENT_ID env var)
        foundry_endpoint: The foundry endpoint to use (defaults to AZURE_AI_FOUNDRY_ENDPOINT env var)
        
    Returns:
        The agent's response as a string
    """
    try:
        # Use provided parameters or fall back to defaults
        current_agent_id = agent_id or AGENT_ID
        current_endpoint = foundry_endpoint or DEFAULT_FOUNDRY_ENDPOINT
        
        if not current_agent_id:
            return "Agent configuration is missing. Please check the system configuration."
        
        if not current_endpoint:
            return "Foundry endpoint configuration is missing. Please check the system configuration."
        
        # Get the appropriate project client
        project = get_project_client(current_endpoint)
        
        print(f"[FOUNDRY] Called with text: '{user_text}', conversation_id: '{conversation_id}', agent_id: '{current_agent_id}'")
        
        # Create a unique thread key that includes agent_id for better isolation
        thread_key = f"{current_agent_id}_{conversation_id}" if conversation_id else current_agent_id
        
        # Get or create thread for this conversation
        if thread_key in _conversation_threads:
            thread_id = _conversation_threads[thread_key]
            print(f"[FOUNDRY] Reusing existing thread: {thread_id}")
        else:
            # Create a new thread for this conversation
            thread = project.agents.threads.create()
            thread_id = thread.id
            print(f"[FOUNDRY] Created new thread: {thread_id}")
            _conversation_threads[thread_key] = thread_id
        
        # Add the user message to the thread
        message = project.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )
        
        # Create and process the run
        run = project.agents.runs.create_and_process(
            thread_id=thread_id,
            agent_id=current_agent_id
        )
        
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return "I'm having trouble right now—please try again."
        
        # Get the messages from the thread
        messages = project.agents.messages.list(
            thread_id=thread_id, 
            order=ListSortOrder.ASCENDING
        )
        
        # Convert ItemPaged to list and find the assistant's response (last message from assistant)
        messages_list = list(messages)
        print(f"[FOUNDRY] Retrieved {len(messages_list)} messages from thread")
        for message in reversed(messages_list):
            if message.role == "assistant" and hasattr(message, 'content') and message.content:
                # Handle different content types
                for content in message.content:
                    if hasattr(content, 'text') and content.text:
                        response_text = content.text.value
                        print(f"[FOUNDRY] Returning response: '{response_text[:100]}...'")
                        return response_text
                    elif hasattr(content, 'value'):
                        response_text = content.value
                        print(f"[FOUNDRY] Returning response: '{response_text[:100]}...'")
                        return response_text
        
        return "I didn't receive a proper response. Please try again."
        
    except Exception as e:
        print(f"Error in ask_foundry: {str(e)}")
        return "I'm having trouble right now—please try again."
