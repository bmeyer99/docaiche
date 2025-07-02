# Modular API Architecture Design

## Current State
The DocAIche API is a monolithic FastAPI application with tightly coupled modules:
```
src/
├── api/           # API endpoints
├── processors/    # Content processing
├── search/        # Search orchestration
├── ingestion/     # Document ingestion
├── enrichment/    # Content enrichment
└── core/          # Shared utilities
```

## Target Architecture

### Layer 1: API Gateway Layer
```python
# src/api/v1/endpoints/
├── documents.py    # Document endpoints
├── search.py       # Search endpoints
├── analytics.py    # Analytics endpoints
└── admin.py        # Admin endpoints
```

### Layer 2: Service Facade Layer (NEW)
```python
# src/services/
├── __init__.py
├── base.py                    # BaseService abstract class
├── content_service.py         # Content processing service
├── search_service.py          # Search orchestration service
├── ingestion_service.py       # Document ingestion service
├── enrichment_service.py      # Content enrichment service
└── telemetry.py              # Service telemetry utilities
```

### Layer 3: Module Implementation Layer
```python
# Existing modules refactored with clean interfaces
src/modules/
├── content_processor/
│   ├── __init__.py
│   ├── interface.py          # Module interface definition
│   ├── implementation.py     # Actual implementation
│   └── models.py            # Data models
├── search_engine/
├── web_scraper/
└── llm_orchestrator/
```

## Key Design Patterns

### 1. Service Facade Pattern
Each service facade provides a clean interface to underlying modules:

```python
# src/services/base.py
from abc import ABC, abstractmethod
from opentelemetry import trace

class BaseService(ABC):
    def __init__(self, name: str, dependencies: dict):
        self.name = name
        self.tracer = trace.get_tracer(f"docaiche.{name}")
        self.dependencies = dependencies
    
    @abstractmethod
    async def initialize(self):
        """Initialize service resources"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """Cleanup service resources"""
        pass
```

### 2. Dependency Injection Container
```python
# src/core/dependencies.py
class DependencyContainer:
    def __init__(self):
        self._services = {}
        self._configs = {}
        self._connections = {}
    
    def register_service(self, name: str, service: BaseService):
        self._services[name] = service
    
    def get_service(self, name: str) -> BaseService:
        return self._services.get(name)
```

### 3. Module Interface Pattern
```python
# src/modules/content_processor/interface.py
from typing import Protocol, Dict, Any

class ContentProcessorInterface(Protocol):
    async def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document and return results"""
        ...
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text from file"""
        ...
```

## Request Flow

### Current Flow
```
API Endpoint → Direct Module Call → Response
```

### New Flow
```
API Endpoint 
    → Service Facade (with telemetry)
    → Module Interface
    → Implementation
    → Response (with metrics)
```

## Telemetry Integration

### Span Hierarchy
```
docaiche-api (root span)
├── document_upload
│   ├── content_service.process
│   │   ├── validate_document
│   │   ├── extract_text
│   │   └── generate_embeddings
│   └── enrichment_service.enrich
│       ├── extract_entities
│       └── classify_content
└── search_query
    ├── search_service.search
    │   ├── parse_query
    │   ├── vector_search
    │   └── rank_results
    └── cache_check
```

### Metrics Collection
```python
# Automatic metrics at service boundaries
- Request count by service
- Request duration by operation
- Error rate by service
- Queue depth (for async operations)
- Resource utilization
```

## Configuration Management

### Service Configuration
```yaml
# config/services.yaml
services:
  content_service:
    max_file_size: 100MB
    supported_formats: [pdf, docx, txt, html]
    processing_timeout: 300s
    
  search_service:
    max_results: 100
    similarity_threshold: 0.7
    cache_ttl: 3600s
```

## Benefits of This Architecture

1. **Clear Boundaries**: Each module has defined interfaces
2. **Testability**: Easy to mock services for testing
3. **Observability**: Automatic telemetry at service boundaries
4. **Future-Ready**: Services can be extracted with minimal changes
5. **Performance**: No network overhead, direct function calls
6. **Flexibility**: Easy to add new services or modify existing ones

## Migration Path to Microservices

If needed in the future, each service facade can be converted to a separate container:

1. Replace direct calls with HTTP/gRPC clients
2. Add service discovery
3. Implement circuit breakers
4. Deploy as separate containers

The interfaces remain the same, minimizing code changes.