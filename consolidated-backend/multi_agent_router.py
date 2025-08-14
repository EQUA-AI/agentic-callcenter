"""
Multi-Agent Message Routing Service
Routes incoming messages to appropriate AI agents based on phone number
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from config_manager import get_config_manager
# Note: We'll need to import the foundry agent function from the API module
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

try:
    from foundry_agent import ask_foundry
except ImportError:
    # Fallback if import fails
    def ask_foundry(message: str, conversation_id: str = None) -> str:
        """Fallback function when foundry_agent is not available"""
        return f"Echo: {message} (foundry_agent not available)"

logger = logging.getLogger(__name__)

class MultiAgentRouter:
    """
    Routes messages to appropriate AI agents based on configuration
    """
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self._routing_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes
    
    def _refresh_routing_cache(self):
        """Refresh routing cache if needed"""
        now = datetime.utcnow()
        if (self._cache_timestamp is None or 
            (now - self._cache_timestamp).seconds > self._cache_ttl):
            
            # Build routing cache: phone_number -> agent_config
            self._routing_cache = {}
            channels = self.config_manager.list_channels(is_active=True)
            
            for channel in channels:
                phone = channel.get('phone_number')
                if phone:
                    agent = self.config_manager.get_agent_for_phone(phone)
                    if agent:
                        self._routing_cache[phone] = {
                            'agent': agent,
                            'channel': channel
                        }
            
            self._cache_timestamp = now
            logger.info(f"Routing cache refreshed with {len(self._routing_cache)} routes")
    
    def get_agent_for_message(self, from_phone: str, to_phone: str, message_content: str = None) -> Optional[Dict]:
        """
        Get the appropriate agent configuration for an incoming message
        
        Args:
            from_phone: Sender's phone number
            to_phone: Recipient's phone number (your business number)
            message_content: Optional message content for routing logic
            
        Returns:
            Dictionary with agent config and routing info, or None if no agent found
        """
        self._refresh_routing_cache()
        
        # Normalize phone numbers to E.164 format
        if not to_phone.startswith('+'):
            to_phone = '+' + to_phone
        
        # Find the route based on the business phone number (to_phone)
        route = self._routing_cache.get(to_phone)
        
        if not route:
            logger.warning(f"No agent configuration found for business number: {to_phone}")
            return None
        
        agent_config = route['agent']
        channel_config = route['channel']
        
        # Add routing metadata
        routing_info = {
            'agent_id': agent_config['agent_id'],
            'agent_name': agent_config['agent_name'],
            'foundry_endpoint': agent_config['foundry_endpoint'],
            'channel_id': channel_config['channel_id'],
            'channel_name': channel_config['channel_name'],
            'channel_type': channel_config['channel_type'],
            'business_phone': to_phone,
            'customer_phone': from_phone,
            'routing_timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Routed message from {from_phone} to agent {agent_config['agent_name']} via {channel_config['channel_name']}")
        
        return routing_info
    
    async def process_message(self, from_phone: str, to_phone: str, message_content: str, conversation_id: str = None) -> Dict[str, Any]:
        """
        Process an incoming message through the appropriate agent
        
        Args:
            from_phone: Sender's phone number
            to_phone: Business phone number that received the message
            message_content: The message content
            conversation_id: Optional conversation ID for context
            
        Returns:
            Dictionary with agent response and routing information
        """
        try:
            # Get the appropriate agent
            routing_info = self.get_agent_for_message(from_phone, to_phone, message_content)
            
            if not routing_info:
                return {
                    'success': False,
                    'error': f'No agent configured for business number {to_phone}',
                    'routing_info': None,
                    'response': None
                }
            
            # Create conversation ID if not provided
            if not conversation_id:
                conversation_id = f"{routing_info['channel_id']}_{from_phone.replace('+', '')}_{int(datetime.utcnow().timestamp())}"
            
            # Process message through the agent
            # Note: We'll need to modify ask_foundry to accept agent_id and foundry_endpoint
            agent_response = await self._call_foundry_agent(
                message_content=message_content,
                conversation_id=conversation_id,
                agent_config=routing_info
            )
            
            return {
                'success': True,
                'routing_info': routing_info,
                'response': agent_response,
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {
                'success': False,
                'error': str(e),
                'routing_info': routing_info if 'routing_info' in locals() else None,
                'response': None
            }
    
    async def _call_foundry_agent(self, message_content: str, conversation_id: str, agent_config: Dict) -> str:
        """
        Call the appropriate Azure AI Foundry agent
        
        Args:
            message_content: The user's message
            conversation_id: Conversation ID for context
            agent_config: Agent configuration from routing
            
        Returns:
            Agent's response
        """
        try:
            # For now, use the existing ask_foundry function
            # TODO: Modify ask_foundry to accept agent_id and endpoint parameters
            response = ask_foundry(message_content, conversation_id)
            
            logger.info(f"Agent {agent_config['agent_name']} responded to conversation {conversation_id}")
            return response
            
        except Exception as e:
            logger.error(f"Foundry agent call failed for {agent_config['agent_id']}: {e}")
            return f"I apologize, but I'm experiencing technical difficulties. Please try again later. (Agent: {agent_config['agent_name']})"
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        self._refresh_routing_cache()
        
        stats = {
            'total_routes': len(self._routing_cache),
            'active_agents': len(set(route['agent']['agent_id'] for route in self._routing_cache.values())),
            'active_channels': len(self._routing_cache),
            'routes_by_type': {},
            'routes_by_agent': {},
            'cache_updated': self._cache_timestamp.isoformat() if self._cache_timestamp else None
        }
        
        # Count by channel type
        for route in self._routing_cache.values():
            channel_type = route['channel']['channel_type']
            stats['routes_by_type'][channel_type] = stats['routes_by_type'].get(channel_type, 0) + 1
        
        # Count by agent
        for route in self._routing_cache.values():
            agent_name = route['agent']['agent_name']
            stats['routes_by_agent'][agent_name] = stats['routes_by_agent'].get(agent_name, 0) + 1
        
        return stats
    
    def validate_routing_config(self) -> Dict[str, Any]:
        """Validate routing configuration"""
        self._refresh_routing_cache()
        
        issues = []
        warnings = []
        
        # Check for phone numbers without agents
        all_channels = self.config_manager.list_channels(is_active=True)
        for channel in all_channels:
            phone = channel.get('phone_number')
            if phone not in self._routing_cache:
                issues.append(f"Channel {channel['channel_name']} ({phone}) has no agent mapping")
        
        # Check for duplicate phone numbers in cache
        phone_count = {}
        for phone in self._routing_cache.keys():
            phone_count[phone] = phone_count.get(phone, 0) + 1
        
        for phone, count in phone_count.items():
            if count > 1:
                issues.append(f"Phone number {phone} has multiple active routes")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_routes': len(self._routing_cache),
            'validation_timestamp': datetime.utcnow().isoformat()
        }

# Global router instance
multi_agent_router = None

def get_multi_agent_router() -> MultiAgentRouter:
    """Get the global multi-agent router instance"""
    global multi_agent_router
    if multi_agent_router is None:
        multi_agent_router = MultiAgentRouter()
    return multi_agent_router
