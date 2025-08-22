"""
Enhanced Conversation Store with Phone-Number-Based Container Architecture
Creates separate containers for each business phone number in the system
"""
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential
import logging
import os
import re
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class MultiContainerConversationStore:
    """
    Manages conversations using separate containers for each business phone number
    Automatically creates containers based on configured channels in ConfigManager
    """
    
    def __init__(self, cosmos_endpoint: str = None, database_name: str = None):
        self.cosmos_endpoint = cosmos_endpoint or os.getenv("COSMOSDB_ENDPOINT")
        self.database_name = database_name or os.getenv("COSMOSDB_DATABASE", "CallCenterDB")
        self.credential = DefaultAzureCredential()
        
        if not self.cosmos_endpoint:
            raise ValueError("COSMOSDB_ENDPOINT environment variable is required")
        
        # Initialize client and database
        self.client = CosmosClient(self.cosmos_endpoint, credential=self.credential)
        self.database = self.client.create_database_if_not_exists(id=self.database_name)
        
        # Cache for container clients
        self._container_cache = {}
        self._phone_number_cache = {}
        
        logger.info("Multi-container conversation store initialized")
    
    def _sanitize_phone_number(self, phone_number: str) -> str:
        """
        Convert phone number to container-safe name
        +18327725964 -> 18327725964
        +917700006208 -> 917700006208
        """
        # Remove + and any non-numeric characters
        sanitized = re.sub(r'[^0-9]', '', phone_number)
        return sanitized
    
    def _get_container_name(self, phone_number: str) -> str:
        """Generate container name for a phone number"""
        sanitized_number = self._sanitize_phone_number(phone_number)
        return f"conversations_{sanitized_number}"
    
    def _get_or_create_container(self, phone_number: str):
        """Get or create container for a specific phone number"""
        container_name = self._get_container_name(phone_number)
        
        # Check cache first
        if container_name in self._container_cache:
            return self._container_cache[container_name]
        
        try:
            # Try to get existing container
            container = self.database.get_container_client(container_name)
            logger.info(f"Found existing container: {container_name}")
            
        except exceptions.CosmosResourceNotFoundError:
            # Create new container for this phone number
            try:
                container = self.database.create_container_if_not_exists(
                    id=container_name,
                    partition_key=PartitionKey(path="/conversation_id"),
                    offer_throughput=400  # Start with minimal throughput
                )
                logger.info(f"Created new container for phone {phone_number}: {container_name}")
                
            except exceptions.CosmosHttpResponseError as e:
                if "blocked by Auth" in str(e):
                    # If auth blocked, try to get container (should exist from infrastructure)
                    container = self.database.get_container_client(container_name)
                    logger.warning(f"Auth blocked creation, using existing: {container_name}")
                else:
                    raise e
        
        # Cache the container client
        self._container_cache[container_name] = container
        self._phone_number_cache[phone_number] = container_name
        
        return container
    
    def save_conversation(self, phone_number: str, conversation_id: str, conversation: dict):
        """
        Save conversation to the appropriate phone number container
        
        Args:
            phone_number: Business phone number (+18327725964)
            conversation_id: Unique conversation identifier
            conversation: Conversation data with messages and metadata
        """
        try:
            container = self._get_or_create_container(phone_number)
            
            # Prepare conversation document
            conversation_doc = {
                "id": conversation_id,
                "conversation_id": conversation_id,
                "phone_number": phone_number,  # Store for reference
                "messages": conversation.get("messages", []),
                "variables": conversation.get("variables", {}),
                "metadata": {
                    "created_at": conversation.get("created_at", datetime.utcnow().isoformat()),
                    "updated_at": datetime.utcnow().isoformat(),
                    "container_name": self._get_container_name(phone_number)
                }
            }
            
            # Upsert the conversation
            container.upsert_item(conversation_doc)
            logger.debug(f"Saved conversation {conversation_id} to {phone_number} container")
            
        except Exception as e:
            logger.error(f"Failed to save conversation {conversation_id} for {phone_number}: {e}")
            raise
    
    def get_conversation(self, phone_number: str, conversation_id: str) -> Optional[Dict]:
        """
        Get conversation from the appropriate phone number container
        
        Args:
            phone_number: Business phone number (+18327725964)
            conversation_id: Unique conversation identifier
            
        Returns:
            Conversation document or None if not found
        """
        try:
            container = self._get_or_create_container(phone_number)
            item = container.read_item(item=conversation_id, partition_key=conversation_id)
            return item
            
        except exceptions.CosmosResourceNotFoundError:
            logger.debug(f"Conversation {conversation_id} not found for {phone_number}")
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id} for {phone_number}: {e}")
            raise
    
    def list_conversations_for_phone(self, phone_number: str, limit: int = 100) -> List[Dict]:
        """
        List all conversations for a specific phone number
        
        Args:
            phone_number: Business phone number (+18327725964)
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation documents
        """
        try:
            container = self._get_or_create_container(phone_number)
            
            query = f"SELECT * FROM c ORDER BY c.metadata.updated_at DESC OFFSET 0 LIMIT {limit}"
            conversations = list(container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to list conversations for {phone_number}: {e}")
            return []
    
    def delete_conversation(self, phone_number: str, conversation_id: str) -> bool:
        """
        Delete a conversation from the appropriate phone number container
        
        Args:
            phone_number: Business phone number (+18327725964)
            conversation_id: Unique conversation identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            container = self._get_or_create_container(phone_number)
            container.delete_item(item=conversation_id, partition_key=conversation_id)
            logger.info(f"Deleted conversation {conversation_id} from {phone_number}")
            return True
            
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Conversation {conversation_id} not found for deletion in {phone_number}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id} for {phone_number}: {e}")
            return False
    
    def get_conversation_stats_for_phone(self, phone_number: str) -> Dict:
        """
        Get statistics for conversations in a phone number container
        
        Args:
            phone_number: Business phone number (+18327725964)
            
        Returns:
            Statistics dictionary with counts and metadata
        """
        try:
            container = self._get_or_create_container(phone_number)
            
            # Count total conversations
            count_query = "SELECT VALUE COUNT(1) FROM c"
            total_conversations = list(container.query_items(
                query=count_query,
                enable_cross_partition_query=True
            ))[0]
            
            # Get recent activity
            recent_query = "SELECT TOP 5 c.conversation_id, c.metadata.updated_at FROM c ORDER BY c.metadata.updated_at DESC"
            recent_conversations = list(container.query_items(
                query=recent_query,
                enable_cross_partition_query=True
            ))
            
            return {
                "phone_number": phone_number,
                "container_name": self._get_container_name(phone_number),
                "total_conversations": total_conversations,
                "recent_conversations": recent_conversations,
                "last_activity": recent_conversations[0]["updated_at"] if recent_conversations else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {phone_number}: {e}")
            return {
                "phone_number": phone_number,
                "container_name": self._get_container_name(phone_number),
                "total_conversations": 0,
                "recent_conversations": [],
                "last_activity": None,
                "error": str(e)
            }
    
    def list_all_phone_containers(self) -> List[Dict]:
        """
        List all phone number containers and their stats
        
        Returns:
            List of container statistics for each phone number
        """
        try:
            # Get all containers in the database
            containers = list(self.database.list_containers())
            conversation_containers = [
                c for c in containers 
                if c['id'].startswith('conversations_') and c['id'] != 'conversations'
            ]
            
            stats = []
            for container_info in conversation_containers:
                container_name = container_info['id']
                # Extract phone number from container name
                number_part = container_name.replace('conversations_', '')
                # Convert back to phone format (add + prefix)
                phone_number = f"+{number_part}"
                
                container_stats = self.get_conversation_stats_for_phone(phone_number)
                stats.append(container_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to list phone containers: {e}")
            return []
    
    def migrate_from_single_container(self, old_container_name: str = "conversations"):
        """
        Migrate conversations from old single container to phone-specific containers
        This should be run once during the upgrade
        
        Args:
            old_container_name: Name of the old single container
        """
        try:
            # Get the old container
            old_container = self.database.get_container_client(old_container_name)
            
            # Query all conversations from old container
            query = "SELECT * FROM c"
            all_conversations = list(old_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            migrated_count = 0
            error_count = 0
            
            for conversation in all_conversations:
                try:
                    # Extract phone number from conversation ID or metadata
                    # Assuming conversation_id format: {channel_id}_{customer_phone}_{timestamp}
                    conv_id = conversation.get('conversation_id', conversation.get('id', ''))
                    
                    # Try to find phone number in the conversation data
                    phone_number = None
                    
                    # Check if there's a phone number in metadata
                    if 'metadata' in conversation and 'phone_number' in conversation['metadata']:
                        phone_number = conversation['metadata']['phone_number']
                    else:
                        # Try to extract from conversation ID pattern
                        # This might need adjustment based on your actual conversation ID format
                        parts = conv_id.split('_')
                        if len(parts) >= 2:
                            # Look for phone number pattern in the parts
                            for part in parts:
                                if part.startswith('1') and len(part) >= 10:  # US number
                                    phone_number = f"+{part}"
                                    break
                                elif part.startswith('91') and len(part) >= 10:  # India number
                                    phone_number = f"+{part}"
                                    break
                    
                    if phone_number:
                        # Save to appropriate phone container
                        self.save_conversation(
                            phone_number=phone_number,
                            conversation_id=conv_id,
                            conversation=conversation
                        )
                        migrated_count += 1
                        logger.debug(f"Migrated conversation {conv_id} to {phone_number}")
                    else:
                        logger.warning(f"Could not determine phone number for conversation {conv_id}")
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to migrate conversation {conv_id}: {e}")
                    error_count += 1
            
            logger.info(f"Migration completed: {migrated_count} migrated, {error_count} errors")
            return {"migrated": migrated_count, "errors": error_count}
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


# Factory function for backwards compatibility
def get_conversation_store(phone_number: str = None) -> MultiContainerConversationStore:
    """
    Get a conversation store instance
    
    Args:
        phone_number: Optional phone number for container-specific operations
        
    Returns:
        MultiContainerConversationStore instance
    """
    return MultiContainerConversationStore()
