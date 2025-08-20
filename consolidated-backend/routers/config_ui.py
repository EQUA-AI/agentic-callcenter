"""
Web UI Router for Configuration Management
Provides user-friendly web interface for managing agents and channels
"""
from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import json
import uuid
from datetime import datetime

from config_manager import (
    get_config_manager, 
    AgentConfig, 
    ChannelConfig, 
    AgentChannelMapping
)

config_ui_router = APIRouter(prefix="/config")
templates = Jinja2Templates(directory="templates")

@config_ui_router.get("/", response_class=HTMLResponse)
async def config_dashboard(request: Request):
    """Main configuration dashboard"""
    try:
        manager = get_config_manager()
        stats = manager.get_stats()
        validation = manager.validate_configuration()
        
        agents = manager.list_agents()
        channels = manager.list_channels()
        
        return templates.TemplateResponse("config_dashboard.html", {
            "request": request,
            "stats": stats,
            "validation": validation,
            "agents": agents,
            "channels": channels
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard: {str(e)}")

@config_ui_router.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    """Agents management page"""
    try:
        manager = get_config_manager()
        agents = manager.list_agents()
        
        # Get channel counts for each agent (avoid circular references)
        for agent in agents:
            channels = manager.get_channels_for_agent(agent['agent_id'])
            agent['channel_count'] = len(channels)
            # Only include basic channel info to avoid circular references
            agent['channels'] = [
                {
                    'channel_id': ch['channel_id'],
                    'channel_name': ch['channel_name'],
                    'channel_type': ch['channel_type'],
                    'phone_number': ch['phone_number']
                } for ch in channels
            ]
        
        return templates.TemplateResponse("agents_management.html", {
            "request": request,
            "agents": agents
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load agents: {str(e)}")

@config_ui_router.get("/channels", response_class=HTMLResponse)
async def channels_page(request: Request, channel_type: Optional[str] = None):
    """Channels management page"""
    try:
        manager = get_config_manager()
        channels = manager.list_channels(channel_type=channel_type)
        
        # Get agent assignments for each channel (avoid circular references)
        for channel in channels:
            mappings = manager.get_mappings_by_channel(channel['channel_id'])
            channel['agent_mappings'] = []
            for mapping in mappings:
                agent = manager.get_agent(mapping['agent_id'])
                if agent:
                    # Only include basic agent info to avoid circular references
                    channel['agent_mappings'].append({
                        'agent': {
                            'agent_id': agent['agent_id'],
                            'agent_name': agent['agent_name'],
                            'foundry_endpoint': agent['foundry_endpoint']
                        },
                        'is_primary': mapping.get('is_primary', False),
                        'mapping_id': mapping['mapping_id']
                    })
        
        return templates.TemplateResponse("channels_management.html", {
            "request": request,
            "channels": channels,
            "filter_type": channel_type
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load channels: {str(e)}")

@config_ui_router.post("/agents/add")
async def add_agent(
    request: Request,
    agent_id: str = Form(...),
    agent_name: str = Form(...),
    foundry_endpoint: str = Form(...),
    description: str = Form("")
):
    """Add a new agent"""
    try:
        manager = get_config_manager()
        
        # Validate agent_id format
        if not agent_id.startswith('asst_'):
            raise HTTPException(status_code=400, detail="Agent ID must start with 'asst_'")
        
        # Check if agent already exists
        if manager.get_agent(agent_id):
            raise HTTPException(status_code=400, detail="Agent ID already exists")
        
        # Create agent configuration
        agent_config = AgentConfig(
            agent_id=agent_id,
            agent_name=agent_name,
            foundry_endpoint=foundry_endpoint,
            description=description
        )
        
        success = manager.add_agent(agent_config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add agent")
        
        return RedirectResponse(url="/config/agents", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add agent: {str(e)}")

@config_ui_router.post("/channels/add")
async def add_channel(
    request: Request,
    channel_id: str = Form(...),
    channel_name: str = Form(...),
    channel_type: str = Form(...),
    provider: str = Form(...),
    phone_number: str = Form(...),
    business_name: str = Form("")
):
    """Add a new channel"""
    try:
        manager = get_config_manager()
        
        # Validate phone number format
        if not phone_number.startswith('+'):
            raise HTTPException(status_code=400, detail="Phone number must be in E.164 format (+1234567890)")
        
        # Check if channel already exists
        if manager.get_channel(channel_id):
            raise HTTPException(status_code=400, detail="Channel ID already exists")
        
        # Check if phone number is already used
        existing_channel = manager.get_channel_by_phone(phone_number)
        if existing_channel:
            raise HTTPException(status_code=400, detail=f"Phone number already used by channel {existing_channel['channel_id']}")
        
        # Create channel configuration
        channel_config = ChannelConfig(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=channel_type,
            provider=provider,
            phone_number=phone_number,
            business_name=business_name
        )
        
        success = manager.add_channel(channel_config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add channel")
        
        return RedirectResponse(url="/config/channels", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add channel: {str(e)}")

@config_ui_router.post("/mappings/add")
async def add_mapping(
    request: Request,
    agent_id: str = Form(...),
    channel_id: str = Form(...),
    is_primary: bool = Form(False)
):
    """Add agent-channel mapping"""
    try:
        manager = get_config_manager()
        
        # Validate agent and channel exist
        if not manager.get_agent(agent_id):
            raise HTTPException(status_code=400, detail="Agent not found")
        
        if not manager.get_channel(channel_id):
            raise HTTPException(status_code=400, detail="Channel not found")
        
        # Check for existing mapping
        existing_mappings = manager.get_mappings_by_channel(channel_id)
        agent_mappings = [m for m in existing_mappings if m['agent_id'] == agent_id]
        if agent_mappings:
            raise HTTPException(status_code=400, detail="Mapping already exists")
        
        # If setting as primary, remove primary flag from other mappings
        if is_primary:
            for mapping in existing_mappings:
                if mapping.get('is_primary'):
                    manager.mappings_container.replace_item(
                        item=mapping['mapping_id'],
                        body={**mapping, 'is_primary': False}
                    )
        
        # Create mapping
        mapping_id = f"mapping_{uuid.uuid4().hex[:8]}"
        mapping = AgentChannelMapping(
            mapping_id=mapping_id,
            agent_id=agent_id,
            channel_id=channel_id,
            is_primary=is_primary
        )
        
        success = manager.add_mapping(mapping)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add mapping")
        
        return RedirectResponse(url="/config/channels", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add mapping: {str(e)}")

@config_ui_router.post("/agents/{agent_id}/delete")
async def delete_agent(agent_id: str):
    """Delete an agent"""
    try:
        manager = get_config_manager()
        
        if not manager.get_agent(agent_id):
            raise HTTPException(status_code=404, detail="Agent not found")
        
        success = manager.remove_agent(agent_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete agent")
        
        return RedirectResponse(url="/config/agents", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

@config_ui_router.post("/channels/{channel_id}/delete")
async def delete_channel(channel_id: str):
    """Delete a channel"""
    try:
        manager = get_config_manager()
        
        if not manager.get_channel(channel_id):
            raise HTTPException(status_code=404, detail="Channel not found")
        
        success = manager.remove_channel(channel_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete channel")
        
        return RedirectResponse(url="/config/channels", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete channel: {str(e)}")

@config_ui_router.post("/mappings/{mapping_id}/delete")
async def delete_mapping(mapping_id: str):
    """Delete a mapping"""
    try:
        manager = get_config_manager()
        
        success = manager.remove_mapping(mapping_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete mapping")
        
        return RedirectResponse(url="/config/channels", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete mapping: {str(e)}")

# API endpoints for programmatic access
@config_ui_router.get("/api/agents")
async def api_list_agents():
    """API: List all agents (clean, no circular references)"""
    try:
        manager = get_config_manager()
        agents = manager.list_agents()
        
        # Return clean agent data without circular references
        clean_agents = []
        for agent in agents:
            clean_agent = {
                'agent_id': agent['agent_id'],
                'agent_name': agent['agent_name'],
                'foundry_endpoint': agent['foundry_endpoint'],
                'description': agent.get('description', ''),
                'created_at': agent.get('created_at'),
                'updated_at': agent.get('updated_at')
            }
            clean_agents.append(clean_agent)
        
        return {"agents": clean_agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load agents: {str(e)}")

@config_ui_router.get("/api/channels")
async def api_list_channels(channel_type: Optional[str] = None):
    """API: List all channels"""
    try:
        manager = get_config_manager()
        channels = manager.list_channels(channel_type=channel_type)
        return {"channels": channels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_ui_router.get("/api/phone/{phone_number}/agent")
async def api_get_agent_for_phone(phone_number: str):
    """API: Get agent configuration for a phone number"""
    try:
        manager = get_config_manager()
        
        # Ensure phone number is in E.164 format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        agent = manager.get_agent_for_phone(phone_number)
        if not agent:
            raise HTTPException(status_code=404, detail="No agent found for this phone number")
        
        # Also get the channel info
        channel = manager.get_channel_by_phone(phone_number)
        
        return {
            "phone_number": phone_number,
            "agent": agent,
            "channel": channel
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_ui_router.get("/api/validation")
async def api_validation():
    """API: Get configuration validation results"""
    try:
        manager = get_config_manager()
        validation = manager.validate_configuration()
        return validation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_ui_router.get("/api/stats")
async def api_stats():
    """API: Get configuration statistics"""
    try:
        manager = get_config_manager()
        stats = manager.get_stats()
        return {
            "total_agents": stats.total_agents,
            "total_channels": stats.total_channels,
            "total_mappings": stats.total_mappings,
            "active_channels": stats.active_channels,
            "whatsapp_channels": stats.whatsapp_channels,
            "sms_channels": stats.sms_channels
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
