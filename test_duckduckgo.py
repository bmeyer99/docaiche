#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('/home/lab/docaiche')

from src.mcp.providers.implementations.duckduckgo import DuckDuckGoSearchProvider
from src.mcp.providers.models import ProviderConfig, ProviderType, SearchOptions

async def test_duckduckgo():
    # Create provider config
    config = ProviderConfig(
        provider_id="duckduckgo",
        provider_type=ProviderType.DUCKDUCKGO,
        enabled=True,
        api_key=None
    )
    
    # Create provider
    provider = DuckDuckGoSearchProvider(config)
    
    # Create search options
    options = SearchOptions(
        query="python programming",
        max_results=5
    )
    
    # Execute search
    print("Testing DuckDuckGo provider...")
    try:
        results = await provider.search(options)
        print(f"Got {len(results.results)} results")
        for i, result in enumerate(results.results):
            print(f"{i+1}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Snippet: {result.snippet[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await provider.cleanup()

if __name__ == "__main__":
    asyncio.run(test_duckduckgo())