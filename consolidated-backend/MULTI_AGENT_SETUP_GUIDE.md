# Multi-Agent WhatsApp Business Configuration Guide

This guide walks you through setting up multiple WhatsApp Business numbers, each connected to their respective AI agents using Azure Communication Services Advanced Messaging.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ WhatsApp Bus #1 │────│ ACS Messaging    │────│ AI Agent Wedding    │
│ +1234567890     │    │ Channel Registry │    │ asst_wedding_001    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ WhatsApp Bus #2 │────│ ACS Messaging    │────│ AI Agent Telco      │
│ +1234567891     │    │ Channel Registry │    │ asst_telco_001      │
└─────────────────┘    └──────────────────┘    └─────────────────────┘

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ SMS Number      │────│ ACS Messaging    │────│ AI Agent General    │
│ +1234567892     │    │ Channel Registry │    │ asst_general_001    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

## 🚀 Quick Start

### 1. Run Initial Setup

```bash
cd consolidated-backend
python setup_config.py
```

This will create sample configurations and guide you through the setup process.

### 2. Start the Server

```bash
uvicorn app:app --reload
```

### 3. Access Configuration Dashboard

Visit `http://localhost:8000/config/` to manage your configuration through the web interface.

## 📋 Configuration Components

### AI Agents
- **Agent ID**: Azure AI Foundry agent identifier (starts with `asst_`)
- **Agent Name**: Human-readable name for the agent
- **Foundry Endpoint**: Your Azure AI Foundry service endpoint
- **Description**: What this agent specializes in

### Messaging Channels
- **Channel ID**: Unique identifier for the messaging channel
- **Channel Name**: Human-readable name
- **Channel Type**: `whatsapp` or `sms`
- **Provider**: `infobip` or `acs`
- **Phone Number**: Business phone number in E.164 format (+1234567890)
- **Business Name**: Optional business name for the channel

### Agent-Channel Mappings
- **Mapping ID**: Unique identifier for the mapping
- **Agent ID**: Which AI agent to use
- **Channel ID**: Which messaging channel
- **Is Primary**: Whether this is the primary agent for the channel

## 🔧 Configuration Methods

### Method 1: Web Dashboard (Recommended)

1. **Access Dashboard**: `http://localhost:8000/config/`
2. **Manage Agents**: Add, edit, delete AI agents
3. **Manage Channels**: Add, edit, delete messaging channels
4. **Create Mappings**: Connect agents to channels
5. **Test Configuration**: Validate routing works correctly

### Method 2: REST API

#### List All Agents
```bash
GET /config/api/agents
```

#### Add New Agent
```bash
POST /config/agents/add
Content-Type: application/x-www-form-urlencoded

agent_id=asst_wedding_001&agent_name=Wedding Planner&foundry_endpoint=https://...&description=Wedding specialist
```

#### Get Agent for Phone Number
```bash
GET /config/api/phone/+1234567890/agent
```

### Method 3: Python Script

```python
from config_manager import get_config_manager, AgentConfig, ChannelConfig, AgentChannelMapping

config_manager = get_config_manager()

# Add agent
agent = AgentConfig(
    agent_id="asst_wedding_001",
    agent_name="Wedding Planner",
    foundry_endpoint="https://your-endpoint.cognitiveservices.azure.com/",
    description="Specialized wedding planning assistant"
)
config_manager.add_agent(agent)

# Add channel
channel = ChannelConfig(
    channel_id="wedding-whatsapp-001",
    channel_name="Wedding Business WhatsApp",
    channel_type="whatsapp",
    provider="infobip",
    phone_number="+1234567890",
    business_name="Dream Weddings"
)
config_manager.add_channel(channel)

# Create mapping
mapping = AgentChannelMapping(
    mapping_id="mapping_001",
    agent_id="asst_wedding_001",
    channel_id="wedding-whatsapp-001",
    is_primary=True
)
config_manager.add_mapping(mapping)
```

## 🧪 Testing Your Configuration

### Test Message Routing

```bash
POST /route/message
Content-Type: application/json

{
    "from": "+1999888777",
    "to": "+1234567890",
    "message": "Hello, I need help planning my wedding",
    "conversation_id": "test_conversation_001"
}
```

### Test Agent Lookup

```bash
GET /route/agent/+1234567890
```

### Validate Configuration

```bash
GET /config/api/validation
```

## 📱 Setting Up WhatsApp Business Numbers

### 1. Get Channel Registration IDs

1. Go to Azure Portal → Communication Services → Your ACS Resource
2. Navigate to **Channels** section
3. For each WhatsApp Business number:
   - Note down the **Channel Registration ID**
   - This ID is needed for the messaging configuration

### 2. Update Channel Configurations

Replace the sample `channel_id` values with actual **Channel Registration IDs** from ACS:

```python
# Example: Update channel with actual ACS channel registration ID
config_manager.update_channel("wedding-whatsapp-001", {
    "channel_id": "actual_channel_registration_id_from_acs"
})
```

### 3. Environment Variables

Make sure these environment variables are set:

```bash
# Azure Communication Services
ACS_CONNECTION_STRING="endpoint=https://..."
AZURE_CLIENT_ID="your-managed-identity-client-id"

# Azure AI Foundry
AZURE_AI_FOUNDRY_ENDPOINT="https://your-foundry-endpoint.cognitiveservices.azure.com/"

# Database
COSMOSDB_ENDPOINT="https://your-cosmos-db.documents.azure.com:443/"
COSMOSDB_DATABASE="CallCenterDB"
```

## 🔄 Message Flow

1. **Incoming Message**: Customer sends message to your WhatsApp Business number
2. **Channel Identification**: System identifies which business number received the message
3. **Agent Lookup**: Configuration manager finds the assigned AI agent
4. **Message Processing**: Message is routed to the appropriate Azure AI Foundry agent
5. **Response Generation**: Agent generates personalized response
6. **Response Delivery**: Response is sent back through the same channel

## 📊 Monitoring and Analytics

### Routing Statistics

```bash
GET /route/stats
```

Returns:
- Total active routes
- Routes by channel type (WhatsApp vs SMS)
- Routes by agent
- Configuration validation status

### Health Check

```bash
GET /health
```

Returns overall system health including:
- Messaging Connect status
- Multi-agent routing statistics
- Available endpoints

## 🛠️ Troubleshooting

### Common Issues

**1. "No agent found for phone number"**
- Check if the phone number has a channel configuration
- Verify the channel has an agent mapping
- Ensure the channel is marked as active

**2. "Agent ID must start with 'asst_'"**
- Azure AI Foundry agent IDs always start with `asst_`
- Copy the exact ID from your Foundry workspace

**3. "Phone number already used"**
- Each phone number can only be used in one active channel
- Check for duplicate channel configurations

**4. "Channel registration ID not found"**
- Update channel configurations with actual ACS channel registration IDs
- Get these from Azure Portal → ACS → Channels

### Debug Commands

```bash
# Check configuration validation
curl http://localhost:8000/config/api/validation

# Test specific phone routing
curl "http://localhost:8000/route/agent/+1234567890"

# View routing statistics
curl http://localhost:8000/route/stats

# Export configuration backup
python setup_config.py
# Choose 'y' when prompted to export
```

## 🔒 Security Considerations

- **Managed Identity**: Use Azure Managed Identity for authentication
- **Environment Variables**: Store sensitive data in environment variables
- **Access Control**: Restrict access to configuration endpoints in production
- **Audit Trail**: All configuration changes are timestamped and tracked

## 🚀 Deployment

### Azure Container Apps

1. **Build and Push Container**
```bash
docker build -f backend.dockerfile -t your-registry/multi-agent-backend .
docker push your-registry/multi-agent-backend
```

2. **Update Container App**
```bash
az containerapp update \
  --name your-container-app \
  --resource-group your-rg \
  --image your-registry/multi-agent-backend
```

3. **Set Environment Variables**
```bash
az containerapp update \
  --name your-container-app \
  --resource-group your-rg \
  --set-env-vars \
    AZURE_CLIENT_ID=your-managed-identity-id \
    ACS_CONNECTION_STRING=your-acs-connection-string \
    AZURE_AI_FOUNDRY_ENDPOINT=https://your-foundry-endpoint.com/ \
    COSMOSDB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
```

## 📚 API Reference

### Configuration Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/config/` | Configuration dashboard |
| GET | `/config/agents` | Agents management page |
| GET | `/config/channels` | Channels management page |
| GET | `/config/api/agents` | List all agents (JSON) |
| GET | `/config/api/channels` | List all channels (JSON) |
| GET | `/config/api/phone/{phone}/agent` | Get agent for phone |
| GET | `/config/api/validation` | Validate configuration |
| GET | `/config/api/stats` | Configuration statistics |

### Routing Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/route/message` | Route incoming message |
| GET | `/route/stats` | Routing statistics |
| GET | `/route/agent/{phone}` | Get agent for phone |

### Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Overall health check |
| GET | `/messaging-connect/status` | Messaging service status |

## 🎯 Best Practices

1. **Use Descriptive Names**: Give agents and channels clear, descriptive names
2. **Set Primary Agents**: Always designate one primary agent per channel
3. **Regular Backups**: Export configurations regularly using the setup script
4. **Test Routing**: Always test new configurations before going live
5. **Monitor Performance**: Use the routing statistics to monitor system performance
6. **Environment Separation**: Use different configurations for dev/staging/production

## 📞 Support

If you need help:

1. **Check Logs**: Look at container logs for error messages
2. **Validate Config**: Use `/config/api/validation` to check for issues
3. **Test Routing**: Use `/route/message` to test message flow
4. **Export Config**: Backup your configuration before making changes

## 🔮 Future Enhancements

- **Advanced Routing Rules**: Route based on message content, time of day, etc.
- **Load Balancing**: Distribute messages across multiple agents
- **Conversation Analytics**: Track conversation success metrics
- **Auto-scaling**: Dynamically adjust agent capacity
- **Multi-language Support**: Route based on detected language
