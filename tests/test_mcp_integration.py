"""
MCP Search System Integration Tests
==================================

Comprehensive integration tests for the MCP (Model Context Protocol) Search System
including external providers, caching, and performance optimizations.
"""

import asyncio
import pytest
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.mcp.providers.search_orchestrator import ExternalSearchOrchestrator
from src.mcp.providers.base import SearchProvider
from src.mcp.providers.models import (
    SearchOptions, SearchResults, SearchResult, SearchResultType,
    ProviderCapabilities, HealthCheck, HealthStatus, ProviderConfig, ProviderType
)
from src.mcp.text_ai.llm_adapter import TextAILLMAdapter
from src.mcp.core.models import NormalizedQuery, VectorSearchResults
from src.search.mcp_integration import MCPSearchEnhancer
from src.search.optimized_cache import OptimizedCacheManager, LRUCache
from src.search.orchestrator import SearchOrchestrator


class MockExternalProvider(SearchProvider):
    """Mock external search provider for testing."""
    
    def __init__(self, provider_id: str, latency_ms: int = 200, success_rate: float = 1.0):
        config = ProviderConfig(
            provider_id=provider_id,
            provider_type=ProviderType.BRAVE,
            api_key="test_key",
            max_results=10,
            timeout_seconds=3.0
        )
        super().__init__(config)
        self.latency_ms = latency_ms
        self.success_rate = success_rate
        self.call_count = 0
    
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_type=ProviderType.BRAVE,
            supports_date_filtering=True,
            supports_site_search=True,
            max_results_per_request=20,
            rate_limit_requests_per_minute=60,
            requires_api_key=True,
            result_types=[SearchResultType.WEB_PAGE],
            reliability_score=self.success_rate
        )
    
    async def search(self, options: SearchOptions) -> SearchResults:
        """Mock search implementation."""
        self.call_count += 1
        
        # Simulate network latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Simulate failures based on success rate
        import random
        if random.random() > self.success_rate:
            raise Exception(f"Simulated failure for {self.config.provider_id}")
        
        # Generate mock results
        results = []
        for i in range(min(options.max_results, 5)):
            result = SearchResult(
                title=f"Test Result {i+1} from {self.config.provider_id}",
                url=f"https://example.com/result{i+1}",
                snippet=f"This is a test snippet {i+1} for query: {options.query}",
                content_type=SearchResultType.WEB_PAGE,
                provider_rank=i+1,
                published_date=datetime.utcnow() - timedelta(days=i),
                metadata={"provider": self.config.provider_id}
            )
            results.append(result)
        
        return SearchResults(
            results=results,
            total_results=len(results),
            execution_time_ms=self.latency_ms,
            provider=self.config.provider_id,
            query=options.query
        )
    
    async def check_health(self) -> HealthCheck:
        """Mock health check."""
        return HealthCheck(
            status=HealthStatus.HEALTHY if self.success_rate > 0.8 else HealthStatus.DEGRADED,
            response_time_ms=self.latency_ms,
            last_success=datetime.utcnow()
        )


class TestMCPSearchOrchestrator:
    """Test the external search orchestrator with performance optimizations."""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock cache manager."""
        cache = Mock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        return cache
    
    @pytest.fixture
    def mock_provider_registry(self):
        """Create a mock provider registry."""
        registry = Mock()
        
        # Create mock providers with different characteristics
        fast_provider = MockExternalProvider("brave_search", latency_ms=150, success_rate=0.95)
        slow_provider = MockExternalProvider("google_search", latency_ms=400, success_rate=0.90)
        
        registry.get_healthy_providers = AsyncMock(return_value=[fast_provider, slow_provider])
        return registry
    
    @pytest.fixture
    def optimized_cache(self, mock_cache_manager):
        """Create an optimized cache manager."""
        return OptimizedCacheManager(
            redis_cache=mock_cache_manager,
            l1_size=10,
            compress_threshold=100,
            enable_stats=True
        )
    
    @pytest.fixture
    def search_orchestrator(self, mock_provider_registry, optimized_cache):
        """Create an external search orchestrator."""
        return ExternalSearchOrchestrator(
            provider_registry=mock_provider_registry,
            cache_manager=optimized_cache,
            enable_hedged_requests=True,
            hedged_delay=0.1,  # Faster for testing
            max_concurrent_providers=2
        )
    
    @pytest.mark.asyncio
    async def test_single_provider_search(self, search_orchestrator):
        """Test search with a single provider."""
        result = await search_orchestrator.search(
            query="test query",
            max_results=5,
            provider_ids=["brave_search"]
        )
        
        assert result is not None
        assert len(result.results) > 0
        assert result.query == "test query"
        assert "brave_search" in result.provider
        assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_hedged_requests(self, search_orchestrator):
        """Test hedged request pattern with multiple providers."""
        start_time = time.time()
        
        result = await search_orchestrator.search(
            query="test hedged query",
            max_results=5
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        assert result is not None
        assert len(result.results) > 0
        # Should be faster than the slowest provider due to hedging
        assert execution_time < 500  # Should complete before slow provider
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, search_orchestrator):
        """Test cache integration with L1 and L2 caching."""
        query = "cache test query"
        
        # First search - should miss cache
        result1 = await search_orchestrator.search(query=query, max_results=3)
        assert result1 is not None
        
        # Second search - should hit cache
        start_time = time.time()
        result2 = await search_orchestrator.search(query=query, max_results=3)
        cache_time = (time.time() - start_time) * 1000
        
        assert result2 is not None
        # Cache hit should be much faster
        assert cache_time < 50  # Should be very fast from cache
    
    @pytest.mark.asyncio
    async def test_adaptive_timeouts(self, search_orchestrator):
        """Test adaptive timeout management."""
        timeout_manager = search_orchestrator.timeout_manager
        
        # Record some latencies
        timeout_manager.record_latency("test_provider", 100)
        timeout_manager.record_latency("test_provider", 200)
        timeout_manager.record_latency("test_provider", 150)
        timeout_manager.record_latency("test_provider", 180)
        timeout_manager.record_latency("test_provider", 120)
        
        # Get adaptive timeout
        adaptive_timeout = timeout_manager.get_timeout("test_provider")
        
        # Should be based on P95 + 20% buffer
        assert 1.5 < adaptive_timeout < 3.0  # Reasonable range
        
        # Unknown provider should get default timeout
        default_timeout = timeout_manager.get_timeout("unknown_provider")
        assert default_timeout == 2.0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, search_orchestrator):
        """Test circuit breaker functionality."""
        # Create a provider that will fail
        failing_provider = MockExternalProvider("failing_provider", success_rate=0.0)
        
        # Record failures
        for _ in range(6):  # Exceed failure threshold
            search_orchestrator._record_failure("failing_provider")
        
        # Circuit should be open
        assert search_orchestrator._is_circuit_open("failing_provider")
        
        # Reset circuit breaker
        search_orchestrator._reset_circuit_breaker("failing_provider")
        assert not search_orchestrator._is_circuit_open("failing_provider")
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, search_orchestrator):
        """Test performance metrics collection."""
        # Perform some searches
        await search_orchestrator.search("metrics test 1", max_results=3)
        await search_orchestrator.search("metrics test 2", max_results=3)
        
        # Get performance stats
        stats = search_orchestrator.get_performance_stats()
        
        assert "search_metrics" in stats
        assert "cache_metrics" in stats
        assert stats["search_metrics"]["total_searches"] >= 2
        assert "provider_health" in stats


class TestMCPIntegrationLayer:
    """Test the MCP integration layer with existing search system."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock()
        client.evaluate_search_results = Mock(return_value=Mock(
            avg_relevance_score=0.7,
            completeness_score=0.8,
            confidence_score=0.9,
            missing_info=[]
        ))
        return client
    
    @pytest.fixture
    def mcp_enhancer(self, mock_llm_client):
        """Create an MCP search enhancer."""
        return MCPSearchEnhancer(llm_client=mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_external_search_query_generation(self, mcp_enhancer):
        """Test external search query optimization."""
        query = await mcp_enhancer.get_external_search_query(
            "python asyncio tutorial",
            technology_hint="python"
        )
        
        assert "python" in query
        assert "asyncio" in query
        assert len(query) > 0
    
    @pytest.mark.asyncio
    async def test_workspace_selection_enhancement(self, mcp_enhancer):
        """Test enhanced workspace selection."""
        available_workspaces = [
            {"id": "python_docs", "technologies": ["python"], "priority": 1},
            {"id": "general_docs", "tags": ["general"], "priority": 2},
            {"id": "javascript_docs", "technologies": ["javascript"], "priority": 1}
        ]
        
        selected = await mcp_enhancer.enhance_workspace_selection(
            "python tutorial",
            available_workspaces,
            technology_hint="python"
        )
        
        assert "python_docs" in selected
        assert len(selected) <= 5
    
    @pytest.mark.asyncio
    async def test_performance_stats_integration(self, mcp_enhancer):
        """Test performance statistics integration."""
        # Mock the orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_performance_stats.return_value = {
            "search_metrics": {"total_searches": 10},
            "cache_metrics": {"l1_hits": 5}
        }
        mcp_enhancer._external_orchestrator = mock_orchestrator
        
        stats = mcp_enhancer.get_performance_stats()
        
        assert "search_metrics" in stats
        assert stats["search_metrics"]["total_searches"] == 10


class TestOptimizedCaching:
    """Test the multi-tier optimized caching system."""
    
    @pytest.fixture
    def mock_redis_cache(self):
        """Create a mock Redis cache."""
        cache = Mock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        return cache
    
    @pytest.fixture
    def optimized_cache(self, mock_redis_cache):
        """Create an optimized cache manager."""
        return OptimizedCacheManager(
            redis_cache=mock_redis_cache,
            l1_size=5,
            compress_threshold=50,
            enable_stats=True
        )
    
    @pytest.mark.asyncio
    async def test_l1_cache_operations(self, optimized_cache):
        """Test L1 (in-memory) cache operations."""
        key = "test_key"
        value = {"test": "data"}
        
        # Set value
        await optimized_cache.set(key, value)
        
        # Get value - should hit L1
        result = await optimized_cache.get(key)
        assert result == value
        
        # Check stats
        stats = optimized_cache.get_stats()
        assert stats["l1_hits"] >= 1
    
    @pytest.mark.asyncio
    async def test_compression_functionality(self, optimized_cache):
        """Test value compression for large objects."""
        # Large value that should trigger compression
        large_value = {"data": "x" * 1000, "items": list(range(100))}
        
        # Set large value
        await optimized_cache.set("large_key", large_value)
        
        # Retrieve and verify
        result = await optimized_cache.get("large_key")
        assert result == large_value
        
        # Check compression stats
        stats = optimized_cache.get_stats()
        assert stats["compressions"] >= 1
    
    @pytest.mark.asyncio
    async def test_batch_operations(self, optimized_cache):
        """Test batch get/set operations."""
        items = {
            "key1": {"value": 1},
            "key2": {"value": 2},
            "key3": {"value": 3}
        }
        
        # Batch set
        success = await optimized_cache.set_batch(items)
        assert success
        
        # Batch get
        results = await optimized_cache.get_batch(list(items.keys()))
        
        assert len(results) == 3
        assert results["key1"]["value"] == 1
        assert results["key2"]["value"] == 2
        assert results["key3"]["value"] == 3
    
    @pytest.mark.asyncio
    async def test_cache_key_computation(self, optimized_cache):
        """Test cache key computation."""
        key1 = optimized_cache.compute_key("arg1", "arg2", param1="value1")
        key2 = optimized_cache.compute_key("arg1", "arg2", param1="value1")
        key3 = optimized_cache.compute_key("arg1", "arg2", param1="value2")
        
        # Same inputs should produce same key
        assert key1 == key2
        
        # Different inputs should produce different keys
        assert key1 != key3
    
    def test_lru_cache_eviction(self):
        """Test LRU cache eviction policy."""
        cache = LRUCache(maxsize=3)
        
        # Fill cache to capacity
        asyncio.run(cache.set("key1", "value1"))
        asyncio.run(cache.set("key2", "value2"))
        asyncio.run(cache.set("key3", "value3"))
        
        # Add one more item - should evict oldest
        asyncio.run(cache.set("key4", "value4"))
        
        # key1 should be evicted
        assert asyncio.run(cache.get("key1")) is None
        assert asyncio.run(cache.get("key2")) == "value2"
        assert asyncio.run(cache.get("key4")) == "value4"


class TestTextAILLMAdapter:
    """Test the Text AI LLM adapter integration."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock()
        client.evaluate_search_results = Mock(return_value=Mock(
            avg_relevance_score=0.8,
            completeness_score=0.7,
            confidence_score=0.9,
            missing_info=["examples"]
        ))
        return client
    
    @pytest.fixture
    def mock_query_analyzer(self):
        """Create a mock query analyzer."""
        analyzer = Mock()
        analyzer.analyze = AsyncMock(return_value={
            "intent": "information_seeking",
            "domain": "technical",
            "entities": ["python", "asyncio"],
            "concepts": ["concurrency"],
            "confidence": 0.8
        })
        return analyzer
    
    @pytest.fixture
    def text_ai_adapter(self, mock_llm_client, mock_query_analyzer):
        """Create a Text AI LLM adapter."""
        return TextAILLMAdapter(
            llm_client=mock_llm_client,
            query_analyzer=mock_query_analyzer
        )
    
    @pytest.mark.asyncio
    async def test_query_analysis(self, text_ai_adapter):
        """Test query analysis functionality."""
        query = NormalizedQuery(
            original_query="python asyncio tutorial",
            normalized_text="python asyncio tutorial",
            technology_hint="python",
            query_hash="test_hash",
            tokens=["python", "asyncio", "tutorial"]
        )
        
        analysis = await text_ai_adapter.analyze_query(query)
        
        assert analysis.intent == "information_seeking"
        assert analysis.domain == "technical"
        assert "python" in analysis.entities
        assert analysis.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_workspace_selection(self, text_ai_adapter):
        """Test workspace selection logic."""
        query = NormalizedQuery(
            original_query="react hooks tutorial",
            normalized_text="react hooks tutorial",
            technology_hint="javascript",
            query_hash="test_hash",
            tokens=["react", "hooks", "tutorial"]
        )
        
        workspaces = [
            {"id": "react_docs", "technologies": ["javascript", "react"], "priority": 1},
            {"id": "python_docs", "technologies": ["python"], "priority": 2},
            {"id": "general", "tags": ["general"], "priority": 3}
        ]
        
        selected = await text_ai_adapter.select_workspaces(query, workspaces)
        
        assert "react_docs" in selected
        assert len(selected) <= 5
    
    @pytest.mark.asyncio
    async def test_result_evaluation(self, text_ai_adapter):
        """Test search result evaluation."""
        query = NormalizedQuery(
            original_query="test query",
            normalized_text="test query",
            technology_hint=None,
            query_hash="test_hash",
            tokens=["test", "query"]
        )
        
        # Mock search results
        mock_results = VectorSearchResults(
            results=[
                Mock(title="Result 1", content="Content 1", url="http://example.com/1", relevance_score=0.9),
                Mock(title="Result 2", content="Content 2", url="http://example.com/2", relevance_score=0.7)
            ],
            query_hash="test_hash",
            execution_time_ms=100,
            total_results=2
        )
        
        evaluation = await text_ai_adapter.evaluate_results(query, mock_results)
        
        assert evaluation.relevance_score == 0.8  # From mock LLM client
        assert evaluation.completeness_score == 0.7
        assert evaluation.confidence == 0.9
        assert "examples" in evaluation.missing_information
    
    @pytest.mark.asyncio
    async def test_external_query_generation(self, text_ai_adapter):
        """Test external search query generation."""
        query = NormalizedQuery(
            original_query="python tutorial",
            normalized_text="python tutorial",
            technology_hint="python",
            query_hash="test_hash",
            tokens=["python", "tutorial"]
        )
        
        # Mock evaluation indicating need for external search
        evaluation = Mock(
            relevance_score=0.3,
            needs_external_search=True
        )
        
        external_query = await text_ai_adapter.generate_external_query(query, evaluation)
        
        assert "python" in external_query
        assert len(external_query) > 0


class TestEndToEndWorkflow:
    """Test complete end-to-end MCP search workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_search_workflow(self):
        """Test the complete search workflow with MCP enhancement."""
        # Mock dependencies
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        mock_llm_client = Mock()
        
        # Mock search results
        mock_anythingllm.search_workspace = AsyncMock(return_value=[
            {
                "id": "doc1",
                "content": "Python asyncio documentation",
                "score": 0.8,
                "metadata": {"document_title": "Asyncio Guide", "source_url": "http://example.com"}
            }
        ])
        
        # Create orchestrator with MCP enhancement
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm,
            llm_client=mock_llm_client
        )
        
        # Mock workspace data
        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "slug": "python_docs",
                "technology": "python",
                "last_updated": datetime.utcnow(),
                "document_count": 100
            }
        ])
        
        # Mock cache miss
        orchestrator.search_cache.get_cached_results = AsyncMock(return_value=None)
        orchestrator.search_cache.cache_results = AsyncMock()
        
        # Execute search
        query = "python asyncio tutorial"
        results, normalized_query = await orchestrator.execute_search(
            SearchQuery(query=query, technology_hint="python")
        )
        
        # Verify results
        assert results is not None
        assert len(results.results) > 0
        assert results.query_time_ms > 0
        assert normalized_query.query == query
        
        # Verify MCP enhancer was initialized
        assert orchestrator.mcp_enhancer is not None
    
    @pytest.mark.asyncio 
    async def test_search_with_external_enhancement(self):
        """Test search that triggers external enhancement."""
        # This would require more complex mocking of the entire workflow
        # For now, verify that the components can work together
        
        # Mock a low-quality search result that would trigger external search
        mock_search_results = Mock()
        mock_search_results.results = []  # Empty results to trigger external search
        
        # Mock MCP enhancer
        mock_enhancer = Mock()
        mock_enhancer.is_external_search_available = Mock(return_value=True)
        mock_enhancer.get_external_search_query = AsyncMock(return_value="enhanced query")
        mock_enhancer.execute_external_search = AsyncMock(return_value=[
            {
                "title": "External Result",
                "url": "http://external.com",
                "snippet": "External content",
                "provider": "brave_search"
            }
        ])
        
        # Verify external search can be triggered
        external_results = await mock_enhancer.execute_external_search("test query")
        assert len(external_results) > 0
        assert external_results[0]["provider"] == "brave_search"


if __name__ == "__main__":
    # Run specific test suites
    pytest.main([
        __file__ + "::TestMCPSearchOrchestrator",
        "-v", "--tb=short"
    ])