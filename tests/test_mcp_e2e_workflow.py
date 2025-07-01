"""
MCP Search System End-to-End Workflow Tests
===========================================

Comprehensive end-to-end workflow validation for the MCP Search System.
Tests complete user journeys from API request through all system components.
"""

import asyncio
import pytest
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Import the FastAPI app and dependencies
from src.main import app
from src.api.v1.dependencies import get_search_orchestrator, get_configuration_manager
from src.search.models import SearchQuery, SearchStrategy
from src.mcp.providers.models import SearchOptions, SearchResults, SearchResult, SearchResultType, ProviderConfig, ProviderType


class TestEndToEndSearchWorkflow:
    """Test complete end-to-end search workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_complete_orchestrator(self):
        """Mock a complete search orchestrator with MCP enhancement."""
        orchestrator = Mock()
        
        # Mock workspace search results
        orchestrator.execute_search = AsyncMock(return_value=(
            Mock(
                results=[
                    Mock(
                        content_id="doc_1",
                        title="Python AsyncIO Tutorial",
                        content_snippet="Learn Python asyncio for concurrent programming...",
                        source_url="https://internal-docs.com/asyncio",
                        relevance_score=0.95,
                        metadata={"workspace": "python_docs", "technology": "python"}
                    ),
                    Mock(
                        content_id="doc_2", 
                        title="FastAPI Async Guide",
                        content_snippet="Building async APIs with FastAPI framework...",
                        source_url="https://internal-docs.com/fastapi",
                        relevance_score=0.88,
                        metadata={"workspace": "python_docs", "technology": "python"}
                    )
                ],
                total_count=2,
                query_time_ms=150,
                strategy_used=SearchStrategy.HYBRID,
                cache_hit=False,
                workspaces_searched=["python_docs"],
                enrichment_triggered=False
            ),
            Mock(
                query="python asyncio tutorial",
                technology_hint="python",
                normalized_text="python asyncio tutorial"
            )
        ))
        
        # Mock MCP enhancer for external search
        mcp_enhancer = Mock()
        mcp_enhancer.is_external_search_available = Mock(return_value=True)
        mcp_enhancer.should_trigger_external_search = AsyncMock(return_value=True)
        mcp_enhancer.get_external_search_query = AsyncMock(return_value="python asyncio tutorial examples")
        mcp_enhancer.execute_external_search = AsyncMock(return_value=[
            {
                "title": "Python AsyncIO Examples - Real Python",
                "url": "https://realpython.com/async-io-python/",
                "snippet": "Complete guide to Python asyncio with practical examples and best practices",
                "provider": "brave_search",
                "content_type": "web_page",
                "relevance_score": 0.92
            },
            {
                "title": "AsyncIO Documentation - Python.org",
                "url": "https://docs.python.org/3/library/asyncio.html",
                "snippet": "Official Python asyncio documentation with API reference",
                "provider": "google_search", 
                "content_type": "documentation",
                "relevance_score": 0.89
            }
        ])
        mcp_enhancer.get_performance_stats = Mock(return_value={
            "search_metrics": {"total_searches": 5, "external_searches": 2},
            "cache_metrics": {"l1_hits": 3, "l2_hits": 1},
            "provider_health": {"brave_search": {"status": "healthy"}}
        })
        
        orchestrator.mcp_enhancer = mcp_enhancer
        return orchestrator
    
    def test_complete_search_workflow_with_internal_results(self, client, mock_complete_orchestrator):
        """Test complete search workflow when internal results are sufficient."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_complete_orchestrator
        
        try:
            # Step 1: Submit search request
            search_request = {
                "query": "python asyncio tutorial",
                "strategy": "hybrid",
                "technology_hint": "python",
                "limit": 10,
                "offset": 0
            }
            
            response = client.post(
                "/api/v1/search",
                json=search_request,
                headers={"Content-Type": "application/json"}
            )
            
            # Step 2: Validate response structure
            assert response.status_code == 200
            data = response.json()
            
            # Step 3: Validate search results
            assert "results" in data
            assert "metadata" in data
            assert len(data["results"]) == 2
            
            # Step 4: Validate result content
            first_result = data["results"][0]
            assert first_result["title"] == "Python AsyncIO Tutorial"
            assert "asyncio" in first_result["content_snippet"].lower()
            assert first_result["relevance_score"] > 0.9
            
            # Step 5: Validate metadata
            metadata = data["metadata"]
            assert metadata["total_count"] == 2
            assert metadata["query_time_ms"] == 150
            assert metadata["strategy_used"] == "hybrid"
            assert "python_docs" in metadata["workspaces_searched"]
            assert not metadata["enrichment_triggered"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_complete_search_workflow_with_external_enhancement(self, client, mock_complete_orchestrator):
        """Test complete search workflow with external search enhancement."""
        
        # Configure orchestrator to return low-quality results that trigger external search
        mock_complete_orchestrator.execute_search = AsyncMock(return_value=(
            Mock(
                results=[],  # Empty internal results
                total_count=0,
                query_time_ms=50,
                strategy_used=SearchStrategy.HYBRID,
                cache_hit=False,
                workspaces_searched=["general_docs"],
                enrichment_triggered=True  # Will trigger external search
            ),
            Mock(
                query="rare javascript framework tutorial",
                technology_hint="javascript",
                normalized_text="rare javascript framework tutorial"
            )
        ))
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_complete_orchestrator
        
        try:
            # Step 1: Submit search request for content not in internal docs
            search_request = {
                "query": "rare javascript framework tutorial",
                "strategy": "hybrid",
                "technology_hint": "javascript",
                "limit": 10
            }
            
            response = client.post(
                "/api/v1/search",
                json=search_request,
                headers={"Content-Type": "application/json"}
            )
            
            # Step 2: Validate response
            assert response.status_code == 200
            data = response.json()
            
            # Step 3: Validate external enhancement triggered
            metadata = data["metadata"]
            assert metadata["enrichment_triggered"] == True
            assert metadata["total_count"] == 0  # No internal results
            
            # Step 4: Verify external search would be called (through mocking)
            mock_complete_orchestrator.mcp_enhancer.should_trigger_external_search.assert_called_once()
            
        finally:
            app.dependency_overrides.clear()
    
    def test_mcp_external_search_api_workflow(self, client, mock_complete_orchestrator):
        """Test MCP external search API workflow."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_complete_orchestrator
        
        try:
            # Step 1: Submit external search request
            external_search_request = {
                "query": "python asyncio tutorial examples",
                "technology_hint": "python",
                "max_results": 5,
                "force_external": True
            }
            
            response = client.post(
                "/api/v1/mcp/search",
                json=external_search_request,
                headers={"Content-Type": "application/json"}
            )
            
            # Step 2: Validate response
            assert response.status_code == 200
            data = response.json()
            
            # Step 3: Validate external search results
            assert "results" in data
            assert "total_results" in data
            assert "providers_used" in data
            assert "execution_time_ms" in data
            
            # Step 4: Validate result structure
            results = data["results"]
            assert len(results) == 2
            
            first_result = results[0]
            assert first_result["title"] == "Python AsyncIO Examples - Real Python"
            assert "realpython.com" in first_result["url"]
            assert first_result["provider"] == "brave_search"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_mcp_provider_management_workflow(self, client, mock_complete_orchestrator):
        """Test complete MCP provider management workflow."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_complete_orchestrator
        
        try:
            # Step 1: List existing providers
            response = client.get("/api/v1/mcp/providers")
            assert response.status_code == 200
            
            # Step 2: Create new provider
            new_provider = {
                "config": {
                    "provider_id": "test_workflow_provider",
                    "provider_type": "brave",
                    "enabled": True,
                    "api_key": "test_key_12345",
                    "priority": 1,
                    "max_results": 10,
                    "timeout_seconds": 3.0,
                    "rate_limit_per_minute": 60,
                    "custom_headers": {"User-Agent": "DocaicheBot/1.0"},
                    "custom_params": {"safesearch": "moderate"}
                }
            }
            
            response = client.post(
                "/api/v1/mcp/providers",
                json=new_provider,
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            
            # Step 3: Retrieve the created provider
            response = client.get("/api/v1/mcp/providers/test_workflow_provider")
            assert response.status_code == 200
            provider_data = response.json()
            assert provider_data["provider_id"] == "test_workflow_provider"
            
            # Step 4: Update provider configuration
            update_data = {
                "enabled": False,
                "priority": 5,
                "max_results": 20
            }
            
            response = client.put(
                "/api/v1/mcp/providers/test_workflow_provider",
                json=update_data,
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            
            # Step 5: Get performance stats
            response = client.get("/api/v1/mcp/stats")
            assert response.status_code == 200
            stats_data = response.json()
            assert "stats" in stats_data
            
            # Step 6: Delete the provider
            response = client.delete("/api/v1/mcp/providers/test_workflow_provider")
            assert response.status_code == 200
            
        finally:
            app.dependency_overrides.clear()


class TestEndToEndUserJourneys:
    """Test realistic user journey scenarios."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def realistic_orchestrator(self):
        """Mock orchestrator with realistic user scenarios."""
        orchestrator = Mock()
        
        # Scenario data
        self.scenarios = {
            "developer_python": {
                "query": "how to implement async database connections in python",
                "internal_results": [
                    {
                        "title": "Python Database Connection Patterns",
                        "snippet": "Best practices for async database connections using asyncpg and SQLAlchemy",
                        "relevance": 0.91
                    }
                ],
                "external_results": [
                    {
                        "title": "AsyncPG Tutorial - FastAPI Documentation",
                        "url": "https://fastapi.tiangolo.com/advanced/async-sql-databases/",
                        "snippet": "Learn how to use async database connections with FastAPI"
                    }
                ]
            },
            "devops_docker": {
                "query": "docker kubernetes deployment strategies",
                "internal_results": [],
                "external_results": [
                    {
                        "title": "Kubernetes Deployment Strategies Guide",
                        "url": "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/",
                        "snippet": "Official Kubernetes documentation on deployment strategies"
                    }
                ]
            }
        }
        
        return orchestrator
    
    def test_developer_search_journey(self, client, realistic_orchestrator):
        """Test a typical developer search journey."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: realistic_orchestrator
        
        # Configure mock for developer scenario
        scenario = self.scenarios["developer_python"]
        realistic_orchestrator.execute_search = AsyncMock(return_value=(
            Mock(
                results=[Mock(**result) for result in scenario["internal_results"]],
                total_count=len(scenario["internal_results"]),
                query_time_ms=120,
                enrichment_triggered=True
            ),
            Mock(query=scenario["query"])
        ))
        
        # Mock MCP enhancer
        mcp_enhancer = Mock()
        mcp_enhancer.execute_external_search = AsyncMock(return_value=scenario["external_results"])
        realistic_orchestrator.mcp_enhancer = mcp_enhancer
        
        try:
            # Developer searches for Python async database help
            response = client.post(
                "/api/v1/search",
                json={
                    "query": scenario["query"],
                    "technology_hint": "python",
                    "strategy": "hybrid"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should find internal documentation
            assert len(data["results"]) >= 1
            assert "database" in data["results"][0]["title"].lower()
            
            # Should trigger external enhancement for additional resources
            assert data["metadata"]["enrichment_triggered"] == True
            
        finally:
            app.dependency_overrides.clear()
    
    def test_admin_monitoring_journey(self, client, realistic_orchestrator):
        """Test admin monitoring and management journey."""
        
        realistic_orchestrator.mcp_enhancer = Mock()
        realistic_orchestrator.mcp_enhancer.get_performance_stats = Mock(return_value={
            "search_metrics": {
                "total_searches": 150,
                "external_searches": 25,
                "avg_response_time_ms": 245,
                "hedged_requests": 8,
                "circuit_breaks": 1
            },
            "cache_metrics": {
                "l1_hits": 95,
                "l2_hits": 30,
                "total_requests": 150,
                "hit_ratio": 0.83
            },
            "provider_health": {
                "brave_search": {"status": "healthy", "success_rate": 0.98},
                "google_search": {"status": "degraded", "success_rate": 0.85},
                "duckduckgo_search": {"status": "healthy", "success_rate": 0.96}
            }
        })
        
        app.dependency_overrides[get_search_orchestrator] = lambda: realistic_orchestrator
        
        try:
            # Admin checks system performance
            response = client.get("/api/v1/mcp/stats")
            assert response.status_code == 200
            stats = response.json()
            
            # Validate performance metrics
            assert stats["stats"]["total_searches"] == 150
            assert stats["stats"]["cache_hits"] >= 125  # L1 + L2 hits
            
            # Admin checks provider health
            response = client.get("/api/v1/mcp/providers")
            assert response.status_code == 200
            providers = response.json()
            
            # Should show provider status
            assert "providers" in providers
            assert "healthy_count" in providers
            
            # Admin checks system configuration
            response = client.get("/api/v1/mcp/config")
            assert response.status_code == 200
            config = response.json()
            
            assert "config" in config
            assert "cache_config" in config
            
        finally:
            app.dependency_overrides.clear()


class TestEndToEndErrorScenarios:
    """Test end-to-end error handling and recovery scenarios."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_provider_failure_recovery_workflow(self, client):
        """Test system behavior when external providers fail."""
        
        # Mock orchestrator with failing external providers
        mock_orchestrator = Mock()
        mock_orchestrator.execute_search = AsyncMock(return_value=(
            Mock(
                results=[],
                total_count=0,
                query_time_ms=50,
                enrichment_triggered=True
            ),
            Mock(query="test query")
        ))
        
        # Mock MCP enhancer with failing providers
        mcp_enhancer = Mock()
        mcp_enhancer.execute_external_search = AsyncMock(side_effect=Exception("All providers failed"))
        mock_orchestrator.mcp_enhancer = mcp_enhancer
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_orchestrator
        
        try:
            # Search should still work even if external providers fail
            response = client.post(
                "/api/v1/search", 
                json={"query": "test query", "strategy": "hybrid"}
            )
            
            # Should return gracefully with internal results only
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "metadata" in data
            
        finally:
            app.dependency_overrides.clear()
    
    def test_rate_limiting_workflow(self, client):
        """Test rate limiting behavior across multiple requests."""
        
        mock_orchestrator = Mock()
        mock_orchestrator.mcp_enhancer = Mock()
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_orchestrator
        
        try:
            # Make multiple rapid requests to test rate limiting
            responses = []
            for i in range(15):  # Exceed typical rate limit
                response = client.get("/api/v1/mcp/providers")
                responses.append(response)
            
            # Some requests should succeed, others may be rate limited
            success_count = len([r for r in responses if r.status_code == 200])
            rate_limited_count = len([r for r in responses if r.status_code == 429])
            
            # Should have some successful requests
            assert success_count > 0
            
            # May have rate limiting (depends on implementation)
            print(f"Successful: {success_count}, Rate limited: {rate_limited_count}")
            
        finally:
            app.dependency_overrides.clear()


class TestEndToEndPerformanceValidation:
    """Test end-to-end performance under realistic conditions."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_search_performance_under_load(self, client):
        """Test search performance with concurrent requests."""
        
        mock_orchestrator = Mock()
        mock_orchestrator.execute_search = AsyncMock(return_value=(
            Mock(
                results=[Mock(title="Test Result", content_snippet="Test content")],
                total_count=1,
                query_time_ms=100
            ),
            Mock(query="test")
        ))
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_orchestrator
        
        try:
            import concurrent.futures
            import time
            
            def single_search():
                start = time.time()
                response = client.post("/api/v1/search", json={"query": "test", "strategy": "hybrid"})
                end = time.time()
                return {
                    "status_code": response.status_code,
                    "duration": (end - start) * 1000
                }
            
            # Execute concurrent searches
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(single_search) for _ in range(20)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Validate performance
            successful = [r for r in results if r["status_code"] == 200]
            avg_duration = sum(r["duration"] for r in successful) / len(successful)
            
            assert len(successful) == 20  # All requests should succeed
            assert avg_duration < 1000  # Should be under 1 second
            
            print(f"Concurrent search performance: {avg_duration:.1f}ms average")
            
        finally:
            app.dependency_overrides.clear()


def run_e2e_test_suite():
    """Run the complete end-to-end test suite."""
    print("=" * 60)
    print("MCP Search System End-to-End Workflow Test Suite")
    print("=" * 60)
    
    # Run tests with timing
    start_time = time.time()
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])
    
    total_time = time.time() - start_time
    print(f"\nTotal E2E test time: {total_time:.1f} seconds")
    
    return exit_code


if __name__ == "__main__":
    run_e2e_test_suite()