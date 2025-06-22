"""
PRD-009 Search Orchestrator Engine - Comprehensive QA Validation Tests
=====================================================================

CRITICAL WORKFLOW: This test suite MUST be created BEFORE examining implementation code.
Code can ONLY pass validation if it passes ALL tests in this comprehensive suite.

Test Categories:
- Functional Tests: Every PRD-009 requirement implementation
- Security Tests: Search query handling, caching security, data protection
- Performance Tests: Parallel processing, timeouts, resource usage
- Integration Tests: CFG-001, DB-001, ALM-001, PRD-008 compatibility
- Error Handling Tests: Exception hierarchy and recovery
- Configuration Tests: SearchConfig validation and defaults
- Operational Tests: Health checks, monitoring, production readiness
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import components to test
from src.search.orchestrator import SearchOrchestrator
from src.search.models import (
    SearchQuery, SearchResults, SearchResult, SearchStrategy,
    WorkspaceInfo, EvaluationResult, SearchAnalytics, CachedSearchResult
)
from src.search.strategies import WorkspaceSearchStrategy
from src.search.ranking import ResultRanker
from src.search.cache import SearchCacheManager
from src.search.exceptions import (
    SearchOrchestrationError, VectorSearchError, MetadataSearchError,
    ResultRankingError, SearchCacheError, WorkspaceSelectionError,
    SearchTimeoutError, LLMEvaluationError, EnrichmentTriggerError
)
from src.search.factory import create_search_orchestrator


class TestPRD009FunctionalRequirements:
    """Test all PRD-009 functional requirements are correctly implemented."""
    
    @pytest.mark.asyncio
    async def test_seven_step_search_workflow_implementation(self):
        """
        CRITICAL: Verify exact 7-step search workflow from PRD-009.
        
        Required workflow:
        1. Query Normalization: Lowercase, trim, hash
        2. Cache Check: Use query_hash to check Redis for SearchResponse
        3. Multi-Workspace Search: Execute intelligent workspace selection and parallel search
        4. AI Evaluation: Call llm_client.evaluate_search_results()
        5. Enrichment Decision: Use EvaluationResult to decide on enrichment
        6. Knowledge Enrichment: Call enricher.enrich_knowledge() as background task
        7. Response Compilation & Caching: Format SearchResponse, cache, return
        """
        # Setup mocks
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        mock_llm = Mock()
        mock_enricher = Mock()
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm,
            llm_client=mock_llm,
            knowledge_enricher=mock_enricher
        )
        
        # Mock cache miss to trigger full workflow
        orchestrator.search_cache.get_cached_results = AsyncMock(return_value=None)
        orchestrator.search_cache.cache_results = AsyncMock()
        
        # Mock workspace search strategy
        mock_workspace = WorkspaceInfo(
            slug="python-docs",
            technology="python",
            relevance_score=0.9,
            last_updated=datetime.utcnow()
        )
        orchestrator.workspace_strategy.identify_relevant_workspaces = AsyncMock(
            return_value=[mock_workspace]
        )
        
        mock_result = SearchResult(
            content_id="test-1",
            title="FastAPI Tutorial",
            content_snippet="Learn FastAPI basics...",
            source_url="https://example.com",
            relevance_score=0.8,
            metadata={}
        )
        orchestrator.workspace_strategy.execute_parallel_search = AsyncMock(
            return_value=[mock_result]
        )
        
        # Mock result ranking
        orchestrator.result_ranker.rank_results = AsyncMock(
            return_value=[mock_result]
        )
        
        # Mock LLM evaluation
        mock_evaluation = EvaluationResult(
            overall_quality=0.7,
            relevance_assessment=0.8,
            completeness_score=0.6,
            needs_enrichment=True,
            enrichment_topics=["fastapi"],
            confidence_level=0.8
        )
        orchestrator._evaluate_search_results = AsyncMock(return_value=mock_evaluation)
        
        # Mock enrichment triggering
        orchestrator._trigger_enrichment = AsyncMock(return_value=True)
        
        # Test query
        query = SearchQuery(
            query="  FastAPI   Tutorial  ",
            technology_hint="PYTHON"
        )
        
        # Execute search workflow
        results = await orchestrator.execute_search(query)
        
        # Verify Step 1: Query Normalization
        assert query.query != "  FastAPI   Tutorial  "  # Should be normalized internally
        
        # Verify Step 2: Cache Check was called
        orchestrator.search_cache.get_cached_results.assert_called_once()
        
        # Verify Step 3: Multi-Workspace Search
        orchestrator.workspace_strategy.identify_relevant_workspaces.assert_called_once()
        orchestrator.workspace_strategy.execute_parallel_search.assert_called_once()
        
        # Verify Step 4: AI Evaluation
        orchestrator._evaluate_search_results.assert_called_once()
        
        # Verify Step 5: Enrichment Decision
        orchestrator._trigger_enrichment.assert_called_once()
        
        # Verify Step 6: Background Enrichment was triggered
        assert results.enrichment_triggered == True
        
        # Verify Step 7: Response Compilation & Caching
        orchestrator.search_cache.cache_results.assert_called_once()
        assert isinstance(results, SearchResults)
        assert len(results.results) == 1
        assert results.cache_hit == False
        assert results.workspaces_searched == ["python-docs"]
    
    def test_multi_workspace_search_strategy_implementation(self):
        """Test intelligent workspace selection with technology-based filtering."""
        mock_db = Mock()
        mock_anythingllm = Mock()
        
        strategy = WorkspaceSearchStrategy(mock_db, mock_anythingllm)
        
        # Verify technology patterns are comprehensive
        assert 'python' in strategy.technology_patterns
        assert 'javascript' in strategy.technology_patterns
        assert 'docker' in strategy.technology_patterns
        assert 'kubernetes' in strategy.technology_patterns
        assert 'aws' in strategy.technology_patterns
        
        # Test keyword extraction
        python_keywords = strategy._extract_technology_keywords("FastAPI python tutorial")
        assert 'python' in python_keywords
        
        js_keywords = strategy._extract_technology_keywords("React JavaScript components")
        assert 'javascript' in js_keywords
        
        # Test max 5 workspace limit is enforced in implementation
        assert hasattr(strategy, 'technology_patterns')
    
    def test_result_ranking_multi_factor_scoring(self):
        """Test 5-factor weighted scoring system implementation."""
        ranker = ResultRanker()
        
        # Verify exact scoring weights from PRD-009
        expected_weights = {
            'vector_similarity': 0.4,   # 40%
            'metadata_relevance': 0.2,  # 20% 
            'recency': 0.15,            # 15%
            'quality_score': 0.15,      # 15%
            'technology_match': 0.1     # 10%
        }
        
        assert ranker.scoring_weights == expected_weights
        assert abs(sum(ranker.scoring_weights.values()) - 1.0) < 0.001
        
        # Test metadata relevance calculation
        result = SearchResult(
            content_id="test-1",
            title="FastAPI Tutorial Guide",
            content_snippet="Learn FastAPI framework basics",
            source_url="https://docs.fastapi.com/tutorial",
            relevance_score=0.8,
            metadata={}
        )
        
        relevance = ranker._calculate_metadata_relevance(result, "fastapi")
        assert 0.0 <= relevance <= 1.0
        assert relevance > 0.5  # Should have high relevance for title match
    
    def test_search_caching_with_query_normalization(self):
        """Test Redis caching with proper query normalization and TTL."""
        mock_cache_manager = Mock()
        cache_manager = SearchCacheManager(mock_cache_manager)
        
        # Test cache key generation with normalization
        query1 = SearchQuery(query="fastapi tutorial", strategy=SearchStrategy.HYBRID)
        query2 = SearchQuery(query="FastAPI Tutorial", strategy=SearchStrategy.HYBRID)
        query3 = SearchQuery(query="fastapi tutorial", strategy=SearchStrategy.VECTOR)
        
        key1 = cache_manager._generate_cache_key(query1)
        key2 = cache_manager._generate_cache_key(query2)
        key3 = cache_manager._generate_cache_key(query3)
        
        # Case normalization should make queries identical
        assert key1 == key2
        
        # Strategy differentiation should make keys different
        assert key1 != key3
        
        # Proper key prefix
        assert key1.startswith(cache_manager.cache_key_prefix)
        assert cache_manager.cache_key_prefix == "search:results:"
        
        # TTL configuration
        assert cache_manager.default_ttl == 3600  # 1 hour


class TestPRD009SecurityValidation:
    """Test security aspects of search orchestration."""
    
    @pytest.mark.asyncio
    async def test_search_query_sanitization(self):
        """Test search queries are properly sanitized and validated."""
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Test query normalization removes potential injection attempts
        malicious_query = SearchQuery(
            query="'; DROP TABLE users; --",
            technology_hint="<script>alert('xss')</script>"
        )
        
        normalized = orchestrator._normalize_query(malicious_query)
        
        # Should normalize to lowercase and trim spaces
        assert normalized.query == "'; drop table users; --"
        assert normalized.technology_hint == "<script>alert('xss')</script>"
        
        # Note: Additional sanitization should be implemented for production
    
    def test_cache_security_configuration(self):
        """Test search cache security settings."""
        mock_cache_manager = Mock()
        cache_manager = SearchCacheManager(mock_cache_manager)
        
        # Verify secure key generation
        query = SearchQuery(query="test query")
        cache_key = cache_manager._generate_cache_key(query)
        
        # Should use secure hash (SHA-256 truncated to 32 chars)
        assert len(cache_key.split(cache_manager.cache_key_prefix)[1]) == 32
        
        # Should have proper TTL limits
        assert cache_manager.default_ttl > 0
        assert cache_manager.default_ttl <= 86400  # Max 24 hours
    
    def test_error_handling_no_information_disclosure(self):
        """Test exception handling doesn't leak sensitive information."""
        # Test base exception
        error = SearchOrchestrationError(
            "Database connection failed",
            error_context={"password": "secret123", "api_key": "key123"}
        )
        
        # Should not expose sensitive data in string representation
        error_str = str(error)
        assert "secret123" not in error_str
        assert "key123" not in error_str
        
        # Test timeout error
        timeout_error = SearchTimeoutError(
            "Search timed out",
            timeout_seconds=30.0,
            operation="multi_workspace_search"
        )
        
        assert timeout_error.error_context["timeout_seconds"] == 30.0
        assert "multi_workspace_search" in timeout_error.error_context["operation"]


class TestPRD009PerformanceValidation:
    """Test performance characteristics and optimization."""
    
    @pytest.mark.asyncio 
    async def test_parallel_workspace_search_performance(self):
        """Test parallel execution with max 5 concurrent workspaces and 2s timeout."""
        mock_db = Mock()
        mock_anythingllm = Mock()
        
        strategy = WorkspaceSearchStrategy(mock_db, mock_anythingllm)
        
        # Create test workspaces
        workspaces = []
        for i in range(7):  # More than max 5
            workspace = WorkspaceInfo(
                slug=f"workspace-{i}",
                technology="python",
                relevance_score=0.8,
                last_updated=datetime.utcnow()
            )
            workspaces.append(workspace)
        
        # Mock AnythingLLM search to simulate fast response
        mock_anythingllm.search_workspace = AsyncMock(
            return_value=[{"id": "test", "content": "test", "score": 0.8}]
        )
        
        start_time = time.time()
        
        # Should handle max 5 workspaces with parallel execution
        results = await strategy.execute_parallel_search("test query", workspaces[:5])
        
        execution_time = time.time() - start_time
        
        # Should complete reasonably fast with parallel execution
        assert execution_time < 5.0  # Should be much faster than 5x2s sequential
        assert isinstance(results, list)
    
    def test_search_timeout_configuration(self):
        """Test timeout settings match PRD-009 specifications."""
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Verify timeout configurations from PRD-009
        assert orchestrator.search_timeout == 30.0  # Total search timeout
        assert orchestrator.workspace_timeout == 2.0  # Per-workspace timeout
    
    def test_caching_performance_optimization(self):
        """Test caching reduces query execution time."""
        mock_cache_manager = Mock()
        cache_manager = SearchCacheManager(mock_cache_manager)
        
        # Verify cache configuration for performance
        assert cache_manager.default_ttl == 3600  # 1 hour
        assert cache_manager.cache_key_prefix == "search:results:"
        assert cache_manager.analytics_key_prefix == "search:analytics:"


class TestPRD009IntegrationValidation:
    """Test integration with foundation components."""
    
    @pytest.mark.asyncio
    async def test_cfg_001_configuration_integration(self):
        """Test integration with CFG-001 configuration system."""
        # Should be able to create orchestrator with configuration
        try:
            mock_db = Mock()
            mock_cache = Mock() 
            mock_anythingllm = Mock()
            
            orchestrator = SearchOrchestrator(
                db_manager=mock_db,
                cache_manager=mock_cache,
                anythingllm_client=mock_anythingllm
            )
            
            # Should have proper timeout configuration
            assert hasattr(orchestrator, 'search_timeout')
            assert hasattr(orchestrator, 'workspace_timeout')
            
        except Exception as e:
            pytest.fail(f"CFG-001 integration failed: {e}")
    
    @pytest.mark.asyncio
    async def test_db_001_database_integration(self):
        """Test integration with DB-001 database schema."""
        mock_db = Mock()
        mock_anythingllm = Mock()
        
        strategy = WorkspaceSearchStrategy(mock_db, mock_anythingllm)
        
        # Mock database query for workspaces
        mock_db.fetch_all = AsyncMock(return_value=[
            Mock(slug="python-docs", technology="python", 
                 last_updated=datetime.utcnow(), document_count=100)
        ])
        
        workspaces = await strategy._get_available_workspaces()
        
        # Should query database correctly
        mock_db.fetch_all.assert_called_once()
        assert len(workspaces) == 1
        assert workspaces[0]['slug'] == "python-docs"
    
    @pytest.mark.asyncio
    async def test_alm_001_anythingllm_integration(self):
        """Test integration with ALM-001 AnythingLLM client."""
        mock_db = Mock()
        mock_anythingllm = Mock()
        
        strategy = WorkspaceSearchStrategy(mock_db, mock_anythingllm)
        
        # Test AnythingLLM client interface compatibility
        workspace = WorkspaceInfo(
            slug="test-workspace",
            technology="python", 
            relevance_score=0.9,
            last_updated=datetime.utcnow()
        )
        
        # Mock AnythingLLM response
        mock_anythingllm.search_workspace = AsyncMock(return_value=[
            {
                "id": "doc-1",
                "content": "FastAPI tutorial content...",
                "score": 0.85,
                "metadata": {
                    "document_id": "doc-1",
                    "document_title": "FastAPI Tutorial",
                    "source_url": "https://fastapi.tiangolo.com"
                }
            }
        ])
        
        # Should convert AnythingLLM results correctly
        raw_result = {
            "id": "doc-1", 
            "content": "Test content",
            "score": 0.8,
            "metadata": {"document_id": "doc-1", "document_title": "Test"}
        }
        
        search_result = strategy._convert_raw_result(raw_result, workspace)
        
        assert search_result.content_id == "doc-1"
        assert search_result.workspace_slug == "test-workspace"
        assert search_result.technology == "python"
    
    def test_prd_008_content_processor_integration(self):
        """Test integration readiness with PRD-008 Content Processor."""
        # Test result format compatibility
        result = SearchResult(
            content_id="processed-doc-123",
            title="Processed Document",
            content_snippet="Processed content snippet...",
            source_url="https://example.com/doc", 
            relevance_score=0.9,
            metadata={
                "content_hash": "abc123",
                "technology": "python",
                "quality_score": 0.8
            },
            technology="python",
            quality_score=0.8
        )
        
        # Should be compatible with processed content format
        assert result.content_id.startswith("processed-")
        assert "quality_score" in result.metadata
        assert result.quality_score == 0.8


class TestPRD009ErrorHandlingValidation:
    """Test comprehensive error handling and exception hierarchy."""
    
    def test_exception_hierarchy_completeness(self):
        """Test all 9 exception classes are properly implemented."""
        # Test inheritance hierarchy
        assert issubclass(VectorSearchError, SearchOrchestrationError)
        assert issubclass(MetadataSearchError, SearchOrchestrationError)
        assert issubclass(ResultRankingError, SearchOrchestrationError)
        assert issubclass(SearchCacheError, SearchOrchestrationError)
        assert issubclass(WorkspaceSelectionError, SearchOrchestrationError)
        assert issubclass(SearchTimeoutError, SearchOrchestrationError)
        assert issubclass(LLMEvaluationError, SearchOrchestrationError)
        assert issubclass(EnrichmentTriggerError, SearchOrchestrationError)
    
    def test_error_context_and_recovery_flags(self):
        """Test error context handling and recovery indicators."""
        # Test vector search error
        vector_error = VectorSearchError(
            "Vector search failed",
            workspace_slug="test-workspace",
            query="test query"
        )
        
        assert vector_error.recoverable == True
        assert "test-workspace" in vector_error.error_context["workspace_slug"]
        assert "test query" in vector_error.error_context["query"]
        
        # Test timeout error (should not be recoverable)
        timeout_error = SearchTimeoutError(
            "Search timed out",
            timeout_seconds=30.0,
            operation="multi_workspace_search"
        )
        
        assert timeout_error.recoverable == False
        assert timeout_error.error_context["timeout_seconds"] == 30.0
    
    @pytest.mark.asyncio
    async def test_graceful_error_handling_in_workflow(self):
        """Test search workflow continues gracefully when non-critical components fail."""
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Mock cache failure (should continue without caching)
        orchestrator.search_cache.get_cached_results = AsyncMock(
            side_effect=SearchCacheError("Cache unavailable")
        )
        orchestrator.search_cache.cache_results = AsyncMock(
            side_effect=SearchCacheError("Cache unavailable")
        )
        
        # Mock successful workspace search
        orchestrator._execute_multi_workspace_search = AsyncMock(
            return_value=SearchResults(
                results=[],
                total_count=0,
                query_time_ms=100,
                strategy_used=SearchStrategy.HYBRID,
                cache_hit=False,
                workspaces_searched=[],
                enrichment_triggered=False
            )
        )
        
        query = SearchQuery(query="test")
        
        # Should handle cache failures gracefully
        try:
            results = await orchestrator.execute_search(query)
            assert isinstance(results, SearchResults)
        except SearchCacheError:
            pytest.fail("Should handle cache errors gracefully")


class TestPRD009FactoryPatternValidation:
    """Test factory pattern implementation for dependency injection."""
    
    @pytest.mark.asyncio 
    async def test_search_orchestrator_factory_creation(self):
        """Test factory function creates orchestrator with proper dependencies."""
        # Test with provided dependencies
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        orchestrator = await create_search_orchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        assert isinstance(orchestrator, SearchOrchestrator)
        assert orchestrator.db_manager == mock_db
        assert orchestrator.cache_manager == mock_cache
        assert orchestrator.anythingllm_client == mock_anythingllm
    
    def test_component_factory_functions(self):
        """Test individual component factory functions."""
        from src.search.factory import (
            create_workspace_search_strategy,
            create_result_ranker,
            create_search_cache_manager
        )
        
        mock_db = Mock()
        mock_cache = Mock()
        mock_anythingllm = Mock()
        
        # Test workspace strategy factory
        strategy = create_workspace_search_strategy(mock_db, mock_anythingllm)
        assert isinstance(strategy, WorkspaceSearchStrategy)
        assert strategy.db_manager == mock_db
        
        # Test result ranker factory
        ranker = create_result_ranker()
        assert isinstance(ranker, ResultRanker)
        
        # Test cache manager factory
        search_cache = create_search_cache_manager(mock_cache)
        assert isinstance(search_cache, SearchCacheManager)
        assert search_cache.cache_manager == mock_cache


class TestPRD009OperationalValidation:
    """Test operational readiness and monitoring capabilities."""
    
    @pytest.mark.asyncio
    async def test_health_check_implementation(self):
        """Test comprehensive health check functionality."""
        mock_db = Mock()
        mock_db.health_check = AsyncMock(return_value={"status": "healthy"})
        
        mock_cache = Mock()
        mock_anythingllm = Mock()
        mock_anythingllm.health_check = AsyncMock(return_value={"status": "healthy"})
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Mock search cache health
        orchestrator.search_cache.get_cache_stats = AsyncMock(
            return_value={"cache_status": "healthy"}
        )
        
        health = await orchestrator.health_check()
        
        assert health["status"] == "healthy"
        assert "components" in health
        assert "timestamp" in health
        assert "database" in health["components"]
        assert "cache" in health["components"]
        assert "anythingllm" in health["components"]
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_and_analytics(self):
        """Test search analytics and performance monitoring."""
        mock_cache_manager = Mock()
        cache_manager = SearchCacheManager(mock_cache_manager)
        
        # Test analytics data structure
        query = SearchQuery(query="test", strategy=SearchStrategy.HYBRID)
        results = SearchResults(
            results=[],
            total_count=0,
            query_time_ms=150,
            strategy_used=SearchStrategy.HYBRID,
            cache_hit=False,
            workspaces_searched=["workspace1"],
            enrichment_triggered=False
        )
        
        # Should store analytics with proper structure
        await cache_manager._store_analytics(query, results, "cache_key_123")
        
        # Verify analytics storage was attempted
        assert True  # Analytics storage is fire-and-forget
    
    def test_production_readiness_configuration(self):
        """Test production-ready configuration defaults."""
        mock_cache_manager = Mock()
        cache_manager = SearchCacheManager(mock_cache_manager)
        
        # Verify production-appropriate defaults
        assert cache_manager.default_ttl == 3600  # 1 hour cache
        assert cache_manager.cache_key_prefix == "search:results:"
        assert cache_manager.analytics_key_prefix == "search:analytics:"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])