"""
Base MCP Resource Interface and Common Functionality
====================================================

Abstract base resource interface defining the contract for all MCP resource
implementations with consistent caching, access patterns, and validation.

Key Features:
- Abstract resource interface for consistency
- Resource metadata and caching management
- URI pattern matching and validation
- Access control and permissions
- Performance monitoring and metrics

Provides foundation for all MCP resources with standardized access,
caching, and monitoring capabilities.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from ..schemas import ResourceDefinition, MCPRequest, MCPResponse
from ..exceptions import ResourceError, ValidationError, AccessDeniedError
from ..auth.consent_manager import ConsentManager
from ..auth.security_audit import SecurityAuditor

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetadata:
    """
    Resource metadata and performance information.
    
    Provides comprehensive metadata about resource characteristics,
    caching behavior, and access patterns.
    """
    
    uri_pattern: str
    name: str
    description: str
    mime_type: str
    
    # Caching characteristics
    cacheable: bool = True
    cache_ttl: int = 3600  # 1 hour default
    max_size_bytes: Optional[int] = None
    
    # Access statistics
    total_accesses: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_response_time_ms: float = 0.0
    
    # Security and compliance
    requires_authentication: bool = False
    access_level: str = "public"
    audit_enabled: bool = True
    
    def update_access_stats(self, response_time_ms: float, cache_hit: bool = False):
        """Update access statistics."""
        self.total_accesses += 1
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # Update average response time
        if self.total_accesses == 1:
            self.average_response_time_ms = response_time_ms
        else:
            self.average_response_time_ms = (
                (self.average_response_time_ms * (self.total_accesses - 1) + response_time_ms)
                / self.total_accesses
            )
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_accesses == 0:
            return 0.0
        return self.cache_hits / self.total_accesses
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "uri_pattern": self.uri_pattern,
            "name": self.name,
            "description": self.description,
            "mime_type": self.mime_type,
            "caching": {
                "cacheable": self.cacheable,
                "cache_ttl": self.cache_ttl,
                "max_size_bytes": self.max_size_bytes
            },
            "statistics": {
                "total_accesses": self.total_accesses,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": self.cache_hit_rate,
                "average_response_time_ms": self.average_response_time_ms
            },
            "security": {
                "requires_authentication": self.requires_authentication,
                "access_level": self.access_level,
                "audit_enabled": self.audit_enabled
            }
        }


@dataclass
class CachedResource:
    """Cached resource data with expiration."""
    data: Any
    cached_at: datetime
    expires_at: datetime
    etag: Optional[str] = None
    content_length: Optional[int] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if cached resource has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def age_seconds(self) -> int:
        """Get age of cached resource in seconds."""
        return int((datetime.utcnow() - self.cached_at).total_seconds())


class BaseResource(ABC):
    """
    Abstract base class for all MCP resource implementations.
    
    Defines the contract that all resources must follow including access,
    caching, validation, and monitoring capabilities.
    """
    
    def __init__(
        self,
        consent_manager: Optional[ConsentManager] = None,
        security_auditor: Optional[SecurityAuditor] = None
    ):
        """
        Initialize base resource with security and monitoring dependencies.
        
        Args:
            consent_manager: Consent management system
            security_auditor: Security audit and logging system
        """
        self.consent_manager = consent_manager
        self.security_auditor = security_auditor
        
        # Resource metadata (must be set by concrete implementations)
        self.metadata: Optional[ResourceMetadata] = None
        
        # Resource definition (must be set by concrete implementations)
        self.resource_definition: Optional[ResourceDefinition] = None
        
        # Cache storage
        self._cache: Dict[str, CachedResource] = {}
        
        logger.debug(f"Base resource initialized: {self.__class__.__name__}")
    
    @abstractmethod
    def get_resource_definition(self) -> ResourceDefinition:
        """
        Get complete resource definition with URI patterns and metadata.
        
        Must be implemented by concrete resource classes to define their
        access patterns, caching behavior, and characteristics.
        
        Returns:
            Complete resource definition
        """
        pass
    
    @abstractmethod
    async def fetch_resource(
        self,
        uri: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch resource data for given URI and parameters.
        
        Must be implemented by concrete resource classes to handle the
        specific resource access logic and return appropriate data.
        
        Args:
            uri: Resource URI to fetch
            params: Optional query parameters
            **kwargs: Additional fetch context
            
        Returns:
            Resource data
            
        Raises:
            ResourceError: If resource access fails
        """
        pass
    
    async def handle_request(
        self,
        uri: str,
        params: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Handle complete resource request with caching, validation, and monitoring.
        
        Provides standardized request handling including URI validation,
        caching, access control, and audit logging.
        
        Args:
            uri: Resource URI to access
            params: Optional query parameters
            client_id: OAuth client identifier
            client_ip: Client IP address for audit
            **kwargs: Additional request context
            
        Returns:
            Resource data with metadata
        """
        start_time = time.time()
        cache_hit = False
        
        # Ensure resource definition is available
        if not self.resource_definition:
            self.resource_definition = self.get_resource_definition()
        
        if not self.metadata:
            raise ResourceError(
                message="Resource metadata not initialized",
                error_code="RESOURCE_NOT_INITIALIZED",
                resource_uri=uri
            )
        
        try:
            # Validate URI and parameters
            self._validate_uri(uri)
            self._validate_params(params)
            
            # Check authentication requirements
            if self.metadata.requires_authentication and not client_id:
                raise AccessDeniedError(
                    message="Authentication required for resource access",
                    error_code="AUTHENTICATION_REQUIRED",
                    resource_uri=uri
                )
            
            # Try cache first if enabled
            cache_key = self._generate_cache_key(uri, params)
            if self.metadata.cacheable:
                cached_data = self._get_from_cache(cache_key)
                if cached_data:
                    cache_hit = True
                    response_data = cached_data
                else:
                    # Fetch fresh data
                    response_data = await self.fetch_resource(uri, params, **kwargs)
                    self._store_in_cache(cache_key, response_data)
            else:
                # Always fetch fresh data
                response_data = await self.fetch_resource(uri, params, **kwargs)
            
            # Add metadata to response
            response_time = int((time.time() - start_time) * 1000)
            enriched_response = self._enrich_response(
                response_data, uri, cache_hit, response_time
            )
            
            # Update statistics
            self.metadata.update_access_stats(response_time, cache_hit)
            
            # Audit successful access
            if self.security_auditor and self.metadata.audit_enabled:
                self.security_auditor.log_resource_access(
                    resource_uri=uri,
                    success=True,
                    client_id=client_id or "unknown",
                    response_time_ms=response_time,
                    cache_hit=cache_hit,
                    client_ip=client_ip
                )
            
            logger.debug(
                f"Resource accessed successfully",
                extra={
                    "resource_uri": uri,
                    "response_time_ms": response_time,
                    "cache_hit": cache_hit,
                    "client_id": client_id
                }
            )
            
            return enriched_response
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.metadata.update_access_stats(response_time, cache_hit=False)
            
            # Audit failed access
            if self.security_auditor and self.metadata.audit_enabled:
                self.security_auditor.log_resource_access(
                    resource_uri=uri,
                    success=False,
                    client_id=client_id or "unknown",
                    response_time_ms=response_time,
                    cache_hit=False,
                    client_ip=client_ip,
                    error_details={"error": str(e), "error_type": type(e).__name__}
                )
            
            logger.error(
                f"Resource access failed",
                extra={
                    "resource_uri": uri,
                    "response_time_ms": response_time,
                    "error": str(e),
                    "client_id": client_id
                },
                exc_info=True
            )
            
            raise
    
    def _validate_uri(self, uri: str) -> None:
        """
        Validate URI against resource pattern.
        
        Args:
            uri: URI to validate
            
        Raises:
            ValidationError: If URI is invalid
        """
        if not uri:
            raise ValidationError(
                message="URI cannot be empty",
                error_code="EMPTY_URI"
            )
        
        # Basic URI validation
        try:
            parsed = urlparse(uri)
            if not parsed.path:
                raise ValidationError(
                    message="URI must have a path component",
                    error_code="INVALID_URI_FORMAT",
                    details={"uri": uri}
                )
        except Exception as e:
            raise ValidationError(
                message=f"Invalid URI format: {str(e)}",
                error_code="URI_PARSE_ERROR",
                details={"uri": uri, "error": str(e)}
            )
    
    def _validate_params(self, params: Optional[Dict[str, Any]]) -> None:
        """
        Validate request parameters.
        
        Args:
            params: Parameters to validate
            
        Raises:
            ValidationError: If parameters are invalid
        """
        if not params:
            return
        
        # Basic parameter validation
        for key, value in params.items():
            if not isinstance(key, str):
                raise ValidationError(
                    message="Parameter keys must be strings",
                    error_code="INVALID_PARAM_KEY",
                    details={"key": str(key), "type": type(key).__name__}
                )
            
            # Check for oversized parameters
            if isinstance(value, str) and len(value) > 10000:
                raise ValidationError(
                    message="Parameter value too large",
                    error_code="PARAM_VALUE_TOO_LARGE",
                    details={"key": key, "length": len(value)}
                )
    
    def _generate_cache_key(self, uri: str, params: Optional[Dict[str, Any]]) -> str:
        """
        Generate cache key for URI and parameters.
        
        Args:
            uri: Resource URI
            params: Request parameters
            
        Returns:
            Cache key string
        """
        import hashlib
        
        # Create deterministic cache key
        key_data = f"{uri}:{sorted((params or {}).items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if valid.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        if cache_key not in self._cache:
            return None
        
        cached = self._cache[cache_key]
        if cached.is_expired:
            del self._cache[cache_key]
            return None
        
        return cached.data
    
    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store data in cache with expiration.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        if not self.metadata.cacheable:
            return
        
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.metadata.cache_ttl)
        
        # Check size limits
        if self.metadata.max_size_bytes:
            import json
            data_size = len(json.dumps(data).encode())
            if data_size > self.metadata.max_size_bytes:
                logger.warning(f"Resource data too large for cache: {data_size} bytes")
                return
        
        self._cache[cache_key] = CachedResource(
            data=data,
            cached_at=now,
            expires_at=expires_at,
            content_length=len(str(data))
        )
        
        # Clean expired entries periodically
        self._cleanup_expired_cache()
    
    def _cleanup_expired_cache(self) -> None:
        """Remove expired entries from cache."""
        expired_keys = [
            key for key, cached in self._cache.items()
            if cached.is_expired
        ]
        
        for key in expired_keys:
            del self._cache[key]
    
    def _enrich_response(
        self,
        data: Dict[str, Any],
        uri: str,
        cache_hit: bool,
        response_time_ms: int
    ) -> Dict[str, Any]:
        """
        Enrich response data with metadata.
        
        Args:
            data: Original response data
            uri: Resource URI
            cache_hit: Whether response came from cache
            response_time_ms: Response time in milliseconds
            
        Returns:
            Enriched response with metadata
        """
        return {
            "data": data,
            "metadata": {
                "uri": uri,
                "resource_type": self.metadata.name,
                "cache_hit": cache_hit,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "mime_type": self.metadata.mime_type
            }
        }
    
    def get_resource_info(self) -> Dict[str, Any]:
        """
        Get comprehensive resource information.
        
        Returns:
            Dictionary with resource definition, metadata, and statistics
        """
        return {
            "definition": self.resource_definition.dict() if self.resource_definition else None,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "cache_stats": {
                "cached_items": len(self._cache),
                "cache_hit_rate": self.metadata.cache_hit_rate if self.metadata else 0.0
            },
            "status": "available" if self.metadata else "not_initialized"
        }
    
    def clear_cache(self) -> int:
        """
        Clear all cached data.
        
        Returns:
            Number of items cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Resource cache cleared: {count} items removed")
        return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get detailed cache statistics.
        
        Returns:
            Cache statistics information
        """
        total_size = sum(
            cached.content_length or 0
            for cached in self._cache.values()
        )
        
        expired_count = sum(
            1 for cached in self._cache.values()
            if cached.is_expired
        )
        
        return {
            "total_items": len(self._cache),
            "expired_items": expired_count,
            "total_size_bytes": total_size,
            "hit_rate": self.metadata.cache_hit_rate if self.metadata else 0.0,
            "average_age_seconds": sum(
                cached.age_seconds for cached in self._cache.values()
            ) / len(self._cache) if self._cache else 0
        }


# TODO: IMPLEMENTATION ENGINEER - Add the following base resource enhancements:
# 1. Advanced caching strategies (LRU, time-based eviction)
# 2. Resource versioning and ETags for conditional requests
# 3. Compression and streaming for large resources
# 4. Resource dependency management and invalidation
# 5. Integration with external caching systems (Redis, Memcached)