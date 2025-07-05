#!/bin/bash

echo "Testing Vector Tab Fix..."
echo "========================="

# Test the providers endpoint with timeout
echo -e "\n1. Testing providers endpoint (should timeout or return fallback):"
curl -s -m 3 http://localhost:4080/api/v1/providers 2>&1 | head -5

# Test if admin UI is accessible
echo -e "\n2. Testing admin UI health:"
curl -s http://localhost:4080/api/health | jq '.'

# Check container logs for provider loading
echo -e "\n3. Recent admin-ui logs related to providers:"
docker-compose logs admin-ui --tail 100 | grep -i "provider" | tail -10

echo -e "\n4. Testing vector search functionality through admin UI proxy:"
# This would simulate what the UI does
curl -s -X GET http://localhost:4080/api/v1/weaviate/config 2>&1 | head -20

echo -e "\nTest complete. The Vector tab should now:"
echo "- Load without crashing even when /api/v1/providers times out"
echo "- Show fallback providers (Ollama, OpenAI, Anthropic, etc.)"
echo "- Display helpful messages when no providers are available"
echo "- Allow basic functionality with limited data"