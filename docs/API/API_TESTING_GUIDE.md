# Docaiche API Testing Guide

This guide provides comprehensive curl commands for testing all API endpoints in the Docaiche system. All endpoints are prefixed with `/api/v1`.

## Base Configuration

```bash
# Set the base URL for your API
BASE_URL="http://localhost:8000/api/v1"

# For endpoints requiring rate limiting, add delay between requests
# Rate limits are specified in the code (e.g., 30/minute for search)
```

## Authentication

**Note**: The current implementation does not show explicit authentication requirements. All endpoints use rate limiting based on IP address.

## Search Endpoints

### 1. Search Documents (POST)
**Endpoint**: `POST /api/v1/search`  
**Rate Limit**: 30/minute  
**Description**: Initiates a search query

```bash
# Basic search
curl -X POST "$BASE_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python async",
    "limit": 20
  }'

# Search with technology hint
curl -X POST "$BASE_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "async patterns",
    "technology_hint": "python",
    "limit": 10,
    "session_id": "test-session-123"
  }'
```

### 2. Search Documents (GET)
**Endpoint**: `GET /api/v1/search`  
**Rate Limit**: 60/minute  
**Description**: GET alternative for simple queries

```bash
# Basic search
curl "$BASE_URL/search?q=python%20async"

# Search with all parameters
curl "$BASE_URL/search?q=fastapi%20tutorial&technology_hint=python&limit=5&session_id=test-123"
```

### 3. Submit Feedback
**Endpoint**: `POST /api/v1/feedback`  
**Rate Limit**: 20/minute  
**Description**: Submit user feedback on search results

```bash
curl -X POST "$BASE_URL/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "doc_001",
    "feedback_type": "helpful",
    "rating": 5,
    "comment": "Very helpful documentation",
    "query_context": "python async",
    "session_id": "test-session-123"
  }'
```

### 4. Submit Signals
**Endpoint**: `POST /api/v1/signals`  
**Rate Limit**: 100/minute  
**Description**: Submit implicit user interaction signals

```bash
curl -X POST "$BASE_URL/signals" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "query_123",
    "session_id": "session_456",
    "signal_type": "click",
    "content_id": "doc_001",
    "result_position": 2,
    "dwell_time_ms": 5000
  }'
```

## Health & Monitoring Endpoints

### 5. Health Check
**Endpoint**: `GET /api/v1/health`  
**Rate Limit**: None  
**Description**: Check system health status

```bash
curl "$BASE_URL/health"
```

### 6. System Statistics
**Endpoint**: `GET /api/v1/stats`  
**Rate Limit**: 10/minute  
**Description**: Get system usage and performance statistics

```bash
curl "$BASE_URL/stats"
```

### 7. Analytics
**Endpoint**: `GET /api/v1/analytics`  
**Rate Limit**: 30/minute  
**Description**: Get system analytics data

```bash
# Get 24-hour analytics
curl "$BASE_URL/analytics?timeRange=24h"

# Get 7-day analytics
curl "$BASE_URL/analytics?timeRange=7d"

# Get 30-day analytics
curl "$BASE_URL/analytics?timeRange=30d"
```

## Admin Endpoints

### 8. Admin Search Content
**Endpoint**: `GET /api/v1/admin/search-content`  
**Rate Limit**: 20/minute  
**Description**: Search content metadata for admin management

```bash
# Basic admin search
curl "$BASE_URL/admin/search-content"

# Search with filters
curl "$BASE_URL/admin/search-content?search_term=python&content_type=documentation&technology=python&limit=50&offset=0"
```

### 9. Flag Content for Removal
**Endpoint**: `DELETE /api/v1/content/{content_id}`  
**Rate Limit**: 10/minute  
**Description**: Flag content for removal (admin action)

```bash
curl -X DELETE "$BASE_URL/content/doc_001"
```

### 10. Get Recent Activity
**Endpoint**: `GET /api/v1/admin/activity/recent`  
**Rate Limit**: 30/minute  
**Description**: Get recent system activity

```bash
# Get recent activity
curl "$BASE_URL/admin/activity/recent?limit=20"

# Filter by activity type
curl "$BASE_URL/admin/activity/recent?limit=20&activity_type=search"
```

### 11. Get Recent Searches
**Endpoint**: `GET /api/v1/admin/activity/searches`  
**Rate Limit**: 30/minute  
**Description**: Get recent search queries

```bash
curl "$BASE_URL/admin/activity/searches?limit=20"
```

### 12. Get Recent Errors
**Endpoint**: `GET /api/v1/admin/activity/errors`  
**Rate Limit**: 30/minute  
**Description**: Get recent system errors

```bash
curl "$BASE_URL/admin/activity/errors?limit=20"
```

### 13. Get Dashboard Data
**Endpoint**: `GET /api/v1/admin/dashboard`  
**Rate Limit**: 20/minute  
**Description**: Get aggregated dashboard data

```bash
curl "$BASE_URL/admin/dashboard"
```

## Configuration Endpoints

### 14. Get Configuration
**Endpoint**: `GET /api/v1/config`  
**Rate Limit**: 10/minute  
**Description**: Get current system configuration

```bash
curl "$BASE_URL/config"
```

### 15. Update Configuration
**Endpoint**: `POST /api/v1/config`  
**Rate Limit**: 5/minute  
**Description**: Update system configuration

```bash
curl -X POST "$BASE_URL/config" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "app.debug",
    "value": true,
    "description": "Enable debug mode"
  }'
```

### 16. Get Collections
**Endpoint**: `GET /api/v1/collections`  
**Rate Limit**: 30/minute  
**Description**: List available documentation collections

```bash
curl "$BASE_URL/collections"
```

## Provider Management Endpoints

### 17. List Providers
**Endpoint**: `GET /api/v1/providers`  
**Rate Limit**: 20/minute  
**Description**: List all available LLM providers

```bash
curl "$BASE_URL/providers"
```

### 18. Test Provider Connection
**Endpoint**: `POST /api/v1/providers/{provider_id}/test`  
**Rate Limit**: 10/minute  
**Description**: Test connection to LLM provider

```bash
# Test Ollama connection
curl -X POST "$BASE_URL/providers/ollama/test" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://localhost:11434/api"
  }'

# Test OpenAI connection
curl -X POST "$BASE_URL/providers/openai/test" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "sk-your-api-key-here",
    "base_url": "https://api.openai.com/v1"
  }'
```

### 19. Update Provider Configuration
**Endpoint**: `POST /api/v1/providers/{provider_id}/config`  
**Rate Limit**: 10/minute  
**Description**: Update provider configuration

```bash
curl -X POST "$BASE_URL/providers/ollama/config" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://localhost:11434/api",
    "model": "llama2"
  }'
```

## Ingestion Endpoints

### 20. Upload Document
**Endpoint**: `POST /api/v1/ingestion/upload`  
**Rate Limit**: Not specified  
**Description**: Upload a document for ingestion

```bash
# Upload a file
curl -X POST "$BASE_URL/ingestion/upload" \
  -F "file=@/path/to/document.pdf"
```

## Enrichment Endpoints

### 21. Enrich Content
**Endpoint**: `POST /api/v1/enrichment/enrich`  
**Rate Limit**: Not specified  
**Description**: Submit content for enrichment processing

```bash
curl -X POST "$BASE_URL/enrichment/enrich" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "doc_001",
    "enrichment_types": ["summary", "tags"],
    "priority": "normal"
  }'
```

### 22. Bulk Enrich Content
**Endpoint**: `POST /api/v1/enrichment/bulk-enrich`  
**Rate Limit**: Not specified  
**Description**: Submit multiple content items for bulk enrichment

```bash
curl -X POST "$BASE_URL/enrichment/bulk-enrich" \
  -H "Content-Type: application/json" \
  -d '{
    "content_ids": ["doc_001", "doc_002", "doc_003"],
    "enrichment_type": "summary",
    "priority": "low"
  }'
```

### 23. Get Enrichment Status
**Endpoint**: `GET /api/v1/enrichment/status/{content_id}`  
**Rate Limit**: Not specified  
**Description**: Get enrichment status for specific content

```bash
curl "$BASE_URL/enrichment/status/doc_001"
```

### 24. Content Gap Analysis
**Endpoint**: `POST /api/v1/enrichment/gap-analysis`  
**Rate Limit**: Not specified  
**Description**: Analyze content gaps for given query

```bash
curl -X POST "$BASE_URL/enrichment/gap-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "kubernetes deployment strategies"
  }'
```

### 25. Get Enrichment Metrics
**Endpoint**: `GET /api/v1/enrichment/metrics`  
**Rate Limit**: Not specified  
**Description**: Get enrichment system performance metrics

```bash
curl "$BASE_URL/enrichment/metrics"
```

### 26. Get Enrichment Analytics
**Endpoint**: `GET /api/v1/enrichment/analytics`  
**Rate Limit**: Not specified  
**Description**: Get enrichment analytics for specified period

```bash
# Get analytics for default period
curl "$BASE_URL/enrichment/analytics"

# Get analytics with date range
curl "$BASE_URL/enrichment/analytics?start_date=2025-06-01&end_date=2025-06-28"
```

### 27. Bulk Import Technology
**Endpoint**: `POST /api/v1/enrichment/bulk-import`  
**Rate Limit**: Not specified  
**Description**: Bulk import documentation for a technology

```bash
curl -X POST "$BASE_URL/enrichment/bulk-import" \
  -H "Content-Type: application/json" \
  -d '{
    "technology_name": "tensorflow"
  }'
```

### 28. Enrichment Health Check
**Endpoint**: `GET /api/v1/enrichment/health`  
**Rate Limit**: Not specified  
**Description**: Check health of enrichment system

```bash
curl "$BASE_URL/enrichment/health"
```

## Testing Scripts

### Automated Testing Script

```bash
#!/bin/bash
# save as test_api.sh

BASE_URL="http://localhost:8000/api/v1"

echo "Testing Docaiche API Endpoints..."
echo "================================"

# Health check
echo -e "\n1. Testing Health Check..."
curl -s "$BASE_URL/health" | jq .

# Search
echo -e "\n2. Testing Search (GET)..."
curl -s "$BASE_URL/search?q=python%20async&limit=5" | jq .

# Stats
echo -e "\n3. Testing Stats..."
curl -s "$BASE_URL/stats" | jq .

# Collections
echo -e "\n4. Testing Collections..."
curl -s "$BASE_URL/collections" | jq .

# Providers
echo -e "\n5. Testing Providers..."
curl -s "$BASE_URL/providers" | jq .

# Configuration
echo -e "\n6. Testing Configuration..."
curl -s "$BASE_URL/config" | jq .

# Analytics
echo -e "\n7. Testing Analytics..."
curl -s "$BASE_URL/analytics?timeRange=24h" | jq .

echo -e "\nAPI Testing Complete!"
```

### Load Testing Script

```bash
#!/bin/bash
# save as load_test.sh

BASE_URL="http://localhost:8000/api/v1"
ITERATIONS=10
DELAY=2

echo "Running load test with $ITERATIONS iterations..."

for i in $(seq 1 $ITERATIONS); do
    echo "Iteration $i"
    
    # Test search endpoint
    curl -s -o /dev/null -w "%{http_code} - Search: %{time_total}s\n" \
        "$BASE_URL/search?q=test%20query%20$i"
    
    # Respect rate limiting
    sleep $DELAY
done
```

## Response Format Examples

### Successful Response
```json
{
  "results": [...],
  "total_count": 42,
  "query": "python async",
  "execution_time_ms": 45,
  "cache_hit": false
}
```

### Error Response (RFC 7807)
```json
{
  "type": "https://docs.example.com/errors/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Rate limit exceeded: 30 per 1 minute",
  "instance": "/api/v1/search",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Notes

1. **Rate Limiting**: Most endpoints have rate limits. Add delays between requests to avoid hitting limits.
2. **Trace IDs**: All responses include an `X-Trace-ID` header for request correlation.
3. **CORS**: The API supports CORS with all origins allowed (configure appropriately for production).
4. **Content Types**: All POST requests should include `Content-Type: application/json` header.
5. **Pagination**: Admin endpoints support pagination with `limit` and `offset` parameters.
6. **Error Handling**: The API uses RFC 7807 Problem Details format for error responses.

## Environment Variables

The API may require certain environment variables to be set:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/docaiche"
export REDIS_URL="redis://localhost:6379"
export ANYTHINGLLM_API_KEY="your-api-key"
export ANYTHINGLLM_ENDPOINT="http://localhost:3001"
```

## Running the API

To start the API server:

```bash
cd /home/lab/docaiche
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the main.py directly:

```bash
python src/main.py
```