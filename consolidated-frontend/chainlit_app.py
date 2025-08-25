"""
Enhanced Chainlit Chat Interface
Integrates with Azure AI Foundry agents and supports multiple service profiles
"""
import chainlit as cl
import aiohttp
import logging
import os
import uuid
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Azure AI Foundry client
from azure_foundry_client import ask_foundry_agent, get_foundry_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")  # Keep for fallback scenarios
# Define chat profiles
@cl.set_chat_profiles
async def chat_profile(current_user: Optional[cl.User]):
    return [
        cl.ChatProfile(
            name="Hajj & Umrah Services",
            markdown_description="🕋 **Complete guidance for your spiritual journey**\n\nGet expert help with pilgrimage planning, religious requirements, travel arrangements, and accommodation booking. Our specialists understand the spiritual and practical aspects of Hajj and Umrah.",
            starters=[
                cl.Starter(
                    label="Plan Hajj Journey",
                    message="I want to plan my Hajj journey for next year. Can you help me understand the requirements and process?"
                ),
                cl.Starter(
                    label="Umrah Requirements", 
                    message="What are the visa requirements and documentation needed for Umrah?"
                ),
                cl.Starter(
                    label="Spiritual Guidance",
                    message="Can you explain the spiritual significance and rituals of Hajj?"
                ),
                cl.Starter(
                    label="Compare Packages",
                    message="I'd like to compare different Hajj and Umrah packages and their costs"
                )
            ]
        ),
        cl.ChatProfile(
            name="Wedding Planning",
            markdown_description="💒 **Professional wedding planning services**\n\nLet us help make your special day absolutely perfect! From venue selection to vendor coordination, we handle every detail with care and expertise.",
            starters=[
                cl.Starter(
                    label="Plan Dream Wedding",
                    message="I want to plan my dream wedding. Can you help me get started with the basics?"
                ),
                cl.Starter(
                    label="Find Venues",
                    message="What are the best wedding venues in my area and how do I choose?"
                ),
                cl.Starter(
                    label="Budget Planning",
                    message="I need help creating a detailed wedding budget breakdown"
                ),
                cl.Starter(
                    label="Theme Ideas",
                    message="Can you suggest unique wedding themes and decoration ideas?"
                )
            ]
        ),
        cl.ChatProfile(
            name="EPCON AI",
            markdown_description="🛠️ **Technical diagnostic & spare parts ordering**\n\nGet comprehensive help with equipment diagnostics, technical troubleshooting, and spare parts ordering. Our EPCON AI specialists provide expert technical assistance.",
            starters=[
                cl.Starter(
                    label="Equipment Diagnostics",
                    message="I need help diagnosing technical issues with my equipment"
                ),
                cl.Starter(
                    label="Spare Parts Ordering",
                    message="I need to order spare parts for my equipment"
                ),
                cl.Starter(
                    label="Technical Support",
                    message="I have technical questions and need expert assistance"
                ),
                cl.Starter(
                    label="General Inquiry",
                    message="I need technical support but I'm not sure what category my issue falls under"
                )
            ]
        )
    ]

# AI Agent Configuration with Azure AI Foundry endpoints
AI_AGENTS_CONFIG = {
    "hajj_agent": {
        "agent_id": "asst_QyONy5LPHKeETJgS1nftQT9x",  # Hardcoded Agent ID for Hajj & Umrah
        "name": "Hajj & Umrah Services",
        "description": "Specialized AI agent for Islamic pilgrimage services",
        "foundry_endpoint": "https://weddingomni.services.ai.azure.com/api/projects/WeddingOmni",  # Your Azure AI Foundry endpoint
        "capabilities": ["pilgrimage_planning", "religious_guidance", "travel_arrangements", "documentation_help"],
        "system_prompt": "You are a specialized AI assistant for Hajj and Umrah services. Provide guidance on Islamic pilgrimage requirements, travel arrangements, and spiritual preparation."
    },
    "wedding_agent": {
        "agent_id": "asst_khFWOGAwaF7BJ73ecupCfXze",  # Hardcoded Agent ID for Wedding Planning
        "name": "Wedding Planning Services", 
        "description": "Professional wedding planning and coordination AI agent",
        "foundry_endpoint": "https://weddingomni.services.ai.azure.com/api/projects/WeddingOmni",  # Your Azure AI Foundry endpoint
        "capabilities": ["venue_selection", "vendor_coordination", "budget_planning", "timeline_management"],
        "system_prompt": "You are a professional wedding planning assistant. Help couples plan their perfect wedding with expert advice on venues, vendors, budgets, and coordination."
    },
    "telco_agent": {
        "agent_id": "asst_LgflhAlTTQMvnDLJp4wmOFQr",  # Hardcoded Agent ID for EPCON AI
        "name": "EPCON AI Technical Support",
        "description": "Technical diagnostics and spare parts ordering AI agent",
        "foundry_endpoint": "https://weddingomni.services.ai.azure.com/api/projects/WeddingOmni",  # Your Azure AI Foundry endpoint
        "capabilities": ["equipment_diagnostics", "spare_parts_ordering", "technical_troubleshooting", "maintenance_support"],
        "system_prompt": "You are EPCON AI, a technical diagnostic and spare parts specialist. Provide expert assistance with equipment troubleshooting, parts identification, and maintenance support."
    }
}

class AzureFoundryAgentConnector:
    """Handles direct communication with Azure AI Foundry agents"""
    
    def __init__(self):
        self.foundry_client = get_foundry_client()
        
    async def send_to_agent(self, message: str, agent_type: str, phone_number: str, context: Optional[dict] = None) -> str:
        """Send message to specific Azure AI Foundry agent and get response"""
        if agent_type not in AI_AGENTS_CONFIG:
            logger.warning(f"Unknown agent type: {agent_type}")
            return "I'm sorry, I couldn't find the appropriate specialist for your request."
        
        agent_config = AI_AGENTS_CONFIG[agent_type]
        
        try:
            # Create conversation ID based on user session
            session_id = cl.user_session.get("session_id", "default")
            conversation_id = f"{phone_number}_{session_id}"
            
            # Prepare context for the agent
            agent_context = {
                "user_phone": phone_number,
                "session_id": session_id,
                "profile": context.get("profile") if context else None,
                "capabilities": agent_config["capabilities"],
                "service_name": agent_config["name"]
            }
            
            logger.info(f"[FOUNDRY] Sending message to agent {agent_config['agent_id']}: {message[:100]}...")
            
            # Call Azure AI Foundry agent directly
            response = await ask_foundry_agent(
                user_text=message,
                agent_id=agent_config["agent_id"],
                conversation_id=conversation_id,
                foundry_endpoint=agent_config["foundry_endpoint"],
                system_prompt=agent_config["system_prompt"],
                context=agent_context
            )
            
            if response and response.strip():
                logger.info(f"[FOUNDRY] Successfully received response from agent {agent_config['agent_id']}")
                return response
            else:
                logger.warning(f"[FOUNDRY] Empty response from agent {agent_config['agent_id']}")
                return "I'm processing your request. Could you please try rephrasing your question?"
                
        except Exception as e:
            logger.error(f"[FOUNDRY] Error communicating with agent {agent_config['agent_id']}: {e}")
            return await self._fallback_response(agent_config, message)
    
    async def _fallback_response(self, agent_config: dict, message: str) -> str:
        """Provide fallback response when agent communication fails"""
        service_fallbacks = {
            "Hajj & Umrah Services": "I apologize for the technical difficulty. For Hajj and Umrah guidance, I'm here to help with pilgrimage planning, religious requirements, and travel arrangements. Please try asking your question again.",
            "Wedding Planning Services": "I apologize for the technical difficulty. For wedding planning assistance, I can help with venue selection, vendor coordination, and timeline planning. Please try asking your question again.",
            "EPCON AI Technical Support": "I apologize for the technical difficulty. For technical support, I can assist with equipment diagnostics, spare parts ordering, and troubleshooting. Please try asking your question again."
        }
        
        return service_fallbacks.get(
            agent_config["name"], 
            "I'm experiencing technical difficulties. Please try again later."
        )
    
    async def clear_conversation(self, agent_type: str, phone_number: str):
        """Clear conversation history for specific agent and user"""
        if agent_type in AI_AGENTS_CONFIG:
            agent_config = AI_AGENTS_CONFIG[agent_type]
            session_id = cl.user_session.get("session_id", "default")
            conversation_id = f"{phone_number}_{session_id}"
            
            self.foundry_client.clear_conversation(
                agent_id=agent_config["agent_id"],
                conversation_id=conversation_id
            )
            logger.info(f"[FOUNDRY] Cleared conversation for agent {agent_config['agent_id']}")
    
    async def get_stats(self) -> dict:
        """Get agent connector statistics"""
        return self.foundry_client.get_conversation_stats()
    
    async def close(self):
        """Clean up resources"""
        await self.foundry_client.close()

# Global agent connector instance
agent_connector = AzureFoundryAgentConnector()

# Service configuration
SERVICE_CONFIG = {
    "hajj": {
        "name": "Hajj & Umrah Services",
        "agent_type": "hajj_agent",
        "emoji": "🕋",
        "color": "#16a34a",
        "greeting": "🕋 Assalamu Alaikum! Welcome to Hajj & Umrah Services. I'm here to help you plan your spiritual journey. Whether you need guidance on rituals, travel arrangements, or accommodation, I'm ready to assist you.",
        "description": "Expert guidance for your spiritual journey to Mecca"
    },
    "wedding": {
        "name": "Wedding Planning",
        "agent_type": "wedding_agent", 
        "emoji": "💒",
        "color": "#be185d",
        "greeting": "💒 Congratulations! Welcome to our Wedding Planning Services. I'm excited to help make your special day absolutely perfect! From venue selection to catering, decorations to photography - let's plan your dream wedding together.",
        "description": "Professional wedding planning and coordination services"
    },
    "telco": {
        "name": "EPCON AI",
        "agent_type": "telco_agent",
        "emoji": "🤖", 
        "color": "#2563eb",
        "greeting": "🤖 Welcome to EPCON AI! I'm here to help with technical diagnostics and spare parts ordering. Whether you need equipment troubleshooting, parts identification, or maintenance support, I'll provide expert assistance powered by our technical knowledge base.",
        "description": "Technical diagnostic & spare parts ordering services"
    }
}

@cl.on_chat_start
async def start():
    """Initialize chat session - wait for profile selection"""
    # Generate unique session ID for web users
    session_id = str(uuid.uuid4())[:8]
    phone_number = f"web_user_{session_id}"
    
    # Set default session values
    cl.user_session.set("phone_number", phone_number)
    cl.user_session.set("agent_type", "telco_agent")  # Default to EPCON AI agent
    cl.user_session.set("current_service", "EPCON AI")
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("profile_welcomed", False)
    
    # Send brief initial message
    await cl.Message(
        content="👋 **Welcome!** Please select a service from the dropdown above to get started with the right specialist.",
        author="Call Center"
    ).send()

async def send_profile_welcome_message(profile_name: str):
    """Send profile-specific welcome message"""
    
    if profile_name == "Hajj & Umrah Services":
        # Update session for Hajj service
        cl.user_session.set("agent_type", "hajj_agent")
        cl.user_session.set("current_service", "Hajj & Umrah Services")
        cl.user_session.set("service_key", "hajj")
        
        welcome_message = """🕋 **Assalamu Alaikum! Welcome to Hajj & Umrah Services**

I'm your dedicated Hajj & Umrah specialist, here to guide you through every step of your spiritual journey to the Holy Land.

**✨ How I can assist you:**
• **Pilgrimage Planning**: Complete Hajj and Umrah packages
• **Religious Guidance**: Rituals, prayers, and spiritual preparation
• **Travel Arrangements**: Flights, accommodation, and transportation
• **Documentation**: Visa requirements and paperwork assistance
• **Group Services**: Family and community pilgrimage coordination

**🤲 Your spiritual journey is sacred to us.** Whether this is your first pilgrimage or you're helping others plan theirs, I'm here to ensure everything is arranged according to Islamic teachings and your personal needs.

*What aspect of your Hajj or Umrah journey would you like to discuss first?*"""
        
        await cl.Message(
            content=welcome_message,
            author="🕋 Hajj & Umrah Specialist"
        ).send()
        
    elif profile_name == "Wedding Planning":
        # Update session for Wedding service
        cl.user_session.set("agent_type", "wedding_agent")
        cl.user_session.set("current_service", "Wedding Planning")
        cl.user_session.set("service_key", "wedding")
        
        welcome_message = """💒 **Congratulations! Welcome to Wedding Planning Services**

I'm your personal wedding planning specialist, excited to help make your special day absolutely magical and stress-free!

**💝 Complete wedding coordination:**
• **Venue Selection**: Perfect locations for your ceremony and reception
• **Vendor Management**: Photographers, caterers, florists, and entertainment
• **Theme & Design**: Decoration, color schemes, and styling
• **Timeline Planning**: Detailed schedules and day-of coordination
• **Budget Management**: Cost-effective planning within your budget

**✨ Your dream wedding awaits!** From intimate ceremonies to grand celebrations, I'll handle every detail so you can focus on what matters most - celebrating your love.

*Tell me about your wedding vision! What's your dream ceremony like?*"""
        
        await cl.Message(
            content=welcome_message,
            author="💒 Wedding Planning Specialist"
        ).send()
        
    elif profile_name == "EPCON AI":
        # Update session for EPCON AI service
        cl.user_session.set("agent_type", "telco_agent")
        cl.user_session.set("current_service", "EPCON AI")
        cl.user_session.set("service_key", "telco")
        
        welcome_message = """🤖 **Welcome to EPCON AI**
**Technical diagnostic & spare parts ordering**

Get comprehensive help with equipment diagnostics, technical troubleshooting, and spare parts ordering. Our EPCON AI specialists provide expert technical assistance.

*How can I help you today?*"""
        
        await cl.Message(
            content=welcome_message,
            author="🤖 EPCON AI Technical Specialist"
        ).send()
    
    # Mark that we've sent the profile welcome
    cl.user_session.set("profile_welcomed", True)
    cl.user_session.set("current_profile", profile_name)

async def detect_and_handle_profile_from_message(message_content: str):
    """Detect if user is trying to use a specific service and show appropriate welcome"""
    
    # Don't show welcome if we've already welcomed for current profile
    if cl.user_session.get("profile_welcomed", False):
        return False
    
    message_lower = message_content.lower()
    
    # Keywords for each service
    hajj_keywords = ["hajj", "umrah", "pilgrimage", "mecca", "spiritual", "holy land", "kaaba"]
    wedding_keywords = ["wedding", "marriage", "bride", "groom", "venue", "celebration", "marry"]
    epcon_keywords = ["technical", "diagnostic", "spare parts", "equipment", "troubleshooting", "epcon", "parts", "maintenance"]
    
    # Check if message matches any service
    if any(keyword in message_lower for keyword in hajj_keywords):
        await send_profile_welcome_message("Hajj & Umrah Services")
        return True
    elif any(keyword in message_lower for keyword in wedding_keywords):
        await send_profile_welcome_message("Wedding Planning")
        return True
    elif any(keyword in message_lower for keyword in epcon_keywords):
        await send_profile_welcome_message("EPCON AI")
        return True
    
    return False

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages with enhanced service context"""
    try:
        # Get session data
        phone_number = cl.user_session.get("phone_number") or "web_user_001"
        agent_type = cl.user_session.get("agent_type") or "telco_agent"  # Default to EPCON AI instead of "general"
        current_service = cl.user_session.get("current_service") or "EPCON AI"
        current_profile = cl.user_session.get("current_profile") or "EPCON AI"
        
        # Check if this is the first real message and detect profile from content
        profile_handled = await detect_and_handle_profile_from_message(message.content)
        
        # If we just showed a profile welcome, don't process the trigger message
        if profile_handled:
            return
        
        # Check if user is asking to switch services
        message_lower = message.content.lower()
        service_switch_keywords = {
            "hajj": ["hajj", "umrah", "pilgrimage", "mecca", "spiritual"],
            "wedding": ["wedding", "marriage", "bride", "groom", "venue", "celebration"],
            "telco": ["technical", "diagnostic", "spare parts", "equipment", "troubleshooting", "epcon"]
        }
        
        # Auto-suggest service switch if needed
        suggested_service = None
        if agent_type not in AI_AGENTS_CONFIG:
            # If we don't have a valid agent type, suggest based on message content
            for key, keywords in service_switch_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    suggested_service = key
                    break
            
            # If no keywords detected, default to EPCON AI
            if not suggested_service:
                suggested_service = "telco"
        
        # Send to Azure AI Foundry agent directly (without showing processing message)
        response = await agent_connector.send_to_agent(
            message.content, 
            agent_type,
            phone_number, 
            context={"profile": current_profile}
        )
        
        # Prepare response with service context
        if suggested_service and agent_type not in AI_AGENTS_CONFIG:
            suggested_config = SERVICE_CONFIG[suggested_service]
            response_with_suggestion = f"""{response}

---

**💡 Service Suggestion:** 
Your question seems related to **{suggested_config['name']}** {suggested_config['emoji']}. 

Would you like me to connect you with our {suggested_config['name']} specialist? They can provide more detailed assistance with {suggested_config['description'].lower()}.

Simply switch to the "{suggested_config['name']}" profile above for specialized help!"""
            
            response = response_with_suggestion
        
        # Get service-specific author name and emoji
        service_authors = {
            "hajj_agent": f"🕋 {SERVICE_CONFIG['hajj']['name']} Specialist",
            "wedding_agent": f"💒 {SERVICE_CONFIG['wedding']['name']} Specialist", 
            "telco_agent": f"🤖 EPCON AI Technical Specialist"
        }
        
        author = service_authors.get(str(agent_type), "Call Center Assistant")
        
        # Send response
        await cl.Message(
            content=response,
            author=author
        ).send()
        
    except Exception as e:
        logger.error(f"Error in main message handler: {str(e)}", exc_info=True)
        await cl.Message(content="I apologize, but I'm having trouble processing your request right now. Please try again.").send()

@cl.on_chat_end
async def end():
    """Clean up when chat ends"""
    try:
        # Clean up any agent connector sessions
        logger.info("Chat session ended and cleaned up")
    except Exception as e:
        logger.error(f"Error during chat cleanup: {e}")

# Add chat action handlers for enhanced interactivity
@cl.action_callback("switch_service")
async def on_service_switch(action):
    """Handle service switch actions"""
    service_key = action.value
    if service_key in SERVICE_CONFIG:
        service = SERVICE_CONFIG[service_key]
        
        # Update session
        cl.user_session.set("agent_type", service["agent_type"])
        cl.user_session.set("current_service", service["name"])
        cl.user_session.set("service_key", service_key)
        
        await cl.Message(
            content=f"Switched to {service['name']} {service['emoji']}\n\n{service['greeting']}",
            author=f"{service['name']} Specialist"
        ).send()

if __name__ == "__main__":
    # Run the Chainlit app
    cl.run(
        host="0.0.0.0",
        port=8080,
        debug=True
    )
