#!/usr/bin/env python3
"""
SUB-TASK A1: TTL Calculation Logic Verification Tests
=====================================================

Comprehensive verification of Context7IngestionService TTL calculation logic.
Tests technology multipliers, document type adjustments, TTL bounds enforcement,
and edge cases.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.search.llm_query_analyzer import QueryIntent


class TestTTLCalculationLogic:
    """Comprehensive TTL calculation logic tests"""
    
    def service(self):
        """Create service with comprehensive TTL config"""
        config = TTLConfig(
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
                "node.js": 1.0,
                "express": 1.0,
                "tailwind": 1.0,
                "bootstrap": 0.8,
                "webpack": 1.2,
                "jest": 1.2,
                "cypress": 1.2
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
                "release_notes": 0.5
            }
        )
        
        return Context7IngestionService(
            llm_client=AsyncMock(),
            weaviate_client=AsyncMock(),
            db_manager=AsyncMock(),
            ttl_config=config
        )
    
    def sample_intent(self):
        """Sample query intent"""
        return QueryIntent(
            intent="documentation",
            technology="react",
            topics=["hooks"],
            doc_type="guide",
            user_level="intermediate"
        )
    
    async def test_technology_multipliers_react(self, service, sample_intent):
        """Test React technology multiplier (1.5)"""
        doc = Context7Document(
            content="React documentation content",
            title="React Guide",
            source_url="https://react.dev",
            technology="react",
            owner="facebook",
            doc_type="guide",
            quality_indicators={"overall_score": 0.8}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.0) = 67.5
            assert ttl == 67
    
    @pytest.mark.asyncio
    async def test_technology_multipliers_typescript(self, service, sample_intent):
        """Test TypeScript technology multiplier (2.0)"""
        doc = Context7Document(
            content="TypeScript documentation content",
            title="TypeScript Guide",
            source_url="https://typescriptlang.org",
            technology="typescript",
            owner="microsoft",
            doc_type="guide",
            quality_indicators={"overall_score": 0.8}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (2.0) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.0) = 90
            assert ttl == 90
    
    @pytest.mark.asyncio
    async def test_technology_multipliers_bootstrap(self, service, sample_intent):
        """Test Bootstrap technology multiplier (0.8)"""
        doc = Context7Document(
            content="Bootstrap documentation content",
            title="Bootstrap Guide",
            source_url="https://getbootstrap.com",
            technology="bootstrap",
            owner="twbs",
            doc_type="guide",
            quality_indicators={"overall_score": 0.8}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (0.8) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.0) = 36
            assert ttl == 36
    
    @pytest.mark.asyncio
    async def test_technology_multipliers_unknown(self, service, sample_intent):
        """Test unknown technology uses default multiplier (1.0)"""
        doc = Context7Document(
            content="Unknown technology content",
            title="Unknown Guide",
            source_url="https://unknown.com",
            technology="unknown-tech",
            owner="unknown",
            doc_type="guide",
            quality_indicators={"overall_score": 0.8}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (1.0) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.0) = 45
            assert ttl == 45
    
    @pytest.mark.asyncio
    async def test_document_type_api_reference(self, service, sample_intent):
        """Test API reference document type multiplier (2.5)"""
        doc = Context7Document(
            content="API reference documentation",
            title="API Reference",
            source_url="https://api.example.com",
            technology="react",
            owner="facebook",
            doc_type="reference",
            quality_indicators={"overall_score": 0.8}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (2.5) * content (1.0) * version (1.0) * quality (1.0) = 112.5
            # Should be capped at max_days (90)
            assert ttl == 90
    
    @pytest.mark.asyncio
    async def test_document_type_changelog(self, service, sample_intent):
        """Test changelog document type multiplier (0.5)"""
        doc = Context7Document(
            content="Version 2.0 changelog",
            title="Changelog",
            source_url="https://example.com/changelog",
            technology="react",
            owner="facebook",
            doc_type="changelog",
            quality_indicators={"overall_score": 0.8}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (0.5) * content (1.0) * version (1.0) * quality (1.0) = 22.5
            assert ttl == 22
    
    @pytest.mark.asyncio
    async def test_document_type_news(self, service, sample_intent):
        """Test news document type multiplier (0.3)"""
        doc = Context7Document(
            content="Latest news about React",
            title="React News",
            source_url="https://react.dev/news",
            technology="react",
            owner="facebook",
            doc_type="news",
            quality_indicators={"overall_score": 0.8}
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (0.3) * content (1.0) * version (1.0) * quality (1.0) = 13.5
            assert ttl == 13
    
    @pytest.mark.asyncio
    async def test_ttl_minimum_bound_enforcement(self, service, sample_intent):
        """Test TTL minimum bound enforcement"""
        doc = Context7Document(
            content="Very low TTL content",
            title="Low TTL Doc",
            source_url="https://example.com/low",
            technology="bootstrap",  # 0.8 multiplier
            owner="twbs",
            doc_type="news",  # 0.3 multiplier
            quality_indicators={"overall_score": 0.3}  # Low quality
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=0.5), \
             patch.object(service, '_analyze_version_for_ttl', return_value=0.6):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (0.8) * doc_type (0.3) * content (0.5) * version (0.6) * quality (0.7) = 1.512
            # Should be enforced to min_days (1)
            assert ttl == 1
    
    @pytest.mark.asyncio
    async def test_ttl_maximum_bound_enforcement(self, service, sample_intent):
        """Test TTL maximum bound enforcement"""
        doc = Context7Document(
            content="High quality comprehensive reference documentation",
            title="Complete Reference",
            source_url="https://example.com/ref",
            technology="typescript",  # 2.0 multiplier
            owner="microsoft",
            doc_type="reference",  # 2.5 multiplier
            quality_indicators={"overall_score": 0.95}  # High quality
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.5), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.3):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (2.0) * doc_type (2.5) * content (1.5) * version (1.3) * quality (1.2) = 702
            # Should be capped at max_days (90)
            assert ttl == 90
    
    @pytest.mark.asyncio
    async def test_quality_score_high_bonus(self, service, sample_intent):
        """Test quality score bonus for high quality content"""
        doc = Context7Document(
            content="High quality documentation",
            title="Quality Doc",
            source_url="https://example.com/quality",
            technology="react",
            owner="facebook",
            doc_type="guide",
            quality_indicators={"overall_score": 0.95}  # High quality
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.2) = 81
            assert ttl == 81
    
    @pytest.mark.asyncio
    async def test_quality_score_low_penalty(self, service, sample_intent):
        """Test quality score penalty for low quality content"""
        doc = Context7Document(
            content="Low quality documentation",
            title="Poor Doc",
            source_url="https://example.com/poor",
            technology="react",
            owner="facebook",
            doc_type="guide",
            quality_indicators={"overall_score": 0.4}  # Low quality
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (1.5) * content (1.0) * version (1.0) * quality (0.7) = 47.25
            assert ttl == 47
    
    @pytest.mark.asyncio
    async def test_content_analysis_deprecated_penalty(self, service):
        """Test content analysis penalty for deprecated content"""
        doc = Context7Document(
            content="This feature is deprecated and will be removed in the next version",
            title="Deprecated Feature",
            source_url="https://example.com/deprecated",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(doc)
        
        # Should get penalty for deprecated content
        assert multiplier == 0.5
    
    @pytest.mark.asyncio
    async def test_content_analysis_stable_bonus(self, service):
        """Test content analysis bonus for stable content"""
        doc = Context7Document(
            content="This is a stable production-ready API recommended for all users",
            title="Stable API",
            source_url="https://example.com/stable",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(doc)
        
        # Should get bonus for stable content
        assert multiplier == 1.5
    
    @pytest.mark.asyncio
    async def test_content_analysis_experimental_penalty(self, service):
        """Test content analysis penalty for experimental content"""
        doc = Context7Document(
            content="This is an experimental beta feature currently in preview",
            title="Experimental Feature",
            source_url="https://example.com/experimental",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(doc)
        
        # Should get penalty for experimental content
        assert multiplier == 0.7
    
    @pytest.mark.asyncio
    async def test_content_analysis_comprehensive_bonus(self, service):
        """Test content analysis bonus for comprehensive content"""
        doc = Context7Document(
            content="This is a complete and comprehensive guide with detailed explanations",
            title="Complete Guide",
            source_url="https://example.com/complete",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(doc)
        
        # Should get bonus for comprehensive content
        assert multiplier == 1.2
    
    @pytest.mark.asyncio
    async def test_content_analysis_length_bonus(self, service):
        """Test content analysis bonus for long content"""
        doc = Context7Document(
            content="X" * 15000,  # Very long content
            title="Long Document",
            source_url="https://example.com/long",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(doc)
        
        # Should get bonus for extensive content
        assert multiplier == 1.1
    
    @pytest.mark.asyncio
    async def test_content_analysis_length_penalty(self, service):
        """Test content analysis penalty for short content"""
        doc = Context7Document(
            content="X" * 500,  # Short content
            title="Short Document",
            source_url="https://example.com/short",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await service._analyze_content_for_ttl(doc)
        
        # Should get penalty for brief content
        assert multiplier == 0.9
    
    @pytest.mark.asyncio
    async def test_version_analysis_latest_bonus(self, service):
        """Test version analysis bonus for latest version"""
        doc = Context7Document(
            content="Documentation content",
            title="Latest Version",
            source_url="https://example.com/latest",
            technology="react",
            owner="facebook",
            version="latest"
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should get bonus for latest version
        assert multiplier == 1.3
    
    @pytest.mark.asyncio
    async def test_version_analysis_stable_bonus(self, service):
        """Test version analysis bonus for stable version"""
        doc = Context7Document(
            content="Documentation content",
            title="Stable Version",
            source_url="https://example.com/stable",
            technology="react",
            owner="facebook",
            version="stable"
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should get bonus for stable version
        assert multiplier == 1.3
    
    @pytest.mark.asyncio
    async def test_version_analysis_beta_penalty(self, service):
        """Test version analysis penalty for beta version"""
        doc = Context7Document(
            content="Documentation content",
            title="Beta Version",
            source_url="https://example.com/beta",
            technology="react",
            owner="facebook",
            version="v2.0.0-beta.1"
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should get penalty for beta version
        assert multiplier == 0.6
    
    @pytest.mark.asyncio
    async def test_version_analysis_alpha_penalty(self, service):
        """Test version analysis penalty for alpha version"""
        doc = Context7Document(
            content="Documentation content",
            title="Alpha Version",
            source_url="https://example.com/alpha",
            technology="react",
            owner="facebook",
            version="v3.0.0-alpha.2"
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should get penalty for alpha version
        assert multiplier == 0.6
    
    @pytest.mark.asyncio
    async def test_version_analysis_major_version_bonus(self, service):
        """Test version analysis bonus for major version"""
        doc = Context7Document(
            content="Documentation content",
            title="Major Version",
            source_url="https://example.com/major",
            technology="react",
            owner="facebook",
            version="v1.0.0"
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should get bonus for major version
        assert multiplier == 1.1
    
    @pytest.mark.asyncio
    async def test_version_analysis_mature_version_bonus(self, service):
        """Test version analysis bonus for mature version"""
        doc = Context7Document(
            content="Documentation content",
            title="Mature Version",
            source_url="https://example.com/mature",
            technology="react",
            owner="facebook",
            version="v5.2.1"
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should get bonus for mature version (major >= 3)
        assert multiplier == 1.2
    
    @pytest.mark.asyncio
    async def test_version_analysis_early_version_penalty(self, service):
        """Test version analysis penalty for early version"""
        doc = Context7Document(
            content="Documentation content",
            title="Early Version",
            source_url="https://example.com/early",
            technology="react",
            owner="facebook",
            version="v0.5.2"
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should get penalty for early version (major == 0)
        assert multiplier == 0.8
    
    @pytest.mark.asyncio
    async def test_version_analysis_no_version(self, service):
        """Test version analysis with no version"""
        doc = Context7Document(
            content="Documentation content",
            title="No Version",
            source_url="https://example.com/no-version",
            technology="react",
            owner="facebook",
            version=None
        )
        
        multiplier = await service._analyze_version_for_ttl(doc)
        
        # Should return default multiplier
        assert multiplier == 1.0
    
    @pytest.mark.asyncio
    async def test_ttl_calculation_error_handling(self, service, sample_intent):
        """Test TTL calculation error handling"""
        doc = Context7Document(
            content="Test content",
            title="Test Document",
            source_url="https://example.com/test",
            technology="react",
            owner="facebook",
            doc_type="guide",
            quality_indicators={"overall_score": 0.8}
        )
        
        # Mock an error in content analysis
        with patch.object(service, '_analyze_content_for_ttl', side_effect=Exception("Analysis error")):
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Should return default TTL on error
            assert ttl == service.ttl_config.default_days
    
    @pytest.mark.asyncio
    async def test_complex_ttl_calculation_scenario(self, service, sample_intent):
        """Test complex TTL calculation with multiple factors"""
        doc = Context7Document(
            content="This is a comprehensive stable API reference with detailed examples",
            title="Complete API Reference",
            source_url="https://example.com/complete-api",
            technology="typescript",  # 2.0 multiplier
            owner="microsoft",
            doc_type="reference",  # 2.5 multiplier
            version="v4.2.0",  # Mature version
            quality_indicators={"overall_score": 0.92}  # High quality
        )
        
        with patch.object(service, '_analyze_content_for_ttl', return_value=1.5), \
             patch.object(service, '_analyze_version_for_ttl', return_value=1.2):
            
            ttl = await service._calculate_intelligent_ttl(doc, sample_intent)
            
            # Base (30) * tech (2.0) * doc_type (2.5) * content (1.5) * version (1.2) * quality (1.2) = 648
            # Should be capped at max_days (90)
            assert ttl == 90


async def main():
    """Run all TTL calculation tests"""
    print("="*60)
    print("SUB-TASK A1: TTL Calculation Logic Verification")
    print("="*60)
    
    # Initialize test class
    test_class = TestTTLCalculationLogic()
    
    # Get service fixture
    service = test_class.service()
    sample_intent = test_class.sample_intent()
    
    tests_passed = 0
    tests_failed = 0
    
    test_methods = [
        test_class.test_technology_multipliers_react,
        test_class.test_technology_multipliers_typescript,
        test_class.test_technology_multipliers_bootstrap,
        test_class.test_technology_multipliers_unknown,
        test_class.test_document_type_api_reference,
        test_class.test_document_type_changelog,
        test_class.test_document_type_news,
        test_class.test_ttl_minimum_bound_enforcement,
        test_class.test_ttl_maximum_bound_enforcement,
        test_class.test_quality_score_high_bonus,
        test_class.test_quality_score_low_penalty,
        test_class.test_content_analysis_deprecated_penalty,
        test_class.test_content_analysis_stable_bonus,
        test_class.test_content_analysis_experimental_penalty,
        test_class.test_content_analysis_comprehensive_bonus,
        test_class.test_content_analysis_length_bonus,
        test_class.test_content_analysis_length_penalty,
        test_class.test_version_analysis_latest_bonus,
        test_class.test_version_analysis_stable_bonus,
        test_class.test_version_analysis_beta_penalty,
        test_class.test_version_analysis_alpha_penalty,
        test_class.test_version_analysis_major_version_bonus,
        test_class.test_version_analysis_mature_version_bonus,
        test_class.test_version_analysis_early_version_penalty,
        test_class.test_version_analysis_no_version,
        test_class.test_ttl_calculation_error_handling,
        test_class.test_complex_ttl_calculation_scenario
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
    print(f"SUB-TASK A1 RESULTS:")
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Success Rate: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")
    
    if tests_failed == 0:
        print("✅ ALL TTL CALCULATION TESTS PASSED")
        return True
    else:
        print(f"❌ {tests_failed} TTL CALCULATION TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)