"""
Basic Unit Tests for MCP Adapters
=================================

Tests for MCP to FastAPI adapter implementations without external dependencies.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mcp.adapters.adapter_factory import AdapterFactory, AdapterType
from src.mcp.adapters.search_adapter import SearchAdapter
from src.mcp.schemas import MCPRequest, MCPResponse


class TestAdapterFactory(unittest.TestCase):
    """Test adapter factory functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.factory = AdapterFactory(
            base_url="http://localhost:8000",
            api_version="v1",
            auth_token="test-token"
        )
    
    def test_create_adapter(self):
        """Test adapter creation."""
        # Create search adapter
        adapter = self.factory.create_adapter(AdapterType.SEARCH)
        self.assertIsInstance(adapter, SearchAdapter)
        self.assertEqual(adapter.base_url, "http://localhost:8000")
        self.assertEqual(adapter.auth_token, "test-token")
        
        # Verify caching
        adapter2 = self.factory.create_adapter(AdapterType.SEARCH)
        self.assertIs(adapter, adapter2)
    
    def test_adapter_types(self):
        """Test all adapter types can be created."""
        for adapter_type in AdapterType:
            adapter = self.factory.create_adapter(adapter_type)
            self.assertIsNotNone(adapter)
            self.assertEqual(adapter.base_url, "http://localhost:8000")


class TestSearchAdapter(unittest.TestCase):
    """Test search adapter functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.adapter = SearchAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
    
    async def test_adapt_search_request(self):
        """Test search request adaptation."""
        mcp_request = MCPRequest(
            id="test-1",
            method="search",
            params={
                'query': 'python tutorial',
                'limit': 20,
                'filters': {
                    'technologies': ['python'],
                    'time_range': '7d'
                }
            }
        )
        
        adapted = await self.adapter.adapt_request(mcp_request)
        
        # Verify adaptation
        self.assertEqual(adapted['query'], 'python tutorial')
        self.assertEqual(adapted['limit'], 20)
        self.assertEqual(adapted['technologies'], ['python'])
        self.assertEqual(adapted['time_range'], '7d')
    
    async def test_adapt_search_response(self):
        """Test search response adaptation."""
        api_response = {
            'results': [
                {
                    'id': 'doc-1',
                    'title': 'Python Tutorial',
                    'content': 'Learn Python...',
                    'url': 'https://example.com/python',
                    'score': 0.95
                }
            ],
            'total_count': 42
        }
        
        adapted = await self.adapter.adapt_response(api_response)
        
        # Verify adaptation
        self.assertEqual(len(adapted['results']), 1)
        self.assertEqual(adapted['total_count'], 42)
        self.assertEqual(adapted['results'][0]['title'], 'Python Tutorial')


class TestRequestAdaptation(unittest.TestCase):
    """Test request adaptation across different adapters."""
    
    def setUp(self):
        """Set up test environment."""
        self.factory = AdapterFactory("http://localhost:8000")
    
    async def test_ingestion_request_adaptation(self):
        """Test ingestion request adaptation."""
        adapter = self.factory.create_adapter(AdapterType.INGESTION)
        
        mcp_request = MCPRequest(
            id="test-1",
            method="ingest",
            params={
                'content': 'Test content',
                'content_type': 'text/plain',
                'metadata': {'author': 'Test'}
            }
        )
        
        adapted = await adapter.adapt_request(mcp_request)
        
        # Verify core fields
        self.assertIn('content', adapted)
        self.assertEqual(adapted['content_type'], 'text/plain')
        self.assertIn('metadata', adapted)
    
    async def test_health_request_adaptation(self):
        """Test health request adaptation."""
        adapter = self.factory.create_adapter(AdapterType.HEALTH)
        
        mcp_request = MCPRequest(
            id="test-1",
            method="check_health",
            params={'include_details': True}
        )
        
        adapted = await adapter.adapt_request(mcp_request)
        
        # Verify adaptation
        self.assertTrue(adapted['include_details'])
        self.assertTrue(adapted['check_dependencies'])


class TestResponseAdaptation(unittest.TestCase):
    """Test response adaptation across different adapters."""
    
    def setUp(self):
        """Set up test environment."""
        self.factory = AdapterFactory("http://localhost:8000")
    
    async def test_health_response_adaptation(self):
        """Test health response adaptation."""
        adapter = self.factory.create_adapter(AdapterType.HEALTH)
        
        api_response = {
            'status': 'healthy',
            'version': '2.1.0',
            'components': {
                'database': {'status': 'healthy'},
                'cache': {'status': 'degraded'}
            }
        }
        
        adapted = await adapter.adapt_response(api_response)
        
        # Verify adaptation
        self.assertEqual(adapted['status'], 'healthy')
        self.assertIn('components', adapted)
        self.assertIn('health_score', adapted)
    
    async def test_config_response_masking(self):
        """Test configuration response with sensitive data masking."""
        adapter = self.factory.create_adapter(AdapterType.CONFIG)
        
        api_response = {
            'items': [
                {'key': 'api_key', 'value': 'secret', 'category': 'security'},
                {'key': 'port', 'value': 8080, 'category': 'network'}
            ]
        }
        
        adapted = await adapter.adapt_response(api_response)
        
        # Verify masking
        configs = adapted['configurations']
        self.assertEqual(configs[0]['value'], '***REDACTED***')
        self.assertTrue(configs[0]['is_sensitive'])
        self.assertEqual(configs[1]['value'], 8080)
        self.assertFalse(configs[1]['is_sensitive'])


if __name__ == "__main__":
    # Run async tests properly
    def async_test(f):
        def wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(f(*args, **kwargs))
            finally:
                loop.close()
        return wrapper
    
    # Patch all async test methods
    for test_class in [TestAdapterFactory, TestSearchAdapter, TestRequestAdaptation, TestResponseAdaptation]:
        for attr_name in dir(test_class):
            if attr_name.startswith('test_'):
                attr = getattr(test_class, attr_name)
                if asyncio.iscoroutinefunction(attr):
                    setattr(test_class, attr_name, async_test(attr))
    
    unittest.main()