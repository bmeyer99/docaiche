#!/bin/bash

echo "============================================================"
echo "Debug Context7 Metadata Flow"
echo "============================================================"

BASE_URL="http://localhost:4080/api/v1"

# Enable debug logging
echo "1. Testing with debug logging..."
docker-compose logs --tail=0 -f api > /tmp/context7_debug.log 2>&1 &
LOG_PID=$!

sleep 2

# Make request
echo "2. Making Context7 request..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Next.js useState hook",
    "use_external_search": true,
    "provider_ids": ["context7"],
    "max_results": 1
  }')

sleep 2
kill $LOG_PID 2>/dev/null

echo "3. Response received:"
echo "$RESPONSE" | jq '.'

echo -e "\n4. Checking logs for metadata flow..."
echo "Looking for metadata in logs:"
grep -i "metadata\|ttl_seconds" /tmp/context7_debug.log | tail -20

echo -e "\n5. Checking for result transformation:"
grep -E "result_dict|Converting results|external_results" /tmp/context7_debug.log | tail -10

# Direct test to Context7 provider
echo -e "\n6. Testing direct Context7 endpoint..."
curl -s -X GET "${BASE_URL}/mcp/context7/fetch?library=next.js&topic=useState" | jq '.documentation[0].metadata // "NO METADATA"'

rm -f /tmp/context7_debug.log