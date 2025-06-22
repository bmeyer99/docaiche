"""
Configuration management for AI Documentation Cache System
PRD-001: HTTP API Foundation - Configuration Management

Basic configuration management that will be enhanced by PRD-003 Configuration Management System.
This provides the minimal configuration needed for the FastAPI application to start.
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    This is a basic configuration that will be expanded when PRD-003 is implemented.
    """
    
    # API Configuration
    API_TITLE: str = Field(
        default="AI Documentation Cache System API",
        description="API title displayed in documentation"
    )
    API_VERSION: str = Field(
        default="1.0.0",
        description="API version"
    )
    API_DESCRIPTION: str = Field(
        default="Intelligent documentation cache with AI-powered search and enrichment",
        description="API description"
    )
    
    # Server Configuration
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    PORT: int = Field(
        default=8080,
        description="Server port"
    )
    RELOAD: bool = Field(
        default=False,
        description="Enable auto-reload for development"
    )
    LOG_LEVEL: str = Field(
        default="info",
        description="Logging level"
    )
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods for CORS"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        default=["*"],
        description="Allowed headers for CORS"
    )
    
    # Security Configuration
    SECURITY_HEADERS_ENABLED: bool = Field(
        default=True,
        description="Enable security headers middleware"
    )
    
    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment (development, staging, production)"
    )
    DEBUG: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings instance.
    
    Returns:
        Settings: The application settings
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload application settings from environment.
    
    Returns:
        Settings: The reloaded application settings
    """
    global _settings
    _settings = None
    return get_settings()