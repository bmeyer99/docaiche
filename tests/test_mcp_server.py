"""
Unit Tests for MCP Server Integration
=====================================

Comprehensive test suite for the integrated MCP server implementation.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestMCPServerIntegration(unittest.TestCase):
    """Test MCP server integration functionality."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.server import MCPServer
        from src.mcp.config import MCPServerConfig, MCPTransportConfig
        
        # Create test configuration
        self.config = MCPServerConfig(
            server_name="Test MCP Server",
            require_authentication=False,
            transport_config=MCPTransportConfig(
                bind_host="localhost",
                bind_port=3001
            )
        )
        
        self.server = MCPServer(self.config)
    
    async def test_server_initialization(self):
        """Test server initialization."""
        # Verify initial state
        self.assertFalse(self.server.is_running)
        self.assertEqual(len(self.server.tools), 0)
        self.assertEqual(len(self.server.resources), 0)
        self.assertEqual(len(self.server.transports), 0)
        
        # Verify metadata
        self.assertEqual(self.server.metadata.name, "DocaiChe MCP Server")
        self.assertEqual(self.server.metadata.protocol_version, "2025-03-26")
    
    async def test_component_registration(self):
        """Test tool and resource registration."""
        from src.mcp.tools.base_tool import BaseTool, ToolMetadata
        from src.mcp.resources.base_resource import BaseResource, ResourceMetadata
        from src.mcp.schemas import ToolDefinition, ResourceDefinition
        
        # Create mock tool
        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_tool_definition.return_value = ToolDefinition(
            name="test_tool",
            description="Test tool",
            inputSchema={}
        )
        
        # Register tool
        self.server.register_tool(mock_tool)
        self.assertIn("test_tool", self.server.tools)
        self.assertEqual(self.server.tools["test_tool"], mock_tool)
        
        # Create mock resource
        mock_resource = Mock(spec=BaseResource)
        mock_resource.get_resource_definition.return_value = ResourceDefinition(
            name="test_resource",
            description="Test resource",
            uri="test://resource"
        )
        
        # Register resource
        self.server.register_resource(mock_resource)
        self.assertIn("test_resource", self.server.resources)
        self.assertEqual(self.server.resources["test_resource"], mock_resource)
    
    async def test_session_management(self):
        """Test client session management."""
        from src.mcp.schemas import MCPRequest
        from src.mcp.transport.base_transport import BaseTransport
        
        # Create mock transport
        mock_transport = Mock(spec=BaseTransport)
        mock_transport.connection_id = "test_connection"
        
        # Create request
        request = MCPRequest(
            id="req-1",
            method="test",
            params={}
        )
        
        # Get or create session
        session = await self.server._get_or_create_session(request, mock_transport)
        
        # Verify session
        self.assertIsNotNone(session)
        self.assertTrue(session.session_id.startswith("session_"))
        self.assertFalse(session.initialized)
        self.assertFalse(session.authenticated)
        
        # Verify session is stored
        self.assertIn(session.session_id, self.server.sessions)
        
        # Get same session again
        session2 = await self.server._get_or_create_session(request, mock_transport)
        self.assertEqual(session.session_id, session2.session_id)
    
    async def test_initialize_handler(self):
        """Test initialize request handling."""
        from src.mcp.schemas import MCPRequest
        from src.mcp.server import ClientSession
        
        # Create session
        session = ClientSession(
            session_id="test_session",
            client_info={}
        )
        
        # Create initialize request
        request = MCPRequest(
            id="init-1",
            method="initialize",
            params={
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "Test Client",
                    "version": "1.0.0"
                }
            }
        )
        
        # Handle initialize
        response = await self.server._handle_initialize(request, session)
        
        # Verify response
        self.assertIsNotNone(response)
        self.assertIn("result", response.dict())
        result = response.dict()["result"]
        
        self.assertEqual(result["protocolVersion"], "2025-03-26")
        self.assertIn("capabilities", result)
        self.assertIn("serverInfo", result)
        self.assertEqual(result["sessionId"], "test_session")
        
        # Verify session state
        self.assertTrue(session.initialized)
        self.assertEqual(session.client_info["name"], "Test Client")
    
    async def test_tools_list_handler(self):
        """Test tools/list request handling."""
        from src.mcp.schemas import MCPRequest, ToolDefinition
        from src.mcp.server import ClientSession
        from src.mcp.tools.base_tool import BaseTool
        
        # Create mock tools
        mock_tool1 = Mock(spec=BaseTool)
        mock_tool1.get_tool_definition.return_value = ToolDefinition(
            name="tool1",
            description="Tool 1",
            inputSchema={"type": "object"}
        )
        
        mock_tool2 = Mock(spec=BaseTool)
        mock_tool2.get_tool_definition.return_value = ToolDefinition(
            name="tool2",
            description="Tool 2",
            inputSchema={"type": "object"}
        )
        
        # Register tools
        self.server.register_tool(mock_tool1)
        self.server.register_tool(mock_tool2)
        
        # Create request
        request = MCPRequest(
            id="list-1",
            method="tools/list",
            params={}
        )
        
        session = ClientSession(
            session_id="test_session",
            client_info={},
            initialized=True
        )
        
        # Handle request
        response = await self.server._handle_tools_list(request, session)
        
        # Verify response
        result = response.dict()["result"]
        self.assertIn("tools", result)
        self.assertEqual(len(result["tools"]), 2)
        
        tool_names = [t["name"] for t in result["tools"]]
        self.assertIn("tool1", tool_names)
        self.assertIn("tool2", tool_names)
    
    async def test_tool_execution(self):
        """Test tool execution handling."""
        from src.mcp.schemas import MCPRequest, MCPResponse
        from src.mcp.server import ClientSession
        from src.mcp.tools.base_tool import BaseTool
        
        # Create mock tool
        mock_tool = Mock(spec=BaseTool)
        mock_tool.execute = AsyncMock(return_value=MCPResponse(
            id="tool-resp-1",
            result={"status": "success", "data": "test"}
        ))
        
        self.server.tools["test_tool"] = mock_tool
        
        # Create request
        request = MCPRequest(
            id="exec-1",
            method="tools/call",
            params={
                "name": "test_tool",
                "arguments": {"param1": "value1"}
            }
        )
        
        session = ClientSession(
            session_id="test_session",
            client_info={},
            initialized=True
        )
        
        # Handle request
        response = await self.server._handle_tools_call(request, session)
        
        # Verify tool was called
        mock_tool.execute.assert_called_once()
        call_args = mock_tool.execute.call_args
        self.assertEqual(call_args[0][0].params, {"param1": "value1"})
    
    async def test_resource_read_handler(self):
        """Test resource read handling."""
        from src.mcp.schemas import MCPRequest
        from src.mcp.server import ClientSession
        from src.mcp.resources.base_resource import BaseResource
        
        # Create mock resource
        mock_resource = Mock(spec=BaseResource)
        mock_resource.can_handle_uri.return_value = True
        mock_resource.fetch_resource = AsyncMock(return_value={
            "mimeType": "application/json",
            "text": json.dumps({"test": "data"})
        })
        
        self.server.resources["test_resource"] = mock_resource
        
        # Create request
        request = MCPRequest(
            id="read-1",
            method="resources/read",
            params={"uri": "test://resource/path"}
        )
        
        session = ClientSession(
            session_id="test_session",
            client_info={},
            initialized=True
        )
        
        # Handle request
        response = await self.server._handle_resources_read(request, session)
        
        # Verify response
        result = response.dict()["result"]
        self.assertIn("contents", result)
        self.assertEqual(len(result["contents"]), 1)
        
        content = result["contents"][0]
        self.assertEqual(content["uri"], "test://resource/path")
        self.assertEqual(content["mimeType"], "application/json")
        self.assertIn("text", content)
    
    async def test_error_handling(self):
        """Test error handling in request processing."""
        from src.mcp.schemas import MCPRequest
        from src.mcp.server import ClientSession
        from src.mcp.exceptions import ValidationError
        
        # Create request for unknown method
        request = MCPRequest(
            id="err-1",
            method="unknown/method",
            params={}
        )
        
        session = ClientSession(
            session_id="test_session",
            client_info={},
            initialized=True
        )
        
        # Mock transport
        mock_transport = Mock()
        
        # Handle request
        response = await self.server._handle_transport_message(request, mock_transport)
        
        # Verify error response
        self.assertIn("error", response.dict())
        error = response.dict()["error"]
        self.assertEqual(error["code"], -32602)  # Invalid params
        self.assertIn("Unknown method", error["message"])
    
    async def test_shutdown_handling(self):
        """Test shutdown request handling."""
        from src.mcp.schemas import MCPRequest
        from src.mcp.server import ClientSession
        
        # Create request
        request = MCPRequest(
            id="shutdown-1",
            method="shutdown",
            params={}
        )
        
        session = ClientSession(
            session_id="test_session",
            client_info={},
            initialized=True
        )
        
        # Handle request
        response = await self.server._handle_shutdown(request, session)
        
        # Verify response
        result = response.dict()["result"]
        self.assertEqual(result["status"], "shutting_down")
    
    async def test_ping_handler(self):
        """Test ping request handling."""
        from src.mcp.schemas import MCPRequest
        from src.mcp.server import ClientSession
        
        # Create request
        request = MCPRequest(
            id="ping-1",
            method="ping",
            params={}
        )
        
        session = ClientSession(
            session_id="test_session",
            client_info={},
            initialized=True
        )
        
        # Handle request
        response = await self.server._handle_ping(request, session)
        
        # Verify response
        result = response.dict()["result"]
        self.assertTrue(result["pong"])
        self.assertIn("timestamp", result)
    
    async def test_logging_level_handler(self):
        """Test logging level setting."""
        from src.mcp.schemas import MCPRequest
        from src.mcp.server import ClientSession
        import logging
        
        # Create request
        request = MCPRequest(
            id="log-1",
            method="logging/setLevel",
            params={"level": "debug"}
        )
        
        session = ClientSession(
            session_id="test_session",
            client_info={},
            initialized=True
        )
        
        # Handle request
        response = await self.server._handle_logging_set_level(request, session)
        
        # Verify response
        result = response.dict()["result"]
        self.assertEqual(result["level"], "debug")
        
        # Verify logging level was set
        self.assertEqual(logging.getLogger().level, logging.DEBUG)


class TestServerLifecycle(unittest.TestCase):
    """Test server lifecycle management."""
    
    @patch('src.mcp.server.StreamableHTTPTransportV2')
    @patch('src.mcp.server.SecurityAuditor')
    async def test_server_start_stop(self, mock_auditor_class, mock_transport_class):
        """Test server start and stop lifecycle."""
        from src.mcp.server import MCPServer
        from src.mcp.config import MCPServerConfig
        
        # Setup mocks
        mock_auditor = AsyncMock()
        mock_auditor_class.return_value = mock_auditor
        
        mock_transport = AsyncMock()
        mock_transport_class.return_value = mock_transport
        
        # Create server
        config = MCPServerConfig(require_authentication=False)
        server = MCPServer(config)
        
        # Start server in background
        start_task = asyncio.create_task(server.start())
        
        # Wait a bit for startup
        await asyncio.sleep(0.1)
        
        # Verify server is running
        self.assertTrue(server.is_running)
        self.assertEqual(len(server.transports), 1)
        
        # Verify transport was started
        mock_transport.connect.assert_called_once()
        mock_transport.start_listening.assert_called_once()
        
        # Stop server
        await server.stop()
        
        # Verify server stopped
        self.assertFalse(server.is_running)
        mock_transport.disconnect.assert_called_once()
        
        # Cancel start task
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    # Run async tests properly
    def async_test(f):
        def wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(f(*args, **kwargs))
            finally:
                loop.close()
        return wrapper
    
    # Patch all async test methods
    for test_class in [TestMCPServerIntegration, TestServerLifecycle]:
        for attr_name in dir(test_class):
            if attr_name.startswith('test_'):
                attr = getattr(test_class, attr_name)
                if asyncio.iscoroutinefunction(attr):
                    setattr(test_class, attr_name, async_test(attr))
    
    unittest.main()