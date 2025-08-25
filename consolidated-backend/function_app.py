import azure.functions as func
import logging
import os
import json

from dotenv import load_dotenv
load_dotenv(override=True)

app = func.FunctionApp()
base_url = os.getenv("API_BASE_URL")
acs_endpoint = os.getenv("ACS_ENDPOINT")
acs_channelRegistrationId = os.getenv("ACS_CHANNEL_REGISTRATION_ID")

import logging
logger = logging.getLogger(__name__)

from azure.communication.messages import NotificationMessagesClient
from azure.communication.messages.models import TextNotificationContent
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Create NotificationMessagesClient Client
messaging_client = NotificationMessagesClient(endpoint=acs_endpoint,
                                            credential=DefaultAzureCredential())

from openai import AzureOpenAI

api_key = os.getenv("AZURE_OPENAI_WHISPER_API_KEY")

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
) if api_key is None or api_key == "" else None

whisper_client = AzureOpenAI(
    api_key=api_key,  
    api_version=os.getenv("AZURE_OPENAI_WHISPER_VERSION"),
    azure_endpoint = os.getenv("AZURE_OPENAI_WHISPER_ENDPOINT"),
    azure_ad_token_provider=token_provider
)


import aiohttp
# Create a session for the functions to use once, instead of creating a new session for each request
API_BASE_URL = os.getenv("API_BASE_URL")
api_client_session = aiohttp.ClientSession()

async def ask(input_message, conversation_id):
    async with api_client_session.post(f"{API_BASE_URL}/conversation/{conversation_id}", json={"message": input_message}) as response:
        response.raise_for_status()
        new_messages = await response.json()
        return new_messages

@app.service_bus_queue_trigger(arg_name="sbmessage", queue_name="messages", connection="ServiceBusConnection") 
async def process_whatsapp_message(sbmessage: func.ServiceBusMessage):
    sb_message_payload = json.loads(sbmessage.get_body().decode('utf-8'))
    logger.info(f'Processing a message: {sb_message_payload}')
    
    if sb_message_payload['eventType'] != "Microsoft.Communication.AdvancedMessageReceived":
        logger.info(f"Message is not of type 'Microsoft.Communication.AdvancedMessageReceived': {sb_message_payload['eventType']}")
        return
    
    data = sb_message_payload['data']
    channel_type = data['channelType'] # should be "whatsapp"
    content = data['content'] if 'content' in data else None
    from_number = data['from']
    media = data['media'] if 'media' in data else None
    media_blob = None
    
    if media is not None:
        media_blob = messaging_client.download_media(media['id'])
        
        if "audio" in media['mimeType']:
            # Convert media_blob to bytes
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
            
            # TODO handle sending image to OpenAI
            # TBD handle media directly in the API layer
    
    # Skip processing if there's no text content
    if not content or content.strip() == "":
        logger.info(f"No text content to process, skipping message from {from_number}")
        return
    
    new_messages = await ask(content, from_number)
    
    logger.info(f"New messages: {new_messages}")
    
    # Send responses to the user
    for message in new_messages:
        if ('name' in message and message['name'] == "Customer") or message['role'] == "user":
            continue
            
        logger.info(f"Sending response: {message}")
        text_options = TextNotificationContent (
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
