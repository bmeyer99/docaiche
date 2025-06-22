"""
Knowledge Enrichment System - PRD-010
Complete enrichment pipeline for background knowledge enhancement.

Provides content analysis, relationship mapping, tag generation,
and quality improvement capabilities as specified in PRD-010.
"""

# Core enrichment components
from .enricher import KnowledgeEnricher
from .tasks import TaskManager
from .queue import EnrichmentTaskQueue, EnrichmentQueue

# Analysis components
from .analyzers import ContentAnalyzer, RelationshipAnalyzer, TagGenerator

# Data models
from .models import (
    EnrichmentTask, EnrichmentResult, EnrichmentConfig,
    EnrichmentMetrics, EnrichmentAnalytics, TaskQueueStatus,
    ContentRelationship, EnrichmentType, EnrichmentPriority,
    TaskStatus
)

# Exceptions
from .exceptions import (
    EnrichmentError, TaskProcessingError, AnalysisError,
    RelationshipMappingError, EnrichmentTimeoutError,
    QueueError, TagGenerationError, QualityAssessmentError,
    MetadataEnhancementError
)

# Factory functions
from .factory import (
    create_knowledge_enricher, create_task_manager,
    create_enrichment_config
)

__all__ = [
    # Core components
    "KnowledgeEnricher",
    "TaskManager", 
    "EnrichmentTaskQueue",
    "EnrichmentQueue",
    
    # Analysis components
    "ContentAnalyzer",
    "RelationshipAnalyzer", 
    "TagGenerator",
    
    # Data models
    "EnrichmentTask",
    "EnrichmentResult",
    "EnrichmentConfig",
    "EnrichmentMetrics",
    "EnrichmentAnalytics",
    "TaskQueueStatus",
    "ContentRelationship",
    "EnrichmentType",
    "EnrichmentPriority", 
    "TaskStatus",
    
    # Exceptions
    "EnrichmentError",
    "TaskProcessingError",
    "AnalysisError",
    "RelationshipMappingError",
    "EnrichmentTimeoutError",
    "QueueError",
    "TagGenerationError",
    "QualityAssessmentError",
    "MetadataEnhancementError",
    
    # Factory functions
    "create_knowledge_enricher",
    "create_task_manager",
    "create_enrichment_config"
]