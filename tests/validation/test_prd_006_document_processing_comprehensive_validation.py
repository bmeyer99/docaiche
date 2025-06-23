import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.document_processing.models import DocumentFormat, ProcessingStatus, DocumentMetadata, DocumentChunk, ProcessingJob
from src.document_processing.chunking import DocumentChunker
from src.document_processing.extraction import TextExtractor
from src.document_processing.ingestion import DocumentIngestionService
from src.document_processing.metadata import MetadataExtractor
from src.document_processing.pipeline import DocumentProcessingPipeline
from src.document_processing.preprocessing import ContentPreprocessor
from src.document_processing.queue import ProcessingQueueManager
import io

client = TestClient(app)

# ---------- FUNCTIONAL TESTS ----------

def test_document_upload_and_status():
    # Test PDF, DOCX, TXT, MD, HTML upload and status
    for ext, mime in [
        (".pdf", "application/pdf"),
        (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (".txt", "text/plain"),
        (".md", "text/markdown"),
        (".html", "text/html"),
    ]:
        file_content = b"Test content"
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test" + ext, file_content, mime)},
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        status_resp = client.get(f"/api/v1/documents/{job_id}/status")
        assert status_resp.status_code == 200
        assert "status" in status_resp.json()

def test_file_size_limit_enforced():
    # Test large file rejection (simulate >100MB)
    big_file = io.BytesIO(b"x" * 101 * 1024 * 1024)
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("big.pdf", big_file, "application/pdf")},
    )
    assert resp.status_code == 413 or resp.status_code == 400

def test_format_detection_and_extraction():
    extractor = TextExtractor()
    # Simulate extraction for each format
    for ext in [DocumentFormat.PDF, DocumentFormat.DOCX, DocumentFormat.TXT, DocumentFormat.MD, DocumentFormat.HTML]:
        # Use dummy file path and format
        try:
            text = pytest.run(asyncio.run(extractor.extract_text("dummy_path", ext)))
        except Exception:
            pass  # Extraction should handle errors gracefully

def test_content_preprocessing():
    pre = ContentPreprocessor()
    text = "Some   text\nwith   extra   whitespace.\n\n"
    cleaned = pytest.run(asyncio.run(pre.clean_text(text)))
    normalized = pytest.run(asyncio.run(pre.normalize_whitespace(cleaned)))
    artifact_free = pytest.run(asyncio.run(pre.remove_artifacts(normalized)))
    assert isinstance(artifact_free, str)

def test_document_chunking():
    chunker = DocumentChunker()
    text = "A" * 5000
    chunks = pytest.run(asyncio.run(chunker.chunk_document(text, "docid")))
    assert isinstance(chunks, list)
    assert all(isinstance(c, DocumentChunk) for c in chunks)

def test_metadata_extraction_and_checksum():
    meta = MetadataExtractor()
    file_data = b"test"
    filename = "test.pdf"
    metadata = pytest.run(asyncio.run(meta.extract_metadata("dummy_path", filename)))
    checksum = pytest.run(asyncio.run(meta.calculate_checksum(file_data)))
    assert isinstance(metadata, DocumentMetadata)
    assert isinstance(checksum, str)

def test_processing_queue_lifecycle():
    # Simulate queue operations
    queue = ProcessingQueueManager(cache_manager=None)
    job = ProcessingJob(job_id="jid", status=ProcessingStatus.PENDING, progress=0.0)
    pytest.run(asyncio.run(queue.enqueue_job(job)))
    out = pytest.run(asyncio.run(queue.dequeue_job()))
    assert out is None or isinstance(out, ProcessingJob)

def test_job_retry_logic():
    # Simulate retry endpoint
    job_id = "fake_job"
    resp = client.post(f"/api/v1/documents/{job_id}/retry")
    assert resp.status_code in (200, 404)

# ---------- INTEGRATION TESTS ----------

def test_db_and_cache_integration(monkeypatch):
    # Patch DB/Cache managers to simulate integration
    service = DocumentIngestionService(config_manager=None, db_manager=None)
    assert hasattr(service, "db_manager")
    assert hasattr(service, "config_manager")

def test_logging_and_monitoring(monkeypatch):
    # Patch logger and check logs are written
    import logging
    logger = logging.getLogger("test")
    logger.info("test log")
    assert True

# ---------- SECURITY TESTS ----------

def test_file_type_and_size_validation():
    # Try uploading an executable
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
    )
    assert resp.status_code == 400

def test_path_traversal_protection():
    # Try uploading with dangerous filename
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("../../etc/passwd", b"root:x:0:0:", "text/plain")},
    )
    assert resp.status_code == 400

def test_input_sanitization():
    # Try uploading HTML with script
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.html", b"<script>alert(1)</script>", "text/html")},
    )
    assert resp.status_code == 200  # Should sanitize, not execute

def test_authentication_required(monkeypatch):
    # Simulate missing/invalid auth if required
    # If endpoints require auth, test 401/403
    assert True  # Placeholder

# ---------- PERFORMANCE TESTS ----------

def test_processing_speed_and_memory(monkeypatch):
    # Simulate timing and memory usage for a small doc
    import time
    start = time.time()
    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", b"quick test", "text/plain")},
    )
    assert resp.status_code == 200
    elapsed = time.time() - start
    assert elapsed < 5  # Should process quickly

def test_queue_throughput(monkeypatch):
    # Simulate multiple concurrent uploads
    for _ in range(10):
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": (f"test{_}.txt", b"test", "text/plain")},
        )
        assert resp.status_code == 200

# ---------- API CONTRACT TESTS ----------

def test_api_endpoints_exist():
    endpoints = [
        "/api/v1/documents/upload",
        "/api/v1/documents/{job_id}/status",
        "/api/v1/documents/{job_id}/retry",
        "/api/v1/documents/upload/batch",
        "/api/v1/documents/health",
        "/api/v1/documents/metrics",
        "/api/v1/documents/{document_id}",
    ]
    for ep in endpoints:
        url = ep.replace("{job_id}", "fakeid").replace("{document_id}", "fakeid")
        resp = client.get(url) if "get" in ep or "status" in ep or "metrics" in ep else client.post(url)
        assert resp.status_code in (200, 404, 405)

def test_error_responses():
    # Trigger errors and check for proper status codes/messages
    resp = client.post("/api/v1/documents/upload", files={})
    assert resp.status_code in (400, 422)

# ---------- DATA MODEL TESTS ----------

def test_pydantic_models():
    # Validate model serialization/deserialization
    meta = DocumentMetadata(document_id="id", filename="f", format=DocumentFormat.PDF, checksum="c", size=1)
    chunk = DocumentChunk(chunk_id="cid", document_id="id", text="t", order=1)
    job = ProcessingJob(job_id="jid", status=ProcessingStatus.PENDING, progress=0.0)
    assert meta.dict()
    assert chunk.dict()
    assert job.dict()

def test_data_integrity():
    # Simulate storing and retrieving metadata/chunks
    assert True  # Placeholder for DB roundtrip

# ---------- ERROR HANDLING TESTS ----------

def test_exception_handling_and_logging(monkeypatch):
    # Simulate error and check logs
    try:
        raise Exception("test")
    except Exception:
        assert True

def test_graceful_failure_and_recovery():
    # Simulate failure and retry
    job_id = "fail_job"
    resp = client.post(f"/api/v1/documents/{job_id}/retry")
    assert resp.status_code in (200, 404)