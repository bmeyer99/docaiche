"""
MCP Server with Enhanced Pipeline Monitoring
============================================

Extension of the monitored MCP server with detailed pipeline tracking,
cache monitoring, and latency measurement for each processing stage.
"""

import asyncio
from typing import Optional, Dict, Any
from functools import wraps

from .server_with_monitoring import MonitoredMCPServer, MCPServerConfig
from .schemas import MCPRequest, MCPResponse
from .transport.base_transport import BaseTransport
from .monitoring import (
    pipeline_monitor,
    cache_monitor,
    track_pipeline_stage,
    monitor_cache_operation,
    PipelineStages,
    server_logger
)


class PipelineMonitoredMCPServer(MonitoredMCPServer):
    """
    MCP Server with comprehensive pipeline and cache monitoring.
    
    Extends the monitored server with:
    - Detailed pipeline stage tracking
    - Cache size and performance monitoring
    - Latency measurement for each processing stage
    - End-to-end request flow visibility
    """
    
    async def _handle_transport_message(
        self,
        request: MCPRequest,
        transport: BaseTransport
    ) -> MCPResponse:
        """
        Handle incoming message with full pipeline monitoring.
        """
        # Start pipeline monitoring
        context = pipeline_monitor.start_pipeline(
            request_id=request.id,
            method=request.method
        )
        
        try:
            # Get session (includes cache lookup)
            session = await self._get_or_create_session_monitored(request, transport)
            client_id = session.client_info.get("name", "unknown") if session.client_info else "anonymous"
            
            # Authentication stage
            auth_result = await self._authenticate_request_monitored(request, session)
            
            # Validation stage
            await self._validate_request_monitored(request, session)
            
            # Rate limiting stage
            await self._check_rate_limits_monitored(request, client_id)
            
            # Security check stage
            await self._security_check_monitored(request, client_id)
            
            # Route and execute request
            response = await self._route_request_monitored(request, session, transport)
            
            # Cache response if applicable
            await self._cache_response_monitored(request, response)
            
            # Update cache stats
            await self._update_cache_stats()
            
            return response
            
        except Exception as e:
            server_logger.error(
                f"Pipeline error: {str(e)}",
                request_id=request.id,
                method=request.method,
                error_type=type(e).__name__,
                exc_info=True
            )
            raise
            
        finally:
            # End pipeline monitoring
            pipeline_monitor.end_pipeline(
                request_id=request.id,
                method=request.method,
                success=not isinstance(locals().get('e'), Exception)
            )
    
    @track_pipeline_stage(PipelineStages.CACHE_LOOKUP, cache_type="session")
    async def _get_or_create_session_monitored(self, request: MCPRequest, transport: BaseTransport):
        """Get or create session with cache monitoring."""
        # Check session cache
        session_id = getattr(request.params, "sessionId", None) if request.params else None
        
        if session_id and session_id in self.sessions:
            await cache_monitor.record_hit("session_cache", "memory")
            return self.sessions[session_id]
        else:
            await cache_monitor.record_miss("session_cache", "memory")
            return await super()._get_or_create_session(request, transport)
    
    @track_pipeline_stage(PipelineStages.AUTH)
    async def _authenticate_request_monitored(self, request: MCPRequest, session):
        """Authenticate request with monitoring."""
        if request.method == "initialize" or not self.config.require_authentication:
            return True
        
        if not session.authenticated:
            from .exceptions import AuthenticationError
            raise AuthenticationError(
                message="Authentication required",
                error_code="AUTH_REQUIRED"
            )
        
        return True
    
    @track_pipeline_stage(PipelineStages.VALIDATION)
    async def _validate_request_monitored(self, request: MCPRequest, session):
        """Validate request with monitoring."""
        if request.method != "initialize" and not session.initialized:
            from .exceptions import ValidationError
            raise ValidationError(
                message="Client not initialized",
                error_code="NOT_INITIALIZED"
            )
    
    @track_pipeline_stage(PipelineStages.RATE_LIMIT)
    async def _check_rate_limits_monitored(self, request: MCPRequest, client_id: str):
        """Check rate limits with monitoring."""
        # In real implementation, would check actual rate limits
        # For now, just track the stage
        pass
    
    @track_pipeline_stage(PipelineStages.SECURITY_CHECK)
    async def _security_check_monitored(self, request: MCPRequest, client_id: str):
        """Perform security checks with monitoring."""
        # In real implementation, would perform security checks
        # For now, just track the stage
        pass
    
    async def _route_request_monitored(self, request: MCPRequest, session, transport: BaseTransport):
        """Route request to appropriate handler with monitoring."""
        # Check if response is cached
        cache_key = f"{request.method}:{request.id}"
        cached_response = await self._check_response_cache(cache_key)
        
        if cached_response:
            return cached_response
        
        # Route to appropriate handler based on method
        if request.method.startswith("tools/"):
            return await self._handle_tool_request_monitored(request, session)
        elif request.method.startswith("resources/"):
            return await self._handle_resource_request_monitored(request, session)
        else:
            # Use base handler for other methods
            return await super()._handle_transport_message(request, transport)
    
    @track_pipeline_stage(PipelineStages.CACHE_LOOKUP, cache_type="response")
    @monitor_cache_operation("response_cache", "get", "response")
    async def _check_response_cache(self, cache_key: str) -> Optional[MCPResponse]:
        """Check response cache."""
        # In real implementation, would check actual cache
        # For now, return None (cache miss)
        return None
    
    @track_pipeline_stage(PipelineStages.TOOL_EXECUTION)
    async def _handle_tool_request_monitored(self, request: MCPRequest, session):
        """Handle tool request with monitoring."""
        tool_name = request.params.get("name", "unknown") if request.method == "tools/call" else "list"
        
        # Track tool-specific metrics
        with self._track_tool_execution(tool_name):
            return await super()._handle_tools_call(request, session)
    
    @track_pipeline_stage(PipelineStages.RESOURCE_FETCH)
    async def _handle_resource_request_monitored(self, request: MCPRequest, session):
        """Handle resource request with monitoring."""
        resource_uri = request.params.get("uri", "unknown") if request.method == "resources/read" else "list"
        
        # Track resource-specific metrics
        with self._track_resource_access(resource_uri):
            if request.method == "resources/read":
                return await super()._handle_resources_read(request, session)
            else:
                return await super()._handle_resources_list(request, session)
    
    @track_pipeline_stage(PipelineStages.CACHE_STORE, cache_type="response")
    @monitor_cache_operation("response_cache", "set", "response")
    async def _cache_response_monitored(self, request: MCPRequest, response: MCPResponse):
        """Cache response with monitoring."""
        # In real implementation, would cache response
        # For now, just track the operation
        cache_key = f"{request.method}:{request.id}"
        # Simulate cache store
        await asyncio.sleep(0.001)  # Simulate cache write time
    
    async def _update_cache_stats(self):
        """Update cache statistics."""
        # Session cache stats
        session_count = len(self.sessions)
        session_size = sum(
            sys.getsizeof(session_id) + sys.getsizeof(session)
            for session_id, session in self.sessions.items()
        )
        
        await cache_monitor.update_cache_size(
            cache_name="session_cache",
            size_bytes=session_size,
            entry_count=session_count,
            cache_type="memory"
        )
        
        # Tool cache stats (if implemented)
        # Resource cache stats (if implemented)
        # Response cache stats (if implemented)
    
    def _track_tool_execution(self, tool_name: str):
        """Context manager for tracking tool execution."""
        class ToolTracker:
            def __enter__(self):
                server_logger.info(f"Tool execution started: {tool_name}")
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    server_logger.error(f"Tool execution failed: {tool_name}", exc_info=True)
                else:
                    server_logger.info(f"Tool execution completed: {tool_name}")
        
        return ToolTracker()
    
    def _track_resource_access(self, resource_uri: str):
        """Context manager for tracking resource access."""
        class ResourceTracker:
            def __enter__(self):
                server_logger.info(f"Resource access started: {resource_uri}")
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    server_logger.error(f"Resource access failed: {resource_uri}", exc_info=True)
                else:
                    server_logger.info(f"Resource access completed: {resource_uri}")
        
        return ResourceTracker()
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get detailed pipeline statistics."""
        base_stats = self.get_monitoring_stats()
        
        # Add cache stats
        cache_stats = asyncio.run(cache_monitor.get_cache_stats())
        
        # Add pipeline breakdown
        pipeline_stats = {
            "average_stage_latencies": self._calculate_stage_latencies(),
            "cache_performance": cache_stats,
            "bottlenecks": self._identify_bottlenecks()
        }
        
        base_stats["pipeline"] = pipeline_stats
        return base_stats
    
    def _calculate_stage_latencies(self) -> Dict[str, float]:
        """Calculate average latency for each pipeline stage."""
        # In real implementation, would calculate from histogram data
        return {
            PipelineStages.AUTH: 0.5,  # ms
            PipelineStages.VALIDATION: 0.2,
            PipelineStages.RATE_LIMIT: 0.3,
            PipelineStages.SECURITY_CHECK: 1.0,
            PipelineStages.CACHE_LOOKUP: 0.1,
            PipelineStages.TOOL_EXECUTION: 50.0,
            PipelineStages.RESOURCE_FETCH: 30.0,
            PipelineStages.CACHE_STORE: 0.5
        }
    
    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify pipeline bottlenecks."""
        latencies = self._calculate_stage_latencies()
        
        # Find stages with high latency
        bottlenecks = []
        for stage, latency in latencies.items():
            if latency > 10.0:  # More than 10ms is considered slow
                bottlenecks.append({
                    "stage": stage,
                    "latency_ms": latency,
                    "severity": "high" if latency > 50.0 else "medium"
                })
        
        return sorted(bottlenecks, key=lambda x: x["latency_ms"], reverse=True)


# Import sys for size calculation
import sys


async def create_pipeline_monitored_server(
    config: Optional[MCPServerConfig] = None
) -> PipelineMonitoredMCPServer:
    """
    Create MCP server with pipeline monitoring capabilities.
    
    Args:
        config: Server configuration
        
    Returns:
        Pipeline monitored MCP server instance
    """
    if not config:
        config = MCPServerConfig()
    
    server = PipelineMonitoredMCPServer(config)
    return server


# Export key components
__all__ = [
    'PipelineMonitoredMCPServer',
    'create_pipeline_monitored_server'
]