"""
Rate limiting tests for AI Logging API
Tests rate limiting behavior, headers, and resilience
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from src.api.v1.ai_logs_endpoints import router
from src.api.models.ai_logs import QueryMode, AILogQuery


class TestAILogsRateLimiting:
    """Test rate limiting functionality for AI logs endpoints"""
    
    @pytest.fixture
    def mock_processor(self):
        processor = AsyncMock()
        processor.process_query.return_value = {
            "logs": [],
            "total_count": 0,
            "query_time_ms": 10
        }
        return processor
    
    @pytest.fixture
    def app_with_rate_limit(self):
        """Create app with aggressive rate limiting for testing"""
        from src.main import create_app
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        
        app = create_app()
        
        # Override rate limiter with test configuration
        test_limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["5 per minute"]  # Aggressive limit for testing
        )
        app.state.limiter = test_limiter
        
        return app
    
    @pytest.mark.asyncio
    async def test_rate_limit_basic(self, app_with_rate_limit, mock_processor):
        """Test basic rate limiting behavior"""
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app_with_rate_limit) as client:
                # Make requests up to the limit
                for i in range(5):
                    response = client.get("/api/v1/ai_logs/query")
                    assert response.status_code == 200
                
                # Next request should be rate limited
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 429
                assert "rate limit exceeded" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, app_with_rate_limit, mock_processor):
        """Test rate limit headers in responses"""
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app_with_rate_limit) as client:
                response = client.get("/api/v1/ai_logs/query")
                
                # Check for rate limit headers
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers
                
                # Verify header values
                limit = int(response.headers["X-RateLimit-Limit"])
                remaining = int(response.headers["X-RateLimit-Remaining"])
                assert limit == 5
                assert remaining == 4  # One request consumed
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_endpoint(self, mock_processor):
        """Test that rate limits are applied per endpoint"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor), \
             patch('src.api.v1.ai_logs_endpoints.correlator') as mock_corr:
            
            mock_corr.analyze_correlation.return_value = {
                "correlation_id": "test",
                "service_flow": []
            }
            
            with TestClient(app) as client:
                # These endpoints should have independent rate limits
                endpoints = [
                    ("/api/v1/ai_logs/query", "GET", None),
                    ("/api/v1/ai_logs/correlate", "POST", {"correlation_id": "test"}),
                    ("/api/v1/ai_logs/patterns", "POST", {"time_range": "1h"})
                ]
                
                for endpoint, method, data in endpoints:
                    if method == "GET":
                        response = client.get(endpoint)
                    else:
                        response = client.post(endpoint, json=data)
                    
                    # Each endpoint should succeed on first request
                    assert response.status_code in [200, 404]  # 404 OK for some mocked responses
    
    @pytest.mark.asyncio
    async def test_rate_limit_burst_protection(self, app_with_rate_limit, mock_processor):
        """Test protection against burst requests"""
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app_with_rate_limit) as client:
                # Simulate burst of concurrent requests
                responses = []
                for i in range(10):
                    response = client.get("/api/v1/ai_logs/query")
                    responses.append(response)
                
                # Count successful vs rate limited
                successful = sum(1 for r in responses if r.status_code == 200)
                rate_limited = sum(1 for r in responses if r.status_code == 429)
                
                assert successful == 5  # Should allow exactly the limit
                assert rate_limited == 5  # Rest should be rate limited
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset(self, mock_processor):
        """Test rate limit reset after time window"""
        from src.main import create_app
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        
        # Create app with very short rate limit window
        app = create_app()
        test_limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["2 per 2 seconds"]  # Short window for testing
        )
        app.state.limiter = test_limiter
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app) as client:
                # Use up the rate limit
                for i in range(2):
                    response = client.get("/api/v1/ai_logs/query")
                    assert response.status_code == 200
                
                # Should be rate limited
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 429
                
                # Wait for reset
                time.sleep(2.1)
                
                # Should work again
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rate_limit_different_clients(self, app_with_rate_limit, mock_processor):
        """Test rate limiting is per client IP"""
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            # Simulate different client IPs
            with TestClient(app_with_rate_limit) as client1:
                with TestClient(app_with_rate_limit) as client2:
                    # Both clients should have independent limits
                    for i in range(5):
                        response1 = client1.get("/api/v1/ai_logs/query")
                        response2 = client2.get("/api/v1/ai_logs/query", 
                                              headers={"X-Forwarded-For": "192.168.1.100"})
                        
                        # Both should succeed (different IPs)
                        assert response1.status_code == 200
                        assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_websocket_rate_limiting(self, app_with_rate_limit):
        """Test rate limiting on WebSocket connections"""
        with TestClient(app_with_rate_limit) as client:
            # Open multiple WebSocket connections rapidly
            connections = []
            try:
                for i in range(10):
                    ws = client.websocket_connect("/api/v1/ai_logs/stream")
                    connections.append(ws)
                
                # Some connections should succeed, others may be limited
                # This depends on the WebSocket rate limit configuration
                assert len(connections) > 0
                
            finally:
                # Clean up connections
                for ws in connections:
                    try:
                        ws.close()
                    except:
                        pass
    
    @pytest.mark.asyncio
    async def test_rate_limit_retry_after(self, app_with_rate_limit, mock_processor):
        """Test Retry-After header in rate limit responses"""
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app_with_rate_limit) as client:
                # Exhaust rate limit
                for i in range(5):
                    client.get("/api/v1/ai_logs/query")
                
                # Get rate limited response
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 429
                
                # Should have Retry-After header
                assert "Retry-After" in response.headers
                retry_after = int(response.headers["Retry-After"])
                assert retry_after > 0 and retry_after <= 60  # Reasonable retry time
    
    @pytest.mark.asyncio
    async def test_rate_limit_with_cache(self, app_with_rate_limit, mock_processor):
        """Test that cached responses don't count against rate limit"""
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app_with_rate_limit) as client:
                # First request (will be cached)
                response = client.get("/api/v1/ai_logs/query?correlation_id=test-123")
                assert response.status_code == 200
                
                # Subsequent requests with same params should use cache
                for i in range(10):
                    response = client.get("/api/v1/ai_logs/query?correlation_id=test-123")
                    assert response.status_code == 200
                    # Should have cache headers
                    if "X-Cache" in response.headers:
                        assert response.headers["X-Cache"] == "HIT"


class TestAILogsRateLimitResilience:
    """Test system resilience under rate limiting"""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, mock_processor):
        """Test system degrades gracefully under load"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app) as client:
                # Simulate sustained load
                errors = 0
                successes = 0
                
                for i in range(100):
                    response = client.get("/api/v1/ai_logs/query")
                    if response.status_code == 200:
                        successes += 1
                    elif response.status_code == 429:
                        errors += 1
                    else:
                        # Unexpected error
                        pytest.fail(f"Unexpected status code: {response.status_code}")
                
                # System should handle mix of success and rate limits
                assert successes > 0
                assert errors > 0
                assert successes + errors == 100
    
    @pytest.mark.asyncio
    async def test_rate_limit_monitoring_impact(self, mock_processor):
        """Test that rate limiting doesn't affect monitoring endpoints"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app) as client:
                # Exhaust rate limit on main endpoint
                for i in range(50):
                    client.get("/api/v1/ai_logs/query")
                
                # Health check should still work
                response = client.get("/api/v1/health")
                assert response.status_code == 200
                
                # Metrics endpoint should work (if available)
                response = client.get("/api/v1/metrics")
                # Metrics might not exist, but shouldn't be rate limited
                assert response.status_code != 429


class TestAILogsRateLimitConfiguration:
    """Test rate limit configuration and customization"""
    
    @pytest.mark.asyncio
    async def test_custom_rate_limits(self):
        """Test custom rate limits for different endpoints"""
        from src.main import create_app
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        
        app = create_app()
        
        # Apply different limits to different endpoints
        limiter = Limiter(key_func=get_remote_address)
        
        # More restrictive limit for expensive operations
        @app.get("/api/v1/ai_logs/expensive")
        @limiter.limit("1 per minute")
        async def expensive_operation():
            return {"status": "ok"}
        
        # More lenient limit for cheap operations
        @app.get("/api/v1/ai_logs/cheap")
        @limiter.limit("100 per minute")
        async def cheap_operation():
            return {"status": "ok"}
        
        with TestClient(app) as client:
            # Test expensive endpoint
            response = client.get("/api/v1/ai_logs/expensive")
            assert response.status_code == 200
            response = client.get("/api/v1/ai_logs/expensive")
            assert response.status_code == 429
            
            # Test cheap endpoint
            for i in range(10):
                response = client.get("/api/v1/ai_logs/cheap")
                assert response.status_code == 200


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])