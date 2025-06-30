# Docaiche Data Models Documentation

## Overview
This document describes the data models, database schema, and expected data flow in the Docaiche system.

## Database Tables and Models

### 1. `system_config`
**Purpose**: Stores system configuration key-value pairs

**Schema**:
```sql
config_key VARCHAR PRIMARY KEY
config_value TEXT NOT NULL
config_type VARCHAR NOT NULL -- 'string', 'integer', 'float', 'boolean', 'json'
schema_version VARCHAR DEFAULT '1.0'
category VARCHAR
description TEXT
is_sensitive BOOLEAN DEFAULT FALSE
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

**Expected Data**:
- API settings (ports, hosts, workers)
- Cache configuration
- LLM provider settings
- Feature flags

### 2. `search_queries`
**Purpose**: Logs all search queries for analytics

**Current Schema** (Limited):
```sql
id VARCHAR PRIMARY KEY
query_text VARCHAR NOT NULL
query_hash VARCHAR NOT NULL
results_json TEXT DEFAULT '{}'
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
```

**Missing Fields** (Expected by stats endpoint):
- `response_time_ms` - Query execution time
- `cache_hit` - Whether results came from cache
- `status` - 'success' or 'failed'
- `result_count` - Number of results returned
- `technology_hint` - Technology filter used
- `user_session_id` - For tracking user sessions

### 3. `content_metadata`
**Purpose**: Stores metadata about ingested documents

**Schema**:
```sql
content_id VARCHAR PRIMARY KEY
title VARCHAR NOT NULL
content_type VARCHAR NOT NULL -- 'documentation', 'code', 'tutorial', etc.
technology VARCHAR NOT NULL
source_url VARCHAR
source_type VARCHAR -- 'github', 'web', 'manual'
workspace VARCHAR NOT NULL DEFAULT 'default'
checksum VARCHAR
version VARCHAR
quality_score REAL DEFAULT 0.0
freshness_score REAL DEFAULT 1.0
processing_status TEXT DEFAULT 'pending'
anythingllm_workspace TEXT
anythingllm_document_id TEXT
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
last_accessed_at TIMESTAMP
access_count INTEGER DEFAULT 0
enriched_at TIMESTAMP
```

### 4. `document_chunks`
**Purpose**: Stores document content broken into chunks

**Schema**:
```sql
chunk_id VARCHAR PRIMARY KEY
content_id VARCHAR NOT NULL (FK -> content_metadata)
chunk_index INTEGER NOT NULL
content TEXT NOT NULL
embedding TEXT
chunk_metadata TEXT
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### 5. `feedback_events`
**Purpose**: Tracks user feedback on search results

**Schema**:
```sql
event_id TEXT PRIMARY KEY
content_id TEXT NOT NULL (FK -> content_metadata)
feedback_type TEXT -- 'helpful', 'not_helpful', 'outdated', 'incorrect', 'flag'
rating INTEGER (1-5)
comment TEXT
user_session_id TEXT
ip_address TEXT
user_agent TEXT
search_query TEXT
result_position INTEGER
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### 6. `usage_signals`
**Purpose**: Tracks user interaction signals

**Schema**:
```sql
signal_id TEXT PRIMARY KEY
content_id TEXT NOT NULL
signal_type TEXT -- 'click', 'dwell_time', 'copy', 'share', 'scroll_depth'
signal_value REAL DEFAULT 0.0
search_query TEXT
result_position INTEGER
user_session_id TEXT
ip_address TEXT
user_agent TEXT
timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
duration_ms INTEGER
session_id TEXT
user_id TEXT
```

### 7. `cache_entries`
**Purpose**: Tracks cache usage (for Redis cache metadata)

**Schema**:
```sql
cache_key VARCHAR PRIMARY KEY
cache_type VARCHAR NOT NULL
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
expires_at TIMESTAMP
access_count INTEGER DEFAULT 0
last_accessed TIMESTAMP
size_bytes INTEGER
```

### 8. `system_metrics`
**Purpose**: System performance and error tracking

**Schema**:
```sql
id VARCHAR PRIMARY KEY
metric_type VARCHAR NOT NULL
metric_name VARCHAR NOT NULL
metric_value REAL NOT NULL
timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
metadata TEXT
```

## API Response Models

### SearchResponse
```json
{
  "results": [
    {
      "content_id": "string",
      "title": "string",
      "snippet": "string",
      "source_url": "string",
      "technology": "string",
      "relevance_score": 0.0-1.0,
      "content_type": "string",
      "workspace": "string"
    }
  ],
  "total_count": 0,
  "query": "string",
  "technology_hint": "string",
  "execution_time_ms": 0,
  "cache_hit": false,
  "enrichment_triggered": false
}
```

### StatsResponse
```json
{
  "search_stats": {
    "total_searches": 0,
    "avg_response_time_ms": 0.0,
    "cache_hit_rate": 0.0,
    "successful_searches": 0,
    "failed_searches": 0
  },
  "cache_stats": {
    "hit_rate": 0.0,
    "miss_rate": 0.0,
    "total_keys": 0,
    "memory_usage_mb": 0,
    "evictions": 0
  },
  "content_stats": {
    "total_documents": 0,
    "total_chunks": 0,
    "avg_quality_score": 0.0,
    "workspaces": 0,
    "last_enrichment": "datetime"
  },
  "system_stats": {
    "uptime_seconds": 0,
    "cpu_usage_percent": 0.0,
    "memory_usage_mb": 0.0,
    "disk_usage_mb": 0.0
  },
  "timestamp": "datetime"
}
```

## Data Flow

### 1. Search Flow
1. User submits search query via API
2. System checks cache for existing results
3. If cache miss:
   - Query AnythingLLM workspaces
   - Apply relevance scoring
   - Optional: Trigger enrichment if results are poor
4. Log query to `search_queries` table
5. Track user interactions in `usage_signals`
6. Return results

### 2. Content Ingestion Flow
1. Document uploaded via API
2. Create entry in `content_metadata`
3. Process document and split into chunks
4. Store chunks in `document_chunks`
5. Upload to AnythingLLM workspace
6. Update processing status
7. Optional: Trigger enrichment

### 3. Enrichment Flow
1. Identify content gaps or quality issues
2. Query LLM for additional content
3. Create new content entries
4. Update `enriched_at` timestamp
5. Update quality scores

### 4. Analytics Flow
1. Query aggregates data from:
   - `search_queries` for search metrics
   - `content_metadata` for content stats
   - `usage_signals` for user behavior
   - `cache_entries` for cache performance
2. Calculate time-based metrics
3. Return aggregated results

## Current Issues

### 1. Schema Mismatches
- `search_queries` table is missing fields needed for proper analytics
- Activity queries expect columns that don't exist
- Stats endpoint expects richer data than schema provides

### 2. Mock Data Still Present
- Search results are hardcoded
- Analytics returns static values
- Collections are not from database

### 3. Missing Implementations
- AnythingLLM integration not fully connected
- Enrichment service not initialized properly
- Cache stats not reading from Redis

## Recommendations

### 1. Schema Updates Needed
```sql
-- Add to search_queries
ALTER TABLE search_queries ADD COLUMN response_time_ms INTEGER;
ALTER TABLE search_queries ADD COLUMN cache_hit BOOLEAN DEFAULT FALSE;
ALTER TABLE search_queries ADD COLUMN status VARCHAR DEFAULT 'success';
ALTER TABLE search_queries ADD COLUMN result_count INTEGER DEFAULT 0;
ALTER TABLE search_queries ADD COLUMN technology_hint VARCHAR;
ALTER TABLE search_queries ADD COLUMN user_session_id VARCHAR;
```

### 2. Implement Real Data Sources
- Connect search to AnythingLLM workspaces
- Read actual cache stats from Redis
- Query real document counts from database

### 3. Complete Integration Points
- Initialize enrichment service with all dependencies
- Connect Ollama for LLM operations
- Implement proper document upload to AnythingLLM

## Testing Considerations

When testing the API:
1. **Direct API (port 4000)**: Test individual service functionality
2. **Through Admin UI (port 4080)**: Test proxy configuration and full stack
3. **Data Validation**: Ensure responses match documented schemas
4. **Performance**: Monitor response times and cache effectiveness
5. **Error Handling**: Verify proper error responses for edge cases