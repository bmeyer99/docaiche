# Coding Standards

## Overview
This document defines coding standards and best practices for the DocAIche project. These standards ensure code consistency, maintainability, and quality across all development work.

## General Principles

### 1. Code Quality
- **MUST** write clean, readable, and maintainable code
- **MUST** follow language-specific best practices
- **MUST** include comprehensive tests for all new code
- **SHOULD** refactor code to improve quality when making changes

### 2. Documentation
- **MUST** document all public APIs and interfaces
- **MUST** include docstrings for all functions and classes
- **SHOULD** include inline comments for complex logic
- **SHOULD** update documentation when changing functionality

### 3. Security
- **MUST** validate all inputs
- **MUST** sanitize outputs
- **MUST NOT** commit secrets or sensitive data
- **MUST** follow secure coding practices

## Python Standards

### Code Style (PEP 8)
- **MUST** follow PEP 8 style guidelines
- **MUST** use 4 spaces for indentation (no tabs)
- **MUST** limit lines to 88 characters (Black formatter standard)
- **MUST** use descriptive variable and function names

### Formatting
```python
# Use Black formatter
pip install black
black src/

# Configuration in pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
```

### Import Organization
```python
# Standard library imports
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
import aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# Local imports
from src.core.config import get_configuration
from src.database.manager import DatabaseManager
from src.services.auth import AuthService
```

### Function and Class Naming
```python
# Functions: snake_case
def get_user_by_id(user_id: str) -> Optional[User]:
    """Retrieve user by ID."""
    pass

def validate_api_key(api_key: str) -> bool:
    """Validate API key format and existence."""
    pass

# Classes: PascalCase
class UserService:
    """Service for user management operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_user(self, user_data: CreateUserRequest) -> User:
        """Create a new user."""
        pass

# Constants: UPPER_SNAKE_CASE
DEFAULT_PAGE_SIZE = 20
MAX_SEARCH_RESULTS = 100
API_VERSION = "1.0.0"
```

### Type Hints
```python
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel

# Always use type hints
def process_search_query(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20
) -> List[SearchResult]:
    """Process search query and return results."""
    pass

# Use Pydantic models for data validation
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    technology_hint: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
```

### Error Handling
```python
# Use specific exception types
class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

# Proper exception handling
async def authenticate_user(token: str) -> User:
    """Authenticate user by JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        user = await get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError("Authentication failed")
```

### Async/Await Best Practices
```python
# Prefer async/await over callbacks
async def fetch_user_data(user_id: str) -> Dict[str, Any]:
    """Fetch user data from multiple sources."""
    # Run concurrent operations
    user, preferences, activity = await asyncio.gather(
        get_user_by_id(user_id),
        get_user_preferences(user_id),
        get_user_activity(user_id),
        return_exceptions=True
    )
    
    return {
        "user": user if not isinstance(user, Exception) else None,
        "preferences": preferences if not isinstance(preferences, Exception) else {},
        "activity": activity if not isinstance(activity, Exception) else []
    }

# Use async context managers
async def process_with_connection():
    """Process data with database connection."""
    async with database_pool.acquire() as conn:
        async with conn.transaction():
            # Database operations
            await conn.execute("INSERT ...")
            await conn.execute("UPDATE ...")
```

### Logging
```python
import logging
import structlog

# Use structured logging
logger = structlog.get_logger(__name__)

async def search_documents(query: str) -> SearchResponse:
    """Search documents with structured logging."""
    request_id = generate_request_id()
    
    logger.info(
        "Search request started",
        request_id=request_id,
        query=query,
        user_id=get_current_user_id()
    )
    
    try:
        results = await search_service.search(query)
        
        logger.info(
            "Search completed successfully",
            request_id=request_id,
            result_count=len(results),
            execution_time_ms=results.execution_time_ms
        )
        
        return results
    except Exception as e:
        logger.error(
            "Search failed",
            request_id=request_id,
            error=str(e),
            exc_info=True
        )
        raise
```

### Database Operations
```python
# Use parameterized queries
async def get_users_by_role(role: str) -> List[User]:
    """Get users by role using parameterized query."""
    query = """
        SELECT id, username, email, role, created_at
        FROM users
        WHERE role = $1 AND is_active = true
        ORDER BY created_at DESC
    """
    rows = await database.fetch_all(query, (role,))
    return [User(**row) for row in rows]

# Use transactions for multiple operations
async def create_user_with_profile(user_data: CreateUserRequest) -> User:
    """Create user and profile in transaction."""
    async with database.transaction():
        # Create user
        user_id = await database.execute(
            "INSERT INTO users (username, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
            user_data.username,
            user_data.email,
            hash_password(user_data.password)
        )
        
        # Create profile
        await database.execute(
            "INSERT INTO user_profiles (user_id, first_name, last_name) VALUES ($1, $2, $3)",
            user_id,
            user_data.first_name,
            user_data.last_name
        )
        
        return await get_user_by_id(user_id)
```

## TypeScript/JavaScript Standards

### Code Style
```typescript
// Use Prettier for formatting
// Configuration in .prettierrc
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2
}

// Use ESLint for code quality
// Configuration in .eslintrc.js
module.exports = {
  extends: [
    '@typescript-eslint/recommended',
    'prettier'
  ],
  rules: {
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/explicit-function-return-type': 'warn'
  }
};
```

### Type Definitions
```typescript
// Define interfaces for all data structures
interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  createdAt: Date;
}

interface SearchRequest {
  query: string;
  technologyHint?: string;
  limit?: number;
}

interface ApiResponse<T> {
  data: T;
  meta: {
    timestamp: string;
    requestId: string;
  };
}

// Use enums for constants
enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  SERVICE = 'service',
  READONLY = 'readonly'
}

// Use generics for reusable types
interface Repository<T, ID = string> {
  findById(id: ID): Promise<T | null>;
  create(data: Omit<T, 'id'>): Promise<T>;
  update(id: ID, data: Partial<T>): Promise<T>;
  delete(id: ID): Promise<void>;
}
```

### Function Definitions
```typescript
// Use explicit return types
async function searchDocuments(
  request: SearchRequest
): Promise<ApiResponse<SearchResult[]>> {
  const results = await searchService.search(request);
  
  return {
    data: results.items,
    meta: {
      timestamp: new Date().toISOString(),
      requestId: generateRequestId()
    }
  };
}

// Use arrow functions for simple operations
const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

// Use proper error handling
async function fetchUserData(userId: string): Promise<User> {
  try {
    const response = await apiClient.get(`/users/${userId}`);
    return response.data;
  } catch (error) {
    if (error.status === 404) {
      throw new UserNotFoundError(`User ${userId} not found`);
    }
    throw new ApiError('Failed to fetch user data', error);
  }
}
```

## Testing Standards

### Test Structure
```python
# Test file naming: test_*.py
# Test class naming: Test*
# Test method naming: test_*

import pytest
from unittest.mock import AsyncMock, Mock

class TestUserService:
    """Test user service functionality."""
    
    @pytest.fixture
    async def user_service(self, mock_db):
        """Create user service with mocked dependencies."""
        return UserService(db_manager=mock_db)
    
    async def test_create_user_success(self, user_service):
        """Test successful user creation."""
        # Arrange
        user_data = CreateUserRequest(
            username="testuser",
            email="test@example.com",
            password="securepassword123"
        )
        
        # Act
        user = await user_service.create_user(user_data)
        
        # Assert
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.id is not None
    
    async def test_create_user_duplicate_email(self, user_service):
        """Test user creation with duplicate email."""
        # Arrange
        user_data = CreateUserRequest(
            username="testuser",
            email="existing@example.com",
            password="securepassword123"
        )
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Email already exists"):
            await user_service.create_user(user_data)
```

### Test Coverage Requirements
```python
# Minimum test coverage: 80%
# Critical path coverage: 100%

# Use pytest-cov for coverage reporting
pytest --cov=src --cov-report=html --cov-report=term-missing

# Coverage configuration in .coveragerc
[run]
source = src
omit = 
    */tests/*
    */migrations/*
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

## Security Standards

### Input Validation
```python
from pydantic import BaseModel, Field, validator
import re

class SearchRequest(BaseModel):
    """Search request with validation."""
    
    query: str = Field(..., min_length=1, max_length=500)
    technology_hint: Optional[str] = Field(None, max_length=50)
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query format."""
        # Prevent XSS and injection attacks
        if re.search(r'[<>"\';]', v):
            raise ValueError('Query contains invalid characters')
        return v.strip()
    
    @validator('technology_hint')
    def validate_technology(cls, v):
        """Validate technology hint."""
        if v:
            allowed_technologies = ['python', 'javascript', 'react', 'typescript']
            if v.lower() not in allowed_technologies:
                raise ValueError(f'Invalid technology: {v}')
        return v.lower() if v else None
```

### Password Security
```python
import bcrypt
import secrets

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_api_key() -> str:
    """Generate secure API key."""
    return f"ak_{'live' if ENVIRONMENT == 'production' else 'test'}_{secrets.token_urlsafe(32)}"
```

### SQL Injection Prevention
```python
# Always use parameterized queries
async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email using parameterized query."""
    query = "SELECT * FROM users WHERE email = $1 AND is_active = true"
    row = await database.fetch_one(query, (email,))
    return User(**row) if row else None

# Never use string formatting for queries
# ❌ BAD
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✅ GOOD
query = "SELECT * FROM users WHERE email = $1"
result = await database.fetch_one(query, (email,))
```

## Performance Standards

### Database Optimization
```python
# Use appropriate indexes
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_search_logs_timestamp ON search_logs(timestamp);
CREATE INDEX CONCURRENTLY idx_documents_technology ON documents(technology) WHERE technology IS NOT NULL;

# Use efficient queries
async def get_recent_searches(user_id: str, limit: int = 10) -> List[SearchLog]:
    """Get recent searches with proper indexing."""
    query = """
        SELECT id, query, timestamp, result_count
        FROM search_logs
        WHERE user_id = $1
        ORDER BY timestamp DESC
        LIMIT $2
    """
    rows = await database.fetch_all(query, (user_id, limit))
    return [SearchLog(**row) for row in rows]
```

### Caching
```python
import aioredis
from functools import wraps

async def cached_search(cache_key: str, search_func, ttl: int = 300):
    """Cache search results."""
    # Check cache first
    cached_result = await redis.get(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    # Execute search
    result = await search_func()
    
    # Cache result
    await redis.setex(cache_key, ttl, json.dumps(result, default=str))
    
    return result
```

## Code Review Standards

### Review Checklist
- [ ] Code follows established style guidelines
- [ ] All functions have type hints and docstrings
- [ ] Tests are comprehensive and passing
- [ ] Security considerations are addressed
- [ ] Performance implications are considered
- [ ] Error handling is robust
- [ ] Documentation is updated
- [ ] No secrets or sensitive data in code

### Review Process
1. **Self-review**: Author reviews own code before submitting
2. **Automated checks**: Linting, formatting, and tests must pass
3. **Peer review**: At least one team member reviews
4. **Security review**: Security-sensitive changes require security team review
5. **Approval**: Code must be approved before merging

## Commit Standards

### Commit Message Format
```
<type>(<scope>): <description>

<body>

<footer>
```

### Commit Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Build tasks, dependency updates

### Examples
```
feat(auth): implement JWT authentication

- Add JWT token generation and validation
- Implement refresh token mechanism
- Add user role-based permissions
- Update API documentation

Closes #123

fix(search): handle empty query gracefully

The search endpoint now returns a proper error message
when query parameter is empty or whitespace only.

Fixes #456

docs(api): update OpenAPI specification

Add new authentication endpoints and security schemes
to the API documentation.
```

## Configuration Management

### Environment Variables
```python
# Use Pydantic for configuration
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str
    database_pool_size: int = 20
    
    # Security
    jwt_secret_key: str
    api_key_prefix: str = "ak_"
    
    # Cache
    redis_url: str
    cache_ttl: int = 300
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### Secrets Management
```python
# Never commit secrets
# Use environment variables or external secret management

# ❌ BAD
API_KEY = "hardcoded-api-key-123"

# ✅ GOOD
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable required")

# ✅ BETTER (with Vault)
API_KEY = await vault_client.get_secret("api/keys/external_service")
```

This coding standards document ensures consistent, secure, and maintainable code across the DocAIche project.