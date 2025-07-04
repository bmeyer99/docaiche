#!/usr/bin/env python3
"""
Test script to verify TTL fields are present in content_metadata table.
"""

import os
import asyncio
import logging
from sqlalchemy import create_engine, text, inspect

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ttl_fields():
    """Test that TTL fields are present in the content_metadata table."""
    
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        # Build PostgreSQL URL from environment variables
        host = os.environ.get("POSTGRES_HOST", "postgres")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "docaiche")
        user = os.environ.get("POSTGRES_USER", "docaiche")
        password = os.environ.get("POSTGRES_PASSWORD", "docaiche-secure-password-2025")
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    # Remove async drivers for synchronous connection
    sync_url = database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    
    try:
        # Create synchronous engine
        engine = create_engine(sync_url)
        
        with engine.begin() as conn:
            # Check if content_metadata table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'content_metadata'
                )
            """))
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                logger.error("content_metadata table does not exist")
                return False
            
            # Check if TTL columns exist
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'content_metadata' 
                AND column_name IN ('expires_at', 'source_provider')
                ORDER BY column_name
            """))
            columns = result.fetchall()
            
            expected_columns = {
                'expires_at': 'timestamp without time zone',
                'source_provider': 'text'
            }
            
            found_columns = {}
            for col in columns:
                found_columns[col[0]] = col[1]
            
            # Verify both columns exist with correct types
            for col_name, expected_type in expected_columns.items():
                if col_name not in found_columns:
                    logger.error(f"Column {col_name} not found in content_metadata table")
                    return False
                
                # PostgreSQL may return different variations of the type name
                actual_type = found_columns[col_name]
                if col_name == 'expires_at' and 'timestamp' not in actual_type.lower():
                    logger.error(f"Column {col_name} has wrong type: {actual_type}, expected timestamp")
                    return False
                elif col_name == 'source_provider' and actual_type.lower() != 'text':
                    logger.error(f"Column {col_name} has wrong type: {actual_type}, expected text")
                    return False
                
                logger.info(f"✓ Column {col_name} found with type {actual_type}")
            
            # Check if indexes exist
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE indexname IN (
                    'idx_content_metadata_expires_at',
                    'idx_content_metadata_source_provider'
                )
                ORDER BY indexname
            """))
            indexes = [row[0] for row in result.fetchall()]
            
            expected_indexes = [
                'idx_content_metadata_expires_at',
                'idx_content_metadata_source_provider'
            ]
            
            for index_name in expected_indexes:
                if index_name in indexes:
                    logger.info(f"✓ Index {index_name} found")
                else:
                    logger.error(f"Index {index_name} not found")
                    return False
            
            logger.info("All TTL fields and indexes are properly configured!")
            return True
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ttl_fields())
    if success:
        print("\n✅ TTL schema test PASSED")
        exit(0)
    else:
        print("\n❌ TTL schema test FAILED")
        exit(1)