"""
Search Orchestrator Tests - PRD-009
Basic validation tests for search orchestration components.

Tests the core search workflow and component integration as specified in PRD-009.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.search.models import SearchQuery, SearchResults, SearchResult, SearchStrategy
from src.search.orchestrator import SearchOrchestrator
from src.search.strategies import WorkspaceSearchStrategy
from src.search.ranking import ResultRanker
from src.search.cache import SearchCacheManager
from src.search.factory import create_search_orchestrator


class TestSearchOrchestrator:
    """Test SearchOrchestrator core functionality."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test SearchOrchestrator initialization with dependencies."""
        # Mock dependencies
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        # Create orchestrator
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Verify initialization
        assert orchestrator.db_manager == mock_db
        assert orchestrator.cache_manager == mock_cache
        assert orchestrator.anythingllm_client == mock_anythingllm
        assert orchestrator.workspace_strategy is not None
        assert orchestrator.result_ranker is not None
        assert orchestrator.search_cache is not None
    
    @pytest.mark.asyncio
    async def test_query_normalization(self):
        """Test query normalization process."""
        # Mock dependencies
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Test query normalization
        original_query = SearchQuery(
            query="  FastAPI   Tutorial  ",
            technology_hint="PYTHON"
        )
        
        normalized = orchestrator._normalize_query(original_query)
        
        assert normalized.query == "fastapi tutorial"
        assert normalized.technology_hint == "python"
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        # Mock dependencies with health check methods
        mock_db = Mock()
        mock_db.health_check = AsyncMock(return_value={"status": "healthy"})
        
        mock_cache = Mock()
        mock_cache_manager = Mock()
        mock_cache_manager.get_cache_stats = AsyncMock(return_value={"cache_status": "healthy"})
        
        mock_anythingllm = Mock()
        mock_anythingllm.health_check = AsyncMock(return_value={"status": "healthy"})
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        # Replace search_cache with mock
        orchestrator.search_cache = mock_cache_manager
        
        # Test health check
        health = await orchestrator.health_check()
        
        assert health["status"] == "healthy"
        assert "components" in health
        assert "timestamp" in health


class TestWorkspaceSearchStrategy:
    """Test WorkspaceSearchStrategy functionality."""
    
    def test_strategy_initialization(self):
        """Test WorkspaceSearchStrategy initialization."""
        mock_db = Mock()
        mock_anythingllm = Mock()
        
        strategy = WorkspaceSearchStrategy(mock_db, mock_anythingllm)
        
        assert strategy.db_manager == mock_db
        assert strategy.anythingllm_client == mock_anythingllm
        assert hasattr(strategy, 'technology_patterns')
        assert len(strategy.technology_patterns) > 0
    
    def test_technology_keyword_extraction(self):
        """Test technology keyword extraction from queries."""
        mock_db = Mock()
        mock_anythingllm = Mock()
        
        strategy = WorkspaceSearchStrategy(mock_db, mock_anythingllm)
        
        # Test Python detection
        python_query = "FastAPI python tutorial with asyncio"
        detected = strategy._extract_technology_keywords(python_query)
        assert 'python' in detected
        
        # Test JavaScript detection
        js_query = "React component with JavaScript hooks"
        detected = strategy._extract_technology_keywords(js_query)
        assert 'javascript' in detected
        
        # Test Docker detection
        docker_query = "Docker container deployment guide"
        detected = strategy._extract_technology_keywords(docker_query)
        assert 'docker' in detected


class TestResultRanker:
    """Test ResultRanker functionality."""
    
    def test_ranker_initialization(self):
        """Test ResultRanker initialization."""
        ranker = ResultRanker()
        
        assert hasattr(ranker, 'scoring_weights')
        assert sum(ranker.scoring_weights.values()) == pytest.approx(1.0)
    
    def test_metadata_relevance_calculation(self):
        """Test metadata-based relevance scoring."""
        ranker = ResultRanker()
        
        # Create test result
        result = SearchResult(
            content_id="test-1",
            title="FastAPI Tutorial Guide",
            content_snippet="Learn FastAPI framework basics and advanced concepts",
            source_url="https://docs.fastapi.com/tutorial",
            relevance_score=0.8,
            metadata={}
        )
        
        # Test relevance calculation
        relevance = ranker._calculate_metadata_relevance(result, "fastapi")
        assert relevance > 0.0
        assert relevance <= 1.0
    
    def test_technology_scoring(self):
        """Test technology matching score calculation."""
        ranker = ResultRanker()
        
        # Create test result
        result = SearchResult(
            content_id="test-1",
            title="Python FastAPI Tutorial",
            content_snippet="FastAPI Python web framework",
            source_url="https://example.com",
            relevance_score=0.8,
            metadata={},
            technology="python"
        )
        
        # Test direct technology match
        tech_score = ranker._calculate_technology_score(result, "python")
        assert tech_score == 1.0
        
        # Test no technology hint
        tech_score = ranker._calculate_technology_score(result, None)
        assert tech_score == 0.5
        
        # Test non-matching technology
        tech_score = ranker._calculate_technology_score(result, "javascript")
        assert tech_score < 0.5


class TestSearchCacheManager:
    """Test SearchCacheManager functionality."""
    
    def test_cache_manager_initialization(self):
        """Test SearchCacheManager initialization."""
        mock_cache = Mock()
        
        cache_manager = SearchCacheManager(mock_cache)
        
        assert cache_manager.cache_manager == mock_cache
        assert cache_manager.default_ttl > 0
        assert cache_manager.cache_key_prefix == "search:results:"
    
    def test_cache_key_generation(self):
        """Test cache key generation for queries."""
        mock_cache = Mock()
        cache_manager = SearchCacheManager(mock_cache)
        
        # Create test queries
        query1 = SearchQuery(query="fastapi tutorial", strategy=SearchStrategy.HYBRID)
        query2 = SearchQuery(query="FastAPI Tutorial", strategy=SearchStrategy.HYBRID)
        query3 = SearchQuery(query="fastapi tutorial", strategy=SearchStrategy.VECTOR)
        
        # Generate cache keys
        key1 = cache_manager._generate_cache_key(query1)
        key2 = cache_manager._generate_cache_key(query2)
        key3 = cache_manager._generate_cache_key(query3)
        
        # Test normalization (should be same for query1 and query2)
        assert key1 == key2
        
        # Test strategy differentiation (should be different for query1 and query3)
        assert key1 != key3
        
        # Test key format
        assert key1.startswith(cache_manager.cache_key_prefix)
        assert len(key1) > len(cache_manager.cache_key_prefix)


class TestSearchFactory:
    """Test search component factory functions."""
    
    @pytest.mark.asyncio
    async def test_create_search_orchestrator_with_mocks(self):
        """Test factory function with mock dependencies."""
        # Mock dependencies
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        # Create orchestrator using factory
        orchestrator = await create_search_orchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Verify creation
        assert isinstance(orchestrator, SearchOrchestrator)
        assert orchestrator.db_manager == mock_db
        assert orchestrator.cache_manager == mock_cache
        assert orchestrator.anythingllm_client == mock_anythingllm


class TestSearchModels:
    """Test search data models."""
    
    def test_search_query_model(self):
        """Test SearchQuery model validation."""
        # Valid query
        query = SearchQuery(
            query="test query",
            strategy=SearchStrategy.HYBRID,
            limit=10,
            offset=0
        )
        
        assert query.query == "test query"
        assert query.strategy == SearchStrategy.HYBRID
        assert query.limit == 10
        assert query.offset == 0
        assert query.filters is None
        assert query.technology_hint is None
        assert query.workspace_slugs is None
    
    def test_search_result_model(self):
        """Test SearchResult model validation."""
        result = SearchResult(
            content_id="test-123",
            title="Test Document",
            content_snippet="This is a test document snippet...",
            source_url="https://example.com/doc",
            relevance_score=0.85,
            metadata={"author": "test", "tags": ["test", "doc"]}
        )
        
        assert result.content_id == "test-123"
        assert result.title == "Test Document"
        assert 0.0 <= result.relevance_score <= 1.0
        assert isinstance(result.metadata, dict)
    
    def test_search_results_model(self):
        """Test SearchResults model validation."""
        # Create test results
        result1 = SearchResult(
            content_id="1",
            title="Doc 1",
            content_snippet="Content 1",
            source_url="https://example.com/1",
            relevance_score=0.9,
            metadata={}
        )
        
        result2 = SearchResult(
            content_id="2",
            title="Doc 2",
            content_snippet="Content 2",
            source_url="https://example.com/2",
            relevance_score=0.8,
            metadata={}
        )
        
        results = SearchResults(
            results=[result1, result2],
            total_count=2,
            query_time_ms=150,
            strategy_used=SearchStrategy.HYBRID,
            cache_hit=False,
            workspaces_searched=["workspace1", "workspace2"],
            enrichment_triggered=False
        )
        
        assert len(results.results) == 2
        assert results.total_count == 2
        assert results.query_time_ms == 150
        assert results.strategy_used == SearchStrategy.HYBRID
        assert not results.cache_hit
        assert len(results.workspaces_searched) == 2
        assert not results.enrichment_triggered


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])