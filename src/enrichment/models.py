# src/enrichment/models.py

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class EnrichmentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class EnrichmentTask(BaseModel):
    """
    Data model representing an enrichment task for background processing.
    """
    task_id: str = Field(..., description="Unique identifier for the enrichment task")
    content_id: str = Field(..., description="ID of the content to enrich")
    status: EnrichmentStatus = Field(default=EnrichmentStatus.PENDING, description="Current status of the enrichment task")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters for enrichment")
    created_at: Optional[str] = Field(None, description="Task creation timestamp")
    updated_at: Optional[str] = Field(None, description="Task last update timestamp")

class GapAnalysisResult(BaseModel):
    """
    Data model representing the result of a gap analysis operation.
    """
    content_id: str = Field(..., description="ID of the content analyzed")
    missing_topics: List[str] = Field(default_factory=list, description="List of missing or insufficiently covered topics")
    outdated_sections: List[str] = Field(default_factory=list, description="List of outdated sections")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions to fill gaps")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata for gap analysis result")