# Service Telemetry Implementation Tasks

## Overview
This document outlines the telemetry implementation tasks required for each microservice to integrate with the Pipeline Visualization System.

## Affected Services
1. Web Scraper Service
2. Content Processor Service
3. Search Engine Service
4. Weaviate Service
5. LLM Orchestrator Service
6. Any future microservices

## Common Tasks for All Services

### 1. OpenTelemetry SDK Installation
**Priority: High**
**Estimated Time: 2 hours per service**

```python
# Add to requirements.txt for each service
opentelemetry-api>=1.21.0
opentelemetry-sdk>=1.21.0
opentelemetry-instrumentation>=0.42b0
opentelemetry-instrumentation-fastapi>=0.42b0  # For FastAPI services
opentelemetry-instrumentation-requests>=0.42b0  # For HTTP clients
opentelemetry-instrumentation-redis>=0.42b0  # If using Redis
opentelemetry-instrumentation-sqlalchemy>=0.42b0  # If using SQLAlchemy
opentelemetry-exporter-otlp-proto-grpc>=1.21.0
opentelemetry-exporter-prometheus>=0.42b0
```

### 2. Telemetry Initialization Module
**Priority: High**
**Estimated Time: 4 hours per service**

#### 2.1 Create Telemetry Configuration
- **File**: `[service]/core/telemetry/__init__.py`

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc import (
    trace_exporter,
    metrics_exporter
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

def init_telemetry(service_name: str, service_version: str):
    """Initialize OpenTelemetry for the service"""
    
    # Create resource identifying this service
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "service.instance.id": os.environ.get("HOSTNAME", "unknown"),
        "deployment.environment": os.environ.get("ENVIRONMENT", "development")
    })
    
    # Configure trace provider
    trace_provider = TracerProvider(resource=resource)
    trace_processor = BatchSpanProcessor(
        trace_exporter.OTLPSpanExporter(
            endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
        )
    )
    trace_provider.add_span_processor(trace_processor)
    trace.set_tracer_provider(trace_provider)
    
    # Configure metrics provider
    metric_reader = PeriodicExportingMetricReader(
        exporter=metrics_exporter.OTLPMetricExporter(
            endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
        ),
        export_interval_millis=10000  # Export every 10 seconds
    )
    metrics_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(metrics_provider)
    
    return trace.get_tracer(service_name), metrics.get_meter(service_name)
```

### 3. Standard Metrics Implementation
**Priority: High**
**Estimated Time: 1 day per service**

#### 3.1 Core Metrics Collection
- **File**: `[service]/core/telemetry/metrics.py`

```python
class ServiceMetrics:
    def __init__(self, meter):
        # Request metrics
        self.request_counter = meter.create_counter(
            name="service.request.count",
            description="Total number of requests processed",
            unit="1"
        )
        
        self.request_duration = meter.create_histogram(
            name="service.request.duration",
            description="Request processing duration",
            unit="ms"
        )
        
        # Queue metrics
        self.queue_length_callback = None
        self.queue_length = meter.create_observable_gauge(
            name="service.queue.length",
            description="Current queue length",
            unit="1",
            callbacks=[self._get_queue_length]
        )
        
        # Error metrics
        self.error_counter = meter.create_counter(
            name="service.error.count",
            description="Total number of errors",
            unit="1"
        )
        
        # Resource metrics
        self.memory_usage = meter.create_observable_gauge(
            name="service.memory.usage",
            description="Current memory usage",
            unit="By",
            callbacks=[self._get_memory_usage]
        )
        
        self.cpu_usage = meter.create_observable_gauge(
            name="service.cpu.usage",
            description="CPU usage percentage",
            unit="1",
            callbacks=[self._get_cpu_usage]
        )
    
    def _get_queue_length(self, options):
        # Implement queue length retrieval
        return [(get_current_queue_length(), {})]
    
    def _get_memory_usage(self, options):
        # Get current memory usage
        import psutil
        process = psutil.Process()
        return [(process.memory_info().rss, {})]
    
    def _get_cpu_usage(self, options):
        # Get current CPU usage
        import psutil
        return [(psutil.cpu_percent(interval=0.1), {})]
```

### 4. Trace Context Propagation
**Priority: High**
**Estimated Time: 4 hours per service**

#### 4.1 HTTP Client Instrumentation
- **File**: `[service]/core/telemetry/propagation.py`

```python
from opentelemetry.propagate import inject, extract
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

class TracePropagator:
    def __init__(self):
        self.propagator = TraceContextTextMapPropagator()
    
    def inject_trace_context(self, headers: dict) -> dict:
        """Inject trace context into outgoing HTTP headers"""
        inject(headers)
        return headers
    
    def extract_trace_context(self, headers: dict):
        """Extract trace context from incoming HTTP headers"""
        return extract(headers)
    
    async def traced_http_request(self, method: str, url: str, **kwargs):
        """Make HTTP request with trace context propagation"""
        headers = kwargs.get('headers', {})
        headers = self.inject_trace_context(headers)
        kwargs['headers'] = headers
        
        with tracer.start_as_current_span(f"http.{method.lower()}") as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", url)
            
            response = await http_client.request(method, url, **kwargs)
            
            span.set_attribute("http.status_code", response.status_code)
            return response
```

### 5. Service-Specific Instrumentation

#### 5.1 Web Scraper Service
**Priority: High**
**Estimated Time: 1 day**

- **Additional Metrics**:
  - URLs processed per second
  - Average fetch time
  - Cache hit rate
  - Robots.txt compliance rate

```python
# web_scraper/core/telemetry/scraper_metrics.py
class ScraperMetrics(ServiceMetrics):
    def __init__(self, meter):
        super().__init__(meter)
        
        self.urls_processed = meter.create_counter(
            name="scraper.urls.processed",
            description="Total URLs processed",
            unit="1"
        )
        
        self.fetch_duration = meter.create_histogram(
            name="scraper.fetch.duration",
            description="URL fetch duration",
            unit="ms"
        )
        
        self.cache_hits = meter.create_counter(
            name="scraper.cache.hits",
            description="Cache hit count",
            unit="1"
        )
        
        self.robots_compliance = meter.create_counter(
            name="scraper.robots.compliance",
            description="Robots.txt compliance checks",
            unit="1"
        )
```

- **Trace Instrumentation**:
```python
@tracer.start_as_current_span("scrape_url")
async def scrape_url(url: str):
    span = trace.get_current_span()
    span.set_attribute("url", url)
    span.set_attribute("user_agent", self.user_agent)
    
    # Check robots.txt
    with tracer.start_as_current_span("check_robots"):
        allowed = await self.check_robots(url)
        span.set_attribute("robots.allowed", allowed)
    
    # Fetch content
    with tracer.start_as_current_span("fetch_content"):
        content = await self.fetch(url)
        span.set_attribute("content.size", len(content))
        span.set_attribute("content.type", content.headers.get("content-type"))
    
    return content
```

#### 5.2 Content Processor Service
**Priority: High**
**Estimated Time: 1 day**

- **Additional Metrics**:
  - Documents processed
  - Extraction success rate
  - Average processing time by content type
  - Text extraction quality score

```python
# content_processor/core/telemetry/processor_metrics.py
class ProcessorMetrics(ServiceMetrics):
    def __init__(self, meter):
        super().__init__(meter)
        
        self.documents_processed = meter.create_counter(
            name="processor.documents.processed",
            description="Total documents processed",
            unit="1"
        )
        
        self.extraction_success = meter.create_counter(
            name="processor.extraction.success",
            description="Successful extractions",
            unit="1"
        )
        
        self.processing_duration = meter.create_histogram(
            name="processor.processing.duration",
            description="Document processing duration",
            unit="ms"
        )
        
        self.quality_score = meter.create_histogram(
            name="processor.quality.score",
            description="Extraction quality score",
            unit="1"
        )
```

#### 5.3 Search Engine Service
**Priority: High**
**Estimated Time: 1 day**

- **Additional Metrics**:
  - Query throughput
  - Search latency by query type
  - Result relevance scores
  - Index size and health

```python
# search_engine/core/telemetry/search_metrics.py
class SearchMetrics(ServiceMetrics):
    def __init__(self, meter):
        super().__init__(meter)
        
        self.queries_processed = meter.create_counter(
            name="search.queries.processed",
            description="Total queries processed",
            unit="1"
        )
        
        self.search_latency = meter.create_histogram(
            name="search.latency",
            description="Search query latency",
            unit="ms"
        )
        
        self.result_count = meter.create_histogram(
            name="search.result.count",
            description="Number of results returned",
            unit="1"
        )
        
        self.relevance_score = meter.create_histogram(
            name="search.relevance.score",
            description="Average relevance score",
            unit="1"
        )
```

#### 5.4 Weaviate Service
**Priority: High**
**Estimated Time: 1 day**

- **Additional Metrics**:
  - Vector operations per second
  - Embedding generation time
  - Vector similarity scores
  - Index performance

```python
# weaviate_service/core/telemetry/vector_metrics.py
class VectorMetrics(ServiceMetrics):
    def __init__(self, meter):
        super().__init__(meter)
        
        self.vector_operations = meter.create_counter(
            name="vector.operations.count",
            description="Total vector operations",
            unit="1"
        )
        
        self.embedding_duration = meter.create_histogram(
            name="vector.embedding.duration",
            description="Embedding generation duration",
            unit="ms"
        )
        
        self.similarity_scores = meter.create_histogram(
            name="vector.similarity.scores",
            description="Vector similarity scores",
            unit="1"
        )
        
        self.index_size = meter.create_observable_gauge(
            name="vector.index.size",
            description="Current vector index size",
            unit="1",
            callbacks=[self._get_index_size]
        )
```

#### 5.5 LLM Orchestrator Service
**Priority: High**
**Estimated Time: 1 day**

- **Additional Metrics**:
  - LLM API calls
  - Token usage
  - Response generation time
  - Model selection distribution

```python
# llm_orchestrator/core/telemetry/llm_metrics.py
class LLMMetrics(ServiceMetrics):
    def __init__(self, meter):
        super().__init__(meter)
        
        self.llm_calls = meter.create_counter(
            name="llm.api.calls",
            description="Total LLM API calls",
            unit="1"
        )
        
        self.token_usage = meter.create_counter(
            name="llm.token.usage",
            description="Total tokens used",
            unit="1"
        )
        
        self.generation_duration = meter.create_histogram(
            name="llm.generation.duration",
            description="Response generation duration",
            unit="ms"
        )
        
        self.model_selection = meter.create_counter(
            name="llm.model.selection",
            description="Model selection count",
            unit="1"
        )
```

### 6. Middleware Integration
**Priority: High**
**Estimated Time: 4 hours per service**

#### 6.1 FastAPI Middleware
- **File**: `[service]/middleware/telemetry_middleware.py`

```python
from fastapi import Request, Response
from opentelemetry import trace
import time

class TelemetryMiddleware:
    def __init__(self, app, tracer, metrics):
        self.app = app
        self.tracer = tracer
        self.metrics = metrics
    
    async def __call__(self, request: Request, call_next):
        # Start span for request
        with self.tracer.start_as_current_span(
            f"{request.method} {request.url.path}"
        ) as span:
            # Add request attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.scheme", request.url.scheme)
            span.set_attribute("http.host", request.url.hostname)
            span.set_attribute("http.target", request.url.path)
            
            # Record metrics
            start_time = time.time()
            
            try:
                response = await call_next(request)
                
                # Add response attributes
                span.set_attribute("http.status_code", response.status_code)
                
                # Record success metrics
                duration = (time.time() - start_time) * 1000
                self.metrics.request_counter.add(1, {"status": "success"})
                self.metrics.request_duration.record(duration)
                
                return response
                
            except Exception as e:
                # Record error
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                
                # Record error metrics
                self.metrics.error_counter.add(
                    1, 
                    {"error.type": type(e).__name__}
                )
                
                raise
```

### 7. Environment Configuration
**Priority: High**
**Estimated Time: 2 hours per service**

#### 7.1 Environment Variables
```bash
# Add to each service's .env file
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=docaiche-[service-name]
OTEL_SERVICE_VERSION=1.0.0
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_COMPRESSION=gzip
OTEL_METRIC_EXPORT_INTERVAL=10000
OTEL_TRACE_SAMPLING_RATE=1.0
```

#### 7.2 Docker Configuration Updates
```dockerfile
# Add to each service's Dockerfile
ENV OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
ENV OTEL_PYTHON_LOG_CORRELATION=true
ENV PYTHONUNBUFFERED=1

# Install instrumentation packages
RUN opentelemetry-bootstrap --action=install
```

### 8. Testing and Validation
**Priority: High**
**Estimated Time: 1 day per service**

#### 8.1 Unit Tests for Telemetry
```python
# tests/test_telemetry.py
import pytest
from unittest.mock import Mock, patch
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

def test_telemetry_initialization():
    """Test that telemetry is properly initialized"""
    tracer, meter = init_telemetry("test-service", "1.0.0")
    assert tracer is not None
    assert meter is not None

def test_metrics_collection():
    """Test that metrics are being collected"""
    meter = Mock()
    metrics = ServiceMetrics(meter)
    
    # Test request counter
    metrics.request_counter.add(1, {"status": "success"})
    meter.create_counter.assert_called()

def test_trace_propagation():
    """Test trace context propagation"""
    propagator = TracePropagator()
    headers = {}
    
    with tracer.start_as_current_span("test"):
        headers = propagator.inject_trace_context(headers)
        assert "traceparent" in headers
```

#### 8.2 Integration Tests
```python
# tests/test_telemetry_integration.py
async def test_end_to_end_tracing():
    """Test that traces flow through the service"""
    # Start a trace
    with tracer.start_as_current_span("test_request") as span:
        # Make a request that should be traced
        response = await client.get("/api/test")
        
        # Verify span attributes
        assert span.get_span_context().trace_id is not None
        assert span.attributes["http.status_code"] == 200
```

### 9. Monitoring and Alerting Setup
**Priority: Medium**
**Estimated Time: 4 hours per service**

#### 9.1 Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "[Service Name] Telemetry Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(service_request_count[5m])"
        }]
      },
      {
        "title": "Request Duration",
        "targets": [{
          "expr": "histogram_quantile(0.95, service_request_duration)"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(service_error_count[5m])"
        }]
      }
    ]
  }
}
```

#### 9.2 Alert Rules
```yaml
# prometheus/alerts/[service].yml
groups:
  - name: [service]_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(service_error_count[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in {{ $labels.service_name }}"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, service_request_duration) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency in {{ $labels.service_name }}"
```

## Implementation Timeline

### Week 1: Foundation
1. Install OpenTelemetry SDK in all services
2. Implement basic telemetry initialization
3. Add standard metrics collection
4. Set up trace propagation

### Week 2: Service-Specific
1. Implement service-specific metrics
2. Add detailed trace instrumentation
3. Integrate middleware
4. Configure environment

### Week 3: Testing and Polish
1. Write comprehensive tests
2. Validate data flow
3. Set up monitoring dashboards
4. Configure alerts

## Success Criteria
- [ ] All services exporting traces to collector
- [ ] All standard metrics being collected
- [ ] Trace context propagating between services
- [ ] Service-specific metrics implemented
- [ ] Dashboard showing real-time data
- [ ] Alerts configured and working
- [ ] Performance impact < 2%
- [ ] All tests passing

## Common Pitfalls to Avoid
1. **Missing Context Propagation**: Always inject/extract trace context
2. **High Cardinality**: Avoid high-cardinality labels in metrics
3. **Memory Leaks**: Properly clean up observers and callbacks
4. **Performance Impact**: Use sampling for high-volume services
5. **Missing Errors**: Always record exceptions in spans