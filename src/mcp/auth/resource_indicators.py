"""
RFC 8707 Resource Indicators Implementation
==========================================

Complete implementation of OAuth 2.1 Resource Indicators (RFC 8707)
for scoped token generation and validation in MCP operations.

Key Features:
- Resource indicator validation and scoping
- Audience claim management for tokens
- Resource-specific token generation
- Security validation and compliance
- Comprehensive audit logging

Implements defense-in-depth security with proper resource isolation
and access control according to RFC 8707 specifications.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass

from ..exceptions import ValidationError, AuthorizationError
from ..config import MCPAuthConfig

logger = logging.getLogger(__name__)


@dataclass
class ResourceDefinition:
    """
    Definition of a protected resource with access control metadata.
    
    Defines resource characteristics including URN, description,
    required scopes, and security level for proper access control.
    """
    
    urn: str
    name: str
    description: str
    required_scopes: List[str]
    security_level: str
    resource_type: str
    allowed_operations: List[str]
    
    def __post_init__(self):
        """Validate resource definition after initialization."""
        if not self.urn.startswith('urn:'):
            raise ValueError("Resource URN must start with 'urn:'")
        
        if self.security_level not in ['public', 'internal', 'confidential']:
            raise ValueError("Security level must be public, internal, or confidential")


class ResourceIndicatorManager:
    """
    RFC 8707 Resource Indicators manager for MCP operations.
    
    Implements complete resource indicator functionality including
    validation, scope management, and token audience assignment
    according to OAuth 2.1 Resource Indicators specification.
    """
    
    def __init__(self, auth_config: MCPAuthConfig):
        """
        Initialize resource indicator manager with authentication configuration.
        
        Args:
            auth_config: OAuth 2.1 authentication configuration
        """
        self.auth_config = auth_config
        self.base_resource_urn = auth_config.resource_indicator
        
        # Define MCP resource hierarchy
        self.resources = self._initialize_resources()
        
        logger.info(
            f"Resource indicator manager initialized",
            extra={
                "base_urn": self.base_resource_urn,
                "resource_count": len(self.resources)
            }
        )
    
    def _initialize_resources(self) -> Dict[str, ResourceDefinition]:
        """
        Initialize MCP resource definitions with proper scope requirements.
        
        Returns:
            Dictionary of resource URNs to resource definitions
        """
        base_urn = self.base_resource_urn
        
        resources = {
            # Root MCP resource
            base_urn: ResourceDefinition(
                urn=base_urn,
                name="DocaiChe MCP Server",
                description="Root MCP server resource",
                required_scopes=["read"],
                security_level="public",
                resource_type="server",
                allowed_operations=["health", "capabilities"]
            ),
            
            # Search tool resource
            f"{base_urn}:tool:search": ResourceDefinition(
                urn=f"{base_urn}:tool:search",
                name="Documentation Search Tool",
                description="Intelligent documentation search with content discovery",
                required_scopes=["read", "search"],
                security_level="public",
                resource_type="tool",
                allowed_operations=["search", "query", "discover"]
            ),
            
            # Ingest tool resource
            f"{base_urn}:tool:ingest": ResourceDefinition(
                urn=f"{base_urn}:tool:ingest",
                name="Content Ingestion Tool",
                description="Content ingestion with consent management",
                required_scopes=["write", "ingest"],
                security_level="internal",
                resource_type="tool",
                allowed_operations=["ingest", "upload", "process"]
            ),
            
            # Feedback tool resource
            f"{base_urn}:tool:feedback": ResourceDefinition(
                urn=f"{base_urn}:tool:feedback",
                name="Feedback Collection Tool",
                description="User feedback and analytics collection",
                required_scopes=["write", "feedback"],
                security_level="public",
                resource_type="tool",
                allowed_operations=["submit", "rate", "comment"]
            ),
            
            # Collections resource
            f"{base_urn}:resource:collections": ResourceDefinition(
                urn=f"{base_urn}:resource:collections",
                name="Documentation Collections",
                description="Access to documentation collections and workspaces",
                required_scopes=["read"],
                security_level="public",
                resource_type="resource",
                allowed_operations=["list", "read", "metadata"]
            ),
            
            # Status resource
            f"{base_urn}:resource:status": ResourceDefinition(
                urn=f"{base_urn}:resource:status",
                name="System Status Resource",
                description="System health and capability information",
                required_scopes=["read"],
                security_level="public",
                resource_type="resource",
                allowed_operations=["health", "status", "metrics"]
            ),
            
            # Metrics resource (restricted)
            f"{base_urn}:resource:metrics": ResourceDefinition(
                urn=f"{base_urn}:resource:metrics",
                name="System Metrics Resource",
                description="Detailed system metrics and analytics",
                required_scopes=["read", "metrics"],
                security_level="internal",
                resource_type="resource",
                allowed_operations=["read", "export", "analyze"]
            ),
            
            # Admin resources (highly restricted)
            f"{base_urn}:admin": ResourceDefinition(
                urn=f"{base_urn}:admin",
                name="Administrative Resources",
                description="Administrative functions and system management",
                required_scopes=["admin", "write"],
                security_level="confidential",
                resource_type="admin",
                allowed_operations=["configure", "manage", "control"]
            )
        }
        
        return resources
    
    def validate_resource_indicator(self, resource: str) -> ResourceDefinition:
        """
        Validate resource indicator according to RFC 8707.
        
        Args:
            resource: Resource indicator URN to validate
            
        Returns:
            Validated resource definition
            
        Raises:
            ValidationError: If resource indicator is invalid
            AuthorizationError: If resource is not accessible
        """
        # Basic URN format validation
        if not self._is_valid_urn_format(resource):
            raise ValidationError(
                message="Invalid resource URN format",
                error_code="INVALID_RESOURCE_URN",
                details={"resource": resource}
            )
        
        # Check if resource is defined
        if resource not in self.resources:
            # Check if it's a hierarchical resource under a known parent
            parent_resource = self._find_parent_resource(resource)
            if parent_resource:
                logger.info(
                    f"Using parent resource for hierarchical access",
                    extra={
                        "requested_resource": resource,
                        "parent_resource": parent_resource.urn
                    }
                )
                return parent_resource
            
            raise ValidationError(
                message="Unknown resource indicator",
                error_code="UNKNOWN_RESOURCE",
                details={"resource": resource}
            )
        
        resource_def = self.resources[resource]
        
        logger.debug(
            f"Resource indicator validated",
            extra={
                "resource": resource,
                "security_level": resource_def.security_level,
                "required_scopes": resource_def.required_scopes
            }
        )
        
        return resource_def
    
    def validate_scope_for_resource(
        self,
        resource: str,
        requested_scopes: List[str],
        operation: Optional[str] = None
    ) -> List[str]:
        """
        Validate requested scopes against resource requirements.
        
        Args:
            resource: Target resource URN
            requested_scopes: List of requested OAuth scopes
            operation: Specific operation being attempted
            
        Returns:
            List of validated scopes for the resource
            
        Raises:
            AuthorizationError: If scopes are insufficient for resource
        """
        resource_def = self.validate_resource_indicator(resource)
        
        # Check required scopes
        missing_scopes = set(resource_def.required_scopes) - set(requested_scopes)
        if missing_scopes:
            raise AuthorizationError(
                message="Insufficient scope for resource access",
                error_code="INSUFFICIENT_SCOPE",
                details={
                    "resource": resource,
                    "required_scopes": resource_def.required_scopes,
                    "requested_scopes": requested_scopes,
                    "missing_scopes": list(missing_scopes)
                }
            )
        
        # Check operation-specific requirements
        if operation and operation not in resource_def.allowed_operations:
            raise AuthorizationError(
                message="Operation not allowed for resource",
                error_code="OPERATION_NOT_ALLOWED",
                details={
                    "resource": resource,
                    "operation": operation,
                    "allowed_operations": resource_def.allowed_operations
                }
            )
        
        # Return scopes that are valid for this resource
        valid_scopes = list(set(requested_scopes) & set(resource_def.required_scopes))
        
        logger.debug(
            f"Scope validation successful",
            extra={
                "resource": resource,
                "operation": operation,
                "valid_scopes": valid_scopes
            }
        )
        
        return valid_scopes
    
    def get_audience_for_resource(self, resource: str) -> str:
        """
        Get appropriate audience claim for JWT token.
        
        Args:
            resource: Target resource URN
            
        Returns:
            Audience claim for JWT token
        """
        resource_def = self.validate_resource_indicator(resource)
        
        # Use the validated resource URN as audience
        audience = resource_def.urn
        
        logger.debug(
            f"Audience determined for resource",
            extra={
                "resource": resource,
                "audience": audience
            }
        )
        
        return audience
    
    def get_resources_for_scope(self, scope: str) -> List[ResourceDefinition]:
        """
        Get all resources accessible with given scope.
        
        Args:
            scope: OAuth scope to check
            
        Returns:
            List of resources accessible with the scope
        """
        accessible_resources = []
        
        for resource_def in self.resources.values():
            if scope in resource_def.required_scopes:
                accessible_resources.append(resource_def)
        
        logger.debug(
            f"Found {len(accessible_resources)} resources for scope '{scope}'"
        )
        
        return accessible_resources
    
    def _is_valid_urn_format(self, urn: str) -> bool:
        """
        Validate URN format according to RFC 8141.
        
        Args:
            urn: URN to validate
            
        Returns:
            True if URN format is valid
        """
        # Basic URN pattern: urn:namespace:specific-string
        urn_pattern = r'^urn:[a-z0-9][a-z0-9\-]{0,31}:[a-z0-9()+,\-.:=@;$_!*\'%/?#]+$'
        
        if not re.match(urn_pattern, urn, re.IGNORECASE):
            return False
        
        # Ensure URN starts with our base resource URN
        if not urn.startswith(self.base_resource_urn):
            return False
        
        return True
    
    def _find_parent_resource(self, resource: str) -> Optional[ResourceDefinition]:
        """
        Find parent resource for hierarchical resource access.
        
        Args:
            resource: Child resource URN
            
        Returns:
            Parent resource definition if found
        """
        # Try progressively shorter URN prefixes to find parent
        parts = resource.split(':')
        
        for i in range(len(parts) - 1, 2, -1):  # Don't go below urn:namespace:
            potential_parent = ':'.join(parts[:i])
            if potential_parent in self.resources:
                return self.resources[potential_parent]
        
        return None
    
    def get_resource_hierarchy(self) -> Dict[str, List[str]]:
        """
        Get resource hierarchy for administration and debugging.
        
        Returns:
            Dictionary mapping parent resources to child resources
        """
        hierarchy = {}
        
        for urn in self.resources.keys():
            parts = urn.split(':')
            if len(parts) > 3:  # Has potential parent
                parent_urn = ':'.join(parts[:-1])
                if parent_urn in self.resources:
                    if parent_urn not in hierarchy:
                        hierarchy[parent_urn] = []
                    hierarchy[parent_urn].append(urn)
        
        return hierarchy
    
    def audit_resource_access(
        self,
        resource: str,
        client_id: str,
        scopes: List[str],
        operation: Optional[str] = None,
        success: bool = True
    ) -> None:
        """
        Audit resource access for security monitoring.
        
        Args:
            resource: Accessed resource URN
            client_id: OAuth client ID
            scopes: Used OAuth scopes
            operation: Performed operation
            success: Whether access was successful
        """
        resource_def = self.resources.get(resource)
        
        logger.info(
            f"Resource access audit",
            extra={
                "event_type": "resource_access",
                "resource": resource,
                "resource_type": resource_def.resource_type if resource_def else "unknown",
                "security_level": resource_def.security_level if resource_def else "unknown",
                "client_id": client_id,
                "scopes": scopes,
                "operation": operation,
                "success": success,
                "timestamp": logger.handlers[0].formatter.formatTime(None) if logger.handlers else None
            }
        )


# TODO: IMPLEMENTATION ENGINEER - Add the following RFC 8707 enhancements:
# 1. Dynamic resource registration for extensibility
# 2. Resource metadata caching for performance
# 3. Integration with external resource servers
# 4. Resource capability negotiation
# 5. Advanced hierarchical resource inheritance patterns