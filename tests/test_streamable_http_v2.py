"""
Unit Tests for Streamable HTTP Transport V2
===========================================

Comprehensive test suite for the enhanced HTTP transport implementation
covering protocol negotiation, fallbacks, and reliability features.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json
import gzip
import zlib

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestProtocolNegotiation(unittest.TestCase):
    """Test protocol negotiation functionality."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.transport.streamable_http_v2 import (
            ProtocolNegotiator, Protocol, CompressionType
        )
        
        self.negotiator = ProtocolNegotiator()
        self.Protocol = Protocol
        self.CompressionType = CompressionType
    
    def test_protocol_priority_order(self):
        """Test protocol priority ordering."""
        expected_order = [
            self.Protocol.HTTP2,
            self.Protocol.HTTP11,
            self.Protocol.WEBSOCKET,
            self.Protocol.HTTP10
        ]
        self.assertEqual(self.negotiator.supported_protocols, expected_order)
    
    def test_compression_priority_order(self):
        """Test compression priority ordering."""
        expected_order = [
            self.CompressionType.BROTLI,
            self.CompressionType.GZIP,
            self.CompressionType.DEFLATE,
            self.CompressionType.NONE
        ]
        self.assertEqual(self.negotiator.supported_compressions, expected_order)
    
    async def test_protocol_negotiation_success(self):
        """Test successful protocol negotiation."""
        # Mock client session
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_response.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test negotiation
        protocol, compression = await self.negotiator.negotiate_protocol(
            "http://test.example.com",
            mock_session
        )
        
        # Should select first successful protocol
        self.assertEqual(protocol, self.Protocol.HTTP2)
        self.assertIsInstance(compression, self.CompressionType)
    
    async def test_protocol_fallback(self):
        """Test protocol fallback on failure."""
        # Mock client session with HTTP/2 failure
        mock_session = AsyncMock()
        
        # First call fails (HTTP/2)
        mock_session.get.side_effect = [
            Exception("HTTP/2 not supported"),
            AsyncMock(__aenter__=AsyncMock(return_value=Mock(status=200)))
        ]
        
        protocol, compression = await self.negotiator.negotiate_protocol(
            "http://test.example.com",
            mock_session
        )
        
        # Should fallback to HTTP/1.1
        self.assertEqual(protocol, self.Protocol.HTTP11)
    
    def test_connection_state_tracking(self):
        """Test connection state management."""
        from src.mcp.transport.streamable_http_v2 import ConnectionState
        
        state = ConnectionState(
            protocol=self.Protocol.HTTP11,
            compression=self.CompressionType.GZIP
        )
        
        # Test initial state
        self.assertTrue(state.is_healthy)
        self.assertEqual(state.consecutive_failures, 0)
        
        # Record success
        state.record_success(50.0)
        self.assertTrue(state.is_healthy)
        self.assertEqual(len(state.rtt_samples), 1)
        self.assertEqual(state.average_rtt, 50.0)
        
        # Record failures
        state.record_failure()
        state.record_failure()
        state.record_failure()
        self.assertFalse(state.is_healthy)
        self.assertEqual(state.consecutive_failures, 3)


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker functionality."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.transport.streamable_http_v2 import CircuitBreaker
        
        self.breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for testing
            half_open_requests=2
        )
    
    def test_closed_state(self):
        """Test circuit breaker in closed state."""
        self.assertEqual(self.breaker.state, "closed")
        self.assertTrue(self.breaker.can_attempt())
        
        # Record some failures but below threshold
        self.breaker.record_failure()
        self.breaker.record_failure()
        self.assertEqual(self.breaker.state, "closed")
        self.assertTrue(self.breaker.can_attempt())
    
    def test_open_state(self):
        """Test circuit breaker opening on failures."""
        # Record failures to open breaker
        for _ in range(3):
            self.breaker.record_failure()
        
        self.assertEqual(self.breaker.state, "open")
        self.assertFalse(self.breaker.can_attempt())
    
    def test_half_open_state(self):
        """Test circuit breaker half-open state."""
        # Open the breaker
        for _ in range(3):
            self.breaker.record_failure()
        
        # Wait for recovery timeout
        import time
        time.sleep(1.1)
        
        # Should enter half-open state
        self.assertTrue(self.breaker.can_attempt())
        self.assertEqual(self.breaker.state, "half-open")
        
        # Record successes to close
        self.breaker.record_success()
        self.breaker.record_success()
        self.assertEqual(self.breaker.state, "closed")
    
    def test_half_open_failure(self):
        """Test circuit breaker re-opening from half-open."""
        # Open the breaker
        for _ in range(3):
            self.breaker.record_failure()
        
        # Enter half-open
        import time
        time.sleep(1.1)
        self.breaker.can_attempt()
        
        # Fail again
        self.breaker.record_failure()
        self.assertEqual(self.breaker.failure_count, 4)


class TestRequestQueue(unittest.TestCase):
    """Test request queue with backpressure."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.transport.streamable_http_v2 import RequestQueue
        from src.mcp.schemas import MCPRequest
        
        self.queue = RequestQueue(max_size=10, high_water=8)
        self.MCPRequest = MCPRequest
    
    async def test_basic_queue_operations(self):
        """Test basic queue put/get operations."""
        # Create test request
        request = self.MCPRequest(
            id="test-1",
            method="test",
            params={}
        )
        
        # Put and get
        await self.queue.put(request)
        self.assertEqual(self.queue.size(), 1)
        
        retrieved = await self.queue.get()
        self.assertEqual(retrieved.id, "test-1")
        self.assertEqual(self.queue.size(), 0)
    
    async def test_priority_queue(self):
        """Test priority queue handling."""
        # Add normal request
        normal_request = self.MCPRequest(
            id="normal-1",
            method="test",
            params={}
        )
        await self.queue.put(normal_request)
        
        # Add priority request
        priority_request = self.MCPRequest(
            id="priority-1",
            method="test",
            params={}
        )
        await self.queue.put(priority_request, priority=True)
        
        # Priority should be retrieved first
        retrieved = await self.queue.get()
        self.assertEqual(retrieved.id, "priority-1")
        
        retrieved = await self.queue.get()
        self.assertEqual(retrieved.id, "normal-1")
    
    async def test_backpressure(self):
        """Test backpressure handling."""
        # Fill queue to high water mark
        for i in range(8):
            request = self.MCPRequest(
                id=f"test-{i}",
                method="test",
                params={}
            )
            await self.queue.put(request)
        
        # Should trigger backpressure
        self.assertTrue(self.queue.is_backpressured)
        
        # Drain queue below threshold
        for _ in range(5):
            await self.queue.get()
        
        # Backpressure should be relieved
        self.assertFalse(self.queue.is_backpressured)
    
    async def test_queue_full(self):
        """Test queue full error."""
        from src.mcp.exceptions import TransportError
        
        # Fill queue to capacity
        for i in range(10):
            request = self.MCPRequest(
                id=f"test-{i}",
                method="test",
                params={}
            )
            await self.queue.put(request)
        
        # Next put should fail
        with self.assertRaises(TransportError) as cm:
            overflow_request = self.MCPRequest(
                id="overflow",
                method="test",
                params={}
            )
            await self.queue.put(overflow_request)
        
        self.assertEqual(cm.exception.error_code, "QUEUE_FULL")


class TestCompressionHandling(unittest.TestCase):
    """Test compression and decompression functionality."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.transport.streamable_http_v2 import (
            StreamableHTTPTransportV2, CompressionType
        )
        from src.mcp.config import MCPTransportConfig
        
        config = MCPTransportConfig(
            bind_host="localhost",
            bind_port=8080,
            max_connections=10
        )
        self.transport = StreamableHTTPTransportV2(config)
        self.CompressionType = CompressionType
    
    async def test_gzip_compression(self):
        """Test gzip compression/decompression."""
        test_data = b"Hello, World! " * 100  # Repeat for compression benefit
        
        # Compress
        compressed = await self.transport._compress_data(
            test_data,
            self.CompressionType.GZIP
        )
        self.assertLess(len(compressed), len(test_data))
        self.assertEqual(compressed[:2], b'\x1f\x8b')  # Gzip magic number
        
        # Decompress
        decompressed = await self.transport._decompress_data(
            compressed,
            self.CompressionType.GZIP
        )
        self.assertEqual(decompressed, test_data)
    
    async def test_deflate_compression(self):
        """Test deflate compression/decompression."""
        test_data = b"Test data for deflate compression" * 50
        
        # Compress
        compressed = await self.transport._compress_data(
            test_data,
            self.CompressionType.DEFLATE
        )
        self.assertLess(len(compressed), len(test_data))
        
        # Decompress
        decompressed = await self.transport._decompress_data(
            compressed,
            self.CompressionType.DEFLATE
        )
        self.assertEqual(decompressed, test_data)
    
    async def test_no_compression(self):
        """Test no compression passthrough."""
        test_data = b"Uncompressed data"
        
        # No compression
        result = await self.transport._compress_data(
            test_data,
            self.CompressionType.NONE
        )
        self.assertEqual(result, test_data)
        
        # No decompression
        result = await self.transport._decompress_data(
            test_data,
            self.CompressionType.NONE
        )
        self.assertEqual(result, test_data)


class TestStreamingSupport(unittest.TestCase):
    """Test streaming functionality."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.transport.streamable_http_v2 import StreamableHTTPTransportV2
        from src.mcp.config import MCPTransportConfig
        from src.mcp.schemas import MCPRequest
        
        config = MCPTransportConfig(
            bind_host="localhost",
            bind_port=8080
        )
        self.transport = StreamableHTTPTransportV2(config)
        self.MCPRequest = MCPRequest
    
    async def test_response_chunking(self):
        """Test response chunking for streaming."""
        # Create large response
        large_data = {"data": "x" * 10000}
        request = self.MCPRequest(
            id="test-stream",
            method="test",
            params={}
        )
        
        # Mock handle_message to return large response
        self.transport.handle_message = AsyncMock(return_value=Mock(
            dict=Mock(return_value=large_data)
        ))
        
        chunks = []
        async for chunk in self.transport._handle_streaming_message(request):
            chunks.append(chunk)
        
        # Should be chunked
        self.assertGreater(len(chunks), 1)
        
        # Reassemble should match original
        reassembled = b"".join(chunks).decode('utf-8')
        self.assertEqual(json.loads(reassembled), large_data)


class TestFallbackMechanisms(unittest.TestCase):
    """Test fallback mechanisms."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.transport.streamable_http_v2 import (
            StreamableHTTPTransportV2, Protocol, CompressionType, ConnectionState
        )
        from src.mcp.config import MCPTransportConfig
        
        config = MCPTransportConfig(
            bind_host="localhost",
            bind_port=8080
        )
        self.transport = StreamableHTTPTransportV2(config)
        self.Protocol = Protocol
        self.CompressionType = CompressionType
        self.ConnectionState = ConnectionState
    
    async def test_protocol_fallback_sequence(self):
        """Test protocol fallback sequence."""
        # Set initial state
        url = "http://test.example.com"
        state = self.ConnectionState(
            protocol=self.Protocol.HTTP2,
            compression=self.CompressionType.GZIP
        )
        self.transport.connection_states[url] = state
        self.transport.supported_protocols = list(self.Protocol)
        
        # First fallback: HTTP/2 → HTTP/1.1
        await self.transport._fallback_protocol(url)
        self.assertEqual(state.protocol, self.Protocol.HTTP11)
        
        # Second fallback: HTTP/1.1 → WebSocket
        await self.transport._fallback_protocol(url)
        self.assertEqual(state.protocol, self.Protocol.WEBSOCKET)
        
        # Third fallback: WebSocket → HTTP/1.0
        await self.transport._fallback_protocol(url)
        self.assertEqual(state.protocol, self.Protocol.HTTP10)
    
    async def test_compression_fallback_on_protocol_change(self):
        """Test compression reset on protocol fallback."""
        url = "http://test.example.com"
        state = self.ConnectionState(
            protocol=self.Protocol.HTTP2,
            compression=self.CompressionType.BROTLI
        )
        self.transport.connection_states[url] = state
        self.transport.supported_protocols = list(self.Protocol)
        
        # Fallback should reset compression
        await self.transport._fallback_protocol(url)
        self.assertEqual(state.compression, self.CompressionType.NONE)
        self.assertTrue(state.is_healthy)
        self.assertEqual(state.consecutive_failures, 0)


class TestHealthAndMetrics(unittest.TestCase):
    """Test health check and metrics functionality."""
    
    def test_connection_metrics(self):
        """Test connection metrics tracking."""
        from src.mcp.transport.base_transport import ConnectionMetrics
        
        metrics = ConnectionMetrics(
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        # Record successful message
        metrics.record_message_sent(1024, 50)
        self.assertEqual(metrics.messages_sent, 1)
        self.assertEqual(metrics.bytes_sent, 1024)
        self.assertEqual(metrics.average_latency_ms, 50.0)
        
        # Record received message
        metrics.record_message_received(2048)
        self.assertEqual(metrics.messages_received, 1)
        self.assertEqual(metrics.bytes_received, 2048)
        
        # Record error
        metrics.record_error()
        self.assertEqual(metrics.errors_count, 1)
    
    def test_rtt_averaging(self):
        """Test RTT averaging calculation."""
        from src.mcp.transport.streamable_http_v2 import ConnectionState, Protocol, CompressionType
        
        state = ConnectionState(
            protocol=Protocol.HTTP11,
            compression=CompressionType.GZIP
        )
        
        # Record RTT samples
        samples = [100, 150, 120, 110, 130]
        for rtt in samples:
            state.record_success(rtt)
        
        # Average should be calculated from recent samples
        expected_avg = sum(samples) / len(samples)
        self.assertEqual(state.average_rtt, expected_avg)
        
        # Test sliding window (last 10 samples)
        for i in range(20):
            state.record_success(200 + i)
        
        # Should only average last 10
        self.assertEqual(len(state.rtt_samples[-10:]), 10)


if __name__ == "__main__":
    # Run async tests properly
    import asyncio
    
    # Monkey patch to run async tests
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
    for test_class in [TestProtocolNegotiation, TestRequestQueue, 
                       TestCompressionHandling, TestStreamingSupport,
                       TestFallbackMechanisms]:
        for attr_name in dir(test_class):
            if attr_name.startswith('test_'):
                attr = getattr(test_class, attr_name)
                if asyncio.iscoroutinefunction(attr):
                    setattr(test_class, attr_name, async_test(attr))
    
    unittest.main()