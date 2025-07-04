import asyncio
import sys
sys.path.append('/app')

from src.core.config.manager import ConfigurationManager

async def update_brave_key():
    config_mgr = ConfigurationManager()
    
    # Get current config
    config = config_mgr.get_configuration()
    if config and config.mcp:
        mcp_config = config.mcp.model_dump()
        
        # Update Brave API key with a test key
        if 'external_search' in mcp_config and 'providers' in mcp_config['external_search']:
            if 'brave_search' in mcp_config['external_search']['providers']:
                # This is a dummy key for testing - replace with real key in production
                mcp_config['external_search']['providers']['brave_search']['api_key'] = 'BSA_test_key_12345'
                
                # Save to database
                await config_mgr.update_in_db('mcp', mcp_config)
                print("Updated Brave API key in database")
            else:
                print("brave_search provider not found")
        else:
            print("MCP config structure not found")
    else:
        print("No MCP config found")

asyncio.run(update_brave_key())