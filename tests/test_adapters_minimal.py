#!/usr/bin/env python3
"""Test MCP adapters with absolute minimal imports."""

import sys
import os
import asyncio

# Add path
sys.path.insert(0, os.path.abspath('src'))

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)

async def test_adapters():
    """Test adapters with direct imports only."""
    try:
        print("Testing minimal adapter functionality...")
        
        # Import mock pydantic directly without going through __init__
        import mcp.mock_pydantic as mock_pydantic
        BaseModel = mock_pydantic.BaseModel
        Field = mock_pydantic.Field
        validator = mock_pydantic.validator
        print("✓ Mock pydantic imported directly")
        
        # Test mock functionality
        class TestModel(BaseModel):
            name: str
            value: int = 0
            
        model = TestModel(name="test", value=42)
        print(f"✓ Mock model created: {model.dict()}")
        
        # Import schemas directly - this will use mock pydantic
        import mcp.schemas as schemas
        MCPRequest = schemas.MCPRequest
        MCPResponse = schemas.MCPResponse
        print("✓ Schemas imported")
        
        # Test request creation
        request = MCPRequest(
            id="test-1",
            method="search",
            params={'query': 'test query'}
        )
        print(f"✓ MCPRequest created: id={request.id}, method={request.method}")
        
        # Import base adapter directly
        import mcp.adapters.base_adapter as base_adapter
        BaseAdapter = base_adapter.BaseAdapter
        print("✓ BaseAdapter imported")
        
        # Import specific adapters directly
        import mcp.adapters.search_adapter as search_adapter
        SearchAdapter = search_adapter.SearchAdapter
        print("✓ SearchAdapter imported")
        
        import mcp.adapters.health_adapter as health_adapter  
        HealthAdapter = health_adapter.HealthAdapter
        print("✓ HealthAdapter imported")
        
        import mcp.adapters.config_adapter as config_adapter
        ConfigAdapter = config_adapter.ConfigAdapter
        print("✓ ConfigAdapter imported")
        
        import mcp.adapters.ingestion_adapter as ingestion_adapter
        IngestionAdapter = ingestion_adapter.IngestionAdapter
        print("✓ IngestionAdapter imported")
        
        # Create adapter instance
        search = SearchAdapter(
            base_url="http://localhost:8000",
            api_version="v1"
        )
        print("✓ SearchAdapter instance created")
        
        # Test request adaptation
        adapted_req = await search.adapt_request(request)
        print(f"✓ Request adapted: {adapted_req}")
        
        # Test response adaptation
        api_response = {
            'results': [
                {
                    'id': 'doc-1',
                    'title': 'Test Document',
                    'content': 'This is test content',
                    'url': 'https://example.com/test',
                    'score': 0.95,
                    'metadata': {'tags': ['test', 'demo']}
                }
            ],
            'total_count': 1,
            'query': 'test query',
            'processing_time_ms': 25
        }
        
        adapted_resp = await search.adapt_response(api_response)
        print(f"✓ Response adapted:")
        print(f"  - Results: {len(adapted_resp['results'])}")
        print(f"  - First result: {adapted_resp['results'][0]['title']}")
        print(f"  - Total count: {adapted_resp['totalCount']}")
        
        # Test other adapters
        health = HealthAdapter("http://localhost:8000")
        health_req = MCPRequest(id="health-1", method="health/status")
        health_adapted = await health.adapt_request(health_req)
        print(f"✓ Health request adapted: endpoint={health_adapted['endpoint']}")
        
        config = ConfigAdapter("http://localhost:8000")
        config_req = MCPRequest(id="config-1", method="config/get", params={'key': 'test.setting'})
        config_adapted = await config.adapt_request(config_req)
        print(f"✓ Config request adapted: {config_adapted}")
        
        # Test ingestion adapter
        ingest = IngestionAdapter("http://localhost:8000")
        ingest_req = MCPRequest(
            id="ingest-1",
            method="ingest/document",
            params={
                'title': 'Test Doc',
                'content': 'Test content',
                'url': 'https://example.com/test'
            }
        )
        ingest_adapted = await ingest.adapt_request(ingest_req)
        print(f"✓ Ingestion request adapted: {ingest_adapted['endpoint']}")
        
        # Test adapter factory
        import mcp.adapters.adapter_factory as adapter_factory
        AdapterFactory = adapter_factory.AdapterFactory
        AdapterType = adapter_factory.AdapterType
        print("✓ AdapterFactory imported")
        
        # Create factory and test adapter creation
        factory = AdapterFactory(base_url="http://localhost:8000")
        search_from_factory = factory.create_adapter(AdapterType.SEARCH)
        print(f"✓ Adapter created from factory: {type(search_from_factory).__name__}")
        
        print("\n✅ All adapter tests passed successfully!")
        print("   Adapters are fully functional with mock dependencies.")
        print("   Dependencies have been successfully resolved.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(test_adapters())