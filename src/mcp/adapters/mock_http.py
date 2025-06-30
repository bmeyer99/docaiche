"""
Mock HTTP Client for MCP Adapters
=================================

Provides a mock HTTP client implementation to replace aiohttp
dependency for environments where it's not available.
"""

import asyncio
import json
from typing import Dict, Any, Optional, Union
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class MockResponse:
    """Mock HTTP response."""
    
    def __init__(self, status: int = 200, data: Any = None, headers: Dict[str, str] = None):
        self.status = status
        self._data = data or {}
        self.headers = headers or {}
    
    async def json(self) -> Dict[str, Any]:
        """Return JSON data."""
        if isinstance(self._data, str):
            return json.loads(self._data)
        return self._data
    
    async def text(self) -> str:
        """Return text data."""
        if isinstance(self._data, dict):
            return json.dumps(self._data)
        return str(self._data)


class MockClientTimeout:
    """Mock client timeout configuration."""
    
    def __init__(self, total: int = 30):
        self.total = total


class MockTCPConnector:
    """Mock TCP connector."""
    
    def __init__(self, limit: int = 100, limit_per_host: int = 30, ttl_dns_cache: int = 300):
        self.limit = limit
        self.limit_per_host = limit_per_host
        self.ttl_dns_cache = ttl_dns_cache


class MockClientSession:
    """Mock HTTP client session."""
    
    def __init__(self, headers: Dict[str, str] = None, timeout: MockClientTimeout = None, 
                 connector: MockTCPConnector = None, raise_for_status: bool = False):
        self.headers = headers or {}
        self.timeout = timeout or MockClientTimeout()
        self.connector = connector
        self.raise_for_status = raise_for_status
        self.closed = False
        self._responses = {}  # URL to response mapping for testing
    
    def set_response(self, url: str, response: MockResponse):
        """Set a mock response for a specific URL."""
        self._responses[url] = response
    
    def set_default_response(self, response: MockResponse):
        """Set default response for all URLs."""
        self._responses['*'] = response
    
    @asynccontextmanager
    async def request(self, method: str, url: str, json: Any = None, 
                     params: Dict[str, Any] = None, **kwargs):
        """Mock HTTP request."""
        await asyncio.sleep(0.01)  # Simulate network delay
        
        # Get response for URL or use default
        response = self._responses.get(url, self._responses.get('*', MockResponse()))
        
        # Log the request for debugging
        logger.debug(f"Mock {method} request to {url}", extra={
            "params": params,
            "json": json
        })
        
        yield response
    
    async def close(self):
        """Close the session."""
        self.closed = True


# Mock the aiohttp module structure
class MockAiohttp:
    """Mock aiohttp module."""
    
    ClientSession = MockClientSession
    ClientTimeout = MockClientTimeout
    TCPConnector = MockTCPConnector
    
    class ClientError(Exception):
        """Mock client error."""
        pass


# Create module-level mock
aiohttp = MockAiohttp()


def create_mock_session(responses: Dict[str, MockResponse] = None) -> MockClientSession:
    """
    Create a mock session with predefined responses.
    
    Args:
        responses: Dictionary mapping URLs to mock responses
        
    Returns:
        Configured mock session
    """
    session = MockClientSession()
    
    if responses:
        for url, response in responses.items():
            session.set_response(url, response)
    else:
        # Set default successful response
        session.set_default_response(MockResponse(
            status=200,
            data={'status': 'success'}
        ))
    
    return session


# Example mock responses for testing
MOCK_SEARCH_RESPONSE = MockResponse(
    status=200,
    data={
        'results': [
            {
                'id': 'doc-1',
                'title': 'Python Tutorial',
                'content': 'Learn Python programming',
                'url': 'https://example.com/python',
                'score': 0.95
            }
        ],
        'total_count': 1,
        'query': 'python',
        'processing_time_ms': 50
    }
)

MOCK_HEALTH_RESPONSE = MockResponse(
    status=200,
    data={
        'status': 'healthy',
        'version': '2.1.0',
        'components': {
            'database': {'status': 'healthy'},
            'cache': {'status': 'healthy'},
            'search': {'status': 'healthy'}
        }
    }
)

MOCK_CONFIG_RESPONSE = MockResponse(
    status=200,
    data={
        'items': [
            {
                'key': 'max_connections',
                'value': 100,
                'category': 'performance'
            }
        ]
    }
)