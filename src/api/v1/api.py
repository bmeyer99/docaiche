"""
API v1 router for AI Documentation Cache System
PRD-001: HTTP API Foundation - Main API Router

This module contains the main API router that will be included in the FastAPI application.
Initially includes basic health endpoint as specified in the task requirements.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

# Create the main API router
api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Basic health endpoint as specified in API-001 task requirements.
    
    Returns:
        Dict[str, Any]: Health status with timestamp and version
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        )