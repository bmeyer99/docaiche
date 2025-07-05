#!/bin/bash

echo "============================================================"
echo "Context7 MCP Integration Test (via curl)"
echo "============================================================"

BASE_URL="http://localhost:4080/api/v1"

echo -e "\n1. Testing React useState search with Context7..."
echo "Request:"
cat << EOF
{
  "query": "React useState hook implementation",
  "use_external_search": true,
  "technology_hint": "react",
  "max_results": 10,
  "provider_ids": ["context7_docs"]
}
EOF

echo -e "\n\nResponse:"
curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "React useState hook implementation",
    "use_external_search": true,
    "technology_hint": "react", 
    "max_results": 10,
    "provider_ids": ["context7_docs"]
  }' | jq '.'

echo -e "\n\n2. Testing TypeScript search with Context7..."
curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "TypeScript interface type checking",
    "use_external_search": true,
    "technology_hint": "typescript",
    "max_results": 10
  }' | jq '.total_results, .providers_used'

echo -e "\n\n3. Testing Vue.js search with Context7..."
curl -s -X POST "${BASE_URL}/mcp/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Vue composition API setup function",
    "use_external_search": true,
    "technology_hint": "vue",
    "max_results": 10
  }' | jq '.total_results, .providers_used'

echo -e "\n\n4. Checking Context7 provider status..."
curl -s -X GET "${BASE_URL}/mcp/providers" | jq '.providers[] | select(.provider_id | contains("context7"))'

echo -e "\n\n5. Testing direct Context7 documentation fetch..."
curl -s -X GET "${BASE_URL}/mcp/context7/fetch?library=react&topic=useState" | jq '.'

echo -e "\n\n============================================================"
echo "Checking logs for Context7 activity..."
echo "============================================================"

# Get recent logs with Context7 mentions
echo -e "\nRecent Context7 logs:"
docker-compose logs --tail=50 api 2>&1 | grep -i "context7\|PIPELINE_METRICS.*context7\|ttl_seconds" || echo "No Context7 logs found"

echo -e "\n\nTo monitor real-time Context7 activity, run:"
echo "  docker-compose logs -f api | grep -i context7"