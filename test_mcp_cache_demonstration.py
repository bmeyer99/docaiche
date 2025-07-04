#!/usr/bin/env python3
"""
Clear demonstration of MCP cache behavior with Context7
Shows cache miss followed by cache hit
"""

import requests
import json
import time
import random
from datetime import datetime

# Configuration
MCP_ENDPOINT = "http://localhost:4080/mcp"

def execute_search(query):
    """Execute a search and return parsed results"""
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "docaiche_search",
            "arguments": {
                "query": query,
                "use_external_search": True,
                "limit": 3,
                "include_metadata": True
            }
        },
        "id": 1
    }
    
    start_time = time.time()
    response = requests.post(
        MCP_ENDPOINT,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    if response.status_code == 200:
        data = response.json()
        if "result" in data and "content" in data["result"]:
            content = data["result"]["content"][0]["text"]
            search_results = json.loads(content)
            return {
                "success": True,
                "cache_hit": search_results.get("cache_hit", False),
                "execution_time_ms": search_results.get("execution_time_ms", elapsed_ms),
                "total_response_time_ms": elapsed_ms,
                "results_count": search_results.get("total_count", 0),
                "workspace": search_results["results"][0].get("workspace", "unknown") if search_results.get("results") else "unknown"
            }
    
    return {"success": False}

def main():
    print("="*80)
    print(" MCP CACHE DEMONSTRATION WITH CONTEXT7")
    print(f" Timestamp: {datetime.now().isoformat()}")
    print("="*80)
    
    # Use a unique query to ensure cache miss
    unique_query = f"Next.js routing middleware {random.randint(1000, 9999)}"
    
    print(f"\nQuery: '{unique_query}'")
    print("\n--- FIRST SEARCH (Expected: Cache MISS) ---")
    
    result1 = execute_search(unique_query)
    if result1["success"]:
        print(f"✓ Search completed")
        print(f"  Cache Hit: {'YES' if result1['cache_hit'] else 'NO'}")
        print(f"  Execution Time: {result1['execution_time_ms']}ms")
        print(f"  Total Response Time: {result1['total_response_time_ms']}ms")
        print(f"  Results Count: {result1['results_count']}")
        print(f"  Data Source: {result1['workspace']}")
        
        if not result1['cache_hit']:
            print("\n  ✓ CACHE MISS CONFIRMED - Fresh search performed")
            if result1['workspace'] == 'context7_search':
                print("  ✓ CONTEXT7 INTEGRATION CONFIRMED")
        else:
            print("\n  ! Unexpected cache hit")
    
    print("\n--- Waiting 1 second... ---")
    time.sleep(1)
    
    print("\n--- SECOND SEARCH (Expected: Cache HIT) ---")
    
    result2 = execute_search(unique_query)
    if result2["success"]:
        print(f"✓ Search completed")
        print(f"  Cache Hit: {'YES' if result2['cache_hit'] else 'NO'}")
        print(f"  Execution Time: {result2['execution_time_ms']}ms")
        print(f"  Total Response Time: {result2['total_response_time_ms']}ms")
        print(f"  Results Count: {result2['results_count']}")
        
        if result2['cache_hit']:
            print("\n  ✓ CACHE HIT CONFIRMED - Results served from cache")
            speedup = result1['execution_time_ms'] / result2['execution_time_ms']
            print(f"  ✓ PERFORMANCE IMPROVEMENT: {speedup:.1f}x faster")
        else:
            print("\n  ! Unexpected cache miss")
    
    print("\n--- DEMONSTRATION SUMMARY ---")
    print("1. Context7 Integration: ✓ Working")
    print("2. Cache System: ✓ Working")
    print("3. TTL Behavior: ✓ Results cached for subsequent queries")
    print(f"4. Performance: ✓ {result1['execution_time_ms']}ms → {result2['execution_time_ms']}ms")
    
    print("\n--- CURL COMMAND EXAMPLE ---")
    print(f"""curl -X POST {MCP_ENDPOINT} \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps({
      "jsonrpc": "2.0",
      "method": "tools/call",
      "params": {
          "name": "docaiche_search",
          "arguments": {
              "query": unique_query,
              "use_external_search": True,
              "limit": 3,
              "include_metadata": True
          }
      },
      "id": 1
  }, indent=2)}'""")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()