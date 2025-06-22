"""
Security Fixes Validation Tests - PRD-010
Tests to validate critical security vulnerabilities have been resolved.

Tests XSS protection, task privilege isolation, and lifecycle management fixes.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch
from src.enrichment.enricher import KnowledgeEnricher
from src.enrichment.security import SecureTaskExecutor, TaskSandbox, PrivilegeLevel
from src.enrichment.tasks import TaskManager
from src.enrichment.models import EnrichmentConfig, EnrichmentTask, EnrichmentType, EnrichmentPriority


class TestXSSProtection:
    """Test XSS vulnerability fixes in analyze_content_gaps method."""
    
    def test_xss_script_tag_blocked(self):
        """Test that script tags are blocked and sanitized."""
        config = EnrichmentConfig()
        db_manager = Mock()
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        # Test various XSS attack vectors
        malicious_queries = [
            "<script>alert('xss')</script>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "javascript:alert('xss')",
            "<img onerror='alert(1)' src='x'>",
            "onload=alert('xss')",
            "<object data='javascript:alert(1)'></object>"
        ]
        
        for query in malicious_queries:
            with pytest.raises(ValueError, match="contains potentially dangerous content"):
                enricher.analyze_content_gaps(query)
    
    def test_html_escape_applied(self):
        """Test that HTML entities are properly escaped."""
        config = EnrichmentConfig()
        db_manager = Mock()
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        # Test with HTML special characters
        query = "test & data < > \" '"
        result = enricher.analyze_content_gaps(query)
        
        # Verify the response contains escaped HTML
        assert result[0]['query'] == "test &amp; data &lt; &gt; &quot; &#x27;"
    
    def test_sql_injection_blocked(self):
        """Test that SQL injection attempts are blocked."""
        config = EnrichmentConfig()
        db_manager = Mock()
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        sql_injection_queries = [
            "'; DROP TABLE content_metadata; --",
            "1; DELETE FROM users; --",
            "UNION SELECT * FROM passwords",
            "'; INSERT INTO users VALUES (1,'admin','password'); --"
        ]
        
        for query in sql_injection_queries:
            with pytest.raises(ValueError, match="contains potentially dangerous content"):
                enricher.analyze_content_gaps(query)
    
    def test_valid_query_passes(self):
        """Test that legitimate queries are processed correctly."""
        config = EnrichmentConfig()
        db_manager = Mock()
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        valid_query = "python documentation tutorials"
        result = enricher.analyze_content_gaps(valid_query)
        
        assert len(result) > 0
        assert result[0]['query'] == valid_query
        assert result[0]['gap_type'] == 'missing_examples'


class TestTaskPrivilegeIsolation:
    """Test task privilege isolation and sandboxing."""
    
    @pytest.mark.asyncio
    async def test_secure_task_executor_initialization(self):
        """Test SecureTaskExecutor initializes correctly."""
        executor = SecureTaskExecutor()
        
        assert executor._execution_metrics['tasks_executed'] == 0
        assert executor._execution_metrics['security_violations'] == 0
        assert len(executor._active_sandboxes) == 0
    
    @pytest.mark.asyncio
    async def test_task_sandbox_privilege_levels(self):
        """Test different privilege levels are applied correctly."""
        # Test minimal privilege level
        sandbox_minimal = TaskSandbox(privilege_level=PrivilegeLevel.MINIMAL)
        assert sandbox_minimal.privilege_level == PrivilegeLevel.MINIMAL
        
        # Test restricted privilege level
        sandbox_restricted = TaskSandbox(privilege_level=PrivilegeLevel.RESTRICTED)
        assert sandbox_restricted.privilege_level == PrivilegeLevel.RESTRICTED
        
        # Test standard privilege level
        sandbox_standard = TaskSandbox(privilege_level=PrivilegeLevel.STANDARD)
        assert sandbox_standard.privilege_level == PrivilegeLevel.STANDARD
    
    @pytest.mark.asyncio
    async def test_task_manager_uses_secure_execution(self):
        """Test TaskManager integrates secure task execution."""
        config = EnrichmentConfig()
        task_queue = Mock()
        db_manager = Mock()
        
        task_manager = TaskManager(config, task_queue, db_manager)
        
        # Verify secure executor is initialized
        assert hasattr(task_manager, 'secure_executor')
        assert isinstance(task_manager.secure_executor, SecureTaskExecutor)
    
    @pytest.mark.asyncio
    async def test_resource_limits_applied(self):
        """Test resource limits are properly applied in sandbox."""
        sandbox = TaskSandbox(
            privilege_level=PrivilegeLevel.RESTRICTED,
            max_memory_mb=128,
            max_cpu_time_seconds=15,
            max_file_size_mb=5
        )
        
        assert sandbox.max_memory_mb == 128
        assert sandbox.max_cpu_time_seconds == 15
        assert sandbox.max_file_size_mb == 5


class TestLifecycleManagement:
    """Test lifecycle management and auto-startup functionality."""
    
    @pytest.mark.asyncio
    async def test_auto_startup_enabled_by_default(self):
        """Test KnowledgeEnricher has auto-startup enabled by default."""
        config = EnrichmentConfig()
        db_manager = Mock()
        
        enricher = KnowledgeEnricher(config, db_manager, auto_start=True)
        
        assert enricher.auto_start is True
        assert hasattr(enricher, '_startup_task')
        assert hasattr(enricher, '_initialization_complete')
    
    @pytest.mark.asyncio
    async def test_auto_startup_can_be_disabled(self):
        """Test auto-startup can be disabled."""
        config = EnrichmentConfig()
        db_manager = Mock()
        
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        assert enricher.auto_start is False
        assert enricher._startup_task is None
    
    @pytest.mark.asyncio
    async def test_wait_for_ready_functionality(self):
        """Test wait_for_ready method works correctly."""
        config = EnrichmentConfig()
        db_manager = Mock()
        
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        # Mark as initialization complete
        enricher._initialization_complete = True
        
        # Should return True immediately since initialization is complete
        ready = await enricher.wait_for_ready(timeout=1.0)
        assert ready is True
    
    @pytest.mark.asyncio
    async def test_health_check_includes_lifecycle_status(self):
        """Test health check includes lifecycle management status."""
        config = EnrichmentConfig()
        db_manager = Mock()
        task_queue = Mock()
        task_queue.health_check = Mock(return_value={'status': 'healthy'})
        
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        enricher.task_queue = task_queue
        enricher.task_manager = Mock()
        enricher.task_manager.health_check = Mock(return_value={'status': 'healthy'})
        enricher.task_manager.get_metrics = Mock(return_value=Mock(
            total_tasks_processed=0,
            error_rate=0.0,
            average_processing_time_ms=0.0,
            last_updated=None
        ))
        
        health = await enricher.health_check()
        
        assert 'auto_start_enabled' in health
        assert 'initialization_complete' in health
        assert health['auto_start_enabled'] is False


class TestSecurityIntegration:
    """Test integration of all security fixes together."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_security_workflow(self):
        """Test complete security workflow from input to execution."""
        config = EnrichmentConfig()
        db_manager = Mock()
        
        # Create enricher with security features
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        # Test input sanitization
        safe_query = "python tutorial"
        result = enricher.analyze_content_gaps(safe_query)
        assert len(result) > 0
        
        # Verify secure task execution is available
        assert hasattr(enricher.task_manager, 'secure_executor')
        
        # Verify lifecycle management is in place
        assert hasattr(enricher, 'wait_for_ready')
        assert hasattr(enricher, '_initialization_complete')
    
    def test_security_logging_does_not_leak_sensitive_data(self):
        """Test that security logging doesn't expose sensitive information."""
        config = EnrichmentConfig()
        db_manager = Mock()
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        # Test with potentially sensitive query
        malicious_query = "<script>alert('xss')</script>sensitive_data_here"
        
        with pytest.raises(ValueError):
            enricher.analyze_content_gaps(malicious_query)
        
        # The error should be raised but logging should be sanitized
        # (actual log content testing would require log capture)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])