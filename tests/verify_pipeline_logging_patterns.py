#!/usr/bin/env python3
"""
VERIFY-C: PIPELINE_METRICS Logging Pattern Verification
=======================================================

Comprehensive verification of PIPELINE_METRICS logging implementation by analyzing
the actual code for correct logging patterns, correlation IDs, and metrics tracking.

This script performs static analysis of the logging implementation without requiring
runtime dependencies, focusing on:

SUB-TASK C1: Context7Provider logging patterns
SUB-TASK C2: SearchOrchestrator Context7 metrics patterns  
SUB-TASK C3: Context7IngestionService and Weaviate logging patterns
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add project root to path
sys.path.append('/home/lab/docaiche')


class PipelineLoggingPatternVerifier:
    """Verify PIPELINE_METRICS logging patterns in the codebase"""
    
    def __init__(self):
        self.project_root = Path('/home/lab/docaiche')
        self.verification_results = {}
        
    def read_file_content(self, file_path: Path) -> str:
        """Read file content safely"""
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
    
    def extract_pipeline_metrics_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Extract PIPELINE_METRICS logging patterns from code"""
        patterns = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if 'PIPELINE_METRICS:' in line and 'logger.info' in line:
                # Extract the full logging statement
                log_statement = line.strip()
                
                # Parse the step and parameters
                step_match = re.search(r'step=([^\s]+)', log_statement)
                correlation_match = re.search(r'correlation_id=([^\s]+)', log_statement)
                trace_match = re.search(r'trace_id=([^\s]+)', log_statement)
                duration_match = re.search(r'duration_ms=([^\s]+)', log_statement)
                
                pattern_info = {
                    'line_number': i + 1,
                    'statement': log_statement,
                    'step': step_match.group(1) if step_match else None,
                    'has_correlation_id': correlation_match is not None,
                    'has_trace_id': trace_match is not None,
                    'has_duration': duration_match is not None,
                    'correlation_param': correlation_match.group(1) if correlation_match else None,
                    'trace_param': trace_match.group(1) if trace_match else None
                }
                
                patterns.append(pattern_info)
        
        return patterns
    
    def verify_context7_provider_logging(self) -> Dict[str, Any]:
        """SUB-TASK C1: Verify Context7Provider logging patterns"""
        print("\n=== SUB-TASK C1: Context7Provider Logging Verification ===")
        
        file_path = self.project_root / 'src' / 'mcp' / 'providers' / 'implementations' / 'context7_provider.py'
        content = self.read_file_content(file_path)
        
        if not content:
            return {"status": "ERROR", "error": "Could not read Context7Provider file"}
        
        patterns = self.extract_pipeline_metrics_patterns(content)
        
        # Analyze patterns for required logging aspects
        results = {
            "total_patterns": len(patterns),
            "patterns": patterns,
            "verification_aspects": {},
            "issues": []
        }
        
        # C1.1: Check correlation ID generation and tracking
        correlation_id_patterns = [p for p in patterns if p['has_correlation_id']]
        if correlation_id_patterns:
            # Check for correlation ID generation pattern
            has_generation = any('uuid.uuid4' in content or 'ctx7_' in line for line in content.split('\n'))
            results["verification_aspects"]["correlation_id_generation"] = {
                "status": "VERIFIED" if has_generation else "MISSING",
                "pattern_count": len(correlation_id_patterns),
                "details": f"Found {len(correlation_id_patterns)} patterns with correlation_id"
            }
        else:
            results["verification_aspects"]["correlation_id_generation"] = {
                "status": "MISSING",
                "pattern_count": 0,
                "details": "No correlation_id patterns found"
            }
            results["issues"].append("Missing correlation ID tracking in Context7Provider")
        
        # C1.2: Check search operation metrics (start/complete/error)
        search_steps = [p for p in patterns if p['step'] and 'search' in p['step']]
        has_start = any('start' in p['step'] for p in search_steps if p['step'])
        has_complete = any('complete' in p['step'] for p in search_steps if p['step'])
        has_error = any('error' in p['step'] for p in search_steps if p['step'])
        
        results["verification_aspects"]["search_operation_metrics"] = {
            "status": "VERIFIED" if (has_start and has_complete) else "PARTIAL" if (has_start or has_complete) else "MISSING",
            "has_start": has_start,
            "has_complete": has_complete,
            "has_error": has_error,
            "search_patterns": len(search_steps)
        }
        
        # C1.3: Check technology extraction logging
        tech_extraction_patterns = [p for p in patterns if p['step'] and 'tech' in p['step']]
        results["verification_aspects"]["technology_extraction"] = {
            "status": "VERIFIED" if tech_extraction_patterns else "MISSING",
            "pattern_count": len(tech_extraction_patterns),
            "patterns": [p['step'] for p in tech_extraction_patterns if p['step']]
        }
        
        # C1.4: Check HTTP request performance metrics
        http_patterns = [p for p in patterns if p['step'] and 'http' in p['step']]
        has_http_start = any('start' in p['step'] for p in http_patterns if p['step'])
        has_http_success = any('success' in p['step'] for p in http_patterns if p['step'])
        has_http_duration = any(p['has_duration'] for p in http_patterns)
        
        results["verification_aspects"]["http_request_metrics"] = {
            "status": "VERIFIED" if (has_http_start and has_http_success and has_http_duration) else "PARTIAL",
            "has_start": has_http_start,
            "has_success": has_http_success,
            "has_duration": has_http_duration,
            "http_patterns": len(http_patterns)
        }
        
        # C1.5: Check cache hit/miss analytics logging
        cache_patterns = [p for p in patterns if p['step'] and 'cache' in p['step']]
        results["verification_aspects"]["cache_analytics"] = {
            "status": "VERIFIED" if cache_patterns else "MISSING",
            "pattern_count": len(cache_patterns),
            "patterns": [p['step'] for p in cache_patterns if p['step']]
        }
        
        # Overall status
        verified_count = sum(1 for aspect in results["verification_aspects"].values() 
                           if aspect.get("status") == "VERIFIED")
        total_aspects = len(results["verification_aspects"])
        
        if verified_count == total_aspects:
            results["status"] = "FULLY_VERIFIED"
        elif verified_count > total_aspects / 2:
            results["status"] = "MOSTLY_VERIFIED"
        else:
            results["status"] = "NEEDS_IMPROVEMENT"
        
        return results
    
    def verify_search_orchestrator_logging(self) -> Dict[str, Any]:
        """SUB-TASK C2: Verify SearchOrchestrator Context7 metrics patterns"""
        print("\n=== SUB-TASK C2: SearchOrchestrator Context7 Metrics Verification ===")
        
        file_path = self.project_root / 'src' / 'search' / 'orchestrator.py'
        content = self.read_file_content(file_path)
        
        if not content:
            return {"status": "ERROR", "error": "Could not read SearchOrchestrator file"}
        
        patterns = self.extract_pipeline_metrics_patterns(content)
        
        results = {
            "total_patterns": len(patterns),
            "patterns": patterns,
            "verification_aspects": {},
            "issues": []
        }
        
        # C2.1: Check external search decision logging
        decision_patterns = [p for p in patterns if p['step'] and 'decision' in p['step']]
        external_patterns = [p for p in patterns if p['step'] and 'external' in p['step']]
        
        results["verification_aspects"]["external_search_decision"] = {
            "status": "VERIFIED" if (decision_patterns or external_patterns) else "MISSING",
            "decision_patterns": len(decision_patterns),
            "external_patterns": len(external_patterns),
            "patterns": [p['step'] for p in decision_patterns + external_patterns if p['step']]
        }
        
        # C2.2: Check Context7-specific pipeline metrics
        context7_patterns = [p for p in patterns if p['step'] and 'context7' in p['step']]
        results["verification_aspects"]["context7_pipeline_metrics"] = {
            "status": "VERIFIED" if context7_patterns else "MISSING",
            "pattern_count": len(context7_patterns),
            "patterns": [p['step'] for p in context7_patterns if p['step']]
        }
        
        # C2.3: Check correlation ID propagation
        trace_id_patterns = [p for p in patterns if p['has_trace_id']]
        correlation_patterns = [p for p in patterns if p['has_correlation_id']]
        
        results["verification_aspects"]["id_propagation"] = {
            "status": "VERIFIED" if (trace_id_patterns or correlation_patterns) else "MISSING",
            "trace_id_patterns": len(trace_id_patterns),
            "correlation_patterns": len(correlation_patterns),
            "details": f"Trace IDs: {len(trace_id_patterns)}, Correlation IDs: {len(correlation_patterns)}"
        }
        
        # C2.4: Check query generation and optimization tracking
        query_patterns = [p for p in patterns if p['step'] and ('query' in p['step'] or 'generation' in p['step'])]
        results["verification_aspects"]["query_generation_tracking"] = {
            "status": "VERIFIED" if query_patterns else "MISSING",
            "pattern_count": len(query_patterns),
            "patterns": [p['step'] for p in query_patterns if p['step']]
        }
        
        # C2.5: Check result conversion and aggregation metrics
        result_patterns = [p for p in patterns if p['step'] and ('result' in p['step'] or 'conversion' in p['step'])]
        results["verification_aspects"]["result_conversion"] = {
            "status": "VERIFIED" if result_patterns else "MISSING",
            "pattern_count": len(result_patterns),
            "patterns": [p['step'] for p in result_patterns if p['step']]
        }
        
        # Overall status
        verified_count = sum(1 for aspect in results["verification_aspects"].values() 
                           if aspect.get("status") == "VERIFIED")
        total_aspects = len(results["verification_aspects"])
        
        if verified_count == total_aspects:
            results["status"] = "FULLY_VERIFIED"
        elif verified_count > total_aspects / 2:
            results["status"] = "MOSTLY_VERIFIED"
        else:
            results["status"] = "NEEDS_IMPROVEMENT"
        
        return results
    
    def verify_context7_ingestion_logging(self) -> Dict[str, Any]:
        """SUB-TASK C3: Verify Context7IngestionService and Weaviate logging patterns"""
        print("\n=== SUB-TASK C3: Context7IngestionService and Weaviate Logging Verification ===")
        
        file_path = self.project_root / 'src' / 'ingestion' / 'context7_ingestion_service.py'
        content = self.read_file_content(file_path)
        
        if not content:
            return {"status": "ERROR", "error": "Could not read Context7IngestionService file"}
        
        patterns = self.extract_pipeline_metrics_patterns(content)
        
        results = {
            "total_patterns": len(patterns),
            "patterns": patterns,
            "verification_aspects": {},
            "issues": []
        }
        
        # C3.1: Check TTL calculation metrics logging
        ttl_patterns = [p for p in patterns if p['step'] and 'ttl' in p['step']]
        has_ttl_calc = any('calculation' in p['step'] for p in ttl_patterns if p['step'])
        has_ttl_detail = any('detail' in p['step'] for p in ttl_patterns if p['step'])
        
        results["verification_aspects"]["ttl_calculation_metrics"] = {
            "status": "VERIFIED" if (has_ttl_calc or has_ttl_detail) else "MISSING",
            "ttl_patterns": len(ttl_patterns),
            "has_calculation": has_ttl_calc,
            "has_detail": has_ttl_detail,
            "patterns": [p['step'] for p in ttl_patterns if p['step']]
        }
        
        # C3.2: Check batch processing performance metrics
        batch_patterns = [p for p in patterns if p['step'] and 'batch' in p['step']]
        has_batch_start = any('start' in p['step'] for p in batch_patterns if p['step'])
        has_batch_complete = any('complete' in p['step'] for p in batch_patterns if p['step'])
        has_batch_duration = any(p['has_duration'] for p in batch_patterns)
        
        results["verification_aspects"]["batch_processing_metrics"] = {
            "status": "VERIFIED" if (has_batch_start and has_batch_complete) else "PARTIAL",
            "batch_patterns": len(batch_patterns),
            "has_start": has_batch_start,
            "has_complete": has_batch_complete,
            "has_duration": has_batch_duration
        }
        
        # C3.3: Check Weaviate TTL operation logging
        weaviate_patterns = [p for p in patterns if p['step'] and 'weaviate' in p['step']]
        ttl_metadata_patterns = [p for p in patterns if p['step'] and 'metadata' in p['step']]
        
        results["verification_aspects"]["weaviate_ttl_operations"] = {
            "status": "VERIFIED" if (weaviate_patterns or ttl_metadata_patterns) else "MISSING",
            "weaviate_patterns": len(weaviate_patterns),
            "metadata_patterns": len(ttl_metadata_patterns),
            "patterns": [p['step'] for p in weaviate_patterns + ttl_metadata_patterns if p['step']]
        }
        
        # C3.4: Check error tracking with correlation IDs
        error_patterns = [p for p in patterns if p['step'] and 'error' in p['step']]
        error_with_correlation = [p for p in error_patterns if p['has_correlation_id']]
        
        results["verification_aspects"]["error_tracking"] = {
            "status": "VERIFIED" if error_with_correlation else "PARTIAL" if error_patterns else "MISSING",
            "error_patterns": len(error_patterns),
            "errors_with_correlation": len(error_with_correlation),
            "correlation_coverage": f"{len(error_with_correlation)}/{len(error_patterns)}" if error_patterns else "0/0"
        }
        
        # C3.5: Check cleanup operation metrics
        cleanup_patterns = [p for p in patterns if p['step'] and 'cleanup' in p['step']]
        has_cleanup_start = any('start' in p['step'] for p in cleanup_patterns if p['step'])
        has_cleanup_complete = any('complete' in p['step'] for p in cleanup_patterns if p['step'])
        
        results["verification_aspects"]["cleanup_operations"] = {
            "status": "VERIFIED" if (has_cleanup_start and has_cleanup_complete) else "PARTIAL",
            "cleanup_patterns": len(cleanup_patterns),
            "has_start": has_cleanup_start,
            "has_complete": has_cleanup_complete,
            "patterns": [p['step'] for p in cleanup_patterns if p['step']]
        }
        
        # Overall status
        verified_count = sum(1 for aspect in results["verification_aspects"].values() 
                           if aspect.get("status") == "VERIFIED")
        total_aspects = len(results["verification_aspects"])
        
        if verified_count == total_aspects:
            results["status"] = "FULLY_VERIFIED"
        elif verified_count > total_aspects / 2:
            results["status"] = "MOSTLY_VERIFIED"
        else:
            results["status"] = "NEEDS_IMPROVEMENT"
        
        return results
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""
        # Run all verifications
        self.verification_results = {
            "C1": self.verify_context7_provider_logging(),
            "C2": self.verify_search_orchestrator_logging(),
            "C3": self.verify_context7_ingestion_logging()
        }
        
        # Calculate overall statistics
        total_patterns = sum(r.get("total_patterns", 0) for r in self.verification_results.values())
        
        fully_verified = sum(1 for r in self.verification_results.values() if r.get("status") == "FULLY_VERIFIED")
        mostly_verified = sum(1 for r in self.verification_results.values() if r.get("status") == "MOSTLY_VERIFIED")
        needs_improvement = sum(1 for r in self.verification_results.values() if r.get("status") == "NEEDS_IMPROVEMENT")
        errors = sum(1 for r in self.verification_results.values() if r.get("status") == "ERROR")
        
        # Determine overall status
        if fully_verified == 3:
            overall_status = "FULLY_VERIFIED"
            status_emoji = "🎉"
        elif fully_verified + mostly_verified >= 2:
            overall_status = "MOSTLY_VERIFIED"
            status_emoji = "⚠️"
        else:
            overall_status = "NEEDS_IMPROVEMENT"
            status_emoji = "❌"
        
        return {
            "overall_status": overall_status,
            "status_emoji": status_emoji,
            "total_patterns": total_patterns,
            "sub_task_counts": {
                "fully_verified": fully_verified,
                "mostly_verified": mostly_verified,
                "needs_improvement": needs_improvement,
                "errors": errors
            },
            "sub_task_results": self.verification_results
        }
    
    def print_comprehensive_report(self, report: Dict[str, Any]):
        """Print the comprehensive verification report"""
        print("\n" + "=" * 100)
        print("🎯 VERIFY-C: PIPELINE_METRICS LOGGING PATTERN VERIFICATION REPORT")
        print("=" * 100)
        
        # Overall status
        print(f"\n{report['status_emoji']} OVERALL STATUS: {report['overall_status']}")
        print(f"📊 Total PIPELINE_METRICS Patterns Found: {report['total_patterns']}")
        
        counts = report['sub_task_counts']
        print(f"✅ Fully Verified: {counts['fully_verified']}/3 sub-tasks")
        print(f"⚠️  Mostly Verified: {counts['mostly_verified']}/3 sub-tasks")
        print(f"❌ Needs Improvement: {counts['needs_improvement']}/3 sub-tasks")
        print(f"🔥 Errors: {counts['errors']}/3 sub-tasks")
        
        # Sub-task details
        print(f"\n📋 SUB-TASK DETAILED RESULTS:")
        print("-" * 80)
        
        for task_id, result in report['sub_task_results'].items():
            status = result.get('status', 'UNKNOWN')
            status_icons = {
                'FULLY_VERIFIED': '✅',
                'MOSTLY_VERIFIED': '⚠️',
                'NEEDS_IMPROVEMENT': '❌',
                'ERROR': '🔥'
            }
            status_icon = status_icons.get(status, '❓')
            
            pattern_count = result.get('total_patterns', 0)
            print(f"\n{status_icon} SUB-TASK {task_id}: {status} ({pattern_count} patterns)")
            
            aspects = result.get('verification_aspects', {})
            for aspect_name, aspect_data in aspects.items():
                aspect_status = aspect_data.get('status', 'UNKNOWN')
                aspect_icon = '✅' if aspect_status == 'VERIFIED' else '⚠️' if aspect_status == 'PARTIAL' else '❌'
                print(f"   {aspect_icon} {aspect_name.replace('_', ' ').title()}: {aspect_status}")
                
                # Show pattern details for verified aspects
                if aspect_status == 'VERIFIED' and 'patterns' in aspect_data:
                    patterns = aspect_data['patterns']
                    if patterns and len(patterns) <= 3:
                        print(f"      └─ Steps: {', '.join(patterns)}")
                    elif patterns:
                        print(f"      └─ Steps: {', '.join(patterns[:3])} (+{len(patterns)-3} more)")
        
        # Key findings
        print(f"\n🔍 KEY FINDINGS:")
        print("-" * 80)
        
        c1_result = report['sub_task_results']['C1']
        c2_result = report['sub_task_results']['C2']
        c3_result = report['sub_task_results']['C3']
        
        findings = []
        
        # Context7Provider findings
        if c1_result.get('verification_aspects', {}).get('correlation_id_generation', {}).get('status') == 'VERIFIED':
            findings.append("✅ Context7Provider properly implements correlation ID generation and tracking")
        
        if c1_result.get('verification_aspects', {}).get('http_request_metrics', {}).get('status') == 'VERIFIED':
            findings.append("✅ HTTP request performance metrics are comprehensively logged")
        
        # SearchOrchestrator findings
        if c2_result.get('verification_aspects', {}).get('context7_pipeline_metrics', {}).get('status') == 'VERIFIED':
            findings.append("✅ SearchOrchestrator implements Context7-specific pipeline metrics")
        
        if c2_result.get('verification_aspects', {}).get('external_search_decision', {}).get('status') == 'VERIFIED':
            findings.append("✅ External search decision logging is properly implemented")
        
        # IngestionService findings
        if c3_result.get('verification_aspects', {}).get('ttl_calculation_metrics', {}).get('status') == 'VERIFIED':
            findings.append("✅ TTL calculation metrics are logged with detailed information")
        
        if c3_result.get('verification_aspects', {}).get('batch_processing_metrics', {}).get('status') == 'VERIFIED':
            findings.append("✅ Batch processing performance metrics are tracked properly")
        
        # Show findings
        for finding in findings:
            print(f"  {finding}")
        
        # Issues and recommendations
        all_issues = []
        for result in report['sub_task_results'].values():
            all_issues.extend(result.get('issues', []))
        
        if all_issues:
            print(f"\n⚠️  ISSUES AND RECOMMENDATIONS:")
            print("-" * 80)
            for issue in all_issues:
                print(f"  • {issue}")
        
        # Pattern statistics
        print(f"\n📈 PATTERN STATISTICS:")
        print("-" * 80)
        
        for task_id, result in report['sub_task_results'].items():
            patterns = result.get('patterns', [])
            if patterns:
                steps = [p.get('step', 'unknown') for p in patterns if p.get('step')]
                unique_steps = set(steps)
                correlation_count = sum(1 for p in patterns if p.get('has_correlation_id'))
                duration_count = sum(1 for p in patterns if p.get('has_duration'))
                
                print(f"  SUB-TASK {task_id}:")
                print(f"    └─ Total patterns: {len(patterns)}")
                print(f"    └─ Unique steps: {len(unique_steps)}")
                print(f"    └─ With correlation_id: {correlation_count}/{len(patterns)}")
                print(f"    └─ With duration_ms: {duration_count}/{len(patterns)}")
        
        # Summary conclusion
        print(f"\n🎯 CONCLUSION:")
        print("-" * 80)
        
        if report['overall_status'] == "FULLY_VERIFIED":
            print("✅ PIPELINE_METRICS logging implementation is FULLY VERIFIED")
            print("   All required logging patterns are present with proper correlation IDs and metrics.")
        elif report['overall_status'] == "MOSTLY_VERIFIED":
            print("⚠️  PIPELINE_METRICS logging is MOSTLY VERIFIED")
            print("   Most patterns are correct, but some aspects need attention or enhancement.")
        else:
            print("❌ PIPELINE_METRICS logging verification NEEDS IMPROVEMENT")
            print("   Significant gaps found in logging patterns that should be addressed.")
        
        print("=" * 100)


def main():
    """Main verification execution"""
    print("🚀 Starting VERIFY-C: PIPELINE_METRICS Logging Pattern Verification")
    print("Analyzing code patterns for correlation IDs, metrics tracking, and proper logging...")
    
    verifier = PipelineLoggingPatternVerifier()
    
    try:
        # Generate and print comprehensive report
        report = verifier.generate_comprehensive_report()
        verifier.print_comprehensive_report(report)
        
        # Return exit code based on results
        if report['overall_status'] == "FULLY_VERIFIED":
            return 0
        elif report['overall_status'] == "MOSTLY_VERIFIED":
            return 1
        else:
            return 2
            
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)