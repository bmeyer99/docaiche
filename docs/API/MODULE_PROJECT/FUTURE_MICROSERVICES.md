# Future Microservices Migration Guide

## Overview
This guide outlines how to extract modules from the modular monolith into separate microservices when the need arises. The modular architecture has been designed to make this transition as smooth as possible.

## When to Consider Microservices

### Valid Reasons
1. **Independent Scaling**: A module needs different scaling characteristics
2. **Team Boundaries**: Different teams need to own and deploy independently  
3. **Technology Diversity**: A module would benefit from a different tech stack
4. **Fault Isolation**: A module's failures shouldn't affect others
5. **Compliance**: Regulatory requirements for data isolation

### Invalid Reasons
1. **"Microservices are trendy"**: Don't add complexity without clear benefits
2. **Resume-Driven Development**: Complexity should solve real problems
3. **Premature Optimization**: Wait until you have actual scaling issues
4. **Poor Module Design**: Fix the design, don't distribute the problem

## Migration Strategy

### Step 1: Identify Candidate Module
```yaml
# Evaluation Criteria
Module: content_processor
Criteria:
  - High CPU usage: ✓ (Heavy PDF processing)
  - Independent scaling need: ✓ (Batch processing spikes)
  - Clear boundaries: ✓ (Well-defined interface)
  - Minimal shared state: ✓ (Stateless processing)
  - Team ownership: ✓ (Document team)
Decision: Good candidate for extraction
```

### Step 2: Create Service Wrapper
```python
# services/content_processor_service/main.py
from fastapi import FastAPI, UploadFile
from src.modules.content_processor.interface import ContentProcessorInterface
from src.modules.content_processor.implementation import ContentProcessor

app = FastAPI(title="Content Processor Service")

# Initialize processor
processor = ContentProcessor(config={...})

@app.post("/process")
async def process_document(file: UploadFile):
    """Process document endpoint"""
    # Save file temporarily
    temp_path = await save_upload(file)
    
    # Process using existing module
    result = await processor.process_document(temp_path)
    
    # Return result
    return result.dict()

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### Step 3: Create Client Adapter
```python
# src/modules/content_processor/remote_client.py
from typing import Dict, Any
import httpx
from pathlib import Path
from .interface import ContentProcessorInterface, ProcessedDocument

class RemoteContentProcessor:
    """Remote client implementing ContentProcessorInterface"""
    
    def __init__(self, service_url: str, timeout: int = 30):
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def process_document(
        self, 
        file_path: Path,
        options: Dict[str, Any] = None
    ) -> ProcessedDocument:
        """Process document via remote service"""
        
        # Upload file to service
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}
            response = await self.client.post(
                f"{self.service_url}/process",
                files=files,
                data={'options': json.dumps(options)} if options else {}
            )
        
        if response.status_code != 200:
            raise Exception(f"Remote processing failed: {response.text}")
        
        # Parse response into ProcessedDocument
        data = response.json()
        return ProcessedDocument(**data)
    
    # Implement other interface methods...
```

### Step 4: Update Dependency Injection
```python
# src/core/di/registrations.py
import os

async def register_services():
    """Register services with remote/local switch"""
    
    # Check if content processor should be remote
    if os.getenv("CONTENT_PROCESSOR_REMOTE", "false").lower() == "true":
        # Register remote client
        from src.modules.content_processor.remote_client import RemoteContentProcessor
        
        container.register(
            ContentProcessorInterface,
            factory=lambda: RemoteContentProcessor(
                service_url=os.getenv("CONTENT_PROCESSOR_URL")
            ),
            scope=Scope.SINGLETON
        )
    else:
        # Register local implementation
        from src.modules.content_processor.implementation import ContentProcessor
        
        container.register(
            ContentProcessorInterface,
            implementation=ContentProcessor,
            scope=Scope.SINGLETON
        )
```

## Microservice Template

### Project Structure
```
content-processor-service/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Service configuration
│   ├── telemetry.py            # OpenTelemetry setup
│   ├── health.py               # Health checks
│   └── processor/              # Module code (copied)
├── tests/
├── k8s/                        # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── docker-compose.yml          # Local development
```

### Dockerfile Template
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: content-processor
  labels:
    app: content-processor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: content-processor
  template:
    metadata:
      labels:
        app: content-processor
    spec:
      containers:
      - name: content-processor
        image: docaiche/content-processor:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://otel-collector:4317"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Communication Patterns

### 1. Synchronous HTTP/gRPC
```python
# HTTP Client with Circuit Breaker
from circuitbreaker import circuit

class ResilientContentProcessor:
    def __init__(self, service_url: str):
        self.service_url = service_url
        self.client = httpx.AsyncClient()
    
    @circuit(failure_threshold=5, recovery_timeout=60)
    async def process_document(self, file_path: Path) -> ProcessedDocument:
        """Process with circuit breaker protection"""
        try:
            response = await self.client.post(
                f"{self.service_url}/process",
                files={"file": open(file_path, "rb")},
                timeout=30.0
            )
            response.raise_for_status()
            return ProcessedDocument(**response.json())
        except Exception as e:
            # Circuit breaker will handle failures
            raise
```

### 2. Asynchronous Messaging
```python
# Redis Queue Implementation
import redis
import json
from typing import Dict, Any

class AsyncContentProcessor:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.pending_queue = "processing:pending"
        self.results_queue = "processing:results"
    
    async def process_document(self, file_path: Path) -> str:
        """Queue document for processing"""
        job_id = str(uuid.uuid4())
        
        # Queue job
        job_data = {
            "id": job_id,
            "file_path": str(file_path),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.redis.lpush(self.pending_queue, json.dumps(job_data))
        
        return job_id
    
    async def get_result(self, job_id: str, timeout: int = 300) -> ProcessedDocument:
        """Get processing result"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for result
            result = self.redis.get(f"result:{job_id}")
            if result:
                data = json.loads(result)
                return ProcessedDocument(**data)
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Processing timeout for job {job_id}")
```

### 3. Event-Driven Architecture
```python
# Event Publishing
from typing import Dict, Any
import aiokafka

class EventPublisher:
    def __init__(self, kafka_url: str):
        self.producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=kafka_url,
            value_serializer=lambda v: json.dumps(v).encode()
        )
    
    async def publish_document_processed(self, document: ProcessedDocument):
        """Publish document processed event"""
        event = {
            "event_type": "document.processed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document.id,
                "workspace_id": document.workspace_id,
                "content_length": len(document.content),
                "chunk_count": len(document.chunks)
            }
        }
        
        await self.producer.send(
            "document-events",
            key=document.id.encode(),
            value=event
        )
```

## Service Mesh Integration

### Istio Configuration
```yaml
# istio/virtual-service.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: content-processor
spec:
  hosts:
  - content-processor
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: content-processor
        subset: canary
      weight: 10
    - destination:
        host: content-processor
        subset: stable
      weight: 90
  - route:
    - destination:
        host: content-processor
        subset: stable
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: content-processor
spec:
  host: content-processor
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    loadBalancer:
      simple: LEAST_REQUEST
  subsets:
  - name: stable
    labels:
      version: stable
  - name: canary
    labels:
      version: canary
```

## Data Consistency Patterns

### 1. Saga Pattern
```python
# Distributed transaction using Saga
class DocumentIngestionSaga:
    def __init__(self, services: Dict[str, Any]):
        self.services = services
        self.completed_steps = []
    
    async def execute(self, file_path: Path, workspace_id: str):
        """Execute distributed transaction"""
        try:
            # Step 1: Process document
            document = await self.services['content_processor'].process(file_path)
            self.completed_steps.append('process')
            
            # Step 2: Store in database
            await self.services['storage'].store(document)
            self.completed_steps.append('store')
            
            # Step 3: Index for search
            await self.services['search'].index(document)
            self.completed_steps.append('index')
            
            # Step 4: Enrich content
            await self.services['enrichment'].enrich(document)
            self.completed_steps.append('enrich')
            
            return document
            
        except Exception as e:
            # Compensate in reverse order
            await self.compensate()
            raise
    
    async def compensate(self):
        """Undo completed steps"""
        for step in reversed(self.completed_steps):
            if step == 'enrich':
                await self.services['enrichment'].remove(document.id)
            elif step == 'index':
                await self.services['search'].remove(document.id)
            elif step == 'store':
                await self.services['storage'].delete(document.id)
            # Process step doesn't need compensation
```

### 2. Event Sourcing
```python
# Event-sourced document state
@dataclass
class DocumentEvent:
    event_id: str
    document_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]

class DocumentEventStore:
    def __init__(self, db):
        self.db = db
    
    async def append(self, event: DocumentEvent):
        """Append event to store"""
        await self.db.events.insert(event.dict())
    
    async def get_document_state(self, document_id: str) -> Dict[str, Any]:
        """Rebuild document state from events"""
        events = await self.db.events.find(
            {"document_id": document_id}
        ).sort("timestamp", 1).to_list()
        
        state = {"id": document_id}
        
        for event in events:
            if event.event_type == "created":
                state.update(event.data)
            elif event.event_type == "processed":
                state["content"] = event.data["content"]
                state["status"] = "processed"
            elif event.event_type == "enriched":
                state["enrichments"] = event.data["enrichments"]
        
        return state
```

## Monitoring and Observability

### Distributed Tracing
```python
# Trace context propagation
from opentelemetry import trace, propagate
from opentelemetry.propagation import inject

class TracedClient:
    def __init__(self, service_url: str):
        self.service_url = service_url
        self.tracer = trace.get_tracer(__name__)
    
    async def call_service(self, endpoint: str, data: Dict[str, Any]):
        """Make traced service call"""
        with self.tracer.start_as_current_span(f"call_{endpoint}") as span:
            # Inject trace context into headers
            headers = {}
            inject(headers)
            
            response = await httpx.post(
                f"{self.service_url}/{endpoint}",
                json=data,
                headers=headers
            )
            
            span.set_attribute("http.status_code", response.status_code)
            return response
```

### Service Metrics
```python
# Prometheus metrics for microservice
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter(
    'service_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'service_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'service_active_connections',
    'Active connections'
)

# Middleware to collect metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    active_connections.inc()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record metrics
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    finally:
        active_connections.dec()
```

## Migration Checklist

### Pre-Migration
- [ ] Module has clean interface
- [ ] Dependencies are well-defined
- [ ] Module is stateless or state is external
- [ ] Performance baseline measured
- [ ] Team ownership established

### Migration Steps
1. [ ] Create service wrapper
2. [ ] Implement health checks
3. [ ] Add telemetry
4. [ ] Create client adapter
5. [ ] Setup CI/CD pipeline
6. [ ] Deploy to staging
7. [ ] Test with canary traffic
8. [ ] Monitor performance
9. [ ] Complete migration
10. [ ] Remove old code

### Post-Migration
- [ ] Performance meets SLAs
- [ ] Monitoring in place
- [ ] Documentation updated
- [ ] Team trained
- [ ] Runbooks created

## Common Pitfalls

### 1. Network Latency
```python
# Bad: Many small calls
for doc in documents:
    result = await remote_service.process(doc)

# Good: Batch operations
results = await remote_service.process_batch(documents)
```

### 2. Missing Timeouts
```python
# Bad: No timeout
response = await client.post(url, data=data)

# Good: Explicit timeout
response = await client.post(url, data=data, timeout=30.0)
```

### 3. No Circuit Breaker
```python
# Bad: Cascading failures
try:
    result = await remote_service.call()
except:
    # Service down affects everyone
    raise

# Good: Circuit breaker protection
@circuit(failure_threshold=5, recovery_timeout=60)
async def call_service():
    return await remote_service.call()
```

### 4. Chatty Interfaces
```python
# Bad: Multiple calls for related data
user = await user_service.get_user(id)
profile = await profile_service.get_profile(id)
settings = await settings_service.get_settings(id)

# Good: Aggregate at the edge
user_data = await user_service.get_user_complete(id)
```

## Tools and Libraries

### Service Development
- **FastAPI**: REST API framework
- **gRPC**: High-performance RPC
- **Pydantic**: Data validation
- **httpx**: Async HTTP client

### Resilience
- **py-circuit-breaker**: Circuit breaker pattern
- **tenacity**: Retry with backoff
- **aiocache**: Distributed caching

### Messaging
- **aiokafka**: Kafka client
- **aioredis**: Redis client
- **celery**: Task queue

### Observability
- **opentelemetry**: Distributed tracing
- **prometheus-client**: Metrics
- **structlog**: Structured logging

### Testing
- **pytest-asyncio**: Async testing
- **testcontainers**: Integration testing
- **locust**: Load testing

## Conclusion

The modular architecture provides a clear path to microservices when needed. By following this guide, teams can extract modules into services incrementally, maintaining system stability while gaining the benefits of service-oriented architecture where it makes sense.