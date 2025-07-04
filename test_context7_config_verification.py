#!/usr/bin/env python3
"""
Context7 Configuration Verification Test Script
Tests all aspects of Context7 configuration system in parallel sub-tasks
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config.models import (
    Context7Config, 
    Context7TTLConfig, 
    Context7IngestionConfig,
    Context7CacheConfig,
    Context7BackgroundJobConfig,
    SystemConfiguration
)
from src.core.config.manager import ConfigurationManager
from src.core.config.defaults import get_environment_overrides, apply_nested_override

class Context7ConfigVerifier:
    """Comprehensive Context7 configuration verification"""
    
    def __init__(self):
        self.results = {
            "b1_class_integration": {},
            "b2_environment_variables": {},
            "b3_configuration_manager": {}
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all verification tests in parallel"""
        print("🔍 Starting Context7 Configuration Verification Tests...")
        
        # Run all sub-tasks in parallel
        results = await asyncio.gather(
            self.test_b1_class_integration(),
            self.test_b2_environment_variables(),
            self.test_b3_configuration_manager(),
            return_exceptions=True
        )
        
        # Combine results
        final_results = {
            "summary": {
                "total_tests": sum(len(r) for r in self.results.values()),
                "passed": sum(sum(1 for t in r.values() if t.get("passed", False)) for r in self.results.values()),
                "failed": sum(sum(1 for t in r.values() if not t.get("passed", False)) for r in self.results.values())
            },
            "details": self.results
        }
        
        return final_results
    
    async def test_b1_class_integration(self) -> Dict[str, Any]:
        """SUB-TASK B1: Test Context7Config class integration"""
        print("\n🔧 SUB-TASK B1: Testing Context7Config class integration...")
        
        # Test 1: Verify Context7Config class exists and structure
        try:
            config = Context7Config()
            self.results["b1_class_integration"]["context7_config_exists"] = {
                "passed": True,
                "message": "Context7Config class instantiated successfully",
                "details": {
                    "enabled": config.enabled,
                    "has_ttl": hasattr(config, "ttl"),
                    "has_ingestion": hasattr(config, "ingestion"),
                    "has_cache": hasattr(config, "cache"),
                    "has_background_jobs": hasattr(config, "background_jobs")
                }
            }
        except Exception as e:
            self.results["b1_class_integration"]["context7_config_exists"] = {
                "passed": False,
                "message": f"Context7Config class instantiation failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 2: Verify default values
        try:
            config = Context7Config()
            expected_defaults = {
                "enabled": True,
                "ttl.default_days": 7,
                "ttl.min_days": 1,
                "ttl.max_days": 90,
                "ingestion.batch_size": 10,
                "ingestion.sync_enabled": True,
                "cache.enabled": True,
                "cache.ttl_multiplier": 1.0,
                "background_jobs.ttl_cleanup_enabled": True
            }
            
            actual_values = {}
            for key, expected_value in expected_defaults.items():
                parts = key.split('.')
                current = config
                for part in parts:
                    current = getattr(current, part)
                actual_values[key] = current
            
            all_match = all(actual_values[k] == v for k, v in expected_defaults.items())
            
            self.results["b1_class_integration"]["default_values"] = {
                "passed": all_match,
                "message": "Default values verification" + (" passed" if all_match else " failed"),
                "details": {
                    "expected": expected_defaults,
                    "actual": actual_values,
                    "mismatches": {k: {"expected": v, "actual": actual_values[k]} 
                                 for k, v in expected_defaults.items() 
                                 if actual_values[k] != v}
                }
            }
        except Exception as e:
            self.results["b1_class_integration"]["default_values"] = {
                "passed": False,
                "message": f"Default values test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 3: Verify TTL configuration bounds and multipliers
        try:
            # Test valid TTL configuration
            ttl_config = Context7TTLConfig(
                default_days=14,
                min_days=2,
                max_days=60
            )
            
            # Test invalid TTL bounds (should raise validation error)
            validation_passed = True
            try:
                invalid_config = Context7TTLConfig(
                    default_days=100,  # Above max_days
                    min_days=1,
                    max_days=90
                )
                validation_passed = False  # Should not reach here
            except Exception:
                pass  # Expected validation error
            
            # Test technology multipliers
            multipliers_test = all(
                0.1 <= multiplier <= 10.0 
                for multiplier in ttl_config.tech_multipliers.values()
            )
            
            self.results["b1_class_integration"]["ttl_bounds_validation"] = {
                "passed": validation_passed and multipliers_test,
                "message": "TTL bounds and multipliers validation",
                "details": {
                    "bounds_validation": validation_passed,
                    "multipliers_in_range": multipliers_test,
                    "sample_multipliers": dict(list(ttl_config.tech_multipliers.items())[:3])
                }
            }
        except Exception as e:
            self.results["b1_class_integration"]["ttl_bounds_validation"] = {
                "passed": False,
                "message": f"TTL bounds validation failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 4: Verify feature toggle functionality
        try:
            config = Context7Config()
            
            # Test feature toggles
            feature_toggles = {
                "ttl.enable_tech_multipliers": config.ttl.enable_tech_multipliers,
                "ttl.enable_doc_type_adjustments": config.ttl.enable_doc_type_adjustments,
                "ttl.enable_freshness_boost": config.ttl.enable_freshness_boost,
                "ttl.enable_popularity_boost": config.ttl.enable_popularity_boost,
                "cache.enabled": config.cache.enabled,
                "background_jobs.ttl_cleanup_enabled": config.background_jobs.ttl_cleanup_enabled
            }
            
            # All feature toggles should be boolean
            all_boolean = all(isinstance(v, bool) for v in feature_toggles.values())
            
            self.results["b1_class_integration"]["feature_toggles"] = {
                "passed": all_boolean,
                "message": "Feature toggles validation",
                "details": {
                    "all_boolean": all_boolean,
                    "toggles": feature_toggles
                }
            }
        except Exception as e:
            self.results["b1_class_integration"]["feature_toggles"] = {
                "passed": False,
                "message": f"Feature toggles test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 5: Test configuration model validation
        try:
            # Test invalid configuration should raise validation error
            validation_errors = []
            
            # Test invalid TTL multiplier
            try:
                Context7TTLConfig(tech_multipliers={"invalid": 50.0})  # Outside 0.1-10.0 range
                validation_errors.append("tech_multipliers validation failed")
            except Exception:
                pass  # Expected
            
            # Test invalid cache configuration
            try:
                Context7CacheConfig(ttl_multiplier=0.05)  # Below minimum
                validation_errors.append("cache ttl_multiplier validation failed")
            except Exception:
                pass  # Expected
            
            # Test SystemConfiguration integration
            system_config = SystemConfiguration(
                app={"environment": "testing"},
                content={},
                weaviate={"endpoint": "http://test:8080", "api_key": "test-key-12345"},
                github={"api_token": "test-token-12345"},
                scraping={},
                redis={},
                ai={"primary_provider": "ollama"},
                context7=Context7Config()
            )
            
            integration_passed = hasattr(system_config, 'context7')
            
            self.results["b1_class_integration"]["model_validation"] = {
                "passed": len(validation_errors) == 0 and integration_passed,
                "message": "Configuration model validation",
                "details": {
                    "validation_errors": validation_errors,
                    "system_config_integration": integration_passed,
                    "context7_in_system": hasattr(system_config, 'context7')
                }
            }
        except Exception as e:
            self.results["b1_class_integration"]["model_validation"] = {
                "passed": False,
                "message": f"Model validation test failed: {e}",
                "details": {"error": str(e)}
            }
        
        print("✅ SUB-TASK B1: Context7Config class integration tests completed")
        return self.results["b1_class_integration"]
    
    async def test_b2_environment_variables(self) -> Dict[str, Any]:
        """SUB-TASK B2: Test environment variable support"""
        print("\n🌍 SUB-TASK B2: Testing environment variable support...")
        
        # Test 1: Verify CONTEXT7_DEFAULT_TTL_DAYS environment variable
        try:
            # Test with mock environment variable
            with patch.dict(os.environ, {"CONTEXT7_TTL_DEFAULT_DAYS": "14"}):
                overrides = get_environment_overrides()
                
                has_ttl_override = "context7.ttl.default_days" in overrides
                correct_value = overrides.get("context7.ttl.default_days") == 14
                
                self.results["b2_environment_variables"]["context7_default_ttl_days"] = {
                    "passed": has_ttl_override and correct_value,
                    "message": "CONTEXT7_TTL_DEFAULT_DAYS environment variable support",
                    "details": {
                        "has_override": has_ttl_override,
                        "correct_value": correct_value,
                        "override_value": overrides.get("context7.ttl.default_days")
                    }
                }
        except Exception as e:
            self.results["b2_environment_variables"]["context7_default_ttl_days"] = {
                "passed": False,
                "message": f"CONTEXT7_TTL_DEFAULT_DAYS test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 2: Test multiple Context7 environment variables
        try:
            test_env_vars = {
                "CONTEXT7_ENABLED": "false",
                "CONTEXT7_TTL_MIN_DAYS": "2",
                "CONTEXT7_TTL_MAX_DAYS": "180",
                "CONTEXT7_INGESTION_BATCH_SIZE": "25",
                "CONTEXT7_CACHE_ENABLED": "false",
                "CONTEXT7_TTL_TECH_PYTHON_MULTIPLIER": "3.0",
                "CONTEXT7_BACKGROUND_TTL_CLEANUP_ENABLED": "false"
            }
            
            with patch.dict(os.environ, test_env_vars):
                overrides = get_environment_overrides()
                
                expected_mappings = {
                    "CONTEXT7_ENABLED": ("context7.enabled", False),
                    "CONTEXT7_TTL_MIN_DAYS": ("context7.ttl.min_days", 2),
                    "CONTEXT7_TTL_MAX_DAYS": ("context7.ttl.max_days", 180),
                    "CONTEXT7_INGESTION_BATCH_SIZE": ("context7.ingestion.batch_size", 25),
                    "CONTEXT7_CACHE_ENABLED": ("context7.cache.enabled", False),
                    "CONTEXT7_TTL_TECH_PYTHON_MULTIPLIER": ("context7.ttl.tech_multipliers.python", 3.0),
                    "CONTEXT7_BACKGROUND_TTL_CLEANUP_ENABLED": ("context7.background_jobs.ttl_cleanup_enabled", False)
                }
                
                results = {}
                for env_var, (config_key, expected_value) in expected_mappings.items():
                    actual_value = overrides.get(config_key)
                    results[env_var] = {
                        "config_key": config_key,
                        "expected": expected_value,
                        "actual": actual_value,
                        "matches": actual_value == expected_value
                    }
                
                all_passed = all(r["matches"] for r in results.values())
                
                self.results["b2_environment_variables"]["multiple_env_vars"] = {
                    "passed": all_passed,
                    "message": "Multiple Context7 environment variables",
                    "details": {
                        "all_passed": all_passed,
                        "individual_results": results
                    }
                }
        except Exception as e:
            self.results["b2_environment_variables"]["multiple_env_vars"] = {
                "passed": False,
                "message": f"Multiple environment variables test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 3: Test nested configuration via dot notation
        try:
            config_dict = {}
            test_cases = [
                ("context7.enabled", True),
                ("context7.ttl.default_days", 21),
                ("context7.ttl.tech_multipliers.react", 2.5),
                ("context7.ingestion.sync_enabled", False),
                ("context7.cache.eviction_policy", "lfu"),
                ("context7.background_jobs.metrics_collection_enabled", True)
            ]
            
            for key, value in test_cases:
                apply_nested_override(config_dict, key, value)
            
            # Verify nested structure was created correctly
            structure_tests = [
                ("context7" in config_dict, "Root context7 key exists"),
                ("ttl" in config_dict.get("context7", {}), "TTL section exists"),
                ("tech_multipliers" in config_dict.get("context7", {}).get("ttl", {}), "Tech multipliers section exists"),
                (config_dict.get("context7", {}).get("ttl", {}).get("tech_multipliers", {}).get("react") == 2.5, "Deep nested value correct"),
                (config_dict.get("context7", {}).get("ingestion", {}).get("sync_enabled") == False, "Boolean conversion correct")
            ]
            
            all_structure_tests_passed = all(test[0] for test in structure_tests)
            
            self.results["b2_environment_variables"]["nested_dot_notation"] = {
                "passed": all_structure_tests_passed,
                "message": "Nested configuration via dot notation",
                "details": {
                    "structure_tests": [{"test": test[1], "passed": test[0]} for test in structure_tests],
                    "final_config": config_dict
                }
            }
        except Exception as e:
            self.results["b2_environment_variables"]["nested_dot_notation"] = {
                "passed": False,
                "message": f"Nested dot notation test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 4: Test type conversion and validation
        try:
            conversion_tests = [
                ("CONTEXT7_TTL_DEFAULT_DAYS", "30", int, 30),
                ("CONTEXT7_TTL_TECH_PYTHON_MULTIPLIER", "2.5", float, 2.5),
                ("CONTEXT7_ENABLED", "true", bool, True),
                ("CONTEXT7_CACHE_ENABLED", "false", bool, False),
                ("CONTEXT7_CACHE_EVICTION_POLICY", "lru", str, "lru")
            ]
            
            conversion_results = {}
            for env_var, env_value, expected_type, expected_value in conversion_tests:
                with patch.dict(os.environ, {env_var: env_value}):
                    overrides = get_environment_overrides()
                    
                    # Find the corresponding config key
                    config_key = None
                    for key, value in overrides.items():
                        if "context7" in key and value == expected_value:
                            config_key = key
                            break
                    
                    if config_key:
                        actual_value = overrides[config_key]
                        conversion_results[env_var] = {
                            "config_key": config_key,
                            "expected_type": expected_type.__name__,
                            "actual_type": type(actual_value).__name__,
                            "expected_value": expected_value,
                            "actual_value": actual_value,
                            "type_correct": isinstance(actual_value, expected_type),
                            "value_correct": actual_value == expected_value
                        }
                    else:
                        conversion_results[env_var] = {
                            "error": "Config key not found in overrides"
                        }
            
            all_conversions_passed = all(
                result.get("type_correct", False) and result.get("value_correct", False)
                for result in conversion_results.values()
            )
            
            self.results["b2_environment_variables"]["type_conversion"] = {
                "passed": all_conversions_passed,
                "message": "Type conversion and validation",
                "details": {
                    "all_conversions_passed": all_conversions_passed,
                    "conversion_results": conversion_results
                }
            }
        except Exception as e:
            self.results["b2_environment_variables"]["type_conversion"] = {
                "passed": False,
                "message": f"Type conversion test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 5: Test environment variable override behavior
        try:
            # Test override priority: environment > default
            with patch.dict(os.environ, {
                "CONTEXT7_TTL_DEFAULT_DAYS": "42",
                "CONTEXT7_INGESTION_BATCH_SIZE": "50"
            }):
                # Create config with defaults
                default_config = Context7Config()
                
                # Get environment overrides
                overrides = get_environment_overrides()
                
                # Apply overrides to config dict
                config_dict = {}
                for key, value in overrides.items():
                    apply_nested_override(config_dict, key, value)
                
                # Create config from overridden dict
                overridden_config = Context7Config(**config_dict.get("context7", {}))
                
                # Verify overrides took effect
                ttl_overridden = overridden_config.ttl.default_days == 42
                batch_overridden = overridden_config.ingestion.batch_size == 50
                
                # Verify non-overridden values remain default
                enabled_default = overridden_config.enabled == True  # Should remain default
                
                self.results["b2_environment_variables"]["override_behavior"] = {
                    "passed": ttl_overridden and batch_overridden and enabled_default,
                    "message": "Environment variable override behavior",
                    "details": {
                        "ttl_overridden": ttl_overridden,
                        "batch_overridden": batch_overridden,
                        "enabled_remains_default": enabled_default,
                        "default_ttl": default_config.ttl.default_days,
                        "overridden_ttl": overridden_config.ttl.default_days,
                        "default_batch": default_config.ingestion.batch_size,
                        "overridden_batch": overridden_config.ingestion.batch_size
                    }
                }
        except Exception as e:
            self.results["b2_environment_variables"]["override_behavior"] = {
                "passed": False,
                "message": f"Override behavior test failed: {e}",
                "details": {"error": str(e)}
            }
        
        print("✅ SUB-TASK B2: Environment variable support tests completed")
        return self.results["b2_environment_variables"]
    
    async def test_b3_configuration_manager(self) -> Dict[str, Any]:
        """SUB-TASK B3: Test configuration manager integration"""
        print("\n⚙️  SUB-TASK B3: Testing configuration manager integration...")
        
        # Test 1: Verify Context7 config loads through ConfigurationManager
        try:
            # Create a temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                config_content = """
app:
  environment: testing
  debug: true
  log_level: INFO
  data_dir: ./test_data
  api_port: 8080
  web_port: 8081
  workers: 2

content:
  chunk_size_default: 1000
  chunk_size_max: 4000
  chunk_overlap: 100
  quality_threshold: 0.3
  min_content_length: 50
  max_content_length: 1000000

weaviate:
  endpoint: http://test-weaviate:8080
  api_key: test-key-12345

github:
  api_token: test-token-12345

scraping:
  user_agent: TestBot/1.0
  rate_limit_delay: 1.0

redis:
  host: test-redis
  port: 6379

ai:
  primary_provider: ollama
  fallback_provider: openai
  enable_failover: true
  cache_ttl_seconds: 3600
  ollama:
    endpoint: http://test-ollama:11434
    model: llama2
    temperature: 0.7
    max_tokens: 4096
    timeout_seconds: 60

context7:
  enabled: true
  ttl:
    default_days: 14
    min_days: 2
    max_days: 60
    enable_tech_multipliers: true
    tech_multipliers:
      python: 3.0
      react: 2.0
  ingestion:
    batch_size: 20
    sync_enabled: false
  cache:
    enabled: false
    ttl_multiplier: 0.5
"""
                f.write(config_content)
                temp_config_path = f.name
            
            try:
                # Create configuration manager
                config_manager = ConfigurationManager()
                
                # Mock database connection to avoid actual DB dependency
                config_manager._db_manager = None
                
                # Initialize with temp config file
                await config_manager.initialize(temp_config_path, watch_file=False)
                
                # Get configuration
                system_config = config_manager.get_configuration()
                
                # Verify Context7 config was loaded
                has_context7 = hasattr(system_config, 'context7')
                context7_enabled = system_config.context7.enabled if has_context7 else False
                ttl_override = system_config.context7.ttl.default_days if has_context7 else None
                
                self.results["b3_configuration_manager"]["context7_loading"] = {
                    "passed": has_context7 and context7_enabled and ttl_override == 14,
                    "message": "Context7 config loading through ConfigurationManager",
                    "details": {
                        "has_context7": has_context7,
                        "context7_enabled": context7_enabled,
                        "ttl_override": ttl_override,
                        "expected_ttl": 14
                    }
                }
                
            finally:
                # Clean up temp file
                os.unlink(temp_config_path)
                
        except Exception as e:
            self.results["b3_configuration_manager"]["context7_loading"] = {
                "passed": False,
                "message": f"Context7 config loading test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 2: Test hierarchical loading (environment > YAML > database)
        try:
            # Create config manager with mocked database
            config_manager = ConfigurationManager()
            config_manager._db_manager = None
            
            # Test environment override taking precedence
            with patch.dict(os.environ, {"CONTEXT7_TTL_DEFAULT_DAYS": "7"}):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    yaml_content = """
app:
  environment: testing
  debug: true
  log_level: INFO
  data_dir: ./test_data
  api_port: 8080
  web_port: 8081
  workers: 2

content:
  chunk_size_default: 1000
  chunk_size_max: 4000
  chunk_overlap: 100
  quality_threshold: 0.3
  min_content_length: 50
  max_content_length: 1000000

weaviate:
  endpoint: http://test-weaviate:8080
  api_key: test-key-12345

github:
  api_token: test-token-12345

scraping:
  user_agent: TestBot/1.0
  rate_limit_delay: 1.0

redis:
  host: test-redis
  port: 6379

ai:
  primary_provider: ollama
  fallback_provider: openai
  enable_failover: true
  cache_ttl_seconds: 3600
  ollama:
    endpoint: http://test-ollama:11434
    model: llama2
    temperature: 0.7
    max_tokens: 4096
    timeout_seconds: 60

context7:
  enabled: true
  ttl:
    default_days: 21  # This should be overridden by environment variable
"""
                    f.write(yaml_content)
                    temp_config_path = f.name
                
                try:
                    await config_manager.initialize(temp_config_path, watch_file=False)
                    system_config = config_manager.get_configuration()
                    
                    # Environment variable (7) should override YAML (21)
                    env_override_worked = system_config.context7.ttl.default_days == 7
                    
                    self.results["b3_configuration_manager"]["hierarchical_loading"] = {
                        "passed": env_override_worked,
                        "message": "Hierarchical loading (environment > YAML > database)",
                        "details": {
                            "env_override_worked": env_override_worked,
                            "final_ttl_value": system_config.context7.ttl.default_days,
                            "expected_from_env": 7,
                            "yaml_value_overridden": 21
                        }
                    }
                    
                finally:
                    os.unlink(temp_config_path)
                    
        except Exception as e:
            self.results["b3_configuration_manager"]["hierarchical_loading"] = {
                "passed": False,
                "message": f"Hierarchical loading test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 3: Test configuration utility methods
        try:
            config = Context7Config()
            
            # Test get_effective_ttl method
            base_ttl = config.get_effective_ttl()
            tech_ttl = config.get_effective_ttl(technology="python")
            doc_type_ttl = config.get_effective_ttl(doc_type="tutorial")
            fresh_ttl = config.get_effective_ttl(is_fresh=True)
            popular_ttl = config.get_effective_ttl(is_popular=True)
            
            # Test get_cache_ttl method
            cache_ttl = config.get_cache_ttl(7)
            
            # Verify methods work and return reasonable values
            methods_work = all(isinstance(ttl, int) for ttl in [base_ttl, tech_ttl, doc_type_ttl, fresh_ttl, popular_ttl])
            cache_ttl_works = isinstance(cache_ttl, int)
            
            # Test bounds checking
            ttl_in_bounds = config.ttl.min_days <= base_ttl <= config.ttl.max_days
            
            self.results["b3_configuration_manager"]["utility_methods"] = {
                "passed": methods_work and cache_ttl_works and ttl_in_bounds,
                "message": "Configuration utility methods (get_effective_ttl, get_cache_ttl)",
                "details": {
                    "methods_work": methods_work,
                    "cache_ttl_works": cache_ttl_works,
                    "ttl_in_bounds": ttl_in_bounds,
                    "base_ttl": base_ttl,
                    "tech_ttl": tech_ttl,
                    "doc_type_ttl": doc_type_ttl,
                    "fresh_ttl": fresh_ttl,
                    "popular_ttl": popular_ttl,
                    "cache_ttl": cache_ttl
                }
            }
            
        except Exception as e:
            self.results["b3_configuration_manager"]["utility_methods"] = {
                "passed": False,
                "message": f"Utility methods test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 4: Test service restart triggers (mock)
        try:
            # Mock service config manager
            from src.core.services.config_manager import ServiceConfigManager
            
            config_manager = ConfigurationManager()
            service_manager = ServiceConfigManager(config_manager)
            
            # Test that Context7 config changes map to correct services
            from src.core.services.config_manager import SERVICE_CONFIG_MAP
            
            context7_mappings = {
                key: services for key, services in SERVICE_CONFIG_MAP.items()
                if key.startswith("context7")
            }
            
            # Verify Context7 mappings exist
            has_context7_mappings = len(context7_mappings) > 0
            
            # Test determine_affected_services method
            affected_services = service_manager._determine_affected_services("context7.ttl.default_days")
            
            self.results["b3_configuration_manager"]["service_restart_triggers"] = {
                "passed": has_context7_mappings and isinstance(affected_services, list),
                "message": "Service restart triggers on Context7 config changes",
                "details": {
                    "has_context7_mappings": has_context7_mappings,
                    "context7_mappings": context7_mappings,
                    "affected_services": affected_services,
                    "affected_services_type": type(affected_services).__name__
                }
            }
            
        except Exception as e:
            self.results["b3_configuration_manager"]["service_restart_triggers"] = {
                "passed": False,
                "message": f"Service restart triggers test failed: {e}",
                "details": {"error": str(e)}
            }
        
        # Test 5: Test configuration file watching (mock)
        try:
            config_manager = ConfigurationManager()
            
            # Test that watch mechanism exists
            has_watch_method = hasattr(config_manager, 'check_for_config_file_changes')
            has_watch_context = hasattr(config_manager, 'watch_config_changes')
            
            # Test watch flag
            config_manager._watch_config_file = True
            watch_enabled = config_manager._watch_config_file
            
            self.results["b3_configuration_manager"]["hot_reloading"] = {
                "passed": has_watch_method and has_watch_context and watch_enabled,
                "message": "Hot-reloading functionality",
                "details": {
                    "has_watch_method": has_watch_method,
                    "has_watch_context": has_watch_context,
                    "watch_enabled": watch_enabled
                }
            }
            
        except Exception as e:
            self.results["b3_configuration_manager"]["hot_reloading"] = {
                "passed": False,
                "message": f"Hot-reloading test failed: {e}",
                "details": {"error": str(e)}
            }
        
        print("✅ SUB-TASK B3: Configuration manager integration tests completed")
        return self.results["b3_configuration_manager"]

async def main():
    """Run all Context7 configuration verification tests"""
    verifier = Context7ConfigVerifier()
    results = await verifier.run_all_tests()
    
    print("\n" + "="*80)
    print("🎯 CONTEXT7 CONFIGURATION VERIFICATION RESULTS")
    print("="*80)
    
    # Print summary
    summary = results["summary"]
    print(f"\n📊 SUMMARY:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Passed: {summary['passed']} ✅")
    print(f"   Failed: {summary['failed']} ❌")
    print(f"   Success Rate: {(summary['passed'] / summary['total_tests'] * 100):.1f}%")
    
    # Print detailed results
    for subtask, subtask_results in results["details"].items():
        print(f"\n🔍 {subtask.upper().replace('_', ' ')}:")
        for test_name, test_result in subtask_results.items():
            status = "✅ PASS" if test_result["passed"] else "❌ FAIL"
            print(f"   {status} {test_name}: {test_result['message']}")
            
            if not test_result["passed"] and "error" in test_result.get("details", {}):
                print(f"      Error: {test_result['details']['error']}")
    
    # Save results to file
    with open("/home/lab/docaiche/context7_config_verification_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: /home/lab/docaiche/context7_config_verification_results.json")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())