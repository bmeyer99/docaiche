"""
PRD-002 Database & Caching Layer - Comprehensive Production Validation
=======================================================================

CRITICAL VALIDATION REQUIREMENTS:
- All 7 database tables match exact PRD schema (lines 33-185)
- P99 latency <10ms for cache operations
- P99 latency <50ms for indexed DB queries
- Redis cache key patterns match specification
- Transaction support with auto-commit/rollback
- Document reconstruction from metadata accuracy
- Integration with PRD-001, PRD-008, PRD-009, PRD-010

SUCCESS CRITERIA: ALL tests must pass for production approval
"""

import pytest
import asyncio
import time
import json
import gzip
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import sqlite3
import aiosqlite
import redis.asyncio as redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import components to validate
try:
    from src.database.manager import DatabaseManager
    from src.cache.manager import CacheManager
    from src.database.models import (
        DocumentMetadata, DocumentChunk, ProcessedDocument,
        SearchQuery, CacheEntry, SystemMetrics, User
    )
    from src.models.document import (
        DocumentMetadata as CanonicalDocumentMetadata,
        DocumentChunk as CanonicalDocumentChunk,
        ProcessedDocument as CanonicalProcessedDocument
    )
    from src.database.schema import create_database_schema
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Performance benchmarking utilities
class PerformanceBenchmark:
    def __init__(self, name: str, target_p99_ms: float):
        self.name = name
        self.target_p99_ms = target_p99_ms
        self.measurements = []
    
    def add_measurement(self, duration_ms: float):
        self.measurements.append(duration_ms)
    
    def get_p99_latency(self) -> float:
        if not self.measurements:
            return float('inf')
        sorted_measurements = sorted(self.measurements)
        p99_index = int(0.99 * len(sorted_measurements))
        return sorted_measurements[min(p99_index, len(sorted_measurements) - 1)]
    
    def meets_target(self) -> bool:
        return self.get_p99_latency() <= self.target_p99_ms

# Test fixtures
@pytest.fixture
async def test_db_path(tmp_path):
    """Create temporary database for testing"""
    db_path = tmp_path / "test_cache.db"
    return str(db_path)

@pytest.fixture
async def redis_client():
    """Mock Redis client for testing"""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = 0
    mock_redis.ttl.return_value = 3600
    return mock_redis

@pytest.fixture
async def database_manager(test_db_path):
    """Create DatabaseManager instance for testing"""
    if not IMPORTS_AVAILABLE:
        pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
    
    manager = DatabaseManager(database_url=f"sqlite+aiosqlite:///{test_db_path}")
    await manager.initialize()
    return manager

@pytest.fixture
async def cache_manager(redis_client):
    """Create CacheManager instance for testing"""
    if not IMPORTS_AVAILABLE:
        pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
    
    with patch('redis.asyncio.from_url', return_value=redis_client):
        manager = CacheManager(redis_url="redis://localhost:6379")
        await manager.initialize()
        return manager

# ===================================================================
# 1. PRD-002 SPECIFICATION COMPLIANCE TESTS
# ===================================================================

class TestPRDSpecificationCompliance:
    """Verify implementation matches exact PRD-002 specifications"""
    
    @pytest.mark.asyncio
    async def test_database_schema_tables_exist(self, test_db_path):
        """Test all 7 required database tables exist with correct schema"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Create database schema
        await create_database_schema(f"sqlite+aiosqlite:///{test_db_path}")
        
        # Verify all 7 tables exist
        async with aiosqlite.connect(test_db_path) as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in await cursor.fetchall()]
        
        required_tables = [
            'document_metadata', 'document_chunks', 'processed_documents',
            'search_queries', 'cache_entries', 'system_metrics', 'users'
        ]
        
        for table in required_tables:
            assert table in tables, f"Required table '{table}' missing from schema"
        
        assert len(tables) == 7, f"Expected 7 tables, found {len(tables)}: {tables}"
    
    @pytest.mark.asyncio
    async def test_document_metadata_table_schema(self, test_db_path):
        """Test document_metadata table matches PRD specification"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        await create_database_schema(f"sqlite+aiosqlite:///{test_db_path}")
        
        async with aiosqlite.connect(test_db_path) as conn:
            cursor = await conn.cursor()
            await cursor.execute("PRAGMA table_info(document_metadata)")
            columns = {row[1]: row[2] for row in await cursor.fetchall()}
        
        required_columns = {
            'id': 'VARCHAR',
            'title': 'VARCHAR',
            'source_url': 'VARCHAR',
            'source_type': 'VARCHAR',
            'content_hash': 'VARCHAR',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME',
            'metadata_json': 'TEXT'
        }
        
        for col_name, col_type in required_columns.items():
            assert col_name in columns, f"Column '{col_name}' missing from document_metadata"
            assert col_type in columns[col_name], f"Column '{col_name}' has wrong type: {columns[col_name]}"
    
    @pytest.mark.asyncio
    async def test_database_indexes_exist(self, test_db_path):
        """Test all required indexes are created"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        await create_database_schema(f"sqlite+aiosqlite:///{test_db_path}")
        
        async with aiosqlite.connect(test_db_path) as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Verify critical indexes exist
        required_indexes = [
            'idx_document_metadata_source_url',
            'idx_document_metadata_content_hash',
            'idx_document_chunks_document_id',
            'idx_search_queries_created_at'
        ]
        
        for index_name in required_indexes:
            assert index_name in indexes, f"Required index '{index_name}' missing"
    
    @pytest.mark.asyncio
    async def test_redis_cache_key_patterns(self, cache_manager):
        """Test Redis cache key patterns match PRD specification"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test document cache key pattern
        doc_key = cache_manager._get_document_key("doc123")
        assert doc_key == "docs_cache:document:doc123"
        
        # Test search cache key pattern
        search_key = cache_manager._get_search_key("test query")
        assert search_key.startswith("docs_cache:search:")
        
        # Test metadata cache key pattern
        metadata_key = cache_manager._get_metadata_key("meta456")
        assert metadata_key == "docs_cache:metadata:meta456"

# ===================================================================
# 2. CANONICAL DATA MODELS VALIDATION
# ===================================================================

class TestCanonicalDataModels:
    """Verify canonical data models match PRD specification"""
    
    def test_canonical_document_metadata_structure(self):
        """Test DocumentMetadata canonical model structure"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test model creation with all required fields
        metadata = CanonicalDocumentMetadata(
            id="doc123",
            title="Test Document",
            source_url="https://example.com/doc",
            source_type="web",
            content_hash="abc123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={"key": "value"}
        )
        
        assert metadata.id == "doc123"
        assert metadata.title == "Test Document"
        assert metadata.source_url == "https://example.com/doc"
        assert metadata.source_type == "web"
        assert metadata.content_hash == "abc123"
        assert isinstance(metadata.created_at, datetime)
        assert isinstance(metadata.updated_at, datetime)
        assert metadata.metadata == {"key": "value"}
    
    def test_canonical_document_chunk_structure(self):
        """Test DocumentChunk canonical model structure"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        chunk = CanonicalDocumentChunk(
            id="chunk123",
            document_id="doc123",
            chunk_index=0,
            content="This is chunk content",
            embedding_vector=[0.1, 0.2, 0.3],
            metadata={"section": "introduction"}
        )
        
        assert chunk.id == "chunk123"
        assert chunk.document_id == "doc123"
        assert chunk.chunk_index == 0
        assert chunk.content == "This is chunk content"
        assert chunk.embedding_vector == [0.1, 0.2, 0.3]
        assert chunk.metadata == {"section": "introduction"}
    
    def test_canonical_processed_document_structure(self):
        """Test ProcessedDocument canonical model structure"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        processed_doc = CanonicalProcessedDocument(
            metadata=CanonicalDocumentMetadata(
                id="doc123",
                title="Test Document",
                source_url="https://example.com/doc",
                source_type="web",
                content_hash="abc123",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={}
            ),
            chunks=[
                CanonicalDocumentChunk(
                    id="chunk123",
                    document_id="doc123",
                    chunk_index=0,
                    content="Chunk content",
                    embedding_vector=[0.1, 0.2],
                    metadata={}
                )
            ]
        )
        
        assert processed_doc.metadata.id == "doc123"
        assert len(processed_doc.chunks) == 1
        assert processed_doc.chunks[0].document_id == "doc123"

# ===================================================================
# 3. PERFORMANCE VALIDATION TESTS
# ===================================================================

class TestPerformanceRequirements:
    """Validate P99 latency requirements: <10ms cache, <50ms indexed DB queries"""
    
    @pytest.mark.asyncio
    async def test_cache_operations_p99_latency(self, cache_manager):
        """Test cache operations meet P99 <10ms requirement"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        cache_benchmark = PerformanceBenchmark("Cache Operations", 10.0)
        
        # Perform 100 cache operations to get statistical significance
        for i in range(100):
            start_time = time.perf_counter()
            
            # Test cache set operation
            await cache_manager.set(f"test_key_{i}", f"test_value_{i}", ttl=3600)
            
            # Test cache get operation
            await cache_manager.get(f"test_key_{i}")
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            cache_benchmark.add_measurement(duration_ms)
        
        p99_latency = cache_benchmark.get_p99_latency()
        assert cache_benchmark.meets_target(), f"Cache P99 latency {p99_latency:.2f}ms exceeds 10ms target"
    
    @pytest.mark.asyncio
    async def test_indexed_db_queries_p99_latency(self, database_manager):
        """Test indexed database queries meet P99 <50ms requirement"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        db_benchmark = PerformanceBenchmark("Indexed DB Queries", 50.0)
        
        # Insert test data first
        test_docs = []
        for i in range(100):
            doc = DocumentMetadata(
                id=f"doc_{i}",
                title=f"Test Document {i}",
                source_url=f"https://example.com/doc{i}",
                source_type="web",
                content_hash=f"hash_{i}",
                metadata_json=json.dumps({"index": i})
            )
            test_docs.append(doc)
        
        async with database_manager.transaction() as session:
            session.add_all(test_docs)
        
        # Perform 100 indexed queries
        for i in range(100):
            start_time = time.perf_counter()
            
            # Query by indexed column (source_url)
            result = await database_manager.get_document_by_url(f"https://example.com/doc{i}")
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            db_benchmark.add_measurement(duration_ms)
        
        p99_latency = db_benchmark.get_p99_latency()
        assert db_benchmark.meets_target(), f"DB query P99 latency {p99_latency:.2f}ms exceeds 50ms target"
    
    @pytest.mark.asyncio
    async def test_redis_compression_performance(self, cache_manager):
        """Test Redis gzip compression doesn't impact performance significantly"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test with large document data
        large_document = {
            "content": "This is a large document content. " * 1000,
            "metadata": {"size": "large", "compressed": True}
        }
        
        compression_benchmark = PerformanceBenchmark("Compression Operations", 20.0)
        
        for i in range(50):
            start_time = time.perf_counter()
            
            # Set with compression
            await cache_manager.set_document(f"large_doc_{i}", large_document)
            
            # Get with decompression
            retrieved_doc = await cache_manager.get_document(f"large_doc_{i}")
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            compression_benchmark.add_measurement(duration_ms)
        
        p99_latency = compression_benchmark.get_p99_latency()
        assert compression_benchmark.meets_target(), f"Compression P99 latency {p99_latency:.2f}ms exceeds 20ms target"

# ===================================================================
# 4. CRITICAL METHOD VALIDATION
# ===================================================================

class TestCriticalMethods:
    """Test critical DatabaseManager and CacheManager methods"""
    
    @pytest.mark.asyncio
    async def test_transaction_context_manager_commit(self, database_manager):
        """Test transaction context manager auto-commit functionality"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        doc_id = "transaction_test_doc"
        
        # Test successful transaction (auto-commit)
        async with database_manager.transaction() as session:
            doc = DocumentMetadata(
                id=doc_id,
                title="Transaction Test",
                source_url="https://example.com/transaction",
                source_type="test",
                content_hash="tx_hash",
                metadata_json="{}"
            )
            session.add(doc)
        
        # Verify document was committed
        result = await database_manager.get_document_metadata(doc_id)
        assert result is not None
        assert result.id == doc_id
        assert result.title == "Transaction Test"
    
    @pytest.mark.asyncio
    async def test_transaction_context_manager_rollback(self, database_manager):
        """Test transaction context manager auto-rollback on exception"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        doc_id = "rollback_test_doc"
        
        # Test transaction rollback on exception
        try:
            async with database_manager.transaction() as session:
                doc = DocumentMetadata(
                    id=doc_id,
                    title="Rollback Test",
                    source_url="https://example.com/rollback",
                    source_type="test",
                    content_hash="rb_hash",
                    metadata_json="{}"
                )
                session.add(doc)
                # Force an exception to trigger rollback
                raise ValueError("Intentional rollback test")
        except ValueError:
            pass  # Expected exception
        
        # Verify document was rolled back (not committed)
        result = await database_manager.get_document_metadata(doc_id)
        assert result is None, "Document should not exist after rollback"
    
    @pytest.mark.asyncio
    async def test_load_processed_document_from_metadata_accuracy(self, database_manager):
        """Test document reconstruction from metadata accuracy"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        doc_id = "reconstruction_test"
        
        # Create complete document with chunks
        async with database_manager.transaction() as session:
            # Create metadata
            metadata = DocumentMetadata(
                id=doc_id,
                title="Reconstruction Test",
                source_url="https://example.com/reconstruct",
                source_type="test",
                content_hash="reconstruct_hash",
                metadata_json=json.dumps({"test": "metadata"})
            )
            session.add(metadata)
            
            # Create chunks
            chunks = []
            for i in range(3):
                chunk = DocumentChunk(
                    id=f"{doc_id}_chunk_{i}",
                    document_id=doc_id,
                    chunk_index=i,
                    content=f"Chunk {i} content",
                    embedding_vector=json.dumps([0.1 * i, 0.2 * i, 0.3 * i]),
                    metadata_json=json.dumps({"chunk_num": i})
                )
                chunks.append(chunk)
                session.add(chunk)
        
        # Test reconstruction
        processed_doc = await database_manager.load_processed_document_from_metadata(doc_id)
        
        assert processed_doc is not None
        assert processed_doc.metadata.id == doc_id
        assert processed_doc.metadata.title == "Reconstruction Test"
        assert len(processed_doc.chunks) == 3
        
        # Verify chunk order and content
        for i, chunk in enumerate(processed_doc.chunks):
            assert chunk.chunk_index == i
            assert chunk.content == f"Chunk {i} content"
            assert chunk.document_id == doc_id
    
    @pytest.mark.asyncio
    async def test_cache_ttl_enforcement(self, cache_manager):
        """Test Redis TTL enforcement and expiration"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Mock redis client to simulate TTL behavior
        cache_manager.redis.ttl = AsyncMock()
        cache_manager.redis.get = AsyncMock()
        
        # Test TTL setting
        await cache_manager.set("ttl_test", "test_value", ttl=1)
        
        # Verify TTL was set
        cache_manager.redis.set.assert_called()
        call_args = cache_manager.redis.set.call_args
        assert 'ex' in call_args.kwargs or len(call_args.args) >= 3
        
        # Test TTL expiration behavior
        cache_manager.redis.get.return_value = None  # Simulate expired key
        result = await cache_manager.get("ttl_test")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_compression_decompression_accuracy(self, cache_manager):
        """Test gzip compression/decompression accuracy"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test with complex nested data
        test_data = {
            "title": "Test Document",
            "content": "This is test content with special characters: àéîôù, 中文, 日本語",
            "metadata": {
                "nested": {
                    "array": [1, 2, 3, "four", {"five": 5}],
                    "boolean": True,
                    "null": None
                }
            },
            "large_text": "Lorem ipsum " * 1000
        }
        
        # Mock Redis to capture and verify compression
        compressed_data = None
        
        async def mock_set(key, value, **kwargs):
            nonlocal compressed_data
            compressed_data = value
            return True
        
        async def mock_get(key):
            return compressed_data
        
        cache_manager.redis.set = mock_set
        cache_manager.redis.get = mock_get
        
        # Set data with compression
        await cache_manager.set_document("compression_test", test_data)
        
        # Verify data was compressed
        assert compressed_data is not None
        assert isinstance(compressed_data, bytes)
        
        # Verify we can decompress and get original data back
        retrieved_data = await cache_manager.get_document("compression_test")
        assert retrieved_data == test_data

# ===================================================================
# 5. SECURITY ASSESSMENT TESTS
# ===================================================================

class TestSecurityAssessment:
    """Validate security requirements and vulnerability prevention"""
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, database_manager):
        """Test parameterized queries prevent SQL injection"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test malicious SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE document_metadata; --",
            "' OR '1'='1",
            "'; DELETE FROM users; --",
            "' UNION SELECT * FROM users --"
        ]
        
        for malicious_input in malicious_inputs:
            # These should be safely handled by parameterized queries
            result = await database_manager.get_document_by_url(malicious_input)
            assert result is None  # Should return None, not cause SQL injection
            
            # Database should still be intact
            # Try a normal query to verify database wasn't corrupted
            normal_result = await database_manager.get_document_metadata("test_doc")
            # This shouldn't raise an exception
    
    @pytest.mark.asyncio
    async def test_database_connection_security(self, database_manager):
        """Test database connection security configuration"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Verify connection string doesn't expose credentials
        assert hasattr(database_manager, 'engine')
        assert not hasattr(database_manager, 'password')
        assert not hasattr(database_manager, 'username')
        
        # Test connection pooling is configured
        engine = database_manager.engine
        assert engine.pool_size > 0
        assert engine.max_overflow >= 0
    
    @pytest.mark.asyncio
    async def test_redis_security_configuration(self, cache_manager):
        """Test Redis security configuration"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Verify Redis client doesn't expose credentials
        assert hasattr(cache_manager, 'redis')
        assert not hasattr(cache_manager, 'password')
        
        # Test Redis connection health
        await cache_manager.redis.ping()
    
    @pytest.mark.asyncio
    async def test_data_serialization_security(self, cache_manager):
        """Test secure data serialization (no code execution)"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test that only safe data types are serialized
        safe_data = {
            "string": "test",
            "number": 123,
            "boolean": True,
            "array": [1, 2, 3],
            "object": {"nested": "value"}
        }
        
        # This should work fine
        await cache_manager.set("safe_data", safe_data)
        result = await cache_manager.get("safe_data")
        assert result == safe_data
        
        # Verify we don't serialize dangerous objects (like functions)
        # This is enforced by JSON serialization which only handles safe types

# ===================================================================
# 6. INTEGRATION TESTING
# ===================================================================

class TestIntegrationWithPRDComponents:
    """Test integration with existing production components"""
    
    @pytest.mark.asyncio
    async def test_integration_with_prd_001_api_foundation(self, database_manager, cache_manager):
        """Test integration with PRD-001 HTTP API Foundation"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Simulate API endpoint using DatabaseManager
        # This tests the Data Access Layer (DAL) usage pattern
        
        # Test document creation via API pattern
        doc_data = {
            "title": "API Integration Test",
            "source_url": "https://api.example.com/doc",
            "source_type": "api",
            "content": "API test content"
        }
        
        # Simulate what an API endpoint would do
        async with database_manager.transaction() as session:
            doc = DocumentMetadata(
                id="api_test_doc",
                title=doc_data["title"],
                source_url=doc_data["source_url"],
                source_type=doc_data["source_type"],
                content_hash="api_hash",
                metadata_json=json.dumps(doc_data)
            )
            session.add(doc)
        
        # Test API search pattern with caching
        search_query = "API test"
        cache_key = f"search:{search_query}"
        
        # Check cache first (API pattern)
        cached_result = await cache_manager.get(cache_key)
        assert cached_result is None  # First time, no cache
        
        # Simulate database search
        result = await database_manager.get_document_metadata("api_test_doc")
        assert result is not None
        
        # Cache the result (API pattern)
        await cache_manager.set(cache_key, {"doc_id": result.id}, ttl=3600)
        
        # Verify cached result
        cached_result = await cache_manager.get(cache_key)
        assert cached_result is not None
        assert cached_result["doc_id"] == "api_test_doc"
    
    @pytest.mark.asyncio
    async def test_integration_with_prd_008_content_processing(self, database_manager):
        """Test integration with PRD-008 Content Processing Pipeline"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Simulate content processor storing processed document
        doc_id = "processed_content_test"
        
        async with database_manager.transaction() as session:
            # Store document metadata
            metadata = DocumentMetadata(
                id=doc_id,
                title="Processed Content Test",
                source_url="https://processor.example.com/doc",
                source_type="processed",
                content_hash="processed_hash",
                metadata_json=json.dumps({"processor": "test"})
            )
            session.add(metadata)
            
            # Store processed chunks
            chunks = []
            for i in range(5):
                chunk = DocumentChunk(
                    id=f"{doc_id}_chunk_{i}",
                    document_id=doc_id,
                    chunk_index=i,
                    content=f"Processed chunk {i}",
                    embedding_vector=json.dumps([0.1, 0.2, 0.3]),
                    metadata_json=json.dumps({"processed": True})
                )
                chunks.append(chunk)
                session.add(chunk)
        
        # Verify content processor can retrieve processed document
        processed_doc = await database_manager.load_processed_document_from_metadata(doc_id)
        assert processed_doc is not None
        assert len(processed_doc.chunks) == 5
        assert all(chunk.document_id == doc_id for chunk in processed_doc.chunks)
    
    @pytest.mark.asyncio
    async def test_integration_with_prd_009_search_orchestration(self, database_manager, cache_manager):
        """Test integration with PRD-009 Search Orchestration"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Simulate search orchestrator workflow
        search_query = "orchestration test"
        
        # 1. Check search cache first
        search_cache_key = f"search:{hash(search_query)}"
        cached_results = await cache_manager.get(search_cache_key)
        assert cached_results is None  # First search
        
        # 2. Perform database search
        # Create test documents first
        test_docs = []
        for i in range(3):
            doc = DocumentMetadata(
                id=f"search_test_{i}",
                title=f"Search Test Document {i}",
                source_url=f"https://search.example.com/doc{i}",
                source_type="search_test",
                content_hash=f"search_hash_{i}",
                metadata_json=json.dumps({"relevance": i + 1})
            )
            test_docs.append(doc)
        
        async with database_manager.transaction() as session:
            session.add_all(test_docs)
        
        # 3. Cache search results
        search_results = [{"id": f"search_test_{i}", "score": i + 1} for i in range(3)]
        await cache_manager.set(search_cache_key, search_results, ttl=3600)
        
        # 4. Verify cached search results
        cached_results = await cache_manager.get(search_cache_key)
        assert cached_results is not None
        assert len(cached_results) == 3
        assert cached_results[0]["id"] == "search_test_0"
    
    @pytest.mark.asyncio
    async def test_integration_with_prd_010_knowledge_enrichment(self, database_manager):
        """Test integration with PRD-010 Knowledge Enrichment"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Simulate knowledge enrichment background task
        doc_id = "enrichment_test"
        
        # 1. Create initial document
        async with database_manager.transaction() as session:
            doc = DocumentMetadata(
                id=doc_id,
                title="Enrichment Test Document",
                source_url="https://enrichment.example.com/doc",
                source_type="enrichment_test",
                content_hash="enrichment_hash",
                metadata_json=json.dumps({"enriched": False})
            )
            session.add(doc)
        
        # 2. Simulate enrichment process updating metadata
        async with database_manager.transaction() as session:
            doc = await session.get(DocumentMetadata, doc_id)
            enriched_metadata = json.loads(doc.metadata_json)
            enriched_metadata.update({
                "enriched": True,
                "topics": ["AI", "ML", "NLP"],
                "sentiment": "positive",
                "summary": "This document discusses AI concepts"
            })
            doc.metadata_json = json.dumps(enriched_metadata)
            doc.updated_at = datetime.utcnow()
        
        # 3. Verify enrichment was stored
        result = await database_manager.get_document_metadata(doc_id)
        metadata = json.loads(result.metadata_json)
        assert metadata["enriched"] is True
        assert "topics" in metadata
        assert "sentiment" in metadata
        assert "summary" in metadata

# ===================================================================
# 7. ERROR HANDLING AND EDGE CASES
# ===================================================================

class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge case scenarios"""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_handling(self):
        """Test graceful handling of database connection failures"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test with invalid database URL
        invalid_manager = DatabaseManager(database_url="sqlite+aiosqlite:///invalid/path/db.sqlite")
        
        # Should handle connection failure gracefully
        with pytest.raises(Exception):  # Expect some form of connection error
            await invalid_manager.initialize()
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_handling(self):
        """Test graceful handling of Redis connection failures"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Create cache manager with invalid Redis URL
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            
            cache_manager = CacheManager(redis_url="redis://invalid:6379")
            
            # Should handle connection failure gracefully
            with pytest.raises(Exception):
                await cache_manager.initialize()
    
    @pytest.mark.asyncio
    async def test_cache_memory_pressure_handling(self, cache_manager):
        """Test cache behavior under memory pressure"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Simulate memory pressure by setting large amounts of data
        large_data = {"content": "x" * 10000}  # 10KB per item
        
        # Set many large items
        for i in range(100):
            await cache_manager.set(f"large_item_{i}", large_data, ttl=3600)
        
        # Verify cache still operates (may evict older items)
        await cache_manager.set("test_after_pressure", "small_value")
        result = await cache_manager.get("test_after_pressure")
        assert result == "small_value"
    
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, database_manager):
        """Test concurrent database operations don't cause corruption"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        async def create_document(doc_id: str):
            async with database_manager.transaction() as session:
                doc = DocumentMetadata(
                    id=doc_id,
                    title=f"Concurrent Test {doc_id}",
                    source_url=f"https://concurrent.example.com/{doc_id}",
                    source_type="concurrent_test",
                    content_hash=f"concurrent_hash_{doc_id}",
                    metadata_json="{}"
                )
                session.add(doc)
        
        # Run concurrent operations
        tasks = [create_document(f"concurrent_{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify all documents were created successfully
        for i in range(10):
            result = await database_manager.get_document_metadata(f"concurrent_{i}")
            assert result is not None
            assert result.id == f"concurrent_{i}"

# ===================================================================
# 8. HEALTH CHECK AND MONITORING
# ===================================================================

class TestHealthCheckAndMonitoring:
    """Test health check endpoints and monitoring capabilities"""
    
    @pytest.mark.asyncio
    async def test_database_health_check(self, database_manager):
        """Test database health check functionality"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test health check method exists and works
        is_healthy = await database_manager.health_check()
        assert is_healthy is True
        
        # Test health check with actual query
        async with database_manager.transaction() as session:
            result = await session.execute(sa.text("SELECT 1"))
            assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_cache_health_check(self, cache_manager):
        """Test cache health check functionality"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Test Redis health check
        is_healthy = await cache_manager.health_check()
        assert is_healthy is True
        
        # Test ping operation
        await cache_manager.redis.ping()
    
    @pytest.mark.asyncio
    async def test_system_metrics_storage(self, database_manager):
        """Test system metrics can be stored and retrieved"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        # Store system metrics
        async with database_manager.transaction() as session:
            metrics = SystemMetrics(
                id="test_metrics",
                metric_name="cache_hit_rate",
                metric_value=0.85,
                timestamp=datetime.utcnow(),
                metadata_json=json.dumps({"component": "cache"})
            )
            session.add(metrics)
        
        # Retrieve metrics
        async with database_manager.transaction() as session:
            result = await session.get(SystemMetrics, "test_metrics")
            assert result is not None
            assert result.metric_name == "cache_hit_rate"
            assert result.metric_value == 0.85

# ===================================================================
# PRODUCTION READINESS SUMMARY TEST
# ===================================================================

class TestProductionReadinessSummary:
    """Final production readiness assessment"""
    
    @pytest.mark.asyncio
    async def test_production_readiness_checklist(self, database_manager, cache_manager):
        """Comprehensive production readiness checklist"""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Required imports not available: {IMPORT_ERROR}")
        
        checklist_results = {}
        
        # 1. Database schema completeness
        try:
            # Test all tables exist
            async with database_manager.transaction() as session:
                result = await session.execute(sa.text("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """))
                table_count = result.scalar()
            checklist_results["database_schema"] = table_count == 7
        except Exception:
            checklist_results["database_schema"] = False
        
        # 2. Cache operations functional
        try:
            await cache_manager.set("readiness_test", "test_value", ttl=60)
            result = await cache_manager.get("readiness_test")
            checklist_results["cache_operations"] = result == "test_value"
        except Exception:
            checklist_results["cache_operations"] = False
        
        # 3. Transaction support working
        try:
            async with database_manager.transaction() as session:
                doc = DocumentMetadata(
                    id="readiness_doc",
                    title="Readiness Test",
                    source_url="https://readiness.test",
                    source_type="test",
                    content_hash="readiness_hash",
                    metadata_json="{}"
                )
                session.add(doc)
            checklist_results["transaction_support"] = True
        except Exception:
            checklist_results["transaction_support"] = False
        
        # 4. Document reconstruction working
        try:
            result = await database_manager.load_processed_document_from_metadata("readiness_doc")
            checklist_results["document_reconstruction"] = result is not None
        except Exception:
            checklist_results["document_reconstruction"] = False
        
        # 5. Health checks working
        try:
            db_health = await database_manager.health_check()
            cache_health = await cache_manager.health_check()
            checklist_results["health_checks"] = db_health and cache_health
        except Exception:
            checklist_results["health_checks"] = False
        
        # Assert all critical components are ready
        for component, status in checklist_results.items():
            assert status, f"Production readiness check failed for: {component}"
        
        # Overall readiness assertion
        all_ready = all(checklist_results.values())
        assert all_ready, f"Production readiness failed. Results: {checklist_results}"

# ===================================================================
# TEST EXECUTION SUMMARY
# ===================================================================

def test_imports_available():
    """Verify all required imports are available"""
    assert IMPORTS_AVAILABLE, f"Required imports not available: {IMPORT_ERROR}"

# Performance test markers
pytestmark = pytest.mark.asyncio