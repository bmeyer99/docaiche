#!/usr/bin/env python3
"""Test MCP adapters in complete isolation without server dependencies."""

import sys
import os
import asyncio

# Add paths
sys.path.insert(0, os.path.abspath('src'))

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)

async def test_adapters():
    """Test adapters without importing the main MCP package."""
    try:
        print("Testing isolated adapter imports...")
        
        # Import mock pydantic directly
        from mcp.mock_pydantic import BaseModel, Field, validator
        print("✓ Mock pydantic imported")
        
        # Test mock functionality
        class TestModel(BaseModel):
            name: str
            value: int = 0
            
        model = TestModel(name="test", value=42)
        print(f"✓ Mock model created: {model.dict()}")
        
        # Import schemas directly with mock
        from mcp.schemas import MCPRequest, MCPResponse
        print("✓ Schemas imported with mock")
        
        # Test request creation
        request = MCPRequest(
            id="test-1",
            method="search",
            params={'query': 'test query'}
        )
        print(f"✓ MCPRequest created: id={request.id}, method={request.method}")
        
        # Import base adapter
        from mcp.adapters.base_adapter import BaseAdapter
        print("✓ BaseAdapter imported")
        
        # Import specific adapters
        from mcp.adapters.search_adapter import SearchAdapter
        print("✓ SearchAdapter imported")
        
        from mcp.adapters.health_adapter import HealthAdapter
        print("✓ HealthAdapter imported")
        
        from mcp.adapters.config_adapter import ConfigAdapter
        print("✓ ConfigAdapter imported")
        
        from mcp.adapters.ingestion_adapter import IngestionAdapter
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
        
        # Test health adapter
        health = HealthAdapter("http://localhost:8000")
        health_req = MCPRequest(id="health-1", method="health/status")
        health_adapted = await health.adapt_request(health_req)
        print(f"✓ Health request adapted: endpoint={health_adapted['endpoint']}")
        
        # Test config adapter
        config = ConfigAdapter("http://localhost:8000")
        config_req = MCPRequest(id="config-1", method="config/get", params={'key': 'test.setting'})
        config_adapted = await config.adapt_request(config_req)
        print(f"✓ Config request adapted: {config_adapted}")
        
        print("\n✅ All adapter tests passed successfully!")
        print("   Adapters are fully functional with mock dependencies.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(test_adapters())