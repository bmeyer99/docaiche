#!/bin/bash

echo "=== Testing Vector Tab Debug ==="

# Test 1: Check if the search config page loads
echo "1. Testing search config page load..."
response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:4080/dashboard/search-config")
if [ "$response" = "200" ]; then
    echo "✓ Search config page loads successfully"
else
    echo "✗ Search config page failed to load (HTTP $response)"
fi

# Test 2: Check provider API directly  
echo "2. Testing provider API..."
providers=$(curl -s "http://localhost:4080/api/v1/providers" | jq length 2>/dev/null)
if [ "$providers" -gt 0 ] 2>/dev/null; then
    echo "✓ Provider API returns $providers providers"
    
    # Check Ollama specifically
    ollama_status=$(curl -s "http://localhost:4080/api/v1/providers" | jq -r '.[] | select(.id=="ollama") | .status' 2>/dev/null)
    ollama_embedding=$(curl -s "http://localhost:4080/api/v1/providers" | jq -r '.[] | select(.id=="ollama") | .supports_embedding' 2>/dev/null)
    
    echo "  - Ollama status: $ollama_status"
    echo "  - Ollama supports embedding: $ollama_embedding"
else
    echo "✗ Provider API failed or returned no providers"
fi

# Test 3: Check if admin-ui can access the API
echo "3. Testing admin-ui API access..."
if docker-compose exec -T admin-ui wget -q --spider http://api:4000/api/v1/providers; then
    echo "✓ Admin-UI can reach API service"
else
    echo "✗ Admin-UI cannot reach API service"
fi

# Test 4: Check recent logs for debugging output
echo "4. Checking for debugging output in admin-ui logs..."
recent_logs=$(docker-compose logs admin-ui --tail=50 2>/dev/null | grep -E "\[VectorSearch\]|\[API\]" | head -5)
if [ -n "$recent_logs" ]; then
    echo "✓ Found debugging output:"
    echo "$recent_logs"
else
    echo "⚠ No debugging output found yet (may need user interaction)"
fi

echo "=== Test Complete ==="
echo ""
echo "Next steps:"
echo "1. Open http://localhost:4080/dashboard/search-config in browser"
echo "2. Click on the Vector tab"
echo "3. Open browser dev tools (F12) and check console"
echo "4. Look for [VectorSearch] debugging messages"