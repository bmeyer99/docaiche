"""
Migration: Add Prompt Templates Table
=====================================

Adds the prompt_templates table for storing AI prompt templates
with version control.
"""

import logging
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def upgrade(conn):
    """Add prompt_templates table and indexes."""
    try:
        # Create prompt templates table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id TEXT PRIMARY KEY NOT NULL,
                prompt_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                version TEXT NOT NULL DEFAULT '1.0.0',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(prompt_type, version)
            )
        """))
        
        # Create indexes for performance
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prompt_templates_prompt_type 
            ON prompt_templates(prompt_type)
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prompt_templates_version 
            ON prompt_templates(version)
        """))
        
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prompt_templates_created_at 
            ON prompt_templates(created_at)
        """))
        
        logger.info("Successfully created prompt_templates table and indexes")
        
    except Exception as e:
        logger.error(f"Failed to create prompt_templates table: {e}")
        raise


async def downgrade(conn):
    """Remove prompt_templates table."""
    try:
        # Drop indexes first
        await conn.execute(text("DROP INDEX IF EXISTS idx_prompt_templates_prompt_type"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_prompt_templates_version"))
        await conn.execute(text("DROP INDEX IF EXISTS idx_prompt_templates_created_at"))
        
        # Drop table
        await conn.execute(text("DROP TABLE IF EXISTS prompt_templates"))
        
        logger.info("Successfully removed prompt_templates table")
        
    except Exception as e:
        logger.error(f"Failed to remove prompt_templates table: {e}")
        raise


# Migration metadata
migration_info = {
    "version": "004",
    "description": "Add prompt_templates table for AI prompt version control",
    "created_at": datetime(2025, 1, 4, 0, 0, 0),
    "author": "system"
}