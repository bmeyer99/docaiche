#!/usr/bin/env python3
"""
Test script to verify synchronous ingestion functionality
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_sync_ingestion():
    """Test search with sync ingestion enabled"""
    base_url = "http://localhost:8080/api/v1"
    
    # Search query that should trigger Context7
    search_query = {
        "query": "how to use react hooks useState documentation",
        "limit": 5,
        "external_providers": ["context7"],
        "use_external_search": True
    }
    
    print(f"\n[{datetime.now().isoformat()}] Testing sync ingestion with query: {search_query['query']}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Execute search
            response = await client.post(
                f"{base_url}/search",
                json=search_query,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Search completed successfully")
                print(f"   - Results found: {result.get('total_count', 0)}")
                print(f"   - Query time: {result.get('query_time_ms', 0)}ms")
                print(f"   - External search used: {result.get('external_search_used', False)}")
                
                # Check for ingestion status
                ingestion_status = result.get('ingestion_status')
                if ingestion_status:
                    print(f"\n📥 Synchronous Ingestion Status:")
                    print(f"   - Success: {ingestion_status.get('success', False)}")
                    print(f"   - Source: {ingestion_status.get('source', 'unknown')}")
                    print(f"   - Type: {ingestion_status.get('type', 'unknown')}")
                    print(f"   - Ingested count: {ingestion_status.get('ingested_count', 0)}")
                    print(f"   - Duration: {ingestion_status.get('duration_ms', 0)}ms")
                else:
                    print("\n⚠️  No ingestion status found in response")
                
                # Show metadata
                if result.get('metadata'):
                    print(f"\n📊 Metadata:")
                    print(json.dumps(result['metadata'], indent=2))
                    
            else:
                print(f"\n❌ Search failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_sync_ingestion())