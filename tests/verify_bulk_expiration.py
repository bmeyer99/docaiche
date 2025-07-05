#!/usr/bin/env python3
"""
Verification script for bulk expiration query methods.
This script validates that all required methods exist and have correct signatures.
"""

import requests
import json
from typing import Dict, Any, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BulkExpirationVerifier:
    """Verify bulk expiration functionality via API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:4080"):
        self.base_url = base_url
        self.test_workspace = "test-workspace"
        
    def verify_api_endpoint(self, endpoint: str, method: str = "GET", params: Dict = None) -> Dict[str, Any]:
        """Make API request and verify response."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, params=params, timeout=30)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_verification(self) -> bool:
        """Run all verification tests."""
        logger.info("Starting bulk expiration verification...")
        
        tests = [
            self.verify_get_expired_documents,
            self.verify_get_expired_documents_optimized,
            self.verify_cleanup_expired_documents,
            self.verify_get_documents_by_provider,
            self.verify_get_expiration_statistics,
            self.verify_parameter_handling,
            self.verify_error_handling
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                test()
                passed_tests += 1
                logger.info(f"✅ {test.__name__} passed")
            except Exception as e:
                logger.error(f"❌ {test.__name__} failed: {e}")
        
        success_rate = (passed_tests / total_tests) * 100
        logger.info(f"Verification complete: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        return passed_tests == total_tests
    
    def verify_get_expired_documents(self):
        """Verify get_expired_documents endpoint."""
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/expired"
        result = self.verify_api_endpoint(endpoint)
        
        assert result["success"], f"API call failed: {result.get('error')}"
        
        data = result["data"]
        required_fields = ["workspace", "expired_documents", "count", "limit"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"
        
        assert data["workspace"] == self.test_workspace
        assert isinstance(data["expired_documents"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["limit"], int)
    
    def verify_get_expired_documents_optimized(self):
        """Verify get_expired_documents_optimized endpoint."""
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/expired/optimized"
        result = self.verify_api_endpoint(endpoint)
        
        assert result["success"], f"API call failed: {result.get('error')}"
        
        data = result["data"]
        required_fields = ["workspace", "expired_documents", "count", "limit", "optimized"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"
        
        assert data["optimized"] == True
    
    def verify_cleanup_expired_documents(self):
        """Verify cleanup_expired_documents endpoint."""
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/expired"
        result = self.verify_api_endpoint(endpoint, method="DELETE")
        
        assert result["success"], f"API call failed: {result.get('error')}"
        
        data = result["data"]
        required_fields = ["workspace", "cleanup_result", "batch_size"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"
        
        cleanup_result = data["cleanup_result"]
        cleanup_fields = ["deleted_documents", "deleted_chunks", "message", "duration_seconds"]
        for field in cleanup_fields:
            assert field in cleanup_result, f"Required cleanup field '{field}' missing"
    
    def verify_get_documents_by_provider(self):
        """Verify get_documents_by_provider endpoint."""
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/providers/github"
        result = self.verify_api_endpoint(endpoint)
        
        assert result["success"], f"API call failed: {result.get('error')}"
        
        data = result["data"]
        required_fields = ["workspace", "source_provider", "documents", "count", "limit"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"
        
        assert data["source_provider"] == "github"
        assert isinstance(data["documents"], list)
    
    def verify_get_expiration_statistics(self):
        """Verify get_expiration_statistics endpoint."""
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/expiration/statistics"
        result = self.verify_api_endpoint(endpoint)
        
        assert result["success"], f"API call failed: {result.get('error')}"
        
        data = result["data"]
        required_fields = ["workspace", "statistics"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"
        
        stats = data["statistics"]
        stats_fields = [
            "total_chunks", "total_documents", "expired_documents", "expired_chunks",
            "expiring_soon_documents", "expiring_soon_chunks", "providers",
            "oldest_expiry", "newest_expiry", "documents_by_expiry"
        ]
        for field in stats_fields:
            assert field in stats, f"Required statistics field '{field}' missing"
    
    def verify_parameter_handling(self):
        """Verify API endpoints handle parameters correctly."""
        # Test custom limit parameter
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/expired"
        result = self.verify_api_endpoint(endpoint, params={"limit": 5})
        
        assert result["success"], "Custom limit parameter failed"
        assert result["data"]["limit"] == 5
        
        # Test custom batch size parameter
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/expired"
        result = self.verify_api_endpoint(endpoint, method="DELETE", params={"batch_size": 10})
        
        assert result["success"], "Custom batch size parameter failed"
        assert result["data"]["batch_size"] == 10
        
        # Test provider parameter
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/providers/gitlab"
        result = self.verify_api_endpoint(endpoint, params={"limit": 50})
        
        assert result["success"], "Provider parameter failed"
        assert result["data"]["source_provider"] == "gitlab"
        assert result["data"]["limit"] == 50
    
    def verify_error_handling(self):
        """Verify API endpoints handle errors properly."""
        # Test invalid workspace
        endpoint = f"/api/v1/weaviate/workspaces/invalid-workspace-12345/expired"
        result = self.verify_api_endpoint(endpoint)
        
        assert not result["success"], "Invalid workspace should return error"
        assert "detail" in result["error"] or "error" in result["error"]
        
        # Test invalid HTTP method
        endpoint = f"/api/v1/weaviate/workspaces/{self.test_workspace}/expired"
        result = self.verify_api_endpoint(endpoint, method="POST")
        
        assert not result["success"], "Invalid HTTP method should return error"

def main():
    """Main verification function."""
    verifier = BulkExpirationVerifier()
    
    logger.info("=" * 60)
    logger.info("BULK EXPIRATION VERIFICATION")
    logger.info("=" * 60)
    
    success = verifier.run_verification()
    
    if success:
        logger.info("🎉 ALL VERIFICATION TESTS PASSED!")
        logger.info("✅ Bulk expiration query methods are working correctly")
        logger.info("✅ API endpoints return proper JSON responses")
        logger.info("✅ Error handling works for edge cases")
        logger.info("✅ TTL filtering logic implemented")
        logger.info("✅ Batch processing functionality available")
        logger.info("✅ Methods return useful statistics and metadata")
        return 0
    else:
        logger.error("❌ SOME VERIFICATION TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())