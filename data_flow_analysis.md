# Complete Data Flow Analysis

## 1. Search Flow

### API Entry Point
- **Endpoint**: `POST /api/v1/search` or `GET /api/v1/search`
- **File**: `/home/lab/docaiche/src/api/v1/search_endpoints.py`
- **Input**: `SearchRequest` (Pydantic model)
  - `query`: string (1-500 chars)
  - `technology_hint`: optional string
  - `limit`: int (1-100, default 20)
  - `session_id`: optional string

### Flow Through SearchService/SearchOrchestrator

1. **Request Validation**:
   - FastAPI validates against `SearchRequest` schema
   - Rate limiting applied (30/min for POST, 60/min for GET)

2. **SearchOrchestrator Processing** (`/home/lab/docaiche/src/search/orchestrator.py`):
   
   a. **Query Normalization** (line 392-463):
      - Input validation (length, characters)
      - Text cleaning via `ContentPreprocessor`
      - Tokenization and Porter stemming
      - Technology hint lowercasing
      - **Data Transformation**: Raw query → normalized tokens → stemmed query string
      - **Potential Issues**: 
        - Character validation might be too restrictive for international queries
        - Simple stemming may not handle all language variations

   b. **Cache Check** (line 158-176):
      - Generate cache key from normalized query using SHA256 hash
      - Check Redis via `SearchCacheManager`
      - Circuit breaker pattern for cache failures
      - **Data Transformation**: Query → SHA256 hash → Redis key
      - **Lost Fields**: None
      - **Added Fields**: `cache_hit` flag

   c. **Multi-Workspace Search** (line 178-189):
      - Identify relevant workspaces via `WorkspaceSearchStrategy`
      - Execute parallel searches with timeout (30s total, 2s per workspace)
      - **Data Transformation**: Query → workspace relevance scores → filtered workspaces
      - **Potential Issues**: Timeout errors not properly propagated

   d. **AI Evaluation** (line 191-200):
      - Optional LLM evaluation of results quality
      - Currently returns mock evaluation
      - **Data Transformation**: Results → evaluation prompt → quality scores
      - **Lost Fields**: None
      - **Added Fields**: `needs_enrichment`, `enrichment_topics`

   e. **Result Compilation** (line 209-218):
      - Aggregate results with metadata
      - Calculate execution time
      - **Data Transformation**: Individual results → `SearchResults` model
      - **Added Fields**: `query_time_ms`, `strategy_used`, `workspaces_searched`, `enrichment_triggered`

   f. **Cache Storage** (line 221-230):
      - Store results in Redis with TTL (default 1 hour)
      - Store analytics data separately (24-hour TTL)
      - Circuit breaker for cache failures
      - **Data Transformation**: `SearchResults` → JSON → Redis storage

### Database Queries
- Workspace metadata lookup (via `DatabaseManager`)
- No direct search result storage in database (only cache)

### Response Transformation
- **Output**: `SearchResponse` (Pydantic model)
  - `results`: List of `SearchResult` objects
  - `total_count`: int
  - `query`: original query string
  - `technology_hint`: optional string
  - `execution_time_ms`: int
  - `cache_hit`: bool
  - `enrichment_triggered`: bool

### Data Validation Gaps
1. No validation of workspace slugs existence
2. No sanitization of HTML in result snippets
3. Missing validation for result relevance scores

---

## 2. Configuration Update Flow

### API Entry Point
- **Endpoint**: `POST /api/v1/config`
- **File**: `/home/lab/docaiche/src/api/v1/config_endpoints.py`
- **Input**: `ConfigurationUpdateRequest`
  - `key`: string (dot notation required)
  - `value`: Any
  - `description`: optional string

### ConfigService Processing

1. **Request Validation** (line 218-224):
   - Key format validation (must contain dot)
   - Rate limiting (5/min)
   - **Validation Gap**: No validation of allowed configuration keys

2. **Background Task Execution** (line 226-237):
   - Async background task via FastAPI
   - Immediate 202 response to client
   - **Lost Fields**: `description` field not used

3. **ConfigurationManager Update** (`/home/lab/docaiche/src/core/config/manager.py`):
   
   a. **Database Update** (line 295-322):
      - Serialize value as JSON if not string
      - UPSERT into `system_config` table
      - **Data Transformation**: 
        - Complex types → JSON string
        - Simple types → string representation
      - **Database Query**: 
        ```sql
        INSERT OR REPLACE INTO system_config 
        (config_key, config_value, is_active, updated_at)
        VALUES (?, ?, ?, ?)
        ```

   b. **Configuration Reload** (line 318):
      - Trigger full configuration reload
      - Merge hierarchy: Environment > YAML > Database
      - **Data Flow**:
        1. Load from database (lowest priority)
        2. Load from config.yaml (medium priority)
        3. Apply environment overrides (highest priority)
        4. Validate with Pydantic models
        5. Update singleton instance

### Configuration Reload Mechanism
1. Database values loaded first
2. YAML config overlays database
3. Environment variables override all
4. Pydantic validation ensures type safety
5. Production secrets validation if environment="production"

### Response Generation
- Immediate 202 Accepted response
- No confirmation of actual update success
- **Missing**: Webhook or SSE for update confirmation

### Potential Issues
1. No rollback mechanism for failed updates
2. No audit trail beyond `updated_at` timestamp
3. Configuration changes not propagated to other services
4. No validation of configuration value types against schema

---

## 3. Content Ingestion Flow

### API Entry Point
- **Endpoint**: `POST /api/v1/ingestion/upload`
- **File**: `/home/lab/docaiche/src/api/v1/ingestion.py`
- **Input**: `UploadFile` (multipart/form-data)

### Current Implementation (Stub)
The current implementation is a stub that:
1. Reads file contents
2. Validates non-empty
3. Returns mock document_id

### Actual Flow (from DocumentIngestionService)
**File**: `/home/lab/docaiche/src/document_processing/ingestion.py`

1. **File Validation** (line 28-45):
   - Check file size (max 20MB default)
   - Validate file extension against allowed formats
   - **Data Validation**:
     - Size check prevents OOM
     - Format whitelist prevents malicious files
   - **Potential Issues**:
     - Extension-based validation can be bypassed
     - No content-type validation
     - No virus scanning

2. **Document Storage** (line 47-57):
   - Store raw file in database
   - Generate document metadata
   - **Data Transformation**:
     - File bytes → database BLOB
     - Filename → metadata record
   - **Database Operation**: Document insertion with metadata

3. **Processing Job Creation** (line 59-79):
   - Generate job_id using SHA256 hash
   - Create `ProcessingJob` record
   - **Data Added**:
     - `job_id`: SHA256 hash
     - `status`: "PENDING"
     - `progress`: 0.0
     - Timestamps
   - **Database Operation**: Job record insertion

### Missing Implementation
1. Actual file processing pipeline trigger
2. Chunk generation and indexing
3. AnythingLLM workspace integration
4. Quality scoring
5. Metadata extraction

### Data Transformations
- Raw bytes → Database BLOB
- Filename → Document metadata
- Document ID → Processing job

---

## 4. Feedback Flow

### API Entry Point
- **Endpoint**: `POST /api/v1/feedback`
- **File**: `/home/lab/docaiche/src/api/v1/search_endpoints.py`
- **Input**: `FeedbackRequest`
  - `content_id`: string
  - `feedback_type`: enum (helpful/not_helpful/outdated/incorrect/flag)
  - `rating`: optional int (1-5)
  - `comment`: optional string (max 1000)
  - `query_context`: optional string
  - `session_id`: optional string

### Processing Flow

1. **Request Validation**:
   - Pydantic validation of feedback type enum
   - Rating range validation (1-5)
   - Comment length validation
   - Rate limiting (20/min)

2. **Background Task** (line 156-160):
   - Currently placeholder implementation
   - Logs feedback receipt
   - Returns 202 Accepted immediately

3. **Database Storage** (from models):
   **Table**: `feedback_events`
   - **Data Transformation**:
     - Generate `event_id` (not shown in current implementation)
     - Add timestamp
     - Link to `content_id` (foreign key)
   - **Added Fields**:
     - `ip_address`
     - `user_agent`
     - `created_at`

### Signal Flow
- **Endpoint**: `POST /api/v1/signals`
- **Input**: `SignalRequest`
  - `query_id`: string
  - `session_id`: string
  - `signal_type`: enum (click/dwell/abandon/refine/copy)
  - `content_id`: optional string
  - `result_position`: optional int
  - `dwell_time_ms`: optional int

### Database Model (`usage_signals` table)
- Foreign key to `content_metadata`
- Signal value storage (float)
- Session tracking
- User agent and IP capture

### Analytics Aggregation
**Missing Implementation**:
1. No aggregation queries defined
2. No background job for analytics computation
3. No connection to search ranking updates
4. No feedback loop to content quality scores

### Data Flow Issues
1. **Lost Data**: 
   - User feedback not connected to search improvements
   - No aggregation of feedback for content scoring
2. **Type Conversions**:
   - Signal enum → string in database
   - Optional fields may store NULL
3. **Validation Gaps**:
   - No validation of content_id existence
   - No duplicate feedback prevention
   - No rate limiting per content_id

---

## Summary of Key Issues

### Data Transformation Issues
1. **Search Flow**:
   - Query normalization may lose semantic meaning
   - Stemming algorithm is basic
   - No query expansion or synonym handling

2. **Configuration Flow**:
   - Complex objects serialized to JSON strings
   - No type preservation for numbers vs strings
   - Configuration hierarchy can cause confusion

3. **Ingestion Flow**:
   - File validation based on extension only
   - No content extraction implementation
   - Missing chunking and indexing

4. **Feedback Flow**:
   - Feedback data not used for improvements
   - No real-time analytics aggregation
   - Missing connection to search quality

### Null/Undefined Handling
1. Optional fields properly handled with Pydantic
2. Database models use `Optional` type hints
3. JSON serialization handles None → null conversion
4. **Risk**: Circuit breaker cache failures may return undefined

### Data Validation Gaps
1. No validation of foreign key references
2. Missing content sanitization
3. No request signature validation
4. Configuration keys not validated against schema

### Performance Concerns
1. **Search**: Sequential workspace identification (not parallel)
2. **Config**: Full reload on every update
3. **Ingestion**: No async processing pipeline
4. **Feedback**: No batching of analytics updates

### Security Issues
1. No input sanitization for XSS prevention
2. File upload lacks virus scanning
3. Configuration updates lack authorization checks
4. IP addresses stored without anonymization