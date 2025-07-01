#!/usr/bin/env python3
"""
Database Provider Initialization Script

This script initializes the database with default provider configurations
at build time, making the database the single source of truth for all
provider settings including default models and configurations.

Key Features:
- Checks for existing data to avoid overwriting user configurations
- Supports incremental updates when new providers are added
- Persists across container reboots
- Maintains backward compatibility
"""

import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration manager
try:
    from src.core.config.manager import ConfigurationManager
    from src.core.config.database import DatabaseConfig
except ImportError as e:
    logger.error(f"Failed to import configuration modules: {e}")
    raise

# Default provider configurations with models
DEFAULT_PROVIDERS = {
    "ollama": {
        "name": "Ollama",
        "type": "text_generation",
        "category": "local",
        "description": "Local LLM inference server with support for multiple models",
        "requiresApiKey": False,
        "supportsEmbedding": True,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "http://localhost:11434/api",
            "timeout": 30,
            "maxRetries": 3
        },
        "models": [
            "llama3.2:3b",
            "llama3.2:1b", 
            "llama3.1:8b",
            "mistral:7b",
            "codellama:7b",
            "phi3:3.8b",
            "gemma2:2b"
        ],
        "queryable": True,
        "defaultModel": "llama3.2:3b"
    },
    "lmstudio": {
        "name": "LM Studio",
        "type": "text_generation",
        "category": "local",
        "description": "Local model inference with LM Studio's OpenAI-compatible API",
        "requiresApiKey": False,
        "supportsEmbedding": False,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "http://localhost:1234/v1",
            "timeout": 30,
            "maxRetries": 3
        },
        "models": [
            "local-model",
            "llama-3.2-3b-instruct",
            "mistral-7b-instruct",
            "codellama-7b-instruct"
        ],
        "queryable": True,
        "defaultModel": "local-model"
    },
    "openai": {
        "name": "OpenAI",
        "type": "text_generation",
        "category": "cloud",
        "description": "OpenAI GPT models and embeddings",
        "requiresApiKey": True,
        "supportsEmbedding": True,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "https://api.openai.com/v1",
            "timeout": 30,
            "maxRetries": 3,
            "apiKey": ""
        },
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "text-embedding-3-large",
            "text-embedding-3-small",
            "text-embedding-ada-002"
        ],
        "queryable": False,
        "defaultModel": "gpt-4o-mini"
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "type": "text_generation", 
        "category": "cloud",
        "description": "Anthropic Claude models for advanced reasoning",
        "requiresApiKey": True,
        "supportsEmbedding": False,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "https://api.anthropic.com",
            "timeout": 30,
            "maxRetries": 3,
            "apiKey": ""
        },
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        "queryable": False,
        "defaultModel": "claude-3-5-sonnet-20241022"
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "text_generation",
        "category": "cloud",
        "description": "Access to multiple AI models through a unified API",
        "requiresApiKey": True,
        "supportsEmbedding": False,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "https://openrouter.ai/api/v1",
            "timeout": 30,
            "maxRetries": 3,
            "apiKey": ""
        },
        "models": [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.1-8b-instruct",
            "mistralai/mistral-7b-instruct",
            "google/gemini-pro"
        ],
        "queryable": True,
        "defaultModel": "anthropic/claude-3.5-sonnet"
    },
    "groq": {
        "name": "Groq",
        "type": "text_generation",
        "category": "cloud",
        "description": "Ultra-fast inference with Groq's LPU technology",
        "requiresApiKey": True,
        "supportsEmbedding": False,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "https://api.groq.com/openai/v1", 
            "timeout": 30,
            "maxRetries": 3,
            "apiKey": ""
        },
        "models": [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ],
        "queryable": False,
        "defaultModel": "llama-3.1-8b-instant"
    },
    "mistral": {
        "name": "Mistral AI",
        "type": "text_generation",
        "category": "cloud", 
        "description": "Mistral AI's efficient and powerful language models",
        "requiresApiKey": True,
        "supportsEmbedding": True,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "https://api.mistral.ai/v1",
            "timeout": 30,
            "maxRetries": 3,
            "apiKey": ""
        },
        "models": [
            "mistral-large-latest",
            "mistral-medium-latest", 
            "mistral-small-latest",
            "codestral-latest",
            "mistral-embed"
        ],
        "queryable": False,
        "defaultModel": "mistral-small-latest"
    },
    "deepseek": {
        "name": "DeepSeek",
        "type": "text_generation",
        "category": "cloud",
        "description": "DeepSeek's advanced reasoning and coding models",
        "requiresApiKey": True,
        "supportsEmbedding": False,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "https://api.deepseek.com/v1",
            "timeout": 30,
            "maxRetries": 3,
            "apiKey": ""
        },
        "models": [
            "deepseek-chat",
            "deepseek-coder",
            "deepseek-reasoner"
        ],
        "queryable": False,
        "defaultModel": "deepseek-chat"
    }
}

# Default model selection configuration
DEFAULT_MODEL_SELECTION = {
    "textGeneration": {
        "provider": "ollama",
        "model": "llama3.2:3b"
    },
    "embeddings": {
        "provider": "ollama", 
        "model": "nomic-embed-text"
    },
    "sharedProvider": True
}


class ProviderInitializer:
    """Handles initialization of provider configurations in the database"""
    
    def __init__(self):
        self.config_manager: Optional[ConfigurationManager] = None
        
    async def initialize(self) -> bool:
        """Initialize the database with default provider configurations"""
        try:
            # Initialize configuration manager
            logger.info("Initializing configuration manager...")
            self.config_manager = ConfigurationManager()
            await self.config_manager.initialize()
            
            # Check database connectivity
            if not await self._check_database_connectivity():
                logger.error("Database connectivity check failed")
                return False
                
            # Initialize providers
            logger.info("Starting provider initialization...")
            await self._initialize_providers()
            
            # Initialize model selection
            await self._initialize_model_selection()
            
            logger.info("✅ Provider initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Provider initialization failed: {e}")
            return False
        finally:
            if self.config_manager:
                await self.config_manager.close()
                
    async def _check_database_connectivity(self) -> bool:
        """Check if database is accessible"""
        try:
            # Try a simple operation to verify connectivity
            test_key = "system.db_connectivity_test"
            await self.config_manager.update_in_db(test_key, {"test": True, "timestamp": datetime.now().isoformat()})
            result = await self.config_manager.get_from_db(test_key)
            
            if result and result.get("test") is True:
                logger.info("✅ Database connectivity verified")
                return True
            else:
                logger.error("❌ Database connectivity test failed - no valid response")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database connectivity test failed: {e}")
            return False
            
    async def _initialize_providers(self) -> None:
        """Initialize provider configurations, checking for existing data"""
        logger.info(f"Initializing {len(DEFAULT_PROVIDERS)} provider configurations...")
        
        providers_initialized = 0
        providers_skipped = 0
        
        for provider_id, provider_config in DEFAULT_PROVIDERS.items():
            try:
                config_key = f"ai.providers.{provider_id}"
                
                # Check if provider configuration already exists
                existing_config = await self.config_manager.get_from_db(config_key)
                
                if existing_config:
                    logger.info(f"⏭️  Provider '{provider_id}' already configured, skipping to preserve user settings")
                    providers_skipped += 1
                    
                    # However, we can still add new models if the provider structure supports it
                    await self._update_provider_models_if_needed(provider_id, provider_config, existing_config)
                    continue
                
                # Initialize new provider configuration
                logger.info(f"🔧 Initializing provider: {provider_id}")
                
                # Prepare configuration for database storage
                db_config = {
                    "name": provider_config["name"],
                    "type": provider_config["type"],
                    "category": provider_config["category"],
                    "description": provider_config["description"],
                    "requiresApiKey": provider_config["requiresApiKey"],
                    "supportsEmbedding": provider_config["supportsEmbedding"],
                    "supportsChat": provider_config["supportsChat"],
                    "status": provider_config["status"],
                    "enabled": provider_config["enabled"],
                    "config": provider_config["config"],
                    "models": provider_config["models"],
                    "queryable": provider_config["queryable"],
                    "defaultModel": provider_config["defaultModel"],
                    "createdAt": datetime.now().isoformat(),
                    "initializedBy": "build_time_init"
                }
                
                # Save to database
                await self.config_manager.update_in_db(config_key, db_config)
                
                logger.info(f"✅ Provider '{provider_id}' initialized with {len(provider_config.get('models', []))} models")
                providers_initialized += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize provider '{provider_id}': {e}")
                continue
                
        logger.info(f"Provider initialization summary: {providers_initialized} initialized, {providers_skipped} skipped (existing)")
        
    async def _update_provider_models_if_needed(self, provider_id: str, new_config: Dict[str, Any], existing_config: Dict[str, Any]) -> None:
        """Update provider models if new ones are available in the default config"""
        try:
            existing_models = set(existing_config.get("models", []))
            new_models = set(new_config.get("models", []))
            
            # Find models that are in the new config but not in existing config
            additional_models = new_models - existing_models
            
            # Also check for other config updates (like base URLs, descriptions, etc.)
            config_updated = False
            updates = []
            
            # Check for new models
            if additional_models:
                logger.info(f"📦 Adding {len(additional_models)} new models to existing provider '{provider_id}': {list(additional_models)}")
                
                # Update the existing config with new models
                updated_models = list(existing_models | new_models)  # Union of both sets
                existing_config["models"] = updated_models
                config_updated = True
                updates.append(f"{len(additional_models)} new models")
            
            # Check for other configuration updates (non-breaking changes only)
            safe_update_fields = {
                "description": "description",
                "supportsEmbedding": "supportsEmbedding", 
                "supportsChat": "supportsChat",
                "queryable": "queryable"
            }
            
            for field, field_name in safe_update_fields.items():
                if field in new_config and existing_config.get(field) != new_config[field]:
                    # Only update if it's an enhancement (not a downgrade)
                    old_value = existing_config.get(field)
                    new_value = new_config[field]
                    
                    # For boolean fields, only update if new value is True and old was False/None
                    if isinstance(new_value, bool) and not old_value and new_value:
                        existing_config[field] = new_value
                        config_updated = True
                        updates.append(f"enabled {field_name}")
                    # For string fields, update if new description is longer/more detailed
                    elif isinstance(new_value, str) and len(str(new_value)) > len(str(old_value or "")):
                        existing_config[field] = new_value  
                        config_updated = True
                        updates.append(f"updated {field_name}")
            
            # Update metadata if any changes were made
            if config_updated:
                existing_config["lastUpdated"] = datetime.now().isoformat()
                existing_config["updatedBy"] = "build_time_model_update"
                
                # Save updated configuration
                config_key = f"ai.providers.{provider_id}"
                await self.config_manager.update_in_db(config_key, existing_config)
                
                logger.info(f"✅ Provider '{provider_id}' updated: {', '.join(updates)}")
            else:
                logger.info(f"⏭️  Provider '{provider_id}' is up to date, no changes needed")
                
        except Exception as e:
            logger.error(f"❌ Failed to update models for provider '{provider_id}': {e}")
            
    async def _initialize_model_selection(self) -> None:
        """Initialize default model selection if not already configured"""
        try:
            config_key = "ai.model_selection"
            
            # Check if model selection already exists
            existing_selection = await self.config_manager.get_from_db(config_key)
            
            if existing_selection:
                logger.info("⏭️  Model selection already configured, skipping to preserve user settings")
                return
                
            logger.info("🔧 Initializing default model selection...")
            
            # Prepare model selection configuration
            db_config = {
                **DEFAULT_MODEL_SELECTION,
                "createdAt": datetime.now().isoformat(),
                "initializedBy": "build_time_init"
            }
            
            # Save to database
            await self.config_manager.update_in_db(config_key, db_config)
            
            logger.info(f"✅ Model selection initialized: Text='{DEFAULT_MODEL_SELECTION['textGeneration']['provider']}/{DEFAULT_MODEL_SELECTION['textGeneration']['model']}', Embeddings='{DEFAULT_MODEL_SELECTION['embeddings']['provider']}/{DEFAULT_MODEL_SELECTION['embeddings']['model']}'")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize model selection: {e}")


async def main():
    """Main initialization function"""
    logger.info("🚀 Starting provider database initialization...")
    
    initializer = ProviderInitializer()
    success = await initializer.initialize()
    
    if success:
        logger.info("🎉 Provider database initialization completed successfully!")
        return 0
    else:
        logger.error("💥 Provider database initialization failed!")
        return 1


if __name__ == "__main__": 
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)