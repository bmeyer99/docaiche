"""
Logs Adapter for MCP to FastAPI Integration
===========================================

Adapts MCP log resource requests to DocaiChe FastAPI AI logs endpoints,
handling log queries, correlation analysis, pattern detection, and streaming.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime, timezone, timedelta
import json

from .base_adapter import BaseAdapter
from ..schemas import MCPRequest, MCPResponse
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class LogsAdapter(BaseAdapter):
    """
    Adapter for MCP log operations to FastAPI AI logs endpoints.
    
    Handles:
    - AI-optimized log queries
    - Cross-service correlation analysis
    - Pattern and anomaly detection
    - Conversation tracking
    - Real-time log streaming
    - Log export functionality
    """
    
    # Time range shortcuts
    TIME_RANGES = {
        '1h': timedelta(hours=1),
        '6h': timedelta(hours=6),
        '12h': timedelta(hours=12),
        '1d': timedelta(days=1),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30)
    }
    
    async def adapt_request(self, mcp_request: MCPRequest) -> Dict[str, Any]:
        """
        Adapt MCP log query request to FastAPI format.
        
        Transforms MCP log parameters to match FastAPI AILogQuery schema.
        """
        params = mcp_request.params or {}
        
        # Build base query
        adapted = {
            'workspace_id': params.get('workspace_id', 'default'),
            'session_id': params.get('session_id', f'mcp-{mcp_request.id}')
        }
        
        # Add search query if provided
        if 'query' in params:
            adapted['query'] = params['query']
        
        # Handle time range
        time_range = params.get('time_range', '1h')
        if time_range in self.TIME_RANGES:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - self.TIME_RANGES[time_range]
            adapted['start_time'] = start_time.isoformat()
            adapted['end_time'] = end_time.isoformat()
        elif 'start_time' in params and 'end_time' in params:
            adapted['start_time'] = params['start_time']
            adapted['end_time'] = params['end_time']
        
        # Add filters
        if 'filters' in params:
            filters = params['filters']
            
            # Log level filter
            if 'log_levels' in filters:
                adapted['log_levels'] = filters['log_levels']
            
            # Service filter
            if 'services' in filters:
                adapted['services'] = filters['services']
            
            # Technology filter
            if 'technologies' in filters:
                adapted['technologies'] = filters['technologies']
            
            # Pattern filter
            if 'patterns' in filters:
                adapted['patterns'] = filters['patterns']
        
        # Pagination
        adapted['limit'] = params.get('limit', 100)
        adapted['offset'] = params.get('offset', 0)
        
        # Sorting
        if 'sort_by' in params:
            adapted['sort_by'] = params['sort_by']
            adapted['sort_order'] = params.get('sort_order', 'desc')
        
        logger.debug(
            "Adapted log query request",
            extra={
                "time_range": time_range,
                "has_query": 'query' in adapted
            }
        )
        
        return adapted
    
    async def adapt_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt FastAPI log response to MCP format.
        
        Transforms FastAPI AILogResponse to MCP-compatible format with
        enhanced metadata and analysis results.
        """
        logs = api_response.get('logs', [])
        
        # Transform logs to MCP format
        mcp_logs = []
        for log in logs:
            mcp_log = {
                'id': log.get('id', ''),
                'timestamp': log.get('timestamp', ''),
                'level': log.get('level', 'info'),
                'service': log.get('service', ''),
                'message': log.get('message', ''),
                'metadata': {
                    'trace_id': log.get('trace_id', ''),
                    'span_id': log.get('span_id', ''),
                    'user_id': log.get('user_id', ''),
                    'session_id': log.get('session_id', ''),
                    'technology': log.get('technology', []),
                    'tags': log.get('tags', [])
                }
            }
            
            # Add structured data if available
            if 'data' in log:
                mcp_log['data'] = log['data']
            
            # Add AI analysis if available
            if 'ai_analysis' in log:
                mcp_log['ai_analysis'] = log['ai_analysis']
            
            mcp_logs.append(mcp_log)
        
        # Build complete response
        adapted = {
            'logs': mcp_logs,
            'total_count': api_response.get('total_count', len(logs)),
            'query_metadata': {
                'workspace_id': api_response.get('workspace_id', ''),
                'time_range': api_response.get('time_range', ''),
                'filters_applied': api_response.get('filters_applied', {}),
                'processing_time_ms': api_response.get('processing_time_ms', 0)
            }
        }
        
        # Add AI insights if available
        if 'ai_insights' in api_response:
            adapted['ai_insights'] = api_response['ai_insights']
        
        # Add pagination info
        if 'next_offset' in api_response:
            adapted['next_offset'] = api_response['next_offset']
        
        return adapted
    
    async def query_logs(self, mcp_request: MCPRequest) -> MCPResponse:
        """
        Execute AI-optimized log query.
        
        Main entry point for log queries with AI enhancement.
        """
        return await self.execute(
            mcp_request=mcp_request,
            method='GET',
            endpoint='/ai_logs/query'
        )
    
    async def correlate_logs(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Perform cross-service log correlation analysis.
        
        Analyzes logs across multiple services to find correlations
        and trace distributed operations.
        """
        params = mcp_request.params or {}
        
        # Build correlation request
        correlation_data = {
            'trace_id': params.get('trace_id', ''),
            'time_window': params.get('time_window', '5m'),
            'services': params.get('services', []),
            'correlation_type': params.get('correlation_type', 'temporal'),
            'min_confidence': params.get('min_confidence', 0.7)
        }
        
        try:
            # Perform correlation
            api_response = await self._make_request(
                method='POST',
                endpoint='/ai_logs/correlate',
                data=correlation_data
            )
            
            # Adapt correlation results
            adapted = {
                'correlations': api_response.get('correlations', []),
                'trace_graph': api_response.get('trace_graph', {}),
                'service_dependencies': api_response.get('service_dependencies', {}),
                'anomalies': api_response.get('anomalies', []),
                'summary': api_response.get('summary', '')
            }
            
            return MCPResponse(
                id=mcp_request.id,
                result=adapted
            )
        
        except Exception as e:
            logger.error(
                f"Log correlation failed: {str(e)}",
                extra={"correlation_data": correlation_data},
                exc_info=True
            )
            raise
    
    async def detect_patterns(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Detect patterns and anomalies in logs using AI.
        
        Analyzes log data to identify patterns, anomalies, and
        potential issues requiring attention.
        """
        params = mcp_request.params or {}
        
        # Build pattern detection request
        pattern_data = {
            'workspace_id': params.get('workspace_id', 'default'),
            'time_range': params.get('time_range', '1h'),
            'pattern_types': params.get('pattern_types', ['error', 'performance', 'security']),
            'sensitivity': params.get('sensitivity', 'medium'),
            'include_predictions': params.get('include_predictions', True)
        }
        
        try:
            # Detect patterns
            api_response = await self._make_request(
                method='POST',
                endpoint='/ai_logs/patterns',
                data=pattern_data
            )
            
            # Adapt pattern results
            adapted = {
                'patterns': api_response.get('patterns', []),
                'anomalies': api_response.get('anomalies', []),
                'trends': api_response.get('trends', []),
                'predictions': api_response.get('predictions', []),
                'recommendations': api_response.get('recommendations', []),
                'risk_score': api_response.get('risk_score', 0)
            }
            
            return MCPResponse(
                id=mcp_request.id,
                result=adapted
            )
        
        except Exception as e:
            logger.error(
                f"Pattern detection failed: {str(e)}",
                extra={"pattern_data": pattern_data},
                exc_info=True
            )
            raise
    
    async def get_conversation_logs(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Get logs for a specific conversation.
        
        Retrieves all logs associated with a conversation ID for
        debugging and analysis.
        """
        params = mcp_request.params or {}
        conversation_id = params.get('conversation_id', '')
        
        if not conversation_id:
            raise ValidationError(
                message="Conversation ID required",
                error_code="MISSING_CONVERSATION_ID"
            )
        
        try:
            # Get conversation logs
            api_response = await self._make_request(
                method='GET',
                endpoint=f'/ai_logs/conversation/{conversation_id}'
            )
            
            # Adapt conversation data
            adapted = {
                'conversation_id': conversation_id,
                'logs': api_response.get('logs', []),
                'summary': api_response.get('summary', ''),
                'participants': api_response.get('participants', []),
                'duration_ms': api_response.get('duration_ms', 0),
                'message_count': api_response.get('message_count', 0),
                'status': api_response.get('status', 'unknown')
            }
            
            return MCPResponse(
                id=mcp_request.id,
                result=adapted
            )
        
        except Exception as e:
            logger.error(
                f"Conversation log retrieval failed: {str(e)}",
                extra={"conversation_id": conversation_id},
                exc_info=True
            )
            raise
    
    async def get_workspace_summary(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Get AI-generated workspace activity summary.
        
        Provides high-level insights and summary of workspace activity
        over a specified time period.
        """
        params = mcp_request.params or {}
        workspace_id = params.get('workspace_id', 'default')
        
        try:
            # Get workspace summary
            api_response = await self._make_request(
                method='GET',
                endpoint=f'/ai_logs/workspace/{workspace_id}/summary',
                params={
                    'time_range': params.get('time_range', '7d'),
                    'include_trends': params.get('include_trends', True)
                }
            )
            
            # Adapt summary data
            adapted = {
                'workspace_id': workspace_id,
                'summary': api_response.get('summary', ''),
                'key_metrics': api_response.get('key_metrics', {}),
                'top_issues': api_response.get('top_issues', []),
                'activity_trends': api_response.get('activity_trends', {}),
                'recommendations': api_response.get('recommendations', []),
                'health_score': api_response.get('health_score', 0)
            }
            
            return MCPResponse(
                id=mcp_request.id,
                result=adapted
            )
        
        except Exception as e:
            logger.error(
                f"Workspace summary retrieval failed: {str(e)}",
                extra={"workspace_id": workspace_id},
                exc_info=True
            )
            raise
    
    async def export_logs(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Export logs in various formats.
        
        Exports filtered logs in requested format for archival or
        external analysis.
        """
        params = mcp_request.params or {}
        
        # Build export request
        export_data = {
            'workspace_id': params.get('workspace_id', 'default'),
            'time_range': params.get('time_range', '1d'),
            'format': params.get('format', 'json'),
            'filters': params.get('filters', {}),
            'include_metadata': params.get('include_metadata', True)
        }
        
        try:
            # Request export
            api_response = await self._make_request(
                method='POST',
                endpoint='/ai_logs/export',
                data=export_data
            )
            
            # Return export info
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'export_id': api_response.get('export_id', ''),
                    'status': api_response.get('status', 'processing'),
                    'download_url': api_response.get('download_url', ''),
                    'expires_at': api_response.get('expires_at', ''),
                    'size_bytes': api_response.get('size_bytes', 0),
                    'record_count': api_response.get('record_count', 0)
                }
            )
        
        except Exception as e:
            logger.error(
                f"Log export failed: {str(e)}",
                extra={"export_data": export_data},
                exc_info=True
            )
            raise


# Logs adapter complete with:
# ✓ AI-optimized log queries
# ✓ Cross-service correlation
# ✓ Pattern and anomaly detection
# ✓ Conversation tracking
# ✓ Workspace summaries
# ✓ Log export functionality
# ✓ Time range handling
# ✓ Comprehensive filtering