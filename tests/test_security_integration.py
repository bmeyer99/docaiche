"""
Test Security Integration with MCP Server
========================================

Integration tests to verify security middleware works with the MCP server.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from mcp.server import MCPServer
from mcp.config import MCPServerConfig
from mcp.schemas import MCPRequest, MCPResponse
from mcp.exceptions import RateLimitError, SecurityError


@pytest.fixture
async def server():
    """Create MCP server with security enabled."""
    config = MCPServerConfig()
    config.rate_limit_max_requests = 5  # Low limit for testing
    config.rate_limit_burst_size = 2
    config.max_auth_failures = 3
    config.require_authentication = False  # Simplify for testing
    
    server = MCPServer(config)
    await server._initialize_services()
    
    yield server
    
    # Cleanup
    if server.security_auditor:
        await server.security_auditor.close()


class TestSecurityIntegration:
    """Test security features integrated with MCP server."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, server):
        """Test that rate limiting is enforced on requests."""
        # Create a mock transport
        transport = Mock()
        transport.connection_id = "test-connection"
        
        # Make requests up to the burst limit
        for i in range(2):
            request = MCPRequest(
                id=f"test-{i}",
                method="tools/list",
                params={}
            )
            
            response = await server._handle_transport_message(request, transport)
            assert response.error is None
            assert response.result is not None
        
        # Third request should be rate limited
        request = MCPRequest(
            id="test-3",
            method="tools/list",
            params={}
        )
        
        response = await server._handle_transport_message(request, transport)
        assert response.error is not None
        assert response.error.code == -32005  # RATE_LIMIT_EXCEEDED
        assert "retry_after" in response.error.data
    
    @pytest.mark.asyncio
    async def test_threat_detection(self, server):
        """Test that SQL injection attempts are blocked."""
        transport = Mock()
        transport.connection_id = "test-connection"
        
        # Initialize session first
        init_request = MCPRequest(
            id="init-1",
            method="initialize",
            params={
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        )
        
        response = await server._handle_transport_message(init_request, transport)
        assert response.error is None
        
        # Try SQL injection
        malicious_request = MCPRequest(
            id="mal-1",
            method="tools/call",
            params={
                "name": "search",
                "arguments": {
                    "query": "'; DROP TABLE documents; --"
                }
            }
        )
        
        response = await server._handle_transport_message(malicious_request, transport)
        assert response.error is not None
        assert response.error.code == -32003  # FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_security_status_endpoint(self, server):
        """Test security status endpoint."""
        transport = Mock()
        transport.connection_id = "test-connection"
        
        # Initialize first
        init_request = MCPRequest(
            id="init-1",
            method="initialize",
            params={
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        )
        
        await server._handle_transport_message(init_request, transport)
        
        # Get security status
        status_request = MCPRequest(
            id="status-1",
            method="security/status",
            params={}
        )
        
        response = await server._handle_transport_message(status_request, transport)
        assert response.error is None
        assert response.result is not None
        assert "threat_score" in response.result
        assert "rate_limit_violations" in response.result
        assert "is_locked" in response.result
    
    @pytest.mark.asyncio
    async def test_consent_management(self, server):
        """Test consent grant and revoke."""
        transport = Mock()
        transport.connection_id = "test-connection"
        
        # Initialize first
        init_request = MCPRequest(
            id="init-1",
            method="initialize",
            params={
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        )
        
        await server._handle_transport_message(init_request, transport)
        
        # Grant consent
        grant_request = MCPRequest(
            id="grant-1",
            method="security/grant_consent",
            params={
                "operation": "ingest/document",
                "duration_hours": 24
            }
        )
        
        response = await server._handle_transport_message(grant_request, transport)
        assert response.error is None
        assert response.result["granted"] is True
        consent_id = response.result["consent_id"]
        
        # Check status shows active consent
        status_request = MCPRequest(
            id="status-2",
            method="security/status",
            params={}
        )
        
        response = await server._handle_transport_message(status_request, transport)
        assert "ingest/document" in response.result["active_consents"]
        
        # Revoke consent
        revoke_request = MCPRequest(
            id="revoke-1",
            method="security/revoke_consent",
            params={
                "operation": "ingest/document"
            }
        )
        
        response = await server._handle_transport_message(revoke_request, transport)
        assert response.error is None
        assert response.result["revoked"] is True
        
        # Check consent is gone
        response = await server._handle_transport_message(status_request, transport)
        assert "ingest/document" not in response.result.get("active_consents", [])
    
    @pytest.mark.asyncio
    async def test_security_metrics(self, server):
        """Test security metrics collection."""
        transport = Mock()
        transport.connection_id = "test-connection"
        
        # Initialize and make some requests
        init_request = MCPRequest(
            id="init-1",
            method="initialize",
            params={
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        )
        
        await server._handle_transport_message(init_request, transport)
        
        # Make a few normal requests
        for i in range(3):
            request = MCPRequest(
                id=f"test-{i}",
                method="ping",
                params={}
            )
            await server._handle_transport_message(request, transport)
        
        # Check metrics
        if server.security_middleware:
            metrics = await server.security_middleware.get_metrics()
            
            assert metrics["total_requests"] > 0
            assert metrics["blocked_requests"] >= 0
            assert metrics["active_clients"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])