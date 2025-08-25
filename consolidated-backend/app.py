"""
Consolidated Backend Service - API + Functions
Dynamic multi-agent architecture supporting multiple phone numbers and agents from CosmosDB configuration
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from starlette_gzip_request import GZipRequestMiddleware
import azure.functions as func
import logging
import os
import json
import aiohttp
import uvicorn
from typing import Dict, Optional
from dotenv import load_dotenv

# Azure Communication Services imports
from azure.communication.messages import NotificationMessagesClient
from azure.communication.messages.models import TextNotificationContent
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from azure.identity import get_bearer_token_provider

# Import multi-agent router for dynamic configuration
from multi_agent_router import get_multi_agent_router

# Import Service Bus background processor
from servicebus_processor import ServiceBusBackgroundProcessor

# Import routers and services
from routers.conversation import conversation_router
from routers.integration import integration_router
from routers.config_ui import config_ui_router

# Messaging Connect service
from messaging_connect import get_messaging_connect_service

# Load environment variables
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize multi-agent router
multi_agent_router = get_multi_agent_router()

# FastAPI application
app = FastAPI(title="Consolidated Backend Service")
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(GZipRequestMiddleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logging.error(f"Unprocessable request: {request} {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# Include routers
app.include_router(conversation_router)
app.include_router(integration_router) 
app.include_router(config_ui_router)

@app.post("/route/message")
async def route_message(request: Request):
    """
    Route an incoming message to the appropriate AI agent
    
    Expected payload:
    {
        "from": "+1234567890",
        "to": "+0987654321", 
        "message": "Hello, I need help with my wedding planning",
        "conversation_id": "optional_conversation_id"
    }
    """
    try:
        data = await request.json()
        
        from_phone = data.get('from')
        to_phone = data.get('to')
        message_content = data.get('message')
        conversation_id = data.get('conversation_id')
        
        if not all([from_phone, to_phone, message_content]):
            return {
                "success": False,
                "error": "Missing required fields: from, to, message",
                "service": "multi_agent_router"
            }
        
        # Process message through multi-agent router
        result = await multi_agent_router.process_message(
            from_phone=from_phone,
            to_phone=to_phone,
            message_content=message_content,
            conversation_id=conversation_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Message routing failed: {e}")
        return {"success": False, "error": str(e), "service": "multi_agent_router"}

@app.get("/route/stats")
async def routing_stats():
    """Get multi-agent routing statistics"""
    try:
        stats = multi_agent_router.get_routing_stats()
        validation = multi_agent_router.validate_routing_config()
        
        return {
            "routing_stats": stats,
            "validation": validation,
            "service": "multi_agent_router"
        }
    except Exception as e:
        logger.error(f"Failed to get routing stats: {e}")
        return {"error": str(e), "service": "multi_agent_router"}

@app.get("/route/agent/{phone_number}")
async def get_agent_for_phone(phone_number: str):
    """Get agent configuration for a specific phone number"""
    try:
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
            
        routing_info = multi_agent_router.get_agent_for_message(
            from_phone="+1000000000",  # Dummy from number
            to_phone=phone_number,
            message_content="test"
        )
        
        if not routing_info:
            return {
                "success": False,
                "error": f"No agent configured for phone number {phone_number}",
                "service": "multi_agent_router"
            }
        
        return {
            "success": True,
            "phone_number": phone_number,
            "routing_info": routing_info,
            "service": "multi_agent_router"
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent for phone {phone_number}: {e}")
        return {"success": False, "error": str(e), "service": "multi_agent_router"}

@app.post("/messaging-connect/test-sms")
async def test_infobip_sms(request: Request):
    """Test Infobip SMS via Messaging Connect"""
    try:
        body = await request.json()
        phone_number = body.get("phone_number")
        message = body.get("message", "Test SMS from Infobip via ACS Messaging Connect")
        channel_id = body.get("channel_id")  # Optional, will use SMS_CHANNEL_ID if not provided
        
        if not messaging_connect_service.is_enabled():
            return {
                "success": False,
                "error": "Messaging Connect not enabled",
                "service": "messaging_connect"
            }
        
        if not phone_number:
            return {
                "success": False,
                "error": "phone_number is required (E.164 format, e.g. +1234567890)",
                "service": "messaging_connect"
            }
        
        result = await messaging_connect_service.send_sms(phone_number, message, channel_id)
        return result
        
    except Exception as e:
        logger.error(f"Infobip SMS test failed: {e}")
        return {"error": str(e), "success": False, "service": "messaging_connect"}

@app.post("/messaging-connect/test-whatsapp")
async def test_infobip_whatsapp(request: Request):
    """Test Infobip WhatsApp via Messaging Connect"""
    try:
        body = await request.json()
        phone_number = body.get("phone_number")
        message = body.get("message", "Test WhatsApp from Infobip via ACS Messaging Connect")
        channel_id = body.get("channel_id")  # Optional, will use WHATSAPP_CHANNEL_ID if not provided
        
        if not messaging_connect_service.is_enabled():
            return {
                "success": False,
                "error": "Messaging Connect not enabled",
                "service": "messaging_connect"
            }
        
        if not phone_number:
            return {
                "success": False,
                "error": "phone_number is required (E.164 format, e.g. +1234567890)",
                "service": "messaging_connect"
            }
        
        result = await messaging_connect_service.send_whatsapp(phone_number, message, channel_id)
        return result
        
    except Exception as e:
        logger.error(f"Infobip WhatsApp test failed: {e}")
        return {"error": str(e), "success": False, "service": "messaging_connect"}

@app.get("/messaging-connect/status")
async def messaging_connect_status():
    """Get Messaging Connect configuration status"""
    try:
        status = messaging_connect_service.get_status()
        return {
            "service": "messaging_connect",
            "configuration": status,
            "endpoints": {
                "test_sms": "/messaging-connect/test-sms",
                "test_whatsapp": "/messaging-connect/test-whatsapp"
            }
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {"error": str(e), "success": False}

@app.post("/messaging-connect/test")
async def test_messaging_connect(request: Request):
    """Legacy test endpoint - use specific test-sms or test-whatsapp endpoints instead"""
    try:
        return {
            "message": "This is a legacy endpoint. Use /messaging-connect/test-sms or /messaging-connect/test-whatsapp instead",
            "endpoints": {
                "sms": "/messaging-connect/test-sms",
                "whatsapp": "/messaging-connect/test-whatsapp",
                "status": "/messaging-connect/status"
            }
        }
    except Exception as e:
        logger.error(f"Messaging Connect test failed: {e}")
        return {"error": str(e), "success": False, "service": "messaging_connect"}

@app.post("/messaging/test")
async def test_messaging(request: Request):
    """Test traditional ACS messaging (existing WhatsApp functionality)"""
    try:
        return {
            "message": "This endpoint tests traditional ACS WhatsApp messaging",
            "messaging_connect_enabled": messaging_connect_enabled,
            "current_messaging": "Traditional ACS WhatsApp",
            "note": "Use /messaging-connect/test for Messaging Connect testing"
        }
        
    except Exception as e:
        logger.error(f"Test messaging failed: {e}")
        return {"error": str(e), "success": False}

# Azure Communication Services client (multi-tenant)
acs_endpoint = os.getenv("ACS_ENDPOINT")
acs_channelRegistrationId = os.getenv("ACS_CHANNEL_REGISTRATION_ID")
messaging_client = NotificationMessagesClient(
    endpoint=acs_endpoint,
    credential=DefaultAzureCredential()
)

# Messaging Connect using REST API (separate from existing WhatsApp)
messaging_connect_service = get_messaging_connect_service()
messaging_connect_enabled = messaging_connect_service.is_enabled()
logger.info(f"Messaging Connect enabled: {messaging_connect_enabled}")

# Whisper client for transcription
api_key = os.getenv("AZURE_OPENAI_WHISPER_API_KEY")
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
) if api_key is None or api_key == "" else None

whisper_client = AzureOpenAI(
    api_key=api_key,
    api_version=os.getenv("AZURE_OPENAI_WHISPER_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_WHISPER_ENDPOINT"),
    azure_ad_token_provider=token_provider
)

# Initialize Service Bus background processor
servicebus_processor = ServiceBusBackgroundProcessor(
    multi_agent_router=multi_agent_router,
    messaging_client=messaging_client, 
    whisper_client=whisper_client,
    messaging_connect_service=messaging_connect_service
)

# FastAPI lifecycle events
@app.on_event("startup")
async def startup_event():
    """Start background services with improved error handling"""
    logger.info("🚀 Starting consolidated backend services...")
    
    try:
        # Check critical environment variables
        required_vars = [
            'ServiceBusConnection__fullyQualifiedNamespace',
            'ACS_ENDPOINT',
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_AI_FOUNDRY_ENDPOINT'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            logger.error("🚨 Service may not function properly!")
        else:
            logger.info("✅ All required environment variables are set")
        
        # Start Service Bus processor with error handling
        try:
            await servicebus_processor.start()
            logger.info("✅ Service Bus processor started successfully")
        except Exception as e:
            logger.error(f"⚠️ Service Bus processor failed to start: {e}")
            logger.info("📝 Service will continue without Service Bus processing")
        
        logger.info("✅ Backend services startup completed!")
        
    except Exception as e:
        logger.error(f"❌ Critical error during startup: {e}")
        # Don't exit - allow container to start for debugging
        logger.info("🔧 Container will continue for debugging purposes")

@app.on_event("shutdown") 
async def shutdown_event():
    """Stop background services"""
    logger.info("🛑 Shutting down consolidated backend services...")
    await servicebus_processor.stop()
    logger.info("✅ All services stopped successfully!")

async def send_response_to_channel(response_text: str, from_number: str, channel_info: Dict):
    """Send response back to the user through the appropriate channel"""
    try:
        channel_type = channel_info['channel_type']
        channel_id = channel_info['channel_id']
        
        if channel_type == 'whatsapp':
            # Send WhatsApp message
            text_options = TextNotificationContent(
                channel_registration_id=channel_id,
                to=[from_number],
                content=response_text,
            )
            
            message_responses = messaging_client.send(text_options)
            message_send_result = message_responses.receipts[0]
            
            if message_send_result is not None:
                logger.info(f"WhatsApp message sent successfully to {from_number} via channel {channel_info['channel_name']}")
            else:
                logger.error(f"Failed to send WhatsApp message to {from_number}")
                
        elif channel_type == 'sms':
            # Send SMS message using messaging connect
            try:
                result = await messaging_connect_service.send_sms(from_number, response_text, channel_id)
                if result['success']:
                    logger.info(f"SMS sent successfully to {from_number} via channel {channel_info['channel_name']}")
                else:
                    logger.error(f"Failed to send SMS to {from_number}: {result.get('error', 'Unknown error')}")
            except Exception as sms_error:
                logger.error(f"SMS send error: {sms_error}")
        else:
            logger.warning(f"Unsupported channel type: {channel_type}")
            
    except Exception as e:
        logger.error(f"Error sending response to {from_number}: {e}")

async def process_tenant_message(message_data: Dict, tenant_id: str, agent_config: Dict):
    """Process message for specific tenant"""
    # Create conversation ID with tenant prefix
    conversation_id = f"{tenant_id}_{message_data.get('conversationId', 'default')}"
    
    # Call the conversation API with tenant-specific configuration
    import aiohttp
    async with aiohttp.ClientSession() as session:
        # In consolidated app, we can call the API directly
        # Or use internal function calls
        await ask_tenant_agent(
            message_data.get('text', ''),
            conversation_id,
            agent_config
        )

async def ask_tenant_agent_internal(input_message: str, conversation_id: str, agent_config: Dict):
    """Internal function to ask tenant-specific agent using direct API call"""
    try:
        # Since we're in the same container, call the conversation router directly
        from routers.conversation import send_message, MessageRequest
        
        # Create the request object
        request = MessageRequest(message=input_message)
        
        # Call the router function directly with tenant context
        # Set the tenant context temporarily for this request
        os.environ['CURRENT_TENANT_ID'] = agent_config.get('agent_id', 'default')
        os.environ['CURRENT_AGENT_ID'] = agent_config.get('agent_id', 'default')
        
        # Call send_message function directly
        response = send_message(conversation_id, request)
        
        # Clean up temp environment variables
        if 'CURRENT_TENANT_ID' in os.environ:
            del os.environ['CURRENT_TENANT_ID']
        if 'CURRENT_AGENT_ID' in os.environ:
            del os.environ['CURRENT_AGENT_ID']
            
        return response
        
    except Exception as e:
        logger.error(f"Error calling tenant agent: {e}")
        return [{"role": "assistant", "content": "I'm sorry, I'm having trouble processing your request right now."}]

async def ask_tenant_agent(input_message: str, conversation_id: str, agent_config: Dict):
    """Ask tenant-specific agent - kept for compatibility"""
    return await ask_tenant_agent_internal(input_message, conversation_id, agent_config)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint with multi-agent routing status"""
    try:
        # Get routing statistics
        routing_stats = multi_agent_router.get_routing_stats()
        
        # Get messaging connect status if available
        messaging_status = {"enabled": True}
        try:
            if 'messaging_connect_service' in globals():
                messaging_status = messaging_connect_service.get_status()
            else:
                messaging_status = {
                    "enabled": bool(os.getenv("MESSAGING_CONNECT_ENABLED", "").lower() == "true"),
                    "sms_configured": bool(os.getenv("SMS_CHANNEL_ID")),
                    "whatsapp_configured": bool(os.getenv("WHATSAPP_CHANNEL_ID")),
                    "sms_channel_id": os.getenv("SMS_CHANNEL_ID", ""),
                    "whatsapp_channel_id": os.getenv("WHATSAPP_CHANNEL_ID", "")
                }
        except Exception as e:
            logger.warning(f"Could not get messaging status: {e}")
            messaging_status = {"enabled": False, "error": str(e)}
        
        return {
            "status": "healthy",
            "messaging_connect": messaging_status,
            "multi_agent_routing": routing_stats,
            "acs_endpoint": os.getenv("ACS_ENDPOINT", ""),
            "service": "consolidated-backend",
            "endpoints": {
                "config_dashboard": "/config/",
                "messaging_connect_sms": "/messaging-connect/test-sms",
                "messaging_connect_whatsapp": "/messaging-connect/test-whatsapp",
                "messaging_connect_status": "/messaging-connect/status",
                "multi_agent_route": "/route/message",
                "routing_stats": "/route/stats"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=500, content={
            "status": "unhealthy", 
            "error": str(e),
            "service": "consolidated-backend"
        })

# Debug endpoint for diagnosing issues
@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check environment configuration"""
    try:
        env_check = {
            "ServiceBusConnection__fullyQualifiedNamespace": bool(os.getenv("ServiceBusConnection__fullyQualifiedNamespace")),
            "ACS_ENDPOINT": bool(os.getenv("ACS_ENDPOINT")),
            "AZURE_OPENAI_ENDPOINT": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
            "AZURE_AI_FOUNDRY_ENDPOINT": bool(os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")),
            "AGENT_ID": bool(os.getenv("AGENT_ID")),
            "SMS_CHANNEL_ID": bool(os.getenv("SMS_CHANNEL_ID")),
            "WHATSAPP_CHANNEL_ID": bool(os.getenv("WHATSAPP_CHANNEL_ID")),
            "APPLICATIONINSIGHTS_CONNECTIONSTRING": bool(os.getenv("APPLICATIONINSIGHTS_CONNECTIONSTRING")),
            "AZURE_COSMOS_CONNECTION_STRING": bool(os.getenv("AZURE_COSMOS_CONNECTION_STRING"))
        }
        
        return {
            "service": "consolidated-backend",
            "environment_variables": env_check,
            "missing_vars": [k for k, v in env_check.items() if not v],
            "servicebus_processor_running": servicebus_processor.running if hasattr(servicebus_processor, 'running') else False
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": str(e),
            "service": "consolidated-backend"
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
