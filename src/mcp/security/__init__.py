"""
MCP Security Framework
======================

Comprehensive security implementation for MCP operations including
input validation, threat detection, audit logging, and compliance.

Key Components:
- SecurityValidator: Input validation and sanitization
- AuditLogger: Security event logging and compliance
- SecurityManager: Centralized security enforcement
- SecurityMiddleware: Request/response security integration
- ThreatDetector: Anomaly detection and threat mitigation
- ComplianceMonitor: Security requirement validation

Implements 2025 MCP security best practices with defense-in-depth
approach and comprehensive monitoring for production environments.
"""

from .validator import SecurityValidator
from .audit_logger import AuditLogger

# Import new security components
try:
    from .security_manager import (
        SecurityManager,
        SecurityPolicy,
        SecurityEvent,
        ThreatLevel,
        ClientSecurityProfile
    )
    from .security_middleware import (
        SecurityMiddleware,
        create_security_decorator
    )
except ImportError:
    # Fallback for partial imports during development
    SecurityManager = None
    SecurityPolicy = None
    SecurityMiddleware = None
    create_security_decorator = None

__all__ = [
    # Original components
    'SecurityValidator',
    'AuditLogger',
    
    # New security components
    'SecurityManager',
    'SecurityPolicy',
    'SecurityMiddleware',
    'create_security_decorator',
    
    # Types and enums
    'SecurityEvent',
    'ThreatLevel',
    'ClientSecurityProfile'
]