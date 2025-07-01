"""
Google Custom Search Provider Implementation
============================================

Provider for Google Custom Search API.
"""

from typing import Dict, Any, Optional
import aiohttp
import asyncio
import logging

from ..base import SearchProvider
from ..models import (
    SearchOptions,
    SearchResults,
    SearchResult,
    SearchResultType,
    ProviderCapabilities,
    HealthCheck,
    HealthStatus,
    ProviderConfig,
    ProviderType
)

logger = logging.getLogger(__name__)


class GoogleSearchProvider(SearchProvider):
    """
    Google Custom Search API provider implementation.
    
    Uses Google's Custom Search JSON API for web search.
    Requires API key and Search Engine ID from Google Cloud Console.
    """
    
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self, config: ProviderConfig):
        """Initialize Google provider with config."""
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        # Extract search engine ID from config
        self.search_engine_id = config.custom_headers.get("cx", "")
    
    def _get_capabilities(self) -> ProviderCapabilities:
        """Get Google Search capabilities."""
        return ProviderCapabilities(
            provider_type=ProviderType.GOOGLE,
            supports_date_filtering=True,
            supports_site_search=True,
            supports_safe_search=True,
            supports_pagination=True,
            supports_language_filter=True,
            supports_country_filter=True,
            max_results_per_request=10,  # Google limit
            rate_limit_requests_per_minute=100,  # Default quota
            requires_api_key=True,
            result_types=[
                SearchResultType.WEB_PAGE,
                SearchResultType.DOCUMENTATION,
                SearchResultType.BLOG_POST
            ],
            special_features=[
                "custom_search_engine",
                "image_search",
                "file_type_filter",
                "link_search"
            ],
            estimated_latency_ms=400,
            reliability_score=0.98
        )
    
    async def search(self, options: SearchOptions) -> SearchResults:
        """Execute search using Google Custom Search API."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        params = {
            "key": self.config.api_key,
            "cx": self.search_engine_id,
            "q": options.query,
            "num": min(options.max_results, 10),
            "safe": "active" if options.safe_search else "off"
        }
        
        # Add optional parameters
        if options.language:
            params["lr"] = f"lang_{options.language}"
        
        if options.date_range:
            params["dateRestrict"] = options.date_range[0] + "1"  # e.g., "d1", "w1"
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.get(
                self.BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=options.timeout_seconds)
            ) as response:
                response.raise_for_status()
                data = await response.json()
            
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return self._parse_results(data, options.query, execution_time)
            
        except Exception as e:
            logger.error(f"Google Search API error: {e}")
            return SearchResults(
                results=[],
                execution_time_ms=0,
                provider=self.__class__.__name__,
                query=options.query,
                error=str(e)
            )
    
    async def check_health(self) -> HealthCheck:
        """Check Google Search API health."""
        try:
            test_options = SearchOptions(query="test", max_results=1, timeout_seconds=3.0)
            start_time = asyncio.get_event_loop().time()
            results = await self.search(test_options)
            response_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            status = HealthStatus.HEALTHY if not results.error else HealthStatus.UNHEALTHY
            
            return HealthCheck(
                status=status,
                response_time_ms=response_time,
                details={"api_endpoint": self.BASE_URL}
            )
        except Exception as e:
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                details={"error": str(e)}
            )
    
    async def validate_config(self) -> bool:
        """Validate Google Search configuration."""
        if not self.config.api_key or not self.search_engine_id:
            logger.error("Google API key or Search Engine ID not configured")
            return False
        
        try:
            health = await self.check_health()
            return health.status == HealthStatus.HEALTHY
        except Exception:
            return False
    
    def _parse_results(self, data: Dict[str, Any], query: str, execution_time: int) -> SearchResults:
        """Parse Google API response to standard format."""
        results = []
        items = data.get("items", [])
        
        for i, item in enumerate(items):
            result = SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                content_type=SearchResultType.WEB_PAGE,
                provider_rank=i + 1,
                metadata={
                    "display_link": item.get("displayLink"),
                    "mime_type": item.get("mime"),
                    "file_format": item.get("fileFormat")
                }
            )
            results.append(result)
        
        return SearchResults(
            results=results,
            total_results=int(data.get("searchInformation", {}).get("totalResults", 0)),
            execution_time_ms=execution_time,
            provider=self.__class__.__name__,
            query=query,
            metadata={"search_time": data.get("searchInformation", {}).get("searchTime")}
        )