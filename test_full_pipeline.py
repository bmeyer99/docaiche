#!/usr/bin/env python3
"""
Test the complete intelligent documentation pipeline with real fetching
"""

import asyncio
import time
import logging
import os

# Set environment variable for data directory
os.environ['DATA_DIR'] = './test_data'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.core.config import get_system_configuration
from src.core.config.manager import ConfigurationManager
from src.llm.client import LLMProviderClient
from src.search.orchestrator_enhanced import EnhancedSearchOrchestrator
from src.database.connection import create_database_manager
from src.cache.manager import CacheManager
from src.clients.anythingllm import AnythingLLMClient


async def test_pipeline_with_real_fetch():
    """Test the complete pipeline with actual documentation fetching"""
    
    print("\n" + "="*60)
    print("Testing Complete Intelligent Documentation Pipeline")
    print("="*60 + "\n")
    
    try:
        # Load configuration
        config_manager = ConfigurationManager()
        config_manager._config_file_path = "/home/lab/docaiche/test_config.yaml"
        await config_manager.load_configuration()
        config = get_system_configuration()
        
        if not config:
            print("❌ Configuration not loaded")
            return
            
        print("✅ Configuration loaded successfully")
        
        # Initialize components
        print("\n🔧 Initializing components...")
        
        llm_client = LLMProviderClient(
            config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict()
        )
        print("  ✓ LLM client initialized")
        
        db_manager = await create_database_manager()
        print("  ✓ Database manager initialized")
        
        cache_manager = CacheManager(config.redis)
        print("  ✓ Cache manager initialized")
        
        anythingllm_client = AnythingLLMClient(config.anythingllm)
        print("  ✓ AnythingLLM client initialized")
        
        # Create enhanced orchestrator
        orchestrator = EnhancedSearchOrchestrator(
            db_manager=db_manager,
            cache_manager=cache_manager,
            anythingllm_client=anythingllm_client,
            llm_client=llm_client
        )
        print("  ✓ Enhanced search orchestrator initialized")
        
        # Test queries that should trigger different types of fetching
        test_queries = [
            {
                "query": "FastAPI async endpoints tutorial for beginners",
                "description": "Should fetch from FastAPI official docs and GitHub"
            },
            {
                "query": "React hooks useState and useEffect guide",
                "description": "Should fetch from React docs and potentially community sources"
            },
            {
                "query": "Python asyncio concurrent tasks examples",
                "description": "Should fetch from Python official docs"
            }
        ]
        
        for test_case in test_queries[:1]:  # Start with just one for testing
            print(f"\n\n{'='*60}")
            print(f"Test Case: {test_case['description']}")
            print(f"Query: \"{test_case['query']}\"")
            print("="*60)
            
            # First search (should fetch and process)
            print("\n📥 First search (fetching from sources)...")
            start_time = time.time()
            
            try:
                results = await orchestrator.search(test_case['query'])
                fetch_time = time.time() - start_time
                
                print(f"\n✅ Search completed in {fetch_time:.2f} seconds")
                print(f"  - Total results: {results.total_count}")
                print(f"  - Cached: {results.cached}")
                print(f"  - Search time: {results.search_time_ms}ms")
                
                if results.results:
                    print("\n📄 Top results:")
                    for i, result in enumerate(results.results[:3]):
                        print(f"\n  {i+1}. {result['title']}")
                        print(f"     Source: {result.get('source', 'Unknown')}")
                        print(f"     Score: {result.get('relevance_score', 0):.2f}")
                        print(f"     Preview: {result.get('content', '')[:100]}...")
                        
                # Wait a moment
                await asyncio.sleep(2)
                
                # Second search (should hit cache)
                print("\n\n💾 Second search (testing cache)...")
                start_time = time.time()
                
                results2 = await orchestrator.search(test_case['query'])
                cache_time = time.time() - start_time
                
                print(f"\n✅ Cache search completed in {cache_time:.2f} seconds")
                print(f"  - Cached: {results2.cached}")
                print(f"  - Speedup: {fetch_time/cache_time:.1f}x faster")
                
            except Exception as e:
                print(f"\n❌ Search failed: {e}")
                logger.exception("Search error details")
                continue
        
        # Check what was actually fetched and stored
        print("\n\n📊 Pipeline Statistics:")
        
        # Check content in database
        content_query = """
        SELECT technology, COUNT(*) as doc_count, 
               COUNT(DISTINCT source_url) as source_count
        FROM content_metadata
        GROUP BY technology
        """
        content_stats = await db_manager.fetch_all(content_query)
        
        if content_stats:
            print("\n  Stored content by technology:")
            for stat in content_stats:
                print(f"    - {stat['technology']}: {stat['doc_count']} documents from {stat['source_count']} sources")
        
        # Check AnythingLLM workspaces
        try:
            workspaces = await anythingllm_client.list_workspaces()
            print(f"\n  AnythingLLM workspaces: {len(workspaces)}")
            for ws in workspaces:
                print(f"    - {ws.get('name', 'Unknown')}: {ws.get('documentCount', 0)} documents")
        except Exception as e:
            print(f"\n  Could not fetch AnythingLLM stats: {e}")
        
        print("\n✨ Pipeline test complete!")
        
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        logger.exception("Pipeline test error")


async def test_source_types():
    """Test that different source types are handled correctly"""
    
    print("\n\n" + "="*60)
    print("Testing Source Type Handling")
    print("="*60 + "\n")
    
    from src.core.config.manager import ConfigurationManager
    from src.core.config import get_system_configuration
    from src.llm.client import LLMProviderClient
    from src.enrichment.llm_source_finder import LLMSourceFinder
    from src.search.llm_query_analyzer import LLMQueryAnalyzer, QueryIntent
    
    # Load config
    config_manager = ConfigurationManager()
    config_manager._config_file_path = "/home/lab/docaiche/test_config.yaml"
    await config_manager.load_configuration()
    config = get_system_configuration()
    
    llm_client = LLMProviderClient(
        config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict()
    )
    
    # Test intent
    intent = QueryIntent(
        technology="fastapi",
        version=None,
        doc_type="tutorial",
        topics=["async", "endpoints"],
        user_level="beginner",
        related_technologies=["python", "asyncio"]
    )
    
    # Find sources
    source_finder = LLMSourceFinder(llm_client)
    sources = await source_finder.find_sources(intent)
    
    print("Found sources:")
    for source in sources:
        print(f"\n  - {source.name}")
        print(f"    Type: {source.source_type}")
        print(f"    URL: {source.url}")
        print(f"    Format: {source.format}")
        print(f"    Quality: {source.quality_score}")


async def main():
    """Run all tests"""
    
    # Test source discovery first
    await test_source_types()
    
    # Then test full pipeline
    await test_pipeline_with_real_fetch()


if __name__ == "__main__":
    asyncio.run(main())