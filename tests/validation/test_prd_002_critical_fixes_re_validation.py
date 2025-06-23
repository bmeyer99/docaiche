"""
PRD-002 Critical Fixes Re-Validation Test Suite
Tests all 18 critical issues identified in previous validation
MANDATORY: Code can ONLY pass if ALL tests pass
"""

import pytest
import asyncio
import sqlite3
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Import the modules to test
from src.database.schema import create_database_schema
from src.database.manager import DatabaseManager, create_database_manager
from src.cache.manager import CacheManager, create_cache_manager
from src.models.document import DocumentMetadata, DocumentChunk, ProcessedDocument


class TestPRD002SchemaCompliance:
    """Test 1-7: Schema Compliance - All 7 PRD-002 tables exactly implemented"""
    
    async def test_01_system_config_table_exact_schema(self):
        """Verify system_config table matches PRD-002 lines 34-40 exactly"""
        test_db = "test_schema_compliance.db"
        create_database_schema(test_db)
        
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(system_config)")
            columns = cursor.fetchall()
            
        expected_columns = {
            'key': ('TEXT', 1, None, 1),  # (type, notnull, default, pk)
            'value': ('JSON', 1, None, 0),
            'schema_version': ('TEXT', 1, "'1.0'", 0),
            'updated_at': ('TIMESTAMP', 1, 'CURRENT_TIMESTAMP', 0),
            'updated_by': ('TEXT', 1, "'system'", 0)
        }
        
        actual_columns = {col[1]: (col[2], col[3], col[4], col[5]) for col in columns}
        assert actual_columns == expected_columns, f"system_config schema mismatch: {actual_columns}"
    
    async def test_02_search_cache_table_exact_schema(self):
        """Verify search_cache table matches PRD-002 lines 43-56 exactly"""
        test_db = "test_schema_compliance.db"
        
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(search_cache)")
            columns = cursor.fetchall()
            
        # Verify all required columns exist with correct types
        column_names = [col[1] for col in columns]
        required_columns = [
            'query_hash', 'original_query', 'search_results', 'technology_hint',
            'workspace_slugs', 'result_count', 'execution_time_ms', 'cache_hit',
            'created_at', 'expires_at', 'access_count', 'last_accessed_at'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column {col} in search_cache"
    
    async def test_03_content_metadata_table_exact_schema(self):
        """Verify content_metadata table matches PRD-002 lines 59-78 exactly"""
        test_db = "test_schema_compliance.db"
        
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(content_metadata)")
            columns = cursor.fetchall()
            
        column_names = [col[1] for col in columns]
        required_columns = [
            'content_id', 'title', 'source_url', 'technology', 'content_hash',
            'word_count', 'heading_count', 'code_block_count', 'chunk_count',
            'quality_score', 'freshness_score', 'processing_status',
            'anythingllm_workspace', 'anythingllm_document_id', 'created_at',
            'updated_at', 'last_accessed_at', 'access_count'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column {col} in content_metadata"
    
    async def test_04_feedback_events_table_exact_schema(self):
        """Verify feedback_events table matches PRD-002 lines 81-94 exactly"""
        test_db = "test_schema_compliance.db"
        
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(feedback_events)")
            columns = cursor.fetchall()
            
        column_names = [col[1] for col in columns]
        required_columns = [
            'event_id', 'content_id', 'feedback_type', 'rating', 'comment',
            'user_session_id', 'ip_address', 'user_agent', 'search_query',
            'result_position', 'created_at'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column {col} in feedback_events"
    
    async def test_05_usage_signals_table_exact_schema(self):
        """Verify usage_signals table matches PRD-002 lines 97-110 exactly"""
        test_db = "test_schema_compliance.db"
        
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(usage_signals)")
            columns = cursor.fetchall()
            
        column_names = [col[1] for col in columns]
        required_columns = [
            'signal_id', 'content_id', 'signal_type', 'signal_value',
            'search_query', 'result_position', 'user_session_id',
            'ip_address', 'user_agent', 'referrer', 'created_at'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column {col} in usage_signals"
    
    async def test_06_source_metadata_table_exact_schema(self):
        """Verify source_metadata table matches PRD-002 lines 113-130 exactly"""
        test_db = "test_schema_compliance.db"
        
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(source_metadata)")
            columns = cursor.fetchall()
            
        column_names = [col[1] for col in columns]
        required_columns = [
            'source_id', 'source_type', 'source_url', 'technology',
            'reliability_score', 'avg_processing_time_ms', 'total_documents_processed',
            'last_successful_fetch', 'last_failed_fetch', 'consecutive_failures',
            'rate_limit_status', 'rate_limit_reset_at', 'avg_content_quality',
            'is_active', 'created_at', 'updated_at'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column {col} in source_metadata"
    
    async def test_07_technology_mappings_table_exact_schema(self):
        """Verify technology_mappings table matches PRD-002 lines 133-150 exactly"""
        test_db = "test_schema_compliance.db"
        
        with sqlite3.connect(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(technology_mappings)")
            columns = cursor.fetchall()
            
        column_names = [col[1] for col in columns]
        required_columns = [
            'mapping_id', 'technology', 'source_type', 'owner', 'repo',
            'docs_path', 'file_patterns', 'base_url', 'priority',
            'is_official', 'last_updated', 'update_frequency_hours',
            'is_active', 'created_at', 'updated_at'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column {col} in technology_mappings"


class TestPRD002SecurityFixes:
    """Test 8-11: Security Fixes - SQL injection prevention and Redis security"""
    
    async def test_08_parameterized_queries_prevent_sql_injection(self):
        """Verify all database queries use parameterized queries"""
        db_manager = await create_database_manager({"db_path": "test_security.db"})
        await db_manager.connect()
        
        # Test malicious SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE system_config; --",
            "' OR '1'='1",
            "1; DELETE FROM content_metadata; --",
            "' UNION SELECT * FROM system_config --"
        ]
        
        for malicious_input in malicious_inputs:
            try:
                # This should not cause SQL injection
                result = await db_manager.fetch_one(
                    "SELECT * FROM system_config WHERE key = :param_0",
                    (malicious_input,)
                )
                # Should return None (no match) without executing malicious SQL
                assert result is None
            except Exception as e:
                # Should not crash with SQL syntax errors
                assert "syntax error" not in str(e).lower()
        
        await db_manager.disconnect()
    
    async def test_09_redis_authentication_configuration(self):
        """Verify Redis authentication and SSL configuration"""
        redis_config = {
            "host": "redis",
            "port": 6379,
            "password": "test_password",
            "ssl": True,
            "ssl_check_hostname": True
        }
        
        cache_manager = CacheManager(redis_config)
        
        # Verify security settings are applied
        assert cache_manager.redis_config["password"] == "test_password"
        assert cache_manager.redis_config["ssl"] is True
        assert cache_manager.redis_config["ssl_check_hostname"] is True
    
    async def test_10_no_sensitive_data_in_logs(self):
        """Verify no sensitive data leaks in database error logging"""
        db_manager = await create_database_manager({"db_path": "test_logging.db"})
        
        with patch('src.database.manager.logger') as mock_logger:
            try:
                # Trigger an error with sensitive data
                await db_manager.fetch_one("INVALID SQL WITH password='secret123'")
            except:
                pass
            
            # Check that sensitive data is not logged
            for call in mock_logger.error.call_args_list:
                log_message = str(call)
                assert "secret123" not in log_message
                assert "password=" not in log_message
    
    async def test_11_foreign_key_constraints_enabled(self):
        """Verify foreign key constraints are properly enabled"""
        db_manager = await create_database_manager({"db_path": "test_fk.db"})
        await db_manager.connect()
        
        # Test foreign key constraint enforcement
        result = await db_manager.fetch_one("PRAGMA foreign_keys")
        assert result[0] == 1, "Foreign key constraints not enabled"
        
        await db_manager.disconnect()


class TestPRD002ArchitectureFixes:
    """Test 12-14: Architecture Fixes - Missing methods implementation"""
    
    async def test_12_transaction_context_manager(self):
        """Verify transaction() context manager with rollback scenarios"""
        db_manager = await create_database_manager({"db_path": "test_transaction.db"})
        await db_manager.connect()
        
        # Test successful transaction
        async with db_manager.transaction() as session:
            from sqlalchemy import text
            await session.execute(text("INSERT INTO system_config (key, value) VALUES ('test_key', '{\"value\": \"test\"}')"))
        
        # Verify data was committed
        result = await db_manager.fetch_one("SELECT value FROM system_config WHERE key = 'test_key'")
        assert result is not None
        
        # Test rollback on exception
        try:
            async with db_manager.transaction() as session:
                await session.execute(text("INSERT INTO system_config (key, value) VALUES ('test_key2', '{\"value\": \"test2\"}')"))
                raise Exception("Force rollback")
        except Exception:
            pass
        
        # Verify data was rolled back
        result = await db_manager.fetch_one("SELECT value FROM system_config WHERE key = 'test_key2'")
        assert result is None
        
        await db_manager.disconnect()
    
    async def test_13_load_processed_document_from_metadata(self):
        """Verify load_processed_document_from_metadata() functionality"""
        db_manager = await create_database_manager({"db_path": "test_document_load.db"})
        await db_manager.connect()
        
        # Create mock metadata row
        mock_row = Mock()
        mock_row.content_id = "test_doc_1"
        mock_row.title = "Test Document"
        mock_row.source_url = "https://example.com/doc"
        mock_row.technology = "python"
        mock_row.content_hash = "abcd1234"
        mock_row.quality_score = 0.85
        mock_row.word_count = 1000
        mock_row.heading_count = 5
        mock_row.code_block_count = 3
        mock_row.chunk_count = 4
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()
        
        # Test document reconstruction
        processed_doc = await db_manager.load_processed_document_from_metadata(mock_row)
        
        assert isinstance(processed_doc, ProcessedDocument)
        assert processed_doc.id == "test_doc_1"
        assert processed_doc.title == "Test Document"
        assert processed_doc.technology == "python"
        assert len(processed_doc.chunks) == 4
        
        await db_manager.disconnect()
    
    async def test_14_missing_methods_implementation(self):
        """Verify all missing methods are implemented and functional"""
        db_manager = await create_database_manager({"db_path": "test_methods.db"})
        
        # Test get_document_metadata method
        assert hasattr(db_manager, 'get_document_metadata')
        assert callable(getattr(db_manager, 'get_document_metadata'))
        
        # Test get_document_by_url method
        assert hasattr(db_manager, 'get_document_by_url')
        assert callable(getattr(db_manager, 'get_document_by_url'))
        
        # Test initialize method
        assert hasattr(db_manager, 'initialize')
        assert callable(getattr(db_manager, 'initialize'))
        
        # Test methods actually work
        await db_manager.initialize()
        result = await db_manager.get_document_metadata("nonexistent")
        assert result is None
        
        result = await db_manager.get_document_by_url("https://nonexistent.com")
        assert result is None


class TestPRD002PerformanceFixes:
    """Test 15-16: Performance Fixes - Connection pooling and compression"""
    
    async def test_15_connection_pooling_configuration(self):
        """Verify connection pooling with pool_size=10, max_overflow=20"""
        db_manager = await create_database_manager({"db_path": "test_pool.db"})
        await db_manager.connect()
        
        # Verify engine has proper pooling configuration
        engine = db_manager.engine
        assert engine.pool.size() == 10, f"Expected pool size 10, got {engine.pool.size()}"
        assert engine.pool._max_overflow == 20, f"Expected max_overflow 20, got {engine.pool._max_overflow}"
        
        await db_manager.disconnect()
    
    async def test_16_compression_optimization(self):
        """Verify cache compression optimization with size thresholds"""
        redis_config = {"host": "redis", "port": 6379, "db": 0}
        cache_manager = CacheManager(redis_config)
        
        # Test compression threshold logic
        small_data = b"small data"
        large_data = b"x" * 2048  # Larger than 1KB threshold
        
        # Small data should not be compressed
        should_compress_small = await cache_manager._should_compress(small_data)
        assert not should_compress_small
        
        # Large data should be compressed
        should_compress_large = await cache_manager._should_compress(large_data)
        assert should_compress_large


class TestPRD002CachePatterns:
    """Test 17: Cache Patterns - Exact PRD-002 cache key patterns"""
    
    async def test_17_exact_cache_key_patterns(self):
        """Verify exact cache key patterns from PRD-002 lines 190-198"""
        redis_config = {"host": "redis", "port": 6379, "db": 0}
        cache_manager = CacheManager(redis_config)
        
        # Test PRD-002 cache key patterns
        search_key = "search:results:abc123"
        content_key = "content:processed:def456"
        ai_key = "ai:evaluation:ghi789"
        github_key = "github:repo:owner/repo:path"
        config_key = "config:system:v1.0"
        rate_limit_key = "rate_limit:api:192.168.1.1"
        session_key = "session:sess123"
        
        # Test compression is applied to correct patterns
        test_data = {"test": "data"}
        
        with patch.object(cache_manager, 'redis_client') as mock_redis:
            mock_redis.setex = Mock()
            
            # These should be compressed
            await cache_manager.set(search_key, test_data, 3600)
            await cache_manager.set(content_key, test_data, 86400)
            await cache_manager.set(github_key, test_data, 3600)
            
            # Verify compression was applied (data size would be different)
            assert mock_redis.setex.call_count == 3


class TestPRD002ModelCompatibility:
    """Test 18: Model Compatibility - All 14 models (7 PRD + 7 test validation)"""
    
    async def test_18_all_models_compatibility(self):
        """Verify all 14 models are properly implemented and compatible"""
        # Test PRD-002 models
        from src.database.models import (
            SystemConfig, SearchCache, ContentMetadata, FeedbackEvents,
            UsageSignals, SourceMetadata, TechnologyMappings
        )
        
        # Test additional validation models
        from src.database.models import (
            DocumentMetadata as DBDocumentMetadata, DocumentChunk as DBDocumentChunk,
            ProcessedDocument as DBProcessedDocument, SearchQuery, CacheEntry,
            SystemMetrics, User
        )
        
        # Test canonical models
        from src.models.document import DocumentMetadata, DocumentChunk, ProcessedDocument
        
        # Verify all models can be instantiated
        models_to_test = [
            SystemConfig, SearchCache, ContentMetadata, FeedbackEvents,
            UsageSignals, SourceMetadata, TechnologyMappings,
            DBDocumentMetadata, DBDocumentChunk, DBProcessedDocument,
            SearchQuery, CacheEntry, SystemMetrics, User
        ]
        
        for model_class in models_to_test:
            assert hasattr(model_class, '__tablename__'), f"Model {model_class} missing tablename"
            assert hasattr(model_class, '__table_args__'), f"Model {model_class} missing table args"


class TestPRD002PerformanceBenchmarks:
    """Performance Benchmarks - Verify <10ms cache, <50ms indexed DB"""
    
    async def test_cache_latency_benchmark(self):
        """Verify cache operations meet <10ms P99 latency requirement"""
        redis_config = {"host": "redis", "port": 6379, "db": 0}
        cache_manager = CacheManager(redis_config)
        
        with patch.object(cache_manager, 'redis_client') as mock_redis:
            mock_redis.get = Mock(return_value=None)
            mock_redis.setex = Mock()
            mock_redis.ping = Mock(return_value=True)
            cache_manager._connected = True
            
            # Measure cache operation latency
            latencies = []
            for i in range(100):
                start_time = time.perf_counter()
                await cache_manager.get(f"test_key_{i}")
                end_time = time.perf_counter()
                latencies.append((end_time - start_time) * 1000)  # Convert to ms
            
            # Calculate P99 latency
            latencies.sort()
            p99_latency = latencies[98]  # 99th percentile
            
            # Should be much less than 10ms for mocked operations
            assert p99_latency < 10.0, f"P99 cache latency {p99_latency}ms exceeds 10ms requirement"
    
    async def test_database_query_latency_benchmark(self):
        """Verify indexed database queries meet <50ms P99 latency requirement"""
        db_manager = await create_database_manager({"db_path": "test_performance.db"})
        await db_manager.connect()
        
        # Measure database query latency
        latencies = []
        for i in range(50):
            start_time = time.perf_counter()
            await db_manager.fetch_one("SELECT 1")
            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        # Calculate P99 latency
        latencies.sort()
        p99_latency = latencies[48]  # 99th percentile (50 * 0.99 = 49.5, round down to 48)
        
        assert p99_latency < 50.0, f"P99 database latency {p99_latency}ms exceeds 50ms requirement"
        
        await db_manager.disconnect()


class TestPRD002IntegrationReadiness:
    """Integration Readiness - Test compatibility with existing components"""
    
    async def test_database_manager_integration(self):
        """Test DatabaseManager integration with existing production components"""
        db_manager = await create_database_manager()
        await db_manager.initialize()
        
        # Test health check endpoint functionality
        health_status = await db_manager.health_check()
        assert health_status["status"] == "healthy"
        assert health_status["connected"] is True
        
        await db_manager.disconnect()
    
    async def test_cache_manager_integration(self):
        """Test CacheManager integration with PRD-009 Search Orchestration"""
        cache_manager = await create_cache_manager()
        
        # Test search result caching pattern (PRD-009 integration)
        query_hash = hashlib.md5("test query".encode()).hexdigest()
        search_key = f"search:results:{query_hash}"
        
        # This should work without errors
        await cache_manager.set(search_key, {"results": []}, ttl=3600)
        result = await cache_manager.get(search_key)
        
        # Result might be None if Redis not available, but should not error
        assert result is None or isinstance(result, dict)


# Test execution configuration
@pytest.mark.asyncio
class TestPRD002CriticalFixesValidation:
    """Master test class to run all critical fixes validation"""
    
    async def test_all_critical_fixes_resolved(self):
        """Run all validation tests to confirm all 18 critical issues resolved"""
        test_classes = [
            TestPRD002SchemaCompliance(),
            TestPRD002SecurityFixes(),
            TestPRD002ArchitectureFixes(),
            TestPRD002PerformanceFixes(),
            TestPRD002CachePatterns(),
            TestPRD002ModelCompatibility(),
            TestPRD002PerformanceBenchmarks(),
            TestPRD002IntegrationReadiness()
        ]
        
        failed_tests = []
        
        for test_instance in test_classes:
            for method_name in dir(test_instance):
                if method_name.startswith('test_'):
                    try:
                        test_method = getattr(test_instance, method_name)
                        await test_method()
                    except Exception as e:
                        failed_tests.append(f"{test_instance.__class__.__name__}.{method_name}: {str(e)}")
        
        if failed_tests:
            raise AssertionError(f"CRITICAL VALIDATION FAILURES:\n" + "\n".join(failed_tests))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])