# Task: DB-001 - Create SQLite Database and All Tables/Indexes

**PRD Reference**: [PRD-002: Database & Caching Layer](../PRDs/PRD-002_DB_and_Caching_Layer.md#database-schema)

## Overview
Create a Python script that initializes the SQLite database with all tables, indexes, and constraints as defined in PRD-002. This is the foundational data persistence layer for the entire system.

## Detailed Requirements

### 1. Database Schema Implementation
Implement all tables exactly as specified in PRD-002:

#### System Configuration Table
```sql
CREATE TABLE system_config (
    key TEXT PRIMARY KEY NOT NULL,
    value JSON NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT NOT NULL DEFAULT 'system'
);
```

#### Search Cache Table
```sql
CREATE TABLE search_cache (
    query_hash TEXT PRIMARY KEY NOT NULL,
    original_query TEXT NOT NULL,
    search_results JSON NOT NULL,
    technology_hint TEXT,
    workspace_slugs JSON,  -- Array of workspace slugs searched
    result_count INTEGER NOT NULL DEFAULT 0,
    execution_time_ms INTEGER NOT NULL DEFAULT 0,
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### Content Metadata Table
```sql
CREATE TABLE content_metadata (
    content_id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    technology TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    word_count INTEGER NOT NULL DEFAULT 0,
    heading_count INTEGER NOT NULL DEFAULT 0,
    code_block_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    quality_score REAL NOT NULL DEFAULT 0.0 CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    freshness_score REAL NOT NULL DEFAULT 1.0 CHECK (freshness_score >= 0.0 AND freshness_score <= 1.0),
    processing_status TEXT NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'flagged')),
    anythingllm_workspace TEXT,
    anythingllm_document_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 0
);
```

#### Feedback Events Table
```sql
CREATE TABLE feedback_events (
    event_id TEXT PRIMARY KEY NOT NULL,
    content_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('helpful', 'not_helpful', 'outdated', 'incorrect', 'flag')),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    user_session_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    search_query TEXT,
    result_position INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content_metadata(content_id) ON DELETE CASCADE
);
```

#### Usage Signals Table
```sql
CREATE TABLE usage_signals (
    signal_id TEXT PRIMARY KEY NOT NULL,
    content_id TEXT NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('click', 'dwell_time', 'copy', 'share', 'scroll_depth')),
    signal_value REAL NOT NULL DEFAULT 0.0,  -- click=1, dwell_time=seconds, scroll_depth=percentage
    search_query TEXT,
    result_position INTEGER,
    user_session_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    referrer TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content_metadata(content_id) ON DELETE CASCADE
);
```

#### Source Metadata Table
```sql
CREATE TABLE source_metadata (
    source_id TEXT PRIMARY KEY NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('github', 'web', 'api')),
    source_url TEXT NOT NULL,
    technology TEXT NOT NULL,
    reliability_score REAL NOT NULL DEFAULT 1.0 CHECK (reliability_score >= 0.0 AND reliability_score <= 1.0),
    avg_processing_time_ms INTEGER NOT NULL DEFAULT 0,
    total_documents_processed INTEGER NOT NULL DEFAULT 0,
    last_successful_fetch TIMESTAMP,
    last_failed_fetch TIMESTAMP,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    rate_limit_status TEXT DEFAULT 'normal' CHECK (rate_limit_status IN ('normal', 'limited', 'exhausted')),
    rate_limit_reset_at TIMESTAMP,
    avg_content_quality REAL DEFAULT 0.0 CHECK (avg_content_quality >= 0.0 AND avg_content_quality <= 1.0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### Technology Mappings Table
```sql
CREATE TABLE technology_mappings (
    mapping_id TEXT PRIMARY KEY NOT NULL,
    technology TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('github', 'web')),
    owner TEXT,  -- GitHub owner/organization
    repo TEXT,   -- GitHub repository name
    docs_path TEXT NOT NULL DEFAULT 'docs',  -- Path to documentation within repo
    file_patterns JSON NOT NULL DEFAULT '["*.md", "*.mdx"]',  -- File patterns to search for
    base_url TEXT,  -- Base URL for web sources
    priority INTEGER NOT NULL DEFAULT 1,  -- Higher number = higher priority
    is_official BOOLEAN NOT NULL DEFAULT FALSE,  -- True for official documentation
    last_updated TIMESTAMP,
    update_frequency_hours INTEGER NOT NULL DEFAULT 24,  -- How often to check for updates
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(technology, source_type, owner, repo, base_url)
);
```

### 2. Performance Indexes
Create all performance indexes as specified:

```sql
-- Search cache indexes
CREATE INDEX idx_search_cache_expires_at ON search_cache(expires_at);
CREATE INDEX idx_search_cache_technology_hint ON search_cache(technology_hint);
CREATE INDEX idx_search_cache_created_at ON search_cache(created_at);

-- Content metadata indexes
CREATE INDEX idx_content_metadata_technology ON content_metadata(technology);
CREATE INDEX idx_content_metadata_source_url ON content_metadata(source_url);
CREATE INDEX idx_content_metadata_content_hash ON content_metadata(content_hash);
CREATE INDEX idx_content_metadata_quality_score ON content_metadata(quality_score);
CREATE INDEX idx_content_metadata_processing_status ON content_metadata(processing_status);
CREATE INDEX idx_content_metadata_created_at ON content_metadata(created_at);
CREATE INDEX idx_content_metadata_last_accessed_at ON content_metadata(last_accessed_at);

-- Feedback events indexes
CREATE INDEX idx_feedback_events_content_id ON feedback_events(content_id);
CREATE INDEX idx_feedback_events_feedback_type ON feedback_events(feedback_type);
CREATE INDEX idx_feedback_events_created_at ON feedback_events(created_at);
CREATE INDEX idx_feedback_events_user_session_id ON feedback_events(user_session_id);

-- Usage signals indexes
CREATE INDEX idx_usage_signals_content_id ON usage_signals(content_id);
CREATE INDEX idx_usage_signals_signal_type ON usage_signals(signal_type);
CREATE INDEX idx_usage_signals_created_at ON usage_signals(created_at);
CREATE INDEX idx_usage_signals_user_session_id ON usage_signals(user_session_id);

-- Source metadata indexes
CREATE INDEX idx_source_metadata_source_type ON source_metadata(source_type);
CREATE INDEX idx_source_metadata_technology ON source_metadata(technology);
CREATE INDEX idx_source_metadata_reliability_score ON source_metadata(reliability_score);
CREATE INDEX idx_source_metadata_is_active ON source_metadata(is_active);
CREATE INDEX idx_source_metadata_updated_at ON source_metadata(updated_at);

-- Technology mappings indexes
CREATE INDEX idx_technology_mappings_technology ON technology_mappings(technology);
CREATE INDEX idx_technology_mappings_source_type ON technology_mappings(source_type);
CREATE INDEX idx_technology_mappings_priority ON technology_mappings(priority);
CREATE INDEX idx_technology_mappings_is_active ON technology_mappings(is_active);
CREATE INDEX idx_technology_mappings_is_official ON technology_mappings(is_official);
```

### 3. Schema Versioning Table
```sql
CREATE TABLE schema_versions (
    version_id TEXT PRIMARY KEY NOT NULL,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    migration_script TEXT
);
```

## Implementation Details

### File: `src/database/init_db.py`
```python
import sqlite3
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, db_path: str = "/app/data/docaiche.db"):
        self.db_path = db_path
        self.schema_version = "1.0.0"
    
    def initialize_database(self, force_recreate: bool = False) -> None:
        """
        Initialize the SQLite database with all tables and indexes.
        
        Args:
            force_recreate: If True, drop existing database and recreate
        """
        # Create data directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if force_recreate and os.path.exists(self.db_path):
            os.remove(self.db_path)
            logger.info(f"Removed existing database: {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create all tables
            self._create_tables(conn)
            
            # Create all indexes
            self._create_indexes(conn)
            
            # Insert initial schema version
            self._insert_schema_version(conn)
            
            # Insert default technology mappings
            self._insert_default_mappings(conn)
            
            conn.commit()
            logger.info(f"Database initialized successfully: {self.db_path}")
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all database tables"""
        
        # System configuration table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY NOT NULL,
                value JSON NOT NULL,
                schema_version TEXT NOT NULL DEFAULT '1.0',
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT NOT NULL DEFAULT 'system'
            )
        """)
        
        # Search cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY NOT NULL,
                original_query TEXT NOT NULL,
                search_results JSON NOT NULL,
                technology_hint TEXT,
                workspace_slugs JSON,
                result_count INTEGER NOT NULL DEFAULT 0,
                execution_time_ms INTEGER NOT NULL DEFAULT 0,
                cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Content metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content_metadata (
                content_id TEXT PRIMARY KEY NOT NULL,
                title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                technology TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                word_count INTEGER NOT NULL DEFAULT 0,
                heading_count INTEGER NOT NULL DEFAULT 0,
                code_block_count INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                quality_score REAL NOT NULL DEFAULT 0.0 CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
                freshness_score REAL NOT NULL DEFAULT 1.0 CHECK (freshness_score >= 0.0 AND freshness_score <= 1.0),
                processing_status TEXT NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'flagged')),
                anythingllm_workspace TEXT,
                anythingllm_document_id TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        
        # Feedback events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_events (
                event_id TEXT PRIMARY KEY NOT NULL,
                content_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL CHECK (feedback_type IN ('helpful', 'not_helpful', 'outdated', 'incorrect', 'flag')),
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                user_session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                search_query TEXT,
                result_position INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_metadata(content_id) ON DELETE CASCADE
            )
        """)
        
        # Usage signals table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_signals (
                signal_id TEXT PRIMARY KEY NOT NULL,
                content_id TEXT NOT NULL,
                signal_type TEXT NOT NULL CHECK (signal_type IN ('click', 'dwell_time', 'copy', 'share', 'scroll_depth')),
                signal_value REAL NOT NULL DEFAULT 0.0,
                search_query TEXT,
                result_position INTEGER,
                user_session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                referrer TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_metadata(content_id) ON DELETE CASCADE
            )
        """)
        
        # Source metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS source_metadata (
                source_id TEXT PRIMARY KEY NOT NULL,
                source_type TEXT NOT NULL CHECK (source_type IN ('github', 'web', 'api')),
                source_url TEXT NOT NULL,
                technology TEXT NOT NULL,
                reliability_score REAL NOT NULL DEFAULT 1.0 CHECK (reliability_score >= 0.0 AND reliability_score <= 1.0),
                avg_processing_time_ms INTEGER NOT NULL DEFAULT 0,
                total_documents_processed INTEGER NOT NULL DEFAULT 0,
                last_successful_fetch TIMESTAMP,
                last_failed_fetch TIMESTAMP,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                rate_limit_status TEXT DEFAULT 'normal' CHECK (rate_limit_status IN ('normal', 'limited', 'exhausted')),
                rate_limit_reset_at TIMESTAMP,
                avg_content_quality REAL DEFAULT 0.0 CHECK (avg_content_quality >= 0.0 AND avg_content_quality <= 1.0),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Technology mappings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS technology_mappings (
                mapping_id TEXT PRIMARY KEY NOT NULL,
                technology TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK (source_type IN ('github', 'web')),
                owner TEXT,
                repo TEXT,
                docs_path TEXT NOT NULL DEFAULT 'docs',
                file_patterns JSON NOT NULL DEFAULT '["*.md", "*.mdx"]',
                base_url TEXT,
                priority INTEGER NOT NULL DEFAULT 1,
                is_official BOOLEAN NOT NULL DEFAULT FALSE,
                last_updated TIMESTAMP,
                update_frequency_hours INTEGER NOT NULL DEFAULT 24,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(technology, source_type, owner, repo, base_url)
            )
        """)
        
        # Schema versions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                version_id TEXT PRIMARY KEY NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                migration_script TEXT
            )
        """)
        
        logger.info("All database tables created successfully")
    
    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create all performance indexes"""
        
        indexes = [
            # Search cache indexes
            "CREATE INDEX IF NOT EXISTS idx_search_cache_expires_at ON search_cache(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_search_cache_technology_hint ON search_cache(technology_hint)",
            "CREATE INDEX IF NOT EXISTS idx_search_cache_created_at ON search_cache(created_at)",
            
            # Content metadata indexes
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_technology ON content_metadata(technology)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_source_url ON content_metadata(source_url)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_content_hash ON content_metadata(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_quality_score ON content_metadata(quality_score)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_processing_status ON content_metadata(processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_created_at ON content_metadata(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_last_accessed_at ON content_metadata(last_accessed_at)",
            
            # Feedback events indexes
            "CREATE INDEX IF NOT EXISTS idx_feedback_events_content_id ON feedback_events(content_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_events_feedback_type ON feedback_events(feedback_type)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_events_created_at ON feedback_events(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_events_user_session_id ON feedback_events(user_session_id)",
            
            # Usage signals indexes
            "CREATE INDEX IF NOT EXISTS idx_usage_signals_content_id ON usage_signals(content_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_signals_signal_type ON usage_signals(signal_type)",
            "CREATE INDEX IF NOT EXISTS idx_usage_signals_created_at ON usage_signals(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_usage_signals_user_session_id ON usage_signals(user_session_id)",
            
            # Source metadata indexes
            "CREATE INDEX IF NOT EXISTS idx_source_metadata_source_type ON source_metadata(source_type)",
            "CREATE INDEX IF NOT EXISTS idx_source_metadata_technology ON source_metadata(technology)",
            "CREATE INDEX IF NOT EXISTS idx_source_metadata_reliability_score ON source_metadata(reliability_score)",
            "CREATE INDEX IF NOT EXISTS idx_source_metadata_is_active ON source_metadata(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_source_metadata_updated_at ON source_metadata(updated_at)",
            
            # Technology mappings indexes
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_technology ON technology_mappings(technology)",
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_source_type ON technology_mappings(source_type)",
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_priority ON technology_mappings(priority)",
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_is_active ON technology_mappings(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_is_official ON technology_mappings(is_official)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        logger.info("All database indexes created successfully")
    
    def _insert_schema_version(self, conn: sqlite3.Connection) -> None:
        """Insert initial schema version record"""
        conn.execute("""
            INSERT OR REPLACE INTO schema_versions (version_id, description)
            VALUES (?, ?)
        """, (self.schema_version, "Initial database schema"))
    
    def _insert_default_mappings(self, conn: sqlite3.Connection) -> None:
        """Insert default technology-to-repository mappings"""
        
        default_mappings = [
            # Python frameworks
            ("python-fastapi", "python", "github", "tiangolo", "fastapi", "docs", '["*.md"]', None, 10, True),
            ("python-django", "python", "github", "django", "django", "docs", '["*.txt", "*.md"]', None, 10, True),
            ("python-flask", "python", "github", "pallets", "flask", "docs", '["*.rst", "*.md"]', None, 9, True),
            
            # JavaScript frameworks
            ("react-official", "react", "github", "facebook", "react", "docs", '["*.md"]', None, 10, True),
            ("nextjs-official", "nextjs", "github", "vercel", "next.js", "docs", '["*.mdx", "*.md"]', None, 10, True),
            ("vue-official", "vue", "github", "vuejs", "core", "packages/vue", '["*.md"]', None, 10, True),
            
            # DevOps tools
            ("docker-official", "docker", "github", "docker", "docs", "content", '["*.md"]', None, 10, True),
            ("kubernetes-official", "kubernetes", "github", "kubernetes", "website", "content", '["*.md"]', None, 10, True),
        ]
        
        for mapping in default_mappings:
            conn.execute("""
                INSERT OR IGNORE INTO technology_mappings 
                (mapping_id, technology, source_type, owner, repo, docs_path, file_patterns, base_url, priority, is_official)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, mapping)
        
        logger.info("Default technology mappings inserted")

def main():
    """CLI interface for database initialization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize AI Documentation Cache database")
    parser.add_argument("--db-path", default="/app/data/docaiche.db", help="Database file path")
    parser.add_argument("--force", action="store_true", help="Force recreate database")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    initializer = DatabaseInitializer(args.db_path)
    initializer.initialize_database(force_recreate=args.force)

if __name__ == "__main__":
    main()
```

### CLI Usage Script
```bash
#!/bin/bash
# scripts/init-db.sh

set -e

DB_PATH="${DB_PATH:-/app/data/docaiche.db}"
FORCE="${FORCE:-false}"

echo "Initializing database at: $DB_PATH"

if [ "$FORCE" = "true" ]; then
    echo "Force recreating database..."
    python -m src.database.init_db --db-path "$DB_PATH" --force
else
    python -m src.database.init_db --db-path "$DB_PATH"
fi

echo "Database initialization complete!"
```

## Acceptance Criteria
- [ ] All tables created exactly as specified in PRD-002
- [ ] All indexes created for performance optimization
- [ ] Foreign key constraints properly configured
- [ ] Check constraints validate data integrity
- [ ] Schema versioning table tracks migrations
- [ ] Default technology mappings inserted
- [ ] Script can be run multiple times safely (idempotent)
- [ ] CLI interface for database initialization
- [ ] Proper error handling and logging
- [ ] Database file created in correct location

## Dependencies
- sqlite3 (Python standard library)
- pathlib (Python standard library)

## Files to Create/Modify
- `src/database/__init__.py` (create)
- `src/database/init_db.py` (create)
- `scripts/init-db.sh` (create)

## Testing
- Verify all tables exist with correct schema
- Test foreign key constraints work
- Test check constraints validate data
- Verify indexes improve query performance
- Test CLI interface with various options
- Verify idempotent behavior

## Integration Notes
- This script will be called during container initialization in PRD-013
- Database schema must match exactly with SQLAlchemy models in DB-002
- Default technology mappings support initial content acquisition
- Schema versioning supports future migrations in DB-006