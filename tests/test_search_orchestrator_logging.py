#!/usr/bin/env python3
"""
SUB-TASK C2: SearchOrchestrator Context7 Metrics Verification
===========================================================

Test script to verify PIPELINE_METRICS logging in SearchOrchestrator for Context7:
- External search decision logging
- Context7-specific pipeline metrics
- Correlation ID propagation
- Query generation and optimization tracking
- Result conversion and aggregation metrics
"""

import asyncio
import logging
import re
import sys
import time
import uuid
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
sys.path.append('/home/lab/docaiche')

from src.search.orchestrator import SearchOrchestrator
from src.search.models import SearchQuery, SearchResults
from src.database.connection import DatabaseManager, CacheManager
from src.clients.weaviate_client import WeaviateVectorClient

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


class SearchOrchestratorLoggingTester:
    """Test SearchOrchestrator PIPELINE_METRICS logging for Context7"""
    
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
                try:
                    # Extract the part after PIPELINE_METRICS:
                    metrics_part = line.split('PIPELINE_METRICS:')[1].strip()
                    
                    # Parse key=value pairs, handling quoted values
                    metric_data = {}
                    in_quotes = False
                    current_key = None
                    current_value = ""
                    tokens = re.findall(r'(\w+)=("[^"]*"|\S+)', metrics_part)
                    
                    for key, value in tokens:
                        # Handle quoted values
                        if value.startswith('"') and value.endswith('"'):
                            metric_data[key] = value[1:-1]
                        else:
                            metric_data[key] = value
                    
                    metrics.append(metric_data)
                except Exception as e:
                    print(f"Failed to parse metrics line: {line}, error: {e}")
        
        return metrics
    
    def create_mock_orchestrator(self):
        """Create a mock SearchOrchestrator with necessary dependencies"""
        # Mock dependencies
        db_manager = Mock(spec=DatabaseManager)
        cache_manager = Mock(spec=CacheManager)
        weaviate_client = Mock(spec=WeaviateVectorClient)
        llm_client = Mock()
        
        # Create orchestrator
        orchestrator = SearchOrchestrator(
            db_manager=db_manager,
            cache_manager=cache_manager,
            weaviate_client=weaviate_client,
            llm_client=llm_client
        )
        
        # Mock the workspace strategy
        orchestrator.workspace_strategy._get_available_workspaces = AsyncMock(return_value=[])
        orchestrator.workspace_strategy.identify_relevant_workspaces = AsyncMock(return_value=[])
        orchestrator.workspace_strategy.execute_parallel_search = AsyncMock(return_value=[])
        
        # Mock the result ranker
        orchestrator.result_ranker.rank_results = AsyncMock(return_value=[])
        
        # Mock the search cache
        orchestrator.search_cache.get_cached_results = AsyncMock(return_value=None)
        orchestrator.search_cache.cache_results = AsyncMock()
        
        return orchestrator
    
    async def test_external_search_decision_logging(self):
        """Test C2.1: Verify external search decision logging"""
        print("\n=== C2.1: Testing External Search Decision Logging ===")
        
        orchestrator = self.create_mock_orchestrator()
        
        # Test explicit external search request
        print("Testing explicit external search decision...")
        
        query = SearchQuery(
            query="react hooks guide",
            use_external_search=True
        )
        
        self.capture_logs()
        
        try:
            results, _ = await orchestrator.execute_search(query)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify external search decision metric
            decision_metrics = [m for m in metrics if m.get('step') == 'external_search_decision']
            assert len(decision_metrics) >= 1, f"Expected external_search_decision metric, got {len(decision_metrics)}"
            
            decision_metric = decision_metrics[0]
            assert 'trace_id' in decision_metric, "external_search_decision missing trace_id"
            assert 'decision' in decision_metric, "external_search_decision missing decision"
            assert decision_metric['decision'] == 'explicit_true', f"Expected decision=explicit_true, got {decision_metric['decision']}"
            
            self.test_results.append({
                "test": "C2.1 External Search Decision - Explicit True",
                "status": "PASS",
                "decision_metric": decision_metric,
                "details": f"Correctly logged explicit external search decision: {decision_metric['decision']}"
            })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C2.1 External Search Decision - Explicit True",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
        
        # Test explicit external search disabled
        print("Testing explicit external search disabled...")
        
        query_disabled = SearchQuery(
            query="vue.js documentation",
            use_external_search=False
        )
        
        self.capture_logs()
        
        try:
            results, _ = await orchestrator.execute_search(query_disabled)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify external search decision metric
            decision_metrics = [m for m in metrics if m.get('step') == 'external_search_decision']
            assert len(decision_metrics) >= 1, f"Expected external_search_decision metric, got {len(decision_metrics)}"
            
            decision_metric = decision_metrics[0]
            assert decision_metric['decision'] == 'explicit_false', f"Expected decision=explicit_false, got {decision_metric['decision']}"
            
            self.test_results.append({
                "test": "C2.1 External Search Decision - Explicit False",
                "status": "PASS",
                "decision_metric": decision_metric,
                "details": f"Correctly logged disabled external search decision: {decision_metric['decision']}"
            })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C2.1 External Search Decision - Explicit False",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
    
    async def test_context7_pipeline_metrics(self):
        """Test C2.2: Verify Context7-specific pipeline metrics"""
        print("\n=== C2.2: Testing Context7-Specific Pipeline Metrics ===")
        
        orchestrator = self.create_mock_orchestrator()
        
        # Mock MCP enhancer for Context7 testing
        mock_mcp_enhancer = Mock()
        mock_mcp_enhancer.is_external_search_available = Mock(return_value=True)
        mock_mcp_enhancer.get_external_search_query = AsyncMock(return_value="optimized react hooks query")
        mock_mcp_enhancer.execute_external_search = AsyncMock(return_value=[
            {
                'title': 'React Hooks Guide',
                'snippet': 'Comprehensive guide to React hooks',
                'url': 'https://context7.com/facebook/react/hooks',
                'provider': 'context7',
                'content_type': 'documentation'
            }
        ])
        orchestrator.mcp_enhancer = mock_mcp_enhancer
        
        query = SearchQuery(
            query="react hooks tutorial",
            technology_hint="react",
            use_external_search=True
        )
        
        self.capture_logs()
        
        try:
            results, _ = await orchestrator.execute_search(query)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify Context7 external search start
            external_start_metrics = [m for m in metrics if m.get('step') == 'context7_external_search_start']
            if external_start_metrics:
                start_metric = external_start_metrics[0]
                assert 'trace_id' in start_metric, "context7_external_search_start missing trace_id"
                assert 'correlation_id' in start_metric, "context7_external_search_start missing correlation_id"
                assert 'query' in start_metric, "context7_external_search_start missing query"
                assert 'technology_hint' in start_metric, "context7_external_search_start missing technology_hint"
                
                self.test_results.append({
                    "test": "C2.2 Context7 External Search Start",
                    "status": "PASS",
                    "start_metric": start_metric,
                    "details": f"Context7 external search started with correlation_id: {start_metric.get('correlation_id')}"
                })
            else:
                self.test_results.append({
                    "test": "C2.2 Context7 External Search Start",
                    "status": "FAIL",
                    "error": "No context7_external_search_start metric found"
                })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C2.2 Context7 Pipeline Metrics",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
    
    async def test_correlation_id_propagation(self):
        """Test C2.3: Verify correlation ID propagation across operations"""
        print("\n=== C2.3: Testing Correlation ID Propagation ===")
        
        orchestrator = self.create_mock_orchestrator()
        
        query = SearchQuery(
            query="typescript documentation",
            technology_hint="typescript"
        )
        
        self.capture_logs()
        
        try:
            results, _ = await orchestrator.execute_search(query)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Extract trace_id from first metric
            trace_ids = set()
            correlation_ids = set()
            
            for metric in metrics:
                if 'trace_id' in metric:
                    trace_ids.add(metric['trace_id'])
                if 'correlation_id' in metric:
                    correlation_ids.add(metric['correlation_id'])
            
            # Verify consistent trace_id across all operations
            assert len(trace_ids) <= 1, f"Inconsistent trace_ids found: {trace_ids}"
            
            if trace_ids:
                trace_id = list(trace_ids)[0]
                
                # Verify trace_id format
                assert trace_id.startswith('search_'), f"Invalid trace_id format: {trace_id}"
                
                # Verify all metrics with trace_id use the same one
                for metric in metrics:
                    if 'trace_id' in metric:
                        assert metric['trace_id'] == trace_id, \
                            f"Inconsistent trace_id: {metric['trace_id']} vs {trace_id}"
                
                self.test_results.append({
                    "test": "C2.3 Trace ID Propagation",
                    "status": "PASS",
                    "trace_id": trace_id,
                    "metrics_with_trace_id": len([m for m in metrics if 'trace_id' in m]),
                    "details": f"Consistent trace_id {trace_id} across {len([m for m in metrics if 'trace_id' in m])} metrics"
                })
            else:
                self.test_results.append({
                    "test": "C2.3 Trace ID Propagation",
                    "status": "FAIL",
                    "error": "No trace_id found in metrics"
                })
            
            # Check for correlation ID consistency within Context7 operations
            if correlation_ids:
                self.test_results.append({
                    "test": "C2.3 Correlation ID Propagation", 
                    "status": "PASS",
                    "correlation_ids": list(correlation_ids),
                    "details": f"Found {len(correlation_ids)} correlation IDs in metrics"
                })
            else:
                self.test_results.append({
                    "test": "C2.3 Correlation ID Propagation",
                    "status": "PASS",
                    "details": "No correlation IDs found (expected when Context7 not used)"
                })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C2.3 ID Propagation",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
    
    async def test_query_generation_tracking(self):
        """Test C2.4: Verify query generation and optimization tracking"""
        print("\n=== C2.4: Testing Query Generation and Optimization Tracking ===")
        
        orchestrator = self.create_mock_orchestrator()
        
        # Mock MCP enhancer with query generation
        mock_mcp_enhancer = Mock()
        mock_mcp_enhancer.is_external_search_available = Mock(return_value=True)
        mock_mcp_enhancer.get_external_search_query = AsyncMock(return_value="optimized next.js documentation guide")
        mock_mcp_enhancer.execute_external_search = AsyncMock(return_value=[])
        orchestrator.mcp_enhancer = mock_mcp_enhancer
        
        query = SearchQuery(
            query="next.js guide",
            technology_hint="next.js",
            use_external_search=True
        )
        
        self.capture_logs()
        
        try:
            results, _ = await orchestrator.execute_search(query)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify query generation metrics
            query_gen_metrics = [m for m in metrics if m.get('step') == 'context7_query_generation']
            if query_gen_metrics:
                gen_metric = query_gen_metrics[0]
                assert 'duration_ms' in gen_metric, "context7_query_generation missing duration_ms"
                assert 'trace_id' in gen_metric, "context7_query_generation missing trace_id"
                assert 'correlation_id' in gen_metric, "context7_query_generation missing correlation_id"
                assert 'original_query' in gen_metric, "context7_query_generation missing original_query"
                assert 'generated_query' in gen_metric, "context7_query_generation missing generated_query"
                
                # Verify reasonable duration
                duration_ms = int(gen_metric['duration_ms'])
                assert 0 <= duration_ms < 5000, f"Unreasonable query generation duration: {duration_ms}ms"
                
                self.test_results.append({
                    "test": "C2.4 Query Generation Tracking",
                    "status": "PASS",
                    "gen_metric": gen_metric,
                    "duration_ms": duration_ms,
                    "details": f"Query generation tracked in {duration_ms}ms"
                })
            else:
                self.test_results.append({
                    "test": "C2.4 Query Generation Tracking",
                    "status": "FAIL",
                    "error": "No context7_query_generation metric found"
                })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C2.4 Query Generation Tracking",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
    
    async def test_result_conversion_metrics(self):
        """Test C2.5: Verify result conversion and aggregation metrics"""
        print("\n=== C2.5: Testing Result Conversion and Aggregation Metrics ===")
        
        orchestrator = self.create_mock_orchestrator()
        
        # Mock MCP enhancer with external results
        mock_external_results = [
            {
                'title': 'Vue.js Guide',
                'snippet': 'Complete Vue.js guide',
                'url': 'https://context7.com/vuejs/vue/guide',
                'provider': 'context7',
                'content_type': 'documentation'
            },
            {
                'title': 'Vue.js API Reference',
                'snippet': 'Vue.js API documentation',
                'url': 'https://context7.com/vuejs/vue/api',
                'provider': 'context7',
                'content_type': 'api'
            }
        ]
        
        mock_mcp_enhancer = Mock()
        mock_mcp_enhancer.is_external_search_available = Mock(return_value=True)
        mock_mcp_enhancer.get_external_search_query = AsyncMock(return_value="vue.js documentation")
        mock_mcp_enhancer.execute_external_search = AsyncMock(return_value=mock_external_results)
        orchestrator.mcp_enhancer = mock_mcp_enhancer
        
        query = SearchQuery(
            query="vue documentation",
            technology_hint="vue",
            use_external_search=True
        )
        
        self.capture_logs()
        
        try:
            results, _ = await orchestrator.execute_search(query)
            captured = self.capture_logs()
            metrics = self.extract_pipeline_metrics(captured)
            
            # Verify provider execution metrics
            provider_exec_metrics = [m for m in metrics if m.get('step') == 'context7_provider_execution']
            if provider_exec_metrics:
                exec_metric = provider_exec_metrics[0]
                assert 'duration_ms' in exec_metric, "context7_provider_execution missing duration_ms"
                assert 'trace_id' in exec_metric, "context7_provider_execution missing trace_id"
                assert 'correlation_id' in exec_metric, "context7_provider_execution missing correlation_id"
                assert 'result_count' in exec_metric, "context7_provider_execution missing result_count"
                
                result_count = int(exec_metric['result_count'])
                assert result_count == len(mock_external_results), \
                    f"Expected result_count={len(mock_external_results)}, got {result_count}"
                
                self.test_results.append({
                    "test": "C2.5 Provider Execution Metrics",
                    "status": "PASS",
                    "exec_metric": exec_metric,
                    "result_count": result_count,
                    "details": f"Provider execution returned {result_count} results"
                })
            else:
                self.test_results.append({
                    "test": "C2.5 Provider Execution Metrics",
                    "status": "FAIL",
                    "error": "No context7_provider_execution metric found"
                })
            
            # Verify result conversion metrics
            conversion_metrics = [m for m in metrics if m.get('step') == 'context7_result_conversion']
            if conversion_metrics:
                conv_metric = conversion_metrics[0]
                assert 'trace_id' in conv_metric, "context7_result_conversion missing trace_id"
                assert 'correlation_id' in conv_metric, "context7_result_conversion missing correlation_id"
                assert 'converted_count' in conv_metric, "context7_result_conversion missing converted_count"
                assert 'original_count' in conv_metric, "context7_result_conversion missing original_count"
                
                converted_count = int(conv_metric['converted_count'])
                original_count = int(conv_metric['original_count'])
                
                assert converted_count <= original_count, \
                    f"Converted count ({converted_count}) > original count ({original_count})"
                
                self.test_results.append({
                    "test": "C2.5 Result Conversion Metrics",
                    "status": "PASS",
                    "conv_metric": conv_metric,
                    "converted_count": converted_count,
                    "original_count": original_count,
                    "details": f"Converted {converted_count}/{original_count} results"
                })
            else:
                self.test_results.append({
                    "test": "C2.5 Result Conversion Metrics",
                    "status": "FAIL",
                    "error": "No context7_result_conversion metric found"
                })
            
        except Exception as e:
            captured = self.capture_logs()
            self.test_results.append({
                "test": "C2.5 Result Conversion Metrics",
                "status": "FAIL",
                "error": str(e),
                "captured_logs": captured
            })
    
    async def run_all_tests(self):
        """Run all SearchOrchestrator Context7 logging tests"""
        print("Starting SearchOrchestrator Context7 PIPELINE_METRICS Logging Verification")
        print("=" * 80)
        
        # Run all test methods
        await self.test_external_search_decision_logging()
        await self.test_context7_pipeline_metrics()
        await self.test_correlation_id_propagation()
        await self.test_query_generation_tracking()
        await self.test_result_conversion_metrics()
        
        # Print summary
        print("\n" + "=" * 80)
        print("SUB-TASK C2 RESULTS SUMMARY")
        print("=" * 80)
        
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
    tester = SearchOrchestratorLoggingTester()
    results = await tester.run_all_tests()
    
    # Return results for integration with other sub-tasks
    return {
        "sub_task": "C2",
        "description": "SearchOrchestrator Context7 PIPELINE_METRICS Logging Verification", 
        "results": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r['status'] == 'PASS'),
            "failed": sum(1 for r in results if r['status'] == 'FAIL')
        }
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nSUB-TASK C2 completed with {result['summary']['passed']}/{result['summary']['total']} tests passing")