"""
MCP Search System Validation Suite
==================================

Comprehensive system validation tests that verify the complete MCP search system
integration including all components working together end-to-end.
"""

import asyncio
import pytest
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import system components for integration testing
from src.search.orchestrator import SearchOrchestrator
from src.search.models import SearchQuery, SearchStrategy
from src.mcp.core.models import NormalizedQuery
from src.mcp.providers.models import SearchOptions, SearchResults, SearchResult, SearchResultType
from src.mcp.text_ai.llm_adapter import TextAILLMAdapter
from src.search.mcp_integration import MCPSearchEnhancer
from src.search.optimized_cache import OptimizedCacheManager


class TestMCPSystemIntegration:
    """Test complete MCP system integration."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create all mock dependencies for system testing."""
        
        # Mock database manager
        mock_db = Mock()
        mock_db.fetch_all = AsyncMock(return_value=[
            {
                "slug": "python_docs",
                "name": "Python Documentation",
                "technology": "python", 
                "last_updated": datetime.utcnow(),
                "document_count": 150
            },
            {
                "slug": "javascript_docs", 
                "name": "JavaScript Documentation",
                "technology": "javascript",
                "last_updated": datetime.utcnow(),
                "document_count": 200
            }
        ])
        mock_db.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Mock cache manager
        mock_cache = Mock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_cache.get_cache_stats = AsyncMock(return_value={"status": "healthy"})
        
        # Mock AnythingLLM client
        mock_anythingllm = Mock()
        mock_anythingllm.search_workspace = AsyncMock(return_value=[
            {
                "id": "doc_1",
                "content": "Python asyncio is a library for concurrent programming",
                "score": 0.92,
                "metadata": {
                    "document_title": "Python AsyncIO Guide",
                    "source_url": "https://docs.python.org/asyncio",
                    "workspace": "python_docs"
                }
            },
            {
                "id": "doc_2",
                "content": "FastAPI framework supports async request handling",
                "score": 0.85,
                "metadata": {
                    "document_title": "FastAPI Async Tutorial", 
                    "source_url": "https://fastapi.tiangolo.com/async",
                    "workspace": "python_docs"
                }
            }
        ])
        mock_anythingllm.health_check = AsyncMock(return_value={"status": "healthy"})
        
        # Mock LLM client for MCP integration
        mock_llm_client = Mock()
        mock_llm_client.evaluate_search_results = Mock(return_value=Mock(
            avg_relevance_score=0.88,
            completeness_score=0.75,
            confidence_score=0.90,
            missing_info=["examples", "code_samples"],
            needs_external_search=True
        ))
        
        return {
            "db": mock_db,
            "cache": mock_cache,
            "anythingllm": mock_anythingllm,
            "llm_client": mock_llm_client
        }
    
    @pytest.mark.asyncio
    async def test_complete_search_orchestrator_with_mcp(self, mock_dependencies):
        """Test SearchOrchestrator with MCP enhancement integration."""
        
        # Create orchestrator with all dependencies
        orchestrator = SearchOrchestrator(
            db_manager=mock_dependencies["db"],
            cache_manager=mock_dependencies["cache"], 
            anythingllm_client=mock_dependencies["anythingllm"],
            llm_client=mock_dependencies["llm_client"]
        )
        
        # Verify MCP enhancer is initialized
        assert orchestrator.mcp_enhancer is not None
        assert hasattr(orchestrator.mcp_enhancer, 'execute_external_search')
        
        # Execute search with technology hint
        query = SearchQuery(
            query="python asyncio tutorial",
            technology_hint="python",
            strategy=SearchStrategy.HYBRID,
            limit=5
        )
        
        # Mock cache miss
        orchestrator.search_cache.get_cached_results = AsyncMock(return_value=None)
        orchestrator.search_cache.cache_results = AsyncMock()
        
        # Execute search
        results, normalized_query = await orchestrator.execute_search(query)
        
        # Validate results
        assert results is not None
        assert len(results.results) > 0
        assert results.total_count >= len(results.results)
        assert results.query_time_ms > 0
        assert results.strategy_used == SearchStrategy.HYBRID
        
        # Validate normalized query
        assert normalized_query.query == "python asyncio tutorial"
        assert normalized_query.technology_hint == "python"
        
        # Verify workspace search was called
        mock_dependencies["anythingllm"].search_workspace.assert_called()
        
        # Verify database was queried for workspaces
        mock_dependencies["db"].fetch_all.assert_called()
    
    @pytest.mark.asyncio
    async def test_mcp_external_search_integration(self, mock_dependencies):
        """Test MCP external search integration with real workflow."""
        
        # Create MCP search enhancer
        mcp_enhancer = MCPSearchEnhancer(llm_client=mock_dependencies["llm_client"])
        
        # Test external search query generation
        external_query = await mcp_enhancer.get_external_search_query(
            "python asyncio tutorial",
            technology_hint="python"
        )
        
        assert "python" in external_query.lower()
        assert "asyncio" in external_query.lower()
        
        # Test workspace selection enhancement
        available_workspaces = [
            {"id": "python_docs", "technologies": ["python"], "priority": 1},
            {"id": "javascript_docs", "technologies": ["javascript"], "priority": 2}, 
            {"id": "general_docs", "tags": ["general"], "priority": 3}
        ]
        
        selected = await mcp_enhancer.enhance_workspace_selection(
            "python async programming",
            available_workspaces,
            technology_hint="python"
        )
        
        assert "python_docs" in selected
        assert len(selected) <= 5
    
    @pytest.mark.asyncio
    async def test_optimized_cache_integration(self, mock_dependencies):
        """Test optimized cache integration with real usage patterns."""
        
        # Create optimized cache manager
        cache_manager = OptimizedCacheManager(
            redis_cache=mock_dependencies["cache"],
            l1_size=50,
            compress_threshold=100,
            enable_stats=True
        )
        
        # Test cache operations
        test_key = "search:test_query"
        test_data = {
            "results": ["result1", "result2"],
            "metadata": {"count": 2, "time": 150},
            "timestamp": time.time()
        }
        
        # Set data
        await cache_manager.set(test_key, test_data)
        
        # Get data (should hit L1 cache)
        retrieved = await cache_manager.get(test_key)
        assert retrieved == test_data
        
        # Check cache stats
        stats = cache_manager.get_stats()
        assert stats["l1_hits"] >= 1
        assert "total_operations" in stats
    
    @pytest.mark.asyncio
    async def test_text_ai_llm_adapter_integration(self, mock_dependencies):
        """Test TextAI LLM adapter integration."""
        
        # Create Text AI adapter
        adapter = TextAILLMAdapter(
            llm_client=mock_dependencies["llm_client"]
        )
        
        # Create test query
        query = NormalizedQuery(
            original_query="python asyncio tutorial",
            normalized_text="python asyncio tutorial", 
            technology_hint="python",
            query_hash="test_hash_123",
            tokens=["python", "asyncio", "tutorial"]
        )
        
        # Test external query generation
        external_query = await adapter.generate_external_query(
            query,
            Mock(relevance_score=0.3, needs_external_search=True)
        )
        
        assert len(external_query) > 0
        assert "python" in external_query.lower()
        
        # Test workspace selection
        workspaces = [
            {"id": "python_docs", "technologies": ["python"], "priority": 1},
            {"id": "web_docs", "technologies": ["html", "css"], "priority": 2}
        ]
        
        selected = await adapter.select_workspaces(query, workspaces)
        assert "python_docs" in selected


class TestSystemHealthAndMonitoring:
    """Test system health monitoring and diagnostics."""
    
    @pytest.fixture
    def system_orchestrator(self):
        """Create orchestrator for health testing."""
        mock_db = Mock()
        mock_db.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_db.fetch_all = AsyncMock(return_value=[
            {"slug": "test_workspace", "technology": "python"}
        ])
        
        mock_cache = Mock()
        mock_cache.get_cache_stats = AsyncMock(return_value={"status": "healthy"})
        
        mock_anythingllm = Mock()
        mock_anythingllm.health_check = AsyncMock(return_value={"status": "healthy"})
        
        return SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
    
    @pytest.mark.asyncio
    async def test_system_health_check(self, system_orchestrator):
        """Test comprehensive system health check."""
        
        # Execute health check
        health = await system_orchestrator.health_check()
        
        # Validate health response structure
        assert "overall_status" in health
        assert "services" in health
        assert "timestamp" in health
        assert "response_time_ms" in health
        
        # Validate individual service health
        services = health["services"]
        service_names = [service["service"] for service in services]
        
        expected_services = [
            "database", 
            "cache_manager",
            "anythingllm_client",
            "search_strategy"
        ]
        
        for expected_service in expected_services:
            assert expected_service in service_names
        
        # All services should be healthy in this test
        assert health["overall_status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_mcp_performance_monitoring(self, system_orchestrator):
        """Test MCP performance monitoring integration."""
        
        # Mock MCP enhancer with performance stats
        mock_mcp_enhancer = Mock()
        mock_mcp_enhancer.get_performance_stats = Mock(return_value={
            "search_metrics": {
                "total_searches": 100,
                "external_searches": 20,
                "avg_response_time_ms": 250,
                "hedged_requests": 5,
                "circuit_breaks": 1
            },
            "cache_metrics": {
                "l1_hits": 75,
                "l2_hits": 15,
                "total_requests": 100,
                "hit_ratio": 0.90,
                "compressions": 10
            },
            "provider_health": {
                "brave_search": {
                    "status": "healthy",
                    "success_rate": 0.98,
                    "avg_latency_ms": 180,
                    "circuit_open": False
                },
                "google_search": {
                    "status": "degraded", 
                    "success_rate": 0.85,
                    "avg_latency_ms": 400,
                    "circuit_open": False
                }
            }
        })
        
        system_orchestrator.mcp_enhancer = mock_mcp_enhancer
        
        # Get performance stats
        stats = system_orchestrator.mcp_enhancer.get_performance_stats()
        
        # Validate performance metrics
        assert stats["search_metrics"]["total_searches"] == 100
        assert stats["cache_metrics"]["hit_ratio"] == 0.90
        assert "brave_search" in stats["provider_health"]
        assert stats["provider_health"]["brave_search"]["status"] == "healthy"


class TestSystemStressValidation:
    """Test system behavior under stress conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_search_handling(self):
        """Test system handling of concurrent search requests."""
        
        # Create lightweight orchestrator for stress testing
        mock_db = Mock()
        mock_db.fetch_all = AsyncMock(return_value=[{"slug": "test"}])
        
        mock_cache = Mock() 
        mock_cache.get_cache_stats = AsyncMock(return_value={"status": "healthy"})
        
        mock_anythingllm = Mock()
        mock_anythingllm.search_workspace = AsyncMock(return_value=[
            {"id": "1", "content": "test", "score": 0.8, "metadata": {}}
        ])
        
        orchestrator = SearchOrchestrator(
            db_manager=mock_db,
            cache_manager=mock_cache,
            anythingllm_client=mock_anythingllm
        )
        
        # Mock cache for faster execution
        orchestrator.search_cache.get_cached_results = AsyncMock(return_value=None)
        orchestrator.search_cache.cache_results = AsyncMock()
        
        # Create multiple concurrent search tasks
        async def single_search(query_id):
            query = SearchQuery(
                query=f"test query {query_id}",
                strategy=SearchStrategy.HYBRID,
                limit=3
            )
            
            start = time.time()
            results, _ = await orchestrator.execute_search(query)
            duration = (time.time() - start) * 1000
            
            return {
                "query_id": query_id,
                "success": len(results.results) > 0,
                "duration_ms": duration
            }
        
        # Execute concurrent searches
        tasks = [single_search(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate results
        successful_results = [r for r in results if isinstance(r, dict) and r["success"]]
        assert len(successful_results) >= 18  # Allow for some failures
        
        avg_duration = sum(r["duration_ms"] for r in successful_results) / len(successful_results)
        assert avg_duration < 1000  # Should complete within 1 second
        
        print(f"Concurrent stress test: {len(successful_results)}/20 successful, avg {avg_duration:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_memory_usage_validation(self):
        """Test memory usage under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create cache and fill with data
        mock_redis = Mock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        
        cache_manager = OptimizedCacheManager(
            redis_cache=mock_redis,
            l1_size=500,
            enable_stats=True
        )
        
        # Fill cache with test data
        for i in range(500):
            test_data = {
                "results": [f"result_{j}" for j in range(10)],
                "metadata": {"query": f"test_query_{i}", "time": time.time()},
                "large_content": "x" * 1000  # 1KB per item
            }
            await cache_manager.set(f"test_key_{i}", test_data)
        
        # Check memory usage
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = peak_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 200  # Should not exceed 200MB
        
        print(f"Memory validation: {initial_memory:.1f}MB -> {peak_memory:.1f}MB (+{memory_growth:.1f}MB)")


def run_system_validation_suite():
    """Run the complete system validation test suite."""
    print("=" * 70)
    print("MCP Search System Comprehensive Validation Suite")
    print("=" * 70)
    
    start_time = time.time()
    
    exit_code = pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x"  # Stop on first failure
    ])
    
    total_time = time.time() - start_time
    print(f"\nTotal system validation time: {total_time:.1f} seconds")
    
    if exit_code == 0:
        print("✅ ALL SYSTEM VALIDATION TESTS PASSED")
    else:
        print("❌ SYSTEM VALIDATION FAILURES DETECTED")
    
    return exit_code


if __name__ == "__main__":
    run_system_validation_suite()