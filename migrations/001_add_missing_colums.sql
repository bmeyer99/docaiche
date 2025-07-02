-- Migration 001: Add missing columns for analytics and statistics
-- Created: 2025-06-28
-- Purpose: Fix schema mismatches identified during API testing

-- 1. Add search_queries table if it doesn't exist
CREATE TABLE IF NOT EXISTS search_queries (
    id VARCHAR PRIMARY KEY NOT NULL,
    query_text VARCHAR NOT NULL,
    query_hash VARCHAR NOT NULL,
    results_json TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- New columns for analytics
    response_time_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    status VARCHAR DEFAULT 'success',
    result_count INTEGER DEFAULT 0,
    technology_hint VARCHAR,
    user_session_id VARCHAR
);

-- 2. Add indexes for search_queries if they don't exist
CREATE INDEX IF NOT EXISTS idx_search_queries_created_at ON search_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_search_queries_status ON search_queries(status);
CREATE INDEX IF NOT EXISTS idx_search_queries_technology_hint ON search_queries(technology_hint);
CREATE INDEX IF NOT EXISTS idx_search_queries_user_session_id ON search_queries(user_session_id);

-- 3. Add error tracking to system_metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id VARCHAR PRIMARY KEY NOT NULL,
    metric_type VARCHAR NOT NULL,
    metric_name VARCHAR NOT NULL,
    metric_value REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    -- Additional fields for error tracking
    error_type VARCHAR,
    error_message TEXT,
    error_context TEXT
);

-- 4. Create index for error queries
CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_type ON system_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

-- 5. Add missing columns to content_metadata if not present
-- SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we need to check first
-- This will be handled by the Python migration script

-- 6. Add workspace column to content_metadata if missing
ALTER TABLE content_metadata ADD COLUMN workspace VARCHAR NOT NULL DEFAULT 'default';

-- 7. Add enriched_at column to content_metadata if missing
ALTER TABLE content_metadata ADD COLUMN enriched_at TIMESTAMP;

-- 8. Add duration_ms and session_id columns to usage_signals
ALTER TABLE usage_signals ADD COLUMN duration_ms INTEGER;
ALTER TABLE usage_signals ADD COLUMN session_id TEXT;
ALTER TABLE usage_signals ADD COLUMN user_id TEXT;

-- 9. Update system_config table structure to match expected schema
CREATE TABLE IF NOT EXISTS system_config_new (
    config_key VARCHAR PRIMARY KEY NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR NOT NULL, -- 'string', 'integer', 'float', 'boolean', 'json'
    schema_version VARCHAR DEFAULT '1.0',
    category VARCHAR,
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Copy data from old system_config if it exists
INSERT OR IGNORE INTO system_config_new (config_key, config_value, config_type, schema_version, updated_at)
SELECT key, value, 'json', schema_version, updated_at
FROM system_config
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='system_config');

-- Drop old table and rename new one
DROP TABLE IF EXISTS system_config;
ALTER TABLE system_config_new RENAME TO system_config;

-- 10. Insert schema version record
INSERT INTO schema_versions (version_id, description, migration_script)
VALUES ('1.1.0', 'Add missing columns for analytics and statistics', 
'001_add_missing_columns.sql');