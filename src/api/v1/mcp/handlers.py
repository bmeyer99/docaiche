"""
MCP Request Handlers
====================

Handles JSON-RPC 2.0 requests for MCP tools and resources.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import Depends

from ..dependencies import get_search_orchestrator, get_database_manager
from src.database.connection import DatabaseManager
from src.search.orchestrator import SearchOrchestrator

logger = logging.getLogger(__name__)


class MCPHandler:
    """
    Main handler for MCP JSON-RPC requests.
    
    Routes requests to appropriate tools and resources.
    """
    
    def __init__(
        self,
        search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
        db_manager: DatabaseManager = Depends(get_database_manager),
    ):
        """
        Initialize MCP handler with dependencies.
        
        Args:
            search_orchestrator: Search service for document queries
            db_manager: Database access for collections and feedback
        """
        self.search_orchestrator = search_orchestrator
        self.db_manager = db_manager
        
        # Initialize tools (will be populated in next phase)
        self.tools = {}
        
        # Initialize resources (will be populated in next phase)
        self.resources = {}
    
    async def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC request.
        
        Args:
            request: JSON-RPC 2.0 request object
            
        Returns:
            JSON-RPC 2.0 response object
        """
        # Validate JSON-RPC structure
        if not isinstance(request, dict):
            return self._error_response(
                code=-32600,
                message="Invalid Request",
                data="Request must be a JSON object"
            )
        
        # Extract request components
        jsonrpc = request.get("jsonrpc")
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        # Validate JSON-RPC version
        if jsonrpc != "2.0":
            return self._error_response(
                code=-32600,
                message="Invalid Request",
                data="JSON-RPC version must be 2.0",
                request_id=request_id
            )
        
        # Route to appropriate handler
        try:
            if method == "tools/call":
                result = await self._handle_tool_call(params)
            elif method == "resources/read":
                result = await self._handle_resource_read(params)
            elif method == "tools/list":
                result = await self._handle_tools_list()
            elif method == "resources/list":
                result = await self._handle_resources_list()
            else:
                return self._error_response(
                    code=-32601,
                    message="Method not found",
                    data=f"Unknown method: {method}",
                    request_id=request_id
                )
            
            # Return success response
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
            
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return self._error_response(
                code=-32603,
                message="Internal error",
                data=str(e),
                request_id=request_id
            )
    
    async def _handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tools/call method.
        
        Args:
            params: Tool call parameters
            
        Returns:
            Tool execution result
        """
        tool_name = params.get("name")
        if not tool_name:
            raise ValueError("Missing required parameter: name")
        
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        arguments = params.get("arguments", {})
        
        # Execute tool
        return await tool.execute(arguments)
    
    async def _handle_resource_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle resources/read method.
        
        Args:
            params: Resource read parameters
            
        Returns:
            Resource data
        """
        uri = params.get("uri")
        if not uri:
            raise ValueError("Missing required parameter: uri")
        
        # Find matching resource
        resource = None
        for resource_uri, resource_handler in self.resources.items():
            if uri.startswith(resource_uri):
                resource = resource_handler
                break
        
        if not resource:
            raise ValueError(f"Unknown resource: {uri}")
        
        # Read resource
        return await resource.read(uri)
    
    async def _handle_tools_list(self) -> Dict[str, Any]:
        """List available tools."""
        return {
            "tools": [
                {
                    "name": name,
                    "description": tool.description
                }
                for name, tool in self.tools.items()
            ]
        }
    
    async def _handle_resources_list(self) -> Dict[str, Any]:
        """List available resources."""
        return {
            "resources": [
                {
                    "uri": uri,
                    "description": resource.description
                }
                for uri, resource in self.resources.items()
            ]
        }
    
    def _error_response(
        self,
        code: int,
        message: str,
        data: Optional[Any] = None,
        request_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create JSON-RPC error response.
        
        Args:
            code: Error code
            message: Error message
            data: Additional error data
            request_id: Request ID from original request
            
        Returns:
            JSON-RPC error response
        """
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
        
        return {
            "jsonrpc": "2.0",
            "error": error,
            "id": request_id
        }