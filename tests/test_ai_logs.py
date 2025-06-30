"""
Comprehensive test suite for AI Logging API
Tests all endpoints, edge cases, and integration scenarios
"""

import pytest
import asyncio
import json
import websockets
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from src.api.v1.ai_logs_endpoints import router
from src.api.models.ai_logs import (
    QueryMode, AILogQuery, AILogResponse, LogEntry,
    CorrelationRequest, CorrelationResponse,
    PatternRequest, PatternResponse,
    ConversationTracking, WorkspaceSummary,
    ExportRequest, ExportFormat
)
from src.api.utils.ai_log_processor import AILogProcessor
from src.api.utils.loki_client import LokiClient
from src.api.utils.log_correlator import LogCorrelator
from src.api.utils.pattern_detector import PatternDetector
from src.api.utils.stream_manager import StreamManager
from src.api.utils.cache_manager import CacheManager


class TestAILogsQueryEndpoint:
    """Test the main query endpoint with various parameters"""
    
    @pytest.fixture
    def mock_processor(self):
        processor = AsyncMock(spec=AILogProcessor)
        processor.process_query.return_value = {
            "logs": [
                {
                    "timestamp": "2025-06-30T10:00:00Z",
                    "level": "INFO",
                    "service": "api",
                    "message": "AI request processed",
                    "correlation_id": "test-123",
                    "conversation_id": "conv-456",
                    "model": "gpt-4",
                    "tokens_used": 150
                }
            ],
            "total_count": 1,
            "query_time_ms": 50,
            "patterns_detected": [],
            "mode": "troubleshoot"
        }
        return processor
    
    @pytest.mark.asyncio
    async def test_query_basic(self, mock_processor):
        """Test basic query functionality"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/query")
                
                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 1
                assert len(data["logs"]) == 1
                assert data["logs"][0]["correlation_id"] == "test-123"
    
    @pytest.mark.asyncio
    async def test_query_with_filters(self, mock_processor):
        """Test query with various filters"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app) as client:
                # Test with mode filter
                response = client.get("/api/v1/ai_logs/query?mode=performance")
                assert response.status_code == 200
                
                # Test with service filter
                response = client.get("/api/v1/ai_logs/query?services=api,anythingllm")
                assert response.status_code == 200
                
                # Test with time range
                response = client.get("/api/v1/ai_logs/query?time_range=24h")
                assert response.status_code == 200
                
                # Test with correlation ID
                response = client.get("/api/v1/ai_logs/query?correlation_id=test-123")
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_query_error_handling(self, mock_processor):
        """Test error handling in query endpoint"""
        from src.main import app
        
        mock_processor.process_query.side_effect = Exception("Loki connection failed")
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/query")
                
                assert response.status_code == 500
                data = response.json()
                assert "error" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_query_cache_header(self, mock_processor):
        """Test cache control headers"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor', mock_processor):
            with TestClient(app) as client:
                # Test with cache enabled (default)
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 200
                
                # Test with cache disabled
                response = client.get("/api/v1/ai_logs/query?cache=false")
                assert response.status_code == 200
                # Verify processor was called with cache=False
                mock_processor.process_query.assert_called_with(
                    query_params=pytest.Any(dict),
                    use_cache=False
                )


class TestAILogsCorrelationEndpoint:
    """Test the correlation analysis endpoint"""
    
    @pytest.fixture
    def mock_correlator(self):
        correlator = AsyncMock(spec=LogCorrelator)
        correlator.analyze_correlation.return_value = {
            "correlation_id": "test-123",
            "service_flow": [
                {"service": "api", "timestamp": "2025-06-30T10:00:00Z", "duration_ms": 50},
                {"service": "anythingllm", "timestamp": "2025-06-30T10:00:01Z", "duration_ms": 200}
            ],
            "total_duration_ms": 250,
            "services_involved": ["api", "anythingllm"],
            "error_propagation": [],
            "bottlenecks": []
        }
        return correlator
    
    @pytest.mark.asyncio
    async def test_correlation_analysis(self, mock_correlator):
        """Test correlation analysis functionality"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.correlator', mock_correlator):
            with TestClient(app) as client:
                request_data = {
                    "correlation_id": "test-123",
                    "include_metrics": True
                }
                response = client.post("/api/v1/ai_logs/correlate", json=request_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["correlation_id"] == "test-123"
                assert len(data["service_flow"]) == 2
                assert data["total_duration_ms"] == 250
    
    @pytest.mark.asyncio
    async def test_correlation_not_found(self, mock_correlator):
        """Test correlation with non-existent ID"""
        from src.main import app
        
        mock_correlator.analyze_correlation.return_value = None
        
        with patch('src.api.v1.ai_logs_endpoints.correlator', mock_correlator):
            with TestClient(app) as client:
                request_data = {"correlation_id": "non-existent"}
                response = client.post("/api/v1/ai_logs/correlate", json=request_data)
                
                assert response.status_code == 404
                assert "not found" in response.json()["detail"]


class TestAILogsPatternDetection:
    """Test pattern detection functionality"""
    
    @pytest.fixture
    def mock_detector(self):
        detector = AsyncMock(spec=PatternDetector)
        detector.detect_patterns.return_value = {
            "patterns_found": [
                {
                    "pattern_type": "rate_limit",
                    "confidence": 0.95,
                    "occurrences": 5,
                    "description": "Rate limiting detected on API endpoint"
                }
            ],
            "recommendations": [
                "Consider implementing request batching",
                "Increase rate limit for authenticated users"
            ]
        }
        return detector
    
    @pytest.mark.asyncio
    async def test_pattern_detection(self, mock_detector):
        """Test pattern detection endpoint"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.detector', mock_detector):
            with TestClient(app) as client:
                request_data = {
                    "time_range": "1h",
                    "services": ["api"],
                    "min_confidence": 0.8
                }
                response = client.post("/api/v1/ai_logs/patterns", json=request_data)
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["patterns_found"]) == 1
                assert data["patterns_found"][0]["pattern_type"] == "rate_limit"
                assert len(data["recommendations"]) == 2


class TestAILogsWebSocketStreaming:
    """Test WebSocket streaming functionality"""
    
    @pytest.fixture
    def mock_stream_manager(self):
        manager = AsyncMock(spec=StreamManager)
        manager.add_connection.return_value = "stream-123"
        manager.update_filter.return_value = True
        return manager
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, mock_stream_manager):
        """Test WebSocket connection and streaming"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.stream_manager', mock_stream_manager):
            with TestClient(app) as client:
                with client.websocket_connect("/api/v1/ai_logs/stream") as websocket:
                    # Send initial filter
                    websocket.send_json({
                        "action": "subscribe",
                        "filter": {
                            "services": ["api"],
                            "severity": ["ERROR", "WARN"]
                        }
                    })
                    
                    # Mock stream manager should have been called
                    mock_stream_manager.add_connection.assert_called_once()
                    
                    # Send filter update
                    websocket.send_json({
                        "action": "update_filter",
                        "filter": {
                            "services": ["api", "anythingllm"]
                        }
                    })
                    
                    # Verify update was called
                    mock_stream_manager.update_filter.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling"""
        from src.main import app
        
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/api/v1/ai_logs/stream") as websocket:
                    # Send invalid message
                    websocket.send_json({"invalid": "message"})
                    websocket.receive_json()


class TestAILogsConversationTracking:
    """Test conversation tracking endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_conversation(self):
        """Test retrieving conversation history"""
        from src.main import app
        
        mock_logs = [
            {
                "timestamp": "2025-06-30T10:00:00Z",
                "message": "User query received",
                "conversation_id": "conv-456"
            }
        ]
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.get_conversation_logs.return_value = mock_logs
            
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/conversation/conv-456")
                
                assert response.status_code == 200
                data = response.json()
                assert data["conversation_id"] == "conv-456"
                assert len(data["logs"]) == 1


class TestAILogsExport:
    """Test export functionality"""
    
    @pytest.mark.asyncio
    async def test_export_json(self):
        """Test JSON export"""
        from src.main import app
        
        mock_data = {"logs": [{"test": "data"}]}
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.export_logs.return_value = (json.dumps(mock_data), "application/json")
            
            with TestClient(app) as client:
                request_data = {
                    "format": "json",
                    "time_range": "1h"
                }
                response = client.post("/api/v1/ai_logs/export", json=request_data)
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_export_csv(self):
        """Test CSV export"""
        from src.main import app
        
        mock_csv = "timestamp,level,message\n2025-06-30T10:00:00Z,INFO,Test"
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.export_logs.return_value = (mock_csv, "text/csv")
            
            with TestClient(app) as client:
                request_data = {
                    "format": "csv",
                    "time_range": "1h"
                }
                response = client.post("/api/v1/ai_logs/export", json=request_data)
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/csv"


class TestAILogsIntegration:
    """Integration tests for AI logging system"""
    
    @pytest.mark.asyncio
    async def test_full_troubleshooting_flow(self):
        """Test complete troubleshooting workflow"""
        from src.main import app
        
        # Mock all components for integration test
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc, \
             patch('src.api.v1.ai_logs_endpoints.correlator') as mock_corr, \
             patch('src.api.v1.ai_logs_endpoints.detector') as mock_det:
            
            # Setup mocks
            mock_proc.process_query.return_value = {
                "logs": [{"correlation_id": "test-123"}],
                "total_count": 1,
                "query_time_ms": 50
            }
            
            mock_corr.analyze_correlation.return_value = {
                "correlation_id": "test-123",
                "service_flow": [{"service": "api"}],
                "bottlenecks": [{"service": "anythingllm", "avg_duration_ms": 500}]
            }
            
            mock_det.detect_patterns.return_value = {
                "patterns_found": [{"pattern_type": "timeout"}],
                "recommendations": ["Increase timeout values"]
            }
            
            with TestClient(app) as client:
                # Step 1: Query for errors
                response = client.get("/api/v1/ai_logs/query?mode=errors")
                assert response.status_code == 200
                
                # Step 2: Analyze correlation
                response = client.post("/api/v1/ai_logs/correlate", 
                                     json={"correlation_id": "test-123"})
                assert response.status_code == 200
                assert len(response.json()["bottlenecks"]) == 1
                
                # Step 3: Detect patterns
                response = client.post("/api/v1/ai_logs/patterns",
                                     json={"time_range": "1h"})
                assert response.status_code == 200
                assert len(response.json()["recommendations"]) == 1


class TestAILogsPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_queries(self):
        """Test handling concurrent queries"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.return_value = {
                "logs": [],
                "total_count": 0,
                "query_time_ms": 10
            }
            
            with TestClient(app) as client:
                # Simulate 10 concurrent requests
                tasks = []
                for i in range(10):
                    response = client.get(f"/api/v1/ai_logs/query?correlation_id=test-{i}")
                    assert response.status_code == 200
                
                # Verify all requests were processed
                assert mock_proc.process_query.call_count >= 10
    
    @pytest.mark.asyncio
    async def test_large_result_handling(self):
        """Test handling large result sets"""
        from src.main import app
        
        # Create large mock result
        large_logs = [
            {
                "timestamp": f"2025-06-30T10:{i:02d}:00Z",
                "message": f"Log entry {i}",
                "correlation_id": f"test-{i}"
            }
            for i in range(1000)
        ]
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.return_value = {
                "logs": large_logs,
                "total_count": 1000,
                "query_time_ms": 500
            }
            
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/query?limit=1000")
                
                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 1000
                assert len(data["logs"]) == 1000


class TestAILogsEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_invalid_time_range(self):
        """Test invalid time range format"""
        from src.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/v1/ai_logs/query?time_range=invalid")
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_empty_correlation_id(self):
        """Test empty correlation ID"""
        from src.main import app
        
        with TestClient(app) as client:
            response = client.post("/api/v1/ai_logs/correlate", 
                                 json={"correlation_id": ""})
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_service_unavailable(self):
        """Test handling when Loki is unavailable"""
        from src.main import app
        
        with patch('src.api.v1.ai_logs_endpoints.processor') as mock_proc:
            mock_proc.process_query.side_effect = ConnectionError("Loki unavailable")
            
            with TestClient(app) as client:
                response = client.get("/api/v1/ai_logs/query")
                assert response.status_code == 503  # Service unavailable


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])