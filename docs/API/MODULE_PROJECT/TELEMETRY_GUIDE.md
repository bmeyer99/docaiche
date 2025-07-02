# OpenTelemetry Implementation Guide

## Overview
This guide details how to implement OpenTelemetry instrumentation in the DocAIche modular API architecture. The goal is to provide comprehensive observability without the overhead of full microservices.

## Architecture Overview

```
┌─────────────────────┐     ┌──────────────────┐
│   FastAPI App       │────▶│ OTLP Exporter    │
│ (Auto-instrumented) │     └──────────────────┘
└─────────────────────┘              │
           │                         ▼
           ▼                ┌──────────────────┐
┌─────────────────────┐     │ OpenTelemetry    │
│  Service Layer      │────▶│ Collector        │
│  (Manual Spans)     │     └──────────────────┘
└─────────────────────┘              │
           │                         ▼
           ▼                ┌──────────────────┐
┌─────────────────────┐     │ Backends:        │
│   Module Layer      │     │ - Prometheus     │
│ (Detailed Spans)    │     │ - Loki          │
└─────────────────────┘     │ - Grafana       │
                            └──────────────────┘
```

## Installation

### Required Packages
```bash
# Add to requirements.txt
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation==0.42b0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-httpx==0.42b0
opentelemetry-instrumentation-redis==0.42b0
opentelemetry-instrumentation-sqlalchemy==0.42b0
opentelemetry-instrumentation-logging==0.42b0
opentelemetry-exporter-otlp-proto-grpc==1.21.0
opentelemetry-exporter-prometheus==0.42b0
```

## Core Implementation

### 1. Telemetry Initialization
```python
# src/core/telemetry/__init__.py
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagate import set_global_textmap

def init_telemetry(
    service_name: str = "docaiche-api",
    service_version: str = "1.0.0",
    otlp_endpoint: str = None
):
    """Initialize OpenTelemetry with auto-instrumentation"""
    
    # Create resource identifying this service
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "service.environment": os.getenv("ENVIRONMENT", "development"),
        "service.instance.id": os.getenv("HOSTNAME", "local"),
        "telemetry.sdk.language": "python",
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.version": "1.21.0",
    })
    
    # Initialize tracing
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,  # Use TLS in production
    )
    
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # Initialize metrics
    metric_reader = PeriodicExportingMetricReader(
        exporter=OTLPMetricExporter(
            endpoint=otlp_endpoint,
            insecure=True,
        ),
        export_interval_millis=10000,  # Export every 10 seconds
    )
    
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    metrics.set_meter_provider(meter_provider)
    
    # Set up context propagation
    set_global_textmap(TraceContextTextMapPropagator())
    
    # Return configured providers
    return tracer_provider, meter_provider

def instrument_app(app):
    """Apply automatic instrumentation to FastAPI app"""
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
        excluded_urls="/health,/metrics",  # Don't trace health checks
    )
    
    # Instrument HTTP client
    HTTPXClientInstrumentor().instrument(
        tracer_provider=trace.get_tracer_provider()
    )
    
    # Instrument Redis
    RedisInstrumentor().instrument(
        tracer_provider=trace.get_tracer_provider()
    )
    
    # Instrument logging to inject trace context
    LoggingInstrumentor().instrument(
        set_logging_format=True,
        log_level="INFO"
    )
```

### 2. Service Layer Telemetry
```python
# src/services/telemetry_mixin.py
from typing import Any, Callable, Dict
from functools import wraps
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from time import time

class TelemetryMixin:
    """Mixin for adding telemetry to services"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.tracer = trace.get_tracer(f"docaiche.service.{service_name}")
        self.meter = metrics.get_meter(f"docaiche.service.{service_name}")
        
        # Create standard metrics
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup standard service metrics"""
        self.request_counter = self.meter.create_counter(
            name=f"{self.service_name}.requests",
            description=f"Total requests to {self.service_name}",
            unit="1"
        )
        
        self.request_duration = self.meter.create_histogram(
            name=f"{self.service_name}.duration",
            description=f"Request duration in {self.service_name}",
            unit="ms"
        )
        
        self.error_counter = self.meter.create_counter(
            name=f"{self.service_name}.errors",
            description=f"Total errors in {self.service_name}",
            unit="1"
        )
        
        self.active_requests = self.meter.create_up_down_counter(
            name=f"{self.service_name}.active_requests",
            description=f"Active requests in {self.service_name}",
            unit="1"
        )
    
    def traced(self, operation_name: str = None):
        """Decorator for tracing service methods"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                span_name = operation_name or func.__name__
                
                # Start span
                with self.tracer.start_as_current_span(
                    f"{self.service_name}.{span_name}"
                ) as span:
                    # Add span attributes
                    span.set_attribute("service.name", self.service_name)
                    span.set_attribute("operation.name", span_name)
                    
                    # Record metrics
                    self.active_requests.add(1)
                    self.request_counter.add(1, {"operation": span_name})
                    
                    start_time = time()
                    try:
                        # Execute function
                        result = await func(*args, **kwargs)
                        
                        # Set success status
                        span.set_status(Status(StatusCode.OK))
                        
                        return result
                        
                    except Exception as e:
                        # Record error
                        span.record_exception(e)
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                        
                        # Record error metric
                        self.error_counter.add(
                            1, 
                            {
                                "operation": span_name,
                                "error_type": type(e).__name__
                            }
                        )
                        
                        raise
                        
                    finally:
                        # Record duration
                        duration_ms = (time() - start_time) * 1000
                        self.request_duration.record(
                            duration_ms,
                            {"operation": span_name}
                        )
                        
                        # Decrement active requests
                        self.active_requests.add(-1)
            
            return wrapper
        return decorator
```

### 3. Module Instrumentation Pattern
```python
# src/modules/content_processor/instrumented.py
from opentelemetry import trace
from typing import Dict, Any
import time

class InstrumentedContentProcessor:
    """Content processor with OpenTelemetry instrumentation"""
    
    def __init__(self, processor: ContentProcessorInterface):
        self.processor = processor
        self.tracer = trace.get_tracer("docaiche.module.content_processor")
    
    async def process_document(
        self, 
        file_path: str, 
        options: Dict[str, Any] = None
    ) -> ProcessedDocument:
        """Process document with telemetry"""
        
        with self.tracer.start_as_current_span("process_document") as span:
            # Add input attributes
            span.set_attribute("document.path", str(file_path))
            span.set_attribute("document.size", os.path.getsize(file_path))
            
            if options:
                for key, value in options.items():
                    span.set_attribute(f"option.{key}", str(value))
            
            # Extract text phase
            with self.tracer.start_as_current_span("extract_text") as extract_span:
                start = time.time()
                text = await self.processor.extract_text(file_path)
                extract_span.set_attribute("text.length", len(text))
                extract_span.set_attribute("duration_ms", (time.time() - start) * 1000)
            
            # Chunk document phase
            with self.tracer.start_as_current_span("chunk_document") as chunk_span:
                chunks = await self.processor.chunk_document(text)
                chunk_span.set_attribute("chunk.count", len(chunks))
                chunk_span.set_attribute("chunk.avg_size", 
                    sum(len(c.text) for c in chunks) / len(chunks) if chunks else 0
                )
            
            # Generate embeddings phase
            with self.tracer.start_as_current_span("generate_embeddings") as embed_span:
                embeddings = []
                for i, chunk in enumerate(chunks):
                    with self.tracer.start_as_current_span(f"embed_chunk_{i}"):
                        embedding = await self.processor.generate_embeddings(chunk.text)
                        embeddings.append(embedding)
                
                embed_span.set_attribute("embeddings.count", len(embeddings))
            
            # Create result
            result = ProcessedDocument(
                id=str(uuid.uuid4()),
                file_path=str(file_path),
                content=text,
                chunks=chunks,
                embeddings=embeddings
            )
            
            # Add result attributes
            span.set_attribute("document.id", result.id)
            span.set_attribute("processing.success", True)
            
            return result
```

## Integration with Existing Stack

### 1. Docker Compose Addition
```yaml
# Add to docker-compose.yml
otel-collector:
  image: otel/opentelemetry-collector-contrib:0.91.0
  command: ["--config=/etc/otel-collector-config.yaml"]
  volumes:
    - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
  ports:
    - "4317:4317"   # OTLP gRPC
    - "4318:4318"   # OTLP HTTP
    - "8888:8888"   # Prometheus metrics
  networks:
    - docaiche
  depends_on:
    - prometheus
    - loki
```

### 2. OpenTelemetry Collector Configuration
```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  
  resource:
    attributes:
      - key: environment
        value: ${ENVIRONMENT}
        action: upsert
  
  attributes:
    actions:
      - key: http.user_agent
        action: delete  # Remove sensitive data

exporters:
  prometheus:
    endpoint: "0.0.0.0:8888"
    namespace: docaiche
    
  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"
    labels:
      attributes:
        service.name: "service_name"
        service.version: "service_version"
    
  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [loki, logging]
    
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

### 3. Application Integration
```python
# src/main.py updates
from src.core.telemetry import init_telemetry, instrument_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with telemetry"""
    # Initialize telemetry
    tracer_provider, meter_provider = init_telemetry(
        service_name="docaiche-api",
        service_version="2.1.0"
    )
    
    # Apply auto-instrumentation
    instrument_app(app)
    
    # ... rest of startup code ...
    
    yield
    
    # Shutdown telemetry
    if tracer_provider:
        tracer_provider.shutdown()
    if meter_provider:
        meter_provider.shutdown()
```

## Telemetry Patterns

### 1. Span Naming Convention
```
service.operation.sub_operation

Examples:
- docaiche-api.document_upload
- content_service.process_document
- content_processor.extract_text
```

### 2. Attribute Standards
```python
# Document attributes
span.set_attribute("document.id", doc_id)
span.set_attribute("document.type", "pdf")
span.set_attribute("document.size_bytes", 1024000)
span.set_attribute("document.page_count", 10)

# Operation attributes
span.set_attribute("operation.name", "process")
span.set_attribute("operation.status", "success")
span.set_attribute("operation.duration_ms", 1500)

# Error attributes
span.set_attribute("error.type", "ValidationError")
span.set_attribute("error.message", str(error))
```

### 3. Metric Naming Convention
```
{service_name}.{metric_type}.{operation}

Examples:
- content_service.requests.total
- content_service.duration.process_document
- content_service.errors.validation
```

## Grafana Dashboard Configuration

### 1. Service Overview Dashboard
```json
{
  "dashboard": {
    "title": "DocAIche Service Overview",
    "panels": [
      {
        "title": "Request Rate by Service",
        "targets": [{
          "expr": "rate(docaiche_requests_total[5m])"
        }]
      },
      {
        "title": "Request Duration P95",
        "targets": [{
          "expr": "histogram_quantile(0.95, docaiche_duration_bucket)"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(docaiche_errors_total[5m])"
        }]
      }
    ]
  }
}
```

### 2. Trace Query Examples
```
# Find slow operations
duration > 1s AND service.name = "content_service"

# Find failed operations
status.code = "ERROR" AND operation.name = "process_document"

# Trace specific document
document.id = "12345"
```

## Performance Considerations

### 1. Sampling Strategy
```python
# src/core/telemetry/sampling.py
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased

def create_sampler(sample_rate: float = 0.1):
    """Create sampler with configurable rate"""
    return ParentBased(
        root=TraceIdRatioBased(sample_rate),
        remote_parent_sampled=True,
        remote_parent_not_sampled=False,
        local_parent_sampled=True,
        local_parent_not_sampled=False,
    )
```

### 2. Span Limits
```python
# Limit span attributes to prevent memory issues
span_limits = trace.SpanLimits(
    max_attributes=128,
    max_events=128,
    max_links=128,
    max_attribute_length=4096,
)
```

### 3. Async Batching
```python
# Configure batch processor for better performance
span_processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    max_export_batch_size=512,
    schedule_delay_millis=5000,  # 5 second delay
)
```

## Troubleshooting

### Common Issues

1. **Missing Spans**
   - Check OTEL_EXPORTER_OTLP_ENDPOINT is set
   - Verify collector is running
   - Check for sampling configuration

2. **High Memory Usage**
   - Reduce span attribute limits
   - Increase batch export frequency
   - Enable sampling

3. **Correlation Issues**
   - Ensure trace propagation is configured
   - Check for context loss in async operations
   - Verify all services use same propagator

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
```

## Best Practices

1. **Use Semantic Conventions**: Follow OpenTelemetry semantic conventions for attributes
2. **Limit Cardinality**: Avoid high-cardinality attributes (e.g., user IDs in metric labels)
3. **Error Handling**: Always record exceptions in spans
4. **Context Propagation**: Ensure trace context is propagated across async boundaries
5. **Resource Efficiency**: Use sampling in production to reduce overhead