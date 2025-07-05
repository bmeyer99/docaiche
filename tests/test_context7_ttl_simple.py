#!/usr/bin/env python3
"""
SUB-TASK A1: TTL Calculation Logic Verification Tests (Simplified)
==================================================================

Comprehensive verification of Context7IngestionService TTL calculation logic.
Tests technology multipliers, document type adjustments, TTL bounds enforcement,
and edge cases without pytest dependency.
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.search.llm_query_analyzer import QueryIntent


class TTLCalculationTests:
    """TTL calculation logic tests"""
    
    def __init__(self):
        # Create service with comprehensive TTL config
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
        
        self.service = Context7IngestionService(
            llm_client=AsyncMock(),
            weaviate_client=AsyncMock(),
            db_manager=AsyncMock(),
            ttl_config=config
        )
        
        self.sample_intent = QueryIntent(
            intent="documentation",
            technology="react",
            topics=["hooks"],
            doc_type="guide",
            user_level="intermediate"
        )
    
    async def test_react_technology_multiplier(self):
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
        
        with patch.object(self.service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(self.service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.0) = 67.5
            assert ttl == 67, f"Expected 67, got {ttl}"
    
    async def test_typescript_technology_multiplier(self):
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
        
        with patch.object(self.service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(self.service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Base (30) * tech (2.0) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.0) = 90
            assert ttl == 90, f"Expected 90, got {ttl}"
    
    async def test_bootstrap_technology_multiplier(self):
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
        
        with patch.object(self.service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(self.service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Base (30) * tech (0.8) * doc_type (1.5) * content (1.0) * version (1.0) * quality (1.0) = 36
            assert ttl == 36, f"Expected 36, got {ttl}"
    
    async def test_api_reference_document_type(self):
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
        
        with patch.object(self.service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(self.service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (2.5) * content (1.0) * version (1.0) * quality (1.0) = 112.5
            # Should be capped at max_days (90)
            assert ttl == 90, f"Expected 90 (capped), got {ttl}"
    
    async def test_changelog_document_type(self):
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
        
        with patch.object(self.service, '_analyze_content_for_ttl', return_value=1.0), \
             patch.object(self.service, '_analyze_version_for_ttl', return_value=1.0):
            
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Base (30) * tech (1.5) * doc_type (0.5) * content (1.0) * version (1.0) * quality (1.0) = 22.5
            assert ttl == 22, f"Expected 22, got {ttl}"
    
    async def test_ttl_minimum_bound_enforcement(self):
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
        
        with patch.object(self.service, '_analyze_content_for_ttl', return_value=0.5), \
             patch.object(self.service, '_analyze_version_for_ttl', return_value=0.6):
            
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Should be enforced to min_days (1)
            assert ttl >= 1, f"Expected TTL >= 1, got {ttl}"
    
    async def test_ttl_maximum_bound_enforcement(self):
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
        
        with patch.object(self.service, '_analyze_content_for_ttl', return_value=1.5), \
             patch.object(self.service, '_analyze_version_for_ttl', return_value=1.3):
            
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Should be capped at max_days (90)
            assert ttl <= 90, f"Expected TTL <= 90, got {ttl}"
    
    async def test_content_analysis_deprecated_penalty(self):
        """Test content analysis penalty for deprecated content"""
        doc = Context7Document(
            content="This feature is deprecated and will be removed in the next version",
            title="Deprecated Feature",
            source_url="https://example.com/deprecated",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await self.service._analyze_content_for_ttl(doc)
        
        # Should get penalty for deprecated content
        assert multiplier == 0.5, f"Expected 0.5, got {multiplier}"
    
    async def test_content_analysis_stable_bonus(self):
        """Test content analysis bonus for stable content"""
        doc = Context7Document(
            content="This is a stable production-ready API recommended for all users",
            title="Stable API",
            source_url="https://example.com/stable",
            technology="react",
            owner="facebook"
        )
        
        multiplier = await self.service._analyze_content_for_ttl(doc)
        
        # Should get bonus for stable content
        assert multiplier == 1.5, f"Expected 1.5, got {multiplier}"
    
    async def test_version_analysis_latest_bonus(self):
        """Test version analysis bonus for latest version"""
        doc = Context7Document(
            content="Documentation content",
            title="Latest Version",
            source_url="https://example.com/latest",
            technology="react",
            owner="facebook",
            version="latest"
        )
        
        multiplier = await self.service._analyze_version_for_ttl(doc)
        
        # Should get bonus for latest version
        assert multiplier == 1.3, f"Expected 1.3, got {multiplier}"
    
    async def test_version_analysis_beta_penalty(self):
        """Test version analysis penalty for beta version"""
        doc = Context7Document(
            content="Documentation content",
            title="Beta Version",
            source_url="https://example.com/beta",
            technology="react",
            owner="facebook",
            version="v2.0.0-beta.1"
        )
        
        multiplier = await self.service._analyze_version_for_ttl(doc)
        
        # Should get penalty for beta version
        assert multiplier == 0.6, f"Expected 0.6, got {multiplier}"
    
    async def test_error_handling(self):
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
        with patch.object(self.service, '_analyze_content_for_ttl', side_effect=Exception("Analysis error")):
            ttl = await self.service._calculate_intelligent_ttl(doc, self.sample_intent)
            
            # Should return default TTL on error
            assert ttl == self.service.ttl_config.default_days, f"Expected {self.service.ttl_config.default_days}, got {ttl}"


async def main():
    """Run all TTL calculation tests"""
    print("="*60)
    print("SUB-TASK A1: TTL Calculation Logic Verification")
    print("="*60)
    
    tests = TTLCalculationTests()
    
    test_methods = [
        ("React Technology Multiplier", tests.test_react_technology_multiplier),
        ("TypeScript Technology Multiplier", tests.test_typescript_technology_multiplier),
        ("Bootstrap Technology Multiplier", tests.test_bootstrap_technology_multiplier),
        ("API Reference Document Type", tests.test_api_reference_document_type),
        ("Changelog Document Type", tests.test_changelog_document_type),
        ("TTL Minimum Bound Enforcement", tests.test_ttl_minimum_bound_enforcement),
        ("TTL Maximum Bound Enforcement", tests.test_ttl_maximum_bound_enforcement),
        ("Content Analysis Deprecated Penalty", tests.test_content_analysis_deprecated_penalty),
        ("Content Analysis Stable Bonus", tests.test_content_analysis_stable_bonus),
        ("Version Analysis Latest Bonus", tests.test_version_analysis_latest_bonus),
        ("Version Analysis Beta Penalty", tests.test_version_analysis_beta_penalty),
        ("Error Handling", tests.test_error_handling)
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
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test runner failed: {e}")
        exit(1)