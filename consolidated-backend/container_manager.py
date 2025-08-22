"""
Container Management Utility for Multi-Phone Conversation Storage
Provides administrative tools for managing phone-number-based containers
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

from multi_container_conversation_store import MultiContainerConversationStore
from config_manager import get_config_manager

logger = logging.getLogger(__name__)

class ConversationContainerManager:
    """
    Administrative tools for managing conversation containers
    """
    
    def __init__(self):
        self.conversation_store = MultiContainerConversationStore()
        self.config_manager = get_config_manager()
    
    def get_system_overview(self) -> Dict:
        """
        Get a complete overview of the conversation storage system
        
        Returns:
            System overview with containers, channels, and statistics
        """
        try:
            # Get all configured channels (phone numbers)
            channels = self.config_manager.list_channels(is_active=True)
            
            # Get all conversation containers
            container_stats = self.conversation_store.list_all_phone_containers()
            
            # Match channels with containers
            overview = {
                "timestamp": datetime.utcnow().isoformat(),
                "configured_channels": len(channels),
                "active_containers": len(container_stats),
                "channels": {},
                "containers": {},
                "orphaned_containers": [],
                "missing_containers": []
            }
            
            # Process configured channels
            channel_phones = {}
            for channel in channels:
                phone = channel.get('phone_number')
                if phone:
                    channel_phones[phone] = channel
                    overview["channels"][phone] = {
                        "channel_id": channel.get('channel_id'),
                        "channel_name": channel.get('channel_name'),
                        "agent_id": channel.get('agent_id'),
                        "has_container": False,
                        "conversation_count": 0
                    }
            
            # Process existing containers
            container_phones = {}
            for container_stat in container_stats:
                phone = container_stat['phone_number']
                container_phones[phone] = container_stat
                overview["containers"][phone] = container_stat
                
                # Update channel info if matched
                if phone in overview["channels"]:
                    overview["channels"][phone]["has_container"] = True
                    overview["channels"][phone]["conversation_count"] = container_stat['total_conversations']
            
            # Find orphaned containers (containers without configured channels)
            for phone in container_phones:
                if phone not in channel_phones:
                    overview["orphaned_containers"].append({
                        "phone_number": phone,
                        "container_name": container_phones[phone]['container_name'],
                        "conversation_count": container_phones[phone]['total_conversations']
                    })
            
            # Find missing containers (channels without containers)
            for phone in channel_phones:
                if phone not in container_phones:
                    overview["missing_containers"].append({
                        "phone_number": phone,
                        "channel_name": channel_phones[phone].get('channel_name'),
                        "agent_id": channel_phones[phone].get('agent_id')
                    })
            
            return overview
            
        except Exception as e:
            logger.error(f"Failed to get system overview: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def create_missing_containers(self) -> Dict:
        """
        Create containers for configured channels that don't have them
        
        Returns:
            Results of container creation operations
        """
        try:
            overview = self.get_system_overview()
            missing = overview.get("missing_containers", [])
            
            results = {
                "created": [],
                "errors": [],
                "total_attempted": len(missing)
            }
            
            for missing_info in missing:
                phone = missing_info["phone_number"]
                try:
                    # Creating a container by trying to get/create it
                    container = self.conversation_store._get_or_create_container(phone)
                    results["created"].append({
                        "phone_number": phone,
                        "container_name": self.conversation_store._get_container_name(phone),
                        "channel_name": missing_info.get("channel_name")
                    })
                    logger.info(f"Created container for phone {phone}")
                    
                except Exception as e:
                    results["errors"].append({
                        "phone_number": phone,
                        "error": str(e)
                    })
                    logger.error(f"Failed to create container for {phone}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to create missing containers: {e}")
            return {"error": str(e)}
    
    def migrate_old_conversations(self, old_container_name: str = "conversations", dry_run: bool = True) -> Dict:
        """
        Migrate conversations from old single container to phone-based containers
        
        Args:
            old_container_name: Name of the old single container
            dry_run: If True, only analyze without making changes
            
        Returns:
            Migration results and statistics
        """
        try:
            if dry_run:
                logger.info("Running migration analysis (dry run)")
            else:
                logger.info("Running actual migration")
            
            # Get the old container
            old_container = self.conversation_store.database.get_container_client(old_container_name)
            
            # Query all conversations from old container
            query = "SELECT * FROM c"
            all_conversations = list(old_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            migration_plan = {
                "total_conversations": len(all_conversations),
                "phone_distribution": {},
                "migration_actions": [],
                "errors": [],
                "dry_run": dry_run
            }
            
            # Analyze conversation distribution
            for conversation in all_conversations:
                try:
                    conv_id = conversation.get('conversation_id', conversation.get('id', ''))
                    
                    # Try to determine phone number
                    phone_number = self._extract_phone_from_conversation(conversation, conv_id)
                    
                    if phone_number:
                        if phone_number not in migration_plan["phone_distribution"]:
                            migration_plan["phone_distribution"][phone_number] = []
                        
                        migration_plan["phone_distribution"][phone_number].append({
                            "conversation_id": conv_id,
                            "message_count": len(conversation.get("messages", [])),
                            "created_at": conversation.get("created_at", "unknown")
                        })
                        
                        migration_plan["migration_actions"].append({
                            "action": "migrate",
                            "conversation_id": conv_id,
                            "from_container": old_container_name,
                            "to_container": self.conversation_store._get_container_name(phone_number),
                            "phone_number": phone_number
                        })
                        
                        # Perform actual migration if not dry run
                        if not dry_run:
                            self.conversation_store.save_conversation(
                                phone_number=phone_number,
                                conversation_id=conv_id,
                                conversation=conversation
                            )
                    else:
                        migration_plan["errors"].append({
                            "conversation_id": conv_id,
                            "error": "Could not determine phone number"
                        })
                        
                except Exception as e:
                    migration_plan["errors"].append({
                        "conversation_id": conv_id,
                        "error": str(e)
                    })
            
            # Summary statistics
            migration_plan["phone_count"] = len(migration_plan["phone_distribution"])
            migration_plan["migratable_conversations"] = len(migration_plan["migration_actions"])
            migration_plan["error_count"] = len(migration_plan["errors"])
            
            if not dry_run:
                logger.info(f"Migration completed: {migration_plan['migratable_conversations']} conversations migrated")
            else:
                logger.info(f"Migration analysis: {migration_plan['migratable_conversations']} conversations ready for migration")
            
            return migration_plan
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {"error": str(e), "dry_run": dry_run}
    
    def _extract_phone_from_conversation(self, conversation: Dict, conv_id: str) -> Optional[str]:
        """
        Extract phone number from conversation data
        
        Args:
            conversation: Conversation document
            conv_id: Conversation ID
            
        Returns:
            Phone number or None if not found
        """
        # Check metadata first
        if 'metadata' in conversation and 'phone_number' in conversation['metadata']:
            return conversation['metadata']['phone_number']
        
        # Check routing_info
        if 'routing_info' in conversation and 'to_phone' in conversation['routing_info']:
            return conversation['routing_info']['to_phone']
        
        # Check messages for business phone context
        messages = conversation.get('messages', [])
        for message in messages:
            if 'to_phone' in message:
                return message['to_phone']
        
        # Try to extract from conversation ID pattern
        # Expected patterns: {channel_id}_{customer_phone}_{timestamp}
        # Or: {business_phone}_{customer_phone}_{timestamp}
        parts = conv_id.split('_')
        if len(parts) >= 2:
            # Look for phone number patterns
            for part in parts:
                if part.startswith('1') and len(part) == 11:  # US number (1 + 10 digits)
                    return f"+{part}"
                elif part.startswith('91') and len(part) >= 12:  # India number (91 + 10+ digits)
                    return f"+{part}"
                elif part.startswith('18') and len(part) == 11:  # Specific US pattern
                    return f"+{part}"
        
        return None
    
    def cleanup_empty_containers(self, dry_run: bool = True) -> Dict:
        """
        Find and optionally delete empty conversation containers
        
        Args:
            dry_run: If True, only analyze without deleting
            
        Returns:
            Cleanup results
        """
        try:
            container_stats = self.conversation_store.list_all_phone_containers()
            
            cleanup_plan = {
                "empty_containers": [],
                "total_containers": len(container_stats),
                "cleanup_actions": [],
                "dry_run": dry_run
            }
            
            for container_stat in container_stats:
                if container_stat['total_conversations'] == 0:
                    cleanup_plan["empty_containers"].append(container_stat)
                    
                    cleanup_plan["cleanup_actions"].append({
                        "action": "delete_container",
                        "container_name": container_stat['container_name'],
                        "phone_number": container_stat['phone_number']
                    })
                    
                    # Perform actual deletion if not dry run
                    if not dry_run:
                        # Note: Cosmos DB doesn't have a direct delete container API via Python SDK
                        # This would typically be done via Azure CLI or portal
                        logger.warning(f"Empty container {container_stat['container_name']} marked for deletion (manual process required)")
            
            cleanup_plan["empty_count"] = len(cleanup_plan["empty_containers"])
            
            return cleanup_plan
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"error": str(e), "dry_run": dry_run}
    
    def export_container_summary(self, output_file: str = None) -> Dict:
        """
        Export a summary of all containers and their contents
        
        Args:
            output_file: Optional file path to save the summary
            
        Returns:
            Container summary data
        """
        try:
            overview = self.get_system_overview()
            summary = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "system_overview": overview,
                "detailed_stats": []
            }
            
            # Get detailed stats for each container
            for phone, container_info in overview.get("containers", {}).items():
                try:
                    detailed_stats = self.conversation_store.get_conversation_stats_for_phone(phone)
                    summary["detailed_stats"].append(detailed_stats)
                except Exception as e:
                    summary["detailed_stats"].append({
                        "phone_number": phone,
                        "error": str(e)
                    })
            
            # Save to file if requested
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(summary, f, indent=2)
                logger.info(f"Container summary exported to {output_file}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"error": str(e)}


# CLI utility functions
if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Conversation Container Management Utility")
    parser.add_argument("command", choices=[
        "overview", "create-missing", "migrate", "migrate-dry-run", 
        "cleanup", "cleanup-dry-run", "export"
    ])
    parser.add_argument("--old-container", default="conversations", help="Old container name for migration")
    parser.add_argument("--output", help="Output file for export")
    
    args = parser.parse_args()
    
    manager = ConversationContainerManager()
    
    if args.command == "overview":
        result = manager.get_system_overview()
        print(json.dumps(result, indent=2))
    
    elif args.command == "create-missing":
        result = manager.create_missing_containers()
        print(json.dumps(result, indent=2))
    
    elif args.command == "migrate":
        result = manager.migrate_old_conversations(args.old_container, dry_run=False)
        print(json.dumps(result, indent=2))
    
    elif args.command == "migrate-dry-run":
        result = manager.migrate_old_conversations(args.old_container, dry_run=True)
        print(json.dumps(result, indent=2))
    
    elif args.command == "cleanup":
        result = manager.cleanup_empty_containers(dry_run=False)
        print(json.dumps(result, indent=2))
    
    elif args.command == "cleanup-dry-run":
        result = manager.cleanup_empty_containers(dry_run=True)
        print(json.dumps(result, indent=2))
    
    elif args.command == "export":
        result = manager.export_container_summary(args.output)
        print(json.dumps(result, indent=2))
