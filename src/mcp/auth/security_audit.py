"""
Security Audit and Monitoring System
====================================

Comprehensive security audit logging and monitoring for MCP operations
following security best practices and compliance requirements.

Key Features:
- Security event logging and correlation
- Authentication and authorization audit trails
- Threat detection and anomaly monitoring
- Compliance reporting and data retention
- Real-time security alerting and notifications

Implements defense-in-depth security monitoring with proper event
correlation and forensic capabilities for production environments.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from ..config import MCPSecurityConfig

# Configure security audit logger separately from application logger
security_logger = logging.getLogger("mcp.security.audit")


class SecurityEventType(str, Enum):
    """Security event type enumeration."""
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_SUCCESS = "auth_grant"
    AUTHORIZATION_FAILURE = "auth_deny"
    TOKEN_VALIDATION_SUCCESS = "token_valid"
    TOKEN_VALIDATION_FAILURE = "token_invalid"
    CONSENT_GRANTED = "consent_grant"
    CONSENT_DENIED = "consent_deny"
    CONSENT_REVOKED = "consent_revoke"
    RESOURCE_ACCESS = "resource_access"
    TOOL_EXECUTION = "tool_exec"
    SUSPICIOUS_ACTIVITY = "suspicious"
    SECURITY_VIOLATION = "violation"
    RATE_LIMIT_EXCEEDED = "rate_limit"
    CONFIGURATION_CHANGE = "config_change"


class SecuritySeverity(str, Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """
    Individual security event with comprehensive metadata.
    
    Captures security-relevant events with proper context for
    audit trails, compliance reporting, and threat detection.
    """
    
    event_id: str
    event_type: SecurityEventType
    severity: SecuritySeverity
    timestamp: datetime
    
    # Event details
    description: str
    success: bool
    
    # Client and session information
    client_id: Optional[str]
    client_ip: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    correlation_id: Optional[str]
    
    # Authentication context
    auth_method: Optional[str]
    token_type: Optional[str]
    granted_scopes: Optional[List[str]]
    
    # Resource and operation context
    resource: Optional[str]
    operation: Optional[str]
    tool_name: Optional[str]
    
    # Additional metadata
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security event to dictionary for logging."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class SecurityAuditor:
    """
    Comprehensive security audit and monitoring system.
    
    Implements security event logging, correlation, and monitoring
    with proper audit trails and compliance support.
    """
    
    def __init__(self, security_config: MCPSecurityConfig):
        """
        Initialize security auditor with configuration.
        
        Args:
            security_config: Security configuration settings
        """
        self.security_config = security_config
        
        # Security event storage (in-memory for this implementation)
        # TODO: IMPLEMENTATION ENGINEER - Replace with persistent storage
        self._security_events: List[SecurityEvent] = []
        self._client_activity: Dict[str, List[SecurityEvent]] = {}
        
        # Threat detection state
        self._failed_auth_attempts: Dict[str, List[datetime]] = {}
        self._suspicious_clients: Set[str] = set()
        
        # Configuration
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.event_retention_days = security_config.audit_retention_days
        
        security_logger.info(
            "Security auditor initialized",
            extra={
                "audit_enabled": security_config.audit_enabled,
                "backend": security_config.audit_backend,
                "retention_days": self.event_retention_days
            }
        )
    
    def log_authentication_event(
        self,
        success: bool,
        client_id: Optional[str] = None,
        auth_method: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Log authentication event for audit and monitoring.
        
        Args:
            success: Whether authentication succeeded
            client_id: OAuth client ID
            auth_method: Authentication method used
            client_ip: Client IP address
            user_agent: Client user agent
            error_details: Additional error information
            correlation_id: Request correlation ID
            
        Returns:
            Event ID for tracking
        """
        event_type = (SecurityEventType.AUTHENTICATION_SUCCESS 
                     if success else SecurityEventType.AUTHENTICATION_FAILURE)
        
        severity = SecuritySeverity.LOW if success else SecuritySeverity.MEDIUM
        
        # Escalate severity for repeated failures
        if not success and client_ip:
            recent_failures = self._count_recent_failures(client_ip)
            if recent_failures >= 3:
                severity = SecuritySeverity.HIGH
            if recent_failures >= self.max_failed_attempts:
                severity = SecuritySeverity.CRITICAL
        
        event = self._create_security_event(
            event_type=event_type,
            severity=severity,
            description=f"Authentication {'succeeded' if success else 'failed'} for client",
            success=success,
            client_id=client_id,
            client_ip=client_ip,
            user_agent=user_agent,
            correlation_id=correlation_id,
            auth_method=auth_method,
            metadata=error_details or {}
        )
        
        self._store_security_event(event)
        
        # Track failed authentication attempts for threat detection
        if not success and client_ip:
            self._track_failed_authentication(client_ip)
        
        return event.event_id
    
    def log_authorization_event(
        self,
        success: bool,
        client_id: str,
        resource: str,
        operation: Optional[str] = None,
        granted_scopes: Optional[List[str]] = None,
        client_ip: Optional[str] = None,
        correlation_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log authorization event for access control audit.
        
        Args:
            success: Whether authorization succeeded
            client_id: OAuth client ID
            resource: Requested resource
            operation: Specific operation requested
            granted_scopes: OAuth scopes granted
            client_ip: Client IP address
            correlation_id: Request correlation ID
            error_details: Additional error information
            
        Returns:
            Event ID for tracking
        """
        event_type = (SecurityEventType.AUTHORIZATION_SUCCESS 
                     if success else SecurityEventType.AUTHORIZATION_FAILURE)
        
        severity = SecuritySeverity.LOW if success else SecuritySeverity.MEDIUM
        
        # Escalate for sensitive resources
        if resource and ("admin" in resource or "confidential" in resource):
            severity = SecuritySeverity.HIGH if success else SecuritySeverity.CRITICAL
        
        event = self._create_security_event(
            event_type=event_type,
            severity=severity,
            description=f"Authorization {'granted' if success else 'denied'} for resource access",
            success=success,
            client_id=client_id,
            client_ip=client_ip,
            resource=resource,
            operation=operation,
            granted_scopes=granted_scopes,
            correlation_id=correlation_id,
            metadata=error_details or {}
        )
        
        self._store_security_event(event)
        return event.event_id
    
    def log_consent_event(
        self,
        consent_action: str,
        consent_id: str,
        client_id: str,
        operation: str,
        permissions: List[str],
        client_ip: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Log consent management event for compliance audit.
        
        Args:
            consent_action: Action taken (granted, denied, revoked)
            consent_id: Consent identifier
            client_id: OAuth client ID
            operation: Operation requiring consent
            permissions: Permissions involved
            client_ip: Client IP address
            correlation_id: Request correlation ID
            
        Returns:
            Event ID for tracking
        """
        event_type_map = {
            "granted": SecurityEventType.CONSENT_GRANTED,
            "denied": SecurityEventType.CONSENT_DENIED,
            "revoked": SecurityEventType.CONSENT_REVOKED
        }
        
        event_type = event_type_map.get(consent_action, SecurityEventType.CONSENT_GRANTED)
        severity = SecuritySeverity.MEDIUM  # Consent events are important for compliance
        
        event = self._create_security_event(
            event_type=event_type,
            severity=severity,
            description=f"User consent {consent_action} for operation",
            success=consent_action == "granted",
            client_id=client_id,
            client_ip=client_ip,
            operation=operation,
            correlation_id=correlation_id,
            metadata={
                "consent_id": consent_id,
                "permissions": permissions
            }
        )
        
        self._store_security_event(event)
        return event.event_id
    
    def log_tool_execution(
        self,
        tool_name: str,
        success: bool,
        client_id: str,
        execution_time_ms: int,
        client_ip: Optional[str] = None,
        correlation_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log MCP tool execution for operational audit.
        
        Args:
            tool_name: Name of executed tool
            success: Whether execution succeeded
            client_id: OAuth client ID
            execution_time_ms: Execution time in milliseconds
            client_ip: Client IP address
            correlation_id: Request correlation ID
            error_details: Additional error information
            
        Returns:
            Event ID for tracking
        """
        severity = SecuritySeverity.LOW
        
        # Escalate for sensitive tools or failures
        if not success:
            severity = SecuritySeverity.MEDIUM
        if tool_name in ["ingest", "admin"]:
            severity = SecuritySeverity.MEDIUM if success else SecuritySeverity.HIGH
        
        event = self._create_security_event(
            event_type=SecurityEventType.TOOL_EXECUTION,
            severity=severity,
            description=f"Tool execution {'succeeded' if success else 'failed'}",
            success=success,
            client_id=client_id,
            client_ip=client_ip,
            tool_name=tool_name,
            correlation_id=correlation_id,
            metadata={
                "execution_time_ms": execution_time_ms,
                **(error_details or {})
            }
        )
        
        self._store_security_event(event)
        return event.event_id
    
    def log_security_violation(
        self,
        violation_type: str,
        description: str,
        client_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        severity: SecuritySeverity = SecuritySeverity.HIGH,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Log security violation for immediate attention.
        
        Args:
            violation_type: Type of security violation
            description: Detailed description
            client_id: OAuth client ID if applicable
            client_ip: Client IP address
            severity: Violation severity level
            metadata: Additional violation metadata
            correlation_id: Request correlation ID
            
        Returns:
            Event ID for tracking
        """
        event = self._create_security_event(
            event_type=SecurityEventType.SECURITY_VIOLATION,
            severity=severity,
            description=description,
            success=False,
            client_id=client_id,
            client_ip=client_ip,
            correlation_id=correlation_id,
            metadata={
                "violation_type": violation_type,
                **(metadata or {})
            }
        )
        
        self._store_security_event(event)
        
        # Mark client as suspicious for enhanced monitoring
        if client_id:
            self._suspicious_clients.add(client_id)
        
        # Log to application logger for immediate visibility
        security_logger.error(
            f"Security violation detected: {violation_type}",
            extra={
                "event_id": event.event_id,
                "client_id": client_id,
                "client_ip": client_ip,
                "severity": severity.value
            }
        )
        
        return event.event_id
    
    def is_client_locked_out(self, client_ip: str) -> bool:
        """
        Check if client IP is locked out due to failed authentication attempts.
        
        Args:
            client_ip: Client IP address to check
            
        Returns:
            True if client is currently locked out
        """
        if client_ip not in self._failed_auth_attempts:
            return False
        
        failed_attempts = self._failed_auth_attempts[client_ip]
        if len(failed_attempts) < self.max_failed_attempts:
            return False
        
        # Check if lockout period has expired
        latest_attempt = max(failed_attempts)
        lockout_expires = latest_attempt + self.lockout_duration
        
        if datetime.utcnow() > lockout_expires:
            # Lockout expired, clear failed attempts
            del self._failed_auth_attempts[client_ip]
            return False
        
        return True
    
    def get_security_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        client_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """
        Retrieve security events for analysis and reporting.
        
        Args:
            event_type: Filter by event type
            client_id: Filter by client ID
            since: Filter events since timestamp
            limit: Maximum number of events to return
            
        Returns:
            List of matching security events
        """
        events = self._security_events.copy()
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if client_id:
            events = [e for e in events if e.client_id == client_id]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Sort by timestamp (newest first) and apply limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def generate_security_report(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive security report for compliance.
        
        Args:
            since: Report start timestamp
            
        Returns:
            Security report with event summaries and statistics
        """
        if not since:
            since = datetime.utcnow() - timedelta(days=7)  # Last 7 days
        
        events = self.get_security_events(since=since, limit=10000)
        
        # Calculate event statistics
        event_counts = {}
        severity_counts = {}
        success_counts = {"success": 0, "failure": 0}
        
        for event in events:
            event_counts[event.event_type.value] = event_counts.get(event.event_type.value, 0) + 1
            severity_counts[event.severity.value] = severity_counts.get(event.severity.value, 0) + 1
            
            if event.success:
                success_counts["success"] += 1
            else:
                success_counts["failure"] += 1
        
        # Generate report
        report = {
            "report_period": {
                "start": since.isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "summary": {
                "total_events": len(events),
                "event_types": event_counts,
                "severity_distribution": severity_counts,
                "success_rate": success_counts
            },
            "security_metrics": {
                "suspicious_clients": len(self._suspicious_clients),
                "locked_out_ips": len(self._failed_auth_attempts),
                "critical_events": len([e for e in events if e.severity == SecuritySeverity.CRITICAL])
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return report
    
    def cleanup_old_events(self) -> int:
        """
        Clean up old security events based on retention policy.
        
        Returns:
            Number of events cleaned up
        """
        if self.event_retention_days <= 0:
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.event_retention_days)
        
        initial_count = len(self._security_events)
        self._security_events = [
            event for event in self._security_events
            if event.timestamp >= cutoff_date
        ]
        
        cleaned_count = initial_count - len(self._security_events)
        
        if cleaned_count > 0:
            security_logger.info(f"Cleaned up {cleaned_count} old security events")
        
        return cleaned_count
    
    def _create_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        description: str,
        success: bool,
        **kwargs
    ) -> SecurityEvent:
        """Create security event with proper metadata."""
        import uuid
        
        return SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            description=description,
            success=success,
            client_id=kwargs.get('client_id'),
            client_ip=kwargs.get('client_ip'),
            user_agent=kwargs.get('user_agent'),
            session_id=kwargs.get('session_id'),
            correlation_id=kwargs.get('correlation_id'),
            auth_method=kwargs.get('auth_method'),
            token_type=kwargs.get('token_type'),
            granted_scopes=kwargs.get('granted_scopes'),
            resource=kwargs.get('resource'),
            operation=kwargs.get('operation'),
            tool_name=kwargs.get('tool_name'),
            metadata=kwargs.get('metadata', {})
        )
    
    def _store_security_event(self, event: SecurityEvent) -> None:
        """Store security event in audit system."""
        self._security_events.append(event)
        
        # Track client activity
        if event.client_id:
            if event.client_id not in self._client_activity:
                self._client_activity[event.client_id] = []
            self._client_activity[event.client_id].append(event)
        
        # Log to security logger
        security_logger.info(
            f"Security event: {event.event_type.value}",
            extra=event.to_dict()
        )
    
    def _track_failed_authentication(self, client_ip: str) -> None:
        """Track failed authentication attempt for threat detection."""
        if client_ip not in self._failed_auth_attempts:
            self._failed_auth_attempts[client_ip] = []
        
        self._failed_auth_attempts[client_ip].append(datetime.utcnow())
        
        # Keep only recent attempts (within lockout window)
        cutoff_time = datetime.utcnow() - self.lockout_duration
        self._failed_auth_attempts[client_ip] = [
            attempt for attempt in self._failed_auth_attempts[client_ip]
            if attempt > cutoff_time
        ]
    
    def _count_recent_failures(self, client_ip: str) -> int:
        """Count recent failed authentication attempts."""
        if client_ip not in self._failed_auth_attempts:
            return 0
        
        cutoff_time = datetime.utcnow() - self.lockout_duration
        recent_failures = [
            attempt for attempt in self._failed_auth_attempts[client_ip]
            if attempt > cutoff_time
        ]
        
        return len(recent_failures)


# TODO: IMPLEMENTATION ENGINEER - Add the following security audit enhancements:
# 1. Real-time security alerting and notification system
# 2. Integration with SIEM systems for enterprise monitoring
# 3. Advanced threat detection with machine learning
# 4. Compliance reporting for SOC2, PCI DSS, etc.
# 5. Forensic analysis capabilities and event correlation