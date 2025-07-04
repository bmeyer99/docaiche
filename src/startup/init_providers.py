"""
Provider Database Initialization

Initializes default provider configurations in the database at startup.
This ensures the database is the single source of truth for provider configurations.
"""

import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional

from src.core.config.manager import ConfigurationManager
from src.logging_config import MetricsLogger

logger = logging.getLogger(__name__)
metrics = MetricsLogger(logger)

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
            "gpt-4o-audio-preview",
            "gpt-4o-realtime-preview",
            "o1",
            "o1-mini",
            "o3",
            "o3-mini",
            "o4-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
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
            "claude-4-sonnet-20250515",
            "claude-4-opus-20250515",
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
            "llama-3.3-70b-versatile",
            "llama-3.3-70b-specdec",
            "llama-3.1-8b-instant",
            "llama-3.2-11b-vision-preview",
            "llama-3.2-90b-vision-preview",
            "llama-3-groq-70b-tool-use",
            "llama-3-groq-8b-tool-use",
            "gemma2-9b-it",
            "whisper-large-v3",
            "whisper-large-v3-turbo",
            "distil-whisper-large-v3-en",
            "compound-beta",
            "compound-beta-mini"
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
            "mistral-large-2411",
            "mistral-medium-2505",
            "mistral-small-2506",
            "codestral-2501",
            "pixtral-large-2411",
            "magistral-medium-2506",
            "magistral-small-2506",
            "mistral-saba-2502",
            "devstral-small-2505",
            "mistral-ocr-2505",
            "open-mixtral-8x22b-2404",
            "mistral-embed",
            "codestral-embed"
        ],
        "queryable": False,
        "defaultModel": "mistral-small-2506"
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
            "deepseek-reasoner",
            "deepseek-coder",
            "deepseek-coder-v2"
        ],
        "queryable": False,
        "defaultModel": "deepseek-chat"
    },
    "vertex": {
        "name": "Google Vertex AI",
        "type": "text_generation",
        "category": "enterprise",
        "description": "Google Cloud Vertex AI with enterprise security",
        "requiresApiKey": False,
        "supportsEmbedding": True,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "vertexProjectId": "",
            "vertexRegion": "us-central1",
            "vertexJsonCredentials": "",
            "timeout": 30,
            "maxRetries": 3
        },
        "models": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
            "text-bison",
            "textembedding-gecko"
        ],
        "queryable": False,
        "defaultModel": "gemini-1.5-flash"
    },
    "gemini": {
        "name": "Google Gemini",
        "type": "text_generation",
        "category": "enterprise",
        "description": "Google Gemini models for multimodal AI",
        "requiresApiKey": True,
        "supportsEmbedding": True,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
            "timeout": 30,
            "maxRetries": 3,
            "apiKey": ""
        },
        "models": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
            "text-embedding-004"
        ],
        "queryable": False,
        "defaultModel": "gemini-1.5-flash"
    },
    "bedrock": {
        "name": "AWS Bedrock",
        "type": "text_generation",
        "category": "enterprise",
        "description": "AWS Bedrock with enterprise-grade AI models",
        "requiresApiKey": False,
        "supportsEmbedding": True,
        "supportsChat": True,
        "status": "untested",
        "enabled": True,
        "config": {
            "awsRegion": "us-east-1",
            "awsAccessKey": "",
            "awsSecretKey": "",
            "awsSessionToken": "",
            "timeout": 30,
            "maxRetries": 3
        },
        "models": [
            "anthropic.claude-4-sonnet:0",
            "anthropic.claude-4-opus:0",
            "anthropic.claude-3-7-sonnet:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-5-haiku-20241022:0",
            "anthropic.claude-3-opus-20240229:0",
            "anthropic.claude-3-haiku-20240307:0",
            "meta.llama3-3-70b-instruct-v1:0",
            "meta.llama3-1-405b-instruct-v1:0",
            "meta.llama3-1-70b-instruct-v1:0",
            "meta.llama3-1-8b-instruct-v1:0",
            "mistral.pixtral-large-2411:0",
            "mistral.mistral-large-2411:0",
            "amazon.titan-text-premier-v1:0",
            "amazon.titan-embed-text-v2:0",
            "amazon.nova-pro-v1:0",
            "amazon.nova-lite-v1:0"
        ],
        "queryable": False,
        "defaultModel": "anthropic.claude-3-5-sonnet-20241022-v2:0"
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


async def initialize_providers(config_manager: ConfigurationManager = None) -> bool:
    """Initialize the database with default provider configurations"""
    start_time = time.time()
    correlation_id = f"init_providers_{int(time.time() * 1000)}"
    
    try:
        logger.info("🚀 Starting provider database initialization...", extra={
            "event": "provider_init_start",
            "correlation_id": correlation_id,
            "timestamp": datetime.now().isoformat(),
            "provider_count": len(DEFAULT_PROVIDERS),
            "operation": "startup_initialization"
        })
        
        # Use direct database connection for startup initialization
        # This bypasses the configuration manager's dependency on itself
        from src.database.manager import DatabaseManager
        import os
        
        # Get DATABASE_URL from environment
        database_url = os.environ.get("DATABASE_URL")
        
        if not database_url:
            # Build PostgreSQL URL from environment variables
            host = os.environ.get("POSTGRES_HOST", "postgres")
            port = os.environ.get("POSTGRES_PORT", "5432")
            db = os.environ.get("POSTGRES_DB", "docaiche")
            user = os.environ.get("POSTGRES_USER", "docaiche")
            password = os.environ.get("POSTGRES_PASSWORD", "docaiche-secure-password-2025")
            
            database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
        
        logger.debug(f"Using database URL: {database_url.split('@')[0]}...", extra={
            "event": "provider_init_db_connect",
            "correlation_id": correlation_id,
            "database_url": database_url.split('@')[0] + "..."
        })
        
        db_manager = DatabaseManager(database_url)
        await db_manager.initialize()
        
        # Initialize providers with enhanced logging
        provider_results = await _initialize_providers_direct(db_manager, correlation_id)
        
        # Initialize model selection with enhanced logging
        model_selection_result = await _initialize_model_selection_direct(db_manager, correlation_id)
        
        # DatabaseManager doesn't have a close method - it manages connections internally
        
        # Calculate metrics
        duration = time.time() - start_time
        
        # Log completion with detailed metrics
        logger.info("✅ Provider initialization completed successfully", extra={
            "event": "provider_init_complete",
            "correlation_id": correlation_id,
            "duration_seconds": round(duration, 3),
            "providers_initialized": provider_results.get("initialized", 0),
            "providers_updated": provider_results.get("updated", 0),
            "providers_skipped": provider_results.get("skipped", 0),
            "model_selection_configured": model_selection_result,
            "operation": "startup_initialization",
            "status": "success"
        })
        
        # Record metrics
        metrics.record_metric("provider_initialization_duration", duration, {
            "status": "success",
            "providers_total": len(DEFAULT_PROVIDERS)
        })
        
        metrics.record_metric("provider_initialization_count", 1, {
            "status": "success",
            "operation": "startup"
        })
        
        return True
        
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(f"❌ Provider initialization failed: {str(e)}", extra={
            "event": "provider_init_error",
            "correlation_id": correlation_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": round(duration, 3),
            "operation": "startup_initialization",
            "status": "failed"
        })
        
        # Log the full traceback for debugging
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        
        # Record error metrics
        metrics.record_metric("provider_initialization_duration", duration, {
            "status": "failed",
            "error_type": type(e).__name__
        })
        
        metrics.record_metric("provider_initialization_count", 1, {
            "status": "failed",
            "operation": "startup"
        })
        
        return False


async def _initialize_providers_direct(db_manager, correlation_id: str) -> Dict[str, int]:
    """Initialize provider configurations, checking for existing data"""
    logger.info(f"Initializing {len(DEFAULT_PROVIDERS)} provider configurations...", extra={
        "event": "providers_init_start",
        "correlation_id": correlation_id,
        "provider_count": len(DEFAULT_PROVIDERS)
    })
    
    providers_initialized = 0
    providers_updated = 0
    providers_skipped = 0
    
    for provider_id, provider_config in DEFAULT_PROVIDERS.items():
        provider_start_time = time.time()
        
        try:
            config_key = f"ai.providers.{provider_id}"
            
            # Check if provider configuration already exists (direct database query)
            existing_config = await _get_config_from_db(db_manager, config_key)
            
            if existing_config:
                logger.debug(f"⏭️  Provider '{provider_id}' already configured, checking for updates...", extra={
                    "event": "provider_exists",
                    "correlation_id": correlation_id,
                    "provider_id": provider_id,
                    "provider_name": provider_config.get("name", provider_id)
                })
                
                # Check for new models and safe configuration updates
                update_result = await _update_provider_if_needed_direct(
                    db_manager, provider_id, provider_config, existing_config, correlation_id
                )
                
                if update_result:
                    providers_updated += 1
                else:
                    providers_skipped += 1
                continue
            
            # Initialize new provider configuration
            logger.info(f"🔧 Initializing provider: {provider_id}", extra={
                "event": "provider_init_start",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "provider_name": provider_config.get("name", provider_id),
                "provider_category": provider_config.get("category", "unknown"),
                "model_count": len(provider_config.get("models", []))
            })
            
            # Prepare configuration for database storage
            # Don't include createdAt as it's not in the schema
            db_config = {
                **provider_config,
                "initializedBy": "startup_init",
                "initTimestamp": datetime.now().isoformat()
            }
            
            # Save to database (direct)
            await _save_config_to_db(db_manager, config_key, db_config)
            
            provider_duration = time.time() - provider_start_time
            
            logger.info(f"✅ Provider '{provider_id}' initialized with {len(provider_config.get('models', []))} models", extra={
                "event": "provider_init_complete",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "provider_name": provider_config.get("name", provider_id),
                "provider_category": provider_config.get("category", "unknown"),
                "model_count": len(provider_config.get("models", [])),
                "duration_seconds": round(provider_duration, 3),
                "status": "initialized"
            })
            
            # Record individual provider metrics
            metrics.record_metric("provider_config_operation_duration", provider_duration, {
                "provider_id": provider_id,
                "operation": "initialize",
                "status": "success"
            })
            
            providers_initialized += 1
            
        except Exception as e:
            provider_duration = time.time() - provider_start_time
            
            logger.error(f"❌ Failed to initialize provider '{provider_id}': {e}", extra={
                "event": "provider_init_error",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": round(provider_duration, 3),
                "status": "failed"
            })
            
            # Record error metrics
            metrics.record_metric("provider_config_operation_duration", provider_duration, {
                "provider_id": provider_id,
                "operation": "initialize",
                "status": "failed",
                "error_type": type(e).__name__
            })
            
            continue
            
    logger.info(f"Provider initialization summary: {providers_initialized} initialized, {providers_updated} updated, {providers_skipped} skipped (existing)", extra={
        "event": "providers_init_summary",
        "correlation_id": correlation_id,
        "providers_initialized": providers_initialized,
        "providers_updated": providers_updated,
        "providers_skipped": providers_skipped,
        "total_providers": len(DEFAULT_PROVIDERS)
    })
    
    return {
        "initialized": providers_initialized,
        "updated": providers_updated,
        "skipped": providers_skipped
    }


async def _update_provider_if_needed_direct(db_manager, provider_id: str, new_config: Dict[str, Any], existing_config: Dict[str, Any], correlation_id: str) -> bool:
    """Update provider models and safe configuration updates if needed"""
    update_start_time = time.time()
    
    try:
        existing_models = set(existing_config.get("models", []))
        new_models = set(new_config.get("models", []))
        
        # Find models that are in the new config but not in existing config
        additional_models = new_models - existing_models
        
        config_updated = False
        updates = []
        
        # Check for new models
        if additional_models:
            logger.info(f"📦 Adding {len(additional_models)} new models to existing provider '{provider_id}': {list(additional_models)}", extra={
                "event": "provider_models_update",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "new_models": list(additional_models),
                "new_model_count": len(additional_models),
                "existing_model_count": len(existing_models)
            })
            
            # Update the existing config with new models
            updated_models = list(existing_models | new_models)  # Union of both sets
            existing_config["models"] = updated_models
            config_updated = True
            updates.append(f"{len(additional_models)} new models")
        
        # Check for safe configuration updates (non-breaking changes only)
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
            existing_config["updateTimestamp"] = datetime.now().isoformat()
            existing_config["updatedBy"] = "startup_update"
            
            # Save updated configuration
            config_key = f"ai.providers.{provider_id}"
            await _save_config_to_db(db_manager, config_key, existing_config)
            
            update_duration = time.time() - update_start_time
            
            logger.info(f"✅ Provider '{provider_id}' updated: {', '.join(updates)}", extra={
                "event": "provider_update_complete",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "provider_name": existing_config.get("name", provider_id),
                "updates": updates,
                "duration_seconds": round(update_duration, 3),
                "status": "updated"
            })
            
            # Record update metrics
            metrics.record_metric("provider_config_operation_duration", update_duration, {
                "provider_id": provider_id,
                "operation": "update",
                "status": "success"
            })
            
            return True
        else:
            logger.debug(f"⏭️  Provider '{provider_id}' is up to date, no changes needed", extra={
                "event": "provider_no_update",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "status": "skipped"
            })
            return False
            
    except Exception as e:
        update_duration = time.time() - update_start_time
        
        logger.error(f"❌ Failed to update provider '{provider_id}': {e}", extra={
            "event": "provider_update_error",
            "correlation_id": correlation_id,
            "provider_id": provider_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": round(update_duration, 3),
            "status": "failed"
        })
        
        # Record error metrics
        metrics.record_metric("provider_config_operation_duration", update_duration, {
            "provider_id": provider_id,
            "operation": "update",
            "status": "failed",
            "error_type": type(e).__name__
        })
        
        return False


async def _initialize_model_selection_direct(db_manager, correlation_id: str) -> bool:
    """Initialize default model selection if not already configured"""
    selection_start_time = time.time()
    
    try:
        config_key = "ai.model_selection"
        
        # Check if model selection already exists
        existing_selection = await _get_config_from_db(db_manager, config_key)
        
        if existing_selection:
            logger.info("⏭️  Model selection already configured, skipping to preserve user settings", extra={
                "event": "model_selection_exists",
                "correlation_id": correlation_id,
                "text_provider": existing_selection.get("textGeneration", {}).get("provider"),
                "text_model": existing_selection.get("textGeneration", {}).get("model"),
                "embeddings_provider": existing_selection.get("embeddings", {}).get("provider"),
                "embeddings_model": existing_selection.get("embeddings", {}).get("model"),
                "status": "skipped"
            })
            return False
            
        logger.info("🔧 Initializing default model selection...", extra={
            "event": "model_selection_init_start",
            "correlation_id": correlation_id,
            "default_text_provider": DEFAULT_MODEL_SELECTION["textGeneration"]["provider"],
            "default_text_model": DEFAULT_MODEL_SELECTION["textGeneration"]["model"],
            "default_embeddings_provider": DEFAULT_MODEL_SELECTION["embeddings"]["provider"],
            "default_embeddings_model": DEFAULT_MODEL_SELECTION["embeddings"]["model"]
        })
        
        # Prepare model selection configuration
        db_config = {
            **DEFAULT_MODEL_SELECTION,
            "initializedBy": "startup_init",
            "initTimestamp": datetime.now().isoformat()
        }
        
        # Save to database
        await _save_config_to_db(db_manager, config_key, db_config)
        
        selection_duration = time.time() - selection_start_time
        
        logger.info(f"✅ Model selection initialized: Text='{DEFAULT_MODEL_SELECTION['textGeneration']['provider']}/{DEFAULT_MODEL_SELECTION['textGeneration']['model']}', Embeddings='{DEFAULT_MODEL_SELECTION['embeddings']['provider']}/{DEFAULT_MODEL_SELECTION['embeddings']['model']}'", extra={
            "event": "model_selection_init_complete",
            "correlation_id": correlation_id,
            "text_provider": DEFAULT_MODEL_SELECTION["textGeneration"]["provider"],
            "text_model": DEFAULT_MODEL_SELECTION["textGeneration"]["model"],
            "embeddings_provider": DEFAULT_MODEL_SELECTION["embeddings"]["provider"],
            "embeddings_model": DEFAULT_MODEL_SELECTION["embeddings"]["model"],
            "shared_provider": DEFAULT_MODEL_SELECTION.get("sharedProvider", False),
            "duration_seconds": round(selection_duration, 3),
            "status": "initialized"
        })
        
        # Record model selection metrics
        metrics.record_metric("model_selection_operation_duration", selection_duration, {
            "operation": "initialize",
            "status": "success"
        })
        
        return True
        
    except Exception as e:
        selection_duration = time.time() - selection_start_time
        
        logger.error(f"❌ Failed to initialize model selection: {e}", extra={
            "event": "model_selection_init_error",
            "correlation_id": correlation_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": round(selection_duration, 3),
            "status": "failed"
        })
        
        # Record error metrics
        metrics.record_metric("model_selection_operation_duration", selection_duration, {
            "operation": "initialize",
            "status": "failed",
            "error_type": type(e).__name__
        })
        
        return False


# Direct database helper functions (bypass configuration manager circular dependency)

async def _get_config_from_db(db_manager, config_key: str) -> Optional[Dict[str, Any]]:
    """Get configuration value from database directly"""
    try:
        row = await db_manager.fetch_one(
            "SELECT value FROM system_config WHERE key = :param_0",
            (config_key,)
        )
        
        if row:
            import json
            # Handle both dict and Row object formats
            if isinstance(row, dict):
                value_str = row.get('value')
            else:
                value_str = row.value if hasattr(row, 'value') else None
            
            if value_str:
                # Handle JSONB values (PostgreSQL returns dict directly)
                if isinstance(value_str, str):
                    return json.loads(value_str)
                else:
                    return value_str
        return None
            
    except Exception as e:
        logger.error(f"Failed to get config '{config_key}' from database: {e}")
        return None


async def _save_config_to_db(db_manager, config_key: str, config_value: Any) -> None:
    """Save configuration value to database directly"""
    try:
        import json
        
        # For JSONB columns, pass the value directly (PostgreSQL will handle serialization)
        # Use PostgreSQL UPSERT syntax to handle both insert and update
        # SystemConfig schema has: key, value, schema_version, updated_at, updated_by
        await db_manager.execute(
            """
            INSERT INTO system_config (key, value, schema_version, updated_at, updated_by)
            VALUES (:param_0, :param_1::jsonb, :param_2, CURRENT_TIMESTAMP, :param_3)
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value,
                schema_version = EXCLUDED.schema_version,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = EXCLUDED.updated_by
            """,
            (config_key, json.dumps(config_value, default=str), "1.0", "startup_init")
        )
            
    except Exception as e:
        logger.error(f"Failed to save config '{config_key}' to database: {e}")
        raise