"""
High-Performance External Search Orchestrator
=============================================

Implements external search with hedged requests, adaptive timeouts,
and multi-tier caching as specified in PERFORMANCE_OPTIMIZATION.md
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta

from .base import SearchProvider
from .models import SearchOptions, SearchResults, SearchResult, HealthStatus
from .registry import ProviderRegistry
from ..core.models import NormalizedQuery
from src.search.optimized_cache import OptimizedCacheManager

logger = logging.getLogger(__name__)


class AdaptiveTimeoutManager:
    """
    Manages adaptive timeouts based on historical performance.
    
    Implements P95 latency + 20% buffer with cap at 5 seconds.
    """
    
    def __init__(self, max_history: int = 100):
        self.provider_latencies = defaultdict(lambda: deque(maxlen=max_history))
        self.default_timeout = 2.0
        self.max_timeout = 5.0
        self.min_timeout = 0.5
    
    def record_latency(self, provider_id: str, latency_ms: float) -> None:
        """Record latency for provider."""
        self.provider_latencies[provider_id].append(latency_ms / 1000.0)  # Convert to seconds
    
    def get_timeout(self, provider_id: str) -> float:
        """Get adaptive timeout for provider."""
        if provider_id not in self.provider_latencies:
            return self.default_timeout
        
        latencies = list(self.provider_latencies[provider_id])
        if len(latencies) < 5:  # Need at least 5 samples
            return self.default_timeout
        
        # Calculate P95 latency
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_index]
        
        # Add 20% buffer and cap
        adaptive_timeout = min(p95_latency * 1.2, self.max_timeout)
        return max(adaptive_timeout, self.min_timeout)


class HedgedRequestManager:
    """
    Manages hedged requests for improved latency.
    
    Starts backup provider after configurable delay if primary is slow.
    """
    
    def __init__(self, hedged_delay: float = 0.2):
        self.hedged_delay = hedged_delay
    
    async def execute_hedged_search(
        self,
        primary_provider: SearchProvider,
        backup_provider: SearchProvider,
        options: SearchOptions
    ) -> SearchResults:
        """
        Execute hedged search with primary and backup providers.
        
        Args:
            primary_provider: Primary search provider
            backup_provider: Backup search provider  
            options: Search options
            
        Returns:
            First successful result
        """
        # Start primary search
        primary_task = asyncio.create_task(
            primary_provider.search(options)
        )
        
        # Wait for hedged delay
        try:
            result = await asyncio.wait_for(primary_task, timeout=self.hedged_delay)
            if not result.error:
                return result
        except asyncio.TimeoutError:
            pass  # Primary is slow, start backup
        
        # Start backup search if primary is slow or failed
        if not primary_task.done():
            backup_task = asyncio.create_task(
                backup_provider.search(options)
            )
            
            # Return first successful result
            done, pending = await asyncio.wait(
                [primary_task, backup_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Return best result
            results = [task.result() for task in done if not task.exception()]
            if results:
                # Return result with no error first, then best by result count
                good_results = [r for r in results if not r.error]
                if good_results:
                    return max(good_results, key=lambda r: len(r.results))
                return results[0]
        
        # Primary completed (possibly with error)
        return await primary_task


class ExternalSearchOrchestrator:
    """
    High-performance external search orchestrator.
    
    Features:
    - Hedged requests for improved latency
    - Adaptive timeouts based on provider performance
    - Multi-tier caching with compression
    - Request batching and deduplication
    - Circuit breaker pattern for failing providers
    - Performance monitoring and metrics
    """
    
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        cache_manager: OptimizedCacheManager,
        enable_hedged_requests: bool = True,
        hedged_delay: float = 0.2,
        max_concurrent_providers: int = 3
    ):
        """
        Initialize external search orchestrator.
        
        Args:
            provider_registry: Registry of available providers
            cache_manager: Multi-tier cache manager
            enable_hedged_requests: Enable hedged request pattern
            hedged_delay: Delay before starting backup provider (seconds)
            max_concurrent_providers: Maximum concurrent providers
        """
        self.provider_registry = provider_registry
        self.cache_manager = cache_manager
        self.enable_hedged_requests = enable_hedged_requests
        self.max_concurrent_providers = max_concurrent_providers
        
        # Performance management
        self.timeout_manager = AdaptiveTimeoutManager()
        self.hedged_manager = HedgedRequestManager(hedged_delay)
        
        # Circuit breaker state
        self.provider_failures = defaultdict(int)
        self.provider_circuit_open = defaultdict(bool)
        self.last_failure_time = defaultdict(datetime)
        self.failure_threshold = 5
        self.circuit_timeout = 300  # 5 minutes
        
        # Performance metrics
        self.metrics = {
            'total_searches': 0,
            'cache_hits': 0,
            'provider_calls': defaultdict(int),
            'hedged_requests': 0,
            'circuit_breaks': 0
        }
        
        logger.info("ExternalSearchOrchestrator initialized with performance optimizations")
    
    async def search(
        self,
        query: str,
        technology_hint: Optional[str] = None,
        max_results: int = 10,
        provider_ids: Optional[List[str]] = None
    ) -> SearchResults:
        """
        Execute optimized external search.
        
        Args:
            query: Search query
            technology_hint: Technology context for provider selection
            max_results: Maximum results to return
            provider_ids: Specific providers to use (None = auto-select)
            
        Returns:
            Combined and optimized search results
        """
        start_time = time.time()
        self.metrics['total_searches'] += 1
        
        # Generate cache key
        cache_key = self._generate_cache_key(query, technology_hint, max_results, provider_ids)
        
        # Check cache first
        cached_results = await self.cache_manager.get(cache_key)
        if cached_results:
            self.metrics['cache_hits'] += 1
            logger.info(f"Cache hit for query: {query[:50]}...")
            return cached_results
        
        try:
            # Select providers
            selected_providers = await self._select_providers(
                query, technology_hint, provider_ids
            )
            
            if not selected_providers:
                return SearchResults(
                    results=[],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    provider="ExternalSearchOrchestrator",
                    query=query,
                    error="No available providers"
                )
            
            # Execute search with optimization strategy
            results = await self._execute_optimized_search(
                query, selected_providers, max_results
            )
            
            # Cache successful results
            if not results.error and results.results:
                await self.cache_manager.set(cache_key, results, ttl=3600)
            
            # Update performance metrics
            execution_time = int((time.time() - start_time) * 1000)
            results.execution_time_ms = execution_time
            
            logger.info(
                f"External search completed in {execution_time}ms: "
                f"{len(results.results)} results from {len(selected_providers)} providers"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"External search failed: {e}")
            return SearchResults(
                results=[],
                execution_time_ms=int((time.time() - start_time) * 1000),
                provider="ExternalSearchOrchestrator",
                query=query,
                error=str(e)
            )
    
    async def _select_providers(
        self,
        query: str,
        technology_hint: Optional[str],
        provider_ids: Optional[List[str]]
    ) -> List[SearchProvider]:
        """
        Select optimal providers for query.
        
        Args:
            query: Search query
            technology_hint: Technology context
            provider_ids: Specific provider IDs to use
            
        Returns:
            List of selected providers
        """
        # Get healthy provider IDs
        available_provider_ids = self.provider_registry.list_providers(active_only=True, healthy_only=True)
        
        if not available_provider_ids:
            return []
        
        # Get actual provider objects
        available_providers = []
        for provider_id in available_provider_ids:
            provider = self.provider_registry.get_provider(provider_id)
            if provider:
                available_providers.append(provider)
        
        # Filter by specified provider IDs
        if provider_ids:
            available_providers = [
                p for p in available_providers 
                if p.config.provider_id in provider_ids
            ]
        
        # Filter out circuit-broken providers
        available_providers = [
            p for p in available_providers
            if not self._is_circuit_open(p.config.provider_id)
        ]
        
        if not available_providers:
            return []
        
        # Smart provider selection based on query
        selected = self._rank_providers_for_query(query, technology_hint, available_providers)
        
        # Limit concurrent providers
        return selected[:self.max_concurrent_providers]
    
    def _rank_providers_for_query(
        self,
        query: str,
        technology_hint: Optional[str],
        providers: List[SearchProvider]
    ) -> List[SearchProvider]:
        """
        Rank providers by suitability for query.
        
        Args:
            query: Search query
            technology_hint: Technology context
            providers: Available providers
            
        Returns:
            Providers ranked by suitability
        """
        provider_scores = {}
        
        for provider in providers:
            score = 0.5  # Base score
            
            # Technology-specific scoring
            if technology_hint:
                if provider.config.provider_id in ['brave_search', 'duckduckgo']:
                    score += 0.3  # Good for technical queries
                
            # Query pattern scoring
            query_lower = query.lower()
            if any(term in query_lower for term in ['github', 'documentation', 'api', 'tutorial']):
                if provider.config.provider_id == 'brave_search':
                    score += 0.4  # Brave excellent for technical content
                elif provider.config.provider_id == 'google':
                    score += 0.2  # Google good general fallback
            
            # Performance-based scoring
            recent_latency = self.timeout_manager.get_timeout(provider.config.provider_id)
            if recent_latency < 1.0:
                score += 0.1  # Bonus for fast providers
            
            # Reliability scoring
            failures = self.provider_failures[provider.config.provider_id]
            if failures == 0:
                score += 0.1
            elif failures < 3:
                score += 0.05
            else:
                score -= 0.1
            
            provider_scores[provider] = score
        
        # Sort by score
        return sorted(providers, key=lambda p: provider_scores[p], reverse=True)
    
    async def _execute_optimized_search(
        self,
        query: str,
        providers: List[SearchProvider],
        max_results: int
    ) -> SearchResults:
        """
        Execute search with performance optimizations.
        
        Args:
            query: Search query
            providers: Selected providers
            max_results: Maximum results
            
        Returns:
            Optimized search results
        """
        # Create search options
        search_options = SearchOptions(
            query=query,
            max_results=max_results,
            timeout_seconds=2.0,  # Base timeout, will be adjusted
            safe_search=True
        )
        
        if len(providers) == 1:
            # Single provider - simple search
            provider = providers[0]
            search_options.timeout_seconds = self.timeout_manager.get_timeout(
                provider.config.provider_id
            )
            return await self._execute_single_provider_search(provider, search_options)
        
        elif len(providers) == 2 and self.enable_hedged_requests:
            # Two providers - hedged requests
            self.metrics['hedged_requests'] += 1
            return await self.hedged_manager.execute_hedged_search(
                providers[0], providers[1], search_options
            )
        
        else:
            # Multiple providers - parallel execution
            return await self._execute_parallel_search(providers, search_options)
    
    async def _execute_single_provider_search(
        self,
        provider: SearchProvider,
        options: SearchOptions
    ) -> SearchResults:
        """Execute search with single provider."""
        try:
            start_time = time.time()
            results = await provider.search(options)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Record performance
            self.timeout_manager.record_latency(provider.config.provider_id, execution_time)
            self.metrics['provider_calls'][provider.config.provider_id] += 1
            
            # Reset circuit breaker on success
            if not results.error:
                self._reset_circuit_breaker(provider.config.provider_id)
            else:
                self._record_failure(provider.config.provider_id)
            
            return results
            
        except Exception as e:
            self._record_failure(provider.config.provider_id)
            logger.error(f"Provider {provider.config.provider_id} failed: {e}")
            return SearchResults(
                results=[],
                execution_time_ms=0,
                provider=provider.config.provider_id,
                query=options.query,
                error=str(e)
            )
    
    async def _execute_parallel_search(
        self,
        providers: List[SearchProvider],
        options: SearchOptions
    ) -> SearchResults:
        """Execute search across multiple providers in parallel."""
        tasks = []
        
        for provider in providers:
            # Adjust timeout per provider
            provider_options = SearchOptions(
                query=options.query,
                max_results=options.max_results,
                timeout_seconds=self.timeout_manager.get_timeout(provider.config.provider_id),
                safe_search=options.safe_search
            )
            
            task = asyncio.create_task(
                self._execute_single_provider_search(provider, provider_options)
            )
            tasks.append((provider.config.provider_id, task))
        
        # Wait for all tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                timeout=5.0  # Overall timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Parallel search timed out")
            results = [SearchResults(
                results=[], execution_time_ms=0, provider="timeout", 
                query=options.query, error="timeout"
            )]
        
        # Combine results
        return self._combine_results(results, options.query)
    
    def _combine_results(self, results: List[SearchResults], query: str) -> SearchResults:
        """
        Combine results from multiple providers.
        
        Args:
            results: List of provider results
            query: Original query
            
        Returns:
            Combined and deduplicated results
        """
        all_results = []
        successful_providers = []
        total_execution_time = 0
        
        for result in results:
            if isinstance(result, Exception):
                continue
                
            if not result.error and result.results:
                all_results.extend(result.results)
                successful_providers.append(result.provider)
                total_execution_time = max(total_execution_time, result.execution_time_ms)
        
        # Deduplicate by URL
        seen_urls = set()
        deduplicated = []
        
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                deduplicated.append(result)
        
        # Sort by relevance (provider rank as proxy)
        deduplicated.sort(key=lambda r: r.provider_rank)
        
        return SearchResults(
            results=deduplicated[:20],  # Limit to top 20
            total_results=len(all_results),
            execution_time_ms=total_execution_time,
            provider=f"Combined({','.join(successful_providers)})",
            query=query,
            truncated=len(deduplicated) > 20,
            metadata={
                'provider_count': len(successful_providers),
                'deduplicated_from': len(all_results)
            }
        )
    
    def _generate_cache_key(
        self,
        query: str,
        technology_hint: Optional[str],
        max_results: int,
        provider_ids: Optional[List[str]]
    ) -> str:
        """Generate cache key for search parameters."""
        key_parts = [
            f"query:{query}",
            f"tech:{technology_hint or 'none'}",
            f"max:{max_results}",
            f"providers:{','.join(sorted(provider_ids or []))}"
        ]
        return self.cache_manager.compute_key(*key_parts)
    
    def _is_circuit_open(self, provider_id: str) -> bool:
        """Check if circuit breaker is open for provider."""
        if not self.provider_circuit_open[provider_id]:
            return False
        
        # Check if circuit timeout has passed
        if datetime.utcnow() - self.last_failure_time[provider_id] > timedelta(seconds=self.circuit_timeout):
            self._reset_circuit_breaker(provider_id)
            return False
        
        return True
    
    def _record_failure(self, provider_id: str) -> None:
        """Record provider failure for circuit breaker."""
        self.provider_failures[provider_id] += 1
        self.last_failure_time[provider_id] = datetime.utcnow()
        
        if self.provider_failures[provider_id] >= self.failure_threshold:
            self.provider_circuit_open[provider_id] = True
            self.metrics['circuit_breaks'] += 1
            logger.warning(f"Circuit breaker opened for provider: {provider_id}")
    
    def _reset_circuit_breaker(self, provider_id: str) -> None:
        """Reset circuit breaker for provider."""
        if self.provider_circuit_open[provider_id]:
            logger.info(f"Circuit breaker reset for provider: {provider_id}")
        
        self.provider_failures[provider_id] = 0
        self.provider_circuit_open[provider_id] = False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        cache_stats = self.cache_manager.get_stats()
        
        return {
            'search_metrics': dict(self.metrics),
            'cache_metrics': cache_stats,
            'provider_health': {
                provider_id: {
                    'failures': self.provider_failures[provider_id],
                    'circuit_open': self.provider_circuit_open[provider_id],
                    'timeout': self.timeout_manager.get_timeout(provider_id)
                }
                for provider_id in self.provider_failures.keys()
            }
        }