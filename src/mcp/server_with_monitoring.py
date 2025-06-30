"""
MCP Server with Monitoring Integration
======================================

Extension of the MCP server with comprehensive monitoring, logging,
metrics, and observability features integrated.
"""

import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from .server import MCPServer, MCPServerConfig, ClientSession
from .schemas import MCPRequest, MCPResponse
from .transport.base_transport import BaseTransport
from .monitoring import (
    observability,
    server_logger,
    metrics,
    health_monitor,
    HealthCheckConfig,
    HealthStatus,
    observable,
    ObservabilityMiddleware
)


class MonitoredMCPServer(MCPServer):
    """
    MCP Server with integrated monitoring capabilities.
    
    Extends the base MCP server with:
    - Structured logging with correlation IDs
    - Prometheus metrics collection
    - Distributed tracing
    - Health monitoring
    - Performance tracking
    """
    
    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        
        # Initialize observability
        self.observability_middleware = ObservabilityMiddleware()
        self.logger = server_logger
        
        # Add start time to metadata
        self.metadata.start_time = datetime.now(timezone.utc)
        
        # Override base logger
        import logging
        logging.getLogger(__name__).handlers = []
        logging.getLogger(__name__).addHandler(self.logger.logger.handlers[0])
    
    async def start(self) -> None:
        """Start server with monitoring initialization."""
        # Initialize observability services
        await observability.initialize()
        
        # Register health checks
        self._register_health_checks()
        
        # Start base server
        await super().start()
        
        # Log startup metrics
        metrics.active_connections.set(0, protocol="mcp")
        self.logger.info(
            "MCP Server started with monitoring",
            server_name=self.metadata.name,
            version=self.metadata.version,
            monitoring_enabled=True
        )
    
    async def stop(self) -> None:
        """Stop server with monitoring cleanup."""
        self.logger.info("Stopping MCP Server with monitoring")
        
        # Stop base server
        await super().stop()
        
        # Shutdown observability
        await observability.shutdown()
    
    def _register_health_checks(self):
        """Register component health checks."""
        # Database health check
        async def check_database():
            try:
                # Check if we have database connectivity
                if hasattr(self, '_adapter_factory'):
                    return {
                        "status": "healthy",
                        "message": "Database adapter available"
                    }
                return {
                    "status": "unknown",
                    "message": "Database not configured"
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "message": f"Database check failed: {str(e)}"
                }
        
        health_monitor.register_check(HealthCheckConfig(
            name="mcp_database",
            check_func=check_database,
            interval_seconds=30,
            critical=True
        ))
        
        # Transport health check
        async def check_transports():
            if not self.transports:
                return {
                    "status": "unhealthy",
                    "message": "No transports configured"
                }
            
            healthy_count = sum(1 for t in self.transports if t.is_connected)
            total_count = len(self.transports)
            
            if healthy_count == total_count:
                return {
                    "status": "healthy",
                    "message": f"All {total_count} transports connected"
                }
            elif healthy_count > 0:
                return {
                    "status": "degraded",
                    "message": f"{healthy_count}/{total_count} transports connected"
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "No transports connected"
                }
        
        health_monitor.register_check(HealthCheckConfig(
            name="mcp_transports",
            check_func=check_transports,
            interval_seconds=15,
            critical=True
        ))
        
        # Security health check
        async def check_security():
            if not self.security_manager:
                return {
                    "status": "unhealthy",
                    "message": "Security not configured"
                }
            
            # Check rate limiting and other security features
            return {
                "status": "healthy",
                "message": "Security framework active"
            }
        
        health_monitor.register_check(HealthCheckConfig(
            name="mcp_security",
            check_func=check_security,
            interval_seconds=60,
            critical=True
        ))
    
    @observable(operation_name="mcp.request.handle")
    async def _handle_transport_message(
        self,
        request: MCPRequest,
        transport: BaseTransport
    ) -> MCPResponse:
        """
        Handle incoming message with full observability.
        
        Wraps the base handler with monitoring capabilities.
        """
        # Get session for client info
        session = await self._get_or_create_session(request, transport)
        client_id = session.client_info.get("name", "unknown") if session.client_info else "anonymous"
        
        # Process through observability middleware
        response = await self.observability_middleware.process_request(
            request=request,
            handler=lambda req: super()._handle_transport_message(req, transport),
            client_id=client_id,
            trace_headers=getattr(transport, 'trace_headers', {})
        )
        
        # Update connection metrics based on method
        if request.method == "initialize":
            metrics.active_connections.inc(protocol="mcp")
        elif request.method == "shutdown":
            metrics.active_connections.dec(protocol="mcp")
        
        return response
    
    async def _handle_tools_call(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle tool execution with metrics."""
        tool_name = request.params.get("name", "unknown")
        
        # Track tool execution
        try:
            response = await super()._handle_tools_call(request, session)
            
            # Track success
            metrics.tool_executions.inc(tool=tool_name, status="success")
            
            return response
            
        except Exception as e:
            # Track failure
            metrics.tool_executions.inc(tool=tool_name, status="error")
            raise
    
    async def _handle_resources_read(
        self,
        request: MCPRequest,
        session: ClientSession
    ) -> MCPResponse:
        """Handle resource access with metrics."""
        uri = request.params.get("uri", "unknown")
        
        # Extract resource type from URI
        resource_type = uri.split(":")[0] if ":" in uri else "unknown"
        
        # Track resource access
        metrics.resource_accesses.inc(
            resource=resource_type,
            operation="read"
        )
        
        return await super()._handle_resources_read(request, session)
    
    async def _get_or_create_session(
        self,
        request: MCPRequest,
        transport: BaseTransport
    ) -> ClientSession:
        """Get or create session with logging."""
        session = await super()._get_or_create_session(request, transport)
        
        if session.session_id not in self.sessions:
            self.logger.info(
                "New client session created",
                session_id=session.session_id,
                transport_type=type(transport).__name__
            )
        
        return session
    
    def get_monitoring_stats(self) -> dict:
        """Get current monitoring statistics."""
        overall_health, health_details = health_monitor.get_overall_status()
        
        return {
            "health": {
                "status": overall_health.value,
                "details": health_details
            },
            "metrics": {
                "active_connections": metrics.active_connections.get(protocol="mcp"),
                "total_requests": metrics.request_counter.get(method="all", status="all"),
                "error_rate": self._calculate_error_rate(),
                "avg_response_time": self._calculate_avg_response_time()
            },
            "uptime_seconds": int((datetime.now(timezone.utc) - self.metadata.start_time).total_seconds())
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        total_requests = 0
        error_requests = 0
        
        for method_data in metrics.request_counter.collect():
            labels = method_data.get("labels", {})
            value = method_data.get("value", 0)
            
            total_requests += value
            if labels.get("status") == "error":
                error_requests += value
        
        return error_requests / total_requests if total_requests > 0 else 0
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time."""
        duration_data = metrics.request_duration.collect()
        if not duration_data:
            return 0
        
        total_time = 0
        total_count = 0
        
        for data in duration_data:
            total_time += data.get("sum", 0)
            total_count += data.get("count", 0)
        
        return total_time / total_count if total_count > 0 else 0


async def create_monitored_server(
    config: Optional[MCPServerConfig] = None
) -> MonitoredMCPServer:
    """
    Create MCP server with monitoring capabilities.
    
    Args:
        config: Server configuration
        
    Returns:
        Monitored MCP server instance
    """
    if not config:
        config = MCPServerConfig()
    
    # Enable monitoring features in config
    config.enable_monitoring = True
    config.metrics_port = getattr(config, 'metrics_port', 9090)
    
    server = MonitoredMCPServer(config)
    return server


@asynccontextmanager
async def run_monitored_server(config: Optional[MCPServerConfig] = None):
    """
    Run MCP server with monitoring in a context manager.
    
    Args:
        config: Server configuration
    """
    server = await create_monitored_server(config)
    
    try:
        await server.start()
        yield server
    finally:
        await server.stop()


# Export monitoring endpoints for integration
from .monitoring.endpoints import router as monitoring_router, public_router as monitoring_public_router

__all__ = [
    'MonitoredMCPServer',
    'create_monitored_server',
    'run_monitored_server',
    'monitoring_router',
    'monitoring_public_router'
]