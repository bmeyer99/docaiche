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

# Core imports that don't require external dependencies
from .base_transport import BaseTransport
from ..exceptions import TransportError

# Conditional imports for transports that require external dependencies
try:
    from .streamable_http import StreamableHTTPTransport, ConnectionManager
except ImportError:
    StreamableHTTPTransport = None
    ConnectionManager = None

try:
    from .stdio_transport import StdioTransport
except ImportError:
    StdioTransport = None

try:
    from .protocol_negotiator import ProtocolNegotiator
except ImportError:
    ProtocolNegotiator = None

__all__ = [
    'StreamableHTTPTransport',
    'ConnectionManager',
    'StdioTransport', 
    'BaseTransport',
    'TransportError',
    'ProtocolNegotiator'
]