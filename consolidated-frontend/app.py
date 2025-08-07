"""
Consolidated Frontend Service - Voice + UI
Unified interface for voice calls and web chat
"""
from contextlib import asynccontextmanager
import os
import uuid
from urllib.parse import urlencode
from typing import Dict, Optional

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import chainlit as cl
import aiohttp
import logging
import asyncio

from azure.identity import DefaultAzureCredential
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.core.messaging import CloudEvent
from azure.communication.callautomation import (
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource,
    SsmlSource
)
from azure.communication.callautomation.aio import CallAutomationClient
from dotenv import load_dotenv

load_dotenv(override=True)

import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Global session management
import aiohttp
api_sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global api_sessions
    
    # Startup: Create session for backend service (ready for future scaling)
    api_sessions = {
        "backend_primary": aiohttp.ClientSession(),
        # Future: "backend_secondary": aiohttp.ClientSession()
    }
    
    yield
    
    # Cleanup: Close all sessions
    for session in api_sessions.values():
        await session.close()

app = FastAPI(
    title="Consolidated Frontend Service",
    description="Voice and Web Chat Interface",
    lifespan=lifespan
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logging.error(f"Unprocessable request: {request} {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# Load balancer for backend services (ready for future scaling)
class BackendLoadBalancer:
    def __init__(self):
        self.primary_url = os.getenv("BACKEND_PRIMARY_URL", "http://backend-service")
        self.secondary_url = os.getenv("BACKEND_SECONDARY_URL", "http://backend-service")  # Same as primary for now
        self.load_balancing_mode = os.getenv("LOAD_BALANCING_MODE", "single")  # single, primary-secondary, round-robin
        self.current_primary = True
        self.health_check_failures = 0
        self.max_failures = 3
    
    async def get_healthy_backend(self) -> tuple[aiohttp.ClientSession, str]:
        """Get a healthy backend service session - simplified for single backend"""
        primary_session = api_sessions["backend_primary"]
        
        if self.load_balancing_mode == "single":
            # Single backend mode - just return the primary session
            return primary_session, self.primary_url
        
        # Future load balancing logic would go here
        if self.current_primary:
            try:
                # Quick health check
                async with primary_session.get(f"{self.primary_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        self.health_check_failures = 0
                        return primary_session, self.primary_url
            except Exception as e:
                logging.warning(f"Primary backend unhealthy: {e}")
                self.health_check_failures += 1
                
                if self.health_check_failures >= self.max_failures and self.load_balancing_mode != "single":
                    logging.info("Switching to secondary backend")
                    self.current_primary = False
                    return api_sessions.get("backend_secondary", primary_session), self.secondary_url
        
        # Default to primary
        return primary_session, self.primary_url
    
    async def ask_backend(self, input_message: str, conversation_id: str, tenant_id: Optional[str] = None):
        """Send message to backend - simplified for single backend"""
        session, backend_url = await self.get_healthy_backend()
        
        payload = {
            "message": input_message,
            "tenant_id": tenant_id
        }
        
        try:
            async with session.post(
                f"{backend_url}/conversation/{conversation_id}",
                json=payload
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logging.error(f"Backend request failed: {e}")
            
            # For single backend mode, just retry once
            if self.load_balancing_mode == "single":
                await asyncio.sleep(1)  # Brief pause before retry
                async with session.post(
                    f"{backend_url}/conversation/{conversation_id}",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                # Future: Try the other backend if in load balancing mode
                raise e

load_balancer = BackendLoadBalancer()

# Initialize Azure Communication Services for voice calls
call_automation_client = CallAutomationClient(
    endpoint=os.getenv("ACS_ENDPOINT"), 
    credential=DefaultAzureCredential()
)
COGNITIVE_SERVICE_ENDPOINT = os.getenv("COGNITIVE_SERVICE_ENDPOINT")
VOICE_NAME = os.getenv("VOICE_NAME", "en-US-AvaMultilingualNeural")

# Voice call constants (from original voice/app.py)
HELLO_PROMPT = "Hello, how may I help you today?"
CHAT_CONTEXT = "ChatContext"
TIMEOUT_SILENCE_PROMPT = "I am sorry, I did not hear anything. If you need assistance, please let me know how I can help you,"
AGENTS_ERROR = "I am sorry, I am unable to assist you at this time. Please try again later."
GOODBYE_PROMPT = "Thank you for calling! I hope I was able to assist you. Have a great day!"
GOODBYE_CONTEXT = "Goodbye"

max_retry_dict = {}

# ===== VOICE HANDLING SECTION =====

# ===== VOICE HANDLING SECTION =====

@app.post("/api/call")
async def incoming_call_handler(req: Request):
    """Handle incoming voice calls - complete implementation from original voice/app.py"""
    try:
        for event_dict in await req.json():
            event = EventGridEvent.from_dict(event_dict)
            logger.info("Incoming event data: %s", event.data)
            
            # Handle the initial validation event from EventGrid
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                logger.info("Validating WebHook subscription")
                validation_url = event.data['validationUrl']
                validation_code = event.data['validationCode']
                async with aiohttp.ClientSession() as client:
                    await client.get(validation_url)
                
                return JSONResponse(content={"validationResponse": validation_code}, status_code=200)
            
            # Handle the incoming call event
            elif event.event_type == "Microsoft.Communication.IncomingCall":
                logger.info("Incoming call received: data=%s", event.data)  
                if event.data['from']['kind'] == "phoneNumber":
                    caller_id = event.data['from']["phoneNumber"]["value"]
                else:
                    caller_id = event.data['from']['rawId'] 
                logger.info("incoming call handler caller id: %s", caller_id)
                
                call_id = uuid.uuid4()
                
                query_parameters = urlencode({"callerId": caller_id})
                # Quick way to get the callback url from current request full URL
                original_uri = str(req.url)
                callback_uri = original_uri.replace("/api/call", f"/api/call/{call_id}?{query_parameters}").replace("http://", "https://")     
                logger.info("callback url: %s", callback_uri)
                
                incoming_call_context = event.data['incomingCallContext']
                answer_call_result = await call_automation_client.answer_call(
                    incoming_call_context=incoming_call_context,
                    cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                    callback_url=callback_uri)
                
                logger.info("Answered call for connection id: %s", answer_call_result.call_connection_id)
                return JSONResponse(status_code=200, content="")
            else:
                logger.warning("Event type not supported: %s", event.event_type)
            
        return JSONResponse(status_code=200, content="")
    except Exception as ex:
        logger.error(f"Error in incoming_call_handler: {ex}")
        return JSONResponse(status_code=500, content=str(ex))

@app.post("/api/call/{contextId}")
async def handle_callback(req: Request):
    """Handle voice call callbacks - complete implementation from original voice/app.py"""
    try:        
        events = await req.json()
        contextId = req.path_params.get("contextId")
        
        logger.info("Request Json: %s", events)
        for event_dict in events:       
            event = CloudEvent.from_dict(event_dict)
            
            call_connection_id = event.data['callConnectionId']
            logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
            caller_id = req.query_params.get("callerId").strip()
            if "+" not in caller_id:
                caller_id = "+" + caller_id.strip()

            logger.info("Call connected: data=%s", event.data)
            if event.type == "Microsoft.Communication.CallConnected":
                max_retry_dict[call_connection_id] = 3
                await reply_and_wait(HELLO_PROMPT, caller_id, call_connection_id, context=CHAT_CONTEXT)
                 
            elif event.type == "Microsoft.Communication.RecognizeCompleted":
                if event.data['recognitionType'] == "speech": 
                    speech_text = event.data['speechResult']['speech']
                    logger.info("Recognition completed, speech_text: %s", speech_text)
                    if speech_text is not None and len(speech_text) > 0:                      
                        
                        # Call backend through load balancer
                        answers = await load_balancer.ask_backend(speech_text, caller_id)
                        # Process response like original
                        final_answer = "\n".join([answer['content'] for answer in answers if answer['role'] == "assistant"])
                        logger.info("Agent response: %s", final_answer)
                        
                        if final_answer.strip() == "":
                            await reply_and_wait(AGENTS_ERROR, caller_id, call_connection_id, context=CHAT_CONTEXT)
                        else:
                            await reply_and_wait(final_answer, caller_id, call_connection_id, context=CHAT_CONTEXT)
                                                 
            elif event.type == "Microsoft.Communication.RecognizeFailed":
                resultInformation = event.data['resultInformation']
                reasonCode = resultInformation['subCode']
                context = event.data['operationContext']
                                
                if reasonCode == 8510 and 0 < max_retry_dict[call_connection_id]:
                    await reply_and_wait(TIMEOUT_SILENCE_PROMPT, caller_id, call_connection_id, context=CHAT_CONTEXT) 
                    max_retry_dict[call_connection_id] -= 1
                else:
                    max_retry_dict.pop(call_connection_id)
                    await play_message(call_connection_id, GOODBYE_PROMPT, GOODBYE_CONTEXT)
                 
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context = event.data['operationContext']    
                if context.lower() == GOODBYE_CONTEXT.lower():
                    await terminate_call(call_connection_id)
                        
        return JSONResponse(status_code=200, content="") 
    except Exception as ex:
        logger.error(f"Error in handle_callback: {ex}")
        return JSONResponse(status_code=500, content=str(ex))

async def reply_and_wait(replyText, callerId, call_connection_id, context=""):
    """Reply and wait for user speech - from original voice/app.py"""
    try:
        logger.debug("Replying and waiting: %s", replyText)        
        connection_client = call_automation_client.get_call_connection(call_connection_id)
        ssmlToPlay = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><voice name="{VOICE_NAME}">{replyText}</voice></speak>'
        await connection_client.start_recognizing_media( 
            input_type=RecognizeInputType.SPEECH,
            target_participant=PhoneNumberIdentifier(callerId), 
            end_silence_timeout=1,
            play_prompt=SsmlSource(ssml_text=ssmlToPlay) if replyText != "" else None,
            operation_context=context)
    except Exception as ex:
        logger.error("Error in recognize: %s", ex)

async def play_message(call_connection_id, text_to_play, context):
    """Play message to caller - from original voice/app.py"""
    logger.debug("Playing message: %s", text_to_play)
    play_source = TextSource(text=text_to_play, voice_name=VOICE_NAME) 
    await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
        play_source,
        operation_context=context)

async def terminate_call(call_connection_id):     
    """Terminate call - from original voice/app.py"""
    await call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)

@app.post("/webhook/voice")
async def voice_webhook(request: Request):
    """Legacy webhook endpoint - redirects to /api/call for compatibility"""
    return await incoming_call_handler(request)

async def process_voice_call(call_data: Dict, tenant_id: Optional[str]):
    """Process voice call with tenant-specific logic"""
    event_type = call_data.get('type', '')
    conversation_id = call_data.get('correlationId', str(uuid.uuid4()))
    
    if event_type == 'Microsoft.Communication.IncomingCall':
        # Handle incoming call
        return await handle_incoming_call(call_data, conversation_id, tenant_id)
    elif event_type == 'Microsoft.Communication.RecognizeCompleted':
        # Handle speech recognition
        return await handle_speech_recognition(call_data, conversation_id, tenant_id)
    else:
        logging.info(f"Unhandled voice event: {event_type}")
        return JSONResponse(content={"status": "ignored"})

async def handle_incoming_call(call_data: Dict, conversation_id: str, tenant_id: Optional[str]):
    """Handle incoming voice call"""
    logging.info(f"Handling incoming call for tenant: {tenant_id}")
    
    # Generate tenant-specific greeting
    greeting = get_tenant_greeting(tenant_id)
    
    response_data = {
        "actions": [
            {
                "action": "playAudio",
                "playAudioOptions": {
                    "audioFileUri": f"data:text/plain;base64,{greeting}"
                }
            },
            {
                "action": "recognize",
                "recognizeOptions": {
                    "inputType": "speech",
                    "stopOnDtmfTones": ["#"],
                    "maxSilenceTimeoutInSeconds": 5
                }
            }
        ]
    }
    
    return JSONResponse(content=response_data)

async def handle_speech_recognition(call_data: Dict, conversation_id: str, tenant_id: Optional[str]):
    """Handle speech recognition results"""
    speech_text = call_data.get('speechText', '')
    logging.info(f"Speech recognized: {speech_text}")
    
    if speech_text:
        # Send to backend with tenant context
        response = await load_balancer.ask_backend(speech_text, conversation_id, tenant_id)
        agent_response = response.get('response', 'I did not understand that.')
        
        return JSONResponse(content={
            "actions": [
                {
                    "action": "playAudio",
                    "playAudioOptions": {
                        "text": agent_response
                    }
                },
                {
                    "action": "recognize",
                    "recognizeOptions": {
                        "inputType": "speech",
                        "stopOnDtmfTones": ["#"],
                        "maxSilenceTimeoutInSeconds": 5
                    }
                }
            ]
        })
    
    return JSONResponse(content={"status": "no_speech"})

def get_tenant_greeting(tenant_id: Optional[str]) -> str:
    """Get tenant-specific greeting"""
    greetings = {
        "wedding": "Hello! Welcome to our Wedding Planning Service. How can I help you today?",
        "telco": "Thank you for calling our Technical Support. How may I assist you?",
        "default": "Hello! How can I help you today?"
    }
    return greetings.get(tenant_id, greetings["default"])

async def determine_tenant_from_phone(phone_number: str) -> Optional[str]:
    """Determine tenant from phone number"""
    # This could call the backend service to get tenant mapping
    try:
        session, backend_url = await load_balancer.get_healthy_backend()
        async with session.get(f"{backend_url}/tenants") as response:
            if response.status == 200:
                tenants_data = await response.json()
                for tenant in tenants_data.get("tenants", []):
                    if phone_number in tenant.get("phone_numbers", []):
                        return tenant["id"]
    except Exception as e:
        logging.warning(f"Could not determine tenant: {e}")
    
    return None

# ===== WEB CHAT SECTION =====

# Chainlit integration for web chat
from chainlit.element import ElementBased
import chainlit as cl

class ConsolidatedChatInterface:
    def __init__(self):
        self.backend_lb = load_balancer
    
    @cl.on_chat_start
    async def start(self):
        """Initialize chat session"""
        cl.user_session.set("conversation_id", str(uuid.uuid4()))
        cl.user_session.set("tenant_id", "default")  # Could be determined by subdomain
        
        await cl.Message(
            content="Hello! Welcome to our multi-service chat. How can I help you today?"
        ).send()
    
    @cl.on_message
    async def main(self, message: cl.Message):
        """Handle chat messages"""
        conversation_id = cl.user_session.get("conversation_id")
        tenant_id = cl.user_session.get("tenant_id")
        
        try:
            # Send to backend via load balancer
            response = await self.backend_lb.ask_backend(
                message.content, 
                conversation_id, 
                tenant_id
            )
            
            agent_response = response.get('response', 'I could not process your request.')
            
            await cl.Message(content=agent_response).send()
            
        except Exception as e:
            logging.error(f"Chat error: {e}")
            await cl.Message(content="I'm having trouble right now. Please try again.").send()

# Initialize chat interface
chat_interface = ConsolidatedChatInterface()

# ===== STATIC FILE SERVING =====

# Serve static files for UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_chat_ui():
    """Serve the main chat interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Service Chat</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .service-selector { margin-bottom: 20px; }
            button { padding: 10px 20px; margin: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Multi-Service Interface</h1>
            <div class="service-selector">
                <h3>Select Service:</h3>
                <button onclick="selectTenant('wedding')">Wedding Planning</button>
                <button onclick="selectTenant('telco')">Technical Support</button>
            </div>
            <div id="chat-container">
                <!-- Chainlit chat will be embedded here -->
                <iframe src="/chat" width="100%" height="600px"></iframe>
            </div>
        </div>
        <script>
            function selectTenant(tenantId) {
                // Update the chat interface with tenant selection
                document.getElementById('chat-container').innerHTML = 
                    `<iframe src="/chat?tenant=${tenantId}" width="100%" height="600px"></iframe>`;
            }
        </script>
    </body>
    </html>
    """

@app.get("/chat")
async def chat_interface(tenant: str = "default"):
    """Serve tenant-specific chat interface"""
    # This would integrate with Chainlit
    return HTMLResponse(content=f"<h1>Chat Interface for {tenant}</h1>")

# ===== HEALTH AND MONITORING =====

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check backend connectivity
    try:
        session, backend_url = await load_balancer.get_healthy_backend()
        async with session.get(f"{backend_url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
            backend_healthy = response.status == 200
    except:
        backend_healthy = False
    
    return {
        "status": "healthy" if backend_healthy else "degraded",
        "service": "consolidated-frontend",
        "backend_connectivity": backend_healthy,
        "load_balancing_mode": load_balancer.load_balancing_mode,
        "backend_url": load_balancer.primary_url
    }

@app.get("/metrics")
async def get_metrics():
    """Simple metrics endpoint"""
    return {
        "backend_failures": load_balancer.health_check_failures,
        "load_balancing_mode": load_balancer.load_balancing_mode,
        "active_sessions": len([s for s in api_sessions.values() if not s.closed]),
        "backend_url": load_balancer.primary_url
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
