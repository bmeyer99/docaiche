#!/usr/bin/env python3
"""Test MCP imports without external dependencies."""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    print("Testing adapter imports...")
    from src.mcp.adapters.adapter_factory import AdapterFactory, AdapterType
    print("✓ AdapterFactory imported successfully")
    
    from src.mcp.adapters.search_adapter import SearchAdapter
    print("✓ SearchAdapter imported successfully")
    
    from src.mcp.schemas import MCPRequest, MCPResponse
    print("✓ Schemas imported successfully")
    
    # Test creating adapter factory
    factory = AdapterFactory("http://localhost:8000")
    print("✓ AdapterFactory created successfully")
    
    # Test creating adapter
    adapter = factory.create_adapter(AdapterType.SEARCH)
    print("✓ SearchAdapter created successfully")
    
    # Test basic request adaptation
    import asyncio
    async def test_adaptation():
        request = MCPRequest(
            id="test-1",
            method="search",
            params={'query': 'test'}
        )
        adapted = await adapter.adapt_request(request)
        return adapted
    
    result = asyncio.run(test_adaptation())
    print(f"✓ Request adaptation successful: {result}")
    
    print("\n✅ All imports and basic functionality working!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()