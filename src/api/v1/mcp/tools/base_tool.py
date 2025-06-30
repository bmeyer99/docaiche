"""
Base Tool Class
==============

Abstract base class for all MCP tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Result from tool execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class BaseTool(ABC):
    """Base class for all MCP tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Tool-specific parameters
            
        Returns:
            ToolResult with execution results
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for tool parameters.
        
        Returns:
            JSON schema dict
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }