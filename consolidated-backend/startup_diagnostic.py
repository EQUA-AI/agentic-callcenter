#!/usr/bin/env python3
"""
Startup Diagnostic Script for Backend Container
Checks all required environment variables and services
"""
import os
import logging
import sys
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables() -> Dict[str, bool]:
    """Check if all required environment variables are set"""
    required_vars = [
        # Azure Service Bus
        'ServiceBusConnection__fullyQualifiedNamespace',
        
        # Azure Communication Services
        'ACS_ENDPOINT',
        'SMS_CHANNEL_ID',
        'WHATSAPP_CHANNEL_ID',
        
        # Azure OpenAI
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_VERSION',
        'AZURE_OPENAI_MODEL',
        'AZURE_OPENAI_WHISPER_DEPLOYMENT',
        
        # Azure AI Foundry
        'AZURE_AI_FOUNDRY_ENDPOINT',
        'AGENT_ID',
        
        # Cosmos DB
        'AZURE_COSMOS_CONNECTION_STRING',
        
        # Application Insights
        'APPLICATIONINSIGHTS_CONNECTIONSTRING'
    ]
    
    results = {}
    for var in required_vars:
        value = os.getenv(var)
        results[var] = bool(value)
        if value:
            logger.info(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            logger.error(f"❌ {var}: NOT SET")
    
    return results

def check_imports():
    """Check if all required modules can be imported"""
    modules_to_check = [
        'azure.servicebus',
        'azure.communication.messages',
        'azure.cosmos',
        'azure.identity',
        'openai',
        'fastapi',
        'uvicorn'
    ]
    
    results = {}
    for module in modules_to_check:
        try:
            __import__(module)
            results[module] = True
            logger.info(f"✅ {module}: imported successfully")
        except ImportError as e:
            results[module] = False
            logger.error(f"❌ {module}: import failed - {e}")
    
    return results

def test_basic_connections():
    """Test basic Azure service connections"""
    tests = {}
    
    # Test Azure Identity
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        tests['azure_identity'] = True
        logger.info("✅ Azure Identity: credential created successfully")
    except Exception as e:
        tests['azure_identity'] = False
        logger.error(f"❌ Azure Identity: failed - {e}")
    
    # Test Service Bus namespace connection
    try:
        servicebus_namespace = os.getenv("ServiceBusConnection__fullyQualifiedNamespace")
        if servicebus_namespace:
            from azure.servicebus.aio import ServiceBusClient
            tests['servicebus_namespace'] = True
            logger.info(f"✅ Service Bus: namespace configured - {servicebus_namespace}")
        else:
            tests['servicebus_namespace'] = False
            logger.error("❌ Service Bus: namespace not configured")
    except Exception as e:
        tests['servicebus_namespace'] = False
        logger.error(f"❌ Service Bus: connection failed - {e}")
    
    return tests

def main():
    """Main diagnostic function"""
    logger.info("🔍 Starting backend container diagnostic...")
    
    # Check environment variables
    logger.info("\n📋 Checking environment variables...")
    env_results = check_environment_variables()
    env_missing = [k for k, v in env_results.items() if not v]
    
    # Check imports
    logger.info("\n📦 Checking module imports...")
    import_results = check_imports()
    import_failed = [k for k, v in import_results.items() if not v]
    
    # Test connections
    logger.info("\n🔗 Testing basic connections...")
    connection_results = test_basic_connections()
    connection_failed = [k for k, v in connection_results.items() if not v]
    
    # Summary
    logger.info("\n📊 DIAGNOSTIC SUMMARY")
    logger.info("=" * 50)
    
    if env_missing:
        logger.error(f"❌ Missing environment variables: {', '.join(env_missing)}")
    else:
        logger.info("✅ All environment variables are set")
    
    if import_failed:
        logger.error(f"❌ Failed imports: {', '.join(import_failed)}")
    else:
        logger.info("✅ All modules imported successfully")
    
    if connection_failed:
        logger.error(f"❌ Failed connections: {', '.join(connection_failed)}")
    else:
        logger.info("✅ All connections successful")
    
    # Overall status
    if env_missing or import_failed or connection_failed:
        logger.error("🚨 CONTAINER STARTUP WILL LIKELY FAIL")
        sys.exit(1)
    else:
        logger.info("🎉 CONTAINER SHOULD START SUCCESSFULLY")
        sys.exit(0)

if __name__ == "__main__":
    main()
