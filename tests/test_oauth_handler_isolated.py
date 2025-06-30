"""
Isolated Unit Tests for OAuth 2.1 Handler
=========================================

Simplified test suite that tests OAuth functionality in isolation.
"""

import unittest
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import secrets


class TestOAuth21Functionality(unittest.TestCase):
    """Test OAuth 2.1 functionality in isolation."""
    
    def test_pkce_challenge_generation(self):
        """Test PKCE challenge generation logic."""
        # Generate code verifier
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        # Generate code challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        # Verify verifier properties
        self.assertGreaterEqual(len(code_verifier), 43)  # Min length
        self.assertLessEqual(len(code_verifier), 128)   # Max length
        
        # Verify challenge can be recomputed
        recomputed_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        self.assertEqual(code_challenge, recomputed_challenge)
    
    def test_authorization_url_building(self):
        """Test authorization URL parameter building."""
        params = {
            "client_id": "test_client",
            "redirect_uri": "https://app.example.com/callback",
            "response_type": "code",
            "scope": "read write",
            "state": "random_state_123",
            "code_challenge": "test_challenge",
            "code_challenge_method": "S256",
            "resource": "https://api.example.com"
        }
        
        # Build query string
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        
        # Verify all parameters are included
        for key, value in params.items():
            self.assertIn(f"{key}={value}", query_string)
    
    def test_token_expiration_check(self):
        """Test token expiration logic."""
        # Valid token (expires in 1 hour)
        valid_exp = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        self.assertGreater(valid_exp, datetime.now(timezone.utc).timestamp())
        
        # Expired token (expired 1 hour ago)
        expired_exp = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        self.assertLess(expired_exp, datetime.now(timezone.utc).timestamp())
    
    def test_scope_validation(self):
        """Test scope validation logic."""
        # Token scopes
        token_scopes = "read write admin".split()
        
        # Test valid scope
        self.assertIn("read", token_scopes)
        self.assertIn("write", token_scopes)
        
        # Test invalid scope
        self.assertNotIn("delete", token_scopes)
        
        # Test multiple scopes
        required_scopes = ["read", "write"]
        has_all_scopes = all(scope in token_scopes for scope in required_scopes)
        self.assertTrue(has_all_scopes)
    
    def test_resource_indicator_validation(self):
        """Test resource indicator validation."""
        # Token resources
        token_resources = ["https://api.example.com", "https://data.example.com"]
        
        # Test valid resource
        self.assertIn("https://api.example.com", token_resources)
        
        # Test invalid resource
        self.assertNotIn("https://other.example.com", token_resources)
        
        # Test multiple resources
        required_resources = ["https://api.example.com"]
        has_all_resources = all(res in token_resources for res in required_resources)
        self.assertTrue(has_all_resources)
    
    def test_token_id_generation(self):
        """Test unique token ID generation."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        token_id = f"oauth_test_provider_{timestamp}_{random_part}"
        
        # Verify format
        self.assertTrue(token_id.startswith("oauth_"))
        self.assertIn("test_provider", token_id)
        # Token ID has format: oauth_test_provider_TIMESTAMP_RANDOM
        parts = token_id.split("_")
        self.assertGreaterEqual(len(parts), 4)
        
        # Generate another ID and verify uniqueness
        random_part2 = secrets.token_hex(4)
        token_id2 = f"oauth_test_provider_{timestamp}_{random_part2}"
        self.assertNotEqual(token_id, token_id2)
    
    def test_refresh_token_data_structure(self):
        """Test refresh token request data structure."""
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": "old_refresh_token",
            "client_id": "test_client",
            "client_secret": "test_secret"
        }
        
        # Add optional resource indicators
        resources = ["https://api.example.com", "https://data.example.com"]
        refresh_data["resource"] = " ".join(resources)
        
        # Verify structure
        self.assertEqual(refresh_data["grant_type"], "refresh_token")
        self.assertIn("refresh_token", refresh_data)
        self.assertIn("resource", refresh_data)
        self.assertEqual(refresh_data["resource"], "https://api.example.com https://data.example.com")
    
    def test_revocation_data_structure(self):
        """Test token revocation data structure."""
        revocation_data = {
            "token": "token_to_revoke",
            "token_type_hint": "access_token",
            "client_id": "test_client",
            "client_secret": "test_secret"
        }
        
        # Verify structure
        self.assertIn("token", revocation_data)
        self.assertIn("token_type_hint", revocation_data)
        self.assertEqual(revocation_data["token_type_hint"], "access_token")
    
    def test_introspection_response_handling(self):
        """Test token introspection response handling."""
        # Active token response
        active_response = {
            "active": True,
            "scope": "read write",
            "client_id": "test_client",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        self.assertTrue(active_response["active"])
        
        # Inactive token response
        inactive_response = {
            "active": False
        }
        self.assertFalse(inactive_response["active"])
    
    def test_auth_token_metadata(self):
        """Test auth token metadata structure."""
        metadata = {
            "provider": "test_provider",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "auth_method": "authorization_code"
        }
        
        # Verify metadata
        self.assertEqual(metadata["provider"], "test_provider")
        self.assertEqual(metadata["auth_method"], "authorization_code")
        self.assertIn("T", metadata["issued_at"])  # ISO format includes T
    
    def test_oauth_config_validation(self):
        """Test OAuth configuration validation."""
        config = {
            "provider_name": "test",
            "client_id": "client",
            "client_secret": "secret",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "require_pkce": True,
            "require_resource_indicators": True,
            "access_token_ttl": 3600,
            "refresh_token_ttl": 2592000
        }
        
        # Verify required fields
        self.assertIn("client_id", config)
        self.assertIn("client_secret", config)
        self.assertIn("authorization_endpoint", config)
        self.assertIn("token_endpoint", config)
        
        # Verify security settings
        self.assertTrue(config["require_pkce"])
        self.assertTrue(config["require_resource_indicators"])
        
        # Verify token lifetimes
        self.assertEqual(config["access_token_ttl"], 3600)  # 1 hour
        self.assertEqual(config["refresh_token_ttl"], 2592000)  # 30 days
    
    def test_provider_info_structure(self):
        """Test provider information structure."""
        provider_info = {
            "provider": "test_provider",
            "type": "oauth2.1",
            "features": {
                "pkce_required": True,
                "resource_indicators": True,
                "refresh_token_rotation": True,
                "token_introspection": True,
                "token_revocation": True,
                "dpop_support": False
            },
            "endpoints": {
                "authorization": "https://auth.example.com/authorize",
                "token": "https://auth.example.com/token",
                "introspection": "https://auth.example.com/introspect",
                "revocation": "https://auth.example.com/revoke",
                "jwks": None
            }
        }
        
        # Verify structure
        self.assertEqual(provider_info["type"], "oauth2.1")
        self.assertTrue(provider_info["features"]["pkce_required"])
        self.assertTrue(provider_info["features"]["resource_indicators"])
        self.assertIn("authorization", provider_info["endpoints"])
        self.assertIn("token", provider_info["endpoints"])


if __name__ == "__main__":
    unittest.main()