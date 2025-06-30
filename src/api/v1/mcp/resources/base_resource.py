"""
Base Resource Class
==================

Abstract base class for all MCP resources.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseResource(ABC):
    """Base class for all MCP resources"""
    
    def __init__(self, uri_prefix: str, description: str):
        self.uri_prefix = uri_prefix
        self.description = description
    
    @abstractmethod
    async def read(self, uri: str) -> Dict[str, Any]:
        """
        Read resource data for given URI.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource data
        """
        pass