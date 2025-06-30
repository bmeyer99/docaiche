"""
Unit Tests for Search Tool
==========================

Comprehensive test suite for the docaiche_search tool implementation
covering all search scopes, error handling, and edge cases.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.mcp.tools.search_tool import SearchTool
from src.mcp.schemas import MCPRequest, SearchToolRequest
from src.mcp.exceptions import ToolExecutionError, ValidationError


class TestSearchTool:
    """Test suite for SearchTool implementation."""
    
    @pytest.fixture
    def search_tool(self):
        """Create search tool instance with mocked dependencies."""
        return SearchTool(
            search_orchestrator=None,
            ingest_client=None,
            consent_manager=None,
            security_auditor=None
        )
    
    @pytest.fixture
    def mock_search_orchestrator(self):
        """Create mock search orchestrator."""
        orchestrator = Mock()
        orchestrator.search = AsyncMock()
        return orchestrator
    
    @pytest.fixture
    def mock_ingest_client(self):
        """Create mock ingest client."""
        client = Mock()
        client.ingest = AsyncMock()
        return client
    
    def test_tool_metadata_initialization(self, search_tool):
        """Test that tool metadata is properly initialized."""
        assert search_tool.metadata.name == "docaiche_search"
        assert search_tool.metadata.version == "1.0.0"
        assert search_tool.metadata.category == "search"
        assert search_tool.metadata.requires_consent is False
        assert search_tool.metadata.max_execution_time_ms == 10000
    
    def test_tool_definition_schema(self, search_tool):
        """Test that tool definition returns valid schema."""
        definition = search_tool.get_tool_definition()
        
        assert definition.name == "docaiche_search"
        assert definition.input_schema["type"] == "object"
        assert "query" in definition.input_schema["properties"]
        assert definition.input_schema["properties"]["query"]["minLength"] == 1
        assert definition.input_schema["properties"]["query"]["maxLength"] == 500
        
        # Check scope enum values
        scope_enum = definition.input_schema["properties"]["scope"]["enum"]
        assert "cached" in scope_enum
        assert "live" in scope_enum
        assert "deep" in scope_enum
    
    @pytest.mark.asyncio
    async def test_cached_search_fallback(self, search_tool):
        """Test cached search with fallback when orchestrator not available."""
        request = MCPRequest(
            id="test-1",
            method="tools/call",
            params={
                "query": "Python type hints",
                "technology": "python",
                "scope": "cached",
                "max_results": 5
            }
        )
        
        response = await search_tool.execute(request)
        
        assert response.result is not None
        assert response.result["query"] == "Python type hints"
        assert response.result["technology"] == "python"
        assert response.result["scope"] == "cached"
        assert len(response.result["results"]) <= 5
        assert response.result["search_metadata"]["cache_hit"] is False
    
    @pytest.mark.asyncio
    async def test_search_with_orchestrator(self, search_tool, mock_search_orchestrator):
        """Test search execution with actual orchestrator."""
        # Configure search tool with orchestrator
        search_tool.search_orchestrator = mock_search_orchestrator
        
        # Mock orchestrator response
        mock_response = Mock()
        mock_response.results = [
            Mock(
                content_id="doc-1",
                title="Python Type Hints Guide",
                snippet="Learn about Python type hints...",
                source_url="https://python.org/docs/type-hints",
                technology="python",
                relevance_score=0.95
            )
        ]
        mock_response.total_count = 1
        mock_response.cache_hit = True
        mock_response.execution_time_ms = 50
        mock_response.enrichment_triggered = False
        
        mock_search_orchestrator.search.return_value = mock_response
        
        request = MCPRequest(
            id="test-2",
            method="tools/call",
            params={
                "query": "Python type hints",
                "technology": "python",
                "scope": "cached",
                "max_results": 10
            }
        )
        
        response = await search_tool.execute(request)
        
        # Verify orchestrator was called
        mock_search_orchestrator.search.assert_called_once_with(
            query="Python type hints",
            technology_hint="python",
            limit=10,
            offset=0
        )
        
        # Verify response formatting
        assert response.result["query"] == "Python type hints"
        assert len(response.result["results"]) == 1
        assert response.result["results"][0]["title"] == "Python Type Hints Guide"
        assert response.result["search_metadata"]["cache_hit"] is True
    
    @pytest.mark.asyncio
    async def test_deep_search_quality_analysis(self, search_tool):
        """Test deep search with quality analysis."""
        # Create search tool with mocked ingest capability
        search_tool.ingest_client = Mock()
        search_tool.ingest_client.ingest = AsyncMock()
        
        request = MCPRequest(
            id="test-3",
            method="tools/call",
            params={
                "query": "React hooks useEffect",
                "technology": "react",
                "scope": "deep",
                "max_results": 10
            }
        )
        
        response = await search_tool.execute(request)
        
        # Verify deep search metadata
        assert response.result["scope"] == "deep"
        assert "content_discovery" in response.result
        assert response.result["content_discovery"]["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_invalid_search_scope(self, search_tool):
        """Test error handling for invalid search scope."""
        request = MCPRequest(
            id="test-4",
            method="tools/call",
            params={
                "query": "test query",
                "scope": "invalid_scope"  # Invalid scope
            }
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await search_tool.execute(request)
        
        assert "Invalid search request" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_with_metadata(self, search_tool):
        """Test search with metadata inclusion."""
        request = MCPRequest(
            id="test-5",
            method="tools/call",
            params={
                "query": "TypeScript generics",
                "technology": "typescript",
                "scope": "cached",
                "max_results": 3,
                "include_metadata": True
            }
        )
        
        response = await search_tool.execute(request)
        
        # Verify metadata is included in results
        for result in response.result["results"]:
            assert "metadata" in result
            assert "last_updated" in result["metadata"]
            assert "tags" in result["metadata"]
    
    @pytest.mark.asyncio
    async def test_search_rate_limiting(self, search_tool):
        """Test that search respects rate limiting."""
        # The metadata should indicate rate limiting
        assert search_tool.metadata.rate_limit_per_minute == 30
        
        definition = search_tool.get_tool_definition()
        assert definition.annotations.rate_limited is True
    
    @pytest.mark.asyncio
    async def test_search_query_validation(self, search_tool):
        """Test search query validation."""
        # Test empty query
        request = MCPRequest(
            id="test-6",
            method="tools/call",
            params={
                "query": "",  # Empty query
                "scope": "cached"
            }
        )
        
        with pytest.raises(ValidationError):
            await search_tool.execute(request)
        
        # Test query too long
        long_query = "a" * 501  # Exceeds 500 char limit
        request = MCPRequest(
            id="test-7",
            method="tools/call",
            params={
                "query": long_query,
                "scope": "cached"
            }
        )
        
        with pytest.raises(ValidationError):
            await search_tool.execute(request)
    
    @pytest.mark.asyncio
    async def test_search_result_deduplication(self, search_tool):
        """Test that search results are properly deduplicated."""
        # This is tested through the _merge_search_results method
        initial_results = [
            Mock(content_id="doc-1", title="Title 1", source_url="url1", relevance_score=0.9),
            Mock(content_id="doc-2", title="Title 2", source_url="url2", relevance_score=0.8)
        ]
        
        enriched_results = [
            Mock(content_id="doc-2", title="Title 2", source_url="url2", relevance_score=0.85),
            Mock(content_id="doc-3", title="Title 3", source_url="url3", relevance_score=0.7)
        ]
        
        merged = search_tool._merge_search_results(initial_results, enriched_results)
        
        # Should have 3 unique results
        assert len(merged) == 3
        
        # Check deduplication worked
        content_ids = [getattr(r, 'content_id') for r in merged]
        assert len(content_ids) == len(set(content_ids))
    
    def test_search_capabilities(self, search_tool):
        """Test search tool capabilities reporting."""
        capabilities = search_tool.get_search_capabilities()
        
        assert capabilities["tool_name"] == "docaiche_search"
        assert "cached" in capabilities["supported_scopes"]
        assert "live" in capabilities["supported_scopes"]
        assert "deep" in capabilities["supported_scopes"]
        
        assert capabilities["features"]["semantic_search"] is True
        assert capabilities["features"]["content_discovery"] is True
        assert capabilities["features"]["real_time_search"] is True
        
        assert capabilities["performance"]["max_execution_time_ms"] == 10000
        assert capabilities["performance"]["rate_limit_per_minute"] == 30


class TestSearchQualityAnalysis:
    """Test suite for search quality analysis functionality."""
    
    @pytest.fixture
    def search_tool(self):
        """Create search tool instance."""
        return SearchTool()
    
    @pytest.mark.asyncio
    async def test_quality_score_calculation(self, search_tool):
        """Test search quality score calculation."""
        # Create mock search results
        results = [
            Mock(
                relevance_score=0.9,
                title="Python Type Hints and Annotations",
                snippet="Complete guide to Python type hints..."
            ),
            Mock(
                relevance_score=0.7,
                title="Advanced Python Programming",
                snippet="Learn advanced Python concepts..."
            )
        ]
        
        query = "Python type hints"
        score = await search_tool._analyze_search_quality(results, query)
        
        # Score should be reasonable for good matches
        assert 0.5 < score <= 1.0
    
    @pytest.mark.asyncio
    async def test_quality_score_empty_results(self, search_tool):
        """Test quality score for empty results."""
        score = await search_tool._analyze_search_quality([], "any query")
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_content_source_discovery(self, search_tool):
        """Test content source discovery for different technologies."""
        # Test Python sources
        python_sources = await search_tool._discover_content_sources(
            "type hints", "python"
        )
        assert len(python_sources) > 0
        assert any("python.org" in s["source_url"] for s in python_sources)
        
        # Test React sources
        react_sources = await search_tool._discover_content_sources(
            "hooks", "react"
        )
        assert len(react_sources) > 0
        assert any("react.dev" in s["source_url"] for s in react_sources)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])