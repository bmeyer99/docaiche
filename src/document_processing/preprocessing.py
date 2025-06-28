"""
Content Preprocessing.
Implements PRD-006: Cleans and normalizes extracted text for downstream processing.
"""

import logging
from fastapi import HTTPException
import re

logger = logging.getLogger(__name__)


class ContentPreprocessor:
    """
    Cleans and normalizes extracted text for downstream processing.
    """

    async def clean_text(self, text: str) -> str:
        """
        Cleans and normalizes text.
        """
        try:
            text = await self.normalize_whitespace(text)
            text = await self.remove_artifacts(text)
            return text
        except Exception as e:
            logger.error(f"Text cleaning failed: {e}")
            raise HTTPException(status_code=500, detail="Text cleaning failed")

    async def normalize_whitespace(self, text: str) -> str:
        """
        Normalizes whitespace in text.
        """
        try:
            return re.sub(r"\s+", " ", text).strip()
        except Exception as e:
            logger.error(f"Whitespace normalization failed: {e}")
            raise HTTPException(
                status_code=500, detail="Whitespace normalization failed"
            )

    async def remove_artifacts(self, text: str) -> str:
        """
        Removes common extraction artifacts from text.
        """
        try:
            # Remove null bytes and control characters except \n, \t
            text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
            # Remove repeated hyphens or underscores
            text = re.sub(r"[-_]{3,}", "", text)
            # Remove page numbers (simple heuristic)
            text = re.sub(r"\n?\s*Page \d+\s*\n?", "", text, flags=re.IGNORECASE)
            return text
        except Exception as e:
            logger.error(f"Artifact removal failed: {e}")
            raise HTTPException(status_code=500, detail="Artifact removal failed")
