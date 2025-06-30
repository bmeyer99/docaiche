"""
HTTP-based Service Implementations
==================================

Provides HTTP client implementations for all MCP services that
integrate with the existing DocaiChe API endpoints.

These implementations bridge the MCP server with the existing
DocaiChe FastAPI backend services.
"""

import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from .service_registry import (
    SearchService, IngestionService, DocumentationService,
    CollectionsService, HealthService, FeedbackService,
    MetricsCollector, AnalyticsEngine
)
from ..exceptions import ServiceError

logger = logging.getLogger(__name__)


class HTTPServiceBase:
    """Base class for HTTP service implementations."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize HTTP service.
        
        Args:
            base_url: Base URL for the service
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists."""
        if not self._session or self._session.closed:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=self.timeout
            )
        return self._session
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data
            
        Raises:
            ServiceError: If request fails
        """
        session = await self._ensure_session()
        url = urljoin(self.base_url, endpoint)
        
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    error_data = await response.text()
                    raise ServiceError(
                        message=f"HTTP {response.status}: {error_data}",
                        error_code=f"HTTP_{response.status}",
                        service_name=self.__class__.__name__
                    )
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            raise ServiceError(
                message=f"HTTP client error: {str(e)}",
                error_code="HTTP_CLIENT_ERROR",
                service_name=self.__class__.__name__
            )
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


class HTTPSearchService(HTTPServiceBase, SearchService):
    """HTTP-based search service implementation."""
    
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute search query."""
        return await self._request(
            'POST',
            '/api/v1/search',
            json={
                'query': query,
                'filters': kwargs.get('filters', {}),
                'limit': kwargs.get('limit', 10),
                'offset': kwargs.get('offset', 0)
            }
        )


class HTTPIngestionService(HTTPServiceBase, IngestionService):
    """HTTP-based ingestion service implementation."""
    
    async def ingest(self, content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Ingest content."""
        return await self._request(
            'POST',
            '/api/v1/ingest',
            json={
                'content': content,
                'metadata': kwargs.get('metadata', {}),
                'source': kwargs.get('source', 'mcp')
            }
        )


class HTTPDocumentationService(HTTPServiceBase, DocumentationService):
    """HTTP-based documentation service implementation."""
    
    async def get_documentation(self, doc_id: str, **kwargs) -> Dict[str, Any]:
        """Get documentation by ID."""
        return await self._request(
            'GET',
            f'/api/v1/docs/{doc_id}'
        )
    
    async def list_documentation(self, **kwargs) -> Dict[str, Any]:
        """List available documentation."""
        return await self._request(
            'GET',
            '/api/v1/docs',
            params=kwargs
        )


class HTTPCollectionsService(HTTPServiceBase, CollectionsService):
    """HTTP-based collections service implementation."""
    
    async def list_collections(self, **kwargs) -> Dict[str, Any]:
        """List available collections."""
        return await self._request(
            'GET',
            '/api/v1/collections',
            params=kwargs
        )
    
    async def get_collection(self, collection_id: str) -> Dict[str, Any]:
        """Get collection details."""
        return await self._request(
            'GET',
            f'/api/v1/collections/{collection_id}'
        )


class HTTPHealthService(HTTPServiceBase, HealthService):
    """HTTP-based health check service implementation."""
    
    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            return await self._request('GET', '/api/v1/health')
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }


class HTTPFeedbackService(HTTPServiceBase, FeedbackService):
    """HTTP-based feedback service implementation."""
    
    async def submit_feedback(self, feedback: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Submit feedback."""
        return await self._request(
            'POST',
            '/api/v1/feedback',
            json={
                'feedback': feedback,
                'user_id': kwargs.get('user_id'),
                'session_id': kwargs.get('session_id'),
                'metadata': kwargs.get('metadata', {})
            }
        )


class HTTPMetricsCollector(HTTPServiceBase, MetricsCollector):
    """HTTP-based metrics collector implementation."""
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect system metrics."""
        return await self._request('GET', '/api/v1/metrics')


class HTTPAnalyticsEngine(HTTPServiceBase, AnalyticsEngine):
    """HTTP-based analytics engine implementation."""
    
    async def track_event(self, event: Dict[str, Any]) -> None:
        """Track analytics event."""
        await self._request(
            'POST',
            '/api/v1/analytics/events',
            json=event
        )


def create_http_services(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create HTTP service implementations from configuration.
    
    Args:
        config: Service configuration
        
    Returns:
        Dictionary of service instances
    """
    services = {}
    
    # Base configuration
    base_url = config.get('docaiche_api_url', 'http://localhost:8000')
    api_key = config.get('docaiche_api_key')
    timeout = config.get('docaiche_api_timeout', 30)
    
    # Create service instances
    services['search'] = HTTPSearchService(base_url, api_key, timeout)
    services['ingestion'] = HTTPIngestionService(base_url, api_key, timeout)
    services['documentation'] = HTTPDocumentationService(base_url, api_key, timeout)
    services['collections'] = HTTPCollectionsService(base_url, api_key, timeout)
    services['health'] = HTTPHealthService(base_url, api_key, timeout)
    services['feedback'] = HTTPFeedbackService(base_url, api_key, timeout)
    services['metrics'] = HTTPMetricsCollector(base_url, api_key, timeout)
    services['analytics'] = HTTPAnalyticsEngine(base_url, api_key, timeout)
    
    logger.info(
        "HTTP services created",
        extra={
            "base_url": base_url,
            "services": list(services.keys())
        }
    )
    
    return services