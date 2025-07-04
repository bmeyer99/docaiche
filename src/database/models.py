"""
SQLAlchemy 2.0 Async ORM Models - PRD-002 DB-002
Defines all database models matching the exact schema from PRD-002 specification

These models provide the ORM layer for all 7 database tables using
SQLAlchemy 2.0 async patterns with proper type hints and constraints.
Also includes additional models expected by validation tests.
"""

import logging
from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import TypeDecorator
import os

logger = logging.getLogger(__name__)

# Create a custom JSON type that uses JSONB for PostgreSQL and JSON for others
class JSONType(TypeDecorator):
    """Platform-agnostic JSON type that uses JSONB on PostgreSQL."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB)
        else:
            return dialect.type_descriptor(JSON)

# Use JSONType instead of JSON in models
JSONField = JSONType


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all SQLAlchemy models using async patterns.

    Provides common async capabilities and consistent patterns
    across all database models.
    """

    pass


# PRD-002 Exact Schema Models (7 tables)


class SystemConfig(Base):
    """System configuration table - PRD-002 lines 34-40"""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSONField, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    updated_by: Mapped[str] = mapped_column(String, nullable=False, default="system")

    __table_args__ = ()


class ConfigurationAuditLog(Base):
    """Configuration change audit log table"""
    
    __tablename__ = "configuration_audit_log"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    user: Mapped[str] = mapped_column(String, nullable=False)
    section: Mapped[str] = mapped_column(String, nullable=False)
    changes: Mapped[Dict[str, Any]] = mapped_column(JSONField, nullable=False)
    previous_values: Mapped[Dict[str, Any]] = mapped_column(JSONField, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    __table_args__ = (
        Index("idx_config_audit_timestamp", "timestamp"),
        Index("idx_config_audit_user", "user"),
        Index("idx_config_audit_section", "section"),
    )


class SearchCache(Base):
    """Search cache table - PRD-002 lines 43-56"""

    __tablename__ = "search_cache"

    query_hash: Mapped[str] = mapped_column(String, primary_key=True)
    original_query: Mapped[str] = mapped_column(String, nullable=False)
    search_results: Mapped[Dict[str, Any]] = mapped_column(JSONField, nullable=False)
    technology_hint: Mapped[Optional[str]] = mapped_column(String)
    workspace_slugs: Mapped[Optional[List[str]]] = mapped_column(JSONField)
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

    __table_args__ = (
        Index("idx_search_cache_expires_at", "expires_at"),
        Index("idx_search_cache_technology_hint", "technology_hint"),
        Index("idx_search_cache_created_at", "created_at"),
    )


class ContentMetadata(Base):
    """Content metadata table - PRD-002 lines 59-78"""

    __tablename__ = "content_metadata"

    content_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    technology: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heading_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_block_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    processing_status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )
    weaviate_workspace: Mapped[Optional[str]] = mapped_column(String)
    weaviate_document_id: Mapped[Optional[str]] = mapped_column(String)
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
    """Feedback events table - PRD-002 lines 81-94"""

    __tablename__ = "feedback_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    content_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("content_metadata.content_id", ondelete="CASCADE"),
        nullable=False,
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

    content: Mapped["ContentMetadata"] = relationship(
        "ContentMetadata", back_populates="feedback_events"
    )

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
    """Usage signals table - PRD-002 lines 97-110"""

    __tablename__ = "usage_signals"

    signal_id: Mapped[str] = mapped_column(String, primary_key=True)
    content_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("content_metadata.content_id", ondelete="CASCADE"),
        nullable=False,
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

    content: Mapped["ContentMetadata"] = relationship(
        "ContentMetadata", back_populates="usage_signals"
    )

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
    """Source metadata table - PRD-002 lines 113-130"""

    __tablename__ = "source_metadata"

    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    technology: Mapped[str] = mapped_column(String, nullable=False)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    avg_processing_time_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_documents_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_successful_fetch: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_failed_fetch: Mapped[Optional[datetime]] = mapped_column(DateTime)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
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

    __table_args__ = (
        CheckConstraint("source_type IN ('github', 'web', 'api')"),
        CheckConstraint("reliability_score >= 0.0 AND reliability_score <= 1.0"),
        CheckConstraint("rate_limit_status IN ('normal', 'limited', 'exhausted')"),
        CheckConstraint("avg_content_quality >= 0.0 AND avg_content_quality <= 1.0"),
        Index("idx_source_metadata_source_type", "source_type"),
        Index("idx_source_metadata_technology", "technology"),
        Index("idx_source_metadata_reliability_score", "reliability_score"),
        Index("idx_source_metadata_is_active", "is_active"),
        Index("idx_source_metadata_updated_at", "updated_at"),
    )


class TechnologyMappings(Base):
    """Technology mappings table - PRD-002 lines 133-150"""

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
    update_frequency_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )

    __table_args__ = (
        CheckConstraint("source_type IN ('github', 'web')"),
        UniqueConstraint(
            "technology",
            "source_type",
            "owner",
            "repo",
            "base_url",
            name="uq_technology_source_mapping",
        ),
        Index("idx_technology_mappings_technology", "technology"),
        Index("idx_technology_mappings_source_type", "source_type"),
        Index("idx_technology_mappings_priority", "priority"),
        Index("idx_technology_mappings_is_active", "is_active"),
        Index("idx_technology_mappings_is_official", "is_official"),
    )


# Additional Models for Test Compatibility


class DocumentMetadata(Base):
    """
    Document metadata model for test compatibility.
    Maps to expected test structure with different schema.
    """

    __tablename__ = "document_metadata"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    __table_args__ = (
        Index("idx_document_metadata_source_url", "source_url"),
        Index("idx_document_metadata_content_hash", "content_hash"),
    )


class DocumentChunk(Base):
    """Document chunk model for test compatibility"""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("document_metadata.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_vector: Mapped[str] = mapped_column(Text)  # JSON string
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )

    __table_args__ = (Index("idx_document_chunks_document_id", "document_id"),)


class ProcessedDocument(Base):
    """Processed document model for test compatibility"""

    __tablename__ = "processed_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("document_metadata.id", ondelete="CASCADE"), nullable=False
    )
    processed_content: Mapped[str] = mapped_column(Text, nullable=False)
    processing_metadata: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )

    __table_args__ = ()


class SearchQuery(Base):
    """Search query model for test compatibility"""

    __tablename__ = "search_queries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    query_text: Mapped[str] = mapped_column(String, nullable=False)
    query_hash: Mapped[str] = mapped_column(String, nullable=False)
    results_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )

    __table_args__ = (Index("idx_search_queries_created_at", "created_at"),)


class CacheEntry(Base):
    """Cache entry model for test compatibility"""

    __tablename__ = "cache_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    cache_value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )

    __table_args__ = ()


class SystemMetrics(Base):
    """System metrics model for test compatibility"""

    __tablename__ = "system_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    __table_args__ = ()


class User(Base):
    """User model for test compatibility"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.current_timestamp()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = ()
