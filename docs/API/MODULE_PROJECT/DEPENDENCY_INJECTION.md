# Dependency Injection Implementation Guide

## Overview
This guide details the implementation of dependency injection (DI) in the DocAIche modular API architecture. DI enables loose coupling between modules, improves testability, and prepares the codebase for potential future microservices extraction.

## Core Concepts

### Benefits of Dependency Injection
1. **Loose Coupling**: Modules depend on interfaces, not concrete implementations
2. **Testability**: Easy to inject mocks for unit testing
3. **Flexibility**: Switch implementations without changing dependent code
4. **Configuration**: Centralized dependency configuration
5. **Lifecycle Management**: Proper initialization and cleanup of resources

## Implementation

### 1. Dependency Container
```python
# src/core/di/container.py
from typing import Dict, Type, TypeVar, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import inspect

T = TypeVar('T')

class Scope(Enum):
    """Dependency lifecycle scope"""
    SINGLETON = "singleton"      # One instance for app lifetime
    SCOPED = "scoped"            # One instance per request
    TRANSIENT = "transient"      # New instance each time

@dataclass
class Registration:
    """Dependency registration details"""
    factory: Callable
    scope: Scope
    interface: Optional[Type] = None
    is_async: bool = False

class DependencyContainer:
    """
    Dependency injection container with support for different scopes
    and async initialization.
    """
    
    def __init__(self):
        self._registrations: Dict[Type, Registration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        
    def register(
        self,
        interface: Type[T],
        implementation: Type[T] = None,
        factory: Callable = None,
        scope: Scope = Scope.SINGLETON,
        **kwargs
    ) -> None:
        """
        Register a dependency.
        
        Args:
            interface: Interface or base class
            implementation: Concrete implementation class
            factory: Factory function to create instances
            scope: Lifecycle scope
            **kwargs: Additional arguments for factory
        """
        if implementation is None and factory is None:
            raise ValueError("Must provide either implementation or factory")
        
        if factory is None:
            # Create default factory from implementation
            def default_factory(**deps):
                return implementation(**deps, **kwargs)
            factory = default_factory
        
        # Check if factory is async
        is_async = asyncio.iscoroutinefunction(factory)
        
        self._registrations[interface] = Registration(
            factory=factory,
            scope=scope,
            interface=interface,
            is_async=is_async
        )
    
    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """Register an existing instance as a singleton"""
        self._singletons[interface] = instance
        self._registrations[interface] = Registration(
            factory=lambda: instance,
            scope=Scope.SINGLETON,
            interface=interface
        )
    
    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a named factory function"""
        self._factories[name] = factory
    
    async def resolve(self, interface: Type[T], scope_id: str = None) -> T:
        """
        Resolve a dependency with automatic dependency injection.
        
        Args:
            interface: Interface to resolve
            scope_id: Scope identifier for scoped dependencies
            
        Returns:
            Instance of the requested type
        """
        if interface not in self._registrations:
            raise KeyError(f"No registration found for {interface}")
        
        registration = self._registrations[interface]
        
        # Handle singleton scope
        if registration.scope == Scope.SINGLETON:
            if interface in self._singletons:
                return self._singletons[interface]
            
            instance = await self._create_instance(registration)
            self._singletons[interface] = instance
            return instance
        
        # Handle scoped dependencies
        elif registration.scope == Scope.SCOPED:
            if scope_id is None:
                raise ValueError("Scope ID required for scoped dependencies")
            
            if scope_id not in self._scoped_instances:
                self._scoped_instances[scope_id] = {}
            
            if interface in self._scoped_instances[scope_id]:
                return self._scoped_instances[scope_id][interface]
            
            instance = await self._create_instance(registration)
            self._scoped_instances[scope_id][interface] = instance
            return instance
        
        # Handle transient dependencies
        else:
            return await self._create_instance(registration)
    
    async def _create_instance(self, registration: Registration) -> Any:
        """Create an instance with dependency injection"""
        factory = registration.factory
        
        # Get factory signature
        sig = inspect.signature(factory)
        
        # Resolve dependencies
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param.annotation != param.empty:
                # Try to resolve dependency
                try:
                    dep = await self.resolve(param.annotation)
                    kwargs[param_name] = dep
                except KeyError:
                    # Skip if not registered
                    pass
        
        # Create instance
        if registration.is_async:
            return await factory(**kwargs)
        else:
            return factory(**kwargs)
    
    def clear_scope(self, scope_id: str) -> None:
        """Clear all instances in a scope"""
        if scope_id in self._scoped_instances:
            del self._scoped_instances[scope_id]
    
    async def dispose(self) -> None:
        """Dispose of all resources"""
        # Dispose singletons that have cleanup methods
        for instance in self._singletons.values():
            if hasattr(instance, 'dispose'):
                if asyncio.iscoroutinefunction(instance.dispose):
                    await instance.dispose()
                else:
                    instance.dispose()
        
        self._singletons.clear()
        self._scoped_instances.clear()

# Global container instance
container = DependencyContainer()
```

### 2. Service Registration
```python
# src/core/di/registrations.py
from src.core.di.container import container, Scope
from src.services.base import BaseService
from src.modules.content_processor.interface import ContentProcessorInterface
from src.modules.search_engine.interface import SearchEngineInterface

async def register_services():
    """Register all services and their dependencies"""
    
    # Register configuration
    from src.core.config import get_configuration
    config = await get_configuration()
    container.register_singleton(Configuration, config)
    
    # Register database connection
    from src.database.connection import create_database_manager
    container.register(
        DatabaseManager,
        factory=create_database_manager,
        scope=Scope.SINGLETON
    )
    
    # Register Redis connection
    from src.cache.redis_client import create_redis_client
    container.register(
        RedisClient,
        factory=create_redis_client,
        scope=Scope.SINGLETON
    )
    
    # Register module implementations
    from src.modules.content_processor.implementation import ContentProcessor
    container.register(
        ContentProcessorInterface,
        implementation=ContentProcessor,
        scope=Scope.SINGLETON
    )
    
    from src.modules.search_engine.implementation import SearchEngine
    container.register(
        SearchEngineInterface,
        implementation=SearchEngine,
        scope=Scope.SINGLETON
    )
    
    # Register services
    from src.services.content_service import ContentService
    container.register(
        ContentService,
        scope=Scope.SINGLETON
    )
    
    from src.services.search_service import SearchService
    container.register(
        SearchService,
        scope=Scope.SINGLETON
    )
```

### 3. FastAPI Integration
```python
# src/core/di/dependencies.py
from typing import Annotated
from fastapi import Depends, Request
from src.core.di.container import container

async def get_container(request: Request) -> DependencyContainer:
    """Get DI container from request"""
    return request.app.state.container

# Dependency injection for FastAPI endpoints
async def get_content_service(
    container: Annotated[DependencyContainer, Depends(get_container)]
) -> ContentService:
    """Inject content service"""
    return await container.resolve(ContentService, scope_id=str(request.state.request_id))

async def get_search_service(
    container: Annotated[DependencyContainer, Depends(get_container)]
) -> SearchService:
    """Inject search service"""
    return await container.resolve(SearchService, scope_id=str(request.state.request_id))

# Request-scoped dependencies
async def get_request_context(request: Request) -> RequestContext:
    """Get request context"""
    return RequestContext(
        request_id=request.state.request_id,
        user_id=request.state.user_id,
        correlation_id=request.headers.get("X-Correlation-ID")
    )
```

### 4. Service Implementation with DI
```python
# src/services/content_service.py
from typing import Dict, Any
from src.services.base import BaseService
from src.modules.content_processor.interface import ContentProcessorInterface
from src.database.connection import DatabaseManager
from src.cache.redis_client import RedisClient

class ContentService(BaseService):
    """Content processing service with dependency injection"""
    
    def __init__(
        self,
        content_processor: ContentProcessorInterface,
        database: DatabaseManager,
        cache: RedisClient,
        config: Configuration
    ):
        super().__init__("content_service", config.content_service)
        self.processor = content_processor
        self.db = database
        self.cache = cache
        
    async def initialize(self):
        """Initialize service"""
        self.logger.info("Initializing content service")
        # Any async initialization
        
    async def shutdown(self):
        """Cleanup service"""
        self.logger.info("Shutting down content service")
        # Any cleanup needed
    
    @traced("process_document")
    async def process_document(
        self,
        file_path: str,
        workspace_id: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process a document with caching"""
        
        # Check cache
        cache_key = f"doc:processed:{file_path}:{workspace_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            self.logger.info(f"Cache hit for {file_path}")
            return cached
        
        # Process document
        result = await self.processor.process_document(file_path, options)
        
        # Store in database
        async with self.db.transaction() as tx:
            await tx.documents.insert({
                "id": result.id,
                "workspace_id": workspace_id,
                "file_path": file_path,
                "content": result.content,
                "metadata": result.metadata.dict()
            })
        
        # Cache result
        await self.cache.set(cache_key, result.dict(), ttl=3600)
        
        return result.dict()
```

### 5. Testing with DI
```python
# tests/test_content_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.services.content_service import ContentService
from src.modules.content_processor.interface import ContentProcessorInterface
from src.core.di.container import DependencyContainer

@pytest.fixture
def mock_processor():
    """Create mock content processor"""
    processor = AsyncMock(spec=ContentProcessorInterface)
    processor.process_document.return_value = ProcessedDocument(
        id="test-123",
        file_path="/test/doc.pdf",
        content="Test content",
        metadata=DocumentMetadata()
    )
    return processor

@pytest.fixture
def mock_database():
    """Create mock database"""
    db = AsyncMock()
    db.transaction.return_value.__aenter__.return_value = Mock()
    return db

@pytest.fixture
def mock_cache():
    """Create mock cache"""
    cache = AsyncMock()
    cache.get.return_value = None
    return cache

@pytest.fixture
async def content_service(mock_processor, mock_database, mock_cache):
    """Create content service with mocked dependencies"""
    service = ContentService(
        content_processor=mock_processor,
        database=mock_database,
        cache=mock_cache,
        config=Configuration(content_service={})
    )
    await service.initialize()
    yield service
    await service.shutdown()

async def test_process_document(content_service, mock_processor):
    """Test document processing"""
    result = await content_service.process_document(
        "/test/doc.pdf",
        "workspace-123"
    )
    
    assert result["id"] == "test-123"
    assert mock_processor.process_document.called
```

### 6. Configuration-Based Wiring
```python
# src/core/di/config_loader.py
import yaml
from typing import Dict, Any
from src.core.di.container import container, Scope

def load_di_config(config_path: str):
    """Load DI configuration from YAML"""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    for service_config in config.get("services", []):
        interface = locate_class(service_config["interface"])
        implementation = locate_class(service_config["implementation"])
        scope = Scope[service_config.get("scope", "SINGLETON").upper()]
        
        container.register(
            interface=interface,
            implementation=implementation,
            scope=scope,
            **service_config.get("kwargs", {})
        )

def locate_class(class_path: str):
    """Dynamically locate a class from string path"""
    module_path, class_name = class_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)
```

### 7. DI Configuration Example
```yaml
# config/di.yaml
services:
  - interface: src.modules.content_processor.interface.ContentProcessorInterface
    implementation: src.modules.content_processor.implementation.ContentProcessor
    scope: singleton
    kwargs:
      max_file_size: 104857600  # 100MB
      
  - interface: src.modules.search_engine.interface.SearchEngineInterface
    implementation: src.modules.search_engine.implementation.SearchEngine
    scope: singleton
    
  - interface: src.services.content_service.ContentService
    implementation: src.services.content_service.ContentService
    scope: singleton
    
dependencies:
  - name: database
    factory: src.database.connection.create_database_manager
    scope: singleton
    
  - name: cache
    factory: src.cache.redis_client.create_redis_client
    scope: singleton
```

## Advanced Patterns

### 1. Factory Pattern with DI
```python
# src/core/di/factories.py
from typing import Protocol, Type
from src.core.di.container import container

class ProcessorFactory(Protocol):
    """Factory for creating processors based on file type"""
    
    async def create_processor(self, file_type: str) -> ContentProcessorInterface:
        ...

class DefaultProcessorFactory:
    """Default implementation of processor factory"""
    
    def __init__(self):
        self.processors = {
            "pdf": PDFProcessor,
            "docx": DocxProcessor,
            "txt": TextProcessor,
        }
    
    async def create_processor(self, file_type: str) -> ContentProcessorInterface:
        processor_class = self.processors.get(file_type, GenericProcessor)
        return await container.resolve(processor_class)

# Register factory
container.register(ProcessorFactory, DefaultProcessorFactory)
```

### 2. Decorator-Based Injection
```python
# src/core/di/decorators.py
from functools import wraps
from typing import Type, List
from src.core.di.container import container

def inject(*dependencies: Type):
    """Decorator for automatic dependency injection"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Resolve dependencies
            resolved_deps = []
            for dep_type in dependencies:
                dep = await container.resolve(dep_type)
                resolved_deps.append(dep)
            
            # Call function with injected dependencies
            return await func(self, *resolved_deps, *args, **kwargs)
        return wrapper
    return decorator

# Usage
class MyService:
    @inject(DatabaseManager, CacheClient)
    async def process(self, db: DatabaseManager, cache: CacheClient, data: dict):
        # Use injected dependencies
        await db.save(data)
        await cache.set(data["id"], data)
```

### 3. Context-Based Resolution
```python
# src/core/di/context.py
from contextvars import ContextVar
from typing import Optional

# Context variables for request-scoped data
request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context", 
    default=None
)

class ContextualContainer(DependencyContainer):
    """Container with context-aware resolution"""
    
    async def resolve_with_context(self, interface: Type[T]) -> T:
        """Resolve with current context"""
        ctx = request_context.get()
        if ctx is None:
            raise RuntimeError("No request context available")
        
        return await self.resolve(interface, scope_id=ctx.request_id)
```

## Best Practices

### 1. Interface Segregation
```python
# Good: Focused interfaces
class DocumentReader(Protocol):
    async def read(self, path: str) -> str: ...

class DocumentWriter(Protocol):
    async def write(self, path: str, content: str) -> None: ...

# Bad: Large interface
class DocumentService(Protocol):
    async def read(self, path: str) -> str: ...
    async def write(self, path: str, content: str) -> None: ...
    async def delete(self, path: str) -> None: ...
    async def search(self, query: str) -> List[str]: ...
    # Too many responsibilities
```

### 2. Explicit Dependencies
```python
# Good: Dependencies are explicit
class SearchService:
    def __init__(
        self,
        search_engine: SearchEngineInterface,
        cache: CacheInterface,
        logger: Logger
    ):
        self.search_engine = search_engine
        self.cache = cache
        self.logger = logger

# Bad: Hidden dependencies
class SearchService:
    def __init__(self):
        self.search_engine = SearchEngine()  # Direct instantiation
        self.cache = get_global_cache()      # Global access
```

### 3. Lifetime Management
```python
# Good: Clear lifecycle
class ServiceWithLifecycle:
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    async def initialize(self):
        # Setup resources
        pass
    
    async def cleanup(self):
        # Release resources
        pass
```

## Testing Strategies

### 1. Test Container
```python
# tests/conftest.py
@pytest.fixture
async def test_container():
    """Create test container with mocks"""
    container = DependencyContainer()
    
    # Register mocks
    container.register_singleton(
        DatabaseManager,
        AsyncMock(spec=DatabaseManager)
    )
    container.register_singleton(
        CacheClient,
        AsyncMock(spec=CacheClient)
    )
    
    yield container
    
    await container.dispose()
```

### 2. Integration Testing
```python
# tests/integration/test_services.py
async def test_service_integration(test_container):
    """Test service with real dependencies"""
    # Register real implementations for integration test
    test_container.register(
        ContentProcessorInterface,
        implementation=ContentProcessor
    )
    
    service = await test_container.resolve(ContentService)
    result = await service.process_document("/test/doc.pdf")
    
    assert result is not None
```

## Migration Guide

### From Direct Instantiation to DI
```python
# Before: Direct instantiation
class OldService:
    def __init__(self):
        self.processor = ContentProcessor()
        self.db = DatabaseConnection()

# After: Dependency injection
class NewService:
    def __init__(
        self,
        processor: ContentProcessorInterface,
        db: DatabaseManager
    ):
        self.processor = processor
        self.db = db
```

### Gradual Migration Steps
1. Define interfaces for existing modules
2. Create DI container and registrations
3. Update services to accept dependencies
4. Replace direct instantiation with DI
5. Add tests with mocked dependencies
6. Remove old initialization code

## Common Pitfalls

1. **Circular Dependencies**: Design interfaces to avoid circular references
2. **Over-Injection**: Don't inject everything; some things can be created directly
3. **Service Locator Anti-Pattern**: Avoid passing the container itself
4. **Lifetime Mismatches**: Be careful mixing singleton and transient scopes
5. **Missing Registrations**: Ensure all dependencies are registered before use