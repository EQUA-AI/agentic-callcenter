import os
import time
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

# Use DefaultAzureCredential for both local and production
_credential = DefaultAzureCredential()

# Initialize the AI Project Client
project = AIProjectClient(
    credential=_credential,
    endpoint=os.environ["AZURE_AI_FOUNDRY_ENDPOINT"]
)

AGENT_ID = os.environ["AGENT_ID"]

# Thread storage for conversation persistence
_conversation_threads = {}

def ask_foundry(user_text: str, conversation_id: str = None) -> str:
    """
    Ask the Azure AI Foundry agent a question and return the response.
    
    Args:
        user_text: The user's input text
        conversation_id: The conversation ID to maintain context
        
    Returns:
        The agent's response as a string
    """
    try:
        print(f"[FOUNDRY] Called with text: '{user_text}', conversation_id: '{conversation_id}'")
        # Get or create thread for this conversation
        if conversation_id and conversation_id in _conversation_threads:
            thread_id = _conversation_threads[conversation_id]
            print(f"[FOUNDRY] Reusing existing thread: {thread_id}")
        else:
            # Create a new thread for this conversation
            thread = project.agents.threads.create()
            thread_id = thread.id
            print(f"[FOUNDRY] Created new thread: {thread_id}")
            if conversation_id:
                _conversation_threads[conversation_id] = thread_id
        
        # Add the user message to the thread
        message = project.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )
        
        # Create and process the run
        run = project.agents.runs.create_and_process(
            thread_id=thread_id,
            agent_id=AGENT_ID
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
