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

def ask_foundry(user_text: str) -> str:
    """
    Ask the Azure AI Foundry agent a question and return the response.
    
    Args:
        user_text: The user's input text
        
    Returns:
        The agent's response as a string
    """
    try:
        # Create a new thread for this conversation
        thread = project.agents.threads.create()
        
        # Add the user message to the thread
        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_text
        )
        
        # Create and process the run
        run = project.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=AGENT_ID
        )
        
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return "I'm having trouble right now—please try again."
        
        # Get the messages from the thread
        messages = project.agents.messages.list(
            thread_id=thread.id, 
            order=ListSortOrder.ASCENDING
        )
        
        # Find the assistant's response (last message from assistant)
        for message in reversed(messages.data):
            if message.role == "assistant" and message.text_messages:
                return message.text_messages[-1].text.value
        
        return "I didn't receive a proper response. Please try again."
        
    except Exception as e:
        print(f"Error in ask_foundry: {str(e)}")
        return "I'm having trouble right now—please try again."
