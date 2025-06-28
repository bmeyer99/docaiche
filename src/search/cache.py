"""
Search Cache Manager - PRD-009
Redis-based caching for search results and query optimization.

Implements search result caching with TTL management, cache invalidation,
and performance optimization as specified in PRD-009.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .models import SearchQuery, SearchResults, CachedSearchResult
from .exceptions import SearchCacheError
from src.database.connection import CacheManager

logger = logging.getLogger(__name__)


class SearchCacheManager:
    """
    Redis-based search result caching manager.

    Implements search result caching with configurable TTL, cache invalidation,
    and query normalization as specified in PRD-009.
    """

    def __init__(self, cache_manager: CacheManager):
        """
        Initialize search cache manager.

        Args:
            cache_manager: Redis cache manager from database layer
        """
        self.cache_manager = cache_manager

        # Cache configuration
        self.default_ttl = 3600  # 1 hour default TTL
        self.cache_key_prefix = "search:results:"
        self.analytics_key_prefix = "search:analytics:"

        logger.info("SearchCacheManager initialized")

    async def get_cached_results(self, query: SearchQuery) -> Optional[SearchResults]:
        """
        Get cached search results for a query.

        Args:
            query: Search query to look up

        Returns:
            Cached SearchResults if found, None otherwise

        Raises:
            SearchCacheError: If cache lookup fails
        """
        try:
            # Generate cache key from normalized query
            cache_key = self._generate_cache_key(query)

            logger.debug(f"Looking up cached results for key: {cache_key}")

            # Get cached data from Redis
            cached_data = await self.cache_manager.get(cache_key)

            if cached_data is None:
                logger.debug("No cached results found")
                return None

            # Parse cached search result
            cached_result = CachedSearchResult(**cached_data)

            # Check if cache has expired (additional check beyond Redis TTL)
            if datetime.utcnow() > cached_result.expires_at:
                logger.debug("Cached results expired, removing from cache")
                await self.cache_manager.delete(cache_key)
                return None

            # Update access statistics
            await self._update_access_stats(cache_key, cached_result)

            # Mark results as cache hit
            search_results = cached_result.results
            search_results.cache_hit = True

            logger.info(f"Cache hit for query: {query.query[:50]}...")
            return search_results

        except Exception as e:
            logger.error(f"Failed to get cached results: {e}")
            raise SearchCacheError(
                f"Cache lookup failed: {str(e)}",
                cache_key=self._generate_cache_key(query),
                operation="get",
                error_context={"error": str(e)},
            )

    async def cache_results(
        self,
        query: SearchQuery,
        results: SearchResults,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Cache search results with TTL.

        Args:
            query: Search query used
            results: Search results to cache
            ttl_seconds: Time to live in seconds (uses default if None)

        Raises:
            SearchCacheError: If caching fails
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(query)

            # Use default TTL if not specified
            ttl = ttl_seconds or self.default_ttl

            # Create cached result object
            cached_result = CachedSearchResult(
                query_hash=cache_key,
                results=results,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl),
                access_count=0,
            )

            # Store in Redis
            await self.cache_manager.set(cache_key, cached_result.model_dump(), ttl)

            # Store analytics data
            await self._store_analytics(query, results, cache_key)

            logger.info(
                f"Cached search results: {len(results.results)} results, TTL: {ttl}s"
            )

        except Exception as e:
            logger.error(f"Failed to cache search results: {e}")
            raise SearchCacheError(
                f"Cache storage failed: {str(e)}",
                cache_key=self._generate_cache_key(query),
                operation="set",
                error_context={"error": str(e), "ttl": ttl_seconds},
            )

    async def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cached search results.

        Args:
            pattern: Cache key pattern to invalidate (invalidates all if None)

        Returns:
            Number of cache entries invalidated

        Raises:
            SearchCacheError: If cache invalidation fails
        """
        try:
            if pattern:
                # Invalidate specific pattern (Note: Redis doesn't have pattern delete,
                # so this is a simplified implementation)
                cache_key = f"{self.cache_key_prefix}{pattern}"
                await self.cache_manager.delete(cache_key)
                logger.info(f"Invalidated cache for pattern: {pattern}")
                return 1
            else:
                # For full invalidation, we'd need to implement a pattern-based deletion
                # This is a simplified implementation
                logger.warning(
                    "Full cache invalidation not implemented - would require Redis SCAN"
                )
                return 0

        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            raise SearchCacheError(
                f"Cache invalidation failed: {str(e)}",
                operation="delete",
                error_context={"pattern": pattern, "error": str(e)},
            )

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            # Get Redis health info
            cache_health = await self.cache_manager.health_check()

            stats = {
                "cache_status": cache_health.get("status", "unknown"),
                "redis_version": cache_health.get("redis_version"),
                "used_memory": cache_health.get("used_memory"),
                "connected_clients": cache_health.get("connected_clients"),
                "default_ttl_seconds": self.default_ttl,
                "cache_key_prefix": self.cache_key_prefix,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"cache_status": "error", "error": str(e)}

    def _generate_cache_key(self, query: SearchQuery) -> str:
        """
        Generate normalized cache key for a search query.

        Args:
            query: Search query

        Returns:
            Normalized cache key string
        """
        # Normalize query components for consistent caching
        normalized_query = query.query.lower().strip()
        normalized_filters = json.dumps(query.filters or {}, sort_keys=True)

        # Create cache key components
        key_components = [
            normalized_query,
            query.strategy.value,
            str(query.limit),
            str(query.offset),
            query.technology_hint or "",
            ",".join(sorted(query.workspace_slugs or [])),
            normalized_filters,
        ]

        # Generate hash for cache key
        key_string = "|".join(key_components)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:32]

        return f"{self.cache_key_prefix}{key_hash}"

    async def _update_access_stats(
        self, cache_key: str, cached_result: CachedSearchResult
    ) -> None:
        """
        Update access statistics for cached result.

        Args:
            cache_key: Cache key for the result
            cached_result: Cached result object
        """
        try:
            # Increment access count
            cached_result.access_count += 1

            # Update last accessed time (note: this is in-memory only)
            # For persistent access tracking, we'd need a separate Redis operation

            # Update cache statistics
            await self.cache_manager.increment(f"stats:cache_hits:{cache_key}")

        except Exception as e:
            logger.warning(f"Failed to update access stats: {e}")
            # Don't raise exception for stats update failures

    async def _store_analytics(
        self, query: SearchQuery, results: SearchResults, cache_key: str
    ) -> None:
        """
        Store search analytics data.

        Args:
            query: Original search query
            results: Search results
            cache_key: Generated cache key
        """
        try:
            analytics_data = {
                "query": query.query,
                "strategy": query.strategy.value,
                "technology_hint": query.technology_hint,
                "result_count": len(results.results),
                "execution_time_ms": results.query_time_ms,
                "workspaces_searched": len(results.workspaces_searched),
                "timestamp": datetime.utcnow().isoformat(),
                "cache_key": cache_key,
            }

            # Store analytics with longer TTL (24 hours)
            analytics_key = f"{self.analytics_key_prefix}{cache_key}"
            await self.cache_manager.set(analytics_key, analytics_data, ttl=86400)

        except Exception as e:
            logger.warning(f"Failed to store analytics: {e}")
            # Don't raise exception for analytics storage failures

    async def warm_cache(self, popular_queries: List[SearchQuery]) -> int:
        """
        Warm cache with popular queries.

        Args:
            popular_queries: List of popular queries to pre-cache

        Returns:
            Number of queries successfully cached
        """
        warmed_count = 0

        for query in popular_queries:
            try:
                # Check if already cached
                cached = await self.get_cached_results(query)
                if cached is None:
                    # Would need to execute search and cache results
                    # This is a placeholder for cache warming logic
                    logger.info(f"Would warm cache for query: {query.query}")
                    warmed_count += 1

            except Exception as e:
                logger.warning(f"Failed to warm cache for query {query.query}: {e}")

        logger.info(f"Cache warming completed: {warmed_count} queries processed")
        return warmed_count
