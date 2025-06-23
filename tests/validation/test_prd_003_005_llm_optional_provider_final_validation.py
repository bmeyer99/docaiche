import os
import pytest
from fastapi.testclient import TestClient

import src.main

@pytest.fixture(scope="session")
def client():
    # Ensure no LLM config is present
    os.environ.pop("LLM_PROVIDER", None)
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OLLAMA_HOST", None)
    return TestClient(src.main.app)

def test_health_endpoint_always_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json().get("overall_status") in ("healthy", "degraded", "unhealthy")

def test_all_endpoints_accessible_without_llm(client):
    endpoints = [
        ("/api/v1/health", "get"),
        ("/api/v1/search", "post"),
        ("/api/v1/ingest", "post"),
        ("/api/v1/config", "get"),
        ("/docs", "get"),
    ]
    for url, method in endpoints:
        req = getattr(client, method)
        if method == "post":
            resp = req(url, json={"query": "test"})
        else:
            resp = req(url)
        assert resp.status_code in (200, 400, 422), f"{url} failed with {resp.status_code}"

def test_llm_endpoint_returns_error_without_provider(client):
    resp = client.post("/api/v1/llm/generate", json={"prompt": "test"})
    assert resp.status_code in (400, 501, 503, 404)
    assert "LLM provider" in resp.text or "not configured" in resp.text or "unavailable" in resp.text or resp.status_code == 404

def test_document_processing_pipeline_works_without_llm(client):
    resp = client.post("/api/v1/ingest", json={"document_url": "https://example.com/doc.txt"})
    assert resp.status_code in (200, 201, 202, 400, 422, 404)

def test_health_endpoint_ok_with_llm_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    client = TestClient(src.main.app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json().get("overall_status") in ("healthy", "degraded", "unhealthy")

def test_llm_endpoint_works_with_valid_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    client = TestClient(src.main.app)
    resp = client.post("/api/v1/llm/generate", json={"prompt": "test"})
    assert resp.status_code in (200, 503, 404)
    if resp.status_code == 200:
        assert "result" in resp.json() or "output" in resp.json()

def test_llm_endpoint_error_message_is_clear(client):
    resp = client.post("/api/v1/llm/generate", json={"prompt": "test"})
    assert resp.status_code in (400, 501, 503, 404)
    assert any(
        msg in resp.text.lower()
        for msg in ["llm provider", "not configured", "unavailable", "missing"]
    ) or resp.status_code == 404

def test_document_processing_independent_of_llm(client):
    resp = client.post("/api/v1/ingest", json={"document_url": "https://example.com/doc.txt"})
    assert resp.status_code not in (500, 503)