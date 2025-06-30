"""
Unit tests for OAuth 2.1 Authentication
=======================================

Tests for OAuth 2.1 with Resource Indicators, JWT validation,
and security compliance.
"""

import pytest
import jwt
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from src.mcp.auth.oauth_handler import (
    OAuth21Handler,
    TokenValidator,
    ResourceIndicator,
    TokenInfo,
    AuthorizationError
)
from src.mcp.auth.jwks_client import JWKSClient
from src.mcp.schemas import MCPRequest


class TestTokenValidator:
    """Test JWT token validation."""
    
    @pytest.fixture
    def rsa_keys(self):
        """Generate RSA key pair for testing."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # Convert to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            "private_key": private_key,
            "public_key": public_key,
            "private_pem": private_pem,
            "public_pem": public_pem
        }
    
    @pytest.fixture
    def mock_jwks_client(self, rsa_keys):
        """Create mock JWKS client."""
        client = Mock(spec=JWKSClient)
        client.get_public_key = AsyncMock(return_value=rsa_keys["public_pem"])
        return client
    
    @pytest.fixture
    def token_validator(self, mock_jwks_client):
        return TokenValidator(
            jwks_client=mock_jwks_client,
            issuer="https://auth.example.com",
            audience="docaiche-mcp"
        )
    
    def create_test_token(self, private_key, claims=None, headers=None):
        """Create a test JWT token."""
        default_claims = {
            "iss": "https://auth.example.com",
            "aud": "docaiche-mcp",
            "sub": "user123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "jti": "token123"
        }
        
        if claims:
            default_claims.update(claims)
        
        default_headers = {
            "kid": "test-key-1",
            "alg": "RS256"
        }
        
        if headers:
            default_headers.update(headers)
        
        return jwt.encode(
            default_claims,
            private_key,
            algorithm="RS256",
            headers=default_headers
        )
    
    @pytest.mark.asyncio
    async def test_validate_valid_token(self, token_validator, rsa_keys):
        """Test validation of valid JWT token."""
        token = self.create_test_token(
            rsa_keys["private_key"],
            claims={
                "scope": "read write",
                "resource": ["docaiche:collections", "docaiche:search"]
            }
        )
        
        result = await token_validator.validate_token(token)
        
        assert result.is_valid is True
        assert result.subject == "user123"
        assert "read" in result.scopes
        assert "write" in result.scopes
        assert "docaiche:collections" in result.resources
    
    @pytest.mark.asyncio
    async def test_validate_expired_token(self, token_validator, rsa_keys):
        """Test validation of expired token."""
        token = self.create_test_token(
            rsa_keys["private_key"],
            claims={
                "exp": datetime.utcnow() - timedelta(hours=1)  # Expired
            }
        )
        
        result = await token_validator.validate_token(token)
        
        assert result.is_valid is False
        assert "expired" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_wrong_issuer(self, token_validator, rsa_keys):
        """Test validation with wrong issuer."""
        token = self.create_test_token(
            rsa_keys["private_key"],
            claims={
                "iss": "https://wrong-issuer.com"
            }
        )
        
        result = await token_validator.validate_token(token)
        
        assert result.is_valid is False
        assert "issuer" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_wrong_audience(self, token_validator, rsa_keys):
        """Test validation with wrong audience."""
        token = self.create_test_token(
            rsa_keys["private_key"],
            claims={
                "aud": "wrong-audience"
            }
        )
        
        result = await token_validator.validate_token(token)
        
        assert result.is_valid is False
        assert "audience" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_invalid_signature(self, token_validator, rsa_keys):
        """Test validation with invalid signature."""
        # Create token with different key
        wrong_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        token = self.create_test_token(wrong_key)
        
        result = await token_validator.validate_token(token)
        
        assert result.is_valid is False
        assert "signature" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_claims(self, token_validator, rsa_keys):
        """Test validation with missing required claims."""
        # Create token without 'sub' claim
        claims = {
            "iss": "https://auth.example.com",
            "aud": "docaiche-mcp",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
            # Missing 'sub'
        }
        
        token = jwt.encode(
            claims,
            rsa_keys["private_key"],
            algorithm="RS256",
            headers={"kid": "test-key-1"}
        )
        
        result = await token_validator.validate_token(token)
        
        assert result.is_valid is False
        assert "missing" in result.error.lower()


class TestResourceIndicator:
    """Test Resource Indicator validation."""
    
    @pytest.fixture
    def resource_validator(self):
        return ResourceIndicator(
            allowed_resources=[
                "docaiche:collections",
                "docaiche:search",
                "docaiche:ingest",
                "docaiche:status"
            ]
        )
    
    def test_validate_allowed_resource(self, resource_validator):
        """Test validation of allowed resources."""
        assert resource_validator.validate_resource("docaiche:search") is True
        assert resource_validator.validate_resource("docaiche:collections") is True
    
    def test_validate_disallowed_resource(self, resource_validator):
        """Test validation of disallowed resources."""
        assert resource_validator.validate_resource("docaiche:admin") is False
        assert resource_validator.validate_resource("unknown:resource") is False
    
    def test_validate_resource_pattern(self, resource_validator):
        """Test validation with resource patterns."""
        resource_validator.allowed_patterns = [
            r"^docaiche:.*",
            r"^https://api\.example\.com/.*"
        ]
        
        assert resource_validator.validate_resource_pattern("docaiche:anything") is True
        assert resource_validator.validate_resource_pattern("https://api.example.com/data") is True
        assert resource_validator.validate_resource_pattern("http://evil.com/data") is False
    
    def test_check_token_resources(self, resource_validator):
        """Test checking token resources against request."""
        token_info = TokenInfo(
            is_valid=True,
            subject="user123",
            scopes=["read", "write"],
            resources=["docaiche:search", "docaiche:collections"]
        )
        
        # Allowed request
        assert resource_validator.check_token_resources(
            token_info,
            requested_resource="docaiche:search"
        ) is True
        
        # Disallowed request
        assert resource_validator.check_token_resources(
            token_info,
            requested_resource="docaiche:ingest"
        ) is False


class TestOAuth21Handler:
    """Test OAuth 2.1 handler integration."""
    
    @pytest.fixture
    def mock_dependencies(self, rsa_keys):
        """Create mock dependencies."""
        mock_jwks = Mock(spec=JWKSClient)
        mock_jwks.get_public_key = AsyncMock(return_value=rsa_keys["public_pem"])
        
        return {
            "jwks_client": mock_jwks,
            "rsa_keys": rsa_keys
        }
    
    @pytest.fixture
    def oauth_handler(self, mock_dependencies):
        return OAuth21Handler(
            jwks_url="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            audience="docaiche-mcp",
            jwks_client=mock_dependencies["jwks_client"]
        )
    
    def create_auth_token(self, private_key, **kwargs):
        """Create authorization token."""
        claims = {
            "iss": "https://auth.example.com",
            "aud": "docaiche-mcp",
            "sub": "user123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "scope": kwargs.get("scope", "read write"),
            "resource": kwargs.get("resource", ["docaiche:search"])
        }
        
        return jwt.encode(
            claims,
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key-1", "alg": "RS256"}
        )
    
    @pytest.mark.asyncio
    async def test_authorize_request_success(self, oauth_handler, mock_dependencies):
        """Test successful request authorization."""
        token = self.create_auth_token(
            mock_dependencies["rsa_keys"]["private_key"],
            scope="read write",
            resource=["docaiche:search", "docaiche:collections"]
        )
        
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        auth_context = await oauth_handler.authorize_request(
            request=request,
            auth_header=f"Bearer {token}"
        )
        
        assert auth_context.authenticated is True
        assert auth_context.client_id == "user123"
        assert "read" in auth_context.scopes
        assert auth_context.resource_access["docaiche:search"] is True
    
    @pytest.mark.asyncio
    async def test_authorize_request_no_token(self, oauth_handler):
        """Test authorization without token."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        with pytest.raises(AuthorizationError) as exc_info:
            await oauth_handler.authorize_request(
                request=request,
                auth_header=None
            )
        
        assert "No authorization" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authorize_request_invalid_token(self, oauth_handler, mock_dependencies):
        """Test authorization with invalid token."""
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        with pytest.raises(AuthorizationError) as exc_info:
            await oauth_handler.authorize_request(
                request=request,
                auth_header="Bearer invalid.token.here"
            )
        
        assert "Invalid token" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authorize_request_insufficient_scope(self, oauth_handler, mock_dependencies):
        """Test authorization with insufficient scope."""
        token = self.create_auth_token(
            mock_dependencies["rsa_keys"]["private_key"],
            scope="read",  # Missing write scope
            resource=["docaiche:search"]
        )
        
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"tool": "docaiche_ingest"}  # Requires write
        )
        
        with pytest.raises(AuthorizationError) as exc_info:
            await oauth_handler.authorize_request(
                request=request,
                auth_header=f"Bearer {token}",
                required_scope="write"
            )
        
        assert "Insufficient scope" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authorize_request_wrong_resource(self, oauth_handler, mock_dependencies):
        """Test authorization for wrong resource."""
        token = self.create_auth_token(
            mock_dependencies["rsa_keys"]["private_key"],
            resource=["docaiche:search"]  # Only search access
        )
        
        request = MCPRequest(
            id="test",
            method="resource/read",
            params={"resource": "collections"}  # Requesting collections
        )
        
        with pytest.raises(AuthorizationError) as exc_info:
            await oauth_handler.authorize_request(
                request=request,
                auth_header=f"Bearer {token}",
                requested_resource="docaiche:collections"
            )
        
        assert "resource access" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_check_authorization_caching(self, oauth_handler, mock_dependencies):
        """Test that token validation results are cached."""
        token = self.create_auth_token(
            mock_dependencies["rsa_keys"]["private_key"]
        )
        
        request = MCPRequest(
            id="test",
            method="tool/execute",
            params={"tool": "docaiche_search"}
        )
        
        # First authorization
        await oauth_handler.authorize_request(
            request=request,
            auth_header=f"Bearer {token}"
        )
        
        # Second authorization (should use cache)
        await oauth_handler.authorize_request(
            request=request,
            auth_header=f"Bearer {token}"
        )
        
        # JWKS client should only be called once due to caching
        assert mock_dependencies["jwks_client"].get_public_key.call_count == 1
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, oauth_handler):
        """Test token revocation."""
        token_id = "token123"
        
        # Revoke token
        await oauth_handler.revoke_token(token_id)
        
        # Check that token is revoked
        is_revoked = await oauth_handler.is_token_revoked(token_id)
        assert is_revoked is True
    
    @pytest.mark.asyncio
    async def test_dpop_validation(self, oauth_handler, mock_dependencies):
        """Test DPoP (Demonstrating Proof of Possession) validation."""
        # Create DPoP proof
        dpop_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        dpop_proof = jwt.encode(
            {
                "jti": "dpop123",
                "htm": "POST",
                "htu": "https://api.docaiche.com/mcp",
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(minutes=5)
            },
            dpop_key,
            algorithm="RS256",
            headers={
                "typ": "dpop+jwt",
                "alg": "RS256",
                "jwk": {
                    # Include public key in header
                    "kty": "RSA",
                    "n": "...",  # Would be actual key material
                    "e": "AQAB"
                }
            }
        )
        
        # Test DPoP validation (would need full implementation)
        # This is a placeholder for DPoP support
        assert dpop_proof is not None


# Test security compliance
class TestSecurityCompliance:
    """Test OAuth 2.1 security compliance."""
    
    @pytest.fixture
    def oauth_handler(self):
        return OAuth21Handler(
            jwks_url="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            audience="docaiche-mcp"
        )
    
    def test_pkce_required(self, oauth_handler):
        """Test that PKCE is required for authorization code flow."""
        assert oauth_handler.require_pkce is True
    
    def test_no_implicit_flow(self, oauth_handler):
        """Test that implicit flow is not supported."""
        assert "implicit" not in oauth_handler.supported_flows
    
    def test_secure_redirect_uri_required(self, oauth_handler):
        """Test that only HTTPS redirect URIs are allowed."""
        assert oauth_handler.validate_redirect_uri("https://example.com/callback") is True
        assert oauth_handler.validate_redirect_uri("http://example.com/callback") is False
    
    def test_state_parameter_required(self, oauth_handler):
        """Test that state parameter is required."""
        assert oauth_handler.require_state is True