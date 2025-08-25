"""
Test Azure AI Foundry Connection
Simple test to verify the Azure AI Foundry client can connect and communicate
"""
import asyncio
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_foundry_connection():
    """Test Azure AI Foundry connection with a simple message"""
    try:
        from azure_foundry_client import ask_foundry_agent
        
        # Test configuration
        test_agent_id = "asst_khFWOGAwaF7BJ73ecupCfXze"  # Wedding agent
        test_endpoint = "https://weddingomni.services.ai.azure.com/api/projects/WeddingOmni"
        test_message = "Hello, can you help me with wedding planning?"
        
        logger.info("Testing Azure AI Foundry connection...")
        logger.info(f"Endpoint: {test_endpoint}")
        logger.info(f"Agent ID: {test_agent_id}")
        logger.info(f"Test message: {test_message}")
        
        # Send test message
        response = await ask_foundry_agent(
            user_text=test_message,
            agent_id=test_agent_id,
            conversation_id="test_conversation",
            foundry_endpoint=test_endpoint,
            system_prompt="You are a helpful wedding planning assistant.",
            context={"test": True}
        )
        
        logger.info("✅ Azure AI Foundry connection successful!")
        logger.info(f"Response: {response}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Azure AI Foundry connection failed: {e}")
        logger.error("Please check your Azure authentication and endpoint configuration")
        return False

async def test_multiple_agents():
    """Test multiple agents to verify configuration"""
    try:
        from azure_foundry_client import ask_foundry_agent
        
        agents_to_test = [
            {
                "id": "asst_khFWOGAwaF7BJ73ecupCfXze",
                "name": "Wedding Planning",
                "message": "What are the most important things to consider when planning a wedding?"
            },
            {
                "id": "asst_QyONy5LPHKeETJgS1nftQT9x", 
                "name": "Hajj & Umrah",
                "message": "What are the basic requirements for performing Hajj?"
            },
            {
                "id": "asst_LgflhAlTTQMvnDLJp4wmOFQr",
                "name": "EPCON AI Technical",
                "message": "I need help with equipment diagnostics. Can you assist?"
            }
        ]
        
        endpoint = "https://weddingomni.services.ai.azure.com/api/projects/WeddingOmni"
        
        for agent in agents_to_test:
            logger.info(f"\n🧪 Testing {agent['name']} agent...")
            try:
                response = await ask_foundry_agent(
                    user_text=agent['message'],
                    agent_id=agent['id'],
                    conversation_id=f"test_{agent['name'].lower().replace(' ', '_')}",
                    foundry_endpoint=endpoint
                )
                logger.info(f"✅ {agent['name']} agent responded successfully")
                logger.info(f"Response preview: {response[:150]}...")
            except Exception as e:
                logger.error(f"❌ {agent['name']} agent failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Multi-agent test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 Starting Azure AI Foundry integration tests...")
    
    # Test basic connection
    basic_test = await test_foundry_connection()
    
    if basic_test:
        # Test multiple agents
        logger.info("\n🔄 Testing multiple agents...")
        await test_multiple_agents()
    
    logger.info("\n📊 Test Summary:")
    logger.info(f"Basic Connection: {'✅ PASS' if basic_test else '❌ FAIL'}")
    
    if basic_test:
        logger.info("\n🎉 Azure AI Foundry integration is ready!")
        logger.info("You can now run the Chainlit application with: chainlit run chainlit_app.py")
    else:
        logger.info("\n⚠️  Please check your Azure authentication:")
        logger.info("1. Run 'az login' if using Azure CLI")
        logger.info("2. Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID environment variables")
        logger.info("3. Verify your Azure AI Foundry endpoint is correct")

if __name__ == "__main__":
    asyncio.run(main())
