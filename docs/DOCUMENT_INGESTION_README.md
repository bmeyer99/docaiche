# Document Ingestion Pipeline

Comprehensive document ingestion system for the AI Documentation Cache System supporting multiple file formats with secure processing and integration with the existing Content Processing Pipeline (PRD-008).

## Features

### Supported Document Formats
- **PDF**: Portable Document Format files
- **DOC/DOCX**: Microsoft Word documents (DOCX only for security)
- **TXT**: Plain text files
- **MD**: Markdown files
- **HTML**: Web pages and HTML documents

### Security Features
- File size limits (50MB maximum)
- Content type validation
- Filename sanitization (prevents path traversal)
- Input validation and sanitization
- Secure content extraction
- Error handling without information leakage

### Processing Capabilities
- Single document upload
- Batch document processing (up to 100 files)
- Parallel processing with controlled concurrency
- Content extraction and normalization
- Integration with PRD-008 Content Processing Pipeline
- Quality scoring and validation
- Comprehensive metadata extraction

## API Endpoints

### Health Check
```http
GET /api/v1/ingestion/health
```

Returns service health status and capabilities:
```json
{
  "status": "healthy",
  "supported_formats": ["pdf", "docx", "txt", "md", "html"],
  "max_file_size_mb": 50,
  "max_batch_size": 100,
  "content_processor_status": "healthy",
  "database_status": "healthy",
  "timestamp": "2023-01-01T00:00:00Z"
}
```

### Single Document Upload
```http
POST /api/v1/ingestion/upload
Content-Type: multipart/form-data

file: [document file]
technology: string (required)
title: string (optional)
source_url: string (optional)
```

Response:
```json
{
  "document_id": "doc_123456789abc",
  "filename": "example.pdf",
  "status": "completed",
  "content_hash": "sha256hash",
  "word_count": 1250,
  "chunk_count": 3,
  "quality_score": 0.85,
  "processing_time_ms": 1500,
  "created_at": "2023-01-01T00:00:00Z"
}
```

### Batch Document Upload
```http
POST /api/v1/ingestion/upload/batch
Content-Type: multipart/form-data

files: [multiple document files]
technology: string (required)
batch_name: string (optional)
```

Response:
```json
{
  "batch_id": "batch_123456789abc",
  "batch_name": "documentation-update",
  "total_documents": 5,
  "successful_count": 4,
  "failed_count": 1,
  "results": [
    {
      "document_id": "doc_1",
      "filename": "guide.md",
      "status": "completed",
      "word_count": 800,
      "quality_score": 0.9
    }
  ],
  "total_processing_time_ms": 3500,
  "created_at": "2023-01-01T00:00:00Z"
}
```

### Document Status
```http
GET /api/v1/ingestion/status/{document_id}
```

Response:
```json
{
  "document_id": "doc_123456789abc",
  "title": "API Documentation",
  "processing_status": "completed",
  "quality_score": 0.85,
  "word_count": 1250,
  "chunk_count": 3,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:01:30Z"
}
```

### Processing Metrics
```http
GET /api/v1/ingestion/metrics
```

Response:
```json
{
  "total_documents_processed": 1500,
  "documents_by_format": {
    "pdf": 600,
    "md": 450,
    "txt": 300,
    "html": 150
  },
  "documents_by_technology": {
    "python": 500,
    "javascript": 400,
    "java": 300,
    "go": 200,
    "rust": 100
  },
  "average_processing_time_ms": 1200.5,
  "success_rate": 94.5,
  "quality_score_distribution": {
    "high": 800,
    "medium": 500,
    "low": 200
  },
  "last_updated": "2023-01-01T00:00:00Z"
}
```

### Document Deletion
```http
DELETE /api/v1/ingestion/documents/{document_id}
```

Response:
```json
{
  "message": "Document deleted successfully",
  "document_id": "doc_123456789abc"
}
```

## Architecture Integration

### Content Processing Pipeline Integration
The ingestion system integrates seamlessly with PRD-008 Content Processing Pipeline:

1. **File Upload** → Security validation and content extraction
2. **Content Extraction** → Format-specific text extraction
3. **Content Processing** → Integration with existing ContentProcessor
4. **Database Storage** → Metadata persistence via established patterns
5. **Quality Assessment** → Content quality scoring and validation

### Data Flow
```
Upload Request → Security Validation → Content Extraction → 
Content Processing (PRD-008) → Database Storage → Response
```

### Error Handling
- **422 Unprocessable Entity**: Validation errors, unsupported formats
- **400 Bad Request**: Invalid requests, missing parameters
- **413 Payload Too Large**: File size exceeds limits
- **500 Internal Server Error**: Processing failures
- **404 Not Found**: Document not found

## Configuration

### Environment Variables
```bash
# File processing limits
MAX_FILE_SIZE_MB=50
MAX_BATCH_SIZE=100

# Processing configuration
CHUNK_SIZE_DEFAULT=1000
CHUNK_SIZE_MAX=4000
CHUNK_OVERLAP=100
QUALITY_THRESHOLD=0.3

# Database configuration
DATABASE_URL=sqlite:///app/data/docs.db
REDIS_URL=redis://localhost:6379/0
```

### Dependencies
Required Python packages for document processing:
```
PyPDF2>=3.0.0          # PDF processing
python-docx>=0.8.11    # Word document processing  
beautifulsoup4>=4.12.0 # HTML processing
lxml>=4.9.0            # XML/HTML parsing
```

## Security Considerations

### File Upload Security
- Maximum file size enforcement (50MB)
- File type validation based on extension and content
- Filename sanitization to prevent path traversal
- Content scanning for malicious patterns

### Content Processing Security
- Secure parsing libraries only
- No execution of embedded scripts or macros
- Input sanitization at all processing stages
- Error message sanitization

### Data Protection
- No temporary file storage on disk
- Memory-based processing only
- Secure cleanup of processing artifacts
- Database parameterized queries

## Performance Characteristics

### Single Document Processing
- **Average processing time**: 500-2000ms depending on size
- **Memory usage**: ~2x document size during processing
- **Supported concurrent uploads**: 10 simultaneous

### Batch Processing
- **Parallel processing**: Up to 5 documents simultaneously
- **Memory optimization**: Streaming processing for large batches
- **Progress tracking**: Individual document status within batch

### Resource Limits
- **Maximum file size**: 50MB per document
- **Maximum batch size**: 100 documents
- **Processing timeout**: 5 minutes per document
- **Memory limit**: 512MB per processing instance

## Testing

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run ingestion tests
pytest tests/test_ingestion_pipeline.py -v
pytest tests/test_ingestion_api.py -v

# Run with coverage
pytest tests/test_ingestion_*.py --cov=src/ingestion --cov-report=html
```

### Test Coverage
- Unit tests for content extraction
- Integration tests for API endpoints
- Security validation tests
- Error handling tests
- Performance benchmark tests

## Deployment

### Docker Integration
The ingestion system is integrated with the main application Docker container:

```dockerfile
# Document processing dependencies added to main Dockerfile
RUN pip install PyPDF2 python-docx beautifulsoup4 lxml
```

### Health Monitoring
Monitor the `/api/v1/ingestion/health` endpoint for:
- Service availability
- Database connectivity
- Content processor status
- Processing capacity

### Logging
Structured JSON logging for:
- Document processing events
- Security validation results
- Performance metrics
- Error conditions

## Example Usage

### Python Client Example
```python
import aiohttp
import aiofiles

async def upload_document(file_path: str, technology: str):
    async with aiohttp.ClientSession() as session:
        async with aiofiles.open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_path)
            data.add_field('technology', technology)
            
            async with session.post(
                'http://localhost:8080/api/v1/ingestion/upload',
                data=data
            ) as response:
                result = await response.json()
                return result

# Usage
result = await upload_document('docs/api-guide.md', 'python')
print(f"Document ID: {result['document_id']}")
```

### cURL Example
```bash
# Single document upload
curl -X POST "http://localhost:8080/api/v1/ingestion/upload" \
  -F "file=@example.pdf" \
  -F "technology=python" \
  -F "title=API Documentation"

# Check processing status
curl "http://localhost:8080/api/v1/ingestion/status/doc_123456789abc"

# Get processing metrics
curl "http://localhost:8080/api/v1/ingestion/metrics"
```

## Troubleshooting

### Common Issues

**File Upload Fails**
- Check file size (max 50MB)
- Verify supported format (PDF, DOCX, TXT, MD, HTML)
- Ensure filename doesn't contain path separators

**Processing Timeout**
- Large files may require more processing time
- Check system memory availability
- Consider splitting large documents

**Quality Score Too Low**
- Ensure document has sufficient text content (>50 characters)
- Check for proper document structure
- Verify content isn't corrupted

**Batch Processing Failures**
- Verify batch size doesn't exceed 100 documents
- Check individual file requirements
- Monitor system resources during batch processing

### Debug Mode
Enable debug logging for detailed processing information:
```bash
export LOG_LEVEL=DEBUG
```

This provides detailed logs for:
- Content extraction steps
- Processing pipeline stages
- Database operations
- Performance metrics