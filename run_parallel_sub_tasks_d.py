#!/usr/bin/env python3
"""
VERIFY-D: Test background job identifies and processes expired documents
=======================================================================

Runs three parallel sub-tasks to verify the background job framework:
- SUB-TASK D1: Test Context7BackgroundJobManager functionality
- SUB-TASK D2: Test TTL cleanup and refresh jobs
- SUB-TASK D3: Test job monitoring and health checks
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import sub-task modules
sys.path.insert(0, os.path.dirname(__file__))
from test_sub_task_d1 import run_sub_task_d1
from test_sub_task_d2 import run_sub_task_d2
from test_sub_task_d3 import run_sub_task_d3


async def run_parallel_sub_tasks():
    """Run all three sub-tasks in parallel"""
    logger.info("=" * 80)
    logger.info("VERIFY-D: Test background job identifies and processes expired documents")
    logger.info("=" * 80)
    
    start_time = datetime.utcnow()
    
    try:
        # Run all three sub-tasks in parallel
        logger.info("Starting parallel execution of three sub-tasks...")
        
        results = await asyncio.gather(
            run_sub_task_d1(),
            run_sub_task_d2(),
            run_sub_task_d3(),
            return_exceptions=True
        )
        
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()
        
        # Process results
        sub_task_results = {}
        all_passed = True
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for i, result in enumerate(results, 1):
            sub_task_id = f"D{i}"
            
            if isinstance(result, Exception):
                logger.error(f"SUB-TASK {sub_task_id} failed with exception: {result}")
                sub_task_results[sub_task_id] = {
                    "status": "EXCEPTION",
                    "error": str(result),
                    "summary": f"SUB-TASK {sub_task_id} crashed with exception"
                }
                all_passed = False
            else:
                sub_task_results[sub_task_id] = result
                
                if result["status"] == "PASSED":
                    logger.info(f"✓ SUB-TASK {sub_task_id}: {result['summary']}")
                    total_tests += result.get("tests_run", 0)
                    total_passed += result.get("tests_passed", 0)
                    total_failed += result.get("tests_failed", 0)
                else:
                    logger.error(f"✗ SUB-TASK {sub_task_id}: {result.get('summary', 'Failed')}")
                    if "error" in result:
                        logger.error(f"  Error: {result['error']}")
                    all_passed = False
                    total_tests += result.get("tests_run", 0)
                    total_failed += result.get("tests_run", 0)
        
        # Generate final report
        final_result = {
            "verification_id": "VERIFY-D",
            "title": "Test background job identifies and processes expired documents",
            "status": "PASSED" if all_passed else "FAILED",
            "execution_time_seconds": total_duration,
            "summary": {
                "sub_tasks_run": 3,
                "sub_tasks_passed": sum(1 for r in sub_task_results.values() if r["status"] == "PASSED"),
                "sub_tasks_failed": sum(1 for r in sub_task_results.values() if r["status"] != "PASSED"),
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            "sub_task_results": sub_task_results,
            "verified_functionality": [
                "Context7BackgroundJobManager initialization and lifecycle",
                "Job registration, scheduling, and execution mechanisms",
                "Error handling and retry logic implementation",
                "TTL cleanup job identifies and processes expired documents",
                "Bulk cleanup operations with batch processing",
                "Document refresh job functionality and candidate selection",
                "Integration with Context7IngestionService confirmed",
                "Job monitoring and health check systems",
                "PIPELINE_METRICS logging and performance tracking",
                "Alert handling and notification mechanisms",
                "Database integration for job storage and history"
            ],
            "completed_at": end_time.isoformat()
        }
        
        # Log final results
        logger.info("=" * 80)
        logger.info("VERIFY-D FINAL RESULTS")
        logger.info("=" * 80)
        logger.info(f"Status: {'✓ PASSED' if all_passed else '✗ FAILED'}")
        logger.info(f"Execution Time: {total_duration:.2f} seconds")
        logger.info(f"Sub-tasks: {final_result['summary']['sub_tasks_passed']}/3 passed")
        logger.info(f"Tests: {total_passed}/{total_tests} passed ({final_result['summary']['success_rate']:.1f}%)")
        
        if all_passed:
            logger.info("\n🎉 All background job functionality verified successfully!")
            logger.info("\nVerified Components:")
            for item in final_result["verified_functionality"]:
                logger.info(f"  ✓ {item}")
        else:
            logger.error("\n❌ Background job verification failed!")
            for sub_task_id, result in sub_task_results.items():
                if result["status"] != "PASSED":
                    logger.error(f"  ✗ SUB-TASK {sub_task_id}: {result.get('summary', 'Failed')}")
        
        logger.info("=" * 80)
        
        # Save detailed results
        with open("verify_d_results.json", "w") as f:
            json.dump(final_result, f, indent=2, default=str)
        
        logger.info("Detailed results saved to: verify_d_results.json")
        
        return final_result
        
    except Exception as e:
        logger.error(f"Critical error during parallel execution: {e}")
        return {
            "verification_id": "VERIFY-D",
            "status": "CRITICAL_ERROR",
            "error": str(e),
            "execution_time_seconds": (datetime.utcnow() - start_time).total_seconds()
        }


if __name__ == "__main__":
    asyncio.run(run_parallel_sub_tasks())