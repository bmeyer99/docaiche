"""
Knowledge Enrichment System - PRD-010
Complete enrichment pipeline for background knowledge enhancement.

Provides content analysis, relationship mapping, tag generation,
and quality improvement capabilities as specified in PRD-010.
"""

# Core enrichment components
from .enricher import KnowledgeEnricher
from .tasks import TaskManager
from .queue import EnrichmentTaskQueue

# Analysis components
from .analyzers import GapAnalyzer

# Data models
from .models import EnrichmentTask, EnrichmentStatus, GapAnalysisResult

# Exceptions
from .exceptions import (
    EnrichmentException,
    GapAnalysisException,
    ContentAcquisitionException,
    BackgroundTaskException,
)

# Factory functions
from .factory import (
    create_knowledge_enricher,
    create_task_manager,
    create_enrichment_config,
    create_enrichment_queue,
    create_knowledge_enricher_with_integrated_config,
    create_task_manager_with_integrated_config,
)

# Configuration integration
from .config import (
    EnrichmentConfigManager,
    get_enrichment_config,
    reload_enrichment_config,
    register_config_reload_callback,
    validate_enrichment_config,
    get_config_manager_status,
)

__all__ = [
    # Core components
    "KnowledgeEnricher",
    "TaskManager",
    "EnrichmentTaskQueue",
    # Analysis components
    "GapAnalyzer",
    # Data models
    "EnrichmentTask",
    "EnrichmentStatus",
    "GapAnalysisResult",
    # Exceptions
    "EnrichmentException",
    "GapAnalysisException",
    "ContentAcquisitionException",
    "BackgroundTaskException",
    # Factory functions
    "create_knowledge_enricher",
    "create_task_manager",
    "create_enrichment_config",
    "create_enrichment_queue",
    "create_knowledge_enricher_with_integrated_config",
    "create_task_manager_with_integrated_config",
    # Configuration integration
    "EnrichmentConfigManager",
    "get_enrichment_config",
    "reload_enrichment_config",
    "register_config_reload_callback",
    "validate_enrichment_config",
    "get_config_manager_status",
]
