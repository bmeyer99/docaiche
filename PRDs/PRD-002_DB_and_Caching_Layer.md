# PRD-002: Database & Caching Layer

## Overview
Specifies the complete data persistence and caching layer, including the SQL schema for SQLite, Redis cache structure, and the data access layer (DAL) interface. Purely responsible for data storage and retrieval.

## Technical Boundaries
- Provides data services to all other components.
- Interfaces with SQLite and Redis.
- Exposes an asynchronous DAL to the application.
- Contains no business logic.

## Success Criteria
- All database tables and indexes created as specified.
- DAL provides functional, performant, and type-safe access.
- Cache operations meet performance targets.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-003: Configuration Management | Loads DB/cache config |
| PRD-013: Operations & Deployment | Deployment and backup scripts |
| PRD-001: HTTP API Foundation | API endpoints use DAL |
| PRD-008: Content Processing Pipeline | Stores processed content |

## Cross-References
- DAL (`DatabaseManager`, `CacheManager`) used by PRD-003, PRD-004, PRD-005, PRD-006, PRD-008, PRD-009, PRD-010, PRD-011.
- Table `content_metadata` referenced in PRD-008, PRD-010.
- Redis cache keys used by PRD-009, PRD-005.

## Database Schema

```sql
-- Table to store system configuration
CREATE TABLE system_config (
    key TEXT PRIMARY KEY NOT NULL,
    value JSON NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT NOT NULL DEFAULT 'system'
);

-- Table to cache search queries and results (PRD-009)
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

-- Table to track ingested content metadata (PRD-008, PRD-010)
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

-- Table to store explicit user feedback (PRD-011)
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

-- Table to track implicit user interactions (PRD-011)
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

-- Table to track source reliability and performance (PRD-010)
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

-- Table to map technologies to authoritative sources (PRD-006, PRD-010)
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

-- Indexes for performance optimization
CREATE INDEX idx_search_cache_expires_at ON search_cache(expires_at);
CREATE INDEX idx_search_cache_technology_hint ON search_cache(technology_hint);
CREATE INDEX idx_search_cache_created_at ON search_cache(created_at);

CREATE INDEX idx_content_metadata_technology ON content_metadata(technology);
CREATE INDEX idx_content_metadata_source_url ON content_metadata(source_url);
CREATE INDEX idx_content_metadata_content_hash ON content_metadata(content_hash);
CREATE INDEX idx_content_metadata_quality_score ON content_metadata(quality_score);
CREATE INDEX idx_content_metadata_processing_status ON content_metadata(processing_status);
CREATE INDEX idx_content_metadata_created_at ON content_metadata(created_at);
CREATE INDEX idx_content_metadata_last_accessed_at ON content_metadata(last_accessed_at);

CREATE INDEX idx_feedback_events_content_id ON feedback_events(content_id);
CREATE INDEX idx_feedback_events_feedback_type ON feedback_events(feedback_type);
CREATE INDEX idx_feedback_events_created_at ON feedback_events(created_at);
CREATE INDEX idx_feedback_events_user_session_id ON feedback_events(user_session_id);

CREATE INDEX idx_usage_signals_content_id ON usage_signals(content_id);
CREATE INDEX idx_usage_signals_signal_type ON usage_signals(signal_type);
CREATE INDEX idx_usage_signals_created_at ON usage_signals(created_at);
CREATE INDEX idx_usage_signals_user_session_id ON usage_signals(user_session_id);

CREATE INDEX idx_source_metadata_source_type ON source_metadata(source_type);
CREATE INDEX idx_source_metadata_technology ON source_metadata(technology);
CREATE INDEX idx_source_metadata_reliability_score ON source_metadata(reliability_score);
CREATE INDEX idx_source_metadata_is_active ON source_metadata(is_active);
CREATE INDEX idx_source_metadata_updated_at ON source_metadata(updated_at);

CREATE INDEX idx_technology_mappings_technology ON technology_mappings(technology);
CREATE INDEX idx_technology_mappings_source_type ON technology_mappings(source_type);
CREATE INDEX idx_technology_mappings_priority ON technology_mappings(priority);
CREATE INDEX idx_technology_mappings_is_active ON technology_mappings(is_active);
CREATE INDEX idx_technology_mappings_is_official ON technology_mappings(is_official);
```

## Redis Cache Structure

| Key Pattern                        | Type    | Data Stored                        | TTL (s) | Description                                 |
|-------------------------------------|---------|------------------------------------|---------|---------------------------------------------|
| search:results:{query_hash}         | String  | Gzip-compressed JSON of results    | 3600    | Caches search response                      |
| content:processed:{content_hash}    | String  | Gzip-compressed JSON of document   | 86400   | Caches processed document                   |
| ai:evaluation:{query_hash}          | String  | JSON of EvaluationResult           | 7200    | Caches AI evaluation                        |
| github:repo:{owner}/{repo}:{path}   | String  | Gzip-compressed repo metadata      | 3600    | Caches GitHub API metadata                  |
| config:system:{version}             | String  | JSON of SystemConfiguration        | 300     | Caches system config                        |
| rate_limit:api:{ip_address}         | String  | Integer counter                    | 60      | Tracks API rate limiting                    |
| session:{session_id}                | Hash    | User session data                  | 1800    | Tracks user interaction session             |

## Canonical Data Models

These models are shared across all PRDs to ensure consistency:

```python
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentMetadata(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    word_count: int
    heading_count: int
    code_block_count: int
    content_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class DocumentChunk(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    id: str = Field(..., description="Unique chunk identifier")
    parent_document_id: str = Field(..., description="Parent document ID")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="0-based index within document")
    total_chunks: int = Field(..., description="Total chunks in document")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessedDocument(BaseModel):
    model_version: str = Field("1.0.0", description="Model version for compatibility")
    id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    full_content: str = Field(..., description="Complete document content")
    source_url: str = Field(..., description="Original source URL")
    technology: str = Field(..., description="Technology stack")
    metadata: DocumentMetadata
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Content quality score")
    chunks: List[DocumentChunk]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
```

## Data Access Layer Models

```python
class DatabaseManager:
    """Manages database connections and executes queries."""
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def execute(self, query: str, params: Tuple = ()) -> None: ...
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Row]: ...
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Row]: ...
    async def execute_transaction(self, queries: List[Tuple[str, Tuple]]) -> bool: ...

class CacheManager:
    """Manages Redis connections and cache operations."""
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def get(self, key: str) -> Optional[Any]: ...
    async def set(self, key: str, value: Any, ttl: int) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def increment(self, key: str) -> int: ...
```

## Schema Versioning Strategy

The database uses Alembic for schema migrations with a dedicated versioning table:

```sql
CREATE TABLE schema_versions (
    version_id TEXT PRIMARY KEY NOT NULL,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    migration_script TEXT
);
```

### Upgrade Path Process:
1. Create new Alembic migration script
2. Test migration on backup database
3. Apply migration with rollback plan
4. Update model versions if schema changes affect data models
5. Document breaking changes and migration steps

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| DB-001  | Write Python script to create SQLite DB and all tables/indexes |
| DB-002  | Define SQLAlchemy 2.0 ORM models for all tables |
| DB-003  | Implement DatabaseManager using sqlalchemy.ext.asyncio |
| DB-004  | Implement CacheManager using redis-py async client |
| DB-005  | Create helper methods for TTLs, compression, serialization |
| DB-006  | Set up Alembic for migrations with schema versioning table |
| DB-007  | Create repository classes using DatabaseManager/CacheManager |
| DB-008  | Implement scheduled cleanup for expired search_cache entries |
| DB-009  | Write unit tests for DAL with mocked connections |
| DB-010  | Create comprehensive backup script for SQLite and Redis |
| DB-011  | Implement canonical data models with versioning |
| DB-012  | Create database schema upgrade and rollback procedures |

## Integration Contracts
- Accepts Python data types and Pydantic models from other components.
- Returns Python types, Pydantic models, or ORM objects.
- P99 latency for cache operations <10ms; for indexed DB queries <50ms.

## Summary Tables

### Tables

| Table Name           | Purpose                                 | Referenced By           |
|----------------------|-----------------------------------------|-------------------------|
| system_config        | Stores runtime config                   | PRD-003, PRD-001        |
| search_cache         | Caches search queries/results           | PRD-009                 |
| content_metadata     | Tracks ingested content                 | PRD-008, PRD-010        |
| feedback_events      | Stores explicit user feedback           | PRD-011                 |
| usage_signals        | Tracks implicit user interactions       | PRD-011                 |
| source_metadata      | Tracks source reliability/performance   | PRD-010                 |
| technology_mappings  | Maps tech to authoritative sources      | PRD-006, PRD-010        |

### Data Models Table

| Model Name      | Description                                 | Used In                 |
|-----------------|---------------------------------------------|-------------------------|
| DatabaseManager | Async DB access                             | PRD-003, PRD-004, etc.  |
| CacheManager    | Async Redis access                          | PRD-003, PRD-005, etc.  |

### Implementation Tasks Table
(see Implementation Tasks above)

---