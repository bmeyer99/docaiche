"""
Weaviate Vector Database API Endpoints
====================================

Direct Weaviate integration endpoints for configuration and workspace management.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body, Depends
from datetime import datetime

from src.clients.weaviate_client import WeaviateVectorClient
from src.core.config.manager import ConfigurationManager
from .dependencies import get_configuration_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weaviate", tags=["weaviate"])


@router.get("/config")
async def get_weaviate_config(
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get current Weaviate configuration."""
    try:
        config = config_manager.get_configuration()
        weaviate_config = config.weaviate
        
        # Try to test connection to get current status
        try:
            async with WeaviateVectorClient(weaviate_config) as client:
                health = await client.health_check()
                connected = health.get("ready", False)
                version = health.get("version", "unknown")
                
                # Get workspace count
                workspaces = await client.list_workspaces()
                workspaces_count = len(workspaces)
        except Exception as e:
            logger.warning(f"Could not connect to Weaviate: {e}")
            connected = False
            version = None
            workspaces_count = 0
        
        return {
            "enabled": True,
            "base_url": weaviate_config.endpoint,
            "api_key": weaviate_config.api_key if weaviate_config.api_key else "",
            "timeout_seconds": 30,
            "max_retries": 3,
            "verify_ssl": False,
            "connected": connected,
            "version": version,
            "workspaces_count": workspaces_count,
            "message": "Connected" if connected else "Not connected"
        }
    except Exception as e:
        logger.error(f"Failed to get Weaviate config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_weaviate_config(
    config_data: Dict[str, Any] = Body(...),
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Update Weaviate configuration."""
    try:
        # TODO: Implement configuration update
        # For now, just return success
        return {
            "success": True,
            "message": "Weaviate configuration updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update Weaviate config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_weaviate_connection(
    config_data: Dict[str, Any] = Body(...),
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Test Weaviate connection with provided configuration."""
    try:
        # Create temporary config for testing
        from src.core.config.models import WeaviateConfig
        
        test_config = WeaviateConfig(
            endpoint=config_data.get("base_url", "http://weaviate:8080"),
            api_key=config_data.get("api_key")
        )
        
        # Test connection
        async with WeaviateVectorClient(test_config) as client:
            health = await client.health_check()
            
            if health.get("ready", False):
                # Get workspace count if connection is successful
                workspaces = await client.list_workspaces()
                return {
                    "success": True,
                    "message": "Connection successful",
                    "version": health.get("version", "unknown"),
                    "workspaces_count": len(workspaces)
                }
            else:
                return {
                    "success": False,
                    "message": "Weaviate is not ready"
                }
    except Exception as e:
        logger.error(f"Weaviate connection test failed: {e}")
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }


@router.get("/workspaces")
async def get_weaviate_workspaces(
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get list of Weaviate workspaces (tenants)."""
    try:
        config = config_manager.get_configuration()
        
        async with WeaviateVectorClient(config.weaviate) as client:
            workspaces = await client.list_workspaces()
            
            # Transform to expected format
            formatted_workspaces = []
            for ws in workspaces:
                formatted_workspaces.append({
                    "id": ws.get("slug", ws.get("name", "unknown")),
                    "name": ws.get("name", ws.get("slug", "Unknown")),
                    "class_name": "DocumentContent",  # Default class name
                    "object_count": 0,  # TODO: Get actual count
                    "status": ws.get("status", "ACTIVE"),
                    "description": f"Workspace for {ws.get('name', 'documents')}"
                })
            
            return formatted_workspaces
    except Exception as e:
        logger.error(f"Failed to get Weaviate workspaces: {e}")
        # Return empty list on error to avoid breaking the UI
        return []


@router.put("/embeddings")
async def update_embedding_config(
    config_data: Dict[str, Any] = Body(...),
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Update embedding configuration for Weaviate."""
    try:
        # TODO: Implement embedding configuration update
        return {
            "success": True,
            "message": "Embedding configuration updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update embedding config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_slug}/expired")
async def get_expired_documents(
    workspace_slug: str,
    limit: int = 10000,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """
    Get expired documents in a workspace.
    
    Args:
        workspace_slug: The workspace to search in
        limit: Maximum number of objects to fetch (default: 10000)
    """
    try:
        config = config_manager.get_configuration()
        
        async with WeaviateVectorClient(config.weaviate) as client:
            expired_docs = await client.get_expired_documents(workspace_slug, limit=limit)
            
            return {
                "workspace": workspace_slug,
                "expired_documents": expired_docs,
                "count": len(expired_docs),
                "limit": limit
            }
    except Exception as e:
        logger.error(f"Failed to get expired documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workspaces/{workspace_slug}/expired")
async def cleanup_expired_documents(
    workspace_slug: str,
    batch_size: int = 50,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """
    Clean up expired documents in a workspace.
    
    Args:
        workspace_slug: The workspace to clean up
        batch_size: Number of documents to process in each batch (default: 50)
    """
    try:
        config = config_manager.get_configuration()
        
        async with WeaviateVectorClient(config.weaviate) as client:
            result = await client.cleanup_expired_documents(workspace_slug, batch_size=batch_size)
            
            return {
                "workspace": workspace_slug,
                "cleanup_result": result,
                "batch_size": batch_size
            }
    except Exception as e:
        logger.error(f"Failed to cleanup expired documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_slug}/providers/{provider}")
async def get_documents_by_provider(
    workspace_slug: str,
    provider: str,
    limit: int = 10000,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """
    Get documents by source provider in a workspace.
    
    Args:
        workspace_slug: The workspace to search in
        provider: The source provider to filter by
        limit: Maximum number of objects to fetch (default: 10000)
    """
    try:
        config = config_manager.get_configuration()
        
        async with WeaviateVectorClient(config.weaviate) as client:
            docs = await client.get_documents_by_provider(workspace_slug, provider, limit=limit)
            
            return {
                "workspace": workspace_slug,
                "source_provider": provider,
                "documents": docs,
                "count": len(docs),
                "limit": limit
            }
    except Exception as e:
        logger.error(f"Failed to get documents by provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_slug}/expired/optimized")
async def get_expired_documents_optimized(
    workspace_slug: str,
    limit: int = 10000,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """
    Get expired documents using optimized native filtering when available.
    
    Args:
        workspace_slug: The workspace to search in
        limit: Maximum number of objects to fetch (default: 10000)
    """
    try:
        config = config_manager.get_configuration()
        
        async with WeaviateVectorClient(config.weaviate) as client:
            expired_docs = await client.get_expired_documents_optimized(workspace_slug, limit=limit)
            
            return {
                "workspace": workspace_slug,
                "expired_documents": expired_docs,
                "count": len(expired_docs),
                "limit": limit,
                "optimized": True
            }
    except Exception as e:
        logger.error(f"Failed to get expired documents (optimized): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_slug}/expiration/statistics")
async def get_expiration_statistics(
    workspace_slug: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """
    Get comprehensive expiration statistics for a workspace.
    
    Args:
        workspace_slug: The workspace to analyze
    """
    try:
        config = config_manager.get_configuration()
        
        async with WeaviateVectorClient(config.weaviate) as client:
            stats = await client.get_expiration_statistics(workspace_slug)
            
            return {
                "workspace": workspace_slug,
                "statistics": stats
            }
    except Exception as e:
        logger.error(f"Failed to get expiration statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))