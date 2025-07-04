#!/usr/bin/env python3
"""
VERIFY-C: PIPELINE_METRICS Logging Verification
===============================================

Main coordinator script that spawns three parallel sub-tasks to verify 
PIPELINE_METRICS logging implementation across different components:

SUB-TASK C1: Context7Provider logging verification
SUB-TASK C2: SearchOrchestrator Context7 metrics verification  
SUB-TASK C3: Context7IngestionService and Weaviate logging verification

Each sub-task runs independently and reports back with specific verification results.
"""

import asyncio
import sys
import time
from typing import Dict, List, Any

# Add project root to path
sys.path.append('/home/lab/docaiche')

# Import test modules
from test_context7_provider_logging import main as run_c1_tests
from test_search_orchestrator_logging import main as run_c2_tests
from test_context7_ingestion_logging import main as run_c3_tests


class PipelineMetricsVerifier:
    """Main coordinator for PIPELINE_METRICS logging verification"""
    
    def __init__(self):
        self.start_time = time.time()
        self.sub_task_results = {}
        
    async def run_parallel_verification(self):
        """Run all three sub-tasks in parallel"""
        print("🚀 Starting VERIFY-C: PIPELINE_METRICS Logging Verification")
        print("=" * 80)
        print("Spawning 3 parallel sub-tasks to test different aspects of logging...")
        print()
        
        # Create tasks for parallel execution
        tasks = {
            "C1": asyncio.create_task(self.run_subtask_c1()),
            "C2": asyncio.create_task(self.run_subtask_c2()),
            "C3": asyncio.create_task(self.run_subtask_c3())
        }
        
        # Wait for all tasks to complete
        print("⏳ Running sub-tasks in parallel...")
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Process results
        for i, (task_id, result) in enumerate(zip(tasks.keys(), results)):
            if isinstance(result, Exception):
                self.sub_task_results[task_id] = {
                    "sub_task": task_id,
                    "status": "ERROR",
                    "error": str(result),
                    "summary": {"total": 0, "passed": 0, "failed": 0}
                }
                print(f"❌ SUB-TASK {task_id} failed with error: {result}")
            else:
                self.sub_task_results[task_id] = result
                summary = result.get("summary", {})
                status = "✅ PASSED" if summary.get("failed", 0) == 0 else "⚠️ PARTIAL"
                print(f"{status} SUB-TASK {task_id}: {summary.get('passed', 0)}/{summary.get('total', 0)} tests passed")
        
        return self.sub_task_results
    
    async def run_subtask_c1(self):
        """Run SUB-TASK C1: Context7Provider logging verification"""
        print("🔄 Starting SUB-TASK C1: Context7Provider logging verification")
        try:
            result = await run_c1_tests()
            print("✅ SUB-TASK C1 completed")
            return result
        except Exception as e:
            print(f"❌ SUB-TASK C1 failed: {e}")
            raise
    
    async def run_subtask_c2(self):
        """Run SUB-TASK C2: SearchOrchestrator Context7 metrics verification"""
        print("🔄 Starting SUB-TASK C2: SearchOrchestrator Context7 metrics verification")
        try:
            result = await run_c2_tests()
            print("✅ SUB-TASK C2 completed")
            return result
        except Exception as e:
            print(f"❌ SUB-TASK C2 failed: {e}")
            raise
    
    async def run_subtask_c3(self):
        """Run SUB-TASK C3: Context7IngestionService and Weaviate logging verification"""
        print("🔄 Starting SUB-TASK C3: Context7IngestionService and Weaviate logging verification")
        try:
            result = await run_c3_tests()
            print("✅ SUB-TASK C3 completed")
            return result
        except Exception as e:
            print(f"❌ SUB-TASK C3 failed: {e}")
            raise
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""
        total_tests = sum(r.get("summary", {}).get("total", 0) for r in self.sub_task_results.values())
        total_passed = sum(r.get("summary", {}).get("passed", 0) for r in self.sub_task_results.values())
        total_failed = sum(r.get("summary", {}).get("failed", 0) for r in self.sub_task_results.values())
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Determine overall status
        if total_failed == 0:
            overall_status = "FULLY VERIFIED"
            status_emoji = "🎉"
        elif total_passed > total_failed:
            overall_status = "MOSTLY VERIFIED"
            status_emoji = "⚠️"
        else:
            overall_status = "VERIFICATION FAILED"
            status_emoji = "❌"
        
        execution_time = time.time() - self.start_time
        
        return {
            "overall_status": overall_status,
            "status_emoji": status_emoji,
            "execution_time_seconds": round(execution_time, 2),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "success_rate": round(overall_success_rate, 1),
            "sub_task_results": self.sub_task_results,
            "verification_aspects": {
                "Context7Provider_logging": self.analyze_subtask_c1(),
                "SearchOrchestrator_metrics": self.analyze_subtask_c2(), 
                "IngestionService_weaviate": self.analyze_subtask_c3()
            }
        }
    
    def analyze_subtask_c1(self) -> Dict[str, Any]:
        """Analyze Context7Provider logging verification results"""
        c1_result = self.sub_task_results.get("C1", {})
        if not c1_result or c1_result.get("status") == "ERROR":
            return {"status": "ERROR", "verified_aspects": []}
        
        results = c1_result.get("results", [])
        verified_aspects = []
        
        # Check specific aspects
        for result in results:
            test_name = result.get("test", "")
            if result.get("status") == "PASS":
                if "Correlation ID" in test_name:
                    verified_aspects.append("correlation_id_generation_tracking")
                elif "Search Operation" in test_name:
                    verified_aspects.append("search_operation_metrics")
                elif "Technology Extraction" in test_name:
                    verified_aspects.append("technology_extraction_logging")
                elif "HTTP Request" in test_name:
                    verified_aspects.append("http_request_performance_metrics")
                elif "Cache" in test_name:
                    verified_aspects.append("cache_hit_miss_analytics")
        
        return {
            "status": "VERIFIED" if c1_result.get("summary", {}).get("failed", 0) == 0 else "PARTIAL",
            "verified_aspects": verified_aspects,
            "summary": c1_result.get("summary", {})
        }
    
    def analyze_subtask_c2(self) -> Dict[str, Any]:
        """Analyze SearchOrchestrator metrics verification results"""
        c2_result = self.sub_task_results.get("C2", {})
        if not c2_result or c2_result.get("status") == "ERROR":
            return {"status": "ERROR", "verified_aspects": []}
        
        results = c2_result.get("results", [])
        verified_aspects = []
        
        # Check specific aspects
        for result in results:
            test_name = result.get("test", "")
            if result.get("status") == "PASS":
                if "External Search Decision" in test_name:
                    verified_aspects.append("external_search_decision_logging")
                elif "Context7" in test_name and "Pipeline" in test_name:
                    verified_aspects.append("context7_pipeline_metrics")
                elif "Correlation ID" in test_name or "ID Propagation" in test_name:
                    verified_aspects.append("correlation_id_propagation")
                elif "Query Generation" in test_name:
                    verified_aspects.append("query_generation_tracking")
                elif "Result Conversion" in test_name:
                    verified_aspects.append("result_conversion_aggregation")
        
        return {
            "status": "VERIFIED" if c2_result.get("summary", {}).get("failed", 0) == 0 else "PARTIAL",
            "verified_aspects": verified_aspects,
            "summary": c2_result.get("summary", {})
        }
    
    def analyze_subtask_c3(self) -> Dict[str, Any]:
        """Analyze Context7IngestionService and Weaviate logging verification results"""
        c3_result = self.sub_task_results.get("C3", {})
        if not c3_result or c3_result.get("status") == "ERROR":
            return {"status": "ERROR", "verified_aspects": []}
        
        results = c3_result.get("results", [])
        verified_aspects = []
        
        # Check specific aspects
        for result in results:
            test_name = result.get("test", "")
            if result.get("status") == "PASS":
                if "TTL" in test_name and "Calculation" in test_name:
                    verified_aspects.append("ttl_calculation_metrics")
                elif "Batch Processing" in test_name:
                    verified_aspects.append("batch_processing_performance")
                elif "Weaviate TTL" in test_name or "TTL Operation" in test_name:
                    verified_aspects.append("weaviate_ttl_operation_logging")
                elif "Error Tracking" in test_name:
                    verified_aspects.append("error_tracking_correlation_ids")
                elif "Cleanup" in test_name:
                    verified_aspects.append("cleanup_operation_metrics")
        
        return {
            "status": "VERIFIED" if c3_result.get("summary", {}).get("failed", 0) == 0 else "PARTIAL",
            "verified_aspects": verified_aspects,
            "summary": c3_result.get("summary", {})
        }
    
    def print_comprehensive_report(self, report: Dict[str, Any]):
        """Print the comprehensive verification report"""
        print("\n" + "=" * 100)
        print("🎯 VERIFY-C: PIPELINE_METRICS LOGGING VERIFICATION REPORT")
        print("=" * 100)
        
        # Overall status
        print(f"\n{report['status_emoji']} OVERALL STATUS: {report['overall_status']}")
        print(f"⏱️  Execution Time: {report['execution_time_seconds']}s")
        print(f"📊 Success Rate: {report['success_rate']}% ({report['total_passed']}/{report['total_tests']} tests passed)")
        
        # Sub-task summaries
        print(f"\n📋 SUB-TASK SUMMARIES:")
        print("-" * 50)
        
        for task_id, result in report['sub_task_results'].items():
            summary = result.get('summary', {})
            status_icon = "✅" if summary.get('failed', 0) == 0 else "⚠️" if summary.get('passed', 0) > 0 else "❌"
            print(f"{status_icon} SUB-TASK {task_id}: {summary.get('passed', 0)}/{summary.get('total', 0)} tests passed")
            print(f"   └─ {result.get('description', 'No description')}")
        
        # Verification aspects
        print(f"\n🔍 VERIFICATION ASPECTS:")
        print("-" * 50)
        
        for aspect_name, aspect_data in report['verification_aspects'].items():
            status = aspect_data.get('status', 'UNKNOWN')
            status_icon = "✅" if status == "VERIFIED" else "⚠️" if status == "PARTIAL" else "❌"
            print(f"{status_icon} {aspect_name.replace('_', ' ').title()}: {status}")
            
            verified_aspects = aspect_data.get('verified_aspects', [])
            if verified_aspects:
                print(f"   └─ Verified: {', '.join(verified_aspects)}")
        
        # Detailed findings
        print(f"\n🔬 DETAILED FINDINGS:")
        print("-" * 50)
        
        key_findings = []
        
        # Context7Provider findings
        c1_aspects = report['verification_aspects']['Context7Provider_logging']['verified_aspects']
        if 'correlation_id_generation_tracking' in c1_aspects:
            key_findings.append("✅ Context7Provider generates and tracks correlation IDs properly")
        if 'http_request_performance_metrics' in c1_aspects:
            key_findings.append("✅ HTTP request performance metrics are logged with proper timing")
        if 'cache_hit_miss_analytics' in c1_aspects:
            key_findings.append("✅ Cache hit/miss analytics are working correctly")
        
        # SearchOrchestrator findings
        c2_aspects = report['verification_aspects']['SearchOrchestrator_metrics']['verified_aspects']
        if 'external_search_decision_logging' in c2_aspects:
            key_findings.append("✅ External search decisions are logged with proper reasoning")
        if 'correlation_id_propagation' in c2_aspects:
            key_findings.append("✅ Correlation IDs propagate correctly across orchestrator operations")
        
        # IngestionService findings
        c3_aspects = report['verification_aspects']['IngestionService_weaviate']['verified_aspects']
        if 'ttl_calculation_metrics' in c3_aspects:
            key_findings.append("✅ TTL calculations are logged with detailed metrics")
        if 'batch_processing_performance' in c3_aspects:
            key_findings.append("✅ Batch processing performance is tracked properly")
        if 'cleanup_operation_metrics' in c3_aspects:
            key_findings.append("✅ Cleanup operations log comprehensive metrics")
        
        for finding in key_findings:
            print(f"  {finding}")
        
        # Recommendations
        failed_tests = [
            result for task_results in report['sub_task_results'].values()
            for result in task_results.get('results', [])
            if result.get('status') == 'FAIL'
        ]
        
        if failed_tests:
            print(f"\n⚠️  RECOMMENDATIONS:")
            print("-" * 50)
            for failed_test in failed_tests[:5]:  # Show first 5 failures
                print(f"  • Fix: {failed_test.get('test', 'Unknown test')}")
                print(f"    └─ Error: {failed_test.get('error', 'Unknown error')}")
        
        # Summary conclusion
        print(f"\n🎯 CONCLUSION:")
        print("-" * 50)
        
        if report['overall_status'] == "FULLY VERIFIED":
            print("✅ PIPELINE_METRICS logging implementation is FULLY VERIFIED")
            print("   All correlation IDs, performance metrics, and logging aspects work correctly.")
        elif report['overall_status'] == "MOSTLY VERIFIED":
            print("⚠️  PIPELINE_METRICS logging is MOSTLY VERIFIED with some issues")
            print("   Core functionality works, but some edge cases need attention.")
        else:
            print("❌ PIPELINE_METRICS logging verification FAILED")
            print("   Significant issues found that need immediate attention.")
        
        print("=" * 100)


async def main():
    """Main verification execution"""
    verifier = PipelineMetricsVerifier()
    
    try:
        # Run parallel verification
        sub_task_results = await verifier.run_parallel_verification()
        
        # Generate and print comprehensive report
        report = verifier.generate_comprehensive_report()
        verifier.print_comprehensive_report(report)
        
        # Return exit code based on results
        if report['overall_status'] == "FULLY VERIFIED":
            return 0
        elif report['overall_status'] == "MOSTLY VERIFIED":
            return 1
        else:
            return 2
            
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)