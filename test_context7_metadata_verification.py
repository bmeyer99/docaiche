#!/usr/bin/env python3
"""
SUB-TASK A2: Context7 Metadata Processing Verification Tests
===========================================================

Comprehensive verification of Context7IngestionService metadata processing.
Tests Context7Document creation, technology/owner extraction, quality assessment,
version detection, and document type classification.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.search.llm_query_analyzer import QueryIntent
from src.mcp.providers.models import SearchResult, SearchResultType


class TestContext7MetadataProcessing:
    """Comprehensive Context7 metadata processing tests"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return Context7IngestionService(
            llm_client=AsyncMock(),
            weaviate_client=AsyncMock(),
            db_manager=AsyncMock(),
            ttl_config=TTLConfig()
        )
    
    @pytest.fixture
    def sample_intent(self):
        """Sample query intent"""
        return QueryIntent(
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
    
    @pytest.mark.asyncio
    async def test_context7_document_creation_basic(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value="18.2.0"), \
             patch.object(service, '_classify_document_type', return_value="guide"), \
             patch.object(service, '_extract_quality_indicators', return_value={"overall_score": 0.85}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document is not None
            assert document.title == "React Hooks Guide"
            assert document.source_url == "https://context7.com/facebook/react/llms.txt"
            assert document.technology == "react"
            assert document.owner == "facebook"
            assert document.version == "18.2.0"
            assert document.doc_type == "guide"
            assert document.language == "en"
            assert document.content == "This is a comprehensive guide to React hooks"
    
    @pytest.mark.asyncio
    async def test_technology_extraction_from_metadata(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value=None), \
             patch.object(service, '_classify_document_type', return_value="documentation"), \
             patch.object(service, '_extract_quality_indicators', return_value={}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document.technology == "vue"
    
    @pytest.mark.asyncio
    async def test_technology_fallback_to_intent(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value=None), \
             patch.object(service, '_classify_document_type', return_value="documentation"), \
             patch.object(service, '_extract_quality_indicators', return_value={}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document.technology == "react"  # From sample_intent
    
    @pytest.mark.asyncio
    async def test_owner_extraction_from_metadata(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value=None), \
             patch.object(service, '_classify_document_type', return_value="documentation"), \
             patch.object(service, '_extract_quality_indicators', return_value={}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document.owner == "microsoft"
    
    @pytest.mark.asyncio
    async def test_owner_fallback_to_unknown(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value=None), \
             patch.object(service, '_classify_document_type', return_value="documentation"), \
             patch.object(service, '_extract_quality_indicators', return_value={}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document.owner == "unknown"
    
    @pytest.mark.asyncio
    async def test_version_extraction_from_content_various_patterns(self, service):
        """Test version extraction from content with various patterns"""
        # Test version pattern: version: X.X.X
        content1 = "This documentation covers version: 18.2.0 of React"
        version1 = await service._extract_version_from_content(content1)
        assert version1 == "18.2.0"
        
        # Test version pattern: vX.X.X
        content2 = "Updated for v3.1.4 release"
        version2 = await service._extract_version_from_content(content2)
        assert version2 == "3.1.4"
        
        # Test version pattern: @X.X.X
        content3 = "Install with npm install react@17.0.2"
        version3 = await service._extract_version_from_content(content3)
        assert version3 == "17.0.2"
        
        # Test version pattern: X.X.X standalone
        content4 = "React 16.8.0 introduced hooks"
        version4 = await service._extract_version_from_content(content4)
        assert version4 == "16.8.0"
        
        # Test no version
        content5 = "This is documentation without version"
        version5 = await service._extract_version_from_content(content5)
        assert version5 is None
    
    @pytest.mark.asyncio
    async def test_document_type_classification_api(self, service):
        """Test document type classification for API docs"""
        title = "React API Reference"
        content = "Complete API documentation for React components"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "api"
        
        title = "TypeScript Reference Manual"
        content = "TypeScript reference documentation"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "api"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_guides(self, service):
        """Test document type classification for guides"""
        title = "React Hooks Guide"
        content = "Comprehensive guide to React hooks"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "guide"
        
        title = "Vue.js Tutorial"
        content = "Step-by-step tutorial for Vue.js"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "guide"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_getting_started(self, service):
        """Test document type classification for getting started"""
        title = "Getting Started with React"
        content = "How to get started with React"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "getting_started"
        
        title = "Vue.js QuickStart"
        content = "Quick start guide for Vue.js"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "getting_started"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_installation(self, service):
        """Test document type classification for installation"""
        title = "React Installation Guide"
        content = "How to install React"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "installation"
        
        title = "Node.js Setup Instructions"
        content = "Setting up Node.js development environment"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "installation"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_configuration(self, service):
        """Test document type classification for configuration"""
        title = "Webpack Configuration"
        content = "How to configure Webpack"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "configuration"
        
        title = "ESLint Config Setup"
        content = "Setting up ESLint configuration"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "configuration"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_troubleshooting(self, service):
        """Test document type classification for troubleshooting"""
        title = "React Troubleshooting"
        content = "Common React issues and solutions"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "troubleshooting"
        
        title = "Debug Common Issues"
        content = "Debugging common development issues"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "troubleshooting"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_changelog(self, service):
        """Test document type classification for changelog"""
        title = "React Changelog"
        content = "Changes in React versions"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "changelog"
        
        title = "Version Changes"
        content = "Changes in this version"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "changelog"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_examples(self, service):
        """Test document type classification for examples"""
        title = "React Examples"
        content = "Examples of React components"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "examples"
        
        title = "Vue.js Cookbook"
        content = "Cookbook of Vue.js recipes"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "examples"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_faq(self, service):
        """Test document type classification for FAQ"""
        title = "React FAQ"
        content = "Frequently asked questions about React"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "faq"
        
        title = "Common Questions"
        content = "Common questions and answers"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "faq"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_best_practices(self, service):
        """Test document type classification for best practices"""
        title = "React Best Practices"
        content = "Best practices for React development"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "best_practices"
        
        title = "Design Patterns"
        content = "Common design patterns in React"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "best_practices"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_blog(self, service):
        """Test document type classification for blog"""
        title = "React Blog Post"
        content = "Latest React blog post"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "blog"
        
        title = "Development Post"
        content = "Blog post about development"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "blog"
    
    @pytest.mark.asyncio
    async def test_document_type_classification_default(self, service):
        """Test document type classification default"""
        title = "Some Random Title"
        content = "Random content that doesn't match patterns"
        doc_type = await service._classify_document_type(title, content)
        assert doc_type == "documentation"
    
    @pytest.mark.asyncio
    async def test_quality_indicators_extraction(self, service):
        """Test quality indicators extraction"""
        search_result = self.create_search_result(
            title="High Quality Documentation",
            content="""# React Hooks Guide
            
React hooks are a powerful feature.

## useState Hook

```jsx
const [count, setCount] = useState(0);
```

## useEffect Hook

```jsx
useEffect(() => {
    // Side effects
}, []);
```

Learn more at [React Docs](https://reactjs.org).

### Advanced Topics

#### Custom Hooks
#### Hook Rules
#### Performance Optimization
""",
            url="https://context7.com/react/hooks"
        )
        
        indicators = await service._extract_quality_indicators(search_result)
        
        assert "has_code_examples" in indicators
        assert "has_links" in indicators
        assert "word_count" in indicators
        assert "char_count" in indicators
        assert "header_count" in indicators
        assert "relevance_score" in indicators
        assert "overall_score" in indicators
        
        # Check specific indicators
        assert indicators["has_code_examples"] is True
        assert indicators["has_links"] is True
        assert indicators["word_count"] > 0
        assert indicators["char_count"] > 0
        assert indicators["header_count"] > 0
        assert indicators["relevance_score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_quality_indicators_no_code_examples(self, service):
        """Test quality indicators when no code examples"""
        search_result = self.create_search_result(
            title="Basic Documentation",
            content="This is basic documentation without code examples",
            url="https://context7.com/basic"
        )
        
        indicators = await service._extract_quality_indicators(search_result)
        
        assert indicators["has_code_examples"] is False
        assert indicators["has_links"] is False
        assert indicators["word_count"] == 8
        assert indicators["char_count"] == 52
        assert indicators["header_count"] == 0
    
    @pytest.mark.asyncio
    async def test_language_detection_from_metadata(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value=None), \
             patch.object(service, '_classify_document_type', return_value="documentation"), \
             patch.object(service, '_extract_quality_indicators', return_value={}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document.language == "es"
    
    @pytest.mark.asyncio
    async def test_language_fallback_to_english(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value=None), \
             patch.object(service, '_classify_document_type', return_value="documentation"), \
             patch.object(service, '_extract_quality_indicators', return_value={}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document.language == "en"
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self, service, sample_intent):
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
        
        with patch.object(service, '_extract_version_from_content', return_value=None), \
             patch.object(service, '_classify_document_type', return_value="documentation"), \
             patch.object(service, '_extract_quality_indicators', return_value={}):
            
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            assert document.metadata == original_metadata
    
    @pytest.mark.asyncio
    async def test_error_handling_in_conversion(self, service, sample_intent):
        """Test error handling in search result conversion"""
        search_result = self.create_search_result(
            title="Error Test",
            content="Test content",
            url="https://context7.com/error/test",
            metadata={"owner": "test", "technology": "react"}
        )
        
        # Mock an error in version extraction
        with patch.object(service, '_extract_version_from_content', side_effect=Exception("Version error")):
            document = await service._convert_search_result_to_document(
                search_result, sample_intent
            )
            
            # Should return None on error
            assert document is None


async def main():
    """Run all metadata processing tests"""
    print("="*60)
    print("SUB-TASK A2: Context7 Metadata Processing Verification")
    print("="*60)
    
    # Initialize test class
    test_class = TestContext7MetadataProcessing()
    
    # Get service fixture
    service = test_class.service()
    sample_intent = test_class.sample_intent()
    
    tests_passed = 0
    tests_failed = 0
    
    test_methods = [
        test_class.test_context7_document_creation_basic,
        test_class.test_technology_extraction_from_metadata,
        test_class.test_technology_fallback_to_intent,
        test_class.test_owner_extraction_from_metadata,
        test_class.test_owner_fallback_to_unknown,
        test_class.test_version_extraction_from_content_various_patterns,
        test_class.test_document_type_classification_api,
        test_class.test_document_type_classification_guides,
        test_class.test_document_type_classification_getting_started,
        test_class.test_document_type_classification_installation,
        test_class.test_document_type_classification_configuration,
        test_class.test_document_type_classification_troubleshooting,
        test_class.test_document_type_classification_changelog,
        test_class.test_document_type_classification_examples,
        test_class.test_document_type_classification_faq,
        test_class.test_document_type_classification_best_practices,
        test_class.test_document_type_classification_blog,
        test_class.test_document_type_classification_default,
        test_class.test_quality_indicators_extraction,
        test_class.test_quality_indicators_no_code_examples,
        test_class.test_language_detection_from_metadata,
        test_class.test_language_fallback_to_english,
        test_class.test_metadata_preservation,
        test_class.test_error_handling_in_conversion
    ]
    
    for test_method in test_methods:
        try:
            test_name = test_method.__name__
            print(f"\n🔍 Running {test_name}...")
            
            # Run the test
            if 'sample_intent' in test_method.__code__.co_varnames:
                await test_method(service, sample_intent)
            else:
                await test_method(service)
            
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
    success = asyncio.run(main())
    exit(0 if success else 1)