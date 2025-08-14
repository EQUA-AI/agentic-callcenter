# Infobip SMS Setup Guide

## Prerequisites ✅
- [x] Infobip account connected to ACS ✅ (You've done this!)
- [ ] Container app deployed with environment variables
- [ ] Infobip channel registration ID

## Required Environment Variables

Add these to your container app environment:

```bash
# Enable Messaging Connect
MESSAGING_CONNECT_ENABLED=true

# Your ACS endpoint (should already be set)
ACS_ENDPOINT=https://your-acs-resource.communication.azure.com

# Your Managed Identity Client ID (should already be set)
AZURE_CLIENT_ID=your-managed-identity-client-id

# Infobip channel IDs (GET THESE FROM ACS PORTAL)
SMS_CHANNEL_ID=your-infobip-sms-channel-registration-id
WHATSAPP_CHANNEL_ID=your-infobip-whatsapp-channel-registration-id  # Optional
```

## How to Find Your Channel Registration IDs

1. **Go to Azure Portal → Your ACS Resource → Channels**
2. **Find your Infobip integration**
3. **Copy the Channel Registration ID** (it looks like a GUID)

Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

## Testing Steps

1. **Deploy your updated container app** with the environment variables above

2. **Check health status:**
   ```bash
   curl https://your-app.azurecontainerapps.io/health
   ```

3. **Check Messaging Connect status:**
   ```bash
   curl https://your-app.azurecontainerapps.io/messaging-connect/status
   ```

4. **Test SMS:**
   ```bash
   curl -X POST https://your-app.azurecontainerapps.io/messaging-connect/test-sms \
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "+1234567890",
       "message": "Test SMS from Infobip!"
     }'
   ```

5. **Or use the Python test script:**
   ```bash
   cd test-scripts
   python test_infobip_sms.py
   ```
   (Update the script with your container app URL and test phone number first)

## Common Issues & Solutions

### 1. "Messaging Connect not enabled"
- Check: `MESSAGING_CONNECT_ENABLED=true` in environment variables

### 2. "SMS channel ID not configured"
- Check: `SMS_CHANNEL_ID` is set to your Infobip channel registration ID
- Verify: The channel ID is copied correctly from ACS portal

### 3. "Authentication failed"
- Check: `AZURE_CLIENT_ID` matches your managed identity
- Verify: Managed identity has proper permissions on ACS resource

### 4. "HTTP 403 Forbidden"
- Check: Managed identity has "Communication Services Data Contributor" role on ACS
- Verify: Container app is using the correct managed identity

### 5. "HTTP 404 Not Found"
- Check: ACS endpoint URL is correct
- Verify: Messaging Connect is enabled on your ACS resource

### 6. "Channel not found"
- Check: Channel registration ID is correct
- Verify: Infobip integration is properly configured in ACS

## Environment Variable Examples

For Container Apps deployment, add to your Bicep or ARM template:

```bicep
env: [
  {
    name: 'MESSAGING_CONNECT_ENABLED'
    value: 'true'
  }
  {
    name: 'SMS_CHANNEL_ID'
    value: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'  // Your actual ID
  }
  {
    name: 'WHATSAPP_CHANNEL_ID'
    value: 'b2c3d4e5-f6g7-8901-bcde-fg2345678901'  // Your actual ID
  }
]
```

## Next Steps

1. **Get your channel registration IDs** from ACS portal
2. **Update environment variables** in your container app
3. **Redeploy** your container app
4. **Test SMS** using the endpoints above
5. **Monitor logs** for any errors

## Support

If you encounter issues:
1. Check container app logs in Azure Portal
2. Verify ACS Messaging Connect configuration
3. Test with a simple SMS first before complex scenarios
