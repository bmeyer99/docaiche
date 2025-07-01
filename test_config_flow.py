#!/usr/bin/env python3
"""Test configuration flow"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test the actual flow
print("=== Testing get_system_configuration ===")
from src.core.config import get_system_configuration

config = get_system_configuration()
print(f"Config returned: {config}")
print(f"Config type: {type(config)}")

if config:
    print(f"Has MCP? {hasattr(config, 'mcp')}")
    if hasattr(config, 'mcp'):
        print(f"MCP config: {config.mcp}")
else:
    print("Config is None - not initialized yet")
    
# Try to initialize it properly
print("\n=== Testing proper initialization ===")
import asyncio
from src.core.config.manager import ConfigurationManager

async def test_proper_init():
    manager = ConfigurationManager()
    await manager.initialize("config.yaml")
    config = manager.get_configuration()
    print(f"Config after init: {config}")
    if config and hasattr(config, 'mcp'):
        print(f"MCP config: {config.mcp}")
        print(f"External search enabled: {config.mcp.external_search.enabled}")
        print(f"Number of providers: {len(config.mcp.external_search.providers)}")
    return config

config = asyncio.run(test_proper_init())