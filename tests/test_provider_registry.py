#!/usr/bin/env python3
"""
Test script for the new provider registry system
Tests basic functionality before continuing with implementation
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm import (
    get_provider_registry, 
    register_provider,
    ProviderCapabilities,
    ProviderCategory,
    OllamaProvider
)

async def test_provider_registry():
    """Test the provider registry system"""
    
    print("🧪 Testing Provider Registry System...")
    
    # Test 1: Get registry instance
    registry = get_provider_registry()
    print(f"✅ Registry instance created: {type(registry).__name__}")
    
    # Test 2: Check if built-in providers are auto-registered
    providers = registry.list_providers()
    print(f"✅ Found {len(providers)} providers:")
    for provider in providers:
        print(f"   - {provider.provider_id}: {provider.display_name} ({provider.category.value})")
    
    # Test 3: Test Ollama provider class
    try:
        ollama_config = {
            "endpoint": "http://localhost:11434",
            "model": "llama2",
            "temperature": 0.7
        }
        
        # Test static methods
        capabilities = OllamaProvider.get_static_capabilities()
        print(f"✅ Ollama capabilities: text={capabilities.text_generation}, local={capabilities.local}")
        
        schema = OllamaProvider.get_config_schema()
        print(f"✅ Ollama config schema has {len(schema.get('properties', {}))} properties")
        
        # Test provider instantiation
        provider = OllamaProvider(ollama_config)
        print(f"✅ Ollama provider created with model: {provider.model}")
        
    except Exception as e:
        print(f"❌ Ollama provider test failed: {e}")
        return False
    
    # Test 4: Test registry stats
    stats = registry.get_registry_stats()
    print(f"✅ Registry stats: {stats['total_providers']} total, {stats['enabled_providers']} enabled")
    
    # Test 5: Test capability filtering
    text_providers = registry.get_providers_by_capability('text_generation')
    print(f"✅ Found {len(text_providers)} providers with text generation")
    
    print("\n🎉 All tests passed! Provider registry system is working.")
    return True

async def test_config_system():
    """Test the enhanced configuration system"""
    
    print("\n🧪 Testing Enhanced Configuration System...")
    
    try:
        from core.config.models import AIConfig, ProviderConfig
        
        # Test 1: Create basic AI config (backward compatibility)
        ai_config = AIConfig()
        print(f"✅ AI config created with {len(ai_config.providers)} providers")
        
        # Test 2: Add new provider dynamically
        new_provider_config = ProviderConfig(
            enabled=True,
            config={
                "api_key": "test-key",
                "base_url": "https://api.anthropic.com"
            },
            priority=8
        )
        
        ai_config.add_provider("anthropic", new_provider_config)
        print(f"✅ Added anthropic provider. Total providers: {len(ai_config.providers)}")
        
        # Test 3: Test provider retrieval
        anthropic_config = ai_config.get_provider_config("anthropic")
        if anthropic_config:
            print(f"✅ Retrieved anthropic config with priority: {anthropic_config.priority}")
        
        # Test 4: Test enabled providers
        enabled = ai_config.get_enabled_providers()
        print(f"✅ Enabled providers: {enabled}")
        
        print("🎉 Configuration system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing AI Providers Foundation Architecture\n")
    
    # Test registry system
    registry_ok = await test_provider_registry()
    
    # Test config system  
    config_ok = await test_config_system()
    
    if registry_ok and config_ok:
        print("\n✅ All foundation tests PASSED! Ready to continue implementation.")
        return True
    else:
        print("\n❌ Some tests FAILED. Need to fix issues before continuing.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)