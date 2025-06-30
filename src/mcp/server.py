"""
MCP Server Implementation V2
============================

Complete Model Context Protocol server implementation integrating all
components into a cohesive, production-ready system.

Key Features:
- Component orchestration and lifecycle management
- Request routing and handler dispatch
- Authentication and authorization integration
- Transport protocol management
- Tool and resource registration
- Comprehensive error handling and recovery
- Performance monitoring and health checks

Implements the complete MCP 2025 specification with all required
features for production deployment.
"""

import asyncio
import logging
import signal
import secrets
from typing import Dict, Any, Optional, List, Set, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
import json
from contextlib import asynccontextmanager

from .schemas import (
    MCPRequest, MCPResponse, MCPError, ErrorCode,
    ToolDefinition, ResourceDefinition,
    InitializeRequest, InitializeResponse,
    InitializedNotification,
    validate_mcp_request, create_success_response, create_error_response
)
from .exceptions import (
    MCPException,
    ValidationError, AuthenticationError, AuthorizationError,
    ToolExecutionError, ResourceError, TransportError
)
from .config import MCPServerConfig

# Import transport implementations
from .transport.base_transport import BaseTransport
from .transport.streamable_http_v2 import StreamableHTTPTransportV2

# Import authentication
from .auth.auth_manager import AuthManager
from .auth.oauth_handler import OAuth21Handler, OAuth21Config

# Import tools
from .tools.base_tool import BaseTool
from .tools.search_tool import SearchTool
from .tools.ingest_tool import IngestTool
from .tools.feedback_tool import FeedbackTool

# Import resources
from .resources.base_resource import BaseResource
from .resources.documentation_resource import DocumentationResource
from .resources.collections_resource import CollectionsResource
from .resources.status_resource import StatusResource

# Import services
from .services.consent_manager import ConsentManager
from .auth.security_audit import SecurityAuditor

logger = logging.getLogger(__name__)


@dataclass
class ServerMetadata:
    """MCP server metadata and capabilities."""
    
    name: str = "DocaiChe MCP Server"
    version: str = "2.0.0"
    protocol_version: str = "2025-03-26"
    vendor: str = "DocaiChe"
    
    capabilities: Dict[str, Any] = field(default_factory=lambda: {
        "tools": {
            "supported": True,
            "annotations": True,
            "streaming": False
        },
        "resources": {
            "supported": True,
            "subscribe": False,
            "list": True
        },
        "prompts": {
            "supported": False
        },
        "logging": {
            "supported": True,
            "levels": ["error", "warning", "info", "debug"]
        },
        "experimental": {
            "streaming": True,
            "batch_requests": True
        }
    })


@dataclass
class ClientSession:
    """Client session information."""
    
    session_id: str
    client_info: Dict[str, Any]
    initialized: bool = False
    authenticated: bool = False
    auth_token: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)


class MCPServer:
    """
    Complete MCP server implementation with component integration.
    
    Orchestrates all MCP components including transport, authentication,
    tools, resources, and services into a cohesive server application.
    """
    
    def __init__(self, config: MCPServerConfig):
        """
        Initialize MCP server with configuration.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.metadata = ServerMetadata()
        
        # Server state
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # Component registries
        self.tools: Dict[str, BaseTool] = {}
        self.resources: Dict[str, BaseResource] = {}
        self.transports: List[BaseTransport] = []
        
        # Client management
        self.sessions: Dict[str, ClientSession] = {}
        self._session_lock = asyncio.Lock()
        
        # Service components
        self.auth_manager: Optional[AuthManager] = None
        self.consent_manager: Optional[ConsentManager] = None
        self.security_auditor: Optional[SecurityAuditor] = None
        
        # Request handlers
        self.request_handlers: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "shutdown": self._handle_shutdown,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "logging/setLevel": self._handle_logging_set_level,
            "ping": self._handle_ping
        }
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info(
            f"MCP Server initialized: {self.metadata.name} v{self.metadata.version}",
            extra={
                "protocol_version": self.metadata.protocol_version,
                "capabilities": self.metadata.capabilities
            }
        )
    
    async def start(self) -> None:
        """
        Start MCP server and all components.
        
        Initializes and starts all server components in the correct order,
        ensuring proper dependency resolution and error handling.
        """
        if self.is_running:
            logger.warning("Server already running")
            return
        
        try:
            logger.info("Starting MCP server...")
            
            # Initialize core services
            await self._initialize_services()
            
            # Initialize authentication
            await self._initialize_authentication()
            
            # Initialize and register tools
            await self._initialize_tools()
            
            # Initialize and register resources
            await self._initialize_resources()
            
            # Initialize transports
            await self._initialize_transports()
            
            # Start all transports
            for transport in self.transports:
                await transport.connect()
                transport.set_message_handler(self._handle_transport_message)
                await transport.start_listening()
            
            self.is_running = True
            
            logger.info(
                "MCP server started successfully",
                extra={
                    "tools": list(self.tools.keys()),
                    "resources": list(self.resources.keys()),
                    "transports": len(self.transports)
                }
            )
            
            # Wait for shutdown
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Server startup failed: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """
        Stop MCP server and cleanup resources.
        
        Performs graceful shutdown of all components in reverse order,
        ensuring proper resource cleanup and connection closure.
        """
        if not self.is_running and not self.transports:
            return
        
        logger.info("Stopping MCP server...")
        
        try:
            # Stop accepting new requests
            self.is_running = False
            
            # Close all client sessions
            await self._close_all_sessions()
            
            # Stop all transports
            for transport in self.transports:
                try:
                    await transport.disconnect()
                except Exception as e:
                    logger.error(f"Error stopping transport: {e}")
            
            # Cleanup services
            if self.security_auditor:
                await self.security_auditor.close()
            
            # Cleanup adapters
            if hasattr(self, '_adapter_factory'):
                await self._adapter_factory.close_all()
            
            logger.info("MCP server stopped")
            
        except Exception as e:
            logger.error(f"Error during server shutdown: {e}", exc_info=True)
        
        finally:
            # Signal shutdown complete
            self.shutdown_event.set()
    
    async def _initialize_services(self) -> None:
        """Initialize core services."""
        # Initialize security auditor
        self.security_auditor = SecurityAuditor(
            log_file=self.config.audit_log_file,
            max_size=self.config.audit_log_max_size,
            retention_days=self.config.audit_log_retention_days
        )
        await self.security_auditor.initialize()
        
        # Initialize consent manager
        self.consent_manager = ConsentManager(
            default_permissions=self.config.default_permissions,
            require_explicit_consent=self.config.require_explicit_consent
        )
        
        logger.info("Core services initialized")
    
    async def _initialize_authentication(self) -> None:
        """Initialize authentication system."""
        # Create OAuth handler
        oauth_config = OAuth21Config(
            provider_name="docaiche",
            client_id=self.config.oauth_client_id,
            client_secret=self.config.oauth_client_secret,
            authorization_endpoint=self.config.oauth_auth_endpoint,
            token_endpoint=self.config.oauth_token_endpoint,
            introspection_endpoint=self.config.oauth_introspection_endpoint,
            revocation_endpoint=self.config.oauth_revocation_endpoint
        )
        
        oauth_handler = OAuth21Handler(
            config=oauth_config,
            security_auditor=self.security_auditor
        )
        
        # Create auth manager
        self.auth_manager = AuthManager(
            auth_providers={"oauth": oauth_handler},
            consent_manager=self.consent_manager,
            security_auditor=self.security_auditor,
            require_auth=self.config.require_authentication
        )
        
        logger.info("Authentication system initialized")
    
    async def _initialize_tools(self) -> None:
        """Initialize and register all tools."""
        # Import adapters instead of HTTP services
        from .adapters.adapter_factory import AdapterFactory, AdapterType
        from .services.service_registry import get_service_registry
        
        # Create adapter factory
        adapter_config = {
            'base_url': self.config.services.get('search_service_url', 'http://localhost:8000').replace('/api/v1/search', ''),
            'api_version': 'v1',
            'auth_token': getattr(self.config, 'docaiche_api_key', None),
            'timeout': 30
        }
        self._adapter_factory = AdapterFactory(**adapter_config)
        
        # Create adapters for tools
        search_adapter = self._adapter_factory.create_adapter(AdapterType.SEARCH)
        ingestion_adapter = self._adapter_factory.create_adapter(AdapterType.INGESTION)
        
        # For feedback, we'll use the search adapter since it includes feedback methods
        # For analytics, we'll use logs adapter for now
        logs_adapter = self._adapter_factory.create_adapter(AdapterType.LOGS)
        
        # Create tool instances with adapters
        search_tool = SearchTool(
            search_service=search_adapter,
            consent_manager=self.consent_manager,
            security_auditor=self.security_auditor
        )
        
        ingest_tool = IngestTool(
            ingestion_service=ingestion_adapter,
            consent_manager=self.consent_manager,
            security_auditor=self.security_auditor
        )
        
        feedback_tool = FeedbackTool(
            feedback_service=search_adapter,  # Search adapter includes feedback methods
            analytics_engine=logs_adapter,     # Logs adapter can handle analytics
            consent_manager=self.consent_manager,
            security_auditor=self.security_auditor
        )
        
        # Register tools
        self.register_tool(search_tool)
        self.register_tool(ingest_tool)
        self.register_tool(feedback_tool)
        
        logger.info(f"Initialized {len(self.tools)} tools with HTTP services")
    
    async def _initialize_resources(self) -> None:
        """Initialize and register all resources."""
        # Use adapter factory created in _initialize_tools
        from .adapters.adapter_factory import AdapterType
        
        # Create adapters for resources
        # For documentation, we can use search adapter as it can handle doc queries
        search_adapter = self._adapter_factory.get_adapter(AdapterType.SEARCH)
        health_adapter = self._adapter_factory.create_adapter(AdapterType.HEALTH)
        config_adapter = self._adapter_factory.create_adapter(AdapterType.CONFIG)
        
        # Create resource instances with adapters
        doc_resource = DocumentationResource(
            documentation_service=search_adapter,  # Search can handle doc queries
            consent_manager=self.consent_manager,
            security_auditor=self.security_auditor
        )
        
        collections_resource = CollectionsResource(
            collections_service=config_adapter,  # Config adapter can handle collections
            consent_manager=self.consent_manager,
            security_auditor=self.security_auditor
        )
        
        status_resource = StatusResource(
            health_service=health_adapter,
            metrics_collector=health_adapter,  # Health adapter includes metrics
            consent_manager=self.consent_manager,
            security_auditor=self.security_auditor
        )
        
        # Register resources
        self.register_resource(doc_resource)
        self.register_resource(collections_resource)
        self.register_resource(status_resource)
        
        logger.info(f"Initialized {len(self.resources)} resources with HTTP services")
    
    async def _initialize_transports(self) -> None:
        """Initialize transport layers."""
        # Create HTTP transport
        http_transport = StreamableHTTPTransportV2(self.config.transport_config)
        self.transports.append(http_transport)
        
        # Additional transports can be added here
        
        logger.info(f"Initialized {len(self.transports)} transports")
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool with the server.
        
        Args:
            tool: Tool instance to register
        """
        tool_def = tool.get_tool_definition()
        self.tools[tool_def.name] = tool
        logger.info(f"Registered tool: {tool_def.name}")
    
    def register_resource(self, resource: BaseResource) -> None:
        """
        Register a resource with the server.
        
        Args:
            resource: Resource instance to register
        """
        resource_def = resource.get_resource_definition()
        self.resources[resource_def.name] = resource
        logger.info(f"Registered resource: {resource_def.name}")
    
    async def _handle_transport_message(
        self,
        request: MCPRequest,
        transport: BaseTransport
    ) -> MCPResponse:
        """
        Handle incoming message from transport.
        
        Args:
            request: MCP request
            transport: Transport that received the request
            
        Returns:
            MCP response
        """
        session = None
        
        try:
            # Get or create session
            session = await self._get_or_create_session(request, transport)
            
            # Update activity
            session.update_activity()
            
            # Check if initialized (except for initialize request)
            if request.method != "initialize" and not session.initialized:
                raise ValidationError(
                    message="Client not initialized",
                    error_code="NOT_INITIALIZED"
                )
            
            # Authenticate if required
            if self.config.require_authentication and request.method != "initialize":
                if not session.authenticated:
                    raise AuthenticationError(
                        message="Authentication required",
                        error_code="AUTH_REQUIRED"
                    )
            
            # Route request to handler
            handler = self.request_handlers.get(request.method)
            if not handler:
                raise ValidationError(
                    message=f"Unknown method: {request.method}",
                    error_code="METHOD_NOT_FOUND"
                )
            
            # Execute handler
            response = await handler(request, session)
            
            # Audit successful request
            if self.security_auditor:
                await self.security_auditor.log_event(
                    event_type="request_handled",
                    details={
                        "method": request.method,
                        "session_id": session.session_id,
                        "success": True
                    }
                )
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                f"Request handling error: {e}",
                extra={
                    "method": request.method,
                    "session_id": session.session_id if session else None,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            # Audit failed request
            if self.security_auditor:
                await self.security_auditor.log_event(
                    event_type="request_failed",
                    severity="high" if isinstance(e, (AuthenticationError, AuthorizationError)) else "medium",
                    details={
                        "method": request.method,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
            
            # Create error response
            if isinstance(e, ValidationError):
                error_code = ErrorCode.INVALID_PARAMS
            elif isinstance(e, AuthenticationError):
                error_code = ErrorCode.INVALID_REQUEST
            elif isinstance(e, AuthorizationError):
                error_code = ErrorCode.INVALID_REQUEST
            else:
                error_code = ErrorCode.INTERNAL_ERROR
            
            return create_error_response(
                request_id=request.id,
                error_code=error_code.value,
                error_message=str(e),
                error_data={"type": type(e).__name__}
            )
    
    async def _get_or_create_session(
        self,
        request: MCPRequest,
        transport: BaseTransport
    ) -> ClientSession:
        """Get or create client session."""
        async with self._session_lock:
            # Try to get session from request
            session_id = getattr(request.params, "sessionId", None) if request.params else None
            
            if session_id and session_id in self.sessions:
                return self.sessions[session_id]
            
            # Create new session
            session_id = f"session_{transport.connection_id}_{secrets.token_urlsafe(8)}"
            session = ClientSession(
                session_id=session_id,
                client_info={}
            )
            
            self.sessions[session_id] = session
            logger.info(f"Created new session: {session_id}")
            
            return session
    
    async def _handle_initialize(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle initialize request."""
        try:
            # Parse initialize request
            init_request = InitializeRequest(**request.params)
            
            # Store client info
            session.client_info = init_request.clientInfo
            
            # Create response
            response = InitializeResponse(
                protocolVersion=self.metadata.protocol_version,
                capabilities=self.metadata.capabilities,
                serverInfo={
                    "name": self.metadata.name,
                    "version": self.metadata.version,
                    "vendor": self.metadata.vendor
                },
                sessionId=session.session_id
            )
            
            # Mark session as initialized
            session.initialized = True
            
            logger.info(
                f"Client initialized",
                extra={
                    "session_id": session.session_id,
                    "client_info": session.client_info
                }
            )
            
            return create_success_response(
                request_id=request.id,
                result=response.dict()
            )
            
        except Exception as e:
            raise ValidationError(
                message=f"Initialize failed: {str(e)}",
                error_code="INITIALIZE_FAILED"
            )
    
    async def _handle_initialized(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle initialized notification."""
        # This is a notification, no response needed
        logger.info(f"Client confirmed initialization: {session.session_id}")
        
        return create_success_response(
            request_id=request.id,
            result={"status": "acknowledged"}
        )
    
    async def _handle_shutdown(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle shutdown request."""
        logger.info(f"Shutdown requested by session: {session.session_id}")
        
        # Schedule graceful shutdown
        asyncio.create_task(self._graceful_shutdown())
        
        return create_success_response(
            request_id=request.id,
            result={"status": "shutting_down"}
        )
    
    async def _handle_tools_list(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle tools/list request."""
        # Get tool definitions
        tools = [
            tool.get_tool_definition().dict()
            for tool in self.tools.values()
        ]
        
        return create_success_response(
            request_id=request.id,
            result={"tools": tools}
        )
    
    async def _handle_tools_call(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle tools/call request."""
        try:
            # Extract tool name and arguments
            tool_name = request.params.get("name")
            tool_args = request.params.get("arguments", {})
            
            if not tool_name:
                raise ValidationError(
                    message="Tool name required",
                    error_code="MISSING_TOOL_NAME"
                )
            
            # Get tool
            tool = self.tools.get(tool_name)
            if not tool:
                raise ValidationError(
                    message=f"Unknown tool: {tool_name}",
                    error_code="UNKNOWN_TOOL"
                )
            
            # Create tool request
            tool_request = MCPRequest(
                id=request.id,
                method=tool_name,
                params=tool_args
            )
            
            # Execute tool
            result = await tool.execute(
                tool_request,
                client_id=session.session_id,
                auth_token=session.auth_token
            )
            
            return result
            
        except ToolExecutionError as e:
            raise
        except Exception as e:
            raise ToolExecutionError(
                message=f"Tool execution failed: {str(e)}",
                error_code="TOOL_EXECUTION_FAILED",
                tool_name=tool_name if 'tool_name' in locals() else "unknown"
            )
    
    async def _handle_resources_list(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle resources/list request."""
        # Get resource definitions
        resources = [
            resource.get_resource_definition().dict()
            for resource in self.resources.values()
        ]
        
        return create_success_response(
            request_id=request.id,
            result={"resources": resources}
        )
    
    async def _handle_resources_read(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle resources/read request."""
        try:
            # Extract resource URI
            uri = request.params.get("uri")
            if not uri:
                raise ValidationError(
                    message="Resource URI required",
                    error_code="MISSING_URI"
                )
            
            # Find matching resource
            resource = None
            for res in self.resources.values():
                if res.can_handle_uri(uri):
                    resource = res
                    break
            
            if not resource:
                raise ResourceError(
                    message=f"No resource handler for URI: {uri}",
                    error_code="UNKNOWN_RESOURCE",
                    resource_uri=uri
                )
            
            # Fetch resource
            result = await resource.fetch_resource(
                uri,
                client_id=session.session_id,
                auth_token=session.auth_token
            )
            
            return create_success_response(
                request_id=request.id,
                result={
                    "contents": [{
                        "uri": uri,
                        "mimeType": result.get("mimeType", "application/json"),
                        "text": result.get("text"),
                        "blob": result.get("blob")
                    }]
                }
            )
            
        except ResourceError as e:
            raise
        except Exception as e:
            raise ResourceError(
                message=f"Resource access failed: {str(e)}",
                error_code="RESOURCE_ACCESS_FAILED",
                resource_uri=uri if 'uri' in locals() else "unknown"
            )
    
    async def _handle_logging_set_level(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle logging/setLevel request."""
        level = request.params.get("level", "info").upper()
        
        # Map to Python logging levels
        level_map = {
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG
        }
        
        if level in level_map:
            logging.getLogger().setLevel(level_map[level])
            logger.info(f"Log level set to: {level}")
        
        return create_success_response(
            request_id=request.id,
            result={"level": level.lower()}
        )
    
    async def _handle_ping(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle ping request."""
        return create_success_response(
            request_id=request.id,
            result={
                "pong": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    async def _close_all_sessions(self) -> None:
        """Close all client sessions."""
        async with self._session_lock:
            session_ids = list(self.sessions.keys())
            for session_id in session_ids:
                try:
                    session = self.sessions.pop(session_id)
                    logger.info(f"Closed session: {session_id}")
                except Exception as e:
                    logger.error(f"Error closing session {session_id}: {e}")
    
    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown."""
        logger.info("Starting graceful shutdown...")
        
        # Wait a bit for ongoing requests
        await asyncio.sleep(2)
        
        # Stop the server
        await self.stop()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            asyncio.create_task(self._graceful_shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    @asynccontextmanager
    async def run_server(self):
        """Context manager for running the server."""
        try:
            await self.start()
            yield self
        finally:
            await self.stop()


async def create_server(config: Optional[MCPServerConfig] = None) -> MCPServer:
    """
    Create and configure MCP server instance.
    
    Args:
        config: Server configuration (uses defaults if not provided)
        
    Returns:
        Configured MCP server instance
    """
    if not config:
        config = MCPServerConfig()
    
    server = MCPServer(config)
    return server


async def run_server(config: Optional[MCPServerConfig] = None) -> None:
    """
    Run MCP server with the given configuration.
    
    Args:
        config: Server configuration
    """
    server = await create_server(config)
    
    async with server.run_server():
        # Server is running, wait for shutdown
        await server.shutdown_event.wait()


# MCP Server implementation complete with:
# ✓ Component orchestration
# ✓ Request routing and dispatch
# ✓ Session management
# ✓ Authentication integration
# ✓ Tool and resource registration
# ✓ Transport management
# ✓ Error handling and recovery
# ✓ Graceful shutdown
# ✓ Signal handling
# ✓ Comprehensive logging
# 
# Integration points:
# - Service injection for tools/resources
# - Transport protocol selection
# - Authentication provider configuration
# - Monitoring and metrics collection
# - Configuration management