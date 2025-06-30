"""
Base Adapter for MCP to FastAPI Integration
===========================================

Provides common functionality for all MCP adapters including error
handling, authentication, rate limiting, and protocol translation.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, TypeVar, Generic, Type
from abc import ABC, abstractmethod
from urllib.parse import urljoin

# Try to import aiohttp, fall back to mock if not available
try:
    import aiohttp
except ImportError:
    try:
        from .mock_http import aiohttp
    except ImportError:
        # Handle direct execution without package context
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mock_http import aiohttp
    logger = logging.getLogger(__name__)
    logger.warning("aiohttp not available, using mock HTTP client")

try:
    from ..exceptions import ServiceError, AuthenticationError, RateLimitError
    from ..schemas import MCPRequest, MCPResponse
except ImportError:
    # Handle direct execution - create minimal exception classes
    class ServiceError(Exception): pass
    class AuthenticationError(Exception): pass
    class RateLimitError(Exception): pass
    # Schemas will be injected by the test

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseAdapter(ABC, Generic[T]):
    """
    Abstract base adapter for MCP to FastAPI integration.
    
    Provides common functionality for protocol translation, error handling,
    authentication, and HTTP communication with DocaiChe FastAPI endpoints.
    """
    
    def __init__(
        self,
        base_url: str,
        api_version: str = "v1",
        timeout: int = 30,
        max_retries: int = 3,
        auth_token: Optional[str] = None
    ):
        """
        Initialize base adapter.
        
        Args:
            base_url: Base URL for the FastAPI service
            api_version: API version (default: v1)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            auth_token: Optional authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.api_version = api_version
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.auth_token = auth_token
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting tracking
        self._request_times: list = []
        self._rate_limit_window = 60  # seconds
        self._rate_limit_max = 60  # requests per window
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists with proper configuration."""
        if not self._session or self._session.closed:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'MCP-Adapter/1.0'
            }
            
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            # Add correlation ID support
            headers['X-Request-ID'] = f'mcp-{asyncio.get_event_loop().time()}'
            
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300
            )
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=self.timeout,
                connector=connector,
                raise_for_status=False
            )
        
        return self._session
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        current_time = asyncio.get_event_loop().time()
        
        # Clean old request times
        self._request_times = [
            t for t in self._request_times 
            if current_time - t < self._rate_limit_window
        ]
        
        # Check if we're at the limit
        if len(self._request_times) >= self._rate_limit_max:
            oldest_request = min(self._request_times)
            retry_after = int(self._rate_limit_window - (current_time - oldest_request))
            
            raise RateLimitError(
                message="Rate limit exceeded for FastAPI endpoint",
                retry_after=retry_after
            )
        
        # Record this request
        self._request_times.append(current_time)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters
            retry_count: Current retry attempt
            
        Returns:
            Response data as dictionary
            
        Raises:
            ServiceError: For service-related errors
            AuthenticationError: For authentication failures
            RateLimitError: For rate limit violations
        """
        # Check rate limit
        await self._check_rate_limit()
        
        session = await self._ensure_session()
        url = urljoin(self.base_url, f"/api/{self.api_version}{endpoint}")
        
        try:
            async with session.request(
                method,
                url,
                json=data,
                params=params
            ) as response:
                # Handle different response codes
                if response.status == 200:
                    return await response.json()
                
                elif response.status == 401:
                    raise AuthenticationError(
                        message="Authentication failed with FastAPI endpoint",
                        details={"endpoint": endpoint}
                    )
                
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', '60'))
                    raise RateLimitError(
                        message="FastAPI rate limit exceeded",
                        retry_after=retry_after
                    )
                
                elif response.status >= 500:
                    # Server error - retry if possible
                    if retry_count < self.max_retries:
                        wait_time = 2 ** retry_count  # Exponential backoff
                        logger.warning(
                            f"Server error {response.status}, retrying in {wait_time}s",
                            extra={"endpoint": endpoint, "attempt": retry_count + 1}
                        )
                        await asyncio.sleep(wait_time)
                        return await self._make_request(
                            method, endpoint, data, params, retry_count + 1
                        )
                    
                    error_text = await response.text()
                    raise ServiceError(
                        message=f"FastAPI server error: {response.status}",
                        service_name="FastAPI",
                        details={
                            "status": response.status,
                            "error": error_text,
                            "endpoint": endpoint
                        }
                    )
                
                else:
                    # Client error
                    error_data = {}
                    try:
                        error_data = await response.json()
                    except:
                        error_data = {"error": await response.text()}
                    
                    raise ServiceError(
                        message=f"FastAPI request failed: {response.status}",
                        service_name="FastAPI",
                        details={
                            "status": response.status,
                            "endpoint": endpoint,
                            "error": error_data
                        }
                    )
        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            # Network/connection errors - retry if possible
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(
                    f"Connection error, retrying in {wait_time}s: {str(e)}",
                    extra={"endpoint": endpoint, "attempt": retry_count + 1}
                )
                await asyncio.sleep(wait_time)
                return await self._make_request(
                    method, endpoint, data, params, retry_count + 1
                )
            
            raise ServiceError(
                message=f"Failed to connect to FastAPI: {str(e)}",
                service_name="FastAPI",
                details={"endpoint": endpoint, "error": str(e)}
            )
    
    @abstractmethod
    async def adapt_request(self, mcp_request: MCPRequest) -> Dict[str, Any]:
        """
        Adapt MCP request to FastAPI format.
        
        Must be implemented by concrete adapters to handle specific
        request transformations.
        
        Args:
            mcp_request: Incoming MCP request
            
        Returns:
            Adapted request data for FastAPI
        """
        pass
    
    @abstractmethod
    async def adapt_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt FastAPI response to MCP format.
        
        Must be implemented by concrete adapters to handle specific
        response transformations.
        
        Args:
            api_response: Response from FastAPI
            
        Returns:
            Adapted response data for MCP
        """
        pass
    
    async def execute(
        self,
        mcp_request: MCPRequest,
        method: str,
        endpoint: str
    ) -> MCPResponse:
        """
        Execute adapted request against FastAPI endpoint.
        
        Handles the complete flow of adapting MCP request, making HTTP
        call, and adapting response back to MCP format.
        
        Args:
            mcp_request: Incoming MCP request
            method: HTTP method to use
            endpoint: FastAPI endpoint to call
            
        Returns:
            MCP response with adapted data
        """
        try:
            # Adapt request
            adapted_request = await self.adapt_request(mcp_request)
            
            # Determine if data goes in body or params
            data = None
            params = None
            if method.upper() in ['GET', 'DELETE']:
                params = adapted_request
            else:
                data = adapted_request
            
            # Make API call
            api_response = await self._make_request(
                method=method,
                endpoint=endpoint,
                data=data,
                params=params
            )
            
            # Adapt response
            adapted_response = await self.adapt_response(api_response)
            
            # Create MCP response
            return MCPResponse(
                id=mcp_request.id,
                result=adapted_response
            )
        
        except Exception as e:
            logger.error(
                f"Adapter execution failed: {str(e)}",
                extra={
                    "adapter": self.__class__.__name__,
                    "endpoint": endpoint,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise
    
    async def close(self) -> None:
        """Close HTTP session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        asyncio.create_task(self.close())
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()


# Base adapter complete with:
# ✓ HTTP session management
# ✓ Rate limiting enforcement
# ✓ Retry logic with exponential backoff
# ✓ Comprehensive error handling
# ✓ Authentication support
# ✓ Request/response adaptation framework
# ✓ Context manager support
# ✓ Correlation ID tracking