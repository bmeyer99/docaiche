"""
Text Extraction Handlers.
Implements PRD-006: Extracts text from PDF, DOCX, TXT, Markdown, and HTML documents.
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from src.document_processing.models import DocumentFormat
import aiofiles
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class TextExtractor:
    """
    Handles multi-format text extraction for document processing.
    """

    async def extract_text(self, file_path: str, format: DocumentFormat) -> str:
        """
        Extracts text from a file based on its format.
        """
        try:
            if format == DocumentFormat.PDF:
                return await self.extract_pdf_text(file_path)
            elif format == DocumentFormat.DOCX:
                return await self.extract_docx_text(file_path)
            elif format == DocumentFormat.TXT:
                return await self.extract_plain_text(file_path)
            elif format == DocumentFormat.MARKDOWN:
                return await self.extract_markdown_text(file_path)
            elif format == DocumentFormat.HTML:
                return await self.extract_html_text(file_path)
            else:
                logger.error(f"Unsupported document format: {format}")
                raise HTTPException(status_code=415, detail="Unsupported document format")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {e}")
            raise HTTPException(status_code=500, detail="Text extraction failed")

    async def extract_pdf_text(self, file_path: str) -> str:
        """
        Extracts text from a PDF file using PyPDF2.
        """
        try:
            import PyPDF2
            async with aiofiles.open(file_path, "rb") as f:
                pdf_bytes = await f.read()
            reader = PyPDF2.PdfReader(pdf_bytes)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise HTTPException(status_code=500, detail="PDF extraction failed")

    async def extract_docx_text(self, file_path: str) -> str:
        """
        Extracts text from a DOCX file using python-docx.
        """
        try:
            import docx
            async with aiofiles.open(file_path, "rb") as f:
                docx_bytes = await f.read()
            from io import BytesIO
            doc = docx.Document(BytesIO(docx_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise HTTPException(status_code=500, detail="DOCX extraction failed")

    async def extract_plain_text(self, file_path: str) -> str:
        """
        Reads plain text file.
        """
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                text = await f.read()
            return text
        except Exception as e:
            logger.error(f"Plain text extraction failed: {e}")
            raise HTTPException(status_code=500, detail="Plain text extraction failed")

    async def extract_markdown_text(self, file_path: str) -> str:
        """
        Extracts text from Markdown file.
        """
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                md = await f.read()
            html = markdown.markdown(md)
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text()
        except Exception as e:
            logger.error(f"Markdown extraction failed: {e}")
            raise HTTPException(status_code=500, detail="Markdown extraction failed")

    async def extract_html_text(self, file_path: str) -> str:
        """
        Extracts text from HTML file.
        """
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                html = await f.read()
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text()
        except Exception as e:
            logger.error(f"HTML extraction failed: {e}")
            raise HTTPException(status_code=500, detail="HTML extraction failed")