#!/bin/bash
# MCP Endpoint Search Example with Context7

echo "=== MCP ENDPOINT SEARCH WITH CONTEXT7 ==="
echo "Searching for: 'Python async await'"
echo ""

# Execute the search
curl -X POST http://localhost:4080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "docaiche_search",
      "arguments": {
        "query": "Python async await",
        "use_external_search": true,
        "limit": 3,
        "include_metadata": true
      }
    },
    "id": 1
  }' | python3 -m json.tool

echo ""
echo "=== KEY POINTS ==="
echo "- Method: tools/call"
echo "- Tool: docaiche_search"
echo "- External Search: true (uses Context7)"
echo "- Results are cached with TTL"
echo "- Subsequent identical queries will be faster"