"""
Content Processing Exceptions - PRD-008
Custom exception classes for content processing pipeline error handling
"""

from typing import Optional, Dict, Any


class ContentProcessingError(Exception):
    """Base exception for content processing errors"""

    def __init__(self, message: str, error_context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_context = error_context or {}


class ContentValidationError(ContentProcessingError):
    """Raised when content validation fails"""

    pass


class ContentNormalizationError(ContentProcessingError):
    """Raised when content normalization fails"""

    pass


class MetadataExtractionError(ContentProcessingError):
    """Raised when metadata extraction fails"""

    pass


class ChunkingError(ContentProcessingError):
    """Raised when content chunking fails"""

    pass


class QualityThresholdError(ContentProcessingError):
    """Raised when content quality is below threshold"""

    def __init__(self, message: str, quality_score: float, threshold: float):
        super().__init__(message)
        self.quality_score = quality_score
        self.threshold = threshold
        self.error_context = {"quality_score": quality_score, "threshold": threshold}


class DatabaseIntegrationError(ContentProcessingError):
    """Raised when database operations fail during processing"""

    pass


class DuplicateContentError(ContentProcessingError):
    """Raised when duplicate content is detected"""

    def __init__(self, message: str, content_hash: str, existing_content_id: str):
        super().__init__(message)
        self.content_hash = content_hash
        self.existing_content_id = existing_content_id
        self.error_context = {
            "content_hash": content_hash,
            "existing_content_id": existing_content_id,
        }
