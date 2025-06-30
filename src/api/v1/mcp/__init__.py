"""
MCP (Model Context Protocol) Integration for DocaiChe
=====================================================

Direct integration of MCP functionality into the FastAPI application.
Provides AI agents with tools and resources for documentation access.
"""

from .router import router

__all__ = ["router"]