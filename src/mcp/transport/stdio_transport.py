"""
Standard I/O Transport Implementation
====================================

Legacy stdio transport for backward compatibility with MCP clients
that do not support Streamable HTTP transport.

Key Features:
- JSON-RPC over stdin/stdout communication
- Line-based message framing
- Process lifecycle management
- Error handling and recovery
- Graceful fallback mechanism

Provides compatibility with existing MCP clients while maintaining
the same interface contract as modern transport implementations.
"""

import asyncio
import json
import logging
import sys
from typing import Optional, TextIO
import signal

from .base_transport import BaseTransport
from ..schemas import MCPRequest, MCPResponse, validate_mcp_request
from ..exceptions import TransportError, ValidationError

logger = logging.getLogger(__name__)


class StdioTransport(BaseTransport):
    """
    Standard I/O transport for MCP communication.
    
    Implements JSON-RPC communication over stdin/stdout for compatibility
    with legacy MCP clients and process-based integration scenarios.
    """
    
    def __init__(self, transport_config: dict):
        """
        Initialize stdio transport.
        
        Args:
            transport_config: Transport configuration (mostly unused for stdio)
        """
        super().__init__(transport_config)
        
        # I/O streams
        self.stdin: Optional[TextIO] = None
        self.stdout: Optional[TextIO] = None
        self.stderr: Optional[TextIO] = None
        
        # Processing state
        self.reader_task: Optional[asyncio.Task] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.shutdown_event = asyncio.Event()
        
        # Line buffering for message parsing
        self.input_buffer = ""
        
        logger.info("Stdio transport initialized")
    
    async def connect(self) -> None:
        """
        Establish stdio transport connection.
        
        Sets up stdin/stdout streams and prepares for message processing.
        
        Raises:
            TransportError: If stdio setup fails
        """
        try:
            # Use system stdin/stdout
            self.stdin = sys.stdin
            self.stdout = sys.stdout
            self.stderr = sys.stderr
            
            # Generate connection ID
            import secrets
            self.connection_id = f"stdio_{secrets.token_urlsafe(8)}"
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            await self._handle_connection_established()
            
            logger.info(f"Stdio transport connected: {self.connection_id}")
            
        except Exception as e:
            error = TransportError(
                message=f"Failed to setup stdio transport: {str(e)}",
                error_code="STDIO_SETUP_FAILED",
                details={"error": str(e)}
            )
            await self._handle_transport_error(error)
            raise error
    
    async def disconnect(self) -> None:
        """
        Close stdio transport gracefully.
        """
        try:
            # Signal shutdown
            self.shutdown_event.set()
            
            # Cancel reader task
            if self.reader_task and not self.reader_task.done():
                self.reader_task.cancel()
                try:
                    await self.reader_task
                except asyncio.CancelledError:
                    pass
            
            # Flush output streams
            if self.stdout:
                self.stdout.flush()
            if self.stderr:
                self.stderr.flush()
            
            await self._handle_connection_closed()
            
            logger.info(f"Stdio transport disconnected: {self.connection_id}")
            
        except Exception as e:
            logger.error(f"Error during stdio transport shutdown: {e}")
    
    async def send_message(self, message: MCPResponse) -> None:
        """
        Send MCP response via stdout.
        
        Args:
            message: MCP response to send
            
        Raises:
            TransportError: If sending fails
        """
        if not self.stdout:
            raise TransportError(
                message="Stdout not available",
                error_code="STDOUT_NOT_AVAILABLE"
            )
        
        try:
            # Serialize message to JSON
            message_data = message.dict()
            message_json = json.dumps(message_data, separators=(',', ':'))
            
            # Write to stdout with newline
            self.stdout.write(message_json + '\n')
            self.stdout.flush()
            
            # Record metrics
            if self.metrics:
                message_bytes = len(message_json.encode('utf-8'))
                self.metrics.record_message_sent(message_bytes, 0)  # No latency for stdio
            
            logger.debug(
                f"Message sent via stdio",
                extra={
                    "message_id": message.id,
                    "size_bytes": len(message_json)
                }
            )
            
        except Exception as e:
            error = TransportError(
                message=f"Failed to send stdio message: {str(e)}",
                error_code="STDIO_SEND_FAILED",
                details={"error": str(e)}
            )
            await self._handle_transport_error(error)
            raise error
    
    async def receive_message(self) -> MCPRequest:
        """
        Receive MCP request from message queue.
        
        Returns:
            Received MCP request
            
        Raises:
            TransportError: If receiving fails
        """
        try:
            # Wait for message from queue
            message = await self.message_queue.get()
            
            # Record metrics
            if self.metrics:
                message_bytes = len(json.dumps(message.dict()).encode('utf-8'))
                self.metrics.record_message_received(message_bytes)
            
            return message
            
        except Exception as e:
            error = TransportError(
                message=f"Failed to receive stdio message: {str(e)}",
                error_code="STDIO_RECEIVE_FAILED",
                details={"error": str(e)}
            )
            await self._handle_transport_error(error)
            raise error
    
    async def start_listening(self) -> None:
        """
        Start listening for stdin input.
        
        Creates background task to read from stdin and parse JSON messages.
        """
        if not self.is_connected:
            raise TransportError(
                message="Transport not connected",
                error_code="TRANSPORT_NOT_CONNECTED"
            )
        
        # Start stdin reader task
        self.reader_task = asyncio.create_task(self._stdin_reader())
        
        logger.info(f"Stdio transport listening for input: {self.connection_id}")
    
    async def _stdin_reader(self) -> None:
        """
        Background task to read from stdin and parse messages.
        """
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Read line from stdin (non-blocking)
                    line = await self._read_stdin_line()
                    
                    if line is None:  # EOF or shutdown
                        break
                    
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Parse JSON message
                    try:
                        message_data = json.loads(line)
                        
                        # Validate MCP request
                        mcp_request = validate_mcp_request(message_data)
                        
                        # Add to message queue for processing
                        await self.message_queue.put(mcp_request)
                        
                        logger.debug(
                            f"Message received via stdin",
                            extra={
                                "method": mcp_request.method,
                                "request_id": mcp_request.id
                            }
                        )
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received via stdin: {e}")
                        await self._send_error_response(
                            request_id="unknown",
                            error_code=-32700,  # Parse error
                            error_message=f"Invalid JSON: {str(e)}"
                        )
                    
                    except ValidationError as e:
                        logger.error(f"Invalid MCP request via stdin: {e}")
                        await self._send_error_response(
                            request_id=message_data.get('id', 'unknown'),
                            error_code=-32602,  # Invalid params
                            error_message=f"Invalid request: {str(e)}"
                        )
                
                except Exception as e:
                    logger.error(f"Error reading from stdin: {e}")
                    await asyncio.sleep(0.1)  # Brief pause before retry
        
        except asyncio.CancelledError:
            logger.debug("Stdin reader task cancelled")
        except Exception as e:
            logger.error(f"Stdin reader task failed: {e}")
            await self._handle_transport_error(e)
    
    async def _read_stdin_line(self) -> Optional[str]:
        """
        Read a line from stdin asynchronously.
        
        Returns:
            Line from stdin or None if EOF/shutdown
        """
        # Use a simple polling approach for stdin reading
        # In production, consider using proper async I/O libraries
        loop = asyncio.get_event_loop()
        
        try:
            # Check if shutdown was requested
            if self.shutdown_event.is_set():
                return None
            
            # Read from stdin in thread pool to avoid blocking
            line = await loop.run_in_executor(None, self.stdin.readline)
            
            # Check for EOF
            if not line:
                return None
            
            return line.strip()
            
        except Exception as e:
            logger.error(f"Error reading stdin line: {e}")
            return None
    
    async def _send_error_response(
        self,
        request_id: str,
        error_code: int,
        error_message: str
    ) -> None:
        """
        Send error response for invalid requests.
        
        Args:
            request_id: Request ID (may be unknown)
            error_code: JSON-RPC error code
            error_message: Error description
        """
        try:
            error_response = self._create_error_response(
                request_id=request_id,
                error_code=error_code,
                error_message=error_message
            )
            
            await self.send_message(error_response)
            
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown.
        """
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            self.shutdown_event.set()
        
        # Handle common termination signals
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, signal_handler)
    
    def write_log(self, level: str, message: str, **kwargs) -> None:
        """
        Write log message to stderr.
        
        Args:
            level: Log level (info, warning, error)
            message: Log message
            **kwargs: Additional log context
        """
        if not self.stderr:
            return
        
        try:
            log_entry = {
                "level": level,
                "message": message,
                "timestamp": self._get_timestamp(),
                "transport": "stdio",
                "connection_id": self.connection_id,
                **kwargs
            }
            
            log_json = json.dumps(log_entry)
            self.stderr.write(f"LOG: {log_json}\n")
            self.stderr.flush()
            
        except Exception as e:
            # Fallback to simple stderr write
            self.stderr.write(f"LOG ERROR: {e}\n")
            self.stderr.flush()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# TODO: IMPLEMENTATION ENGINEER - Add the following stdio transport enhancements:
# 1. Binary message framing for large messages
# 2. Message compression for bandwidth optimization
# 3. Process monitoring and automatic restart
# 4. Input validation and sanitization
# 5. Integration with process management tools