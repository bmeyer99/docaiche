"""
Configuration Schemas for Search Providers
==========================================

JSON schemas for provider configuration validation.
"""

from typing import Dict, Any

# Base schema shared by all providers
BASE_PROVIDER_SCHEMA = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean",
            "description": "Whether this provider is enabled",
            "default": True
        },
        "priority": {
            "type": "integer",
            "description": "Provider priority (lower = higher priority)",
            "minimum": 0,
            "default": 100
        },
        "timeout_seconds": {
            "type": "number",
            "description": "Request timeout in seconds",
            "minimum": 1.0,
            "maximum": 30.0,
            "default": 5.0
        },
        "max_retries": {
            "type": "integer",
            "description": "Maximum retry attempts",
            "minimum": 0,
            "maximum": 5,
            "default": 2
        },
        "circuit_breaker_threshold": {
            "type": "integer",
            "description": "Failures before circuit opens",
            "minimum": 1,
            "maximum": 10,
            "default": 3
        },
        "circuit_breaker_timeout": {
            "type": "integer",
            "description": "Seconds before circuit breaker resets",
            "minimum": 10,
            "maximum": 600,
            "default": 60
        }
    },
    "additionalProperties": True
}

# Brave Search configuration schema
BRAVE_SCHEMA = {
    **BASE_PROVIDER_SCHEMA,
    "properties": {
        **BASE_PROVIDER_SCHEMA["properties"],
        "api_key": {
            "type": "string",
            "description": "Brave Search API key",
            "minLength": 32,
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "goggles_id": {
            "type": "string",
            "description": "Optional Goggles ID for custom ranking",
            "default": None
        },
        "search_lang": {
            "type": "string",
            "description": "Default search language",
            "pattern": "^[a-z]{2}$",
            "default": "en"
        },
        "country": {
            "type": "string",
            "description": "Default country for results",
            "pattern": "^[A-Z]{2}$",
            "default": "US"
        }
    },
    "required": ["api_key"]
}

# Google Custom Search configuration schema
GOOGLE_SCHEMA = {
    **BASE_PROVIDER_SCHEMA,
    "properties": {
        **BASE_PROVIDER_SCHEMA["properties"],
        "api_key": {
            "type": "string",
            "description": "Google API key",
            "minLength": 20
        },
        "search_engine_id": {
            "type": "string",
            "description": "Custom Search Engine ID (cx parameter)",
            "minLength": 10
        },
        "site_search": {
            "type": "array",
            "description": "Limit search to specific sites",
            "items": {
                "type": "string",
                "format": "hostname"
            },
            "default": []
        },
        "file_types": {
            "type": "array",
            "description": "Preferred file types",
            "items": {
                "type": "string",
                "enum": ["pdf", "doc", "docx", "html", "md", "txt"]
            },
            "default": []
        }
    },
    "required": ["api_key", "search_engine_id"]
}

# Bing Web Search configuration schema
BING_SCHEMA = {
    **BASE_PROVIDER_SCHEMA,
    "properties": {
        **BASE_PROVIDER_SCHEMA["properties"],
        "api_key": {
            "type": "string",
            "description": "Bing Search API key (Ocp-Apim-Subscription-Key)",
            "minLength": 32
        },
        "endpoint": {
            "type": "string",
            "description": "API endpoint URL",
            "format": "uri",
            "default": "https://api.bing.microsoft.com/v7.0/search"
        },
        "market": {
            "type": "string",
            "description": "Default market (e.g., en-US)",
            "pattern": "^[a-z]{2}-[A-Z]{2}$",
            "default": "en-US"
        },
        "response_filter": {
            "type": "array",
            "description": "Types of results to include",
            "items": {
                "type": "string",
                "enum": ["Webpages", "News", "Images", "Videos"]
            },
            "default": ["Webpages"]
        }
    },
    "required": ["api_key"]
}

# DuckDuckGo configuration schema (no API key required)
DUCKDUCKGO_SCHEMA = {
    **BASE_PROVIDER_SCHEMA,
    "properties": {
        **BASE_PROVIDER_SCHEMA["properties"],
        "region": {
            "type": "string",
            "description": "Region for results (e.g., us-en)",
            "pattern": "^[a-z]{2}-[a-z]{2}$",
            "default": "us-en"
        },
        "safe_search": {
            "type": "string",
            "description": "Safe search level",
            "enum": ["strict", "moderate", "off"],
            "default": "moderate"
        },
        "no_redirect": {
            "type": "boolean",
            "description": "Disable redirect following",
            "default": True
        },
        "no_html": {
            "type": "boolean",
            "description": "Request JSON responses where available",
            "default": False
        }
    }
}

# SearXNG configuration schema
SEARXNG_SCHEMA = {
    **BASE_PROVIDER_SCHEMA,
    "properties": {
        **BASE_PROVIDER_SCHEMA["properties"],
        "instance_url": {
            "type": "string",
            "description": "SearXNG instance URL",
            "format": "uri",
            "default": "https://search.nixnet.services"
        },
        "api_key": {
            "type": "string",
            "description": "Optional API key for private instances",
            "default": None
        },
        "engines": {
            "type": "array",
            "description": "Specific engines to use",
            "items": {
                "type": "string"
            },
            "default": ["google", "bing", "duckduckgo", "github", "stackoverflow"]
        },
        "categories": {
            "type": "array",
            "description": "Search categories to include",
            "items": {
                "type": "string",
                "enum": ["general", "it", "science", "files", "map", "music", "news", "social_media", "videos"]
            },
            "default": ["general", "it", "science"]
        },
        "language": {
            "type": "string",
            "description": "Default language",
            "default": "en"
        },
        "time_range": {
            "type": "string",
            "description": "Default time range",
            "enum": ["", "day", "week", "month", "year"],
            "default": ""
        }
    }
}

# Map provider types to their schemas
PROVIDER_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "brave": BRAVE_SCHEMA,
    "google": GOOGLE_SCHEMA,
    "bing": BING_SCHEMA,
    "duckduckgo": DUCKDUCKGO_SCHEMA,
    "searxng": SEARXNG_SCHEMA
}

def get_provider_schema(provider_type: str) -> Dict[str, Any]:
    """
    Get configuration schema for a provider type.
    
    Args:
        provider_type: Type of provider
        
    Returns:
        JSON schema for provider configuration
        
    Raises:
        ValueError: If provider type not found
    """
    schema = PROVIDER_SCHEMAS.get(provider_type.lower())
    if not schema:
        raise ValueError(f"Unknown provider type: {provider_type}")
    return schema

def validate_provider_config(provider_type: str, config: Dict[str, Any]) -> bool:
    """
    Validate provider configuration against schema.
    
    Args:
        provider_type: Type of provider
        config: Configuration to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If validation fails with details
    """
    try:
        import jsonschema
        schema = get_provider_schema(provider_type)
        jsonschema.validate(config, schema)
        return True
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid configuration: {e.message}")
    except ImportError:
        # Fallback if jsonschema not available
        schema = get_provider_schema(provider_type)
        required = schema.get("required", [])
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        return True