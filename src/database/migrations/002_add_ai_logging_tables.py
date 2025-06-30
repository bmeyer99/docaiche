"""
Database migration to add AI logging and analytics tables.
Migration version: 002

This migration adds tables for tracking AI operations, conversations,
correlation IDs, and performance metrics for the AI logging system.
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "2.0.0"
MIGRATION_DESCRIPTION = "Add AI logging and analytics tables"


def upgrade(conn: sqlite3.Connection) -> None:
    """Apply migration to add AI logging tables."""
    logger.info("Applying migration 002: Add AI logging tables")
    
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    
    # AI Operations table - tracks all AI requests
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_operations (
            operation_id TEXT PRIMARY KEY NOT NULL,
            correlation_id TEXT NOT NULL,
            conversation_id TEXT,
            workspace_id TEXT,
            session_id TEXT,
            user_id TEXT,
            
            -- Request details
            model TEXT NOT NULL,
            request_type TEXT NOT NULL CHECK (request_type IN ('completion', 'chat', 'embedding', 'function', 'agent')),
            prompt TEXT,
            prompt_hash TEXT,
            
            -- Response details
            response TEXT,
            tokens_prompt INTEGER DEFAULT 0,
            tokens_completion INTEGER DEFAULT 0,
            tokens_total INTEGER DEFAULT 0,
            
            -- Performance metrics
            duration_ms INTEGER,
            latency_ms INTEGER,
            queue_time_ms INTEGER,
            
            -- Status and error tracking
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'timeout', 'cancelled')),
            error_type TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            
            -- Metadata
            service_name TEXT NOT NULL DEFAULT 'api',
            endpoint TEXT,
            ip_address TEXT,
            user_agent TEXT,
            
            -- Timestamps
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            
            -- Indexes will be created separately
            CHECK (tokens_total >= 0),
            CHECK (duration_ms >= 0 OR duration_ms IS NULL)
        )
    """)
    
    # AI Conversations table - tracks conversation threads
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_conversations (
            conversation_id TEXT PRIMARY KEY NOT NULL,
            workspace_id TEXT NOT NULL,
            user_id TEXT,
            session_id TEXT,
            
            -- Conversation metadata
            title TEXT,
            summary TEXT,
            tags JSON,
            
            -- Metrics
            message_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0,
            
            -- Status
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
            
            -- Timestamps
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_message_at TIMESTAMP,
            ended_at TIMESTAMP,
            
            CHECK (message_count >= 0),
            CHECK (total_tokens >= 0),
            CHECK (total_cost >= 0.0)
        )
    """)
    
    # AI Correlations table - tracks request flows across services
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_correlations (
            correlation_id TEXT PRIMARY KEY NOT NULL,
            root_operation_id TEXT,
            
            -- Flow tracking
            service_chain JSON NOT NULL DEFAULT '[]',
            total_operations INTEGER DEFAULT 1,
            
            -- Performance
            total_duration_ms INTEGER,
            bottleneck_service TEXT,
            bottleneck_duration_ms INTEGER,
            
            -- Error tracking
            has_errors BOOLEAN DEFAULT FALSE,
            error_count INTEGER DEFAULT 0,
            first_error_service TEXT,
            first_error_message TEXT,
            
            -- Timestamps
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            
            FOREIGN KEY (root_operation_id) REFERENCES ai_operations(operation_id) ON DELETE CASCADE,
            CHECK (total_operations > 0),
            CHECK (error_count >= 0)
        )
    """)
    
    # AI Workspace Usage table - aggregated usage by workspace
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_workspace_usage (
            workspace_id TEXT NOT NULL,
            date DATE NOT NULL,
            hour INTEGER,
            
            -- Usage metrics
            request_count INTEGER DEFAULT 0,
            conversation_count INTEGER DEFAULT 0,
            unique_users INTEGER DEFAULT 0,
            
            -- Token usage
            tokens_prompt INTEGER DEFAULT 0,
            tokens_completion INTEGER DEFAULT 0,
            tokens_total INTEGER DEFAULT 0,
            
            -- Model breakdown
            model_usage JSON NOT NULL DEFAULT '{}',
            
            -- Performance metrics
            avg_response_time_ms REAL,
            p95_response_time_ms REAL,
            p99_response_time_ms REAL,
            
            -- Error metrics
            error_count INTEGER DEFAULT 0,
            error_rate REAL DEFAULT 0.0,
            
            -- Cost tracking
            estimated_cost REAL DEFAULT 0.0,
            
            -- Timestamps
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            PRIMARY KEY (workspace_id, date, hour),
            CHECK (hour >= 0 AND hour <= 23 OR hour IS NULL),
            CHECK (request_count >= 0),
            CHECK (error_rate >= 0.0 AND error_rate <= 1.0)
        )
    """)
    
    # AI Error Patterns table - tracks common error patterns
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_error_patterns (
            pattern_id TEXT PRIMARY KEY NOT NULL,
            pattern_hash TEXT NOT NULL UNIQUE,
            
            -- Pattern details
            error_type TEXT NOT NULL,
            error_pattern TEXT NOT NULL,
            sample_message TEXT,
            
            -- Occurrence tracking
            first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            occurrence_count INTEGER DEFAULT 1,
            affected_services JSON DEFAULT '[]',
            
            -- Resolution
            is_resolved BOOLEAN DEFAULT FALSE,
            resolution_notes TEXT,
            resolved_at TIMESTAMP,
            
            -- Auto-detection
            detection_confidence REAL DEFAULT 1.0,
            is_auto_detected BOOLEAN DEFAULT TRUE,
            
            CHECK (occurrence_count > 0),
            CHECK (detection_confidence >= 0.0 AND detection_confidence <= 1.0)
        )
    """)
    
    # AI Performance Baselines table - tracks performance baselines
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_performance_baselines (
            baseline_id TEXT PRIMARY KEY NOT NULL,
            service_name TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            model TEXT,
            
            -- Baseline metrics
            avg_duration_ms REAL NOT NULL,
            p50_duration_ms REAL NOT NULL,
            p95_duration_ms REAL NOT NULL,
            p99_duration_ms REAL NOT NULL,
            
            -- Sample size
            sample_count INTEGER NOT NULL,
            
            -- Validity period
            calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            valid_until TIMESTAMP NOT NULL,
            
            -- Status
            is_active BOOLEAN DEFAULT TRUE,
            
            UNIQUE(service_name, operation_type, model, is_active),
            CHECK (sample_count > 0)
        )
    """)
    
    # Create indexes for performance
    indexes = [
        # AI Operations indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_correlation_id ON ai_operations(correlation_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_conversation_id ON ai_operations(conversation_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_workspace_id ON ai_operations(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_user_id ON ai_operations(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_model ON ai_operations(model)",
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_status ON ai_operations(status)",
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_created_at ON ai_operations(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_ai_operations_service_name ON ai_operations(service_name)",
        
        # AI Conversations indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_conversations_workspace_id ON ai_conversations(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_conversations_status ON ai_conversations(status)",
        "CREATE INDEX IF NOT EXISTS idx_ai_conversations_started_at ON ai_conversations(started_at)",
        "CREATE INDEX IF NOT EXISTS idx_ai_conversations_last_message_at ON ai_conversations(last_message_at)",
        
        # AI Correlations indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_correlations_has_errors ON ai_correlations(has_errors)",
        "CREATE INDEX IF NOT EXISTS idx_ai_correlations_started_at ON ai_correlations(started_at)",
        
        # AI Workspace Usage indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_workspace_usage_workspace_id ON ai_workspace_usage(workspace_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_workspace_usage_date ON ai_workspace_usage(date)",
        "CREATE INDEX IF NOT EXISTS idx_ai_workspace_usage_workspace_date ON ai_workspace_usage(workspace_id, date)",
        
        # AI Error Patterns indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_error_patterns_error_type ON ai_error_patterns(error_type)",
        "CREATE INDEX IF NOT EXISTS idx_ai_error_patterns_is_resolved ON ai_error_patterns(is_resolved)",
        "CREATE INDEX IF NOT EXISTS idx_ai_error_patterns_last_seen_at ON ai_error_patterns(last_seen_at)",
        
        # AI Performance Baselines indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_performance_baselines_service_name ON ai_performance_baselines(service_name)",
        "CREATE INDEX IF NOT EXISTS idx_ai_performance_baselines_is_active ON ai_performance_baselines(is_active)",
    ]
    
    for index_sql in indexes:
        conn.execute(index_sql)
    
    # Insert migration record
    conn.execute("""
        INSERT INTO schema_versions (version_id, description, migration_script)
        VALUES (?, ?, ?)
    """, (MIGRATION_VERSION, MIGRATION_DESCRIPTION, "002_add_ai_logging_tables.py"))
    
    logger.info("Migration 002 completed successfully")


def downgrade(conn: sqlite3.Connection) -> None:
    """Rollback migration - drop AI logging tables."""
    logger.info("Rolling back migration 002: Remove AI logging tables")
    
    tables = [
        "ai_performance_baselines",
        "ai_error_patterns", 
        "ai_workspace_usage",
        "ai_correlations",
        "ai_conversations",
        "ai_operations"
    ]
    
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    
    # Remove migration record
    conn.execute("""
        DELETE FROM schema_versions WHERE version_id = ?
    """, (MIGRATION_VERSION,))
    
    logger.info("Migration 002 rolled back successfully")


def get_migration_info() -> dict:
    """Get migration information."""
    return {
        "version": MIGRATION_VERSION,
        "description": MIGRATION_DESCRIPTION,
        "upgrade_function": upgrade,
        "downgrade_function": downgrade
    }