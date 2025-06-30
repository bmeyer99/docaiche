"""
MCP Router
==========

Main FastAPI router for MCP (Model Context Protocol) endpoints.
Handles JSON-RPC 2.0 requests from AI agents.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from .handlers import MCPHandler

logger = logging.getLogger(__name__)

# Create the MCP router
router = APIRouter(
    prefix="/mcp",
    tags=["MCP - Model Context Protocol"],
    responses={
        200: {"description": "Successful MCP response"},
        400: {"description": "Invalid JSON-RPC request"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "/",
    summary="MCP JSON-RPC Endpoint",
    description="""
    Main endpoint for MCP (Model Context Protocol) requests.
    
    Accepts JSON-RPC 2.0 requests from AI agents to:
    - Execute tools (search, ingest, feedback)
    - Read resources (collections, status)
    
    No authentication required.
    """,
    response_model=Dict[str, Any],
)
async def handle_mcp_request(
    request: Request,
    mcp_handler: MCPHandler = Depends(),
) -> JSONResponse:
    """
    Handle incoming MCP JSON-RPC requests.
    
    Args:
        request: FastAPI request object containing JSON-RPC payload
        mcp_handler: Injected MCP handler
        
    Returns:
        JSON-RPC response
    """
    try:
        # Get request body
        body = await request.json()
        
        # Log incoming request
        logger.info(
            f"MCP request received",
            extra={
                "method": body.get("method"),
                "id": body.get("id"),
            }
        )
        
        # Handle the request
        response = await mcp_handler.handle(body)
        
        # Return JSON-RPC response
        return JSONResponse(content=response)
        
    except ValueError as e:
        # Invalid JSON
        logger.error(f"Invalid JSON in MCP request: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                },
                "id": None
            }
        )
    except Exception as e:
        # Internal error
        logger.error(f"MCP request failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                },
                "id": body.get("id") if "body" in locals() else None
            }
        )


@router.get(
    "/",
    summary="MCP Information",
    description="Get information about available MCP tools and resources",
)
async def get_mcp_info() -> Dict[str, Any]:
    """
    Return information about available MCP tools and resources.
    
    This is a convenience endpoint for discovery, not part of MCP spec.
    """
    return {
        "protocol": "MCP (Model Context Protocol)",
        "version": "2025-03-26",
        "tools": [
            {
                "name": "docaiche/search",
                "description": "Search documentation with intelligent ranking"
            },
            {
                "name": "docaiche/ingest",
                "description": "Ingest new documentation"
            },
            {
                "name": "docaiche/feedback",
                "description": "Submit feedback on search results or documents"
            }
        ],
        "resources": [
            {
                "uri": "docaiche://collections",
                "description": "List available documentation collections"
            },
            {
                "uri": "docaiche://status",
                "description": "Get system status and health information"
            }
        ],
        "authentication": "None required"
    }