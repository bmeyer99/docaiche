"""
Base Search Provider Interface
===============================

Abstract base class for all external search providers with
built-in circuit breaker, rate limiting, and monitoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import time
import logging
from datetime import datetime, timedelta
from enum import Enum

from .models import (
    SearchOptions,
    SearchResults,
    ProviderCapabilities,
    HealthCheck,
    HealthStatus,
    RateLimitInfo,
    CostInfo,
    ProviderConfig
)

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class SearchProvider(ABC):
    """
    Abstract base class for external search providers.
    
    Provides common functionality for circuit breakers, rate limiting,
    health monitoring, and result standardization. All providers must
    implement the abstract methods.
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.capabilities = self._get_capabilities()
        
        # Circuit breaker state
        self._circuit_state = CircuitState.CLOSED
        self._circuit_failures = 0
        self._circuit_last_failure = None
        self._circuit_half_open_success = 0
        
        # Rate limiting
        self._rate_limit_info = RateLimitInfo()
        
        # Cost tracking
        self._cost_info = CostInfo()
        
        # Health monitoring
        self._last_health_check = None
        self._consecutive_failures = 0
        self._total_requests = 0
        self._failed_requests = 0
        self._total_latency_ms = 0
        
        logger.info(f"Initialized {self.__class__.__name__} provider")
    
    @abstractmethod
    async def search(self, options: SearchOptions) -> SearchResults:
        """
        Execute search with given options.
        
        Must be implemented by each provider to perform actual search.
        Results should be standardized to SearchResults format.
        
        Args:
            options: Search parameters
            
        Returns:
            Standardized search results
            
        Raises:
            ProviderError: On search failure
        """
        pass
    
    @abstractmethod
    def _get_capabilities(self) -> ProviderCapabilities:
        """
        Get provider capabilities.
        
        Must return accurate capabilities for this provider.
        
        Returns:
            Provider capabilities
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> HealthCheck:
        """
        Perform health check on provider.
        
        Should make a lightweight API call to verify service availability.
        
        Returns:
            Health check results
        """
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """
        Validate provider configuration.
        
        Should check API keys, endpoints, and other settings.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: With details about invalid config
        """
        pass
    
    # Common functionality provided by base class
    
    async def search_with_circuit_breaker(
        self, 
        options: SearchOptions
    ) -> SearchResults:
        """
        Execute search with circuit breaker protection.
        
        Wraps the search method with circuit breaker logic.
        
        Args:
            options: Search parameters
            
        Returns:
            Search results
            
        Raises:
            ProviderError: If circuit is open or search fails
        """
        # Check circuit breaker
        if not self._circuit_allows_request():
            from ..core.exceptions import ProviderError
            raise ProviderError(
                provider_name=self.__class__.__name__,
                operation="search",
                provider_error="Circuit breaker is open",
                fallback_providers=[]
            )
        
        start_time = time.time()
        try:
            # Check rate limits
            if not await self._check_rate_limit():
                from ..core.exceptions import ProviderError
                raise ProviderError(
                    provider_name=self.__class__.__name__,
                    operation="search",
                    provider_error="Rate limit exceeded",
                    fallback_providers=[]
                )
            
            # Execute search
            results = await self.search(options)
            
            # Record success
            self._record_success(int((time.time() - start_time) * 1000))
            
            return results
            
        except Exception as e:
            # Record failure
            self._record_failure()
            raise
    
    def _circuit_allows_request(self) -> bool:
        """
        Check if circuit breaker allows request.
        
        Returns:
            True if request should proceed
        """
        if self._circuit_state == CircuitState.CLOSED:
            return True
        
        if self._circuit_state == CircuitState.OPEN:
            # Check if enough time has passed to try again
            if self._circuit_last_failure:
                elapsed = (datetime.utcnow() - self._circuit_last_failure).seconds
                if elapsed >= self.config.circuit_breaker_timeout:
                    logger.info(f"Circuit breaker entering half-open state")
                    self._circuit_state = CircuitState.HALF_OPEN
                    self._circuit_half_open_success = 0
                    return True
            return False
        
        # HALF_OPEN - allow limited requests
        return True
    
    def _record_success(self, latency_ms: int):
        """Record successful request."""
        self._total_requests += 1
        self._total_latency_ms += latency_ms
        
        if self._circuit_state == CircuitState.HALF_OPEN:
            self._circuit_half_open_success += 1
            if self._circuit_half_open_success >= 3:
                logger.info(f"Circuit breaker closing after successful recovery")
                self._circuit_state = CircuitState.CLOSED
                self._circuit_failures = 0
        elif self._circuit_state == CircuitState.CLOSED:
            self._circuit_failures = 0
            self._consecutive_failures = 0
    
    def _record_failure(self):
        """Record failed request."""
        self._total_requests += 1
        self._failed_requests += 1
        self._consecutive_failures += 1
        self._circuit_failures += 1
        self._circuit_last_failure = datetime.utcnow()
        
        if self._circuit_state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker reopening after half-open failure")
            self._circuit_state = CircuitState.OPEN
        elif (self._circuit_state == CircuitState.CLOSED and 
              self._circuit_failures >= self.config.circuit_breaker_threshold):
            logger.error(f"Circuit breaker opening after {self._circuit_failures} failures")
            self._circuit_state = CircuitState.OPEN
    
    async def _check_rate_limit(self) -> bool:
        """
        Check if request is within rate limits.
        
        Returns:
            True if request can proceed
        """
        if not self.capabilities.rate_limit_requests_per_minute:
            return True
        
        now = datetime.utcnow()
        window_elapsed = (now - self._rate_limit_info.window_start).seconds
        
        # Reset window if needed
        if window_elapsed >= self._rate_limit_info.window_duration_seconds:
            self._rate_limit_info = RateLimitInfo(
                requests_limit=self.capabilities.rate_limit_requests_per_minute
            )
        
        # Check limit
        if self._rate_limit_info.remaining_requests() == 0:
            self._rate_limit_info.is_limited = True
            self._rate_limit_info.retry_after = self._rate_limit_info.reset_time()
            return False
        
        # Update count
        self._rate_limit_info.requests_made += 1
        return True
    
    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        return self.capabilities
    
    def get_rate_limits(self) -> RateLimitInfo:
        """Get current rate limit information."""
        return self._rate_limit_info
    
    def get_cost_info(self) -> CostInfo:
        """Get usage and cost tracking data."""
        return self._cost_info
    
    async def update_cost_info(self, requests: int = 1, cost: float = 0.0):
        """
        Update cost tracking information.
        
        Args:
            requests: Number of requests to add
            cost: Cost to add
        """
        self._cost_info.requests_this_month += requests
        self._cost_info.total_cost_this_month += cost
    
    def get_health_status(self) -> HealthCheck:
        """
        Get current health status without making API call.
        
        Returns:
            Current health status based on recent activity
        """
        # Calculate error rate
        error_rate = 0.0
        if self._total_requests > 0:
            error_rate = (self._failed_requests / self._total_requests) * 100
        
        # Determine status
        status = HealthStatus.HEALTHY
        if self._circuit_state == CircuitState.OPEN:
            status = HealthStatus.UNHEALTHY
        elif self._circuit_state == CircuitState.HALF_OPEN:
            status = HealthStatus.DEGRADED
        elif error_rate > 25:
            status = HealthStatus.DEGRADED
        
        # Calculate average latency
        avg_latency = None
        if self._total_requests > self._failed_requests:
            successful_requests = self._total_requests - self._failed_requests
            avg_latency = int(self._total_latency_ms / successful_requests)
        
        return HealthCheck(
            status=status,
            response_time_ms=avg_latency,
            consecutive_failures=self._consecutive_failures,
            error_rate_percent=error_rate,
            circuit_breaker_state=self._circuit_state.value,
            rate_limit_status=self._rate_limit_info,
            details={
                "total_requests": self._total_requests,
                "failed_requests": self._failed_requests
            }
        )
    
    def _standardize_results(
        self,
        raw_results: List[Dict[str, Any]],
        query: str,
        execution_time_ms: int
    ) -> SearchResults:
        """
        Standardize raw results to common format.
        
        Helper method for providers to use.
        
        Args:
            raw_results: Provider-specific results
            query: Original query
            execution_time_ms: Execution time
            
        Returns:
            Standardized SearchResults
        """
        from .models import SearchResult, SearchResultType
        
        results = []
        for i, raw in enumerate(raw_results):
            # Providers should override this mapping
            result = SearchResult(
                title=raw.get("title", ""),
                url=raw.get("url", ""),
                snippet=raw.get("snippet", ""),
                content_type=SearchResultType.WEB_PAGE,
                provider_rank=i + 1,
                metadata=raw
            )
            results.append(result)
        
        return SearchResults(
            results=results,
            total_results=len(results),
            execution_time_ms=execution_time_ms,
            provider=self.__class__.__name__,
            query=query
        )
    
    async def warm_up(self) -> bool:
        """
        Warm up provider connection.
        
        Makes a test query to establish connection and verify working state.
        
        Returns:
            True if warm-up successful
        """
        try:
            logger.info(f"Warming up {self.__class__.__name__}")
            test_options = SearchOptions(
                query="test",
                max_results=1,
                timeout_seconds=2.0
            )
            await self.search_with_circuit_breaker(test_options)
            return True
        except Exception as e:
            logger.warning(f"Warm-up failed for {self.__class__.__name__}: {e}")
            return False