"""
Authentication Provider Base Class
=================================

Defines the base authentication provider interface and token structure
for MCP OAuth 2.1 implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List


@dataclass
class AuthToken:
    """Authentication token with metadata."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    issued_at: datetime = None
    
    def __post_init__(self):
        if self.issued_at is None:
            self.issued_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_in is None:
            return False
        elapsed = (datetime.utcnow() - self.issued_at).total_seconds()
        return elapsed >= self.expires_in


class AuthProvider(ABC):
    """Base class for authentication providers."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthToken:
        """Authenticate with the given credentials."""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> AuthToken:
        """Refresh an access token using a refresh token."""
        pass
    
    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid."""
        pass
    
    @abstractmethod
    def get_supported_grant_types(self) -> List[str]:
        """Get list of supported OAuth grant types."""
        pass