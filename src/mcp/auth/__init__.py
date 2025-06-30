"""
MCP Authentication and Authorization Framework
=============================================

OAuth 2.1 compliant authentication system with RFC 8707 Resource Indicators
and comprehensive security controls for MCP operations.

Key Components:
- OAuth 2.1 handlers with PKCE support
- Resource Indicators (RFC 8707) implementation
- User consent management system
- Token validation and scope verification
- Audit logging and security monitoring

Follows 2025 MCP security specification with enhanced threat mitigation
and compliance requirements for production deployment.
"""

from .oauth_handler import OAuth21Handler as OAuth2Handler, TokenValidator
from .resource_indicators import ResourceIndicatorManager
from .consent_manager import ConsentManager, ConsentRecord
from .security_audit import SecurityAuditor

__all__ = [
    'OAuth2Handler',
    'TokenValidator', 
    'ResourceIndicatorManager',
    'ConsentManager',
    'ConsentRecord',
    'SecurityAuditor'
]