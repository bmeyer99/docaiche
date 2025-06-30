"""
MCP Transport Layer Implementation
=================================

Comprehensive transport layer supporting multiple MCP communication mechanisms
including Streamable HTTP (2025 specification) and fallback protocols.

Key Components:
- Streamable HTTP transport with compression and streaming
- Legacy stdio transport for backward compatibility
- Connection management and lifecycle handling
- Protocol negotiation and fallback mechanisms
- Performance optimization and error recovery

Implements MCP 2025 transport specification with enhanced reliability,
scalability, and observability for production deployment.
"""

from .streamable_http import StreamableHTTPTransport, ConnectionManager
from .stdio_transport import StdioTransport
from .base_transport import BaseTransport, TransportError
from .protocol_negotiator import ProtocolNegotiator

__all__ = [
    'StreamableHTTPTransport',
    'ConnectionManager',
    'StdioTransport', 
    'BaseTransport',
    'TransportError',
    'ProtocolNegotiator'
]