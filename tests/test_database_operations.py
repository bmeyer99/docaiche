#!/usr/bin/env python3
"""
Test database operations with PostgreSQL
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def test_database_operations():
    """Test various database operations."""
    database_url = os.environ.get("DATABASE_URL", 
        "postgresql+asyncpg://docaiche:docaiche-secure-password-2025@postgres:5432/docaiche")
    
    print("Testing Database Operations")
    print("=" * 50)
    
    engine = create_async_engine(database_url)
    
    async with engine.begin() as conn:
        # Test 1: System Config (JSON operations)
        print("\n1. Testing system_config with JSONB:")
        
        # Insert config
        await conn.execute(text("""
            INSERT INTO system_config (key, value, updated_by)
            VALUES (:key, CAST(:value AS jsonb), :user)
        """), {
            "key": "search_settings",
            "value": json.dumps({
                "max_results": 100,
                "timeout": 30,
                "features": ["fuzzy", "semantic"]
            }),
            "user": "test_script"
        })
        print("  ✓ Insert with JSONB")
        
        # Query JSONB
        result = await conn.execute(text("""
            SELECT key, value->>'max_results' as max_results,
                   value->'features' as features
            FROM system_config WHERE key = :key
        """), {"key": "search_settings"})
        row = result.fetchone()
        print(f"  ✓ JSONB query: max_results={row.max_results}, features={row.features}")
        
        # Test 2: Search Cache with expiration
        print("\n2. Testing search_cache:")
        
        await conn.execute(text("""
            INSERT INTO search_cache 
            (query_hash, original_query, search_results, expires_at, technology_hint)
            VALUES (:hash, :query, CAST(:results AS jsonb), :expires, :tech)
        """), {
            "hash": "test_hash_123",
            "query": "postgresql tutorial",
            "results": json.dumps({"results": [{"title": "Test"}], "count": 1}),
            "expires": datetime.utcnow() + timedelta(hours=1),
            "tech": "postgresql"
        })
        print("  ✓ Insert with expiration")
        
        # Test 3: Content Metadata with enums
        print("\n3. Testing content_metadata with enums:")
        
        await conn.execute(text("""
            INSERT INTO content_metadata 
            (content_id, title, source_url, technology, content_hash, 
             processing_status, quality_score, metadata)
            VALUES (:id, :title, :url, :tech, :hash, 
                    CAST(:status AS processing_status), :score, CAST(:meta AS jsonb))
        """), {
            "id": "content_001",
            "title": "PostgreSQL Guide",
            "url": "https://example.com/pg-guide",
            "tech": "postgresql",
            "hash": "hash_abc123",
            "status": "completed",
            "score": 0.95,
            "meta": json.dumps({"author": "Test", "tags": ["database", "sql"]})
        })
        print("  ✓ Insert with enum and metadata")
        
        # Test 4: Transactions
        print("\n4. Testing transactions:")
        
        # This will be rolled back
        async with conn.begin_nested() as savepoint:
            await conn.execute(text("""
                INSERT INTO system_config (key, value)
                VALUES ('temp_config', '{"temp": true}'::jsonb)
            """))
            
            # Check it exists
            result = await conn.execute(text(
                "SELECT COUNT(*) as count FROM system_config WHERE key = 'temp_config'"
            ))
            count = result.scalar()
            print(f"  ✓ Within transaction: {count} temp record")
            
            # Rollback
            await savepoint.rollback()
        
        # Verify rollback
        result = await conn.execute(text(
            "SELECT COUNT(*) as count FROM system_config WHERE key = 'temp_config'"
        ))
        count = result.scalar()
        print(f"  ✓ After rollback: {count} temp records")
        
        # Test 5: Indexes performance
        print("\n5. Testing index usage:")
        
        # Add more test data
        for i in range(10):
            await conn.execute(text("""
                INSERT INTO content_metadata 
                (content_id, title, source_url, technology, content_hash, quality_score)
                VALUES (:id, :title, :url, :tech, :hash, :score)
            """), {
                "id": f"content_{i+100:03d}",
                "title": f"Document {i}",
                "url": f"https://example.com/doc{i}",
                "tech": "python" if i % 2 == 0 else "javascript",
                "hash": f"hash_{i:03d}",
                "score": 0.5 + (i * 0.05)
            })
        
        # Query using index
        result = await conn.execute(text("""
            SELECT content_id, title, quality_score
            FROM content_metadata
            WHERE technology = :tech AND quality_score > :score
            ORDER BY quality_score DESC
        """), {"tech": "python", "score": 0.7})
        
        rows = result.fetchall()
        print(f"  ✓ Index query returned {len(rows)} results")
        
        # Test 6: Foreign key constraints
        print("\n6. Testing foreign key constraints:")
        
        try:
            # This should fail - invalid content_id
            await conn.execute(text("""
                INSERT INTO feedback_events 
                (event_id, content_id, feedback_type)
                VALUES ('event_001', 'invalid_content_id', CAST('helpful' AS feedback_type))
            """))
            print("  ✗ Foreign key constraint not working!")
        except Exception as e:
            print("  ✓ Foreign key constraint enforced")
        
        # Valid insert
        await conn.execute(text("""
            INSERT INTO feedback_events 
            (event_id, content_id, feedback_type, rating)
            VALUES (:id, :content_id, CAST(:type AS feedback_type), :rating)
        """), {
            "id": "event_001",
            "content_id": "content_001",
            "type": "helpful",
            "rating": 5
        })
        print("  ✓ Valid foreign key insert")
        
    await engine.dispose()
    print("\n" + "=" * 50)
    print("All database operations completed successfully! ✅")


async def test_connection_pooling():
    """Test connection pooling behavior."""
    database_url = os.environ.get("DATABASE_URL", 
        "postgresql+asyncpg://docaiche:docaiche-secure-password-2025@postgres:5432/docaiche")
    
    print("\n\nTesting Connection Pooling")
    print("=" * 50)
    
    # Create engine with specific pool settings
    engine = create_async_engine(
        database_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True
    )
    
    # Simulate concurrent connections
    async def query_task(task_id):
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT :id as task_id, pg_backend_pid() as pid"), {"id": task_id})
            row = result.fetchone()
            return f"Task {row.task_id}: PID {row.pid}"
    
    # Run multiple concurrent queries
    tasks = [query_task(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    for result in results:
        print(f"  {result}")
    
    await engine.dispose()
    print("\nConnection pooling test completed! ✅")


if __name__ == "__main__":
    asyncio.run(test_database_operations())
    asyncio.run(test_connection_pooling())