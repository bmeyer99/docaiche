# Module Interface Specifications

## Overview
This document defines the interfaces for each major module in the DocAIche system. These interfaces establish contracts between services and modules, enabling loose coupling and future extensibility.

## Core Principles
1. **Protocol-Based**: Use Python Protocol classes for interface definitions
2. **Async-First**: All I/O operations must be async
3. **Type-Safe**: Full type annotations for all methods
4. **Error Handling**: Well-defined exceptions for each module
5. **Testable**: Interfaces should be easily mockable

## Content Processor Interface

### Interface Definition
```python
# src/modules/content_processor/interface.py
from typing import Protocol, Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path

class ContentProcessorInterface(Protocol):
    """Interface for document content processing operations"""
    
    async def process_document(
        self,
        file_path: Union[str, Path],
        options: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """
        Process a document and extract structured content.
        
        Args:
            file_path: Path to the document file
            options: Processing options (e.g., OCR settings, language)
            
        Returns:
            ProcessedDocument with extracted content and metadata
            
        Raises:
            DocumentProcessingError: If processing fails
            UnsupportedFormatError: If file format not supported
        """
        ...
    
    async def extract_text(
        self,
        file_path: Union[str, Path],
        preserve_formatting: bool = False
    ) -> str:
        """
        Extract plain text from a document.
        
        Args:
            file_path: Path to the document
            preserve_formatting: Whether to preserve layout
            
        Returns:
            Extracted text content
        """
        ...
    
    async def extract_metadata(
        self,
        file_path: Union[str, Path]
    ) -> DocumentMetadata:
        """
        Extract metadata from a document.
        
        Returns:
            Document metadata (author, creation date, etc.)
        """
        ...
    
    async def generate_embeddings(
        self,
        text: str,
        model: str = "default"
    ) -> List[float]:
        """
        Generate embeddings for text content.
        
        Args:
            text: Text to embed
            model: Embedding model to use
            
        Returns:
            Vector embeddings
        """
        ...
    
    async def chunk_document(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[TextChunk]:
        """
        Split document into chunks for processing.
        
        Returns:
            List of text chunks with positions
        """
        ...

# Data Models
from dataclasses import dataclass
from enum import Enum

class DocumentType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"

@dataclass
class ProcessedDocument:
    """Processed document with content and metadata"""
    id: str
    file_path: str
    content: str
    metadata: 'DocumentMetadata'
    chunks: List['TextChunk']
    embeddings: Optional[List[float]] = None
    processing_time: float = 0.0
    processed_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DocumentMetadata:
    """Document metadata"""
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    document_type: DocumentType = DocumentType.UNKNOWN
    language: str = "en"
    size_bytes: int = 0

@dataclass
class TextChunk:
    """Text chunk with position information"""
    text: str
    start_position: int
    end_position: int
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# Exceptions
class DocumentProcessingError(Exception):
    """Base exception for document processing errors"""
    pass

class UnsupportedFormatError(DocumentProcessingError):
    """Raised when document format is not supported"""
    pass
```

## Search Engine Interface

### Interface Definition
```python
# src/modules/search_engine/interface.py
from typing import Protocol, List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

class SearchEngineInterface(Protocol):
    """Interface for search operations"""
    
    async def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0
    ) -> SearchResult:
        """
        Execute a search query.
        
        Args:
            query: Search query string
            filters: Optional filters to apply
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            Search results with documents and metadata
        """
        ...
    
    async def vector_search(
        self,
        query_embedding: List[float],
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[VectorSearchMatch]:
        """
        Execute vector similarity search.
        
        Returns:
            Matches sorted by similarity score
        """
        ...
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        text_weight: float = 0.5,
        vector_weight: float = 0.5,
        filters: Optional[SearchFilters] = None,
        limit: int = 10
    ) -> SearchResult:
        """
        Execute hybrid text + vector search.
        """
        ...
    
    async def get_suggestions(
        self,
        query: str,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Get search query suggestions.
        """
        ...
    
    async def analyze_query(
        self,
        query: str
    ) -> QueryAnalysis:
        """
        Analyze search query for intent and entities.
        """
        ...

# Data Models
@dataclass
class SearchFilters:
    """Search filter criteria"""
    document_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    authors: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    workspace_id: Optional[str] = None
    metadata_filters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    """Search results container"""
    query: str
    total_results: int
    results: List['SearchMatch']
    facets: Dict[str, List['Facet']]
    search_time_ms: float
    suggestions: List[str] = field(default_factory=list)

@dataclass
class SearchMatch:
    """Individual search match"""
    document_id: str
    title: str
    content_preview: str
    score: float
    highlights: List['Highlight']
    metadata: Dict[str, Any]
    source_path: Optional[str] = None

@dataclass
class VectorSearchMatch:
    """Vector search match with similarity"""
    document_id: str
    chunk_id: str
    similarity_score: float
    content: str
    metadata: Dict[str, Any]

@dataclass
class Highlight:
    """Text highlight in search result"""
    field: str
    snippet: str
    start: int
    end: int

@dataclass
class Facet:
    """Search facet for filtering"""
    value: str
    count: int

@dataclass
class QueryAnalysis:
    """Analyzed query with intent and entities"""
    original_query: str
    normalized_query: str
    intent: str  # search, question, command
    entities: Dict[str, List[str]]
    suggested_filters: SearchFilters
```

## Ingestion Pipeline Interface

### Interface Definition
```python
# src/modules/ingestion_pipeline/interface.py
from typing import Protocol, List, Dict, Any, Optional, AsyncIterator
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class IngestionPipelineInterface(Protocol):
    """Interface for document ingestion operations"""
    
    async def ingest_file(
        self,
        file_path: Path,
        workspace_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        options: Optional[IngestionOptions] = None
    ) -> IngestionResult:
        """
        Ingest a single file into the system.
        """
        ...
    
    async def ingest_batch(
        self,
        file_paths: List[Path],
        workspace_id: str,
        options: Optional[IngestionOptions] = None
    ) -> BatchIngestionResult:
        """
        Ingest multiple files as a batch.
        """
        ...
    
    async def ingest_url(
        self,
        url: str,
        workspace_id: str,
        options: Optional[IngestionOptions] = None
    ) -> IngestionResult:
        """
        Ingest content from a URL.
        """
        ...
    
    async def monitor_ingestion(
        self,
        job_id: str
    ) -> AsyncIterator[IngestionProgress]:
        """
        Monitor ongoing ingestion progress.
        """
        ...
    
    async def cancel_ingestion(
        self,
        job_id: str
    ) -> bool:
        """
        Cancel an ongoing ingestion job.
        """
        ...

# Data Models
class IngestionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class IngestionOptions:
    """Options for document ingestion"""
    process_async: bool = True
    extract_images: bool = False
    extract_tables: bool = True
    generate_summary: bool = True
    ocr_enabled: bool = True
    language: str = "auto"
    chunk_size: int = 1000
    chunk_overlap: int = 100

@dataclass
class IngestionResult:
    """Result of document ingestion"""
    job_id: str
    document_id: str
    status: IngestionStatus
    file_path: str
    workspace_id: str
    processing_time_ms: float
    metadata: Dict[str, Any]
    error: Optional[str] = None

@dataclass
class BatchIngestionResult:
    """Result of batch ingestion"""
    job_id: str
    total_files: int
    successful: int
    failed: int
    results: List[IngestionResult]
    total_time_ms: float

@dataclass
class IngestionProgress:
    """Progress update for ingestion job"""
    job_id: str
    current_file: str
    files_completed: int
    total_files: int
    percent_complete: float
    estimated_time_remaining_s: Optional[float]
    current_stage: str  # "downloading", "extracting", "processing", etc.
```

## Enrichment Service Interface

### Interface Definition
```python
# src/modules/enrichment_service/interface.py
from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass

class EnrichmentServiceInterface(Protocol):
    """Interface for content enrichment operations"""
    
    async def enrich_document(
        self,
        document_id: str,
        enrichment_types: List[str]
    ) -> EnrichmentResult:
        """
        Enrich a document with additional metadata.
        
        Args:
            document_id: Document to enrich
            enrichment_types: Types of enrichment to apply
            
        Returns:
            Enrichment results
        """
        ...
    
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Entity]:
        """
        Extract named entities from text.
        """
        ...
    
    async def classify_content(
        self,
        text: str,
        classification_scheme: str = "default"
    ) -> Classification:
        """
        Classify content into categories.
        """
        ...
    
    async def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        style: str = "abstractive"
    ) -> str:
        """
        Generate text summary.
        """
        ...
    
    async def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10,
        algorithm: str = "tfidf"
    ) -> List[Keyword]:
        """
        Extract keywords from text.
        """
        ...
    
    async def analyze_sentiment(
        self,
        text: str
    ) -> SentimentAnalysis:
        """
        Analyze text sentiment.
        """
        ...

# Data Models
@dataclass
class EnrichmentResult:
    """Container for all enrichment results"""
    document_id: str
    entities: List['Entity']
    classification: 'Classification'
    keywords: List['Keyword']
    summary: Optional[str]
    sentiment: Optional['SentimentAnalysis']
    processing_time_ms: float
    enrichment_types: List[str]

@dataclass
class Entity:
    """Named entity"""
    text: str
    type: str  # PERSON, ORG, LOCATION, etc.
    start_position: int
    end_position: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Classification:
    """Document classification result"""
    primary_category: str
    confidence: float
    all_categories: List[Tuple[str, float]]  # (category, confidence)
    classification_scheme: str

@dataclass
class Keyword:
    """Extracted keyword with relevance"""
    keyword: str
    score: float
    frequency: int

@dataclass
class SentimentAnalysis:
    """Sentiment analysis result"""
    sentiment: str  # positive, negative, neutral
    confidence: float
    scores: Dict[str, float]  # sentiment -> score mapping
```

## Common Types and Utilities

### Shared Types
```python
# src/modules/common/types.py
from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    """Generic result wrapper with error handling"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

@dataclass
class PagedResult(Generic[T]):
    """Paged result container"""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
```

### Module Exceptions
```python
# src/modules/common/exceptions.py
class ModuleError(Exception):
    """Base exception for all module errors"""
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code

class ValidationError(ModuleError):
    """Input validation error"""
    pass

class ResourceNotFoundError(ModuleError):
    """Requested resource not found"""
    pass

class ExternalServiceError(ModuleError):
    """External service call failed"""
    pass

class QuotaExceededError(ModuleError):
    """Service quota exceeded"""
    pass
```

## Interface Implementation Guidelines

### 1. Implementation Pattern
```python
# src/modules/content_processor/implementation.py
from .interface import ContentProcessorInterface

class ContentProcessor:
    """Concrete implementation of ContentProcessorInterface"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Initialize resources
    
    async def process_document(self, file_path: Path, options: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        # Implementation
        pass
```

### 2. Testing Pattern
```python
# tests/modules/test_content_processor.py
from unittest.mock import AsyncMock
from src.modules.content_processor.interface import ContentProcessorInterface

def create_mock_processor() -> ContentProcessorInterface:
    """Create mock content processor for testing"""
    mock = AsyncMock(spec=ContentProcessorInterface)
    mock.process_document.return_value = ProcessedDocument(...)
    return mock
```

### 3. Service Integration Pattern
```python
# src/services/content_service.py
from src.modules.content_processor.interface import ContentProcessorInterface

class ContentService(BaseService):
    def __init__(self, processor: ContentProcessorInterface):
        super().__init__("content_service")
        self.processor = processor
    
    async def process(self, file_path: str) -> Dict[str, Any]:
        with self.tracer.start_as_current_span("process_document"):
            result = await self.processor.process_document(file_path)
            return result.dict()
```

## Versioning Strategy

Interfaces should be versioned to allow for backward compatibility:

```python
# src/modules/content_processor/v1/interface.py  # Original
# src/modules/content_processor/v2/interface.py  # New version
```

Services can support multiple interface versions during migration periods.