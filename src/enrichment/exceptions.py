"""
Enrichment Exceptions - PRD-010
Structured exception hierarchy for knowledge enrichment operations.

Provides comprehensive error handling for all enrichment pipeline operations
with proper error context and recovery guidance.
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class EnrichmentError(Exception):
    """
    Base exception for all knowledge enrichment errors.
    
    Provides common error context and logging for enrichment operations.
    """
    
    def __init__(
        self, 
        message: str, 
        error_context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """
        Initialize enrichment error.
        
        Args:
            message: Human-readable error message
            error_context: Additional context for debugging
            recoverable: Whether the error is recoverable
        """
        self.message = message
        self.error_context = error_context or {}
        self.recoverable = recoverable
        super().__init__(self.message)
        
        # Log error with context
        logger.error(
            f"EnrichmentError: {message}",
            extra={
                "error_context": self.error_context,
                "recoverable": self.recoverable
            }
        )


class TaskProcessingError(EnrichmentError):
    """
    Exception for enrichment task processing errors.
    
    Handles errors during background task execution and processing.
    """
    
    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None,
        content_id: Optional[str] = None,
        task_type: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize task processing error.
        
        Args:
            message: Error message
            task_id: Task identifier that failed
            content_id: Content ID being processed
            task_type: Type of enrichment task
            error_context: Additional error context
        """
        context = {
            "task_id": task_id,
            "content_id": content_id,
            "task_type": task_type,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class AnalysisError(EnrichmentError):
    """
    Exception for content analysis operations.
    
    Handles errors during content analysis and processing.
    """
    
    def __init__(
        self,
        message: str,
        content_id: Optional[str] = None,
        analysis_type: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize analysis error.
        
        Args:
            message: Error message
            content_id: Content ID being analyzed
            analysis_type: Type of analysis being performed
            error_context: Additional error context
        """
        context = {
            "content_id": content_id,
            "analysis_type": analysis_type,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class RelationshipMappingError(EnrichmentError):
    """
    Exception for relationship mapping operations.
    
    Handles errors during document relationship identification and mapping.
    """
    
    def __init__(
        self,
        message: str,
        source_content_id: Optional[str] = None,
        target_content_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize relationship mapping error.
        
        Args:
            message: Error message
            source_content_id: Source document ID
            target_content_id: Target document ID
            relationship_type: Type of relationship being mapped
            error_context: Additional error context
        """
        context = {
            "source_content_id": source_content_id,
            "target_content_id": target_content_id,
            "relationship_type": relationship_type,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class EnrichmentTimeoutError(EnrichmentError):
    """
    Exception for enrichment operation timeouts.
    
    Handles timeout scenarios during enrichment processing.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        content_id: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize enrichment timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration
            operation: Operation that timed out
            content_id: Content ID being processed
            error_context: Additional error context
        """
        context = {
            "timeout_seconds": timeout_seconds,
            "operation": operation,
            "content_id": content_id,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=False)


class QueueError(EnrichmentError):
    """
    Exception for task queue operations.
    
    Handles errors in task queue management and processing.
    """
    
    def __init__(
        self,
        message: str,
        queue_size: Optional[int] = None,
        operation: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize queue error.
        
        Args:
            message: Error message
            queue_size: Current queue size
            operation: Queue operation that failed
            error_context: Additional error context
        """
        context = {
            "queue_size": queue_size,
            "operation": operation,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class TagGenerationError(EnrichmentError):
    """
    Exception for tag generation operations.
    
    Handles errors during automated tag generation.
    """
    
    def __init__(
        self,
        message: str,
        content_id: Optional[str] = None,
        existing_tags: Optional[List[str]] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize tag generation error.
        
        Args:
            message: Error message
            content_id: Content ID for tag generation
            existing_tags: Existing tags on content
            error_context: Additional error context
        """
        context = {
            "content_id": content_id,
            "existing_tags": existing_tags,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class QualityAssessmentError(EnrichmentError):
    """
    Exception for quality assessment operations.
    
    Handles errors during content quality evaluation and scoring.
    """
    
    def __init__(
        self,
        message: str,
        content_id: Optional[str] = None,
        current_quality_score: Optional[float] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize quality assessment error.
        
        Args:
            message: Error message
            content_id: Content ID being assessed
            current_quality_score: Current quality score
            error_context: Additional error context
        """
        context = {
            "content_id": content_id,
            "current_quality_score": current_quality_score,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class MetadataEnhancementError(EnrichmentError):
    """
    Exception for metadata enhancement operations.
    
    Handles errors during metadata enrichment and augmentation.
    """
    
    def __init__(
        self,
        message: str,
        content_id: Optional[str] = None,
        metadata_fields: Optional[List[str]] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize metadata enhancement error.
        
        Args:
            message: Error message
            content_id: Content ID being enhanced
            metadata_fields: Metadata fields being processed
            error_context: Additional error context
        """
        context = {
            "content_id": content_id,
            "metadata_fields": metadata_fields,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)