#!/usr/bin/env python3
"""Test MCP adapters only without server dependencies."""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Set up minimal imports to avoid server dependencies
import logging
logging.basicConfig(level=logging.INFO)

try:
    print("Testing adapter imports (without server)...")
    
    # Import base adapter
    from src.mcp.adapters.base_adapter import BaseAdapter
    print("✓ BaseAdapter imported")
    
    # Import adapter types
    from src.mcp.adapters.adapter_factory import AdapterType
    print("✓ AdapterType imported")
    
    # Import individual adapters
    from src.mcp.adapters.search_adapter import SearchAdapter
    print("✓ SearchAdapter imported")
    
    from src.mcp.adapters.ingestion_adapter import IngestionAdapter
    print("✓ IngestionAdapter imported")
    
    from src.mcp.adapters.health_adapter import HealthAdapter  
    print("✓ HealthAdapter imported")
    
    # Test creating an adapter directly
    adapter = SearchAdapter(
        base_url="http://localhost:8000",
        api_version="v1"
    )
    print("✓ SearchAdapter instance created")
    
    # Test request adaptation
    from src.mcp.schemas import MCPRequest
    import asyncio
    
    async def test_basic():
        request = MCPRequest(
            id="test-1",
            method="search",
            params={'query': 'test'}
        )
        print(f"✓ MCPRequest created: {request.id}")
        
        # Test adaptation
        adapted = await adapter.adapt_request(request)
        print(f"✓ Request adapted: {adapted}")
        
        # Test response adaptation
        api_response = {
            'results': [{'id': 'doc-1', 'title': 'Test'}],
            'total_count': 1
        }
        response = await adapter.adapt_response(api_response)
        print(f"✓ Response adapted: {len(response['results'])} results")
    
    asyncio.run(test_basic())
    
    print("\n✅ Adapter functionality working without server dependencies!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()