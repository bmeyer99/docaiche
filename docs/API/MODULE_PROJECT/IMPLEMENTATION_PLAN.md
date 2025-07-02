# Implementation Plan - Modular API Project

## Overview
This document provides a detailed step-by-step implementation plan for transforming the DocAIche API into a modular architecture. Each phase builds upon the previous one, allowing for incremental progress and testing.

## Phase 1: Foundation (Days 1-2)

### Task 1.1: Create Service Layer Structure
**Priority**: High  
**Duration**: 2 hours

```bash
mkdir -p src/services
mkdir -p src/modules
mkdir -p src/core/telemetry
mkdir -p config/services
```

**Todo Items**:
- [ ] Create service layer directory structure
- [ ] Create module directory structure
- [ ] Create telemetry directory structure
- [ ] Create service configuration directory

### Task 1.2: Implement Base Service Class
**Priority**: High  
**Duration**: 3 hours

Create `src/services/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from opentelemetry import trace, metrics
import logging

class BaseService(ABC):
    """Base class for all services with telemetry integration"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"docaiche.service.{name}")
        self.tracer = trace.get_tracer(f"docaiche.service.{name}")
        self.meter = metrics.get_meter(f"docaiche.service.{name}")
        self._initialized = False
        
        # Create standard metrics
        self._request_counter = self.meter.create_counter(
            name=f"{name}.requests",
            description=f"Total requests to {name} service"
        )
        self._request_duration = self.meter.create_histogram(
            name=f"{name}.duration",
            description=f"Request duration for {name} service",
            unit="ms"
        )
    
    @abstractmethod
    async def initialize(self):
        """Initialize service resources"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """Cleanup service resources"""
        pass
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
```

**Todo Items**:
- [ ] Create BaseService abstract class
- [ ] Add telemetry integration (tracer, meter)
- [ ] Add standard metrics (request count, duration)
- [ ] Add logging configuration
- [ ] Add async context manager support

### Task 1.3: Implement Dependency Injection Container
**Priority**: High  
**Duration**: 4 hours

Create `src/core/dependencies.py`:
```python
from typing import Dict, Any, TypeVar, Type
from src.services.base import BaseService

T = TypeVar('T')

class DependencyContainer:
    """Central dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, BaseService] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Any] = {}
    
    def register_service(self, service_class: Type[T], name: str = None) -> None:
        """Register a service class"""
        pass
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance"""
        pass
    
    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance"""
        pass
```

**Todo Items**:
- [ ] Create DependencyContainer class
- [ ] Implement service registration
- [ ] Implement service resolution
- [ ] Add singleton support
- [ ] Add factory pattern support
- [ ] Add configuration injection

### Task 1.4: Setup OpenTelemetry
**Priority**: High  
**Duration**: 3 hours

Create `src/core/telemetry/__init__.py`:
```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def init_telemetry(app_name: str = "docaiche-api"):
    """Initialize OpenTelemetry for the application"""
    pass
```

**Todo Items**:
- [ ] Install OpenTelemetry packages
- [ ] Create telemetry initialization
- [ ] Configure trace provider
- [ ] Configure metrics provider
- [ ] Setup OTLP exporters
- [ ] Add FastAPI auto-instrumentation

## Phase 2: Module Refactoring (Days 3-5)

### Task 2.1: Create Module Interfaces
**Priority**: High  
**Duration**: 4 hours

For each major module, create interface definitions:

```python
# src/modules/content_processor/interface.py
from typing import Protocol, Dict, Any, List

class ContentProcessorInterface(Protocol):
    """Interface for content processing operations"""
    
    async def process_document(self, 
                             file_path: str, 
                             options: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document and extract content"""
        ...
    
    async def extract_text(self, file_path: str) -> str:
        """Extract plain text from document"""
        ...
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        ...
```

**Todo Items**:
- [ ] Create ContentProcessorInterface
- [ ] Create SearchEngineInterface
- [ ] Create IngestionPipelineInterface
- [ ] Create EnrichmentServiceInterface
- [ ] Define data models for each interface

### Task 2.2: Refactor Content Processor Module
**Priority**: High  
**Duration**: 6 hours

Refactor the existing content processor to implement the interface:

**Todo Items**:
- [ ] Move content processor to modules directory
- [ ] Implement ContentProcessorInterface
- [ ] Extract configuration to separate file
- [ ] Add input validation
- [ ] Add error handling
- [ ] Add logging at key points
- [ ] Write unit tests for interface

### Task 2.3: Refactor Search Module
**Priority**: High  
**Duration**: 6 hours

**Todo Items**:
- [ ] Move search orchestrator to modules directory
- [ ] Implement SearchEngineInterface
- [ ] Separate search logic from API concerns
- [ ] Add caching layer abstraction
- [ ] Add search metrics collection
- [ ] Write unit tests

### Task 2.4: Refactor Ingestion Module
**Priority**: Medium  
**Duration**: 4 hours

**Todo Items**:
- [ ] Move ingestion pipeline to modules directory
- [ ] Implement IngestionPipelineInterface
- [ ] Add batch processing support
- [ ] Add progress tracking
- [ ] Write unit tests

### Task 2.5: Refactor Enrichment Module
**Priority**: Medium  
**Duration**: 4 hours

**Todo Items**:
- [ ] Move enrichment logic to modules directory
- [ ] Implement EnrichmentServiceInterface
- [ ] Add plugin architecture for enrichers
- [ ] Write unit tests

## Phase 3: Service Implementation (Days 6-7)

### Task 3.1: Implement Content Service
**Priority**: High  
**Duration**: 4 hours

Create `src/services/content_service.py`:

**Todo Items**:
- [ ] Create ContentService class extending BaseService
- [ ] Inject ContentProcessor module
- [ ] Add telemetry spans for each operation
- [ ] Add metrics collection
- [ ] Add error handling and recovery
- [ ] Add input validation
- [ ] Write integration tests

### Task 3.2: Implement Search Service
**Priority**: High  
**Duration**: 4 hours

**Todo Items**:
- [ ] Create SearchService class
- [ ] Inject SearchEngine module
- [ ] Add caching layer
- [ ] Add telemetry for search operations
- [ ] Add search analytics
- [ ] Write integration tests

### Task 3.3: Implement Ingestion Service
**Priority**: Medium  
**Duration**: 3 hours

**Todo Items**:
- [ ] Create IngestionService class
- [ ] Add queue management
- [ ] Add progress tracking
- [ ] Add telemetry
- [ ] Write integration tests

### Task 3.4: Implement Enrichment Service
**Priority**: Medium  
**Duration**: 3 hours

**Todo Items**:
- [ ] Create EnrichmentService class
- [ ] Add enrichment pipeline
- [ ] Add telemetry
- [ ] Write integration tests

## Phase 4: API Integration (Days 8-9)

### Task 4.1: Update API Endpoints
**Priority**: High  
**Duration**: 6 hours

Refactor API endpoints to use services instead of direct module calls:

**Todo Items**:
- [ ] Update document upload endpoint
- [ ] Update search endpoint
- [ ] Update admin endpoints
- [ ] Update analytics endpoints
- [ ] Add service dependency injection
- [ ] Update error handling

### Task 4.2: Update Application Startup
**Priority**: High  
**Duration**: 3 hours

Update `src/main.py` to initialize services:

**Todo Items**:
- [ ] Add service initialization in lifespan
- [ ] Add telemetry initialization
- [ ] Register services in DI container
- [ ] Add health checks for services
- [ ] Add graceful shutdown

### Task 4.3: Configuration Management
**Priority**: Medium  
**Duration**: 2 hours

**Todo Items**:
- [ ] Create service configuration files
- [ ] Add configuration validation
- [ ] Add environment variable support
- [ ] Document configuration options

## Phase 5: Testing & Optimization (Days 10-11)

### Task 5.1: Integration Testing
**Priority**: High  
**Duration**: 4 hours

**Todo Items**:
- [ ] Write end-to-end tests
- [ ] Test service interactions
- [ ] Test telemetry data
- [ ] Test error scenarios
- [ ] Performance testing

### Task 5.2: Performance Optimization
**Priority**: Medium  
**Duration**: 4 hours

**Todo Items**:
- [ ] Profile application performance
- [ ] Optimize hot paths
- [ ] Reduce memory allocations
- [ ] Optimize telemetry overhead
- [ ] Document performance metrics

### Task 5.3: Documentation
**Priority**: Medium  
**Duration**: 3 hours

**Todo Items**:
- [ ] Update API documentation
- [ ] Document service interfaces
- [ ] Create architecture diagrams
- [ ] Write operation guide
- [ ] Update README files

## Phase 6: Deployment (Day 12)

### Task 6.1: Update Deployment Configuration
**Priority**: High  
**Duration**: 2 hours

**Todo Items**:
- [ ] Update Docker configuration
- [ ] Add OpenTelemetry collector
- [ ] Update environment variables
- [ ] Test deployment locally
- [ ] Create rollback plan

### Task 6.2: Monitoring Setup
**Priority**: High  
**Duration**: 3 hours

**Todo Items**:
- [ ] Configure Grafana dashboards
- [ ] Setup alerting rules
- [ ] Configure trace visualization
- [ ] Test monitoring pipeline
- [ ] Document monitoring setup

## Success Metrics

### Performance Metrics
- [ ] API response time < 5% increase
- [ ] Memory usage < 10% increase
- [ ] CPU usage < 5% increase

### Code Quality Metrics
- [ ] Test coverage > 80%
- [ ] All interfaces documented
- [ ] No circular dependencies
- [ ] Clean separation of concerns

### Observability Metrics
- [ ] All service calls traced
- [ ] Key metrics exported
- [ ] Logs correlated with traces
- [ ] Dashboards functional

## Rollback Plan

If issues arise:
1. Services can be bypassed by routing directly to modules
2. Telemetry can be disabled via configuration
3. Git tags mark each phase completion
4. Database changes are backward compatible

## Notes

- Each task includes specific todo items for easy tracking
- Priorities help focus on critical path items
- Duration estimates include testing and documentation
- Phase completion should be marked with git tags
- Regular testing ensures no regression