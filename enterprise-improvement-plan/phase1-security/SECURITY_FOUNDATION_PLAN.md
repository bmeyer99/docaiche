# Phase 1: Critical Security Foundation
*Priority: IMMEDIATE - System Blockers*
*Timeline: Weeks 1-3*

## Overview
This phase addresses the most critical security vulnerabilities that pose immediate risk to the system. These issues must be resolved before any production deployment.

## Critical Security Fixes (Week 1-2)

### 1. Authentication Bypass Fix
**Current Issue**: `verify_admin_access()` in `/src/api/endpoints.py:422` returns `True` unconditionally

**Implementation Steps**:
```python
# Replace placeholder implementation with real JWT validation
async def verify_admin_access(authorization: str = Header(None)) -> bool:
    """Verify admin access using JWT token validation"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        role = payload.get("role")
        
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
            
        return True
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Files to Modify**:
- `/src/api/endpoints.py`
- `/src/api/v1/dependencies.py`
- Add new file: `/src/core/auth.py`

### 2. JWT Authentication System
**Implementation Components**:
- JWT token generation and validation
- Token refresh mechanism
- Secure token storage
- Role-based access control

**New Files to Create**:
```
/src/core/auth/
├── __init__.py
├── jwt_handler.py
├── models.py
├── dependencies.py
└── middleware.py
```

**Key Features**:
- Access tokens (15 minutes expiry)
- Refresh tokens (7 days expiry)
- Token blacklisting for logout
- Role-based permissions (admin, user, service)

### 3. Rate Limiting Implementation
**Library**: slowapi (async-compatible rate limiter)

**Installation**:
```bash
pip install slowapi
```

**Configuration**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.get("/api/v1/search")
@limiter.limit("30/minute")  # 30 requests per minute
async def search_endpoint(request: Request):
    pass
```

**Rate Limits per Endpoint**:
- Search endpoints: 30/minute per IP
- Admin endpoints: 10/minute per IP
- Upload endpoints: 5/minute per IP
- Health checks: 120/minute per IP

### 4. CORS Configuration Fix
**Current Issue**: CORS allows all origins (`"*"`) in `/src/main.py:183`

**Fix**:
```python
# Environment-specific CORS configuration
ALLOWED_ORIGINS = {
    "development": ["http://localhost:3000", "http://localhost:4080"],
    "staging": ["https://staging.docaiche.com"],
    "production": ["https://app.docaiche.com", "https://admin.docaiche.com"]
}

environment = os.getenv("ENVIRONMENT", "development")
allowed_origins = ALLOWED_ORIGINS.get(environment, ["http://localhost:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## Secrets Management (Week 2-3)

### 1. HashiCorp Vault Deployment
**Docker Compose Addition**:
```yaml
vault:
  image: vault:1.15.0
  ports:
    - "8200:8200"
  environment:
    - VAULT_DEV_ROOT_TOKEN_ID=dev-root-token
    - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
  volumes:
    - vault_data:/vault/data
  command: vault server -dev
  networks:
    - docaiche
```

### 2. Secret Migration Strategy
**Secrets to Move from docker-compose.yml**:
- `POSTGRES_PASSWORD`
- `WEAVIATE_API_KEY`
- `BRAVE_API_KEY`
- Database connection strings
- JWT signing keys

**Implementation**:
```python
# New secrets client
import hvac

class SecretsManager:
    def __init__(self, vault_url: str, token: str):
        self.client = hvac.Client(url=vault_url, token=token)
    
    async def get_secret(self, path: str) -> dict:
        """Retrieve secret from Vault"""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
    
    async def set_secret(self, path: str, data: dict):
        """Store secret in Vault"""
        self.client.secrets.kv.v2.create_or_update_secret(path=path, secret=data)
```

### 3. Environment Configuration
**New Configuration Structure**:
```
/config/
├── base.yaml
├── development.yaml
├── staging.yaml
└── production.yaml
```

## Compliance Foundation (Week 3)

### 1. Comprehensive Audit Logging
**Enhanced Audit System**:
```python
class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    async def log_event(self, event_type: str, user_id: str, resource: str, action: str, metadata: dict = None):
        """Log security and administrative events"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "metadata": metadata or {},
            "ip_address": get_client_ip(),
            "user_agent": get_user_agent()
        }
        self.logger.info(json.dumps(audit_entry))
```

**Events to Log**:
- Authentication attempts (success/failure)
- Administrative actions
- Configuration changes
- Data access and modifications
- Permission changes
- API key generation/revocation

### 2. Data Encryption
**Encryption at Rest**:
- Database encryption using PostgreSQL TDE
- Redis encryption for cached data
- File system encryption for uploaded documents

**Encryption in Transit**:
- TLS 1.3 for all HTTP communications
- mTLS for service-to-service communication
- WebSocket connections over TLS

**Implementation**:
```python
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data before storage"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data after retrieval"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

### 3. Privacy Controls
**Data Anonymization**:
```python
import hashlib

class PrivacyControls:
    @staticmethod
    def anonymize_user_id(user_id: str) -> str:
        """Create anonymous hash of user ID"""
        return hashlib.sha256(user_id.encode()).hexdigest()
    
    @staticmethod
    def sanitize_logs(log_data: dict) -> dict:
        """Remove PII from log data"""
        sensitive_fields = ['email', 'ip_address', 'user_id']
        sanitized = log_data.copy()
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***REDACTED***"
        return sanitized
```

## Testing & Validation

### Security Testing Checklist
- [ ] Authentication bypass tests
- [ ] JWT token validation tests
- [ ] Rate limiting functionality tests
- [ ] CORS configuration validation
- [ ] Secrets management integration tests
- [ ] Audit logging verification
- [ ] Encryption/decryption tests

### Penetration Testing
- OWASP ZAP automated scanning
- Manual authentication testing
- Rate limiting bypass attempts
- Input validation testing
- Session management testing

## Rollback Procedures

### If Authentication Changes Fail
1. Revert to environment variable based auth temporarily
2. Maintain admin access through direct database modification
3. Use emergency admin token for system recovery

### If Secrets Management Fails
1. Fallback to environment variables
2. Maintain service continuity with existing credentials
3. Fix Vault configuration without service disruption

## Success Criteria

### Security Metrics
- [ ] Zero authentication bypass vulnerabilities
- [ ] All endpoints protected by rate limiting
- [ ] No hardcoded secrets in configuration files
- [ ] CORS properly configured for each environment
- [ ] All sensitive data encrypted at rest and in transit
- [ ] Comprehensive audit trail for all security events

### Performance Metrics
- [ ] < 50ms additional latency from security middleware
- [ ] Rate limiting allows legitimate traffic while blocking abuse
- [ ] Secrets retrieval < 10ms response time

### Compliance Metrics
- [ ] All administrative actions logged
- [ ] PII handling compliant with privacy requirements
- [ ] Encryption meets enterprise security standards

## Dependencies
- JWT library (PyJWT)
- Rate limiting library (slowapi)
- Vault client library (hvac)
- Encryption library (cryptography)
- Audit logging infrastructure

## Next Phase
Upon completion, proceed to Phase 2: Architecture Consolidation with a secure foundation in place.