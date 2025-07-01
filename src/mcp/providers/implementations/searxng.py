"""
SearXNG Search Provider Implementation
======================================

Provider for SearXNG metasearch engine.
"""

from typing import Dict, Any, Optional, List
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


class SearXNGSearchProvider(SearchProvider):
    """
    SearXNG metasearch engine provider implementation.
    
    SearXNG aggregates results from multiple search engines.
    Can use public instances or self-hosted instance.
    """
    
    # Default to a public instance, but should use self-hosted in production
    DEFAULT_INSTANCE = "https://search.nixnet.services"
    
    def __init__(self, config: ProviderConfig):
        """Initialize SearXNG provider with config."""
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.instance_url = config.base_url or self.DEFAULT_INSTANCE
    
    def _get_capabilities(self) -> ProviderCapabilities:
        """Get SearXNG capabilities."""
        return ProviderCapabilities(
            provider_type=ProviderType.SEARXNG,
            supports_date_filtering=True,
            supports_site_search=True,
            supports_safe_search=True,
            supports_pagination=True,
            supports_language_filter=True,
            supports_country_filter=False,
            max_results_per_request=100,
            rate_limit_requests_per_minute=60,  # Depends on instance
            requires_api_key=False,  # Usually no key needed
            result_types=[
                SearchResultType.WEB_PAGE,
                SearchResultType.DOCUMENTATION,
                SearchResultType.CODE_REPOSITORY,
                SearchResultType.FORUM,
                SearchResultType.BLOG_POST
            ],
            special_features=[
                "metasearch",
                "engine_selection",
                "category_search",
                "self_hostable",
                "privacy_focused",
                "open_source"
            ],
            estimated_latency_ms=800,  # Slower due to aggregation
            reliability_score=0.85  # Depends on instance
        )
    
    async def search(self, options: SearchOptions) -> SearchResults:
        """Execute search using SearXNG."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Build query parameters for SearXNG API
        params = {
            "q": options.query,
            "format": "json",
            "pageno": 1,
            "safesearch": 1 if options.safe_search else 0
        }
        
        # Add language
        if options.language:
            params["language"] = options.language
        
        # Add time range
        if options.date_range:
            time_range_map = {
                "day": "day",
                "week": "week",
                "month": "month",
                "year": "year"
            }
            if options.date_range in time_range_map:
                params["time_range"] = time_range_map[options.date_range]
        
        # Enable specific engines for technical search
        params["engines"] = "google,bing,duckduckgo,github,stackoverflow"
        
        # Add categories for documentation
        if "documentation" in options.query.lower() or "docs" in options.query.lower():
            params["categories"] = "it,science"
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.get(
                f"{self.instance_url}/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=options.timeout_seconds),
                headers={"User-Agent": "MCP Search Bot 1.0"}
            ) as response:
                response.raise_for_status()
                data = await response.json()
            
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return self._parse_results(data, options.query, execution_time)
            
        except Exception as e:
            logger.error(f"SearXNG search error: {e}")
            return SearchResults(
                results=[],
                execution_time_ms=0,
                provider=self.__class__.__name__,
                query=options.query,
                error=str(e)
            )
    
    async def check_health(self) -> HealthCheck:
        """Check SearXNG instance health."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            start_time = asyncio.get_event_loop().time()
            
            # Check instance config endpoint
            async with self.session.get(
                f"{self.instance_url}/config",
                timeout=aiohttp.ClientTimeout(total=3.0)
            ) as response:
                response.raise_for_status()
                config = await response.json()
            
            response_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "instance_url": self.instance_url,
                    "instance_version": config.get("version", "unknown"),
                    "engines_enabled": len(config.get("engines", []))
                }
            )
        except Exception as e:
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                details={"error": str(e), "instance": self.instance_url}
            )
    
    async def validate_config(self) -> bool:
        """Validate SearXNG configuration."""
        try:
            health = await self.check_health()
            return health.status == HealthStatus.HEALTHY
        except Exception:
            return False
    
    def _parse_results(self, data: Dict[str, Any], query: str, execution_time: int) -> SearchResults:
        """Parse SearXNG response to standard format."""
        results = []
        searx_results = data.get("results", [])
        
        for i, item in enumerate(searx_results[:50]):  # Limit results
            # Detect content type from engine and URL
            content_type = self._detect_content_type(item)
            
            result = SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                content_type=content_type,
                provider_rank=i + 1,
                metadata={
                    "engine": item.get("engine"),
                    "engines": item.get("engines", []),
                    "score": item.get("score", 1.0),
                    "category": item.get("category"),
                    "template": item.get("template")
                }
            )
            results.append(result)
        
        # Get engine statistics
        engines_used = set()
        for result in searx_results:
            engines_used.update(result.get("engines", []))
        
        return SearchResults(
            results=results,
            total_results=len(searx_results),
            execution_time_ms=execution_time,
            provider=self.__class__.__name__,
            query=query,
            metadata={
                "number_of_results": data.get("number_of_results", 0),
                "engines_used": list(engines_used),
                "suggestions": data.get("suggestions", []),
                "infoboxes": data.get("infoboxes", [])
            }
        )
    
    def _detect_content_type(self, item: Dict[str, Any]) -> SearchResultType:
        """Detect content type from SearXNG result."""
        url = item.get("url", "").lower()
        engine = item.get("engine", "").lower()
        
        if engine == "github" or "github.com" in url:
            return SearchResultType.CODE_REPOSITORY
        elif engine == "stackoverflow" or "stackoverflow.com" in url:
            return SearchResultType.FORUM
        elif any(doc in url for doc in ["docs.", "documentation", "/api/"]):
            return SearchResultType.DOCUMENTATION
        elif any(blog in url for blog in ["blog", "medium.com", "dev.to"]):
            return SearchResultType.BLOG_POST
        else:
            return SearchResultType.WEB_PAGE