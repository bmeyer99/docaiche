#!/usr/bin/env python3
"""
Optimize database performance by adding indexes to frequently queried columns.
"""

import asyncio
import logging
from sqlalchemy import text
from src.database.connection import DatabaseManager
from src.core.config import get_system_configuration

logger = logging.getLogger(__name__)

async def create_indexes():
    """Create indexes for better query performance."""
    config = get_system_configuration()
    db_manager = DatabaseManager(config)
    
    indexes = [
        # Content metadata indexes
        ("idx_content_metadata_content_id", "content_metadata", "content_id"),
        ("idx_content_metadata_technology", "content_metadata", "technology"),
        ("idx_content_metadata_created_at", "content_metadata", "created_at"),
        ("idx_content_metadata_weaviate_workspace", "content_metadata", "weaviate_workspace"),
        
        # Search cache indexes
        ("idx_search_cache_original_query", "search_cache", "original_query"),
        ("idx_search_cache_created_at", "search_cache", "created_at"),
        ("idx_search_cache_access_count", "search_cache", "access_count"),
        
        # Usage signals indexes
        ("idx_usage_signals_user_session_id", "usage_signals", "user_session_id"),
        ("idx_usage_signals_created_at", "usage_signals", "created_at"),
        
        # Provider configurations indexes
        ("idx_provider_configurations_name", "provider_configurations", "name"),
        ("idx_provider_configurations_enabled", "provider_configurations", "enabled"),
        
        # Composite indexes for common queries
        ("idx_content_metadata_tech_created", "content_metadata", "technology, created_at"),
        ("idx_search_cache_query_created", "search_cache", "original_query, created_at"),
    ]
    
    async with db_manager.get_session() as session:
        for index_name, table_name, columns in indexes:
            try:
                # Check if index already exists
                check_query = text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name=:index_name
                """)
                result = await session.execute(check_query, {"index_name": index_name})
                if result.scalar():
                    logger.info(f"Index {index_name} already exists")
                    continue
                
                # Create index
                create_query = text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} ({columns})
                """)
                await session.execute(create_query)
                await session.commit()
                logger.info(f"Created index {index_name} on {table_name}({columns})")
                
            except Exception as e:
                logger.error(f"Failed to create index {index_name}: {e}")
                await session.rollback()
        
        # Analyze tables to update statistics
        try:
            await session.execute(text("ANALYZE"))
            await session.commit()
            logger.info("Updated database statistics")
        except Exception as e:
            logger.error(f"Failed to analyze database: {e}")

async def main():
    """Main function to run index optimization."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting database index optimization...")
    
    try:
        await create_indexes()
        logger.info("Database index optimization completed successfully")
    except Exception as e:
        logger.error(f"Database index optimization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())