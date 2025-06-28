#!/usr/bin/env python3
"""Quick test of LLM connection"""

import asyncio
import logging
from pathlib import Path

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_connection():
    from src.core.config.manager import ConfigurationManager
    from src.core.config import get_system_configuration
    from src.llm.client import LLMProviderClient
    
    # Load test config
    config_manager = ConfigurationManager()
    config_manager._config_file_path = "/home/lab/docaiche/test_config.yaml"
    await config_manager.load_configuration()
    config = get_system_configuration()
    
    print(f"Config loaded: {config.app.environment}")
    print(f"AI config: {config.ai}")
    
    # Try to create LLM client
    ai_dict = config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict()
    print(f"AI dict: {ai_dict}")
    
    llm_client = LLMProviderClient(ai_dict)
    print(f"Providers initialized: {list(llm_client.providers.keys())}")
    
    if llm_client.providers:
        # Try a simple generation
        try:
            response = await llm_client.generate("Say 'Hello World'")
            print(f"Response: {response}")
        except Exception as e:
            print(f"Generation failed: {e}")
    else:
        print("No providers available")

if __name__ == "__main__":
    asyncio.run(test_connection())