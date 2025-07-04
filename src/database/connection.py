"""
Database Connection Management - PRD-002 DB-001
Async DatabaseManager and CacheManager implementations using SQLAlchemy 2.0 and Redis

Provides async database and cache connections with proper connection pooling,
transaction management, and configuration integration from CFG-001.
"""

import logging
import gzip
import json
import os
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, Tuple, AsyncContextManager
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, Row
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# Import configuration system for integration
try:
    from src.core.config import get_system_configuration
except ImportError:
    get_system_configuration = None

# Import enhanced logging for database operations
try:
    from src.logging_config import DatabaseLogger, setup_structured_logging
    # Initialize database logger
    _db_logger = DatabaseLogger(logger)
except ImportError:
    _db_logger = None
    logger.warning("DatabaseLogger not available - using basic logging")


# Canonical data models from PRD-002
class DocumentMetadata(BaseModel):
    """Document metadata model for compatibility"""

    model_config = {"protected_namespaces": ()}

    model_version: str = "1.0.0"
    word_count: int
    heading_count: int
    code_block_count: int
    content_hash: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentChunk(BaseModel):
    """Document chunk model for compatibility"""

    model_config = {"protected_namespaces": ()}

    model_version: str = "1.0.0"
    id: str
    parent_document_id: str
    content: str
    chunk_index: int
    total_chunks: int
    created_at: datetime


class ProcessedDocument(BaseModel):
    """Complete processed document model"""

    model_config = {"protected_namespaces": ()}

    model_version: str = "1.0.0"
    id: str
    title: str
    full_content: str
    source_url: str
    technology: str
    metadata: DocumentMetadata
    quality_score: float
    chunks: List[DocumentChunk]
    created_at: datetime
    updated_at: Optional[datetime] = None


class UploadResult(BaseModel):
    """Result of document upload operation to AnythingLLM"""

    model_config = {"protected_namespaces": ()}

    document_id: str
    workspace_slug: str
    total_chunks: int
    successful_uploads: int
    failed_uploads: int
    uploaded_chunk_ids: List[str]
    failed_chunk_ids: List[str]
    errors: List[str]


class DatabaseManager:
    """
    Manages async database connections and executes queries using SQLAlchemy 2.0.

    Implements exact interface specified in PRD-002 with async/await patterns,
    connection pooling, and transaction support.
    """

    def __init__(self, database_url: str):
        """
        Initialize DatabaseManager with async SQLAlchemy engine.

        Args:
            database_url: SQLite database URL (e.g., "sqlite+aiosqlite:///app/data/docaiche.db")
        """
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._connected = False
        self._connection_pool_stats = {"active": 0, "idle": 0, "size": 1}

    async def connect(self) -> None:
        """Establish async database connection with proper connection pooling"""
        start_time = time.time()
        try:
            if _db_logger:
                _db_logger.log_connection_event("connection_attempt", client_ip="localhost")
            # Create async engine with database-specific configuration
            connect_args = {}
            pool_size = 10
            max_overflow = 20
            
            # Configure based on database type
            if self.database_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
                pool_size = 1  # SQLite doesn't support true concurrency
                max_overflow = 0
            elif self.database_url.startswith("postgresql"):
                # PostgreSQL optimizations
                connect_args = {
                    "server_settings": {
                        "application_name": "docaiche",
                        "jit": "off"  # Disable JIT for more predictable performance
                    },
                    "command_timeout": 60,
                    "prepared_statement_cache_size": 0,  # Disable to prevent cache bloat
                }
                pool_size = 10
                max_overflow = 20
            
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL logging in debug mode
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=pool_size,
                max_overflow=max_overflow,
                connect_args=connect_args,
            )

            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Test connection and configure database-specific settings
            async with self.engine.begin() as conn:
                if self.database_url.startswith("sqlite"):
                    # SQLite-specific configuration
                    await conn.execute(text("PRAGMA foreign_keys = ON"))
                    await conn.execute(text("PRAGMA journal_mode = WAL"))
                    await conn.execute(text("PRAGMA synchronous = NORMAL"))
                    await conn.execute(text("PRAGMA wal_checkpoint(PASSIVE)"))
                elif self.database_url.startswith("postgresql"):
                    # PostgreSQL-specific configuration
                    # Set search path if needed
                    await conn.execute(text("SET search_path TO public"))
                    # Ensure we're using UTC
                    await conn.execute(text("SET timezone = 'UTC'"))
                
                # Test connection
                await conn.execute(text("SELECT 1"))

            self._connected = True
            connection_duration = (time.time() - start_time) * 1000
            logger.info(
                "Database connection established successfully with foreign key constraints enabled"
            )
            if _db_logger:
                _db_logger.log_connection_event(
                    "connection_established", 
                    pool_stats=self._connection_pool_stats,
                    duration_ms=connection_duration,
                    client_ip="localhost"
                )

        except Exception as e:
            connection_duration = (time.time() - start_time) * 1000
            logger.error(f"Failed to connect to database: {e}")
            if _db_logger:
                _db_logger.log_connection_event(
                    "connection_failed", 
                    error_message=str(e),
                    duration_ms=connection_duration,
                    client_ip="localhost"
                )
            raise

    async def disconnect(self) -> None:
        """Close database connections and cleanup resources"""
        if self.engine:
            if _db_logger:
                _db_logger.log_connection_event("disconnection_initiated", client_ip="localhost")
            await self.engine.dispose()
            self._connected = False
            logger.info("Database connection closed")
            if _db_logger:
                _db_logger.log_connection_event("disconnection_completed", client_ip="localhost")

    async def execute(self, query: str, params: Tuple = ()) -> None:
        """
        Execute a SQL query with parameters.

        Args:
            query: SQL query string with ? placeholders for positional parameters
            params: Query parameters as tuple

        Raises:
            SQLAlchemyError: If query execution fails
        """
        if not self._connected:
            await self.connect()

        start_time = time.time()
        operation_type = query.strip().split()[0].upper()
        table_name = self._extract_table_name(query)
        
        try:
            async with self.session_factory() as session:
                # Convert positional parameters to dictionary for SQLAlchemy text()
                if params:
                    # For ? placeholders, convert to numbered parameters
                    param_dict = {f"param_{i}": param for i, param in enumerate(params)}
                    # Replace ? with :param_0, :param_1, etc.
                    query_modified = query
                    for i in range(len(params)):
                        query_modified = query_modified.replace("?", f":param_{i}", 1)
                    await session.execute(text(query_modified), param_dict)
                else:
                    await session.execute(text(query))
                await session.commit()
                
                # Log successful execution
                duration_ms = (time.time() - start_time) * 1000
                if _db_logger:
                    _db_logger.log_query_performance(
                        operation=operation_type,
                        table=table_name,
                        duration_ms=duration_ms,
                        rows_affected=1,  # Estimate for execute operations
                        query_hash=hash(query) % 10000,
                        client_ip="localhost"
                    )
                    
        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
            if _db_logger:
                _db_logger.log_query_performance(
                    operation=f"{operation_type}_ERROR",
                    table=table_name,
                    duration_ms=duration_ms,
                    rows_affected=0,
                    error_message=str(e),
                    query_hash=hash(query) % 10000,
                    client_ip="localhost"
                )
            raise

    async def fetch_one(self, query: str, params = None) -> Optional[Row]:
        """
        Fetch single row from query result.

        Args:
            query: SQL query string with :named or ? placeholders
            params: Query parameters as tuple (for ? placeholders) or dict (for :named placeholders)

        Returns:
            Single row or None if no results

        Raises:
            SQLAlchemyError: If query execution fails
        """
        if not self._connected:
            await self.connect()

        start_time = time.time()
        operation_type = "SELECT_ONE"
        table_name = self._extract_table_name(query)
        
        try:
            async with self.session_factory() as session:
                if params is not None:
                    if isinstance(params, dict):
                        # Named parameters - use as-is
                        result = await session.execute(text(query), params)
                    elif isinstance(params, (tuple, list)):
                        # Positional parameters - convert to named parameters
                        param_dict = {}
                        query_modified = query
                        for i, value in enumerate(params):
                            param_name = f"param_{i}"
                            param_dict[param_name] = value
                            # Replace ? with :param_0, :param_1, etc.
                            query_modified = query_modified.replace("?", f":{param_name}", 1)
                        result = await session.execute(text(query_modified), param_dict)
                    else:
                        # Single parameter value
                        param_dict = {"param_0": params}
                        query_modified = query.replace("?", ":param_0", 1)
                        result = await session.execute(text(query_modified), param_dict)
                else:
                    result = await session.execute(text(query))
                row = result.fetchone()
                
                # Log successful fetch
                duration_ms = (time.time() - start_time) * 1000
                rows_returned = 1 if row else 0
                if _db_logger:
                    _db_logger.log_query_performance(
                        operation=operation_type,
                        table=table_name,
                        duration_ms=duration_ms,
                        rows_affected=rows_returned,
                        query_hash=hash(query) % 10000,
                        client_ip="localhost"
                    )
                
                # Convert Row to dict for easier access
                return dict(row._mapping) if row else None
                
        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Query fetch_one failed: {query[:100]}... Error: {e}")
            if _db_logger:
                _db_logger.log_query_performance(
                    operation=f"{operation_type}_ERROR",
                    table=table_name,
                    duration_ms=duration_ms,
                    rows_affected=0,
                    error_message=str(e),
                    query_hash=hash(query) % 10000,
                    client_ip="localhost"
                )
            raise

    async def fetch_all(self, query: str, params = None) -> List[Row]:
        """
        Fetch all rows from query result.

        Args:
            query: SQL query string with :named or ? placeholders
            params: Query parameters as tuple (for ? placeholders) or dict (for :named placeholders)

        Returns:
            List of rows

        Raises:
            SQLAlchemyError: If query execution fails
        """
        if not self._connected:
            await self.connect()

        start_time = time.time()
        operation_type = "SELECT_ALL"
        table_name = self._extract_table_name(query)
        
        try:
            async with self.session_factory() as session:
                if params is not None:
                    if isinstance(params, dict):
                        # Named parameters - use as-is
                        result = await session.execute(text(query), params)
                    elif isinstance(params, (tuple, list)):
                        # Positional parameters - convert to named parameters
                        param_dict = {}
                        query_modified = query
                        for i, value in enumerate(params):
                            param_name = f"param_{i}"
                            param_dict[param_name] = value
                            # Replace ? with :param_0, :param_1, etc.
                            query_modified = query_modified.replace("?", f":{param_name}", 1)
                        result = await session.execute(text(query_modified), param_dict)
                    else:
                        # Single parameter value
                        param_dict = {"param_0": params}
                        query_modified = query.replace("?", ":param_0", 1)
                        result = await session.execute(text(query_modified), param_dict)
                else:
                    result = await session.execute(text(query))
                rows = result.fetchall()
                
                # Log successful fetch
                duration_ms = (time.time() - start_time) * 1000
                rows_returned = len(rows)
                if _db_logger:
                    _db_logger.log_query_performance(
                        operation=operation_type,
                        table=table_name,
                        duration_ms=duration_ms,
                        rows_affected=rows_returned,
                        query_hash=hash(query) % 10000,
                        client_ip="localhost"
                    )
                
                # Convert Rows to list of dicts for easier access
                return [dict(row._mapping) for row in rows]
                
        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Query fetch_all failed: {query[:100]}... Error: {e}")
            if _db_logger:
                _db_logger.log_query_performance(
                    operation=f"{operation_type}_ERROR",
                    table=table_name,
                    duration_ms=duration_ms,
                    rows_affected=0,
                    error_message=str(e),
                    query_hash=hash(query) % 10000,
                    client_ip="localhost"
                )
            raise

    async def execute_transaction(self, queries: List[Tuple[str, Tuple]]) -> bool:
        """
        Execute multiple queries in a single transaction.

        Args:
            queries: List of (query, params) tuples

        Returns:
            True if transaction succeeded, False otherwise
        """
        if not self._connected:
            await self.connect()

        start_time = time.time()
        transaction_id = f"tx_{int(time.time() * 1000000) % 1000000}"
        
        if _db_logger:
            _db_logger.log_transaction_event("begin", transaction_id, query_count=len(queries), client_ip="localhost")
        
        try:
            async with self.session_factory() as session:
                async with session.begin():
                    for query, params in queries:
                        # Convert positional parameters to dictionary for SQLAlchemy text()
                        if params:
                            # For ? placeholders, convert to numbered parameters
                            param_dict = {
                                f"param_{i}": param for i, param in enumerate(params)
                            }
                            # Replace ? with :param_0, :param_1, etc.
                            query_modified = query
                            for i in range(len(params)):
                                query_modified = query_modified.replace(
                                    "?", f":param_{i}", 1
                                )
                            await session.execute(text(query_modified), param_dict)
                        else:
                            await session.execute(text(query))
                    # Commit is automatic with async context manager
                
                # Log successful transaction
                duration_ms = (time.time() - start_time) * 1000
                if _db_logger:
                    _db_logger.log_transaction_event(
                        "commit", 
                        transaction_id, 
                        duration_ms=duration_ms,
                        query_count=len(queries),
                        client_ip="localhost"
                    )
                return True
                
        except SQLAlchemyError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Transaction failed: {e}")
            if _db_logger:
                _db_logger.log_transaction_event(
                    "rollback", 
                    transaction_id, 
                    duration_ms=duration_ms,
                    error_message=str(e),
                    query_count=len(queries),
                    client_ip="localhost"
                )
            return False

    @asynccontextmanager
    async def transaction(self) -> AsyncContextManager[AsyncSession]:
        """
        Provides async context manager for database transactions.

        Usage:
            async with db_manager.transaction() as session:
                await session.execute(text("INSERT INTO ..."), params)
                await session.execute(text("UPDATE ..."), params)
                # Auto-commit on success, auto-rollback on exception

        Returns:
            AsyncContextManager that handles transaction lifecycle
        """
        if not self._connected:
            await self.connect()

        start_time = time.time()
        transaction_id = f"ctx_tx_{int(time.time() * 1000000) % 1000000}"
        
        if _db_logger:
            _db_logger.log_transaction_event("context_begin", transaction_id, client_ip="localhost")

        async with self.session_factory() as session:
            async with session.begin():
                try:
                    yield session
                    # Log successful context transaction
                    duration_ms = (time.time() - start_time) * 1000
                    if _db_logger:
                        _db_logger.log_transaction_event(
                            "context_commit", 
                            transaction_id, 
                            duration_ms=duration_ms,
                            client_ip="localhost"
                        )
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    if _db_logger:
                        _db_logger.log_transaction_event(
                            "context_rollback", 
                            transaction_id, 
                            duration_ms=duration_ms,
                            error_message=str(e),
                            client_ip="localhost"
                        )
                    await session.rollback()
                    raise

    async def load_processed_document_from_metadata(
        self, metadata_row: Row
    ) -> ProcessedDocument:
        """
        Reconstructs ProcessedDocument from database metadata row.

        Args:
            metadata_row: Row from content_metadata table query result

        Returns:
            Complete ProcessedDocument with metadata and chunks
        """
        try:
            # Extract basic metadata from row
            content_id = metadata_row.content_id
            title = metadata_row.title
            source_url = metadata_row.source_url
            technology = metadata_row.technology
            content_hash = metadata_row.content_hash
            quality_score = metadata_row.quality_score
            created_at = metadata_row.created_at
            updated_at = metadata_row.updated_at

            # Create document metadata
            doc_metadata = DocumentMetadata(
                word_count=metadata_row.word_count,
                heading_count=metadata_row.heading_count,
                code_block_count=metadata_row.code_block_count,
                content_hash=content_hash,
                created_at=created_at,
                updated_at=updated_at,
            )

            # For now, create minimal chunks (will be enhanced when cache is available)
            # This is a placeholder implementation to satisfy the interface
            chunks = [
                DocumentChunk(
                    id=f"{content_id}_chunk_0",
                    parent_document_id=content_id,
                    content="[Content loading from cache not yet implemented]",
                    chunk_index=0,
                    total_chunks=metadata_row.chunk_count or 1,
                    created_at=created_at,
                )
            ]

            # Create processed document
            processed_doc = ProcessedDocument(
                id=content_id,
                title=title,
                full_content="[Full content loading from cache not yet implemented]",
                source_url=source_url,
                technology=technology,
                metadata=doc_metadata,
                quality_score=quality_score,
                chunks=chunks,
                created_at=created_at,
                updated_at=updated_at,
            )

            return processed_doc

        except Exception as e:
            logger.error(f"Failed to load processed document from metadata: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check database health and return status information.

        Returns:
            Dictionary with health status and connection info
        """
        start_time = time.time()
        try:
            if not self._connected:
                await self.connect()

            # Test basic query
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1 as test"))
                test_result = result.fetchone()

            duration_ms = (time.time() - start_time) * 1000
            health_status = {
                "status": "healthy",
                "connected": self._connected,
                "database_url": self.database_url.split("://")[0] + "://[REDACTED]",
                "test_query": test_result.test if test_result else None,
                "health_check_duration_ms": duration_ms,
            }
            
            if _db_logger:
                _db_logger.log_query_performance(
                    operation="HEALTH_CHECK",
                    table="system",
                    duration_ms=duration_ms,
                    rows_affected=1,
                    client_ip="localhost"
                )
            
            return health_status
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            if _db_logger:
                _db_logger.log_connection_event(
                    "health_check_failed",
                    error_message=str(e),
                    duration_ms=duration_ms,
                    client_ip="localhost"
                )
            return {"status": "unhealthy", "connected": False, "error": str(e)}
    
    def _extract_table_name(self, query: str) -> str:
        """
        Extract table name from SQL query for logging purposes.
        
        Args:
            query: SQL query string
            
        Returns:
            Table name or 'unknown' if not found
        """
        try:
            # Simple regex-free table extraction for common SQL patterns
            query_upper = query.upper().strip()
            
            # Handle SELECT queries
            if query_upper.startswith('SELECT'):
                if ' FROM ' in query_upper:
                    from_part = query_upper.split(' FROM ')[1]
                    table = from_part.split()[0].strip()
                    return table.replace('`', '').replace('"', '').replace("'", '')
            
            # Handle INSERT queries
            elif query_upper.startswith('INSERT'):
                if ' INTO ' in query_upper:
                    into_part = query_upper.split(' INTO ')[1]
                    table = into_part.split()[0].strip()
                    return table.replace('`', '').replace('"', '').replace("'", '')
                    
            # Handle UPDATE queries
            elif query_upper.startswith('UPDATE'):
                update_part = query_upper.split('UPDATE')[1].strip()
                table = update_part.split()[0].strip()
                return table.replace('`', '').replace('"', '').replace("'", '')
                
            # Handle DELETE queries
            elif query_upper.startswith('DELETE'):
                if ' FROM ' in query_upper:
                    from_part = query_upper.split(' FROM ')[1]
                    table = from_part.split()[0].strip()
                    return table.replace('`', '').replace('"', '').replace("'", '')
                    
            return 'unknown'
        except Exception:
            return 'unknown'


class CacheManager:
    """
    Manages Redis connections and cache operations with async patterns.

    Implements exact interface specified in PRD-002 with compression,
    TTL management, and proper error handling.
    """

    def __init__(self, redis_config: Dict[str, Any]):
        """
        Initialize CacheManager with Redis configuration.

        Args:
            redis_config: Redis configuration dictionary from CFG-001
        """
        self.redis_config = redis_config
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False
        
        # Initialize cache operation logger
        try:
            from src.logging_config import ExternalServiceLogger
            self._cache_logger = ExternalServiceLogger(logger)
        except ImportError:
            self._cache_logger = None

    async def connect(self) -> None:
        """Establish async Redis connection"""
        start_time = time.time()
        try:
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint=f"{self.redis_config.get('host', 'redis')}:{self.redis_config.get('port', 6379)}",
                    method="CONNECT",
                    duration_ms=0,
                    status_code=0
                )
            # Create Redis connection with configuration from CFG-001
            self.redis_client = redis.Redis(
                host=self.redis_config.get("host", "redis"),
                port=self.redis_config.get("port", 6379),
                password=self.redis_config.get("password"),
                db=self.redis_config.get("db", 0),
                max_connections=self.redis_config.get("max_connections", 20),
                socket_timeout=self.redis_config.get("socket_timeout", 5),
                socket_connect_timeout=self.redis_config.get("connection_timeout", 5),
                decode_responses=False,  # Handle binary data for compression
                ssl=self.redis_config.get("ssl", False),
            )

            # Test connection
            await self.redis_client.ping()
            self._connected = True
            connection_duration = (time.time() - start_time) * 1000
            logger.info("Redis connection established successfully")
            
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint=f"{self.redis_config.get('host', 'redis')}:{self.redis_config.get('port', 6379)}",
                    method="CONNECT",
                    duration_ms=connection_duration,
                    status_code=200
                )

        except Exception as e:
            connection_duration = (time.time() - start_time) * 1000
            logger.error(f"Failed to connect to Redis: {e}")
            
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint=f"{self.redis_config.get('host', 'redis')}:{self.redis_config.get('port', 6379)}",
                    method="CONNECT",
                    duration_ms=connection_duration,
                    status_code=500,
                    error_message=str(e)
                )
            raise

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.aclose()
            self._connected = False
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with automatic decompression.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or Redis unavailable
        """
        start_time = time.time()
        try:
            if not self._connected:
                await self.connect()

            data = await self.redis_client.get(key)
            cache_hit = data is not None
            
            if data is None:
                duration_ms = (time.time() - start_time) * 1000
                if self._cache_logger:
                    self._cache_logger.log_service_call(
                        service="redis",
                        endpoint="GET",
                        method="GET",
                        duration_ms=duration_ms,
                        status_code=404,
                        cache_key=key,
                        cache_hit=False
                    )
                return None

            # Decompress if data is compressed
            if key.startswith(
                ("search:results:", "content:processed:", "github:repo:")
            ):
                data = gzip.decompress(data)

            # Parse JSON
            result = json.loads(data.decode("utf-8"))
            duration_ms = (time.time() - start_time) * 1000
            
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="GET",
                    method="GET",
                    duration_ms=duration_ms,
                    status_code=200,
                    cache_key=key,
                    cache_hit=True,
                    data_size_bytes=len(data)
                )
            
            return result

        except (ConnectionError, TimeoutError, OSError) as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"Redis connection failed for get({key}): {e}. Gracefully degrading without cache."
            )
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="GET",
                    method="GET",
                    duration_ms=duration_ms,
                    status_code=503,
                    cache_key=key,
                    error_message=str(e)
                )
            self._connected = False
            return None
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Cache get failed for key {key}: {e}")
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="GET",
                    method="GET",
                    duration_ms=duration_ms,
                    status_code=500,
                    cache_key=key,
                    error_message=str(e)
                )
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Set value in cache with compression and TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        start_time = time.time()
        try:
            if not self._connected:
                await self.connect()

            # Serialize to JSON
            data = json.dumps(value, default=str).encode("utf-8")

            # Compress data for specific key patterns
            if key.startswith(
                ("search:results:", "content:processed:", "github:repo:")
            ):
                data = gzip.compress(data)

            # Set with TTL
            await self.redis_client.setex(key, ttl, data)
            duration_ms = (time.time() - start_time) * 1000
            
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="SET",
                    method="SET",
                    duration_ms=duration_ms,
                    status_code=200,
                    cache_key=key,
                    data_size_bytes=len(data),
                    ttl_seconds=ttl
                )

        except (ConnectionError, TimeoutError, OSError) as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"Redis connection failed for set({key}): {e}. Gracefully degrading without cache."
            )
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="SET",
                    method="SET",
                    duration_ms=duration_ms,
                    status_code=503,
                    cache_key=key,
                    error_message=str(e)
                )
            self._connected = False
            # Don't raise - allow application to continue without cache
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Cache set failed for key {key}: {e}")
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="SET",
                    method="SET",
                    duration_ms=duration_ms,
                    status_code=500,
                    cache_key=key,
                    error_message=str(e)
                )
            # Don't raise - allow application to continue without cache

    async def delete(self, key: str) -> None:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete
        """
        try:
            if not self._connected:
                await self.connect()

            await self.redis_client.delete(key)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(
                f"Redis connection failed for delete({key}): {e}. Gracefully degrading without cache."
            )
            self._connected = False
            # Don't raise - allow application to continue without cache
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            # Don't raise - allow application to continue without cache

    async def increment(self, key: str) -> int:
        """
        Increment counter value and return new value.

        Args:
            key: Cache key for counter

        Returns:
            New counter value, or 1 if Redis unavailable
        """
        try:
            if not self._connected:
                await self.connect()

            return await self.redis_client.incr(key)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(
                f"Redis connection failed for increment({key}): {e}. Gracefully degrading without cache."
            )
            self._connected = False
            return 1  # Return default value when Redis unavailable
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            return 1  # Return default value on error

    async def expire(self, key: str, seconds: int) -> None:
        """
        Set expiration time for existing key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds
        """
        try:
            if not self._connected:
                await self.connect()

            await self.redis_client.expire(key, seconds)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(
                f"Redis connection failed for expire({key}): {e}. Gracefully degrading without cache."
            )
            self._connected = False
            # Don't raise - allow application to continue without cache
        except Exception as e:
            logger.error(f"Cache expire failed for key {key}: {e}")
            # Don't raise - allow application to continue without cache

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health and return status information.

        Returns:
            Dictionary with health status and connection info
        """
        start_time = time.time()
        try:
            if not self._connected:
                await self.connect()

            # Test ping
            ping_result = await self.redis_client.ping()

            # Get info
            info = await self.redis_client.info()
            duration_ms = (time.time() - start_time) * 1000
            
            health_status = {
                "status": "healthy",
                "connected": self._connected,
                "ping": ping_result,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "health_check_duration_ms": duration_ms,
            }
            
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="HEALTH_CHECK",
                    method="PING",
                    duration_ms=duration_ms,
                    status_code=200
                )
            
            return health_status
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            if self._cache_logger:
                self._cache_logger.log_service_call(
                    service="redis",
                    endpoint="HEALTH_CHECK",
                    method="PING",
                    duration_ms=duration_ms,
                    status_code=500,
                    error_message=str(e)
                )
            return {"status": "unhealthy", "connected": False, "error": str(e)}


async def create_database_manager(
    config: Optional[Dict[str, Any]] = None,
) -> DatabaseManager:
    """
    Factory function to create DatabaseManager with configuration integration.

    Args:
        config: Optional configuration override

    Returns:
        Configured DatabaseManager instance
    """
    # Check for DATABASE_URL environment variable first
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        # Use the provided DATABASE_URL
        logger.info(f"Using DATABASE_URL from environment: {database_url.split('@')[0]}...")
    elif config and "database_url" in config:
        database_url = config["database_url"]
    else:
        # Fall back to SQLite configuration
        if config is None:
            # Integrate with CFG-001 configuration system
            try:
                if get_system_configuration is not None:
                    system_config = get_system_configuration()
                    db_path = f"{system_config.app.data_dir}/docaiche.db"
                else:
                    db_path = "/data/docaiche.db"
            except Exception as e:
                logger.warning(f"Could not load configuration, using default: {e}")
                db_path = "/data/docaiche.db"
        else:
            db_path = config.get("db_path", "/data/docaiche.db")

        # Fix SQLite URL construction for aiosqlite
        # Convert relative paths to absolute and ensure proper URL format
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

        # Ensure database directory exists for SQLite
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)

        # Construct proper SQLite URL for aiosqlite
        database_url = f"sqlite+aiosqlite:///{db_path}"
    
    return DatabaseManager(database_url)


async def create_cache_manager(config: Optional[Dict[str, Any]] = None) -> CacheManager:
    """
    Factory function to create CacheManager with configuration integration.

    Args:
        config: Optional configuration override

    Returns:
        Configured CacheManager instance
    """
    if config is None:
        # Integrate with CFG-001 configuration system
        try:
            if get_system_configuration is not None:
                system_config = get_system_configuration()
                redis_config = {
                    "host": system_config.redis.host,
                    "port": system_config.redis.port,
                    "password": system_config.redis.password,
                    "db": system_config.redis.db,
                    "max_connections": system_config.redis.max_connections,
                    "connection_timeout": system_config.redis.connection_timeout,
                    "socket_timeout": system_config.redis.socket_timeout,
                    "ssl": system_config.redis.ssl,
                }
            else:
                redis_config = {
                    "host": "redis",
                    "port": 6379,
                    "db": 0,
                    "max_connections": 20,
                    "connection_timeout": 5,
                    "socket_timeout": 5,
                    "ssl": False,
                }
        except Exception as e:
            logger.warning(f"Could not load configuration, using defaults: {e}")
            redis_config = {
                "host": "redis",
                "port": 6379,
                "db": 0,
                "max_connections": 20,
                "connection_timeout": 5,
                "socket_timeout": 5,
                "ssl": False,
            }
    else:
        redis_config = config

    return CacheManager(redis_config)
