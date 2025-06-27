#!/usr/bin/env python3
"""
PRD-010 Critical Failure Diagnostic Script
Identifies root causes for the 5 critical system failures
"""

import asyncio
import resource
import sys
import traceback
from unittest.mock import Mock

# Test TaskSandbox resource limit failure
def test_resource_limits():
    """Test if resource limits can be set in current environment"""
    print("=== Testing Resource Limits ===")
    
    try:
        # Test memory limit setting
        if hasattr(resource, 'RLIMIT_AS'):
            current_limit = resource.getrlimit(resource.RLIMIT_AS)
            print(f"Current memory limit: {current_limit}")
            
            # Try to set a smaller limit
            new_limit = min(current_limit[0], 256 * 1024 * 1024) if current_limit[0] != resource.RLIM_INFINITY else 256 * 1024 * 1024
            try:
                resource.setrlimit(resource.RLIMIT_AS, (new_limit, new_limit))
                print("✅ Memory limit setting: SUCCESS")
                
                # Only restore if original wasn't unlimited (container-compatible)
                if current_limit[0] != resource.RLIM_INFINITY and current_limit[0] != -1:
                    resource.setrlimit(resource.RLIMIT_AS, current_limit)
                    print("✅ Memory limit restoration: SUCCESS")
                else:
                    print("✅ Memory limit restoration: SKIPPED (unlimited in container)")
                    
            except (PermissionError, ValueError) as e:
                print(f"❌ Memory limit setting: FAILED - {e}")
                return False
        else:
            print("⚠️  RLIMIT_AS not available on this platform")
            
        # Test CPU limit setting
        if hasattr(resource, 'RLIMIT_CPU'):
            current_cpu = resource.getrlimit(resource.RLIMIT_CPU)
            print(f"Current CPU limit: {current_cpu}")
            
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
                print("✅ CPU limit setting: SUCCESS")
                
                # Only restore if original wasn't unlimited (container-compatible)
                if current_cpu[0] != resource.RLIM_INFINITY and current_cpu[0] != -1:
                    resource.setrlimit(resource.RLIMIT_CPU, current_cpu)
                    print("✅ CPU limit restoration: SUCCESS")
                else:
                    print("✅ CPU limit restoration: SKIPPED (unlimited in container)")
                    
            except (PermissionError, ValueError) as e:
                print(f"❌ CPU limit setting: FAILED - {e}")
                return False
        else:
            print("⚠️  RLIMIT_CPU not available on this platform")
            
        return True
        
    except Exception as e:
        print(f"❌ Resource limit test failed: {e}")
        traceback.print_exc()
        return False

# Test ConcurrentTaskExecutor max_concurrent_tasks attribute
def test_concurrent_executor_attributes():
    """Test if ConcurrentTaskExecutor has required attributes"""
    print("\n=== Testing ConcurrentTaskExecutor Attributes ===")
    
    try:
        from src.enrichment.concurrent import ConcurrentTaskExecutor, ResourceLimits
        from src.enrichment.models import EnrichmentConfig
        
        config = EnrichmentConfig()
        resource_limits = ResourceLimits()
        
        executor = ConcurrentTaskExecutor(config, resource_limits)
        
        # Check for max_concurrent_tasks attribute
        if hasattr(executor, 'max_concurrent_tasks'):
            print(f"✅ max_concurrent_tasks attribute exists: {executor.max_concurrent_tasks}")
            return True
        elif hasattr(config, 'max_concurrent_tasks'):
            print(f"✅ max_concurrent_tasks found in config: {config.max_concurrent_tasks}")
            return True
        else:
            print("❌ max_concurrent_tasks attribute missing")
            print(f"Available attributes: {[attr for attr in dir(executor) if not attr.startswith('_')]}")
            return False
            
    except Exception as e:
        print(f"❌ ConcurrentTaskExecutor test failed: {e}")
        traceback.print_exc()
        return False

# Test lifecycle shutdown status
async def test_lifecycle_shutdown():
    """Test lifecycle graceful_shutdown returns proper status"""
    print("\n=== Testing Lifecycle Shutdown ===")
    
    try:
        from src.enrichment.lifecycle import LifecycleManager
        from src.enrichment.models import EnrichmentConfig
        
        config = EnrichmentConfig()
        db_manager = Mock()
        
        lifecycle_manager = LifecycleManager(config, db_manager)
        
        # Test graceful shutdown
        result = await lifecycle_manager.graceful_shutdown(timeout=1.0)
        
        if isinstance(result, dict):
            print(f"✅ Shutdown returns dict: {list(result.keys())}")
            
            if 'graceful' in result:
                print(f"✅ 'graceful' key present: {result['graceful']}")
                return True
            else:
                print("❌ 'graceful' key missing from shutdown result")
                return False
        else:
            print(f"❌ Shutdown returns wrong type: {type(result)}")
            return False
            
    except Exception as e:
        print(f"❌ Lifecycle shutdown test failed: {e}")
        traceback.print_exc()
        return False

# Test XSS protection patterns
def test_xss_protection():
    """Test XSS protection in analyze_content_gaps"""
    print("\n=== Testing XSS Protection ===")
    
    try:
        from src.enrichment.enricher import KnowledgeEnricher
        from src.enrichment.models import EnrichmentConfig
        
        config = EnrichmentConfig()
        db_manager = Mock()
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        # Test event handler patterns that should be blocked
        dangerous_patterns = [
            "onload=alert('xss')",
            "onerror=malicious()",
            "<script>alert(1)</script>",
            "javascript:alert(1)"
        ]
        
        blocked_count = 0
        for pattern in dangerous_patterns:
            try:
                enricher.analyze_content_gaps(pattern)
                print(f"❌ Pattern not blocked: {pattern}")
            except ValueError:
                blocked_count += 1
                print(f"✅ Pattern blocked: {pattern}")
        
        if blocked_count == len(dangerous_patterns):
            print(f"✅ All {blocked_count} dangerous patterns blocked")
            return True
        else:
            print(f"❌ Only {blocked_count}/{len(dangerous_patterns)} patterns blocked")
            return False
            
    except Exception as e:
        print(f"❌ XSS protection test failed: {e}")
        traceback.print_exc()
        return False

# Test SQL injection detection
def test_sql_injection_protection():
    """Test SQL injection detection"""
    print("\n=== Testing SQL Injection Protection ===")
    
    try:
        from src.enrichment.enricher import KnowledgeEnricher
        from src.enrichment.models import EnrichmentConfig
        
        config = EnrichmentConfig()
        db_manager = Mock()
        enricher = KnowledgeEnricher(config, db_manager, auto_start=False)
        
        # Test SQL injection patterns
        sql_patterns = [
            "'; DROP TABLE users; --",
            "UNION SELECT * FROM passwords",
            "DELETE FROM content_metadata",
            "INSERT INTO malicious VALUES"
        ]
        
        blocked_count = 0
        for pattern in sql_patterns:
            try:
                enricher.analyze_content_gaps(pattern)
                print(f"❌ SQL pattern not blocked: {pattern}")
            except ValueError:
                blocked_count += 1
                print(f"✅ SQL pattern blocked: {pattern}")
        
        if blocked_count == len(sql_patterns):
            print(f"✅ All {blocked_count} SQL injection patterns blocked")
            return True
        else:
            print(f"❌ Only {blocked_count}/{len(sql_patterns)} SQL patterns blocked")
            return False
            
    except Exception as e:
        print(f"❌ SQL injection protection test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all diagnostic tests"""
    print("PRD-010 Critical Failure Diagnostic")
    print("=" * 50)
    
    results = []
    
    # Run synchronous tests
    results.append(("Resource Limits", test_resource_limits()))
    results.append(("ConcurrentTaskExecutor Attributes", test_concurrent_executor_attributes()))
    results.append(("XSS Protection", test_xss_protection()))
    results.append(("SQL Injection Protection", test_sql_injection_protection()))
    
    # Run async test
    results.append(("Lifecycle Shutdown", await test_lifecycle_shutdown()))
    
    # Summary
    print("\n" + "=" * 50)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed < len(results):
        print("\n🚨 CRITICAL FAILURES DETECTED - Production deployment blocked")
        return 1
    else:
        print("\n✅ All critical systems operational")
        return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))