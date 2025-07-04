#!/usr/bin/env python3
"""
Test PostgreSQL connection and basic operations
"""

import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine


async def test_async_connection():
    """Test async PostgreSQL connection."""
    database_url = os.environ.get("DATABASE_URL", 
        "postgresql+asyncpg://docaiche:docaiche-secure-password-2025@postgres:5432/docaiche")
    
    print(f"Testing async connection to: {database_url.split('@')[1]}")
    
    try:
        # Create async engine
        engine = create_async_engine(database_url)
        
        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ Connected successfully!")
            print(f"  PostgreSQL version: {version}")
            
            # Test table creation
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ Table creation works")
            
            # Test insert
            await conn.execute(text("""
                INSERT INTO test_table (name, data) 
                VALUES (:name, CAST(:data AS jsonb))
            """), {"name": "test_item", "data": '{"key": "value"}'})
            print("✓ Insert works")
            
            # Test select
            result = await conn.execute(text("SELECT * FROM test_table"))
            rows = result.fetchall()
            print(f"✓ Select works - found {len(rows)} rows")
            
            # Test JSONB operations
            result = await conn.execute(text("""
                SELECT data->>'key' as key_value FROM test_table
            """))
            jsonb_result = result.scalar()
            print(f"✓ JSONB operations work - value: {jsonb_result}")
            
            # Clean up
            await conn.execute(text("DROP TABLE test_table"))
            print("✓ Cleanup complete")
            
        await engine.dispose()
        print("\n✅ All async tests passed!")
        
    except Exception as e:
        print(f"\n❌ Async test failed: {e}")
        raise


def test_sync_connection():
    """Test sync PostgreSQL connection for migrations."""
    database_url = os.environ.get("DATABASE_URL", 
        "postgresql://docaiche:docaiche-secure-password-2025@postgres:5432/docaiche")
    
    # Remove async driver for sync connection
    sync_url = database_url.replace("+asyncpg", "")
    
    print(f"\nTesting sync connection to: {sync_url.split('@')[1]}")
    
    try:
        # Create sync engine
        engine = create_engine(sync_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Sync connection works")
            
            # List existing tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            print(f"✓ Found {len(tables)} tables: {tables}")
            
        engine.dispose()
        print("\n✅ All sync tests passed!")
        
    except Exception as e:
        print(f"\n❌ Sync test failed: {e}")
        raise


async def main():
    """Run all tests."""
    print("PostgreSQL Connection Test")
    print("=" * 50)
    
    # Test sync connection first (used by migrations)
    test_sync_connection()
    
    # Test async connection (used by application)
    await test_async_connection()
    
    print("\n" + "=" * 50)
    print("All tests completed successfully! ✅")


if __name__ == "__main__":
    asyncio.run(main())