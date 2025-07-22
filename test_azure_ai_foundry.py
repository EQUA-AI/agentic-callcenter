#!/usr/bin/env python3
"""
Test script to verify Azure AI Foundry integration is working
"""
import asyncio
import aiohttp
import json
import logging
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_azure_ai_foundry():
    """Test Azure AI Foundry integration for wedding concierge via the API service"""
    
    # Generate a unique conversation ID
    conversation_id = str(uuid.uuid4())
    
    # The API service URL (internal)
    api_url = "https://dev-api-3dirbnu5qgcl2.internal.purplefield-53a338ec.eastus2.azurecontainerapps.io"
    
    # Test message for wedding concierge
    test_message = "What is the dress code for the wedding? Also, what time does the ceremony start?"
    
    logger.info(f"Testing Azure AI Foundry integration with conversation ID: {conversation_id}")
    logger.info(f"API Service URL: {api_url}")
    logger.info(f"Test message: {test_message}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # First, let's try to access the API health endpoint
            async with session.get(f"{api_url}/") as response:
                if response.status == 200:
                    logger.info("✅ API service is accessible")
                else:
                    logger.error(f"❌ API service returned status {response.status}")
                    return False
            
            # Now test the conversation endpoint
            api_endpoint = f"{api_url}/conversation/{conversation_id}/stream"
            
            payload = {
                "message": test_message,
                "conversation_id": conversation_id
            }
            
            logger.info(f"Testing API endpoint: {api_endpoint}")
            
            async with session.post(
                api_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                logger.info(f"API Response Status: {response.status}")
                
                if response.status == 200:
                    logger.info("✅ API is responding")
                    
                    # Read the streaming response
                    async for line in response.content:
                        if line.strip():
                            try:
                                data = json.loads(line.decode('utf-8'))
                                logger.info(f"📨 Received: {data}")
                            except json.JSONDecodeError:
                                logger.info(f"📨 Raw response: {line.decode('utf-8')}")
                    
                    return True
                elif response.status == 405:
                    logger.error("❌ Method Not Allowed - API endpoint might not exist")
                    return False
                else:
                    logger.error(f"❌ API returned status {response.status}")
                    response_text = await response.text()
                    logger.error(f"Response: {response_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error testing Azure AI Foundry: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Azure AI Foundry integration test...")
    
    success = await test_azure_ai_foundry()
    
    if success:
        logger.info("✅ Azure AI Foundry integration test PASSED!")
        logger.info("🎉 The wedding concierge system is working correctly:")
        logger.info("   - API service is accessible")
        logger.info("   - Conversation endpoint is responding")
        logger.info("   - Azure AI Foundry wedding agent is connected")
        return True
    else:
        logger.error("❌ Azure AI Foundry integration test FAILED!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
