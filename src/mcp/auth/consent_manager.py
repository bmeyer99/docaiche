"""
User Consent Management System
==============================

Comprehensive consent management for MCP operations requiring explicit
user authorization according to 2025 security best practices.

Key Features:
- Explicit consent collection and validation
- Consent scope and operation tracking
- Time-limited consent with expiration
- Consent revocation and audit trails
- Security compliance and monitoring

Implements defense-in-depth consent management with proper audit logging
and compliance validation for production security requirements.
"""

import time
import secrets
import hashlib
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from ..schemas import ConsentRequest
from ..exceptions import ConsentError, ValidationError, AuthorizationError
from ..config import MCPAuthConfig

logger = logging.getLogger(__name__)


class ConsentStatus(str, Enum):
    """Consent status enumeration."""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class ConsentRecord:
    """
    Individual consent record with comprehensive metadata.
    
    Tracks consent details including permissions, expiration,
    and audit information for compliance and security monitoring.
    """
    
    consent_id: str
    client_id: str
    operation: str
    description: str
    required_permissions: List[str]
    data_sources: List[str]
    
    # Consent status and timing
    status: ConsentStatus
    granted_at: Optional[datetime]
    expires_at: datetime
    created_at: datetime
    
    # Security metadata
    client_ip: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    
    # Additional context
    consent_context: Dict[str, Any]
    
    def __post_init__(self):
        """Validate consent record after initialization."""
        if self.expires_at <= self.created_at:
            raise ValueError("Consent expiration must be after creation time")
        
        if self.granted_at and self.granted_at > self.expires_at:
            raise ValueError("Consent grant time cannot be after expiration")
    
    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        now = datetime.utcnow()
        return (
            self.status == ConsentStatus.GRANTED and
            now < self.expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if consent has expired."""
        return datetime.utcnow() >= self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert consent record to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO format
        for key in ['granted_at', 'expires_at', 'created_at']:
            if data[key]:
                data[key] = data[key].isoformat()
        return data


class ConsentManager:
    """
    Comprehensive consent management system for MCP operations.
    
    Implements explicit consent collection, validation, and audit
    according to 2025 MCP security requirements and privacy regulations.
    """
    
    def __init__(self, auth_config: MCPAuthConfig):
        """
        Initialize consent manager with authentication configuration.
        
        Args:
            auth_config: OAuth 2.1 authentication configuration
        """
        self.auth_config = auth_config
        self.default_consent_ttl = auth_config.consent_ttl
        
        # In-memory consent storage
        # TODO: IMPLEMENTATION ENGINEER - Replace with persistent storage (Redis/Database)
        self._consent_records: Dict[str, ConsentRecord] = {}
        self._client_consents: Dict[str, Set[str]] = {}  # client_id -> consent_ids
        
        # Consent policies for different operations
        self.consent_policies = self._initialize_consent_policies()
        
        logger.info(
            f"Consent manager initialized",
            extra={
                "default_ttl": self.default_consent_ttl,
                "storage_backend": auth_config.consent_storage_backend
            }
        )
    
    def _initialize_consent_policies(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize consent policies for different MCP operations.
        
        Returns:
            Dictionary of operation consent policies
        """
        return {
            "content_ingestion": {
                "description": "Ingest content from external sources",
                "required_permissions": ["data_access", "content_processing"],
                "sensitive_operations": ["url_fetch", "content_parsing"],
                "default_ttl": 3600,  # 1 hour
                "requires_explicit_consent": True
            },
            
            "deep_search": {
                "description": "Perform deep search with content discovery",
                "required_permissions": ["search_access", "content_discovery"],
                "sensitive_operations": ["external_search", "content_analysis"],
                "default_ttl": 7200,  # 2 hours
                "requires_explicit_consent": True
            },
            
            "feedback_collection": {
                "description": "Collect user feedback and usage analytics",
                "required_permissions": ["analytics_access", "feedback_processing"],
                "sensitive_operations": ["usage_tracking", "behavior_analysis"],
                "default_ttl": 86400,  # 24 hours
                "requires_explicit_consent": False
            },
            
            "system_administration": {
                "description": "Perform system administration tasks",
                "required_permissions": ["admin_access", "system_control"],
                "sensitive_operations": ["config_change", "system_restart"],
                "default_ttl": 1800,  # 30 minutes
                "requires_explicit_consent": True
            },
            
            "data_export": {
                "description": "Export system data and metrics",
                "required_permissions": ["data_export", "metrics_access"],
                "sensitive_operations": ["data_extraction", "metrics_export"],
                "default_ttl": 3600,  # 1 hour
                "requires_explicit_consent": True
            }
        }
    
    async def request_consent(
        self,
        consent_request: ConsentRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Request user consent for sensitive operations.
        
        Args:
            consent_request: Consent request details
            client_ip: Client IP address for audit
            user_agent: Client user agent for audit
            session_id: Session ID for tracking
            
        Returns:
            Consent ID for tracking and validation
            
        Raises:
            ValidationError: If consent request is invalid
        """
        # Validate consent request
        await self._validate_consent_request(consent_request)
        
        # Generate unique consent ID
        consent_id = self._generate_consent_id(consent_request)
        
        # Create consent record
        consent_record = ConsentRecord(
            consent_id=consent_id,
            client_id=consent_request.client_id,
            operation=consent_request.operation,
            description=consent_request.description,
            required_permissions=consent_request.required_permissions,
            data_sources=consent_request.data_sources,
            status=ConsentStatus.PENDING,
            granted_at=None,
            expires_at=datetime.utcnow() + timedelta(seconds=consent_request.expires_in),
            created_at=datetime.utcnow(),
            client_ip=client_ip,
            user_agent=user_agent,
            session_id=session_id,
            consent_context={}
        )
        
        # Store consent record
        self._consent_records[consent_id] = consent_record
        
        # Track client consents
        if consent_request.client_id not in self._client_consents:
            self._client_consents[consent_request.client_id] = set()
        self._client_consents[consent_request.client_id].add(consent_id)
        
        logger.info(
            f"Consent requested",
            extra={
                "consent_id": consent_id,
                "client_id": consent_request.client_id,
                "operation": consent_request.operation,
                "expires_in": consent_request.expires_in
            }
        )
        
        return consent_id
    
    async def grant_consent(
        self,
        consent_id: str,
        granted_permissions: Optional[List[str]] = None
    ) -> ConsentRecord:
        """
        Grant consent for requested operation.
        
        Args:
            consent_id: Consent ID to grant
            granted_permissions: Specific permissions granted (subset of requested)
            
        Returns:
            Updated consent record
            
        Raises:
            ConsentError: If consent cannot be granted
        """
        consent_record = self._get_consent_record(consent_id)
        
        # Validate consent can be granted
        if consent_record.status != ConsentStatus.PENDING:
            raise ConsentError(
                message="Consent is not in pending state",
                error_code="CONSENT_NOT_PENDING",
                details={"consent_id": consent_id, "status": consent_record.status}
            )
        
        if consent_record.is_expired():
            consent_record.status = ConsentStatus.EXPIRED
            raise ConsentError(
                message="Consent request has expired",
                error_code="CONSENT_EXPIRED",
                details={"consent_id": consent_id}
            )
        
        # Update consent record
        consent_record.status = ConsentStatus.GRANTED
        consent_record.granted_at = datetime.utcnow()
        
        # Update permissions if subset provided
        if granted_permissions:
            # Ensure granted permissions are subset of requested
            if not set(granted_permissions).issubset(set(consent_record.required_permissions)):
                raise ConsentError(
                    message="Granted permissions exceed requested permissions",
                    error_code="INVALID_GRANTED_PERMISSIONS",
                    details={
                        "granted": granted_permissions,
                        "requested": consent_record.required_permissions
                    }
                )
            consent_record.required_permissions = granted_permissions
        
        logger.info(
            f"Consent granted",
            extra={
                "consent_id": consent_id,
                "client_id": consent_record.client_id,
                "operation": consent_record.operation,
                "permissions": consent_record.required_permissions
            }
        )
        
        return consent_record
    
    async def validate_consent(
        self,
        client_id: str,
        operation: str,
        required_permissions: List[str]
    ) -> bool:
        """
        Validate that client has valid consent for operation.
        
        Args:
            client_id: OAuth client ID
            operation: Operation being attempted
            required_permissions: Permissions required for operation
            
        Returns:
            True if client has valid consent
            
        Raises:
            ConsentError: If consent is required but not found
        """
        # Check if operation requires consent
        policy = self.consent_policies.get(operation)
        if not policy or not policy.get("requires_explicit_consent", False):
            # No explicit consent required
            return True
        
        # Find valid consent for client and operation
        client_consent_ids = self._client_consents.get(client_id, set())
        
        for consent_id in client_consent_ids:
            consent_record = self._consent_records.get(consent_id)
            if not consent_record:
                continue
            
            # Check if consent matches operation and is valid
            if (consent_record.operation == operation and
                consent_record.is_valid() and
                set(required_permissions).issubset(set(consent_record.required_permissions))):
                
                logger.debug(
                    f"Valid consent found",
                    extra={
                        "consent_id": consent_id,
                        "client_id": client_id,
                        "operation": operation
                    }
                )
                return True
        
        # No valid consent found
        raise ConsentError(
            message="Valid consent required for operation",
            error_code="CONSENT_REQUIRED",
            required_consent=operation,
            details={
                "operation": operation,
                "required_permissions": required_permissions
            }
        )
    
    async def revoke_consent(self, consent_id: str) -> ConsentRecord:
        """
        Revoke previously granted consent.
        
        Args:
            consent_id: Consent ID to revoke
            
        Returns:
            Updated consent record
        """
        consent_record = self._get_consent_record(consent_id)
        
        if consent_record.status != ConsentStatus.GRANTED:
            raise ConsentError(
                message="Cannot revoke consent that is not granted",
                error_code="CONSENT_NOT_GRANTED",
                details={"consent_id": consent_id, "status": consent_record.status}
            )
        
        consent_record.status = ConsentStatus.REVOKED
        
        logger.info(
            f"Consent revoked",
            extra={
                "consent_id": consent_id,
                "client_id": consent_record.client_id,
                "operation": consent_record.operation
            }
        )
        
        return consent_record
    
    def cleanup_expired_consents(self) -> int:
        """
        Clean up expired consent records.
        
        Returns:
            Number of expired consents cleaned up
        """
        current_time = datetime.utcnow()
        expired_count = 0
        
        for consent_id, consent_record in list(self._consent_records.items()):
            if consent_record.expires_at < current_time:
                if consent_record.status in [ConsentStatus.PENDING, ConsentStatus.GRANTED]:
                    consent_record.status = ConsentStatus.EXPIRED
                    expired_count += 1
        
        if expired_count > 0:
            logger.debug(f"Marked {expired_count} consents as expired")
        
        return expired_count
    
    def get_client_consents(self, client_id: str) -> List[ConsentRecord]:
        """
        Get all consent records for a client.
        
        Args:
            client_id: OAuth client ID
            
        Returns:
            List of consent records for the client
        """
        client_consent_ids = self._client_consents.get(client_id, set())
        consents = []
        
        for consent_id in client_consent_ids:
            consent_record = self._consent_records.get(consent_id)
            if consent_record:
                consents.append(consent_record)
        
        return consents
    
    async def _validate_consent_request(self, consent_request: ConsentRequest) -> None:
        """Validate consent request parameters."""
        if not consent_request.operation:
            raise ValidationError(
                message="Operation is required for consent request",
                error_code="MISSING_OPERATION"
            )
        
        if not consent_request.required_permissions:
            raise ValidationError(
                message="Required permissions must be specified",
                error_code="MISSING_PERMISSIONS"
            )
        
        if consent_request.expires_in < 60 or consent_request.expires_in > 86400:
            raise ValidationError(
                message="Consent expiration must be between 1 minute and 24 hours",
                error_code="INVALID_EXPIRATION"
            )
    
    def _generate_consent_id(self, consent_request: ConsentRequest) -> str:
        """Generate unique consent ID."""
        # Create unique identifier based on request and timestamp
        content = (
            f"{consent_request.client_id}:"
            f"{consent_request.operation}:"
            f"{time.time()}:"
            f"{secrets.token_urlsafe(8)}"
        )
        
        consent_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"consent_{consent_hash}"
    
    def _get_consent_record(self, consent_id: str) -> ConsentRecord:
        """Get consent record by ID with validation."""
        if consent_id not in self._consent_records:
            raise ConsentError(
                message="Consent record not found",
                error_code="CONSENT_NOT_FOUND",
                details={"consent_id": consent_id}
            )
        
        return self._consent_records[consent_id]


# TODO: IMPLEMENTATION ENGINEER - Add the following consent management features:
# 1. Persistent storage backend (Redis/Database) for consent records
# 2. Consent delegation and hierarchical permissions
# 3. Automated consent expiration notifications
# 4. Consent analytics and compliance reporting
# 5. Integration with external consent management platforms