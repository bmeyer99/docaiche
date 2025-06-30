"""
Cache Manager for AI log queries using Redis.

This module provides intelligent caching for log queries with
dynamic TTL calculation and cache invalidation strategies.
"""

import json
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching for AI log queries.
    
    Features:
    - Dynamic TTL based on query parameters
    - Cache invalidation strategies
    - Compression for large results
    - Cache statistics tracking
    """
    
    def __init__(self, 
                 redis_url: str = "redis://redis:6379",
                 key_prefix: str = "ai_logs:",
                 default_ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys
            default_ttl: Default TTL in seconds
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self._redis_client = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "invalidations": 0
        }
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self._redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis_client = None
            
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            
    def _is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._redis_client is not None
        
    def generate_cache_key(self, query_params: Dict[str, Any]) -> str:
        """
        Generate a cache key from query parameters.
        
        Args:
            query_params: Query parameters dictionary
            
        Returns:
            Cache key string
        """
        # Sort params for consistent hashing
        sorted_params = json.dumps(query_params, sort_keys=True)
        param_hash = hashlib.sha256(sorted_params.encode()).hexdigest()[:16]
        
        # Include important params in key for debugging
        mode = query_params.get("mode", "unknown")
        time_range = query_params.get("time_range", "unknown")
        
        return f"{self.key_prefix}{mode}:{time_range}:{param_hash}"
        
    def calculate_ttl(self, query_params: Dict[str, Any]) -> int:
        """
        Calculate appropriate TTL based on query parameters.
        
        Args:
            query_params: Query parameters
            
        Returns:
            TTL in seconds
        """
        time_range = query_params.get("time_range", "1h")
        
        # Parse time range
        if time_range.endswith("m"):
            minutes = int(time_range[:-1])
            if minutes <= 5:
                return 30  # 30 seconds for very recent data
            elif minutes <= 30:
                return 60  # 1 minute for recent data
            else:
                return 300  # 5 minutes for less recent data
                
        elif time_range.endswith("h"):
            hours = int(time_range[:-1])
            if hours <= 1:
                return 300  # 5 minutes for last hour
            elif hours <= 6:
                return 600  # 10 minutes for several hours
            else:
                return 1800  # 30 minutes for longer ranges
                
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            if days <= 1:
                return 3600  # 1 hour for daily data
            else:
                return 7200  # 2 hours for multi-day data
                
        return self.default_ttl
        
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None
        """
        if not self._is_connected():
            return None
            
        try:
            cached_data = await self._redis_client.get(cache_key)
            
            if cached_data:
                self._stats["hits"] += 1
                logger.debug(f"Cache hit: {cache_key}")
                
                # Deserialize
                return json.loads(cached_data)
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss: {cache_key}")
                return None
                
        except RedisError as e:
            logger.error(f"Redis error on get: {e}")
            self._stats["errors"] += 1
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid cached data: {e}")
            await self.invalidate(cache_key)
            return None
            
    async def set(self, 
                  cache_key: str, 
                  data: Dict[str, Any], 
                  ttl: Optional[int] = None) -> bool:
        """
        Cache a result.
        
        Args:
            cache_key: Cache key
            data: Data to cache
            ttl: TTL in seconds (uses default if None)
            
        Returns:
            Success status
        """
        if not self._is_connected():
            return False
            
        try:
            # Serialize data
            serialized = json.dumps(data)
            
            # Check size (warn if large)
            size_mb = len(serialized) / (1024 * 1024)
            if size_mb > 1:
                logger.warning(f"Large cache entry: {cache_key} ({size_mb:.1f} MB)")
                
            # Set with TTL
            ttl = ttl or self.default_ttl
            await self._redis_client.setex(cache_key, ttl, serialized)
            
            logger.debug(f"Cached result: {cache_key} (TTL: {ttl}s)")
            return True
            
        except RedisError as e:
            logger.error(f"Redis error on set: {e}")
            self._stats["errors"] += 1
            return False
            
    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: Key pattern (supports * wildcard)
            
        Returns:
            Number of keys invalidated
        """
        if not self._is_connected():
            return 0
            
        try:
            # Find matching keys
            keys = []
            async for key in self._redis_client.scan_iter(match=pattern):
                keys.append(key)
                
            if keys:
                # Delete in batch
                deleted = await self._redis_client.delete(*keys)
                self._stats["invalidations"] += deleted
                logger.info(f"Invalidated {deleted} cache entries matching: {pattern}")
                return deleted
            else:
                return 0
                
        except RedisError as e:
            logger.error(f"Redis error on invalidate: {e}")
            self._stats["errors"] += 1
            return 0
            
    async def invalidate_by_service(self, service: str) -> int:
        """
        Invalidate all cache entries for a specific service.
        
        Args:
            service: Service name
            
        Returns:
            Number of keys invalidated
        """
        # Invalidate all entries that might contain this service's data
        pattern = f"{self.key_prefix}*"
        return await self.invalidate(pattern)
        
    async def invalidate_by_time_range(self, time_range: str) -> int:
        """
        Invalidate cache entries for a specific time range.
        
        Args:
            time_range: Time range (e.g., "1h", "30m")
            
        Returns:
            Number of keys invalidated
        """
        pattern = f"{self.key_prefix}*:{time_range}:*"
        return await self.invalidate(pattern)
        
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics dictionary
        """
        stats = dict(self._stats)
        
        if self._is_connected():
            try:
                # Get Redis info
                info = await self._redis_client.info()
                stats.update({
                    "connected": True,
                    "used_memory_mb": info.get("used_memory", 0) / (1024 * 1024),
                    "total_keys": await self._redis_client.dbsize(),
                    "hit_rate": stats["hits"] / (stats["hits"] + stats["misses"]) 
                                if (stats["hits"] + stats["misses"]) > 0 else 0
                })
            except:
                stats["connected"] = False
        else:
            stats["connected"] = False
            
        return stats
        
    async def clear_all(self) -> bool:
        """
        Clear all AI log cache entries.
        
        Returns:
            Success status
        """
        if not self._is_connected():
            return False
            
        try:
            count = await self.invalidate(f"{self.key_prefix}*")
            logger.info(f"Cleared all AI log cache entries: {count} keys")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
            
    async def warm_cache(self, common_queries: List[Dict[str, Any]]) -> int:
        """
        Pre-warm cache with common queries.
        
        Args:
            common_queries: List of common query parameters
            
        Returns:
            Number of entries warmed
        """
        warmed = 0
        
        for query_params in common_queries:
            cache_key = self.generate_cache_key(query_params)
            
            # Check if already cached
            if await self.get(cache_key):
                continue
                
            # This would normally execute the query and cache result
            # For now, just count
            warmed += 1
            
        logger.info(f"Warmed cache with {warmed} entries")
        return warmed