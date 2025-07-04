#!/bin/bash

echo "============================================================"
echo "Verifying TTL Metadata in Context7 Results"
echo "============================================================"

BASE_URL="http://localhost:4080/api/v1"

echo "1. Fetching Context7 results with full metadata..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "React useState hook",
    "use_external_search": true,
    "provider_ids": ["context7"],
    "max_results": 2
  }')

# Save full response
echo "$RESPONSE" > /tmp/context7_response.json

# Check if we got results
RESULT_COUNT=$(echo "$RESPONSE" | jq '.total_results')
echo "   Total results: $RESULT_COUNT"

if [ "$RESULT_COUNT" -gt 0 ]; then
    echo -e "\n2. Checking TTL metadata in first result..."
    echo "$RESPONSE" | jq '.results[0] | {
        title: .title,
        provider: .provider,
        metadata: .metadata
    }'
    
    # Check specifically for TTL
    TTL=$(echo "$RESPONSE" | jq -r '.results[0].metadata.ttl_seconds // "NOT FOUND"')
    PRIORITY=$(echo "$RESPONSE" | jq -r '.results[0].metadata.ingestion_priority // "NOT FOUND"')
    TECHNOLOGY=$(echo "$RESPONSE" | jq -r '.results[0].metadata.technology // "NOT FOUND"')
    
    echo -e "\n3. TTL Metadata Summary:"
    echo "   - TTL seconds: $TTL"
    echo "   - Ingestion priority: $PRIORITY"
    echo "   - Technology: $TECHNOLOGY"
    
    if [ "$TTL" != "NOT FOUND" ]; then
        echo "   ✅ TTL metadata is present and ready for ingestion!"
    else
        echo "   ❌ TTL metadata is missing"
    fi
else
    echo "   ❌ No results returned. Checking logs..."
    docker-compose logs --tail=20 api 2>&1 | grep -i "context7\|error"
fi

echo -e "\n4. Testing other technologies for TTL..."
for TECH in "typescript interfaces" "vue composition api" "svelte stores"; do
    echo -e "\n   Testing: $TECH"
    RESULT=$(curl -s -X POST "${BASE_URL}/mcp/search" \
      -H "Content-Type: application/json" \
      -d "{
        \"query\": \"$TECH\",
        \"use_external_search\": true,
        \"provider_ids\": [\"context7\"],
        \"max_results\": 1
      }")
    
    TTL=$(echo "$RESULT" | jq -r '.results[0].metadata.ttl_seconds // "N/A"')
    TECH_DETECTED=$(echo "$RESULT" | jq -r '.results[0].metadata.technology // "N/A"')
    echo "     - Technology: $TECH_DETECTED, TTL: $TTL seconds"
done

echo -e "\n============================================================"
echo "Context7 TTL Integration Summary"
echo "============================================================"