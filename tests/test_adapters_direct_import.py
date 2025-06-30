#!/usr/bin/env python3
"""Test MCP adapters with direct file imports to avoid circular dependencies."""

import sys
import os
import asyncio

# Set up environment
os.environ['MCP_USE_MOCKS'] = '1'

# Add path
sys.path.insert(0, os.path.abspath('src'))

# Set up logging
import logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise

async def test_adapters():
    """Test adapters functionality."""
    try:
        print("Testing MCP adapters with mock dependencies...")
        print("-" * 50)
        
        # Step 1: Test mock pydantic directly
        print("\n1. Testing mock pydantic:")
        exec(open('src/mcp/mock_pydantic.py').read(), globals())
        
        class TestModel(BaseModel):
            name: str
            value: int = Field(default=0)
            
        model = TestModel(name="test", value=42)
        print(f"   ✓ Created model: {model.dict()}")
        
        # Step 2: Import schemas module directly
        print("\n2. Testing schemas with mock:")
        import importlib.util
        spec = importlib.util.spec_from_file_location("schemas", "src/mcp/schemas.py")
        schemas = importlib.util.module_from_spec(spec)
        
        # Inject mock pydantic into schemas module
        schemas.BaseModel = BaseModel
        schemas.Field = Field
        schemas.validator = validator
        
        spec.loader.exec_module(schemas)
        
        # Create MCP request
        request = schemas.MCPRequest(
            id="test-1",
            method="search",
            params={'query': 'test query'}
        )
        print(f"   ✓ Created MCPRequest: {request.id}")
        
        # Step 3: Test base adapter
        print("\n3. Testing base adapter:")
        spec = importlib.util.spec_from_file_location("base_adapter", "src/mcp/adapters/base_adapter.py")
        base_adapter = importlib.util.module_from_spec(spec)
        
        # Inject schemas before loading
        base_adapter.MCPRequest = schemas.MCPRequest
        base_adapter.MCPResponse = schemas.MCPResponse
        
        # Create mock aiohttp for base adapter
        base_adapter.aiohttp = type('MockAiohttp', (), {
            'ClientSession': lambda: None,
            'ClientTimeout': lambda total: None
        })()
        
        spec.loader.exec_module(base_adapter)
        print("   ✓ Base adapter loaded")
        
        # Step 4: Test search adapter
        print("\n4. Testing search adapter:")
        spec = importlib.util.spec_from_file_location("search_adapter", "src/mcp/adapters/search_adapter.py")
        search_adapter = importlib.util.module_from_spec(spec)
        
        # Inject dependencies
        search_adapter.BaseAdapter = base_adapter.BaseAdapter
        search_adapter.MCPRequest = schemas.MCPRequest
        search_adapter.logger = logging.getLogger('search_adapter')
        
        spec.loader.exec_module(search_adapter)
        
        # Create adapter instance
        adapter = search_adapter.SearchAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
        print("   ✓ SearchAdapter instance created")
        
        # Test request adaptation
        adapted = await adapter.adapt_request(request)
        print(f"   ✓ Request adapted: query='{adapted['query']}', limit={adapted['limit']}")
        
        # Test response adaptation
        api_response = {
            'results': [
                {
                    'id': 'doc-1',
                    'title': 'Test Document',
                    'content': 'This is test content with the query terms',
                    'url': 'https://example.com/test',
                    'score': 0.95,
                    'metadata': {'tags': ['test', 'demo']}
                }
            ],
            'total_count': 1,
            'query': 'test query',
            'processing_time_ms': 25
        }
        
        response = await adapter.adapt_response(api_response)
        print(f"   ✓ Response adapted: {len(response['results'])} results")
        print(f"   ✓ First result: '{response['results'][0]['title']}'")
        
        # Step 5: Test other adapters
        print("\n5. Testing other adapters:")
        
        # Health adapter
        spec = importlib.util.spec_from_file_location("health_adapter", "src/mcp/adapters/health_adapter.py")
        health_adapter = importlib.util.module_from_spec(spec)
        health_adapter.BaseAdapter = base_adapter.BaseAdapter
        health_adapter.MCPRequest = schemas.MCPRequest
        health_adapter.logger = logging.getLogger('health_adapter')
        spec.loader.exec_module(health_adapter)
        
        health = health_adapter.HealthAdapter("http://localhost:8000")
        print("   ✓ HealthAdapter created")
        
        # Config adapter
        spec = importlib.util.spec_from_file_location("config_adapter", "src/mcp/adapters/config_adapter.py")
        config_adapter = importlib.util.module_from_spec(spec)
        config_adapter.BaseAdapter = base_adapter.BaseAdapter
        config_adapter.MCPRequest = schemas.MCPRequest
        config_adapter.logger = logging.getLogger('config_adapter')
        spec.loader.exec_module(config_adapter)
        
        config = config_adapter.ConfigAdapter("http://localhost:8000")
        print("   ✓ ConfigAdapter created")
        
        # Ingestion adapter
        spec = importlib.util.spec_from_file_location("ingestion_adapter", "src/mcp/adapters/ingestion_adapter.py")
        ingestion_adapter = importlib.util.module_from_spec(spec)
        ingestion_adapter.BaseAdapter = base_adapter.BaseAdapter
        ingestion_adapter.MCPRequest = schemas.MCPRequest
        ingestion_adapter.logger = logging.getLogger('ingestion_adapter')
        spec.loader.exec_module(ingestion_adapter)
        
        ingest = ingestion_adapter.IngestionAdapter("http://localhost:8000")
        print("   ✓ IngestionAdapter created")
        
        print("\n" + "=" * 50)
        print("✅ All adapter tests passed successfully!")
        print("   - Mock pydantic working correctly")
        print("   - Adapters functional without external dependencies")
        print("   - Request/response adaptation working as expected")
        print("   - All adapter types can be instantiated")
        print("\nDependency resolution complete. Adapters are ready for use.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(test_adapters())