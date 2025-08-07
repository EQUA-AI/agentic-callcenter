"""
Consolidated Backend Service - API + Functions
Multi-tenant architecture supporting multiple phone numbers and agents
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
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Multi-tenant configuration
class TenantConfig:
    def __init__(self):
        self.agents = {}
        self.phone_numbers = {}
        self.load_tenant_configs()
    
    def load_tenant_configs(self):
        """Load tenant configurations from environment or database"""
        # Example tenant configuration
        self.agents = {
            "wedding": {
                "agent_id": os.getenv("AGENT_ID", "asst_khFWOGAwaF7BJ73ecupCfXze"),
                "foundry_endpoint": os.getenv("AZURE_AI_FOUNDRY_ENDPOINT"),
                "phone_numbers": ["+1234567890"]  # WhatsApp number
            },
            "telco": {
                "agent_id": "asst_telco_agent_id",
                "foundry_endpoint": os.getenv("AZURE_AI_FOUNDRY_ENDPOINT"),
                "phone_numbers": ["+1234567891"]  # Different number
            }
        }
        
        # Reverse mapping for phone number to tenant lookup
        for tenant_id, config in self.agents.items():
            for phone in config["phone_numbers"]:
                self.phone_numbers[phone] = tenant_id
    
    def get_tenant_by_phone(self, phone_number: str) -> Optional[str]:
        """Get tenant ID by phone number"""
        return self.phone_numbers.get(phone_number)
    
    def get_agent_config(self, tenant_id: str) -> Optional[Dict]:
        """Get agent configuration for tenant"""
        return self.agents.get(tenant_id)

# Initialize tenant configuration
tenant_config = TenantConfig()

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

# Import existing routers with multi-tenant support
from routers.conversation import conversation_router
from routers.integration import integration_router

app.include_router(conversation_router)
app.include_router(integration_router)

# Azure Functions integration
function_app = func.FunctionApp()

# Azure Communication Services client (multi-tenant)
from azure.communication.messages import NotificationMessagesClient
from azure.communication.messages.models import TextNotificationContent
from azure.identity import DefaultAzureCredential

acs_endpoint = os.getenv("ACS_ENDPOINT")
acs_channelRegistrationId = os.getenv("ACS_CHANNEL_REGISTRATION_ID")
messaging_client = NotificationMessagesClient(
    endpoint=acs_endpoint,
    credential=DefaultAzureCredential()
)

# Whisper client for transcription
from openai import AzureOpenAI
from azure.identity import get_bearer_token_provider

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

@function_app.service_bus_queue_trigger(
    arg_name="sbmessage", 
    queue_name="messages",
    connection="ServiceBusConnection"
)
async def process_whatsapp_message(sbmessage: func.ServiceBusMessage):
    """Process messages from Service Bus - Multi-tenant aware with full WhatsApp support"""
    try:
        sb_message_payload = json.loads(sbmessage.get_body().decode('utf-8'))
        logger.info(f'Processing a message: {sb_message_payload}')
        
        if sb_message_payload['eventType'] != "Microsoft.Communication.AdvancedMessageReceived":
            logger.info(f"Message is not of type 'Microsoft.Communication.AdvancedMessageReceived': {sb_message_payload['eventType']}")
            return
        
        data = sb_message_payload['data']
        channel_type = data['channelType']  # should be "whatsapp"
        content = data['content'] if 'content' in data else None
        from_number = data['from']
        media = data['media'] if 'media' in data else None
        
        # Handle media (audio/image processing like original)
        if media is not None:
            media_blob = messaging_client.download_media(media['id'])
            
            if "audio" in media['mimeType']:
                # Convert media_blob to bytes for whisper transcription
                binary_data = b"".join(media_blob)
                
                transcription = whisper_client.audio.transcriptions.create(
                    model="whisper",
                    file=binary_data
                )
                content = transcription.text
                
            elif "image" in media['mimeType']:
                # Convert media_blob to bytes
                binary_data = b"".join(media_blob)
                caption = media['caption'] if 'caption' in media else None
                # TODO: Handle image processing as in original
        
        # Skip processing if there's no text content
        if not content or content.strip() == "":
            logger.info(f"No text content to process, skipping message from {from_number}")
            return
        
        # Determine which tenant this message belongs to (for multi-tenant support)
        tenant_id = tenant_config.get_tenant_by_phone(data.get('to', ''))
        if not tenant_id:
            logger.warning(f"No tenant found for phone number: {data.get('to', '')}")
            tenant_id = "default"  # fallback to default tenant
        
        agent_config = tenant_config.get_agent_config(tenant_id)
        if not agent_config:
            logger.error(f"No agent config found for tenant: {tenant_id}")
            return
        
        logger.info(f"Routing message to tenant: {tenant_id}, agent: {agent_config['agent_id']}")
        
        # Process message with tenant-specific agent (call internal API)
        conversation_id = from_number  # Use phone number as conversation ID
        new_messages = await ask_tenant_agent_internal(content, conversation_id, agent_config)
        
        logger.info(f"New messages: {new_messages}")
        
        # Send responses to the user (exactly like original)
        for message in new_messages:
            if ('name' in message and message['name'] == "Customer") or message['role'] == "user":
                continue
                
            logger.info(f"Sending response: {message}")
            text_options = TextNotificationContent(
                channel_registration_id=acs_channelRegistrationId,
                to=[from_number],
                content=message['content'],
            )
            
            # calling send() with whatsapp message details
            message_responses = messaging_client.send(text_options)
            message_send_result = message_responses.receipts[0]
            
            if (message_send_result is not None):
                logger.info(f"WhatsApp Text Message with message id {message_send_result.message_id} was successfully sent to {message_send_result.to}.")
            else:
                logger.error(f"Message failed to send: {message_send_result}")
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {str(e)}")

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
    return {
        "status": "healthy",
        "service": "consolidated-backend",
        "tenants": list(tenant_config.agents.keys())
    }

# Tenant management endpoints
@app.get("/tenants")
async def list_tenants():
    """List all configured tenants"""
    return {
        "tenants": [
            {
                "id": tenant_id,
                "phone_numbers": config["phone_numbers"],
                "agent_id": config["agent_id"]
            }
            for tenant_id, config in tenant_config.agents.items()
        ]
    }

@app.post("/tenants/{tenant_id}/phone-numbers")
async def add_phone_number(tenant_id: str, phone_number: str):
    """Add phone number to tenant"""
    if tenant_id not in tenant_config.agents:
        return JSONResponse(status_code=404, content={"error": "Tenant not found"})
    
    tenant_config.agents[tenant_id]["phone_numbers"].append(phone_number)
    tenant_config.phone_numbers[phone_number] = tenant_id
    
    return {"message": f"Phone number {phone_number} added to tenant {tenant_id}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
