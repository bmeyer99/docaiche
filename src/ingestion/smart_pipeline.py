"""
Smart Ingestion Pipeline with LLM-powered processing
Intelligently processes and stores documentation in Weaviate
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.llm.client import LLMProviderClient
from src.clients.weaviate_client import WeaviateVectorClient
from src.database.manager import DatabaseManager
from src.search.llm_query_analyzer import QueryIntent
from src.document_processing.models import DocumentContent

logger = logging.getLogger(__name__)


class Chunk(BaseModel):
    """Represents a document chunk"""
    text: str
    index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessingResult(BaseModel):
    """Result of processing a document"""
    success: bool
    chunks_processed: int
    workspace_slug: str
    error_message: Optional[str] = None


class SmartIngestionPipeline:
    """Intelligent document ingestion pipeline"""
    
    def __init__(
        self,
        llm_client: LLMProviderClient,
        weaviate_client: WeaviateVectorClient,
        db_manager: DatabaseManager
    ):
        self.llm = llm_client
        self.weaviate = weaviate_client
        self.db = db_manager
    
    async def process_documentation(
        self,
        content: DocumentContent,
        intent: QueryIntent
    ) -> ProcessingResult:
        """
        Process documentation content intelligently
        
        Args:
            content: Document content to process
            intent: Query intent for context
            
        Returns:
            ProcessingResult with status and details
        """
        try:
            # 1. Smart chunking based on content and intent
            chunks = await self._smart_chunk(content.text, intent)
            
            if not chunks:
                return ProcessingResult(
                    success=False,
                    chunks_processed=0,
                    workspace_slug="",
                    error_message="No chunks created from content"
                )
            
            # 2. Create or get workspace
            workspace_name = f"{intent.technology}-docs"
            workspace_slug = workspace_name.lower().replace(" ", "-")
            
            # Check if workspace exists
            workspaces = await self.weaviate.list_workspaces()
            workspace_exists = any(w.get("slug") == workspace_slug for w in workspaces)
            
            if not workspace_exists:
                workspace = await self.weaviate.get_or_create_workspace(workspace_slug, workspace_name)
                if not workspace:
                    return ProcessingResult(
                        success=False,
                        chunks_processed=0,
                        workspace_slug="",
                        error_message="Failed to create workspace"
                    )
            
            # 3. Upload all chunks to Weaviate as a single document
            from src.database.connection import ProcessedDocument, DocumentChunk
            
            # Convert all chunks to DocumentChunk objects
            doc_chunks = []
            for chunk in chunks:
                metadata = {
                    "source": content.source_url,
                    "technology": intent.technology,
                    "topics": intent.topics,
                    "doc_type": intent.doc_type,
                    "processed_at": datetime.utcnow().isoformat()
                }
                metadata.update(chunk.metadata)
                
                doc_chunk = DocumentChunk(
                    id=f"{content.source_url}_{chunk.index}",
                    parent_document_id=content.content_id,
                    content=chunk.text,
                    chunk_index=chunk.index,
                    total_chunks=len(chunks),
                    created_at=datetime.utcnow(),
                    source_provider=content.metadata.get('source', 'unknown') if hasattr(content, 'metadata') and content.metadata else None
                )
                doc_chunks.append(doc_chunk)
            
            # Create ProcessedDocument with all chunks
            from src.database.connection import DocumentMetadata
            
            # Create metadata for the document
            doc_metadata = DocumentMetadata(
                word_count=sum(len(chunk.text.split()) for chunk in chunks),
                heading_count=sum(1 for chunk in chunks for line in chunk.text.split('\n') if line.strip().startswith('#')),
                code_block_count=sum(chunk.text.count('```') // 2 for chunk in chunks),
                content_hash=str(hash(content.text))[:16],
                created_at=datetime.utcnow()
            )
            
            processed_doc = ProcessedDocument(
                id=content.content_id,
                title=content.title or content.source_url.split('/')[-1],
                full_content=content.text,
                source_url=content.source_url,
                technology=intent.technology,
                metadata=doc_metadata,
                quality_score=0.8,  # Default quality score
                chunks=doc_chunks,
                created_at=datetime.utcnow()
            )
            
            # Upload entire document to Weaviate
            try:
                result = await self.weaviate.upload_document(workspace_slug, processed_doc)
                uploaded_count = result.successful_uploads
            except Exception as e:
                logger.error(f"Failed to upload document: {e}")
                uploaded_count = 0
            
            # 4. Store metadata in database
            await self._store_content_metadata(
                content, 
                chunks, 
                workspace_slug,
                intent,
                uploaded_count
            )
            
            return ProcessingResult(
                success=uploaded_count > 0,
                chunks_processed=uploaded_count,
                workspace_slug=workspace_slug
            )
            
        except Exception as e:
            logger.error(f"Documentation processing failed: {e}")
            return ProcessingResult(
                success=False,
                chunks_processed=0,
                workspace_slug="",
                error_message=str(e)
            )
    
    async def _smart_chunk(self, text: str, intent: QueryIntent) -> List[Chunk]:
        """
        Intelligently chunk document based on content structure and intent
        
        Args:
            text: Document text to chunk
            intent: Query intent for context
            
        Returns:
            List of chunks
        """
        try:
            # For very long documents, process in sections
            max_text_length = 10000
            if len(text) > max_text_length:
                # Simple chunking for very long documents
                return self._simple_chunk(text, chunk_size=1000)
            
            prompt = f"""
            Split this {intent.technology} documentation into semantic chunks.
            
            Document type: {intent.doc_type}
            Topics: {', '.join(intent.topics) if intent.topics else 'general'}
            User level: {intent.user_level}
            
            Requirements:
            - Each chunk should be 500-1000 tokens (roughly 2000-4000 characters)
            - Keep code blocks completely intact within a chunk
            - Maintain context and coherence
            - End chunks at natural boundaries (end of section, paragraph, etc.)
            - Preserve markdown formatting
            
            Mark chunk boundaries with exactly: ---CHUNK---
            
            Document to chunk:
            {text[:8000]}  # Limit to prevent token overflow
            
            Split the document and mark boundaries. Include the entire processable content.
            """
            
            response = await self.llm.generate(prompt)
            
            # Split by chunk marker
            chunk_texts = response.split("---CHUNK---")
            
            # Create chunk objects
            chunks = []
            for i, chunk_text in enumerate(chunk_texts):
                chunk_text = chunk_text.strip()
                if chunk_text and len(chunk_text) > 50:  # Minimum chunk size
                    # Extract any headers or key topics from chunk
                    chunk_metadata = await self._extract_chunk_metadata(chunk_text, intent)
                    
                    chunks.append(Chunk(
                        text=chunk_text,
                        index=i,
                        metadata=chunk_metadata
                    ))
            
            # If no chunks were created or too few, fall back to simple chunking
            if len(chunks) < 2:
                return self._simple_chunk(text, chunk_size=1000)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Smart chunking failed: {e}")
            # Fall back to simple chunking
            return self._simple_chunk(text, chunk_size=1000)
    
    def _simple_chunk(self, text: str, chunk_size: int = 1000) -> List[Chunk]:
        """
        Simple text chunking with overlap
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            
        Returns:
            List of chunks
        """
        chunks = []
        overlap = 100
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph exceeds chunk size, start new chunk
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(Chunk(
                    text=current_chunk.strip(),
                    index=chunk_index,
                    metadata={"chunking_method": "simple"}
                ))
                chunk_index += 1
                
                # Start new chunk with overlap from previous
                if len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                index=chunk_index,
                metadata={"chunking_method": "simple"}
            ))
        
        return chunks
    
    async def _extract_chunk_metadata(
        self, 
        chunk_text: str, 
        intent: QueryIntent
    ) -> Dict[str, Any]:
        """
        Extract metadata from a chunk using LLM
        
        Args:
            chunk_text: Chunk text
            intent: Query intent
            
        Returns:
            Metadata dictionary
        """
        try:
            # For performance, only extract metadata for first 500 chars
            preview = chunk_text[:500]
            
            prompt = f"""
            Extract key metadata from this documentation chunk.
            
            Technology: {intent.technology}
            Chunk preview: {preview}
            
            Extract:
            1. Main topic or concept covered
            2. Any code language used
            3. Difficulty level (beginner/intermediate/advanced)
            
            Return as JSON:
            {{
                "main_topic": "...",
                "code_language": "...",
                "difficulty": "..."
            }}
            
            Return ONLY the JSON.
            """
            
            response = await self.llm.generate(prompt)
            
            # Parse response
            try:
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                
                metadata = json.loads(cleaned_response.strip())
                return metadata
                
            except json.JSONDecodeError:
                return {"extraction_failed": True}
                
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {}
    
    async def _store_content_metadata(
        self,
        content: DocumentContent,
        chunks: List[Chunk],
        workspace_slug: str,
        intent: QueryIntent,
        uploaded_count: int
    ):
        """
        Store content metadata in database
        
        Args:
            content: Original document content
            chunks: Processed chunks
            workspace_slug: Weaviate workspace
            intent: Query intent
            uploaded_count: Number of successfully uploaded chunks
        """
        try:
            # Calculate quality score based on successful uploads
            quality_score = uploaded_count / len(chunks) if chunks else 0.0
            
            # Prepare metadata
            metadata = {
                "title": content.title or f"{intent.technology} Documentation",
                "source_url": content.source_url,
                "technology": intent.technology,
                "topics": json.dumps(intent.topics),
                "doc_type": intent.doc_type,
                "user_level": intent.user_level,
                "workspace": workspace_slug,
                "chunks": len(chunks),
                "uploaded_chunks": uploaded_count,
                "quality_score": quality_score,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Store in content_metadata table
            query = """
            INSERT INTO content_metadata (
                content_id,
                title,
                source_url,
                technology,
                quality_score,
                enrichment_metadata,
                weaviate_workspace,
                chunk_count,
                created_at,
                updated_at
            ) VALUES (
                :content_id,
                :title,
                :source_url,
                :technology,
                :quality_score,
                :metadata,
                :workspace,
                :chunks,
                :created_at,
                :updated_at
            )
            ON CONFLICT(content_id) DO UPDATE SET
                quality_score = :quality_score,
                enrichment_metadata = :metadata,
                chunk_count = :chunks,
                updated_at = :updated_at
            """
            
            params = {
                "content_id": content.content_id,
                "title": metadata["title"],
                "source_url": metadata["source_url"],
                "technology": metadata["technology"],
                "quality_score": metadata["quality_score"],
                "metadata": json.dumps(metadata),
                "workspace": workspace_slug,
                "chunks": len(chunks),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await self.db.execute(query, params)
            
        except Exception as e:
            logger.error(f"Failed to store content metadata: {e}")