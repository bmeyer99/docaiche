"""
Document Ingestion Pipeline - FINAL PRODUCTION APPROVAL VALIDATION
Critical validation test suite for production deployment decision

Tests all production-critical requirements:
1. Critical blocker resolution verification
2. Core workflow functionality 
3. Security measures validation
4. API endpoint functionality
5. Integration with PRD-008 Content Processing Pipeline
6. Production readiness assessment

VALIDATION CRITERIA: ALL tests must pass for production approval
"""

import pytest
import asyncio
import os
import tempfile
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

# Test imports
from src.database.connection import DatabaseManager, create_database_manager
from src.ingestion.pipeline import IngestionPipeline, create_ingestion_pipeline
from src.ingestion.models import DocumentUploadRequest, IngestionStatus
from src.api.v1.ingestion import get_ingestion_pipeline, health_check
from src.main import create_application


class TestCriticalBlockerResolution:
    """CRITICAL: Verify all 3 major production blockers are resolved"""
    
    @pytest.mark.asyncio
    async def test_container_friendly_configuration_paths(self):
        """BLOCKER 1: Verify container-friendly database paths work"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test absolute path works in container-like environment
            db_path = os.path.join(temp_dir, "data", "test.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            db_manager = await create_database_manager({"db_path": db_path})
            await db_manager.connect()
            
            # Verify connection works
            result = await db_manager.fetch_one("SELECT 1 as test")
            assert result.test == 1
            
            await db_manager.disconnect()
    
    @pytest.mark.asyncio 
    async def test_api_route_registration_fixed(self):
        """BLOCKER 2: Verify API routes are properly registered"""
        from src.api.v1.api import api_router
        
        # Check ingestion router is included
        route_paths = []
        for route in api_router.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)
            elif hasattr(route, 'prefix'):
                route_paths.append(route.prefix)
        
        # Verify key ingestion endpoints are registered
        ingestion_routes_found = any('/ingestion' in path for path in route_paths)
        assert ingestion_routes_found, f"Ingestion routes not found in: {route_paths}"
    
    @pytest.mark.asyncio
    async def test_content_processing_integration_working(self):
        """BLOCKER 3: Verify content processing pipeline integration works"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/test.db"})
                
                # Mock realistic content processing with proper lengths
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "realistic_doc_123"
                mock_processed_doc.content_hash = "hash_12345"
                mock_processed_doc.word_count = 1500  # Realistic length
                mock_processed_doc.chunks = ["chunk1", "chunk2", "chunk3", "chunk4"]
                mock_processed_doc.quality_score = 0.85
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Realistic document content for testing", {"pages": 3})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test with realistic document
                    file_data = b"Realistic document content that would be found in production use"
                    upload_request = DocumentUploadRequest(
                        filename="production_test.txt",
                        content_type="text/plain",
                        technology="python",
                        title="Production Test Document"
                    )
                    
                    result = await pipeline.ingest_single_document(file_data, upload_request)
                    
                    # Verify integration works with realistic data
                    assert result.status == IngestionStatus.COMPLETED
                    assert result.word_count == 1500
                    assert result.chunk_count == 4
                    assert result.quality_score == 0.85


class TestCoreWorkflowFunctionality:
    """Validate core document ingestion workflow functionality"""
    
    @pytest.mark.asyncio
    async def test_complete_upload_to_storage_workflow(self):
        """Test end-to-end document upload → processing → storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/workflow.db"})
                
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "workflow_doc"
                mock_processed_doc.content_hash = "workflow_hash"
                mock_processed_doc.word_count = 250
                mock_processed_doc.chunks = ["chunk1", "chunk2"]
                mock_processed_doc.quality_score = 0.9
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Workflow test content", {"format": "text"})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test multiple formats
                    test_files = [
                        (b"Plain text content", "test.txt", "text/plain"),
                        (b"# Markdown Content", "test.md", "text/markdown"),
                        (b"<html><body>HTML content</body></html>", "test.html", "text/html")
                    ]
                    
                    for file_data, filename, content_type in test_files:
                        upload_request = DocumentUploadRequest(
                            filename=filename,
                            content_type=content_type,
                            technology="test"
                        )
                        
                        result = await pipeline.ingest_single_document(file_data, upload_request)
                        assert result.status == IngestionStatus.COMPLETED
                        assert result.filename == filename
    
    @pytest.mark.asyncio
    async def test_batch_processing_functionality(self):
        """Test batch document processing works correctly"""
        from src.ingestion.models import BatchUploadRequest
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/batch.db"})
                
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "batch_doc"
                mock_processed_doc.content_hash = "batch_hash"
                mock_processed_doc.word_count = 100
                mock_processed_doc.chunks = ["chunk"]
                mock_processed_doc.quality_score = 0.8
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Batch content", {})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Create batch of documents
                    files_data = []
                    for i in range(3):
                        upload_request = DocumentUploadRequest(
                            filename=f"batch_{i}.txt",
                            content_type="text/plain",
                            technology="test"
                        )
                        files_data.append((b"batch content", upload_request))
                    
                    batch_request = BatchUploadRequest(
                        documents=[req for _, req in files_data],
                        technology="test",
                        batch_name="test_batch"
                    )
                    
                    result = await pipeline.ingest_batch_documents(files_data, batch_request)
                    
                    assert result.total_documents == 3
                    assert result.successful_count == 3
                    assert result.failed_count == 0


class TestSecurityMeasuresValidation:
    """Validate security measures are working correctly"""
    
    @pytest.mark.asyncio
    async def test_file_size_security_limits(self):
        """Test file size limits prevent oversized uploads"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/security.db"})
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test oversized file (51MB > 50MB limit)
                    oversized_data = b"x" * (51 * 1024 * 1024)
                    
                    upload_request = DocumentUploadRequest(
                        filename="oversized.txt",
                        content_type="text/plain",
                        technology="test"
                    )
                    
                    result = await pipeline.ingest_single_document(oversized_data, upload_request)
                    assert result.status == IngestionStatus.REJECTED
                    assert "exceeds limit" in result.error_message
    
    @pytest.mark.asyncio
    async def test_malicious_file_format_rejection(self):
        """Test malicious file formats are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/security.db"})
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test dangerous file extensions
                    malicious_files = [
                        ("malware.exe", "application/exe"),
                        ("script.js", "application/javascript"),
                        ("virus.bat", "application/batch")
                    ]
                    
                    for filename, content_type in malicious_files:
                        upload_request = DocumentUploadRequest(
                            filename=filename,
                            content_type=content_type,
                            technology="test"
                        )
                        
                        result = await pipeline.ingest_single_document(b"malicious content", upload_request)
                        assert result.status == IngestionStatus.REJECTED
                        assert "Unsupported file format" in result.error_message
    
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self):
        """Test path traversal attacks are prevented"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/security.db"})
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test path traversal attempts
                    malicious_paths = [
                        "../../../etc/passwd",
                        "..\\windows\\system32\\config\\sam",
                        "/etc/hosts"
                    ]
                    
                    for malicious_path in malicious_paths:
                        with pytest.raises(ValueError, match="path components not allowed"):
                            DocumentUploadRequest(
                                filename=malicious_path,
                                content_type="text/plain", 
                                technology="test"
                            )


class TestAPIEndpointFunctionality:
    """Validate API endpoints functionality"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_functional(self):
        """Test health endpoint returns correct status"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/health.db"})
                await mock_processor.db_manager.connect()
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await get_ingestion_pipeline()
                    health_result = await health_check(pipeline)
                    
                    assert health_result.status in ["healthy", "degraded"]
                    assert len(health_result.supported_formats) > 0
                    assert health_result.max_file_size_mb == 50
                    assert health_result.max_batch_size == 100
                    assert health_result.database_status in ["healthy", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_dependency_injection(self):
        """Test dependency injection works for pipeline"""
        with patch('src.ingestion.pipeline.create_ingestion_pipeline') as mock_create:
            mock_pipeline = AsyncMock()
            mock_create.return_value = mock_pipeline
            
            pipeline = await get_ingestion_pipeline()
            assert pipeline is not None
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fastapi_application_includes_routes(self):
        """Test FastAPI application includes ingestion routes"""
        app = create_application()
        
        # Check routes are included
        route_paths = []
        for route in app.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)
            elif hasattr(route, 'prefix'):
                route_paths.append(route.prefix)
        
        # Should have API v1 prefix
        has_api_v1 = any('/api/v1' in str(path) for path in route_paths)
        assert has_api_v1, f"API v1 routes not found in: {route_paths}"


class TestPRD008Integration:
    """Validate integration with Content Processing Pipeline (PRD-008)"""
    
    @pytest.mark.asyncio
    async def test_content_processor_receives_correct_data(self):
        """Test PRD-008 integration receives properly formatted data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/prd008.db"})
                
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "prd008_test"
                mock_processed_doc.content_hash = "prd008_hash"
                mock_processed_doc.word_count = 500
                mock_processed_doc.chunks = ["chunk1", "chunk2"]
                mock_processed_doc.quality_score = 0.95
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Extracted content for PRD-008", {"format": "text"})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    upload_request = DocumentUploadRequest(
                        filename="prd008_test.txt",
                        content_type="text/plain",
                        technology="python",
                        title="PRD-008 Integration Test",
                        source_url="test://prd008-integration"
                    )
                    
                    result = await pipeline.ingest_single_document(b"test content", upload_request)
                    
                    # Verify PRD-008 was called with correct parameters
                    mock_processor.process_and_store_document.assert_called_once()
                    call_args = mock_processor.process_and_store_document.call_args
                    file_content = call_args[0][0]
                    technology = call_args[0][1]
                    
                    # Verify FileContent object structure
                    assert file_content.content == "Extracted content for PRD-008"
                    assert file_content.title == "PRD-008 Integration Test"
                    assert file_content.source_url == "test://prd008-integration"
                    assert technology == "python"
                    
                    # Verify result reflects PRD-008 processing
                    assert result.status == IngestionStatus.COMPLETED
                    assert result.document_id == "prd008_test"


class TestProductionReadinessChecks:
    """Final production readiness validation"""
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test system handles concurrent requests without issues"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/concurrent.db"})
                
                mock_processed_doc = MagicMock()
                mock_processed_doc.id = "concurrent_doc"
                mock_processed_doc.content_hash = "concurrent_hash"
                mock_processed_doc.word_count = 200
                mock_processed_doc.chunks = ["chunk"]
                mock_processed_doc.quality_score = 0.8
                
                mock_processor.process_and_store_document.return_value = (mock_processed_doc, "success")
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Concurrent content", {})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Create multiple concurrent requests
                    async def process_document(i):
                        upload_request = DocumentUploadRequest(
                            filename=f"concurrent_{i}.txt",
                            content_type="text/plain",
                            technology="test"
                        )
                        return await pipeline.ingest_single_document(b"content", upload_request)
                    
                    # Execute 10 concurrent requests
                    tasks = [process_document(i) for i in range(10)]
                    results = await asyncio.gather(*tasks)
                    
                    # All should succeed
                    for result in results:
                        assert result.status == IngestionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_error_handling_robustness(self):
        """Test system handles errors gracefully without crashing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/error.db"})
                
                # Mock various failure scenarios
                mock_processor.process_and_store_document.side_effect = [
                    (None, "processing_failed"),  # Processing failure
                    Exception("Database error"),   # Exception
                    (MagicMock(id="success", content_hash="hash", word_count=100, 
                              chunks=["chunk"], quality_score=0.8), "success")  # Success
                ]
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = ("Error test content", {})
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test different error scenarios
                    error_scenarios = [
                        ("processing_fail.txt", IngestionStatus.FAILED),
                        ("exception_fail.txt", IngestionStatus.FAILED), 
                        ("success.txt", IngestionStatus.COMPLETED)
                    ]
                    
                    for filename, expected_status in error_scenarios:
                        upload_request = DocumentUploadRequest(
                            filename=filename,
                            content_type="text/plain",
                            technology="test"
                        )
                        
                        result = await pipeline.ingest_single_document(b"content", upload_request)
                        assert result.status == expected_status
                        assert result.filename == filename
    
    @pytest.mark.asyncio
    async def test_metrics_collection_functionality(self):
        """Test processing metrics collection works"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = await create_database_manager({"db_path": f"{temp_dir}/metrics.db"})
                await mock_processor.db_manager.connect()
                
                # Setup mock database responses for metrics
                mock_processor.db_manager.fetch_one.side_effect = [
                    type('MockRow', (), {'__getitem__': lambda s, i: 10})(),  # total docs
                    type('MockRow', (), {'__getitem__': lambda s, i: 2})(),   # failed docs
                ]
                mock_processor.db_manager.fetch_all.return_value = [
                    ('pdf', 5), ('txt', 3), ('html', 2)  # format distribution
                ]
                
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor_factory.return_value = mock_extractor
                    
                    pipeline = await create_ingestion_pipeline()
                    
                    # Test metrics collection
                    metrics = await pipeline.get_processing_metrics()
                    
                    assert metrics is not None
                    assert hasattr(metrics, 'total_documents_processed')
                    assert hasattr(metrics, 'success_rate')
                    assert hasattr(metrics, 'documents_by_format')


# Integration test to verify all components work together
@pytest.mark.integration
class TestCompleteProductionWorkflow:
    """Complete end-to-end production workflow validation"""
    
    @pytest.mark.asyncio
    async def test_full_production_simulation(self):
        """Simulate complete production workflow with realistic data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic database setup
            db_manager = await create_database_manager({"db_path": f"{temp_dir}/production.db"})
            await db_manager.connect()
            
            # Create necessary tables for production simulation
            await db_manager.execute("""
                CREATE TABLE IF NOT EXISTS content_metadata (
                    content_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_url TEXT,
                    technology TEXT,
                    processing_status TEXT DEFAULT 'pending',
                    content_hash TEXT,
                    word_count INTEGER,
                    chunk_count INTEGER,
                    quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            
            with patch('src.processors.factory.create_content_processor') as mock_factory:
                mock_processor = AsyncMock()
                mock_processor.db_manager = db_manager
                
                # Simulate realistic processing
                async def realistic_process_and_store(file_content, technology):
                    doc_id = f"prod_{hash(file_content.content) % 10000}"
                    
                    # Simulate database storage
                    await db_manager.execute("""
                        INSERT INTO content_metadata 
                        (content_id, title, source_url, technology, processing_status, 
                         content_hash, word_count, chunk_count, quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        doc_id, file_content.title, file_content.source_url, technology,
                        "completed", f"hash_{doc_id}", len(file_content.content.split()),
                        3, 0.85
                    ))
                    
                    mock_doc = MagicMock()
                    mock_doc.id = doc_id
                    mock_doc.content_hash = f"hash_{doc_id}"
                    mock_doc.word_count = len(file_content.content.split())
                    mock_doc.chunks = ["chunk1", "chunk2", "chunk3"]
                    mock_doc.quality_score = 0.85
                    
                    return mock_doc, "success"
                
                mock_processor.process_and_store_document.side_effect = realistic_process_and_store
                mock_factory.return_value = mock_processor
                
                with patch('src.ingestion.extractors.create_document_extractor') as mock_extractor_factory:
                    mock_extractor = AsyncMock()
                    mock_extractor.extract_content.return_value = (
                        "This is realistic production document content with sufficient text to simulate real world usage patterns.",
                        {"format": "text", "pages": 1}
                    )
                    mock_extractor_factory.return_value = mock_extractor
                    
                    # Test complete production workflow
                    pipeline = await create_ingestion_pipeline(db_manager=db_manager)
                    
                    # Simulate realistic production documents
                    production_docs = [
                        ("python_guide.txt", "text/plain", "python", "Python Development Guide"),
                        ("api_spec.md", "text/markdown", "javascript", "API Specification"),
                        ("readme.html", "text/html", "general", "Project README")
                    ]
                    
                    successful_uploads = 0
                    for filename, content_type, technology, title in production_docs:
                        upload_request = DocumentUploadRequest(
                            filename=filename,
                            content_type=content_type,
                            technology=technology,
                            title=title,
                            source_url=f"production://docs/{filename}"
                        )
                        
                        result = await pipeline.ingest_single_document(
                            f"Production content for {title}".encode(), 
                            upload_request
                        )
                        
                        if result.status == IngestionStatus.COMPLETED:
                            successful_uploads += 1
                        
                        # Verify document was stored
                        stored_doc = await db_manager.fetch_one(
                            "SELECT * FROM content_metadata WHERE content_id = ?",
                            (result.document_id,)
                        )
                        assert stored_doc is not None
                        assert stored_doc.technology == technology
                        assert stored_doc.processing_status == "completed"
                    
                    # Verify all documents processed successfully
                    assert successful_uploads == len(production_docs)
                    
                    # Test metrics collection on real data
                    metrics = await pipeline.get_processing_metrics()
                    assert metrics.total_documents_processed >= len(production_docs)
            
            await db_manager.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])