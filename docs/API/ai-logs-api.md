# AI Logs API Documentation

## Overview

The AI Logs API provides comprehensive logging, monitoring, and troubleshooting capabilities specifically designed for AI agents and developers working with the DocAIche system. This API enables real-time access to logs from all services, intelligent correlation analysis, pattern detection, and advanced debugging features.

## Base URL

```
https://your-domain.com/api/v1/ai_logs
```

## Authentication

All AI Logs API endpoints use the same authentication as the main DocAIche API. Include your API key in the Authorization header:

```http
Authorization: Bearer your_api_key_here
```

## Rate Limiting

The AI Logs API implements rate limiting to ensure fair usage:

- **Query endpoints**: 60 requests per minute per IP
- **WebSocket connections**: 10 concurrent connections per IP
- **Export endpoints**: 10 requests per minute per IP
- **Real-time endpoints**: 120 requests per minute per IP

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

## Endpoints

### 1. Query Logs

**GET** `/query`

Retrieve and filter logs based on various criteria with intelligent query optimization.

#### Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `mode` | string | No | Query optimization mode: `troubleshoot`, `performance`, `errors`, `security`, `audit` | `troubleshoot` |
| `services` | array[string] | No | Filter by specific services: `api`, `admin-ui`, `anythingllm`, `redis`, `loki`, etc. | `["all"]` |
| `time_range` | string | No | Time range in format: `1h`, `24h`, `7d`, `30d` | `1h` |
| `start_time` | string | No | ISO 8601 timestamp for range start | - |
| `end_time` | string | No | ISO 8601 timestamp for range end | - |
| `correlation_id` | string | No | Filter by specific correlation ID | - |
| `conversation_id` | string | No | Filter by conversation ID | - |
| `session_id` | string | No | Filter by user session ID | - |
| `workspace_id` | string | No | Filter by workspace ID | - |
| `severity` | array[string] | No | Log levels: `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL` | `["WARN", "ERROR", "CRITICAL"]` |
| `models` | array[string] | No | Filter by AI models used | - |
| `min_tokens` | integer | No | Minimum token usage threshold | - |
| `max_tokens` | integer | No | Maximum token usage threshold | - |
| `search_text` | string | No | Full-text search in log messages | - |
| `limit` | integer | No | Maximum results to return (1-1000) | `100` |
| `offset` | integer | No | Pagination offset | `0` |
| `cache` | boolean | No | Use cached results if available | `true` |

#### Response

```json
{
  "logs": [
    {
      "timestamp": "2025-06-30T14:30:00.123Z",
      "level": "INFO",
      "service": "api",
      "message": "AI request processed successfully",
      "correlation_id": "req_abc123def456",
      "conversation_id": "conv_789xyz",
      "session_id": "sess_user123",
      "workspace_id": "ws_react_docs",
      "model": "gpt-4",
      "tokens_used": 150,
      "duration_ms": 1200,
      "user_id": "user_456",
      "endpoint": "/api/v1/search",
      "status_code": 200,
      "metadata": {
        "query_type": "semantic_search",
        "result_count": 5,
        "cache_hit": false
      }
    }
  ],
  "total_count": 1,
  "query_time_ms": 45,
  "patterns_detected": [
    {
      "pattern_type": "high_token_usage",
      "confidence": 0.85,
      "description": "Token usage is 20% above average"
    }
  ],
  "cached": false,
  "partial_results": false,
  "warnings": []
}
```

#### Status Codes

- `200 OK`: Query successful
- `400 Bad Request`: Invalid parameters
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `503 Service Unavailable`: Loki service unavailable

### 2. Correlation Analysis

**POST** `/correlate`

Analyze the flow of requests across services using correlation IDs to identify bottlenecks and error propagation.

#### Request Body

```json
{
  "correlation_id": "req_abc123def456",
  "include_metrics": true,
  "include_errors": true,
  "service_graph": true
}
```

#### Response

```json
{
  "correlation_id": "req_abc123def456",
  "service_flow": [
    {
      "service": "api",
      "timestamp": "2025-06-30T14:30:00.123Z",
      "duration_ms": 50,
      "status": "success",
      "operation": "receive_request"
    },
    {
      "service": "anythingllm",
      "timestamp": "2025-06-30T14:30:00.200Z",
      "duration_ms": 1100,
      "status": "success",
      "operation": "vector_search"
    }
  ],
  "total_duration_ms": 1150,
  "services_involved": ["api", "anythingllm"],
  "bottlenecks": [
    {
      "service": "anythingllm",
      "avg_duration_ms": 1100,
      "percentage_of_total": 95.7
    }
  ],
  "error_propagation": [],
  "recommendations": [
    "Consider implementing caching for AnythingLLM vector searches",
    "Monitor AnythingLLM service performance"
  ]
}
```

### 3. Pattern Detection

**POST** `/patterns`

Detect common issues, performance patterns, and anomalies in the logs using AI-powered analysis.

#### Request Body

```json
{
  "time_range": "24h",
  "services": ["api", "anythingllm"],
  "min_confidence": 0.8,
  "pattern_types": ["errors", "performance", "security", "rate_limiting"],
  "custom_patterns": [
    {
      "name": "custom_timeout",
      "regex": "timeout.*connection",
      "description": "Custom timeout pattern"
    }
  ]
}
```

#### Response

```json
{
  "patterns_found": [
    {
      "pattern_type": "rate_limiting",
      "confidence": 0.95,
      "occurrences": 15,
      "description": "Rate limiting events detected on API endpoint",
      "affected_services": ["api"],
      "time_distribution": {
        "peak_hour": "14:00-15:00",
        "frequency": "every 4 minutes"
      },
      "sample_logs": [
        {
          "timestamp": "2025-06-30T14:30:00Z",
          "message": "Rate limit exceeded for IP 192.168.1.100"
        }
      ]
    }
  ],
  "recommendations": [
    "Consider implementing request batching for high-volume clients",
    "Review rate limiting thresholds for authenticated users",
    "Add rate limiting metrics to monitoring dashboard"
  ],
  "analysis_duration_ms": 850
}
```

### 4. Real-time Streaming

**WebSocket** `/stream`

Establish a WebSocket connection for real-time log streaming with customizable filters.

#### Connection

```javascript
const ws = new WebSocket('wss://your-domain.com/api/v1/ai_logs/stream');

// Send initial subscription
ws.send(JSON.stringify({
  "action": "subscribe",
  "filter": {
    "services": ["api", "anythingllm"],
    "severity": ["ERROR", "CRITICAL"],
    "correlation_id": "req_abc123def456"
  }
}));

// Update filter
ws.send(JSON.stringify({
  "action": "update_filter",
  "filter": {
    "services": ["api"],
    "severity": ["WARN", "ERROR", "CRITICAL"]
  }
}));

// Ping to keep connection alive
ws.send(JSON.stringify({"action": "ping"}));
```

#### Incoming Messages

```json
{
  "type": "log_entry",
  "data": {
    "timestamp": "2025-06-30T14:30:00.123Z",
    "level": "ERROR",
    "service": "api",
    "message": "Database connection failed",
    "correlation_id": "req_abc123def456"
  }
}
```

### 5. Conversation Tracking

**GET** `/conversation/{conversation_id}`

Retrieve all logs related to a specific conversation for debugging multi-turn interactions.

#### Response

```json
{
  "conversation_id": "conv_789xyz",
  "logs": [
    {
      "timestamp": "2025-06-30T14:30:00Z",
      "message": "Conversation started",
      "turn_number": 1,
      "user_input": "How do I implement React hooks?",
      "ai_response_preview": "React hooks are functions that...",
      "tokens_used": 145,
      "model": "gpt-4"
    }
  ],
  "summary": {
    "total_turns": 3,
    "total_tokens": 450,
    "average_response_time_ms": 1200,
    "errors_encountered": 0,
    "workspace": "react-docs"
  }
}
```

### 6. Workspace Summary

**GET** `/workspace/{workspace_id}/summary`

Get aggregated logs and metrics for a specific workspace.

#### Response

```json
{
  "workspace_id": "ws_react_docs",
  "time_range": "24h",
  "metrics": {
    "total_requests": 1250,
    "successful_requests": 1200,
    "error_rate": 0.04,
    "average_response_time_ms": 800,
    "total_tokens_used": 125000,
    "unique_users": 45
  },
  "top_queries": [
    "React hooks implementation",
    "State management patterns",
    "Component lifecycle"
  ],
  "error_breakdown": [
    {
      "error_type": "timeout",
      "count": 30,
      "percentage": 60
    }
  ]
}
```

### 7. Export Logs

**POST** `/export`

Export logs in various formats for further analysis or archival.

#### Request Body

```json
{
  "format": "json",
  "time_range": "7d",
  "services": ["api", "anythingllm"],
  "filters": {
    "severity": ["ERROR", "CRITICAL"],
    "correlation_id": "req_abc123def456"
  },
  "include_metadata": true,
  "compression": "gzip"
}
```

#### Supported Formats

- `json`: Structured JSON format
- `csv`: Comma-separated values
- `jsonl`: JSON Lines format
- `elasticsearch`: Elasticsearch bulk format

#### Response Headers

```
Content-Type: application/json
Content-Disposition: attachment; filename="ai_logs_export_20250630.json"
X-Export-Count: 1500
X-Export-Size-Bytes: 2048576
```

### 8. Pattern Library

**GET** `/patterns`

Retrieve the library of predefined patterns used for detection.

#### Response

```json
{
  "patterns": [
    {
      "id": "rate_limiting",
      "name": "Rate Limiting Detection",
      "description": "Detects rate limiting events across services",
      "regex": "(rate limit|too many requests|429)",
      "confidence_threshold": 0.8,
      "category": "performance"
    }
  ],
  "custom_patterns_count": 5,
  "total_patterns": 20
}
```

## Error Handling

All endpoints follow consistent error response format:

```json
{
  "detail": "Error description",
  "error_code": "AI_LOGS_001",
  "timestamp": "2025-06-30T14:30:00Z",
  "correlation_id": "req_error123",
  "suggestion": "Check your query parameters and try again"
}
```

### Common Error Codes

- `AI_LOGS_001`: Invalid query parameters
- `AI_LOGS_002`: Correlation ID not found
- `AI_LOGS_003`: Time range too large
- `AI_LOGS_004`: Service unavailable
- `AI_LOGS_005`: Export format not supported
- `AI_LOGS_006`: WebSocket connection failed

## Best Practices

### Query Optimization

1. **Use specific time ranges**: Narrow time ranges improve query performance
2. **Filter by service**: Specify services to reduce data volume
3. **Use correlation IDs**: Most efficient way to trace specific requests
4. **Enable caching**: Use `cache=true` for repeated queries

### Troubleshooting Workflow

1. Start with error mode: `mode=errors&time_range=1h`
2. Identify correlation IDs from error logs
3. Use correlation analysis to trace request flow
4. Apply pattern detection to identify root causes
5. Use real-time streaming to monitor fixes

### Performance Considerations

1. **Pagination**: Use `limit` and `offset` for large result sets
2. **WebSocket filtering**: Apply filters to reduce bandwidth
3. **Export scheduling**: Use exports for bulk data analysis
4. **Cache utilization**: Enable caching for dashboard queries

### Security Guidelines

1. **Sanitize inputs**: All user inputs are automatically sanitized
2. **Rate limiting**: Respect rate limits to ensure service availability
3. **Data access**: Only access logs for authorized workspaces
4. **Correlation IDs**: Don't include sensitive data in correlation IDs

## SDK Examples

### Python

```python
import requests
import json

class AILogsClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def query_logs(self, **params):
        response = requests.get(
            f"{self.base_url}/api/v1/ai_logs/query",
            params=params,
            headers=self.headers
        )
        return response.json()
    
    def correlate(self, correlation_id):
        data = {"correlation_id": correlation_id}
        response = requests.post(
            f"{self.base_url}/api/v1/ai_logs/correlate",
            json=data,
            headers=self.headers
        )
        return response.json()

# Usage
client = AILogsClient("https://your-domain.com", "your_api_key")
logs = client.query_logs(mode="errors", time_range="1h")
correlation = client.correlate("req_abc123def456")
```

### JavaScript

```javascript
class AILogsClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async queryLogs(params = {}) {
        const url = new URL(`${this.baseUrl}/api/v1/ai_logs/query`);
        Object.keys(params).forEach(key => 
            url.searchParams.append(key, params[key])
        );
        
        const response = await fetch(url, {
            headers: this.headers
        });
        return await response.json();
    }
    
    async streamLogs(filter) {
        const ws = new WebSocket(
            `${this.baseUrl.replace('http', 'ws')}/api/v1/ai_logs/stream`
        );
        
        ws.onopen = () => {
            ws.send(JSON.stringify({
                action: 'subscribe',
                filter: filter
            }));
        };
        
        return ws;
    }
}

// Usage
const client = new AILogsClient('https://your-domain.com', 'your_api_key');
const logs = await client.queryLogs({mode: 'errors', time_range: '1h'});
const stream = await client.streamLogs({services: ['api'], severity: ['ERROR']});
```

## Monitoring and Alerting

The AI Logs API provides built-in monitoring capabilities:

### Health Checks

```http
GET /api/v1/ai_logs/health
```

Returns system health status and component availability.

### Metrics

- Query response times
- Cache hit rates
- Error rates by service
- WebSocket connection counts
- Export request volumes

### Alerting Recommendations

1. **High error rates**: Alert when error rate > 5% over 5 minutes
2. **Service unavailability**: Alert when Loki connection fails
3. **Query performance**: Alert when 95th percentile response time > 2 seconds
4. **Rate limiting**: Alert when rate limits are frequently hit

## Changelog

### Version 1.0.0 (2025-06-30)
- Initial release with core querying functionality
- Real-time WebSocket streaming
- Correlation analysis and pattern detection
- Multi-format export capabilities
- Comprehensive API documentation

## Support

For API support and questions:
- Email: api-support@docaiche.com
- Documentation: https://docs.docaiche.com/ai-logs
- Status Page: https://status.docaiche.com