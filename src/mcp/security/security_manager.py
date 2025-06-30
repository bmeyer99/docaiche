"""
Security Manager - Cross-Cutting Security Implementation
========================================================

Centralized security management for MCP server implementing consent,
audit logging, rate limiting, and threat protection.

Provides comprehensive security enforcement across all MCP operations
with configurable policies and real-time threat detection.
"""

import asyncio
import hashlib
import secrets
import time
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import logging

from ..exceptions import SecurityError, AuthorizationError, RateLimitError
from ..schemas import MCPRequest, MCPResponse, ConsentRequest
from ..auth.consent_manager import ConsentManager
from ..auth.security_audit import SecurityAuditor

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Security threat levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(Enum):
    """Security event types for monitoring."""
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    CONSENT_VIOLATION = "consent_violation"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration_attempt"
    INJECTION_ATTEMPT = "injection_attempt"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    
    # Rate limiting
    rate_limit_window: int = 60  # seconds
    rate_limit_max_requests: int = 60
    rate_limit_burst_size: int = 10
    
    # Authentication
    max_auth_failures: int = 5
    auth_failure_lockout_time: int = 300  # seconds
    require_mfa_for_sensitive: bool = True
    
    # Consent
    require_explicit_consent: bool = True
    consent_expiry_days: int = 90
    sensitive_operations: Set[str] = field(default_factory=lambda: {
        "ingest/document",
        "config/update",
        "admin/*"
    })
    
    # Data protection
    max_response_size_mb: int = 10
    max_batch_size: int = 100
    enable_data_masking: bool = True
    
    # Threat detection
    anomaly_detection_enabled: bool = True
    threat_score_threshold: float = 0.7
    block_on_high_threat: bool = True


@dataclass
class ClientSecurityProfile:
    """Security profile for a client."""
    
    client_id: str
    last_auth_failure: Optional[datetime] = None
    auth_failure_count: int = 0
    is_locked: bool = False
    lock_expires: Optional[datetime] = None
    
    # Rate limiting
    request_timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    rate_limit_violations: int = 0
    
    # Threat scoring
    threat_score: float = 0.0
    threat_events: List[Tuple[datetime, SecurityEvent, str]] = field(default_factory=list)
    
    # Consent tracking
    active_consents: Dict[str, datetime] = field(default_factory=dict)
    consent_violations: int = 0


class RateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, policy: SecurityPolicy):
        self.policy = policy
        self.buckets: Dict[str, float] = {}
        self.last_update: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, client_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits.
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        async with self._lock:
            now = time.time()
            
            # Initialize bucket if needed
            if client_id not in self.buckets:
                self.buckets[client_id] = float(self.policy.rate_limit_burst_size)
                self.last_update[client_id] = now
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_update[client_id]
            refill_rate = self.policy.rate_limit_max_requests / self.policy.rate_limit_window
            tokens_to_add = elapsed * refill_rate
            
            self.buckets[client_id] = min(
                self.buckets[client_id] + tokens_to_add,
                float(self.policy.rate_limit_burst_size)
            )
            self.last_update[client_id] = now
            
            # Check if we have tokens available
            if self.buckets[client_id] >= 1.0:
                self.buckets[client_id] -= 1.0
                return True, None
            else:
                # Calculate retry after
                tokens_needed = 1.0 - self.buckets[client_id]
                retry_after = int(tokens_needed / refill_rate) + 1
                return False, retry_after


class ThreatDetector:
    """Real-time threat detection and scoring."""
    
    def __init__(self):
        self.patterns = {
            # SQL injection patterns
            r"(\b(union|select|insert|update|delete|drop)\b.*\b(from|where|table)\b)": (SecurityEvent.INJECTION_ATTEMPT, 0.8),
            # Path traversal
            r"(\.\.\/|\.\.\\|%2e%2e%2f|%252e%252e%252f)": (SecurityEvent.INJECTION_ATTEMPT, 0.7),
            # Script injection
            r"(<script|javascript:|onerror=|onload=)": (SecurityEvent.INJECTION_ATTEMPT, 0.8),
            # Command injection
            r"(;|\||&&|`|\$\(|\${).*\b(rm|cat|ls|wget|curl)\b": (SecurityEvent.INJECTION_ATTEMPT, 0.9),
            # Data exfiltration patterns
            r"(limit|offset|skip|take)\s*=\s*([0-9]{4,}|all|\*)": (SecurityEvent.DATA_EXFILTRATION_ATTEMPT, 0.6),
        }
        
        # Behavioral analysis thresholds
        self.behavior_thresholds = {
            "requests_per_minute": 100,
            "unique_resources_per_minute": 50,
            "failed_auth_per_hour": 10,
            "data_volume_mb_per_hour": 100
        }
    
    async def analyze_request(
        self,
        request: MCPRequest,
        profile: ClientSecurityProfile
    ) -> Tuple[float, List[SecurityEvent]]:
        """
        Analyze request for threats and return threat score.
        
        Returns:
            Tuple of (threat_score, detected_events)
        """
        threat_score = 0.0
        detected_events = []
        
        # Check request content for patterns
        request_str = json.dumps(request.dict())
        
        import re
        for pattern, (event_type, score) in self.patterns.items():
            if re.search(pattern, request_str, re.IGNORECASE):
                threat_score += score
                detected_events.append(event_type)
                logger.warning(
                    f"Threat pattern detected: {event_type.value}",
                    extra={
                        "client_id": profile.client_id,
                        "event_type": event_type.value,
                        "score": score
                        # Do not log the actual pattern to avoid exposing detection logic
                    }
                )
        
        # Behavioral analysis
        if await self._check_anomalous_behavior(profile):
            threat_score += 0.5
            detected_events.append(SecurityEvent.ANOMALOUS_BEHAVIOR)
        
        # Normalize score
        threat_score = min(threat_score, 1.0)
        
        return threat_score, detected_events
    
    async def _check_anomalous_behavior(self, profile: ClientSecurityProfile) -> bool:
        """Check for anomalous behavior patterns."""
        now = datetime.utcnow()
        
        # Check request rate
        recent_requests = [
            ts for ts in profile.request_timestamps
            if (now - datetime.fromtimestamp(ts)).seconds < 60
        ]
        if len(recent_requests) > self.behavior_thresholds["requests_per_minute"]:
            return True
        
        # Check authentication failures
        recent_auth_failures = sum(
            1 for ts, event, _ in profile.threat_events
            if event == SecurityEvent.AUTH_FAILURE and (now - ts).seconds < 3600
        )
        if recent_auth_failures > self.behavior_thresholds["failed_auth_per_hour"]:
            return True
        
        return False


class SecurityManager:
    """
    Centralized security management for MCP server.
    
    Implements cross-cutting security concerns including:
    - Consent management and enforcement
    - Audit logging and compliance
    - Rate limiting and DDoS protection
    - Threat detection and mitigation
    - Data protection and masking
    """
    
    def __init__(
        self,
        consent_manager: ConsentManager,
        security_auditor: SecurityAuditor,
        policy: Optional[SecurityPolicy] = None
    ):
        self.consent_manager = consent_manager
        self.security_auditor = security_auditor
        self.policy = policy or SecurityPolicy()
        
        # Components
        self.rate_limiter = RateLimiter(self.policy)
        self.threat_detector = ThreatDetector()
        
        # Client profiles
        self.client_profiles: Dict[str, ClientSecurityProfile] = {}
        self._profile_lock = asyncio.Lock()
        
        # Security metrics
        self.metrics = {
            "total_requests": 0,
            "blocked_requests": 0,
            "rate_limit_hits": 0,
            "threat_detections": 0,
            "consent_violations": 0
        }
        
        logger.info("Security manager initialized", extra={"policy": self.policy})
    
    async def validate_request(
        self,
        request: MCPRequest,
        client_id: str,
        auth_context: Dict[str, Any]
    ) -> None:
        """
        Validate request against all security policies.
        
        Raises:
            SecurityError: If any security validation fails
            RateLimitError: If rate limit exceeded
            AuthorizationError: If authorization fails
        """
        # Get or create client profile
        profile = await self._get_client_profile(client_id)
        
        # Update request tracking
        profile.request_timestamps.append(time.time())
        self.metrics["total_requests"] += 1
        
        # 1. Check if client is locked
        if await self._is_client_locked(profile):
            self.metrics["blocked_requests"] += 1
            raise SecurityError(
                message="Client account is temporarily locked",
                error_code="ACCOUNT_LOCKED",
                details={"lock_expires": profile.lock_expires.isoformat() if profile.lock_expires else None}
            )
        
        # 2. Rate limiting
        allowed, retry_after = await self.rate_limiter.check_rate_limit(client_id)
        if not allowed:
            profile.rate_limit_violations += 1
            self.metrics["rate_limit_hits"] += 1
            
            # Log rate limit event
            await self._record_threat_event(
                profile,
                SecurityEvent.RATE_LIMIT_EXCEEDED,
                f"Rate limit exceeded for {request.method}"
            )
            
            raise RateLimitError(
                message="Rate limit exceeded",
                retry_after=retry_after
            )
        
        # 3. Threat detection
        threat_score, detected_events = await self.threat_detector.analyze_request(
            request, profile
        )
        
        if detected_events:
            self.metrics["threat_detections"] += 1
            for event in detected_events:
                await self._record_threat_event(
                    profile,
                    event,
                    f"Detected in request to {request.method}"
                )
        
        # Update profile threat score
        profile.threat_score = (profile.threat_score * 0.8) + (threat_score * 0.2)
        
        if self.policy.block_on_high_threat and threat_score >= self.policy.threat_score_threshold:
            self.metrics["blocked_requests"] += 1
            
            # Audit high threat detection
            await self.security_auditor.log_security_event(
                event_type="threat_blocked",
                severity="high",
                client_id=client_id,
                details={
                    "threat_score": threat_score,
                    "detected_events": [e.value for e in detected_events],
                    "request_method": request.method
                }
            )
            
            raise SecurityError(
                message="Request blocked due to security threat",
                error_code="THREAT_DETECTED",
                details={"threat_level": ThreatLevel.HIGH.value}
            )
        
        # 4. Consent validation for sensitive operations
        if await self._requires_consent(request.method):
            if not await self._validate_consent(profile, request, auth_context):
                self.metrics["consent_violations"] += 1
                
                await self._record_threat_event(
                    profile,
                    SecurityEvent.CONSENT_VIOLATION,
                    f"Missing consent for {request.method}"
                )
                
                raise AuthorizationError(
                    message="Explicit consent required for this operation",
                    error_code="CONSENT_REQUIRED",
                    details={"operation": request.method}
                )
        
        # 5. Audit successful validation
        await self.security_auditor.audit_request(
            request=request,
            client_id=client_id,
            auth_context=auth_context,
            threat_score=threat_score
        )
    
    async def validate_response(
        self,
        response: MCPResponse,
        request: MCPRequest,
        client_id: str
    ) -> MCPResponse:
        """
        Validate and potentially modify response for security.
        
        Returns:
            Potentially modified response
        """
        # Check response size
        response_size = len(json.dumps(response.dict()))
        if response_size > self.policy.max_response_size_mb * 1024 * 1024:
            logger.warning(
                "Response size exceeds limit",
                extra={
                    "client_id": client_id,
                    "size_mb": response_size / 1024 / 1024,
                    "limit_mb": self.policy.max_response_size_mb
                }
            )
            
            # Truncate response
            if hasattr(response.result, 'results') and isinstance(response.result['results'], list):
                response.result['results'] = response.result['results'][:10]
                response.result['truncated'] = True
                response.result['truncation_reason'] = "Response size limit exceeded"
        
        # Data masking if enabled
        if self.policy.enable_data_masking:
            response = await self._apply_data_masking(response, client_id)
        
        # Audit response
        await self.security_auditor.audit_response(
            response=response,
            request=request,
            client_id=client_id
        )
        
        return response
    
    async def handle_auth_failure(self, client_id: str, reason: str) -> None:
        """Handle authentication failure."""
        profile = await self._get_client_profile(client_id)
        
        profile.auth_failure_count += 1
        profile.last_auth_failure = datetime.utcnow()
        
        await self._record_threat_event(
            profile,
            SecurityEvent.AUTH_FAILURE,
            reason
        )
        
        # Check if we should lock the account
        if profile.auth_failure_count >= self.policy.max_auth_failures:
            profile.is_locked = True
            profile.lock_expires = datetime.utcnow() + timedelta(
                seconds=self.policy.auth_failure_lockout_time
            )
            
            await self.security_auditor.log_security_event(
                event_type="account_locked",
                severity="high",
                client_id=client_id,
                details={
                    "failure_count": profile.auth_failure_count,
                    "lock_duration_seconds": self.policy.auth_failure_lockout_time
                }
            )
    
    async def handle_auth_success(self, client_id: str) -> None:
        """Handle successful authentication."""
        profile = await self._get_client_profile(client_id)
        
        # Reset failure count
        profile.auth_failure_count = 0
        profile.last_auth_failure = None
        
        # Decay threat score on successful auth
        profile.threat_score *= 0.9
    
    async def grant_consent(
        self,
        client_id: str,
        operation: str,
        duration_hours: Optional[int] = None
    ) -> str:
        """Grant consent for an operation."""
        profile = await self._get_client_profile(client_id)
        
        # Create consent record
        consent_id = await self.consent_manager.request_consent(
            ConsentRequest(
                client_id=client_id,
                operation=operation,
                resource_uri=operation,
                purpose=f"Access to {operation}",
                duration_hours=duration_hours or (self.policy.consent_expiry_days * 24)
            )
        )
        
        # Track in profile
        profile.active_consents[operation] = datetime.utcnow() + timedelta(
            hours=duration_hours or (self.policy.consent_expiry_days * 24)
        )
        
        return consent_id
    
    async def revoke_consent(self, client_id: str, operation: str) -> None:
        """Revoke consent for an operation."""
        profile = await self._get_client_profile(client_id)
        
        if operation in profile.active_consents:
            del profile.active_consents[operation]
        
        # Also revoke in consent manager
        # This would need consent ID tracking for full implementation
    
    async def get_security_status(self, client_id: str) -> Dict[str, Any]:
        """Get security status for a client."""
        profile = await self._get_client_profile(client_id)
        
        return {
            "client_id": client_id,
            "is_locked": profile.is_locked,
            "lock_expires": profile.lock_expires.isoformat() if profile.lock_expires else None,
            "threat_score": round(profile.threat_score, 3),
            "rate_limit_violations": profile.rate_limit_violations,
            "consent_violations": profile.consent_violations,
            "active_consents": list(profile.active_consents.keys()),
            "recent_threats": [
                {
                    "timestamp": ts.isoformat(),
                    "event": event.value,
                    "description": desc
                }
                for ts, event, desc in profile.threat_events[-10:]
            ]
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get security metrics."""
        return {
            **self.metrics,
            "active_clients": len(self.client_profiles),
            "locked_clients": sum(
                1 for p in self.client_profiles.values() if p.is_locked
            ),
            "high_threat_clients": sum(
                1 for p in self.client_profiles.values()
                if p.threat_score >= self.policy.threat_score_threshold
            )
        }
    
    # Private methods
    
    async def _get_client_profile(self, client_id: str) -> ClientSecurityProfile:
        """Get or create client security profile."""
        async with self._profile_lock:
            if client_id not in self.client_profiles:
                self.client_profiles[client_id] = ClientSecurityProfile(
                    client_id=client_id
                )
            return self.client_profiles[client_id]
    
    async def _is_client_locked(self, profile: ClientSecurityProfile) -> bool:
        """Check if client is currently locked."""
        if not profile.is_locked:
            return False
        
        # Check if lock has expired
        if profile.lock_expires and datetime.utcnow() > profile.lock_expires:
            profile.is_locked = False
            profile.lock_expires = None
            return False
        
        return True
    
    async def _requires_consent(self, operation: str) -> bool:
        """Check if operation requires explicit consent."""
        if not self.policy.require_explicit_consent:
            return False
        
        # Check against sensitive operations
        for pattern in self.policy.sensitive_operations:
            if pattern.endswith("*"):
                if operation.startswith(pattern[:-1]):
                    return True
            elif operation == pattern:
                return True
        
        return False
    
    async def _validate_consent(
        self,
        profile: ClientSecurityProfile,
        request: MCPRequest,
        auth_context: Dict[str, Any]
    ) -> bool:
        """Validate consent for operation."""
        operation = request.method
        
        # Check profile cache first
        if operation in profile.active_consents:
            if datetime.utcnow() < profile.active_consents[operation]:
                return True
            else:
                # Expired consent
                del profile.active_consents[operation]
        
        # Check with consent manager
        has_consent = await self.consent_manager.check_consent(
            client_id=profile.client_id,
            operation=operation,
            resource_uri=operation
        )
        
        if has_consent:
            # Cache the consent
            profile.active_consents[operation] = datetime.utcnow() + timedelta(
                days=self.policy.consent_expiry_days
            )
        
        return has_consent
    
    async def _record_threat_event(
        self,
        profile: ClientSecurityProfile,
        event: SecurityEvent,
        description: str
    ) -> None:
        """Record a security threat event."""
        profile.threat_events.append((
            datetime.utcnow(),
            event,
            description
        ))
        
        # Keep only recent events
        if len(profile.threat_events) > 100:
            profile.threat_events = profile.threat_events[-50:]
    
    async def _apply_data_masking(
        self,
        response: MCPResponse,
        client_id: str
    ) -> MCPResponse:
        """Apply data masking to response."""
        # This is a simplified implementation
        # In production, would use more sophisticated masking rules
        
        if not response.result:
            return response
        
        # Example: mask sensitive fields
        sensitive_patterns = ["password", "secret", "token", "key", "credential"]
        
        def mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
            masked = {}
            for key, value in data.items():
                if any(pattern in key.lower() for pattern in sensitive_patterns):
                    masked[key] = "***MASKED***"
                elif isinstance(value, dict):
                    masked[key] = mask_dict(value)
                elif isinstance(value, list):
                    masked[key] = [
                        mask_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    masked[key] = value
            return masked
        
        if isinstance(response.result, dict):
            response.result = mask_dict(response.result)
        
        return response