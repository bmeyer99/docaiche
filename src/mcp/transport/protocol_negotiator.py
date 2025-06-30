"""
Protocol Negotiation and Transport Selection
============================================

Intelligent protocol negotiation system for selecting optimal transport
mechanisms based on client capabilities and server configuration.

Key Features:
- Automatic transport protocol detection
- Client capability negotiation
- Fallback mechanism for compatibility
- Performance-based transport selection
- Version compatibility management

Ensures optimal transport selection while maintaining backward
compatibility with legacy MCP clients and protocols.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from .base_transport import BaseTransport
from .streamable_http import StreamableHTTPTransport
from .stdio_transport import StdioTransport
from ..schemas import MCPVersion
from ..exceptions import TransportError, ValidationError
from ..config import MCPTransportConfig

logger = logging.getLogger(__name__)


class TransportProtocol(str, Enum):
    """Supported transport protocols."""
    STREAMABLE_HTTP = "streamable-http"
    HTTP_SSE = "http-sse"  # Legacy support
    STDIO = "stdio"
    WEBSOCKET = "websocket"  # Future support


class ClientCapability(str, Enum):
    """Client capability indicators."""
    HTTP_2 = "http2"
    COMPRESSION = "compression"
    STREAMING = "streaming"
    BINARY_FRAMING = "binary_framing"
    WEBSOCKETS = "websockets"
    AUTHENTICATION = "authentication"


@dataclass
class TransportCapabilities:
    """
    Transport capability definition for protocol selection.
    """
    
    protocol: TransportProtocol
    supported_versions: List[MCPVersion]
    capabilities: List[ClientCapability]
    performance_score: int  # Higher is better
    reliability_score: int  # Higher is better
    compatibility_score: int  # Higher is better
    
    def total_score(self) -> int:
        """Calculate total transport score."""
        return self.performance_score + self.reliability_score + self.compatibility_score


class ProtocolNegotiator:
    """
    Protocol negotiation and transport selection system.
    
    Implements intelligent transport selection based on client capabilities,
    server configuration, and performance requirements.
    """
    
    def __init__(self, transport_config: MCPTransportConfig):
        """
        Initialize protocol negotiator.
        
        Args:
            transport_config: Transport configuration
        """
        self.transport_config = transport_config
        
        # Define transport capabilities
        self.transport_capabilities = self._initialize_transport_capabilities()
        
        # Transport preference order (can be configured)
        self.preferred_protocols = [
            TransportProtocol.STREAMABLE_HTTP,
            TransportProtocol.HTTP_SSE,
            TransportProtocol.STDIO
        ]
        
        logger.info(
            f"Protocol negotiator initialized",
            extra={
                "supported_protocols": [tc.protocol.value for tc in self.transport_capabilities],
                "preferred_protocol": self.preferred_protocols[0].value
            }
        )
    
    def _initialize_transport_capabilities(self) -> List[TransportCapabilities]:
        """
        Initialize transport capability definitions.
        
        Returns:
            List of transport capabilities
        """
        return [
            # Streamable HTTP (2025 specification)
            TransportCapabilities(
                protocol=TransportProtocol.STREAMABLE_HTTP,
                supported_versions=[MCPVersion.V2025_03_26],
                capabilities=[
                    ClientCapability.HTTP_2,
                    ClientCapability.COMPRESSION,
                    ClientCapability.STREAMING,
                    ClientCapability.AUTHENTICATION
                ],
                performance_score=9,
                reliability_score=9,
                compatibility_score=7
            ),
            
            # HTTP Server-Sent Events (legacy)
            TransportCapabilities(
                protocol=TransportProtocol.HTTP_SSE,
                supported_versions=[MCPVersion.V2024_11_05, MCPVersion.V2025_03_26],
                capabilities=[
                    ClientCapability.STREAMING,
                    ClientCapability.AUTHENTICATION
                ],
                performance_score=7,
                reliability_score=8,
                compatibility_score=8
            ),
            
            # Standard I/O (maximum compatibility)
            TransportCapabilities(
                protocol=TransportProtocol.STDIO,
                supported_versions=[MCPVersion.V2024_11_05, MCPVersion.V2025_03_26],
                capabilities=[],  # Minimal capabilities
                performance_score=5,
                reliability_score=6,
                compatibility_score=10
            )
        ]
    
    def negotiate_transport(
        self,
        client_capabilities: Dict[str, Any],
        client_preferences: Optional[List[str]] = None
    ) -> Tuple[TransportProtocol, TransportCapabilities]:
        """
        Negotiate optimal transport protocol with client.
        
        Args:
            client_capabilities: Client capability information
            client_preferences: Client transport preferences (ordered)
            
        Returns:
            Tuple of (selected protocol, transport capabilities)
            
        Raises:
            TransportError: If no compatible transport found
        """
        logger.debug(
            f"Starting transport negotiation",
            extra={
                "client_capabilities": client_capabilities,
                "client_preferences": client_preferences
            }
        )
        
        # Extract client information
        client_version = self._parse_client_version(client_capabilities)
        client_caps = self._parse_client_capabilities(client_capabilities)
        
        # Score and rank available transports
        scored_transports = []
        
        for transport_cap in self.transport_capabilities:
            # Check version compatibility
            if client_version not in transport_cap.supported_versions:
                logger.debug(f"Transport {transport_cap.protocol.value} incompatible with client version {client_version.value}")
                continue
            
            # Calculate compatibility score
            compatibility_score = self._calculate_compatibility_score(
                transport_cap, client_caps, client_preferences
            )
            
            if compatibility_score > 0:
                total_score = (
                    transport_cap.performance_score +
                    transport_cap.reliability_score +
                    compatibility_score
                )
                
                scored_transports.append((total_score, transport_cap))
        
        # Sort by score (highest first)
        scored_transports.sort(key=lambda x: x[0], reverse=True)
        
        if not scored_transports:
            raise TransportError(
                message="No compatible transport protocol found",
                error_code="NO_COMPATIBLE_TRANSPORT",
                details={
                    "client_version": client_version.value,
                    "client_capabilities": client_caps
                }
            )
        
        # Select best transport
        best_score, best_transport = scored_transports[0]
        
        logger.info(
            f"Transport negotiated",
            extra={
                "selected_protocol": best_transport.protocol.value,
                "score": best_score,
                "client_version": client_version.value,
                "alternatives": [t[1].protocol.value for t in scored_transports[1:3]]
            }
        )
        
        return best_transport.protocol, best_transport
    
    def create_transport(
        self,
        protocol: TransportProtocol,
        transport_config: Optional[MCPTransportConfig] = None
    ) -> BaseTransport:
        """
        Create transport instance for selected protocol.
        
        Args:
            protocol: Selected transport protocol
            transport_config: Optional transport configuration override
            
        Returns:
            Configured transport instance
            
        Raises:
            TransportError: If transport creation fails
        """
        config = transport_config or self.transport_config
        
        try:
            if protocol == TransportProtocol.STREAMABLE_HTTP:
                return StreamableHTTPTransport(config)
            
            elif protocol == TransportProtocol.STDIO:
                return StdioTransport(config.dict())
            
            elif protocol == TransportProtocol.HTTP_SSE:
                # For now, use HTTP transport with SSE configuration
                return StreamableHTTPTransport(config)
            
            else:
                raise TransportError(
                    message=f"Unsupported transport protocol: {protocol.value}",
                    error_code="UNSUPPORTED_TRANSPORT",
                    details={"protocol": protocol.value}
                )
                
        except Exception as e:
            raise TransportError(
                message=f"Failed to create transport: {str(e)}",
                error_code="TRANSPORT_CREATION_FAILED",
                details={"protocol": protocol.value, "error": str(e)}
            )
    
    def get_server_capabilities(self) -> Dict[str, Any]:
        """
        Get server transport capabilities for client negotiation.
        
        Returns:
            Server capability information
        """
        capabilities = {
            "supported_protocols": [],
            "preferred_protocol": self.preferred_protocols[0].value,
            "mcp_versions": [v.value for v in MCPVersion],
            "features": {
                "compression": self.transport_config.compression_enabled,
                "streaming": True,
                "authentication": True,
                "max_message_size": self.transport_config.max_message_size
            }
        }
        
        # Add protocol-specific information
        for transport_cap in self.transport_capabilities:
            protocol_info = {
                "protocol": transport_cap.protocol.value,
                "versions": [v.value for v in transport_cap.supported_versions],
                "capabilities": [c.value for c in transport_cap.capabilities],
                "performance_score": transport_cap.performance_score,
                "reliability_score": transport_cap.reliability_score
            }
            
            capabilities["supported_protocols"].append(protocol_info)
        
        return capabilities
    
    def _parse_client_version(self, client_capabilities: Dict[str, Any]) -> MCPVersion:
        """Parse client MCP version from capabilities."""
        version_str = client_capabilities.get("mcp_version", "2024-11-05")
        
        try:
            return MCPVersion(version_str)
        except ValueError:
            # Default to older version for compatibility
            logger.warning(f"Unknown client MCP version: {version_str}, defaulting to 2024-11-05")
            return MCPVersion.V2024_11_05
    
    def _parse_client_capabilities(self, client_capabilities: Dict[str, Any]) -> List[ClientCapability]:
        """Parse client capabilities from capability information."""
        caps = []
        
        # Check for specific capability indicators
        if client_capabilities.get("supports_http2", False):
            caps.append(ClientCapability.HTTP_2)
        
        if client_capabilities.get("supports_compression", False):
            caps.append(ClientCapability.COMPRESSION)
        
        if client_capabilities.get("supports_streaming", False):
            caps.append(ClientCapability.STREAMING)
        
        if client_capabilities.get("supports_websockets", False):
            caps.append(ClientCapability.WEBSOCKETS)
        
        if client_capabilities.get("supports_authentication", False):
            caps.append(ClientCapability.AUTHENTICATION)
        
        # Parse from capabilities array if present
        capability_list = client_capabilities.get("capabilities", [])
        for cap_str in capability_list:
            try:
                cap = ClientCapability(cap_str)
                if cap not in caps:
                    caps.append(cap)
            except ValueError:
                logger.debug(f"Unknown client capability: {cap_str}")
        
        return caps
    
    def _calculate_compatibility_score(
        self,
        transport_cap: TransportCapabilities,
        client_caps: List[ClientCapability],
        client_preferences: Optional[List[str]]
    ) -> int:
        """Calculate compatibility score for transport and client."""
        score = transport_cap.compatibility_score
        
        # Bonus for matching client capabilities
        matching_caps = set(transport_cap.capabilities) & set(client_caps)
        score += len(matching_caps) * 2
        
        # Bonus for client preference
        if client_preferences:
            try:
                preference_index = client_preferences.index(transport_cap.protocol.value)
                # Higher bonus for higher preference (lower index)
                score += (len(client_preferences) - preference_index) * 3
            except ValueError:
                pass  # Protocol not in client preferences
        
        # Bonus for server preference
        try:
            server_preference_index = self.preferred_protocols.index(transport_cap.protocol)
            score += (len(self.preferred_protocols) - server_preference_index) * 2
        except ValueError:
            pass  # Protocol not in server preferences
        
        return score
    
    def validate_transport_config(self, protocol: TransportProtocol) -> bool:
        """
        Validate transport configuration for protocol.
        
        Args:
            protocol: Transport protocol to validate
            
        Returns:
            True if configuration is valid
        """
        if protocol == TransportProtocol.STREAMABLE_HTTP:
            return (
                self.transport_config.bind_port > 0 and
                self.transport_config.bind_host is not None
            )
        
        elif protocol == TransportProtocol.STDIO:
            return True  # Stdio requires minimal configuration
        
        else:
            logger.warning(f"Unknown transport protocol for validation: {protocol.value}")
            return False


# TODO: IMPLEMENTATION ENGINEER - Add the following negotiation enhancements:
# 1. Dynamic capability discovery and adaptation
# 2. Transport performance benchmarking and selection
# 3. Client-specific transport caching and preferences
# 4. Advanced fallback strategies with graceful degradation
# 5. Integration with service mesh and load balancer configurations