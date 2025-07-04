#!/usr/bin/env python3
"""
Migration script from SQLite to PostgreSQL
Transfers all data while preserving relationships and converting data types
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SQLiteToPostgresMigrator:
    """Migrate data from SQLite to PostgreSQL."""
    
    def __init__(self, sqlite_path: str, postgres_url: str):
        """Initialize migrator with database connections."""
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url.replace("+asyncpg", "").replace("+aiosqlite", "")
        
        # Table migration order (respects foreign key dependencies)
        self.table_order = [
            # Independent tables first
            'system_config',
            'schema_versions',
            'technology_mappings',
            'source_metadata',
            'configuration_audit_log',
            
            # Tables with content_id
            'content_metadata',
            'document_metadata',
            'processed_documents',
            
            # Dependent tables
            'feedback_events',
            'usage_signals',
            'document_chunks',
            
            # Cache and search tables
            'search_cache',
            
            # AI logging tables
            'ai_log_entries',
            'ai_pattern_detections',
        ]
    
    def migrate(self):
        """Execute the migration process."""
        logger.info("Starting SQLite to PostgreSQL migration...")
        
        # Check if SQLite database exists
        if not os.path.exists(self.sqlite_path):
            logger.error(f"SQLite database not found: {self.sqlite_path}")
            return False
        
        # SQLite connection has been removed
        logger.error("SQLite is no longer supported. Cannot migrate from SQLite.")
        return False
        
        pg_engine = create_engine(self.postgres_url, poolclass=NullPool)
        
        try:
            # Get list of tables from SQLite
            sqlite_tables = self._get_sqlite_tables(sqlite_conn)
            logger.info(f"Found {len(sqlite_tables)} tables in SQLite database")
            
            # Initialize PostgreSQL schema
            logger.info("Initializing PostgreSQL schema...")
            from src.database.init_db_postgres import PostgreSQLInitializer
            pg_init = PostgreSQLInitializer(self.postgres_url)
            pg_init.initialize_database(force_recreate=False)
            
            # Migrate each table
            with pg_engine.begin() as pg_conn:
                # Disable foreign key checks during migration
                pg_conn.execute(text("SET session_replication_role = replica;"))
                
                for table_name in self.table_order:
                    if table_name in sqlite_tables:
                        self._migrate_table(sqlite_conn, pg_conn, table_name)
                
                # Re-enable foreign key checks
                pg_conn.execute(text("SET session_replication_role = DEFAULT;"))
            
            # Verify migration
            self._verify_migration(sqlite_conn, pg_engine)
            
            logger.info("Migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            sqlite_conn.close()
            pg_engine.dispose()
    
    def _get_sqlite_tables(self, conn) -> List[str]:
        """Get list of tables from SQLite database."""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row['name'] for row in cursor]
    
    def _migrate_table(self, sqlite_conn, pg_conn, table_name: str):
        """Migrate a single table from SQLite to PostgreSQL."""
        logger.info(f"Migrating table: {table_name}")
        
        # Get row count
        count_cursor = sqlite_conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        row_count = count_cursor.fetchone()['count']
        
        if row_count == 0:
            logger.info(f"  Table {table_name} is empty, skipping...")
            return
        
        logger.info(f"  Found {row_count} rows to migrate")
        
        # Get all rows from SQLite
        cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            return
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        # Prepare insert statement
        placeholders = ', '.join([f":{col}" for col in columns])
        insert_sql = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """
        
        # Migrate rows in batches
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            batch_data = []
            
            for row in batch:
                row_dict = {}
                for col in columns:
                    value = row[col]
                    
                    # Convert SQLite types to PostgreSQL types
                    if isinstance(value, str):
                        # Try to parse JSON strings
                        if col in ['value', 'search_results', 'workspace_slugs', 'changes', 
                                  'previous_values', 'file_patterns', 'chunks', 'metadata',
                                  'affected_services', 'sample_traces']:
                            try:
                                value = json.loads(value) if value else None
                            except json.JSONDecodeError:
                                pass
                    
                    # Convert SQLite boolean (0/1) to PostgreSQL boolean
                    elif col in ['cache_hit', 'is_active', 'is_official'] and value is not None:
                        value = bool(value)
                    
                    # Handle timestamps
                    elif col in ['created_at', 'updated_at', 'expires_at', 'last_accessed_at',
                                'timestamp', 'applied_at', 'last_updated', 'last_successful_fetch',
                                'last_failed_fetch', 'rate_limit_reset_at', 'processed_at',
                                'first_seen', 'last_seen']:
                        if value and isinstance(value, str):
                            try:
                                # Parse various timestamp formats
                                for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
                                          '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
                                    try:
                                        value = datetime.strptime(value, fmt)
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass
                    
                    # Handle enum conversions
                    elif col == 'processing_status' and value:
                        # Map SQLite text to PostgreSQL enum
                        if value not in ['pending', 'processing', 'completed', 'failed', 
                                       'flagged', 'pending_context7']:
                            value = 'pending'  # Default
                    
                    row_dict[col] = value
                
                batch_data.append(row_dict)
            
            # Execute batch insert
            try:
                pg_conn.execute(text(insert_sql), batch_data)
                logger.info(f"  Migrated {min(i + batch_size, len(rows))}/{len(rows)} rows")
            except Exception as e:
                logger.error(f"  Error migrating batch: {e}")
                # Try individual inserts for this batch
                for row_dict in batch_data:
                    try:
                        pg_conn.execute(text(insert_sql), [row_dict])
                    except Exception as row_error:
                        logger.error(f"  Failed to migrate row: {row_error}")
                        logger.debug(f"  Row data: {row_dict}")
    
    def _verify_migration(self, sqlite_conn, pg_engine):
        """Verify that migration was successful."""
        logger.info("\nVerifying migration...")
        
        with pg_engine.connect() as pg_conn:
            for table_name in self.table_order:
                # Get counts from both databases
                try:
                    # SQLite count check has been removed
                    sqlite_count = 0
                except Exception:
                    # Table doesn't exist
                    continue
                
                try:
                    pg_result = pg_conn.execute(text(f"SELECT COUNT(*) as count FROM {table_name}"))
                    pg_count = pg_result.fetchone().count
                except Exception:
                    pg_count = 0
                
                if sqlite_count == pg_count:
                    logger.info(f"✓ {table_name}: {sqlite_count} rows")
                else:
                    logger.warning(f"✗ {table_name}: SQLite={sqlite_count}, PostgreSQL={pg_count}")


def main():
    """Main entry point for migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate DocAIche from SQLite to PostgreSQL")
    parser.add_argument(
        "--sqlite-path",
        default="/data/docaiche.db",
        help="Path to SQLite database (default: /data/docaiche.db)"
    )
    parser.add_argument(
        "--postgres-url",
        default=None,
        help="PostgreSQL connection URL (default: from DATABASE_URL env var)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify migration, don't migrate data"
    )
    
    args = parser.parse_args()
    
    # Get PostgreSQL URL
    postgres_url = args.postgres_url or os.environ.get("DATABASE_URL")
    if not postgres_url:
        logger.error("PostgreSQL URL not provided. Set DATABASE_URL environment variable or use --postgres-url")
        sys.exit(1)
    
    # Create migrator
    migrator = SQLiteToPostgresMigrator(args.sqlite_path, postgres_url)
    
    # Execute migration
    if args.verify_only:
        logger.info("Verification mode - checking existing data...")
        # Just verify
        # SQLite connection has been removed
        logger.error("SQLite is no longer supported. Cannot verify migration.")
        sys.exit(1)
        pg_engine = create_engine(postgres_url.replace("+asyncpg", "").replace("+aiosqlite", ""))
        migrator._verify_migration(sqlite_conn, pg_engine)
        sqlite_conn.close()
        pg_engine.dispose()
    else:
        success = migrator.migrate()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()