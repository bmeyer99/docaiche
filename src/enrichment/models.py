"""
Enrichment Data Models - PRD-010
Pydantic models for knowledge enrichment operations and task management.

Defines the exact data structures specified in PRD-010 for enrichment
tasks, results, and metadata management.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EnrichmentPriority(str, Enum):
    """Enrichment task priority levels as specified in PRD-010"""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class EnrichmentType(str, Enum):
    """Types of enrichment operations as specified in PRD-010"""
    CONTENT_ANALYSIS = "content_analysis"
    RELATIONSHIP_MAPPING = "relationship_mapping"
    TAG_GENERATION = "tag_generation"
    QUALITY_ASSESSMENT = "quality_assessment"
    METADATA_ENHANCEMENT = "metadata_enhancement"


class EnrichmentStrategy(str, Enum):
    """Enrichment strategies for API compatibility - alias for EnrichmentType"""
    CONTENT_GAP_ANALYSIS = "content_analysis"
    RELATIONSHIP_MAPPING = "relationship_mapping"
    TAG_GENERATION = "tag_generation"
    QUALITY_ASSESSMENT = "quality_assessment"
    METADATA_ENHANCEMENT = "metadata_enhancement"


class TaskPriority(str, Enum):
    """Task priority levels - alias for EnrichmentPriority for API compatibility"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "normal"  # Map MEDIUM to NORMAL for compatibility
    NORMAL = "normal"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentRelationship(BaseModel):
    """
    Content relationship model for document connections.
    
    Represents relationships between documents identified during enrichment.
    """
    source_content_id: str = Field(..., description="Source document ID")
    target_content_id: str = Field(..., description="Target document ID")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Relationship confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional relationship metadata")


class EnrichmentTask(BaseModel):
    """
    Enrichment task model for background processing queue.
    
    Implements exact EnrichmentTask structure from PRD-010 with all specified fields.
    """
    content_id: str = Field(..., description="Content ID to enrich")
    priority: EnrichmentPriority = Field(EnrichmentPriority.NORMAL, description="Task priority")
    task_type: EnrichmentType = Field(..., description="Type of enrichment to perform")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation timestamp")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Current task status")
    started_at: Optional[datetime] = Field(None, description="Task processing start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum retry attempts")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional task context")


class EnrichmentResult(BaseModel):
    """
    Enrichment processing result model.
    
    Implements exact EnrichmentResult structure from PRD-010 with all enhancement outputs.
    """
    content_id: str = Field(..., description="Content ID that was enriched")
    enhanced_tags: List[str] = Field(default_factory=list, description="Generated tags")
    relationships: List[ContentRelationship] = Field(default_factory=list, description="Identified relationships")
    quality_improvements: Dict[str, Any] = Field(default_factory=dict, description="Quality enhancements")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in enrichment")
    enrichment_metadata: Dict[str, Any] = Field(default_factory=dict, description="Enrichment metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Result creation timestamp")


class EnrichmentMetrics(BaseModel):
    """
    Enrichment system performance metrics.
    
    Tracks enrichment operation statistics for monitoring and optimization.
    """
    total_tasks_processed: int = Field(0, description="Total tasks processed")
    successful_tasks: int = Field(0, description="Successfully completed tasks")
    failed_tasks: int = Field(0, description="Failed tasks")
    average_processing_time_ms: float = Field(0.0, description="Average processing time")
    tasks_by_priority: Dict[str, int] = Field(default_factory=dict, description="Task count by priority")
    tasks_by_type: Dict[str, int] = Field(default_factory=dict, description="Task count by type")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Error rate percentage")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Metrics last update time")


class EnrichmentConfig(BaseModel):
    """
    Enrichment system configuration model.
    
    Configuration parameters for enrichment processing behavior.
    """
    max_concurrent_tasks: int = Field(5, ge=1, le=20, description="Maximum concurrent enrichment tasks")
    task_timeout_seconds: int = Field(300, ge=30, description="Task timeout in seconds")
    retry_delay_seconds: int = Field(60, ge=1, description="Delay between retries")
    queue_poll_interval: int = Field(10, ge=1, description="Queue polling interval in seconds")
    batch_size: int = Field(10, ge=1, le=100, description="Batch processing size")
    enable_relationship_mapping: bool = Field(True, description="Enable relationship mapping")
    enable_tag_generation: bool = Field(True, description="Enable automatic tag generation")
    enable_quality_assessment: bool = Field(True, description="Enable quality assessment")
    min_confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")


class TaskQueueStatus(BaseModel):
    """
    Task queue status model for monitoring.
    
    Provides queue statistics and operational status.
    """
    pending_tasks: int = Field(0, description="Number of pending tasks")
    processing_tasks: int = Field(0, description="Number of currently processing tasks")
    queue_size: int = Field(0, description="Total queue size")
    oldest_pending_task: Optional[datetime] = Field(None, description="Timestamp of oldest pending task")
    queue_health: str = Field("healthy", description="Queue health status")
    last_processed_task: Optional[datetime] = Field(None, description="Last task processing time")


class ContentGap(BaseModel):
    """
    Content gap model for gap analysis results.
    
    Represents identified gaps in content coverage.
    """
    query: str = Field(..., description="Query that identified the gap")
    gap_type: str = Field(..., description="Type of content gap")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in gap identification")
    suggested_sources: List[str] = Field(default_factory=list, description="Suggested sources to fill gap")
    priority: str = Field("medium", description="Gap priority level")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional gap metadata")


class RelationshipType(str, Enum):
    """Relationship types for content connections"""
    SIMILAR = "similar"
    RELATED = "related"
    DUPLICATE = "duplicate"
    REFERENCE = "reference"
    PREREQUISITE = "prerequisite"
    FOLLOW_UP = "follow_up"


class KnowledgeGraph(BaseModel):
    """
    Knowledge graph model for content relationships.
    
    Represents the relationship graph between content items.
    """
    content_id: str = Field(..., description="Content ID")
    related_content: List[ContentRelationship] = Field(default_factory=list, description="Related content items")
    topics: List[str] = Field(default_factory=list, description="Content topics")
    concepts: List[str] = Field(default_factory=list, description="Key concepts")
    complexity_score: float = Field(0.0, ge=0.0, le=1.0, description="Content complexity score")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Graph creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class EnrichmentAnalytics(BaseModel):
    """
    Analytics data for enrichment operations.
    
    Detailed analytics for performance monitoring and optimization.
    """
    period_start: datetime = Field(..., description="Analytics period start")
    period_end: datetime = Field(..., description="Analytics period end")
    total_content_enriched: int = Field(0, description="Total content items enriched")
    tags_generated: int = Field(0, description="Total tags generated")
    relationships_identified: int = Field(0, description="Total relationships identified")
    average_quality_improvement: float = Field(0.0, description="Average quality score improvement")
    processing_efficiency: float = Field(0.0, description="Processing efficiency metric")
    error_patterns: Dict[str, int] = Field(default_factory=dict, description="Error pattern analysis")
    performance_trends: Dict[str, List[float]] = Field(default_factory=dict, description="Performance trend data")