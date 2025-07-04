#!/bin/bash

echo "============================================================"
echo "Testing Context7 with Simple Fallback"
echo "============================================================"

BASE_URL="http://localhost:4080/api/v1"

# First, ensure Context7 provider is registered
echo "1. Checking Context7 provider registration..."
curl -s -X GET "${BASE_URL}/mcp/providers" | jq '.providers[] | select(.provider_id == "context7") | {id: .provider_id, status: .health.status, enabled: .config.enabled}'

# Force a restart to ensure fresh state
echo -e "\n2. Restarting API service to clear state..."
docker-compose restart api
sleep 10  # Wait for service to be ready

# Now test with a known working technology (Next.js)
echo -e "\n3. Testing Next.js search through MCP..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Next.js app directory metadata",
    "use_external_search": true,
    "provider_ids": ["context7"],
    "max_results": 5
  }')

echo "$RESPONSE" | jq '.'

# Check logs for Context7 activity
echo -e "\n4. Checking logs for Context7 activity..."
docker-compose logs --tail=50 api 2>&1 | grep -E "context7|PIPELINE_METRICS.*context7|simple.*external.*search|fallback"

# Test direct Context7 provider if available
echo -e "\n5. Testing through regular search with external flag..."
curl -s -X POST "${BASE_URL}/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Next.js metadata export app directory",
    "limit": 5,
    "use_external_search": true
  }' | jq '{total: .total, has_external: .external_results}'