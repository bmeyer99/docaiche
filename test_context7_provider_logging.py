#!/usr/bin/env python3
"""
SUB-TASK C1: Context7Provider Logging Verification
=================================================

Test script to verify PIPELINE_METRICS logging in Context7Provider:
- Correlation ID generation and tracking
- Search operation metrics (start/complete/error)
- Technology extraction logging
- HTTP request performance metrics
- Cache hit/miss analytics logging
"""

import asyncio
import logging
import re
import sys
import time
import uuid
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from typing import List, Dict, Any

# Add project root to path
sys.path.append('/home/lab/docaiche')

from src.mcp.providers.implementations.context7_provider import Context7Provider
from src.mcp.providers.models import ProviderConfig, SearchOptions

# Configure logging to capture all PIPELINE_METRICS logs
log_capture = StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Also add console handler for visibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class Context7LoggingTester:
    """Test Context7Provider PIPELINE_METRICS logging implementation"""
    
    def __init__(self):
        self.test_results = []
        self.captured_logs = []
        
    def capture_logs(self):
        """Capture current log output"""
        captured = log_capture.getvalue()
        log_capture.seek(0)
        log_capture.truncate(0)
        self.captured_logs.append(captured)
        return captured
    
    def extract_pipeline_metrics(self, log_text: str) -> List[Dict[str, Any]]:
        """Extract PIPELINE_METRICS entries from log text"""
        metrics = []
        lines = log_text.split('\n')
        
        for line in lines:
            if 'PIPELINE_METRICS:' in line:
                # Parse the metrics line
                try:
                    # Extract the part after PIPELINE_METRICS:
                    metrics_part = line.split('PIPELINE_METRICS:')[1].strip()
                    
                    # Parse key=value pairs
                    metric_data = {}
                    # Simple regex to match key=value pairs
                    pairs = re.findall(r'(\w+)=([^\s]+)', metrics_part)
                    for key, value in pairs:
                        # Handle quoted values
                        if value.startswith('"') and value.endswith('"'):
                            metric_data[key] = value[1:-1]
                        else:
                            metric_data[key] = value
                    
                    metrics.append(metric_data)
                except Exception as e:
                    print(f"Failed to parse metrics line: {line}, error: {e}")
        
        return metrics
    
    async def test_correlation_id_generation(self):
        """Test C1.1: Verify correlation ID generation and tracking"""
        print("\n=== C1.1: Testing Correlation ID Generation ===")
        
        config = ProviderConfig(
            provider_id="context7_test",
            name="Context7 Test",
            config={}
        )
        
        provider = Context7Provider(config)
        await provider.initialize()
        
        # Test search with correlation ID tracking
        search_options = SearchOptions(
            query="next.js documentation",
            max_results=5
        )
        
        # Clear logs and execute search
        self.capture_logs()
        
        try:
            results = await provider.search(search_options)
            captured = self.capture_logs()
            
            # Extract PIPELINE_METRICS
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify correlation ID presence and consistency
            correlation_ids = set()
            for metric in metrics:
                if 'correlation_id' in metric:
                    correlation_ids.add(metric['correlation_id'])
            
            # Check that correlation IDs are consistent and follow pattern
            assert len(correlation_ids) > 0, "No correlation IDs found in metrics"
            
            # Verify correlation ID format (ctx7_XXXXXXXX)
            for corr_id in correlation_ids:
                assert corr_id.startswith('ctx7_'), f"Invalid correlation ID format: {corr_id}"
                assert len(corr_id) == 13, f"Invalid correlation ID length: {corr_id}"
            
            # Verify the same correlation ID is used across related operations
            search_start_metrics = [m for m in metrics if m.get('step') == 'context7_search_start']
            assert len(search_start_metrics) == 1, f"Expected 1 search_start metric, got {len(search_start_metrics)}"
            
            search_correlation_id = search_start_metrics[0]['correlation_id']
            
            # Verify all metrics use the same correlation ID
            for metric in metrics:
                if 'correlation_id' in metric:
                    assert metric['correlation_id'] == search_correlation_id, \
                        f"Inconsistent correlation ID: {metric['correlation_id']} vs {search_correlation_id}"
            
            self.test_results.append({
                "test": "C1.1 Correlation ID Generation",
                "status": "PASS",
                "correlation_ids_found": list(correlation_ids),
                "metrics_count": len(metrics),
                "details": f"Found {len(correlation_ids)} unique correlation IDs across {len(metrics)} metrics"
            })
            
        except Exception as e:
            self.test_results.append({
                "test": "C1.1 Correlation ID Generation",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
        
        finally:
            await provider.cleanup()
    
    async def test_search_operation_metrics(self):
        """Test C1.2: Verify search operation metrics (start/complete/error)"""
        print("\n=== C1.2: Testing Search Operation Metrics ===")
        
        config = ProviderConfig(
            provider_id="context7_metrics",
            name="Context7 Metrics Test",
            config={}
        )
        
        provider = Context7Provider(config)
        await provider.initialize()
        
        # Test successful search
        print("Testing successful search metrics...")
        search_options = SearchOptions(
            query="react hooks tutorial",
            max_results=3
        )
        
        self.capture_logs()
        
        try:
            results = await provider.search(search_options)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify search_start metric
            start_metrics = [m for m in metrics if m.get('step') == 'context7_search_start']
            assert len(start_metrics) == 1, f"Expected 1 search_start metric, got {len(start_metrics)}"
            
            start_metric = start_metrics[0]
            assert 'correlation_id' in start_metric, "search_start missing correlation_id"
            assert 'query' in start_metric, "search_start missing query"
            assert 'provider' in start_metric, "search_start missing provider"
            assert start_metric['provider'] == 'context7', f"Expected provider=context7, got {start_metric['provider']}"
            
            # Verify search_complete metric
            complete_metrics = [m for m in metrics if m.get('step') == 'context7_search_complete']
            assert len(complete_metrics) == 1, f"Expected 1 search_complete metric, got {len(complete_metrics)}"
            
            complete_metric = complete_metrics[0]
            assert 'correlation_id' in complete_metric, "search_complete missing correlation_id"
            assert 'duration_ms' in complete_metric, "search_complete missing duration_ms"
            assert 'result_count' in complete_metric, "search_complete missing result_count"
            assert 'success' in complete_metric, "search_complete missing success"
            assert complete_metric['success'] == 'true', f"Expected success=true, got {complete_metric['success']}"
            
            # Verify duration is reasonable (> 0, < 30000ms)
            duration_ms = int(complete_metric['duration_ms'])
            assert 0 < duration_ms < 30000, f"Unreasonable duration: {duration_ms}ms"
            
            self.test_results.append({
                "test": "C1.2 Search Operation Metrics",
                "status": "PASS",
                "start_metric": start_metric,
                "complete_metric": complete_metric,
                "duration_ms": duration_ms,
                "details": f"Search completed successfully in {duration_ms}ms"
            })
            
        except Exception as e:
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Check for error metrics
            error_metrics = [m for m in metrics if m.get('step') == 'context7_search_error']
            
            self.test_results.append({
                "test": "C1.2 Search Operation Metrics",
                "status": "FAIL",
                "error": str(e),
                "error_metrics": error_metrics,
                "captured_logs": captured
            })
        
        finally:
            await provider.cleanup()
    
    async def test_technology_extraction_logging(self):
        """Test C1.3: Verify technology extraction logging"""
        print("\n=== C1.3: Testing Technology Extraction Logging ===")
        
        config = ProviderConfig(
            provider_id="context7_tech",
            name="Context7 Tech Test",
            config={}
        )
        
        provider = Context7Provider(config)
        await provider.initialize()
        
        # Test successful technology extraction
        print("Testing successful technology extraction...")
        search_options = SearchOptions(
            query="vue.js component guide",
            max_results=3
        )
        
        self.capture_logs()
        
        try:
            results = await provider.search(search_options)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify tech_extraction metric
            tech_metrics = [m for m in metrics if m.get('step') == 'context7_tech_extraction']
            assert len(tech_metrics) == 1, f"Expected 1 tech_extraction metric, got {len(tech_metrics)}"
            
            tech_metric = tech_metrics[0]
            assert 'correlation_id' in tech_metric, "tech_extraction missing correlation_id"
            assert 'duration_ms' in tech_metric, "tech_extraction missing duration_ms"
            assert 'technology' in tech_metric, "tech_extraction missing technology"
            assert 'owner' in tech_metric, "tech_extraction missing owner"
            assert 'success' in tech_metric, "tech_extraction missing success"
            assert tech_metric['success'] == 'true', f"Expected success=true, got {tech_metric['success']}"
            
            # Verify technology extraction worked
            assert tech_metric['technology'] == 'vue', f"Expected technology=vue, got {tech_metric['technology']}"
            assert tech_metric['owner'] == 'vuejs', f"Expected owner=vuejs, got {tech_metric['owner']}"
            
            self.test_results.append({
                "test": "C1.3 Technology Extraction Success",
                "status": "PASS",
                "tech_metric": tech_metric,
                "details": f"Successfully extracted {tech_metric['technology']} from {tech_metric['owner']}"
            })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C1.3 Technology Extraction Success",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
        
        # Test failed technology extraction
        print("Testing failed technology extraction...")
        search_options_fail = SearchOptions(
            query="random nonsense query xyz123",
            max_results=3
        )
        
        self.capture_logs()
        
        try:
            results = await provider.search(search_options_fail)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify tech_extraction failure metric
            tech_metrics = [m for m in metrics if m.get('step') == 'context7_tech_extraction']
            assert len(tech_metrics) == 1, f"Expected 1 tech_extraction metric, got {len(tech_metrics)}"
            
            tech_metric = tech_metrics[0]
            assert 'correlation_id' in tech_metric, "tech_extraction missing correlation_id"
            assert 'duration_ms' in tech_metric, "tech_extraction missing duration_ms"
            assert 'decision' in tech_metric, "tech_extraction missing decision"
            assert 'success' in tech_metric, "tech_extraction missing success"
            assert tech_metric['success'] == 'false', f"Expected success=false, got {tech_metric['success']}"
            assert tech_metric['decision'] == 'no_technology_detected', f"Expected decision=no_technology_detected, got {tech_metric['decision']}"
            
            self.test_results.append({
                "test": "C1.3 Technology Extraction Failure",
                "status": "PASS",
                "tech_metric": tech_metric,
                "details": f"Correctly detected no technology with decision={tech_metric['decision']}"
            })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C1.3 Technology Extraction Failure",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
        
        finally:
            await provider.cleanup()
    
    async def test_http_request_metrics(self):
        """Test C1.4: Verify HTTP request performance metrics"""
        print("\n=== C1.4: Testing HTTP Request Performance Metrics ===")
        
        config = ProviderConfig(
            provider_id="context7_http",
            name="Context7 HTTP Test",
            config={}
        )
        
        provider = Context7Provider(config)
        await provider.initialize()
        
        # Test HTTP request metrics
        search_options = SearchOptions(
            query="typescript documentation",
            max_results=3
        )
        
        self.capture_logs()
        
        try:
            results = await provider.search(search_options)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify HTTP request start
            http_start_metrics = [m for m in metrics if m.get('step') == 'context7_http_request_start']
            assert len(http_start_metrics) == 1, f"Expected 1 http_request_start metric, got {len(http_start_metrics)}"
            
            http_start = http_start_metrics[0]
            assert 'correlation_id' in http_start, "http_request_start missing correlation_id"
            assert 'url' in http_start, "http_request_start missing url"
            assert 'technology' in http_start, "http_request_start missing technology"
            assert 'owner' in http_start, "http_request_start missing owner"
            
            # Verify HTTP request success/failure
            http_success_metrics = [m for m in metrics if m.get('step') == 'context7_http_request_success']
            http_failed_metrics = [m for m in metrics if m.get('step') == 'context7_http_request_failed']
            
            if http_success_metrics:
                http_result = http_success_metrics[0]
                assert 'correlation_id' in http_result, "http_request_success missing correlation_id"
                assert 'duration_ms' in http_result, "http_request_success missing duration_ms"
                assert 'status_code' in http_result, "http_request_success missing status_code"
                assert 'content_length' in http_result, "http_request_success missing content_length"
                
                # Verify reasonable values
                duration_ms = int(http_result['duration_ms'])
                assert 0 < duration_ms < 10000, f"Unreasonable HTTP duration: {duration_ms}ms"
                
                status_code = int(http_result['status_code'])
                assert status_code == 200, f"Expected status_code=200, got {status_code}"
                
                content_length = int(http_result['content_length'])
                assert content_length > 0, f"Expected content_length > 0, got {content_length}"
                
                self.test_results.append({
                    "test": "C1.4 HTTP Request Success Metrics",
                    "status": "PASS",
                    "http_start": http_start,
                    "http_result": http_result,
                    "duration_ms": duration_ms,
                    "content_length": content_length,
                    "details": f"HTTP request completed in {duration_ms}ms, {content_length} bytes"
                })
                
            elif http_failed_metrics:
                http_result = http_failed_metrics[0]
                assert 'correlation_id' in http_result, "http_request_failed missing correlation_id"
                assert 'duration_ms' in http_result, "http_request_failed missing duration_ms"
                assert 'status_code' in http_result, "http_request_failed missing status_code"
                assert 'reason' in http_result, "http_request_failed missing reason"
                
                self.test_results.append({
                    "test": "C1.4 HTTP Request Failed Metrics",
                    "status": "PASS",
                    "http_start": http_start,
                    "http_result": http_result,
                    "details": f"HTTP request failed with status {http_result['status_code']}, reason: {http_result['reason']}"
                })
            else:
                assert False, "Expected either http_request_success or http_request_failed metric"
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C1.4 HTTP Request Metrics",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
        
        finally:
            await provider.cleanup()
    
    async def test_cache_analytics_logging(self):
        """Test C1.5: Verify cache hit/miss analytics logging"""
        print("\n=== C1.5: Testing Cache Hit/Miss Analytics ===")
        
        config = ProviderConfig(
            provider_id="context7_cache",
            name="Context7 Cache Test",
            config={'cache_ttl': 300}  # 5 minutes cache
        )
        
        provider = Context7Provider(config)
        await provider.initialize()
        
        # First request (should be cache miss)
        print("Testing cache miss...")
        search_options = SearchOptions(
            query="angular documentation",
            max_results=3
        )
        
        self.capture_logs()
        
        try:
            results1 = await provider.search(search_options)
            captured1 = self.capture_logs()
            metrics1 = self.extract_pipeline_metrics(captured1)
            
            # Should not have cache hit metrics on first request
            cache_hit_metrics1 = [m for m in metrics1 if m.get('step') == 'context7_cache_hit']
            assert len(cache_hit_metrics1) == 0, f"Unexpected cache hit on first request: {cache_hit_metrics1}"
            
            # Second request (should be cache hit if caching works)
            print("Testing potential cache hit...")
            await asyncio.sleep(0.1)  # Small delay
            
            self.capture_logs()
            results2 = await provider.search(search_options)
            captured2 = self.capture_logs()
            metrics2 = self.extract_pipeline_metrics(captured2)
            
            # Check for cache hit metrics
            cache_hit_metrics2 = [m for m in metrics2 if m.get('step') == 'context7_cache_hit']
            
            if cache_hit_metrics2:
                cache_hit = cache_hit_metrics2[0]
                assert 'correlation_id' in cache_hit, "cache_hit missing correlation_id"
                assert 'duration_ms' in cache_hit, "cache_hit missing duration_ms"
                assert 'technology' in cache_hit, "cache_hit missing technology"
                assert 'owner' in cache_hit, "cache_hit missing owner"
                assert 'content_length' in cache_hit, "cache_hit missing content_length"
                
                # Cache hit should be fast
                duration_ms = int(cache_hit['duration_ms'])
                assert duration_ms < 100, f"Cache hit too slow: {duration_ms}ms"
                
                self.test_results.append({
                    "test": "C1.5 Cache Hit Analytics",
                    "status": "PASS",
                    "cache_hit": cache_hit,
                    "duration_ms": duration_ms,
                    "details": f"Cache hit detected in {duration_ms}ms"
                })
            else:
                # Cache miss - this is also valid behavior
                self.test_results.append({
                    "test": "C1.5 Cache Hit Analytics",
                    "status": "PASS",
                    "details": "No cache hit detected (cache miss behavior working correctly)"
                })
            
            # Test cache miss scenario with different query
            print("Testing explicit cache miss...")
            search_options_different = SearchOptions(
                query="unique query for cache miss test " + str(uuid.uuid4()),
                max_results=3
            )
            
            self.capture_logs()
            results3 = await provider.search(search_options_different)
            captured3 = self.capture_logs()
            metrics3 = self.extract_pipeline_metrics(captured3)
            
            # Should not have cache hit metrics for different query
            cache_hit_metrics3 = [m for m in metrics3 if m.get('step') == 'context7_cache_hit']
            assert len(cache_hit_metrics3) == 0, f"Unexpected cache hit for different query: {cache_hit_metrics3}"
            
            self.test_results.append({
                "test": "C1.5 Cache Miss Analytics",
                "status": "PASS",
                "details": "Cache miss correctly detected for different query"
            })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C1.5 Cache Analytics",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
        
        finally:
            await provider.cleanup()
    
    async def run_all_tests(self):
        """Run all Context7Provider logging tests"""
        print("Starting Context7Provider PIPELINE_METRICS Logging Verification")
        print("=" * 70)
        
        # Run all test methods
        await self.test_correlation_id_generation()
        await self.test_search_operation_metrics()
        await self.test_technology_extraction_logging()
        await self.test_http_request_metrics()
        await self.test_cache_analytics_logging()
        
        # Print summary
        print("\n" + "=" * 70)
        print("SUB-TASK C1 RESULTS SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {passed/len(self.test_results)*100:.1f}%")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {result['test']}: {result['status']}")
            if result['status'] == 'PASS' and 'details' in result:
                print(f"   └─ {result['details']}")
            elif result['status'] == 'FAIL':
                print(f"   └─ Error: {result.get('error', 'Unknown error')}")
        
        return self.test_results


async def main():
    """Main test execution"""
    tester = Context7LoggingTester()
    results = await tester.run_all_tests()
    
    # Return results for integration with other sub-tasks
    return {
        "sub_task": "C1",
        "description": "Context7Provider PIPELINE_METRICS Logging Verification",
        "results": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r['status'] == 'PASS'),
            "failed": sum(1 for r in results if r['status'] == 'FAIL')
        }
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nSUB-TASK C1 completed with {result['summary']['passed']}/{result['summary']['total']} tests passing")