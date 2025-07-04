"""
Database migration to add configuration audit log table.
Migration version: 003

This migration adds a table for tracking configuration changes,
providing an audit trail for all system configuration modifications.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

MIGRATION_VERSION = "3.0.0"
MIGRATION_DESCRIPTION = "Add configuration audit log table"


def upgrade(conn) -> None:
    """Apply migration to add configuration audit log table."""
    logger.info(f"Applying migration {MIGRATION_VERSION}: {MIGRATION_DESCRIPTION}")
    
    cursor = conn.cursor()
    
    # Create configuration_audit_log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuration_audit_log (
            id TEXT PRIMARY KEY,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user TEXT NOT NULL,
            section TEXT NOT NULL,
            changes JSONB NOT NULL,
            previous_values JSONB NOT NULL,
            comment TEXT
        )
    """)
    
    # Create indices for efficient querying
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_config_audit_timestamp 
        ON configuration_audit_log(timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_config_audit_user 
        ON configuration_audit_log(user)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_config_audit_section 
        ON configuration_audit_log(section)
    """)
    
    conn.commit()
    logger.info(f"Migration {MIGRATION_VERSION} applied successfully")


def downgrade(conn) -> None:
    """Rollback migration to remove configuration audit log table."""
    logger.info(f"Rolling back migration {MIGRATION_VERSION}")
    
    cursor = conn.cursor()
    
    # Drop indices
    cursor.execute("DROP INDEX IF EXISTS idx_config_audit_timestamp")
    cursor.execute("DROP INDEX IF EXISTS idx_config_audit_user")
    cursor.execute("DROP INDEX IF EXISTS idx_config_audit_section")
    
    # Drop table
    cursor.execute("DROP TABLE IF EXISTS configuration_audit_log")
    
    conn.commit()
    logger.info(f"Migration {MIGRATION_VERSION} rolled back successfully")


def validate(conn) -> bool:
    """Validate that migration was applied correctly."""
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'configuration_audit_log'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.error("configuration_audit_log table not found")
            return False
        
        # Check if indices exist
        cursor.execute("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE indexname IN (
                'idx_config_audit_timestamp',
                'idx_config_audit_user', 
                'idx_config_audit_section'
            )
        """)
        index_count = cursor.fetchone()[0]
        
        if index_count != 3:
            logger.error("Not all required indices found")
            return False
        
        logger.info(f"Migration {MIGRATION_VERSION} validation successful")
        return True
        
    except Exception as e:
        logger.error(f"Migration validation failed: {e}")
        return False