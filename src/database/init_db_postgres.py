"""
Database Initialization Module for PostgreSQL Migration
Creates all tables with PostgreSQL-specific optimizations
"""

import os
import logging
import uuid
from typing import Optional
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

class PostgreSQLInitializer:
    """Initialize PostgreSQL database with DocAIche schema."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize with database URL."""
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL must be provided")
        
        # Remove async drivers for synchronous connection
        self.sync_url = self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
        self.schema_version = "1.0.0"
    
    def initialize_database(self, force_recreate: bool = False) -> None:
        """Initialize PostgreSQL database with all tables and indexes."""
        engine = create_engine(self.sync_url)
        
        try:
            with engine.begin() as conn:
                if force_recreate:
                    # Drop all tables
                    conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                    conn.execute(text("CREATE SCHEMA public"))
                    conn.execute(text("GRANT ALL ON SCHEMA public TO docaiche"))
                
                # Create enums first (PostgreSQL specific)
                self._create_enums(conn)
                
                # Create tables
                self._create_tables(conn)
                
                # Create indexes
                self._create_indexes(conn)
                
                # Insert initial data
                self._insert_schema_version(conn)
                self._insert_default_mappings(conn)
                
                logger.info("PostgreSQL database initialized successfully")
                
        except OperationalError as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _create_enums(self, conn):
        """Create PostgreSQL enum types."""
        # These are already created in init-postgres.sql, but check anyway
        enums = [
            ("processing_status", "'pending', 'processing', 'completed', 'failed', 'flagged', 'pending_context7'"),
            ("feedback_type", "'helpful', 'not_helpful', 'outdated', 'incorrect', 'flag'"),
            ("signal_type", "'click', 'dwell_time', 'copy', 'share', 'scroll_depth'"),
            ("source_type", "'github', 'web', 'api'"),
            ("rate_limit_status", "'normal', 'limited', 'exhausted'")
        ]
        
        for enum_name, values in enums:
            conn.execute(text(f"""
                DO $$ BEGIN
                    CREATE TYPE {enum_name} AS ENUM ({values});
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
    
    def _create_tables(self, conn):
        """Create all database tables with PostgreSQL types."""
        
        # System configuration table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY NOT NULL,
                value JSONB NOT NULL,
                schema_version TEXT NOT NULL DEFAULT '1.0',
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT NOT NULL DEFAULT 'system'
            )
        """))
        
        # Configuration audit log table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS configuration_audit_log (
                id TEXT PRIMARY KEY NOT NULL,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                section TEXT NOT NULL,
                changes JSONB NOT NULL,
                previous_values JSONB NOT NULL,
                comment TEXT
            )
        """))
        
        # Search cache table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY NOT NULL,
                original_query TEXT NOT NULL,
                search_results JSONB NOT NULL,
                technology_hint TEXT,
                workspace_slugs JSONB,
                result_count INTEGER NOT NULL DEFAULT 0,
                execution_time_ms INTEGER NOT NULL DEFAULT 0,
                cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Content metadata table
        conn.execute(text("""
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
                processing_status processing_status NOT NULL DEFAULT 'pending',
                weaviate_workspace TEXT,
                weaviate_document_id TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER NOT NULL DEFAULT 0,
                metadata JSONB,
                expires_at TIMESTAMP,
                source_provider TEXT
            )
        """))
        
        # Feedback events table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS feedback_events (
                event_id TEXT PRIMARY KEY NOT NULL,
                content_id TEXT NOT NULL,
                feedback_type feedback_type NOT NULL,
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
        """))
        
        # Usage signals table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usage_signals (
                signal_id TEXT PRIMARY KEY NOT NULL,
                content_id TEXT NOT NULL,
                signal_type signal_type NOT NULL,
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
        """))
        
        # Source metadata table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS source_metadata (
                source_id TEXT PRIMARY KEY NOT NULL,
                source_type source_type NOT NULL,
                source_url TEXT NOT NULL,
                technology TEXT NOT NULL,
                reliability_score REAL NOT NULL DEFAULT 1.0 CHECK (reliability_score >= 0.0 AND reliability_score <= 1.0),
                avg_processing_time_ms INTEGER NOT NULL DEFAULT 0,
                total_documents_processed INTEGER NOT NULL DEFAULT 0,
                last_successful_fetch TIMESTAMP,
                last_failed_fetch TIMESTAMP,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                rate_limit_status rate_limit_status DEFAULT 'normal',
                rate_limit_reset_at TIMESTAMP,
                avg_content_quality REAL DEFAULT 0.0 CHECK (avg_content_quality >= 0.0 AND avg_content_quality <= 1.0),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Technology mappings table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS technology_mappings (
                mapping_id TEXT PRIMARY KEY NOT NULL,
                technology TEXT NOT NULL,
                source_type source_type NOT NULL,
                owner TEXT,
                repo TEXT,
                docs_path TEXT NOT NULL DEFAULT 'docs',
                file_patterns JSONB NOT NULL DEFAULT '["*.md", "*.mdx"]'::jsonb,
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
        """))
        
        # Schema versions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                version_id TEXT PRIMARY KEY NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                migration_script TEXT
            )
        """))
        
        # Additional tables for compatibility
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_metadata (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                technology TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                word_count INTEGER DEFAULT 0,
                heading_count INTEGER DEFAULT 0,
                code_block_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                parent_document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                total_chunks INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_document_id) REFERENCES document_metadata(id) ON DELETE CASCADE
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS processed_documents (
                id TEXT PRIMARY KEY,
                technology TEXT NOT NULL,
                title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                full_content TEXT,
                chunks JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # AI logging tables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_log_entries (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                service TEXT NOT NULL,
                message TEXT NOT NULL,
                trace_id TEXT,
                span_id TEXT,
                user_id TEXT,
                session_id TEXT,
                request_id TEXT,
                metadata JSONB,
                error_type TEXT,
                error_message TEXT,
                error_stack TEXT,
                duration_ms INTEGER,
                status_code INTEGER,
                endpoint TEXT,
                method TEXT,
                client_ip TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_pattern_detections (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                occurrence_count INTEGER DEFAULT 1,
                affected_services JSONB,
                sample_traces JSONB,
                metadata JSONB
            )
        """))
        
        logger.info("All tables created successfully")
    
    def _create_indexes(self, conn):
        """Create all performance indexes with PostgreSQL optimizations."""
        
        # Use GIN indexes for JSONB columns
        gin_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_search_cache_workspace_slugs_gin ON search_cache USING GIN (workspace_slugs)",
            "CREATE INDEX IF NOT EXISTS idx_search_cache_results_gin ON search_cache USING GIN (search_results)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_metadata_gin ON content_metadata USING GIN (metadata)",
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_patterns_gin ON technology_mappings USING GIN (file_patterns)",
        ]
        
        # Standard B-tree indexes
        btree_indexes = [
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
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_expires_at ON content_metadata(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_content_metadata_source_provider ON content_metadata(source_provider)",
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
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_is_official ON technology_mappings(is_official)",
            # Configuration audit log indexes
            "CREATE INDEX IF NOT EXISTS idx_config_audit_timestamp ON configuration_audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_config_audit_user ON configuration_audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_config_audit_section ON configuration_audit_log(section)",
        ]
        
        # Create GIN indexes
        for index_sql in gin_indexes:
            try:
                conn.execute(text(index_sql))
            except Exception as e:
                logger.warning(f"Could not create GIN index: {e}")
        
        # Create B-tree indexes
        for index_sql in btree_indexes:
            conn.execute(text(index_sql))
        
        logger.info("All indexes created successfully")
    
    def _insert_schema_version(self, conn):
        """Insert initial schema version."""
        conn.execute(text("""
            INSERT INTO schema_versions (version_id, description)
            VALUES (:version, :description)
            ON CONFLICT (version_id) DO NOTHING
        """), {"version": self.schema_version, "description": "Initial PostgreSQL schema"})
    
    def _insert_default_mappings(self, conn):
        """Insert default technology mappings."""
        
        default_mappings = [
            # Python frameworks
            {
                "id": str(uuid.uuid4()),
                "tech": "python-fastapi",
                "type": "github",
                "owner": "tiangolo",
                "repo": "fastapi",
                "path": "docs",
                "patterns": '["*.md"]',
                "priority": 10,
                "official": True,
            },
            {
                "id": str(uuid.uuid4()),
                "tech": "python-django",
                "type": "github",
                "owner": "django",
                "repo": "django",
                "path": "docs",
                "patterns": '["*.txt", "*.md"]',
                "priority": 10,
                "official": True,
            },
            {
                "id": str(uuid.uuid4()),
                "tech": "python-flask",
                "type": "github",
                "owner": "pallets",
                "repo": "flask",
                "path": "docs",
                "patterns": '["*.rst", "*.md"]',
                "priority": 9,
                "official": True,
            },
            # JavaScript frameworks
            {
                "id": str(uuid.uuid4()),
                "tech": "react",
                "type": "github",
                "owner": "facebook",
                "repo": "react",
                "path": "docs",
                "patterns": '["*.md"]',
                "priority": 10,
                "official": True,
            },
            {
                "id": str(uuid.uuid4()),
                "tech": "nextjs",
                "type": "github",
                "owner": "vercel",
                "repo": "next.js",
                "path": "docs",
                "patterns": '["*.mdx", "*.md"]',
                "priority": 10,
                "official": True,
            },
            {
                "id": str(uuid.uuid4()),
                "tech": "vue",
                "type": "github",
                "owner": "vuejs",
                "repo": "core",
                "path": "packages/vue",
                "patterns": '["*.md"]',
                "priority": 10,
                "official": True,
            },
            # DevOps tools
            {
                "id": str(uuid.uuid4()),
                "tech": "docker",
                "type": "github",
                "owner": "docker",
                "repo": "docs",
                "path": "content",
                "patterns": '["*.md"]',
                "priority": 10,
                "official": True,
            },
            {
                "id": str(uuid.uuid4()),
                "tech": "kubernetes",
                "type": "github",
                "owner": "kubernetes",
                "repo": "website",
                "path": "content",
                "patterns": '["*.md"]',
                "priority": 10,
                "official": True,
            },
        ]
        
        for mapping in default_mappings:
            conn.execute(text("""
                INSERT INTO technology_mappings 
                (mapping_id, technology, source_type, owner, repo, docs_path, file_patterns, priority, is_official)
                VALUES (:id, :tech, :type, :owner, :repo, :path, CAST(:patterns AS jsonb), :priority, :official)
                ON CONFLICT DO NOTHING
            """), mapping)
        
        logger.info("Default technology mappings inserted")


def main():
    """CLI interface for PostgreSQL database initialization."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Initialize DocAIche PostgreSQL database"
    )
    parser.add_argument("--force", action="store_true", help="Force recreate database")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    try:
        initializer = PostgreSQLInitializer()
        initializer.initialize_database(force_recreate=args.force)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    main()