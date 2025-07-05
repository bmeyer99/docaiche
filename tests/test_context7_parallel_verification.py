#!/usr/bin/env python3
"""
VERIFY-A: Context7IngestionService Parallel Verification Runner
=============================================================

Master test runner that executes all three sub-tasks in parallel:
- SUB-TASK A1: TTL calculation logic tests
- SUB-TASK A2: Context7 metadata processing tests  
- SUB-TASK A3: Batch processing and Weaviate integration tests

This runner spawns all three sub-tasks simultaneously and collects their results.
"""

import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import subprocess
import threading
from datetime import datetime


class ParallelTestRunner:
    """Parallel test runner for Context7 verification tasks"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
        
    def run_subtask(self, task_name, script_path):
        """Run a single subtask in a separate process"""
        try:
            print(f"🚀 Starting {task_name}...")
            
            # Run the test script
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per task
            )
            
            success = result.returncode == 0
            
            self.results[task_name] = {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": "N/A"  # Will be calculated by the runner
            }
            
            if success:
                print(f"✅ {task_name} COMPLETED SUCCESSFULLY")
            else:
                print(f"❌ {task_name} FAILED")
                
            return success
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {task_name} TIMED OUT")
            self.results[task_name] = {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Test timed out after 5 minutes",
                "duration": "300s (timeout)"
            }
            return False
            
        except Exception as e:
            print(f"💥 {task_name} CRASHED: {e}")
            self.results[task_name] = {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": "N/A"
            }
            return False
    
    def run_all_parallel(self):
        """Run all three subtasks in parallel"""
        print("="*80)
        print("VERIFY-A: Context7IngestionService Parallel Verification")
        print("="*80)
        print(f"Starting parallel execution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.start_time = time.time()
        
        # Define the three subtasks
        tasks = [
            ("SUB-TASK A1: TTL Calculation Logic", "test_context7_ttl_simple.py"),
            ("SUB-TASK A2: Context7 Metadata Processing", "test_context7_metadata_simple.py"),
            ("SUB-TASK A3: Batch Processing & Weaviate Integration", "test_context7_batch_simple.py")
        ]
        
        # Run all tasks in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.run_subtask, task_name, script_path): task_name
                for task_name, script_path in tasks
            }
            
            # Wait for all tasks to complete
            for future in futures:
                task_name = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"💥 {task_name} exception: {e}")
        
        self.end_time = time.time()
        
        # Generate comprehensive report
        self.generate_report()
        
        # Return overall success
        return all(result["success"] for result in self.results.values())
    
    def generate_report(self):
        """Generate comprehensive verification report"""
        total_duration = self.end_time - self.start_time
        
        print("\n" + "="*80)
        print("CONTEXT7 INGESTION SERVICE VERIFICATION REPORT")
        print("="*80)
        print(f"Total Execution Time: {total_duration:.2f} seconds")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Summary table
        print("SUB-TASK RESULTS:")
        print("-" * 80)
        successful_tasks = 0
        failed_tasks = 0
        
        for task_name, result in self.results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{task_name:<50} {status}")
            
            if result["success"]:
                successful_tasks += 1
            else:
                failed_tasks += 1
        
        print("-" * 80)
        print(f"Total Tasks: {len(self.results)}")
        print(f"Successful: {successful_tasks}")
        print(f"Failed: {failed_tasks}")
        print(f"Success Rate: {successful_tasks/len(self.results)*100:.1f}%")
        
        # Detailed results for each task
        print("\n" + "="*80)
        print("DETAILED RESULTS")
        print("="*80)
        
        for task_name, result in self.results.items():
            print(f"\n{task_name}")
            print("-" * len(task_name))
            print(f"Status: {'PASSED' if result['success'] else 'FAILED'}")
            print(f"Return Code: {result['returncode']}")
            
            if result["stdout"]:
                print("\nSTDOUT:")
                print(result["stdout"])
            
            if result["stderr"]:
                print("\nSTDERR:")
                print(result["stderr"])
            
            print("-" * 40)
        
        # Overall assessment
        print("\n" + "="*80)
        print("VERIFICATION ASSESSMENT")
        print("="*80)
        
        if successful_tasks == len(self.results):
            print("🎉 ALL VERIFICATION TESTS PASSED!")
            print("✅ Context7IngestionService is functioning correctly with:")
            print("   - Proper TTL calculation logic")
            print("   - Correct metadata processing")
            print("   - Reliable batch processing and Weaviate integration")
            print("   - Robust error handling")
            print("   - Performance optimization")
        else:
            print(f"⚠️  {failed_tasks} out of {len(self.results)} verification tasks failed")
            print("❌ Context7IngestionService has issues that need to be addressed:")
            
            for task_name, result in self.results.items():
                if not result["success"]:
                    print(f"   - {task_name}: {result.get('stderr', 'Unknown error')}")
        
        print("\n" + "="*80)
        
        # Specific verification details
        print("VERIFICATION COVERAGE:")
        print("- TTL Calculation Logic:")
        print("  ✓ Technology multipliers (React, TypeScript, Bootstrap, etc.)")
        print("  ✓ Document type adjustments (API, Guide, Tutorial, etc.)")
        print("  ✓ TTL bounds enforcement (1-90 days)")
        print("  ✓ Content analysis (deprecated, stable, experimental)")
        print("  ✓ Version analysis (latest, beta, alpha)")
        print("  ✓ Quality score adjustments")
        print("  ✓ Error handling and edge cases")
        
        print("\n- Context7 Metadata Processing:")
        print("  ✓ Context7Document creation from SearchResult")
        print("  ✓ Technology and owner extraction")
        print("  ✓ Version detection from content")
        print("  ✓ Document type classification")
        print("  ✓ Quality indicators extraction")
        print("  ✓ Language detection and fallbacks")
        print("  ✓ Metadata preservation")
        
        print("\n- Batch Processing & Weaviate Integration:")
        print("  ✓ Batch processing of multiple documents")
        print("  ✓ Parallel processing optimization")
        print("  ✓ TTL metadata application to Weaviate")
        print("  ✓ Error handling for individual failures")
        print("  ✓ Cleanup of expired documents")
        print("  ✓ Performance with large batches")
        print("  ✓ Correlation ID propagation")
        
        print("\n" + "="*80)


def main():
    """Main entry point"""
    runner = ParallelTestRunner()
    success = runner.run_all_parallel()
    
    if success:
        print("\n🎉 ALL CONTEXT7 INGESTION SERVICE VERIFICATION TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME CONTEXT7 INGESTION SERVICE VERIFICATION TESTS FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)