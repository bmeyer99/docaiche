# Docaiche API Quick Reference

## Essential Endpoints

### Search
```bash
# Quick search
curl "http://localhost:8000/api/v1/search?q=your+search+term"

# Advanced search
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "python async", "technology_hint": "python", "limit": 20}'
```

### Health Check
```bash
# System health
curl "http://localhost:8000/api/v1/health"

# Statistics
curl "http://localhost:8000/api/v1/stats"
```

### Configuration
```bash
# View config
curl "http://localhost:8000/api/v1/config"

# Update config
curl -X POST "http://localhost:8000/api/v1/config" \
  -H "Content-Type: application/json" \
  -d '{"key": "app.debug", "value": true}'
```

### Admin
```bash
# Dashboard
curl "http://localhost:8000/api/v1/admin/dashboard"

# Search content
curl "http://localhost:8000/api/v1/admin/search-content?search_term=python"

# Recent activity
curl "http://localhost:8000/api/v1/admin/activity/recent"
```

### Providers
```bash
# List providers
curl "http://localhost:8000/api/v1/providers"

# Test provider
curl -X POST "http://localhost:8000/api/v1/providers/ollama/test" \
  -H "Content-Type: application/json" \
  -d '{"base_url": "http://localhost:11434/api"}'
```

## Rate Limits

| Endpoint | Rate Limit |
|----------|-----------|
| GET /search | 60/minute |
| POST /search | 30/minute |
| /feedback | 20/minute |
| /signals | 100/minute |
| /stats | 10/minute |
| /config (GET) | 10/minute |
| /config (POST) | 5/minute |
| /admin/* | 20-30/minute |
| /providers/* | 10-20/minute |

## Response Headers

All responses include:
- `X-Trace-ID`: Request correlation ID
- `X-Process-Time`: Processing time
- `Retry-After`: (on rate limit errors)

## Error Format (RFC 7807)

```json
{
  "type": "error-type-uri",
  "title": "Error Title",
  "status": 400,
  "detail": "Detailed error message",
  "instance": "/api/v1/endpoint",
  "error_code": "ERROR_CODE",
  "trace_id": "uuid"
}
```

## Testing Tools

```bash
# Run all tests
./test_all_endpoints.sh

# Python test suite
python test_api.py

# Test with custom base URL
python test_api.py --base-url http://your-api:8000/api/v1

# Quick health check
curl -s http://localhost:8000/api/v1/health | jq .
```

## Common Use Cases

### 1. Search and Get Feedback
```bash
# Search
RESPONSE=$(curl -s "http://localhost:8000/api/v1/search?q=fastapi+tutorial")
CONTENT_ID=$(echo $RESPONSE | jq -r '.results[0].content_id')

# Submit feedback
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -d "{\"content_id\": \"$CONTENT_ID\", \"feedback_type\": \"helpful\", \"rating\": 5}"
```

### 2. Monitor System Health
```bash
# Combined health check
for endpoint in health stats analytics?timeRange=24h; do
  echo "=== $endpoint ==="
  curl -s "http://localhost:8000/api/v1/$endpoint" | jq '.status // .overall_status // "OK"'
done
```

### 3. Bulk Operations
```bash
# Upload multiple documents
for file in *.pdf; do
  curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
    -F "file=@$file"
  sleep 2  # Rate limiting
done
```

## Environment Setup

```bash
# Required services
export DATABASE_URL="postgresql://user:pass@localhost/docaiche"
export REDIS_URL="redis://localhost:6379"

# Optional services
export ANYTHINGLLM_ENDPOINT="http://localhost:3001"
export ANYTHINGLLM_API_KEY="your-key"

# Start API
python -m uvicorn src.main:app --reload
```