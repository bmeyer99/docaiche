# Phase 2: Architecture Consolidation
*Priority: HIGH - Core System Stability*
*Timeline: Weeks 4-6*

## Overview
This phase consolidates the architecture by merging duplicate implementations, optimizing database connections, and implementing resilience patterns. This creates a stable foundation for scaling.

## API Consolidation (Week 4)

### 1. Merge Duplicate API Implementations
**Current Issue**: Both `/src/api/endpoints.py` and `/src/api/v1/api.py` contain overlapping functionality

**Consolidation Strategy**:
```
New Structure:
/src/api/
├── __init__.py
├── v1/
│   ├── __init__.py
│   ├── router.py (consolidated main router)
│   ├── endpoints/
│   │   ├── search.py
│   │   ├── admin.py
│   │   ├── config.py
│   │   ├── health.py
│   │   └── websocket.py
│   ├── dependencies.py
│   ├── middleware.py
│   └── schemas.py
└── v2/ (future API version)
```

**Migration Steps**:
1. Analyze endpoint overlap between endpoints.py and v1 router
2. Merge common functionality into v1 structure
3. Remove duplicate endpoints.py file
4. Update all imports and references
5. Implement proper API versioning headers

### 2. Standardize Error Handling
**Current Issue**: Multiple exception handlers without unification

**New Unified Error Handler**:
```python
from src.api.v1.exceptions import APIError, ValidationError, AuthenticationError

class UnifiedErrorHandler:
    @staticmethod
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        """Handle all API errors with consistent format"""
        error_response = {
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": exc.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.headers.get("X-Request-ID"),
                "path": str(request.url)
            }
        }
        
        # Log error for monitoring
        logger.error(f"API Error: {exc.error_code} - {exc.message}", 
                    extra={"request_id": error_response["error"]["request_id"]})
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
```

**Error Types to Standardize**:
- ValidationError (400)
- AuthenticationError (401)
- AuthorizationError (403)
- NotFoundError (404)
- RateLimitError (429)
- InternalServerError (500)
- ServiceUnavailableError (503)

### 3. Implement API Versioning Strategy
**Versioning Approach**: URL path versioning with header support

```python
from fastapi import APIRouter, Header
from typing import Optional

class VersionedAPIRouter(APIRouter):
    def __init__(self, version: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.version = version
        self.prefix = f"/api/{version}"
    
    async def version_check(self, api_version: Optional[str] = Header(None)):
        """Check API version compatibility"""
        if api_version and api_version != self.version:
            supported_versions = ["v1", "v2"]
            if api_version not in supported_versions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported API version. Supported: {supported_versions}"
                )

# Usage
v1_router = VersionedAPIRouter(version="v1")
v2_router = VersionedAPIRouter(version="v2")  # Future use
```

### 4. Comprehensive Input Validation
**Enhanced Validation Schemas**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import re

class SearchRequestValidated(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    technology_hint: Optional[str] = Field(None, max_length=50)
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    filters: Optional[dict] = Field(None)
    
    @validator('query')
    def validate_query(cls, v):
        # Prevent injection attacks
        if re.search(r'[<>"\';]', v):
            raise ValueError('Query contains invalid characters')
        return v.strip()
    
    @validator('technology_hint')
    def validate_technology(cls, v):
        if v:
            allowed_technologies = ['python', 'javascript', 'react', 'typescript', 'java']
            if v.lower() not in allowed_technologies:
                raise ValueError(f'Technology must be one of: {allowed_technologies}')
        return v.lower() if v else None

class ConfigUpdateValidated(BaseModel):
    key: str = Field(..., pattern=r'^[a-zA-Z][a-zA-Z0-9._-]*$')
    value: str = Field(..., max_length=1000)
    
    @validator('key')
    def validate_config_key(cls, v):
        allowed_prefixes = ['search.', 'cache.', 'llm.', 'security.']
        if not any(v.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(f'Config key must start with: {allowed_prefixes}')
        return v
```

## Database & Performance Optimization (Week 5-6)

### 1. Enhanced PostgreSQL Connection Pooling
**Current Issue**: Basic connection pooling without optimization

**Enhanced Configuration**:
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import asyncpg

class EnhancedDatabaseManager:
    def __init__(self):
        self.pool_config = {
            'min_size': 5,
            'max_size': 20,
            'max_queries': 50000,
            'max_inactive_connection_lifetime': 300,
            'timeout': 30,
            'command_timeout': 60
        }
    
    async def create_pool(self):
        """Create optimized connection pool"""
        self.pool = await asyncpg.create_pool(
            database_url=DATABASE_URL,
            **self.pool_config
        )
        
        # Connection pool monitoring
        self.monitor_pool_health()
    
    async def monitor_pool_health(self):
        """Monitor connection pool metrics"""
        metrics = {
            'pool_size': self.pool.get_size(),
            'pool_free_size': self.pool.get_free_size(),
            'pool_idle_size': self.pool.get_idle_size()
        }
        
        # Send to monitoring system
        await self.send_pool_metrics(metrics)
```

**Database Optimization Settings**:
```sql
-- PostgreSQL configuration optimizations
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
```

### 2. Redis Connection Clustering
**Enhanced Redis Configuration**:
```python
import aioredis
from aioredis.cluster import RedisCluster

class RedisClusterManager:
    def __init__(self):
        self.cluster_nodes = [
            {"host": "redis-node1", "port": 6379},
            {"host": "redis-node2", "port": 6379}, 
            {"host": "redis-node3", "port": 6379}
        ]
    
    async def initialize_cluster(self):
        """Initialize Redis cluster connection"""
        self.redis = RedisCluster(
            startup_nodes=self.cluster_nodes,
            decode_responses=True,
            skip_full_coverage_check=True,
            max_connections=20,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Test cluster connectivity
        await self.health_check()
    
    async def health_check(self):
        """Check cluster health"""
        try:
            await self.redis.ping()
            cluster_info = await self.redis.cluster_info()
            return {"status": "healthy", "cluster_info": cluster_info}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
```

### 3. Circuit Breaker Patterns
**Implementation for External Services**:
```python
import asyncio
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self):
        """Check if enough time has passed to attempt reset"""
        return (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout
    
    def _on_success(self):
        """Reset circuit breaker on successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage example for external API calls
weaviate_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

async def query_weaviate_with_circuit_breaker(query):
    """Query Weaviate with circuit breaker protection"""
    return await weaviate_circuit_breaker.call(weaviate_client.query, query)
```

### 4. Database Query Optimization
**Enhanced Indexing Strategy**:
```sql
-- Performance indexes for common queries
CREATE INDEX CONCURRENTLY idx_documents_technology ON documents(technology) WHERE technology IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_documents_created_at ON documents(created_at);
CREATE INDEX CONCURRENTLY idx_documents_workspace_id ON documents(workspace_id);
CREATE INDEX CONCURRENTLY idx_search_logs_timestamp ON search_logs(timestamp);
CREATE INDEX CONCURRENTLY idx_search_logs_query_hash ON search_logs(query_hash);

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY idx_documents_tech_workspace ON documents(technology, workspace_id);
CREATE INDEX CONCURRENTLY idx_content_fulltext ON documents USING gin(to_tsvector('english', content));
```

**Query Optimization Patterns**:
```python
class OptimizedQueries:
    @staticmethod
    async def search_documents_optimized(technology: str, workspace_id: str, limit: int):
        """Optimized document search with proper indexing"""
        query = """
        SELECT d.id, d.title, d.content, d.technology, 
               ts_rank(to_tsvector('english', d.content), plainto_tsquery($1)) as rank
        FROM documents d
        WHERE d.technology = $2 
        AND d.workspace_id = $3
        AND to_tsvector('english', d.content) @@ plainto_tsquery($1)
        ORDER BY rank DESC, d.created_at DESC
        LIMIT $4
        """
        return await database.fetch_all(query, (search_term, technology, workspace_id, limit))
    
    @staticmethod
    async def get_document_stats_optimized(workspace_id: str):
        """Optimized stats query with proper aggregation"""
        query = """
        SELECT 
            technology,
            COUNT(*) as document_count,
            AVG(LENGTH(content)) as avg_content_length,
            MAX(created_at) as last_updated
        FROM documents 
        WHERE workspace_id = $1 
        GROUP BY technology
        """
        return await database.fetch_all(query, (workspace_id,))
```

## Infrastructure as Code (Week 6)

### 1. Terraform Modules
**Directory Structure**:
```
/terraform/
├── modules/
│   ├── api/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── database/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── monitoring/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── development/
│   ├── staging/
│   └── production/
└── shared/
```

**API Module Example**:
```hcl
# modules/api/main.tf
resource "docker_image" "docaiche_api" {
  name = "docaiche/api:${var.api_version}"
  build {
    context = "${var.project_root}/src/api"
    dockerfile = "Dockerfile"
  }
}

resource "docker_container" "docaiche_api" {
  name  = "docaiche-api-${var.environment}"
  image = docker_image.docaiche_api.latest
  
  env = [
    "ENVIRONMENT=${var.environment}",
    "DATABASE_URL=${var.database_url}",
    "REDIS_URL=${var.redis_url}",
    "VAULT_URL=${var.vault_url}"
  ]
  
  ports {
    internal = 4000
    external = var.api_port
  }
  
  labels {
    label = "traefik.enable"
    value = "true"
  }
  
  healthcheck {
    test     = ["CMD", "curl", "-f", "http://localhost:4000/health"]
    interval = "30s"
    timeout  = "10s"
    retries  = 3
  }
}
```

### 2. Container Security Scanning
**Trivy Integration**:
```yaml
# .github/workflows/security-scan.yml
name: Container Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t docaiche/api:${{ github.sha }} .
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'docaiche/api:${{ github.sha }}'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
```

**Docker Security Best Practices**:
```dockerfile
# Multi-stage build with security scanning
FROM python:3.11-slim as builder

# Create non-root user
RUN groupadd -r docaiche && useradd -r -g docaiche docaiche

# Install security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as runtime

# Copy from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN groupadd -r docaiche && useradd -r -g docaiche docaiche

# Set up application
WORKDIR /app
COPY src/ ./src/
RUN chown -R docaiche:docaiche /app

# Switch to non-root user
USER docaiche

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:4000/health || exit 1

EXPOSE 4000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "4000"]
```

## Testing & Validation

### Architecture Testing Checklist
- [ ] API consolidation doesn't break existing functionality
- [ ] All endpoints use consistent error handling
- [ ] Database connection pooling improves performance
- [ ] Circuit breakers prevent cascade failures
- [ ] Container security scanning passes all checks
- [ ] Infrastructure as Code deploys successfully

### Performance Testing
- Database connection pool performance under load
- Circuit breaker behavior during failures
- API response time consistency
- Error handling overhead measurement

## Rollback Procedures

### API Consolidation Rollback
1. Maintain backup of original endpoints.py
2. Feature flag new consolidated API
3. Route traffic back to original implementation if needed

### Database Changes Rollback
1. Database migration rollback scripts
2. Connection pool configuration reset
3. Index removal procedures if performance degrades

## Success Criteria

### Architecture Metrics
- [ ] Single API implementation without duplication
- [ ] Consistent error responses across all endpoints
- [ ] Database connection pool utilization > 80%
- [ ] Circuit breaker prevents > 95% of cascade failures
- [ ] Container vulnerability scan shows zero critical issues

### Performance Metrics
- [ ] API response time improved by 20%
- [ ] Database query performance improved by 30%
- [ ] Connection pool efficiency > 85%
- [ ] Error handling adds < 5ms overhead

## Dependencies
- Database migration tools
- Terraform infrastructure
- Container security scanning tools
- Performance testing framework

## Next Phase
Upon completion, proceed to Phase 3: Observability & Monitoring with a consolidated, resilient architecture.