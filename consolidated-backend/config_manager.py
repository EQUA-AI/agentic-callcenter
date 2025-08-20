"""
Configuration Manager for Multi-Agent WhatsApp Business Integration
Manages multiple phone numbers, AI agents, and messaging channels
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, validator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Configuration Models
class AgentConfig(BaseModel):
    """Configuration for an AI Agent"""
    agent_id: str
    agent_name: str
    foundry_endpoint: str
    description: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    
    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not v.startswith('asst_'):
            raise ValueError('Agent ID must start with "asst_"')
        return v
    
    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        super().__init__(**data)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ChannelConfig(BaseModel):
    """Configuration for a messaging channel"""
    channel_id: str
    channel_name: str
    channel_type: str  # 'whatsapp', 'sms'
    provider: str  # 'infobip', 'acs'
    phone_number: str
    business_name: str = ""
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not v.startswith('+'):
            raise ValueError('Phone number must be in E.164 format (+1234567890)')
        return v
    
    @validator('channel_type')
    def validate_channel_type(cls, v):
        allowed_types = ['whatsapp', 'sms']
        if v.lower() not in allowed_types:
            raise ValueError(f'Channel type must be one of: {allowed_types}')
        return v.lower()
    
    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        super().__init__(**data)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class AgentChannelMapping(BaseModel):
    """Mapping between agents and channels"""
    mapping_id: str
    agent_id: str
    channel_id: str
    is_primary: bool = False  # Primary channel for this agent
    routing_rules: Dict = {}  # Additional routing logic
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        super().__init__(**data)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

@dataclass
class ConfigManagerStats:
    """Statistics for the configuration manager"""
    total_agents: int
    total_channels: int
    total_mappings: int
    active_channels: int
    whatsapp_channels: int
    sms_channels: int

class ConfigurationManager:
    """
    Manages configurations for multi-agent WhatsApp Business integration
    """
    
    def __init__(self):
        # Initialize Cosmos DB connection
        self.credential = DefaultAzureCredential()
        self.cosmos_endpoint = os.getenv("COSMOSDB_ENDPOINT")
        self.database_name = os.getenv("COSMOSDB_DATABASE", "CallCenterDB")
        self.config_container_name = "agent_configs"
        
        if not self.cosmos_endpoint:
            raise ValueError("COSMOSDB_ENDPOINT environment variable is required")
        
        # Initialize database
        self._init_database()
        
        # Cache for performance
        self._agents_cache = {}
        self._channels_cache = {}
        self._mappings_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def _init_database(self):
        """Initialize Cosmos DB database and containers"""
        try:
            self.cosmos_client = CosmosClient(
                url=self.cosmos_endpoint,
                credential=self.credential
            )
            
            # Create database if it doesn't exist
            self.database = self.cosmos_client.create_database_if_not_exists(
                id=self.database_name
            )
            
            # Create containers if they don't exist
            self.agents_container = self.database.create_container_if_not_exists(
                id="agents",
                partition_key="/agent_id"
            )
            
            self.channels_container = self.database.create_container_if_not_exists(
                id="channels",
                partition_key="/channel_id"
            )
            
            self.mappings_container = self.database.create_container_if_not_exists(
                id="agent_channel_mappings",
                partition_key="/mapping_id"
            )
            
            logger.info("Configuration database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _refresh_cache_if_needed(self):
        """Refresh cache if expired"""
        now = datetime.utcnow()
        if (self._cache_timestamp is None or 
            (now - self._cache_timestamp).seconds > self._cache_ttl):
            self._refresh_cache()
    
    def _refresh_cache(self):
        """Refresh all caches"""
        try:
            # Refresh agents cache
            agents = list(self.agents_container.read_all_items())
            self._agents_cache = {agent['agent_id']: agent for agent in agents}
            
            # Refresh channels cache
            channels = list(self.channels_container.read_all_items())
            self._channels_cache = {channel['channel_id']: channel for channel in channels}
            
            # Refresh mappings cache
            mappings = list(self.mappings_container.read_all_items())
            self._mappings_cache = {mapping['mapping_id']: mapping for mapping in mappings}
            
            self._cache_timestamp = datetime.utcnow()
            logger.info("Configuration cache refreshed")
            
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
    
    # Agent Management
    def add_agent(self, agent_config: AgentConfig) -> bool:
        """Add a new AI agent configuration"""
        try:
            agent_dict = agent_config.dict()
            agent_dict['id'] = agent_config.agent_id  # Cosmos DB requires 'id' field
            
            # Convert datetime objects to ISO format strings for JSON serialization
            if agent_dict.get('created_at') and isinstance(agent_dict['created_at'], datetime):
                agent_dict['created_at'] = agent_dict['created_at'].isoformat()
            if agent_dict.get('updated_at') and isinstance(agent_dict['updated_at'], datetime):
                agent_dict['updated_at'] = agent_dict['updated_at'].isoformat()
            
            self.agents_container.create_item(agent_dict)
            self._agents_cache[agent_config.agent_id] = agent_dict
            
            logger.info(f"Added agent: {agent_config.agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add agent {agent_config.agent_id}: {e}")
            return False
    
    def update_agent(self, agent_id: str, updates: Dict) -> bool:
        """Update an existing agent configuration"""
        try:
            # Get existing agent
            existing_agent = self.agents_container.read_item(
                item=agent_id,
                partition_key=agent_id
            )
            
            # Apply updates
            for key, value in updates.items():
                if key != 'agent_id':  # Don't allow changing the ID
                    existing_agent[key] = value
            
            existing_agent['updated_at'] = datetime.utcnow().isoformat()
            
            # Update in database
            self.agents_container.replace_item(
                item=agent_id,
                body=existing_agent
            )
            
            # Update cache
            self._agents_cache[agent_id] = existing_agent
            
            logger.info(f"Updated agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update agent {agent_id}: {e}")
            return False
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent configuration"""
        try:
            # First, remove all mappings for this agent
            mappings = self.get_mappings_by_agent(agent_id)
            for mapping in mappings:
                self.remove_mapping(mapping['mapping_id'])
            
            # Remove the agent
            self.agents_container.delete_item(
                item=agent_id,
                partition_key=agent_id
            )
            
            # Remove from cache
            if agent_id in self._agents_cache:
                del self._agents_cache[agent_id]
            
            logger.info(f"Removed agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove agent {agent_id}: {e}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get a specific agent configuration"""
        self._refresh_cache_if_needed()
        return self._agents_cache.get(agent_id)
    
    def list_agents(self) -> List[Dict]:
        """List all agent configurations"""
        self._refresh_cache_if_needed()
        return list(self._agents_cache.values())
    
    # Channel Management
    def add_channel(self, channel_config: ChannelConfig) -> bool:
        """Add a new messaging channel configuration"""
        try:
            channel_dict = channel_config.dict()
            channel_dict['id'] = channel_config.channel_id  # Cosmos DB requires 'id' field
            
            # Convert datetime objects to ISO format strings for JSON serialization
            if channel_dict.get('created_at') and isinstance(channel_dict['created_at'], datetime):
                channel_dict['created_at'] = channel_dict['created_at'].isoformat()
            if channel_dict.get('updated_at') and isinstance(channel_dict['updated_at'], datetime):
                channel_dict['updated_at'] = channel_dict['updated_at'].isoformat()
            
            self.channels_container.create_item(channel_dict)
            self._channels_cache[channel_config.channel_id] = channel_dict
            
            logger.info(f"Added channel: {channel_config.channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add channel {channel_config.channel_id}: {e}")
            return False
    
    def update_channel(self, channel_id: str, updates: Dict) -> bool:
        """Update an existing channel configuration"""
        try:
            # Get existing channel
            existing_channel = self.channels_container.read_item(
                item=channel_id,
                partition_key=channel_id
            )
            
            # Apply updates
            for key, value in updates.items():
                if key != 'channel_id':  # Don't allow changing the ID
                    existing_channel[key] = value
            
            existing_channel['updated_at'] = datetime.utcnow().isoformat()
            
            # Update in database
            self.channels_container.replace_item(
                item=channel_id,
                body=existing_channel
            )
            
            # Update cache
            self._channels_cache[channel_id] = existing_channel
            
            logger.info(f"Updated channel: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update channel {channel_id}: {e}")
            return False
    
    def remove_channel(self, channel_id: str) -> bool:
        """Remove a channel configuration"""
        try:
            # First, remove all mappings for this channel
            mappings = self.get_mappings_by_channel(channel_id)
            for mapping in mappings:
                self.remove_mapping(mapping['mapping_id'])
            
            # Remove the channel
            self.channels_container.delete_item(
                item=channel_id,
                partition_key=channel_id
            )
            
            # Remove from cache
            if channel_id in self._channels_cache:
                del self._channels_cache[channel_id]
            
            logger.info(f"Removed channel: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove channel {channel_id}: {e}")
            return False
    
    def get_channel(self, channel_id: str) -> Optional[Dict]:
        """Get a specific channel configuration"""
        self._refresh_cache_if_needed()
        return self._channels_cache.get(channel_id)
    
    def get_channel_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get channel configuration by phone number"""
        self._refresh_cache_if_needed()
        for channel in self._channels_cache.values():
            if channel.get('phone_number') == phone_number:
                return channel
        return None
    
    def list_channels(self, channel_type: Optional[str] = None, is_active: Optional[bool] = None) -> List[Dict]:
        """List channels with optional filtering"""
        self._refresh_cache_if_needed()
        channels = list(self._channels_cache.values())
        
        if channel_type:
            channels = [c for c in channels if c.get('channel_type') == channel_type.lower()]
        
        if is_active is not None:
            channels = [c for c in channels if c.get('is_active') == is_active]
        
        return channels
    
    # Mapping Management
    def add_mapping(self, mapping: AgentChannelMapping) -> bool:
        """Add agent-channel mapping"""
        try:
            mapping_dict = mapping.dict()
            mapping_dict['id'] = mapping.mapping_id  # Cosmos DB requires 'id' field
            
            # Convert datetime objects to ISO format strings for JSON serialization
            if mapping_dict.get('created_at') and isinstance(mapping_dict['created_at'], datetime):
                mapping_dict['created_at'] = mapping_dict['created_at'].isoformat()
            if mapping_dict.get('updated_at') and isinstance(mapping_dict['updated_at'], datetime):
                mapping_dict['updated_at'] = mapping_dict['updated_at'].isoformat()
            
            self.mappings_container.create_item(mapping_dict)
            self._mappings_cache[mapping.mapping_id] = mapping_dict
            
            logger.info(f"Added mapping: {mapping.mapping_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add mapping {mapping.mapping_id}: {e}")
            return False
    
    def remove_mapping(self, mapping_id: str) -> bool:
        """Remove agent-channel mapping"""
        try:
            self.mappings_container.delete_item(
                item=mapping_id,
                partition_key=mapping_id
            )
            
            if mapping_id in self._mappings_cache:
                del self._mappings_cache[mapping_id]
            
            logger.info(f"Removed mapping: {mapping_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove mapping {mapping_id}: {e}")
            return False
    
    def get_mappings_by_agent(self, agent_id: str) -> List[Dict]:
        """Get all mappings for a specific agent"""
        self._refresh_cache_if_needed()
        return [m for m in self._mappings_cache.values() if m.get('agent_id') == agent_id]
    
    def get_mappings_by_channel(self, channel_id: str) -> List[Dict]:
        """Get all mappings for a specific channel"""
        self._refresh_cache_if_needed()
        return [m for m in self._mappings_cache.values() if m.get('channel_id') == channel_id]
    
    def get_agent_for_phone(self, phone_number: str) -> Optional[Dict]:
        """Get the agent configuration for a given phone number"""
        # First find the channel
        channel = self.get_channel_by_phone(phone_number)
        if not channel:
            return None
        
        # Then find the mapping
        mappings = self.get_mappings_by_channel(channel['channel_id'])
        if not mappings:
            return None
        
        # Get the first active mapping (or primary if available)
        active_mappings = [m for m in mappings if m.get('is_active', True)]
        if not active_mappings:
            return None
        
        # Prefer primary mapping
        primary_mapping = next((m for m in active_mappings if m.get('is_primary')), active_mappings[0])
        
        # Return the agent configuration
        return self.get_agent(primary_mapping['agent_id'])
    
    def get_channels_for_agent(self, agent_id: str) -> List[Dict]:
        """Get all channels assigned to a specific agent"""
        mappings = self.get_mappings_by_agent(agent_id)
        channels = []
        
        for mapping in mappings:
            if mapping.get('is_active', True):
                channel = self.get_channel(mapping['channel_id'])
                if channel:
                    channels.append(channel)
        
        return channels
    
    # Statistics and Health
    def get_stats(self) -> ConfigManagerStats:
        """Get configuration statistics"""
        self._refresh_cache_if_needed()
        
        total_agents = len(self._agents_cache)
        total_channels = len(self._channels_cache)
        total_mappings = len(self._mappings_cache)
        
        active_channels = sum(1 for c in self._channels_cache.values() if c.get('is_active', True))
        whatsapp_channels = sum(1 for c in self._channels_cache.values() if c.get('channel_type') == 'whatsapp')
        sms_channels = sum(1 for c in self._channels_cache.values() if c.get('channel_type') == 'sms')
        
        return ConfigManagerStats(
            total_agents=total_agents,
            total_channels=total_channels,
            total_mappings=total_mappings,
            active_channels=active_channels,
            whatsapp_channels=whatsapp_channels,
            sms_channels=sms_channels
        )
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate the entire configuration"""
        issues = []
        warnings = []
        
        # Check for orphaned mappings
        for mapping in self._mappings_cache.values():
            agent_id = mapping.get('agent_id')
            channel_id = mapping.get('channel_id')
            
            if agent_id not in self._agents_cache:
                issues.append(f"Mapping {mapping['mapping_id']} references non-existent agent {agent_id}")
            
            if channel_id not in self._channels_cache:
                issues.append(f"Mapping {mapping['mapping_id']} references non-existent channel {channel_id}")
        
        # Check for duplicate phone numbers
        phone_numbers = {}
        for channel in self._channels_cache.values():
            phone = channel.get('phone_number')
            if phone in phone_numbers:
                issues.append(f"Duplicate phone number {phone} in channels {phone_numbers[phone]} and {channel['channel_id']}")
            else:
                phone_numbers[phone] = channel['channel_id']
        
        # Check for agents without channels
        for agent in self._agents_cache.values():
            agent_id = agent['agent_id']
            mappings = self.get_mappings_by_agent(agent_id)
            if not mappings:
                warnings.append(f"Agent {agent_id} has no channel mappings")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "stats": self.get_stats()
        }

# Global configuration manager instance
config_manager = None

def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance"""
    global config_manager
    if config_manager is None:
        config_manager = ConfigurationManager()
    return config_manager
