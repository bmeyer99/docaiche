"""
PRD-002 Database & Caching Layer RE-VALIDATION Test Suite
Post System Debugger Fixes - Comprehensive Security & Integration Testing

This test suite validates that all 4 critical security issues have been resolved:
1. SQL injection prevention via proper parameter binding
2. Foreign key constraints enabled across all connections
3. CFG-001 configuration integration fixed
4. Redis graceful degradation implemented

Target: 28/28 tests passing (improvement from 21/28)
"""

import pytest
import tempfile
import os
import sqlite3
import asyncio
import json
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, AsyncMock

from src.database.init_db import DatabaseInitializer
from src.database.connection import (
    DatabaseManager, CacheManager, create_database_manager, create_cache_manager,
    DocumentMetadata, DocumentChunk, ProcessedDocument
)


class TestCriticalSecurityFixes:
    """
    CRITICAL: Test all 4 security fixes identified by System Debugger
    These tests must ALL PASS for production approval
    """

    @pytest.mark.asyncio
    async def test_sql_injection_prevention_fixed(self):
        """TEST-S001-REVALIDATE: Verify SQL injection vulnerability is eliminated"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            try:
                # Test that parameter binding properly prevents SQL injection
                malicious_input = "'; DROP TABLE content_metadata; --"
                
                # This should execute safely with proper parameter binding
                result = await manager.fetch_all(
                    "SELECT * FROM content_metadata WHERE title = ?",
                    (malicious_input,)
                )
                
                # Should execute without error (empty result set expected)
                assert isinstance(result, list), "Query should return list even with malicious input"
                
                # Verify table still exists and wasn't dropped
                table_check = await manager.fetch_one(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='content_metadata'"
                )
                assert table_check is not None, "CRITICAL: Table was dropped - SQL injection succeeded!"
                assert table_check[0] == "content_metadata", "Table integrity compromised"
                
                # Test parameter binding with multiple parameters
                await manager.execute(
                    "INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                    ("test_id", "Test Title", "http://test.com", "python", "hash123")
                )
                
                # Verify data was inserted correctly
                inserted = await manager.fetch_one(
                    "SELECT title FROM content_metadata WHERE content_id = ?",
                    ("test_id",)
                )
                assert inserted[0] == "Test Title", "Parameter binding failed for INSERT"
                
            finally:
                await manager.disconnect()

    @pytest.mark.asyncio 
    async def test_foreign_key_constraints_enabled_fixed(self):
        """TEST-S002-REVALIDATE: Verify foreign key constraints are properly enabled"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            try:
                # Verify foreign keys are enabled
                result = await manager.fetch_one("PRAGMA foreign_keys")
                assert result[0] == 1, "CRITICAL: Foreign keys not enabled - referential integrity at risk"
                
                # Test foreign key constraint enforcement
                with pytest.raises(Exception):  # Should raise integrity error
                    await manager.execute(
                        "INSERT INTO feedback_events (event_id, content_id, feedback_type) VALUES (?, ?, ?)",
                        ("event1", "nonexistent_content", "helpful")
                    )
                
                # Create parent record first
                await manager.execute(
                    "INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                    ("content1", "Test", "http://test.com", "python", "hash1")
                )
                
                # Now foreign key insert should succeed
                await manager.execute(
                    "INSERT INTO feedback_events (event_id, content_id, feedback_type) VALUES (?, ?, ?)",
                    ("event1", "content1", "helpful")
                )
                
                # Verify cascade delete works
                await manager.execute(
                    "DELETE FROM content_metadata WHERE content_id = ?",
                    ("content1",)
                )
                
                # Feedback event should be cascaded deleted
                feedback_count = await manager.fetch_one(
                    "SELECT COUNT(*) FROM feedback_events WHERE content_id = ?",
                    ("content1",)
                )
                assert feedback_count[0] == 0, "CASCADE DELETE not working - foreign key integrity compromised"
                
            finally:
                await manager.disconnect()

    @pytest.mark.asyncio
    async def test_cfg001_configuration_integration_fixed(self):
        """TEST-I001-REVALIDATE: Verify CFG-001 configuration integration works"""
        # Mock successful configuration
        mock_config = MagicMock()
        mock_config.app.data_dir = "/test/data"
        mock_config.redis.host = "test-redis"
        mock_config.redis.port = 6380
        mock_config.redis.password = "test-password"
        mock_config.redis.db = 2
        mock_config.redis.max_connections = 50
        mock_config.redis.connection_timeout = 10
        mock_config.redis.socket_timeout = 10
        mock_config.redis.ssl = True
        
        # Test that configuration import works
        with patch('src.database.connection.get_system_configuration', return_value=mock_config):
            # Should not raise ImportError or AttributeError
            db_manager = await create_database_manager()
            cache_manager = await create_cache_manager()
            
            # Verify configuration is used
            assert "/test/data/docaiche.db" in db_manager.database_url
            assert cache_manager.redis_config["host"] == "test-redis"
            assert cache_manager.redis_config["port"] == 6380
            assert cache_manager.redis_config["password"] == "test-password"
            assert cache_manager.redis_config["ssl"] is True
        
        # Test graceful fallback when configuration fails
        with patch('src.database.connection.get_system_configuration', side_effect=Exception("Config error")):
            db_manager = await create_database_manager()
            cache_manager = await create_cache_manager()
            
            # Should use fallback defaults
            assert "/app/data/docaiche.db" in db_manager.database_url
            assert cache_manager.redis_config["host"] == "redis"
            assert cache_manager.redis_config["port"] == 6379

    @pytest.mark.asyncio
    async def test_redis_graceful_degradation_fixed(self):
        """TEST-E002-REVALIDATE: Verify Redis graceful degradation is implemented"""
        redis_config = {
            "host": "nonexistent-redis-server",
            "port": 6379,
            "db": 0,
            "connection_timeout": 1,
            "socket_timeout": 1
        }
        
        cache_manager = CacheManager(redis_config)
        
        # All operations should handle connection failures gracefully
        
        # GET operation should return None on failure, not raise exception
        result = await cache_manager.get("test_key")
        assert result is None, "GET should return None on Redis failure, not raise exception"
        
        # SET operation should not raise exception
        try:
            await cache_manager.set("test_key", "test_value", 60)
            # Should complete without exception (logs warning but continues)
        except Exception as e:
            pytest.fail(f"SET should not raise exception on Redis failure: {e}")
        
        # DELETE operation should not raise exception
        try:
            await cache_manager.delete("test_key")
            # Should complete without exception
        except Exception as e:
            pytest.fail(f"DELETE should not raise exception on Redis failure: {e}")
        
        # INCREMENT should return default value on failure
        result = await cache_manager.increment("counter_key")
        assert result == 1, "INCREMENT should return default value 1 on Redis failure"
        
        # EXPIRE should not raise exception
        try:
            await cache_manager.expire("test_key", 60)
            # Should complete without exception
        except Exception as e:
            pytest.fail(f"EXPIRE should not raise exception on Redis failure: {e}")
        
        # Health check should report unhealthy but not crash
        health = await cache_manager.health_check()
        assert health["status"] == "unhealthy", "Health check should report unhealthy status"
        assert health["connected"] is False, "Health check should show not connected"
        assert "error" in health, "Health check should include error details"


class TestFunctionalRequirementsRevalidation:
    """
    Re-validate all functional requirements to ensure fixes didn't break anything
    """

    def test_all_required_tables_created(self):
        """TEST-F001-REVALIDATE: Verify all 8 required tables still exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = [
                'system_config', 'search_cache', 'content_metadata', 
                'feedback_events', 'usage_signals', 'source_metadata', 
                'technology_mappings', 'schema_versions'
            ]
            
            for table in required_tables:
                assert table in tables, f"Required table '{table}' missing after fixes"
            
            assert len(tables) == 8, f"Expected 8 tables, found {len(tables)}"
            conn.close()

    @pytest.mark.asyncio
    async def test_database_operations_work_correctly(self):
        """TEST-F002-REVALIDATE: Verify all database operations work with fixed parameter binding"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            try:
                # Test INSERT
                await manager.execute(
                    "INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                    ("test1", "Test Title", "http://test.com", "python", "hash1")
                )
                
                # Test SELECT fetch_one
                result = await manager.fetch_one(
                    "SELECT title FROM content_metadata WHERE content_id = ?",
                    ("test1",)
                )
                assert result[0] == "Test Title"
                
                # Test SELECT fetch_all
                results = await manager.fetch_all(
                    "SELECT content_id FROM content_metadata WHERE technology = ?",
                    ("python",)
                )
                assert len(results) == 1
                assert results[0][0] == "test1"
                
                # Test UPDATE
                await manager.execute(
                    "UPDATE content_metadata SET title = ? WHERE content_id = ?",
                    ("Updated Title", "test1")
                )
                
                updated = await manager.fetch_one(
                    "SELECT title FROM content_metadata WHERE content_id = ?",
                    ("test1",)
                )
                assert updated[0] == "Updated Title"
                
                # Test transaction
                success = await manager.execute_transaction([
                    ("INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                     ("test2", "Transaction Test", "http://test2.com", "javascript", "hash2")),
                    ("UPDATE content_metadata SET title = ? WHERE content_id = ?",
                     ("Transaction Updated", "test2"))
                ])
                assert success is True
                
                # Verify transaction worked
                final = await manager.fetch_one(
                    "SELECT title FROM content_metadata WHERE content_id = ?",
                    ("test2",)
                )
                assert final[0] == "Transaction Updated"
                
            finally:
                await manager.disconnect()


class TestPerformanceRevalidation:
    """
    Re-validate performance features to ensure fixes maintain performance
    """

    @pytest.mark.asyncio
    async def test_async_connection_pooling_still_works(self):
        """TEST-P001-REVALIDATE: Verify async connection pooling after fixes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            try:
                # Verify pool configuration
                assert manager.engine is not None
                assert manager.session_factory is not None
                
                # Test concurrent operations
                async def test_query(i):
                    await manager.execute(
                        "INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                        (f"test_{i}", f"Title {i}", f"http://test{i}.com", "python", f"hash_{i}")
                    )
                    return await manager.fetch_one(
                        "SELECT title FROM content_metadata WHERE content_id = ?",
                        (f"test_{i}",)
                    )
                
                # Run concurrent operations
                tasks = [test_query(i) for i in range(5)]
                results = await asyncio.gather(*tasks)
                
                # All should succeed
                assert len(results) == 5
                for i, result in enumerate(results):
                    assert result[0] == f"Title {i}"
                
            finally:
                await manager.disconnect()

    @pytest.mark.asyncio
    async def test_index_effectiveness_now_works(self):
        """TEST-P002-REVALIDATE: Verify index testing works with fixed parameter binding"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Insert test data using proper parameter binding
            conn = sqlite3.connect(db_path)
            for i in range(50):
                conn.execute(
                    "INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                    (f'content_{i}', f'Title {i}', f'http://test{i}.com', 'python', f'hash_{i}')
                )
            conn.commit()
            conn.close()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            try:
                # Test query that should use index
                result = await manager.fetch_all(
                    "EXPLAIN QUERY PLAN SELECT * FROM content_metadata WHERE technology = ?",
                    ('python',)
                )
                
                query_plan = ' '.join([str(row) for row in result])
                
                # Should use index (exact text varies by SQLite version)
                assert ('idx_content_metadata_technology' in query_plan or 
                       'USING INDEX' in query_plan or
                       'INDEX' in query_plan), f"Index not being used: {query_plan}"
                
                # Test actual query performance with index
                data_result = await manager.fetch_all(
                    "SELECT COUNT(*) FROM content_metadata WHERE technology = ?",
                    ('python',)
                )
                assert data_result[0][0] == 50, "Query should return correct count"
                
            finally:
                await manager.disconnect()


class TestOperationalRevalidation:
    """
    Re-validate operational features to ensure production readiness
    """

    @pytest.mark.asyncio
    async def test_health_checks_still_work(self):
        """TEST-O001-REVALIDATE: Verify health checks work after fixes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            
            # Test database health check
            health = await manager.health_check()
            assert health["status"] == "healthy"
            assert health["connected"] is True
            assert health["test_query"] == 1
            assert "[REDACTED]" in health["database_url"]
        
        # Test cache health check with invalid Redis
        redis_config = {"host": "invalid-redis", "port": 6379, "db": 0}
        cache_manager = CacheManager(redis_config)
        
        health = await cache_manager.health_check()
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health

    @pytest.mark.asyncio
    async def test_transaction_context_manager_works(self):
        """TEST-O002-REVALIDATE: Verify transaction context manager works with fixes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            try:
                # Test successful transaction
                async with manager.transaction() as session:
                    from sqlalchemy import text
                    await session.execute(
                        text("INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (:id, :title, :url, :tech, :hash)"),
                        {"id": "test1", "title": "Test", "url": "http://test.com", "tech": "python", "hash": "hash1"}
                    )
                
                # Verify data was committed
                result = await manager.fetch_one(
                    "SELECT title FROM content_metadata WHERE content_id = ?",
                    ("test1",)
                )
                assert result[0] == "Test"
                
                # Test transaction rollback on error
                try:
                    async with manager.transaction() as session:
                        from sqlalchemy import text
                        await session.execute(
                            text("INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (:id, :title, :url, :tech, :hash)"),
                            {"id": "test2", "title": "Test2", "url": "http://test2.com", "tech": "python", "hash": "hash2"}
                        )
                        # Force error to trigger rollback
                        raise Exception("Simulated error")
                except Exception:
                    pass  # Expected
                
                # Verify rollback occurred
                result = await manager.fetch_one(
                    "SELECT COUNT(*) FROM content_metadata WHERE content_id = ?",
                    ("test2",)
                )
                assert result[0] == 0, "Transaction rollback failed"
                
            finally:
                await manager.disconnect()


class TestCompleteSystemIntegration:
    """
    Test complete system integration to ensure all components work together
    """

    @pytest.mark.asyncio
    async def test_document_processing_workflow(self):
        """TEST-I003-REVALIDATE: Verify complete document processing workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            try:
                # Insert content metadata
                await manager.execute(
                    "INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash, word_count, heading_count, code_block_count, quality_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ("doc1", "Test Document", "http://test.com", "python", "hash1", 100, 5, 2, 0.8)
                )
                
                # Test document reconstruction
                metadata_row = await manager.fetch_one(
                    "SELECT * FROM content_metadata WHERE content_id = ?",
                    ("doc1",)
                )
                
                # Convert row to object-like access for testing
                class MockRow:
                    def __init__(self, data):
                        self.content_id = data[0]
                        self.title = data[1]
                        self.source_url = data[2]
                        self.technology = data[3]
                        self.content_hash = data[4]
                        self.word_count = data[5]
                        self.heading_count = data[6]
                        self.code_block_count = data[7]
                        self.chunk_count = data[8]
                        self.quality_score = data[9]
                        self.freshness_score = data[10]
                        self.processing_status = data[11]
                        self.anythingllm_workspace = data[12]
                        self.anythingllm_document_id = data[13]
                        self.created_at = data[14]
                        self.updated_at = data[15]
                        self.last_accessed_at = data[16]
                        self.access_count = data[17]
                
                mock_row = MockRow(metadata_row)
                processed_doc = await manager.load_processed_document_from_metadata(mock_row)
                
                # Verify document reconstruction
                assert processed_doc.id == "doc1"
                assert processed_doc.title == "Test Document"
                assert processed_doc.technology == "python"
                assert processed_doc.quality_score == 0.8
                assert processed_doc.metadata.word_count == 100
                assert processed_doc.metadata.heading_count == 5
                assert processed_doc.metadata.code_block_count == 2
                
            finally:
                await manager.disconnect()

    def test_technology_mappings_and_defaults(self):
        """TEST-I004-REVALIDATE: Verify technology mappings still work correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check default mappings
            cursor.execute("SELECT COUNT(*) FROM technology_mappings WHERE is_official = 1")
            official_count = cursor.fetchone()[0]
            assert official_count >= 8, f"Expected at least 8 official mappings, found {official_count}"
            
            # Verify specific technologies
            cursor.execute("SELECT technology FROM technology_mappings WHERE is_official = 1")
            technologies = [row[0] for row in cursor.fetchall()]
            
            expected_technologies = ['python-fastapi', 'python-django', 'react', 'nextjs']
            for tech in expected_technologies:
                assert tech in technologies, f"Missing official mapping for {tech}"
            
            # Test custom mapping insertion
            cursor.execute("""
                INSERT INTO technology_mappings 
                (mapping_id, technology, source_type, owner, repo, docs_path, file_patterns, priority, is_official)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("custom1", "custom-tech", "github", "test-owner", "test-repo", "docs", '["*.md"]', 5, False))
            
            conn.commit()
            
            # Verify custom mapping
            cursor.execute("SELECT technology FROM technology_mappings WHERE mapping_id = ?", ("custom1",))
            result = cursor.fetchone()
            assert result[0] == "custom-tech"
            
            conn.close()


# Meta-test to verify comprehensive test coverage
def test_revalidation_suite_completeness():
    """META-TEST: Verify re-validation test suite is comprehensive"""
    import inspect
    
    # Count test methods in each class
    test_classes = [
        TestCriticalSecurityFixes,
        TestFunctionalRequirementsRevalidation,
        TestPerformanceRevalidation,
        TestOperationalRevalidation,
        TestCompleteSystemIntegration
    ]
    
    total_tests = 0
    critical_tests = 0
    
    for test_class in test_classes:
        methods = [name for name, method in inspect.getmembers(test_class, predicate=inspect.isfunction)
                  if name.startswith('test_')]
        total_tests += len(methods)
        
        if test_class == TestCriticalSecurityFixes:
            critical_tests = len(methods)
    
    # Verify comprehensive coverage
    # Re-validation suite aims for at least 12 focused tests
    assert total_tests >= 12, f"Insufficient test coverage: {total_tests} tests"
    assert critical_tests == 4, f"Expected 4 critical security tests, found {critical_tests}"
    
    print(f"✅ Re-validation suite includes {total_tests} comprehensive tests")
    print(f"✅ Critical security fixes: {critical_tests} tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])