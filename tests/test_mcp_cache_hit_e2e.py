#!/usr/bin/env python3
"""
MCP Endpoint Cache Hit E2E Test
================================

This test validates the end-to-end flow of a cache hit through the MCP endpoint.
It performs the following:
1. First query (cache miss) - caches the result
2. Second identical query (cache hit) - retrieves from cache
3. Validates cache behavior and performance

Expected Flow for Cache Hit:
1. MCP endpoint receives request
2. SearchOrchestrator checks cache (HIT)
3. Returns cached results immediately
4. No external search triggered
5. Much faster response time
"""

import asyncio
import httpx
import json
import time
from datetime import datetime


async def test_mcp_cache_hit():
    """Test MCP cache hit scenario with identical queries."""
    
    # Base URL for the MCP endpoint
    # When running from API container, use localhost
    base_url = "http://localhost:3000/api/v1/mcp"
    
    # Test query that should be cached
    test_query = {
        "query": "python asyncio tutorial examples best practices",
        "workspace": "python_docs",
        "technology_hint": "python",
        "max_results": 10,
        "force_external": False  # Allow cache to be used
    }
    
    print("=" * 80)
    print("MCP Cache Hit E2E Test")
    print("=" * 80)
    print(f"Test started at: {datetime.now().isoformat()}")
    print(f"Base URL: {base_url}")
    print(f"Test Query: {json.dumps(test_query, indent=2)}")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # First query - Expected to be a cache miss
            print("\n1. FIRST QUERY (Expected Cache Miss)")
            print("-" * 40)
            
            start_time_1 = time.time()
            response_1 = await client.post(
                f"{base_url}/search",
                json=test_query,
                headers={"Content-Type": "application/json"}
            )
            end_time_1 = time.time()
            duration_1 = (end_time_1 - start_time_1) * 1000  # Convert to milliseconds
            
            print(f"Status Code: {response_1.status_code}")
            print(f"Response Time: {duration_1:.2f}ms")
            
            if response_1.status_code == 200:
                data_1 = response_1.json()
                print(f"Cache Hit: {data_1.get('cache_hit', False)}")
                print(f"Correlation ID: {data_1.get('correlation_id', 'N/A')}")
                print(f"Number of Results: {len(data_1.get('results', []))}")
                print(f"Execution Time (reported): {data_1.get('execution_time_ms', 'N/A')}ms")
                
                # Display first result if available
                if data_1.get('results'):
                    first_result = data_1['results'][0]
                    print(f"\nFirst Result:")
                    print(f"  Title: {first_result.get('title', 'N/A')}")
                    print(f"  URL: {first_result.get('url', 'N/A')}")
                    print(f"  Provider: {first_result.get('provider', 'N/A')}")
                    print(f"  Score: {first_result.get('relevance_score', 'N/A')}")
            else:
                print(f"Error Response: {response_1.text}")
            
            # Wait a moment to ensure cache is properly written
            print("\nWaiting 2 seconds to ensure cache is written...")
            await asyncio.sleep(2)
            
            # Second query - Expected to be a cache hit
            print("\n2. SECOND QUERY (Expected Cache Hit)")
            print("-" * 40)
            
            start_time_2 = time.time()
            response_2 = await client.post(
                f"{base_url}/search",
                json=test_query,  # Identical query
                headers={"Content-Type": "application/json"}
            )
            end_time_2 = time.time()
            duration_2 = (end_time_2 - start_time_2) * 1000  # Convert to milliseconds
            
            print(f"Status Code: {response_2.status_code}")
            print(f"Response Time: {duration_2:.2f}ms")
            
            if response_2.status_code == 200:
                data_2 = response_2.json()
                print(f"Cache Hit: {data_2.get('cache_hit', False)}")
                print(f"Correlation ID: {data_2.get('correlation_id', 'N/A')}")
                print(f"Number of Results: {len(data_2.get('results', []))}")
                print(f"Execution Time (reported): {data_2.get('execution_time_ms', 'N/A')}ms")
                
                # Verify cache hit
                cache_hit = data_2.get('cache_hit', False)
                if cache_hit:
                    print("\n✅ CACHE HIT CONFIRMED!")
                else:
                    print("\n❌ CACHE MISS - This was expected to be a cache hit!")
            else:
                print(f"Error Response: {response_2.text}")
            
            # Performance comparison
            print("\n3. PERFORMANCE COMPARISON")
            print("-" * 40)
            print(f"First Query Time: {duration_1:.2f}ms")
            print(f"Second Query Time: {duration_2:.2f}ms")
            
            if duration_2 < duration_1:
                speedup = (duration_1 - duration_2) / duration_1 * 100
                print(f"✅ Cache Hit was {speedup:.1f}% faster")
            else:
                print("❌ Cache Hit was not faster - unexpected!")
            
            # Result comparison
            print("\n4. RESULT COMPARISON")
            print("-" * 40)
            
            if response_1.status_code == 200 and response_2.status_code == 200:
                results_1 = data_1.get('results', [])
                results_2 = data_2.get('results', [])
                
                print(f"First query results: {len(results_1)}")
                print(f"Second query results: {len(results_2)}")
                
                if len(results_1) == len(results_2):
                    print("✅ Same number of results")
                    
                    # Check if results are identical
                    results_match = True
                    for i, (r1, r2) in enumerate(zip(results_1, results_2)):
                        if r1.get('url') != r2.get('url') or r1.get('title') != r2.get('title'):
                            results_match = False
                            print(f"❌ Result {i+1} differs")
                            break
                    
                    if results_match:
                        print("✅ Results are identical")
                else:
                    print("❌ Different number of results")
            
            # Test with slight query variation
            print("\n5. TESTING CACHE WITH QUERY VARIATION")
            print("-" * 40)
            
            # Slightly different query (extra space)
            varied_query = test_query.copy()
            varied_query['query'] = "python asyncio tutorial examples  best practices"  # Extra space
            
            response_3 = await client.post(
                f"{base_url}/search",
                json=varied_query,
                headers={"Content-Type": "application/json"}
            )
            
            if response_3.status_code == 200:
                data_3 = response_3.json()
                cache_hit_3 = data_3.get('cache_hit', False)
                print(f"Query with extra space - Cache Hit: {cache_hit_3}")
                
                if cache_hit_3:
                    print("✅ Cache normalization working - minor variations still hit cache")
                else:
                    print("ℹ️  Cache is exact match only - variations cause cache miss")
            
            # Summary
            print("\n" + "=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            
            success_criteria = []
            
            # Check cache hit occurred
            if response_2.status_code == 200 and data_2.get('cache_hit', False):
                success_criteria.append("✅ Cache hit occurred on second query")
            else:
                success_criteria.append("❌ Cache hit did not occur on second query")
            
            # Check performance improvement
            if duration_2 < duration_1:
                success_criteria.append(f"✅ Cache hit was faster ({speedup:.1f}% improvement)")
            else:
                success_criteria.append("❌ Cache hit was not faster")
            
            # Check results consistency
            if response_1.status_code == 200 and response_2.status_code == 200:
                if len(data_1.get('results', [])) == len(data_2.get('results', [])):
                    success_criteria.append("✅ Results are consistent between queries")
                else:
                    success_criteria.append("❌ Results differ between queries")
            
            for criteria in success_criteria:
                print(criteria)
            
            # Final verdict
            all_passed = all("✅" in criteria for criteria in success_criteria)
            print("\n" + "=" * 80)
            if all_passed:
                print("✅ ALL TESTS PASSED - Cache is working correctly!")
            else:
                print("❌ SOME TESTS FAILED - Cache may have issues")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ ERROR during test: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_mcp_cache_hit())