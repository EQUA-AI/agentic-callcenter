"""
Azure AI Foundry Integration for Chainlit Frontend
Direct integration with Azure AI Foundry agents using the AI Project Client
"""
import os
import time
import logging
from typing import Optional, Dict, Any
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

# Configure logging
logger = logging.getLogger(__name__)

class AzureAIFoundryClient:
    """
    Azure AI Foundry client for direct agent communication
    Supports multiple agents and endpoints with conversation persistence
    """
    
    def __init__(self):
        # Use DefaultAzureCredential for authentication
        self._credential = DefaultAzureCredential()
        
        # Global project clients storage (keyed by endpoint)
        self._project_clients = {}
        
        # Thread storage for conversation persistence
        self._conversation_threads = {}
        
        # Load environment variables for default configuration
        self.default_endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
        self.default_agent_id = os.getenv("AGENT_ID")
        
        logger.info(f"AzureAIFoundryClient initialized with default endpoint: {self.default_endpoint}")
    
    def get_project_client(self, foundry_endpoint: str = None) -> AIProjectClient:
        """Get or create a project client for the given endpoint"""
        endpoint = foundry_endpoint or self.default_endpoint
        
        if not endpoint:
            raise ValueError("Azure AI Foundry endpoint must be provided either as parameter or AZURE_AI_FOUNDRY_ENDPOINT environment variable")
        
        if endpoint not in self._project_clients:
            logger.info(f"Creating new AIProjectClient for endpoint: {endpoint}")
            self._project_clients[endpoint] = AIProjectClient(
                credential=self._credential,
                endpoint=endpoint
            )
        
        return self._project_clients[endpoint]
    
    async def ask_agent(
        self, 
        user_text: str, 
        agent_id: Optional[str] = None, 
        conversation_id: Optional[str] = None, 
        foundry_endpoint: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Ask an Azure AI Foundry agent a question and return the response.
        
        Args:
            user_text: The user's input text
            agent_id: The specific agent ID to use
            conversation_id: The conversation ID to maintain context
            foundry_endpoint: The foundry endpoint to use
            system_prompt: Optional system prompt (metadata for context)
            context: Additional context information
            
        Returns:
            The agent's response as a string
        """
        try:
            # Use provided parameters or fall back to defaults
            current_agent_id = agent_id or self.default_agent_id
            current_endpoint = foundry_endpoint or self.default_endpoint
            
            if not current_agent_id:
                logger.error("No agent ID provided and no default AGENT_ID environment variable set")
                return "Agent configuration is missing. Please check the system configuration."
            
            if not current_endpoint:
                logger.error("No foundry endpoint provided and no default AZURE_AI_FOUNDRY_ENDPOINT environment variable set")
                return "Foundry endpoint configuration is missing. Please check the system configuration."
            
            # Get the appropriate project client
            project = self.get_project_client(current_endpoint)
            
            logger.info(f"[FOUNDRY] Processing message for agent {current_agent_id}: '{user_text[:100]}...'")
            
            # Create a unique thread key that includes agent_id for better isolation
            thread_key = f"{current_agent_id}_{conversation_id}" if conversation_id else f"{current_agent_id}_default"
            
            # Get or create thread for this conversation
            if thread_key in self._conversation_threads:
                thread_id = self._conversation_threads[thread_key]
                logger.debug(f"[FOUNDRY] Reusing existing thread: {thread_id}")
            else:
                # Create a new thread for this conversation
                thread = project.agents.threads.create()
                thread_id = thread.id
                logger.info(f"[FOUNDRY] Created new thread: {thread_id}")
                self._conversation_threads[thread_key] = thread_id
            
            # Add context information as metadata if provided
            message_metadata = {}
            if context:
                # Ensure all metadata values are strings
                for key, value in context.items():
                    message_metadata[key] = str(value)
            if system_prompt:
                message_metadata["system_prompt"] = system_prompt
            
            # Add the user message to the thread
            message = project.agents.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_text,
                metadata=message_metadata if message_metadata else None
            )
            
            logger.debug(f"[FOUNDRY] Added user message to thread {thread_id}")
            
            # Create and process the run
            run = project.agents.runs.create_and_process(
                thread_id=thread_id,
                agent_id=current_agent_id
            )
            
            if run.status == "failed":
                error_msg = getattr(run, 'last_error', 'Unknown error')
                logger.error(f"[FOUNDRY] Run failed for agent {current_agent_id}: {error_msg}")
                return "I'm having trouble processing your request right now. Please try again."
            
            # Get the messages from the thread
            messages = project.agents.messages.list(
                thread_id=thread_id, 
                order=ListSortOrder.ASCENDING
            )
            
            # Convert ItemPaged to list and find the assistant's response
            messages_list = list(messages)
            logger.debug(f"[FOUNDRY] Retrieved {len(messages_list)} messages from thread")
            
            # Find the most recent assistant response
            for message in reversed(messages_list):
                if message.role == "assistant" and hasattr(message, 'content') and message.content:
                    # Handle different content types
                    for content in message.content:
                        if hasattr(content, 'text') and content.text:
                            response_text = content.text.value
                            logger.info(f"[FOUNDRY] Successfully got response from agent {current_agent_id}")
                            return response_text
                        elif hasattr(content, 'value'):
                            response_text = content.value
                            logger.info(f"[FOUNDRY] Successfully got response from agent {current_agent_id}")
                            return response_text
            
            logger.warning(f"[FOUNDRY] No valid assistant response found in thread {thread_id}")
            return "I didn't receive a proper response. Please try again."
            
        except Exception as e:
            logger.error(f"[FOUNDRY] Error in ask_agent for agent {agent_id}: {str(e)}", exc_info=True)
            return "I'm having trouble right now—please try again."
    
    def clear_conversation(self, agent_id: str, conversation_id: Optional[str] = None):
        """Clear conversation thread for a specific agent and conversation"""
        thread_key = f"{agent_id}_{conversation_id}" if conversation_id else f"{agent_id}_default"
        if thread_key in self._conversation_threads:
            del self._conversation_threads[thread_key]
            logger.info(f"[FOUNDRY] Cleared conversation thread for {thread_key}")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about active conversations"""
        return {
            "active_threads": len(self._conversation_threads),
            "active_endpoints": len(self._project_clients),
            "thread_keys": list(self._conversation_threads.keys())
        }
    
    async def close(self):
        """Clean up resources"""
        self._conversation_threads.clear()
        self._project_clients.clear()
        logger.info("[FOUNDRY] AzureAIFoundryClient resources cleaned up")

# Global instance for the Chainlit app
_foundry_client = None

def get_foundry_client() -> AzureAIFoundryClient:
    """Get the global Azure AI Foundry client instance"""
    global _foundry_client
    if _foundry_client is None:
        _foundry_client = AzureAIFoundryClient()
    return _foundry_client

async def ask_foundry_agent(
    user_text: str, 
    agent_id: str, 
    conversation_id: Optional[str] = None, 
    foundry_endpoint: Optional[str] = None,
    system_prompt: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to ask an Azure AI Foundry agent
    
    Args:
        user_text: The user's input text
        agent_id: The specific agent ID to use
        conversation_id: The conversation ID to maintain context
        foundry_endpoint: The foundry endpoint to use
        system_prompt: Optional system prompt for context
        context: Additional context information
        
    Returns:
        The agent's response as a string
    """
    client = get_foundry_client()
    return await client.ask_agent(
        user_text=user_text,
        agent_id=agent_id,
        conversation_id=conversation_id,
        foundry_endpoint=foundry_endpoint,
        system_prompt=system_prompt,
        context=context
    )
