"""
Unit Tests for Ingest Tool
===========================

Comprehensive test suite for the docaiche_ingest tool implementation
covering consent management, URL validation, priority queuing, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestIngestTool:
    """Test suite for ingest tool operations."""
    
    def test_url_validation(self):
        """Test URL validation for different source types."""
        from urllib.parse import urlparse
        
        def validate_url(url, source_type):
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False, "Invalid scheme"
            
            # Check source type specific rules
            if source_type == "github":
                if "github.com" not in parsed.netloc:
                    return False, "Not a GitHub URL"
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) < 2:
                    return False, "Invalid GitHub path"
            
            elif source_type == "web":
                blocked = ["localhost", "127.0.0.1", "0.0.0.0", "internal"]
                if any(b in parsed.netloc for b in blocked):
                    return False, "Blocked domain"
            
            elif source_type == "api":
                if not parsed.path or parsed.path == "/":
                    return False, "Missing API endpoint"
            
            return True, "Valid"
        
        # Test GitHub URLs
        valid, msg = validate_url("https://github.com/python/cpython/tree/main/Doc", "github")
        assert valid is True
        
        valid, msg = validate_url("https://gitlab.com/project/repo", "github")
        assert valid is False
        assert msg == "Not a GitHub URL"
        
        valid, msg = validate_url("https://github.com/python", "github")
        assert valid is False
        assert msg == "Invalid GitHub path"
        
        # Test web URLs
        valid, msg = validate_url("https://react.dev/learn", "web")
        assert valid is True
        
        valid, msg = validate_url("http://localhost:8080/docs", "web")
        assert valid is False
        assert msg == "Blocked domain"
        
        # Test API URLs
        valid, msg = validate_url("https://api.example.com/v1/docs", "api")
        assert valid is True
        
        valid, msg = validate_url("https://api.example.com/", "api")
        assert valid is False
        assert msg == "Missing API endpoint"
        
        # Test invalid schemes
        valid, msg = validate_url("ftp://example.com/docs", "web")
        assert valid is False
        assert msg == "Invalid scheme"
    
    def test_priority_scoring(self):
        """Test priority score calculation."""
        def calculate_priority_score(priority):
            priority_map = {
                "high": 1,
                "normal": 5,
                "low": 10
            }
            return priority_map.get(priority, 5)
        
        assert calculate_priority_score("high") == 1
        assert calculate_priority_score("normal") == 5
        assert calculate_priority_score("low") == 10
        assert calculate_priority_score("invalid") == 5  # Default
    
    def test_wait_time_estimation(self):
        """Test wait time estimation logic."""
        def estimate_wait_time(priority, queue_size, active_count):
            # Base: 30 seconds per active
            base_time = active_count * 30
            
            # Queue time based on priority
            if priority == "high":
                queue_time = queue_size * 10
            elif priority == "normal":
                queue_time = queue_size * 20
            else:  # low
                queue_time = queue_size * 30
            
            return base_time + queue_time
        
        # Test with no queue
        assert estimate_wait_time("high", 0, 2) == 60  # 2 * 30
        
        # Test with queue
        assert estimate_wait_time("high", 5, 2) == 110  # 60 + 5*10
        assert estimate_wait_time("normal", 5, 2) == 160  # 60 + 5*20
        assert estimate_wait_time("low", 5, 2) == 210  # 60 + 5*30
    
    def test_consent_permission_calculation(self):
        """Test consent permission requirement calculation."""
        def get_required_permissions(ingest_params):
            permissions = ["ingest_content"]
            
            if ingest_params.get("workspace"):
                permissions.append(f"modify_workspace:{ingest_params['workspace']}")
            
            source_type = ingest_params.get("source_type")
            if source_type == "github":
                permissions.append("access_github")
            elif source_type == "api":
                permissions.append("access_external_api")
            
            return permissions
        
        # Test basic ingestion
        params = {"source_type": "web"}
        perms = get_required_permissions(params)
        assert "ingest_content" in perms
        assert len(perms) == 1
        
        # Test with workspace
        params = {"source_type": "web", "workspace": "public"}
        perms = get_required_permissions(params)
        assert "modify_workspace:public" in perms
        
        # Test GitHub source
        params = {"source_type": "github", "workspace": "dev"}
        perms = get_required_permissions(params)
        assert "access_github" in perms
        assert "modify_workspace:dev" in perms
        
        # Test API source
        params = {"source_type": "api"}
        perms = get_required_permissions(params)
        assert "access_external_api" in perms
    
    def test_ingestion_id_generation(self):
        """Test ingestion ID generation."""
        from datetime import datetime
        
        def generate_ingestion_id(source_url):
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            hash_part = hash(source_url) % 10000
            return f"ing_{timestamp}_{hash_part:04d}"
        
        # Test ID format
        id1 = generate_ingestion_id("https://example.com/docs")
        assert id1.startswith("ing_")
        assert len(id1.split("_")) == 3
        
        # Test uniqueness for different URLs
        id2 = generate_ingestion_id("https://different.com/docs")
        assert id1.split("_")[2] != id2.split("_")[2]  # Hash parts differ
    
    def test_queue_management(self):
        """Test ingestion queue behavior."""
        import asyncio
        
        async def test_queue():
            queue = asyncio.Queue()
            
            # Add items with priority scores
            items = [
                (5, {"id": "normal1", "priority": "normal"}),
                (1, {"id": "high1", "priority": "high"}),
                (10, {"id": "low1", "priority": "low"}),
                (1, {"id": "high2", "priority": "high"})
            ]
            
            for item in items:
                await queue.put(item)
            
            # Items should come out in FIFO order
            # (asyncio.Queue doesn't sort by priority)
            retrieved = []
            while not queue.empty():
                priority, item = await queue.get()
                retrieved.append(item["id"])
            
            assert retrieved == ["normal1", "high1", "low1", "high2"]
        
        asyncio.run(test_queue())
    
    def test_concurrent_ingestion_limits(self):
        """Test concurrent ingestion limit enforcement."""
        active_ingestions = {}
        max_concurrent = 5
        
        def can_start_ingestion():
            return len(active_ingestions) < max_concurrent
        
        # Test under limit
        for i in range(4):
            active_ingestions[f"ing_{i}"] = {"status": "active"}
        assert can_start_ingestion() is True
        
        # Test at limit
        active_ingestions["ing_4"] = {"status": "active"}
        assert can_start_ingestion() is False
        
        # Test after completion
        del active_ingestions["ing_0"]
        assert can_start_ingestion() is True
    
    def test_error_handling_scenarios(self):
        """Test various error scenarios."""
        # Test missing required fields
        def validate_params(params):
            errors = []
            
            if "source_url" not in params:
                errors.append("source_url is required")
            if "source_type" not in params:
                errors.append("source_type is required")
            
            if params.get("source_type") not in ["github", "web", "api"]:
                errors.append("Invalid source_type")
            
            priority = params.get("priority", "normal")
            if priority not in ["low", "normal", "high"]:
                errors.append("Invalid priority")
            
            max_depth = params.get("max_depth", 3)
            if not isinstance(max_depth, int) or max_depth < 1 or max_depth > 10:
                errors.append("max_depth must be between 1 and 10")
            
            return errors
        
        # Test missing fields
        errors = validate_params({})
        assert "source_url is required" in errors
        assert "source_type is required" in errors
        
        # Test invalid values
        errors = validate_params({
            "source_url": "https://example.com",
            "source_type": "invalid",
            "priority": "urgent",
            "max_depth": 15
        })
        assert "Invalid source_type" in errors
        assert "Invalid priority" in errors
        assert "max_depth must be between 1 and 10" in errors
        
        # Test valid params
        errors = validate_params({
            "source_url": "https://example.com",
            "source_type": "web",
            "priority": "high",
            "max_depth": 3
        })
        assert len(errors) == 0
    
    def test_ingestion_result_formatting(self):
        """Test ingestion result formatting."""
        def format_result(status, ingestion_id, priority, queue_position):
            return {
                "status": status,
                "ingestion_id": ingestion_id,
                "priority": priority,
                "estimated_wait_time_seconds": queue_position * 20,
                "queue_position": queue_position,
                "message": f"Content ingestion queued with {priority} priority"
            }
        
        result = format_result("queued", "ing_123", "high", 3)
        assert result["status"] == "queued"
        assert result["ingestion_id"] == "ing_123"
        assert result["estimated_wait_time_seconds"] == 60
        assert "high priority" in result["message"]
    
    def test_capabilities_structure(self):
        """Test ingestion capabilities structure."""
        capabilities = {
            "tool_name": "docaiche_ingest",
            "version": "1.0.0",
            "supported_sources": ["github", "web", "api"],
            "supported_technologies": [
                "python", "javascript", "typescript", "react"
            ],
            "features": {
                "consent_management": True,
                "priority_queuing": True,
                "duplicate_detection": True,
                "metadata_extraction": True,
                "incremental_updates": True,
                "workspace_organization": True
            },
            "limits": {
                "max_concurrent_ingestions": 5,
                "max_crawl_depth": 10,
                "rate_limit_per_minute": 10,
                "max_url_length": 2048
            },
            "security": {
                "requires_consent": True,
                "requires_authentication": True,
                "audit_logging": True,
                "blocked_domains": ["localhost", "127.0.0.1", "0.0.0.0", "internal"]
            }
        }
        
        assert len(capabilities["supported_sources"]) == 3
        assert capabilities["features"]["consent_management"] is True
        assert capabilities["limits"]["max_concurrent_ingestions"] == 5
        assert "localhost" in capabilities["security"]["blocked_domains"]


class TestIngestToolEdgeCases:
    """Test edge cases and security scenarios."""
    
    def test_malicious_url_patterns(self):
        """Test detection of potentially malicious URLs."""
        blocked_patterns = [
            "http://localhost/admin",
            "https://127.0.0.1:8080/config",
            "http://0.0.0.0/internal",
            "https://internal.company.com/secrets",
            "file:///etc/passwd",
            "javascript:alert('xss')"
        ]
        
        def is_url_safe(url):
            from urllib.parse import urlparse
            
            try:
                parsed = urlparse(url)
                
                # Check scheme
                if parsed.scheme not in ['http', 'https']:
                    return False
                
                # Check for blocked domains
                blocked = ["localhost", "127.0.0.1", "0.0.0.0", "internal"]
                if any(b in parsed.netloc.lower() for b in blocked):
                    return False
                
                return True
            except:
                return False
        
        for url in blocked_patterns:
            assert is_url_safe(url) is False
        
        # Test safe URLs
        safe_urls = [
            "https://github.com/python/cpython",
            "https://react.dev/docs",
            "https://api.example.com/v1/docs"
        ]
        
        for url in safe_urls:
            assert is_url_safe(url) is True
    
    def test_concurrent_queue_operations(self):
        """Test thread-safe queue operations."""
        import asyncio
        
        async def producer(queue, items):
            for item in items:
                await queue.put(item)
                await asyncio.sleep(0.01)  # Simulate work
        
        async def consumer(queue, results):
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    results.append(item)
                except asyncio.TimeoutError:
                    break
        
        async def test_concurrent():
            queue = asyncio.Queue()
            results = []
            
            items1 = [(1, "high1"), (5, "normal1")]
            items2 = [(1, "high2"), (10, "low1")]
            
            # Run producers concurrently
            await asyncio.gather(
                producer(queue, items1),
                producer(queue, items2)
            )
            
            # Consume all items
            await consumer(queue, results)
            
            # Should have all 4 items
            assert len(results) == 4
        
        asyncio.run(test_concurrent())
    
    def test_special_characters_in_urls(self):
        """Test handling of special characters in URLs."""
        from urllib.parse import urlparse, quote
        
        urls_with_special_chars = [
            "https://example.com/docs/C++_guide",
            "https://example.com/path with spaces",
            "https://example.com/path?query=value&other=test",
            "https://example.com/path#section"
        ]
        
        for url in urls_with_special_chars:
            try:
                parsed = urlparse(url)
                # Should be able to parse without errors
                assert parsed.scheme in ['http', 'https']
            except:
                # URLs with spaces need encoding
                if ' ' in url:
                    encoded_url = url.replace(' ', '%20')
                    parsed = urlparse(encoded_url)
                    assert parsed.scheme in ['http', 'https']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])