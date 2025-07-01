#!/bin/bash

# MCP End-to-End Test Script
# Tests all MCP functionality through the admin-ui proxy

BASE_URL="http://localhost:4080/api/v1/mcp"
CONTENT_TYPE="Content-Type: application/json"

echo "=== MCP End-to-End Testing ==="
echo

# Test 1: Basic connectivity
echo "1. Testing basic connectivity..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"jsonrpc": "2.0", "method": "invalid", "id": 1}' | jq -r '.error.message'
echo

# Test 2: List available tools
echo "2. Listing available tools..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}' | jq '.result.tools[] | {name, description}'
echo

# Test 3: List available resources
echo "3. Listing available resources..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{"jsonrpc": "2.0", "method": "resources/list", "id": 3}' | jq '.result.resources[] | {uri, description}'
echo

# Test 4: Execute search tool
echo "4. Testing search tool..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "docaiche_search",
      "arguments": {
        "query": "python async",
        "technology": "python",
        "limit": 3
      }
    },
    "id": 4
  }' | jq '.result.content[0].text | {query, technology, returned_count, execution_time_ms}'
echo

# Test 5: Read status resource
echo "5. Reading system status..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "params": {
      "uri": "docaiche://status"
    },
    "id": 5
  }' | jq '.result.text | {overall_status, timestamp, services: .services | keys}'
echo

# Test 6: Read collections resource
echo "6. Reading collections..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "params": {
      "uri": "docaiche://collections"
    },
    "id": 6
  }' | jq '.result.text | {total_collections, collections: .collections}'
echo

# Test 7: Error handling - missing parameters
echo "7. Testing error handling (missing params)..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "docaiche_search"
    },
    "id": 7
  }' | jq '.error | {code, message}'
echo

# Test 8: Error handling - invalid tool
echo "8. Testing error handling (invalid tool)..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "invalid_tool",
      "arguments": {}
    },
    "id": 8
  }' | jq '.error | {code, message, data}'
echo

# Test 9: JSON-RPC compliance - notification (no id)
echo "9. Testing JSON-RPC notification..."
curl -s -X POST $BASE_URL \
  -H "$CONTENT_TYPE" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list"
  }' | jq '.'
echo

# Test 10: Concurrent requests
echo "10. Testing concurrent requests..."
{
  curl -s -X POST $BASE_URL -H "$CONTENT_TYPE" -d '{"jsonrpc": "2.0", "method": "tools/list", "id": "c1"}' &
  curl -s -X POST $BASE_URL -H "$CONTENT_TYPE" -d '{"jsonrpc": "2.0", "method": "resources/list", "id": "c2"}' &
  curl -s -X POST $BASE_URL -H "$CONTENT_TYPE" -d '{"jsonrpc": "2.0", "method": "resources/read", "params": {"uri": "docaiche://status"}, "id": "c3"}' &
  wait
} | jq -s '.[].id'
echo

echo "=== End-to-End Testing Complete ==="