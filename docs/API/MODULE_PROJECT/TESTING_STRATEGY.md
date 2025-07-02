# Testing Strategy for Modular API Architecture

## Overview
This document outlines the comprehensive testing strategy for the DocAIche modular API architecture. The strategy covers unit testing, integration testing, contract testing, and performance testing with a focus on the new modular structure.

## Testing Principles

1. **Test Pyramid**: Follow the test pyramid with many unit tests, fewer integration tests, and minimal E2E tests
2. **Fast Feedback**: Tests should run quickly to provide rapid feedback
3. **Isolation**: Tests should be independent and not affect each other
4. **Clarity**: Test names should clearly describe what they test
5. **Maintainability**: Tests should be easy to understand and modify

## Test Structure

```
tests/
├── unit/                      # Unit tests for individual components
│   ├── modules/              # Module implementation tests
│   ├── services/             # Service layer tests
│   └── api/                  # API endpoint tests
├── integration/              # Integration tests
│   ├── modules/              # Module integration tests
│   ├── services/             # Service integration tests
│   └── api/                  # API integration tests
├── contract/                 # Contract tests for interfaces
├── performance/              # Performance and load tests
├── fixtures/                 # Shared test fixtures
├── mocks/                    # Mock implementations
└── conftest.py              # Pytest configuration
```

## Unit Testing

### 1. Module Unit Tests
```python
# tests/unit/modules/test_content_processor.py
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path
from src.modules.content_processor.implementation import ContentProcessor
from src.modules.content_processor.interface import (
    ProcessedDocument,
    DocumentMetadata,
    UnsupportedFormatError
)

class TestContentProcessor:
    """Unit tests for ContentProcessor module"""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance with mocked dependencies"""
        return ContentProcessor(config={
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "supported_formats": ["pdf", "docx", "txt"]
        })
    
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create sample PDF file"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"PDF content")
        return pdf_file
    
    async def test_process_document_success(self, processor, sample_pdf):
        """Test successful document processing"""
        # Mock the internal methods
        with patch.object(processor, '_extract_pdf_text', return_value="Extracted text"):
            with patch.object(processor, '_generate_chunks', return_value=[]):
                result = await processor.process_document(sample_pdf)
                
                assert isinstance(result, ProcessedDocument)
                assert result.content == "Extracted text"
                assert result.file_path == str(sample_pdf)
    
    async def test_process_unsupported_format(self, processor, tmp_path):
        """Test handling of unsupported file format"""
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("content")
        
        with pytest.raises(UnsupportedFormatError):
            await processor.process_document(bad_file)
    
    async def test_extract_metadata(self, processor, sample_pdf):
        """Test metadata extraction"""
        with patch('PyPDF2.PdfReader') as mock_reader:
            mock_reader.return_value.metadata = {
                '/Title': 'Test Document',
                '/Author': 'Test Author'
            }
            
            metadata = await processor.extract_metadata(sample_pdf)
            
            assert metadata.title == 'Test Document'
            assert metadata.author == 'Test Author'
    
    @pytest.mark.parametrize("chunk_size,overlap,expected_chunks", [
        (100, 20, 12),  # Small chunks
        (500, 50, 3),   # Medium chunks
        (1000, 0, 2),   # Large chunks, no overlap
    ])
    async def test_chunk_document(self, processor, chunk_size, overlap, expected_chunks):
        """Test document chunking with different parameters"""
        text = "Lorem ipsum " * 100  # ~1200 characters
        
        chunks = await processor.chunk_document(text, chunk_size, overlap)
        
        assert len(chunks) == expected_chunks
        assert all(len(chunk.text) <= chunk_size for chunk in chunks)
```

### 2. Service Unit Tests
```python
# tests/unit/services/test_content_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.services.content_service import ContentService
from src.modules.content_processor.interface import ProcessedDocument

class TestContentService:
    """Unit tests for ContentService"""
    
    @pytest.fixture
    def mock_processor(self):
        """Mock content processor"""
        processor = AsyncMock()
        processor.process_document.return_value = ProcessedDocument(
            id="doc-123",
            file_path="/test/doc.pdf",
            content="Test content",
            metadata=Mock(),
            chunks=[]
        )
        return processor
    
    @pytest.fixture
    def mock_database(self):
        """Mock database manager"""
        db = AsyncMock()
        db.transaction.return_value.__aenter__ = AsyncMock()
        db.transaction.return_value.__aexit__ = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_cache(self):
        """Mock cache client"""
        cache = AsyncMock()
        cache.get.return_value = None  # Cache miss
        return cache
    
    @pytest.fixture
    async def service(self, mock_processor, mock_database, mock_cache):
        """Create service with mocked dependencies"""
        service = ContentService(
            content_processor=mock_processor,
            database=mock_database,
            cache=mock_cache,
            config={"cache_ttl": 3600}
        )
        await service.initialize()
        yield service
        await service.shutdown()
    
    async def test_process_document_cache_miss(
        self, service, mock_processor, mock_cache, mock_database
    ):
        """Test document processing with cache miss"""
        result = await service.process_document(
            "/test/doc.pdf",
            "workspace-123"
        )
        
        # Verify processor was called
        mock_processor.process_document.assert_called_once_with(
            "/test/doc.pdf", None
        )
        
        # Verify cache was checked and updated
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()
        
        # Verify database was updated
        assert mock_database.transaction.called
    
    async def test_process_document_cache_hit(
        self, service, mock_processor, mock_cache
    ):
        """Test document processing with cache hit"""
        # Setup cache hit
        cached_data = {"id": "cached-123", "content": "Cached content"}
        mock_cache.get.return_value = cached_data
        
        result = await service.process_document(
            "/test/doc.pdf",
            "workspace-123"
        )
        
        # Verify processor was NOT called
        mock_processor.process_document.assert_not_called()
        
        # Verify result is from cache
        assert result == cached_data
    
    async def test_process_document_error_handling(
        self, service, mock_processor
    ):
        """Test error handling in document processing"""
        mock_processor.process_document.side_effect = Exception("Processing failed")
        
        with pytest.raises(Exception) as exc_info:
            await service.process_document("/test/doc.pdf", "workspace-123")
        
        assert str(exc_info.value) == "Processing failed"
```

### 3. API Unit Tests
```python
# tests/unit/api/test_document_endpoints.py
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from src.api.v1.endpoints.documents import router
from src.services.content_service import ContentService

@pytest.fixture
def mock_content_service():
    """Mock content service"""
    service = AsyncMock(spec=ContentService)
    service.process_document.return_value = {
        "id": "doc-123",
        "status": "processed"
    }
    return service

@pytest.fixture
def client(mock_content_service):
    """Create test client with mocked dependencies"""
    from fastapi import FastAPI
    app = FastAPI()
    
    # Override dependency
    app.dependency_overrides[ContentService] = lambda: mock_content_service
    
    app.include_router(router)
    return TestClient(app)

def test_upload_document(client, mock_content_service):
    """Test document upload endpoint"""
    response = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        data={"workspace_id": "workspace-123"}
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == "doc-123"
    
    # Verify service was called
    mock_content_service.process_document.assert_called_once()

def test_upload_invalid_file(client):
    """Test upload with invalid file"""
    response = client.post(
        "/documents/upload",
        files={"file": ("test.exe", b"EXE content", "application/exe")},
        data={"workspace_id": "workspace-123"}
    )
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
```

## Integration Testing

### 1. Module Integration Tests
```python
# tests/integration/modules/test_content_processor_integration.py
import pytest
from pathlib import Path
from src.modules.content_processor.implementation import ContentProcessor
from src.database.connection import create_test_database

class TestContentProcessorIntegration:
    """Integration tests for ContentProcessor with real dependencies"""
    
    @pytest.fixture
    async def processor(self):
        """Create processor with real dependencies"""
        processor = ContentProcessor(config={
            "max_file_size": 10 * 1024 * 1024,
            "supported_formats": ["pdf", "docx", "txt"]
        })
        yield processor
    
    @pytest.fixture
    def sample_pdf(self):
        """Use real sample PDF from fixtures"""
        return Path("tests/fixtures/sample.pdf")
    
    async def test_process_real_pdf(self, processor, sample_pdf):
        """Test processing a real PDF file"""
        result = await processor.process_document(sample_pdf)
        
        assert result.content != ""
        assert len(result.chunks) > 0
        assert result.metadata.page_count > 0
        assert result.processing_time > 0
    
    @pytest.mark.slow
    async def test_process_large_document(self, processor):
        """Test processing large document"""
        large_doc = Path("tests/fixtures/large_document.pdf")
        
        result = await processor.process_document(large_doc)
        
        assert len(result.chunks) > 100
        assert result.processing_time < 30  # Should complete within 30 seconds
```

### 2. Service Integration Tests
```python
# tests/integration/services/test_content_service_integration.py
import pytest
from src.services.content_service import ContentService
from src.modules.content_processor.implementation import ContentProcessor
from src.database.connection import create_test_database
from src.cache.redis_client import create_test_redis_client

class TestContentServiceIntegration:
    """Integration tests for ContentService with real components"""
    
    @pytest.fixture
    async def database(self):
        """Create test database"""
        db = await create_test_database()
        yield db
        await db.cleanup()
    
    @pytest.fixture
    async def cache(self):
        """Create test Redis client"""
        cache = await create_test_redis_client()
        yield cache
        await cache.flushdb()
        await cache.close()
    
    @pytest.fixture
    async def service(self, database, cache):
        """Create service with real dependencies"""
        processor = ContentProcessor(config={})
        service = ContentService(
            content_processor=processor,
            database=database,
            cache=cache,
            config={"cache_ttl": 60}
        )
        await service.initialize()
        yield service
        await service.shutdown()
    
    async def test_end_to_end_document_processing(self, service, tmp_path):
        """Test complete document processing flow"""
        # Create test document
        test_doc = tmp_path / "test.txt"
        test_doc.write_text("This is a test document for integration testing.")
        
        # Process document
        result = await service.process_document(
            str(test_doc),
            "test-workspace"
        )
        
        assert result["id"] is not None
        assert result["content"] == "This is a test document for integration testing."
        
        # Verify it's in cache
        result2 = await service.process_document(
            str(test_doc),
            "test-workspace"
        )
        assert result2 == result  # Should be same (from cache)
```

## Contract Testing

### 1. Interface Contract Tests
```python
# tests/contract/test_module_contracts.py
import pytest
from typing import Type
from src.modules.content_processor.interface import ContentProcessorInterface
from src.modules.search_engine.interface import SearchEngineInterface

def verify_interface_contract(
    interface: Type,
    implementation: Type,
    required_methods: list
):
    """Verify that implementation satisfies interface contract"""
    for method_name in required_methods:
        assert hasattr(implementation, method_name), \
            f"{implementation.__name__} missing required method: {method_name}"
        
        # Verify method signatures match
        interface_method = getattr(interface, method_name)
        impl_method = getattr(implementation, method_name)
        
        assert interface_method.__annotations__ == impl_method.__annotations__, \
            f"Method signature mismatch for {method_name}"

class TestModuleContracts:
    """Test that all modules implement their interfaces correctly"""
    
    def test_content_processor_contract(self):
        """Test ContentProcessor implements interface"""
        from src.modules.content_processor.implementation import ContentProcessor
        
        verify_interface_contract(
            ContentProcessorInterface,
            ContentProcessor,
            [
                "process_document",
                "extract_text",
                "extract_metadata",
                "generate_embeddings",
                "chunk_document"
            ]
        )
    
    def test_search_engine_contract(self):
        """Test SearchEngine implements interface"""
        from src.modules.search_engine.implementation import SearchEngine
        
        verify_interface_contract(
            SearchEngineInterface,
            SearchEngine,
            [
                "search",
                "vector_search",
                "hybrid_search",
                "get_suggestions",
                "analyze_query"
            ]
        )
```

### 2. API Contract Tests
```python
# tests/contract/test_api_contracts.py
import pytest
import json
from jsonschema import validate
from pathlib import Path

class TestAPIContracts:
    """Test API responses match documented schemas"""
    
    @pytest.fixture
    def schemas(self):
        """Load API schemas"""
        schema_dir = Path("docs/api/schemas")
        schemas = {}
        for schema_file in schema_dir.glob("*.json"):
            schemas[schema_file.stem] = json.loads(schema_file.read_text())
        return schemas
    
    def test_document_upload_response_schema(self, client, schemas):
        """Test document upload response matches schema"""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", b"content", "text/plain")},
            data={"workspace_id": "test"}
        )
        
        validate(response.json(), schemas["document_upload_response"])
    
    def test_search_response_schema(self, client, schemas):
        """Test search response matches schema"""
        response = client.get(
            "/api/v1/search",
            params={"q": "test query", "limit": 10}
        )
        
        validate(response.json(), schemas["search_response"])
```

## Performance Testing

### 1. Load Testing
```python
# tests/performance/test_load.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import httpx

class TestLoadPerformance:
    """Load testing for API endpoints"""
    
    @pytest.mark.performance
    async def test_concurrent_document_processing(self, api_url):
        """Test handling concurrent document uploads"""
        async def upload_document(client: httpx.AsyncClient, index: int):
            start_time = time.time()
            
            response = await client.post(
                f"{api_url}/api/v1/documents/upload",
                files={"file": (f"test{index}.txt", b"test content", "text/plain")},
                data={"workspace_id": "perf-test"}
            )
            
            duration = time.time() - start_time
            return response.status_code, duration
        
        async with httpx.AsyncClient() as client:
            # Run 100 concurrent uploads
            tasks = [upload_document(client, i) for i in range(100)]
            results = await asyncio.gather(*tasks)
        
        # Analyze results
        success_count = sum(1 for status, _ in results if status == 200)
        avg_duration = sum(duration for _, duration in results) / len(results)
        
        assert success_count >= 95  # At least 95% success rate
        assert avg_duration < 2.0   # Average response time under 2 seconds
    
    @pytest.mark.performance
    def test_search_throughput(self, api_url):
        """Test search endpoint throughput"""
        queries = ["test", "document", "search", "api", "performance"]
        
        def search_request(query):
            response = httpx.get(
                f"{api_url}/api/v1/search",
                params={"q": query, "limit": 10}
            )
            return response.elapsed.total_seconds()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Execute 1000 search requests
            durations = list(executor.map(
                search_request,
                queries * 200
            ))
        
        # Calculate metrics
        p95_duration = sorted(durations)[int(len(durations) * 0.95)]
        avg_duration = sum(durations) / len(durations)
        
        assert p95_duration < 0.5  # 95th percentile under 500ms
        assert avg_duration < 0.2  # Average under 200ms
```

### 2. Memory Testing
```python
# tests/performance/test_memory.py
import pytest
import psutil
import os

class TestMemoryUsage:
    """Test memory usage patterns"""
    
    @pytest.mark.performance
    async def test_memory_leak_in_processing(self, service):
        """Test for memory leaks in document processing"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process many documents
        for i in range(100):
            await service.process_document(
                f"/tmp/test{i}.txt",
                "memory-test"
            )
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal
        assert memory_increase < 50  # Less than 50MB increase
```

## Test Fixtures and Utilities

### 1. Common Fixtures
```python
# tests/fixtures/common.py
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def sample_documents():
    """Provide sample documents for testing"""
    return {
        "pdf": Path("tests/fixtures/sample.pdf"),
        "docx": Path("tests/fixtures/sample.docx"),
        "txt": Path("tests/fixtures/sample.txt"),
        "large_pdf": Path("tests/fixtures/large.pdf")
    }

@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        (workspace / "documents").mkdir()
        (workspace / "processed").mkdir()
        yield workspace
```

### 2. Mock Factories
```python
# tests/mocks/factories.py
from unittest.mock import AsyncMock
from typing import Dict, Any

def create_mock_processor(**overrides):
    """Factory for creating mock processors"""
    mock = AsyncMock()
    mock.process_document.return_value = {
        "id": "mock-123",
        "content": "Mock content",
        **overrides
    }
    return mock

def create_mock_service(service_class, **config):
    """Factory for creating mock services"""
    mock = AsyncMock(spec=service_class)
    for key, value in config.items():
        setattr(mock, key, value)
    return mock
```

## Testing Best Practices

### 1. Test Naming Convention
```python
# Good test names
def test_process_document_with_valid_pdf_returns_processed_document():
    pass

def test_search_with_empty_query_returns_validation_error():
    pass

# Bad test names
def test_process():  # Too vague
    pass

def test_1():  # Meaningless
    pass
```

### 2. Test Organization
```python
class TestContentProcessor:
    """Group related tests in classes"""
    
    class TestProcessDocument:
        """Further group by method/functionality"""
        
        def test_valid_document(self):
            pass
        
        def test_invalid_format(self):
            pass
        
        def test_oversized_file(self):
            pass
```

### 3. Async Test Patterns
```python
# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None

# Test async context managers
async def test_service_lifecycle():
    async with ContentService(...) as service:
        result = await service.process()
        assert result is not None
```

## Continuous Testing

### 1. Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: pytest tests/unit -v
        language: system
        pass_filenames: false
        always_run: true
```

### 2. CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: |
          pytest tests/unit --cov=src --cov-report=xml
      
  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
      postgres:
        image: postgres:15
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: |
          pytest tests/integration -v
  
  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run performance tests
        run: |
          pytest tests/performance -m performance
```

## Test Coverage Goals

### Coverage Targets
- **Unit Tests**: 80% coverage minimum
- **Integration Tests**: Cover all critical paths
- **API Tests**: 100% endpoint coverage
- **Contract Tests**: All interfaces verified

### Coverage Configuration
```ini
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra 
    -q 
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing:skip-covered
    --cov-fail-under=80
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## Test Maintenance

### 1. Regular Test Review
- Review and update tests when interfaces change
- Remove obsolete tests
- Refactor duplicate test code
- Update test data and fixtures

### 2. Test Documentation
```python
def test_complex_scenario():
    """
    Test document processing with special characters.
    
    This test verifies that the processor correctly handles:
    - Unicode characters in content
    - Special markup in metadata
    - Edge cases in chunking
    
    See: https://github.com/docaiche/issues/123
    """
    pass
```

### 3. Flaky Test Management
```python
# Mark flaky tests
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_external_service_integration():
    """Test that might fail due to external factors"""
    pass

# Skip tests conditionally
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_TESTS"),
    reason="Slow tests disabled"
)
def test_large_file_processing():
    pass
```