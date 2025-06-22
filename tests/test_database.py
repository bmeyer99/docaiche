"""
Tests for Database & Caching Layer - PRD-002 DB-001
Validates database initialization, connection management, and basic operations
"""

import pytest
import tempfile
import os
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.database.init_db import DatabaseInitializer
from src.database.connection import DatabaseManager, CacheManager, create_database_manager, create_cache_manager


class TestDatabaseInitializer:
    """Test database initialization functionality"""
    
    def test_database_initializer_creation(self):
        """Test DatabaseInitializer can be created with custom path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            assert initializer.db_path == db_path
            assert initializer.schema_version == "1.0.0"
    
    def test_database_initializer_default_path(self):
        """Test DatabaseInitializer uses configuration system for default path"""
        with patch('src.database.init_db.get_system_configuration') as mock_config:
            mock_config.return_value.app.data_dir = "/test/data"
            initializer = DatabaseInitializer()
            assert initializer.db_path == "/test/data/docaiche.db"
    
    def test_database_initializer_fallback_path(self):
        """Test DatabaseInitializer falls back to default when config fails"""
        with patch('src.database.init_db.get_system_configuration', side_effect=Exception("Config error")):
            initializer = DatabaseInitializer()
            assert initializer.db_path == "/app/data/docaiche.db"
    
    def test_database_initialization(self):
        """Test database initialization creates all tables and indexes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            initializer = DatabaseInitializer(db_path)
            
            # Initialize database
            initializer.initialize_database()
            
            # Verify database file was created
            assert os.path.exists(db_path)
            
            # Get database info
            info = initializer.get_database_info()
            assert info["exists"] is True
            assert info["table_count"] == 7  # All required tables
            assert info["schema_version"] == "1.0.0"
    
    def test_database_force_recreate(self):
        """Test force recreation removes existing database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            # Create initial database
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            assert os.path.exists(db_path)
            
            # Force recreate
            initializer.initialize_database(force_recreate=True)
            assert os.path.exists(db_path)
            
            # Verify it's a fresh database
            info = initializer.get_database_info()
            assert info["schema_version"] == "1.0.0"
    
    def test_database_info_nonexistent(self):
        """Test database info for non-existent database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "nonexistent.db")
            initializer = DatabaseInitializer(db_path)
            
            info = initializer.get_database_info()
            assert info["exists"] is False
            assert info["path"] == db_path


class TestDatabaseManager:
    """Test DatabaseManager async functionality"""
    
    @pytest.mark.asyncio
    async def test_database_manager_creation(self):
        """Test DatabaseManager can be created with database URL"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            db_url = f"sqlite+aiosqlite:///{db_path}"
            
            manager = DatabaseManager(db_url)
            assert manager.database_url == db_url
            assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_database_manager_connect_disconnect(self):
        """Test DatabaseManager connection lifecycle"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            # Initialize database first
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Test connection
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            
            await manager.connect()
            assert manager._connected is True
            
            await manager.disconnect()
            assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_database_manager_health_check(self):
        """Test DatabaseManager health check functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            # Initialize database
            initializer = DatabaseInitializer(db_path)
            initializer.initialize_database()
            
            # Test health check
            db_url = f"sqlite+aiosqlite:///{db_path}"
            manager = DatabaseManager(db_url)
            
            health = await manager.health_check()
            assert health["status"] == "healthy"
            assert health["connected"] is True
            assert health["test_query"] == 1


class TestCacheManager:
    """Test CacheManager functionality with mocked Redis"""
    
    @pytest.mark.asyncio
    async def test_cache_manager_creation(self):
        """Test CacheManager can be created with Redis config"""
        redis_config = {
            "host": "localhost",
            "port": 6379,
            "db": 0
        }
        
        manager = CacheManager(redis_config)
        assert manager.redis_config == redis_config
        assert manager._connected is False
    
    @pytest.mark.asyncio
    async def test_cache_manager_health_check_unhealthy(self):
        """Test CacheManager health check when Redis is unavailable"""
        redis_config = {
            "host": "nonexistent-redis",
            "port": 6379,
            "db": 0
        }
        
        manager = CacheManager(redis_config)
        health = await manager.health_check()
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health


class TestFactoryFunctions:
    """Test factory functions for creating managers"""
    
    @pytest.mark.asyncio
    async def test_create_database_manager_with_config(self):
        """Test create_database_manager with custom config"""
        config = {"db_path": "/custom/path/db.sqlite"}
        manager = await create_database_manager(config)
        assert isinstance(manager, DatabaseManager)
        assert "sqlite+aiosqlite:///custom/path/db.sqlite" in manager.database_url
    
    @pytest.mark.asyncio
    async def test_create_database_manager_default(self):
        """Test create_database_manager with system configuration"""
        with patch('src.database.connection.get_system_configuration') as mock_config:
            mock_config.return_value.app.data_dir = "/test/data"
            manager = await create_database_manager()
            assert isinstance(manager, DatabaseManager)
            assert "sqlite+aiosqlite:///test/data/docaiche.db" in manager.database_url
    
    @pytest.mark.asyncio
    async def test_create_cache_manager_with_config(self):
        """Test create_cache_manager with custom config"""
        config = {"host": "custom-redis", "port": 6380}
        manager = await create_cache_manager(config)
        assert isinstance(manager, CacheManager)
        assert manager.redis_config == config
    
    @pytest.mark.asyncio
    async def test_create_cache_manager_default(self):
        """Test create_cache_manager with system configuration"""
        with patch('src.database.connection.get_system_configuration') as mock_config:
            mock_redis = MagicMock()
            mock_redis.host = "config-redis"
            mock_redis.port = 6379
            mock_redis.password = None
            mock_redis.db = 0
            mock_redis.max_connections = 20
            mock_redis.connection_timeout = 5
            mock_redis.socket_timeout = 5
            mock_redis.ssl = False
            
            mock_config.return_value.redis = mock_redis
            manager = await create_cache_manager()
            assert isinstance(manager, CacheManager)
            assert manager.redis_config["host"] == "config-redis"


if __name__ == "__main__":
    pytest.main([__file__])