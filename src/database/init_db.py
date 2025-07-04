"""
Database Initialization Module - PRD-002 DB-001
Creates SQLite database with all tables, indexes, and constraints as specified

This module implements the exact database schema from the task requirements,
integrating with the CFG-001 configuration system for database settings.
"""

import sqlite3
import os
import logging
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Import configuration system for integration
try:
    from src.core.config import get_system_configuration
except ImportError:
    get_system_configuration = None


class DatabaseInitializer:
    """
    Database initialization class implementing exact schema from DB-001 task.

    Integrates with CFG-001 configuration system and provides idempotent
    database creation with all tables, indexes, and default data.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DatabaseInitializer with configuration integration.

        Args:
            db_path: Override database path (uses config if None)
        """
        # Check for DATABASE_URL environment variable first
        self.database_url = os.environ.get("DATABASE_URL")
        
        if self.database_url:
            # Using PostgreSQL or other database URL
            self.db_path = None
            self.is_postgres = "postgresql" in self.database_url
            logger.info(f"Using DATABASE_URL: {self.database_url.split('@')[0]}...")
        elif db_path:
            self.db_path = db_path
            self.database_url = f"sqlite:///{db_path}"
            self.is_postgres = False
        else:
            # Integrate with CFG-001 configuration system
            try:
                if get_system_configuration is not None:
                    config = get_system_configuration()
                    self.db_path = os.path.join(config.app.data_dir, "docaiche.db")
                    logger.info(f"Using configuration from CFG-001: {self.db_path}")
                else:
                    self.db_path = "/data/docaiche.db"
                    logger.info(
                        "CFG-001 configuration not available, using default path"
                    )
            except Exception as e:
                logger.warning(
                    f"Could not load CFG-001 configuration, using default path: {e}"
                )
                self.db_path = "/data/docaiche.db"
            
            self.database_url = f"sqlite:///{self.db_path}"
            self.is_postgres = False

        self.schema_version = "1.0.0"

    def initialize_database(self, force_recreate: bool = False) -> None:
        """
        Initialize the database with all tables and indexes.

        Args:
            force_recreate: If True, drop existing database and recreate
        """
        # Delegate to PostgreSQL initializer if using PostgreSQL
        if self.is_postgres:
            from src.database.init_db_postgres import PostgreSQLInitializer
            pg_init = PostgreSQLInitializer(self.database_url)
            pg_init.initialize_database(force_recreate=force_recreate)
            return
        
        # Original SQLite initialization code
        if self.db_path:
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
        """Create all database tables exactly as specified in task requirements"""

        # System configuration table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY NOT NULL,
                value JSON NOT NULL,
                schema_version TEXT NOT NULL DEFAULT '1.0',
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT NOT NULL DEFAULT 'system'
            )
        """
        )

        # Search cache table
        conn.execute(
            """
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
        """
        )

        # Content metadata table
        conn.execute(
            """
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
                weaviate_workspace TEXT,
                weaviate_document_id TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER NOT NULL DEFAULT 0
            )
        """
        )

        # Feedback events table
        conn.execute(
            """
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
        """
        )

        # Usage signals table
        conn.execute(
            """
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
        """
        )

        # Source metadata table
        conn.execute(
            """
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
        """
        )

        # Technology mappings table
        conn.execute(
            """
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
        """
        )

        # Schema versions table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version_id TEXT PRIMARY KEY NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                migration_script TEXT
            )
        """
        )

        logger.info("All database tables created successfully")

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create all performance indexes exactly as specified in task requirements"""

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
            "CREATE INDEX IF NOT EXISTS idx_technology_mappings_is_official ON technology_mappings(is_official)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

        logger.info("All database indexes created successfully")

    def _insert_schema_version(self, conn: sqlite3.Connection) -> None:
        """Insert initial schema version record"""
        conn.execute(
            """
            INSERT OR REPLACE INTO schema_versions (version_id, description)
            VALUES (?, ?)
        """,
            (self.schema_version, "Initial database schema"),
        )

    def _insert_default_mappings(self, conn: sqlite3.Connection) -> None:
        """Insert default technology-to-repository mappings"""

        default_mappings = [
            # Python frameworks
            (
                str(uuid.uuid4()),
                "python-fastapi",
                "github",
                "tiangolo",
                "fastapi",
                "docs",
                '["*.md"]',
                None,
                10,
                True,
            ),
            (
                str(uuid.uuid4()),
                "python-django",
                "github",
                "django",
                "django",
                "docs",
                '["*.txt", "*.md"]',
                None,
                10,
                True,
            ),
            (
                str(uuid.uuid4()),
                "python-flask",
                "github",
                "pallets",
                "flask",
                "docs",
                '["*.rst", "*.md"]',
                None,
                9,
                True,
            ),
            # JavaScript frameworks
            (
                str(uuid.uuid4()),
                "react",
                "github",
                "facebook",
                "react",
                "docs",
                '["*.md"]',
                None,
                10,
                True,
            ),
            (
                str(uuid.uuid4()),
                "nextjs",
                "github",
                "vercel",
                "next.js",
                "docs",
                '["*.mdx", "*.md"]',
                None,
                10,
                True,
            ),
            (
                str(uuid.uuid4()),
                "vue",
                "github",
                "vuejs",
                "core",
                "packages/vue",
                '["*.md"]',
                None,
                10,
                True,
            ),
            # DevOps tools
            (
                str(uuid.uuid4()),
                "docker",
                "github",
                "docker",
                "docs",
                "content",
                '["*.md"]',
                None,
                10,
                True,
            ),
            (
                str(uuid.uuid4()),
                "kubernetes",
                "github",
                "kubernetes",
                "website",
                "content",
                '["*.md"]',
                None,
                10,
                True,
            ),
        ]

        for mapping in default_mappings:
            conn.execute(
                """
                INSERT OR IGNORE INTO technology_mappings 
                (mapping_id, technology, source_type, owner, repo, docs_path, file_patterns, base_url, priority, is_official)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                mapping,
            )

        logger.info("Default technology mappings inserted")

    def get_database_path(self) -> str:
        """Get the configured database path"""
        return self.db_path

    def check_database_exists(self) -> bool:
        """Check if database file exists"""
        return os.path.exists(self.db_path)

    def get_database_info(self) -> dict:
        """Get database information and stats"""
        if not self.check_database_exists():
            return {"exists": False, "path": self.db_path}

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get table count
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                table_count = cursor.fetchone()[0]

                # Get schema version
                try:
                    cursor = conn.execute(
                        "SELECT version_id FROM schema_versions ORDER BY applied_at DESC LIMIT 1"
                    )
                    schema_version = cursor.fetchone()
                    schema_version = schema_version[0] if schema_version else "unknown"
                except sqlite3.OperationalError:
                    schema_version = "unknown"

                # Get file size
                file_size = os.path.getsize(self.db_path)

                return {
                    "exists": True,
                    "path": self.db_path,
                    "table_count": table_count,
                    "schema_version": schema_version,
                    "file_size_bytes": file_size,
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                }
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {"exists": True, "path": self.db_path, "error": str(e)}


def main():
    """CLI interface for database initialization"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize AI Documentation Cache database"
    )
    parser.add_argument(
        "--db-path", help="Database file path (uses config if not specified)"
    )
    parser.add_argument("--force", action="store_true", help="Force recreate database")
    parser.add_argument("--info", action="store_true", help="Show database information")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    initializer = DatabaseInitializer(args.db_path)

    if args.info:
        info = initializer.get_database_info()
        print("Database Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        initializer.initialize_database(force_recreate=args.force)


if __name__ == "__main__":
    main()
