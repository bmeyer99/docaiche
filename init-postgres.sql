-- PostgreSQL initialization script for DocAIche
-- Creates required extensions and optimizations

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create custom types if needed
DO $$ BEGIN
    CREATE TYPE processing_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'flagged', 'pending_context7');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE feedback_type AS ENUM ('helpful', 'not_helpful', 'outdated', 'incorrect', 'flag');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE signal_type AS ENUM ('click', 'dwell_time', 'copy', 'share', 'scroll_depth');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE source_type AS ENUM ('github', 'web', 'api');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE rate_limit_status AS ENUM ('normal', 'limited', 'exhausted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Set database parameters for better performance
ALTER DATABASE docaiche SET random_page_cost = 1.1;
ALTER DATABASE docaiche SET effective_io_concurrency = 200;
ALTER DATABASE docaiche SET max_parallel_workers_per_gather = 2;
ALTER DATABASE docaiche SET max_parallel_workers = 8;

-- Create indexes on JSONB columns after tables are created
-- This will be handled by the SQLAlchemy migrations