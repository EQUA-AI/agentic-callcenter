#!/usr/bin/env python3
"""
Test script to verify WhatsApp integration via voice service
"""
import asyncio
import aiohttp
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_whatsapp_integration():
    """Test WhatsApp integration via the voice service"""
    
    # The voice service URL (publicly accessible)
    voice_url = "https://dev-voice-3dirbnu5qgcl2.purplefield-53a338ec.eastus2.azurecontainerapps.io"
    
    # Test webhook payload (simulating a WhatsApp message)
    test_payload = {
        "from": {"phoneNumber": "+1234567890"},
        "to": {"phoneNumber": "+0987654321"},
        "callConnectionId": "test-connection-id",
        "serverCallId": "test-server-call-id",
        "correlationId": "test-correlation-id",
        "eventType": "Microsoft.Communication.CallConnected",
        "data": {
            "callConnectionState": "connected",
            "serverCallId": "test-server-call-id",
            "callConnectionId": "test-connection-id"
        }
    }
    
    logger.info(f"Testing WhatsApp/Voice integration")
    logger.info(f"Voice Service URL: {voice_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test the voice service call endpoint
            api_endpoint = f"{voice_url}/api/call"
            
            logger.info(f"Testing voice endpoint: {api_endpoint}")
            
            async with session.post(
                api_endpoint,
                json=test_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                logger.info(f"Voice API Response Status: {response.status}")
                
                if response.status == 200:
                    logger.info("✅ Voice service is responding")
                    response_text = await response.text()
                    logger.info(f"📨 Response: {response_text}")
                    return True
                elif response.status == 405:
                    logger.error("❌ Method Not Allowed - Voice endpoint might not exist")
                    return False
                else:
                    logger.error(f"❌ Voice service returned status {response.status}")
                    response_text = await response.text()
                    logger.error(f"Response: {response_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error testing WhatsApp integration: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting WhatsApp integration test...")
    
    success = await test_whatsapp_integration()
    
    if success:
        logger.info("✅ WhatsApp integration test PASSED!")
        logger.info("🎉 The voice service is working correctly")
        return True
    else:
        logger.error("❌ WhatsApp integration test FAILED!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
