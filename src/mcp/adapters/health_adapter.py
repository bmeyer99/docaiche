"""
Health Adapter for MCP to FastAPI Integration
============================================

Adapts MCP status resource requests to DocaiChe FastAPI health endpoints,
handling system health checks, metrics, analytics, and monitoring data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base_adapter import BaseAdapter
from ..schemas import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class HealthAdapter(BaseAdapter):
    """
    Adapter for MCP health/status operations to FastAPI health endpoints.
    
    Handles:
    - System health checks
    - Component status monitoring
    - Performance metrics
    - Usage analytics
    - Resource utilization
    """
    
    async def adapt_request(self, mcp_request: MCPRequest) -> Dict[str, Any]:
        """
        Adapt MCP health check request to FastAPI format.
        
        Health checks typically don't require complex request transformation.
        """
        params = mcp_request.params or {}
        
        # Build health check request
        adapted = {
            'include_details': params.get('include_details', True),
            'check_dependencies': params.get('check_dependencies', True),
            'timeout': params.get('timeout', 5)
        }
        
        # Add specific component checks if requested
        if 'components' in params:
            adapted['components'] = params['components']
        
        return adapted
    
    async def adapt_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt FastAPI health response to MCP format.
        
        Transforms FastAPI HealthResponse to MCP-compatible format with
        comprehensive status information.
        """
        # Build MCP health response
        adapted = {
            'status': api_response.get('status', 'unknown'),
            'timestamp': api_response.get('timestamp', datetime.now(timezone.utc).isoformat()),
            'version': api_response.get('version', 'unknown'),
            'uptime_seconds': api_response.get('uptime_seconds', 0)
        }
        
        # Add component health details
        if 'components' in api_response:
            components = {}
            for comp_name, comp_data in api_response['components'].items():
                components[comp_name] = {
                    'status': comp_data.get('status', 'unknown'),
                    'message': comp_data.get('message', ''),
                    'last_check': comp_data.get('last_check', ''),
                    'metadata': comp_data.get('metadata', {})
                }
            adapted['components'] = components
        
        # Add system metrics
        if 'metrics' in api_response:
            adapted['metrics'] = {
                'cpu_usage': api_response['metrics'].get('cpu_usage', 0),
                'memory_usage': api_response['metrics'].get('memory_usage', 0),
                'disk_usage': api_response['metrics'].get('disk_usage', 0),
                'active_connections': api_response['metrics'].get('active_connections', 0),
                'request_rate': api_response['metrics'].get('request_rate', 0)
            }
        
        # Add service dependencies
        if 'dependencies' in api_response:
            adapted['dependencies'] = api_response['dependencies']
        
        # Calculate overall health score
        if 'components' in adapted:
            healthy_count = sum(
                1 for c in adapted['components'].values() 
                if c['status'] == 'healthy'
            )
            total_count = len(adapted['components'])
            adapted['health_score'] = (healthy_count / total_count * 100) if total_count > 0 else 0
        
        return adapted
    
    async def check_health(self, mcp_request: MCPRequest) -> MCPResponse:
        """
        Execute system health check.
        
        Main entry point for health status checks.
        """
        return await self.execute(
            mcp_request=mcp_request,
            method='GET',
            endpoint='/health'
        )
    
    async def get_stats(self, mcp_request: MCPRequest) -> MCPResponse:
        """
        Get system usage statistics.
        
        Retrieves detailed usage and performance statistics.
        """
        params = mcp_request.params or {}
        
        try:
            # Get stats from API
            api_response = await self._make_request(
                method='GET',
                endpoint='/stats',
                params={
                    'include_history': params.get('include_history', False),
                    'time_range': params.get('time_range', '1h')
                }
            )
            
            # Adapt stats response
            adapted = {
                'current_stats': {
                    'total_requests': api_response.get('total_requests', 0),
                    'total_documents': api_response.get('total_documents', 0),
                    'total_searches': api_response.get('total_searches', 0),
                    'active_users': api_response.get('active_users', 0),
                    'cache_hit_rate': api_response.get('cache_hit_rate', 0),
                    'average_response_time': api_response.get('average_response_time', 0)
                },
                'resource_usage': {
                    'cpu_percent': api_response.get('cpu_percent', 0),
                    'memory_mb': api_response.get('memory_mb', 0),
                    'disk_gb': api_response.get('disk_gb', 0),
                    'network_mbps': api_response.get('network_mbps', 0)
                }
            }
            
            # Add historical data if available
            if 'history' in api_response:
                adapted['history'] = api_response['history']
            
            # Add top operations
            if 'top_operations' in api_response:
                adapted['top_operations'] = api_response['top_operations']
            
            return MCPResponse(
                id=mcp_request.id,
                result=adapted
            )
        
        except Exception as e:
            logger.error(
                f"Stats retrieval failed: {str(e)}",
                exc_info=True
            )
            raise
    
    async def get_analytics(self, mcp_request: MCPRequest) -> MCPResponse:
        """
        Get system analytics data.
        
        Retrieves analytics data for specified time range with
        insights and trends.
        """
        params = mcp_request.params or {}
        
        try:
            # Get analytics from API
            api_response = await self._make_request(
                method='GET',
                endpoint='/analytics',
                params={
                    'time_range': params.get('time_range', '7d'),
                    'granularity': params.get('granularity', 'hour'),
                    'metrics': params.get('metrics', ['requests', 'errors', 'latency'])
                }
            )
            
            # Adapt analytics response
            adapted = {
                'time_range': api_response.get('time_range', ''),
                'granularity': api_response.get('granularity', ''),
                'metrics': {}
            }
            
            # Process each metric
            for metric_name, metric_data in api_response.get('metrics', {}).items():
                adapted['metrics'][metric_name] = {
                    'data_points': metric_data.get('data_points', []),
                    'total': metric_data.get('total', 0),
                    'average': metric_data.get('average', 0),
                    'min': metric_data.get('min', 0),
                    'max': metric_data.get('max', 0),
                    'trend': metric_data.get('trend', 'stable')
                }
            
            # Add insights
            if 'insights' in api_response:
                adapted['insights'] = api_response['insights']
            
            # Add anomalies
            if 'anomalies' in api_response:
                adapted['anomalies'] = api_response['anomalies']
            
            return MCPResponse(
                id=mcp_request.id,
                result=adapted
            )
        
        except Exception as e:
            logger.error(
                f"Analytics retrieval failed: {str(e)}",
                exc_info=True
            )
            raise
    
    async def get_monitoring(self, mcp_request: MCPRequest) -> MCPResponse:
        """
        Get monitoring service information.
        
        Retrieves information about monitoring services, alerts,
        and operational status.
        """
        params = mcp_request.params or {}
        
        try:
            # Get monitoring info from API
            api_response = await self._make_request(
                method='GET',
                endpoint='/monitoring'
            )
            
            # Adapt monitoring response
            adapted = {
                'monitoring_enabled': api_response.get('monitoring_enabled', False),
                'services': {}
            }
            
            # Process monitoring services
            for service_name, service_data in api_response.get('services', {}).items():
                adapted['services'][service_name] = {
                    'enabled': service_data.get('enabled', False),
                    'status': service_data.get('status', 'unknown'),
                    'last_check': service_data.get('last_check', ''),
                    'alerts': service_data.get('alerts', []),
                    'configuration': service_data.get('configuration', {})
                }
            
            # Add active alerts
            if 'active_alerts' in api_response:
                adapted['active_alerts'] = [
                    {
                        'id': alert.get('id', ''),
                        'severity': alert.get('severity', 'info'),
                        'title': alert.get('title', ''),
                        'description': alert.get('description', ''),
                        'created_at': alert.get('created_at', ''),
                        'service': alert.get('service', '')
                    }
                    for alert in api_response['active_alerts']
                ]
            
            # Add metrics endpoints
            if 'metrics_endpoints' in api_response:
                adapted['metrics_endpoints'] = api_response['metrics_endpoints']
            
            return MCPResponse(
                id=mcp_request.id,
                result=adapted
            )
        
        except Exception as e:
            logger.error(
                f"Monitoring info retrieval failed: {str(e)}",
                exc_info=True
            )
            raise
    
    async def check_component(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Check health of a specific component.
        
        Performs detailed health check on a specific system component.
        """
        params = mcp_request.params or {}
        component = params.get('component', '')
        
        if not component:
            # Return list of available components
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'available_components': [
                        'database',
                        'cache',
                        'search_engine',
                        'ai_service',
                        'storage',
                        'message_queue'
                    ]
                }
            )
        
        try:
            # Check specific component
            health_response = await self.check_health(mcp_request)
            components = health_response.result.get('components', {})
            
            if component in components:
                component_health = components[component]
                return MCPResponse(
                    id=mcp_request.id,
                    result={
                        'component': component,
                        'health': component_health,
                        'recommendations': self._get_component_recommendations(
                            component,
                            component_health
                        )
                    }
                )
            else:
                return MCPResponse(
                    id=mcp_request.id,
                    result={
                        'component': component,
                        'health': {
                            'status': 'not_found',
                            'message': f'Component {component} not found'
                        }
                    }
                )
        
        except Exception as e:
            logger.error(
                f"Component health check failed: {str(e)}",
                extra={"component": component},
                exc_info=True
            )
            raise
    
    def _get_component_recommendations(
        self,
        component: str,
        health: Dict[str, Any]
    ) -> List[str]:
        """
        Get recommendations based on component health status.
        
        Provides actionable recommendations for improving component health.
        """
        recommendations = []
        status = health.get('status', 'unknown')
        
        if status == 'degraded':
            if component == 'database':
                recommendations.append("Consider optimizing database queries")
                recommendations.append("Check for long-running transactions")
            elif component == 'cache':
                recommendations.append("Monitor cache hit rates")
                recommendations.append("Consider increasing cache size")
            elif component == 'search_engine':
                recommendations.append("Rebuild search indices if needed")
                recommendations.append("Check search query performance")
        
        elif status == 'unhealthy':
            recommendations.append(f"Immediate attention required for {component}")
            recommendations.append("Check service logs for errors")
            recommendations.append("Verify service configuration")
        
        return recommendations


# Health adapter complete with:
# ✓ System health checks
# ✓ Component status monitoring
# ✓ Usage statistics
# ✓ Analytics data retrieval
# ✓ Monitoring service info
# ✓ Component-specific checks
# ✓ Health recommendations
# ✓ Alert management