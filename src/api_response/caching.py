"""
ResponseCacheHandler: Handles caching of API responses in Redis.
"""

import json
from typing import Any, Optional
from redis.asyncio import Redis
from .models import CachedResponse
from .exceptions import CacheError


class ResponseCacheHandler:
    """
    Manages caching of API responses in Redis.
    """

    def __init__(self, redis_client: Redis, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl

    async def get(self, key: str) -> Optional[CachedResponse]:
        """
        Get a cached response from Redis.
        """
        try:
            cached_data = await self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                return CachedResponse(**data)
            return None
        except Exception as e:
            raise CacheError(f"Failed to get cache for key {key}: {e}")

    async def set(self, key: str, response: Any):
        """
        Set a response in the Redis cache.
        """
        try:
            # Pydantic's model_dump_json handles datetime serialization
            cache_entry = CachedResponse(key=key, value=response, ttl=self.ttl)
            await self.redis.set(key, cache_entry.model_dump_json(), ex=self.ttl)
        except Exception as e:
            raise CacheError(f"Failed to set cache for key {key}: {e}")

    async def invalidate(self, key: str):
        """
        Invalidate a cache entry.
        """
        try:
            await self.redis.delete(key)
        except Exception as e:
            raise CacheError(f"Failed to invalidate cache for key {key}: {e}")
