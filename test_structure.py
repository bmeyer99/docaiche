#!/usr/bin/env python3
"""
Simple structure test for the provider registry system
Tests import structure and basic class definitions without external dependencies
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported"""
    
    print("🧪 Testing Module Imports...")
    
    try:
        # Test basic models import
        print("Testing models import...")
        from llm.models import ProviderCapabilities, ProviderCategory, ProviderInfo
        print("✅ Models imported successfully")
        
        # Test registry import
        print("Testing registry import...")
        from llm.provider_registry import ProviderRegistry, get_provider_registry
        print("✅ Registry imported successfully")
        
        # Test base provider import
        print("Testing base provider import...")
        from llm.base_provider import BaseLLMProvider
        print("✅ Base provider imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enum_values():
    """Test enum definitions"""
    
    print("\n🧪 Testing Enum Values...")
    
    try:
        from llm.models import ProviderCategory, HealthStatus
        
        categories = list(ProviderCategory)
        print(f"✅ Provider categories: {[c.value for c in categories]}")
        
        statuses = list(HealthStatus)
        print(f"✅ Health statuses: {[s.value for s in statuses]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enum test failed: {e}")
        return False

def test_registry_structure():
    """Test registry class structure"""
    
    print("\n🧪 Testing Registry Structure...")
    
    try:
        from llm.provider_registry import ProviderRegistry
        
        # Test that registry has expected methods
        expected_methods = [
            'register', 'unregister', 'get_provider_class', 
            'list_providers', 'get_registry_stats'
        ]
        
        for method in expected_methods:
            if hasattr(ProviderRegistry, method):
                print(f"✅ Registry has method: {method}")
            else:
                print(f"❌ Registry missing method: {method}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Registry structure test failed: {e}")
        return False

def test_file_structure():
    """Test that all expected files exist"""
    
    print("\n🧪 Testing File Structure...")
    
    expected_files = [
        'src/llm/__init__.py',
        'src/llm/models.py', 
        'src/llm/provider_registry.py',
        'src/llm/base_provider.py',
        'src/llm/ollama_provider.py',
        'src/core/config/models.py'
    ]
    
    all_exist = True
    for file_path in expected_files:
        if os.path.exists(file_path):
            print(f"✅ File exists: {file_path}")
        else:
            print(f"❌ File missing: {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """Run all structure tests"""
    print("🚀 Testing AI Providers Foundation Structure\n")
    
    tests = [
        test_file_structure,
        test_imports,
        test_enum_values,
        test_registry_structure
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    if all(results):
        print("\n✅ All structure tests PASSED! Foundation is properly implemented.")
        return True
    else:
        print(f"\n❌ {len([r for r in results if not r])} tests FAILED. Foundation needs fixes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)