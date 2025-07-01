"""
Optimized Multi-Tier Cache Manager
===================================

High-performance caching with L1 (in-memory) and L2 (Redis) tiers
for maximum efficiency.
"""

import time
import logging
from typing import Any, Optional, Dict, Callable
from collections import OrderedDict
from datetime import datetime, timedelta
import asyncio
import hashlib
import json
import zlib

from src.database.connection import CacheManager

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Thread-safe LRU cache implementation for L1 caching.
    """
    
    def __init__(self, maxsize: int = 100):
        self.maxsize = maxsize
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]['value']
            self.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
            
            self.cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
    
    async def clear_expired(self) -> None:
        """Remove expired entries."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                k for k, v in self.cache.items() 
                if v['expires'] < current_time
            ]
            for key in expired_keys:
                del self.cache[key]
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class OptimizedCacheManager:
    """
    Multi-tier cache manager with L1 (in-memory) and L2 (Redis) caching.
    
    Features:
    - Fast L1 cache for hot data
    - Distributed L2 cache for larger dataset
    - Compression for large values
    - Batch operations for efficiency
    """
    
    def __init__(
        self,
        redis_cache: CacheManager,
        l1_size: int = 100,
        compress_threshold: int = 1024,  # Compress values > 1KB
        enable_stats: bool = True
    ):
        """
        Initialize optimized cache manager.
        
        Args:
            redis_cache: Existing Redis cache manager
            l1_size: Maximum items in L1 cache
            compress_threshold: Compress values larger than this (bytes)
            enable_stats: Track performance statistics
        """
        self.l1_cache = LRUCache(maxsize=l1_size)
        self.l2_cache = redis_cache
        self.compress_threshold = compress_threshold
        self.enable_stats = enable_stats
        
        # Performance stats
        self.stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'misses': 0,
            'compressions': 0,
            'avg_compression_ratio': 0.0
        }
        
        # Start background task for cache maintenance
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        
        logger.info(f"OptimizedCacheManager initialized with L1 size: {l1_size}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (L1 first, then L2).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        start_time = time.time()
        
        # Check L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            if self.enable_stats:
                self.stats['l1_hits'] += 1
            logger.debug(f"L1 cache hit for key: {key}")
            return value
        
        # Check L2 cache
        try:
            compressed_value = await self.l2_cache.get(key)
            if compressed_value is not None:
                # Decompress if needed
                value = self._decompress_value(compressed_value)
                
                # Promote to L1
                await self.l1_cache.set(key, value)
                
                if self.enable_stats:
                    self.stats['l2_hits'] += 1
                
                logger.debug(f"L2 cache hit for key: {key}")
                return value
        except Exception as e:
            logger.error(f"L2 cache error for key {key}: {e}")
        
        # Cache miss
        if self.enable_stats:
            self.stats['misses'] += 1
        
        logger.debug(f"Cache miss for key: {key} (took {time.time() - start_time:.3f}s)")
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        Set value in both cache tiers.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        try:
            # Set in L1 cache
            await self.l1_cache.set(key, value, ttl)
            
            # Compress for L2 if needed
            compressed_value = self._compress_value(value)
            
            # Set in L2 cache
            await self.l2_cache.set(key, compressed_value, ttl)
            
            logger.debug(f"Cached key: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def get_batch(self, keys: list) -> Dict[str, Any]:
        """
        Get multiple values efficiently.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict of key -> value for found items
        """
        results = {}
        l2_keys = []
        
        # Check L1 first
        for key in keys:
            value = await self.l1_cache.get(key)
            if value is not None:
                results[key] = value
            else:
                l2_keys.append(key)
        
        # Batch get from L2 for remaining keys
        if l2_keys:
            try:
                # Redis MGET equivalent
                l2_results = await self._batch_get_l2(l2_keys)
                
                for key, compressed_value in l2_results.items():
                    if compressed_value is not None:
                        value = self._decompress_value(compressed_value)
                        results[key] = value
                        # Promote to L1
                        await self.l1_cache.set(key, value)
                        
            except Exception as e:
                logger.error(f"Batch L2 get error: {e}")
        
        return results
    
    async def set_batch(self, items: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Set multiple values efficiently.
        
        Args:
            items: Dict of key -> value
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        try:
            # Set in L1
            for key, value in items.items():
                await self.l1_cache.set(key, value, ttl)
            
            # Prepare for L2 batch set
            l2_items = {
                key: self._compress_value(value)
                for key, value in items.items()
            }
            
            # Batch set in L2
            await self._batch_set_l2(l2_items, ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"Batch set error: {e}")
            return False
    
    def compute_key(self, *args, **kwargs) -> str:
        """
        Compute cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key
        """
        # Create stable hash from arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def _compress_value(self, value: Any) -> Any:
        """Compress value if it's large enough."""
        # Serialize to JSON
        serialized = json.dumps(value)
        
        # Check size
        if len(serialized) > self.compress_threshold:
            # Compress
            compressed = zlib.compress(serialized.encode())
            
            if self.enable_stats:
                self.stats['compressions'] += 1
                ratio = len(compressed) / len(serialized)
                # Update running average
                avg = self.stats['avg_compression_ratio']
                n = self.stats['compressions']
                self.stats['avg_compression_ratio'] = (avg * (n-1) + ratio) / n
            
            return {'_compressed': True, 'data': compressed}
        
        return value
    
    def _decompress_value(self, value: Any) -> Any:
        """Decompress value if needed."""
        if isinstance(value, dict) and value.get('_compressed'):
            # Decompress
            decompressed = zlib.decompress(value['data'])
            return json.loads(decompressed)
        return value
    
    async def _batch_get_l2(self, keys: list) -> Dict[str, Any]:
        """Batch get from L2 cache."""
        # This would use Redis MGET or pipeline
        results = {}
        for key in keys:
            value = await self.l2_cache.get(key)
            if value is not None:
                results[key] = value
        return results
    
    async def _batch_set_l2(self, items: Dict[str, Any], ttl: int) -> None:
        """Batch set in L2 cache."""
        # This would use Redis MSET or pipeline
        for key, value in items.items():
            await self.l2_cache.set(key, value, ttl)
    
    async def _maintenance_loop(self) -> None:
        """Background maintenance tasks."""
        while True:
            try:
                # Clear expired L1 entries every minute
                await asyncio.sleep(60)
                await self.l1_cache.clear_expired()
                
                # Log stats every 5 minutes
                if self.enable_stats and time.time() % 300 < 60:
                    self._log_stats()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache maintenance error: {e}")
    
    def _log_stats(self) -> None:
        """Log cache performance statistics."""
        total_hits = self.stats['l1_hits'] + self.stats['l2_hits']
        total_requests = total_hits + self.stats['misses']
        
        if total_requests > 0:
            hit_rate = total_hits / total_requests
            l1_ratio = self.stats['l1_hits'] / total_hits if total_hits > 0 else 0
            
            logger.info(
                f"Cache stats - "
                f"Hit rate: {hit_rate:.2%}, "
                f"L1 ratio: {l1_ratio:.2%}, "
                f"L1 hit rate: {self.l1_cache.hit_rate:.2%}, "
                f"Compressions: {self.stats['compressions']}, "
                f"Avg compression: {self.stats['avg_compression_ratio']:.2%}"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current cache statistics."""
        total_hits = self.stats['l1_hits'] + self.stats['l2_hits']
        total_requests = total_hits + self.stats['misses']
        
        return {
            'total_requests': total_requests,
            'hit_rate': total_hits / total_requests if total_requests > 0 else 0,
            'l1_hits': self.stats['l1_hits'],
            'l2_hits': self.stats['l2_hits'],
            'misses': self.stats['misses'],
            'l1_size': len(self.l1_cache.cache),
            'l1_hit_rate': self.l1_cache.hit_rate,
            'compressions': self.stats['compressions'],
            'avg_compression_ratio': self.stats['avg_compression_ratio']
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        self._maintenance_task.cancel()
        try:
            await self._maintenance_task
        except asyncio.CancelledError:
            pass


# Decorator for easy caching
def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    cache_none: bool = False
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        cache_none: Whether to cache None results
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(self, *args, **kwargs):
            # Check if object has cache manager
            cache_manager = getattr(self, '_cache', None)
            if not cache_manager:
                return await func(self, *args, **kwargs)
            
            # Compute cache key
            key = f"{key_prefix}:{func.__name__}:{cache_manager.compute_key(*args, **kwargs)}"
            
            # Check cache
            cached_value = await cache_manager.get(key)
            if cached_value is not None or (cached_value is None and cache_none):
                return cached_value
            
            # Call function
            result = await func(self, *args, **kwargs)
            
            # Cache result
            if result is not None or cache_none:
                await cache_manager.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator