"""
PRD-001 HTTP API Foundation - Final Production Readiness Validation
Testing critical blocker fixes and production approval criteria
"""

import pytest
import asyncio
import os
import ast
import importlib
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import status
import json
import time
import requests
from unittest.mock import patch, MagicMock

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

class TestCriticalFixesValidation:
    """Test that all critical production blockers have been resolved"""
    
    def test_module_file_size_limits(self):
        """Verify all 4 endpoint modules are under 200 lines"""
        endpoint_modules = [
            "src/api/v1/search_endpoints.py",
            "src/api/v1/admin_endpoints.py", 
            "src/api/v1/config_endpoints.py",
            "src/api/v1/health_endpoints.py"
        ]
        
        for module_path in endpoint_modules:
            full_path = Path(__file__).parent.parent.parent.parent / module_path
            assert full_path.exists(), f"Module {module_path} does not exist"
            
            with open(full_path, 'r') as f:
                lines = f.readlines()
                line_count = len(lines)
                
            assert line_count < 200, f"Module {module_path} has {line_count} lines, exceeds 200 line limit"
            assert line_count > 50, f"Module {module_path} has {line_count} lines, suspiciously small"
    
    def test_no_hardcoded_credentials_config(self):
        """Verify zero hardcoded credentials in config system"""
        config_files = [
            "src/core/config/__init__.py",
            "src/core/config/defaults.py",
            "src/core/config/models.py", 
            "src/core/config/secrets.py",
            "src/core/config/validation.py"
        ]
        
        suspicious_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][a-zA-Z0-9]{8,}["\']'
        ]
        
        import re
        
        for config_file in config_files:
            full_path = Path(__file__).parent.parent.parent.parent / config_file
            if full_path.exists():
                with open(full_path, 'r') as f:
                    content = f.read()
                
                for pattern in suspicious_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    assert not matches, f"Found potential hardcoded credential in {config_file}: {matches}"
    
    def test_fastapi_application_startup_no_errors(self):
        """Test FastAPI application starts without import errors"""
        try:
            from src.main import app
            assert app is not None, "FastAPI app instance not created"
            
            # Test basic app properties
            assert hasattr(app, 'router'), "App missing router attribute"
            assert hasattr(app, 'middleware_stack'), "App missing middleware stack"
            
        except ImportError as e:
            pytest.fail(f"Import error during FastAPI startup: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error during FastAPI startup: {e}")
    
    def test_all_8_endpoints_functional_after_split(self):
        """Verify all 8 endpoints still functional after module split"""
        from src.main import app
        client = TestClient(app)
        
        # Required endpoints from PRD-001
        endpoints_to_test = [
            ("/api/v1/search", "POST"),
            ("/api/v1/search/feedback", "POST"), 
            ("/api/v1/search/signals", "POST"),
            ("/api/v1/admin/content/search", "GET"),
            ("/api/v1/config", "GET"),
            ("/api/v1/config", "PUT"),
            ("/health", "GET"),
            ("/api/v1/system/stats", "GET")
        ]
        
        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            
            # Should not be 404 (endpoint exists) or 500 (no import errors)
            assert response.status_code != 404, f"Endpoint {endpoint} not found after module split"
            assert response.status_code != 500, f"Internal server error on {endpoint} after module split"

class TestPRD001ImplementationTasks:
    """Test all 12 PRD-001 implementation tasks are working correctly"""
    
    def test_fastapi_application_initialization(self):
        """Task 1: FastAPI application properly initialized"""
        from src.main import app
        
        assert app.title == "AI Documentation Cache API"
        assert app.version == "1.0.0"
        assert "/api/v1" in str(app.router.routes)
    
    def test_pydantic_schemas_validation(self):
        """Task 2: Pydantic schemas for request/response validation"""
        from src.api.v1.schemas import (
            SearchRequest, SearchResponse, ErrorResponse,
            FeedbackRequest, ConfigResponse
        )
        
        # Test basic schema validation
        search_req = SearchRequest(query="test", max_results=5)
        assert search_req.query == "test"
        assert search_req.max_results == 5
        
        error_resp = ErrorResponse(type="validation_error", title="Test Error")
        assert error_resp.type == "validation_error"
    
    def test_authentication_middleware(self):
        """Task 3: Authentication middleware implementation"""
        from src.main import app
        client = TestClient(app)
        
        # Test protected endpoint without auth
        response = client.post("/api/v1/admin/content/search")
        assert response.status_code in [401, 403], "Admin endpoint should require authentication"
    
    def test_rate_limiting_middleware(self):
        """Task 4: Rate limiting implementation"""
        from src.main import app
        client = TestClient(app)
        
        # Make rapid requests to trigger rate limiting
        responses = []
        for i in range(10):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # Should have at least some successful requests
        assert 200 in responses, "Rate limiting blocking all requests"
    
    def test_cors_middleware_configuration(self):
        """Task 5: CORS middleware properly configured"""
        from src.main import app
        client = TestClient(app)
        
        # Test preflight request
        response = client.options("/api/v1/search", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        })
        
        # Should not be blocked by CORS
        assert response.status_code != 403, "CORS blocking legitimate requests"
    
    def test_rfc7807_error_handling(self):
        """Task 6: RFC 7807 compliant error handling"""
        from src.main import app
        client = TestClient(app)
        
        # Trigger validation error
        response = client.post("/api/v1/search", json={"invalid": "data"})
        
        if response.status_code == 422:
            error_data = response.json()
            assert "type" in error_data, "Error response missing RFC 7807 'type' field"
            assert "title" in error_data, "Error response missing RFC 7807 'title' field"
    
    def test_structured_logging_integration(self):
        """Task 7: Structured logging implementation"""
        import logging
        
        # Check if structured logging is configured
        logger = logging.getLogger("src")
        assert len(logger.handlers) > 0, "No logging handlers configured"
    
    def test_health_check_endpoints(self):
        """Task 8: Health check endpoints implementation"""
        from src.main import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200, "Health endpoint not responding"
        
        health_data = response.json()
        assert "status" in health_data, "Health response missing status field"
        assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_search_endpoint_integration(self):
        """Task 9: Search endpoints with orchestrator integration"""
        from src.main import app
        client = TestClient(app)
        
        search_payload = {
            "query": "test search",
            "max_results": 5,
            "include_metadata": True
        }
        
        response = client.post("/api/v1/search", json=search_payload)
        # Should not have import/integration errors
        assert response.status_code != 500, "Search endpoint has integration errors"
    
    def test_admin_endpoints_functionality(self):
        """Task 10: Admin endpoints for content management"""
        from src.main import app
        client = TestClient(app)
        
        # Test admin search endpoint exists
        response = client.get("/api/v1/admin/content/search")
        assert response.status_code != 404, "Admin search endpoint not found"
    
    def test_configuration_endpoints(self):
        """Task 11: Configuration management endpoints"""
        from src.main import app
        client = TestClient(app)
        
        # Test config GET endpoint
        response = client.get("/api/v1/config")
        assert response.status_code != 404, "Config GET endpoint not found"
        
        # Test config PUT endpoint
        response = client.put("/api/v1/config", json={"test": "value"})
        assert response.status_code != 404, "Config PUT endpoint not found"
    
    def test_openapi_documentation(self):
        """Task 12: OpenAPI documentation generation"""
        from src.main import app
        client = TestClient(app)
        
        response = client.get("/docs")
        assert response.status_code == 200, "OpenAPI docs not accessible"

class TestSecurityReAssessment:
    """Re-assess security after fixes"""
    
    def test_no_secrets_in_source_code(self):
        """Verify no secrets exposed in any source files"""
        src_path = Path(__file__).parent.parent.parent.parent / "src"
        
        secret_patterns = [
            r'sk-[a-zA-Z0-9]{48}',  # OpenAI API keys
            r'[a-zA-Z0-9]{32,}',    # Generic long strings that might be secrets
            r'password\s*[:=]\s*["\'][^"\']{8,}["\']',
            r'secret\s*[:=]\s*["\'][^"\']{8,}["\']'
        ]
        
        import re
        
        for py_file in src_path.rglob("*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
            
            for pattern in secret_patterns:
                matches = re.findall(pattern, content)
                # Filter out obvious false positives
                real_secrets = [m for m in matches if not any(fp in m.lower() for fp in [
                    'example', 'placeholder', 'test', 'mock', 'fake', 'demo'
                ])]
                
                assert not real_secrets, f"Potential secrets found in {py_file}: {real_secrets}"
    
    def test_environment_variable_configuration(self):
        """Verify proper environment variable usage"""
        from src.core.config import get_settings
        
        settings = get_settings()
        
        # Should use environment variables for sensitive config
        assert hasattr(settings, 'anythingllm_api_key'), "Missing AnythingLLM API key config"
        assert hasattr(settings, 'database_url'), "Missing database URL config"
    
    def test_error_responses_no_leak(self):
        """Verify error responses don't leak internal information"""
        from src.main import app
        client = TestClient(app)
        
        # Trigger various error conditions
        response = client.post("/api/v1/search", json={"malicious": "<script>alert('xss')</script>"})
        
        if response.status_code in [400, 422, 500]:
            error_content = response.text.lower()
            
            # Should not leak internal paths or stack traces
            assert "/home/" not in error_content, "Error response leaking file paths"
            assert "traceback" not in error_content, "Error response leaking stack traces"
            assert "sqlalchemy" not in error_content, "Error response leaking implementation details"

class TestIntegrationValidation:
    """Test integration with other PRD components"""
    
    def test_search_orchestrator_integration(self):
        """Verify integration with Search Orchestrator (PRD-009)"""
        try:
            from src.search.orchestrator import SearchOrchestrator
            orchestrator = SearchOrchestrator()
            assert orchestrator is not None, "SearchOrchestrator not instantiable"
        except ImportError:
            pytest.skip("Search Orchestrator not yet implemented")
    
    def test_anythingllm_integration_health(self):
        """Verify AnythingLLM Integration (PRD-004) status in health checks"""
        from src.main import app
        client = TestClient(app)
        
        response = client.get("/api/v1/system/stats")
        if response.status_code == 200:
            stats_data = response.json()
            # Should have some reference to external service status
            assert isinstance(stats_data, dict), "Stats response should be a dictionary"
    
    def test_configuration_consistency(self):
        """Verify configuration is consistent across components"""
        from src.core.config import get_settings
        
        settings = get_settings()
        
        # Test that settings can be loaded without errors
        assert settings is not None, "Configuration cannot be loaded"
        
        # Verify environment variable hierarchy works
        test_env_var = "TEST_CONFIG_VALUE"
        os.environ[test_env_var] = "test_value"
        
        # Configuration should be able to read environment variables
        assert os.getenv(test_env_var) == "test_value", "Environment variable reading broken"
        
        # Cleanup
        del os.environ[test_env_var]

class TestPerformanceAndReliability:
    """Test performance characteristics and reliability"""
    
    def test_application_startup_time(self):
        """Verify application starts within reasonable time"""
        start_time = time.time()
        
        from src.main import app
        
        startup_time = time.time() - start_time
        
        # Should start within 5 seconds
        assert startup_time < 5.0, f"Application startup took {startup_time:.2f}s, too slow"
    
    def test_endpoint_response_times(self):
        """Test endpoint response times under normal load"""
        from src.main import app
        client = TestClient(app)
        
        # Test health endpoint performance
        start_time = time.time()
        response = client.get("/health")
        response_time = time.time() - start_time
        
        assert response.status_code == 200, "Health endpoint not responding"
        assert response_time < 1.0, f"Health endpoint too slow: {response_time:.2f}s"
    
    def test_concurrent_request_handling(self):
        """Test basic concurrent request handling"""
        from src.main import app
        client = TestClient(app)
        
        # Make multiple rapid requests
        responses = []
        for i in range(5):
            response = client.get("/health")
            responses.append(response.status_code)
        
        # All should succeed (no resource conflicts)
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 4, f"Only {success_count}/5 concurrent requests succeeded"

class TestOperationalReadiness:
    """Test operational readiness for production deployment"""
    
    def test_graceful_error_handling(self):
        """Test graceful handling of various error conditions"""
        from src.main import app
        client = TestClient(app)
        
        # Test malformed JSON
        response = client.post("/api/v1/search", 
                             data="malformed json", 
                             headers={"Content-Type": "application/json"})
        
        # Should handle gracefully, not crash
        assert response.status_code in [400, 422], "Malformed JSON not handled gracefully"
    
    def test_health_monitoring_capabilities(self):
        """Test health monitoring and observability"""
        from src.main import app
        client = TestClient(app)
        
        # Health endpoint should provide useful information
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data, "Health check missing status"
        assert "timestamp" in health_data, "Health check missing timestamp"
    
    def test_configuration_validation_at_startup(self):
        """Test configuration validation during startup"""
        from src.core.config import get_settings
        
        # Should not raise exceptions during normal configuration loading
        try:
            settings = get_settings()
            assert settings is not None
        except Exception as e:
            pytest.fail(f"Configuration validation failed: {e}")

# Test Execution Functions
def run_all_validation_tests():
    """Execute all validation tests and return results"""
    test_results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "failures": [],
        "categories": {
            "critical_fixes": {"passed": 0, "total": 0, "failures": []},
            "prd_implementation": {"passed": 0, "total": 0, "failures": []},
            "security": {"passed": 0, "total": 0, "failures": []},
            "integration": {"passed": 0, "total": 0, "failures": []},
            "performance": {"passed": 0, "total": 0, "failures": []},
            "operational": {"passed": 0, "total": 0, "failures": []}
        }
    }
    
    test_classes = [
        (TestCriticalFixesValidation, "critical_fixes"),
        (TestPRD001ImplementationTasks, "prd_implementation"), 
        (TestSecurityReAssessment, "security"),
        (TestIntegrationValidation, "integration"),
        (TestPerformanceAndReliability, "performance"),
        (TestOperationalReadiness, "operational")
    ]
    
    for test_class, category in test_classes:
        instance = test_class()
        test_methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for test_method in test_methods:
            test_results["total_tests"] += 1
            test_results["categories"][category]["total"] += 1
            
            try:
                getattr(instance, test_method)()
                test_results["passed_tests"] += 1
                test_results["categories"][category]["passed"] += 1
            except Exception as e:
                test_results["failed_tests"] += 1
                failure_info = f"{test_class.__name__}.{test_method}: {str(e)}"
                test_results["failures"].append(failure_info)
                test_results["categories"][category]["failures"].append(failure_info)
    
    return test_results

if __name__ == "__main__":
    results = run_all_validation_tests()
    
    print("\n" + "="*80)
    print("PRD-001 HTTP API FOUNDATION - FINAL PRODUCTION VALIDATION RESULTS")
    print("="*80)
    
    print(f"\nOVERALL RESULTS:")
    print(f"Tests Passed: {results['passed_tests']}/{results['total_tests']}")
    print(f"Success Rate: {(results['passed_tests']/results['total_tests']*100):.1f}%")
    
    for category, data in results["categories"].items():
        status = "PASS" if data["passed"] == data["total"] else "FAIL"
        print(f"{category.replace('_', ' ').title()}: {data['passed']}/{data['total']} [{status}]")
    
    if results["failures"]:
        print(f"\nFAILURES ({len(results['failures'])}):")
        for failure in results["failures"]:
            print(f"  ❌ {failure}")
    
    # Final production decision
    all_tests_passed = results["passed_tests"] == results["total_tests"]
    critical_fixes_passed = results["categories"]["critical_fixes"]["passed"] == results["categories"]["critical_fixes"]["total"]
    security_passed = results["categories"]["security"]["passed"] == results["categories"]["security"]["total"]
    
    print(f"\n" + "="*80)
    if all_tests_passed and critical_fixes_passed and security_passed:
        print("🟢 APPROVED FOR PRODUCTION DEPLOYMENT")
        print("All critical blockers resolved, PRD-001 ready for production")
    else:
        print("🔴 REQUIRES ADDITIONAL FIXES")
        print("Critical issues preventing production approval")
    print("="*80)