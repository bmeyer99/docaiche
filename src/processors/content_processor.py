"""
Content Processor Implementation - PRD-008 CP-001
Complete content processing pipeline for transforming raw content into standardized format

Implements exact specifications from PRD-008 with content normalization, metadata extraction,
quality scoring, chunking, and database integration with the validated foundation systems.
"""

import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlparse

from src.core.config.models import ContentConfig
from src.database.connection import DatabaseManager
from src.models.schemas import ProcessedDocument, DocumentChunk, DocumentMetadata

logger = logging.getLogger(__name__)


# Input data models for content processing
class FileContent:
    """File content from GitHub repository client"""
    def __init__(self, content: str, source_url: str, title: str = ""):
        self.content = content
        self.source_url = source_url
        self.title = title


class ScrapedContent:
    """Scraped content from web scraping client"""
    def __init__(self, content: str, source_url: str, title: str = ""):
        self.content = content
        self.source_url = source_url
        self.title = title


class ContentProcessor:
    """
    Content processing pipeline implementing PRD-008 specifications.
    
    Handles transformation of raw content into standardized, chunked format
    with complete database integration and error handling.
    """
    
    def __init__(self, config: ContentConfig, db_manager: DatabaseManager):
        """
        Initialize ContentProcessor with configuration and database manager.
        
        Args:
            config: Content processing configuration from CFG-001
            db_manager: Database manager instance from DB-001
        """
        self.config = config
        self.db_manager = db_manager
        
        # Configuration values from PRD-008
        self.chunk_size_default = config.chunk_size_default  # 1000 chars
        self.chunk_size_max = config.chunk_size_max  # 4000 chars
        self.chunk_overlap = config.chunk_overlap  # 100 chars
        self.quality_threshold = config.quality_threshold  # 0.3
        self.min_content_length = config.min_content_length  # 50 chars
        self.max_content_length = config.max_content_length  # 1000000 chars
        
        logger.info(f"ContentProcessor initialized with chunk_size={self.chunk_size_default}, "
                   f"quality_threshold={self.quality_threshold}")
    
    def process_document(self, raw_content: Union[FileContent, ScrapedContent], technology: str) -> Optional[ProcessedDocument]:
        """
        Process raw content into standardized, chunked format.
        
        Processing workflow: Normalization → Metadata Extraction → Quality Scoring → Chunking → Storage
        
        Args:
            raw_content: FileContent or ScrapedContent from clients
            technology: Technology/framework identifier
            
        Returns:
            ProcessedDocument if processing successful, None if content rejected
        """
        try:
            logger.info(f"Starting content processing for {raw_content.source_url}")
            
            # Step 1: Validate input content length
            if len(raw_content.content) < self.min_content_length:
                logger.warning(f"Content too short ({len(raw_content.content)} chars), minimum: {self.min_content_length}")
                return None
            
            if len(raw_content.content) > self.max_content_length:
                logger.warning(f"Content too long ({len(raw_content.content)} chars), maximum: {self.max_content_length}")
                return None
            
            # Step 2: Content normalization
            normalized_content = self._normalize_content(raw_content.content)
            
            # Step 3: Extract metadata
            content_metadata = self._extract_metadata(normalized_content, raw_content, technology)
            
            # Step 4: Calculate quality score
            quality_score = self._calculate_quality_score(normalized_content, content_metadata)
            
            # Step 5: Apply quality threshold filter
            if quality_score < self.quality_threshold:
                logger.warning(f"Content quality {quality_score:.2f} below threshold {self.quality_threshold}")
                return None
            
            # Step 6: Generate content chunks
            chunks = self._create_chunks(normalized_content, content_metadata['content_id'])
            
            # Step 7: Create ProcessedDocument
            processed_doc = ProcessedDocument(
                id=content_metadata['content_id'],
                title=content_metadata['title'],
                source_url=raw_content.source_url,
                technology=technology,
                content_hash=content_metadata['content_hash'],
                chunks=chunks,
                word_count=content_metadata['word_count'],
                quality_score=quality_score,
                processing_metadata={
                    'heading_count': content_metadata['heading_count'],
                    'code_block_count': content_metadata['code_block_count'],
                    'chunk_count': len(chunks),
                    'normalized_length': len(normalized_content),
                    'original_length': len(raw_content.content)
                },
                created_at=datetime.utcnow()
            )
            
            logger.info(f"Content processing completed: {len(chunks)} chunks, quality: {quality_score:.2f}")
            return processed_doc
            
        except Exception as e:
            logger.error(f"Content processing failed for {raw_content.source_url}: {e}")
            return None
    
    async def process_and_store_document(
        self,
        raw_content: Union[FileContent, ScrapedContent],
        technology: str
    ) -> Tuple[Optional[ProcessedDocument], str]:
        """
        Complete integration workflow: process content and persist to database.
        
        Database Integration Points:
        1. Check for existing content via content_hash
        2. Process raw content into ProcessedDocument
        3. Store metadata in content_metadata table
        4. Update processing_status throughout workflow
        5. Handle deduplication and error recovery
        
        Args:
            raw_content: FileContent or ScrapedContent from clients
            technology: Technology/framework identifier
            
        Returns:
            Tuple of (ProcessedDocument if successful, status_message)
        """
        content_id = None
        try:
            # Step 1: Check for duplicate content
            content_hash = self._compute_content_hash(raw_content.content)
            existing_doc = await self._check_duplicate_content(content_hash)
            if existing_doc:
                logger.info(f"Duplicate content found for hash {content_hash[:8]}...")
                return existing_doc, "duplicate_content_found"
            
            # Step 2: Create initial metadata record with 'processing' status
            content_id = self._generate_content_id(raw_content.source_url, technology)
            await self._create_initial_metadata_record(content_id, raw_content, technology, content_hash)
            
            # Step 3: Process content into ProcessedDocument
            processed_doc = self.process_document(raw_content, technology)
            if not processed_doc:
                await self._update_processing_status(content_id, "failed", "processing_failed")
                return None, "processing_failed"
            
            # Step 4: Store processed document metadata
            await self._store_document_metadata(processed_doc)
            
            # Step 5: Update status to completed
            await self._update_processing_status(content_id, "completed")
            
            logger.info(f"Document processing and storage completed for {content_id}")
            return processed_doc, "success"
            
        except Exception as e:
            logger.error(f"Document processing and storage failed: {e}")
            if content_id:
                await self._handle_processing_error(content_id, e)
            return None, f"error: {str(e)}"
    
    def _normalize_content(self, content: str) -> str:
        """
        Normalize content with text cleaning and standardization.
        
        Processing steps:
        - Remove excessive whitespace
        - Normalize line endings
        - Clean up formatting artifacts
        - Preserve code blocks and structure
        
        Args:
            content: Raw content string
            
        Returns:
            Normalized content string
        """
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace while preserving structure
        # Keep double newlines (paragraph breaks) but remove triple+ newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove trailing whitespace from lines
        content = '\n'.join(line.rstrip() for line in content.split('\n'))
        
        # Normalize tabs to spaces for consistency
        content = content.replace('\t', '    ')
        
        # Remove excessive spaces, but preserve code indentation patterns
        # Split by lines to handle each line individually
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Don't modify lines that are inside code blocks or have significant indentation
            if not line.startswith('    ') and '```' not in line:
                # Remove excessive spaces but preserve single spaces
                line = re.sub(r'[ ]{2,}', ' ', line)
            processed_lines.append(line)
        
        content = '\n'.join(processed_lines)
        
        # Clean up common formatting artifacts
        content = re.sub(r'[\u200b-\u200d\ufeff]', '', content)  # Remove zero-width characters
        
        return content.strip()
    
    def _extract_metadata(self, content: str, raw_content: Union[FileContent, ScrapedContent], technology: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from content.
        
        Metadata includes:
        - Word count, heading count, code block count
        - Content hash for deduplication
        - Title extraction
        - Content ID generation
        
        Args:
            content: Normalized content
            raw_content: Original content object
            technology: Technology identifier
            
        Returns:
            Dictionary with extracted metadata
        """
        # Generate unique content ID
        content_id = self._generate_content_id(raw_content.source_url, technology)
        
        # Extract title from content or use provided title
        title = raw_content.title or self._extract_title_from_content(content) or self._extract_title_from_url(raw_content.source_url)
        
        # Calculate word count (excluding code blocks for accuracy)
        word_count = self._count_words(content)
        
        # Count headings (markdown style)
        heading_count = len(re.findall(r'^#{1,6}\s+.+$', content, re.MULTILINE))
        
        # Count code blocks
        code_block_count = len(re.findall(r'```[\s\S]*?```', content)) + len(re.findall(r'`[^`\n]+`', content))
        
        # Generate content hash for deduplication
        content_hash = self._compute_content_hash(content)
        
        return {
            'content_id': content_id,
            'title': title,
            'word_count': word_count,
            'heading_count': heading_count,
            'code_block_count': code_block_count,
            'content_hash': content_hash
        }
    
    def _calculate_quality_score(self, content: str, metadata: Dict[str, Any]) -> float:
        """
        Calculate content quality score using heuristic analysis.
        
        Quality factors:
        - Content length and structure
        - Presence of headings and organization
        - Code examples and technical content
        - Language quality indicators
        
        Args:
            content: Normalized content
            metadata: Extracted metadata
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Base score from content length
        length_score = min(1.0, len(content) / 2000)  # Optimal around 2000 chars
        score += length_score * 0.3
        
        # Structure score from headings
        if metadata['heading_count'] > 0:
            structure_score = min(1.0, metadata['heading_count'] / 5)  # Optimal around 5 headings
            score += structure_score * 0.2
        
        # Technical content score from code blocks
        if metadata['code_block_count'] > 0:
            technical_score = min(1.0, metadata['code_block_count'] / 3)  # Optimal around 3 code blocks
            score += technical_score * 0.2
        
        # Language quality indicators
        sentence_count = len(re.findall(r'[.!?]+', content))
        if sentence_count > 0:
            avg_sentence_length = metadata['word_count'] / sentence_count
            if 10 <= avg_sentence_length <= 25:  # Good sentence length range
                score += 0.15
        
        # Content density (avoid too sparse content)
        if metadata['word_count'] > 100:
            density = metadata['word_count'] / len(content.split('\n'))
            if density > 5:  # Good word density per line
                score += 0.15
        
        return min(1.0, score)
    
    def _create_chunks(self, content: str, document_id: str) -> List[DocumentChunk]:
        """
        Create content chunks with configurable size and overlap.
        
        Chunking strategy:
        - Default chunk size: 1000 characters
        - Maximum chunk size: 4000 characters
        - Overlap: 100 characters
        - Preserve paragraph and code block boundaries
        
        Args:
            content: Normalized content to chunk
            document_id: Parent document identifier
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(content):
            # Calculate chunk end position
            chunk_end = min(current_pos + self.chunk_size_default, len(content))
            
            # Try to break at paragraph or sentence boundary
            chunk_text = content[current_pos:chunk_end]
            
            # If not at end of content, find better break point
            if chunk_end < len(content):
                # Look for paragraph break first
                last_paragraph = chunk_text.rfind('\n\n')
                if last_paragraph > len(chunk_text) * 0.7:  # Must be in last 30% to be useful
                    chunk_end = current_pos + last_paragraph + 2
                    chunk_text = content[current_pos:chunk_end]
                else:
                    # Look for sentence break
                    last_sentence = max(
                        chunk_text.rfind('. '),
                        chunk_text.rfind('! '),
                        chunk_text.rfind('? ')
                    )
                    if last_sentence > len(chunk_text) * 0.7:
                        chunk_end = current_pos + last_sentence + 2
                        chunk_text = content[current_pos:chunk_end]
            
            # Create chunk
            chunk = DocumentChunk(
                id=f"{document_id}_chunk_{chunk_index}",
                content=chunk_text.strip(),
                chunk_index=chunk_index,
                total_chunks=0,  # Will be updated after all chunks created
                word_count=len(chunk_text.split()),
                metadata={
                    'document_id': document_id,  # Store parent document ID in metadata
                    'start_position': current_pos,
                    'end_position': chunk_end,
                    'overlap_with_previous': min(self.chunk_overlap, current_pos) if chunk_index > 0 else 0
                }
            )
            chunks.append(chunk)
            
            # Move to next position with overlap
            current_pos = max(chunk_end - self.chunk_overlap, chunk_end)
            chunk_index += 1
            
            # Safety check to prevent infinite loops
            if chunk_index > 1000:
                logger.warning(f"Maximum chunk limit reached for document {document_id}")
                break
        
        # Update total_chunks for all chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        logger.debug(f"Created {len(chunks)} chunks for document {document_id}")
        return chunks
    
    def _compute_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content for deduplication"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _generate_content_id(self, source_url: str, technology: str) -> str:
        """Generate unique content ID from URL and technology"""
        # Create deterministic ID based on URL and technology
        url_hash = hashlib.md5(f"{source_url}_{technology}".encode('utf-8')).hexdigest()[:8]
        return f"{technology}_{url_hash}_{uuid.uuid4().hex[:8]}"
    
    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """Extract title from content (first heading or title-like pattern)"""
        # Look for first markdown heading
        heading_match = re.search(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()
        
        # Look for title-like patterns at start of content
        lines = content.split('\n')[:5]  # Check first 5 lines
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100 and not line.startswith('```'):
                # Check if line looks like a title (mostly alphanumeric, some punctuation)
                if re.match(r'^[A-Za-z0-9\s\-_:()]+$', line):
                    return line
        
        return None
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract title from URL path as fallback"""
        try:
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split('/') if part]
            if path_parts:
                # Use last path component, clean it up
                title = path_parts[-1]
                title = re.sub(r'\.[^.]+$', '', title)  # Remove file extension
                title = title.replace('-', ' ').replace('_', ' ')
                return title.title()
        except Exception:
            pass
        return "Untitled Document"
    
    def _count_words(self, content: str) -> int:
        """Count words excluding code blocks for accuracy"""
        # Remove code blocks temporarily
        content_no_code = re.sub(r'```[\s\S]*?```', '', content)
        content_no_code = re.sub(r'`[^`\n]+`', '', content_no_code)
        
        # Count words
        words = re.findall(r'\b\w+\b', content_no_code)
        return len(words)
    
    # Database integration methods
    async def _check_duplicate_content(self, content_hash: str) -> Optional[ProcessedDocument]:
        """
        Check if content already exists in database.
        
        Args:
            content_hash: SHA-256 hash of content
            
        Returns:
            ProcessedDocument if found, None otherwise
        """
        query = "SELECT * FROM content_metadata WHERE content_hash = ?"
        result = await self.db_manager.fetch_one(query, (content_hash,))
        if result:
            return await self.db_manager.load_processed_document_from_metadata(result)
        return None
    
    async def _create_initial_metadata_record(
        self,
        content_id: str,
        raw_content: Union[FileContent, ScrapedContent],
        technology: str,
        content_hash: str
    ) -> None:
        """
        Create initial record in content_metadata table with 'processing' status.
        
        Args:
            content_id: Unique content identifier
            raw_content: Original content object
            technology: Technology identifier
            content_hash: Content hash for deduplication
        """
        query = """
            INSERT INTO content_metadata
            (content_id, title, source_url, technology, content_hash, processing_status, created_at)
            VALUES (?, ?, ?, ?, ?, 'processing', CURRENT_TIMESTAMP)
        """
        title = getattr(raw_content, 'title', '') or self._extract_title_from_url(raw_content.source_url)
        params = (content_id, title, raw_content.source_url, technology, content_hash)
        await self.db_manager.execute(query, params)
        logger.debug(f"Created initial metadata record for {content_id}")
    
    async def _store_document_metadata(self, processed_doc: ProcessedDocument) -> None:
        """
        Update content_metadata table with processing results.
        
        Args:
            processed_doc: Complete processed document
        """
        query = """
            UPDATE content_metadata SET
                word_count = ?, heading_count = ?, code_block_count = ?,
                chunk_count = ?, quality_score = ?, updated_at = CURRENT_TIMESTAMP
            WHERE content_id = ?
        """
        params = (
            processed_doc.word_count,
            processed_doc.processing_metadata.get('heading_count', 0),
            processed_doc.processing_metadata.get('code_block_count', 0),
            len(processed_doc.chunks),
            processed_doc.quality_score,
            processed_doc.id
        )
        await self.db_manager.execute(query, params)
        logger.debug(f"Stored document metadata for {processed_doc.id}")
    
    async def _update_processing_status(
        self,
        content_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update processing_status in content_metadata table.
        
        Valid statuses: 'pending', 'processing', 'completed', 'failed', 'flagged'
        
        Args:
            content_id: Content identifier
            status: New processing status
            error_message: Optional error message for logging
        """
        query = "UPDATE content_metadata SET processing_status = ?, updated_at = CURRENT_TIMESTAMP WHERE content_id = ?"
        await self.db_manager.execute(query, (status, content_id))
        
        if error_message:
            logger.error(f"Processing failed for {content_id}: {error_message}")
        else:
            logger.debug(f"Updated processing status to '{status}' for {content_id}")
    
    async def _handle_processing_error(self, content_id: str, error: Exception) -> None:
        """
        Comprehensive error handling for processing failures.
        
        Error Recovery Patterns:
        1. Update processing_status to 'failed'
        2. Log detailed error information
        3. Determine if error is retryable
        4. Clean up partial processing artifacts
        
        Args:
            content_id: Content identifier
            error: Exception that occurred
        """
        try:
            await self._update_processing_status(content_id, "failed")
            
            # Log with structured error data
            logger.error(
                "Content processing failed",
                extra={
                    "content_id": content_id,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retryable": self._is_retryable_error(error)
                }
            )
            
            # Clean up any partial artifacts
            await self._cleanup_partial_processing(content_id)
            
        except Exception as cleanup_error:
            logger.critical(f"Failed to handle processing error for {content_id}: {cleanup_error}")
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if processing error is retryable.
        
        Retryable errors:
        - Network timeouts
        - Temporary database connection issues
        - Memory pressure (for large documents)
        
        Non-retryable errors:
        - Invalid content format
        - Content quality below threshold
        - Malformed input data
        
        Args:
            error: Exception to evaluate
            
        Returns:
            True if error is retryable, False otherwise
        """
        retryable_types = (
            ConnectionError,
            TimeoutError,
            MemoryError,
        )
        return isinstance(error, retryable_types)
    
    async def _cleanup_partial_processing(self, content_id: str) -> None:
        """
        Clean up any partial processing artifacts.
        
        Cleanup tasks:
        1. Remove any temporary files
        2. Clear partial cache entries
        3. Reset processing counters
        
        Args:
            content_id: Content identifier to clean up
        """
        # For now, this is a placeholder as we don't have temporary artifacts
        # In future iterations, this could clean up:
        # - Temporary chunk files
        # - Partial cache entries
        # - Processing locks
        logger.debug(f"Cleaned up partial processing artifacts for {content_id}")