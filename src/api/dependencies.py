"""
Simplified service dependencies for the Docaiche API.

Provides direct access to core services with clear error handling.
No complex graceful degradation - fail fast with clear error messages.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status

# Import services (these would need to be implemented)
try:
    from services.search import SearchService
    from services.config import ConfigService
    from services.health import HealthService
    from services.content import ContentService
    from services.feedback import FeedbackService
except ImportError:
    # Mock services for initial implementation
    SearchService = None
    ConfigService = None
    HealthService = None
    ContentService = None
    FeedbackService = None


class ServiceError(Exception):
    """Base exception for service-related errors."""
    pass


class ServiceUnavailableError(ServiceError):
    """Service is unavailable."""
    pass


def get_search_service() -> "SearchService":
    """Get the search service instance."""
    if SearchService is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is not available"
        )
    
    try:
        return SearchService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize search service: {str(e)}"
        )


def get_config_service() -> "ConfigService":
    """Get the configuration service instance."""
    if ConfigService is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration service is not available"
        )
    
    try:
        return ConfigService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize configuration service: {str(e)}"
        )


def get_health_service() -> "HealthService":
    """Get the health service instance."""
    if HealthService is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health service is not available"
        )
    
    try:
        return HealthService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize health service: {str(e)}"
        )


def get_content_service() -> "ContentService":
    """Get the content service instance."""
    if ContentService is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content service is not available"
        )
    
    try:
        return ContentService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize content service: {str(e)}"
        )


def get_feedback_service() -> "FeedbackService":
    """Get the feedback service instance."""
    if FeedbackService is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback service is not available"
        )
    
    try:
        return FeedbackService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize feedback service: {str(e)}"
        )