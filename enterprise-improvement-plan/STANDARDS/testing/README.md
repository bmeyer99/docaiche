# Testing Standards

## Overview
This document defines comprehensive testing standards for the DocAIche enterprise platform. These standards ensure high-quality, reliable, and maintainable code through systematic testing practices.

## Testing Philosophy

### 1. Test-Driven Development (TDD)
- **SHOULD** write tests before implementing functionality
- **MUST** write tests for all new features
- **MUST** maintain test coverage above 80%
- **SHOULD** aim for 100% coverage on critical paths

### 2. Test Pyramid
- **70% Unit Tests**: Fast, isolated, comprehensive
- **20% Integration Tests**: Component interactions
- **10% End-to-End Tests**: Full user workflows

### 3. Testing Types
- **Unit Tests**: Individual functions and classes
- **Integration Tests**: Service and API interactions
- **Security Tests**: Vulnerability and penetration testing
- **Performance Tests**: Load and stress testing
- **Contract Tests**: API contract validation

## Unit Testing Standards

### Test Structure (AAA Pattern)
```python
import pytest
from unittest.mock import AsyncMock, Mock, patch

class TestUserService:
    """Test user service functionality."""
    
    @pytest.fixture
    async def user_service(self, mock_db_manager):
        """Create user service with mocked dependencies."""
        return UserService(db_manager=mock_db_manager)
    
    @pytest.fixture
    def valid_user_data(self):
        """Provide valid user data for testing."""
        return CreateUserRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!"
        )
    
    async def test_create_user_success(self, user_service, valid_user_data):
        """Test successful user creation."""
        # Arrange
        expected_user = User(
            id="user_123",
            username=valid_user_data.username,
            email=valid_user_data.email,
            role=UserRole.USER,
            created_at=datetime.utcnow()
        )
        
        user_service.db_manager.execute.return_value = "user_123"
        user_service.db_manager.fetch_one.return_value = expected_user.dict()
        
        # Act
        result = await user_service.create_user(valid_user_data)
        
        # Assert
        assert result.username == valid_user_data.username
        assert result.email == valid_user_data.email
        assert result.role == UserRole.USER
        assert result.id == "user_123"
        
        # Verify database interactions
        user_service.db_manager.execute.assert_called_once()
        user_service.db_manager.fetch_one.assert_called_once()
    
    async def test_create_user_duplicate_email(self, user_service, valid_user_data):
        """Test user creation with duplicate email."""
        # Arrange
        user_service.db_manager.execute.side_effect = UniqueViolationError("Duplicate email")
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Email already exists"):
            await user_service.create_user(valid_user_data)
    
    async def test_create_user_invalid_data(self, user_service):
        """Test user creation with invalid data."""
        # Arrange
        invalid_data = CreateUserRequest(
            username="",  # Invalid: empty username
            email="invalid-email",  # Invalid: bad format
            password="weak"  # Invalid: too short
        )
        
        # Act & Assert
        with pytest.raises(ValidationError):
            await user_service.create_user(invalid_data)
    
    @pytest.mark.parametrize("username,expected_valid", [
        ("validuser", True),
        ("user_123", True),
        ("user-name", True),
        ("", False),  # Empty
        ("a" * 51, False),  # Too long
        ("user@name", False),  # Invalid characters
        ("admin", False),  # Reserved word
    ])
    async def test_validate_username(self, user_service, username, expected_valid):
        """Test username validation with various inputs."""
        if expected_valid:
            # Should not raise exception
            validated = user_service._validate_username(username)
            assert validated == username.lower()
        else:
            with pytest.raises(ValidationError):
                user_service._validate_username(username)
```

### Test Fixtures and Factories
```python
import pytest
from unittest.mock import AsyncMock
from factory import Factory, Faker, SubFactory
from datetime import datetime

# Test Factories
class UserFactory(Factory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
    
    id = Faker('uuid4')
    username = Faker('user_name')
    email = Faker('email')
    role = UserRole.USER
    created_at = Faker('date_time', tzinfo=timezone.utc)
    is_active = True

class SearchRequestFactory(Factory):
    """Factory for creating test search requests."""
    
    class Meta:
        model = SearchRequest
    
    query = Faker('sentence', nb_words=3)
    technology_hint = Faker('random_element', elements=['python', 'javascript', 'react'])
    limit = 20

# Test Fixtures
@pytest.fixture
async def mock_db_manager():
    """Mock database manager for testing."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.execute = AsyncMock()
    mock.fetch_one = AsyncMock()
    mock.fetch_all = AsyncMock()
    mock.transaction = AsyncMock()
    return mock

@pytest.fixture
async def mock_redis_manager():
    """Mock Redis manager for testing."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.exists = AsyncMock()
    return mock

@pytest.fixture
async def mock_search_service():
    """Mock search service for testing."""
    mock = AsyncMock()
    mock.search = AsyncMock()
    mock.index_document = AsyncMock()
    mock.delete_document = AsyncMock()
    return mock

@pytest.fixture
def sample_users():
    """Provide sample users for testing."""
    return [
        UserFactory(),
        UserFactory(role=UserRole.ADMIN),
        UserFactory(role=UserRole.SERVICE),
    ]

@pytest.fixture
async def authenticated_client(test_client, sample_users):
    """Provide authenticated test client."""
    user = sample_users[0]
    token = jwt_manager.create_access_token(user.id, user.role.value, [])
    test_client.headers = {"Authorization": f"Bearer {token}"}
    return test_client
```

### Mock and Patch Best Practices
```python
import pytest
from unittest.mock import AsyncMock, Mock, patch, call

class TestAuthenticationService:
    """Test authentication service with proper mocking."""
    
    @patch('src.services.auth.jwt_manager')
    @patch('src.services.auth.password_manager')
    async def test_authenticate_user_success(self, mock_password_manager, mock_jwt_manager):
        """Test successful user authentication with patches."""
        # Arrange
        auth_service = AuthenticationService()
        mock_password_manager.verify_password.return_value = True
        mock_jwt_manager.create_access_token.return_value = "mock_token"
        
        user = UserFactory()
        credentials = LoginRequest(username=user.username, password="correct_password")
        
        with patch.object(auth_service, 'get_user_by_username', return_value=user):
            # Act
            result = await auth_service.authenticate_user(credentials)
            
            # Assert
            assert result.access_token == "mock_token"
            assert result.user.id == user.id
            mock_password_manager.verify_password.assert_called_once_with(
                "correct_password", user.password_hash
            )
    
    async def test_database_transaction_rollback(self, mock_db_manager):
        """Test database transaction rollback on error."""
        # Arrange
        auth_service = AuthenticationService(db_manager=mock_db_manager)
        mock_db_manager.transaction.side_effect = DatabaseError("Connection failed")
        
        # Act & Assert
        with pytest.raises(ServiceError):
            async with auth_service.create_user_transaction():
                await auth_service.create_user(UserFactory())
        
        # Verify transaction was attempted
        mock_db_manager.transaction.assert_called_once()
```

## Integration Testing

### API Integration Tests
```python
import pytest
import httpx
from fastapi.testclient import TestClient
from src.main import app

class TestSearchAPI:
    """Integration tests for search API."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        return TestClient(app)
    
    @pytest.fixture
    async def setup_test_data(self, test_db):
        """Set up test data in database."""
        # Insert test documents
        documents = [
            {
                "id": "doc_1",
                "title": "React Hooks Guide",
                "content": "Learn about React hooks...",
                "technology": "react"
            },
            {
                "id": "doc_2", 
                "title": "Python FastAPI Tutorial",
                "content": "Build APIs with FastAPI...",
                "technology": "python"
            }
        ]
        
        for doc in documents:
            await test_db.execute(
                "INSERT INTO documents (id, title, content, technology) VALUES ($1, $2, $3, $4)",
                doc["id"], doc["title"], doc["content"], doc["technology"]
            )
        
        yield documents
        
        # Cleanup
        await test_db.execute("DELETE FROM documents WHERE id IN ('doc_1', 'doc_2')")
    
    async def test_search_endpoint_success(self, authenticated_client, setup_test_data):
        """Test successful search request."""
        # Act
        response = authenticated_client.get("/api/v1/search?q=react&limit=10")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "total_count" in data
        assert "query" in data
        assert data["query"] == "react"
        assert len(data["results"]) > 0
        
        # Verify result structure
        result = data["results"][0]
        assert "content_id" in result
        assert "title" in result
        assert "snippet" in result
        assert "relevance_score" in result
    
    async def test_search_endpoint_authentication_required(self, test_client):
        """Test search endpoint requires authentication."""
        # Act
        response = test_client.get("/api/v1/search?q=test")
        
        # Assert
        assert response.status_code == 401
        error = response.json()
        assert error["error"]["code"] == "AUTH_REQUIRED"
    
    async def test_search_endpoint_validation(self, authenticated_client):
        """Test search endpoint input validation."""
        # Test empty query
        response = authenticated_client.get("/api/v1/search?q=")
        assert response.status_code == 422
        
        # Test query too long
        long_query = "x" * 501
        response = authenticated_client.get(f"/api/v1/search?q={long_query}")
        assert response.status_code == 422
        
        # Test invalid limit
        response = authenticated_client.get("/api/v1/search?q=test&limit=101")
        assert response.status_code == 422
    
    async def test_search_endpoint_rate_limiting(self, authenticated_client):
        """Test search endpoint rate limiting."""
        # Make requests up to limit
        for i in range(30):
            response = authenticated_client.get(f"/api/v1/search?q=test{i}")
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = authenticated_client.get("/api/v1/search?q=rate_limited")
        assert response.status_code == 429
        
        error = response.json()
        assert error["error"]["code"] == "RATE_LIMIT_EXCEEDED"
```

### Database Integration Tests
```python
import pytest
import asyncpg
from src.database.manager import DatabaseManager
from src.database.models import User, Document

class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture
    async def test_db_manager(self):
        """Create test database manager."""
        db_manager = DatabaseManager(test_database_url)
        await db_manager.connect()
        yield db_manager
        await db_manager.disconnect()
    
    @pytest.fixture
    async def clean_database(self, test_db_manager):
        """Ensure clean database state."""
        # Setup: Clean tables
        await test_db_manager.execute("TRUNCATE TABLE users CASCADE")
        await test_db_manager.execute("TRUNCATE TABLE documents CASCADE")
        
        yield
        
        # Teardown: Clean tables
        await test_db_manager.execute("TRUNCATE TABLE users CASCADE")
        await test_db_manager.execute("TRUNCATE TABLE documents CASCADE")
    
    async def test_user_crud_operations(self, test_db_manager, clean_database):
        """Test complete user CRUD operations."""
        # Create user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "role": "user"
        }
        
        user_id = await test_db_manager.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, user_data["username"], user_data["email"], 
             user_data["password_hash"], user_data["role"])
        
        assert user_id is not None
        
        # Read user
        user = await test_db_manager.fetch_one(
            "SELECT * FROM users WHERE id = $1", user_id
        )
        
        assert user["username"] == user_data["username"]
        assert user["email"] == user_data["email"]
        assert user["role"] == user_data["role"]
        
        # Update user
        await test_db_manager.execute(
            "UPDATE users SET email = $1 WHERE id = $2",
            "updated@example.com", user_id
        )
        
        updated_user = await test_db_manager.fetch_one(
            "SELECT email FROM users WHERE id = $1", user_id
        )
        assert updated_user["email"] == "updated@example.com"
        
        # Delete user
        await test_db_manager.execute("DELETE FROM users WHERE id = $1", user_id)
        
        deleted_user = await test_db_manager.fetch_one(
            "SELECT * FROM users WHERE id = $1", user_id
        )
        assert deleted_user is None
    
    async def test_transaction_rollback(self, test_db_manager, clean_database):
        """Test database transaction rollback."""
        try:
            async with test_db_manager.transaction():
                # Insert user
                await test_db_manager.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES ($1, $2, $3, $4)
                """, "testuser", "test@example.com", "hashed", "user")
                
                # Force error to trigger rollback
                await test_db_manager.execute("INVALID SQL STATEMENT")
        except Exception:
            pass  # Expected to fail
        
        # Verify rollback - user should not exist
        users = await test_db_manager.fetch_all("SELECT * FROM users")
        assert len(users) == 0
```

## Security Testing

### Authentication and Authorization Tests
```python
import pytest
from src.core.auth import JWTManager, RBACManager
from src.core.security import SecurityViolationError

class TestSecurityFeatures:
    """Security-focused testing."""
    
    async def test_jwt_token_validation(self):
        """Test JWT token security."""
        jwt_manager = JWTManager("test_secret")
        
        # Test valid token
        token = jwt_manager.create_access_token("user123", "user", ["read"])
        payload = jwt_manager.verify_token(token)
        assert payload["sub"] == "user123"
        
        # Test tampered token
        tampered_token = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.verify_token(tampered_token)
        assert exc_info.value.status_code == 401
        
        # Test expired token
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(hours=1)
            with pytest.raises(HTTPException):
                jwt_manager.verify_token(token)
    
    async def test_rbac_permissions(self):
        """Test role-based access control."""
        # Test admin permissions
        assert RBACManager.check_permission(Role.ADMIN, Permission.ADMIN_ACCESS)
        assert RBACManager.check_permission(Role.ADMIN, Permission.USERS_DELETE)
        
        # Test user permissions
        assert RBACManager.check_permission(Role.USER, Permission.SEARCH_QUERY)
        assert not RBACManager.check_permission(Role.USER, Permission.ADMIN_ACCESS)
        
        # Test readonly permissions
        assert RBACManager.check_permission(Role.READONLY, Permission.SEARCH_QUERY)
        assert not RBACManager.check_permission(Role.READONLY, Permission.USERS_WRITE)
    
    @pytest.mark.parametrize("malicious_input,expected_error", [
        ("<script>alert('xss')</script>", "Invalid characters"),
        ("'; DROP TABLE users; --", "Invalid characters"),
        ("javascript:alert(1)", "Invalid characters"),
        ("onload=alert(1)", "Invalid characters"),
    ])
    async def test_input_validation_security(self, malicious_input, expected_error):
        """Test input validation against attacks."""
        with pytest.raises(ValueError, match=expected_error):
            SecureSearchRequest(query=malicious_input)
    
    async def test_password_security(self):
        """Test password hashing and validation."""
        password_manager = PasswordManager()
        
        password = "SecurePassword123!"
        hashed = password_manager.hash_password(password)
        
        # Test password verification
        assert password_manager.verify_password(password, hashed)
        assert not password_manager.verify_password("WrongPassword", hashed)
        
        # Test hash uniqueness (same password should produce different hashes)
        hash1 = password_manager.hash_password(password)
        hash2 = password_manager.hash_password(password)
        assert hash1 != hash2
        
        # Both hashes should verify the same password
        assert password_manager.verify_password(password, hash1)
        assert password_manager.verify_password(password, hash2)
```

### Penetration Testing
```python
class TestPenetrationTesting:
    """Automated penetration testing."""
    
    async def test_sql_injection_attempts(self, authenticated_client):
        """Test SQL injection vulnerability."""
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1 #",
        ]
        
        for payload in sql_payloads:
            response = authenticated_client.get(f"/api/v1/search?q={payload}")
            
            # Should not return 500 error (indicating SQL injection)
            assert response.status_code in [200, 400, 422]
            
            if response.status_code == 200:
                data = response.json()
                # Should not return unexpected data
                assert "results" in data
                assert isinstance(data["results"], list)
    
    async def test_xss_attempts(self, authenticated_client):
        """Test XSS vulnerability."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "'><script>alert('xss')</script>",
        ]
        
        for payload in xss_payloads:
            response = authenticated_client.post("/api/v1/search", json={
                "query": payload,
                "limit": 10
            })
            
            # Should be validated and rejected
            assert response.status_code in [400, 422]
    
    async def test_authentication_bypass_attempts(self, test_client):
        """Test authentication bypass attempts."""
        bypass_headers = [
            {"X-Forwarded-User": "admin"},
            {"X-Remote-User": "admin"},
            {"Authorization": "Bearer invalid"},
            {"Authorization": "Basic YWRtaW46YWRtaW4="},  # admin:admin
        ]
        
        for headers in bypass_headers:
            response = test_client.get("/api/v1/admin/users", headers=headers)
            
            # Should require proper authentication
            assert response.status_code == 401
    
    async def test_rate_limiting_bypass(self, authenticated_client):
        """Test rate limiting bypass attempts."""
        # Test with different headers that might bypass rate limiting
        bypass_headers = [
            {"X-Forwarded-For": "127.0.0.1"},
            {"X-Real-IP": "127.0.0.1"},
            {"X-Originating-IP": "127.0.0.1"},
        ]
        
        # Exhaust rate limit first
        for i in range(35):  # Exceed search limit of 30
            response = authenticated_client.get(f"/api/v1/search?q=test{i}")
        
        # Should be rate limited
        response = authenticated_client.get("/api/v1/search?q=rate_test")
        assert response.status_code == 429
        
        # Try bypassing with different headers
        for headers in bypass_headers:
            authenticated_client.headers.update(headers)
            response = authenticated_client.get("/api/v1/search?q=bypass_test")
            
            # Should still be rate limited
            assert response.status_code == 429
```

## Performance Testing

### Load Testing
```python
import asyncio
import aiohttp
import time
from statistics import mean, median

class TestPerformanceLoad:
    """Performance and load testing."""
    
    async def test_search_endpoint_performance(self, test_server):
        """Test search endpoint performance under load."""
        url = f"{test_server}/api/v1/search"
        headers = {"Authorization": "Bearer test_token"}
        
        async def make_request(session, query_id):
            """Make single search request."""
            start_time = time.time()
            async with session.get(
                url, 
                params={"q": f"test query {query_id}", "limit": 20},
                headers=headers
            ) as response:
                await response.text()
                return time.time() - start_time, response.status
        
        async def load_test(concurrent_users, requests_per_user):
            """Run load test with specified parameters."""
            async with aiohttp.ClientSession() as session:
                tasks = []
                
                for user_id in range(concurrent_users):
                    for req_id in range(requests_per_user):
                        query_id = user_id * requests_per_user + req_id
                        tasks.append(make_request(session, query_id))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                response_times = []
                status_codes = []
                
                for result in results:
                    if isinstance(result, tuple):
                        response_time, status = result
                        response_times.append(response_time)
                        status_codes.append(status)
                
                return response_times, status_codes
        
        # Test with different load levels
        test_scenarios = [
            (10, 5),   # 10 users, 5 requests each
            (25, 4),   # 25 users, 4 requests each
            (50, 2),   # 50 users, 2 requests each
        ]
        
        for concurrent_users, requests_per_user in test_scenarios:
            response_times, status_codes = await load_test(
                concurrent_users, requests_per_user
            )
            
            # Performance assertions
            avg_response_time = mean(response_times)
            median_response_time = median(response_times)
            success_rate = status_codes.count(200) / len(status_codes)
            
            # Performance thresholds
            assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time}s"
            assert median_response_time < 0.5, f"Median response time too high: {median_response_time}s"
            assert success_rate > 0.95, f"Success rate too low: {success_rate}"
            
            print(f"Load test ({concurrent_users} users, {requests_per_user} req/user):")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Median response time: {median_response_time:.3f}s")
            print(f"  Success rate: {success_rate:.2%}")
    
    async def test_database_performance(self, test_db_manager):
        """Test database performance under load."""
        # Insert test data
        await self._insert_test_documents(test_db_manager, 1000)
        
        async def search_query(query_text):
            """Execute search query and measure time."""
            start_time = time.time()
            results = await test_db_manager.fetch_all("""
                SELECT id, title, content, technology
                FROM documents
                WHERE to_tsvector('english', content) @@ plainto_tsquery($1)
                ORDER BY ts_rank(to_tsvector('english', content), plainto_tsquery($1)) DESC
                LIMIT 20
            """, query_text)
            return time.time() - start_time, len(results)
        
        # Test concurrent database queries
        tasks = [search_query(f"test query {i}") for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        query_times = [r[0] for r in results]
        avg_query_time = mean(query_times)
        
        # Database performance assertion
        assert avg_query_time < 0.1, f"Database query too slow: {avg_query_time}s"
```

### Memory and Resource Testing
```python
import psutil
import tracemalloc

class TestResourceUsage:
    """Test memory and resource usage."""
    
    async def test_memory_usage(self, test_server):
        """Test memory usage under load."""
        # Start memory tracing
        tracemalloc.start()
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(100):
                tasks.append(self._make_search_request(session, f"query {i}"))
            
            await asyncio.gather(*tasks)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Get memory trace
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage assertions
        assert memory_growth < 50, f"Memory growth too high: {memory_growth}MB"
        assert peak / 1024 / 1024 < 100, f"Peak memory too high: {peak / 1024 / 1024}MB"
    
    async def test_connection_pooling(self, test_db_manager):
        """Test database connection pooling efficiency."""
        # Monitor connection pool
        initial_pool_size = test_db_manager.pool.get_size()
        
        # Create many concurrent database operations
        async def db_operation(op_id):
            async with test_db_manager.acquire() as conn:
                await conn.execute("SELECT pg_sleep(0.1)")
                return op_id
        
        tasks = [db_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        final_pool_size = test_db_manager.pool.get_size()
        
        # Pool should not grow excessively
        assert final_pool_size <= initial_pool_size + 10
        assert len(results) == 50  # All operations completed
```

## Test Configuration

### pytest Configuration
```ini
# pytest.ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    security: Security tests
    performance: Performance tests
    slow: Slow running tests
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
```

### Coverage Configuration
```ini
# .coveragerc
[run]
source = src
omit = 
    */tests/*
    */migrations/*
    */venv/*
    */node_modules/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod

[html]
directory = htmlcov
```

### Test Environment Setup
```python
# conftest.py
import pytest
import asyncio
import asyncpg
from fastapi.testclient import TestClient
from src.main import app
from src.database.manager import DatabaseManager

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_database():
    """Create test database."""
    # Create test database
    conn = await asyncpg.connect("postgresql://user:pass@localhost/postgres")
    await conn.execute("DROP DATABASE IF EXISTS test_docaiche")
    await conn.execute("CREATE DATABASE test_docaiche")
    await conn.close()
    
    # Run migrations
    test_db_manager = DatabaseManager("postgresql://user:pass@localhost/test_docaiche")
    await test_db_manager.connect()
    await test_db_manager.run_migrations()
    
    yield test_db_manager
    
    # Cleanup
    await test_db_manager.disconnect()
    conn = await asyncpg.connect("postgresql://user:pass@localhost/postgres")
    await conn.execute("DROP DATABASE test_docaiche")
    await conn.close()

@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
async def clean_tables(test_database):
    """Clean database tables between tests."""
    # Truncate all tables
    await test_database.execute("TRUNCATE TABLE users CASCADE")
    await test_database.execute("TRUNCATE TABLE documents CASCADE")
    await test_database.execute("TRUNCATE TABLE search_logs CASCADE")
    yield
    # Cleanup after test
    await test_database.execute("TRUNCATE TABLE users CASCADE")
    await test_database.execute("TRUNCATE TABLE documents CASCADE")
    await test_database.execute("TRUNCATE TABLE search_logs CASCADE")
```

## Continuous Integration Testing

### GitHub Actions Configuration
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_docaiche
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=src --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration -v
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost/test_docaiche
        REDIS_URL: redis://localhost:6379
    
    - name: Run security tests
      run: |
        pytest tests/security -v -m security
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        
  performance:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run performance tests
      run: |
        pytest tests/performance -v -m performance --timeout=300
```

This comprehensive testing standards document ensures high-quality, reliable code through systematic testing practices, covering unit tests, integration tests, security tests, and performance tests with proper CI/CD integration.