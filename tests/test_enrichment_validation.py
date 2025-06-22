"""
PRD-010 Enrichment System Validation
Basic tests to validate enrichment system implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.enrichment import (
    KnowledgeEnricher, EnrichmentConfig, EnrichmentTask,
    EnrichmentType, EnrichmentPriority, TaskStatus,
    create_knowledge_enricher, create_enrichment_config
)


class TestEnrichmentConfig:
    """Test enrichment configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = EnrichmentConfig()
        
        assert config.max_concurrent_tasks == 5
        assert config.task_timeout_seconds == 300
        assert config.enable_relationship_mapping is True
        assert config.enable_tag_generation is True
        assert config.min_confidence_threshold == 0.7
    
    def test_factory_config(self):
        """Test factory configuration creation."""
        config = create_enrichment_config(
            max_concurrent_tasks=10,
            enable_relationship_mapping=False
        )
        
        assert config.max_concurrent_tasks == 10
        assert config.enable_relationship_mapping is False


class TestEnrichmentTask:
    """Test enrichment task model."""
    
    def test_task_creation(self):
        """Test enrichment task creation."""
        task = EnrichmentTask(
            content_id="test-content-123",
            task_type=EnrichmentType.CONTENT_ANALYSIS,
            priority=EnrichmentPriority.HIGH
        )
        
        assert task.content_id == "test-content-123"
        assert task.task_type == EnrichmentType.CONTENT_ANALYSIS
        assert task.priority == EnrichmentPriority.HIGH
        assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
class TestKnowledgeEnricher:
    """Test knowledge enricher functionality."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager."""
        return Mock()
    
    @pytest.fixture
    def enricher(self, mock_db_manager):
        """Create knowledge enricher with mocks."""
        config = EnrichmentConfig()
        return KnowledgeEnricher(config, mock_db_manager)
    
    async def test_enricher_creation(self, enricher):
        """Test enricher creation."""
        assert enricher is not None
        assert isinstance(enricher.config, EnrichmentConfig)
        assert not enricher._running
    
    async def test_enricher_start_stop(self, enricher):
        """Test enricher start/stop lifecycle."""
        # Mock the task manager start method
        enricher.task_manager.start = AsyncMock()
        enricher.task_manager.stop = AsyncMock()
        
        await enricher.start()
        assert enricher._running
        
        await enricher.stop()
        assert not enricher._running
    
    async def test_enrich_content_not_running(self, enricher):
        """Test content enrichment when not running."""
        with pytest.raises(Exception):
            await enricher.enrich_content("test-content")


class TestFactoryFunctions:
    """Test factory functions."""
    
    @pytest.mark.asyncio
    async def test_create_knowledge_enricher(self):
        """Test knowledge enricher factory."""
        # Mock database manager creation
        with pytest.raises(Exception):
            # This will fail because we don't have a real database
            # but it validates the factory function exists and is callable
            await create_knowledge_enricher()


def test_enrichment_imports():
    """Test that all enrichment components can be imported."""
    from src.enrichment import (
        KnowledgeEnricher, TaskManager, EnrichmentTaskQueue,
        ContentAnalyzer, RelationshipAnalyzer, TagGenerator,
        EnrichmentTask, EnrichmentResult, EnrichmentConfig,
        EnrichmentType, EnrichmentPriority, TaskStatus,
        EnrichmentError, TaskProcessingError
    )
    
    # Verify classes exist
    assert KnowledgeEnricher is not None
    assert TaskManager is not None
    assert EnrichmentTaskQueue is not None
    assert ContentAnalyzer is not None
    assert RelationshipAnalyzer is not None
    assert TagGenerator is not None
    
    # Verify models exist
    assert EnrichmentTask is not None
    assert EnrichmentResult is not None
    assert EnrichmentConfig is not None
    
    # Verify enums exist
    assert EnrichmentType is not None
    assert EnrichmentPriority is not None
    assert TaskStatus is not None
    
    # Verify exceptions exist
    assert EnrichmentError is not None
    assert TaskProcessingError is not None