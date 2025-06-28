#!/usr/bin/env python3
"""
Test script for the intelligent documentation pipeline
Tests the full flow from query analysis to caching
"""

import asyncio
import time
import logging
from typing import List
import os

# Set environment variable for data directory
os.environ['DATA_DIR'] = './test_data'

# Add project root to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.core.config import get_system_configuration
from src.core.config.manager import get_configuration_manager
from src.llm.client import LLMProviderClient
from src.search.orchestrator_enhanced import EnhancedSearchOrchestrator
from src.database.connection import create_database_manager
from src.cache.manager import CacheManager
from src.clients.anythingllm import AnythingLLMClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_llm_connection():
    """Test basic LLM connectivity"""
    print("\n=== Testing LLM Connection ===")
    try:
        # Load configuration first
        from src.core.config.manager import ConfigurationManager
        config_manager = ConfigurationManager()
        config_manager._config_file_path = "/home/lab/docaiche/test_config.yaml"  # Use test config
        await config_manager.load_configuration()
        config = get_system_configuration()
        
        if not config:
            print("✗ Configuration not loaded")
            return False
            
        llm_client = LLMProviderClient(config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict())
        
        # Simple test prompt
        response = await llm_client.generate("What is FastAPI in one sentence?")
        print(f"✓ LLM Response: {response[:100]}...")
        return True
    except Exception as e:
        print(f"✗ LLM Connection Failed: {e}")
        return False


async def test_query_analysis():
    """Test query analysis component"""
    print("\n=== Testing Query Analysis ===")
    try:
        # Load configuration first
        from src.core.config.manager import ConfigurationManager
        config_manager = ConfigurationManager()
        config_manager._config_file_path = "/home/lab/docaiche/test_config.yaml"  # Use test config
        await config_manager.load_configuration()
        config = get_system_configuration()
        
        if not config:
            print("✗ Configuration not loaded")
            return False
        llm_client = LLMProviderClient(config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict())
        
        from src.search.llm_query_analyzer import LLMQueryAnalyzer
        analyzer = LLMQueryAnalyzer(llm_client)
        
        test_query = "FastAPI async tutorial for beginners"
        intent = await analyzer.analyze_query(test_query)
        
        print(f"✓ Query: {test_query}")
        print(f"  Technology: {intent.technology}")
        print(f"  Doc Type: {intent.doc_type}")
        print(f"  Topics: {intent.topics}")
        print(f"  User Level: {intent.user_level}")
        
        return True
    except Exception as e:
        print(f"✗ Query Analysis Failed: {e}")
        return False


async def test_source_discovery():
    """Test documentation source discovery"""
    print("\n=== Testing Source Discovery ===")
    try:
        # Load configuration first
        from src.core.config.manager import ConfigurationManager
        config_manager = ConfigurationManager()
        config_manager._config_file_path = "/home/lab/docaiche/test_config.yaml"  # Use test config
        await config_manager.load_configuration()
        config = get_system_configuration()
        
        if not config:
            print("✗ Configuration not loaded")
            return False
        llm_client = LLMProviderClient(config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict())
        
        from src.search.llm_query_analyzer import LLMQueryAnalyzer, QueryIntent
        from src.enrichment.llm_source_finder import LLMSourceFinder
        
        # Create a test intent
        intent = QueryIntent(
            technology="fastapi",
            version=None,
            doc_type="tutorial",
            topics=["async", "getting started"],
            user_level="beginner"
        )
        
        finder = LLMSourceFinder(llm_client)
        sources = await finder.find_sources(intent)
        
        print(f"✓ Found {len(sources)} sources:")
        for source in sources[:3]:
            print(f"  - {source.name} ({source.source_type})")
            print(f"    URL: {source.url}")
            print(f"    Quality: {source.quality_score}")
        
        return True
    except Exception as e:
        print(f"✗ Source Discovery Failed: {e}")
        return False


async def test_full_pipeline():
    """Test the complete intelligent pipeline"""
    print("\n=== Testing Full Pipeline ===")
    
    try:
        # Initialize components
        from src.core.config.manager import ConfigurationManager
        config_manager = ConfigurationManager()
        await config_manager.load_configuration()
        config = get_system_configuration()
        
        if not config:
            print("✗ Configuration not loaded")
            return False
            
        llm_client = LLMProviderClient(config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict())
        
        # Get database and cache managers
        db_manager = await create_database_manager()
        cache_manager = CacheManager(config.redis)
        anythingllm_client = AnythingLLMClient(config.anythingllm)
        
        # Create enhanced orchestrator
        orchestrator = EnhancedSearchOrchestrator(
            db_manager=db_manager,
            cache_manager=cache_manager,
            anythingllm_client=anythingllm_client,
            llm_client=llm_client
        )
        
        # Test queries
        test_queries = [
            "FastAPI async tutorial for beginners",
            "React hooks comprehensive guide",
            "Django REST framework authentication",
            "Python asyncio advanced examples"
        ]
        
        for query in test_queries[:1]:  # Start with just one query for testing
            print(f"\n--- Testing: {query} ---")
            
            # First search (should fetch and cache)
            print("First search (fetching)...")
            start = time.time()
            
            try:
                results1 = await orchestrator.search(query)
                fetch_time = time.time() - start
                
                print(f"✓ Initial fetch completed in {fetch_time:.2f}s")
                print(f"  Results: {len(results1.results)}")
                print(f"  Cached: {results1.cached}")
                
                if results1.results:
                    print(f"  Top result: {results1.results[0]['title']}")
                
            except Exception as e:
                print(f"✗ First search failed: {e}")
                continue
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Second search (should hit cache)
            print("\nSecond search (cached)...")
            start = time.time()
            
            try:
                results2 = await orchestrator.search(query)
                cache_time = time.time() - start
                
                print(f"✓ Cache hit completed in {cache_time:.2f}s")
                print(f"  Results: {len(results2.results)}")
                print(f"  Cached: {results2.cached}")
                print(f"  Speedup: {fetch_time/cache_time:.1f}x faster")
                
            except Exception as e:
                print(f"✗ Second search failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Full Pipeline Test Failed: {e}")
        logger.exception("Full pipeline test error")
        return False


async def main():
    """Run all tests"""
    print("DocAIche Intelligent Pipeline Test Suite")
    print("=" * 50)
    
    # Run tests in order
    tests = [
        ("LLM Connection", test_llm_connection),
        ("Query Analysis", test_query_analysis),
        ("Source Discovery", test_source_discovery),
        ("Full Pipeline", test_full_pipeline)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The intelligent pipeline is ready.")
    else:
        print("\n⚠️  Some tests failed. Please check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())