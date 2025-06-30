"""
Base Transport Interface and Common Functionality
================================================

Abstract base transport interface defining the contract for all MCP
transport implementations with common functionality and error handling.

Key Features:
- Abstract transport interface for consistency
- Common connection lifecycle management
- Message serialization and deserialization
- Error handling and recovery patterns
- Performance monitoring and metrics

Provides foundation for Streamable HTTP, stdio, and future transport
implementations with consistent behavior and reliability patterns.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable, Union
from datetime import datetime
from dataclasses import dataclass

from ..schemas import MCPRequest, MCPResponse, MCPError
from ..exceptions import TransportError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """
    Connection performance and reliability metrics.
    
    Tracks connection statistics for monitoring, alerting,
    and performance optimization.
    """
    
    connected_at: datetime
    last_activity: datetime
    messages_sent: int
    messages_received: int
    bytes_sent: int
    bytes_received: int
    errors_count: int
    average_latency_ms: float
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def record_message_sent(self, byte_size: int, latency_ms: float):
        """Record outbound message statistics."""
        self.messages_sent += 1
        self.bytes_sent += byte_size
        self._update_average_latency(latency_ms)
        self.update_activity()
    
    def record_message_received(self, byte_size: int):
        """Record inbound message statistics."""
        self.messages_received += 1
        self.bytes_received += byte_size
        self.update_activity()
    
    def record_error(self):
        """Record transport error."""
        self.errors_count += 1
        self.update_activity()
    
    def _update_average_latency(self, new_latency_ms: float):
        """Update rolling average latency."""
        if self.messages_sent == 1:
            self.average_latency_ms = new_latency_ms
        else:
            # Simple moving average
            self.average_latency_ms = (
                (self.average_latency_ms * (self.messages_sent - 1) + new_latency_ms) 
                / self.messages_sent
            )


class BaseTransport(ABC):
    """
    Abstract base class for MCP transport implementations.
    
    Defines the contract that all transport implementations must follow
    including connection management, message handling, and error recovery.
    """
    
    def __init__(self, transport_config: Dict[str, Any]):
        """
        Initialize base transport with configuration.
        
        Args:
            transport_config: Transport-specific configuration
        """
        self.config = transport_config
        self.is_connected = False
        self.connection_id: Optional[str] = None
        self.metrics: Optional[ConnectionMetrics] = None
        
        # Message handlers
        self._message_handlers: Dict[str, Callable[[MCPRequest], Awaitable[MCPResponse]]] = {}
        self._error_handler: Optional[Callable[[Exception], Awaitable[None]]] = None
        
        # Connection callbacks
        self._on_connect: Optional[Callable[[], Awaitable[None]]] = None
        self._on_disconnect: Optional[Callable[[], Awaitable[None]]] = None
        
        logger.debug(f"Base transport initialized: {self.__class__.__name__}")
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish transport connection.
        
        Must be implemented by concrete transport classes to handle
        transport-specific connection establishment.
        
        Raises:
            TransportError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close transport connection gracefully.
        
        Must be implemented by concrete transport classes to handle
        transport-specific connection cleanup.
        """
        pass
    
    @abstractmethod
    async def send_message(self, message: MCPResponse) -> None:
        """
        Send MCP response message through transport.
        
        Args:
            message: MCP response to send
            
        Raises:
            TransportError: If message sending fails
        """
        pass
    
    @abstractmethod
    async def receive_message(self) -> MCPRequest:
        """
        Receive MCP request message from transport.
        
        Returns:
            Received MCP request
            
        Raises:
            TransportError: If message receiving fails
        """
        pass
    
    @abstractmethod
    async def start_listening(self) -> None:
        """
        Start listening for incoming messages.
        
        Must be implemented by concrete transport classes to handle
        transport-specific message listening and processing.
        """
        pass
    
    def register_message_handler(
        self,
        method: str,
        handler: Callable[[MCPRequest], Awaitable[MCPResponse]]
    ) -> None:
        """
        Register handler for specific MCP method.
        
        Args:
            method: MCP method name to handle
            handler: Async handler function
        """
        self._message_handlers[method] = handler
        logger.debug(f"Message handler registered for method: {method}")
    
    def register_error_handler(
        self,
        handler: Callable[[Exception], Awaitable[None]]
    ) -> None:
        """
        Register global error handler for transport errors.
        
        Args:
            handler: Async error handler function
        """
        self._error_handler = handler
        logger.debug("Global error handler registered")
    
    def set_connection_callbacks(
        self,
        on_connect: Optional[Callable[[], Awaitable[None]]] = None,
        on_disconnect: Optional[Callable[[], Awaitable[None]]] = None
    ) -> None:
        """
        Set connection lifecycle callbacks.
        
        Args:
            on_connect: Callback for connection establishment
            on_disconnect: Callback for connection termination
        """
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        logger.debug("Connection callbacks configured")
    
    async def handle_message(self, request: MCPRequest) -> MCPResponse:
        """
        Handle incoming MCP request message.
        
        Routes message to appropriate handler based on method name
        and provides consistent error handling and response formatting.
        
        Args:
            request: Incoming MCP request
            
        Returns:
            MCP response for the request
        """
        start_time = time.time()
        
        try:
            # Validate request
            if not request.method:
                raise ValidationError(
                    message="MCP request missing method",
                    error_code="MISSING_METHOD"
                )
            
            # Find handler for method
            handler = self._message_handlers.get(request.method)
            if not handler:
                return self._create_error_response(
                    request_id=request.id,
                    error_code=-32601,  # Method not found
                    error_message=f"Method not found: {request.method}",
                    correlation_id=getattr(request, 'correlation_id', None)
                )
            
            # Execute handler
            response = await handler(request)
            
            # Record successful handling
            execution_time = int((time.time() - start_time) * 1000)
            if response.execution_time_ms is None:
                response.execution_time_ms = execution_time
            
            logger.debug(
                f"Message handled successfully",
                extra={
                    "method": request.method,
                    "request_id": request.id,
                    "execution_time_ms": execution_time
                }
            )
            
            return response
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            
            logger.error(
                f"Message handling failed",
                extra={
                    "method": request.method,
                    "request_id": request.id,
                    "error": str(e),
                    "execution_time_ms": execution_time
                },
                exc_info=True
            )
            
            # Create error response
            if isinstance(e, ValidationError):
                error_code = -32602  # Invalid params
            else:
                error_code = -32603  # Internal error
            
            return self._create_error_response(
                request_id=request.id,
                error_code=error_code,
                error_message=str(e),
                error_data={"execution_time_ms": execution_time},
                correlation_id=getattr(request, 'correlation_id', None)
            )
    
    async def _handle_connection_established(self) -> None:
        """Handle connection establishment."""
        self.is_connected = True
        self.metrics = ConnectionMetrics(
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            messages_sent=0,
            messages_received=0,
            bytes_sent=0,
            bytes_received=0,
            errors_count=0,
            average_latency_ms=0.0
        )
        
        if self._on_connect:
            try:
                await self._on_connect()
            except Exception as e:
                logger.error(f"Connection callback failed: {e}")
        
        logger.info(f"Transport connection established: {self.connection_id}")
    
    async def _handle_connection_closed(self) -> None:
        """Handle connection termination."""
        was_connected = self.is_connected
        self.is_connected = False
        
        if was_connected and self._on_disconnect:
            try:
                await self._on_disconnect()
            except Exception as e:
                logger.error(f"Disconnection callback failed: {e}")
        
        logger.info(f"Transport connection closed: {self.connection_id}")
    
    async def _handle_transport_error(self, error: Exception) -> None:
        """Handle transport-level errors."""
        if self.metrics:
            self.metrics.record_error()
        
        logger.error(
            f"Transport error",
            extra={
                "connection_id": self.connection_id,
                "error_type": type(error).__name__,
                "error": str(error)
            },
            exc_info=True
        )
        
        if self._error_handler:
            try:
                await self._error_handler(error)
            except Exception as handler_error:
                logger.error(f"Error handler failed: {handler_error}")
    
    def _create_error_response(
        self,
        request_id: Union[str, int],
        error_code: int,
        error_message: str,
        error_data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> MCPResponse:
        """Create standardized error response."""
        from ..schemas import create_error_response
        
        return create_error_response(
            request_id=request_id,
            error_code=error_code,
            error_message=error_message,
            error_data=error_data,
            correlation_id=correlation_id
        )
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information and metrics.
        
        Returns:
            Dictionary with connection status and metrics
        """
        info = {
            "transport_type": self.__class__.__name__,
            "connection_id": self.connection_id,
            "is_connected": self.is_connected,
            "config": self.config
        }
        
        if self.metrics:
            info["metrics"] = {
                "connected_at": self.metrics.connected_at.isoformat(),
                "last_activity": self.metrics.last_activity.isoformat(),
                "messages_sent": self.metrics.messages_sent,
                "messages_received": self.metrics.messages_received,
                "bytes_sent": self.metrics.bytes_sent,
                "bytes_received": self.metrics.bytes_received,
                "errors_count": self.metrics.errors_count,
                "average_latency_ms": self.metrics.average_latency_ms
            }
        
        return info


# TODO: IMPLEMENTATION ENGINEER - Add the following transport enhancements:
# 1. Message compression and decompression support
# 2. Transport-level encryption for sensitive data
# 3. Connection pooling for high-throughput scenarios
# 4. Automatic retry mechanisms with exponential backoff
# 5. Health check and keepalive functionality