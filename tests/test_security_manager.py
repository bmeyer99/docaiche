"""
Test Security Manager Implementation
===================================

Comprehensive tests for security manager, middleware, and policies.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from mcp.security.security_manager import (
    SecurityManager, SecurityPolicy, SecurityEvent,
    ThreatLevel, ClientSecurityProfile, RateLimiter
)
from mcp.security.security_middleware import SecurityMiddleware
from mcp.schemas import MCPRequest, MCPResponse, MCPError
from mcp.exceptions import SecurityError, RateLimitError, AuthorizationError


class TestSecurityPolicy:
    """Test security policy configuration."""
    
    def test_default_policy(self):
        """Test default security policy values."""
        policy = SecurityPolicy()
        
        assert policy.rate_limit_window == 60
        assert policy.rate_limit_max_requests == 60
        assert policy.max_auth_failures == 5
        assert policy.require_explicit_consent is True
        assert "ingest/document" in policy.sensitive_operations
    
    def test_custom_policy(self):
        """Test custom security policy."""
        policy = SecurityPolicy(
            rate_limit_max_requests=100,
            max_auth_failures=3,
            require_explicit_consent=False
        )
        
        assert policy.rate_limit_max_requests == 100
        assert policy.max_auth_failures == 3
        assert policy.require_explicit_consent is False


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test basic rate limiting."""
        policy = SecurityPolicy(
            rate_limit_max_requests=10,
            rate_limit_window=60,
            rate_limit_burst_size=5
        )
        limiter = RateLimiter(policy)
        
        # Should allow burst size requests immediately
        for i in range(5):
            allowed, retry_after = await limiter.check_rate_limit("client1")
            assert allowed is True
            assert retry_after is None
        
        # 6th request should be rate limited
        allowed, retry_after = await limiter.check_rate_limit("client1")
        assert allowed is False
        assert retry_after > 0
    
    @pytest.mark.asyncio
    async def test_multiple_clients(self):
        """Test rate limiting for multiple clients."""
        policy = SecurityPolicy(rate_limit_burst_size=2)
        limiter = RateLimiter(policy)
        
        # Each client should have independent limits
        allowed1, _ = await limiter.check_rate_limit("client1")
        allowed2, _ = await limiter.check_rate_limit("client2")
        
        assert allowed1 is True
        assert allowed2 is True
        
        # Use up client1's tokens
        await limiter.check_rate_limit("client1")
        allowed1, _ = await limiter.check_rate_limit("client1")
        allowed2, _ = await limiter.check_rate_limit("client2")
        
        assert allowed1 is False  # client1 rate limited
        assert allowed2 is True   # client2 still has tokens


class TestSecurityManager:
    """Test security manager functionality."""
    
    @pytest.fixture
    def mock_consent_manager(self):
        """Create mock consent manager."""
        manager = Mock()
        manager.check_consent = AsyncMock(return_value=True)
        manager.request_consent = AsyncMock(return_value="consent-123")
        return manager
    
    @pytest.fixture
    def mock_auditor(self):
        """Create mock security auditor."""
        auditor = Mock()
        auditor.audit_request = AsyncMock()
        auditor.audit_response = AsyncMock()
        auditor.log_security_event = AsyncMock()
        return auditor
    
    @pytest.fixture
    def security_manager(self, mock_consent_manager, mock_auditor):
        """Create security manager instance."""
        return SecurityManager(
            consent_manager=mock_consent_manager,
            security_auditor=mock_auditor
        )
    
    @pytest.mark.asyncio
    async def test_validate_request_success(self, security_manager):
        """Test successful request validation."""
        request = MCPRequest(
            id="test-1",
            method="search",
            params={"query": "test"}
        )
        
        # Should not raise any exceptions
        await security_manager.validate_request(
            request=request,
            client_id="client1",
            auth_context={"authenticated": True}
        )
        
        # Verify audit was called
        security_manager.security_auditor.audit_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, security_manager):
        """Test rate limit enforcement."""
        request = MCPRequest(id="test-1", method="search")
        
        # Exhaust rate limit
        security_manager.policy.rate_limit_burst_size = 1
        security_manager.rate_limiter = RateLimiter(security_manager.policy)
        
        # First request should succeed
        await security_manager.validate_request(
            request=request,
            client_id="client1",
            auth_context={}
        )
        
        # Second request should be rate limited
        with pytest.raises(RateLimitError) as exc_info:
            await security_manager.validate_request(
                request=request,
                client_id="client1",
                auth_context={}
            )
        
        assert exc_info.value.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_threat_detection(self, security_manager):
        """Test threat detection for malicious patterns."""
        # SQL injection attempt
        request = MCPRequest(
            id="test-1",
            method="search",
            params={"query": "'; DROP TABLE users; --"}
        )
        
        with pytest.raises(SecurityError) as exc_info:
            await security_manager.validate_request(
                request=request,
                client_id="client1",
                auth_context={}
            )
        
        assert "THREAT_DETECTED" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_consent_validation(self, security_manager):
        """Test consent validation for sensitive operations."""
        request = MCPRequest(
            id="test-1",
            method="ingest/document",
            params={"content": "test"}
        )
        
        # Mock consent check to return False
        security_manager.consent_manager.check_consent.return_value = False
        
        with pytest.raises(AuthorizationError) as exc_info:
            await security_manager.validate_request(
                request=request,
                client_id="client1",
                auth_context={}
            )
        
        assert "CONSENT_REQUIRED" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_auth_failure_lockout(self, security_manager):
        """Test account lockout after auth failures."""
        security_manager.policy.max_auth_failures = 3
        
        # Record auth failures
        for i in range(3):
            await security_manager.handle_auth_failure(
                client_id="client1",
                reason="Invalid credentials"
            )
        
        # Client should now be locked
        request = MCPRequest(id="test-1", method="search")
        
        with pytest.raises(SecurityError) as exc_info:
            await security_manager.validate_request(
                request=request,
                client_id="client1",
                auth_context={}
            )
        
        assert "ACCOUNT_LOCKED" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_response_size_limiting(self, security_manager):
        """Test response size limiting."""
        security_manager.policy.max_response_size_mb = 0.001  # 1KB
        
        large_response = MCPResponse(
            id="test-1",
            result={
                "results": [{"data": "x" * 1000} for _ in range(100)]
            }
        )
        
        request = MCPRequest(id="test-1", method="search")
        
        modified_response = await security_manager.validate_response(
            response=large_response,
            request=request,
            client_id="client1"
        )
        
        # Response should be truncated
        assert len(modified_response.result["results"]) == 10
        assert modified_response.result.get("truncated") is True
    
    @pytest.mark.asyncio
    async def test_data_masking(self, security_manager):
        """Test sensitive data masking."""
        response = MCPResponse(
            id="test-1",
            result={
                "user": {
                    "name": "John Doe",
                    "password": "secret123",
                    "api_key": "sk-123456"
                }
            }
        )
        
        request = MCPRequest(id="test-1", method="user/get")
        
        masked_response = await security_manager.validate_response(
            response=response,
            request=request,
            client_id="client1"
        )
        
        # Sensitive fields should be masked
        assert masked_response.result["user"]["password"] == "***MASKED***"
        assert masked_response.result["user"]["api_key"] == "***MASKED***"
        assert masked_response.result["user"]["name"] == "John Doe"  # Not masked
    
    @pytest.mark.asyncio
    async def test_security_metrics(self, security_manager):
        """Test security metrics collection."""
        request = MCPRequest(id="test-1", method="search")
        
        # Generate some activity
        await security_manager.validate_request(
            request=request,
            client_id="client1",
            auth_context={}
        )
        
        metrics = await security_manager.get_metrics()
        
        assert metrics["total_requests"] == 1
        assert metrics["blocked_requests"] == 0
        assert metrics["active_clients"] == 1


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    @pytest.fixture
    def security_middleware(self, mock_consent_manager, mock_auditor):
        """Create security middleware instance."""
        manager = SecurityManager(
            consent_manager=mock_consent_manager,
            security_auditor=mock_auditor
        )
        return SecurityMiddleware(manager)
    
    @pytest.mark.asyncio
    async def test_middleware_success(self, security_middleware):
        """Test successful request through middleware."""
        request = MCPRequest(id="test-1", method="search")
        auth_context = {"client_id": "client1"}
        
        # Mock handler
        async def handler(req):
            return MCPResponse(id=req.id, result={"status": "ok"})
        
        response = await security_middleware.process_request(
            request=request,
            auth_context=auth_context,
            handler=handler
        )
        
        assert response.result["status"] == "ok"
        assert response.metadata["security"]["validated"] is True
    
    @pytest.mark.asyncio
    async def test_middleware_rate_limit_error(self, security_middleware):
        """Test middleware handling of rate limit errors."""
        request = MCPRequest(id="test-1", method="search")
        auth_context = {"client_id": "client1"}
        
        # Exhaust rate limit
        security_middleware.security_manager.policy.rate_limit_burst_size = 0
        
        # Mock handler (shouldn't be called)
        handler = AsyncMock()
        
        response = await security_middleware.process_request(
            request=request,
            auth_context=auth_context,
            handler=handler
        )
        
        assert response.error is not None
        assert response.error.code == -32005  # RATE_LIMIT_EXCEEDED
        assert "retry_after" in response.error.data
        handler.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_security_error(self, security_middleware):
        """Test middleware handling of security errors."""
        # SQL injection attempt
        request = MCPRequest(
            id="test-1",
            method="search",
            params={"query": "'; DROP TABLE users; --"}
        )
        auth_context = {"client_id": "client1"}
        
        handler = AsyncMock()
        
        response = await security_middleware.process_request(
            request=request,
            auth_context=auth_context,
            handler=handler
        )
        
        assert response.error is not None
        assert response.error.code == -32003  # FORBIDDEN
        handler.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_bypass_methods(self, security_middleware):
        """Test bypass methods skip security validation."""
        request = MCPRequest(id="test-1", method="initialize")
        auth_context = {}  # No auth context
        
        # Mock handler
        async def handler(req):
            return MCPResponse(id=req.id, result={"initialized": True})
        
        # Should succeed even without auth
        response = await security_middleware.process_request(
            request=request,
            auth_context=auth_context,
            handler=handler
        )
        
        assert response.result["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_wrapped_handler(self, security_middleware):
        """Test wrapped handler functionality."""
        # Original handler
        async def original_handler(request, auth_context):
            return MCPResponse(
                id=request.id,
                result={"client": auth_context.get("client_id")}
            )
        
        # Wrap handler
        wrapped = security_middleware.wrap_handler(original_handler)
        
        request = MCPRequest(id="test-1", method="search")
        auth_context = {"client_id": "client1"}
        
        response = await wrapped(request, auth_context)
        
        assert response.result["client"] == "client1"
        assert response.metadata["security"]["validated"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])