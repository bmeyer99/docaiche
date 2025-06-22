"""
Tests for FastAPI application initialization
PRD-001: HTTP API Foundation - Application Tests

Basic test coverage for the FastAPI application initialization as specified
in the API-001 task requirements.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_application_creation():
    """
    Test that the FastAPI application is created successfully.
    
    Verifies:
    - Application instance exists
    - Application has correct title and version
    """
    assert app is not None
    assert app.title == "AI Documentation Cache System API"
    assert app.version == "1.0.0"
    assert app.description == "Intelligent documentation cache with AI-powered search and enrichment"


def test_health_endpoint():
    """
    Test the health endpoint as specified in API-001 task requirements.
    
    Verifies:
    - Health endpoint returns 200 status
    - Response contains required fields
    - Response format matches specification
    """
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    
    # Verify timestamp format (ISO 8601 with Z suffix)
    assert data["timestamp"].endswith("Z")


def test_cors_headers():
    """
    Test that CORS headers are present in responses.
    
    Verifies:
    - CORS headers are present
    - Correct access control headers
    """
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    
    # Check for basic CORS headers
    headers = response.headers
    assert "access-control-allow-origin" in headers
    assert "access-control-allow-credentials" in headers


def test_security_headers():
    """
    Test that security headers are present in responses.
    
    Verifies:
    - Security headers are added by SecurityMiddleware
    - Headers match task specification
    """
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    
    headers = response.headers
    
    # Verify required security headers from task specification
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert "content-security-policy" in headers
    assert "referrer-policy" in headers


def test_openapi_docs_available():
    """
    Test that OpenAPI documentation is available.
    
    Verifies:
    - /docs endpoint is accessible
    - OpenAPI JSON is available
    """
    # Test Swagger UI docs
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    
    # Test OpenAPI JSON
    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    
    openapi_data = openapi_response.json()
    assert openapi_data["info"]["title"] == "AI Documentation Cache System API"
    assert openapi_data["info"]["version"] == "1.0.0"


def test_application_tags():
    """
    Test that OpenAPI tags are configured correctly.
    
    Verifies:
    - Required tags are present in OpenAPI specification
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi_data = response.json()
    tags = openapi_data.get("tags", [])
    tag_names = [tag["name"] for tag in tags]
    
    # Verify required tags from task specification
    expected_tags = ["search", "feedback", "admin", "config", "health"]
    for expected_tag in expected_tags:
        assert expected_tag in tag_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])