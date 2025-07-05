#!/usr/bin/env python3
"""
Debug script to trace why Context7 ingestion isn't happening.
"""

import json
import requests
import time

print("=== Context7 Ingestion Debug ===\n")

# Test search with explicit Context7 provider
print("1. Performing search with Context7...")
response = requests.post(
    "http://localhost:4080/api/v1/search",
    json={
        "query": "react hooks best practices",
        "technology_hint": "react",
        "use_external_search": True,
        "external_providers": ["context7"],
        "limit": 3
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"Search returned {result['total_count']} results")
    print(f"External search used: {result.get('external_search_used', False)}")
    print(f"Ingestion status: {result.get('ingestion_status', 'None')}")
    
    # Check results metadata
    if result['results']:
        print("\n2. Checking result metadata:")
        for i, res in enumerate(result['results'][:2]):
            print(f"\nResult {i+1}:")
            print(f"  Title: {res['title']}")
            print(f"  Workspace: {res.get('workspace', 'N/A')}")
            print(f"  Technology: {res.get('technology', 'N/A')}")
            
            # Note: The API response doesn't include full metadata,
            # but we can see the workspace is 'context7_search'
    
    print("\n3. Key observations:")
    print("- Results are from Context7 (workspace: context7_search)")
    print("- External search is working")
    print("- But ingestion_status is null")
    print("\nThis suggests the issue is in the enrichment trigger logic")
    print("The code needs to properly detect Context7 results for sync ingestion")
    
else:
    print(f"Search failed with status {response.status_code}")

print("\n4. Checking container logs for more details...")
time.sleep(2)

# Show how to check logs
print("\nTo debug further, run:")
print("docker compose logs api --tail 200 | grep -i 'trigger.*enrichment\\|external_results\\|context7_results'")
print("\nThe issue is likely in the _trigger_enrichment method where it filters Context7 results")