"""
Brave Search Provider Implementation
====================================

Provider for Brave Search API with documentation focus.
"""

from typing import Dict, Any, List, Optional
import aiohttp
import asyncio
import logging
from datetime import datetime

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


class BraveSearchProvider(SearchProvider):
    """
    Brave Search API provider implementation.
    
    Supports web search with focus on technical documentation
    and code repositories. Requires API key from https://brave.com/search/api/
    """
    
    BASE_URL = "https://api.search.brave.com/res/v1"
    
    def __init__(self, config: ProviderConfig):
        """Initialize Brave provider with config."""
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _get_capabilities(self) -> ProviderCapabilities:
        """Get Brave Search capabilities."""
        return ProviderCapabilities(
            provider_type=ProviderType.BRAVE,
            supports_date_filtering=True,
            supports_site_search=True,
            supports_safe_search=True,
            supports_pagination=True,
            supports_language_filter=True,
            supports_country_filter=True,
            max_results_per_request=20,
            rate_limit_requests_per_minute=60,
            requires_api_key=True,
            result_types=[
                SearchResultType.WEB_PAGE,
                SearchResultType.DOCUMENTATION,
                SearchResultType.CODE_REPOSITORY,
                SearchResultType.BLOG_POST
            ],
            special_features=[
                "code_search",
                "discussions",
                "goggles",  # Custom ranking profiles
                "freshness"  # Recent results boost
            ],
            estimated_latency_ms=300,
            reliability_score=0.95
        )
    
    async def search(self, options: SearchOptions) -> SearchResults:
        """
        Execute search using Brave Search API.
        
        Args:
            options: Search parameters
            
        Returns:
            Standardized search results
        """
        # Generate trace ID for this search
        import uuid
        trace_id = f"brave-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"[{trace_id}] Starting Brave search for query: '{options.query}', max_results: {options.max_results}")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.debug(f"[{trace_id}] Created new aiohttp session")
        
        # Build query parameters
        params = self._build_search_params(options)
        
        # Add API key to headers
        headers = {
            "X-Subscription-Token": self.config.api_key,
            "Accept": "application/json"
        }
        headers.update(self.config.custom_headers)
        
        logger.debug(f"[{trace_id}] Request params: {params}")
        logger.debug(f"[{trace_id}] Request URL: {self.BASE_URL}/web/search")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.get(
                f"{self.BASE_URL}/web/search",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=options.timeout_seconds)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            logger.info(f"[{trace_id}] Brave API response received in {execution_time}ms, status: {response.status}")
            logger.debug(f"[{trace_id}] Response contains {len(data.get('web', {}).get('results', []))} web results")
            
            # Parse and standardize results
            results = self._parse_results(data, options.query, execution_time)
            
            logger.info(f"[{trace_id}] Search completed: {len(results.results)} results parsed, execution_time: {results.execution_time_ms}ms")
            
            return results
            
        except aiohttp.ClientError as e:
            logger.error(f"[{trace_id}] Brave Search API error: {e}")
            return SearchResults(
                results=[],
                execution_time_ms=0,
                provider=self.__class__.__name__,
                query=options.query,
                error=str(e)
            )
    
    async def check_health(self) -> HealthCheck:
        """
        Check Brave Search API health.
        
        Returns:
            Health check results
        """
        try:
            # Make a minimal search request
            test_options = SearchOptions(
                query="test",
                max_results=1,
                timeout_seconds=3.0
            )
            
            start_time = asyncio.get_event_loop().time()
            results = await self.search(test_options)
            response_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            if results.error:
                return HealthCheck(
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    details={"error": results.error}
                )
            
            return HealthCheck(
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_success=datetime.utcnow(),
                details={
                    "api_endpoint": self.BASE_URL,
                    "test_query_results": len(results.results)
                }
            )
            
        except Exception as e:
            logger.error(f"Brave health check failed: {e}")
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                last_failure=datetime.utcnow(),
                details={"error": str(e)}
            )
    
    async def validate_config(self) -> bool:
        """
        Validate Brave Search configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.config.api_key:
            logger.error("Brave Search API key not configured")
            return False
        
        # Test API key with minimal request
        try:
            health = await self.check_health()
            return health.status == HealthStatus.HEALTHY
        except Exception:
            return False
    
    def _build_search_params(self, options: SearchOptions) -> Dict[str, Any]:
        """
        Build query parameters for Brave API.
        
        Args:
            options: Search options
            
        Returns:
            Query parameters dict
        """
        params = {
            "q": options.query,
            "count": min(options.max_results, 20),  # Brave max is 20
            "safesearch": "strict" if options.safe_search else "off"
        }
        
        # Add optional parameters
        if options.language:
            params["search_lang"] = options.language
        
        if options.country:
            params["country"] = options.country
        
        if options.date_range:
            # Convert to Brave freshness parameter
            freshness_map = {
                "day": "d",
                "week": "w",
                "month": "m",
                "year": "y"
            }
            if options.date_range in freshness_map:
                params["freshness"] = freshness_map[options.date_range]
        
        if options.site_search:
            # Add site restriction to query
            params["q"] = f"site:{options.site_search} {options.query}"
        
        # Add goggles for technical search
        if "github.com" in options.query or "documentation" in options.query:
            params["goggles_id"] = "tech_docs"  # Custom ranking for tech docs
        
        # Merge custom parameters
        params.update(options.custom_params)
        
        return params
    
    def _parse_results(
        self,
        data: Dict[str, Any],
        query: str,
        execution_time: int
    ) -> SearchResults:
        """
        Parse Brave API response to standard format.
        
        Args:
            data: Brave API response
            query: Original query
            execution_time: Request duration
            
        Returns:
            Standardized results
        """
        results = []
        
        # Parse web results
        web_results = data.get("web", {}).get("results", [])
        for i, item in enumerate(web_results):
            # Determine content type
            content_type = self._detect_content_type(item)
            
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(item.get("url", ""))
            source_domain = parsed_url.netloc if parsed_url.netloc else ""
            
            result = SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
                source_domain=source_domain,
                content_type=content_type,
                provider_rank=i + 1,
                published_date=self._parse_date(item.get("published_date")),
                language=item.get("language"),
                metadata={
                    "favicon": item.get("favicon"),
                    "thumbnail": item.get("thumbnail"),
                    "age": item.get("age"),
                    "extra_snippets": item.get("extra_snippets", [])
                }
            )
            results.append(result)
        
        # Also parse discussions if available
        discussions = data.get("discussions", {}).get("results", [])
        for item in discussions[:5]:  # Limit discussions
            result = SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
                content_type=SearchResultType.FORUM,
                provider_rank=len(results) + 1,
                published_date=self._parse_date(item.get("published_date")),
                metadata={
                    "forum_name": item.get("forum_name"),
                    "type": "discussion"
                }
            )
            results.append(result)
        
        return SearchResults(
            results=results,
            total_results=data.get("total", len(results)),
            execution_time_ms=execution_time,
            provider=self.__class__.__name__,
            query=query,
            truncated=len(results) < data.get("total", 0),
            metadata={
                "query_info": data.get("query", {}),
                "mixed_results": data.get("mixed", {})
            }
        )
    
    def _detect_content_type(self, item: Dict[str, Any]) -> SearchResultType:
        """Detect content type from result data."""
        url = item.get("url", "").lower()
        title = item.get("title", "").lower()
        
        if "github.com" in url or "gitlab.com" in url:
            return SearchResultType.CODE_REPOSITORY
        elif any(doc in url for doc in ["docs.", "documentation", "/api/", "reference"]):
            return SearchResultType.DOCUMENTATION
        elif any(blog in url for blog in ["blog", "medium.com", "dev.to"]):
            return SearchResultType.BLOG_POST
        elif any(forum in url for forum in ["stackoverflow", "reddit", "discourse"]):
            return SearchResultType.FORUM
        elif "tutorial" in title or "how to" in title:
            return SearchResultType.TUTORIAL
        else:
            return SearchResultType.WEB_PAGE
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None
        
        try:
            # Brave uses ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            self.session = None