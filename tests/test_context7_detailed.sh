#!/bin/bash

echo "============================================================"
echo "Detailed Context7 Integration Test"
echo "============================================================"

BASE_URL="http://localhost:4080/api/v1"

# Clear logs first
echo "Clearing previous logs..."
docker-compose logs --tail=0 -f api > /tmp/api_logs.txt 2>&1 &
LOG_PID=$!
sleep 2

echo -e "\n1. Testing internal search (baseline)..."
curl -s -X POST "${BASE_URL}/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Next.js metadata",
    "limit": 5
  }' | jq '.total'

echo -e "\n2. Testing MCP search with external flag..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Next.js app router metadata export",
    "use_external_search": true,
    "max_results": 5
  }')

echo "$RESPONSE" | jq '.'

# Kill log capture
kill $LOG_PID 2>/dev/null

echo -e "\n3. Analyzing flow..."
echo "API Logs showing Context7 flow:"
echo "--------------------------------"
grep -E "context7|external.*search|PIPELINE_METRICS|ttl_seconds|orchestrator.*search" /tmp/api_logs.txt | tail -30

echo -e "\n4. Summary:"
echo "- Total results: $(echo "$RESPONSE" | jq '.total_results')"
echo "- Providers used: $(echo "$RESPONSE" | jq '.providers_used')"
echo "- Cache hit: $(echo "$RESPONSE" | jq '.cache_hit')"

# Check if Context7 was actually called
if grep -q "context7_http_request_success" /tmp/api_logs.txt; then
    echo "- Context7 HTTP request: ✓ SUCCESS"
else
    echo "- Context7 HTTP request: ✗ NOT CALLED or FAILED"
fi

if grep -q "ttl_seconds" /tmp/api_logs.txt; then
    echo "- TTL metadata present: ✓ YES"
else
    echo "- TTL metadata present: ✗ NO"
fi

rm -f /tmp/api_logs.txt