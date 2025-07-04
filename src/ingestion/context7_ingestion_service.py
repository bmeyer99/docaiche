"""
Context7 Ingestion Service
==========================

Specialized ingestion service for Context7 documentation with intelligent TTL support
and enhanced metadata processing. Extends SmartIngestionPipeline with Context7-specific
features and optimizations.
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator

from .smart_pipeline import SmartIngestionPipeline, ProcessingResult, Chunk
from src.llm.client import LLMProviderClient
from src.clients.weaviate_client import WeaviateVectorClient
from src.database.manager import DatabaseManager
from src.search.llm_query_analyzer import QueryIntent
from src.document_processing.models import DocumentContent
from src.mcp.providers.models import SearchResult

logger = logging.getLogger(__name__)


class Context7Document(BaseModel):
    """Enhanced document model for Context7 processing"""
    content: str
    title: str
    source_url: str
    technology: str
    owner: str
    version: Optional[str] = None
    doc_type: str = "documentation"
    language: str = "en"
    quality_indicators: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TTLConfig(BaseModel):
    """TTL configuration for different document types"""
    default_days: int = 30
    min_days: int = 1
    max_days: int = 90
    
    @validator('min_days')
    def validate_min_days(cls, v):
        if v <= 0:
            raise ValueError('min_days must be positive')
        return v
    
    @validator('max_days')
    def validate_max_days(cls, v, values):
        if 'min_days' in values and v <= values['min_days']:
            raise ValueError('max_days must be greater than min_days')
        return v
    
    @validator('default_days')
    def validate_default_days(cls, v, values):
        if 'min_days' in values and v < values['min_days']:
            raise ValueError('default_days must be between min_days and max_days')
        if 'max_days' in values and v > values['max_days']:
            raise ValueError('default_days must be between min_days and max_days')
        return v
    
    @validator('technology_multipliers')
    def validate_technology_multipliers(cls, v):
        for tech, multiplier in v.items():
            if multiplier <= 0:
                raise ValueError('Technology multipliers must be positive')
        return v
    
    @validator('doc_type_multipliers')
    def validate_doc_type_multipliers(cls, v):
        for doc_type, multiplier in v.items():
            if multiplier <= 0:
                raise ValueError('Document type multipliers must be positive')
        return v
    
    # Technology-specific TTL adjustments
    technology_multipliers: Dict[str, float] = Field(default_factory=lambda: {
        "react": 1.5,
        "vue": 1.5,
        "angular": 1.5,
        "next.js": 2.0,
        "typescript": 2.0,
        "javascript": 1.0,
        "node.js": 1.0,
        "python": 1.0,
        "django": 1.5,
        "flask": 1.5,
        "fastapi": 1.5,
        "express": 1.0,
        "tailwind": 1.0,
        "bootstrap": 0.8,
        "webpack": 1.2,
        "vite": 1.2,
        "rollup": 1.2,
        "parcel": 1.2,
        "babel": 1.2,
        "eslint": 1.2,
        "prettier": 1.2,
        "jest": 1.2,
        "cypress": 1.2,
        "playwright": 1.2,
    })
    
    # Document type multipliers
    doc_type_multipliers: Dict[str, float] = Field(default_factory=lambda: {
        "api": 2.0,
        "guide": 1.5,
        "tutorial": 1.2,
        "reference": 2.5,
        "changelog": 0.5,
        "migration": 1.0,
        "examples": 1.0,
        "cookbook": 1.5,
        "best_practices": 2.0,
        "troubleshooting": 1.8,
        "configuration": 1.8,
        "installation": 1.0,
        "getting_started": 1.2,
        "faq": 1.5,
        "blog": 0.8,
        "news": 0.3,
        "announcement": 0.5,
        "release_notes": 0.5,
    })


class Context7IngestionService(SmartIngestionPipeline):
    """
    Context7-specific ingestion service with intelligent TTL support.
    
    Extends SmartIngestionPipeline with:
    - Intelligent TTL calculation based on content analysis
    - Context7-specific metadata enrichment
    - Quality assessment for documentation
    - Batch processing for multiple Context7 results
    - Integration with Weaviate TTL infrastructure
    """
    
    def __init__(
        self,
        llm_client: LLMProviderClient,
        weaviate_client: WeaviateVectorClient,
        db_manager: DatabaseManager,
        ttl_config: Optional[TTLConfig] = None
    ):
        super().__init__(llm_client, weaviate_client, db_manager)
        self.ttl_config = ttl_config or TTLConfig()
        
        logger.info("Context7 ingestion service initialized with TTL support")
    
    async def process_context7_results(
        self,
        search_results: List[SearchResult],
        intent: QueryIntent,
        correlation_id: str = None
    ) -> List[ProcessingResult]:
        """
        Process multiple Context7 search results with batch optimization.
        
        Args:
            search_results: List of Context7 search results
            intent: Query intent for processing context
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            List of processing results
        """
        start_time = time.time()
        if correlation_id is None:
            correlation_id = f"ctx7_ingest_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Processing {len(search_results)} Context7 results")
            logger.info(f"PIPELINE_METRICS: step=context7_batch_processing_start "
                       f"correlation_id={correlation_id} result_count={len(search_results)} "
                       f"technology={intent.technology}")
            
            # Convert search results to Context7 documents
            conversion_start = time.time()
            documents = []
            for result in search_results:
                doc = await self._convert_search_result_to_document(result, intent, correlation_id)
                if doc:
                    documents.append(doc)
            
            conversion_time = int((time.time() - conversion_start) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_document_conversion duration_ms={conversion_time} "
                       f"correlation_id={correlation_id} converted_count={len(documents)} "
                       f"original_count={len(search_results)}")
            
            if not documents:
                logger.warning("No valid documents found in search results")
                return []
            
            # Process documents in batches
            batch_size = 5  # Process 5 documents at once
            results = []
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_start = time.time()
                batch_results = await self._process_document_batch(batch, intent, correlation_id)
                batch_time = int((time.time() - batch_start) * 1000)
                
                logger.info(f"PIPELINE_METRICS: step=context7_batch_process duration_ms={batch_time} "
                           f"correlation_id={correlation_id} batch_number={i//batch_size + 1} "
                           f"batch_size={len(batch)} processed_count={len(batch_results)}")
                
                results.extend(batch_results)
            
            total_time = int((time.time() - start_time) * 1000)
            logger.info(f"Successfully processed {len(results)} Context7 documents")
            logger.info(f"PIPELINE_METRICS: step=context7_batch_processing_complete duration_ms={total_time} "
                       f"correlation_id={correlation_id} total_processed={len(results)} "
                       f"success_rate={len(results)/len(search_results)*100:.1f}%")
            return results
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to process Context7 results: {e}")
            logger.info(f"PIPELINE_METRICS: step=context7_batch_processing_error duration_ms={total_time} "
                       f"correlation_id={correlation_id} error=\"{str(e)}\" success=false")
            return []
    
    async def process_context7_document(
        self,
        document: Context7Document,
        intent: QueryIntent,
        correlation_id: str = None
    ) -> ProcessingResult:
        """
        Process a single Context7 document with enhanced metadata and TTL.
        
        Args:
            document: Context7 document to process
            intent: Query intent for processing context
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Processing result with TTL information
        """
        start_time = time.time()
        if correlation_id is None:
            correlation_id = f"ctx7_doc_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Processing Context7 document: {document.title}")
            logger.info(f"PIPELINE_METRICS: step=context7_document_processing_start "
                       f"correlation_id={correlation_id} document_title=\"{document.title}\" "
                       f"technology={document.technology} owner={document.owner}")
            
            # Enhanced content analysis
            enhancement_start = time.time()
            enhanced_content = await self._enhance_document_content(document, intent)
            enhancement_time = int((time.time() - enhancement_start) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_content_enhancement duration_ms={enhancement_time} "
                       f"correlation_id={correlation_id} original_length={len(document.content)} "
                       f"enhanced_length={len(enhanced_content)}")
            
            # Calculate intelligent TTL
            ttl_start = time.time()
            ttl_days = await self._calculate_intelligent_ttl(document, intent, correlation_id)
            ttl_time = int((time.time() - ttl_start) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_ttl_calculation duration_ms={ttl_time} "
                       f"correlation_id={correlation_id} ttl_days={ttl_days} "
                       f"doc_type={document.doc_type} technology={document.technology}")
            
            # Perform quality assessment
            quality_start = time.time()
            quality_score = await self._assess_document_quality(document, correlation_id)
            quality_time = int((time.time() - quality_start) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_quality_assessment duration_ms={quality_time} "
                       f"correlation_id={correlation_id} quality_score={quality_score:.2f} "
                       f"content_length={len(document.content)}")
            
            # Create DocumentContent for pipeline processing
            doc_content = DocumentContent(
                content_id=document.source_url,
                title=document.title,
                text=enhanced_content,
                source_url=document.source_url,
                metadata={
                    "technology": document.technology,
                    "owner": document.owner,
                    "version": document.version,
                    "doc_type": document.doc_type,
                    "language": document.language,
                    "quality_score": quality_score,
                    "ttl_days": ttl_days,
                    "source_provider": "context7",
                    "processed_at": datetime.utcnow().isoformat()
                }
            )
            
            # Process with enhanced pipeline
            pipeline_start = time.time()
            result = await self._process_with_ttl(doc_content, intent, ttl_days, correlation_id)
            pipeline_time = int((time.time() - pipeline_start) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_pipeline_processing duration_ms={pipeline_time} "
                       f"correlation_id={correlation_id} success={result.success} "
                       f"chunks_processed={result.chunks_processed}")
            
            total_time = int((time.time() - start_time) * 1000)
            logger.info(f"Successfully processed Context7 document with TTL: {ttl_days} days")
            logger.info(f"PIPELINE_METRICS: step=context7_document_processing_complete duration_ms={total_time} "
                       f"correlation_id={correlation_id} success=true ttl_days={ttl_days} "
                       f"quality_score={quality_score:.2f} chunks_processed={result.chunks_processed}")
            return result
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to process Context7 document: {e}")
            logger.info(f"PIPELINE_METRICS: step=context7_document_processing_error duration_ms={total_time} "
                       f"correlation_id={correlation_id} error=\"{str(e)}\" success=false")
            return ProcessingResult(
                success=False,
                chunks_processed=0,
                workspace_slug="",
                error_message=str(e)
            )
    
    async def _convert_search_result_to_document(
        self,
        result: SearchResult,
        intent: QueryIntent,
        correlation_id: str = None
    ) -> Optional[Context7Document]:
        """Convert SearchResult to Context7Document"""
        try:
            # Extract owner and technology from metadata
            owner = result.metadata.get("owner", "unknown")
            technology = result.metadata.get("technology", intent.technology)
            
            # Extract version information if available
            version = await self._extract_version_from_content(result.content)
            
            # Determine document type from title and content
            doc_type = await self._classify_document_type(result.title, result.content)
            
            return Context7Document(
                content=result.content,
                title=result.title,
                source_url=result.url,
                technology=technology,
                owner=owner,
                version=version,
                doc_type=doc_type,
                language=result.language or "en",
                quality_indicators=await self._extract_quality_indicators(result),
                metadata=result.metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to convert search result to document: {e}")
            return None
    
    async def _process_document_batch(
        self,
        documents: List[Context7Document],
        intent: QueryIntent,
        correlation_id: str = None
    ) -> List[ProcessingResult]:
        """Process a batch of documents efficiently"""
        import asyncio
        
        tasks = []
        for doc in documents:
            task = asyncio.create_task(
                self.process_context7_document(doc, intent, correlation_id)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, ProcessingResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
        
        return valid_results
    
    async def _enhance_document_content(
        self,
        document: Context7Document,
        intent: QueryIntent
    ) -> str:
        """Enhance document content with Context7-specific processing"""
        try:
            # Add structured metadata header
            metadata_header = f"""# {document.title}

**Technology:** {document.technology}
**Owner:** {document.owner}
**Version:** {document.version or 'Latest'}
**Document Type:** {document.doc_type}
**Source:** {document.source_url}

---

"""
            
            # Clean and normalize content
            content = document.content.strip()
            
            # Add context-specific enhancements
            if document.technology in ["react", "vue", "angular"]:
                content = await self._enhance_frontend_content(content, document.technology)
            elif document.technology in ["node.js", "express", "fastapi"]:
                content = await self._enhance_backend_content(content, document.technology)
            elif document.technology in ["typescript", "javascript"]:
                content = await self._enhance_language_content(content, document.technology)
            
            # Combine enhanced content
            enhanced_content = metadata_header + content
            
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Failed to enhance document content: {e}")
            return document.content
    
    async def _calculate_intelligent_ttl(
        self,
        document: Context7Document,
        intent: QueryIntent,
        correlation_id: str = None
    ) -> int:
        """Calculate intelligent TTL based on document characteristics"""
        try:
            base_ttl = self.ttl_config.default_days
            
            # Apply technology multiplier
            tech_multiplier = self.ttl_config.technology_multipliers.get(
                document.technology.lower(), 1.0
            )
            
            # Apply document type multiplier
            doc_type_multiplier = self.ttl_config.doc_type_multipliers.get(
                document.doc_type.lower(), 1.0
            )
            
            # Calculate base TTL
            calculated_ttl = base_ttl * tech_multiplier * doc_type_multiplier
            
            # Apply content-based adjustments
            content_adjustment = await self._analyze_content_for_ttl(document)
            calculated_ttl *= content_adjustment
            
            # Apply version-based adjustments
            version_adjustment = await self._analyze_version_for_ttl(document)
            calculated_ttl *= version_adjustment
            
            # Apply quality-based adjustments
            quality_score = document.quality_indicators.get("overall_score", 0.8)
            if quality_score > 0.9:
                calculated_ttl *= 1.2  # High quality content lasts longer
            elif quality_score < 0.5:
                calculated_ttl *= 0.7  # Low quality content expires sooner
            
            # Ensure TTL is within bounds
            final_ttl = max(
                self.ttl_config.min_days,
                min(int(calculated_ttl), self.ttl_config.max_days)
            )
            
            logger.info(f"Calculated TTL for {document.technology}/{document.doc_type}: {final_ttl} days")
            if correlation_id:
                logger.info(f"PIPELINE_METRICS: step=context7_ttl_calculation_detail "
                           f"correlation_id={correlation_id} base_ttl={base_ttl} "
                           f"tech_multiplier={tech_multiplier} doc_type_multiplier={doc_type_multiplier} "
                           f"final_ttl={final_ttl} quality_score={quality_score}")
            return final_ttl
            
        except Exception as e:
            logger.error(f"Failed to calculate intelligent TTL: {e}")
            return self.ttl_config.default_days
    
    async def _analyze_content_for_ttl(self, document: Context7Document) -> float:
        """Analyze content characteristics to adjust TTL"""
        try:
            content = document.content.lower()
            
            # Check for version-specific indicators
            if any(term in content for term in ["deprecated", "legacy", "old", "outdated"]):
                return 0.5  # Shorter TTL for deprecated content
            
            # Check for stability indicators
            if any(term in content for term in ["stable", "lts", "production", "recommended"]):
                return 1.5  # Longer TTL for stable content
            
            # Check for experimental/beta indicators
            if any(term in content for term in ["beta", "experimental", "preview", "alpha"]):
                return 0.7  # Shorter TTL for experimental content
            
            # Check for comprehensive content indicators
            if any(term in content for term in ["complete", "comprehensive", "detailed", "thorough"]):
                return 1.2  # Longer TTL for comprehensive content
            
            # Check content length (longer content often more valuable)
            content_length = len(document.content)
            if content_length > 10000:
                return 1.1  # Longer TTL for extensive content
            elif content_length < 1000:
                return 0.9  # Shorter TTL for brief content
            
            return 1.0  # Default multiplier
            
        except Exception as e:
            logger.error(f"Failed to analyze content for TTL: {e}")
            return 1.0
    
    async def _analyze_version_for_ttl(self, document: Context7Document) -> float:
        """Analyze version information to adjust TTL"""
        try:
            if not document.version:
                return 1.0
            
            version = document.version.lower()
            
            # Check for version patterns
            if any(term in version for term in ["latest", "current", "stable"]):
                return 1.3  # Longer TTL for latest versions
            
            if any(term in version for term in ["beta", "alpha", "rc", "preview"]):
                return 0.6  # Shorter TTL for pre-release versions
            
            # Check for major version indicators
            if "v1" in version or "1.0" in version:
                return 1.1  # Slightly longer for major versions
            
            # Check for specific version numbers
            import re
            version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
            if version_match:
                major, minor, patch = map(int, version_match.groups())
                if major >= 3:  # Mature versions
                    return 1.2
                elif major == 0:  # Early versions
                    return 0.8
            
            return 1.0  # Default multiplier
            
        except Exception as e:
            logger.error(f"Failed to analyze version for TTL: {e}")
            return 1.0
    
    async def _assess_document_quality(self, document: Context7Document, correlation_id: str = None) -> float:
        """Assess document quality using multiple metrics"""
        try:
            quality_score = 0.0
            max_score = 1.0
            
            # Content length quality (0.2 max)
            content_length = len(document.content)
            if content_length > 5000:
                quality_score += 0.2
            elif content_length > 1000:
                quality_score += 0.15
            elif content_length > 500:
                quality_score += 0.1
            
            # Code examples quality (0.2 max)
            code_blocks = len(re.findall(r'```[\s\S]*?```', document.content))
            if code_blocks >= 5:
                quality_score += 0.2
            elif code_blocks >= 3:
                quality_score += 0.15
            elif code_blocks >= 1:
                quality_score += 0.1
            
            # Structure quality (0.2 max)
            headers = len(re.findall(r'^#+\s', document.content, re.MULTILINE))
            if headers >= 10:
                quality_score += 0.2
            elif headers >= 5:
                quality_score += 0.15
            elif headers >= 3:
                quality_score += 0.1
            
            # Link quality (0.2 max)
            links = len(re.findall(r'\[.*?\]\(.*?\)', document.content))
            if links >= 10:
                quality_score += 0.2
            elif links >= 5:
                quality_score += 0.15
            elif links >= 2:
                quality_score += 0.1
            
            # Completeness quality (0.2 max)
            completeness_indicators = [
                "installation", "setup", "configuration", "example", "usage",
                "api", "reference", "guide", "tutorial", "troubleshooting"
            ]
            content_lower = document.content.lower()
            found_indicators = sum(1 for indicator in completeness_indicators if indicator in content_lower)
            
            if found_indicators >= 7:
                quality_score += 0.2
            elif found_indicators >= 5:
                quality_score += 0.15
            elif found_indicators >= 3:
                quality_score += 0.1
            
            # Normalize to 0-1 scale
            final_score = min(quality_score, max_score)
            
            logger.info(f"Document quality assessment: {final_score:.2f}")
            if correlation_id:
                logger.info(f"PIPELINE_METRICS: step=context7_quality_assessment_detail "
                           f"correlation_id={correlation_id} content_length={content_length} "
                           f"code_blocks={code_blocks} headers={headers} links={links} "
                           f"found_indicators={found_indicators} final_score={final_score:.2f}")
            return final_score
            
        except Exception as e:
            logger.error(f"Failed to assess document quality: {e}")
            return 0.5  # Default quality score
    
    async def _process_with_ttl(
        self,
        content: DocumentContent,
        intent: QueryIntent,
        ttl_days: int,
        correlation_id: str = None
    ) -> ProcessingResult:
        """Process document with TTL support"""
        try:
            # First, process with the standard pipeline
            result = await self.process_documentation(content, intent)
            
            if not result.success:
                return result
            
            # Add TTL metadata to stored chunks
            await self._add_ttl_metadata(content, result.workspace_slug, ttl_days, correlation_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process with TTL: {e}")
            return ProcessingResult(
                success=False,
                chunks_processed=0,
                workspace_slug="",
                error_message=str(e)
            )
    
    async def _add_ttl_metadata(
        self,
        content: DocumentContent,
        workspace_slug: str,
        ttl_days: int,
        correlation_id: str = None
    ) -> None:
        """Add TTL metadata to processed chunks in Weaviate"""
        try:
            # Calculate TTL timestamps
            now = datetime.utcnow()
            expires_at = now + timedelta(days=ttl_days)
            
            # Update content metadata in database
            ttl_metadata = {
                "ttl_days": ttl_days,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "source_provider": "context7"
            }
            
            # Store TTL metadata
            query = """
            UPDATE content_metadata 
            SET enrichment_metadata = jsonb_set(
                COALESCE(enrichment_metadata, '{}'),
                '{ttl_info}',
                :ttl_metadata
            ),
            updated_at = :updated_at
            WHERE content_id = :content_id
            """
            
            await self.db.execute(query, {
                "ttl_metadata": json.dumps(ttl_metadata),
                "updated_at": now,
                "content_id": content.content_id
            })
            
            logger.info(f"Added TTL metadata for content: {content.content_id}")
            if correlation_id:
                logger.info(f"PIPELINE_METRICS: step=context7_ttl_metadata_added "
                           f"correlation_id={correlation_id} content_id={content.content_id} "
                           f"workspace_slug={workspace_slug} ttl_days={ttl_days}")
            
        except Exception as e:
            logger.error(f"Failed to add TTL metadata: {e}")
            if correlation_id:
                logger.info(f"PIPELINE_METRICS: step=context7_ttl_metadata_error "
                           f"correlation_id={correlation_id} error=\"{str(e)}\"")
    
    async def _extract_version_from_content(self, content: str) -> Optional[str]:
        """Extract version information from content"""
        try:
            # Common version patterns
            version_patterns = [
                r'version\s*:?\s*([v]?\d+\.\d+\.\d+)',
                r'v(\d+\.\d+\.\d+)',
                r'@(\d+\.\d+\.\d+)',
                r'(\d+\.\d+\.\d+)',
            ]
            
            content_lower = content.lower()
            for pattern in version_patterns:
                match = re.search(pattern, content_lower)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract version from content: {e}")
            return None
    
    async def _classify_document_type(self, title: str, content: str) -> str:
        """Classify document type based on title and content"""
        try:
            title_lower = title.lower()
            content_lower = content.lower()
            
            # Classification patterns
            if any(term in title_lower for term in ["api", "reference"]):
                return "api"
            elif any(term in title_lower for term in ["guide", "tutorial"]):
                return "guide"
            elif any(term in title_lower for term in ["getting started", "quickstart"]):
                return "getting_started"
            elif any(term in title_lower for term in ["installation", "setup"]):
                return "installation"
            elif any(term in title_lower for term in ["configuration", "config"]):
                return "configuration"
            elif any(term in title_lower for term in ["troubleshooting", "debug"]):
                return "troubleshooting"
            elif any(term in title_lower for term in ["changelog", "changes"]):
                return "changelog"
            elif any(term in title_lower for term in ["migration", "upgrade"]):
                return "migration"
            elif any(term in title_lower for term in ["examples", "cookbook"]):
                return "examples"
            elif any(term in title_lower for term in ["faq", "questions"]):
                return "faq"
            elif any(term in title_lower for term in ["best practices", "patterns"]):
                return "best_practices"
            elif any(term in title_lower for term in ["blog", "post"]):
                return "blog"
            elif any(term in title_lower for term in ["news", "announcement"]):
                return "news"
            elif any(term in title_lower for term in ["release", "version"]):
                return "release_notes"
            else:
                return "documentation"
                
        except Exception as e:
            logger.error(f"Failed to classify document type: {e}")
            return "documentation"
    
    async def _extract_quality_indicators(self, result: SearchResult) -> Dict[str, Any]:
        """Extract quality indicators from search result"""
        try:
            indicators = {
                "has_code_examples": bool(re.search(r'```[\s\S]*?```', result.content)),
                "has_links": bool(re.search(r'\[.*?\]\(.*?\)', result.content)),
                "word_count": len(result.content.split()),
                "char_count": len(result.content),
                "header_count": len(re.findall(r'^#+\s', result.content, re.MULTILINE)),
                "relevance_score": result.relevance_score,
                "overall_score": 0.0  # Will be calculated later
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Failed to extract quality indicators: {e}")
            return {}
    
    async def _enhance_frontend_content(self, content: str, technology: str) -> str:
        """Enhance frontend framework content"""
        try:
            # Add technology-specific context
            enhancement = f"\n\n## {technology.title()} Context\n\n"
            enhancement += f"This documentation is specific to {technology}. "
            
            if technology == "react":
                enhancement += "React concepts like components, hooks, and state management apply here."
            elif technology == "vue":
                enhancement += "Vue concepts like components, directives, and reactivity apply here."
            elif technology == "angular":
                enhancement += "Angular concepts like components, services, and dependency injection apply here."
            
            return content + enhancement
            
        except Exception as e:
            logger.error(f"Failed to enhance frontend content: {e}")
            return content
    
    async def _enhance_backend_content(self, content: str, technology: str) -> str:
        """Enhance backend framework content"""
        try:
            # Add technology-specific context
            enhancement = f"\n\n## {technology.title()} Context\n\n"
            enhancement += f"This documentation is specific to {technology}. "
            
            if technology == "node.js":
                enhancement += "Node.js concepts like modules, event loop, and async/await apply here."
            elif technology == "express":
                enhancement += "Express concepts like middleware, routing, and request/response objects apply here."
            elif technology == "fastapi":
                enhancement += "FastAPI concepts like path operations, dependency injection, and async support apply here."
            
            return content + enhancement
            
        except Exception as e:
            logger.error(f"Failed to enhance backend content: {e}")
            return content
    
    async def _enhance_language_content(self, content: str, technology: str) -> str:
        """Enhance programming language content"""
        try:
            # Add language-specific context
            enhancement = f"\n\n## {technology.title()} Context\n\n"
            enhancement += f"This documentation is specific to {technology}. "
            
            if technology == "typescript":
                enhancement += "TypeScript concepts like types, interfaces, and generics apply here."
            elif technology == "javascript":
                enhancement += "JavaScript concepts like closures, prototypes, and async programming apply here."
            
            return content + enhancement
            
        except Exception as e:
            logger.error(f"Failed to enhance language content: {e}")
            return content
    
    async def cleanup_expired_documents(self, workspace_slug: str, correlation_id: str = None) -> Dict[str, Any]:
        """Clean up expired documents from Weaviate and database"""
        start_time = time.time()
        if correlation_id is None:
            correlation_id = f"ctx7_cleanup_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Starting cleanup of expired documents in workspace: {workspace_slug}")
            logger.info(f"PIPELINE_METRICS: step=context7_cleanup_start "
                       f"correlation_id={correlation_id} workspace_slug={workspace_slug}")
            
            # Use Weaviate client's cleanup method directly
            weaviate_start = time.time()
            weaviate_result = await self.weaviate.cleanup_expired_documents(workspace_slug)
            weaviate_time = int((time.time() - weaviate_start) * 1000)
            logger.info(f"PIPELINE_METRICS: step=context7_weaviate_cleanup duration_ms={weaviate_time} "
                       f"correlation_id={correlation_id} deleted_documents={weaviate_result.get('deleted_documents', 0)} "
                       f"deleted_chunks={weaviate_result.get('deleted_chunks', 0)}")
            
            # Also clean up from database
            query = """
            DELETE FROM content_metadata
            WHERE weaviate_workspace = :workspace_slug
            AND enrichment_metadata->'ttl_info'->>'expires_at' < :now
            """
            
            db_result = await self.db.execute(query, {
                "workspace_slug": workspace_slug,
                "now": datetime.utcnow().isoformat()
            })
            
            total_time = int((time.time() - start_time) * 1000)
            result = {
                "workspace": workspace_slug,
                "weaviate_cleanup": weaviate_result,
                "database_records_cleaned": db_result,
                "cleaned_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Cleanup completed for workspace {workspace_slug}")
            logger.info(f"PIPELINE_METRICS: step=context7_cleanup_complete duration_ms={total_time} "
                       f"correlation_id={correlation_id} workspace_slug={workspace_slug} "
                       f"total_deleted={weaviate_result.get('deleted_documents', 0)}")
            return result
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to cleanup expired documents: {e}")
            logger.info(f"PIPELINE_METRICS: step=context7_cleanup_error duration_ms={total_time} "
                       f"correlation_id={correlation_id} workspace_slug={workspace_slug} "
                       f"error=\"{str(e)}\"")
            return {
                "workspace": workspace_slug,
                "weaviate_cleanup": {"deleted_documents": 0, "deleted_chunks": 0},
                "database_records_cleaned": 0,
                "errors": [str(e)],
                "cleaned_at": datetime.utcnow().isoformat()
            }