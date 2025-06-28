#!/usr/bin/env python3
"""
Test the enhanced search orchestrator through the API
"""

import asyncio
import httpx
import json
import time

async def test_enhanced_search():
    """Test search with the enhanced orchestrator"""
    
    api_url = "http://localhost:4080/api/v1"
    
    # Test queries to verify intelligent pipeline
    test_queries = [
        "FastAPI async endpoints tutorial",
        "React hooks useState guide",
        "Python asyncio examples"
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n" + "="*60)
        print("Testing Enhanced Search API")
        print("="*60 + "\n")
        
        # Check health first
        try:
            response = await client.get(f"{api_url}/health")
            print(f"Health check: {response.status_code}")
            if response.status_code == 200:
                health = response.json()
                print(f"Status: {health.get('status', 'unknown')}")
                for service in health.get('services', []):
                    print(f"  - {service['name']}: {service['status']}")
            print()
        except Exception as e:
            print(f"Health check failed: {e}\n")
        
        # Test each query
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print("="*60)
            
            try:
                # First search
                start_time = time.time()
                response = await client.post(
                    f"{api_url}/search",
                    json={"query": query, "limit": 5}
                )
                first_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n✅ Search successful in {first_time:.2f}s")
                    print(f"  - Results: {data.get('total_count', 0)}")
                    print(f"  - Cached: {data.get('cache_hit', False)}")
                    print(f"  - Execution time: {data.get('execution_time_ms', 0)}ms")
                    
                    # Show top results
                    results = data.get('results', [])
                    if results:
                        print("\nTop results:")
                        for i, result in enumerate(results[:3]):
                            print(f"\n  {i+1}. {result.get('title', 'Untitled')}")
                            print(f"     Technology: {result.get('technology', 'unknown')}")
                            print(f"     Score: {result.get('relevance_score', 0):.2f}")
                            print(f"     {result.get('snippet', '')[:100]}...")
                    
                    # Wait and test cache
                    await asyncio.sleep(2)
                    
                    # Second search (should hit cache)
                    start_time = time.time()
                    response2 = await client.post(
                        f"{api_url}/search",
                        json={"query": query, "limit": 5}
                    )
                    cache_time = time.time() - start_time
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        print(f"\n💾 Cache test successful in {cache_time:.2f}s")
                        print(f"  - Cached: {data2.get('cache_hit', False)}")
                        print(f"  - Speedup: {first_time/cache_time:.1f}x faster")
                else:
                    print(f"\n❌ Search failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        print("\n\n✨ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_search())