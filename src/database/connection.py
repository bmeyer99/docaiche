"""
Database Connection Management - PRD-002 DB-001
Async DatabaseManager and CacheManager implementations using SQLAlchemy 2.0 and Redis

Provides async database and cache connections with proper connection pooling,
transaction management, and configuration integration from CFG-001.
"""

import logging
import gzip
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, Tuple, AsyncContextManager, Union
from datetime import datetime, timedelta

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, Row
from pydantic import BaseModel

from .models import Base

logger = logging.getLogger(__name__)

# Import configuration system for integration
try:
    from src.core.config import get_system_configuration
except ImportError:
    get_system_configuration = None


# Canonical data models from PRD-002
class DocumentMetadata(BaseModel):
    """Document metadata model for compatibility"""
    model_version: str = "1.0.0"
    word_count: int
    heading_count: int
    code_block_count: int
    content_hash: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentChunk(BaseModel):
    """Document chunk model for compatibility"""
    model_version: str = "1.0.0"
    id: str
    parent_document_id: str
    content: str
    chunk_index: int
    total_chunks: int
    created_at: datetime


class ProcessedDocument(BaseModel):
    """Complete processed document model"""
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
    
    async def connect(self) -> None:
        """Establish async database connection with proper connection pooling"""
        try:
            # Create async engine with SQLite-specific configuration
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL logging in debug mode
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    "check_same_thread": False,  # Required for SQLite with async
                }
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection and enable foreign key constraints
            async with self.engine.begin() as conn:
                # CRITICAL: Enable foreign key constraints for data integrity
                await conn.execute(text("PRAGMA foreign_keys = ON"))
                await conn.execute(text("SELECT 1"))
            
            self._connected = True
            logger.info("Database connection established successfully with foreign key constraints enabled")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connections and cleanup resources"""
        if self.engine:
            await self.engine.dispose()
            self._connected = False
            logger.info("Database connection closed")
    
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
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
            raise
    
    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Row]:
        """
        Fetch single row from query result.
        
        Args:
            query: SQL query string with ? placeholders for positional parameters
            params: Query parameters as tuple
            
        Returns:
            Single row or None if no results
            
        Raises:
            SQLAlchemyError: If query execution fails
        """
        if not self._connected:
            await self.connect()
        
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
                    result = await session.execute(text(query_modified), param_dict)
                else:
                    result = await session.execute(text(query))
                return result.fetchone()
        except SQLAlchemyError as e:
            logger.error(f"Query fetch_one failed: {query[:100]}... Error: {e}")
            raise
    
    async def fetch_all(self, query: str, params: Tuple = ()) -> List[Row]:
        """
        Fetch all rows from query result.
        
        Args:
            query: SQL query string with ? placeholders for positional parameters
            params: Query parameters as tuple
            
        Returns:
            List of rows
            
        Raises:
            SQLAlchemyError: If query execution fails
        """
        if not self._connected:
            await self.connect()
        
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
                    result = await session.execute(text(query_modified), param_dict)
                else:
                    result = await session.execute(text(query))
                return result.fetchall()
        except SQLAlchemyError as e:
            logger.error(f"Query fetch_all failed: {query[:100]}... Error: {e}")
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
        
        try:
            async with self.session_factory() as session:
                async with session.begin():
                    for query, params in queries:
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
                    # Commit is automatic with async context manager
                return True
        except SQLAlchemyError as e:
            logger.error(f"Transaction failed: {e}")
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
        
        async with self.session_factory() as session:
            async with session.begin():
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
    
    async def load_processed_document_from_metadata(self, metadata_row: Row) -> ProcessedDocument:
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
                updated_at=updated_at
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
                    created_at=created_at
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
                updated_at=updated_at
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
        try:
            if not self._connected:
                await self.connect()
            
            # Test basic query
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1 as test"))
                test_result = result.fetchone()
            
            return {
                "status": "healthy",
                "connected": self._connected,
                "database_url": self.database_url.split("://")[0] + "://[REDACTED]",
                "test_query": test_result.test if test_result else None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


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
    
    async def connect(self) -> None:
        """Establish async Redis connection"""
        try:
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
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
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
        try:
            if not self._connected:
                await self.connect()
            
            data = await self.redis_client.get(key)
            if data is None:
                return None
            
            # Decompress if data is compressed
            if key.startswith(("search:results:", "content:processed:", "github:repo:")):
                data = gzip.decompress(data)
            
            # Parse JSON
            return json.loads(data.decode('utf-8'))
            
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed for get({key}): {e}. Gracefully degrading without cache.")
            self._connected = False
            return None
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Set value in cache with compression and TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        try:
            if not self._connected:
                await self.connect()
            
            # Serialize to JSON
            data = json.dumps(value, default=str).encode('utf-8')
            
            # Compress data for specific key patterns
            if key.startswith(("search:results:", "content:processed:", "github:repo:")):
                data = gzip.compress(data)
            
            # Set with TTL
            await self.redis_client.setex(key, ttl, data)
            
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed for set({key}): {e}. Gracefully degrading without cache.")
            self._connected = False
            # Don't raise - allow application to continue without cache
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
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
            logger.warning(f"Redis connection failed for delete({key}): {e}. Gracefully degrading without cache.")
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
            logger.warning(f"Redis connection failed for increment({key}): {e}. Gracefully degrading without cache.")
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
            logger.warning(f"Redis connection failed for expire({key}): {e}. Gracefully degrading without cache.")
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
        try:
            if not self._connected:
                await self.connect()
            
            # Test ping
            ping_result = await self.redis_client.ping()
            
            # Get info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "connected": self._connected,
                "ping": ping_result,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


async def create_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """
    Factory function to create DatabaseManager with configuration integration.
    
    Args:
        config: Optional configuration override
        
    Returns:
        Configured DatabaseManager instance
    """
    if config is None:
        # Integrate with CFG-001 configuration system
        try:
            from src.core.config import get_system_configuration
            system_config = get_system_configuration()
            db_path = f"{system_config.app.data_dir}/docaiche.db"
        except Exception as e:
            logger.warning(f"Could not load configuration, using default: {e}")
            db_path = "/app/data/docaiche.db"
    else:
        db_path = config.get("db_path", "/app/data/docaiche.db")
    
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
            from src.core.config import get_system_configuration
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