"""
Unit Tests for MCP Adapters
===========================

Tests for MCP to FastAPI adapter implementations.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mcp.adapters.adapter_factory import AdapterFactory, AdapterType
from src.mcp.adapters.search_adapter import SearchAdapter
from src.mcp.adapters.ingestion_adapter import IngestionAdapter
from src.mcp.adapters.logs_adapter import LogsAdapter
from src.mcp.adapters.health_adapter import HealthAdapter
from src.mcp.adapters.config_adapter import ConfigAdapter
from src.mcp.schemas import MCPRequest, MCPResponse
from src.mcp.exceptions import ServiceError, RateLimitError


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
    
    def test_get_adapter_stats(self):
        """Test adapter statistics."""
        # Create some adapters
        self.factory.create_adapter(AdapterType.SEARCH)
        self.factory.create_adapter(AdapterType.HEALTH)
        
        stats = self.factory.get_adapter_stats()
        self.assertEqual(stats['active_adapters'], 2)
        self.assertIn('search', stats['adapters'])
        self.assertIn('health', stats['adapters'])
    
    async def test_close_all(self):
        """Test closing all adapters."""
        # Create adapters
        search = self.factory.create_adapter(AdapterType.SEARCH)
        health = self.factory.create_adapter(AdapterType.HEALTH)
        
        # Mock close methods
        search.close = AsyncMock()
        health.close = AsyncMock()
        
        # Close all
        await self.factory.close_all()
        
        # Verify closed
        search.close.assert_called_once()
        health.close.assert_called_once()
        self.assertEqual(len(self.factory._adapters), 0)


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
                },
                'options': {
                    'fuzzy': True,
                    'semantic': True
                }
            }
        )
        
        adapted = await self.adapter.adapt_request(mcp_request)
        
        # Verify adaptation
        self.assertEqual(adapted['query'], 'python tutorial')
        self.assertEqual(adapted['limit'], 20)
        self.assertEqual(adapted['technologies'], ['python'])
        self.assertEqual(adapted['time_range'], '7d')
        self.assertTrue(adapted['fuzzy_search'])
        self.assertTrue(adapted['use_semantic'])
    
    async def test_adapt_search_response(self):
        """Test search response adaptation."""
        api_response = {
            'results': [
                {
                    'id': 'doc-1',
                    'title': 'Python Tutorial',
                    'content': 'Learn Python...',
                    'url': 'https://example.com/python',
                    'score': 0.95,
                    'source': 'docs',
                    'snippet': 'Learn Python basics...'
                }
            ],
            'total_count': 42,
            'query': 'python tutorial',
            'processing_time_ms': 123
        }
        
        adapted = await self.adapter.adapt_response(api_response)
        
        # Verify adaptation
        self.assertEqual(len(adapted['results']), 1)
        self.assertEqual(adapted['total_count'], 42)
        
        result = adapted['results'][0]
        self.assertEqual(result['id'], 'doc-1')
        self.assertEqual(result['title'], 'Python Tutorial')
        self.assertEqual(result['score'], 0.95)
        self.assertIn('metadata', result)
        self.assertEqual(result['snippet'], 'Learn Python basics...')
    
    @patch('aiohttp.ClientSession.request')
    async def test_search_execution(self, mock_request):
        """Test complete search execution."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'results': [{'id': 'doc-1', 'title': 'Test'}],
            'total_count': 1
        })
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # Execute search
        mcp_request = MCPRequest(
            id="test-1",
            method="search",
            params={'query': 'test'}
        )
        
        response = await self.adapter.search(mcp_request)
        
        # Verify response
        self.assertIsInstance(response, MCPResponse)
        self.assertEqual(response.id, "test-1")
        self.assertIn('results', response.result)


class TestIngestionAdapter(unittest.TestCase):
    """Test ingestion adapter functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.adapter = IngestionAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
    
    async def test_adapt_ingestion_request(self):
        """Test ingestion request adaptation."""
        mcp_request = MCPRequest(
            id="test-1",
            method="ingest",
            params={
                'content': 'Test document content',
                'content_type': 'text/plain',
                'metadata': {'author': 'Test'},
                'document': {
                    'title': 'Test Document',
                    'tags': ['test', 'example']
                }
            }
        )
        
        adapted = await self.adapter.adapt_request(mcp_request)
        
        # Verify adaptation
        self.assertIn('content', adapted)
        self.assertTrue(adapted['is_base64'])
        self.assertEqual(adapted['content_type'], 'text/plain')
        self.assertIn('content_hash', adapted)
        self.assertEqual(adapted['document']['title'], 'Test Document')
    
    async def test_validate_content(self):
        """Test content validation."""
        mcp_request = MCPRequest(
            id="test-1",
            method="validate",
            params={
                'content': 'Test content',
                'content_type': 'text/plain'
            }
        )
        
        response = await self.adapter.validate_content(mcp_request)
        
        # Verify validation
        self.assertTrue(response.result['valid'])
        self.assertEqual(len(response.result['errors']), 0)
        self.assertIn('content_size', response.result)


class TestLogsAdapter(unittest.TestCase):
    """Test logs adapter functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.adapter = LogsAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
    
    async def test_adapt_log_query_request(self):
        """Test log query request adaptation."""
        mcp_request = MCPRequest(
            id="test-1",
            method="query_logs",
            params={
                'query': 'error',
                'time_range': '1h',
                'filters': {
                    'log_levels': ['error', 'warning'],
                    'services': ['api', 'worker']
                },
                'limit': 50
            }
        )
        
        adapted = await self.adapter.adapt_request(mcp_request)
        
        # Verify adaptation
        self.assertEqual(adapted['query'], 'error')
        self.assertIn('start_time', adapted)
        self.assertIn('end_time', adapted)
        self.assertEqual(adapted['log_levels'], ['error', 'warning'])
        self.assertEqual(adapted['services'], ['api', 'worker'])
        self.assertEqual(adapted['limit'], 50)
    
    async def test_pattern_detection_request(self):
        """Test pattern detection request."""
        mcp_request = MCPRequest(
            id="test-1",
            method="detect_patterns",
            params={
                'workspace_id': 'test-workspace',
                'time_range': '1h',
                'pattern_types': ['error', 'performance']
            }
        )
        
        # Mock the request method
        self.adapter._make_request = AsyncMock(return_value={
            'patterns': [
                {'type': 'error_spike', 'confidence': 0.85}
            ],
            'anomalies': [],
            'risk_score': 3.5
        })
        
        response = await self.adapter.detect_patterns(mcp_request)
        
        # Verify response
        self.assertIn('patterns', response.result)
        self.assertIn('risk_score', response.result)
        self.assertEqual(response.result['risk_score'], 3.5)


class TestHealthAdapter(unittest.TestCase):
    """Test health adapter functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.adapter = HealthAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
    
    async def test_adapt_health_response(self):
        """Test health response adaptation."""
        api_response = {
            'status': 'healthy',
            'timestamp': '2024-01-01T00:00:00Z',
            'version': '2.1.0',
            'components': {
                'database': {
                    'status': 'healthy',
                    'message': 'Connected'
                },
                'cache': {
                    'status': 'degraded',
                    'message': 'High memory usage'
                }
            },
            'metrics': {
                'cpu_usage': 45.2,
                'memory_usage': 78.5
            }
        }
        
        adapted = await self.adapter.adapt_response(api_response)
        
        # Verify adaptation
        self.assertEqual(adapted['status'], 'healthy')
        self.assertIn('components', adapted)
        self.assertEqual(adapted['components']['database']['status'], 'healthy')
        self.assertIn('health_score', adapted)
        self.assertEqual(adapted['health_score'], 50.0)  # 1/2 healthy
    
    async def test_component_recommendations(self):
        """Test component health recommendations."""
        recommendations = self.adapter._get_component_recommendations(
            'cache',
            {'status': 'degraded'}
        )
        
        self.assertGreater(len(recommendations), 0)
        self.assertIn('cache', recommendations[0])


class TestConfigAdapter(unittest.TestCase):
    """Test configuration adapter functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.adapter = ConfigAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
    
    async def test_sensitive_data_masking(self):
        """Test sensitive configuration masking."""
        api_response = {
            'items': [
                {
                    'key': 'api_key',
                    'value': 'secret-key-123',
                    'category': 'security'
                },
                {
                    'key': 'max_connections',
                    'value': 100,
                    'category': 'performance'
                }
            ]
        }
        
        adapted = await self.adapter.adapt_response(api_response)
        
        # Verify masking
        configs = adapted['configurations']
        self.assertEqual(configs[0]['value'], '***REDACTED***')
        self.assertTrue(configs[0]['is_sensitive'])
        self.assertEqual(configs[1]['value'], 100)
        self.assertFalse(configs[1]['is_sensitive'])
    
    async def test_configuration_validation(self):
        """Test configuration validation."""
        mcp_request = MCPRequest(
            id="test-1",
            method="validate",
            params={
                'configurations': [
                    {
                        'key': 'port',
                        'value': '8080',
                        'data_type': 'integer'
                    },
                    {
                        'key': 'enabled',
                        'value': 'invalid',
                        'data_type': 'boolean'
                    }
                ]
            }
        )
        
        response = await self.adapter.validate_configuration(mcp_request)
        
        # Verify validation
        results = response.result['validation_results']
        self.assertTrue(results[0]['valid'])
        self.assertFalse(results[1]['valid'])
        self.assertFalse(response.result['all_valid'])


class TestErrorHandling(unittest.TestCase):
    """Test adapter error handling."""
    
    def setUp(self):
        """Set up test environment."""
        self.adapter = SearchAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
    
    @patch('aiohttp.ClientSession.request')
    async def test_rate_limit_error(self, mock_request):
        """Test rate limit error handling."""
        # Mock 429 response
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_request.return_value.__aenter__.return_value = mock_response
        
        mcp_request = MCPRequest(id="test-1", method="search", params={})
        
        with self.assertRaises(RateLimitError) as context:
            await self.adapter.search(mcp_request)
        
        self.assertEqual(context.exception.details['retry_after_seconds'], 60)
    
    @patch('aiohttp.ClientSession.request')
    async def test_retry_logic(self, mock_request):
        """Test retry logic for server errors."""
        # Mock server error then success
        mock_error = MagicMock()
        mock_error.status = 500
        mock_error.text = AsyncMock(return_value="Server error")
        
        mock_success = MagicMock()
        mock_success.status = 200
        mock_success.json = AsyncMock(return_value={'results': []})
        
        mock_request.return_value.__aenter__.side_effect = [
            mock_error,
            mock_success
        ]
        
        # Should retry and succeed
        response = await self.adapter._make_request('GET', '/test')
        
        self.assertEqual(response, {'results': []})
        self.assertEqual(mock_request.call_count, 2)


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
    for test_class in [
        TestAdapterFactory,
        TestSearchAdapter,
        TestIngestionAdapter,
        TestLogsAdapter,
        TestHealthAdapter,
        TestConfigAdapter,
        TestErrorHandling
    ]:
        for attr_name in dir(test_class):
            if attr_name.startswith('test_'):
                attr = getattr(test_class, attr_name)
                if asyncio.iscoroutinefunction(attr):
                    setattr(test_class, attr_name, async_test(attr))
    
    unittest.main()