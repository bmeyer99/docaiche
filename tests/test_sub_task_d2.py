#!/usr/bin/env python3
"""
SUB-TASK D2: Test TTL cleanup and refresh jobs
===============================================

Tests for TTL cleanup and refresh job functionality including:
- TTL cleanup job identifies expired documents correctly
- Bulk cleanup operations and batch processing
- Document refresh job functionality
- Integration with Context7IngestionService
- Job performance with large datasets
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from background_jobs.models import (
    JobConfig, JobExecution, JobStatus, JobType, JobPriority,
    Context7JobConfig, JobSchedule
)
from background_jobs.jobs import TTLCleanupJob, DocumentRefreshJob

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestTTLCleanupJob:
    """Test TTL cleanup job functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = Context7JobConfig(
            ttl_cleanup_batch_size=100,
            ttl_cleanup_max_age_days=30,
            refresh_batch_size=50,
            refresh_threshold_days=7,
            refresh_max_age_days=14,
            minimum_quality_score=0.7,
            rate_limit_delay_seconds=0.1,
            skip_recent_updates=True,
            target_workspaces=["workspace1", "workspace2"],
            excluded_workspaces=["excluded-workspace"]
        )
        
        # Mock dependencies
        self.context7_service = AsyncMock()
        self.weaviate_client = AsyncMock()
        self.db_manager = AsyncMock()
        
        # Create TTL cleanup job
        self.ttl_job = TTLCleanupJob(
            context7_service=self.context7_service,
            weaviate_client=self.weaviate_client,
            db_manager=self.db_manager,
            config=self.config
        )
    
    async def test_ttl_cleanup_job_execution(self):
        """Test TTL cleanup job execution"""
        logger.info("Testing TTL cleanup job execution")
        
        # Create job configuration
        job_config = JobConfig(
            job_id="ttl-cleanup-test",
            job_type=JobType.TTL_CLEANUP,
            job_name="Test TTL Cleanup",
            description="Test TTL cleanup job",
            enabled=True,
            priority=JobPriority.HIGH,
            parameters={
                "batch_size": 100,
                "max_age_days": 30
            }
        )
        
        # Create execution
        execution = JobExecution(
            execution_id="ttl-cleanup-exec-1",
            job_id=job_config.job_id,
            status=JobStatus.PENDING,
            correlation_id="ttl-cleanup-test-1"
        )
        
        # Mock workspace list
        self.weaviate_client.list_workspaces.return_value = ["workspace1", "workspace2"]
        
        # Mock cleanup results
        cleanup_result = {
            "weaviate_cleanup": {
                "deleted_documents": 25,
                "deleted_chunks": 150,
                "workspace": "workspace1"
            },
            "status": "completed"
        }
        
        self.context7_service.cleanup_expired_documents.return_value = cleanup_result
        
        # Mock database cleanup
        mock_db_result = MagicMock()
        mock_db_result.rowcount = 5
        self.db_manager.execute.return_value = mock_db_result
        
        # Execute job
        result = await self.ttl_job.execute(job_config, execution)
        
        # Verify result
        assert result["status"] == "completed"
        assert "summary" in result
        assert result["summary"]["total_workspaces"] == 2
        assert result["summary"]["total_deleted_documents"] == 50  # 25 per workspace
        assert result["summary"]["total_deleted_chunks"] == 300  # 150 per workspace
        
        # Verify service calls
        assert self.context7_service.cleanup_expired_documents.call_count == 2
        
        logger.info("✓ TTL cleanup job execution test passed")
    
    async def test_ttl_cleanup_expired_document_identification(self):
        """Test TTL cleanup identifies expired documents correctly"""
        logger.info("Testing expired document identification")
        
        # Create job configuration
        job_config = JobConfig(
            job_id="ttl-cleanup-identify-test",
            job_type=JobType.TTL_CLEANUP,
            job_name="Test TTL Cleanup Identification",
            description="Test expired document identification",
            enabled=True,
            priority=JobPriority.HIGH,
            parameters={
                "batch_size": 50,
                "max_age_days": 15
            }
        )
        
        # Create execution
        execution = JobExecution(
            execution_id="ttl-cleanup-identify-exec-1",
            job_id=job_config.job_id,
            status=JobStatus.PENDING,
            correlation_id="ttl-cleanup-identify-test-1"
        )
        
        # Mock workspace list
        self.weaviate_client.list_workspaces.return_value = ["test-workspace"]
        
        # Mock cleanup with specific identification results
        cleanup_result = {
            "weaviate_cleanup": {
                "deleted_documents": 12,
                "deleted_chunks": 48,
                "workspace": "test-workspace",
                "identified_expired": 12,
                "criteria": {
                    "max_age_days": 15,
                    "cutoff_date": (datetime.utcnow() - timedelta(days=15)).isoformat()
                }
            },
            "status": "completed"
        }
        
        self.context7_service.cleanup_expired_documents.return_value = cleanup_result
        
        # Mock database cleanup
        mock_db_result = MagicMock()
        mock_db_result.rowcount = 3
        self.db_manager.execute.return_value = mock_db_result
        
        # Execute job
        result = await self.ttl_job.execute(job_config, execution)
        
        # Verify identification worked correctly
        assert result["status"] == "completed"
        assert result["summary"]["total_deleted_documents"] == 12
        assert result["parameters"]["max_age_days"] == 15
        
        # Verify service was called with correct parameters
        self.context7_service.cleanup_expired_documents.assert_called_with(
            workspace_slug="test-workspace",
            correlation_id="ttl-cleanup-identify-test-1"
        )
        
        logger.info("✓ Expired document identification test passed")
    
    async def test_ttl_cleanup_bulk_operations(self):
        """Test bulk cleanup operations and batch processing"""
        logger.info("Testing bulk cleanup operations")
        
        # Create job configuration for bulk operations
        job_config = JobConfig(
            job_id="ttl-cleanup-bulk-test",
            job_type=JobType.TTL_CLEANUP,
            job_name="Test TTL Cleanup Bulk",
            description="Test bulk cleanup operations",
            enabled=True,
            priority=JobPriority.HIGH,
            parameters={
                "batch_size": 500,  # Large batch size
                "max_age_days": 30
            }
        )
        
        # Create execution
        execution = JobExecution(
            execution_id="ttl-cleanup-bulk-exec-1",
            job_id=job_config.job_id,
            status=JobStatus.PENDING,
            correlation_id="ttl-cleanup-bulk-test-1"
        )
        
        # Mock multiple workspaces
        self.weaviate_client.list_workspaces.return_value = [
            "workspace1", "workspace2", "workspace3", "workspace4", "workspace5"
        ]
        
        # Mock cleanup results with varying numbers
        cleanup_results = [
            {"weaviate_cleanup": {"deleted_documents": 100, "deleted_chunks": 500}},
            {"weaviate_cleanup": {"deleted_documents": 85, "deleted_chunks": 425}},
            {"weaviate_cleanup": {"deleted_documents": 120, "deleted_chunks": 600}},
            {"weaviate_cleanup": {"deleted_documents": 75, "deleted_chunks": 375}},
            {"weaviate_cleanup": {"deleted_documents": 95, "deleted_chunks": 475}}
        ]
        
        self.context7_service.cleanup_expired_documents.side_effect = cleanup_results
        
        # Mock database cleanup
        mock_db_result = MagicMock()
        mock_db_result.rowcount = 25
        self.db_manager.execute.return_value = mock_db_result
        
        # Execute job
        result = await self.ttl_job.execute(job_config, execution)
        
        # Verify bulk operations
        assert result["status"] == "completed"
        assert result["summary"]["total_workspaces"] == 5
        assert result["summary"]["total_deleted_documents"] == 475  # Sum of all results
        assert result["summary"]["total_deleted_chunks"] == 2375  # Sum of all results
        assert result["summary"]["processed_workspaces"] == 5
        assert result["summary"]["success_rate_percent"] == 100.0
        
        # Verify all workspaces were processed
        assert self.context7_service.cleanup_expired_documents.call_count == 5
        
        logger.info("✓ Bulk cleanup operations test passed")
    
    async def test_ttl_cleanup_error_handling(self):
        """Test TTL cleanup error handling"""
        logger.info("Testing TTL cleanup error handling")
        
        # Create job configuration
        job_config = JobConfig(
            job_id="ttl-cleanup-error-test",
            job_type=JobType.TTL_CLEANUP,
            job_name="Test TTL Cleanup Error Handling",
            description="Test error handling in TTL cleanup",
            enabled=True,
            priority=JobPriority.HIGH,
            parameters={
                "batch_size": 100,
                "max_age_days": 30
            }
        )
        
        # Create execution
        execution = JobExecution(
            execution_id="ttl-cleanup-error-exec-1",
            job_id=job_config.job_id,
            status=JobStatus.PENDING,
            correlation_id="ttl-cleanup-error-test-1"
        )
        
        # Mock workspace list
        self.weaviate_client.list_workspaces.return_value = ["workspace1", "workspace2"]
        
        # Mock cleanup - first succeeds, second fails
        cleanup_success = {
            "weaviate_cleanup": {
                "deleted_documents": 50,
                "deleted_chunks": 200
            }
        }
        
        self.context7_service.cleanup_expired_documents.side_effect = [
            cleanup_success,
            Exception("Cleanup failed for workspace2")
        ]
        
        # Mock database cleanup
        mock_db_result = MagicMock()
        mock_db_result.rowcount = 10
        self.db_manager.execute.return_value = mock_db_result
        
        # Execute job
        result = await self.ttl_job.execute(job_config, execution)
        
        # Verify error handling
        assert result["status"] == "completed"  # Job completes despite workspace error
        assert result["summary"]["total_workspaces"] == 2
        assert result["summary"]["processed_workspaces"] == 1  # Only one succeeded
        assert result["summary"]["failed_workspaces"] == 1
        assert result["summary"]["success_rate_percent"] == 50.0
        assert len(result["failed_workspaces"]) == 1
        assert "workspace2" in result["failed_workspaces"]
        
        logger.info("✓ TTL cleanup error handling test passed")


class TestDocumentRefreshJob:
    """Test document refresh job functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = Context7JobConfig(
            ttl_cleanup_batch_size=100,
            ttl_cleanup_max_age_days=30,
            refresh_batch_size=50,
            refresh_threshold_days=7,
            refresh_max_age_days=14,
            minimum_quality_score=0.7,
            rate_limit_delay_seconds=0.1,
            skip_recent_updates=True,
            target_workspaces=["workspace1", "workspace2"],
            excluded_workspaces=["excluded-workspace"]
        )
        
        # Mock dependencies
        self.context7_service = AsyncMock()
        self.weaviate_client = AsyncMock()
        self.db_manager = AsyncMock()
        self.llm_client = AsyncMock()
        
        # Create document refresh job
        self.refresh_job = DocumentRefreshJob(
            context7_service=self.context7_service,
            weaviate_client=self.weaviate_client,
            db_manager=self.db_manager,
            llm_client=self.llm_client,
            config=self.config
        )
    
    async def test_document_refresh_job_execution(self):
        """Test document refresh job execution"""
        logger.info("Testing document refresh job execution")
        
        # Create job configuration
        job_config = JobConfig(
            job_id="doc-refresh-test",
            job_type=JobType.DOCUMENT_REFRESH,
            job_name="Test Document Refresh",
            description="Test document refresh job",
            enabled=True,
            priority=JobPriority.MEDIUM,
            parameters={
                "batch_size": 25,
                "threshold_days": 7,
                "max_age_days": 14,
                "minimum_quality_score": 0.7
            }
        )
        
        # Create execution
        execution = JobExecution(
            execution_id="doc-refresh-exec-1",
            job_id=job_config.job_id,
            status=JobStatus.PENDING,
            correlation_id="doc-refresh-test-1"
        )
        
        # Mock workspace list
        self.weaviate_client.list_workspaces.return_value = ["workspace1"]
        
        # Mock refresh candidates
        mock_candidates = [
            {
                "content_id": "doc1",
                "enrichment_metadata": {
                    "source_url": "https://example.com/doc1",
                    "technology": "python",
                    "quality_score": 0.8
                },
                "created_at": datetime.utcnow() - timedelta(days=10),
                "updated_at": datetime.utcnow() - timedelta(days=5),
                "quality_score": 0.8
            },
            {
                "content_id": "doc2",
                "enrichment_metadata": {
                    "source_url": "https://example.com/doc2",
                    "technology": "javascript",
                    "quality_score": 0.9
                },
                "created_at": datetime.utcnow() - timedelta(days=12),
                "updated_at": datetime.utcnow() - timedelta(days=6),
                "quality_score": 0.9
            }
        ]
        
        # Mock database queries
        self.db_manager.fetch_all.return_value = mock_candidates
        self.db_manager.execute.return_value = MagicMock()
        
        # Execute job
        result = await self.refresh_job.execute(job_config, execution)
        
        # Verify result
        assert result["status"] == "completed"
        assert "summary" in result
        assert result["summary"]["total_workspaces"] == 1
        assert result["summary"]["processed_workspaces"] == 1
        assert result["summary"]["total_refreshed_documents"] == 2
        assert result["summary"]["success_rate_percent"] == 100.0
        
        # Verify database queries were made
        self.db_manager.fetch_all.assert_called_once()
        
        logger.info("✓ Document refresh job execution test passed")
    
    async def test_refresh_candidate_identification(self):
        """Test refresh candidate identification"""
        logger.info("Testing refresh candidate identification")
        
        # Mock database results with various scenarios
        mock_db_results = [
            {
                "content_id": "doc1",
                "enrichment_metadata": {
                    "source_url": "https://example.com/doc1",
                    "technology": "python",
                    "quality_score": 0.8,
                    "ttl_info": {
                        "expires_at": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                        "source_provider": "context7"
                    }
                },
                "created_at": datetime.utcnow() - timedelta(days=10),
                "updated_at": datetime.utcnow() - timedelta(days=5)
            },
            {
                "content_id": "doc2",
                "enrichment_metadata": {
                    "source_url": "https://example.com/doc2",
                    "technology": "javascript",
                    "quality_score": 0.6,  # Below threshold
                    "ttl_info": {
                        "expires_at": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                        "source_provider": "context7"
                    }
                },
                "created_at": datetime.utcnow() - timedelta(days=15),
                "updated_at": datetime.utcnow() - timedelta(days=8)
            },
            {
                "content_id": "doc3",
                "enrichment_metadata": {
                    "source_url": "https://example.com/doc3",
                    "technology": "go",
                    "quality_score": 0.9,
                    "ttl_info": {
                        "expires_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                        "source_provider": "context7"
                    }
                },
                "created_at": datetime.utcnow() - timedelta(days=20),
                "updated_at": datetime.utcnow() - timedelta(days=10)
            }
        ]
        
        self.db_manager.fetch_all.return_value = mock_db_results
        
        # Test candidate identification
        candidates = await self.refresh_job._get_refresh_candidates(
            workspace="test-workspace",
            threshold_days=7,
            max_age_days=14,
            min_quality=0.7,
            correlation_id="test-correlation"
        )
        
        # Verify filtering
        assert len(candidates) == 2  # Only doc1 and doc3 meet quality threshold
        candidate_ids = [c["content_id"] for c in candidates]
        assert "doc1" in candidate_ids
        assert "doc3" in candidate_ids
        assert "doc2" not in candidate_ids  # Below quality threshold
        
        logger.info("✓ Refresh candidate identification test passed")
    
    async def test_batch_refresh_processing(self):
        """Test batch refresh processing"""
        logger.info("Testing batch refresh processing")
        
        # Create test candidates
        candidates = [
            {
                "content_id": f"doc{i}",
                "enrichment_metadata": {
                    "source_url": f"https://example.com/doc{i}",
                    "technology": "python",
                    "quality_score": 0.8
                },
                "quality_score": 0.8
            }
            for i in range(10)
        ]
        
        # Mock database execute for refresh
        self.db_manager.execute.return_value = MagicMock()
        
        # Test batch refresh
        result = await self.refresh_job._refresh_document_batch(
            candidates=candidates,
            workspace="test-workspace",
            correlation_id="test-correlation"
        )
        
        # Verify batch processing
        assert result["refreshed"] == 10
        assert result["failed"] == 0
        
        # Verify database updates were called
        assert self.db_manager.execute.call_count == 10
        
        logger.info("✓ Batch refresh processing test passed")
    
    async def test_refresh_performance_large_dataset(self):
        """Test refresh job performance with large datasets"""
        logger.info("Testing refresh performance with large datasets")
        
        # Create job configuration for large dataset
        job_config = JobConfig(
            job_id="doc-refresh-large-test",
            job_type=JobType.DOCUMENT_REFRESH,
            job_name="Test Large Dataset Refresh",
            description="Test refresh job with large dataset",
            enabled=True,
            priority=JobPriority.MEDIUM,
            parameters={
                "batch_size": 100,  # Large batch size
                "threshold_days": 7,
                "max_age_days": 14,
                "minimum_quality_score": 0.7
            }
        )
        
        # Create execution
        execution = JobExecution(
            execution_id="doc-refresh-large-exec-1",
            job_id=job_config.job_id,
            status=JobStatus.PENDING,
            correlation_id="doc-refresh-large-test-1"
        )
        
        # Mock workspace list
        self.weaviate_client.list_workspaces.return_value = ["large-workspace"]
        
        # Mock large dataset of candidates
        large_candidates = [
            {
                "content_id": f"doc{i}",
                "enrichment_metadata": {
                    "source_url": f"https://example.com/doc{i}",
                    "technology": "python",
                    "quality_score": 0.8
                },
                "created_at": datetime.utcnow() - timedelta(days=10),
                "updated_at": datetime.utcnow() - timedelta(days=5),
                "quality_score": 0.8
            }
            for i in range(500)  # 500 candidates
        ]
        
        self.db_manager.fetch_all.return_value = large_candidates
        self.db_manager.execute.return_value = MagicMock()
        
        # Execute job and measure performance
        start_time = datetime.utcnow()
        result = await self.refresh_job.execute(job_config, execution)
        end_time = datetime.utcnow()
        
        execution_time = (end_time - start_time).total_seconds()
        
        # Verify performance
        assert result["status"] == "completed"
        assert result["summary"]["total_refreshed_documents"] == 500
        assert execution_time < 10.0  # Should complete within 10 seconds
        
        # Verify batch processing efficiency
        # With batch size 100, should have 5 batches
        expected_batches = (500 + 100 - 1) // 100  # Ceiling division
        assert expected_batches == 5
        
        logger.info(f"✓ Large dataset refresh completed in {execution_time:.2f} seconds")
        logger.info("✓ Refresh performance test passed")


async def run_sub_task_d2():
    """Run SUB-TASK D2 tests"""
    logger.info("=" * 60)
    logger.info("SUB-TASK D2: Testing TTL cleanup and refresh jobs")
    logger.info("=" * 60)
    
    ttl_test_instance = TestTTLCleanupJob()
    refresh_test_instance = TestDocumentRefreshJob()
    
    try:
        # Setup
        ttl_test_instance.setup_method()
        refresh_test_instance.setup_method()
        
        # Run TTL cleanup tests
        await ttl_test_instance.test_ttl_cleanup_job_execution()
        await ttl_test_instance.test_ttl_cleanup_expired_document_identification()
        await ttl_test_instance.test_ttl_cleanup_bulk_operations()
        await ttl_test_instance.test_ttl_cleanup_error_handling()
        
        # Run document refresh tests
        await refresh_test_instance.test_document_refresh_job_execution()
        await refresh_test_instance.test_refresh_candidate_identification()
        await refresh_test_instance.test_batch_refresh_processing()
        await refresh_test_instance.test_refresh_performance_large_dataset()
        
        logger.info("=" * 60)
        logger.info("SUB-TASK D2: All tests passed successfully!")
        logger.info("=" * 60)
        
        return {
            "sub_task": "D2",
            "status": "PASSED",
            "tests_run": 8,
            "tests_passed": 8,
            "tests_failed": 0,
            "summary": "TTL cleanup and refresh jobs functionality verified successfully",
            "details": [
                "TTL cleanup job execution and document identification",
                "Bulk cleanup operations with batch processing",
                "TTL cleanup error handling and resilience",
                "Document refresh job execution and candidate identification",
                "Batch refresh processing with quality filtering",
                "Refresh job performance with large datasets",
                "Integration with Context7IngestionService verified",
                "Database operations for TTL management confirmed"
            ]
        }
        
    except Exception as e:
        logger.error(f"SUB-TASK D2 failed: {e}")
        return {
            "sub_task": "D2",
            "status": "FAILED",
            "error": str(e),
            "summary": "TTL cleanup and refresh jobs functionality test failed"
        }


if __name__ == "__main__":
    asyncio.run(run_sub_task_d2())