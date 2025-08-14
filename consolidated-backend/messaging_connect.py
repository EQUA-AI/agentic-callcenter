"""
Azure Communication Services Messaging Connect REST API Integration
Specifically designed for Infobip SMS/WhatsApp integration
"""

import aiohttp
import asyncio
import logging
import os
from typing import Dict, Optional
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

logger = logging.getLogger(__name__)


class MessagingConnectClient:
    """
    Client for Azure Communication Services Messaging Connect REST API
    Uses Managed Identity authentication for secure access to Infobip channels
    """
    
    def __init__(self, acs_endpoint: str, client_id: str = None):
        self.acs_endpoint = acs_endpoint.rstrip('/')
        self.messaging_endpoint = f"{self.acs_endpoint}/messaging/connect/v1"
        
        # Use Managed Identity for authentication
        if client_id:
            self.credential = ManagedIdentityCredential(client_id=client_id)
        else:
            self.credential = DefaultAzureCredential()
            
        self._token_cache = None
        self._token_expiry = None
        
    async def _get_access_token(self) -> str:
        """Get cached or fresh access token"""
        import time
        
        if (self._token_cache is None or 
            self._token_expiry is None or 
            time.time() >= self._token_expiry - 300):  # Refresh 5 min early
            
            token = await asyncio.to_thread(
                self.credential.get_token,
                "https://communication.azure.com/.default"
            )
            self._token_cache = token.token
            self._token_expiry = token.expires_on
            
        return self._token_cache
    
    async def send_infobip_sms(self, channel_id: str, to: str, message: str) -> Dict:
        """
        Send SMS via Infobip channel through ACS Messaging Connect
        
        Args:
            channel_id: Your Infobip channel registration ID from ACS
            to: Phone number in E.164 format (e.g., +1234567890)
            message: SMS text message to send
            
        Returns:
            Dict with message ID and status from ACS
        """
        try:
            token = await self._get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ACS-MessagingConnect-Infobip/1.0"
            }
            
            # Payload format for Infobip SMS via ACS Messaging Connect
            payload = {
                "channelRegistrationId": channel_id,
                "to": [{"phoneNumber": to}],
                "content": {
                    "text": message
                }
            }
            
            logger.info(f"Sending Infobip SMS to {to} via channel {channel_id}")
            logger.debug(f"Payload: {payload}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.messaging_endpoint}/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    response_text = await response.text()
                    logger.debug(f"Response status: {response.status}, body: {response_text}")
                    
                    if response.status == 202:  # Accepted
                        try:
                            result = await response.json() if response_text else {}
                            logger.info(f"SMS sent successfully: {result}")
                            return {
                                "success": True,
                                "message_id": result.get("messageId", "unknown"),
                                "status": "accepted",
                                "channel": "infobip_sms"
                            }
                        except:
                            # Some ACS endpoints return 202 with empty body
                            logger.info("SMS accepted (empty response body)")
                            return {
                                "success": True,
                                "message_id": "pending",
                                "status": "accepted",
                                "channel": "infobip_sms"
                            }
                    else:
                        logger.error(f"SMS failed - Status {response.status}: {response_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response_text}",
                            "channel": "infobip_sms"
                        }
                        
        except Exception as e:
            logger.error(f"Messaging Connect SMS error: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": "infobip_sms"
            }
    
    async def send_infobip_whatsapp(self, channel_id: str, to: str, message: str) -> Dict:
        """
        Send WhatsApp message via Infobip channel through ACS Messaging Connect
        
        Args:
            channel_id: Your Infobip WhatsApp channel registration ID from ACS
            to: Phone number in E.164 format
            message: WhatsApp message text
            
        Returns:
            Dict with result
        """
        try:
            token = await self._get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ACS-MessagingConnect-Infobip/1.0"
            }
            
            # Payload format for Infobip WhatsApp via ACS Messaging Connect
            payload = {
                "channelRegistrationId": channel_id,
                "to": [{"phoneNumber": to}],
                "content": {
                    "text": message
                }
            }
            
            logger.info(f"Sending Infobip WhatsApp to {to} via channel {channel_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.messaging_endpoint}/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status == 202:
                        try:
                            result = await response.json() if response_text else {}
                            logger.info(f"WhatsApp sent successfully: {result}")
                            return {
                                "success": True,
                                "message_id": result.get("messageId", "unknown"),
                                "status": "accepted",
                                "channel": "infobip_whatsapp"
                            }
                        except:
                            return {
                                "success": True,
                                "message_id": "pending",
                                "status": "accepted",
                                "channel": "infobip_whatsapp"
                            }
                    else:
                        logger.error(f"WhatsApp failed - Status {response.status}: {response_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response_text}",
                            "channel": "infobip_whatsapp"
                        }
                        
        except Exception as e:
            logger.error(f"Messaging Connect WhatsApp error: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": "infobip_whatsapp"
            }


class MessagingConnectService:
    """
    Service wrapper for Messaging Connect functionality with Infobip
    """
    
    def __init__(self):
        self.enabled = os.getenv('MESSAGING_CONNECT_ENABLED', 'false').lower() == 'true'
        self.client = None
        self.sms_channel_id = os.getenv('SMS_CHANNEL_ID')
        self.whatsapp_channel_id = os.getenv('WHATSAPP_CHANNEL_ID')
        
        if self.enabled:
            acs_endpoint = os.getenv('ACS_ENDPOINT')
            client_id = os.getenv('AZURE_CLIENT_ID')
            
            if not acs_endpoint:
                logger.warning("ACS_ENDPOINT not found, Messaging Connect disabled")
                self.enabled = False
            else:
                self.client = MessagingConnectClient(acs_endpoint, client_id)
                logger.info(f"Messaging Connect service initialized - SMS: {bool(self.sms_channel_id)}, WhatsApp: {bool(self.whatsapp_channel_id)}")
    
    async def send_sms(self, phone_number: str, message: str, channel_id: str = None) -> Dict:
        """
        Send SMS via Infobip
        
        Args:
            phone_number: Phone number in E.164 format
            message: SMS text
            channel_id: Optional specific channel ID, uses SMS_CHANNEL_ID env var if not provided
            
        Returns:
            Dict with result
        """
        if not self.enabled:
            return {"success": False, "error": "Messaging Connect not enabled"}
        
        if not self.client:
            return {"success": False, "error": "Messaging Connect client not initialized"}
        
        # Use provided channel_id or fall back to environment variable
        use_channel_id = channel_id or self.sms_channel_id
        if not use_channel_id:
            return {"success": False, "error": "SMS channel ID not configured"}
        
        try:
            result = await self.client.send_infobip_sms(use_channel_id, phone_number, message)
            return result
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_whatsapp(self, phone_number: str, message: str, channel_id: str = None) -> Dict:
        """
        Send WhatsApp message via Infobip
        
        Args:
            phone_number: Phone number in E.164 format
            message: WhatsApp message text
            channel_id: Optional specific channel ID, uses WHATSAPP_CHANNEL_ID env var if not provided
            
        Returns:
            Dict with result
        """
        if not self.enabled:
            return {"success": False, "error": "Messaging Connect not enabled"}
        
        if not self.client:
            return {"success": False, "error": "Messaging Connect client not initialized"}
        
        # Use provided channel_id or fall back to environment variable
        use_channel_id = channel_id or self.whatsapp_channel_id
        if not use_channel_id:
            return {"success": False, "error": "WhatsApp channel ID not configured"}
        
        try:
            result = await self.client.send_infobip_whatsapp(use_channel_id, phone_number, message)
            return result
        except Exception as e:
            logger.error(f"Failed to send WhatsApp: {e}")
            return {"success": False, "error": str(e)}
    
    def is_enabled(self) -> bool:
        """Check if Messaging Connect is enabled"""
        return self.enabled
    
    def get_status(self) -> Dict:
        """Get service status and configuration"""
        return {
            "enabled": self.enabled,
            "sms_configured": bool(self.sms_channel_id),
            "whatsapp_configured": bool(self.whatsapp_channel_id),
            "sms_channel_id": self.sms_channel_id,
            "whatsapp_channel_id": self.whatsapp_channel_id
        }


# Global service instance
_messaging_connect_service = None

def get_messaging_connect_service() -> MessagingConnectService:
    """Get global Messaging Connect service instance"""
    global _messaging_connect_service
    if _messaging_connect_service is None:
        _messaging_connect_service = MessagingConnectService()
    return _messaging_connect_service
