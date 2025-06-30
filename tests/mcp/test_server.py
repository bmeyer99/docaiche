"""
System tests for MCP Server
===========================

End-to-end tests for the complete MCP server implementation,
including integration with all components.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.mcp.server import MCPServer
from src.mcp.schemas import MCPRequest, MCPResponse
from src.mcp.transport.streamable_http import StreamableHTTPTransport
from src.mcp.auth.oauth_handler import OAuth21Handler
from src.mcp.security.security_manager import SecurityManager
from src.mcp.tools.registry import ToolRegistry
from src.mcp.resources.registry import ResourceRegistry


class TestMCPServerIntegration:
    """Test MCP server integration."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for server."""
        deps = {
            "transport": Mock(spec=StreamableHTTPTransport),
            "auth_handler": Mock(spec=OAuth21Handler),
            "security_manager": Mock(spec=SecurityManager),
            "tool_registry": Mock(spec=ToolRegistry),
            "resource_registry": Mock(spec=ResourceRegistry),
            "api_client": AsyncMock()
        }
        
        # Setup default behaviors
        deps["transport"].initialize = AsyncMock()
        deps["transport"].close = AsyncMock()
        deps["transport"].receive_request = AsyncMock()
        deps["transport"].send_response = AsyncMock()
        
        deps["auth_handler"].authorize_request = AsyncMock(return_value={
            "authenticated": True,
            "client_id": "test_client",
            "scopes": ["read", "write"]
        })
        
        deps["security_manager"].enforce_security = AsyncMock(return_value={
            "allowed": True,
            "violations": []
        })
        
        return deps
    
    @pytest.fixture
    def mcp_server(self, mock_dependencies):
        """Create MCP server with mocked dependencies."""
        server = MCPServer(
            transport=mock_dependencies["transport"],
            auth_handler=mock_dependencies["auth_handler"],
            security_manager=mock_dependencies["security_manager"],
            tool_registry=mock_dependencies["tool_registry"],
            resource_registry=mock_dependencies["resource_registry"],
            api_client=mock_dependencies["api_client"]
        )
        return server
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_server):
        """Test server initialization."""
        await mcp_server.initialize()
        
        assert mcp_server.is_running is False
        mcp_server.transport.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_tool_request(self, mcp_server, mock_dependencies):
        """Test handling tool execution request."""
        request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={
                "tool": "docaiche_search",
                "arguments": {
                    "query": "machine learning"
                }
            }
        )
        
        # Mock tool execution
        mock_tool = AsyncMock()
        mock_tool.execute.return_value = {
            "results": [{"id": "1", "title": "ML Guide"}],
            "total": 1
        }
        mock_dependencies["tool_registry"].get_tool.return_value = mock_tool
        
        response = await mcp_server.handle_request(request, auth_context={
            "authenticated": True,
            "client_id": "test_client"
        })
        
        assert response.id == "test-123"
        assert response.result is not None
        assert response.result["results"][0]["title"] == "ML Guide"
        mock_tool.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_resource_request(self, mcp_server, mock_dependencies):
        """Test handling resource access request."""
        request = MCPRequest(
            id="test-456",
            method="resource/list",
            params={
                "resource": "collections"
            }
        )
        
        # Mock resource handler
        mock_resource = AsyncMock()
        mock_resource.list.return_value = {
            "collections": [
                {"id": "1", "name": "PyTorch Docs"}
            ],
            "total": 1
        }
        mock_dependencies["resource_registry"].get_resource.return_value = mock_resource
        
        response = await mcp_server.handle_request(request, auth_context={
            "authenticated": True,
            "client_id": "test_client"
        })
        
        assert response.id == "test-456"
        assert len(response.result["collections"]) == 1
        mock_resource.list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, mcp_server, mock_dependencies):
        """Test handling of authentication failure."""
        request = MCPRequest(
            id="test-789",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        # Mock auth failure
        mock_dependencies["auth_handler"].authorize_request.side_effect = Exception("Invalid token")
        
        response = await mcp_server.handle_request(request, auth_header="Bearer invalid")
        
        assert response.error is not None
        assert response.error["code"] == -32602  # Invalid params
        assert "authentication" in response.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_security_violation(self, mcp_server, mock_dependencies):
        """Test handling of security violations."""
        request = MCPRequest(
            id="test-999",
            method="tool/execute",
            params={
                "tool": "docaiche_search",
                "arguments": {
                    "query": "'; DROP TABLE users;--"
                }
            }
        )
        
        # Mock security violation
        mock_dependencies["security_manager"].enforce_security.return_value = {
            "allowed": False,
            "reason": "SQL injection detected",
            "violations": ["sql_injection"]
        }
        
        response = await mcp_server.handle_request(request, auth_context={
            "authenticated": True,
            "client_id": "test_client"
        })
        
        assert response.error is not None
        assert "security" in response.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mcp_server, mock_dependencies):
        """Test rate limiting enforcement."""
        request = MCPRequest(
            id="test-rate",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        # Mock rate limit exceeded
        mock_dependencies["security_manager"].enforce_security.return_value = {
            "allowed": False,
            "reason": "Rate limit exceeded",
            "violations": ["rate_limit"]
        }
        
        response = await mcp_server.handle_request(request, auth_context={
            "authenticated": True,
            "client_id": "test_client"
        })
        
        assert response.error is not None
        assert response.error["code"] == -32005  # Rate limit error
        assert "rate limit" in response.error["message"].lower()
    
    @pytest.mark.asyncio
    async def test_request_logging(self, mcp_server, mock_dependencies):
        """Test that requests are properly logged."""
        mock_audit_logger = AsyncMock()
        mcp_server.audit_logger = mock_audit_logger
        
        request = MCPRequest(
            id="test-log",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        await mcp_server.handle_request(request, auth_context={
            "authenticated": True,
            "client_id": "test_client"
        })
        
        # Verify audit logging
        mock_audit_logger.log_request.assert_called_once()
        call_args = mock_audit_logger.log_request.call_args[1]
        assert call_args["request_id"] == "test-log"
        assert call_args["client_id"] == "test_client"
    
    @pytest.mark.asyncio
    async def test_server_lifecycle(self, mcp_server, mock_dependencies):
        """Test server start and stop lifecycle."""
        # Setup transport to simulate receiving requests
        requests = [
            MCPRequest(id="1", method="tool/list", params={}),
            MCPRequest(id="2", method="resource/list", params={})
        ]
        mock_dependencies["transport"].receive_request.side_effect = [
            requests[0],
            requests[1],
            asyncio.CancelledError()  # Simulate shutdown
        ]
        
        # Mock handlers
        mock_dependencies["tool_registry"].list_tools.return_value = []
        mock_dependencies["resource_registry"].list_resources.return_value = []
        
        # Start server
        server_task = asyncio.create_task(mcp_server.start())
        
        # Give server time to process requests
        await asyncio.sleep(0.1)
        
        # Stop server
        await mcp_server.stop()
        
        # Verify server processed requests
        assert mock_dependencies["transport"].receive_request.call_count >= 2
        assert mock_dependencies["transport"].send_response.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, mcp_server, mock_dependencies):
        """Test handling multiple concurrent requests."""
        # Create multiple requests
        requests = [
            MCPRequest(
                id=f"concurrent-{i}",
                method="tool/execute",
                params={
                    "tool": "docaiche_search",
                    "arguments": {"query": f"query {i}"}
                }
            )
            for i in range(5)
        ]
        
        # Mock tool execution with delay
        async def delayed_execute(*args, **kwargs):
            await asyncio.sleep(0.01)  # Small delay
            return {"results": [], "total": 0}
        
        mock_tool = AsyncMock()
        mock_tool.execute.side_effect = delayed_execute
        mock_dependencies["tool_registry"].get_tool.return_value = mock_tool
        
        # Handle requests concurrently
        tasks = [
            mcp_server.handle_request(req, auth_context={
                "authenticated": True,
                "client_id": f"client_{i}"
            })
            for i, req in enumerate(requests)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests were handled
        assert len(responses) == 5
        assert all(r.error is None for r in responses)
        assert mock_tool.execute.call_count == 5


class TestMCPServerErrorHandling:
    """Test server error handling scenarios."""
    
    @pytest.fixture
    def error_server(self, mock_dependencies):
        """Create server for error testing."""
        return MCPServer(
            transport=mock_dependencies["transport"],
            auth_handler=mock_dependencies["auth_handler"],
            security_manager=mock_dependencies["security_manager"]
        )
    
    @pytest.mark.asyncio
    async def test_invalid_method(self, error_server):
        """Test handling of invalid method."""
        request = MCPRequest(
            id="test-invalid",
            method="invalid/method",
            params={}
        )
        
        response = await error_server.handle_request(request)
        
        assert response.error is not None
        assert response.error["code"] == -32601  # Method not found
    
    @pytest.mark.asyncio
    async def test_malformed_request(self, error_server):
        """Test handling of malformed request."""
        # Create request with missing required field
        malformed = {"method": "tool/execute"}  # Missing id
        
        response = await error_server.handle_raw_request(malformed)
        
        assert response["error"]["code"] == -32600  # Invalid request
    
    @pytest.mark.asyncio
    async def test_internal_server_error(self, error_server, mock_dependencies):
        """Test handling of internal server errors."""
        request = MCPRequest(
            id="test-internal",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        # Mock unexpected error
        mock_dependencies["tool_registry"].get_tool.side_effect = RuntimeError("Unexpected error")
        
        response = await error_server.handle_request(request, auth_context={
            "authenticated": True,
            "client_id": "test"
        })
        
        assert response.error is not None
        assert response.error["code"] == -32603  # Internal error
    
    @pytest.mark.asyncio
    async def test_transport_failure_recovery(self, error_server, mock_dependencies):
        """Test recovery from transport failures."""
        # Simulate transport failure then recovery
        mock_dependencies["transport"].send_response.side_effect = [
            ConnectionError("Transport failed"),
            None  # Success on retry
        ]
        
        request = MCPRequest(
            id="test-transport",
            method="tool/list",
            params={}
        )
        
        # Server should retry on transport failure
        await error_server.process_request(request)
        
        # Verify retry occurred
        assert mock_dependencies["transport"].send_response.call_count == 2


class TestMCPServerMetrics:
    """Test server metrics and monitoring."""
    
    @pytest.fixture
    def metrics_server(self, mock_dependencies):
        """Create server with metrics enabled."""
        server = MCPServer(
            transport=mock_dependencies["transport"],
            enable_metrics=True
        )
        return server
    
    @pytest.mark.asyncio
    async def test_request_metrics(self, metrics_server):
        """Test request metrics collection."""
        request = MCPRequest(
            id="test-metrics",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        await metrics_server.handle_request(request)
        
        metrics = metrics_server.get_metrics()
        assert metrics["total_requests"] > 0
        assert "tool/execute" in metrics["requests_by_method"]
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, metrics_server):
        """Test performance metrics collection."""
        # Handle multiple requests
        for i in range(10):
            request = MCPRequest(
                id=f"perf-{i}",
                method="tool/execute",
                params={"tool": "docaiche_search"}
            )
            await metrics_server.handle_request(request)
        
        metrics = metrics_server.get_metrics()
        assert "average_response_time" in metrics
        assert "p95_response_time" in metrics
        assert metrics["average_response_time"] > 0
    
    @pytest.mark.asyncio
    async def test_error_metrics(self, metrics_server):
        """Test error metrics collection."""
        # Generate some errors
        for i in range(5):
            request = MCPRequest(
                id=f"error-{i}",
                method="invalid/method",
                params={}
            )
            await metrics_server.handle_request(request)
        
        metrics = metrics_server.get_metrics()
        assert metrics["total_errors"] >= 5
        assert "-32601" in metrics["errors_by_code"]  # Method not found