"""
Configuration Adapter for MCP to FastAPI Integration
===================================================

Adapts MCP configuration resource requests to DocaiChe FastAPI config endpoints,
handling system configuration management, settings updates, and feature flags.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import json

from .base_adapter import BaseAdapter
from ..schemas import MCPRequest, MCPResponse
from ..exceptions import ValidationError, AuthorizationError

logger = logging.getLogger(__name__)


class ConfigAdapter(BaseAdapter):
    """
    Adapter for MCP configuration operations to FastAPI config endpoints.
    
    Handles:
    - Configuration retrieval and updates
    - Feature flag management
    - System settings
    - Provider configuration
    - Environment-specific settings
    """
    
    # Configuration categories
    CONFIG_CATEGORIES = {
        'system': 'System-wide settings',
        'security': 'Security and authentication settings',
        'performance': 'Performance tuning parameters',
        'features': 'Feature flags and toggles',
        'providers': 'AI provider configurations',
        'integrations': 'External service integrations'
    }
    
    # Sensitive configuration keys that require special handling
    SENSITIVE_KEYS = {
        'api_keys', 'secrets', 'passwords', 'tokens',
        'private_keys', 'credentials', 'oauth_client_secret'
    }
    
    async def adapt_request(self, mcp_request: MCPRequest) -> Dict[str, Any]:
        """
        Adapt MCP configuration request to FastAPI format.
        
        Transforms MCP config parameters to match FastAPI configuration schema.
        """
        params = mcp_request.params or {}
        
        # Build config request
        adapted = {
            'category': params.get('category', 'system'),
            'include_defaults': params.get('include_defaults', False),
            'include_metadata': params.get('include_metadata', True)
        }
        
        # Add specific configuration keys if requested
        if 'keys' in params:
            adapted['keys'] = params['keys']
        
        # Add environment filter
        if 'environment' in params:
            adapted['environment'] = params['environment']
        
        return adapted
    
    async def adapt_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt FastAPI configuration response to MCP format.
        
        Transforms FastAPI ConfigurationResponse to MCP-compatible format with
        proper masking of sensitive values.
        """
        items = api_response.get('items', [])
        
        # Transform configuration items
        mcp_configs = []
        for item in items:
            # Check if value contains sensitive data
            is_sensitive = any(
                sensitive in item.get('key', '').lower()
                for sensitive in self.SENSITIVE_KEYS
            )
            
            mcp_config = {
                'key': item.get('key', ''),
                'value': '***REDACTED***' if is_sensitive else item.get('value'),
                'category': item.get('category', 'system'),
                'description': item.get('description', ''),
                'data_type': item.get('data_type', 'string'),
                'is_sensitive': is_sensitive,
                'metadata': {
                    'updated_at': item.get('updated_at', ''),
                    'updated_by': item.get('updated_by', ''),
                    'version': item.get('version', 1),
                    'environment': item.get('environment', 'all')
                }
            }
            
            # Add validation rules if available
            if 'validation' in item:
                mcp_config['validation'] = item['validation']
            
            # Add default value if different from current
            if 'default_value' in item and item['default_value'] != item['value']:
                mcp_config['default_value'] = item['default_value']
            
            mcp_configs.append(mcp_config)
        
        # Build complete response
        adapted = {
            'configurations': mcp_configs,
            'total_count': len(mcp_configs),
            'categories': list(set(c['category'] for c in mcp_configs)),
            'last_updated': api_response.get('last_updated', '')
        }
        
        # Add category descriptions
        adapted['category_info'] = {
            cat: self.CONFIG_CATEGORIES.get(cat, cat)
            for cat in adapted['categories']
        }
        
        return adapted
    
    async def get_configuration(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Get system configuration.
        
        Main entry point for configuration retrieval.
        """
        return await self.execute(
            mcp_request=mcp_request,
            method='GET',
            endpoint='/config'
        )
    
    async def update_configuration(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Update configuration values.
        
        Updates one or more configuration settings with validation
        and audit logging.
        """
        params = mcp_request.params or {}
        updates = params.get('updates', [])
        
        if not updates:
            raise ValidationError(
                message="No configuration updates provided",
                error_code="NO_UPDATES"
            )
        
        # Validate updates
        for update in updates:
            if 'key' not in update or 'value' not in update:
                raise ValidationError(
                    message="Configuration update must include key and value",
                    error_code="INVALID_UPDATE"
                )
            
            # Check for sensitive keys
            if any(sensitive in update['key'].lower() for sensitive in self.SENSITIVE_KEYS):
                # Require additional authorization for sensitive updates
                if not params.get('authorized', False):
                    raise AuthorizationError(
                        message="Additional authorization required for sensitive configuration",
                        required_permission="config:write:sensitive"
                    )
        
        # Build update request
        update_data = {
            'updates': updates,
            'reason': params.get('reason', 'MCP configuration update'),
            'updated_by': params.get('updated_by', 'mcp-adapter'),
            'validate_before_apply': params.get('validate', True),
            'create_backup': params.get('create_backup', True)
        }
        
        try:
            # Submit updates
            api_response = await self._make_request(
                method='PUT',
                endpoint='/config',
                data=update_data
            )
            
            # Return update results
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'status': 'success',
                    'updated_count': api_response.get('updated_count', 0),
                    'updates': api_response.get('updates', []),
                    'backup_id': api_response.get('backup_id', ''),
                    'warnings': api_response.get('warnings', [])
                }
            )
        
        except Exception as e:
            logger.error(
                f"Configuration update failed: {str(e)}",
                extra={"updates": updates},
                exc_info=True
            )
            raise
    
    async def get_feature_flags(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Get feature flag configurations.
        
        Retrieves all feature flags with their current states and rules.
        """
        params = mcp_request.params or {}
        
        # Get features from config
        config_request = MCPRequest(
            id=mcp_request.id,
            method="get_configuration",
            params={
                'category': 'features',
                'include_metadata': True
            }
        )
        
        config_response = await self.get_configuration(config_request)
        configs = config_response.result.get('configurations', [])
        
        # Transform to feature flag format
        feature_flags = {}
        for config in configs:
            if config['category'] == 'features':
                flag_name = config['key'].replace('feature.', '')
                feature_flags[flag_name] = {
                    'enabled': config['value'] in [True, 'true', 'enabled', '1'],
                    'description': config['description'],
                    'rules': config.get('validation', {}),
                    'metadata': config['metadata']
                }
        
        return MCPResponse(
            id=mcp_request.id,
            result={
                'feature_flags': feature_flags,
                'total_count': len(feature_flags),
                'evaluation_context': {
                    'environment': params.get('environment', 'production'),
                    'user_segment': params.get('user_segment', 'all')
                }
            }
        )
    
    async def toggle_feature_flag(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Toggle a feature flag on or off.
        
        Enables or disables a specific feature flag with proper validation.
        """
        params = mcp_request.params or {}
        flag_name = params.get('flag_name', '')
        enabled = params.get('enabled', None)
        
        if not flag_name:
            raise ValidationError(
                message="Feature flag name required",
                error_code="MISSING_FLAG_NAME"
            )
        
        if enabled is None:
            raise ValidationError(
                message="Enabled state must be specified",
                error_code="MISSING_ENABLED_STATE"
            )
        
        # Update feature flag via config
        update_request = MCPRequest(
            id=mcp_request.id,
            method="update_configuration",
            params={
                'updates': [{
                    'key': f'feature.{flag_name}',
                    'value': 'enabled' if enabled else 'disabled',
                    'category': 'features'
                }],
                'reason': f"Feature flag {flag_name} {'enabled' if enabled else 'disabled'} via MCP"
            }
        )
        
        return await self.update_configuration(update_request)
    
    async def get_provider_config(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Get AI provider configurations.
        
        Retrieves configurations for AI providers with sensitive data masked.
        """
        params = mcp_request.params or {}
        provider = params.get('provider', 'all')
        
        try:
            # Get provider info from API
            api_response = await self._make_request(
                method='GET',
                endpoint='/provider',
                params={'provider': provider} if provider != 'all' else {}
            )
            
            # Adapt provider response
            providers = api_response.get('providers', [])
            adapted_providers = []
            
            for prov in providers:
                adapted_provider = {
                    'name': prov.get('name', ''),
                    'type': prov.get('type', ''),
                    'enabled': prov.get('enabled', False),
                    'model': prov.get('model', ''),
                    'endpoint': prov.get('endpoint', ''),
                    'configuration': {
                        k: '***REDACTED***' if 'key' in k.lower() or 'secret' in k.lower() else v
                        for k, v in prov.get('configuration', {}).items()
                    },
                    'capabilities': prov.get('capabilities', []),
                    'limits': prov.get('limits', {})
                }
                adapted_providers.append(adapted_provider)
            
            return MCPResponse(
                id=mcp_request.id,
                result={
                    'providers': adapted_providers,
                    'default_provider': api_response.get('default_provider', ''),
                    'total_count': len(adapted_providers)
                }
            )
        
        except Exception as e:
            logger.error(
                f"Provider config retrieval failed: {str(e)}",
                exc_info=True
            )
            raise
    
    async def validate_configuration(
        self,
        mcp_request: MCPRequest
    ) -> MCPResponse:
        """
        Validate configuration values.
        
        Validates configuration updates before applying them to ensure
        system stability.
        """
        params = mcp_request.params or {}
        configs = params.get('configurations', [])
        
        if not configs:
            raise ValidationError(
                message="No configurations to validate",
                error_code="NO_CONFIGS"
            )
        
        validation_results = []
        
        for config in configs:
            result = {
                'key': config.get('key', ''),
                'value': config.get('value'),
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Basic validation
            if not config.get('key'):
                result['valid'] = False
                result['errors'].append("Configuration key is required")
            
            if 'value' not in config:
                result['valid'] = False
                result['errors'].append("Configuration value is required")
            
            # Type validation
            data_type = config.get('data_type', 'string')
            value = config.get('value')
            
            if data_type == 'integer':
                try:
                    int(value)
                except (TypeError, ValueError):
                    result['valid'] = False
                    result['errors'].append(f"Value must be an integer, got {type(value).__name__}")
            
            elif data_type == 'boolean':
                if not isinstance(value, bool) and value not in ['true', 'false', '0', '1']:
                    result['valid'] = False
                    result['errors'].append("Value must be a boolean")
            
            elif data_type == 'json':
                if isinstance(value, str):
                    try:
                        json.loads(value)
                    except json.JSONDecodeError as e:
                        result['valid'] = False
                        result['errors'].append(f"Invalid JSON: {str(e)}")
            
            # Check for deprecated configs
            if config.get('key', '').startswith('deprecated.'):
                result['warnings'].append("This configuration key is deprecated")
            
            validation_results.append(result)
        
        return MCPResponse(
            id=mcp_request.id,
            result={
                'validation_results': validation_results,
                'all_valid': all(r['valid'] for r in validation_results),
                'error_count': sum(len(r['errors']) for r in validation_results),
                'warning_count': sum(len(r['warnings']) for r in validation_results)
            }
        )


# Configuration adapter complete with:
# ✓ Configuration retrieval and updates
# ✓ Sensitive data masking
# ✓ Feature flag management
# ✓ Provider configuration
# ✓ Configuration validation
# ✓ Audit trail support
# ✓ Environment-specific settings
# ✓ Authorization checks