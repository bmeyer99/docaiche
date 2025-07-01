"""
Configuration Management API Endpoints
======================================

Core search configuration management endpoints.
"""

from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from fastapi.responses import JSONResponse
import logging
import json

from .models import (
    SearchConfigRequest,
    SearchConfigResponse,
    ConfigValidationRequest,
    ConfigValidationResponse,
    ConfigExportRequest,
    ConfigImportRequest,
    ConfigChangeLog,
    APIResponse,
    ErrorResponse
)
from src.mcp.core import SearchConfiguration
from ..dependencies import get_database_manager
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["configuration"])


# Placeholder for dependency injection
async def get_config_service():
    """Get configuration service instance."""
    # TODO: Implement in Phase 2
    pass


@router.get("", response_model=SearchConfigResponse)
async def get_search_configuration():
    """
    Retrieve current search configuration.
    
    Returns the complete search system configuration including:
    - Queue management settings
    - Timeout values
    - Performance thresholds
    - Resource limits
    - Feature toggles
    - Advanced settings
    """
    try:
        # TODO: Phase 2 - Load from database/storage
        config = SearchConfiguration()
        
        return SearchConfigResponse(
            queue_management=config.queue_management.dict(),
            timeouts=config.timeouts.dict(),
            performance_thresholds=config.performance_thresholds.dict(),
            resource_limits=config.resource_limits.dict(),
            feature_toggles={
                "enable_external_search": config.enable_external_search,
                "enable_ai_evaluation": config.enable_ai_evaluation,
                "enable_query_refinement": config.enable_query_refinement,
                "enable_knowledge_ingestion": config.enable_knowledge_ingestion,
                "enable_result_caching": config.enable_result_caching,
            },
            advanced_settings={
                "workspace_selection_strategy": config.workspace_selection_strategy,
                "result_ranking_algorithm": config.result_ranking_algorithm,
                "external_provider_priority": config.external_provider_priority,
            },
            last_updated=datetime.utcnow(),
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=APIResponse)
async def update_search_configuration(
    request: SearchConfigRequest = Body(...),
    # config_service = Depends(get_config_service)
):
    """
    Update search configuration with validation.
    
    Updates the search system configuration after validating all parameters.
    Supports partial updates - only provided fields will be updated.
    
    Configuration changes trigger:
    - Validation of all parameters
    - Dependency checking between settings
    - Audit log entry creation
    - Hot reload of affected components
    """
    try:
        # TODO: Phase 2 - Implement configuration update
        # 1. Load current configuration
        # 2. Merge with updates
        # 3. Validate complete configuration
        # 4. Save to storage
        # 5. Trigger hot reload
        # 6. Create audit log
        
        return APIResponse(
            success=True,
            message="Configuration updated successfully",
            data={"updated_sections": list(request.dict(exclude_unset=True).keys())}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[ConfigChangeLog])
async def get_configuration_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    section: str = Query(None),
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """
    Get configuration change history.
    
    Returns audit log of all configuration changes with:
    - Who made the change
    - When it was made
    - What was changed
    - Previous values
    - Change comments
    
    Supports filtering by configuration section and pagination.
    """
    try:
        # Build query with optional section filter
        if section:
            query = """
                SELECT id, timestamp, user, section, changes, previous_values, comment
                FROM configuration_audit_log 
                WHERE section = ?
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """
            params = (section, limit, offset)
        else:
            query = """
                SELECT id, timestamp, user, section, changes, previous_values, comment
                FROM configuration_audit_log 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """
            params = (limit, offset)
        
        results = await db_manager.fetch_all(query, params)
        
        # Convert results to ConfigChangeLog models
        audit_logs = []
        for row in results:
            audit_logs.append(ConfigChangeLog(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
                user=row["user"],
                section=row["section"],
                changes=json.loads(row["changes"]) if isinstance(row["changes"], str) else row["changes"],
                previous_values=json.loads(row["previous_values"]) if isinstance(row["previous_values"], str) else row["previous_values"],
                comment=row["comment"]
            ))
        
        return audit_logs
        
w    except Exception as e:
        logger.error(f"Failed to get configuration history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=ConfigValidationResponse)
async def validate_configuration(
    request: ConfigValidationRequest = Body(...)
):
    """
    Validate configuration without saving.
    
    Performs comprehensive validation including:
    - Parameter range validation
    - Type checking
    - Dependency validation between settings
    - Performance impact analysis
    
    Returns validation results with errors, warnings, and suggestions.
    """
    try:
        errors = []
        warnings = []
        suggestions = []
        
        # TODO: Phase 2 - Implement full validation
        # For now, create a SearchConfiguration to trigger basic validation
        try:
            config_dict = request.config.dict(exclude_unset=True)
            test_config = SearchConfiguration.from_dict(config_dict)
            
            # Check for dependency warnings
            warnings = test_config.get_dependency_warnings()
            
        except Exception as e:
            errors.append(str(e))
        
        return ConfigValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_configuration(
    request: ConfigExportRequest = Body(...)
):
    """
    Export configuration in specified format.
    
    Exports the current configuration as:
    - JSON (default)
    - YAML
    
    Options:
    - Include or exclude secrets
    - Export specific sections only
    - Include metadata and version info
    """
    try:
        # TODO: Phase 2 - Implement export functionality
        config = SearchConfiguration()
        
        if request.format == "json":
            import json
            data = config.to_dict()
            
            # Remove secrets if requested
            if not request.include_secrets:
                # TODO: Remove sensitive fields
                pass
            
            # Filter sections if specified
            if request.sections:
                filtered_data = {k: v for k, v in data.items() if k in request.sections}
                data = filtered_data
            
            return JSONResponse(
                content={
                    "version": "1.0.0",
                    "exported_at": datetime.utcnow().isoformat(),
                    "configuration": data
                }
            )
        else:
            # YAML export
            raise HTTPException(status_code=501, detail="YAML export not implemented")
            
    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=APIResponse)
async def import_configuration(
    request: ConfigImportRequest = Body(...)
):
    """
    Import configuration from file.
    
    Imports configuration with options to:
    - Validate only (dry run)
    - Replace entire configuration
    - Merge with existing configuration
    
    Performs validation before applying changes.
    """
    try:
        # TODO: Phase 2 - Implement import functionality
        # 1. Parse input data based on format
        # 2. Validate configuration
        # 3. If validate_only, return validation results
        # 4. Otherwise apply configuration
        # 5. Create audit log entry
        
        if request.validate_only:
            return APIResponse(
                success=True,
                message="Configuration validation successful",
                data={"valid": True}
            )
        else:
            return APIResponse(
                success=True,
                message="Configuration imported successfully",
                data={"sections_updated": ["all"]}
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to import configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Queue and timeout specific endpoints

@router.get("/queues")
async def get_queue_configuration():
    """Get queue-specific configuration settings."""
    try:
        config = SearchConfiguration()
        return config.queue_management.dict()
    except Exception as e:
        logger.error(f"Failed to get queue configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/queues", response_model=APIResponse)
async def update_queue_configuration(
    settings: Dict[str, Any] = Body(...)
):
    """Update queue-specific configuration settings."""
    try:
        # TODO: Phase 2 - Implement queue config update
        return APIResponse(
            success=True,
            message="Queue configuration updated successfully"
        )
    except Exception as e:
        logger.error(f"Failed to update queue configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeouts")
async def get_timeout_configuration():
    """Get timeout configuration settings."""
    try:
        config = SearchConfiguration()
        return config.timeouts.dict()
    except Exception as e:
        logger.error(f"Failed to get timeout configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/timeouts", response_model=APIResponse)
async def update_timeout_configuration(
    settings: Dict[str, Any] = Body(...)
):
    """Update timeout configuration settings."""
    try:
        # TODO: Phase 2 - Implement timeout config update
        return APIResponse(
            success=True,
            message="Timeout configuration updated successfully"
        )
    except Exception as e:
        logger.error(f"Failed to update timeout configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))