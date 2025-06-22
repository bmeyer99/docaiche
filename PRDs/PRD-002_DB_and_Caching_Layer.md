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
-- ... (other tables as in original spec)
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