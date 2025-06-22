"""
Security middleware and utilities for AI Documentation Cache System
PRD-001: HTTP API Foundation - Security Middleware

Implements security headers middleware as specified in the task requirements.
"""

import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware as specified in API-001 task requirements.
    
    Adds the following security headers to all responses:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (for HTTPS)
    """
    
    def __init__(self, app, enable_hsts: bool = True):
        """
        Initialize security middleware.
        
        Args:
            app: The ASGI application
            enable_hsts: Whether to enable HSTS header for HTTPS
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response with security headers added
        """
        try:
            # Process the request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in SecurityMiddleware: {e}")
            raise
    
    def _add_security_headers(self, request: Request, response: Response) -> None:
        """
        Add security headers to the response.
        
        Args:
            request: The incoming request
            response: The response to add headers to
        """
        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable XSS filtering
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict-Transport-Security: Force HTTPS (only for HTTPS requests)
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content-Security-Policy: Basic CSP (can be enhanced later)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy: Control browser features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"


def create_security_middleware(enable_hsts: bool = True) -> type:
    """
    Create a security middleware class with configuration.
    
    Args:
        enable_hsts: Whether to enable HSTS header for HTTPS
        
    Returns:
        SecurityMiddleware: Configured security middleware class
    """
    class ConfiguredSecurityMiddleware(SecurityMiddleware):
        def __init__(self, app):
            super().__init__(app, enable_hsts=enable_hsts)
    
    return ConfiguredSecurityMiddleware