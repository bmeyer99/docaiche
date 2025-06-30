"""
Search Adapter for MCP to FastAPI Integration
=============================================

Adapts MCP search tool requests to DocaiChe FastAPI search endpoints,
handling query transformation, result formatting, and feedback integration.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base_adapter import BaseAdapter
from ..schemas import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class SearchAdapter(BaseAdapter):
    """
    Adapter for MCP search operations to FastAPI search endpoints.
    
    Handles:
    - Search query transformation
    - Result ranking and formatting
    - Feedback submission
    - Signal tracking for relevance
    """
    
    async def adapt_request(self, mcp_request: MCPRequest) -> Dict[str, Any]:
        """
        Adapt MCP search request to FastAPI format.
        
        Transforms MCP search parameters to match FastAPI SearchRequest schema.
        """
        params = mcp_request.params or {}
        
        # Extract search parameters
        query = params.get('query', '')
        filters = params.get('filters', {})
        limit = params.get('limit', 10)
        offset = params.get('offset', 0)
        
        # Build FastAPI search request
        adapted = {
            'query': query,
            'limit': min(limit, 100),  # Cap at 100 for safety
            'offset': offset,
            'session_id': params.get('session_id', f'mcp-{mcp_request.id}')
        }
        
        # Add optional filters
        if filters:
            # Technology filter
            if 'technologies' in filters:
                adapted['technologies'] = filters['technologies']
            
            # Time range filter
            if 'time_range' in filters:
                adapted['time_range'] = filters['time_range']
            
            # Document type filter
            if 'doc_types' in filters:
                adapted['doc_types'] = filters['doc_types']
            
            # Source filter
            if 'sources' in filters:
                adapted['sources'] = filters['sources']
        
        # Add search options
        if 'options' in params:
            options = params['options']
            
            # Fuzzy search
            if 'fuzzy' in options:
                adapted['fuzzy_search'] = options['fuzzy']
            
            # Semantic search
            if 'semantic' in options:
                adapted['use_semantic'] = options['semantic']
            
            # Include snippets
            if 'include_snippets' in options:
                adapted['include_snippets'] = options['include_snippets']
        
        logger.debug(
            "Adapted search request",
            extra={
                "mcp_query": query,
                "adapted_request": adapted
            }
        )
        
        return adapted
    
    async def adapt_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt FastAPI search response to MCP format.
        
        Transforms FastAPI SearchResponse to MCP-compatible format with
        enhanced metadata and relevance scoring.
        """
        results = api_response.get('results', [])
        
        # Transform results to MCP format
        mcp_results = []
        for idx, result in enumerate(results):
            mcp_result = {
                'id': result.get('id', f'doc-{idx}'),
                'title': result.get('title', 'Untitled'),
                'content': result.get('content', ''),
                'url': result.get('url', ''),
                'score': result.get('score', 0.0),
                'metadata': {
                    'source': result.get('source', 'unknown'),
                    'technology': result.get('technology', []),
                    'doc_type': result.get('doc_type', 'unknown'),
                    'created_at': result.get('created_at', ''),
                    'updated_at': result.get('updated_at', ''),
                    'language': result.get('language', 'en'),
                    'tags': result.get('tags', [])
                }
            }
            
            # Add snippet if available
            if 'snippet' in result:
                mcp_result['snippet'] = result['snippet']
            
            # Add highlights if available
            if 'highlights' in result:
                mcp_result['highlights'] = result['highlights']
            
            mcp_results.append(mcp_result)
        
        # Build complete response
        adapted = {
            'results': mcp_results,
            'total_count': api_response.get('total_count', len(results)),
            'search_metadata': {
                'query': api_response.get('query', ''),
                'search_type': api_response.get('search_type', 'hybrid'),
                'processing_time_ms': api_response.get('processing_time_ms', 0),
                'session_id': api_response.get('session_id', ''),
                'filters_applied': api_response.get('filters_applied', {})
            }
        }
        
        # Add pagination info
        if 'next_offset' in api_response:
            adapted['next_offset'] = api_response['next_offset']
        
        # Add suggestions if available
        if 'suggestions' in api_response:
            adapted['suggestions'] = api_response['suggestions']
        
        # Add related searches if available
        if 'related_searches' in api_response:
            adapted['related_searches'] = api_response['related_searches']
        
        logger.debug(
            "Adapted search response",
            extra={
                "result_count": len(mcp_results),
                "total_count": adapted['total_count']
            }
        )
        
        return adapted
    
    async def search(self, mcp_request: MCPRequest) -> MCPResponse:
        """
        Execute search operation.
        
        Main entry point for search operations, handling the complete
        search flow from MCP request to response.
        """
        return await self.execute(
            mcp_request=mcp_request,
            method='POST',
            endpoint='/search'
        )
    
    async def submit_feedback(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Submit search feedback for relevance improvement.
        
        Handles feedback submission to improve search quality and ranking.
        """
        params = mcp_request.params or {}
        
        # Build feedback request
        feedback_data = {
            'session_id': params.get('session_id', f'mcp-{mcp_request.id}'),
            'query': params.get('query', ''),
            'result_id': params.get('result_id', ''),
            'relevance_score': params.get('relevance_score', 0),
            'feedback_type': params.get('feedback_type', 'explicit'),
            'comments': params.get('comments', ''),
            'metadata': {
                'source': 'mcp',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_agent': 'MCP-SearchAdapter/1.0'
            }
        }
        
        try:
            # Submit feedback
            api_response = await self._make_request(
                method='POST',
                endpoint='/feedback',
                data=feedback_data
            )
            
            # Return success response
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'status': 'success',
                    'feedback_id': api_response.get('feedback_id', ''),
                    'message': 'Feedback submitted successfully'
                }
            )
        
        except Exception as e:
            logger.error(
                f"Feedback submission failed: {str(e)}",
                extra={"feedback_data": feedback_data},
                exc_info=True
            )
            raise
    
    async def track_signal(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Track implicit user signals for search improvement.
        
        Records user interactions like clicks, dwell time, and other
        implicit signals to improve search relevance.
        """
        params = mcp_request.params or {}
        
        # Build signal request
        signal_data = {
            'session_id': params.get('session_id', f'mcp-{mcp_request.id}'),
            'signal_type': params.get('signal_type', 'click'),
            'result_id': params.get('result_id', ''),
            'query': params.get('query', ''),
            'position': params.get('position', 0),
            'dwell_time_ms': params.get('dwell_time_ms', 0),
            'metadata': params.get('metadata', {})
        }
        
        try:
            # Submit signal
            api_response = await self._make_request(
                method='POST',
                endpoint='/signals',
                data=signal_data
            )
            
            # Return success response
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'status': 'success',
                    'signal_id': api_response.get('signal_id', ''),
                    'message': 'Signal tracked successfully'
                }
            )
        
        except Exception as e:
            logger.error(
                f"Signal tracking failed: {str(e)}",
                extra={"signal_data": signal_data},
                exc_info=True
            )
            raise
    
    async def get_suggestions(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Get search suggestions based on partial query.
        
        Provides autocomplete and query suggestions for improved
        search experience.
        """
        params = mcp_request.params or {}
        prefix = params.get('prefix', '')
        
        # For now, use search endpoint with limit
        search_params = {
            'query': prefix,
            'limit': 5,
            'include_suggestions': True
        }
        
        try:
            # Get suggestions via search
            api_response = await self._make_request(
                method='POST',
                endpoint='/search',
                data=search_params
            )
            
            # Extract suggestions
            suggestions = api_response.get('suggestions', [])
            if not suggestions and 'results' in api_response:
                # Fallback: extract titles from results
                suggestions = [
                    r.get('title', '')
                    for r in api_response.get('results', [])[:5]
                    if r.get('title')
                ]
            
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'suggestions': suggestions,
                    'prefix': prefix
                }
            )
        
        except Exception as e:
            logger.error(
                f"Suggestion retrieval failed: {str(e)}",
                extra={"prefix": prefix},
                exc_info=True
            )
            # Return empty suggestions on error
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'suggestions': [],
                    'prefix': prefix
                }
            )


# Search adapter complete with:
# ✓ Query transformation and filtering
# ✓ Result adaptation with metadata
# ✓ Feedback submission support
# ✓ Signal tracking for relevance
# ✓ Suggestion/autocomplete support
# ✓ Pagination handling
# ✓ Error recovery
# ✓ Comprehensive logging