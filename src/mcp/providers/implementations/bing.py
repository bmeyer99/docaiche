"""
Bing Search Provider Implementation
====================================

Provider for Microsoft Bing Web Search API.
"""

from typing import Dict, Any, Optional
from datetime import datetime
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


class BingSearchProvider(SearchProvider):
    """
    Bing Web Search API provider implementation.
    
    Uses Microsoft's Bing Web Search API v7.
    Requires API key from Azure Cognitive Services.
    """
    
    BASE_URL = "https://api.bing.microsoft.com/v7.0/search"
    
    def __init__(self, config: ProviderConfig):
        """Initialize Bing provider with config."""
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _get_capabilities(self) -> ProviderCapabilities:
        """Get Bing Search capabilities."""
        return ProviderCapabilities(
            provider_type=ProviderType.BING,
            supports_date_filtering=True,
            supports_site_search=True,
            supports_safe_search=True,
            supports_pagination=True,
            supports_language_filter=True,
            supports_country_filter=True,
            max_results_per_request=50,
            rate_limit_requests_per_minute=1000,  # Depends on tier
            requires_api_key=True,
            result_types=[
                SearchResultType.WEB_PAGE,
                SearchResultType.DOCUMENTATION,
                SearchResultType.VIDEO,
                SearchResultType.BLOG_POST
            ],
            special_features=[
                "freshness_boost",
                "answer_cards",
                "computation",
                "entity_search"
            ],
            estimated_latency_ms=350,
            reliability_score=0.97
        )
    
    async def search(self, options: SearchOptions) -> SearchResults:
        """Execute search using Bing Web Search API."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.config.api_key,
            "Accept": "application/json"
        }
        
        params = {
            "q": options.query,
            "count": min(options.max_results, 50),
            "safeSearch": "Strict" if options.safe_search else "Off",
            "textFormat": "Raw",
            "responseFilter": "Webpages"
        }
        
        # Add optional parameters
        if options.language:
            params["mkt"] = f"{options.language}-{options.country or 'US'}"
        
        if options.date_range:
            # Bing freshness parameter
            freshness_map = {
                "day": "Day",
                "week": "Week", 
                "month": "Month"
            }
            if options.date_range in freshness_map:
                params["freshness"] = freshness_map[options.date_range]
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=options.timeout_seconds)
            ) as response:
                response.raise_for_status()
                data = await response.json()
            
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return self._parse_results(data, options.query, execution_time)
            
        except Exception as e:
            logger.error(f"Bing Search API error: {e}")
            return SearchResults(
                results=[],
                execution_time_ms=0,
                provider=self.__class__.__name__,
                query=options.query,
                error=str(e)
            )
    
    async def check_health(self) -> HealthCheck:
        """Check Bing Search API health."""
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
        """Validate Bing Search configuration."""
        if not self.config.api_key:
            logger.error("Bing API key not configured")
            return False
        
        try:
            health = await self.check_health()
            return health.status == HealthStatus.HEALTHY
        except Exception:
            return False
    
    def _parse_results(self, data: Dict[str, Any], query: str, execution_time: int) -> SearchResults:
        """Parse Bing API response to standard format."""
        results = []
        web_pages = data.get("webPages", {}).get("value", [])
        
        for i, item in enumerate(web_pages):
            result = SearchResult(
                title=item.get("name", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                content_type=SearchResultType.WEB_PAGE,
                provider_rank=i + 1,
                published_date=self._parse_date(item.get("dateLastCrawled")),
                language=item.get("language"),
                metadata={
                    "display_url": item.get("displayUrl"),
                    "is_family_friendly": item.get("isFamilyFriendly", True),
                    "deep_links": item.get("deepLinks", [])
                }
            )
            results.append(result)
        
        return SearchResults(
            results=results,
            total_results=data.get("webPages", {}).get("totalEstimatedMatches", len(results)),
            execution_time_ms=execution_time,
            provider=self.__class__.__name__,
            query=query,
            metadata={
                "altered_query": data.get("queryContext", {}).get("alteredQuery"),
                "spelling_suggestions": data.get("spellSuggestions")
            }
        )
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse Bing date format."""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None