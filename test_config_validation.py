#!/usr/bin/env python3
"""
CFG-001 Configuration System Validation Tests
Tests the implemented configuration system for functionality, security, and integration readiness
"""

import sys
import os
sys.path.append('src')

def test_basic_imports():
    """Test that all configuration components can be imported"""
    print("=== Testing Basic Imports ===")
    try:
        from src.core.config.models import (
            AppConfig, CircuitBreakerConfig, ContentConfig,
            AnythingLLMConfig, GitHubConfig, ScrapingConfig,
            RedisConfig, OllamaConfig, OpenAIConfig, AIConfig,
            SystemConfiguration
        )
        print("✓ All configuration models import successfully")
        
        from src.core.config.validation import ConfigurationValidators
        print("✓ Configuration validators import successfully")
        
        from src.core.config.defaults import get_environment_overrides, apply_nested_override
        print("✓ Configuration defaults import successfully")
        
        from src.core.config.secrets import SecretsManager
        print("✓ Secrets manager imports successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_model_validation():
    """Test Pydantic model validation with valid and invalid data"""
    print("\n=== Testing Model Validation ===")
    try:
        from src.core.config.models import AnythingLLMConfig, OllamaConfig, RedisConfig
        
        # Test valid AnythingLLM config
        valid_config = AnythingLLMConfig(
            endpoint="https://api.example.com",
            api_key="test-key-12345"
        )
        print("✓ Valid AnythingLLM config accepts valid data")
        
        # Test invalid endpoint
        try:
            invalid_config = AnythingLLMConfig(
                endpoint="invalid-url",
                api_key="test-key-12345"
            )
            print("✗ Should have rejected invalid endpoint")
            return False
        except ValueError:
            print("✓ Correctly rejects invalid endpoint URL")
        
        # Test invalid API key
        try:
            invalid_config = AnythingLLMConfig(
                endpoint="https://api.example.com",
                api_key="short"
            )
            print("✗ Should have rejected short API key")
            return False
        except ValueError:
            print("✓ Correctly rejects short API key")
        
        # Test Redis memory validation
        redis_config = RedisConfig(maxmemory="512mb")
        print("✓ Redis config accepts valid memory format")
        
        try:
            invalid_redis = RedisConfig(maxmemory="invalid-format")
            print("✗ Should have rejected invalid memory format")
            return False
        except ValueError:
            print("✓ Correctly rejects invalid Redis memory format")
        
        return True
    except Exception as e:
        print(f"✗ Model validation test failed: {e}")
        return False

def test_environment_overrides():
    """Test environment variable parsing and nested overrides"""
    print("\n=== Testing Environment Overrides ===")
    try:
        from src.core.config.defaults import get_environment_overrides, apply_nested_override
        
        # Set test environment variables
        os.environ["APP_DEBUG"] = "true"
        os.environ["REDIS_HOST"] = "test-redis"
        os.environ["AI_PRIMARY_PROVIDER"] = "openai"
        
        overrides = get_environment_overrides()
        print(f"✓ Environment overrides parsed: {len(overrides)} variables")
        
        # Test specific overrides
        if overrides.get("app.debug") == True:
            print("✓ Boolean environment variable parsed correctly")
        else:
            print("✗ Boolean environment variable parsing failed")
            return False
        
        if overrides.get("redis.host") == "test-redis":
            print("✓ String environment variable parsed correctly")
        else:
            print("✗ String environment variable parsing failed")
            return False
        
        # Test nested override application
        config_dict = {}
        apply_nested_override(config_dict, "app.debug", True)
        apply_nested_override(config_dict, "redis.host", "test-host")
        
        if config_dict.get("app", {}).get("debug") == True:
            print("✓ Nested override application works correctly")
        else:
            print("✗ Nested override application failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Environment override test failed: {e}")
        return False

def test_configuration_building():
    """Test building complete system configuration"""
    print("\n=== Testing Configuration Building ===")
    try:
        # Set minimal required environment variables for testing
        os.environ["ANYTHINGLLM_API_KEY"] = "test-anythingllm-key-12345"
        os.environ["GITHUB_API_TOKEN"] = "test-github-token-12345"
        os.environ["OPENAI_API_KEY"] = "test-openai-key-12345"
        os.environ["APP_ENVIRONMENT"] = "development"  # Avoid production validation
        
        from src.core.config import get_system_configuration
        
        config = get_system_configuration()
        print("✓ System configuration built successfully")
        
        # Validate configuration structure
        if hasattr(config, 'app') and hasattr(config, 'redis') and hasattr(config, 'ai'):
            print("✓ Configuration has all required sections")
        else:
            print("✗ Configuration missing required sections")
            return False
        
        # Test configuration access
        api_port = config.app.api_port
        redis_host = config.redis.host
        primary_provider = config.ai.primary_provider
        
        print(f"✓ Configuration values accessible: port={api_port}, redis={redis_host}, provider={primary_provider}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration building test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_functions():
    """Test configuration validation functions"""
    print("\n=== Testing Validation Functions ===")
    try:
        from src.core.config import validate_configuration
        
        validation_result = validate_configuration()
        print(f"✓ Configuration validation completed: {validation_result}")
        
        if "valid" in validation_result:
            print("✓ Validation returns proper structure")
        else:
            print("✗ Validation missing required fields")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Validation function test failed: {e}")
        return False

def test_secrets_management():
    """Test secrets management functionality"""
    print("\n=== Testing Secrets Management ===")
    try:
        from src.core.config.secrets import SecretsManager
        
        # Test secret masking
        masked = SecretsManager.mask_secret_for_logging("test-secret-key-12345")
        if masked.endswith("2345") and masked.startswith("*"):
            print("✓ Secret masking works correctly")
        else:
            print("✗ Secret masking failed")
            return False
        
        # Test secret format validation
        if SecretsManager.validate_secret_format("valid-key-12345"):
            print("✓ Valid secret format accepted")
        else:
            print("✗ Valid secret format rejected")
            return False
        
        if not SecretsManager.validate_secret_format("short"):
            print("✓ Invalid secret format rejected")
        else:
            print("✗ Invalid secret format accepted")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Secrets management test failed: {e}")
        return False

def test_integration_compatibility():
    """Test integration with existing API-001 implementation"""
    print("\n=== Testing Integration Compatibility ===")
    try:
        # Test that main application still works with new config system
        from src.main import app
        print("✓ Main application imports successfully with new config system")
        
        # Test that we can access FastAPI app properties
        if hasattr(app, 'title') and hasattr(app, 'version'):
            print("✓ FastAPI application maintains expected structure")
        else:
            print("✗ FastAPI application structure changed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Integration compatibility test failed: {e}")
        return False

def run_all_tests():
    """Run all configuration validation tests"""
    print("CFG-001 Configuration System Validation Tests")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_model_validation,
        test_environment_overrides,
        test_configuration_building,
        test_validation_functions,
        test_secrets_management,
        test_integration_compatibility
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - Configuration system is ready for validation")
        return True
    else:
        print("❌ TESTS FAILED - Configuration system requires fixes before validation")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)