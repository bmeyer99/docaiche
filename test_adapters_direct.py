#!/usr/bin/env python3
"""Test MCP adapters directly without any other imports."""

import sys
import os

# Add both paths to ensure imports work
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('./src'))

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)

# Manually configure mock imports before any MCP imports
os.environ['MCP_USE_MOCKS'] = '1'

try:
    print("Testing direct adapter imports...")
    
    # First test the mocks work
    from mcp.mock_pydantic import BaseModel
    print("✓ Mock pydantic imported")
    
    # Import schemas directly
    from mcp.schemas import MCPRequest, MCPResponse
    print("✓ Schemas imported")
    
    # Test creating a request
    request = MCPRequest(
        id="test-1",
        method="search",
        params={'query': 'test'}
    )
    print(f"✓ MCPRequest created: {request.id}")
    
    # Import base adapter directly
    from mcp.adapters.base_adapter import BaseAdapter
    print("✓ BaseAdapter imported")
    
    # Import search adapter
    from mcp.adapters.search_adapter import SearchAdapter
    print("✓ SearchAdapter imported")
    
    # Create adapter instance
    adapter = SearchAdapter(
        base_url="http://localhost:8000",
        api_version="v1"
    )
    print("✓ SearchAdapter instance created")
    
    # Test async functionality
    import asyncio
    
    async def test_adaptation():
        # Test request adaptation
        adapted = await adapter.adapt_request(request)
        print(f"✓ Request adapted: {adapted}")
        
        # Test response adaptation
        api_response = {
            'results': [
                {
                    'id': 'doc-1',
                    'title': 'Test Document',
                    'content': 'Test content',
                    'url': 'https://example.com/test',
                    'score': 0.95
                }
            ],
            'total_count': 1,
            'query': 'test'
        }
        
        response = await adapter.adapt_response(api_response)
        print(f"✓ Response adapted successfully")
        print(f"  - Results: {len(response['results'])}")
        print(f"  - First result title: {response['results'][0]['title']}")
        
        return response
    
    result = asyncio.run(test_adaptation())
    
    # Test other adapters
    from mcp.adapters.health_adapter import HealthAdapter
    health_adapter = HealthAdapter("http://localhost:8000")
    print("✓ HealthAdapter created")
    
    from mcp.adapters.config_adapter import ConfigAdapter
    config_adapter = ConfigAdapter("http://localhost:8000")
    print("✓ ConfigAdapter created")
    
    print("\n✅ All adapter tests passed successfully!")
    print("   Adapters are working correctly with mock dependencies.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()