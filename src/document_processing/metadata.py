"""
Metadata Extraction.
Implements PRD-006: Extracts document metadata and properties for indexing and storage.
"""

import logging
from typing import Optional
from fastapi import HTTPException
from src.document_processing.models import DocumentMetadata, DocumentFormat
import hashlib
import mimetypes
from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Extracts document metadata and properties for indexing and storage.
    """

    async def extract_metadata(self, file_path: str, filename: str) -> DocumentMetadata:
        """
        Extracts metadata from file.
        """
        try:
            import os

            file_size = os.path.getsize(file_path)
            mime_type, _ = mimetypes.guess_type(filename)
            format = await self.detect_format(None, filename)
            upload_timestamp = datetime.utcnow().isoformat()
            async with open(file_path, "rb") as f:
                file_data = f.read()
            checksum = await self.calculate_checksum(file_data)
            return DocumentMetadata(
                filename=filename,
                file_size=file_size,
                format=format,
                mime_type=mime_type or "application/octet-stream",
                upload_timestamp=upload_timestamp,
                checksum=checksum,
            )
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise HTTPException(status_code=500, detail="Metadata extraction failed")

    async def calculate_checksum(self, file_data: bytes) -> str:
        """
        Calculates SHA256 checksum of file data.
        """
        try:
            return hashlib.sha256(file_data).hexdigest()
        except Exception as e:
            logger.error(f"Checksum calculation failed: {e}")
            raise HTTPException(status_code=500, detail="Checksum calculation failed")

    async def detect_format(
        self, file_data: Optional[bytes], filename: str
    ) -> DocumentFormat:
        """
        Detects document format based on filename extension.
        """
        try:
            ext = filename.split(".")[-1].lower()
            if ext == "pdf":
                return DocumentFormat.PDF
            elif ext == "docx":
                return DocumentFormat.DOCX
            elif ext == "txt":
                return DocumentFormat.TXT
            elif ext == "md":
                return DocumentFormat.MARKDOWN
            elif ext == "html" or ext == "htm":
                return DocumentFormat.HTML
            else:
                logger.warning(f"Unknown document format for file: {filename}")
                raise HTTPException(status_code=415, detail="Unknown document format")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Format detection failed: {e}")
            raise HTTPException(status_code=500, detail="Format detection failed")
