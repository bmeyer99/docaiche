#!/usr/bin/env python3
"""Test MCP configuration loading"""

import yaml
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config.models import MCPConfig, SystemConfiguration

# Load the YAML file
with open('config.yaml', 'r') as f:
    config_data = yaml.safe_load(f)

print("=== Raw YAML Data ===")
print(f"Top-level keys: {list(config_data.keys())}")

if 'mcp' in config_data:
    print(f"\nMCP section: {config_data['mcp']}")
    
    # Try to create MCPConfig
    try:
        mcp_config = MCPConfig(**config_data['mcp'])
        print(f"\nMCPConfig created successfully!")
        print(f"External search enabled: {mcp_config.external_search.enabled}")
        print(f"Number of providers: {len(mcp_config.external_search.providers)}")
        print(f"Provider names: {list(mcp_config.external_search.providers.keys())}")
        
        for name, provider in mcp_config.external_search.providers.items():
            print(f"\n{name}:")
            print(f"  enabled: {provider.enabled}")
            print(f"  priority: {provider.priority}")
            print(f"  api_key: {'<set>' if provider.api_key else '<not set>'}")
            
    except Exception as e:
        print(f"\nError creating MCPConfig: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\nNo 'mcp' section found in config.yaml")