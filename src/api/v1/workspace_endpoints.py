"""
Workspace initialization endpoints
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from src.clients.anythingllm import AnythingLLMClient
from src.core.config.manager import ConfigurationManager
from .dependencies import get_configuration_manager
from .middleware import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/init-workspace", tags=["admin"])
@limiter.limit("5/minute")
async def initialize_workspace(
    request: Request,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Initialize default AnythingLLM workspace"""
    try:
        config = config_manager.get_configuration()
        
        async with AnythingLLMClient(config.anythingllm) as client:
            # Get existing workspaces
            workspaces = await client.list_workspaces()
            
            # Check if default workspace exists
            for ws in workspaces:
                if ws.get("slug") == "docaiche-default":
                    return {"message": "Default workspace already exists", "workspace": ws}
            
            # Create default workspace
            workspace = await client.get_or_create_workspace("docaiche-default", "DocAIche Default")
            
            return {"message": "Default workspace created", "workspace": workspace}
            
    except Exception as e:
        logger.error(f"Failed to initialize workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))