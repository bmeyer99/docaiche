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
from .connection import DatabaseManager, CacheManager
from .models import Base, SystemConfig, SearchCache, ContentMetadata, FeedbackEvents, UsageSignals, SourceMetadata, TechnologyMappings, SchemaVersions

__all__ = [
    "DatabaseInitializer",
    "DatabaseManager", 
    "CacheManager",
    "Base",
    "SystemConfig",
    "SearchCache", 
    "ContentMetadata",
    "FeedbackEvents",
    "UsageSignals",
    "SourceMetadata",
    "TechnologyMappings",
    "SchemaVersions",
]