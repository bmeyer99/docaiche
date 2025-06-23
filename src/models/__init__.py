"""
Canonical Data Models Package - PRD-002 DB-011
Shared data models ensuring consistency across all PRD components
"""

from .document import DocumentMetadata, DocumentChunk, ProcessedDocument

__all__ = [
    "DocumentMetadata",
    "DocumentChunk", 
    "ProcessedDocument"
]