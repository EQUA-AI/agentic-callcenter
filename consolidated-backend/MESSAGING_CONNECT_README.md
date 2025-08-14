# Azure Communication Services Messaging Connect Integration

This integration adds **separate** messaging capabilities using Azure Communication Services Messaging Connect with Infobip channels. This implementation is **completely independent** from the existing WhatsApp functionality and uses different phone numbers for testing.

## Architecture

- **Traditional ACS WhatsApp**: Uses existing Azure Communication Services SDK for WhatsApp messaging
- **Messaging Connect**: Uses REST API for Infobip channels (WhatsApp, SMS) with separate phone numbers
- **No Mixing**: Both services run independently and use different endpoints and phone numbers

## Features

- **Separate Messaging Services**: Messaging Connect runs alongside existing WhatsApp without interference
- **REST API Integration**: Uses ACS Messaging Connect REST API (no Python SDK dependency)
- **Managed Identity Authentication**: Secure authentication using Azure Managed Identity
- **Infobip Integration**: Support for Infobip phone numbers and advanced messaging features
- **Independent Testing**: Different endpoints and phone numbers for each service

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MESSAGING_CONNECT_ENABLED` | Enable Messaging Connect (true/false) | Yes |
| `ACS_ENDPOINT` | Azure Communication Services endpoint | Yes |
| `AZURE_CLIENT_ID` | User Assigned Managed Identity Client ID | Yes |
| `WHATSAPP_CHANNEL_ID` | WhatsApp channel registration ID | Yes |
| `SMS_CHANNEL_ID` | SMS channel registration ID (Infobip) | Optional |

### Bicep Parameters

```bicep
// Enable Messaging Connect
messagingConnectEnabled: true

// Infobip channel IDs
whatsappChannelId: "your-infobip-whatsapp-channel-id"
smsChannelId: "your-infobip-sms-channel-id"
```

## Usage

### Basic Message Sending

```python
from messaging_connect import get_messaging_connect_service

# Send message via Infobip channel (separate from existing WhatsApp)
messaging_service = get_messaging_connect_service()
result = await messaging_service.send_infobip_message(
    channel_id="your-infobip-channel-id",
    phone_number="+1234567890", 
    message="Hello from Messaging Connect!"
)
```

### WhatsApp via Messaging Connect

```python
# Send WhatsApp message via Messaging Connect (different number than existing WhatsApp)
result = await messaging_service.client.send_whatsapp_message(
    channel_id="your-infobip-whatsapp-channel-id",
    to="+1234567890",
    message="Hello from Messaging Connect WhatsApp!"
)
```

### SMS via Messaging Connect

```python
# Send SMS message via Messaging Connect
result = await messaging_service.client.send_sms_message(
    channel_id="your-infobip-sms-channel-id",
    to="+1234567890",
    message="Your verification code is 123456"
)
```

## API Endpoints

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "messaging_connect_enabled": true,
  "acs_endpoint": "https://your-acs.communication.azure.com",
  "service": "consolidated-backend"
}
```

### Test Traditional ACS WhatsApp
```http
POST /messaging/test
Content-Type: application/json

{
  "note": "This tests existing WhatsApp functionality"
}
```

### Test Messaging Connect (Separate)
```http
POST /messaging-connect/test
Content-Type: application/json

{
  "channel_id": "your-infobip-channel-id",
  "phone_number": "+1234567890",
  "message": "Test message from Messaging Connect"
}
```

Response:
```json
{
  "success": true,
  "result": {
    "message_id": "msg_123456",
    "status": "accepted"
  },
  "service": "messaging_connect"
}
```

## Channel Priority

Messaging Connect operates independently with its own channels:

1. **WhatsApp via Messaging Connect** - Using Infobip WhatsApp channel
2. **SMS via Messaging Connect** - Using Infobip SMS channel

Note: These are separate from traditional ACS WhatsApp and use different phone numbers.

## Error Handling

The integration includes comprehensive error handling:

- **Authentication failures**: Automatic token refresh
- **Channel failures**: Automatic fallback to next available channel
- **Rate limiting**: Built-in retry logic
- **Logging**: Detailed logs for debugging

## Infobip Integration

This integration supports Infobip's advanced features:

### WhatsApp Business Features
- Template messages
- Media messages (images, documents)
- Interactive messages (buttons, lists)
- Rich text formatting

### SMS Features
- International delivery
- Delivery receipts
- Two-way messaging
- Unicode support

## Deployment

The integration is automatically deployed with the consolidated backend when `messagingConnectEnabled` is set to `true` in the Bicep configuration.

### Azure Resources Required

1. **Azure Communication Services** - Primary messaging service
2. **User Assigned Managed Identity** - Authentication
3. **Infobip Account** - Number provisioning and routing
4. **Container Apps** - Hosting environment

## Monitoring

### Logs
All messaging activities are logged with appropriate levels:
- `INFO`: Successful operations
- `WARNING`: Fallback channel usage
- `ERROR`: Failed operations

### Metrics
Monitor these key metrics:
- Message delivery success rate
- Channel usage distribution
- Authentication failures
- API response times

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Managed Identity has correct permissions
   - Check `AZURE_CLIENT_ID` environment variable

2. **Channel Failures**
   - Verify channel registration IDs
   - Check Infobip account status
   - Validate phone number formats (E.164)

3. **Message Delivery Issues**
   - Check recipient phone number validity
   - Verify channel capabilities (WhatsApp opt-in status)
   - Review rate limiting settings

### Debug Mode

Enable debug logging by setting log level to `DEBUG`:

```python
import logging
logging.getLogger("messaging_connect").setLevel(logging.DEBUG)
```
