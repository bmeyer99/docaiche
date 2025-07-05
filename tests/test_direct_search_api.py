#!/usr/bin/env python3
"""
Direct Search API Test
======================

Test the search API directly to verify if external search would be triggered.
"""

import json
import requests
import time
import uuid
from datetime import datetime

def test_direct_search():
    """Test search directly through the API endpoint."""
    
    # Generate unique query
    unique_id = uuid.uuid4().hex[:8]
    query = f"Context7 MCP integration test_{unique_id}"
    
    # Direct API endpoint
    url = "http://localhost:4080/api/v1/search"
    
    # Search parameters
    params = {
        "q": query,  # API expects 'q' not 'query'
        "technology": "react",
        "limit": 10,
        "use_external_search": True  # Explicitly request external search
    }
    
    print("=" * 80)
    print("Direct Search API Test")
    print("=" * 80)
    print(f"Test ID: {unique_id}")
    print(f"Query: {query}")
    print(f"URL: {url}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        duration_ms = int((time.time() - start_time) * 1000)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Time: {duration_ms}ms")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nResults:")
            print(f"- Total Count: {data.get('total_count', 0)}")
            print(f"- Cache Hit: {data.get('cache_hit', False)}")
            print(f"- Query Time: {data.get('query_time_ms', 0)}ms")
            print(f"- External Search Used: {data.get('external_search_used', False)}")
            
            results = data.get('results', [])
            print(f"\nFound {len(results)} results:")
            for i, result in enumerate(results[:3]):
                print(f"\n{i+1}. {result.get('title', 'No title')}")
                print(f"   URL: {result.get('source_url', 'No URL')}")
                print(f"   Score: {result.get('relevance_score', 0)}")
                print(f"   Workspace: {result.get('workspace', 'Unknown')}")
                
        else:
            print(f"\nError Response: {response.text}")
            
    except Exception as e:
        print(f"\nRequest failed: {e}")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    test_direct_search()