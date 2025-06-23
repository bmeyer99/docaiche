"""
Database & Caching Layer - PRD-002
Complete database initialization and management system for AI Documentation Cache

This module provides:
- SQLite database schema creation with all tables and indexes
- SQLAlchemy 2.0 async ORM models and connection management  
- Redis cache integration with async client setup
- Configuration integration using CFG-001 system
- Database health checks and migration support
"""

from .init_db import DatabaseInitializer
from .manager import DatabaseManager, create_database_manager
from .models import Base, SystemConfig, SearchCache, ContentMetadata, FeedbackEvents, UsageSignals, SourceMetadata, TechnologyMappings
from .schema import create_database_schema

__all__ = [
    "DatabaseInitializer",
    "DatabaseManager",
    "create_database_manager",
    "create_database_schema",
    "Base",
    "SystemConfig",
    "SearchCache",
    "ContentMetadata",
    "FeedbackEvents",
    "UsageSignals",
    "SourceMetadata",
    "TechnologyMappings",
]