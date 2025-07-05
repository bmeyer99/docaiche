#!/bin/bash

echo "=== Direct Context7 Search Test ==="
echo

# Test 1: Search with explicit external search flag
echo "1. Testing search with explicit external search enabled..."
curl -X POST http://localhost:4080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "react hooks documentation",
    "technology_hint": "react",
    "use_external_search": true,
    "limit": 5
  }' | jq '.'

echo
echo "2. Checking logs for Context7 activity after search..."
sleep 2
docker compose logs admin-ui --tail 50 | grep -i "context7\|external_search\|ingestion" | tail -10

echo
echo "3. Testing search with Context7 as specific provider..."
curl -X POST http://localhost:4080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "nextjs app router tutorial",
    "technology_hint": "next.js",
    "use_external_search": true,
    "external_providers": ["context7"],
    "limit": 5
  }' | jq '.'

echo
echo "4. Final log check..."
sleep 2
docker compose logs admin-ui --tail 100 | grep -E "PIPELINE_METRICS.*external|context7|c7_|ingestion_status" | tail -10