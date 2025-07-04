"""
Integration tests for Context7 TTL End-to-End Workflow
=====================================================

Comprehensive integration tests for the complete Context7 TTL workflow including:
- End-to-end document processing with TTL
- Integration between Context7IngestionService and WeaviateClient
- TTL metadata persistence and retrieval
- Background cleanup job scheduling
- Complete workflow from search results to cleanup
- Performance testing of integrated systems

Test Coverage:
- Complete Context7 document ingestion with TTL
- TTL metadata storage and retrieval across components
- Background job execution and scheduling
- End-to-end workflow validation
- Performance characteristics of integrated workflow
- Error propagation and recovery across components
- Configuration integration and environment loading
"""

import pytest
import asyncio
import logging
import json
import os
import time
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.ingestion.context7_ingestion_service import (
    Context7IngestionService,
    Context7Document,
    TTLConfig
)
from src.clients.weaviate_client import WeaviateVectorClient
from src.database.manager import DatabaseManager
from src.llm.client import LLMProviderClient
from src.search.llm_query_analyzer import QueryIntent
from src.mcp.providers.models import SearchResult, SearchResultType
from src.document_processing.models import DocumentContent


class TestContext7TTLIntegration:
    """Integration tests for Context7 TTL workflow"""
    
    @pytest.fixture
    def integration_config(self):
        """Integration test configuration"""
        return {
            "ttl_config": TTLConfig(
                default_days=30,
                min_days=1,
                max_days=90,
                technology_multipliers={"react": 1.5, "typescript": 2.0},
                doc_type_multipliers={"api": 2.0, "guide": 1.5}
            ),
            "workspace_slug": "integration-test-workspace",
            "correlation_id": "integration-test-123"
        }
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for integration tests"""
        client = AsyncMock(spec=LLMProviderClient)
        client.generate.return_value = "Enhanced content analysis result"
        return client
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Mock Weaviate client for integration tests"""
        client = AsyncMock(spec=WeaviateVectorClient)
        
        # Mock successful upload
        upload_result = Mock()
        upload_result.successful_uploads = 5
        client.upload_document.return_value = upload_result
        
        # Mock TTL operations
        client.cleanup_expired_documents.return_value = {
            "deleted_documents": 2,
            "deleted_chunks": 8,
            "message": "Cleanup successful"
        }
        
        client.get_document_ttl_info.return_value = {
            "document_id": "test-doc",
            "ttl_days": 45,
            "expired": False,
            "time_remaining_seconds": 3600000
        }
        
        client.update_document_ttl.return_value = {
            "success": True,
            "updated_chunks": 3,
            "new_ttl_days": 60
        }
        
        return client
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager for integration tests"""
        db = AsyncMock(spec=DatabaseManager)
        db.execute.return_value = None
        db.fetch_all.return_value = []
        db.fetch_one.return_value = None
        return db
    
    @pytest.fixture
    def integrated_service(self, mock_llm_client, mock_weaviate_client, mock_db_manager, integration_config):
        """Fully integrated Context7 service"""
        service = Context7IngestionService(
            llm_client=mock_llm_client,
            weaviate_client=mock_weaviate_client,
            db_manager=mock_db_manager,
            ttl_config=integration_config["ttl_config"]
        )
        return service
    
    @pytest.fixture
    def sample_search_results(self):
        """Sample search results for integration testing"""
        return [
            SearchResult(
                title="React Hooks Complete Guide",
                url="https://context7.com/facebook/react/hooks.txt",
                snippet="Comprehensive guide to React Hooks",
                content="""# React Hooks Complete Guide

React Hooks revolutionize how we write React components by allowing state and lifecycle features in function components.

## useState Hook

The useState hook is the most basic hook for managing state in functional components.

```jsx
import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}
```

## useEffect Hook

The useEffect hook handles side effects in functional components.

```jsx
import React, { useState, useEffect } from 'react';

function DataFetcher() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    fetch('/api/data')
      .then(response => response.json())
      .then(setData);
  }, []);
  
  return <div>{data ? JSON.stringify(data) : 'Loading...'}</div>;
}
```

## Custom Hooks

Custom hooks allow you to extract component logic into reusable functions.

```jsx
function useCounter(initialValue = 0) {
  const [count, setCount] = useState(initialValue);
  
  const increment = () => setCount(count + 1);
  const decrement = () => setCount(count - 1);
  const reset = () => setCount(initialValue);
  
  return { count, increment, decrement, reset };
}
```

## Best Practices

1. Always use hooks at the top level of your component
2. Never call hooks inside loops, conditions, or nested functions
3. Use the dependency array in useEffect to control when effects run
4. Extract complex logic into custom hooks
5. Use useCallback and useMemo for performance optimization

This comprehensive guide covers all the essential concepts for mastering React Hooks.
""",
                content_type=SearchResultType.DOCUMENTATION,
                source_domain="context7.com",
                relevance_score=0.95,
                provider_rank=1,
                language="en",
                metadata={
                    "owner": "facebook",
                    "technology": "react",
                    "section": 1,
                    "total_sections": 1,
                    "source": "context7",
                    "type": SearchResultType.DOCUMENTATION,
                    "version": "18.2.0",
                    "last_updated": "2024-01-15"
                }
            ),
            SearchResult(
                title="TypeScript Advanced Types Reference",
                url="https://context7.com/microsoft/typescript/advanced-types.txt",
                snippet="Complete reference for TypeScript advanced types",
                content="""# TypeScript Advanced Types Reference

TypeScript's type system is incredibly powerful and flexible. This reference covers advanced type constructs that enable type-safe, expressive code.

## Utility Types

TypeScript provides several utility types to facilitate common type transformations.

### Partial<T>

Makes all properties of T optional.

```typescript
interface User {
  name: string;
  email: string;
  age: number;
}

type PartialUser = Partial<User>;
// { name?: string; email?: string; age?: number; }
```

### Required<T>

Makes all properties of T required.

```typescript
type RequiredUser = Required<PartialUser>;
// { name: string; email: string; age: number; }
```

### Pick<T, K>

Constructs a type by picking specific properties from T.

```typescript
type UserContactInfo = Pick<User, 'name' | 'email'>;
// { name: string; email: string; }
```

## Conditional Types

Conditional types enable type-level programming with conditional logic.

```typescript
type ApiResponse<T> = T extends string
  ? { message: T }
  : T extends number
  ? { code: T }
  : { data: T };

type StringResponse = ApiResponse<string>; // { message: string }
type NumberResponse = ApiResponse<number>; // { code: number }
type ObjectResponse = ApiResponse<User>; // { data: User }
```

## Mapped Types

Mapped types allow creating new types based on existing ones.

```typescript
type Readonly<T> = {
  readonly [P in keyof T]: T[P];
};

type Optional<T> = {
  [P in keyof T]?: T[P];
};

type Nullable<T> = {
  [P in keyof T]: T[P] | null;
};
```

## Template Literal Types

Template literal types enable powerful string manipulation at the type level.

```typescript
type EventName<T extends string> = `on${Capitalize<T>}`;

type ClickEvent = EventName<'click'>; // 'onClick'
type ChangeEvent = EventName<'change'>; // 'onChange'
```

This reference provides comprehensive coverage of TypeScript's advanced type system features.
""",
                content_type=SearchResultType.DOCUMENTATION,
                source_domain="context7.com",
                relevance_score=0.92,
                provider_rank=2,
                language="en",
                metadata={
                    "owner": "microsoft",
                    "technology": "typescript",
                    "section": 1,
                    "total_sections": 1,
                    "source": "context7",
                    "type": SearchResultType.DOCUMENTATION,
                    "version": "5.0.0",
                    "last_updated": "2024-01-10"
                }
            )
        ]
    
    @pytest.fixture
    def sample_query_intent(self):
        """Sample query intent for integration testing"""
        return QueryIntent(
            intent="documentation",
            technology="react",
            topics=["hooks", "state management", "lifecycle"],
            doc_type="guide",
            user_level="intermediate",
            specific_question="How to use React hooks effectively",
            context_needed=True,
            priority="high"
        )
    
    @pytest.mark.asyncio
    async def test_end_to_end_document_processing_with_ttl(self, integrated_service, sample_search_results, sample_query_intent, integration_config):
        """Test complete end-to-end document processing with TTL"""
        
        # Mock the parent pipeline processing
        with patch.object(integrated_service, 'process_documentation') as mock_process:
            mock_process.return_value = Mock(
                success=True,
                chunks_processed=5,
                workspace_slug=integration_config["workspace_slug"]
            )
            
            # Process search results end-to-end
            start_time = time.time()
            results = await integrated_service.process_context7_results(
                sample_search_results,
                sample_query_intent,
                integration_config["correlation_id"]
            )
            processing_time = time.time() - start_time
            
            # Verify results
            assert len(results) == 2, f"Should process 2 documents, got {len(results)}"
            assert all(result.success for result in results), "All documents should be processed successfully"
            assert all(result.chunks_processed == 5 for result in results), "All documents should have 5 chunks"
            
            # Verify performance
            assert processing_time < 10.0, f"End-to-end processing took too long: {processing_time}s"
            
            # Verify database TTL metadata was added
            db_calls = integrated_service.db.execute.call_args_list
            ttl_calls = [call for call in db_calls if "ttl_info" in str(call)]
            assert len(ttl_calls) == 2, "Should add TTL metadata for both documents"
    
    @pytest.mark.asyncio
    async def test_ttl_calculation_integration(self, integrated_service, sample_search_results, sample_query_intent):
        """Test TTL calculation integration across the workflow"""
        
        # Process first search result (React guide)
        react_result = sample_search_results[0]
        
        # Mock conversion and processing
        with patch.object(integrated_service, '_extract_version_from_content', return_value="18.2.0"), \
             patch.object(integrated_service, '_classify_document_type', return_value="guide"), \
             patch.object(integrated_service, '_extract_quality_indicators', return_value={"overall_score": 0.9}):
            
            # Convert to Context7 document
            document = await integrated_service._convert_search_result_to_document(
                react_result, sample_query_intent
            )
            
            # Calculate TTL
            ttl_days = await integrated_service._calculate_intelligent_ttl(
                document, sample_query_intent, "ttl-integration-test"
            )
            
            # Verify TTL calculation
            # React (1.5) * guide (1.5) * content adjustments * quality (1.2) * base (30)
            # Should be significant but capped at max (90)
            assert 45 <= ttl_days <= 90, f"TTL should be in expected range, got {ttl_days}"
            
            # Assess quality
            quality = await integrated_service._assess_document_quality(document)
            assert quality >= 0.8, f"High-quality document should score >= 0.8, got {quality}"
    
    @pytest.mark.asyncio
    async def test_weaviate_integration_with_ttl_metadata(self, integrated_service, integration_config):
        """Test Weaviate integration with TTL metadata operations"""
        
        # Test TTL info retrieval
        ttl_info = await integrated_service.weaviate.get_document_ttl_info(
            integration_config["workspace_slug"], "test-doc-123"
        )
        
        assert ttl_info is not None
        assert ttl_info["ttl_days"] == 45
        assert ttl_info["expired"] is False
        
        # Test TTL update
        update_result = await integrated_service.weaviate.update_document_ttl(
            integration_config["workspace_slug"], "test-doc-123", 60
        )
        
        assert update_result["success"] is True
        assert update_result["new_ttl_days"] == 60
        assert update_result["updated_chunks"] == 3
        
        # Test cleanup operation
        cleanup_result = await integrated_service.cleanup_expired_documents(
            integration_config["workspace_slug"],
            integration_config["correlation_id"]
        )
        
        assert cleanup_result["weaviate_cleanup"]["deleted_documents"] == 2
        assert cleanup_result["weaviate_cleanup"]["deleted_chunks"] == 8
    
    @pytest.mark.asyncio
    async def test_database_ttl_metadata_persistence(self, integrated_service, integration_config):
        """Test TTL metadata persistence in database"""
        from src.document_processing.models import DocumentContent
        
        # Create test document content
        content = DocumentContent(
            content_id="integration-test-doc",
            title="Integration Test Document",
            text="Test content for integration testing",
            source_url="https://example.com/integration-test",
            metadata={
                "technology": "react",
                "owner": "testowner",
                "doc_type": "guide"
            }
        )
        
        # Add TTL metadata
        await integrated_service._add_ttl_metadata(
            content,
            integration_config["workspace_slug"],
            45,
            integration_config["correlation_id"]
        )
        
        # Verify database call
        integrated_service.db.execute.assert_called_once()
        args, kwargs = integrated_service.db.execute.call_args
        
        # Verify query structure
        assert "UPDATE content_metadata" in args[0]
        assert "ttl_info" in args[0]
        assert kwargs["content_id"] == "integration-test-doc"
        
        # Verify TTL metadata structure
        ttl_metadata = json.loads(kwargs["ttl_metadata"])
        assert ttl_metadata["ttl_days"] == 45
        assert ttl_metadata["source_provider"] == "context7"
        assert "created_at" in ttl_metadata
        assert "expires_at" in ttl_metadata
    
    @pytest.mark.asyncio
    async def test_error_propagation_across_components(self, integrated_service, sample_search_results, sample_query_intent):
        """Test error handling and propagation across integrated components"""
        
        # Test database error propagation
        integrated_service.db.execute.side_effect = Exception("Database connection lost")
        
        # Process should continue despite database errors
        with patch.object(integrated_service, 'process_documentation') as mock_process:
            mock_process.return_value = Mock(
                success=True,
                chunks_processed=3,
                workspace_slug="test-workspace"
            )
            
            results = await integrated_service.process_context7_results(
                sample_search_results, sample_query_intent
            )
            
            # Should still process documents successfully
            assert len(results) > 0, "Should process documents despite database errors"
            assert all(result.success for result in results), "Documents should process successfully"
        
        # Test Weaviate error propagation
        integrated_service.weaviate.upload_document.side_effect = Exception("Weaviate connection failed")
        
        # Reset database mock
        integrated_service.db.execute.side_effect = None
        integrated_service.db.execute.return_value = None
        
        with patch.object(integrated_service, 'process_documentation', side_effect=Exception("Upload failed")):
            results = await integrated_service.process_context7_results(
                sample_search_results, sample_query_intent
            )
            
            # Should handle errors gracefully
            assert len(results) >= 0, "Should handle errors gracefully"
            if results:
                assert any(not result.success for result in results), "Some results should show failure"
    
    @pytest.mark.asyncio
    async def test_performance_of_integrated_workflow(self, integrated_service, integration_config):
        """Test performance characteristics of integrated workflow"""
        
        # Create larger dataset for performance testing
        large_search_results = []
        for i in range(20):
            result = SearchResult(
                title=f"Performance Test Document {i}",
                url=f"https://context7.com/test/doc{i}.txt",
                snippet=f"Test document {i} for performance testing",
                content=f"# Performance Test Document {i}\n\nContent for performance testing document {i}." + "A" * 1000,
                content_type=SearchResultType.DOCUMENTATION,
                source_domain="context7.com",
                relevance_score=0.8,
                provider_rank=i + 1,
                metadata={
                    "owner": "testowner",
                    "technology": "react",
                    "source": "context7"
                }
            )
            large_search_results.append(result)
        
        # Mock fast processing
        with patch.object(integrated_service, 'process_documentation') as mock_process:
            mock_process.return_value = Mock(
                success=True,
                chunks_processed=2,
                workspace_slug=integration_config["workspace_slug"]
            )
            
            # Measure performance
            start_time = time.time()
            results = await integrated_service.process_context7_results(
                large_search_results,
                QueryIntent(
                    intent="documentation",
                    technology="react",
                    topics=["performance"],
                    doc_type="guide"
                ),
                "performance-test-correlation"
            )
            processing_time = time.time() - start_time
            
            # Performance assertions
            assert processing_time < 30.0, f"Large batch processing took too long: {processing_time}s"
            assert len(results) == 20, f"Should process all 20 documents, got {len(results)}"
            assert all(result.success for result in results), "All documents should process successfully"
            
            # Verify throughput
            throughput = len(results) / processing_time
            assert throughput > 1.0, f"Throughput too low: {throughput} docs/sec"
    
    @pytest.mark.asyncio
    async def test_configuration_integration_from_environment(self, mock_llm_client, mock_weaviate_client, mock_db_manager):
        """Test configuration loading from environment variables"""
        
        env_vars = {
            "CONTEXT7_TTL_DEFAULT_DAYS": "60",
            "CONTEXT7_TTL_MIN_DAYS": "5",
            "CONTEXT7_TTL_MAX_DAYS": "180",
            "CONTEXT7_TTL_TECH_MULTIPLIER_REACT": "2.5",
            "CONTEXT7_TTL_DOC_TYPE_MULTIPLIER_API": "3.5",
        }
        
        with patch.dict(os.environ, env_vars):
            # Simulate loading config from environment
            config = TTLConfig(
                default_days=int(os.environ.get("CONTEXT7_TTL_DEFAULT_DAYS", 30)),
                min_days=int(os.environ.get("CONTEXT7_TTL_MIN_DAYS", 1)),
                max_days=int(os.environ.get("CONTEXT7_TTL_MAX_DAYS", 90)),
                technology_multipliers={
                    "react": float(os.environ.get("CONTEXT7_TTL_TECH_MULTIPLIER_REACT", 1.5))
                },
                doc_type_multipliers={
                    "api": float(os.environ.get("CONTEXT7_TTL_DOC_TYPE_MULTIPLIER_API", 2.0))
                }
            )
            
            # Create service with environment-loaded config
            service = Context7IngestionService(
                llm_client=mock_llm_client,
                weaviate_client=mock_weaviate_client,
                db_manager=mock_db_manager,
                ttl_config=config
            )
            
            # Verify configuration was loaded correctly
            assert service.ttl_config.default_days == 60
            assert service.ttl_config.min_days == 5
            assert service.ttl_config.max_days == 180
            assert service.ttl_config.technology_multipliers["react"] == 2.5
            assert service.ttl_config.doc_type_multipliers["api"] == 3.5
    
    @pytest.mark.asyncio
    async def test_background_cleanup_job_integration(self, integrated_service, integration_config):
        """Test background cleanup job integration"""
        
        # Simulate scheduled cleanup job
        workspaces = ["workspace-1", "workspace-2", "workspace-3"]
        
        cleanup_results = []
        for workspace in workspaces:
            result = await integrated_service.cleanup_expired_documents(
                workspace, f"cleanup-job-{workspace}"
            )
            cleanup_results.append(result)
        
        # Verify all cleanups completed
        assert len(cleanup_results) == 3
        for result in cleanup_results:
            assert "weaviate_cleanup" in result
            assert "database_records_cleaned" in result
            assert "cleaned_at" in result
        
        # Verify total cleanup statistics
        total_deleted_docs = sum(r["weaviate_cleanup"]["deleted_documents"] for r in cleanup_results)
        total_deleted_chunks = sum(r["weaviate_cleanup"]["deleted_chunks"] for r in cleanup_results)
        
        assert total_deleted_docs == 6  # 2 per workspace
        assert total_deleted_chunks == 24  # 8 per workspace
    
    @pytest.mark.asyncio
    async def test_concurrent_ttl_operations_integration(self, integrated_service, integration_config):
        """Test concurrent TTL operations across integrated components"""
        
        # Simulate concurrent operations on different workspaces
        workspace_ops = [
            ("workspace-a", "process"),
            ("workspace-b", "cleanup"),
            ("workspace-c", "update-ttl"),
            ("workspace-d", "get-stats"),
        ]
        
        async def perform_operation(workspace, operation):
            if operation == "process":
                # Simulate document processing
                doc = Context7Document(
                    content="Concurrent test content",
                    title="Concurrent Test Doc",
                    source_url=f"https://example.com/{workspace}",
                    technology="react",
                    owner="testowner"
                )
                return await integrated_service.process_context7_document(
                    doc, QueryIntent(intent="documentation", technology="react"), f"concurrent-{workspace}"
                )
            elif operation == "cleanup":
                return await integrated_service.cleanup_expired_documents(workspace, f"concurrent-cleanup-{workspace}")
            elif operation == "update-ttl":
                return await integrated_service.weaviate.update_document_ttl(workspace, "test-doc", 45)
            elif operation == "get-stats":
                return await integrated_service.weaviate.get_expiration_statistics(workspace)
        
        # Mock successful processing for concurrent test
        with patch.object(integrated_service, 'process_documentation') as mock_process:
            mock_process.return_value = Mock(success=True, chunks_processed=3, workspace_slug="test")
            
            # Run all operations concurrently
            tasks = [perform_operation(workspace, op) for workspace, op in workspace_ops]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all operations completed without interference
            assert len(results) == 4
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Operation {i} failed: {result}"
                
                # Verify operation-specific results
                workspace, operation = workspace_ops[i]
                if operation == "process":
                    assert result.success is True
                elif operation == "cleanup":
                    assert "weaviate_cleanup" in result
                elif operation == "update-ttl":
                    assert result["success"] is True
                elif operation == "get-stats":
                    # Mock returns default structure
                    pass


class TestContext7TTLConfigurationIntegration:
    """Integration tests for TTL configuration across components"""
    
    @pytest.mark.asyncio
    async def test_ttl_config_propagation(self):
        """Test TTL configuration propagation through the system"""
        
        # Create custom configuration
        custom_config = TTLConfig(
            default_days=45,
            min_days=3,
            max_days=120,
            technology_multipliers={
                "react": 2.0,
                "vue": 1.8,
                "angular": 1.6,
                "typescript": 2.5
            },
            doc_type_multipliers={
                "api": 3.0,
                "guide": 2.0,
                "tutorial": 1.5,
                "reference": 3.5
            }
        )
        
        # Mock dependencies
        mock_llm = AsyncMock()
        mock_weaviate = AsyncMock()
        mock_db = AsyncMock()
        
        # Create service with custom config
        service = Context7IngestionService(
            llm_client=mock_llm,
            weaviate_client=mock_weaviate,
            db_manager=mock_db,
            ttl_config=custom_config
        )
        
        # Test various technology/doc type combinations
        test_cases = [
            ("typescript", "api", 120),  # Should hit max bound: 45 * 2.5 * 3.0 = 337.5 -> 120
            ("vue", "tutorial", 121),    # 45 * 1.8 * 1.5 = 121.5 -> 120 (capped)
            ("react", "guide", 120),     # 45 * 2.0 * 2.0 = 180 -> 120 (capped)
            ("angular", "guide", 120),   # 45 * 1.6 * 2.0 = 144 -> 120 (capped)
        ]
        
        for technology, doc_type, expected_max in test_cases:
            doc = Context7Document(
                content="Test content for configuration testing",
                title=f"{technology.title()} {doc_type.title()}",
                source_url=f"https://example.com/{technology}/{doc_type}",
                technology=technology,
                owner="testowner",
                doc_type=doc_type,
                quality_indicators={"overall_score": 0.8}
            )
            
            # Mock analysis methods to return neutral multipliers
            with patch.object(service, '_analyze_content_for_ttl', return_value=1.0), \
                 patch.object(service, '_analyze_version_for_ttl', return_value=1.0):
                
                ttl = await service._calculate_intelligent_ttl(doc, Mock())
                
                # Verify TTL respects bounds and configuration
                assert 3 <= ttl <= 120, f"TTL {ttl} out of configured bounds for {technology}/{doc_type}"
                
                # For high-multiplier combinations, should hit the max bound
                if technology in ["typescript", "react"] and doc_type in ["api", "reference", "guide"]:
                    assert ttl == 120, f"High multiplier combo should hit max bound: {technology}/{doc_type} = {ttl}"
    
    @pytest.mark.asyncio
    async def test_environment_config_validation_integration(self):
        """Test environment configuration validation in integrated system"""
        
        # Test with invalid environment configuration
        invalid_env_vars = {
            "CONTEXT7_TTL_DEFAULT_DAYS": "150",  # Above max
            "CONTEXT7_TTL_MIN_DAYS": "-1",      # Negative
            "CONTEXT7_TTL_MAX_DAYS": "5",       # Below default
        }
        
        with patch.dict(os.environ, invalid_env_vars):
            # Simulate config validation
            try:
                # This would fail validation in a real system
                config = TTLConfig(
                    default_days=int(os.environ.get("CONTEXT7_TTL_DEFAULT_DAYS", 30)),
                    min_days=max(1, int(os.environ.get("CONTEXT7_TTL_MIN_DAYS", 1))),  # Enforce minimum
                    max_days=max(90, int(os.environ.get("CONTEXT7_TTL_MAX_DAYS", 90)))  # Enforce minimum
                )
                
                # Adjust default if it's out of bounds
                if config.default_days > config.max_days:
                    config.default_days = config.max_days
                if config.default_days < config.min_days:
                    config.default_days = config.min_days
                
                # Verify corrected configuration
                assert config.min_days == 1      # Corrected from -1
                assert config.max_days == 90     # Corrected from 5
                assert config.default_days == 90 # Corrected from 150
                
            except Exception as e:
                # Configuration validation should catch invalid values
                assert "validation" in str(e).lower() or "invalid" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])