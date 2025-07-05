#!/usr/bin/env python3
"""
Test script to add brave and brave2 providers to the database configuration
"""

import json
import sqlite3
import sys

# Test API keys
BRAVE_API_KEY = "test-brave-api-key-12345"
BRAVE2_API_KEY = "test-brave2-api-key-67890"

def add_brave_providers():
    """Add brave and brave2 providers to the MCP configuration in database"""
    try:
        # Connect to database
        conn = sqlite3.connect('/data/docaiche.db')
        cursor = conn.cursor()
        
        # Get current MCP configuration
        cursor.execute('SELECT value FROM system_config WHERE key = "mcp"')
        row = cursor.fetchone()
        
        if not row:
            print("No MCP configuration found in database")
            return False
            
        # Parse current config
        mcp_config = json.loads(row[0])
        providers = mcp_config.get('external_search', {}).get('providers', {})
        
        # Add brave provider with real API key
        providers['brave'] = {
            'enabled': True,
            'api_key': BRAVE_API_KEY,
            'priority': 10,
            'max_requests_per_minute': 60,
            'timeout_seconds': 5.0,
            'search_engine_id': None
        }
        
        # Add brave2 provider with different API key
        providers['brave2'] = {
            'enabled': True,
            'api_key': BRAVE2_API_KEY,
            'priority': 20,
            'max_requests_per_minute': 60,
            'timeout_seconds': 5.0,
            'search_engine_id': None
        }
        
        # Update the configuration
        mcp_config['external_search']['providers'] = providers
        
        # Save back to database
        cursor.execute(
            'UPDATE system_config SET value = ? WHERE key = "mcp"',
            (json.dumps(mcp_config),)
        )
        
        conn.commit()
        
        print("Successfully added brave providers:")
        print(f"  brave: API key = {BRAVE_API_KEY}")
        print(f"  brave2: API key = {BRAVE2_API_KEY}")
        
        # Verify the update
        cursor.execute('SELECT value FROM system_config WHERE key = "mcp"')
        updated_row = cursor.fetchone()
        updated_config = json.loads(updated_row[0])
        updated_providers = updated_config.get('external_search', {}).get('providers', {})
        
        print("\nAll MCP providers after update:")
        for pid, pconfig in updated_providers.items():
            api_key = pconfig.get('api_key', 'None')
            if len(api_key) > 20:
                api_key = api_key[:20] + '...'
            print(f"  {pid}: enabled={pconfig.get('enabled')}, api_key={api_key}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = add_brave_providers()
    sys.exit(0 if success else 1)