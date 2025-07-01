#!/usr/bin/env python3
"""Test MCP configuration during startup"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config.loader import ConfigurationLoader

async def main():
    print("=== Testing MCP Configuration Loading ===")
    
    # Load configuration
    loader = ConfigurationLoader("config.yaml")
    config = await loader.load_hierarchical_configuration()
    
    print(f"\nConfig loaded. Has MCP? {hasattr(config, 'mcp')}")
    if hasattr(config, 'mcp'):
        print(f"MCP config: {config.mcp}")
        print(f"External search enabled: {config.mcp.external_search.enabled}")
        print(f"Number of providers: {len(config.mcp.external_search.providers)}")
        print(f"Provider names: {list(config.mcp.external_search.providers.keys())}")

if __name__ == "__main__":
    asyncio.run(main())