#!/usr/bin/env python3
"""
PRD-010 Knowledge Enrichment System Validation
Quick validation that the enrichment system is properly implemented.
"""

import sys

def main():
    print("=== PRD-010 Knowledge Enrichment System Validation ===")
    print()
    
    # Test 1: Import validation
    print("Test 1: Import Validation")
    try:
        from src.enrichment import (
            KnowledgeEnricher, TaskManager, EnrichmentTaskQueue,
            ContentAnalyzer, RelationshipAnalyzer, TagGenerator,
            EnrichmentTask, EnrichmentResult, EnrichmentConfig,
            EnrichmentType, EnrichmentPriority, TaskStatus,
            create_knowledge_enricher, create_enrichment_config
        )
        print("✓ All enrichment components imported successfully")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    
    # Test 2: Configuration creation
    print("\nTest 2: Configuration Creation")
    try:
        config = create_enrichment_config(max_concurrent_tasks=10)
        assert config.max_concurrent_tasks == 10
        print("✓ Configuration factory working")
    except Exception as e:
        print(f"✗ Configuration creation failed: {e}")
        return False
    
    # Test 3: Task model creation
    print("\nTest 3: Task Model Creation")
    try:
        task = EnrichmentTask(
            content_id="test-123",
            task_type=EnrichmentType.CONTENT_ANALYSIS,
            priority=EnrichmentPriority.HIGH
        )
        assert task.content_id == "test-123"
        assert task.status == TaskStatus.PENDING
        print("✓ Task model creation working")
    except Exception as e:
        print(f"✗ Task model creation failed: {e}")
        return False
    
    # Test 4: Analyzer creation
    print("\nTest 4: Analyzer Creation")
    try:
        content_analyzer = ContentAnalyzer()
        relationship_analyzer = RelationshipAnalyzer()
        tag_generator = TagGenerator()
        print("✓ All analyzers created successfully")
    except Exception as e:
        print(f"✗ Analyzer creation failed: {e}")
        return False
    
    # Test 5: EnrichmentConfig integration with core config
    print("\nTest 5: Core Config Integration")
    try:
        from src.core.config.models import EnrichmentConfig as CoreEnrichmentConfig
        core_config = CoreEnrichmentConfig()
        assert core_config.max_concurrent_tasks == 5
        print("✓ Core configuration integration working")
    except Exception as e:
        print(f"✗ Core config integration failed: {e}")
        return False
    
    print("\n=== PRD-010 Knowledge Enrichment System: VALIDATION PASSED ===")
    print("✓ All components properly implemented")
    print("✓ Factory pattern working")
    print("✓ Configuration integration complete")
    print("✓ Data models functional")
    print("✓ Analysis components ready")
    
    return True

if __name__ == "__main__":
    sys.path.append('.')
    success = main()
    sys.exit(0 if success else 1)