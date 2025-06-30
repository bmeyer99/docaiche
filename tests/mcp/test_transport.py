"""
Unit tests for MCP Transport Layer
==================================

Tests for Streamable HTTP transport with protocol negotiation,
connection management, and fallback mechanisms.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.mcp.transport.streamable_http import (
    StreamableHTTPTransport,
    StreamableHTTPMessage,
    ConnectionManager,
    ConnectionState,
    TransportError,
    ProtocolNegotiator,
    CircuitBreaker,
    CircuitState
)
from src.mcp.schemas import MCPRequest, MCPResponse


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def circuit_breaker(self):
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
            expected_exception=Exception
        )
    
    @pytest.mark.asyncio
    async def test_circuit_closed_allows_calls(self, circuit_breaker):
        """Test that closed circuit allows calls through."""
        async def success_call():
            return "success"
        
        result = await circuit_breaker.call(success_call)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test that circuit opens after failure threshold."""
        async def failing_call():
            raise Exception("Test failure")
        
        # First failures should go through
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Circuit should now be open
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Further calls should fail immediately
        with pytest.raises(Exception) as exc_info:
            await circuit_breaker.call(failing_call)
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_recovery(self, circuit_breaker):
        """Test circuit recovery through half-open state."""
        async def failing_call():
            raise Exception("Test failure")
        
        async def success_call():
            return "success"
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_call)
        
        # Simulate time passing (would need to mock time in real implementation)
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=6)
        
        # Next call should try half-open
        result = await circuit_breaker.call(success_call)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_resets_on_success(self, circuit_breaker):
        """Test that successful calls reset the failure count."""
        async def sometimes_failing(should_fail):
            if should_fail:
                raise Exception("Test failure")
            return "success"
        
        # Some failures
        for i in range(2):
            with pytest.raises(Exception):
                await circuit_breaker.call(lambda: sometimes_failing(True))
        
        # Success should reset
        result = await circuit_breaker.call(lambda: sometimes_failing(False))
        assert result == "success"
        assert circuit_breaker.failure_count == 0


class TestProtocolNegotiator:
    """Test protocol negotiation."""
    
    @pytest.fixture
    def negotiator(self):
        return ProtocolNegotiator()
    
    @pytest.mark.asyncio
    async def test_negotiate_http2_success(self, negotiator):
        """Test successful HTTP/2 negotiation."""
        mock_connection = Mock()
        mock_connection.can_use_http2 = AsyncMock(return_value=True)
        
        protocol = await negotiator.negotiate(
            connection=mock_connection,
            preferred_protocols=["http/2", "http/1.1"]
        )
        
        assert protocol == "http/2"
    
    @pytest.mark.asyncio
    async def test_fallback_to_http1(self, negotiator):
        """Test fallback to HTTP/1.1 when HTTP/2 unavailable."""
        mock_connection = Mock()
        mock_connection.can_use_http2 = AsyncMock(return_value=False)
        mock_connection.can_use_http1 = AsyncMock(return_value=True)
        
        protocol = await negotiator.negotiate(
            connection=mock_connection,
            preferred_protocols=["http/2", "http/1.1"]
        )
        
        assert protocol == "http/1.1"
    
    @pytest.mark.asyncio
    async def test_websocket_upgrade(self, negotiator):
        """Test WebSocket protocol upgrade."""
        mock_connection = Mock()
        mock_connection.can_upgrade_websocket = AsyncMock(return_value=True)
        
        protocol = await negotiator.negotiate(
            connection=mock_connection,
            preferred_protocols=["websocket", "http/1.1"]
        )
        
        assert protocol == "websocket"
    
    @pytest.mark.asyncio
    async def test_no_supported_protocol(self, negotiator):
        """Test error when no protocol is supported."""
        mock_connection = Mock()
        mock_connection.can_use_http2 = AsyncMock(return_value=False)
        mock_connection.can_use_http1 = AsyncMock(return_value=False)
        
        with pytest.raises(TransportError) as exc_info:
            await negotiator.negotiate(
                connection=mock_connection,
                preferred_protocols=["http/2", "http/1.1"]
            )
        assert "No supported protocol" in str(exc_info.value)


class TestConnectionManager:
    """Test connection management."""
    
    @pytest.fixture
    def connection_manager(self):
        return ConnectionManager(
            max_connections=10,
            connection_timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_create_connection(self, connection_manager):
        """Test creating a new connection."""
        connection = await connection_manager.create_connection(
            client_id="test_client",
            endpoint="http://localhost:8080"
        )
        
        assert connection.client_id == "test_client"
        assert connection.endpoint == "http://localhost:8080"
        assert connection.state == ConnectionState.CONNECTED
        assert "test_client" in connection_manager.connections
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self, connection_manager):
        """Test connection reuse from pool."""
        # Create first connection
        conn1 = await connection_manager.create_connection(
            client_id="test_client",
            endpoint="http://localhost:8080"
        )
        
        # Request same connection
        conn2 = await connection_manager.get_connection("test_client")
        
        assert conn1 is conn2
        assert len(connection_manager.connections) == 1
    
    @pytest.mark.asyncio
    async def test_max_connections_limit(self, connection_manager):
        """Test enforcement of maximum connections limit."""
        # Create max connections
        for i in range(10):
            await connection_manager.create_connection(
                client_id=f"client_{i}",
                endpoint="http://localhost:8080"
            )
        
        # Next connection should fail
        with pytest.raises(TransportError) as exc_info:
            await connection_manager.create_connection(
                client_id="client_11",
                endpoint="http://localhost:8080"
            )
        assert "Maximum connections" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_connection_health_check(self, connection_manager):
        """Test connection health checking."""
        connection = await connection_manager.create_connection(
            client_id="test_client",
            endpoint="http://localhost:8080"
        )
        
        # Mock health check
        connection.is_healthy = AsyncMock(return_value=True)
        
        is_healthy = await connection_manager.check_connection_health("test_client")
        assert is_healthy is True
        connection.is_healthy.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_connection(self, connection_manager):
        """Test closing connections."""
        connection = await connection_manager.create_connection(
            client_id="test_client",
            endpoint="http://localhost:8080"
        )
        
        await connection_manager.close_connection("test_client")
        
        assert "test_client" not in connection_manager.connections
        assert connection.state == ConnectionState.CLOSED
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, connection_manager):
        """Test connection timeout handling."""
        connection = await connection_manager.create_connection(
            client_id="test_client",
            endpoint="http://localhost:8080"
        )
        
        # Simulate timeout
        connection.last_activity = datetime.now() - timedelta(seconds=31)
        
        # Check for timeouts
        await connection_manager.cleanup_stale_connections()
        
        assert "test_client" not in connection_manager.connections


class TestStreamableHTTPTransport:
    """Test StreamableHTTPTransport functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock aiohttp session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def transport(self, mock_session):
        with patch('src.mcp.transport.streamable_http.aiohttp_available', True):
            transport = StreamableHTTPTransport(
                endpoint="http://localhost:8080",
                session=mock_session
            )
            return transport
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, transport, mock_session):
        """Test successful request sending."""
        request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={"query": "test"}
        )
        
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": {"answer": "test result"}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.post.return_value = mock_response
        
        response = await transport.send_request(request)
        
        assert response.id == "test-123"
        assert response.result == {"answer": "test result"}
        assert response.error is None
    
    @pytest.mark.asyncio
    async def test_send_request_with_retry(self, transport, mock_session):
        """Test request retry on failure."""
        request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={"query": "test"}
        )
        
        # First call fails, second succeeds
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        mock_response_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
        mock_response_fail.__aexit__ = AsyncMock(return_value=None)
        
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": {"answer": "test result"}
        })
        mock_response_success.__aenter__ = AsyncMock(return_value=mock_response_success)
        mock_response_success.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.post.side_effect = [mock_response_fail, mock_response_success]
        
        response = await transport.send_request(request)
        
        assert response.id == "test-123"
        assert response.result == {"answer": "test result"}
        assert mock_session.post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, transport, mock_session):
        """Test handling streaming responses."""
        request = MCPRequest(
            id="test-123",
            method="resource/read",
            params={"stream": True}
        )
        
        # Mock streaming response
        chunks = [
            b'{"chunk":1}',
            b'{"chunk":2}',
            b'{"chunk":3}'
        ]
        
        async def chunk_generator():
            for chunk in chunks:
                yield chunk
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.iter_chunked = lambda size: chunk_generator()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.post.return_value = mock_response
        
        # Collect streamed chunks
        received_chunks = []
        async for chunk in transport.stream_request(request):
            received_chunks.append(chunk)
        
        assert len(received_chunks) == 3
        assert all(isinstance(chunk, dict) for chunk in received_chunks)
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, transport, mock_session):
        """Test handling of connection errors."""
        request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={"query": "test"}
        )
        
        # Mock connection error
        mock_session.post.side_effect = ConnectionError("Connection refused")
        
        with pytest.raises(TransportError) as exc_info:
            await transport.send_request(request)
        
        assert "Connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, transport, mock_session):
        """Test request timeout handling."""
        request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={"query": "test"}
        )
        
        # Mock timeout
        mock_session.post.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(TransportError) as exc_info:
            await transport.send_request(request, timeout=5)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_protocol_negotiation(self, transport):
        """Test transport protocol negotiation."""
        # Test initial protocol detection
        await transport.initialize()
        
        assert transport.protocol in ["http/2", "http/1.1", "websocket"]
        assert transport.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_close_transport(self, transport, mock_session):
        """Test proper transport cleanup."""
        await transport.initialize()
        await transport.close()
        
        assert transport.connection_state == ConnectionState.CLOSED
        mock_session.close.assert_called_once()


class TestStreamableHTTPMessage:
    """Test message formatting and parsing."""
    
    def test_create_request_message(self):
        """Test creating request message."""
        request = MCPRequest(
            id="test-123",
            method="tool/execute",
            params={"query": "test"}
        )
        
        message = StreamableHTTPMessage.from_mcp_request(request)
        
        assert message.id == "test-123"
        assert message.method == "tool/execute"
        assert message.params == {"query": "test"}
        assert message.headers["Content-Type"] == "application/json"
    
    def test_create_response_message(self):
        """Test creating response message."""
        response = MCPResponse(
            id="test-123",
            result={"answer": "42"}
        )
        
        message = StreamableHTTPMessage.from_mcp_response(response)
        
        assert message.id == "test-123"
        assert message.result == {"answer": "42"}
        assert message.error is None
    
    def test_parse_json_rpc_response(self):
        """Test parsing JSON-RPC response."""
        json_data = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": {"data": "test"}
        }
        
        message = StreamableHTTPMessage.parse_json_rpc(json_data)
        
        assert message.id == "test-123"
        assert message.result == {"data": "test"}
        assert message.error is None
    
    def test_parse_error_response(self):
        """Test parsing error response."""
        json_data = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            }
        }
        
        message = StreamableHTTPMessage.parse_json_rpc(json_data)
        
        assert message.id == "test-123"
        assert message.result is None
        assert message.error["code"] == -32600
        assert message.error["message"] == "Invalid Request"


# Integration test fixtures
@pytest.fixture
def mock_transport_dependencies():
    """Create mock dependencies for transport."""
    return {
        "session": AsyncMock(),
        "connection_manager": Mock(spec=ConnectionManager),
        "circuit_breaker": Mock(spec=CircuitBreaker)
    }


@pytest.mark.asyncio
async def test_transport_with_circuit_breaker(mock_transport_dependencies):
    """Test transport with circuit breaker integration."""
    with patch('src.mcp.transport.streamable_http.aiohttp_available', True):
        transport = StreamableHTTPTransport(
            endpoint="http://localhost:8080",
            session=mock_transport_dependencies["session"],
            enable_circuit_breaker=True
        )
        
        # Simulate multiple failures
        mock_transport_dependencies["session"].post.side_effect = [
            ConnectionError("Failed"),
            ConnectionError("Failed"),
            ConnectionError("Failed"),
        ]
        
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"query": "test"}
        )
        
        # First 3 failures should go through
        for i in range(3):
            with pytest.raises(TransportError):
                await transport.send_request(request)
        
        # Circuit should now be open
        with pytest.raises(TransportError) as exc_info:
            await transport.send_request(request)
        assert "Circuit breaker" in str(exc_info.value)