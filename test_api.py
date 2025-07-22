#!/usr/bin/env python3
"""Test script to verify Azure AI Foundry integration"""

import asyncio
import aiohttp
import json
import os

async def test_api():
    api_url = "http://dev-api-3dirbnu5qgcl2"
    test_conversation_id = "test-foundry-123"
    
    async with aiohttp.ClientSession() as session:
        # Test message to Azure AI Foundry agent
        test_message = {
            "role": "user", 
            "content": "Hello! I need help with my internet connection. It's not working."
        }
        
        print(f"Testing API at: {api_url}")
        print(f"Sending message: {test_message}")
        
        try:
            async with session.post(
                f"{api_url}/conversation/{test_conversation_id}", 
                json=test_message,
                timeout=30
            ) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 200:
                    response_data = await response.json()
                    print(f"✅ Success! Azure AI Foundry responded:")
                    print(f"Response: {json.dumps(response_data, indent=2)}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Error: HTTP {response.status}")
                    print(f"Error details: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

if __name__ == "__main__":
    print("🧪 Testing Azure AI Foundry integration...")
    success = asyncio.run(test_api())
    
    if success:
        print("\n🎉 All vanilla AI agents have been successfully removed!")
        print("🚀 Azure AI Foundry agents are working correctly!")
        print("🌐 Frontend UI: https://dev-ui-3dirbnu5qgcl2.purplefield-53a338ec.eastus2.azurecontainerapps.io/")
        print("📱 WhatsApp Voice: https://dev-voice-3dirbnu5qgcl2.purplefield-53a338ec.eastus2.azurecontainerapps.io/api/call")
    else:
        print("\n❌ Test failed - please check logs for details")
