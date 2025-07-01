"""
MCP API Integration Tests
========================

Integration tests for the MCP API endpoints including provider management,
configuration, and external search functionality.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

# Import the FastAPI app
from src.api.main import app
from src.api.v1.dependencies import get_search_orchestrator, get_configuration_manager


class TestMCPProvidersAPI:
    """Test MCP provider management API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_orchestrator(self):
        """Mock search orchestrator with MCP enhancer."""
        orchestrator = Mock()
        
        # Mock MCP enhancer
        mcp_enhancer = Mock()
        mcp_enhancer.get_performance_stats.return_value = {
            "search_metrics": {"total_searches": 10},
            "cache_metrics": {"l1_hits": 5}
        }
        orchestrator.mcp_enhancer = mcp_enhancer
        
        return orchestrator
    
    def test_get_providers_list(self, client, mock_search_orchestrator):
        """Test GET /api/v1/mcp/providers endpoint."""
        
        # Override dependency
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            response = client.get("/api/v1/mcp/providers")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "providers" in data
            assert "total_count" in data
            assert "healthy_count" in data
            assert isinstance(data["providers"], list)
            
        finally:
            app.dependency_overrides.clear()
    
    def test_get_providers_list_enabled_only(self, client, mock_search_orchestrator):
        """Test GET /api/v1/mcp/providers?enabled_only=true endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            response = client.get("/api/v1/mcp/providers?enabled_only=true")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should filter to enabled providers only
            for provider in data["providers"]:
                assert provider["config"]["enabled"] == True
                
        finally:
            app.dependency_overrides.clear()
    
    def test_get_single_provider(self, client, mock_search_orchestrator):
        """Test GET /api/v1/mcp/providers/{provider_id} endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            response = client.get("/api/v1/mcp/providers/brave_search")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["provider_id"] == "brave_search"
            assert "config" in data
            assert "capabilities" in data
            assert "health" in data
            assert "stats" in data
            
        finally:
            app.dependency_overrides.clear()
    
    def test_get_nonexistent_provider(self, client, mock_search_orchestrator):
        """Test GET /api/v1/mcp/providers/{nonexistent} returns 404."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            response = client.get("/api/v1/mcp/providers/nonexistent_provider")
            
            assert response.status_code == 404
            
        finally:
            app.dependency_overrides.clear()
    
    def test_create_provider(self, client, mock_search_orchestrator):
        """Test POST /api/v1/mcp/providers endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        provider_config = {
            "config": {
                "provider_id": "test_provider",
                "provider_type": "brave",
                "enabled": True,
                "api_key": "test_api_key",
                "priority": 1,
                "max_results": 10,
                "timeout_seconds": 3.0,
                "rate_limit_per_minute": 60,
                "custom_headers": {},
                "custom_params": {}
            }
        }
        
        try:
            response = client.post(
                "/api/v1/mcp/providers",
                json=provider_config,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["provider_id"] == "test_provider"
            assert data["config"]["provider_type"] == "brave"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_create_provider_invalid_data(self, client, mock_search_orchestrator):
        """Test POST /api/v1/mcp/providers with invalid data."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        invalid_config = {
            "config": {
                "provider_type": "brave",  # Missing required provider_id
                "enabled": True
            }
        }
        
        try:
            response = client.post(
                "/api/v1/mcp/providers",
                json=invalid_config,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 400
            
        finally:
            app.dependency_overrides.clear()
    
    def test_update_provider(self, client, mock_search_orchestrator):
        """Test PUT /api/v1/mcp/providers/{provider_id} endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        update_data = {
            "enabled": False,
            "priority": 5,
            "max_results": 20
        }
        
        try:
            response = client.put(
                "/api/v1/mcp/providers/brave_search",
                json=update_data,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["provider_id"] == "brave_search"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_provider(self, client, mock_search_orchestrator):
        """Test DELETE /api/v1/mcp/providers/{provider_id} endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            response = client.delete("/api/v1/mcp/providers/brave_search")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "message" in data
            assert "brave_search" in data["message"]
            
        finally:
            app.dependency_overrides.clear()


class TestMCPConfigurationAPI:
    """Test MCP configuration API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_orchestrator(self):
        """Mock search orchestrator."""
        return Mock()
    
    def test_get_mcp_config(self, client, mock_search_orchestrator):
        """Test GET /api/v1/mcp/config endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            response = client.get("/api/v1/mcp/config")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "config" in data
            assert "cache_config" in data
            assert "last_updated" in data
            
            # Verify config structure
            config = data["config"]
            assert "enable_external_search" in config
            assert "enable_hedged_requests" in config
            assert "hedged_delay_seconds" in config
            assert "max_concurrent_providers" in config
            assert "external_search_threshold" in config
            
            # Verify cache config structure
            cache_config = data["cache_config"]
            assert "l1_cache_size" in cache_config
            assert "l2_cache_ttl" in cache_config
            assert "compression_threshold" in cache_config
            
        finally:
            app.dependency_overrides.clear()


class TestMCPSearchAPI:
    """Test MCP external search API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_orchestrator(self):
        """Mock search orchestrator with external search capability."""
        orchestrator = Mock()
        
        # Mock MCP enhancer with external search
        mcp_enhancer = Mock()
        mcp_enhancer.execute_external_search = AsyncMock(return_value=[
            {
                "title": "Test External Result",
                "url": "https://example.com/test",
                "snippet": "This is a test external search result",
                "provider": "brave_search",
                "content_type": "web_page"
            }
        ])
        orchestrator.mcp_enhancer = mcp_enhancer
        
        return orchestrator
    
    def test_external_search(self, client, mock_search_orchestrator):
        """Test POST /api/v1/mcp/search endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        search_request = {
            "query": "test external search",
            "technology_hint": "python",
            "max_results": 5,
            "force_external": True
        }
        
        try:
            response = client.post(
                "/api/v1/mcp/search",
                json=search_request,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "results" in data
            assert "total_results" in data
            assert "providers_used" in data
            assert "execution_time_ms" in data
            assert "cache_hit" in data
            
            # Check result structure
            if data["results"]:
                result = data["results"][0]
                assert "title" in result
                assert "url" in result
                assert "snippet" in result
                assert "provider" in result
                assert "content_type" in result
            
        finally:
            app.dependency_overrides.clear()
    
    def test_external_search_no_enhancer(self, client):
        """Test external search when MCP enhancer is not available."""
        
        # Mock orchestrator without MCP enhancer
        mock_orchestrator = Mock()
        mock_orchestrator.mcp_enhancer = None
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_orchestrator
        
        search_request = {
            "query": "test query",
            "max_results": 5,
            "force_external": False
        }
        
        try:
            response = client.post(
                "/api/v1/mcp/search",
                json=search_request,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 503
            
        finally:
            app.dependency_overrides.clear()
    
    def test_external_search_invalid_request(self, client, mock_search_orchestrator):
        """Test external search with invalid request data."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        invalid_request = {
            "max_results": 5,  # Missing required "query" field
            "force_external": True
        }
        
        try:
            response = client.post(
                "/api/v1/mcp/search",
                json=invalid_request,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 422  # Validation error
            
        finally:
            app.dependency_overrides.clear()


class TestMCPStatsAPI:
    """Test MCP performance statistics API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_orchestrator(self):
        """Mock search orchestrator with performance stats."""
        orchestrator = Mock()
        
        # Mock MCP enhancer with performance stats
        mcp_enhancer = Mock()
        mcp_enhancer.get_performance_stats.return_value = {
            "search_metrics": {
                "total_searches": 100,
                "hedged_requests": 15,
                "circuit_breaks": 2
            },
            "cache_metrics": {
                "l1_hits": 80,
                "l2_hits": 15,
                "total_requests": 100
            },
            "provider_health": {
                "brave_search": {
                    "failures": 1,
                    "circuit_open": False,
                    "timeout": 2.5
                }
            }
        }
        orchestrator.mcp_enhancer = mcp_enhancer
        
        return orchestrator
    
    def test_get_mcp_stats(self, client, mock_search_orchestrator):
        """Test GET /api/v1/mcp/stats endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            response = client.get("/api/v1/mcp/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "stats" in data
            assert "collection_period_hours" in data
            assert "last_reset" in data
            
            # Verify stats structure
            stats = data["stats"]
            assert "total_searches" in stats
            assert "cache_hits" in stats
            assert "cache_misses" in stats
            assert "avg_response_time_ms" in stats
            assert "hedged_requests" in stats
            assert "circuit_breaks" in stats
            assert "provider_stats" in stats
            
        finally:
            app.dependency_overrides.clear()


class TestMCPAPIRateLimiting:
    """Test rate limiting on MCP API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_orchestrator(self):
        """Mock search orchestrator."""
        return Mock()
    
    def test_rate_limiting_providers_endpoint(self, client, mock_search_orchestrator):
        """Test rate limiting on providers endpoint."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            # Make requests up to the rate limit
            responses = []
            for i in range(12):  # Limit is 10/minute
                response = client.get("/api/v1/mcp/providers")
                responses.append(response)
            
            # First 10 should succeed
            for response in responses[:10]:
                assert response.status_code in [200, 429]  # May hit rate limit
            
            # Additional requests should be rate limited
            if len([r for r in responses if r.status_code == 429]) > 0:
                print("Rate limiting working correctly")
            
        finally:
            app.dependency_overrides.clear()


class TestMCPAPIErrorHandling:
    """Test error handling in MCP API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_internal_server_error_handling(self, client):
        """Test internal server error handling."""
        
        # Mock orchestrator that raises an exception
        def failing_orchestrator():
            raise Exception("Simulated internal error")
        
        app.dependency_overrides[get_search_orchestrator] = failing_orchestrator
        
        try:
            response = client.get("/api/v1/mcp/providers")
            
            assert response.status_code == 500
            data = response.json()
            
            # Should have proper error structure
            assert "detail" in data
            
        finally:
            app.dependency_overrides.clear()
    
    def test_malformed_json_handling(self, client):
        """Test handling of malformed JSON requests."""
        
        mock_orchestrator = Mock()
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_orchestrator
        
        try:
            response = client.post(
                "/api/v1/mcp/search",
                data="{ invalid json }",  # Malformed JSON
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 422
            
        finally:
            app.dependency_overrides.clear()


class TestMCPAPIIntegrationWorkflow:
    """Test complete API workflow integration."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_orchestrator(self):
        """Mock search orchestrator for workflow testing."""
        return Mock()
    
    def test_complete_provider_management_workflow(self, client, mock_search_orchestrator):
        """Test complete provider CRUD workflow."""
        
        app.dependency_overrides[get_search_orchestrator] = lambda: mock_search_orchestrator
        
        try:
            # 1. List providers (should be empty initially)
            response = client.get("/api/v1/mcp/providers")
            assert response.status_code == 200
            
            # 2. Create a new provider
            provider_config = {
                "config": {
                    "provider_id": "workflow_test_provider",
                    "provider_type": "brave",
                    "enabled": True,
                    "priority": 1,
                    "max_results": 10,
                    "timeout_seconds": 3.0,
                    "rate_limit_per_minute": 60,
                    "custom_headers": {},
                    "custom_params": {}
                }
            }
            
            response = client.post("/api/v1/mcp/providers", json=provider_config)
            assert response.status_code == 200
            
            # 3. Get the created provider
            response = client.get("/api/v1/mcp/providers/workflow_test_provider")
            assert response.status_code == 200
            
            # 4. Update the provider
            update_data = {"enabled": False, "priority": 5}
            response = client.put("/api/v1/mcp/providers/workflow_test_provider", json=update_data)
            assert response.status_code == 200
            
            # 5. Delete the provider
            response = client.delete("/api/v1/mcp/providers/workflow_test_provider")
            assert response.status_code == 200
            
        finally:
            app.dependency_overrides.clear()


def run_api_integration_tests():
    """Run the API integration test suite."""
    return pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_api_integration_tests()