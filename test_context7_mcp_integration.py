#!/usr/bin/env python3
"""
Direct Context7 MCP Integration Test
====================================

Tests Context7 integration through the MCP search endpoint.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


async def test_context7_through_mcp():
    """Test Context7 integration via MCP search endpoint."""
    
    base_url = "http://localhost:4080/api/v1"
    
    async with aiohttp.ClientSession() as session:
        print("\n" + "="*60)
        print("Context7 MCP Integration Test")
        print("="*60)
        
        # Test 1: React useState search
        print("\n1. Testing React useState search...")
        react_payload = {
            "query": "React useState hook implementation",
            "use_external_search": True,
            "technology_hint": "react",
            "max_results": 10,
            "provider_ids": ["context7_docs"]
        }
        
        try:
            start_time = time.time()
            async with session.post(f"{base_url}/mcp/search", json=react_payload) as resp:
                duration_ms = int((time.time() - start_time) * 1000)
                result = await resp.json()
                
                print(f"   Status: {resp.status}")
                print(f"   Duration: {duration_ms}ms")
                
                if resp.status == 200:
                    print(f"   Results: {result.get('total_results', 0)}")
                    print(f"   Providers used: {result.get('providers_used', [])}")
                    
                    # Check for Context7 results
                    results = result.get('results', [])
                    context7_results = [r for r in results if r.get('provider') == 'context7']
                    
                    if context7_results:
                        print(f"   ✓ Context7 results found: {len(context7_results)}")
                        first_result = context7_results[0]
                        print(f"   Title: {first_result.get('title', 'N/A')}")
                        print(f"   URL: {first_result.get('url', 'N/A')}")
                        
                        # Check for TTL metadata
                        if 'metadata' in first_result:
                            metadata = first_result['metadata']
                            if 'ttl_seconds' in metadata:
                                print(f"   ✓ TTL metadata present: {metadata['ttl_seconds']} seconds")
                            else:
                                print("   ✗ TTL metadata missing")
                    else:
                        print("   ✗ No Context7 results found")
                else:
                    print(f"   ✗ Error: {result}")
                    
        except Exception as e:
            print(f"   ✗ Request failed: {e}")
        
        # Test 2: TypeScript search
        print("\n2. Testing TypeScript interface search...")
        ts_payload = {
            "query": "TypeScript interface type checking",
            "use_external_search": True,
            "technology_hint": "typescript",
            "max_results": 10
        }
        
        try:
            start_time = time.time()
            async with session.post(f"{base_url}/mcp/search", json=ts_payload) as resp:
                duration_ms = int((time.time() - start_time) * 1000)
                result = await resp.json()
                
                print(f"   Status: {resp.status}")
                print(f"   Duration: {duration_ms}ms")
                
                if resp.status == 200:
                    results = result.get('results', [])
                    context7_results = [r for r in results if r.get('provider') == 'context7']
                    
                    if context7_results:
                        print(f"   ✓ Context7 results: {len(context7_results)}")
                    else:
                        print("   ✗ No Context7 results")
                        
        except Exception as e:
            print(f"   ✗ Request failed: {e}")
        
        # Test 3: Vue.js search
        print("\n3. Testing Vue.js Composition API search...")
        vue_payload = {
            "query": "Vue composition API setup function", 
            "use_external_search": True,
            "technology_hint": "vue",
            "max_results": 10
        }
        
        try:
            start_time = time.time()
            async with session.post(f"{base_url}/mcp/search", json=vue_payload) as resp:
                duration_ms = int((time.time() - start_time) * 1000)
                result = await resp.json()
                
                print(f"   Status: {resp.status}")
                print(f"   Duration: {duration_ms}ms")
                
                if resp.status == 200:
                    results = result.get('results', [])
                    context7_results = [r for r in results if r.get('provider') == 'context7']
                    
                    if context7_results:
                        print(f"   ✓ Context7 results: {len(context7_results)}")
                    else:
                        print("   ✗ No Context7 results")
                        
        except Exception as e:
            print(f"   ✗ Request failed: {e}")
        
        # Test 4: Check Context7 provider status
        print("\n4. Checking Context7 provider status...")
        try:
            async with session.get(f"{base_url}/mcp/providers") as resp:
                result = await resp.json()
                
                if resp.status == 200:
                    providers = result.get('providers', [])
                    context7_providers = [p for p in providers if 'context7' in p.get('provider_id', '').lower()]
                    
                    if context7_providers:
                        print(f"   ✓ Context7 providers found: {len(context7_providers)}")
                        for provider in context7_providers:
                            print(f"   - {provider['provider_id']}: {provider.get('health', {}).get('status', 'unknown')}")
                    else:
                        print("   ✗ No Context7 providers configured")
                else:
                    print(f"   ✗ Failed to get providers: {resp.status}")
                    
        except Exception as e:
            print(f"   ✗ Request failed: {e}")
        
        # Test 5: Direct Context7 fetch
        print("\n5. Testing direct Context7 documentation fetch...")
        try:
            params = {
                "library": "react",
                "topic": "useState"
            }
            async with session.get(f"{base_url}/mcp/context7/fetch", params=params) as resp:
                result = await resp.json()
                
                print(f"   Status: {resp.status}")
                
                if resp.status == 200:
                    docs = result.get('documentation', [])
                    print(f"   ✓ Documentation entries: {len(docs)}")
                    if docs:
                        first_doc = docs[0]
                        print(f"   Title: {first_doc.get('title', 'N/A')}")
                        metadata = first_doc.get('metadata', {})
                        if 'ttl_seconds' in metadata:
                            print(f"   ✓ TTL: {metadata['ttl_seconds']} seconds")
                else:
                    print(f"   ✗ Error: {result}")
                    
        except Exception as e:
            print(f"   ✗ Request failed: {e}")
        
        print("\n" + "="*60)
        print("Context7 Integration Test Complete")
        print("="*60 + "\n")


async def check_mcp_logs():
    """Check API logs for Context7 activity."""
    print("\nChecking API logs for Context7 activity...")
    
    # This would typically tail the Docker logs
    # For now, we'll just indicate where to look
    print("To view Context7 logs, run:")
    print("  docker-compose logs -f api | grep -i context7")
    print("  docker-compose logs -f api | grep -i 'PIPELINE_METRICS.*context7'")
    print("  docker-compose logs -f api | grep -i 'ttl_seconds'")


if __name__ == "__main__":
    print("Starting Context7 MCP Integration Test")
    print("Make sure the API service is running at http://localhost:4080")
    
    asyncio.run(test_context7_through_mcp())
    asyncio.run(check_mcp_logs())