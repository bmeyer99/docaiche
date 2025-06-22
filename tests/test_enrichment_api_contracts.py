"""
Test suite for Enrichment API Contract Standardization - PRD-010
Validates that all enrichment API contracts follow system-wide patterns.

Tests the standardized interfaces, error handling, HTTP status codes,
and integration with other system components.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, status

from src.api.v1.enrichment import (
    enrichment_router,
    map_enrichment_exception_to_http_status,
    handle_enrichment_error
)
from src.enrichment.exceptions import (
    EnrichmentError, TaskProcessingError, EnrichmentTimeoutError,
    AnalysisError, InvalidTaskError
)
from src.enrichment.models import (
    EnrichmentType, EnrichmentPriority, EnrichmentResult,
    EnrichmentMetrics, ContentGap
)


@pytest.fixture
def app():
    """Create FastAPI app with enrichment router for testing."""
    app = FastAPI()
    app.include_router(enrichment_router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_enricher():
    """Create mock knowledge enricher."""
    enricher = AsyncMock()
    
    # Mock successful responses
    enricher.enrich_content.return_value = ["task_123", "task_124"]
    enricher.trigger_bulk_enrichment.return_value = {
        "total_submitted": 2,
        "successful_submissions": 2,
        "failed_submissions": 0,
        "task_ids": ["task_125", "task_126"],
        "failures": [],
        "enrichment_type": "content_analysis",
        "priority": "normal"
    }
    enricher.get_enrichment_status.return_value = {
        "content_id": "test_content",
        "status": "available",
        "title": "Test Content",
        "quality_score": 0.8,
        "enrichment_available": True
    }
    enricher.get_system_metrics.return_value = EnrichmentMetrics(
        total_tasks_processed=100,
        successful_tasks=95,
        failed_tasks=5
    )
    enricher._execute_gap_analysis.return_value = [
        {
            "query": "test query",
            "gap_type": "missing_examples",
            "confidence": 0.8,
            "priority": "high",
            "suggested_sources": ["github", "documentation"],
            "metadata": {}
        }
    ]
    enricher.bulk_import_technology.return_value = EnrichmentResult(
        content_id="bulk_import_test",
        enhanced_tags=["test", "bulk_import"],
        relationships=[],
        quality_improvements={"imported_documents": 50},
        processing_time_ms=30000,
        confidence_score=0.9
    )
    enricher.health_check.return_value = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return enricher


class TestHTTPStatusCodeMapping:
    """Test HTTP status code mapping for enrichment exceptions."""
    
    def test_invalid_task_error_mapping(self):
        """Test InvalidTaskError maps to 400 Bad Request."""
        exc = InvalidTaskError("Invalid task parameters")
        status_code = map_enrichment_exception_to_http_status(exc)
        assert status_code == status.HTTP_400_BAD_REQUEST
    
    def test_timeout_error_mapping(self):
        """Test EnrichmentTimeoutError maps to 408 Request Timeout."""
        exc = EnrichmentTimeoutError("Operation timed out")
        status_code = map_enrichment_exception_to_http_status(exc)
        assert status_code == status.HTTP_408_REQUEST_TIMEOUT
    
    def test_analysis_error_mapping(self):
        """Test AnalysisError maps to 422 Unprocessable Entity."""
        exc = AnalysisError("Analysis failed")
        status_code = map_enrichment_exception_to_http_status(exc)
        assert status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_task_processing_error_mapping(self):
        """Test TaskProcessingError maps to 503 Service Unavailable."""
        exc = TaskProcessingError("Task processing failed")
        status_code = map_enrichment_exception_to_http_status(exc)
        assert status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    def test_general_enrichment_error_mapping(self):
        """Test EnrichmentError maps to 500 Internal Server Error."""
        exc = EnrichmentError("General enrichment error")
        status_code = map_enrichment_exception_to_http_status(exc)
        assert status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_unknown_exception_mapping(self):
        """Test unknown exceptions map to 500 Internal Server Error."""
        exc = ValueError("Unknown error")
        status_code = map_enrichment_exception_to_http_status(exc)
        assert status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestErrorHandling:
    """Test standardized error handling patterns."""
    
    def test_handle_enrichment_error_structure(self):
        """Test error response structure follows system patterns."""
        exc = EnrichmentError("Test error", error_context={"key": "value"})
        http_exc = handle_enrichment_error(exc)
        
        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert isinstance(http_exc.detail, dict)
        assert "error" in http_exc.detail
        assert "message" in http_exc.detail
        assert "details" in http_exc.detail
        assert "timestamp" in http_exc.detail
        assert http_exc.detail["error"] == "EnrichmentError"
        assert http_exc.detail["message"] == "Test error"
        assert http_exc.detail["details"] == {"key": "value"}
    
    def test_handle_enrichment_error_without_context(self):
        """Test error handling without error context."""
        exc = EnrichmentError("Test error")
        http_exc = handle_enrichment_error(exc)
        
        assert http_exc.detail["details"] == {}


class TestEnrichmentEndpoints:
    """Test enrichment API endpoints follow standardized patterns."""
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_enrich_content_success(self, mock_get_enricher, client, mock_enricher):
        """Test successful content enrichment submission."""
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {
            "content_id": "test_content",
            "enrichment_types": ["content_analysis", "tag_generation"],
            "priority": "normal"
        }
        
        response = client.post("/enrichment/enrich", json=request_data)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_ids" in data
        assert "content_id" in data
        assert "enrichment_types" in data
        assert "priority" in data
        assert "submitted_at" in data
        assert data["content_id"] == "test_content"
        assert len(data["task_ids"]) == 2
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_bulk_enrich_success(self, mock_get_enricher, client, mock_enricher):
        """Test successful bulk enrichment submission."""
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {
            "content_ids": ["content_1", "content_2"],
            "enrichment_type": "content_analysis",
            "priority": "low"
        }
        
        response = client.post("/enrichment/bulk-enrich", json=request_data)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "total_submitted" in data
        assert "successful_submissions" in data
        assert "failed_submissions" in data
        assert "task_ids" in data
        assert data["total_submitted"] == 2
        assert data["successful_submissions"] == 2
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_get_enrichment_status_success(self, mock_get_enricher, client, mock_enricher):
        """Test successful enrichment status retrieval."""
        mock_get_enricher.return_value = mock_enricher
        
        response = client.get("/enrichment/status/test_content")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content_id" in data
        assert "status" in data
        assert "enrichment_available" in data
        assert data["content_id"] == "test_content"
        assert data["status"] == "available"
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_get_enrichment_status_not_found(self, mock_get_enricher, client, mock_enricher):
        """Test enrichment status for non-existent content."""
        mock_enricher.get_enrichment_status.return_value = {
            "content_id": "missing_content",
            "status": "not_found",
            "message": "Content not found"
        }
        mock_get_enricher.return_value = mock_enricher
        
        response = client.get("/enrichment/status/missing_content")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert data["error"] == "ContentNotFound"
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_gap_analysis_success(self, mock_get_enricher, client, mock_enricher):
        """Test successful content gap analysis."""
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {"query": "test query for gaps"}
        
        response = client.post("/enrichment/gap-analysis", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert "query" in data[0]
        assert "gap_type" in data[0]
        assert "confidence" in data[0]
        assert data[0]["query"] == "test query for gaps"
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_bulk_import_success(self, mock_get_enricher, client, mock_enricher):
        """Test successful bulk technology import."""
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {"technology_name": "react"}
        
        response = client.post("/enrichment/bulk-import", json=request_data)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "content_id" in data
        assert "enhanced_tags" in data
        assert "processing_time_ms" in data
        assert "confidence_score" in data
        assert data["confidence_score"] == 0.9
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_get_metrics_success(self, mock_get_enricher, client, mock_enricher):
        """Test successful metrics retrieval."""
        mock_get_enricher.return_value = mock_enricher
        
        response = client.get("/enrichment/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_tasks_processed" in data
        assert "successful_tasks" in data
        assert "failed_tasks" in data
        assert data["total_tasks_processed"] == 100
        assert data["successful_tasks"] == 95
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_health_check_success(self, mock_get_enricher, client, mock_enricher):
        """Test successful health check."""
        mock_get_enricher.return_value = mock_enricher
        
        response = client.get("/enrichment/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_health_check_unhealthy(self, mock_get_enricher, client, mock_enricher):
        """Test health check when system is unhealthy."""
        mock_enricher.health_check.return_value = {
            "status": "unhealthy",
            "error": "Service degraded"
        }
        mock_get_enricher.return_value = mock_enricher
        
        response = client.get("/enrichment/health")
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"


class TestRequestValidation:
    """Test request validation follows Pydantic patterns."""
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_enrich_content_invalid_priority(self, mock_get_enricher, client, mock_enricher):
        """Test validation of invalid priority values."""
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {
            "content_id": "test_content",
            "priority": "invalid_priority"
        }
        
        response = client.post("/enrichment/enrich", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher') 
    def test_enrich_content_missing_content_id(self, mock_get_enricher, client, mock_enricher):
        """Test validation of missing required fields."""
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {"priority": "normal"}
        
        response = client.post("/enrichment/enrich", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_bulk_enrich_empty_content_ids(self, mock_get_enricher, client, mock_enricher):
        """Test validation of empty content ID lists."""
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {
            "content_ids": [],
            "enrichment_type": "content_analysis"
        }
        
        response = client.post("/enrichment/bulk-enrich", json=request_data)
        
        # Should be accepted but return appropriate response
        assert response.status_code in [status.HTTP_202_ACCEPTED, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestErrorResponseFormats:
    """Test error response formats match system standards."""
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_service_unavailable_error_format(self, mock_get_enricher, client):
        """Test service unavailable error response format."""
        mock_get_enricher.side_effect = Exception("Service unavailable")
        
        response = client.get("/enrichment/metrics")
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        # The dependency injection will handle this error
    
    @patch('src.api.v1.enrichment.get_knowledge_enricher')
    def test_enrichment_error_format(self, mock_get_enricher, client, mock_enricher):
        """Test enrichment error response format."""
        mock_enricher.enrich_content.side_effect = EnrichmentError(
            "Test enrichment error",
            error_context={"context_key": "context_value"}
        )
        mock_get_enricher.return_value = mock_enricher
        
        request_data = {
            "content_id": "test_content",
            "priority": "normal"
        }
        
        response = client.post("/enrichment/enrich", json=request_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "details" in data
        assert "timestamp" in data
        assert data["error"] == "EnrichmentError"
        assert data["details"]["context_key"] == "context_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])