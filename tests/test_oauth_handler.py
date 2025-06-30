"""
Unit Tests for OAuth 2.1 Handler
=================================

Comprehensive test suite for the OAuth 2.1 handler implementation
covering authentication flows, token validation, and security features.
"""

import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import secrets
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestOAuth21Handler(unittest.TestCase):
    """Test suite for OAuth 2.1 handler operations."""
    
    def setUp(self):
        """Set up test environment."""
        from src.mcp.auth.oauth_handler import OAuth21Config, OAuth21Handler
        from src.mcp.schemas import ResourceIndicator
        
        self.config = OAuth21Config(
            provider_name="test_provider",
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token",
            introspection_endpoint="https://auth.example.com/introspect",
            revocation_endpoint="https://auth.example.com/revoke",
            require_pkce=True,
            require_resource_indicators=True,
            allowed_resource_servers=["https://api.example.com"]
        )
        
        self.handler = OAuth21Handler(
            config=self.config,
            token_storage=None,
            http_client=None,
            security_auditor=None
        )
        
        self.resource_indicators = [
            ResourceIndicator(
                resource="https://api.example.com",
                actions=["read", "write"]
            )
        ]
    
    def test_pkce_challenge_generation(self):
        """Test PKCE challenge generation."""
        redirect_uri = "https://app.example.com/callback"
        scope = "read write"
        
        auth_url, pkce_challenge = self.handler.initiate_auth_flow(
            redirect_uri=redirect_uri,
            scope=scope,
            resource_indicators=self.resource_indicators
        )
        
        # Verify PKCE challenge
        self.assertIsNotNone(pkce_challenge.code_verifier)
        self.assertIsNotNone(pkce_challenge.code_challenge)
        self.assertEqual(pkce_challenge.code_challenge_method, "S256")
        
        # Verify verifier length
        self.assertGreaterEqual(len(pkce_challenge.code_verifier), 43)
        self.assertLessEqual(len(pkce_challenge.code_verifier), 128)
        
        # Verify challenge is S256 of verifier
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(pkce_challenge.code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        self.assertEqual(pkce_challenge.code_challenge, expected_challenge)
        
        # Verify auth URL
        self.assertTrue(auth_url.startswith(self.config.authorization_endpoint))
        self.assertIn("code_challenge=", auth_url)
        self.assertIn("code_challenge_method=S256", auth_url)
    
    def test_authorization_request_creation(self):
        """Test authorization request creation with resource indicators."""
        redirect_uri = "https://app.example.com/callback"
        scope = "read write"
        state = "test_state_123"
        
        auth_url, pkce_challenge = self.handler.initiate_auth_flow(
            redirect_uri=redirect_uri,
            scope=scope,
            resource_indicators=self.resource_indicators,
            state=state
        )
        
        # Parse URL parameters
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)
        
        # Verify required parameters
        self.assertEqual(params["client_id"][0], self.config.client_id)
        self.assertEqual(params["redirect_uri"][0], redirect_uri)
        self.assertEqual(params["response_type"][0], "code")
        self.assertEqual(params["scope"][0], scope)
        self.assertEqual(params["state"][0], state)
        
        # Verify resource indicators
        self.assertIn("resource", params)
        self.assertEqual(params["resource"][0], "https://api.example.com")
    
    def test_pkce_verification(self):
        """Test PKCE challenge verification."""
        async def test_verify():
            # Generate challenge
            verifier = base64.urlsafe_b64encode(
                secrets.token_bytes(32)
            ).decode('utf-8').rstrip('=')
            
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode('utf-8')).digest()
            ).decode('utf-8').rstrip('=')
            
            # Test valid verification
            await self.handler._verify_pkce_challenge(verifier, challenge, "S256")
            
            # Test invalid verifier
            invalid_verifier = base64.urlsafe_b64encode(
                secrets.token_bytes(32)
            ).decode('utf-8').rstrip('=')
            
            from src.mcp.exceptions import ValidationError
            with self.assertRaises(ValidationError) as cm:
                await self.handler._verify_pkce_challenge(
                    invalid_verifier, challenge, "S256"
                )
            self.assertEqual(cm.exception.error_code, "PKCE_VERIFICATION_FAILED")
            
            # Test unsupported method
            with self.assertRaises(ValidationError) as cm:
                await self.handler._verify_pkce_challenge(
                    verifier, challenge, "plain"
                )
            self.assertEqual(cm.exception.error_code, "INVALID_PKCE_METHOD")
        
        asyncio.run(test_verify())
    
    def test_token_validation(self):
        """Test token validation logic."""
        async def test_validate():
            # Test with revoked token
            self.handler._revoked_tokens.add("revoked_token")
            result = await self.handler.validate_token("revoked_token")
            self.assertFalse(result)
            
            # Test with expired token
            expired_claims = {
                "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
                "scope": "read write"
            }
            self.handler._validate_jwt_token = AsyncMock(return_value=expired_claims)
            result = await self.handler.validate_token("expired_token")
            self.assertFalse(result)
            
            # Test with valid token
            valid_claims = {
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
                "scope": "read write",
                "resource": ["https://api.example.com"]
            }
            self.handler._validate_jwt_token = AsyncMock(return_value=valid_claims)
            result = await self.handler.validate_token("valid_token", "read")
            self.assertTrue(result)
            
            # Test scope validation
            result = await self.handler.validate_token("valid_token", "admin")
            self.assertFalse(result)
            
            # Test resource validation
            result = await self.handler.validate_token(
                "valid_token", 
                required_resources=["https://api.example.com"]
            )
            self.assertTrue(result)
            
            result = await self.handler.validate_token(
                "valid_token",
                required_resources=["https://other.example.com"]
            )
            self.assertFalse(result)
        
        asyncio.run(test_validate())
    
    def test_authentication_flow(self):
        """Test complete authentication flow."""
        async def test_auth():
            # Setup auth flow
            redirect_uri = "https://app.example.com/callback"
            scope = "read write"
            
            auth_url, pkce_challenge = self.handler.initiate_auth_flow(
                redirect_uri=redirect_uri,
                scope=scope,
                resource_indicators=self.resource_indicators
            )
            
            # Extract state from auth URL
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(auth_url)
            params = parse_qs(parsed.query)
            state = params["state"][0]
            
            # Simulate authorization code
            auth_code = "test_auth_code_123"
            
            # Mock token exchange
            self.handler._exchange_code_for_token = AsyncMock(return_value={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": scope
            })
            
            # Mock token validation
            self.handler._validate_access_token = AsyncMock(return_value={
                "sub": "test_user",
                "scope": scope,
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
            })
            
            # Authenticate
            credentials = {
                "authorization_code": auth_code,
                "code_verifier": pkce_challenge.code_verifier,
                "state": state
            }
            
            auth_token = await self.handler.authenticate(
                credentials,
                self.resource_indicators
            )
            
            # Verify token
            self.assertIsNotNone(auth_token)
            self.assertEqual(auth_token.access_token, "test_access_token")
            self.assertEqual(auth_token.refresh_token, "test_refresh_token")
            self.assertEqual(auth_token.scope, scope)
            self.assertEqual(auth_token.token_type, "Bearer")
            
            # Verify resource access
            self.assertIn("https://api.example.com", auth_token.resource_access)
            self.assertEqual(
                auth_token.resource_access["https://api.example.com"],
                ["read", "write"]
            )
        
        asyncio.run(test_auth())
    
    def test_token_refresh(self):
        """Test token refresh flow."""
        async def test_refresh():
            # Mock HTTP client
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "read write"
            })
            
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            self.handler.http_client = mock_http
            
            # Refresh token
            auth_token = await self.handler.refresh_token(
                "old_refresh_token",
                self.resource_indicators
            )
            
            # Verify new token
            self.assertEqual(auth_token.access_token, "new_access_token")
            self.assertEqual(auth_token.refresh_token, "new_refresh_token")
            
            # Verify HTTP call
            mock_http.post.assert_called_once()
            call_args = mock_http.post.call_args
            self.assertEqual(call_args[0][0], self.config.token_endpoint)
            
            # Verify refresh data
            refresh_data = call_args[1]["data"]
            self.assertEqual(refresh_data["grant_type"], "refresh_token")
            self.assertEqual(refresh_data["refresh_token"], "old_refresh_token")
            self.assertIn("resource", refresh_data)
        
        asyncio.run(test_refresh())
    
    def test_token_revocation(self):
        """Test token revocation."""
        async def test_revoke():
            # Test without HTTP client
            result = await self.handler.revoke_token("test_token")
            self.assertTrue(result)
            self.assertIn("test_token", self.handler._revoked_tokens)
            
            # Test with HTTP client
            mock_response = Mock()
            mock_response.status_code = 200
            
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            self.handler.http_client = mock_http
            
            result = await self.handler.revoke_token(
                "test_token_2",
                "refresh_token"
            )
            self.assertTrue(result)
            self.assertIn("test_token_2", self.handler._revoked_tokens)
            
            # Verify HTTP call
            mock_http.post.assert_called_once()
            call_args = mock_http.post.call_args
            self.assertEqual(call_args[0][0], self.config.revocation_endpoint)
            
            # Verify revocation data
            revoke_data = call_args[1]["data"]
            self.assertEqual(revoke_data["token"], "test_token_2")
            self.assertEqual(revoke_data["token_type_hint"], "refresh_token")
        
        asyncio.run(test_revoke())
    
    def test_jwt_validation_fallback(self):
        """Test JWT validation fallback for testing."""
        async def test_jwt():
            # Test simple JWT decode for testing
            test_payload = {
                "sub": "test_user",
                "scope": "read write",
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
            }
            
            # Create fake JWT
            header = base64.urlsafe_b64encode(
                json.dumps({"alg": "none", "typ": "JWT"}).encode()
            ).decode().rstrip('=')
            
            payload = base64.urlsafe_b64encode(
                json.dumps(test_payload).encode()
            ).decode().rstrip('=')
            
            signature = ""
            fake_jwt = f"{header}.{payload}.{signature}"
            
            # Validate
            claims = await self.handler._validate_jwt_token(fake_jwt)
            self.assertEqual(claims["sub"], "test_user")
            self.assertEqual(claims["scope"], "read write")
        
        asyncio.run(test_jwt())
    
    def test_token_introspection(self):
        """Test token introspection."""
        async def test_introspect():
            # Test without endpoint
            result = await self.handler._introspect_token("test_token")
            self.assertTrue(result)
            
            # Test with endpoint
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={"active": True})
            
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            self.handler.http_client = mock_http
            
            result = await self.handler._introspect_token("active_token")
            self.assertTrue(result)
            
            # Test inactive token
            mock_response.json = Mock(return_value={"active": False})
            result = await self.handler._introspect_token("inactive_token")
            self.assertFalse(result)
        
        asyncio.run(test_introspect())
    
    def test_provider_info(self):
        """Test provider information."""
        info = self.handler.get_provider_info()
        
        self.assertEqual(info["provider"], "test_provider")
        self.assertEqual(info["type"], "oauth2.1")
        
        # Verify features
        features = info["features"]
        self.assertTrue(features["pkce_required"])
        self.assertTrue(features["resource_indicators"])
        self.assertTrue(features["token_introspection"])
        self.assertTrue(features["token_revocation"])
        
        # Verify endpoints
        endpoints = info["endpoints"]
        self.assertEqual(endpoints["authorization"], self.config.authorization_endpoint)
        self.assertEqual(endpoints["token"], self.config.token_endpoint)
        self.assertEqual(endpoints["introspection"], self.config.introspection_endpoint)
        self.assertEqual(endpoints["revocation"], self.config.revocation_endpoint)


class TestOAuth21Config(unittest.TestCase):
    """Test OAuth 2.1 configuration."""
    
    def test_config_defaults(self):
        """Test configuration default values."""
        from src.mcp.auth.oauth_handler import OAuth21Config
        
        config = OAuth21Config(
            provider_name="test",
            client_id="client",
            client_secret="secret",
            authorization_endpoint="https://auth.example.com/authorize",
            token_endpoint="https://auth.example.com/token"
        )
        
        # Verify defaults
        self.assertTrue(config.require_pkce)
        self.assertTrue(config.require_resource_indicators)
        self.assertEqual(config.access_token_ttl, 3600)
        self.assertEqual(config.refresh_token_ttl, 2592000)
        self.assertTrue(config.refresh_token_rotation)
        self.assertFalse(config.dpop_required)
        self.assertEqual(config.max_auth_age, 300)
    
    def test_pkce_challenge_expiration(self):
        """Test PKCE challenge expiration."""
        from src.mcp.auth.oauth_handler import PKCEChallenge
        
        # Fresh challenge
        fresh = PKCEChallenge(
            code_verifier="test_verifier",
            code_challenge="test_challenge"
        )
        self.assertFalse(fresh.is_expired())
        
        # Expired challenge
        old_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        expired = PKCEChallenge(
            code_verifier="test_verifier",
            code_challenge="test_challenge",
            created_at=old_time
        )
        self.assertTrue(expired.is_expired())


if __name__ == "__main__":
    unittest.main()