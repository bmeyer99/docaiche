"""
Enrichment Models - PRD-010
Complete data models for the enrichment system.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class EnrichmentStatus(str, Enum):
    """Enrichment task status states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EnrichmentType(str, Enum):
    """Types of enrichment operations"""
    CONTENT_ANALYSIS = "content_analysis"
    RELATIONSHIP_MAPPING = "relationship_mapping"
    TAG_GENERATION = "tag_generation"
    QUALITY_ASSESSMENT = "quality_assessment"
    METADATA_ENHANCEMENT = "metadata_enhancement"


class EnrichmentPriority(str, Enum):
    """Enrichment task priority levels"""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnrichmentTask(BaseModel):
    """
    Data model representing an enrichment task for background processing.
    """
    task_id: str = Field(..., description="Unique identifier for the enrichment task")
    content_id: str = Field(..., description="ID of the content to enrich")
    task_type: EnrichmentType = Field(default=EnrichmentType.CONTENT_ANALYSIS, description="Type of enrichment task")
    priority: EnrichmentPriority = Field(default=EnrichmentPriority.NORMAL, description="Task priority level")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status of the enrichment task")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters for enrichment")
    created_at: Optional[datetime] = Field(None, description="Task creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Task last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if task failed")


class GapAnalysisResult(BaseModel):
    """
    Data model representing the result of a gap analysis operation.
    """
    content_id: str = Field(..., description="ID of the content analyzed")
    missing_topics: List[str] = Field(default_factory=list, description="List of missing or insufficiently covered topics")
    outdated_sections: List[str] = Field(default_factory=list, description="List of outdated sections")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions to fill gaps")
    confidence_score: float = Field(default=0.0, description="Confidence score for gap analysis")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata for gap analysis result")


class EnrichmentResult(BaseModel):
    """
    Data model representing the result of an enrichment operation.
    """
    task_id: str = Field(..., description="ID of the enrichment task")
    content_id: str = Field(..., description="ID of the enriched content")
    enrichment_type: EnrichmentType = Field(..., description="Type of enrichment performed")
    results: Dict[str, Any] = Field(default_factory=dict, description="Enrichment results data")
    confidence_score: float = Field(default=0.0, description="Confidence score for enrichment results")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata for enrichment result")
    created_at: Optional[datetime] = Field(None, description="Result creation timestamp")


class EnrichmentConfig(BaseModel):
    """
    Configuration model for enrichment operations.
    """
    max_concurrent_tasks: int = Field(default=5, description="Maximum number of concurrent enrichment tasks")
    task_timeout_seconds: int = Field(default=300, description="Task timeout in seconds")
    retry_delay_seconds: int = Field(default=60, description="Delay between retry attempts")
    queue_poll_interval: int = Field(default=10, description="Queue polling interval in seconds")
    batch_size: int = Field(default=10, description="Batch processing size")
    enable_relationship_mapping: bool = Field(default=True, description="Enable relationship mapping enrichment")
    enable_tag_generation: bool = Field(default=True, description="Enable tag generation enrichment")
    enable_quality_assessment: bool = Field(default=True, description="Enable quality assessment enrichment")
    min_confidence_threshold: float = Field(default=0.7, description="Minimum confidence threshold for results")


class QueueMetrics(BaseModel):
    """
    Metrics for enrichment task queue.
    """
    total_tasks_queued: int = Field(default=0, description="Total tasks queued")
    total_tasks_processed: int = Field(default=0, description="Total tasks processed")
    current_queue_size: int = Field(default=0, description="Current queue size")
    average_processing_time_ms: float = Field(default=0.0, description="Average processing time")
    error_rate: float = Field(default=0.0, description="Error rate percentage")
    last_updated: Optional[datetime] = Field(None, description="Last metrics update timestamp")


class TaskMetrics(BaseModel):
    """
    Metrics for task processing.
    """
    total_tasks_processed: int = Field(default=0, description="Total tasks processed")
    tasks_successful: int = Field(default=0, description="Successful tasks")
    tasks_failed: int = Field(default=0, description="Failed tasks")
    average_processing_time_ms: float = Field(default=0.0, description="Average processing time")
    error_rate: float = Field(default=0.0, description="Error rate percentage")
    last_updated: Optional[datetime] = Field(None, description="Last metrics update timestamp")