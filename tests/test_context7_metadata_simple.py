#!/usr/bin/env python3
"""
SUB-TASK A2: Context7 Metadata Processing Verification Tests (Simplified)
=========================================================================

Comprehensive verification of Context7IngestionService metadata processing.
Tests Context7Document creation, technology/owner extraction, quality assessment,
version detection, and document type classification without pytest dependency.
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.search.llm_query_analyzer import QueryIntent
from src.mcp.providers.models import SearchResult, SearchResultType


class MetadataProcessingTests:
    """Context7 metadata processing tests"""
    
    def __init__(self):
        self.service = Context7IngestionService(
            llm_client=AsyncMock(),
            weaviate_client=AsyncMock(),
            db_manager=AsyncMock(),
            ttl_config=TTLConfig()
        )
        
        self.sample_intent = QueryIntent(
            intent="documentation",
            technology="react",
            topics=["hooks"],
            doc_type="guide",
            user_level="intermediate"
        )
    
    def create_search_result(self, title, content, url, metadata=None):
        """Helper to create search results"""
        return SearchResult(
            title=title,
            url=url,
            snippet=content[:200],
            content=content,
            content_type=SearchResultType.DOCUMENTATION,
            source_domain="context7.com",
            relevance_score=0.85,
            provider_rank=1,
            metadata=metadata or {}
        )
    
    async def test_basic_document_creation(self):
        """Test basic Context7Document creation from SearchResult"""
        search_result = self.create_search_result(
            title="React Hooks Guide",
            content="This is a comprehensive guide to React hooks",
            url="https://context7.com/facebook/react/llms.txt",
            metadata={
                "owner": "facebook",
                "technology": "react",
                "source": "context7"
            }
        )
        
        with patch.object(self.service, '_extract_version_from_content', return_value="18.2.0"), \
             patch.object(self.service, '_classify_document_type', return_value="guide"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={"overall_score": 0.85}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document is not None, "Document should not be None"
            assert document.title == "React Hooks Guide", f"Expected 'React Hooks Guide', got '{document.title}'"
            assert document.source_url == "https://context7.com/facebook/react/llms.txt", f"Wrong source URL: {document.source_url}"
            assert document.technology == "react", f"Expected 'react', got '{document.technology}'"
            assert document.owner == "facebook", f"Expected 'facebook', got '{document.owner}'"
            assert document.version == "18.2.0", f"Expected '18.2.0', got '{document.version}'"
            assert document.doc_type == "guide", f"Expected 'guide', got '{document.doc_type}'"
            assert document.language == "en", f"Expected 'en', got '{document.language}'"
    
    async def test_technology_extraction_from_metadata(self):
        """Test technology extraction from metadata"""
        search_result = self.create_search_result(
            title="Vue.js Components",
            content="Vue component documentation",
            url="https://context7.com/vuejs/vue/llms.txt",
            metadata={
                "owner": "vuejs",
                "technology": "vue",
                "source": "context7"
            }
        )
        
        with patch.object(self.service, '_extract_version_from_content', return_value=None), \
             patch.object(self.service, '_classify_document_type', return_value="documentation"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document.technology == "vue", f"Expected 'vue', got '{document.technology}'"
    
    async def test_technology_fallback_to_intent(self):
        """Test technology fallback to intent when not in metadata"""
        search_result = self.create_search_result(
            title="Generic Guide",
            content="Generic documentation",
            url="https://context7.com/generic/docs/llms.txt",
            metadata={
                "owner": "generic",
                "source": "context7"
            }
        )
        
        with patch.object(self.service, '_extract_version_from_content', return_value=None), \
             patch.object(self.service, '_classify_document_type', return_value="documentation"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document.technology == "react", f"Expected 'react' (from intent), got '{document.technology}'"
    
    async def test_owner_extraction_from_metadata(self):
        """Test owner extraction from metadata"""
        search_result = self.create_search_result(
            title="TypeScript Documentation",
            content="TypeScript type system guide",
            url="https://context7.com/microsoft/typescript/llms.txt",
            metadata={
                "owner": "microsoft",
                "technology": "typescript",
                "source": "context7"
            }
        )
        
        with patch.object(self.service, '_extract_version_from_content', return_value=None), \
             patch.object(self.service, '_classify_document_type', return_value="documentation"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document.owner == "microsoft", f"Expected 'microsoft', got '{document.owner}'"
    
    async def test_owner_fallback_to_unknown(self):
        """Test owner fallback to unknown when not in metadata"""
        search_result = self.create_search_result(
            title="Unknown Owner Doc",
            content="Documentation without owner",
            url="https://context7.com/unknown/docs/llms.txt",
            metadata={
                "technology": "javascript",
                "source": "context7"
            }
        )
        
        with patch.object(self.service, '_extract_version_from_content', return_value=None), \
             patch.object(self.service, '_classify_document_type', return_value="documentation"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document.owner == "unknown", f"Expected 'unknown', got '{document.owner}'"
    
    async def test_version_extraction_patterns(self):
        """Test version extraction from content with various patterns"""
        # Test version pattern: version: X.X.X
        content1 = "This documentation covers version: 18.2.0 of React"
        version1 = await self.service._extract_version_from_content(content1)
        assert version1 == "18.2.0", f"Expected '18.2.0', got '{version1}'"
        
        # Test version pattern: vX.X.X
        content2 = "Updated for v3.1.4 release"
        version2 = await self.service._extract_version_from_content(content2)
        assert version2 == "3.1.4", f"Expected '3.1.4', got '{version2}'"
        
        # Test no version
        content3 = "This is documentation without version"
        version3 = await self.service._extract_version_from_content(content3)
        assert version3 is None, f"Expected None, got '{version3}'"
    
    async def test_document_type_classification_api(self):
        """Test document type classification for API docs"""
        title = "React API Reference"
        content = "Complete API documentation for React components"
        doc_type = await self.service._classify_document_type(title, content)
        assert doc_type == "api", f"Expected 'api', got '{doc_type}'"
    
    async def test_document_type_classification_guide(self):
        """Test document type classification for guides"""
        title = "React Hooks Guide"
        content = "Comprehensive guide to React hooks"
        doc_type = await self.service._classify_document_type(title, content)
        assert doc_type == "guide", f"Expected 'guide', got '{doc_type}'"
    
    async def test_document_type_classification_getting_started(self):
        """Test document type classification for getting started"""
        title = "Getting Started with React"
        content = "How to get started with React"
        doc_type = await self.service._classify_document_type(title, content)
        assert doc_type == "getting_started", f"Expected 'getting_started', got '{doc_type}'"
    
    async def test_document_type_classification_installation(self):
        """Test document type classification for installation"""
        title = "React Installation Guide"
        content = "How to install React"
        doc_type = await self.service._classify_document_type(title, content)
        assert doc_type == "installation", f"Expected 'installation', got '{doc_type}'"
    
    async def test_document_type_classification_default(self):
        """Test document type classification default"""
        title = "Some Random Title"
        content = "Random content that doesn't match patterns"
        doc_type = await self.service._classify_document_type(title, content)
        assert doc_type == "documentation", f"Expected 'documentation', got '{doc_type}'"
    
    async def test_quality_indicators_extraction(self):
        """Test quality indicators extraction"""
        search_result = self.create_search_result(
            title="High Quality Documentation",
            content="""# React Hooks Guide
            
React hooks are a powerful feature.

## useState Hook

```jsx
const [count, setCount] = useState(0);
```

Learn more at [React Docs](https://reactjs.org).

### Advanced Topics
""",
            url="https://context7.com/react/hooks"
        )
        
        indicators = await self.service._extract_quality_indicators(search_result)
        
        assert "has_code_examples" in indicators, "Missing has_code_examples indicator"
        assert "has_links" in indicators, "Missing has_links indicator"
        assert "word_count" in indicators, "Missing word_count indicator"
        assert "char_count" in indicators, "Missing char_count indicator"
        assert "header_count" in indicators, "Missing header_count indicator"
        assert "relevance_score" in indicators, "Missing relevance_score indicator"
        
        # Check specific indicators
        assert indicators["has_code_examples"] is True, "Should detect code examples"
        assert indicators["has_links"] is True, "Should detect links"
        assert indicators["word_count"] > 0, "Word count should be > 0"
        assert indicators["char_count"] > 0, "Char count should be > 0"
        assert indicators["header_count"] > 0, "Header count should be > 0"
        assert indicators["relevance_score"] == 0.85, f"Expected 0.85, got {indicators['relevance_score']}"
    
    async def test_language_detection_from_metadata(self):
        """Test language detection from metadata"""
        search_result = self.create_search_result(
            title="Spanish Documentation",
            content="Documentación en español",
            url="https://context7.com/es/docs/llms.txt",
            metadata={
                "owner": "example",
                "technology": "react",
                "source": "context7"
            }
        )
        search_result.language = "es"
        
        with patch.object(self.service, '_extract_version_from_content', return_value=None), \
             patch.object(self.service, '_classify_document_type', return_value="documentation"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document.language == "es", f"Expected 'es', got '{document.language}'"
    
    async def test_language_fallback_to_english(self):
        """Test language fallback to English"""
        search_result = self.create_search_result(
            title="No Language Doc",
            content="Documentation without language",
            url="https://context7.com/docs/llms.txt",
            metadata={
                "owner": "example",
                "technology": "react",
                "source": "context7"
            }
        )
        
        with patch.object(self.service, '_extract_version_from_content', return_value=None), \
             patch.object(self.service, '_classify_document_type', return_value="documentation"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document.language == "en", f"Expected 'en', got '{document.language}'"
    
    async def test_metadata_preservation(self):
        """Test that original metadata is preserved"""
        original_metadata = {
            "owner": "facebook",
            "technology": "react",
            "source": "context7",
            "section": 1,
            "total_sections": 3,
            "custom_field": "custom_value"
        }
        
        search_result = self.create_search_result(
            title="React Documentation",
            content="React documentation content",
            url="https://context7.com/facebook/react/llms.txt",
            metadata=original_metadata
        )
        
        with patch.object(self.service, '_extract_version_from_content', return_value=None), \
             patch.object(self.service, '_classify_document_type', return_value="documentation"), \
             patch.object(self.service, '_extract_quality_indicators', return_value={}):
            
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            assert document.metadata == original_metadata, f"Metadata not preserved: {document.metadata}"
    
    async def test_error_handling_in_conversion(self):
        """Test error handling in search result conversion"""
        search_result = self.create_search_result(
            title="Error Test",
            content="Test content",
            url="https://context7.com/error/test",
            metadata={"owner": "test", "technology": "react"}
        )
        
        # Mock an error in version extraction
        with patch.object(self.service, '_extract_version_from_content', side_effect=Exception("Version error")):
            document = await self.service._convert_search_result_to_document(
                search_result, self.sample_intent
            )
            
            # Should return None on error
            assert document is None, "Document should be None on error"


async def main():
    """Run all metadata processing tests"""
    print("="*60)
    print("SUB-TASK A2: Context7 Metadata Processing Verification")
    print("="*60)
    
    tests = MetadataProcessingTests()
    
    test_methods = [
        ("Basic Document Creation", tests.test_basic_document_creation),
        ("Technology Extraction from Metadata", tests.test_technology_extraction_from_metadata),
        ("Technology Fallback to Intent", tests.test_technology_fallback_to_intent),
        ("Owner Extraction from Metadata", tests.test_owner_extraction_from_metadata),
        ("Owner Fallback to Unknown", tests.test_owner_fallback_to_unknown),
        ("Version Extraction Patterns", tests.test_version_extraction_patterns),
        ("Document Type Classification API", tests.test_document_type_classification_api),
        ("Document Type Classification Guide", tests.test_document_type_classification_guide),
        ("Document Type Classification Getting Started", tests.test_document_type_classification_getting_started),
        ("Document Type Classification Installation", tests.test_document_type_classification_installation),
        ("Document Type Classification Default", tests.test_document_type_classification_default),
        ("Quality Indicators Extraction", tests.test_quality_indicators_extraction),
        ("Language Detection from Metadata", tests.test_language_detection_from_metadata),
        ("Language Fallback to English", tests.test_language_fallback_to_english),
        ("Metadata Preservation", tests.test_metadata_preservation),
        ("Error Handling in Conversion", tests.test_error_handling_in_conversion)
    ]
    
    tests_passed = 0
    tests_failed = 0
    
    for test_name, test_method in test_methods:
        try:
            print(f"\n🔍 Running {test_name}...")
            await test_method()
            print(f"✅ {test_name} PASSED")
            tests_passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            tests_failed += 1
    
    print(f"\n{'='*60}")
    print(f"SUB-TASK A2 RESULTS:")
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Success Rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")
    
    if tests_failed == 0:
        print("✅ ALL METADATA PROCESSING TESTS PASSED")
        return True
    else:
        print(f"❌ {tests_failed} METADATA PROCESSING TESTS FAILED")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test runner failed: {e}")
        exit(1)