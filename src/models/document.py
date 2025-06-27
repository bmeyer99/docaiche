"""
Document models for the Docaiche system.

This module re-exports the document models from schemas.py to maintain
compatibility with existing imports.
"""

from .schemas import DocumentMetadata, DocumentChunk, ProcessedDocument

__all__ = [
    "DocumentMetadata",
    "DocumentChunk", 
    "ProcessedDocument"
]