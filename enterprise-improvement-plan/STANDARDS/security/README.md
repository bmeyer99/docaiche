# Security Standards

## Overview
This document defines comprehensive security standards for the DocAIche enterprise platform. These standards ensure that all code, infrastructure, and processes meet enterprise-grade security requirements.

## Security Principles

### 1. Defense in Depth
- **MUST** implement multiple layers of security controls
- **MUST** assume each layer may be compromised
- **MUST** design for graceful degradation under attack
- **SHOULD** implement security monitoring at each layer

### 2. Zero Trust Architecture
- **MUST** verify every request regardless of source
- **MUST** implement least privilege access
- **MUST** assume network breach at all times
- **SHOULD** continuously validate security posture

### 3. Security by Design
- **MUST** consider security from the start of development
- **MUST** perform threat modeling for new features
- **MUST** implement secure defaults
- **SHOULD** prefer secure libraries and frameworks

## Authentication & Authorization

### JWT Authentication
```python
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional

class JWTManager:
    """Enterprise-grade JWT manager with security best practices."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 15
        self.refresh_token_expire_days = 7
        self.issuer = "docaiche-api"
        self.audience = "docaiche-users"
    
    def create_access_token(self, user_id: str, role: str, permissions: List[str]) -> str:
        """Create secure JWT access token."""
        now = datetime.utcnow()
        claims = {
            "sub": user_id,
            "role": role,
            "permissions": permissions,
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes),
            "iss": self.issuer,
            "aud": self.audience,
            "jti": secrets.token_hex(16)  # Unique token ID for revocation
        }
        return jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with comprehensive validation."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require_exp": True,
                    "require_iat": True,
                    "require_sub": True,
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True
                }
            )
            
            # Check if token is blacklisted
            if await self.is_token_blacklisted(payload.get("jti")):
                raise jwt.InvalidTokenError("Token is blacklisted")
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

### API Key Management
```python
import secrets
import hashlib
from datetime import datetime, timedelta
from enum import Enum

class APIKeyScope(Enum):
    """API key access scopes."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SERVICE = "service"

class APIKeyManager:
    """Secure API key management system."""
    
    def __init__(self):
        self.key_prefix = "ak_"
        self.key_length = 32
        self.hash_algorithm = "sha256"
    
    def generate_api_key(self, user_id: str, scope: APIKeyScope, name: str) -> Dict[str, Any]:
        """Generate secure API key with metadata."""
        # Generate cryptographically secure key
        raw_key = secrets.token_urlsafe(self.key_length)
        full_key = f"{self.key_prefix}{raw_key}"
        
        # Hash key for storage (never store raw key)
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        # Generate unique key ID
        key_id = f"key_{secrets.token_hex(8)}"
        
        key_data = {
            "key_id": key_id,
            "key_hash": key_hash,
            "user_id": user_id,
            "scope": scope.value,
            "name": name,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=90),
            "is_active": True,
            "last_used": None,
            "usage_count": 0
        }
        
        # Store in database
        await self.store_api_key(key_data)
        
        # Return key only once
        return {
            "api_key": full_key,  # Only returned once
            "key_id": key_id,
            "scope": scope.value,
            "expires_at": key_data["expires_at"]
        }
    
    async def validate_api_key(self, provided_key: str) -> Dict[str, Any]:
        """Validate API key and return metadata."""
        # Hash provided key
        key_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        
        # Query database
        key_data = await self.get_api_key_by_hash(key_hash)
        
        if not key_data:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        if not key_data["is_active"]:
            raise HTTPException(status_code=401, detail="API key deactivated")
        
        if datetime.utcnow() > key_data["expires_at"]:
            raise HTTPException(status_code=401, detail="API key expired")
        
        # Update usage tracking
        await self.update_key_usage(key_data["key_id"])
        
        return key_data
```

### Role-Based Access Control (RBAC)
```python
from enum import Enum
from typing import Set, Dict, List

class Permission(Enum):
    """System permissions."""
    # User permissions
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    
    # Search permissions
    SEARCH_QUERY = "search:query"
    SEARCH_ADMIN = "search:admin"
    
    # Configuration permissions
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    
    # Admin permissions
    ADMIN_ACCESS = "admin:access"
    ADMIN_USERS = "admin:users"
    ADMIN_AUDIT = "admin:audit"

class Role(Enum):
    """User roles with associated permissions."""
    ADMIN = "admin"
    USER = "user"
    SERVICE = "service"
    READONLY = "readonly"

class RBACManager:
    """Role-based access control manager."""
    
    ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
        Role.ADMIN: {
            Permission.USERS_READ,
            Permission.USERS_WRITE,
            Permission.USERS_DELETE,
            Permission.SEARCH_QUERY,
            Permission.SEARCH_ADMIN,
            Permission.CONFIG_READ,
            Permission.CONFIG_WRITE,
            Permission.ADMIN_ACCESS,
            Permission.ADMIN_USERS,
            Permission.ADMIN_AUDIT,
        },
        Role.USER: {
            Permission.USERS_READ,
            Permission.SEARCH_QUERY,
            Permission.CONFIG_READ,
        },
        Role.SERVICE: {
            Permission.SEARCH_QUERY,
            Permission.CONFIG_READ,
        },
        Role.READONLY: {
            Permission.SEARCH_QUERY,
            Permission.CONFIG_READ,
        }
    }
    
    @classmethod
    def check_permission(cls, user_role: Role, required_permission: Permission) -> bool:
        """Check if user role has required permission."""
        return required_permission in cls.ROLE_PERMISSIONS.get(user_role, set())
    
    @classmethod
    def require_permission(cls, permission: Permission):
        """Decorator to require specific permission."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                current_user = get_current_user()
                if not cls.check_permission(current_user.role, permission):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission required: {permission.value}"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
```

## Input Validation & Sanitization

### Comprehensive Input Validation
```python
from pydantic import BaseModel, Field, validator
import re
import html
from typing import Optional, List

class SecureSearchRequest(BaseModel):
    """Secure search request with comprehensive validation."""
    
    query: str = Field(..., min_length=1, max_length=500)
    technology_hint: Optional[str] = Field(None, max_length=50)
    limit: int = Field(20, ge=1, le=100)
    
    @validator('query')
    def validate_query(cls, v):
        """Validate and sanitize search query."""
        # Remove HTML/XML tags
        v = re.sub(r'<[^>]+>', '', v)
        
        # Escape HTML entities
        v = html.escape(v)
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'\bunion\b', r'\bselect\b', r'\binsert\b', r'\bupdate\b',
            r'\bdelete\b', r'\bdrop\b', r'\bcreate\b', r'\balter\b',
            r'--', r'/\*', r'\*/', r';'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Invalid characters in query')
        
        # Check for XSS patterns
        xss_patterns = [
            r'<script', r'javascript:', r'onload=', r'onerror=',
            r'onclick=', r'onmouseover=', r'onfocus=', r'onblur='
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Invalid characters in query')
        
        return v.strip()
    
    @validator('technology_hint')
    def validate_technology(cls, v):
        """Validate technology hint against whitelist."""
        if v:
            allowed_technologies = [
                'python', 'javascript', 'typescript', 'react', 'vue',
                'angular', 'node', 'django', 'flask', 'fastapi'
            ]
            if v.lower() not in allowed_technologies:
                raise ValueError(f'Invalid technology: {v}')
        return v.lower() if v else None

class SecureUserRegistration(BaseModel):
    """Secure user registration with validation."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        # Only allow alphanumeric and specific special characters
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username contains invalid characters')
        
        # Prevent reserved usernames
        reserved = ['admin', 'root', 'api', 'system', 'null', 'undefined']
        if v.lower() in reserved:
            raise ValueError('Username is reserved')
        
        return v.lower()
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format and security."""
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        
        # Check for suspicious patterns
        if '..' in v or v.startswith('.') or v.endswith('.'):
            raise ValueError('Invalid email format')
        
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        # Check length
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Check complexity
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain number')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain special character')
        
        # Check for common patterns
        common_patterns = ['password', '123456', 'qwerty', 'admin']
        if any(pattern in v.lower() for pattern in common_patterns):
            raise ValueError('Password contains common patterns')
        
        return v
```

### SQL Injection Prevention
```python
# Always use parameterized queries
class SecureUserRepository:
    """Repository with SQL injection protection."""
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with parameterized query."""
        query = """
            SELECT id, username, email, role, created_at, is_active
            FROM users 
            WHERE email = $1 AND is_active = true
        """
        row = await self.db.fetch_one(query, (email,))
        return User(**row) if row else None
    
    async def search_users(self, filters: Dict[str, Any]) -> List[User]:
        """Search users with dynamic filters (safe)."""
        # Build query with whitelisted columns
        allowed_columns = {'username', 'email', 'role', 'is_active'}
        conditions = []
        params = []
        param_counter = 1
        
        for column, value in filters.items():
            if column not in allowed_columns:
                raise ValueError(f"Invalid filter column: {column}")
            
            conditions.append(f"{column} = ${param_counter}")
            params.append(value)
            param_counter += 1
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT id, username, email, role, created_at, is_active
            FROM users
            WHERE {where_clause}
            ORDER BY created_at DESC
        """
        
        rows = await self.db.fetch_all(query, tuple(params))
        return [User(**row) for row in rows]
```

## Cryptography & Password Security

### Password Hashing
```python
import bcrypt
import secrets
from typing import Tuple

class PasswordManager:
    """Secure password management."""
    
    def __init__(self):
        # Use high cost factor for production
        self.rounds = 12 if ENVIRONMENT == "production" else 4
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with salt."""
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate secure OTP for 2FA."""
        return ''.join(secrets.choice('0123456789') for _ in range(length))
```

### Data Encryption
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    """Data encryption for sensitive information."""
    
    def __init__(self, master_key: str):
        # Derive key from master key
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def encrypt_pii(self, pii_data: Dict[str, str]) -> Dict[str, str]:
        """Encrypt PII fields."""
        pii_fields = {'email', 'phone', 'address', 'ssn'}
        encrypted = {}
        
        for key, value in pii_data.items():
            if key in pii_fields and value:
                encrypted[key] = self.encrypt_sensitive_data(value)
            else:
                encrypted[key] = value
        
        return encrypted
```

## Security Headers & Middleware

### Security Headers Middleware
```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Comprehensive security headers middleware."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS (only for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        permissions_policy = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        # Remove server information
        response.headers.pop("Server", None)
        
        return response
```

### Rate Limiting
```python
import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional

class RateLimiter:
    """Advanced rate limiting with multiple strategies."""
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.blocked_ips = defaultdict(float)  # IP -> unblock_time
        self.user_limits = defaultdict(deque)
        
        # Rate limits per endpoint type
        self.limits = {
            "search": {"requests": 30, "window": 60},      # 30/minute
            "auth": {"requests": 5, "window": 60},         # 5/minute  
            "admin": {"requests": 10, "window": 60},       # 10/minute
            "upload": {"requests": 5, "window": 60},       # 5/minute
            "default": {"requests": 60, "window": 60}      # 60/minute
        }
    
    async def is_allowed(
        self,
        identifier: str,
        endpoint_type: str = "default",
        user_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed."""
        current_time = time.time()
        
        # Check if IP is blocked
        if identifier in self.blocked_ips:
            if current_time < self.blocked_ips[identifier]:
                return False, {"error": "IP temporarily blocked"}
            else:
                del self.blocked_ips[identifier]
        
        # Get rate limit for endpoint type
        limit_config = self.limits.get(endpoint_type, self.limits["default"])
        window_size = limit_config["window"]
        max_requests = limit_config["requests"]
        
        # Clean old requests
        window_start = current_time - window_size
        request_queue = self.requests[identifier]
        
        while request_queue and request_queue[0] < window_start:
            request_queue.popleft()
        
        # Check limit
        if len(request_queue) >= max_requests:
            # Progressive blocking for abuse
            if len(request_queue) > max_requests * 2:
                self.blocked_ips[identifier] = current_time + 300  # 5 min block
            
            return False, {
                "error": "Rate limit exceeded",
                "limit": max_requests,
                "window": window_size,
                "retry_after": window_size
            }
        
        # Add current request
        request_queue.append(current_time)
        
        # Return success with rate limit info
        return True, {
            "limit": max_requests,
            "remaining": max_requests - len(request_queue),
            "reset": current_time + window_size,
            "window": window_size
        }
```

## Audit Logging & Monitoring

### Comprehensive Audit Logging
```python
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

class AuditEventType(Enum):
    """Types of audit events."""
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_TOKEN_REFRESH = "auth.token_refresh"
    
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_ROLE_CHANGE = "user.role_change"
    
    CONFIG_UPDATE = "config.update"
    CONFIG_VIEW = "config.view"
    
    DATA_ACCESS = "data.access"
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"
    
    ADMIN_ACTION = "admin.action"
    SECURITY_VIOLATION = "security.violation"

class AuditLogger:
    """Comprehensive audit logging system."""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # Configure structured logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        resource: str,
        action: str,
        result: str,
        request: Optional[Request] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log audit event with comprehensive details."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "result": result,  # "success", "failure", "denied"
            "metadata": metadata or {}
        }
        
        if request:
            audit_entry.update({
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("User-Agent"),
                "request_id": request.headers.get("X-Request-ID"),
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params)
            })
        
        # Log to audit trail
        self.logger.info(json.dumps(audit_entry))
        
        # Store in database for querying
        await self._store_audit_log(audit_entry)
        
        # Send to security monitoring if critical
        if event_type in [AuditEventType.SECURITY_VIOLATION, AuditEventType.AUTH_FAILED]:
            await self._send_security_alert(audit_entry)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP with proxy consideration."""
        # Check for forwarded IP headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _store_audit_log(self, audit_entry: Dict[str, Any]):
        """Store audit log in database."""
        query = """
            INSERT INTO audit_logs (
                timestamp, event_type, user_id, resource, action, result,
                ip_address, user_agent, request_id, method, path, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """
        await database.execute(query, (
            audit_entry["timestamp"],
            audit_entry["event_type"],
            audit_entry.get("user_id"),
            audit_entry["resource"],
            audit_entry["action"],
            audit_entry["result"],
            audit_entry.get("ip_address"),
            audit_entry.get("user_agent"),
            audit_entry.get("request_id"),
            audit_entry.get("method"),
            audit_entry.get("path"),
            json.dumps(audit_entry["metadata"])
        ))
```

### Security Monitoring
```python
class SecurityMonitor:
    """Real-time security monitoring and alerting."""
    
    def __init__(self):
        self.alert_thresholds = {
            "failed_logins": {"count": 5, "window": 300},      # 5 in 5 minutes
            "admin_actions": {"count": 10, "window": 3600},    # 10 in 1 hour
            "suspicious_queries": {"count": 20, "window": 600} # 20 in 10 minutes
        }
        
        self.incident_queue = asyncio.Queue()
    
    async def analyze_security_event(self, audit_entry: Dict[str, Any]):
        """Analyze audit event for security threats."""
        event_type = audit_entry["event_type"]
        user_id = audit_entry.get("user_id")
        ip_address = audit_entry.get("ip_address")
        
        # Check for authentication failures
        if event_type == "auth.failed":
            await self._check_brute_force(ip_address, user_id)
        
        # Check for privilege escalation
        elif event_type == "user.role_change":
            await self._check_privilege_escalation(audit_entry)
        
        # Check for data exfiltration
        elif event_type == "data.export":
            await self._check_data_exfiltration(user_id, audit_entry)
        
        # Check for suspicious patterns
        await self._check_anomalous_behavior(audit_entry)
    
    async def _check_brute_force(self, ip_address: str, user_id: str):
        """Detect brute force attacks."""
        # Query recent failed attempts
        recent_failures = await self._get_recent_failures(ip_address, user_id)
        
        threshold = self.alert_thresholds["failed_logins"]
        if len(recent_failures) >= threshold["count"]:
            await self._create_security_incident(
                "brute_force_attempt",
                f"Brute force detected from {ip_address}",
                {"ip_address": ip_address, "user_id": user_id, "attempts": len(recent_failures)}
            )
    
    async def _check_privilege_escalation(self, audit_entry: Dict[str, Any]):
        """Detect potential privilege escalation."""
        metadata = audit_entry.get("metadata", {})
        old_role = metadata.get("old_role")
        new_role = metadata.get("new_role")
        
        # Alert on elevation to admin
        if new_role == "admin" and old_role != "admin":
            await self._create_security_incident(
                "privilege_escalation",
                f"User elevated to admin role",
                audit_entry
            )
    
    async def _create_security_incident(
        self,
        incident_type: str,
        description: str,
        metadata: Dict[str, Any]
    ):
        """Create security incident for investigation."""
        incident = {
            "id": f"inc_{secrets.token_hex(8)}",
            "type": incident_type,
            "description": description,
            "severity": self._calculate_severity(incident_type),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "open",
            "metadata": metadata
        }
        
        # Store incident
        await self._store_incident(incident)
        
        # Send alerts
        await self._send_security_alert(incident)
        
        # Add to processing queue
        await self.incident_queue.put(incident)
```

## Secure Configuration

### Environment-Based Security
```python
from pydantic import BaseSettings
from typing import List, Optional

class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    # JWT Configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # API Key Configuration
    api_key_prefix: str = "ak_"
    api_key_default_expiry_days: int = 90
    
    # Rate Limiting
    rate_limit_search: int = 30  # per minute
    rate_limit_auth: int = 5     # per minute
    rate_limit_admin: int = 10   # per minute
    
    # Security Headers
    enable_hsts: bool = True
    hsts_max_age: int = 31536000
    csp_policy: Optional[str] = None
    
    # Encryption
    encryption_key: str
    
    # CORS
    cors_origins: List[str] = []
    cors_allow_credentials: bool = True
    
    # Security Monitoring
    enable_audit_logging: bool = True
    enable_security_monitoring: bool = True
    security_alert_webhook: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_prefix = "SECURITY_"

# Environment-specific configurations
class DevelopmentSecuritySettings(SecuritySettings):
    """Development security settings."""
    cors_origins = ["http://localhost:3000", "http://localhost:4080"]
    enable_hsts = False

class ProductionSecuritySettings(SecuritySettings):
    """Production security settings."""
    cors_origins = ["https://app.docaiche.com"]
    enable_hsts = True
    jwt_access_token_expire_minutes = 15
    enable_security_monitoring = True
```

## Security Testing

### Security Test Requirements
```python
import pytest
from unittest.mock import Mock, patch

class TestSecurityFeatures:
    """Comprehensive security testing."""
    
    async def test_jwt_authentication(self):
        """Test JWT authentication security."""
        # Test valid token
        token = jwt_manager.create_access_token("user123", "user", [])
        payload = jwt_manager.verify_token(token)
        assert payload["sub"] == "user123"
        
        # Test expired token
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(hours=1)
            with pytest.raises(HTTPException) as exc_info:
                jwt_manager.verify_token(token)
            assert exc_info.value.status_code == 401
    
    async def test_input_validation(self):
        """Test input validation security."""
        # Test XSS prevention
        malicious_input = "<script>alert('xss')</script>"
        with pytest.raises(ValueError):
            SecureSearchRequest(query=malicious_input)
        
        # Test SQL injection prevention
        sql_injection = "'; DROP TABLE users; --"
        with pytest.raises(ValueError):
            SecureSearchRequest(query=sql_injection)
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        rate_limiter = RateLimiter()
        
        # Make requests within limit
        for i in range(30):
            allowed, info = await rate_limiter.is_allowed("test_ip", "search")
            assert allowed
        
        # Exceed limit
        allowed, info = await rate_limiter.is_allowed("test_ip", "search")
        assert not allowed
        assert "Rate limit exceeded" in info["error"]
    
    async def test_password_security(self):
        """Test password hashing and validation."""
        password_manager = PasswordManager()
        
        password = "SecurePassword123!"
        hashed = password_manager.hash_password(password)
        
        # Test correct password
        assert password_manager.verify_password(password, hashed)
        
        # Test incorrect password
        assert not password_manager.verify_password("WrongPassword", hashed)
    
    async def test_audit_logging(self):
        """Test audit logging functionality."""
        audit_logger = AuditLogger()
        
        with patch.object(audit_logger, '_store_audit_log') as mock_store:
            await audit_logger.log_event(
                AuditEventType.USER_CREATE,
                "user123",
                "users",
                "create",
                "success"
            )
            
            mock_store.assert_called_once()
            audit_entry = mock_store.call_args[0][0]
            assert audit_entry["event_type"] == "user.create"
            assert audit_entry["user_id"] == "user123"
```

## Compliance Requirements

### GDPR Compliance
```python
class GDPRCompliance:
    """GDPR compliance implementation."""
    
    async def handle_data_subject_request(
        self,
        request_type: str,
        user_id: str,
        data_categories: List[str]
    ) -> Dict[str, Any]:
        """Handle GDPR data subject requests."""
        
        if request_type == "access":
            return await self._export_user_data(user_id, data_categories)
        elif request_type == "deletion":
            return await self._delete_user_data(user_id, data_categories)
        elif request_type == "portability":
            return await self._export_portable_data(user_id)
        else:
            raise ValueError(f"Unknown request type: {request_type}")
    
    async def _export_user_data(self, user_id: str, categories: List[str]) -> Dict[str, Any]:
        """Export all user data for GDPR access request."""
        user_data = {}
        
        if "profile" in categories:
            user_data["profile"] = await self._get_user_profile(user_id)
        
        if "activity" in categories:
            user_data["activity"] = await self._get_user_activity(user_id)
        
        if "search_history" in categories:
            user_data["search_history"] = await self._get_search_history(user_id)
        
        # Anonymize sensitive fields
        return self._anonymize_export_data(user_data)
    
    async def _delete_user_data(self, user_id: str, categories: List[str]) -> Dict[str, Any]:
        """Delete user data for GDPR deletion request."""
        deleted_records = {}
        
        async with database.transaction():
            if "profile" in categories:
                deleted_records["profile"] = await self._delete_user_profile(user_id)
            
            if "activity" in categories:
                deleted_records["activity"] = await self._anonymize_user_activity(user_id)
            
            if "search_history" in categories:
                deleted_records["search_history"] = await self._delete_search_history(user_id)
        
        # Log deletion for audit
        await audit_logger.log_event(
            AuditEventType.DATA_DELETE,
            user_id,
            "user_data",
            "gdpr_deletion",
            "success",
            metadata={"categories": categories, "records_affected": deleted_records}
        )
        
        return deleted_records
```

This comprehensive security standards document provides enterprise-grade security requirements and implementations for the DocAIche platform, ensuring robust protection against modern security threats while maintaining compliance with regulatory requirements.