#!/usr/bin/env python3
"""
TTL Schema Verification Script

This script verifies that the TTL database schema changes have been implemented correctly:
1. expires_at column exists in content_metadata table with TIMESTAMP type
2. source_provider column exists in content_metadata table with TEXT type
3. Appropriate indexes were created for performance
4. Schema consistency across all database files
"""

import os
import asyncio
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TTLSchemaVerifier:
    """Verifies TTL schema changes in the database."""
    
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL", "postgresql://docaiche:docaiche@localhost:5432/docaiche")
        self.sync_url = self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
        self.engine = create_engine(self.sync_url)
        
    def verify_schema_changes(self):
        """Verify all TTL schema changes."""
        logger.info("Starting TTL schema verification...")
        
        try:
            with self.engine.begin() as conn:
                # Test 1: Check expires_at column exists with correct type
                self._verify_expires_at_column(conn)
                
                # Test 2: Check source_provider column exists with correct type
                self._verify_source_provider_column(conn)
                
                # Test 3: Check indexes were created
                self._verify_indexes(conn)
                
                # Test 4: Check schema consistency
                self._verify_schema_consistency(conn)
                
                logger.info("✅ All TTL schema verification tests passed!")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Database verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during verification: {e}")
            return False
    
    def _verify_expires_at_column(self, conn):
        """Verify expires_at column exists with correct type."""
        logger.info("Checking expires_at column...")
        
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'content_metadata' 
            AND column_name = 'expires_at'
        """)).fetchone()
        
        if not result:
            raise ValueError("expires_at column not found in content_metadata table")
            
        if result[1] != 'timestamp without time zone':
            raise ValueError(f"expires_at column has wrong type: {result[1]}, expected: timestamp without time zone")
            
        if result[2] != 'YES':
            raise ValueError(f"expires_at column should be nullable, got: {result[2]}")
            
        logger.info("✅ expires_at column verified: TIMESTAMP type, nullable")
    
    def _verify_source_provider_column(self, conn):
        """Verify source_provider column exists with correct type."""
        logger.info("Checking source_provider column...")
        
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'content_metadata' 
            AND column_name = 'source_provider'
        """)).fetchone()
        
        if not result:
            raise ValueError("source_provider column not found in content_metadata table")
            
        if result[1] != 'text':
            raise ValueError(f"source_provider column has wrong type: {result[1]}, expected: text")
            
        if result[2] != 'YES':
            raise ValueError(f"source_provider column should be nullable, got: {result[2]}")
            
        logger.info("✅ source_provider column verified: TEXT type, nullable")
    
    def _verify_indexes(self, conn):
        """Verify that appropriate indexes were created."""
        logger.info("Checking TTL indexes...")
        
        # Check expires_at index
        result = conn.execute(text("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'content_metadata' 
            AND indexname = 'idx_content_metadata_expires_at'
        """)).fetchone()
        
        if not result:
            raise ValueError("idx_content_metadata_expires_at index not found")
            
        logger.info("✅ expires_at index verified")
        
        # Check source_provider index
        result = conn.execute(text("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'content_metadata' 
            AND indexname = 'idx_content_metadata_source_provider'
        """)).fetchone()
        
        if not result:
            raise ValueError("idx_content_metadata_source_provider index not found")
            
        logger.info("✅ source_provider index verified")
    
    def _verify_schema_consistency(self, conn):
        """Verify schema consistency across database files."""
        logger.info("Checking schema consistency...")
        
        # Check that schema version is recorded
        result = conn.execute(text("""
            SELECT version_id, description 
            FROM schema_versions 
            ORDER BY applied_at DESC 
            LIMIT 1
        """)).fetchone()
        
        if not result:
            raise ValueError("No schema version found")
            
        logger.info(f"✅ Schema version: {result[0]} - {result[1]}")
        
        # Check total column count in content_metadata
        result = conn.execute(text("""
            SELECT COUNT(*) as column_count
            FROM information_schema.columns 
            WHERE table_name = 'content_metadata'
        """)).fetchone()
        
        expected_columns = 21  # Based on current schema
        if result[0] != expected_columns:
            raise ValueError(f"Expected {expected_columns} columns, found {result[0]}")
            
        logger.info(f"✅ Schema consistency verified: {result[0]} columns in content_metadata")
    
    def run_sample_queries(self):
        """Run sample queries to test TTL functionality."""
        logger.info("Running sample TTL queries...")
        
        try:
            with self.engine.begin() as conn:
                # Sample query 1: Find expired content
                conn.execute(text("""
                    SELECT COUNT(*) as expired_count
                    FROM content_metadata 
                    WHERE expires_at < NOW()
                """))
                
                # Sample query 2: Find content by source provider
                conn.execute(text("""
                    SELECT COUNT(*) as provider_count
                    FROM content_metadata 
                    WHERE source_provider = 'github'
                """))
                
                # Sample query 3: Complex query using both TTL columns
                conn.execute(text("""
                    SELECT technology, source_provider, COUNT(*) as count
                    FROM content_metadata 
                    WHERE expires_at IS NULL OR expires_at > NOW()
                    GROUP BY technology, source_provider
                    LIMIT 10
                """))
                
                logger.info("✅ Sample TTL queries executed successfully")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Sample queries failed: {e}")
            return False

def main():
    """Main verification function."""
    verifier = TTLSchemaVerifier()
    
    # Run schema verification
    schema_ok = verifier.verify_schema_changes()
    
    # Run sample queries
    queries_ok = verifier.run_sample_queries()
    
    if schema_ok and queries_ok:
        logger.info("🎉 TTL schema verification completed successfully!")
        logger.info("The database is ready for TTL implementation.")
        return 0
    else:
        logger.error("❌ TTL schema verification failed!")
        return 1

if __name__ == "__main__":
    exit(main())