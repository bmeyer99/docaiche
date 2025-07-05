#!/bin/bash

echo "============================================================"
echo "Testing Context7 with Next.js (known working technology)"
echo "============================================================"

BASE_URL="http://localhost:4080/api/v1"

echo -e "\n1. Testing Next.js search with Context7..."
curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Next.js app directory metadata export",
    "use_external_search": true,
    "technology_hint": "nextjs",
    "max_results": 5
  }' | jq '.'

echo -e "\n\n2. Direct Context7 fetch for Next.js..."
curl -s -X GET "${BASE_URL}/mcp/context7/fetch?library=next.js&topic=metadata" | jq '.'

echo -e "\n\n3. Checking logs for successful Context7 fetch..."
docker-compose logs --tail=30 api 2>&1 | grep -E "context7.*success=true|ttl_seconds|PIPELINE_METRICS.*context7.*200"