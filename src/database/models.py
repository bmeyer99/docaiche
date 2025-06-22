"""
SQLAlchemy 2.0 Async ORM Models - PRD-002 DB-001
Defines all database models matching the exact schema from task requirements

These models provide the ORM layer for all database tables using
SQLAlchemy 2.0 async patterns with proper type hints and constraints.
"""

import logging
from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, JSON,
    CheckConstraint, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all SQLAlchemy models using async patterns.
    
    Provides common async capabilities and consistent patterns
    across all database models.
    """
    pass


class SystemConfig(Base):
    """
    System configuration table for storing runtime configuration.
    
    Maps to system_config table from task requirements.
    """
    __tablename__ = "system_config"
    
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    updated_by: Mapped[str] = mapped_column(String, nullable=False, default="system")


class SearchCache(Base):
    """
    Search cache table for caching search queries and results.
    
    Maps to search_cache table from task requirements.
    """
    __tablename__ = "search_cache"
    
    query_hash: Mapped[str] = mapped_column(String, primary_key=True)
    original_query: Mapped[str] = mapped_column(String, nullable=False)
    search_results: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    technology_hint: Mapped[Optional[str]] = mapped_column(String)
    workspace_slugs: Mapped[Optional[List[str]]] = mapped_column(JSON)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    
    # Indexes as specified in task requirements
    __table_args__ = (
        Index("idx_search_cache_expires_at", "expires_at"),
        Index("idx_search_cache_technology_hint", "technology_hint"),
        Index("idx_search_cache_created_at", "created_at"),
    )


class ContentMetadata(Base):
    """
    Content metadata table for tracking ingested content.
    
    Maps to content_metadata table from task requirements.
    """
    __tablename__ = "content_metadata"
    
    content_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    technology: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heading_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_block_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    processing_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    anythingllm_workspace: Mapped[Optional[str]] = mapped_column(String)
    anythingllm_document_id: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Relationships
    feedback_events: Mapped[List["FeedbackEvents"]] = relationship(
        "FeedbackEvents", back_populates="content", cascade="all, delete-orphan"
    )
    usage_signals: Mapped[List["UsageSignals"]] = relationship(
        "UsageSignals", back_populates="content", cascade="all, delete-orphan"
    )
    
    # Constraints and indexes as specified in task requirements
    __table_args__ = (
        CheckConstraint("quality_score >= 0.0 AND quality_score <= 1.0"),
        CheckConstraint("freshness_score >= 0.0 AND freshness_score <= 1.0"),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed', 'flagged')"
        ),
        Index("idx_content_metadata_technology", "technology"),
        Index("idx_content_metadata_source_url", "source_url"),
        Index("idx_content_metadata_content_hash", "content_hash"),
        Index("idx_content_metadata_quality_score", "quality_score"),
        Index("idx_content_metadata_processing_status", "processing_status"),
        Index("idx_content_metadata_created_at", "created_at"),
        Index("idx_content_metadata_last_accessed_at", "last_accessed_at"),
    )


class FeedbackEvents(Base):
    """
    Feedback events table for storing explicit user feedback.
    
    Maps to feedback_events table from task requirements.
    """
    __tablename__ = "feedback_events"
    
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    content_id: Mapped[str] = mapped_column(
        String, ForeignKey("content_metadata.content_id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    user_session_id: Mapped[Optional[str]] = mapped_column(String)
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    user_agent: Mapped[Optional[str]] = mapped_column(String)
    search_query: Mapped[Optional[str]] = mapped_column(String)
    result_position: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    
    # Relationship
    content: Mapped["ContentMetadata"] = relationship(
        "ContentMetadata", back_populates="feedback_events"
    )
    
    # Constraints and indexes as specified in task requirements
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('helpful', 'not_helpful', 'outdated', 'incorrect', 'flag')"
        ),
        CheckConstraint("rating >= 1 AND rating <= 5"),
        Index("idx_feedback_events_content_id", "content_id"),
        Index("idx_feedback_events_feedback_type", "feedback_type"),
        Index("idx_feedback_events_created_at", "created_at"),
        Index("idx_feedback_events_user_session_id", "user_session_id"),
    )


class UsageSignals(Base):
    """
    Usage signals table for tracking implicit user interactions.
    
    Maps to usage_signals table from task requirements.
    """
    __tablename__ = "usage_signals"
    
    signal_id: Mapped[str] = mapped_column(String, primary_key=True)
    content_id: Mapped[str] = mapped_column(
        String, ForeignKey("content_metadata.content_id", ondelete="CASCADE"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(String, nullable=False)
    signal_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    search_query: Mapped[Optional[str]] = mapped_column(String)
    result_position: Mapped[Optional[int]] = mapped_column(Integer)
    user_session_id: Mapped[Optional[str]] = mapped_column(String)
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    user_agent: Mapped[Optional[str]] = mapped_column(String)
    referrer: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    
    # Relationship
    content: Mapped["ContentMetadata"] = relationship(
        "ContentMetadata", back_populates="usage_signals"
    )
    
    # Constraints and indexes as specified in task requirements
    __table_args__ = (
        CheckConstraint(
            "signal_type IN ('click', 'dwell_time', 'copy', 'share', 'scroll_depth')"
        ),
        Index("idx_usage_signals_content_id", "content_id"),
        Index("idx_usage_signals_signal_type", "signal_type"),
        Index("idx_usage_signals_created_at", "created_at"),
        Index("idx_usage_signals_user_session_id", "user_session_id"),
    )


class SourceMetadata(Base):
    """
    Source metadata table for tracking source reliability and performance.
    
    Maps to source_metadata table from task requirements.
    """
    __tablename__ = "source_metadata"
    
    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    technology: Mapped[str] = mapped_column(String, nullable=False)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    avg_processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_documents_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_successful_fetch: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_failed_fetch: Mapped[Optional[datetime]] = mapped_column(DateTime)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rate_limit_status: Mapped[str] = mapped_column(String, default="normal")
    rate_limit_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    avg_content_quality: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    
    # Constraints and indexes as specified in task requirements
    __table_args__ = (
        CheckConstraint("source_type IN ('github', 'web', 'api')"),
        CheckConstraint("reliability_score >= 0.0 AND reliability_score <= 1.0"),
        CheckConstraint(
            "rate_limit_status IN ('normal', 'limited', 'exhausted')"
        ),
        CheckConstraint("avg_content_quality >= 0.0 AND avg_content_quality <= 1.0"),
        Index("idx_source_metadata_source_type", "source_type"),
        Index("idx_source_metadata_technology", "technology"),
        Index("idx_source_metadata_reliability_score", "reliability_score"),
        Index("idx_source_metadata_is_active", "is_active"),
        Index("idx_source_metadata_updated_at", "updated_at"),
    )


class TechnologyMappings(Base):
    """
    Technology mappings table for mapping technologies to authoritative sources.
    
    Maps to technology_mappings table from task requirements.
    """
    __tablename__ = "technology_mappings"
    
    mapping_id: Mapped[str] = mapped_column(String, primary_key=True)
    technology: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[Optional[str]] = mapped_column(String)
    repo: Mapped[Optional[str]] = mapped_column(String)
    docs_path: Mapped[str] = mapped_column(String, nullable=False, default="docs")
    file_patterns: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=lambda: ["*.md", "*.mdx"]
    )
    base_url: Mapped[Optional[str]] = mapped_column(String)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    update_frequency_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    
    # Constraints and indexes as specified in task requirements
    __table_args__ = (
        CheckConstraint("source_type IN ('github', 'web')"),
        UniqueConstraint(
            "technology", "source_type", "owner", "repo", "base_url",
            name="uq_technology_source_mapping"
        ),
        Index("idx_technology_mappings_technology", "technology"),
        Index("idx_technology_mappings_source_type", "source_type"),
        Index("idx_technology_mappings_priority", "priority"),
        Index("idx_technology_mappings_is_active", "is_active"),
        Index("idx_technology_mappings_is_official", "is_official"),
    )


# Note: Schema versioning is handled by Alembic as per PRD-002
# No custom schema_versions table needed - removed to match exact 7-table requirement