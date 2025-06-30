# MCP Quick Start Guide

Get up and running with DocaiChe MCP in 5 minutes!

## Prerequisites

- Python 3.8+
- pip
- Basic knowledge of REST APIs

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/docaiche.git
cd docaiche
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment

Create a `.env` file:

```bash
MCP_SECRET_KEY=your-secret-key-here
MCP_CLIENT_ID=demo_client
MCP_CLIENT_SECRET=demo_secret
```

### 4. Start the Server

```bash
python -m src.mcp.main
```

The server will start at `http://localhost:8000`.

## Your First Request

### 1. Get an Access Token

```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=demo_client" \
  -d "client_secret=demo_secret" \
  -d "resource=urn:docaiche:api:v1"
```

Save the `access_token` from the response.

### 2. Search Documentation

```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "docaiche/search",
      "arguments": {
        "query": "authentication",
        "max_results": 5
      }
    }
  }'
```

### 3. Check System Status

```bash
curl -X POST http://localhost:8000/mcp/resources/read \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "resources/read",
    "params": {
      "uri": "docaiche://status"
    }
  }'
```

## Python Client Example

```python
import httpx
import asyncio

async def quick_start():
    # Get token
    token_response = await httpx.post(
        "http://localhost:8000/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "demo_client",
            "client_secret": "demo_secret"
        }
    )
    token = token_response.json()["access_token"]
    
    # Search documentation
    search_response = await httpx.post(
        "http://localhost:8000/mcp/tools/call",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "docaiche/search",
                "arguments": {
                    "query": "getting started",
                    "max_results": 3
                }
            }
        }
    )
    
    results = search_response.json()["result"]
    print(f"Found {results['total_count']} documents")
    
    for doc in results['results']:
        print(f"- {doc['title']} (score: {doc['score']:.2f})")

# Run the example
asyncio.run(quick_start())
```

## JavaScript Client Example

```javascript
// Quick start with fetch
async function quickStart() {
    // Get token
    const tokenResponse = await fetch('http://localhost:8000/oauth/token', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams({
            grant_type: 'client_credentials',
            client_id: 'demo_client',
            client_secret: 'demo_secret'
        })
    });
    const { access_token } = await tokenResponse.json();
    
    // Search documentation
    const searchResponse = await fetch('http://localhost:8000/mcp/tools/call', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${access_token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            id: '1',
            method: 'tools/call',
            params: {
                name: 'docaiche/search',
                arguments: {
                    query: 'getting started',
                    max_results: 3
                }
            }
        })
    });
    
    const { result } = await searchResponse.json();
    console.log(`Found ${result.total_count} documents`);
    
    result.results.forEach(doc => {
        console.log(`- ${doc.title} (score: ${doc.score.toFixed(2)})`);
    });
}

quickStart().catch(console.error);
```

## Available Tools

| Tool | Description | Required Scope |
|------|-------------|----------------|
| `docaiche/search` | Search documentation | `search:read` |
| `docaiche/ingest` | Add new documents | `ingest:write` |
| `docaiche/feedback` | Submit feedback | `feedback:write` |

## Available Resources

| Resource | Description | Required Scope |
|----------|-------------|----------------|
| `docaiche://collections` | List collections | `collections:read` |
| `docaiche://status` | System status | `status:read` |

## What's Next?

1. **Explore the API**: Check out the [API Reference](MCP_API_REFERENCE.md)
2. **Deploy to Production**: Follow the [Deployment Guide](MCP_DEPLOYMENT_GUIDE.md)
3. **Build Custom Tools**: Read the [Developer Guide](MCP_DEVELOPER_GUIDE.md)
4. **Monitor Your System**: Set up [monitoring and alerts](MCP_DEPLOYMENT_GUIDE.md#monitoring-setup)

## Common Issues

### Authentication Failed

Make sure your client credentials are correct and the server is running.

### Connection Refused

Check that the server is running on the correct port:
```bash
netstat -an | grep 8000
```

### Rate Limited

The default rate limit is 100 requests per minute. Implement exponential backoff in your client.

## Need Help?

- 📖 [Full Documentation](README.md)
- 🐛 [Report Issues](https://github.com/your-org/docaiche/issues)
- 💬 [Community Forum](https://forum.docaiche.example.com)