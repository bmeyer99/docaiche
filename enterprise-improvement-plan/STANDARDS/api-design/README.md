# API Design Guidelines

## Overview
This document defines the standards and best practices for designing RESTful APIs in the DocAIche system. These guidelines ensure consistency, usability, and maintainability across all API endpoints.

## Core Principles

### 1. RESTful Design
- **MUST** follow REST architectural principles
- **MUST** use HTTP verbs appropriately
- **MUST** design around resources, not actions
- **SHOULD** be stateless and cacheable

### 2. Consistency
- **MUST** follow naming conventions consistently
- **MUST** use standard HTTP status codes
- **MUST** implement uniform error handling
- **SHOULD** maintain consistent response structures

### 3. Security First
- **MUST** implement authentication on all endpoints (except health checks)
- **MUST** use HTTPS in production
- **MUST** validate all inputs
- **MUST** implement rate limiting

## URL Design Standards

### Resource Naming
```
✅ Good Examples:
GET /api/v1/users
GET /api/v1/users/{id}
GET /api/v1/users/{id}/api-keys
POST /api/v1/search
GET /api/v1/admin/audit-logs

❌ Bad Examples:
GET /api/v1/getUsers
GET /api/v1/user_list
POST /api/v1/doSearch
GET /api/v1/auditLogs
```

### URL Structure Rules
- **MUST** use plural nouns for collections (`/users`, not `/user`)
- **MUST** use lowercase with hyphens for multi-word resources (`/api-keys`, not `/apiKeys`)
- **MUST** use nested resources for relationships (`/users/{id}/api-keys`)
- **MUST NOT** use verbs in URLs (`/search` is acceptable as it's a well-known resource)
- **MUST** version APIs in the URL (`/api/v1/`)

### Path Parameters vs Query Parameters
```
✅ Path Parameters (for resource identification):
GET /api/v1/users/{user_id}
DELETE /api/v1/auth/api-keys/{key_id}

✅ Query Parameters (for filtering, pagination, options):
GET /api/v1/search?q=react&limit=20&technology_hint=javascript
GET /api/v1/users?role=admin&limit=50&offset=100
```

## HTTP Methods

### Standard Usage
| Method | Use Case | Idempotent | Safe |
|--------|----------|------------|------|
| GET | Retrieve resource(s) | ✅ | ✅ |
| POST | Create new resource | ❌ | ❌ |
| PUT | Replace entire resource | ✅ | ❌ |
| PATCH | Partial update | ❌ | ❌ |
| DELETE | Remove resource | ✅ | ❌ |

### Examples
```http
# Retrieve all users
GET /api/v1/users

# Retrieve specific user
GET /api/v1/users/{id}

# Create new user
POST /api/v1/users

# Replace user entirely
PUT /api/v1/users/{id}

# Update user partially
PATCH /api/v1/users/{id}

# Delete user
DELETE /api/v1/users/{id}
```

## Request/Response Standards

### Content Type
- **MUST** use `application/json` for API requests/responses
- **MUST** specify `Content-Type: application/json` header
- **MAY** use `multipart/form-data` for file uploads

### Request Structure
```json
{
  "data": {
    "type": "user",
    "attributes": {
      "username": "john.doe",
      "email": "john@example.com",
      "role": "user"
    }
  }
}
```

### Response Structure
```json
{
  "data": {
    "id": "user_123",
    "type": "user",
    "attributes": {
      "username": "john.doe",
      "email": "john@example.com",
      "role": "user",
      "created_at": "2025-01-05T12:00:00Z"
    }
  },
  "meta": {
    "timestamp": "2025-01-05T12:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Collection Responses
```json
{
  "data": [
    {
      "id": "user_123",
      "type": "user",
      "attributes": { ... }
    }
  ],
  "meta": {
    "total_count": 150,
    "page": 1,
    "page_size": 20,
    "has_more": true
  }
}
```

## Status Codes

### Success Codes
| Code | Use Case | Response Body |
|------|----------|---------------|
| 200 | Successful GET, PUT, PATCH | Resource data |
| 201 | Successful POST (creation) | Created resource data |
| 202 | Accepted (async processing) | Status message |
| 204 | Successful DELETE | No content |

### Client Error Codes
| Code | Use Case | Description |
|------|----------|-------------|
| 400 | Bad Request | Invalid request syntax |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource conflict |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |

### Server Error Codes
| Code | Use Case | Description |
|------|----------|-------------|
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Service temporarily down |
| 504 | Gateway Timeout | Upstream service timeout |

## Error Handling

### Error Response Format (RFC 7807)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "type": "ValidationError",
    "timestamp": "2025-01-05T12:00:00Z",
    "request_id": "req_abc123",
    "path": "/api/v1/users",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  }
}
```

### Standard Error Codes
```
AUTH_REQUIRED          - Authentication required
AUTH_INVALID           - Invalid credentials
AUTH_EXPIRED           - Token expired
PERMISSION_DENIED      - Insufficient permissions
VALIDATION_ERROR       - Input validation failed
RESOURCE_NOT_FOUND     - Requested resource not found
RESOURCE_CONFLICT      - Resource already exists
RATE_LIMIT_EXCEEDED    - Too many requests
INTERNAL_ERROR         - Internal server error
SERVICE_UNAVAILABLE    - Service temporarily unavailable
```

### Validation Errors
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "type": "ValidationError",
    "timestamp": "2025-01-05T12:00:00Z",
    "request_id": "req_abc123",
    "path": "/api/v1/users",
    "validation_errors": [
      {
        "field": "email",
        "code": "INVALID_FORMAT",
        "message": "Invalid email format"
      },
      {
        "field": "password",
        "code": "TOO_SHORT",
        "message": "Password must be at least 8 characters"
      }
    ]
  }
}
```

## Authentication & Authorization

### JWT Authentication
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### API Key Authentication
```http
X-API-Key: ak_live_1234567890abcdef
```

### Role-Based Access Control
```json
{
  "user": {
    "id": "user_123",
    "role": "admin",
    "permissions": [
      "users:read",
      "users:write",
      "users:delete",
      "admin:access"
    ]
  }
}
```

## Pagination

### Query Parameters
```
GET /api/v1/users?limit=20&offset=100
GET /api/v1/search?limit=50&page=3
```

### Response Format
```json
{
  "data": [...],
  "meta": {
    "total_count": 1500,
    "page": 3,
    "page_size": 20,
    "has_more": true,
    "next_offset": 120,
    "prev_offset": 80
  }
}
```

## Filtering & Sorting

### Filtering
```
GET /api/v1/users?role=admin&status=active
GET /api/v1/search?technology_hint=react&content_type=tutorial
```

### Sorting
```
GET /api/v1/users?sort=created_at&order=desc
GET /api/v1/search?sort=relevance_score&order=desc
```

### Complex Queries
```
GET /api/v1/audit-logs?start_date=2025-01-01&end_date=2025-01-05&event_type=auth&user_id=user_123
```

## Rate Limiting

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1641380400
X-RateLimit-Window: 3600
```

### Rate Limit Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "type": "RateLimitError",
    "retry_after": 3600
  }
}
```

## Caching

### Cache Headers
```http
Cache-Control: public, max-age=300
ETag: "abc123"
Last-Modified: Sat, 05 Jan 2025 12:00:00 GMT
```

### Conditional Requests
```http
If-None-Match: "abc123"
If-Modified-Since: Sat, 05 Jan 2025 12:00:00 GMT
```

## Versioning

### URL Versioning (Preferred)
```
/api/v1/users
/api/v2/users
```

### Header Versioning (Alternative)
```http
Accept: application/vnd.docaiche.v1+json
API-Version: 1.0
```

## Security Headers

### Required Headers
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Documentation Requirements

### OpenAPI Specification
- **MUST** document all endpoints in OpenAPI 3.0+ format
- **MUST** include request/response schemas
- **MUST** include authentication requirements
- **MUST** include example requests/responses

### Endpoint Documentation
```yaml
/users:
  get:
    summary: List users
    description: |
      Retrieve a paginated list of users.
      
      **Permissions Required:** users:read
      **Rate Limit:** 100 requests/hour
    parameters:
      - name: limit
        in: query
        description: Maximum users to return
        schema:
          type: integer
          minimum: 1
          maximum: 100
          default: 20
    responses:
      '200':
        description: Users retrieved successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UsersResponse'
```

## Testing Requirements

### Test Coverage
- **MUST** test all happy path scenarios
- **MUST** test all error conditions
- **MUST** test authentication/authorization
- **MUST** test input validation
- **SHOULD** test edge cases and boundary conditions

### Test Types
```python
# Unit tests for endpoint logic
def test_create_user_success():
    response = client.post("/api/v1/users", json={...})
    assert response.status_code == 201

# Integration tests for full workflows
def test_user_lifecycle():
    # Create, read, update, delete user
    pass

# Security tests
def test_unauthorized_access():
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401

# Performance tests
def test_search_performance():
    # Test response time under load
    pass
```

## Performance Guidelines

### Response Times
- **MUST** respond within 200ms for simple queries
- **SHOULD** respond within 500ms for complex queries
- **MUST** implement timeout handling for long operations

### Optimization Techniques
- Use database indexing for filtered fields
- Implement response caching where appropriate
- Use pagination for large datasets
- Optimize database queries
- Implement request/response compression

## Deprecation Strategy

### Deprecation Headers
```http
Sunset: Sat, 31 Dec 2025 23:59:59 GMT
Deprecation: true
Link: </api/v2/users>; rel="successor-version"
```

### Deprecation Response
```json
{
  "data": {...},
  "meta": {
    "deprecation": {
      "deprecated": true,
      "sunset_date": "2025-12-31T23:59:59Z",
      "successor_version": "/api/v2/users",
      "migration_guide": "https://docs.docaiche.com/migration/v1-to-v2"
    }
  }
}
```

## Common Patterns

### Resource Creation
```http
POST /api/v1/users
Content-Type: application/json

{
  "username": "john.doe",
  "email": "john@example.com",
  "password": "securepassword123"
}

# Response
HTTP/1.1 201 Created
Location: /api/v1/users/user_123

{
  "data": {
    "id": "user_123",
    "type": "user",
    "attributes": {...}
  }
}
```

### Bulk Operations
```http
POST /api/v1/users/bulk
Content-Type: application/json

{
  "data": [
    {"username": "user1", "email": "user1@example.com"},
    {"username": "user2", "email": "user2@example.com"}
  ]
}

# Response
{
  "data": {
    "created": 2,
    "failed": 0,
    "results": [...]
  }
}
```

### Search and Filtering
```http
GET /api/v1/search?q=react hooks&technology_hint=javascript&limit=20

{
  "data": {
    "results": [...],
    "total_count": 156,
    "query": "react hooks",
    "execution_time_ms": 45,
    "cache_hit": true
  }
}
```

This API design guide ensures consistent, secure, and maintainable APIs across the DocAIche platform.