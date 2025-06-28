"""
Content Processing Pipeline - PRD-008
Handles transformation of raw content into standardized, chunked format for storage.
"""

from .content_processor import ContentProcessor, FileContent, ScrapedContent
from .factory import (
    create_content_processor,
    create_file_content,
    create_scraped_content,
)
from .exceptions import (
    ContentProcessingError,
    ContentValidationError,
    ContentNormalizationError,
    MetadataExtractionError,
    ChunkingError,
    QualityThresholdError,
    DatabaseIntegrationError,
    DuplicateContentError,
)

__all__ = [
    # Core classes
    "ContentProcessor",
    "FileContent",
    "ScrapedContent",
    # Factory functions
    "create_content_processor",
    "create_file_content",
    "create_scraped_content",
    # Exceptions
    "ContentProcessingError",
    "ContentValidationError",
    "ContentNormalizationError",
    "MetadataExtractionError",
    "ChunkingError",
    "QualityThresholdError",
    "DatabaseIntegrationError",
    "DuplicateContentError",
]
