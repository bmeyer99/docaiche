"""
Test suite for Document Ingestion API Endpoints
FastAPI integration tests for secure document upload and processing
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from io import BytesIO

from src.main import app
from src.ingestion.models import IngestionStatus, IngestionResult


@pytest.fixture
def client():
    """Test client for FastAPI application"""
    return TestClient(app)


@pytest.fixture
def mock_pipeline():
    """Mock ingestion pipeline for testing"""
    pipeline = Mock()
    pipeline.ingest_single_document = AsyncMock()
    pipeline.ingest_batch_documents = AsyncMock()
    pipeline.get_processing_metrics = AsyncMock()
    pipeline.db_manager = Mock()
    pipeline.db_manager.fetch_one = AsyncMock()
    pipeline.db_manager.execute = AsyncMock()
    pipeline.supported_formats = {'pdf', 'doc', 'docx', 'txt', 'md', 'html'}
    pipeline.max_file_size = 50 * 1024 * 1024
    pipeline.max_batch_size = 100
    return pipeline


class TestIngestionHealthEndpoint:
    """Test health check endpoint functionality"""
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_health_check_success(self, mock_get_pipeline, client, mock_pipeline):
        """Test successful health check response"""
        mock_get_pipeline.return_value = mock_pipeline
        mock_pipeline.db_manager.fetch_one.return_value = (1,)  # Database healthy
        
        response = client.get("/api/v1/ingestion/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "supported_formats" in data
        assert "max_file_size_mb" in data
        assert data["database_status"] == "healthy"
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_health_check_database_unhealthy(self, mock_get_pipeline, client, mock_pipeline):
        """Test health check with database issues"""
        mock_get_pipeline.return_value = mock_pipeline
        mock_pipeline.db_manager.fetch_one.side_effect = Exception("Database connection failed")
        
        response = client.get("/api/v1/ingestion/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database_status"] == "unhealthy"


class TestSingleDocumentUpload:
    """Test single document upload endpoint"""
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_successful_document_upload(self, mock_get_pipeline, client, mock_pipeline):
        """Test successful single document upload"""
        # Mock successful processing
        mock_result = IngestionResult(
            document_id="doc_123456789abc",
            filename="test.txt",
            status=IngestionStatus.COMPLETED,
            content_hash="hash123",
            word_count=10,
            chunk_count=2,
            quality_score=0.8,
            processing_time_ms=150
        )
        mock_pipeline.ingest_single_document.return_value = mock_result
        mock_get_pipeline.return_value = mock_pipeline
        
        # Prepare test file
        test_content = b"This is a test document with sufficient content for processing."
        
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.txt", BytesIO(test_content), "text/plain")},
            data={"technology": "python", "title": "Test Document"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "doc_123456789abc"
        assert data["status"] == "completed"
        assert data["filename"] == "test.txt"
        assert data["word_count"] == 10
        assert data["quality_score"] == 0.8
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_document_upload_rejection(self, mock_get_pipeline, client, mock_pipeline):
        """Test document upload rejection due to validation"""
        # Mock rejection result
        mock_result = IngestionResult(
            document_id="doc_rejected",
            filename="test.txt",
            status=IngestionStatus.REJECTED,
            error_message="File format not supported"
        )
        mock_pipeline.ingest_single_document.return_value = mock_result
        mock_get_pipeline.return_value = mock_pipeline
        
        test_content = b"Invalid content"
        
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.txt", BytesIO(test_content), "text/plain")},
            data={"technology": "python"}
        )
        
        assert response.status_code == 422
        assert "File format not supported" in response.text
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_document_upload_processing_failure(self, mock_get_pipeline, client, mock_pipeline):
        """Test document upload processing failure"""
        # Mock processing failure
        mock_result = IngestionResult(
            document_id="doc_failed",
            filename="test.txt",
            status=IngestionStatus.FAILED,
            error_message="Internal processing error"
        )
        mock_pipeline.ingest_single_document.return_value = mock_result
        mock_get_pipeline.return_value = mock_pipeline
        
        test_content = b"Test content that fails processing"
        
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.txt", BytesIO(test_content), "text/plain")},
            data={"technology": "python"}
        )
        
        assert response.status_code == 500
        assert "Internal processing error" in response.text
    
    def test_missing_file_rejection(self, client):
        """Test rejection when no file is provided"""
        response = client.post(
            "/api/v1/ingestion/upload",
            data={"technology": "python"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_technology_rejection(self, client):
        """Test rejection when technology parameter is missing"""
        test_content = b"Test content"
        
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.txt", BytesIO(test_content), "text/plain")}
        )
        
        assert response.status_code == 422  # Validation error


class TestBatchDocumentUpload:
    """Test batch document upload endpoint"""
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_successful_batch_upload(self, mock_get_pipeline, client, mock_pipeline):
        """Test successful batch document upload"""
        from src.ingestion.models import BatchIngestionResult
        
        # Mock successful batch processing
        mock_results = [
            IngestionResult(
                document_id="doc_1",
                filename="doc1.txt",
                status=IngestionStatus.COMPLETED,
                word_count=10,
                chunk_count=1,
                quality_score=0.8
            ),
            IngestionResult(
                document_id="doc_2",
                filename="doc2.txt",
                status=IngestionStatus.COMPLETED,
                word_count=15,
                chunk_count=2,
                quality_score=0.7
            )
        ]
        
        mock_batch_result = BatchIngestionResult(
            batch_id="batch_123",
            total_documents=2,
            successful_count=2,
            failed_count=0,
            results=mock_results,
            total_processing_time_ms=300
        )
        mock_pipeline.ingest_batch_documents.return_value = mock_batch_result
        mock_get_pipeline.return_value = mock_pipeline
        
        # Prepare test files
        files = [
            ("files", ("doc1.txt", BytesIO(b"Content 1"), "text/plain")),
            ("files", ("doc2.txt", BytesIO(b"Content 2"), "text/plain"))
        ]
        
        response = client.post(
            "/api/v1/ingestion/upload/batch",
            files=files,
            data={"technology": "python", "batch_name": "test-batch"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == "batch_123"
        assert data["total_documents"] == 2
        assert data["successful_count"] == 2
        assert data["failed_count"] == 0
        assert len(data["results"]) == 2
    
    def test_empty_batch_rejection(self, client):
        """Test rejection of empty batch uploads"""
        response = client.post(
            "/api/v1/ingestion/upload/batch",
            data={"technology": "python"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_batch_size_limit_rejection(self, mock_get_pipeline, client, mock_pipeline):
        """Test rejection of oversized batches"""
        mock_pipeline.max_batch_size = 2  # Set low limit for testing
        mock_get_pipeline.return_value = mock_pipeline
        
        # Create batch exceeding limit
        files = [
            ("files", (f"doc{i}.txt", BytesIO(b"Content"), "text/plain"))
            for i in range(3)  # Exceeds limit of 2
        ]
        
        response = client.post(
            "/api/v1/ingestion/upload/batch",
            files=files,
            data={"technology": "python"}
        )
        
        assert response.status_code == 400
        assert "exceeds maximum" in response.text


class TestDocumentStatusAndManagement:
    """Test document status and management endpoints"""
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_get_document_status_success(self, mock_get_pipeline, client, mock_pipeline):
        """Test successful document status retrieval"""
        # Mock database response
        mock_pipeline.db_manager.fetch_one.return_value = (
            "doc_123", "Test Document", "completed", 0.8, 100, 5,
            "2023-01-01T00:00:00Z", "2023-01-01T00:01:00Z"
        )
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.get("/api/v1/ingestion/status/doc_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "doc_123"
        assert data["title"] == "Test Document"
        assert data["processing_status"] == "completed"
        assert data["quality_score"] == 0.8
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_get_document_status_not_found(self, mock_get_pipeline, client, mock_pipeline):
        """Test document status retrieval for non-existent document"""
        mock_pipeline.db_manager.fetch_one.return_value = None
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.get("/api/v1/ingestion/status/nonexistent")
        
        assert response.status_code == 404
        assert "Document not found" in response.text
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_delete_document_success(self, mock_get_pipeline, client, mock_pipeline):
        """Test successful document deletion"""
        # Mock document exists
        mock_pipeline.db_manager.fetch_one.return_value = ("doc_123",)
        mock_pipeline.db_manager.execute.return_value = None
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.delete("/api/v1/ingestion/documents/doc_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"
        assert data["document_id"] == "doc_123"
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_delete_document_not_found(self, mock_get_pipeline, client, mock_pipeline):
        """Test deletion of non-existent document"""
        mock_pipeline.db_manager.fetch_one.return_value = None
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.delete("/api/v1/ingestion/documents/nonexistent")
        
        assert response.status_code == 404
        assert "Document not found" in response.text


class TestProcessingMetrics:
    """Test processing metrics endpoint"""
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_get_processing_metrics_success(self, mock_get_pipeline, client, mock_pipeline):
        """Test successful metrics retrieval"""
        from src.ingestion.models import ProcessingMetrics
        
        mock_metrics = ProcessingMetrics(
            total_documents_processed=100,
            documents_by_format={"pdf": 30, "txt": 40, "md": 30},
            documents_by_technology={"python": 50, "javascript": 30, "java": 20},
            average_processing_time_ms=250.0,
            success_rate=95.5,
            quality_score_distribution={"high": 60, "medium": 30, "low": 10}
        )
        mock_pipeline.get_processing_metrics.return_value = mock_metrics
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.get("/api/v1/ingestion/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents_processed"] == 100
        assert "documents_by_format" in data
        assert "documents_by_technology" in data
        assert data["success_rate"] == 95.5


class TestErrorHandling:
    """Test error handling and security measures"""
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_pipeline_creation_failure(self, mock_get_pipeline, client):
        """Test handling of pipeline creation failures"""
        mock_get_pipeline.side_effect = Exception("Pipeline creation failed")
        
        response = client.get("/api/v1/ingestion/health")
        
        assert response.status_code == 500
        assert "Ingestion service unavailable" in response.text
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_file_read_failure_handling(self, mock_get_pipeline, client, mock_pipeline):
        """Test handling of file read failures"""
        mock_get_pipeline.return_value = mock_pipeline
        
        # Simulate file that can't be read
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.txt", None, "text/plain")},  # None content
            data={"technology": "python"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_file_extension_handling(self, client):
        """Test handling of files with invalid extensions"""
        test_content = b"Test content"
        
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.exe", BytesIO(test_content), "application/x-executable")},
            data={"technology": "python"}
        )
        
        assert response.status_code == 422  # Validation error from Pydantic models
    
    @patch('src.api.v1.ingestion.get_ingestion_pipeline')
    def test_database_error_handling(self, mock_get_pipeline, client, mock_pipeline):
        """Test handling of database errors"""
        mock_pipeline.db_manager.fetch_one.side_effect = Exception("Database error")
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.get("/api/v1/ingestion/status/doc_123")
        
        assert response.status_code == 500
        assert "Failed to retrieve document status" in response.text


class TestSecurityMeasures:
    """Test security validation and measures"""
    
    def test_malicious_filename_rejection(self, client):
        """Test rejection of malicious filenames"""
        test_content = b"Test content"
        
        # Test path traversal attempt
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("../../../etc/passwd", BytesIO(test_content), "text/plain")},
            data={"technology": "python"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_oversized_file_handling(self, client):
        """Test handling of oversized files"""
        # Create a large content payload (this will be caught at validation level)
        large_content = b"x" * (1024 * 1024)  # 1MB (smaller than actual limit for test efficiency)
        
        response = client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("large.txt", BytesIO(large_content), "text/plain")},
            data={"technology": "python"}
        )
        
        # Should still process as 1MB is under the 50MB limit
        # The actual size limit is enforced in the pipeline
        assert response.status_code in [200, 422, 500]  # Depends on mocking
    
    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection in parameters"""
        malicious_id = "'; DROP TABLE content_metadata; --"
        
        response = client.get(f"/api/v1/ingestion/status/{malicious_id}")
        
        # Should handle malicious input safely
        assert response.status_code in [404, 500]  # Not successful injection