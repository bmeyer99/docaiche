# Immediate Implementation Plan - Quick Start

## Goal
Implement a working proof-of-concept of the intelligent documentation pipeline within the next few hours.

## Phase 1: LLM Query Analyzer (30 minutes)

### Create Query Analyzer
```python
# src/search/llm_query_analyzer.py
from typing import Dict, Any
from src.llm.client import LLMProviderClient
from pydantic import BaseModel

class QueryIntent(BaseModel):
    technology: str
    version: Optional[str] = None
    doc_type: str  # tutorial, reference, guide
    topics: List[str]
    user_level: str  # beginner, intermediate, advanced

class LLMQueryAnalyzer:
    def __init__(self, llm_client: LLMProviderClient):
        self.llm = llm_client
    
    async def analyze_query(self, query: str) -> QueryIntent:
        prompt = f"""
        Analyze this documentation search query: "{query}"
        
        Extract and return as JSON:
        - technology: main technology/framework
        - version: version if specified (null if not)
        - doc_type: "tutorial", "reference", or "guide"
        - topics: list of specific topics mentioned
        - user_level: "beginner", "intermediate", or "advanced"
        
        Example: "fastapi async tutorial for beginners"
        {{
            "technology": "fastapi",
            "version": null,
            "doc_type": "tutorial",
            "topics": ["async", "asynchronous programming"],
            "user_level": "beginner"
        }}
        """
        
        response = await self.llm.generate(prompt)
        return QueryIntent.parse_raw(response)
```

## Phase 2: Dynamic Source Discovery (30 minutes)

### Create Source Finder
```python
# src/enrichment/llm_source_finder.py
class DocumentationSource(BaseModel):
    name: str
    url: str
    source_type: str  # github, official, community
    format: str  # markdown, html, pdf
    quality_score: float

class LLMSourceFinder:
    async def find_sources(self, intent: QueryIntent) -> List[DocumentationSource]:
        prompt = f"""
        Find documentation sources for {intent.technology} {intent.version or 'latest'}
        focusing on {intent.doc_type} about {', '.join(intent.topics)}.
        
        Return as JSON array with:
        - name: source name
        - url: direct URL to documentation
        - source_type: "github", "official", or "community"  
        - format: "markdown", "html", or "pdf"
        - quality_score: 0.0 to 1.0
        
        Find at least 3 sources, prioritizing official docs and GitHub.
        """
        
        response = await self.llm.generate(prompt)
        sources = json.loads(response)
        return [DocumentationSource(**s) for s in sources]
```

## Phase 3: Smart Fetching (45 minutes)

### Enhance GitHub Client
```python
# Update src/clients/github.py
class SmartGitHubClient(GitHubClient):
    async def fetch_docs_intelligently(
        self, 
        repo_url: str, 
        intent: QueryIntent
    ) -> List[DocumentContent]:
        # Extract owner/repo from URL
        owner, repo = self._parse_github_url(repo_url)
        
        # Use LLM to find relevant files
        prompt = f"""
        In the GitHub repo {owner}/{repo}, find documentation files for:
        - Technology: {intent.technology}
        - Topics: {', '.join(intent.topics)}
        - Type: {intent.doc_type}
        
        Common locations:
        - /docs, /documentation
        - README.md
        - /examples
        - /tutorials, /guides
        
        Return file paths as JSON array.
        """
        
        file_paths = await self.llm.generate(prompt)
        
        # Fetch identified files
        contents = []
        for path in json.loads(file_paths):
            content = await self.fetch_file(owner, repo, path)
            if content:
                contents.append(content)
        
        return contents
```

## Phase 4: Process and Store (45 minutes)

### Create Processing Pipeline
```python
# src/ingestion/smart_pipeline.py
class SmartIngestionPipeline:
    def __init__(
        self,
        llm_client: LLMProviderClient,
        anythingllm_client: AnythingLLMClient,
        db_manager: DatabaseManager
    ):
        self.llm = llm_client
        self.anythingllm = anythingllm_client
        self.db = db_manager
    
    async def process_documentation(
        self,
        content: DocumentContent,
        intent: QueryIntent
    ) -> ProcessingResult:
        # 1. Smart chunking
        chunks = await self._smart_chunk(content.text, intent)
        
        # 2. Create/get workspace
        workspace_name = f"{intent.technology}-docs"
        workspace = await self.anythingllm.create_workspace(workspace_name)
        
        # 3. Upload to AnythingLLM
        for chunk in chunks:
            await self.anythingllm.upload_document(
                workspace_slug=workspace.slug,
                content=chunk.text,
                metadata={
                    "source": content.source_url,
                    "topics": intent.topics,
                    "chunk_index": chunk.index
                }
            )
        
        # 4. Store in database
        await self._store_content_metadata(content, chunks, workspace)
        
        return ProcessingResult(success=True, chunks_processed=len(chunks))
    
    async def _smart_chunk(self, text: str, intent: QueryIntent) -> List[Chunk]:
        prompt = f"""
        Split this documentation into semantic chunks for {intent.technology}.
        Each chunk should:
        - Be 500-1000 tokens
        - Keep code blocks intact
        - Maintain context
        - End at natural boundaries
        
        Mark chunk boundaries with "---CHUNK---"
        """
        
        response = await self.llm.generate(prompt + "\n\n" + text)
        chunks = response.split("---CHUNK---")
        
        return [
            Chunk(text=chunk.strip(), index=i) 
            for i, chunk in enumerate(chunks) 
            if chunk.strip()
        ]
```

## Phase 5: Wire Everything Together (30 minutes)

### Update Search Orchestrator
```python
# src/search/orchestrator_enhanced.py
class EnhancedSearchOrchestrator(SearchOrchestrator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_analyzer = LLMQueryAnalyzer(self.llm_client)
        self.source_finder = LLMSourceFinder(self.llm_client)
        self.github_client = SmartGitHubClient(...)
        self.pipeline = SmartIngestionPipeline(...)
    
    async def search(self, query: str) -> SearchResponse:
        # 1. Check cache first
        cached = await self._check_cache(query)
        if cached:
            return cached
        
        # 2. Analyze query intent
        intent = await self.query_analyzer.analyze_query(query)
        
        # 3. Find documentation sources
        sources = await self.source_finder.find_sources(intent)
        
        # 4. Fetch documentation
        all_content = []
        for source in sources[:3]:  # Limit to top 3
            if source.source_type == "github":
                content = await self.github_client.fetch_docs_intelligently(
                    source.url, intent
                )
                all_content.extend(content)
        
        # 5. Process and store
        for content in all_content:
            await self.pipeline.process_documentation(content, intent)
        
        # 6. Search in AnythingLLM
        results = await self.anythingllm.search(
            workspace_slug=f"{intent.technology}-docs",
            query=query
        )
        
        # 7. Cache and return
        await self._cache_results(query, results)
        return self._format_response(results)
```

## Testing Script

```python
# test_pipeline.py
async def test_full_pipeline():
    # Initialize components
    config = get_system_configuration()
    llm_client = LLMProviderClient(config.ai)
    
    orchestrator = EnhancedSearchOrchestrator(
        db_manager=await get_database_manager(),
        cache_manager=await get_cache_manager(),
        anythingllm_client=await get_anythingllm_client(),
        llm_client=llm_client
    )
    
    # Test queries
    test_queries = [
        "FastAPI async tutorial for beginners",
        "React hooks comprehensive guide",
        "Django REST framework authentication",
        "Python asyncio advanced examples"
    ]
    
    for query in test_queries:
        print(f"\n=== Testing: {query} ===")
        
        # First search (should fetch and cache)
        start = time.time()
        results1 = await orchestrator.search(query)
        fetch_time = time.time() - start
        print(f"Initial fetch: {fetch_time:.2f}s, results: {len(results1.results)}")
        
        # Second search (should hit cache)
        start = time.time()
        results2 = await orchestrator.search(query)
        cache_time = time.time() - start
        print(f"Cache hit: {cache_time:.2f}s, results: {len(results2.results)}")
```

## Immediate Next Steps (Do Now!)

### 1. Create LLM Query Analyzer (15 min)
```bash
# Create the file
cat > src/search/llm_query_analyzer.py << 'EOF'
# Paste the query analyzer code
EOF
```

### 2. Test with Ollama (5 min)
```python
# Quick test script
import asyncio
from src.llm.client import LLMProviderClient

async def test_llm():
    client = LLMProviderClient({"primary_provider": "ollama"})
    response = await client.generate("What is FastAPI?")
    print(response)

asyncio.run(test_llm())
```

### 3. Create Source Finder (15 min)
```bash
cat > src/enrichment/llm_source_finder.py << 'EOF'
# Paste the source finder code
EOF
```

### 4. Integration Test (20 min)
- Wire up the components
- Test with a real query
- Verify AnythingLLM storage
- Check cache behavior

## Configuration Needed

```yaml
# config.yaml
ai:
  primary_provider: ollama
  ollama:
    model: llama3.3:latest
    endpoint: http://192.168.4.204:11434
    temperature: 0.3  # Lower for more consistent parsing

processing:
  chunk_size: 1000
  overlap: 100
  
search:
  cache_ttl: 3600  # 1 hour
  max_sources: 3
```

## Expected Results

After implementation, a search for "FastAPI async tutorial" should:

1. **Query Analysis** (2s)
   - Detect: technology=fastapi, doc_type=tutorial, topics=[async]

2. **Source Discovery** (3s)
   - Find: FastAPI official docs, FastAPI GitHub, Real Python tutorial

3. **Intelligent Fetching** (10s)
   - Fetch: README.md, docs/tutorial/async.md, examples/async/

4. **Processing** (5s)
   - Create 10-15 semantic chunks
   - Upload to AnythingLLM workspace

5. **Search Results** (1s)
   - Return relevant chunks
   - Cache for future queries

**Total first search: ~21 seconds**
**Cached search: <1 second**

This implementation can be completed in 2-3 hours and will demonstrate the full intelligent pipeline!