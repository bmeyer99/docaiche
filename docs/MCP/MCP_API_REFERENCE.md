# MCP API Reference

## Overview

The DocaiChe MCP (Model Context Protocol) server provides AI agents with intelligent documentation search and ingestion capabilities. This API reference covers all available tools, resources, and configuration options.

## Authentication

The MCP server supports OAuth 2.1 authentication with Resource Indicators (RFC 8707).

### OAuth 2.1 Flow

```json
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=your_client_id
&client_secret=your_client_secret
&resource=urn:docaiche:api:v1
&scope=search:read ingest:write
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "search:read ingest:write",
  "resource": "urn:docaiche:api:v1"
}
```

### Required Scopes

| Operation | Required Scope |
|-----------|---------------|
| Search documentation | `search:read` |
| Ingest documentation | `ingest:write` |
| Access collections | `collections:read` |
| Submit feedback | `feedback:write` |
| View status | `status:read` |

## Tools

### docaiche/search

Search for documentation content with intelligent caching and relevance scoring.

**Input Schema:**
```typescript
{
  "query": string;           // Search query
  "collection"?: string;     // Optional: specific collection
  "max_results"?: number;    // Optional: max results (default: 10)
  "include_metadata"?: boolean; // Optional: include metadata
}
```

**Output Schema:**
```typescript
{
  "results": [
    {
      "uri": string;         // Document URI
      "title": string;       // Document title
      "snippet": string;     // Relevant text snippet
      "score": number;       // Relevance score (0-1)
      "collection": string;  // Collection name
      "metadata"?: {         // Optional metadata
        "author"?: string;
        "date_modified"?: string;
        "tags"?: string[];
      }
    }
  ],
  "total_count": number;     // Total matching documents
  "query_time_ms": number;   // Query execution time
}
```

**Example:**
```json
{
  "tool": "docaiche/search",
  "arguments": {
    "query": "authentication OAuth",
    "max_results": 5,
    "include_metadata": true
  }
}
```

### docaiche/ingest

Ingest documentation with consent management and validation.

**Input Schema:**
```typescript
{
  "uri": string;             // Document URI
  "content": string;         // Document content
  "metadata": {
    "title": string;         // Document title
    "author"?: string;       // Optional: author
    "tags"?: string[];       // Optional: tags
    "collection": string;    // Target collection
  },
  "consent": {
    "user_confirmed": boolean;  // User consent
    "purpose": string;          // Ingestion purpose
  }
}
```

**Output Schema:**
```typescript
{
  "status": "success" | "failed";
  "document_id": string;        // Assigned document ID
  "validation_results": {
    "content_valid": boolean;
    "metadata_valid": boolean;
    "consent_valid": boolean;
  },
  "indexing_time_ms": number;
}
```

**Example:**
```json
{
  "tool": "docaiche/ingest",
  "arguments": {
    "uri": "https://docs.example.com/api/auth",
    "content": "# Authentication Guide\n\nThis guide covers...",
    "metadata": {
      "title": "Authentication Guide",
      "author": "DevOps Team",
      "tags": ["auth", "security"],
      "collection": "api-docs"
    },
    "consent": {
      "user_confirmed": true,
      "purpose": "Adding API documentation"
    }
  }
}
```

### docaiche/feedback

Submit feedback for search results or documentation quality.

**Input Schema:**
```typescript
{
  "type": "search_relevance" | "doc_quality" | "general";
  "target_uri"?: string;      // Optional: specific document
  "query"?: string;           // Optional: search query
  "rating"?: number;          // Optional: 1-5 rating
  "comment": string;          // Feedback text
  "metadata"?: {              // Optional metadata
    "user_role"?: string;
    "use_case"?: string;
  }
}
```

**Output Schema:**
```typescript
{
  "feedback_id": string;      // Unique feedback ID
  "status": "received";
  "timestamp": string;        // ISO 8601 timestamp
}
```

## Resources

### docaiche/collections

List available documentation collections.

**URI:** `docaiche://collections`

**Response Schema:**
```typescript
{
  "collections": [
    {
      "name": string;         // Collection identifier
      "display_name": string; // Human-readable name
      "description": string;  // Collection description
      "document_count": number; // Number of documents
      "last_updated": string;   // ISO 8601 timestamp
      "access_level": "public" | "restricted";
    }
  ]
}
```

### docaiche/status

Get system status and health information.

**URI:** `docaiche://status`

**Response Schema:**
```typescript
{
  "status": "healthy" | "degraded" | "unhealthy";
  "version": string;          // MCP server version
  "uptime_seconds": number;
  "components": {
    "search_engine": {
      "status": string;
      "latency_ms": number;
    },
    "ingestion_pipeline": {
      "status": string;
      "queue_depth": number;
    },
    "cache": {
      "status": string;
      "hit_rate": number;
      "size_mb": number;
    }
  },
  "metrics": {
    "total_searches": number;
    "total_documents": number;
    "avg_search_time_ms": number;
  }
}
```

## Transport

The MCP server supports Streamable HTTP transport with automatic protocol negotiation.

### Connection Options

```typescript
{
  "transport": "http",
  "endpoint": "https://mcp.docaiche.example.com",
  "options": {
    "protocol": "http/2" | "http/1.1",  // Auto-negotiated
    "compression": "gzip" | "br",        // Supported compression
    "keepalive": true,
    "timeout_ms": 30000,
    "retry": {
      "max_attempts": 3,
      "backoff_ms": [100, 500, 2000]
    }
  }
}
```

### WebSocket Fallback

For real-time updates and streaming:

```typescript
{
  "transport": "websocket",
  "endpoint": "wss://mcp.docaiche.example.com/ws",
  "options": {
    "heartbeat_interval_ms": 30000,
    "reconnect": true
  }
}
```

## Error Handling

### Error Response Format

```typescript
{
  "error": {
    "code": string;           // Error code
    "message": string;        // Human-readable message
    "details"?: any;          // Optional error details
    "request_id": string;     // Request correlation ID
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `AUTH_REQUIRED` | 401 | Authentication required |
| `INVALID_TOKEN` | 401 | Invalid or expired token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `INTERNAL_ERROR` | 500 | Server error |

## Rate Limiting

The API implements token bucket rate limiting:

- **Default limits:**
  - Search: 100 requests/minute
  - Ingest: 10 requests/minute
  - Feedback: 50 requests/minute

- **Headers:**
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

## Monitoring Endpoints

### Health Check

```
GET /health
```

Returns overall system health (always 200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-09T10:30:00Z",
  "components": {...}
}
```

### Metrics

```
GET /metrics
```

Returns Prometheus-formatted metrics:
```
# HELP mcp_requests_total Total MCP requests
# TYPE mcp_requests_total counter
mcp_requests_total{method="tools/call",status="success"} 1234
```

### Ready Check

```
GET /ready
```

Returns 200 if ready, 503 if not ready.

## Security Considerations

1. **Always use HTTPS** for production deployments
2. **Rotate client secrets** regularly
3. **Implement consent** for all data ingestion
4. **Monitor rate limits** to prevent abuse
5. **Use correlation IDs** for request tracing

## SDK Examples

### Python Client

```python
from mcp import MCPClient

# Initialize client
client = MCPClient(
    endpoint="https://mcp.docaiche.example.com",
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# Search documentation
results = await client.call_tool(
    "docaiche/search",
    {
        "query": "authentication",
        "max_results": 10
    }
)

# Ingest documentation
response = await client.call_tool(
    "docaiche/ingest",
    {
        "uri": "https://docs.example.com/guide",
        "content": "...",
        "metadata": {...},
        "consent": {
            "user_confirmed": True,
            "purpose": "Documentation update"
        }
    }
)
```

### JavaScript/TypeScript Client

```typescript
import { MCPClient } from '@anthropic/mcp';

// Initialize client
const client = new MCPClient({
  endpoint: 'https://mcp.docaiche.example.com',
  auth: {
    clientId: 'your_client_id',
    clientSecret: 'your_client_secret'
  }
});

// Search documentation
const results = await client.callTool('docaiche/search', {
  query: 'authentication',
  maxResults: 10
});

// Access resources
const collections = await client.readResource('docaiche://collections');
```

## Changelog

### v1.0.0 (2024-01-09)
- Initial MCP implementation
- OAuth 2.1 authentication
- Search, ingest, and feedback tools
- Collections and status resources
- Comprehensive monitoring