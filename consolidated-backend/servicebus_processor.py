"""
Service Bus background processor for consolidated backend
Processes Service Bus messages without requiring separate Functions runtime
"""
import asyncio
import json
import logging
import os
from typing import Optional
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)

class ServiceBusBackgroundProcessor:
    def __init__(self, multi_agent_router, messaging_client, whisper_client, messaging_connect_service):
        self.multi_agent_router = multi_agent_router
        self.messaging_client = messaging_client
        self.whisper_client = whisper_client
        self.messaging_connect_service = messaging_connect_service
        self.running = False
        self.task = None
        
        # Service Bus configuration
        self.servicebus_namespace = os.getenv("ServiceBusConnection__fullyQualifiedNamespace")
        self.queue_name = "messages"
        self.credential = DefaultAzureCredential()
        
    async def start(self):
        """Start the background Service Bus processor"""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._process_messages())
        logger.info("✅ Service Bus background processor started")
        
    async def stop(self):
        """Stop the background Service Bus processor"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Service Bus background processor stopped")
        
    async def _process_messages(self):
        """Main message processing loop"""
        while self.running:
            try:
                async with ServiceBusClient(
                    fully_qualified_namespace=self.servicebus_namespace,
                    credential=self.credential
                ) as servicebus_client:
                    
                    async with servicebus_client.get_queue_receiver(
                        queue_name=self.queue_name,
                        max_wait_time=30  # Wait up to 30 seconds for messages
                    ) as receiver:
                        
                        logger.info(f"🔍 Listening for messages on queue: {self.queue_name}")
                        
                        async for message in receiver:
                            if not self.running:
                                break
                                
                            try:
                                await self._handle_message(message)
                                await receiver.complete_message(message)
                                logger.info("✅ Message processed and completed")
                                
                            except Exception as e:
                                logger.error(f"❌ Error processing message: {e}")
                                await receiver.abandon_message(message)
                                
            except Exception as e:
                logger.error(f"❌ Service Bus connection error: {e}")
                if self.running:
                    await asyncio.sleep(10)  # Wait before retrying
                    
    async def _handle_message(self, message: ServiceBusMessage):
        """Handle individual Service Bus message"""
        try:
            # Parse message body
            message_body = message.body.decode('utf-8')
            sb_message_payload = json.loads(message_body)
            
            logger.info(f'📨 Processing Service Bus message: {sb_message_payload.get("eventType", "unknown")}')
            
            if sb_message_payload.get('eventType') != "Microsoft.Communication.AdvancedMessageReceived":
                logger.info(f"⏭️ Skipping non-message event: {sb_message_payload.get('eventType')}")
                return
            
            data = sb_message_payload.get('data', {})
            channel_type = data.get('channelType', '')
            content = data.get('content', '')
            from_number = data.get('from', '')
            to_number = data.get('to', '')
            media = data.get('media')
            
            # Handle media processing (audio/image)
            if media:
                content = await self._process_media(media, content)
            
            # Skip if no content
            if not content or content.strip() == "":
                logger.info(f"⏭️ No text content to process from {from_number}")
                return
            
            # Create conversation ID
            conversation_id = f"{channel_type}_{from_number.replace('+', '')}"
            
            logger.info(f"🎯 Routing message from {from_number} to {to_number} using dynamic configuration")
            
            # Process through multi-agent router
            result = await self.multi_agent_router.process_message(
                from_phone=from_number,
                to_phone=to_number,
                message_content=content,
                conversation_id=conversation_id
            )
            
            if not result['success']:
                logger.error(f"❌ Failed to process message: {result.get('error', 'Unknown error')}")
                return
            
            routing_info = result['routing_info']
            agent_response = result['response']
            
            logger.info(f"🤖 Agent {routing_info['agent_name']} responded for channel {routing_info['channel_name']}")
            
            # Send response back
            await self._send_response_to_channel(
                response_text=agent_response,
                from_number=from_number,
                channel_info=routing_info
            )
            
        except Exception as e:
            logger.error(f"❌ Error in _handle_message: {e}")
            raise
            
    async def _process_media(self, media: dict, existing_content: str) -> str:
        """Process media attachments (audio transcription, image handling)"""
        try:
            media_id = media.get('id')
            mime_type = media.get('mimeType', '')
            
            if not media_id:
                return existing_content
                
            # Download media
            media_blob = self.messaging_client.download_media(media_id)
            binary_data = b"".join(media_blob)
            
            if "audio" in mime_type:
                # Transcribe audio using Whisper
                logger.info("🎵 Transcribing audio message...")
                transcription = self.whisper_client.audio.transcriptions.create(
                    model="whisper",
                    file=binary_data
                )
                return transcription.text
                
            elif "image" in mime_type:
                # Handle image - for now just use caption if available
                caption = media.get('caption', '')
                logger.info("🖼️ Processing image message...")
                return caption if caption else existing_content
                
            return existing_content
            
        except Exception as e:
            logger.error(f"❌ Error processing media: {e}")
            return existing_content
            
    async def _send_response_to_channel(self, response_text: str, from_number: str, channel_info: dict):
        """Send response back through appropriate channel"""
        try:
            channel_type = channel_info.get('channel_type', '')
            channel_id = channel_info.get('channel_id', '')
            channel_name = channel_info.get('channel_name', 'Unknown')
            
            if channel_type == 'whatsapp':
                await self._send_whatsapp_response(response_text, from_number, channel_id, channel_name)
            elif channel_type == 'sms':
                await self._send_sms_response(response_text, from_number, channel_id, channel_name)
            else:
                logger.error(f"❌ Unsupported channel type: {channel_type}")
                
        except Exception as e:
            logger.error(f"❌ Error sending response: {e}")
            
    async def _send_whatsapp_response(self, response_text: str, from_number: str, channel_id: str, channel_name: str):
        """Send WhatsApp response"""
        try:
            from azure.communication.messages.models import TextNotificationContent
            
            text_options = TextNotificationContent(
                channel_registration_id=channel_id,
                to=[from_number],
                content=response_text,
            )
            
            message_responses = self.messaging_client.send(text_options)
            message_send_result = message_responses.receipts[0]
            
            if message_send_result:
                logger.info(f"✅ WhatsApp message sent to {from_number} via {channel_name}")
            else:
                logger.error(f"❌ Failed to send WhatsApp message to {from_number}")
                
        except Exception as e:
            logger.error(f"❌ WhatsApp send error: {e}")
            
    async def _send_sms_response(self, response_text: str, from_number: str, channel_id: str, channel_name: str):
        """Send SMS response"""
        try:
            result = await self.messaging_connect_service.send_sms(from_number, response_text, channel_id)
            if result.get('success'):
                logger.info(f"✅ SMS sent to {from_number} via {channel_name}")
            else:
                logger.error(f"❌ Failed to send SMS to {from_number}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ SMS send error: {e}")
