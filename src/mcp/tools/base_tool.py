"""
Base MCP Tool Interface and Common Functionality
================================================

Abstract base tool interface defining the contract for all MCP tool
implementations with consistent behavior and validation patterns.

Key Features:
- Abstract tool interface for consistency
- Tool metadata and annotation management
- Request validation and response formatting
- Error handling and audit logging
- Performance monitoring and metrics

Provides foundation for all MCP tools with standardized execution,
validation, and monitoring capabilities.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

from ..schemas import (
    MCPRequest, MCPResponse, ToolDefinition, ToolAnnotation,
    create_success_response, create_error_response
)
from ..exceptions import ToolExecutionError, ValidationError, ConsentError
from ..auth.consent_manager import ConsentManager
from ..auth.security_audit import SecurityAuditor

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """
    Tool metadata and execution information.
    
    Provides comprehensive metadata about tool capabilities,
    performance characteristics, and usage patterns.
    """
    
    name: str
    version: str
    description: str
    category: str
    
    # Execution statistics
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time_ms: float = 0.0
    
    # Security and compliance
    security_level: str = "public"
    requires_consent: bool = False
    audit_enabled: bool = True
    
    # Performance characteristics
    max_execution_time_ms: int = 30000  # 30 seconds default
    rate_limit_per_minute: int = 30
    
    def update_execution_stats(self, execution_time_ms: float, success: bool):
        """Update execution statistics."""
        self.total_executions += 1
        
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # Update average execution time
        if self.total_executions == 1:
            self.average_execution_time_ms = execution_time_ms
        else:
            self.average_execution_time_ms = (
                (self.average_execution_time_ms * (self.total_executions - 1) + execution_time_ms)
                / self.total_executions
            )
    
    @property
    def success_rate(self) -> float:
        """Calculate tool success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "statistics": {
                "total_executions": self.total_executions,
                "successful_executions": self.successful_executions,
                "failed_executions": self.failed_executions,
                "success_rate": self.success_rate,
                "average_execution_time_ms": self.average_execution_time_ms
            },
            "security": {
                "security_level": self.security_level,
                "requires_consent": self.requires_consent,
                "audit_enabled": self.audit_enabled
            },
            "performance": {
                "max_execution_time_ms": self.max_execution_time_ms,
                "rate_limit_per_minute": self.rate_limit_per_minute
            }
        }


class BaseTool(ABC):
    """
    Abstract base class for all MCP tool implementations.
    
    Defines the contract that all tools must follow including execution,
    validation, security, and monitoring capabilities.
    """
    
    def __init__(
        self,
        consent_manager: Optional[ConsentManager] = None,
        security_auditor: Optional[SecurityAuditor] = None
    ):
        """
        Initialize base tool with security and monitoring dependencies.
        
        Args:
            consent_manager: Consent management system
            security_auditor: Security audit and logging system
        """
        self.consent_manager = consent_manager
        self.security_auditor = security_auditor
        
        # Tool metadata (must be set by concrete implementations)
        self.metadata: Optional[ToolMetadata] = None
        
        # Tool definition (must be set by concrete implementations)
        self.tool_definition: Optional[ToolDefinition] = None
        
        logger.debug(f"Base tool initialized: {self.__class__.__name__}")
    
    @abstractmethod
    def get_tool_definition(self) -> ToolDefinition:
        """
        Get complete tool definition with schema and annotations.
        
        Must be implemented by concrete tool classes to define their
        interface, validation schema, and behavior annotations.
        
        Returns:
            Complete tool definition
        """
        pass
    
    @abstractmethod
    async def execute(
        self,
        request: MCPRequest,
        **kwargs
    ) -> MCPResponse:
        """
        Execute tool with validated request parameters.
        
        Must be implemented by concrete tool classes to handle the
        specific tool logic and return appropriate responses.
        
        Args:
            request: Validated MCP request
            **kwargs: Additional execution context
            
        Returns:
            MCP response with tool results
            
        Raises:
            ToolExecutionError: If tool execution fails
        """
        pass
    
    async def handle_request(
        self,
        request: MCPRequest,
        client_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        **kwargs
    ) -> MCPResponse:
        """
        Handle complete tool request with security, validation, and monitoring.
        
        Provides standardized request handling including validation,
        consent checking, execution, and audit logging.
        
        Args:
            request: MCP request to handle
            client_id: OAuth client identifier
            client_ip: Client IP address for audit
            **kwargs: Additional execution context
            
        Returns:
            MCP response with tool results or error
        """
        start_time = time.time()
        
        # Ensure tool definition is available
        if not self.tool_definition:
            self.tool_definition = self.get_tool_definition()
        
        if not self.metadata:
            raise ToolExecutionError(
                message="Tool metadata not initialized",
                error_code="TOOL_NOT_INITIALIZED",
                tool_name=self.tool_definition.name if self.tool_definition else "unknown"
            )
        
        try:
            # Validate request parameters
            await self._validate_request(request)
            
            # Check consent requirements
            if self.metadata.requires_consent and self.consent_manager:
                await self._check_consent(request, client_id)
            
            # Execute tool
            response = await self.execute(
                request,
                client_id=client_id,
                client_ip=client_ip,
                **kwargs
            )
            
            # Record successful execution
            execution_time = int((time.time() - start_time) * 1000)
            self.metadata.update_execution_stats(execution_time, success=True)
            
            # Audit successful execution
            if self.security_auditor and self.metadata.audit_enabled:
                self.security_auditor.log_tool_execution(
                    tool_name=self.metadata.name,
                    success=True,
                    client_id=client_id or "unknown",
                    execution_time_ms=execution_time,
                    client_ip=client_ip
                )
            
            logger.debug(
                f"Tool executed successfully",
                extra={
                    "tool_name": self.metadata.name,
                    "request_id": request.id,
                    "execution_time_ms": execution_time,
                    "client_id": client_id
                }
            )
            
            return response
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.metadata.update_execution_stats(execution_time, success=False)
            
            # Audit failed execution
            if self.security_auditor and self.metadata.audit_enabled:
                self.security_auditor.log_tool_execution(
                    tool_name=self.metadata.name,
                    success=False,
                    client_id=client_id or "unknown",
                    execution_time_ms=execution_time,
                    client_ip=client_ip,
                    error_details={"error": str(e), "error_type": type(e).__name__}
                )
            
            logger.error(
                f"Tool execution failed",
                extra={
                    "tool_name": self.metadata.name,
                    "request_id": request.id,
                    "execution_time_ms": execution_time,
                    "error": str(e),
                    "client_id": client_id
                },
                exc_info=True
            )
            
            # Create error response
            if isinstance(e, ToolExecutionError):
                error_code = -32603  # Internal error
            elif isinstance(e, ValidationError):
                error_code = -32602  # Invalid params
            elif isinstance(e, ConsentError):
                error_code = -32600  # Invalid request
            else:
                error_code = -32603  # Internal error
            
            return create_error_response(
                request_id=request.id,
                error_code=error_code,
                error_message=str(e),
                error_data={
                    "tool_name": self.metadata.name,
                    "execution_time_ms": execution_time,
                    "error_type": type(e).__name__
                },
                correlation_id=getattr(request, 'correlation_id', None)
            )
    
    async def _validate_request(self, request: MCPRequest) -> None:
        """
        Validate request parameters against tool schema.
        
        Args:
            request: MCP request to validate
            
        Raises:
            ValidationError: If request is invalid
        """
        if not request.params:
            if self.tool_definition and self.tool_definition.input_schema.get("required"):
                raise ValidationError(
                    message="Required parameters missing",
                    error_code="MISSING_REQUIRED_PARAMS",
                    details={"required": self.tool_definition.input_schema["required"]}
                )
            return
        
        # Basic parameter validation
        # TODO: IMPLEMENTATION ENGINEER - Add comprehensive JSON schema validation
        if self.tool_definition:
            schema = self.tool_definition.input_schema
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Check required parameters
            for param in required:
                if param not in request.params:
                    raise ValidationError(
                        message=f"Required parameter missing: {param}",
                        error_code="MISSING_REQUIRED_PARAM",
                        details={"missing_param": param}
                    )
            
            # Check parameter types (basic validation)
            for param_name, param_value in request.params.items():
                if param_name in properties:
                    expected_type = properties[param_name].get("type")
                    if expected_type and not self._validate_parameter_type(param_value, expected_type):
                        raise ValidationError(
                            message=f"Invalid parameter type for {param_name}",
                            error_code="INVALID_PARAM_TYPE",
                            details={
                                "param": param_name,
                                "expected_type": expected_type,
                                "actual_type": type(param_value).__name__
                            }
                        )
    
    async def _check_consent(self, request: MCPRequest, client_id: Optional[str]) -> None:
        """
        Check consent requirements for tool execution.
        
        Args:
            request: MCP request
            client_id: OAuth client identifier
            
        Raises:
            ConsentError: If consent is required but not found
        """
        if not client_id or not self.consent_manager:
            return
        
        # Determine required permissions based on tool and parameters
        required_permissions = self._get_required_permissions(request)
        
        # Validate consent
        await self.consent_manager.validate_consent(
            client_id=client_id,
            operation=self.metadata.name,
            required_permissions=required_permissions
        )
    
    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """
        Basic parameter type validation.
        
        Args:
            value: Parameter value to validate
            expected_type: Expected JSON Schema type
            
        Returns:
            True if type is valid
        """
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected_python_type = type_map.get(expected_type)
        if not expected_python_type:
            return True  # Unknown type, allow
        
        return isinstance(value, expected_python_type)
    
    def _get_required_permissions(self, request: MCPRequest) -> List[str]:
        """
        Determine required permissions for tool execution.
        
        Args:
            request: MCP request
            
        Returns:
            List of required permissions
        """
        # Default permissions based on tool annotations
        if self.tool_definition and self.tool_definition.annotations:
            return ["tool_access", f"tool_{self.metadata.name}"]
        
        return ["tool_access"]
    
    def get_tool_info(self) -> Dict[str, Any]:
        """
        Get comprehensive tool information.
        
        Returns:
            Dictionary with tool definition, metadata, and statistics
        """
        info = {
            "definition": self.tool_definition.dict() if self.tool_definition else None,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "status": "available" if self.metadata else "not_initialized"
        }
        
        return info
    
    def reset_statistics(self) -> None:
        """Reset tool execution statistics."""
        if self.metadata:
            self.metadata.total_executions = 0
            self.metadata.successful_executions = 0
            self.metadata.failed_executions = 0
            self.metadata.average_execution_time_ms = 0.0
            
            logger.info(f"Tool statistics reset: {self.metadata.name}")


# TODO: IMPLEMENTATION ENGINEER - Add the following base tool enhancements:
# 1. JSON Schema validation for request parameters
# 2. Tool dependency management and injection
# 3. Caching mechanisms for expensive operations
# 4. Tool versioning and migration support
# 5. Advanced permission and role-based access control