"""
Document Chunking Strategies.
Implements PRD-006: Splits documents into manageable chunks for processing and storage.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from src.document_processing.models import DocumentChunk
import uuid
import re

logger = logging.getLogger(__name__)

class DocumentChunker:
    """
    Splits documents into chunks for processing and storage.
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def chunk_document(self, text: str, document_id: str) -> List[DocumentChunk]:
        """
        Splits text into fixed-size chunks with overlap.
        """
        try:
            chunks = []
            start = 0
            idx = 0
            length = len(text)
            while start < length:
                end = min(start + self.chunk_size, length)
                chunk_text = text[start:end]
                chunk_id = str(uuid.uuid4())
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    content=chunk_text,
                    chunk_index=idx,
                    start_offset=start,
                    end_offset=end
                )
                chunks.append(chunk)
                idx += 1
                start += self.chunk_size - self.overlap
            return chunks
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            raise HTTPException(status_code=500, detail="Chunking failed")

    async def semantic_chunking(self, text: str, document_id: str) -> List[DocumentChunk]:
        """
        Splits text into chunks based on sentence boundaries (simple heuristic).
        """
        try:
            sentences = re.split(r'(?<=[.!?]) +', text)
            chunks = []
            chunk_text = ""
            idx = 0
            start_offset = 0
            for sentence in sentences:
                if len(chunk_text) + len(sentence) > self.chunk_size:
                    chunk_id = str(uuid.uuid4())
                    chunk = DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        content=chunk_text.strip(),
                        chunk_index=idx,
                        start_offset=start_offset,
                        end_offset=start_offset + len(chunk_text)
                    )
                    chunks.append(chunk)
                    idx += 1
                    start_offset += len(chunk_text)
                    chunk_text = ""
                chunk_text += sentence + " "
            if chunk_text.strip():
                chunk_id = str(uuid.uuid4())
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    content=chunk_text.strip(),
                    chunk_index=idx,
                    start_offset=start_offset,
                    end_offset=start_offset + len(chunk_text)
                )
                chunks.append(chunk)
            return chunks
        except Exception as e:
            logger.error(f"Semantic chunking failed: {e}")
            raise HTTPException(status_code=500, detail="Semantic chunking failed")