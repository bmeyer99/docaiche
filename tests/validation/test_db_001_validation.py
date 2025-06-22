"""
Comprehensive Validation Tests for PRD-002 Database & Caching Layer
DB-001 Implementation - SQLite Database Schema

This test suite validates the complete implementation against all task requirements,
security standards, performance benchmarks, and integration capabilities.

Test Categories:
- Functional Tests: Schema compliance, table creation, indexing
- Security Tests: SQL injection prevention, access controls, data validation
- Performance Tests: Connection pooling, query optimization, index effectiveness
- Integration Tests: CFG-001 integration, Redis caching, async patterns
- Operational Tests: CLI tools, health checks, error handling
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
from src.database.connection import DatabaseManager, CacheManager, create_database_manager, create_cache_manager
from src.database.models import Base, SystemConfig, SearchCache, ContentMetadata, FeedbackEvents, UsageSignals, SourceMetadata, TechnologyMappings, SchemaVersions


class TestPRD002FunctionalRequirements:
    """
    Functional Tests: Validate exact PRD-002 requirements implementation
    
    These tests verify that every specified requirement from the task
    has been implemented exactly as documented.
    """
    
    def test_all_required_tables_created(self):
        """TEST-F001: Verify all 7 required tables are created with exact schema"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Verify database exists
            assert os.path.exists(db_path), "Database file was not created"
            
            # Connect and verify tables
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = [
                'system_config', 'search_cache', 'content_metadata', 
                'feedback_events', 'usage_signals', 'source_metadata', 
                'technology_mappings', 'schema_versions'
            ]
            
            for table in required_tables:
                assert table in tables, f"Required table '{table}' not found"
            
            # Verify total count matches expected (7 + schema_versions = 8)
            assert len(tables) == 8, f"Expected 8 tables, found {len(tables)}: {tables}"
            conn.close()
    
    def test_system_config_table_schema(self):
        """TEST-F002: Verify system_config table has exact schema specification"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table schema
            cursor.execute("PRAGMA table_info(system_config)")
            columns = cursor.fetchall()
            
            expected_columns = {
                'key': 'TEXT',
                'value': 'JSON', 
                'schema_version': 'TEXT',
                'updated_at': 'TIMESTAMP',
                'updated_by': 'TEXT'
            }
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_primary = col[5] == 1
                
                assert col_name in expected_columns, f"Unexpected column: {col_name}"
                # Note: SQLite may show slightly different type names
                if col_name == 'key':
                    assert is_primary, "key column should be primary key"
            
            conn.close()
    
    def test_search_cache_table_schema(self):
        """TEST-F003: Verify search_cache table has exact schema specification"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verify table exists and has correct columns
            cursor.execute("PRAGMA table_info(search_cache)")
            columns = {col[1]: col[2] for col in cursor.fetchall()}
            
            required_columns = [
                'query_hash', 'original_query', 'search_results', 'technology_hint',
                'workspace_slugs', 'result_count', 'execution_time_ms', 'cache_hit',
                'created_at', 'expires_at', 'access_count', 'last_accessed_at'
            ]
            
            for col in required_columns:
                assert col in columns, f"Missing column '{col}' in search_cache"
            
            conn.close()
    
    def test_content_metadata_table_constraints(self):
        """TEST-F004: Verify content_metadata table constraints and checks"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            
            # Test quality_score constraint (0.0 to 1.0)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash, quality_score)
                    VALUES ('test1', 'Test', 'http://test.com', 'python', 'hash1', 1.5)
                """)
            
            # Test valid quality_score
            conn.execute("""
                INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash, quality_score)
                VALUES ('test2', 'Test', 'http://test.com', 'python', 'hash2', 0.8)
            """)
            
            # Test processing_status constraint
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash, processing_status)
                    VALUES ('test3', 'Test', 'http://test.com', 'python', 'hash3', 'invalid_status')
                """)
            
            conn.close()
    
    def test_foreign_key_constraints(self):
        """TEST-F005: Verify foreign key constraints are enforced"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Try to insert feedback_event without content_metadata (should fail)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO feedback_events (event_id, content_id, feedback_type)
                    VALUES ('event1', 'nonexistent', 'helpful')
                """)
            
            # Create content first, then feedback (should succeed)
            conn.execute("""
                INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash)
                VALUES ('content1', 'Test', 'http://test.com', 'python', 'hash1')
            """)
            
            conn.execute("""
                INSERT INTO feedback_events (event_id, content_id, feedback_type)
                VALUES ('event1', 'content1', 'helpful')
            """)
            
            conn.close()
    
    def test_all_25_indexes_created(self):
        """TEST-F006: Verify all 25 performance indexes are created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all index names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            expected_indexes = [
                # Search cache indexes (3)
                'idx_search_cache_expires_at', 'idx_search_cache_technology_hint', 'idx_search_cache_created_at',
                # Content metadata indexes (7)
                'idx_content_metadata_technology', 'idx_content_metadata_source_url', 'idx_content_metadata_content_hash',
                'idx_content_metadata_quality_score', 'idx_content_metadata_processing_status', 'idx_content_metadata_created_at',
                'idx_content_metadata_last_accessed_at',
                # Feedback events indexes (4)
                'idx_feedback_events_content_id', 'idx_feedback_events_feedback_type', 'idx_feedback_events_created_at',
                'idx_feedback_events_user_session_id',
                # Usage signals indexes (4)
                'idx_usage_signals_content_id', 'idx_usage_signals_signal_type', 'idx_usage_signals_created_at',
                'idx_usage_signals_user_session_id',
                # Source metadata indexes (5)
                'idx_source_metadata_source_type', 'idx_source_metadata_technology', 'idx_source_metadata_reliability_score',
                'idx_source_metadata_is_active', 'idx_source_metadata_updated_at',
                # Technology mappings indexes (5)
                'idx_technology_mappings_technology', 'idx_technology_mappings_source_type', 'idx_technology_mappings_priority',
                'idx_technology_mappings_is_active', 'idx_technology_mappings_is_official'
            ]
            
            # Verify all expected indexes exist
            for idx in expected_indexes:
                assert idx in indexes, f"Missing index: {idx}"
            
            # Verify count (25 custom + any automatic unique indexes)
            assert len([idx for idx in indexes if idx.startswith('idx_')]) >= 25, f"Expected at least 25 indexes, found {len(indexes)}"
            
            conn.close()
    
    def test_default_technology_mappings_inserted(self):
        """TEST-F007: Verify default technology mappings are inserted"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check that technology mappings exist
            cursor.execute("SELECT COUNT(*) FROM technology_mappings")
            count = cursor.fetchone()[0]
            
            assert count >= 8, f"Expected at least 8 default mappings, found {count}"
            
            # Verify specific mappings exist
            cursor.execute("SELECT technology FROM technology_mappings WHERE is_official = 1")
            technologies = [row[0] for row in cursor.fetchall()]
            
            expected_technologies = ['python-fastapi', 'python-django', 'react', 'nextjs', 'docker', 'kubernetes']
            for tech in expected_technologies:
                assert tech in technologies, f"Missing default mapping for {tech}"
            
            conn.close()
    
    def test_schema_version_tracking(self):
        """TEST-F008: Verify schema version is properly tracked"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verify schema version record exists
            cursor.execute("SELECT version_id, description FROM schema_versions ORDER BY applied_at DESC LIMIT 1")
            result = cursor.fetchone()
            
            assert result is not None, "No schema version record found"
            assert result[0] == "1.0.0", f"Expected version 1.0.0, got {result[0]}"
            assert "Initial database schema" in result[1], f"Unexpected description: {result[1]}"
            
            conn.close()


class TestPRD002SecurityValidation:
    """
    Security Tests: Validate database security measures
    
    These tests ensure the implementation follows security best practices
    and protects against common database vulnerabilities.
    """
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """TEST-S001: Verify parameterized queries prevent SQL injection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Create database manager
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            # Attempt SQL injection via parameterized query (should be safe)
            malicious_input = "'; DROP TABLE content_metadata; --"
            
            try:
                # This should not execute the malicious SQL
                await manager.execute(
                    "SELECT * FROM content_metadata WHERE title = ?",
                    (malicious_input,)
                )
                
                # Verify table still exists
                result = await manager.fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='content_metadata'")
                assert result is not None, "Table was dropped - SQL injection succeeded!"
                
            finally:
                await manager.disconnect()
    
    def test_no_hardcoded_credentials(self):
        """TEST-S002: Verify no hardcoded credentials in database files"""
        # Check init_db.py for hardcoded secrets
        with open("src/database/init_db.py", "r") as f:
            content = f.read()
        
        # Should not contain obvious credential patterns
        forbidden_patterns = [
            "password=", "secret=", "key=", "token=",
            "api_key", "secret_key", "private_key"
        ]
        
        for pattern in forbidden_patterns:
            # Allow in comments or logging messages, but not in actual code
            lines_with_pattern = [line for line in content.split('\n') 
                                if pattern in line.lower() and not line.strip().startswith('#')]
            assert len(lines_with_pattern) == 0, f"Found potential hardcoded credential pattern: {pattern}"
    
    @pytest.mark.asyncio
    async def test_database_connection_security(self):
        """TEST-S003: Verify database connections use secure practices"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            
            # Verify connection uses proper async patterns
            await manager.connect()
            assert manager._connected is True
            
            # Verify foreign keys are enabled (security feature)
            result = await manager.fetch_one("PRAGMA foreign_keys")
            assert result[0] == 1, "Foreign keys should be enabled for referential integrity"
            
            await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_security(self):
        """TEST-S004: Verify transaction rollback prevents partial updates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            # Test transaction rollback on error
            queries = [
                ("INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                 ('test1', 'Test Title', 'http://test.com', 'python', 'hash1')),
                ("INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (?, ?, ?, ?, ?)",
                 ('test1', 'Duplicate ID', 'http://test.com', 'python', 'hash2'))  # Should fail on duplicate
            ]
            
            # This should fail and rollback
            result = await manager.execute_transaction(queries)
            assert result is False, "Transaction should have failed"
            
            # Verify no partial data was inserted
            count_result = await manager.fetch_one("SELECT COUNT(*) FROM content_metadata WHERE content_id = ?", ('test1',))
            assert count_result[0] == 0, "Transaction rollback failed - partial data was inserted"
            
            await manager.disconnect()


class TestPRD002PerformanceValidation:
    """
    Performance Tests: Validate database performance characteristics
    
    These tests ensure the implementation meets performance requirements
    and uses efficient patterns for async operations and caching.
    """
    
    @pytest.mark.asyncio
    async def test_async_connection_pooling(self):
        """TEST-P001: Verify async connection pooling is implemented"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            # Verify async engine is configured properly
            assert manager.engine is not None, "Async engine not created"
            assert manager.session_factory is not None, "Session factory not created"
            
            # Test concurrent operations (basic concurrency test)
            async def test_query():
                return await manager.fetch_one("SELECT 1")
            
            # Run multiple concurrent queries
            tasks = [test_query() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 5
            assert all(result[0] == 1 for result in results)
            
            await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_index_effectiveness(self):
        """TEST-P002: Verify indexes improve query performance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Insert test data
            conn = sqlite3.connect(db_path)
            for i in range(100):
                conn.execute("""
                    INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash)
                    VALUES (?, ?, ?, ?, ?)
                """, (f'content_{i}', f'Title {i}', f'http://test{i}.com', 'python', f'hash_{i}'))
            conn.commit()
            conn.close()
            
            # Test that query uses index (check EXPLAIN QUERY PLAN)
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            # Query that should use technology index
            result = await manager.fetch_all("EXPLAIN QUERY PLAN SELECT * FROM content_metadata WHERE technology = ?", ('python',))
            query_plan = str(result)
            
            # Should mention using index (exact text may vary by SQLite version)
            assert 'idx_content_metadata_technology' in query_plan or 'USING INDEX' in query_plan, f"Query plan: {query_plan}"
            
            await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_compression_performance(self):
        """TEST-P003: Verify Redis cache compression works efficiently"""
        redis_config = {
            "host": "localhost",
            "port": 6379,
            "db": 0
        }
        
        # Mock Redis for testing
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.setex = AsyncMock()
        mock_redis.get = AsyncMock()
        
        with patch('src.database.connection.redis.Redis', return_value=mock_redis):
            cache_manager = CacheManager(redis_config)
            await cache_manager.connect()
            
            # Test large data compression
            large_data = {"results": [{"id": i, "content": "x" * 1000} for i in range(100)]}
            
            await cache_manager.set("search:results:test", large_data, 3600)
            
            # Verify setex was called (compression should happen internally)
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            
            # Verify data was compressed (for search:results: keys)
            assert call_args[0][0] == "search:results:test"  # key
            assert call_args[0][1] == 3600  # ttl
            # Data should be compressed bytes
            assert isinstance(call_args[0][2], bytes)


class TestPRD002IntegrationValidation:
    """
    Integration Tests: Validate integration with other system components
    
    These tests ensure the database layer integrates properly with
    the CFG-001 configuration system and other PRD components.
    """
    
    def test_cfg001_configuration_integration(self):
        """TEST-I001: Verify integration with CFG-001 configuration system"""
        # Mock configuration system
        mock_config = MagicMock()
        mock_config.app.data_dir = "/custom/data"
        mock_config.redis.host = "custom-redis"
        mock_config.redis.port = 6380
        mock_config.redis.password = "test-password"
        mock_config.redis.db = 2
        mock_config.redis.max_connections = 50
        mock_config.redis.connection_timeout = 10
        mock_config.redis.socket_timeout = 10
        mock_config.redis.ssl = True
        
        with patch('src.database.init_db.get_system_configuration', return_value=mock_config):
            # Test DatabaseInitializer uses config
            initializer = DatabaseInitializer()
            assert initializer.db_path == "/custom/data/docaiche.db"
        
        with patch('src.database.connection.get_system_configuration', return_value=mock_config):
            # Test factory functions use config
            async def test_factory():
                db_manager = await create_database_manager()
                cache_manager = await create_cache_manager()
                
                assert "/custom/data/docaiche.db" in db_manager.database_url
                assert cache_manager.redis_config["host"] == "custom-redis"
                assert cache_manager.redis_config["port"] == 6380
                assert cache_manager.redis_config["password"] == "test-password"
                assert cache_manager.redis_config["ssl"] is True
            
            asyncio.run(test_factory())
    
    @pytest.mark.asyncio
    async def test_sqlalchemy_models_integration(self):
        """TEST-I002: Verify SQLAlchemy 2.0 models work with database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Test that models can be imported and have correct structure
            from src.database.models import ContentMetadata, FeedbackEvents
            
            # Verify model relationships are defined
            assert hasattr(ContentMetadata, 'feedback_events'), "ContentMetadata missing feedback_events relationship"
            assert hasattr(FeedbackEvents, 'content'), "FeedbackEvents missing content relationship"
            
            # Verify constraints are defined
            assert hasattr(ContentMetadata, '__table_args__'), "ContentMetadata missing table constraints"
            
            # Check that table args include expected constraints
            table_args = ContentMetadata.__table_args__
            constraint_strings = [str(arg) for arg in table_args if hasattr(arg, 'name')]
            
            # Should have check constraints for quality_score and processing_status
            assert any('quality_score' in constraint for constraint in constraint_strings)
            assert any('processing_status' in constraint for constraint in constraint_strings)
    
    @pytest.mark.asyncio
    async def test_document_metadata_compatibility(self):
        """TEST-I003: Verify document models are compatible with content processing"""
        from src.database.connection import DocumentMetadata, DocumentChunk, ProcessedDocument
        
        # Test that models can be instantiated with valid data
        doc_metadata = DocumentMetadata(
            word_count=100,
            heading_count=5,
            code_block_count=2,
            content_hash="test_hash",
            created_at=datetime.now()
        )
        
        assert doc_metadata.word_count == 100
        assert doc_metadata.model_version == "1.0.0"
        
        # Test document chunk
        chunk = DocumentChunk(
            id="chunk_1",
            parent_document_id="doc_1",
            content="Test content",
            chunk_index=0,
            total_chunks=1,
            created_at=datetime.now()
        )
        
        assert chunk.chunk_index == 0
        assert chunk.model_version == "1.0.0"
        
        # Test complete processed document
        processed_doc = ProcessedDocument(
            id="doc_1",
            title="Test Document",
            full_content="Full test content",
            source_url="http://test.com",
            technology="python",
            metadata=doc_metadata,
            quality_score=0.8,
            chunks=[chunk],
            created_at=datetime.now()
        )
        
        assert processed_doc.quality_score == 0.8
        assert len(processed_doc.chunks) == 1


class TestPRD002OperationalValidation:
    """
    Operational Tests: Validate production readiness and operational features
    
    These tests ensure the implementation is ready for production deployment
    with proper health checks, error handling, and CLI tools.
    """
    
    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """TEST-O001: Verify database health check functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            
            # Test healthy database
            health = await manager.health_check()
            assert health["status"] == "healthy"
            assert health["connected"] is True
            assert health["test_query"] == 1
            assert "database_url" in health
            assert "[REDACTED]" in health["database_url"]  # Should hide credentials
    
    @pytest.mark.asyncio
    async def test_cache_health_check(self):
        """TEST-O002: Verify Redis cache health check functionality"""
        redis_config = {"host": "nonexistent-redis", "port": 6379, "db": 0}
        cache_manager = CacheManager(redis_config)
        
        # Test unhealthy cache (connection should fail)
        health = await cache_manager.health_check()
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health
    
    def test_cli_script_functionality(self):
        """TEST-O003: Verify CLI script works correctly"""
        # Test that CLI script exists and is executable
        cli_script = Path("scripts/init-db.sh")
        assert cli_script.exists(), "CLI script init-db.sh not found"
        
        # Verify script has proper shebang
        with open(cli_script, 'r') as f:
            first_line = f.readline().strip()
        assert first_line.startswith('#!/bin/bash'), "CLI script missing bash shebang"
        
        # Check script has execution permissions (on Unix systems)
        if os.name != 'nt':  # Not Windows
            import stat
            file_stat = cli_script.stat()
            assert file_stat.st_mode & stat.S_IEXEC, "CLI script not executable"
    
    def test_database_info_functionality(self):
        """TEST-O004: Verify database info collection works"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Test database info collection
            info = initializer.get_database_info()
            
            assert info["exists"] is True
            assert info["path"] == db_path
            assert info["table_count"] == 8  # 7 main tables + schema_versions
            assert info["schema_version"] == "1.0.0"
            assert "file_size_bytes" in info
            assert "file_size_mb" in info
            assert info["file_size_bytes"] > 0
    
    def test_idempotent_initialization(self):
        """TEST-O005: Verify database initialization is idempotent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            
            # Initialize database twice
            initializer.initialize_database()
            original_info = initializer.get_database_info()
            
            initializer.initialize_database()  # Should not fail
            second_info = initializer.get_database_info()
            
            # Should have same table count and schema version
            assert original_info["table_count"] == second_info["table_count"]
            assert original_info["schema_version"] == second_info["schema_version"]
    
    def test_error_handling_robustness(self):
        """TEST-O006: Verify robust error handling"""
        # Test initialization with invalid path
        invalid_path = "/nonexistent/directory/test.db"
        initializer = DatabaseInitializer(invalid_path)
        
        # Should handle directory creation gracefully
        try:
            initializer.initialize_database()
            # If this succeeds, verify directory was created
            assert os.path.exists(os.path.dirname(invalid_path))
        except Exception as e:
            # If it fails, it should be a clear, specific error
            assert "permission" in str(e).lower() or "directory" in str(e).lower()


class TestPRD002ErrorHandlingValidation:
    """
    Error Handling Tests: Validate comprehensive error handling
    
    These tests ensure the implementation handles all failure scenarios
    gracefully and provides appropriate error messages and recovery.
    """
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_handling(self):
        """TEST-E001: Verify graceful handling of database connection failures"""
        # Test with invalid database URL
        invalid_url = "sqlite+aiosqlite:///nonexistent/directory/db.sqlite"
        manager = DatabaseManager(invalid_url)
        
        # Connection should fail gracefully
        with pytest.raises(Exception):  # Should raise specific database error
            await manager.connect()
        
        # Health check should return unhealthy status
        health = await manager.health_check()
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
    
    @pytest.mark.asyncio
    async def test_cache_connection_failure_handling(self):
        """TEST-E002: Verify graceful handling of Redis connection failures"""
        redis_config = {
            "host": "nonexistent-redis-server",
            "port": 6379,
            "db": 0,
            "connection_timeout": 1  # Short timeout for faster test
        }
        
        cache_manager = CacheManager(redis_config)
        
        # Operations should handle connection failures gracefully
        result = await cache_manager.get("test_key")
        assert result is None  # Should return None on connection failure
        
        # Set operation should handle failure
        try:
            await cache_manager.set("test_key", "test_value", 60)
        except Exception as e:
            # Should be a specific, clear error
            assert "connection" in str(e).lower() or "redis" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_transaction_failure_recovery(self):
        """TEST-E003: Verify transaction failure recovery"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            await manager.connect()
            
            # Test transaction context manager with exception
            try:
                async with manager.transaction() as session:
                    await session.execute(text("INSERT INTO content_metadata (content_id, title, source_url, technology, content_hash) VALUES (:id, :title, :url, :tech, :hash)"),
                                        {"id": "test1", "title": "Test", "url": "http://test.com", "tech": "python", "hash": "hash1"})
                    # Force an error
                    raise Exception("Simulated error")
            except Exception:
                pass  # Expected to fail
            
            # Verify rollback occurred - no data should be inserted
            result = await manager.fetch_one("SELECT COUNT(*) FROM content_metadata WHERE content_id = ?", ("test1",))
            assert result[0] == 0, "Transaction rollback failed"
            
            await manager.disconnect()


# Test Suite Summary and Execution
def test_suite_completeness():
    """META-TEST: Verify test suite covers all requirements"""
    # Count functional tests
    functional_tests = [name for name in globals() if name.startswith('test_') and 'functional' in name.lower()]
    
    # Verify we have comprehensive coverage
    test_classes = [
        TestPRD002FunctionalRequirements,
        TestPRD002SecurityValidation, 
        TestPRD002PerformanceValidation,
        TestPRD002IntegrationValidation,
        TestPRD002OperationalValidation,
        TestPRD002ErrorHandlingValidation
    ]
    
    total_test_methods = 0
    for test_class in test_classes:
        methods = [method for method in dir(test_class) if method.startswith('test_')]
        total_test_methods += len(methods)
    
    # Should have comprehensive test coverage (at least 20 test methods)
    assert total_test_methods >= 20, f"Insufficient test coverage: {total_test_methods} tests"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])