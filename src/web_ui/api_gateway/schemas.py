"""Pydantic schemas for API Gateway endpoints."""

from pydantic import BaseModel
from typing import Optional, Dict, Any

class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str

class StatsResponse(BaseModel):
    """Schema for system statistics response."""
    uptime: float
    active_users: int
    additional_stats: Optional[Dict[str, Any]]

class ConfigResponse(BaseModel):
    """Schema for configuration response."""
    config: Dict[str, Any]

class ContentResponse(BaseModel):
    """Schema for content response."""
    content: Dict[str, Any]