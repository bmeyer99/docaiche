#!/usr/bin/env python3
"""
Database Migration Runner
Runs SQL migrations and handles SQLite-specific limitations
"""

import sqlite3
import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationRunner:
    def __init__(self, db_path: str = None):
        """Initialize migration runner"""
        if not db_path:
            # Default to the data directory used by the application
            db_path = "/app/data/docaiche.db"
            # If running locally, check for local path
            if not os.path.exists(db_path):
                local_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'docaiche.db')
                if os.path.exists(local_path):
                    db_path = local_path
        
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent
        
    def get_table_columns(self, conn: sqlite3.Connection, table_name: str) -> List[str]:
        """Get list of columns for a table"""
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    
    def table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if table exists"""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None
    
    def add_column_if_not_exists(self, conn: sqlite3.Connection, table: str, column: str, 
                                column_def: str):
        """Add column to table if it doesn't exist"""
        if self.table_exists(conn, table):
            columns = self.get_table_columns(conn, table)
            if column not in columns:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
                    logger.info(f"Added column {column} to table {table}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise
                    logger.info(f"Column {column} already exists in table {table}")
    
    def run_migration_001(self):
        """Run the first migration with SQLite-specific handling"""
        logger.info("Running migration 001: Add missing columns")
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 1. Create search_queries table if not exists
            if not self.table_exists(conn, 'search_queries'):
                conn.execute("""
                    CREATE TABLE search_queries (
                        id VARCHAR PRIMARY KEY NOT NULL,
                        query_text VARCHAR NOT NULL,
                        query_hash VARCHAR NOT NULL,
                        results_json TEXT DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        response_time_ms INTEGER,
                        cache_hit BOOLEAN DEFAULT FALSE,
                        status VARCHAR DEFAULT 'success',
                        result_count INTEGER DEFAULT 0,
                        technology_hint VARCHAR,
                        user_session_id VARCHAR
                    )
                """)
                logger.info("Created search_queries table")
            else:
                # Add missing columns to existing table
                self.add_column_if_not_exists(conn, 'search_queries', 'response_time_ms', 'INTEGER')
                self.add_column_if_not_exists(conn, 'search_queries', 'cache_hit', 'BOOLEAN DEFAULT FALSE')
                self.add_column_if_not_exists(conn, 'search_queries', 'status', "VARCHAR DEFAULT 'success'")
                self.add_column_if_not_exists(conn, 'search_queries', 'result_count', 'INTEGER DEFAULT 0')
                self.add_column_if_not_exists(conn, 'search_queries', 'technology_hint', 'VARCHAR')
                self.add_column_if_not_exists(conn, 'search_queries', 'user_session_id', 'VARCHAR')
            
            # 2. Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_search_queries_created_at ON search_queries(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_search_queries_status ON search_queries(status)",
                "CREATE INDEX IF NOT EXISTS idx_search_queries_technology_hint ON search_queries(technology_hint)",
                "CREATE INDEX IF NOT EXISTS idx_search_queries_user_session_id ON search_queries(user_session_id)",
            ]
            for idx in indexes:
                conn.execute(idx)
            
            # 3. Create system_metrics table if not exists
            if not self.table_exists(conn, 'system_metrics'):
                conn.execute("""
                    CREATE TABLE system_metrics (
                        id VARCHAR PRIMARY KEY NOT NULL,
                        metric_type VARCHAR NOT NULL,
                        metric_name VARCHAR NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        error_type VARCHAR,
                        error_message TEXT,
                        error_context TEXT
                    )
                """)
                logger.info("Created system_metrics table")
            else:
                self.add_column_if_not_exists(conn, 'system_metrics', 'error_type', 'VARCHAR')
                self.add_column_if_not_exists(conn, 'system_metrics', 'error_message', 'TEXT')
                self.add_column_if_not_exists(conn, 'system_metrics', 'error_context', 'TEXT')
            
            # Create indexes for system_metrics
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_type ON system_metrics(metric_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)")
            
            # 4. Add columns to content_metadata
            if self.table_exists(conn, 'content_metadata'):
                self.add_column_if_not_exists(conn, 'content_metadata', 'workspace', "VARCHAR NOT NULL DEFAULT 'default'")
                self.add_column_if_not_exists(conn, 'content_metadata', 'enriched_at', 'TIMESTAMP')
            
            # 5. Add columns to usage_signals
            if self.table_exists(conn, 'usage_signals'):
                self.add_column_if_not_exists(conn, 'usage_signals', 'duration_ms', 'INTEGER')
                self.add_column_if_not_exists(conn, 'usage_signals', 'session_id', 'TEXT')
                self.add_column_if_not_exists(conn, 'usage_signals', 'user_id', 'TEXT')
            
            # 6. Update system_config table structure
            if self.table_exists(conn, 'system_config'):
                # Check if we need to migrate
                columns = self.get_table_columns(conn, 'system_config')
                if 'config_key' not in columns:  # Old schema uses 'key'
                    logger.info("Migrating system_config table to new schema")
                    
                    # Create new table
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS system_config_new (
                            config_key VARCHAR PRIMARY KEY NOT NULL,
                            config_value TEXT NOT NULL,
                            config_type VARCHAR NOT NULL,
                            schema_version VARCHAR DEFAULT '1.0',
                            category VARCHAR,
                            description TEXT,
                            is_sensitive BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Copy data
                    conn.execute("""
                        INSERT OR IGNORE INTO system_config_new (config_key, config_value, config_type, schema_version, updated_at)
                        SELECT key, value, 'json', schema_version, updated_at
                        FROM system_config
                    """)
                    
                    # Drop old and rename
                    conn.execute("DROP TABLE system_config")
                    conn.execute("ALTER TABLE system_config_new RENAME TO system_config")
                else:
                    # Just add missing columns
                    self.add_column_if_not_exists(conn, 'system_config', 'config_type', "VARCHAR NOT NULL DEFAULT 'json'")
                    self.add_column_if_not_exists(conn, 'system_config', 'category', 'VARCHAR')
                    self.add_column_if_not_exists(conn, 'system_config', 'description', 'TEXT')
                    self.add_column_if_not_exists(conn, 'system_config', 'is_sensitive', 'BOOLEAN DEFAULT FALSE')
                    self.add_column_if_not_exists(conn, 'system_config', 'created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            
            # 7. Record migration
            if self.table_exists(conn, 'schema_versions'):
                # Check if already applied
                cursor = conn.execute(
                    "SELECT 1 FROM schema_versions WHERE version_id = '1.1.0'"
                )
                if not cursor.fetchone():
                    conn.execute("""
                        INSERT INTO schema_versions (version_id, description, migration_script)
                        VALUES ('1.1.0', 'Add missing columns for analytics and statistics', 
                        '001_add_missing_columns.sql')
                    """)
                    logger.info("Recorded migration version 1.1.0")
                else:
                    logger.info("Migration 1.1.0 already applied")
            
            conn.commit()
            logger.info("Migration 001 completed successfully")
    
    def check_database_status(self):
        """Check current database status"""
        logger.info(f"Checking database at: {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check search_queries columns
            if self.table_exists(conn, 'search_queries'):
                columns = self.get_table_columns(conn, 'search_queries')
                logger.info(f"search_queries columns: {columns}")
                
                # Count records
                cursor = conn.execute("SELECT COUNT(*) FROM search_queries")
                count = cursor.fetchone()[0]
                logger.info(f"search_queries records: {count}")
            else:
                logger.warning("search_queries table does not exist")
            
            # Check system_config
            if self.table_exists(conn, 'system_config'):
                columns = self.get_table_columns(conn, 'system_config')
                logger.info(f"system_config columns: {columns}")
            
            # Check schema version
            if self.table_exists(conn, 'schema_versions'):
                cursor = conn.execute(
                    "SELECT version_id, applied_at FROM schema_versions ORDER BY applied_at DESC LIMIT 5"
                )
                versions = cursor.fetchall()
                logger.info("Schema versions:")
                for v in versions:
                    logger.info(f"  - {v[0]} applied at {v[1]}")


def main():
    """Run migrations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--db-path", help="Database path")
    parser.add_argument("--check", action="store_true", help="Check database status")
    
    args = parser.parse_args()
    
    runner = MigrationRunner(args.db_path)
    
    if args.check:
        runner.check_database_status()
    else:
        runner.run_migration_001()
        runner.check_database_status()


if __name__ == "__main__":
    main()