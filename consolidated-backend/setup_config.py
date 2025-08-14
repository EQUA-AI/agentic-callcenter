"""
Multi-Agent Configuration Setup Script
Helps you set up your WhatsApp Business numbers with AI agents
"""
import asyncio
import json
import os
from typing import List, Dict

from config_manager import (
    get_config_manager, 
    AgentConfig, 
    ChannelConfig, 
    AgentChannelMapping
)

class ConfigSetup:
    """Helper class for setting up multi-agent configurations"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
    
    def create_sample_configuration(self):
        """Create a sample configuration to get you started"""
        
        print("🚀 Setting up sample multi-agent configuration...")
        
        # Sample agents
        agents = [
            {
                "agent_id": "asst_wedding_planner_001",
                "agent_name": "Wedding Planner Assistant",
                "foundry_endpoint": os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "https://your-foundry-endpoint.cognitiveservices.azure.com/"),
                "description": "Specialized in wedding planning, venue booking, and vendor coordination"
            },
            {
                "agent_id": "asst_telco_support_001", 
                "agent_name": "Telco Customer Support",
                "foundry_endpoint": os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "https://your-foundry-endpoint.cognitiveservices.azure.com/"),
                "description": "Handles telecom customer support, billing inquiries, and technical issues"
            },
            {
                "agent_id": "asst_general_assistant_001",
                "agent_name": "General Business Assistant",
                "foundry_endpoint": os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", "https://your-foundry-endpoint.cognitiveservices.azure.com/"),
                "description": "General purpose business assistant for various inquiries"
            }
        ]
        
        # Sample channels (you'll need to update these with your actual numbers and channel IDs)
        channels = [
            {
                "channel_id": "wedding-whatsapp-infobip-001",
                "channel_name": "Wedding Business WhatsApp",
                "channel_type": "whatsapp",
                "provider": "infobip",
                "phone_number": "+1234567890",  # Replace with your actual WhatsApp Business number
                "business_name": "Dream Weddings Co."
            },
            {
                "channel_id": "telco-whatsapp-infobip-001",
                "channel_name": "Telco Support WhatsApp", 
                "channel_type": "whatsapp",
                "provider": "infobip",
                "phone_number": "+1234567891",  # Replace with your actual WhatsApp Business number
                "business_name": "TelcoSupport Inc."
            },
            {
                "channel_id": "general-sms-infobip-001",
                "channel_name": "General SMS Support",
                "channel_type": "sms",
                "provider": "infobip", 
                "phone_number": "+1234567892",  # Replace with your actual SMS number
                "business_name": "General Business"
            }
        ]
        
        # Add agents
        print("\n📋 Adding AI Agents...")
        for agent_data in agents:
            try:
                agent_config = AgentConfig(**agent_data)
                success = self.config_manager.add_agent(agent_config)
                if success:
                    print(f"✅ Added agent: {agent_data['agent_name']} ({agent_data['agent_id']})")
                else:
                    print(f"❌ Failed to add agent: {agent_data['agent_name']}")
            except Exception as e:
                print(f"❌ Error adding agent {agent_data['agent_name']}: {e}")
        
        # Add channels
        print("\n📱 Adding Messaging Channels...")
        for channel_data in channels:
            try:
                channel_config = ChannelConfig(**channel_data)
                success = self.config_manager.add_channel(channel_config)
                if success:
                    print(f"✅ Added channel: {channel_data['channel_name']} ({channel_data['phone_number']})")
                else:
                    print(f"❌ Failed to add channel: {channel_data['channel_name']}")
            except Exception as e:
                print(f"❌ Error adding channel {channel_data['channel_name']}: {e}")
        
        # Create mappings
        print("\n🔗 Creating Agent-Channel Mappings...")
        mappings = [
            {
                "mapping_id": "mapping_wedding_001",
                "agent_id": "asst_wedding_planner_001",
                "channel_id": "wedding-whatsapp-infobip-001",
                "is_primary": True
            },
            {
                "mapping_id": "mapping_telco_001", 
                "agent_id": "asst_telco_support_001",
                "channel_id": "telco-whatsapp-infobip-001",
                "is_primary": True
            },
            {
                "mapping_id": "mapping_general_001",
                "agent_id": "asst_general_assistant_001", 
                "channel_id": "general-sms-infobip-001",
                "is_primary": True
            }
        ]
        
        for mapping_data in mappings:
            try:
                mapping = AgentChannelMapping(**mapping_data)
                success = self.config_manager.add_mapping(mapping)
                if success:
                    print(f"✅ Created mapping: {mapping_data['agent_id']} → {mapping_data['channel_id']}")
                else:
                    print(f"❌ Failed to create mapping: {mapping_data['agent_id']} → {mapping_data['channel_id']}")
            except Exception as e:
                print(f"❌ Error creating mapping: {e}")
        
        print("\n✨ Sample configuration complete!")
        print("\n⚠️  IMPORTANT: You need to update the following:")
        print("   1. Replace sample phone numbers with your actual WhatsApp Business numbers")
        print("   2. Update agent IDs with your actual Azure AI Foundry agent IDs")
        print("   3. Get channel registration IDs from ACS portal for each WhatsApp number")
        print("   4. Visit /config/ to manage your configuration through the web UI")
    
    def validate_setup(self):
        """Validate the current configuration"""
        print("🔍 Validating configuration...")
        
        validation = self.config_manager.validate_configuration()
        stats = self.config_manager.get_stats()
        
        print(f"\n📊 Configuration Statistics:")
        print(f"   Total Agents: {stats.total_agents}")
        print(f"   Total Channels: {stats.total_channels}")
        print(f"   WhatsApp Channels: {stats.whatsapp_channels}")
        print(f"   SMS Channels: {stats.sms_channels}")
        print(f"   Active Channels: {stats.active_channels}")
        print(f"   Total Mappings: {stats.total_mappings}")
        
        if validation['valid']:
            print("\n✅ Configuration is valid!")
        else:
            print("\n❌ Configuration issues found:")
            for issue in validation['issues']:
                print(f"   • {issue}")
        
        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"   • {warning}")
    
    def export_configuration(self, filename: str = "agent_config_backup.json"):
        """Export current configuration to JSON file"""
        try:
            agents = self.config_manager.list_agents()
            channels = self.config_manager.list_channels()
            
            # Get all mappings
            mappings = []
            for agent in agents:
                agent_mappings = self.config_manager.get_mappings_by_agent(agent['agent_id'])
                mappings.extend(agent_mappings)
            
            config_export = {
                "export_timestamp": self.config_manager._cache_timestamp.isoformat() if self.config_manager._cache_timestamp else None,
                "agents": agents,
                "channels": channels,
                "mappings": mappings
            }
            
            with open(filename, 'w') as f:
                json.dump(config_export, f, indent=2, default=str)
            
            print(f"✅ Configuration exported to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export configuration: {e}")
            return False
    
    def display_routing_summary(self):
        """Display a summary of current routing configuration"""
        print("🚦 Current Routing Configuration:")
        print("=" * 60)
        
        channels = self.config_manager.list_channels(is_active=True)
        
        for channel in channels:
            phone = channel['phone_number']
            agent = self.config_manager.get_agent_for_phone(phone)
            
            print(f"\n📱 {channel['channel_name']}")
            print(f"   Phone: {phone}")
            print(f"   Type: {channel['channel_type'].upper()}")
            print(f"   Provider: {channel['provider'].title()}")
            
            if agent:
                print(f"   → Routed to: {agent['agent_name']} ({agent['agent_id']})")
            else:
                print(f"   ❌ No agent assigned!")
        
        print("\n" + "=" * 60)

def main():
    """Main setup function"""
    print("🤖 Multi-Agent WhatsApp Business Configuration Setup")
    print("=" * 55)
    
    setup = ConfigSetup()
    
    # Check if configuration already exists
    stats = setup.config_manager.get_stats()
    
    if stats.total_agents == 0 and stats.total_channels == 0:
        print("\n🆕 No existing configuration found.")
        
        choice = input("\nWould you like to create a sample configuration? (y/n): ").lower().strip()
        
        if choice == 'y':
            setup.create_sample_configuration()
        else:
            print("\n📝 You can manually configure agents and channels via:")
            print("   • Web UI: Visit /config/ after starting the server")
            print("   • API: Use the REST endpoints under /config/api/")
    else:
        print(f"\n📋 Found existing configuration:")
        print(f"   Agents: {stats.total_agents}")
        print(f"   Channels: {stats.total_channels}")
        print(f"   Mappings: {stats.total_mappings}")
    
    # Always show current routing summary
    print("\n" + "="*60)
    setup.display_routing_summary()
    
    # Validate configuration
    print("\n" + "="*60)
    setup.validate_setup()
    
    # Export option
    print("\n" + "="*60)
    export_choice = input("\nWould you like to export current configuration to backup file? (y/n): ").lower().strip()
    if export_choice == 'y':
        setup.export_configuration()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("   1. Start your server: uvicorn app:app --reload")
    print("   2. Visit the configuration dashboard: http://localhost:8000/config/")
    print("   3. Update phone numbers and agent IDs with your actual values")
    print("   4. Get channel registration IDs from Azure Communication Services portal")
    print("   5. Test your configuration using the /route/message endpoint")

if __name__ == "__main__":
    main()
