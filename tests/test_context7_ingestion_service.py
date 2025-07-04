"""
Unit tests for Context7IngestionService
======================================

Comprehensive tests for the Context7-specific ingestion service with TTL support,
metadata enrichment, quality assessment, batch processing, and logging verification.

Test Coverage:
- TTL calculation algorithms and edge cases
- Configuration loading and validation
- Context7 document processing and metadata extraction
- Weaviate TTL operations and cleanup
- PIPELINE_METRICS logging verification
- Background job scheduling and execution
- Error handling and fallback mechanisms
- Performance and batch processing operations
"""

import pytest
import asyncio
import logging
import json
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
import time

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.ingestion.smart_pipeline import ProcessingResult
from src.search.llm_query_analyzer import QueryIntent
from src.mcp.providers.models import SearchResult, SearchResultType
from src.document_processing.models import DocumentContent


class TestContext7IngestionService:
    """Test suite for Context7IngestionService"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        mock = AsyncMock()
        mock.generate.return_value = "mocked response"
        return mock
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Mock Weaviate client"""
        mock = AsyncMock()
        mock.upload_document.return_value = Mock(successful_uploads=5)
        mock.cleanup_expired_documents.return_value = {
            "deleted_documents": 2,
            "deleted_chunks": 10
        }
        return mock
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        mock = AsyncMock()
        mock.execute.return_value = None
        mock.fetch_all.return_value = []
        return mock
    
    @pytest.fixture
    def ttl_config(self):
        """Test TTL configuration"""
        return TTLConfig(
            default_days=30,
            min_days=1,
            max_days=90,
            technology_multipliers={
                "react": 1.5,
                "typescript": 2.0,
                "vue": 1.5
            },
            doc_type_multipliers={
                "api": 2.0,
                "guide": 1.5,
                "tutorial": 1.2
            }
        )
    
    @pytest.fixture
    def service(self, mock_llm_client, mock_weaviate_client, mock_db_manager, ttl_config):
        """Context7IngestionService instance"""
        return Context7IngestionService(
            llm_client=mock_llm_client,
            weaviate_client=mock_weaviate_client,
            db_manager=mock_db_manager,
            ttl_config=ttl_config
        )
    
    @pytest.fixture
    def sample_search_result(self):
        """Sample search result from Context7"""
        return SearchResult(
            title="React Hooks Documentation",
            url="https://context7.com/facebook/react/llms.txt",
            snippet="Learn about React Hooks and state management",
            content="""# React Hooks

React Hooks allow you to use state and other React features without writing a class.

## useState Hook

```jsx
import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>You clicked {count} times</p>
      <button onClick={() => setCount(count + 1)}>
        Click me
      </button>
    </div>
  );
}
```

## useEffect Hook

The Effect Hook lets you perform side effects in function components.

```jsx
import React, { useState, useEffect } from 'react';

function Example() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    document.title = `You clicked ${count} times`;
  });
  
  return (
    <div>
      <p>You clicked {count} times</p>
      <button onClick={() => setCount(count + 1)}>
        Click me
      </button>
    </div>
  );
}
```

This is a comprehensive guide to React Hooks with examples and best practices.
""",
            content_type=SearchResultType.DOCUMENTATION,
            source_domain="context7.com",
            relevance_score=0.95,
            provider_rank=1,
            metadata={
                "owner": "facebook",
                "technology": "react",
                "section": 1,
                "total_sections": 1,
                "source": "context7",
                "type": SearchResultType.DOCUMENTATION
            }
        )
    
    @pytest.fixture
    def sample_query_intent(self):
        """Sample query intent"""
        return QueryIntent(
            intent="documentation",
            technology="react",
            topics=["hooks", "state management"],
            doc_type="guide",
            user_level="intermediate",
            specific_question="How to use React hooks",
            context_needed=True,
            priority="high"
        )

    @pytest.fixture
    def sample_context7_document(self):
        """Sample Context7 document"""
        return Context7Document(
            content="""# React Hooks Guide

React Hooks are a new addition in React 16.8. They let you use state and other React features without writing a class.

## What are Hooks?

Hooks are functions that let you "hook into" React state and lifecycle features from function components.

## Rules of Hooks

1. Only call Hooks at the top level
2. Only call Hooks from React functions

## Built-in Hooks

### useState
```jsx
const [state, setState] = useState(initialState);
```

### useEffect
```jsx
useEffect(() => {
  // Side effect code
}, [dependencies]);
```

This guide covers the essential concepts and best practices for using React Hooks effectively.
""",
            title="React Hooks Guide",
            source_url="https://context7.com/facebook/react/llms.txt",
            technology="react",
            owner="facebook",
            version="18.2.0",
            doc_type="guide",
            language="en",
            quality_indicators={
                "has_code_examples": True,
                "has_links": False,
                "word_count": 150,
                "char_count": 800,
                "header_count": 5,
                "relevance_score": 0.95,
                "overall_score": 0.85
            },
            metadata={
                "source": "context7",
                "official": True
            }
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, service, ttl_config):
        """Test service initialization"""
        assert service.ttl_config == ttl_config
        assert service.ttl_config.default_days == 30
        assert service.ttl_config.technology_multipliers["react"] == 1.5

    @pytest.mark.asyncio
    async def test_convert_search_result_to_document(self, service, sample_search_result, sample_query_intent):
        """Test converting search result to Context7 document"""
        with patch.object(service, '_extract_version_from_content', return_value="18.2.0"), \
             patch.object(service, '_classify_document_type', return_value="guide"), \
             patch.object(service, '_extract_quality_indicators', return_value={"overall_score": 0.85}):
            
            document = await service._convert_search_result_to_document(
                sample_search_result, sample_query_intent
            )
            
            assert document is not None
            assert document.title == "React Hooks Documentation"
            assert document.technology == "react"
            assert document.owner == "facebook"
            assert document.version == "18.2.0"
            assert document.doc_type == "guide"

    @pytest.mark.asyncio
    async def test_calculate_intelligent_ttl_react_guide(self, service, sample_context7_document, sample_query_intent):
        """Test TTL calculation for React guide"""
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.2), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.1):
            
            ttl = await service._calculate_intelligent_ttl(sample_context7_document, sample_query_intent)
            
            # Base (30) * tech_multiplier (1.5) * doc_type_multiplier (1.5) * content (1.2) * version (1.1) * quality (1.2) ≈ 89.64
            assert 60 <= ttl <= 90  # Should be capped at max_days

    @pytest.mark.asyncio
    async def test_calculate_intelligent_ttl_typescript_api(self, service, sample_query_intent):
        """Test TTL calculation for TypeScript API documentation"""
        # Create a TypeScript API document
        ts_doc = Context7Document(
            content="TypeScript API reference with comprehensive type definitions",
            title="TypeScript API Reference",
            source_url="https://context7.com/microsoft/typescript/llms.txt",
            technology="typescript",
            owner="microsoft",
            doc_type="api",
            quality_indicators={"overall_score": 0.95}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.5), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.3):
            
            ttl = await service._calculate_intelligent_ttl(ts_doc, sample_query_intent)
            
            # Base (30) * tech_multiplier (2.0) * doc_type_multiplier (2.0) * content (1.5) * version (1.3) * quality (1.2) ≈ 468
            assert ttl == 90  # Should be capped at max_days

    @pytest.mark.asyncio
    async def test_calculate_intelligent_ttl_minimum_bound(self, service, sample_query_intent):
        """Test TTL calculation minimum bound"""
        # Create a low-quality, deprecated document
        deprecated_doc = Context7Document(
            content="This feature is deprecated and will be removed soon",
            title="Deprecated Feature",
            source_url="https://context7.com/deprecated/feature/llms.txt",
            technology="unknown",
            owner="unknown",
            doc_type="changelog",
            quality_indicators={"overall_score": 0.3}  # Low quality
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=0.5), \
             patch.object(service, '_analyze_version_for_ttl', return_value=0.6):
            
            ttl = await service._calculate_intelligent_ttl(deprecated_doc, sample_query_intent)
            
            assert ttl >= 1  # Should not go below min_days

    @pytest.mark.asyncio
    async def test_assess_document_quality_high_quality(self, service, sample_context7_document):
        """Test quality assessment for high-quality document"""
        quality = await service._assess_document_quality(sample_context7_document)
        
        # Should score well due to code examples, headers, and good structure
        assert 0.7 <= quality <= 1.0

    @pytest.mark.asyncio
    async def test_assess_document_quality_low_quality(self, service):
        """Test quality assessment for low-quality document"""
        low_quality_doc = Context7Document(
            content="Short content without examples or structure.",
            title="Basic Info",
            source_url="https://example.com/basic",
            technology="unknown",
            owner="unknown",
            doc_type="blog"
        )
        
        quality = await service._assess_document_quality(low_quality_doc)
        
        # Should score low due to lack of content, examples, and structure
        assert 0.0 <= quality <= 0.3

    @pytest.mark.asyncio
    async def test_analyze_content_for_ttl_stable_content(self, service):
        """Test content analysis for stable content"""
        stable_doc = Context7Document(
            content="This is a stable, production-ready API that is recommended for all users. "
                   "It provides comprehensive functionality and is thoroughly tested.",
            title="Stable API",
            source_url="https://example.com/stable",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(stable_doc)
        
        # Should get bonus for stability indicators
        assert multiplier > 1.0

    @pytest.mark.asyncio
    async def test_analyze_content_for_ttl_deprecated_content(self, service):
        """Test content analysis for deprecated content"""
        deprecated_doc = Context7Document(
            content="This feature is deprecated and will be removed in the next major version. "
                   "Please use the new API instead.",
            title="Deprecated Feature",
            source_url="https://example.com/deprecated",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(deprecated_doc)
        
        # Should get penalty for deprecation
        assert multiplier < 1.0

    @pytest.mark.asyncio
    async def test_analyze_version_for_ttl_latest_version(self, service):
        """Test version analysis for latest version"""
        latest_doc = Context7Document(
            content="Documentation content",
            title="Latest Version",
            source_url="https://example.com/latest",
            technology="react",
            owner="facebook",
            version="latest"
        )
        
        multiplier = await service._analyze_version_for_ttl(latest_doc)
        
        # Should get bonus for latest version
        assert multiplier > 1.0

    @pytest.mark.asyncio
    async def test_analyze_version_for_ttl_beta_version(self, service):
        """Test version analysis for beta version"""
        beta_doc = Context7Document(
            content="Documentation content",
            title="Beta Version",
            source_url="https://example.com/beta",
            technology="react",
            owner="facebook",
            version="v2.0.0-beta.1"
        )
        
        multiplier = await service._analyze_version_for_ttl(beta_doc)
        
        # Should get penalty for beta version
        assert multiplier < 1.0

    @pytest.mark.asyncio
    async def test_extract_version_from_content(self, service):
        """Test version extraction from content"""
        content_with_version = """
        This documentation covers React version 18.2.0.
        Install with: npm install react@18.2.0
        """
        
        version = await service._extract_version_from_content(content_with_version)
        
        assert version == "18.2.0"

    @pytest.mark.asyncio
    async def test_extract_version_from_content_no_version(self, service):
        """Test version extraction when no version is present"""
        content_without_version = "This is documentation without version information."
        
        version = await service._extract_version_from_content(content_without_version)
        
        assert version is None

    @pytest.mark.asyncio
    async def test_classify_document_type_api(self, service):
        """Test document type classification for API docs"""
        title = "React API Reference"
        content = "Complete API reference for React components and hooks"
        
        doc_type = await service._classify_document_type(title, content)
        
        assert doc_type == "api"

    @pytest.mark.asyncio
    async def test_classify_document_type_tutorial(self, service):
        """Test document type classification for tutorial"""
        title = "Getting Started Tutorial"
        content = "This tutorial will guide you through the basics"
        
        doc_type = await service._classify_document_type(title, content)
        
        assert doc_type == "getting_started"

    @pytest.mark.asyncio
    async def test_enhance_frontend_content_react(self, service):
        """Test content enhancement for React"""
        original_content = "This is about React components."
        
        enhanced = await service._enhance_frontend_content(original_content, "react")
        
        assert "React Context" in enhanced
        assert "components, hooks, and state management" in enhanced
        assert original_content in enhanced

    @pytest.mark.asyncio
    async def test_enhance_backend_content_nodejs(self, service):
        """Test content enhancement for Node.js"""
        original_content = "This is about Node.js servers."
        
        enhanced = await service._enhance_backend_content(original_content, "node.js")
        
        assert "Node.js Context" in enhanced
        assert "modules, event loop, and async/await" in enhanced
        assert original_content in enhanced

    @pytest.mark.asyncio
    async def test_enhance_language_content_typescript(self, service):
        """Test content enhancement for TypeScript"""
        original_content = "This is about TypeScript types."
        
        enhanced = await service._enhance_language_content(original_content, "typescript")
        
        assert "Typescript Context" in enhanced
        assert "types, interfaces, and generics" in enhanced
        assert original_content in enhanced

    @pytest.mark.asyncio
    async def test_process_context7_document_success(self, service, sample_context7_document, sample_query_intent):
        """Test successful processing of Context7 document"""
        # Mock the parent class method
        with patch.object(service, 'process_documentation') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                chunks_processed=5,
                workspace_slug="react-docs"
            )
            
            with patch.object(service, '_enhance_document_content', return_value="enhanced content"), \
                 patch.object(service, '_calculate_intelligent_ttl', return_value=45), \
                 patch.object(service, '_assess_document_quality', return_value=0.85), \
                 patch.object(service, '_add_ttl_metadata'):
                
                result = await service.process_context7_document(
                    sample_context7_document, sample_query_intent
                )
                
                assert result.success is True
                assert result.chunks_processed == 5
                assert result.workspace_slug == "react-docs"

    @pytest.mark.asyncio
    async def test_process_context7_results_batch(self, service, sample_search_result, sample_query_intent):
        """Test batch processing of Context7 results"""
        search_results = [sample_search_result] * 3  # Three identical results
        
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = Context7Document(
                content="test content",
                title="Test Doc",
                source_url="https://test.com",
                technology="react",
                owner="facebook"
            )
            
            with patch.object(service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="react-docs"
                )
                
                results = await service.process_context7_results(search_results, sample_query_intent)
                
                assert len(results) == 3
                assert all(result.success for result in results)
                assert all(result.chunks_processed == 2 for result in results)

    @pytest.mark.asyncio
    async def test_cleanup_expired_documents(self, service, mock_weaviate_client, mock_db_manager):
        """Test cleanup of expired documents"""
        workspace_slug = "test-workspace"
        
        # Mock Weaviate cleanup result
        mock_weaviate_client.cleanup_expired_documents.return_value = {
            "deleted_documents": 3,
            "deleted_chunks": 15,
            "message": "Cleanup successful"
        }
        
        # Mock database cleanup result
        mock_db_manager.execute.return_value = 3  # 3 records deleted
        
        result = await service.cleanup_expired_documents(workspace_slug)
        
        assert result["workspace"] == workspace_slug
        assert result["weaviate_cleanup"]["deleted_documents"] == 3
        assert result["weaviate_cleanup"]["deleted_chunks"] == 15
        assert result["database_records_cleaned"] == 3
        assert "cleaned_at" in result

    @pytest.mark.asyncio
    async def test_extract_quality_indicators(self, service, sample_search_result):
        """Test extraction of quality indicators"""
        indicators = await service._extract_quality_indicators(sample_search_result)
        
        assert "has_code_examples" in indicators
        assert "has_links" in indicators
        assert "word_count" in indicators
        assert "char_count" in indicators
        assert "header_count" in indicators
        assert "relevance_score" in indicators
        assert "overall_score" in indicators
        
        # Check that code examples are detected
        assert indicators["has_code_examples"] is True  # Sample has code blocks
        assert indicators["word_count"] > 0
        assert indicators["char_count"] > 0
        assert indicators["relevance_score"] == 0.95

    @pytest.mark.asyncio
    async def test_error_handling_in_document_processing(self, service, sample_context7_document, sample_query_intent):
        """Test error handling in document processing"""
        # Mock a failure in the process_documentation method
        with patch.object(service, 'process_documentation') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            result = await service.process_context7_document(
                sample_context7_document, sample_query_intent
            )
            
            assert result.success is False
            assert result.chunks_processed == 0
            assert "Processing failed" in result.error_message

    @pytest.mark.asyncio
    async def test_ttl_config_defaults(self):
        """Test TTL configuration defaults"""
        config = TTLConfig()
        
        assert config.default_days == 30
        assert config.min_days == 1
        assert config.max_days == 90
        assert "react" in config.technology_multipliers
        assert "api" in config.doc_type_multipliers

    @pytest.mark.asyncio
    async def test_ttl_config_custom_values(self):
        """Test TTL configuration with custom values"""
        config = TTLConfig(
            default_days=15,
            min_days=2,
            max_days=60,
            technology_multipliers={"vue": 2.0},
            doc_type_multipliers={"tutorial": 1.0}
        )
        
        assert config.default_days == 15
        assert config.min_days == 2
        assert config.max_days == 60
        assert config.technology_multipliers["vue"] == 2.0
        assert config.doc_type_multipliers["tutorial"] == 1.0


class TestContext7Document:
    """Test suite for Context7Document model"""
    
    def test_context7_document_creation(self):
        """Test creating a Context7Document"""
        doc = Context7Document(
            content="Test content",
            title="Test Document",
            source_url="https://test.com",
            technology="react",
            owner="facebook"
        )
        
        assert doc.content == "Test content"
        assert doc.title == "Test Document"
        assert doc.source_url == "https://test.com"
        assert doc.technology == "react"
        assert doc.owner == "facebook"
        assert doc.doc_type == "documentation"  # Default
        assert doc.language == "en"  # Default
        assert doc.version is None  # Optional
        assert isinstance(doc.quality_indicators, dict)
        assert isinstance(doc.metadata, dict)

    def test_context7_document_with_optional_fields(self):
        """Test creating Context7Document with optional fields"""
        doc = Context7Document(
            content="Test content",
            title="Test Document",
            source_url="https://test.com",
            technology="react",
            owner="facebook",
            version="18.2.0",
            doc_type="api",
            language="es",
            quality_indicators={"score": 0.9},
            metadata={"custom": "value"}
        )
        
        assert doc.version == "18.2.0"
        assert doc.doc_type == "api"
        assert doc.language == "es"
        assert doc.quality_indicators["score"] == 0.9
        assert doc.metadata["custom"] == "value"


class TestTTLConfig:
    """Test suite for TTLConfig model"""
    
    def test_ttl_config_defaults(self):
        """Test TTL config with default values"""
        config = TTLConfig()
        
        assert config.default_days == 30
        assert config.min_days == 1
        assert config.max_days == 90
        assert isinstance(config.technology_multipliers, dict)
        assert isinstance(config.doc_type_multipliers, dict)
        
        # Check some expected defaults
        assert config.technology_multipliers.get("react") == 1.5
        assert config.doc_type_multipliers.get("api") == 2.0

    def test_ttl_config_custom_values(self):
        """Test TTL config with custom values"""
        custom_tech_multipliers = {"custom_tech": 3.0}
        custom_doc_multipliers = {"custom_doc": 0.5}
        
        config = TTLConfig(
            default_days=45,
            min_days=5,
            max_days=120,
            technology_multipliers=custom_tech_multipliers,
            doc_type_multipliers=custom_doc_multipliers
        )
        
        assert config.default_days == 45
        assert config.min_days == 5
        assert config.max_days == 120
        assert config.technology_multipliers == custom_tech_multipliers
        assert config.doc_type_multipliers == custom_doc_multipliers


class TestContext7TTLAdvanced:
    """Advanced TTL functionality tests"""
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing log messages"""
        return MagicMock()
    
    @pytest.fixture
    def complex_ttl_config(self):
        """Complex TTL configuration for advanced testing"""
        return TTLConfig(
            default_days=30,
            min_days=1,
            max_days=90,
            technology_multipliers={
                "react": 1.5,
                "vue": 1.5,
                "angular": 1.5,
                "next.js": 2.0,
                "typescript": 2.0,
                "javascript": 1.0,
                "python": 1.0,
                "django": 1.5,
                "flask": 1.5,
                "fastapi": 1.5,
                "express": 1.0,
                "node.js": 1.0,
                "tailwind": 1.0,
                "bootstrap": 0.8,
                "webpack": 1.2,
                "vite": 1.2,
                "rollup": 1.2,
                "unknown": 1.0
            },
            doc_type_multipliers={
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
                "documentation": 1.0
            }
        )
    
    @pytest.fixture
    def service_with_complex_config(self, mock_llm_client, mock_weaviate_client, mock_db_manager, complex_ttl_config):
        """Service with complex configuration"""
        return Context7IngestionService(
            llm_client=mock_llm_client,
            weaviate_client=mock_weaviate_client,
            db_manager=mock_db_manager,
            ttl_config=complex_ttl_config
        )
    
    @pytest.mark.asyncio
    async def test_ttl_calculation_with_all_multipliers(self, service_with_complex_config):
        """Test TTL calculation with all multiplier combinations"""
        # Test various technology/doc type combinations
        test_cases = [
            ("react", "api", 90),  # Should hit max bound
            ("bootstrap", "changelog", 12),  # Low multipliers
            ("typescript", "reference", 90),  # Should hit max bound
            ("unknown", "news", 9),  # Low multipliers
            ("next.js", "best_practices", 90),  # Should hit max bound
            ("python", "tutorial", 36),  # Moderate multipliers
        ]
        
        for technology, doc_type, expected_bound in test_cases:
            doc = Context7Document(
                content="Test content for TTL calculation",
                title=f"{technology.title()} {doc_type.title()}",
                source_url=f"https://example.com/{technology}/{doc_type}",
                technology=technology,
                owner="testowner",
                doc_type=doc_type,
                quality_indicators={"overall_score": 0.8}
            )
            
            with patch.object(service_with_complex_config, '_analyze_content_for_ttl', return_value=1.0), \
                 patch.object(service_with_complex_config, '_analyze_version_for_ttl', return_value=1.0):
                
                ttl = await service_with_complex_config._calculate_intelligent_ttl(doc, Mock())
                
                # Verify bounds are respected
                assert 1 <= ttl <= 90, f"TTL {ttl} out of bounds for {technology}/{doc_type}"
                
                # Verify specific cases
                if technology in ["react", "typescript", "next.js"] and doc_type in ["api", "reference", "best_practices"]:
                    assert ttl == 90, f"High value combo should hit max: {technology}/{doc_type}"
                elif technology == "bootstrap" and doc_type == "changelog":
                    assert ttl < 20, f"Low value combo should be low: {technology}/{doc_type}"
    
    @pytest.mark.asyncio
    async def test_content_analysis_edge_cases(self, service_with_complex_config):
        """Test content analysis with edge cases"""
        edge_cases = [
            ("This is DEPRECATED and will be removed", 0.5),
            ("This is deprecated, legacy, and old", 0.5),
            ("This is stable, production-ready, and recommended", 1.5),
            ("This is STABLE and LTS", 1.5),
            ("This is beta, experimental, and alpha", 0.7),
            ("This is a comprehensive, complete, and detailed guide", 1.2),
            ("Short", 0.9),  # Very short content
            ("A" * 15000, 1.1),  # Very long content
            ("", 0.9),  # Empty content
        ]
        
        for content, expected_multiplier in edge_cases:
            doc = Context7Document(
                content=content,
                title="Test Document",
                source_url="https://example.com/test",
                technology="react",
                owner="testowner"
            )
            
            multiplier = await service_with_complex_config._analyze_content_for_ttl(doc)
            
            assert multiplier == expected_multiplier, f"Content '{content[:50]}...' should have multiplier {expected_multiplier}, got {multiplier}"
    
    @pytest.mark.asyncio
    async def test_version_analysis_edge_cases(self, service_with_complex_config):
        """Test version analysis with edge cases"""
        version_cases = [
            ("latest", 1.3),
            ("current", 1.3),
            ("stable", 1.3),
            ("v1.0.0-beta", 0.6),
            ("v2.0.0-alpha.1", 0.6),
            ("v3.0.0-rc.1", 0.6),
            ("preview", 0.6),
            ("v1.0.0", 1.1),
            ("v4.2.1", 1.2),  # Mature version
            ("v0.1.0", 0.8),  # Early version
            ("", 1.0),  # Empty version
            (None, 1.0),  # No version
        ]
        
        for version, expected_multiplier in version_cases:
            doc = Context7Document(
                content="Test content",
                title="Test Document",
                source_url="https://example.com/test",
                technology="react",
                owner="testowner",
                version=version
            )
            
            multiplier = await service_with_complex_config._analyze_version_for_ttl(doc)
            
            assert multiplier == expected_multiplier, f"Version '{version}' should have multiplier {expected_multiplier}, got {multiplier}"
    
    @pytest.mark.asyncio
    async def test_quality_assessment_comprehensive(self, service_with_complex_config):
        """Test comprehensive quality assessment"""
        # High quality document
        high_quality_doc = Context7Document(
            content="""# Complete API Reference
            
## Overview
This is a comprehensive guide to the API with detailed examples and best practices.

## Installation
```bash
npm install package-name
```

## Configuration
```javascript
const config = {
    apiKey: 'your-key',
    endpoint: 'https://api.example.com'
};
```

## Usage Examples
```javascript
// Basic usage
const client = new APIClient(config);

// Advanced usage
const result = await client.query({
    filters: ['example'],
    limit: 10
});
```

## API Reference
### Methods
- `query()` - Perform a search query
- `create()` - Create a new resource
- `update()` - Update an existing resource
- `delete()` - Delete a resource

### Headers
- `Authorization` - API key for authentication
- `Content-Type` - Must be application/json

## Troubleshooting
Common issues and solutions:
- Issue 1: [Solution](https://example.com/solution1)
- Issue 2: [Solution](https://example.com/solution2)

## Best Practices
1. Always validate input
2. Use error handling
3. Implement rate limiting

See the [official documentation](https://example.com/docs) for more details.
""",
            title="Complete API Reference",
            source_url="https://example.com/api",
            technology="react",
            owner="testowner",
            doc_type="api"
        )
        
        quality = await service_with_complex_config._assess_document_quality(high_quality_doc)
        assert quality >= 0.8, f"High quality document should score >= 0.8, got {quality}"
        
        # Low quality document
        low_quality_doc = Context7Document(
            content="Brief info.",
            title="Info",
            source_url="https://example.com/info",
            technology="react",
            owner="testowner",
            doc_type="blog"
        )
        
        quality = await service_with_complex_config._assess_document_quality(low_quality_doc)
        assert quality <= 0.2, f"Low quality document should score <= 0.2, got {quality}"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_comprehensive(self, service_with_complex_config):
        """Test comprehensive document type classification"""
        classification_cases = [
            ("React API Documentation", "Complete API reference", "api"),
            ("Getting Started with Vue", "Quick start guide", "getting_started"),
            ("Installation Guide", "How to install", "installation"),
            ("Configuration Settings", "Config options", "configuration"),
            ("Troubleshooting Guide", "Debug common issues", "troubleshooting"),
            ("Changelog v2.0", "What's new", "changelog"),
            ("Migration from v1 to v2", "Upgrade guide", "migration"),
            ("Code Examples", "Usage examples", "examples"),
            ("FAQ Section", "Frequently asked questions", "faq"),
            ("Best Practices", "Recommended patterns", "best_practices"),
            ("Blog Post: New Features", "Latest updates", "blog"),
            ("News: Product Launch", "Announcement", "news"),
            ("Release Notes v3.0", "Version 3.0 changes", "release_notes"),
            ("Unknown Document", "General content", "documentation"),
        ]
        
        for title, content, expected_type in classification_cases:
            doc_type = await service_with_complex_config._classify_document_type(title, content)
            assert doc_type == expected_type, f"Title '{title}' should be classified as '{expected_type}', got '{doc_type}'"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_ttl_calculation(self, service_with_complex_config):
        """Test error handling in TTL calculation"""
        # Test with invalid document data
        invalid_doc = Context7Document(
            content="Test content",
            title="Test Document",
            source_url="https://example.com/test",
            technology="react",
            owner="testowner"
        )
        
        # Mock methods to raise exceptions
        with patch.object(service_with_complex_config, '_analyze_content_for_ttl', side_effect=Exception("Content analysis failed")):
            ttl = await service_with_complex_config._calculate_intelligent_ttl(invalid_doc, Mock())
            # Should fall back to default TTL
            assert ttl == 30, f"Should fallback to default TTL on error, got {ttl}"
        
        with patch.object(service_with_complex_config, '_analyze_version_for_ttl', side_effect=Exception("Version analysis failed")):
            ttl = await service_with_complex_config._calculate_intelligent_ttl(invalid_doc, Mock())
            # Should still calculate with other multipliers
            assert ttl > 0, f"Should still calculate TTL with partial failures, got {ttl}"
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, service_with_complex_config):
        """Test batch processing performance characteristics"""
        # Create multiple documents
        documents = []
        for i in range(10):
            doc = Context7Document(
                content=f"Test content {i}",
                title=f"Test Document {i}",
                source_url=f"https://example.com/test{i}",
                technology="react",
                owner="testowner",
                doc_type="guide"
            )
            documents.append(doc)
        
        # Mock processing to be fast
        with patch.object(service_with_complex_config, 'process_context7_document') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                chunks_processed=3,
                workspace_slug="test-workspace"
            )
            
            start_time = time.time()
            results = await service_with_complex_config._process_document_batch(documents, Mock())
            processing_time = time.time() - start_time
            
            # Should complete quickly with concurrent processing
            assert processing_time < 5.0, f"Batch processing took too long: {processing_time}s"
            assert len(results) == 10, f"Should process all documents, got {len(results)}"
            assert all(result.success for result in results), "All documents should be processed successfully"
    
    @pytest.mark.asyncio
    async def test_ttl_metadata_addition(self, service_with_complex_config):
        """Test TTL metadata addition to database"""
        from src.document_processing.models import DocumentContent
        
        content = DocumentContent(
            content_id="test-doc-123",
            title="Test Document",
            text="Test content",
            source_url="https://example.com/test",
            metadata={
                "technology": "react",
                "owner": "testowner"
            }
        )
        
        # Mock database execute
        mock_db = service_with_complex_config.db = AsyncMock()
        mock_db.execute.return_value = None
        
        await service_with_complex_config._add_ttl_metadata(content, "test-workspace", 45, "test-correlation-id")
        
        # Verify database was called with correct parameters
        mock_db.execute.assert_called_once()
        args, kwargs = mock_db.execute.call_args
        
        assert "UPDATE content_metadata" in args[0]
        assert "ttl_info" in args[0]
        assert kwargs["content_id"] == "test-doc-123"
        assert "ttl_metadata" in kwargs
        
        # Verify TTL metadata structure
        ttl_metadata = json.loads(kwargs["ttl_metadata"])
        assert ttl_metadata["ttl_days"] == 45
        assert "created_at" in ttl_metadata
        assert "expires_at" in ttl_metadata
        assert ttl_metadata["source_provider"] == "context7"


class TestContext7LoggingVerification:
    """Tests for PIPELINE_METRICS logging verification"""
    
    @pytest.fixture
    def log_capture(self):
        """Capture log messages for verification"""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        logger = logging.getLogger("src.ingestion.context7_ingestion_service")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        yield log_capture
        
        logger.removeHandler(handler)
    
    @pytest.mark.asyncio
    async def test_pipeline_metrics_logging_document_processing(self, service, sample_context7_document, sample_query_intent, log_capture):
        """Test PIPELINE_METRICS logging during document processing"""
        # Mock all the processing steps
        with patch.object(service, 'process_documentation') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                chunks_processed=5,
                workspace_slug="test-workspace"
            )
            
            with patch.object(service, '_enhance_document_content', return_value="enhanced content"), \
                 patch.object(service, '_calculate_intelligent_ttl', return_value=45), \
                 patch.object(service, '_assess_document_quality', return_value=0.85), \
                 patch.object(service, '_add_ttl_metadata'):
                
                await service.process_context7_document(sample_context7_document, sample_query_intent, "test-correlation-123")
                
                # Verify logging messages
                log_output = log_capture.getvalue()
                
                # Check for required PIPELINE_METRICS entries
                assert "PIPELINE_METRICS: step=context7_document_processing_start" in log_output
                assert "correlation_id=test-correlation-123" in log_output
                assert "PIPELINE_METRICS: step=context7_content_enhancement" in log_output
                assert "PIPELINE_METRICS: step=context7_ttl_calculation" in log_output
                assert "PIPELINE_METRICS: step=context7_quality_assessment" in log_output
                assert "PIPELINE_METRICS: step=context7_document_processing_complete" in log_output
                assert "duration_ms=" in log_output
                assert "success=true" in log_output
    
    @pytest.mark.asyncio
    async def test_pipeline_metrics_logging_batch_processing(self, service, sample_search_result, sample_query_intent, log_capture):
        """Test PIPELINE_METRICS logging during batch processing"""
        search_results = [sample_search_result] * 3
        
        with patch.object(service, '_convert_search_result_to_document') as mock_convert:
            mock_convert.return_value = Context7Document(
                content="test content",
                title="Test Doc",
                source_url="https://test.com",
                technology="react",
                owner="facebook"
            )
            
            with patch.object(service, 'process_context7_document') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    chunks_processed=2,
                    workspace_slug="test-workspace"
                )
                
                await service.process_context7_results(search_results, sample_query_intent, "batch-correlation-456")
                
                # Verify batch logging
                log_output = log_capture.getvalue()
                
                assert "PIPELINE_METRICS: step=context7_batch_processing_start" in log_output
                assert "correlation_id=batch-correlation-456" in log_output
                assert "result_count=3" in log_output
                assert "PIPELINE_METRICS: step=context7_document_conversion" in log_output
                assert "PIPELINE_METRICS: step=context7_batch_process" in log_output
                assert "PIPELINE_METRICS: step=context7_batch_processing_complete" in log_output
    
    @pytest.mark.asyncio
    async def test_pipeline_metrics_logging_error_handling(self, service, sample_context7_document, sample_query_intent, log_capture):
        """Test PIPELINE_METRICS logging during error conditions"""
        # Mock a failure in document processing
        with patch.object(service, 'process_documentation', side_effect=Exception("Processing failed")):
            
            result = await service.process_context7_document(sample_context7_document, sample_query_intent, "error-correlation-789")
            
            # Verify error logging
            log_output = log_capture.getvalue()
            
            assert "PIPELINE_METRICS: step=context7_document_processing_error" in log_output
            assert "correlation_id=error-correlation-789" in log_output
            assert "error=\"Processing failed\"" in log_output
            assert "success=false" in log_output
            assert result.success is False
    
    @pytest.mark.asyncio
    async def test_pipeline_metrics_ttl_detail_logging(self, service, sample_context7_document, sample_query_intent, log_capture):
        """Test detailed TTL calculation logging"""
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.2), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.1):
            
            await service._calculate_intelligent_ttl(sample_context7_document, sample_query_intent, "ttl-correlation-101")
            
            # Verify detailed TTL logging
            log_output = log_capture.getvalue()
            
            assert "PIPELINE_METRICS: step=context7_ttl_calculation_detail" in log_output
            assert "correlation_id=ttl-correlation-101" in log_output
            assert "base_ttl=" in log_output
            assert "tech_multiplier=" in log_output
            assert "doc_type_multiplier=" in log_output
            assert "final_ttl=" in log_output
            assert "quality_score=" in log_output


class TestContext7ErrorHandling:
    """Tests for error handling and fallback mechanisms"""
    
    @pytest.mark.asyncio
    async def test_convert_search_result_error_handling(self, service, sample_search_result, sample_query_intent):
        """Test error handling in search result conversion"""
        # Mock methods to raise exceptions
        with patch.object(service, '_extract_version_from_content', side_effect=Exception("Version extraction failed")), \
             patch.object(service, '_classify_document_type', side_effect=Exception("Classification failed")), \
             patch.object(service, '_extract_quality_indicators', side_effect=Exception("Quality extraction failed")):
            
            document = await service._convert_search_result_to_document(sample_search_result, sample_query_intent)
            
            # Should return None on error
            assert document is None
    
    @pytest.mark.asyncio
    async def test_batch_processing_partial_failures(self, service, sample_query_intent):
        """Test batch processing with partial failures"""
        # Create documents where some will fail
        documents = []
        for i in range(5):
            doc = Context7Document(
                content=f"Test content {i}",
                title=f"Test Document {i}",
                source_url=f"https://example.com/test{i}",
                technology="react",
                owner="testowner"
            )
            documents.append(doc)
        
        # Mock processing to fail for some documents
        def mock_process(doc, intent, correlation_id):
            if "Test Document 2" in doc.title:
                raise Exception("Processing failed for document 2")
            return ProcessingResult(
                success=True,
                chunks_processed=3,
                workspace_slug="test-workspace"
            )
        
        with patch.object(service, 'process_context7_document', side_effect=mock_process):
            results = await service._process_document_batch(documents, sample_query_intent)
            
            # Should return results for successful documents only
            assert len(results) == 4, f"Should process 4 successful documents, got {len(results)}"
            assert all(result.success for result in results), "All returned results should be successful"
    
    @pytest.mark.asyncio
    async def test_quality_assessment_error_handling(self, service):
        """Test quality assessment error handling"""
        # Create document with problematic content
        problematic_doc = Context7Document(
            content=None,  # This should cause issues
            title="Problematic Document",
            source_url="https://example.com/problematic",
            technology="react",
            owner="testowner"
        )
        
        # Mock to raise exception during quality assessment
        with patch('re.findall', side_effect=Exception("Regex failed")):
            quality = await service._assess_document_quality(problematic_doc)
            
            # Should return default quality score
            assert quality == 0.5, f"Should return default quality score on error, got {quality}"
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, service):
        """Test database error handling"""
        from src.document_processing.models import DocumentContent
        
        content = DocumentContent(
            content_id="test-doc-123",
            title="Test Document",
            text="Test content",
            source_url="https://example.com/test",
            metadata={}
        )
        
        # Mock database to raise exception
        mock_db = service.db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        # Should handle database errors gracefully
        try:
            await service._add_ttl_metadata(content, "test-workspace", 45, "test-correlation-id")
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"Database error should be handled gracefully, but got: {e}")


class TestContext7ConfigurationLoading:
    """Tests for Context7 configuration loading and validation"""
    
    @pytest.fixture
    def env_vars(self):
        """Mock environment variables"""
        return {
            "CONTEXT7_TTL_DEFAULT_DAYS": "45",
            "CONTEXT7_TTL_MIN_DAYS": "2",
            "CONTEXT7_TTL_MAX_DAYS": "120",
            "CONTEXT7_TTL_TECH_MULTIPLIER_REACT": "2.0",
            "CONTEXT7_TTL_TECH_MULTIPLIER_VUE": "1.8",
            "CONTEXT7_TTL_DOC_TYPE_MULTIPLIER_API": "3.0",
            "CONTEXT7_TTL_DOC_TYPE_MULTIPLIER_TUTORIAL": "1.5",
        }
    
    @pytest.mark.asyncio
    async def test_config_loading_from_environment(self, env_vars):
        """Test loading configuration from environment variables"""
        with patch.dict(os.environ, env_vars):
            # Mock function to load config from environment
            def load_config_from_env():
                config = TTLConfig()
                config.default_days = int(os.environ.get("CONTEXT7_TTL_DEFAULT_DAYS", config.default_days))
                config.min_days = int(os.environ.get("CONTEXT7_TTL_MIN_DAYS", config.min_days))
                config.max_days = int(os.environ.get("CONTEXT7_TTL_MAX_DAYS", config.max_days))
                
                # Load technology multipliers
                for key, value in os.environ.items():
                    if key.startswith("CONTEXT7_TTL_TECH_MULTIPLIER_"):
                        tech = key.replace("CONTEXT7_TTL_TECH_MULTIPLIER_", "").lower()
                        config.technology_multipliers[tech] = float(value)
                    elif key.startswith("CONTEXT7_TTL_DOC_TYPE_MULTIPLIER_"):
                        doc_type = key.replace("CONTEXT7_TTL_DOC_TYPE_MULTIPLIER_", "").lower()
                        config.doc_type_multipliers[doc_type] = float(value)
                
                return config
            
            config = load_config_from_env()
            
            assert config.default_days == 45
            assert config.min_days == 2
            assert config.max_days == 120
            assert config.technology_multipliers["react"] == 2.0
            assert config.technology_multipliers["vue"] == 1.8
            assert config.doc_type_multipliers["api"] == 3.0
            assert config.doc_type_multipliers["tutorial"] == 1.5
    
    @pytest.mark.asyncio
    async def test_config_validation_bounds(self):
        """Test configuration validation for bounds"""
        # Test invalid bounds
        with pytest.raises(ValueError, match="min_days must be positive"):
            TTLConfig(min_days=0)
        
        with pytest.raises(ValueError, match="max_days must be greater than min_days"):
            TTLConfig(min_days=10, max_days=5)
        
        with pytest.raises(ValueError, match="default_days must be between min_days and max_days"):
            TTLConfig(default_days=100, min_days=1, max_days=50)
    
    @pytest.mark.asyncio
    async def test_config_validation_multipliers(self):
        """Test configuration validation for multipliers"""
        # Test negative multipliers
        with pytest.raises(ValueError, match="Technology multipliers must be positive"):
            TTLConfig(technology_multipliers={"react": -1.0})
        
        with pytest.raises(ValueError, match="Document type multipliers must be positive"):
            TTLConfig(doc_type_multipliers={"api": -0.5})
        
        # Test zero multipliers
        with pytest.raises(ValueError, match="Technology multipliers must be positive"):
            TTLConfig(technology_multipliers={"react": 0.0})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])