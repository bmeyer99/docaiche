"""
Unit tests for SecurityManager
==============================

Tests for centralized security enforcement including rate limiting,
threat detection, and consent management.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock

from src.mcp.security.security_manager import (
    SecurityManager,
    SecurityPolicy,
    RateLimiter,
    ThreatDetector,
    ClientSecurityProfile,
    SecurityViolation
)
from src.mcp.security.consent_manager import ConsentManager
from src.mcp.security.audit_logger import AuditLogger
from src.mcp.schemas import MCPRequest


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        policy = SecurityPolicy(
            max_requests_per_minute=10,
            max_requests_per_hour=100
        )
        return RateLimiter(policy)
    
    @pytest.mark.asyncio
    async def test_allow_within_limits(self, rate_limiter):
        """Test that requests within limits are allowed."""
        client_id = "test_client"
        
        # First 10 requests should be allowed
        for i in range(10):
            allowed = await rate_limiter.check_rate_limit(client_id)
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_block_exceeding_minute_limit(self, rate_limiter):
        """Test that requests exceeding minute limit are blocked."""
        client_id = "test_client"
        
        # Make 10 allowed requests
        for i in range(10):
            await rate_limiter.check_rate_limit(client_id)
        
        # 11th request should be blocked
        allowed = await rate_limiter.check_rate_limit(client_id)
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_reset_after_time_window(self, rate_limiter):
        """Test that rate limits reset after time window."""
        client_id = "test_client"
        
        # Make 10 requests
        for i in range(10):
            await rate_limiter.check_rate_limit(client_id)
        
        # Should be blocked
        assert await rate_limiter.check_rate_limit(client_id) is False
        
        # Simulate time passing (would need to mock time in real implementation)
        # For now, just clear the bucket
        rate_limiter.minute_buckets.clear()
        
        # Should be allowed again
        assert await rate_limiter.check_rate_limit(client_id) is True
    
    @pytest.mark.asyncio
    async def test_independent_client_limits(self, rate_limiter):
        """Test that different clients have independent rate limits."""
        client1 = "client1"
        client2 = "client2"
        
        # Max out client1
        for i in range(10):
            await rate_limiter.check_rate_limit(client1)
        
        # Client1 should be blocked
        assert await rate_limiter.check_rate_limit(client1) is False
        
        # Client2 should still be allowed
        assert await rate_limiter.check_rate_limit(client2) is True


class TestThreatDetector:
    """Test threat detection functionality."""
    
    @pytest.fixture
    def threat_detector(self):
        return ThreatDetector()
    
    @pytest.mark.asyncio
    async def test_detect_injection_attempt(self, threat_detector):
        """Test detection of injection attempts."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={
                "query": "SELECT * FROM users WHERE id = 1; DROP TABLE users;--"
            }
        )
        
        threats = await threat_detector.analyze_request(request)
        assert len(threats) > 0
        assert any("injection" in t.lower() for t in threats)
    
    @pytest.mark.asyncio
    async def test_detect_path_traversal(self, threat_detector):
        """Test detection of path traversal attempts."""
        request = MCPRequest(
            id="test",
            method="resource/read",
            params={
                "path": "../../etc/passwd"
            }
        )
        
        threats = await threat_detector.analyze_request(request)
        assert len(threats) > 0
        assert any("traversal" in t.lower() for t in threats)
    
    @pytest.mark.asyncio
    async def test_detect_oversized_payload(self, threat_detector):
        """Test detection of oversized payloads."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={
                "data": "x" * 10_000_000  # 10MB string
            }
        )
        
        threats = await threat_detector.analyze_request(request)
        assert len(threats) > 0
        assert any("size" in t.lower() for t in threats)
    
    @pytest.mark.asyncio
    async def test_no_threats_in_safe_request(self, threat_detector):
        """Test that safe requests don't trigger threats."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={
                "query": "artificial intelligence documentation"
            }
        )
        
        threats = await threat_detector.analyze_request(request)
        assert len(threats) == 0
    
    @pytest.mark.asyncio
    async def test_update_client_profile(self, threat_detector):
        """Test client profile updates based on behavior."""
        client_id = "test_client"
        
        # Simulate suspicious behavior
        for i in range(5):
            request = MCPRequest(
                id=f"test{i}",
                method="tool/execute",
                params={"query": f"../../../etc/passwd{i}"}
            )
            await threat_detector.analyze_request(request)
            threat_detector.update_client_profile(client_id, ["path_traversal"])
        
        # Check that client is marked as suspicious
        profile = threat_detector.client_profiles.get(client_id)
        assert profile is not None
        assert profile.threat_score > 0
        assert profile.violation_count > 0


class TestSecurityManager:
    """Test SecurityManager integration."""
    
    @pytest.fixture
    def mock_consent_manager(self):
        manager = Mock(spec=ConsentManager)
        manager.check_consent = AsyncMock(return_value=True)
        manager.record_consent = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_audit_logger(self):
        logger = Mock(spec=AuditLogger)
        logger.log_security_event = AsyncMock()
        return logger
    
    @pytest.fixture
    def security_manager(self, mock_consent_manager, mock_audit_logger):
        policy = SecurityPolicy(
            max_requests_per_minute=10,
            max_requests_per_hour=100,
            enable_threat_detection=True
        )
        return SecurityManager(
            consent_manager=mock_consent_manager,
            security_auditor=mock_audit_logger,
            policy=policy
        )
    
    @pytest.mark.asyncio
    async def test_enforce_security_allows_valid_request(self, security_manager):
        """Test that valid requests pass security enforcement."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"query": "machine learning"}
        )
        
        result = await security_manager.enforce_security(
            client_id="test_client",
            request=request
        )
        
        assert result.allowed is True
        assert result.reason is None
        assert len(result.violations) == 0
    
    @pytest.mark.asyncio
    async def test_enforce_security_blocks_threats(self, security_manager):
        """Test that threatening requests are blocked."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={
                "query": "'; DROP TABLE users; --"
            }
        )
        
        result = await security_manager.enforce_security(
            client_id="test_client",
            request=request
        )
        
        assert result.allowed is False
        assert result.reason is not None
        assert len(result.violations) > 0
    
    @pytest.mark.asyncio
    async def test_enforce_security_rate_limits(self, security_manager):
        """Test that rate limiting is enforced."""
        client_id = "test_client"
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"query": "test"}
        )
        
        # Make requests up to the limit
        for i in range(10):
            result = await security_manager.enforce_security(
                client_id=client_id,
                request=request
            )
            assert result.allowed is True
        
        # Next request should be rate limited
        result = await security_manager.enforce_security(
            client_id=client_id,
            request=request
        )
        assert result.allowed is False
        assert "rate limit" in result.reason.lower()
    
    @pytest.mark.asyncio
    async def test_enforce_security_checks_consent(self, security_manager, mock_consent_manager):
        """Test that consent is checked for operations."""
        mock_consent_manager.check_consent.return_value = False
        
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"operation": "ingest"}
        )
        
        result = await security_manager.enforce_security(
            client_id="test_client",
            request=request
        )
        
        assert result.allowed is False
        assert "consent" in result.reason.lower()
        mock_consent_manager.check_consent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enforce_security_logs_violations(self, security_manager, mock_audit_logger):
        """Test that security violations are logged."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={
                "query": "../../../etc/passwd"
            }
        )
        
        await security_manager.enforce_security(
            client_id="test_client",
            request=request
        )
        
        mock_audit_logger.log_security_event.assert_called()
        call_args = mock_audit_logger.log_security_event.call_args[1]
        assert call_args["event_type"] == "security_violation"
        assert call_args["severity"] == "high"
    
    @pytest.mark.asyncio
    async def test_get_client_security_status(self, security_manager):
        """Test retrieving client security status."""
        client_id = "test_client"
        
        # Make some requests
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"query": "test"}
        )
        
        for i in range(5):
            await security_manager.enforce_security(
                client_id=client_id,
                request=request
            )
        
        # Get status
        status = await security_manager.get_client_security_status(client_id)
        
        assert status["client_id"] == client_id
        assert status["requests_this_minute"] == 5
        assert status["threat_score"] >= 0
        assert status["is_blocked"] is False
    
    @pytest.mark.asyncio
    async def test_block_and_unblock_client(self, security_manager):
        """Test manual client blocking and unblocking."""
        client_id = "test_client"
        
        # Block client
        await security_manager.block_client(
            client_id=client_id,
            reason="Manual block for testing",
            duration_minutes=60
        )
        
        # Verify client is blocked
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"query": "test"}
        )
        
        result = await security_manager.enforce_security(
            client_id=client_id,
            request=request
        )
        assert result.allowed is False
        assert "blocked" in result.reason.lower()
        
        # Unblock client
        await security_manager.unblock_client(client_id)
        
        # Verify client is unblocked
        result = await security_manager.enforce_security(
            client_id=client_id,
            request=request
        )
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_reset_client_profile(self, security_manager):
        """Test resetting client security profile."""
        client_id = "test_client"
        
        # Create some history
        for i in range(5):
            request = MCPRequest(
                id=f"test{i}",
                method="tool/execute",
                params={"query": "test"}
            )
            await security_manager.enforce_security(
                client_id=client_id,
                request=request
            )
        
        # Reset profile
        await security_manager.reset_client_profile(client_id)
        
        # Get status - should be clean
        status = await security_manager.get_client_security_status(client_id)
        assert status["requests_this_minute"] == 0
        assert status["threat_score"] == 0


# Test fixtures for integration tests
@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for security manager."""
    consent_manager = Mock(spec=ConsentManager)
    consent_manager.check_consent = AsyncMock(return_value=True)
    consent_manager.record_consent = AsyncMock()
    
    audit_logger = Mock(spec=AuditLogger)
    audit_logger.log_security_event = AsyncMock()
    
    return {
        "consent_manager": consent_manager,
        "audit_logger": audit_logger
    }


@pytest.mark.asyncio
async def test_security_manager_initialization(mock_dependencies):
    """Test SecurityManager initialization with various configurations."""
    # Test with default policy
    manager = SecurityManager(
        consent_manager=mock_dependencies["consent_manager"],
        security_auditor=mock_dependencies["audit_logger"]
    )
    assert manager.policy.max_requests_per_minute == 60
    
    # Test with custom policy
    custom_policy = SecurityPolicy(
        max_requests_per_minute=30,
        max_requests_per_hour=300,
        enable_threat_detection=False
    )
    manager = SecurityManager(
        consent_manager=mock_dependencies["consent_manager"],
        security_auditor=mock_dependencies["audit_logger"],
        policy=custom_policy
    )
    assert manager.policy.max_requests_per_minute == 30
    assert manager.policy.enable_threat_detection is False