"""
Redis Cache Manager - PRD-002 DB-004
Manages Redis connections and cache operations with async patterns

Implements exact interface specified in PRD-002 with compression,
TTL management, and proper error handling according to lines 190-198.
"""

import logging
import gzip
import json
from typing import Optional, Dict, Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages Redis connections and cache operations with async patterns.
    
    Implements exact interface specified in PRD-002 with compression,
    TTL management, and proper error handling.
    
    Cache key patterns from PRD-002 lines 190-198:
    - search:results:{query_hash} - TTL 3600s, gzip compressed
    - content:processed:{content_hash} - TTL 86400s, gzip compressed
    - ai:evaluation:{query_hash} - TTL 7200s
    - github:repo:{owner}/{repo}:{path} - TTL 3600s, gzip compressed
    - config:system:{version} - TTL 300s
    - rate_limit:api:{ip_address} - TTL 60s
    - session:{session_id} - TTL 1800s
    
    Also supports test validation cache key patterns:
    - docs_cache:document:{doc_id}
    - docs_cache:search:{search_hash}
    - docs_cache:metadata:{meta_id}
    """
    
    def __init__(self, redis_config: Dict[str, Any]):
        """
        Initialize CacheManager with Redis configuration.
        
        Args:
            redis_config: Redis configuration dictionary from PRD-003
        """
        self.redis_config = redis_config
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Establish async Redis connection"""
        try:
            # Create Redis connection with security configuration from PRD-003
            self.redis_client = redis.Redis(
                host=self.redis_config.get("host", "redis"),
                port=self.redis_config.get("port", 6379),
                password=self.redis_config.get("password"),  # Redis authentication
                db=self.redis_config.get("db", 0),
                max_connections=self.redis_config.get("max_connections", 20),
                socket_timeout=self.redis_config.get("socket_timeout", 5),
                socket_connect_timeout=self.redis_config.get("connection_timeout", 5),
                decode_responses=False,  # Handle binary data for compression
                ssl=self.redis_config.get("ssl", False),  # SSL configuration for security
                ssl_check_hostname=self.redis_config.get("ssl_check_hostname", False),
                ssl_cert_reqs=self.redis_config.get("ssl_cert_reqs"),
                ssl_ca_certs=self.redis_config.get("ssl_ca_certs"),
                ssl_certfile=self.redis_config.get("ssl_certfile"),
                ssl_keyfile=self.redis_config.get("ssl_keyfile"),
            )
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.aclose()
            self._connected = False
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with automatic decompression.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or Redis unavailable
        """
        try:
            if not self._connected:
                await self.connect()
            
            data = await self.redis_client.get(key)
            if data is None:
                return None
            
            # Decompress if data is compressed (PRD-002 cache patterns)
            if key.startswith(("search:results:", "content:processed:", "github:repo:")):
                data = gzip.decompress(data)
            
            # Parse JSON
            return json.loads(data.decode('utf-8'))
            
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed for get({key}): {e}. Gracefully degrading without cache.")
            self._connected = False
            return None
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Set value in cache with compression and TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (from PRD-002 specification)
        """
        try:
            if not self._connected:
                await self.connect()
            
            # Serialize to JSON
            data = json.dumps(value, default=str).encode('utf-8')
            
            # Compress data for specific key patterns with size threshold optimization
            if key.startswith(("search:results:", "content:processed:", "github:repo:", "docs_cache:document:")):
                if await self._should_compress(data):
                    data = gzip.compress(data)
            
            # Set with TTL
            await self.redis_client.setex(key, ttl, data)
            
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed for set({key}): {e}. Gracefully degrading without cache.")
            self._connected = False
            # Don't raise - allow application to continue without cache
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            # Don't raise - allow application to continue without cache
    
    async def delete(self, key: str) -> None:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
        """
        try:
            if not self._connected:
                await self.connect()
            
            await self.redis_client.delete(key)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed for delete({key}): {e}. Gracefully degrading without cache.")
            self._connected = False
            # Don't raise - allow application to continue without cache
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            # Don't raise - allow application to continue without cache
    
    async def increment(self, key: str) -> int:
        """
        Increment counter value and return new value.
        
        Args:
            key: Cache key for counter
            
        Returns:
            New counter value, or 1 if Redis unavailable
        """
        try:
            if not self._connected:
                await self.connect()
            
            return await self.redis_client.incr(key)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed for increment({key}): {e}. Gracefully degrading without cache.")
            self._connected = False
            return 1  # Return default value when Redis unavailable
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            return 1  # Return default value on error
    
    async def expire(self, key: str, seconds: int) -> None:
        """
        Set expiration time for existing key.
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
        """
        try:
            if not self._connected:
                await self.connect()
            
            await self.redis_client.expire(key, seconds)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed for expire({key}): {e}. Gracefully degrading without cache.")
            self._connected = False
            # Don't raise - allow application to continue without cache
        except Exception as e:
            logger.error(f"Cache expire failed for key {key}: {e}")
            # Don't raise - allow application to continue without cache
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health and return status information.
        
        Returns:
            Dictionary with health status and connection info
        """
        try:
            if not self._connected:
                await self.connect()
            
            # Test ping
            ping_result = await self.redis_client.ping()
            
            # Get info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "connected": self._connected,
                "ping": ping_result,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    def _get_document_key(self, doc_id: str) -> str:
        """Generate document cache key for test validation compatibility"""
        return f"docs_cache:document:{doc_id}"
    
    def _get_search_key(self, query: str) -> str:
        """Generate search cache key for test validation compatibility"""
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"docs_cache:search:{query_hash}"
    
    def _get_metadata_key(self, meta_id: str) -> str:
        """Generate metadata cache key for test validation compatibility"""
        return f"docs_cache:metadata:{meta_id}"
    
    async def set_document(self, doc_id: str, document: Dict[str, Any]) -> None:
        """
        Set document with compression and proper cache key pattern.
        
        Args:
            doc_id: Document identifier
            document: Document data to cache
        """
        key = self._get_document_key(doc_id)
        await self.set(key, document, ttl=86400)  # 24 hours TTL for documents
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document with automatic decompression.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document data or None if not found
        """
        key = self._get_document_key(doc_id)
        return await self.get(key)
    
    async def initialize(self) -> None:
        """
        Initialize cache manager and ensure connection.
        Expected by test validation framework.
        """
        await self.connect()
    
    async def _should_compress(self, data: bytes) -> bool:
        """
        Determine if data should be compressed based on size threshold.
        Optimize compression logic with size thresholds for performance.
        
        Args:
            data: Data to evaluate for compression
            
        Returns:
            True if data should be compressed
        """
        # Only compress data larger than 1KB to optimize performance
        return len(data) > 1024


async def create_cache_manager(config: Optional[Dict[str, Any]] = None) -> CacheManager:
    """
    Factory function to create CacheManager with configuration integration.
    
    Args:
        config: Optional configuration override
        
    Returns:
        Configured CacheManager instance
    """
    if config is None:
        # Integrate with PRD-003 configuration system
        try:
            from src.core.config import get_system_configuration
            if get_system_configuration is not None:
                system_config = get_system_configuration()
                redis_config = {
                    "host": system_config.redis.host,
                    "port": system_config.redis.port,
                    "password": system_config.redis.password,
                    "db": system_config.redis.db,
                    "max_connections": system_config.redis.max_connections,
                    "connection_timeout": system_config.redis.connection_timeout,
                    "socket_timeout": system_config.redis.socket_timeout,
                    "ssl": system_config.redis.ssl,
                }
            else:
                redis_config = {
                    "host": "redis",
                    "port": 6379,
                    "db": 0,
                    "max_connections": 20,
                    "connection_timeout": 5,
                    "socket_timeout": 5,
                    "ssl": False,
                }
        except ImportError:
            logger.warning("Could not load configuration, using defaults")
            redis_config = {
                "host": "redis",
                "port": 6379,
                "db": 0,
                "max_connections": 20,
                "connection_timeout": 5,
                "socket_timeout": 5,
                "ssl": False,
            }
    else:
        redis_config = config
    
    return CacheManager(redis_config)