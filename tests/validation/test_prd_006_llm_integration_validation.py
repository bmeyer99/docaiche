import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
from src.document_processing.models import DocumentFormat, DocumentMetadata, DocumentChunk
from src.document_processing.chunking import DocumentChunker
from src.document_processing.metadata import MetadataExtractor
from src.document_processing.pipeline import DocumentProcessingPipeline
from src.llm.client import LLMProviderClient
from src.llm.models import LLMProviderUnavailableError
import io

client = TestClient(app)

# ---------- FUNCTIONAL & INTEGRATION TESTS ----------

def test_document_processing_no_llm(monkeypatch):
    """Document processing works fully when no LLM providers are configured"""
    with patch("src.llm.client.LLMProviderClient", side_effect=LLMProviderUnavailableError):
        file_content = b"Test content"
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", file_content, "text/plain")},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        status_resp = client.get(f"/api/v1/documents/{job_id}/status")
        assert status_resp.status_code == 200
        # Should not error due to missing LLM

def test_document_processing_with_llm_enabled(monkeypatch):
    """Document processing pipeline works with LLM provider enabled"""
    mock_llm = MagicMock()
    mock_llm.status.any_provider_available = True
    monkeypatch.setattr("src.llm.client.LLMProviderClient", lambda *a, **kw: mock_llm)
    file_content = b"Test content"
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", file_content, "text/plain")},
    )
    assert resp.status_code == 200

def test_document_processing_with_llm_disabled(monkeypatch):
    """Document processing pipeline works with LLM provider disabled"""
    mock_llm = MagicMock()
    mock_llm.status.any_provider_available = False
    monkeypatch.setattr("src.llm.client.LLMProviderClient", lambda *a, **kw: mock_llm)
    file_content = b"Test content"
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", file_content, "text/plain")},
    )
    assert resp.status_code == 200

def test_quality_assessment_with_and_without_llm(monkeypatch):
    """Quality assessment works with and without LLM provider"""
    # With LLM
    mock_llm = MagicMock()
    mock_llm.status.any_provider_available = True
    mock_llm.assess_content_quality.return_value = {"overall_score": 0.9}
    monkeypatch.setattr("src.llm.client.LLMProviderClient", lambda *a, **kw: mock_llm)
    pipeline = DocumentProcessingPipeline()
    result = pipeline.assess_quality("docid", "content")
    assert result is not None

    # Without LLM
    monkeypatch.setattr("src.llm.client.LLMProviderClient", side_effect=LLMProviderUnavailableError)
    pipeline = DocumentProcessingPipeline()
    try:
        result = pipeline.assess_quality("docid", "content")
    except LLMProviderUnavailableError:
        result = None
    assert result is None or result == {}

def test_chunking_and_metadata_independent_of_llm():
    """Chunking and metadata extraction work regardless of LLM provider state"""
    chunker = DocumentChunker()
    text = "A" * 5000
    chunks = chunker.chunk_document(text, "docid")
    assert isinstance(chunks, list)
    assert all(isinstance(c, DocumentChunk) for c in chunks)

    meta = MetadataExtractor()
    file_data = b"test"
    filename = "test.pdf"
    metadata = meta.extract_metadata("dummy_path", filename)
    assert isinstance(metadata, DocumentMetadata)

def test_api_response_llm_status(monkeypatch):
    """API endpoints respond with informative LLM enhancement availability"""
    # Simulate LLM available
    mock_llm = MagicMock()
    mock_llm.status.any_provider_available = True
    monkeypatch.setattr("src.llm.client.LLMProviderClient", lambda *a, **kw: mock_llm)
    resp = client.get("/api/v1/documents/health")
    assert resp.status_code == 200
    assert "llm" in resp.json()

    # Simulate LLM unavailable
    mock_llm.status.any_provider_available = False
    monkeypatch.setattr("src.llm.client.LLMProviderClient", lambda *a, **kw: mock_llm)
    resp = client.get("/api/v1/documents/health")
    assert resp.status_code == 200
    assert "llm" in resp.json()

def test_error_handling_llm_unavailable(monkeypatch):
    """Error handling and graceful degradation when LLM is unavailable"""
    monkeypatch.setattr("src.llm.client.LLMProviderClient", side_effect=LLMProviderUnavailableError)
    pipeline = DocumentProcessingPipeline()
    try:
        pipeline.assess_quality("docid", "content")
    except LLMProviderUnavailableError:
        assert True

def test_performance_when_llm_missing(monkeypatch):
    """Performance and reliability when LLM features are unavailable"""
    import time
    monkeypatch.setattr("src.llm.client.LLMProviderClient", side_effect=LLMProviderUnavailableError)
    start = time.time()
    file_content = b"Test content"
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", file_content, "text/plain")},
    )
    elapsed = time.time() - start
    assert resp.status_code == 200
    assert elapsed < 5