#!/bin/bash
# Test configuration update API endpoint

echo "Testing configuration update API..."

# Test 1: Update a simple string value
echo -e "\n1. Testing simple string update..."
curl -X POST http://localhost:4080/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "key": "test.simple_string",
    "value": "Hello World"
  }' \
  -w "\nHTTP Status: %{http_code}\n"

# Wait a moment for background task
sleep 2

# Test 2: Update a complex JSON value
echo -e "\n\n2. Testing complex JSON update..."
curl -X POST http://localhost:4080/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "key": "mcp.external_search.providers.test_provider",
    "value": {
      "enabled": true,
      "api_key": "test-key-123",
      "settings": {
        "timeout": 30,
        "retries": 3
      }
    }
  }' \
  -w "\nHTTP Status: %{http_code}\n"

# Wait for update to complete
sleep 2

# Test 3: Get configuration to verify
echo -e "\n\n3. Retrieving configuration..."
curl -X GET http://localhost:4080/api/v1/config \
  -H "Content-Type: application/json" | jq '.'

echo -e "\n\n✅ Test completed. Check if updates were successful without SQL errors."