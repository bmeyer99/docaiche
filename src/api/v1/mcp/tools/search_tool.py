"""
Search Tool for MCP
==================

Provides documentation search capabilities for AI agents.
"""

import logging
from typing import Dict, Any, Optional

from .base_tool import BaseTool, ToolResult
from src.search.orchestrator import SearchOrchestrator
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class SearchTool(BaseTool):
    """Documentation search tool"""
    
    def __init__(self, search_orchestrator: SearchOrchestrator = None):
        super().__init__(
            name="docaiche_search",
            description="Search for documentation across all collections"
        )
        self.search_orchestrator = search_orchestrator
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute documentation search.
        
        Args:
            params: Search parameters including:
                - query: Search query string
                - technology: Optional technology filter
                - limit: Maximum results (default 10)
                - offset: Result offset (default 0)
                
        Returns:
            ToolResult with search results
        """
        try:
            # Extract parameters
            query = params.get("query")
            if not query:
                return ToolResult(
                    success=False,
                    error="Missing required parameter: query",
                    error_code="MISSING_PARAMETER"
                )
            
            technology = params.get("technology")
            limit = params.get("limit", 10)
            offset = params.get("offset", 0)
            
            # Validate parameters
            if not isinstance(limit, int) or limit < 1 or limit > 50:
                limit = 10
            if not isinstance(offset, int) or offset < 0:
                offset = 0
            
            # Execute search if orchestrator available
            if self.search_orchestrator:
                logger.info(f"Executing search: query='{query}', technology='{technology}'")
                
                search_response = await self.search_orchestrator.search(
                    query=query,
                    technology_hint=technology,
                    limit=limit,
                    offset=offset
                )
                
                # Format results for MCP
                results = []
                for result in search_response.results:
                    results.append({
                        "content_id": result.content_id,
                        "title": result.title,
                        "snippet": result.snippet,
                        "source_url": result.source_url,
                        "technology": result.technology,
                        "relevance_score": result.relevance_score,
                        "content_type": result.content_type,
                        "workspace": result.workspace
                    })
                
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "technology": technology,
                        "results": results,
                        "total_count": search_response.total_count,
                        "returned_count": len(results),
                        "cache_hit": search_response.cache_hit,
                        "execution_time_ms": search_response.execution_time_ms
                    }
                )
            else:
                # Return mock results if no orchestrator
                logger.warning("Search orchestrator not available, returning mock results")
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "technology": technology,
                        "results": [
                            {
                                "content_id": "mock_1",
                                "title": f"Mock result for: {query}",
                                "snippet": f"This is a mock search result for query: {query}",
                                "source_url": "https://example.com/mock",
                                "technology": technology or "unknown",
                                "relevance_score": 0.8,
                                "content_type": "documentation",
                                "workspace": "default"
                            }
                        ],
                        "total_count": 1,
                        "returned_count": 1,
                        "cache_hit": False,
                        "execution_time_ms": 0
                    }
                )
                
        except Exception as e:
            logger.error(f"Search tool execution failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e),
                error_code="SEARCH_ERROR"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for search tool parameters"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for documentation",
                    "minLength": 1,
                    "maxLength": 500
                },
                "technology": {
                    "type": "string",
                    "description": "Technology filter (e.g., python, typescript, react)",
                    "maxLength": 100
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10
                },
                "offset": {
                    "type": "integer",
                    "description": "Result offset for pagination",
                    "minimum": 0,
                    "default": 0
                }
            },
            "required": ["query"]
        }