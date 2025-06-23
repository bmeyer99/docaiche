"""
Unit Tests for LLM JSON Parser - PRD-005 LLM-010
Comprehensive test suite for JSON parsing logic with mock provider responses

Tests JSON extraction from various LLM response formats, error scenarios,
and validation against Pydantic model schemas as specified in PRD-005.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock

from src.llm.json_parser import (
    JSONParser, 
    JSONParsingError, 
    JSONValidationError,
    parse_llm_response
)
from src.llm.models import EvaluationResult, EnrichmentStrategy, QualityAssessment, RepositoryTarget


class TestJSONParser:
    """Test cases for JSONParser class functionality."""
    
    def test_extract_plain_json(self):
        """Test extraction of plain JSON from LLM response."""
        response = '''
        {
          "model_version": "1.0.0",
          "sufficiency_score": 0.8,
          "confidence": 0.9,
          "missing_aspects": ["examples", "error handling"],
          "should_enrich": true,
          "reasoning": "The results provide good coverage but lack practical examples.",
          "created_at": "2024-01-15T10:30:00Z"
        }
        '''
        
        result = JSONParser.extract_and_parse(response, EvaluationResult)
        
        assert isinstance(result, EvaluationResult)
        assert result.model_version == "1.0.0"
        assert result.sufficiency_score == 0.8
        assert result.confidence == 0.9
        assert result.missing_aspects == ["examples", "error handling"]
        assert result.should_enrich == True
        assert "practical examples" in result.reasoning
    
    def test_extract_markdown_wrapped_json(self):
        """Test extraction of JSON wrapped in markdown code blocks."""
        response = '''
        Here's my analysis of the search results:
        
        ```json
        {
          "model_version": "1.0.0",
          "relevance_score": 0.7,
          "quality_score": 0.8,
          "should_store": true,
          "content_type": "tutorial",
          "confidence": 0.85,
          "created_at": "2024-01-15T10:30:00Z"
        }
        ```
        
        This assessment considers the tutorial's completeness and accuracy.
        '''
        
        result = JSONParser.extract_and_parse(response, QualityAssessment)
        
        assert isinstance(result, QualityAssessment)
        assert result.relevance_score == 0.7
        assert result.quality_score == 0.8
        assert result.should_store == True
        assert result.content_type == "tutorial"
        assert result.confidence == 0.85
    
    def test_extract_json_with_explanatory_text(self):
        """Test extraction of JSON surrounded by explanatory text."""
        response = '''
        Based on my analysis, I recommend the following enrichment strategy:
        
        {
          "model_version": "1.0.0",
          "target_repositories": [
            {
              "model_version": "1.0.0",
              "owner": "fastapi",
              "repo": "fastapi",
              "path": "docs/tutorial",
              "priority": 0.9
            }
          ],
          "search_queries": ["FastAPI middleware examples", "async middleware patterns"],
          "priority_sources": ["github", "official_docs"],
          "estimated_value": 0.8,
          "created_at": "2024-01-15T10:30:00Z"
        }
        
        This strategy focuses on high-value official documentation.
        '''
        
        result = JSONParser.extract_and_parse(response, EnrichmentStrategy)
        
        assert isinstance(result, EnrichmentStrategy)
        assert len(result.target_repositories) == 1
        assert result.target_repositories[0].owner == "fastapi"
        assert result.target_repositories[0].repo == "fastapi"
        assert "FastAPI middleware examples" in result.search_queries
        assert result.priority_sources == ["github", "official_docs"]
        assert result.estimated_value == 0.8
    
    def test_extract_json_with_trailing_commas(self):
        """Test parsing JSON with trailing commas (common LLM error)."""
        response = '''
        {
          "model_version": "1.0.0",
          "sufficiency_score": 0.6,
          "confidence": 0.7,
          "missing_aspects": ["performance", "security",],
          "should_enrich": true,
          "reasoning": "More details needed on security practices.",
          "created_at": "2024-01-15T10:30:00Z",
        }
        '''
        
        result = JSONParser.extract_and_parse(response, EvaluationResult)
        
        assert isinstance(result, EvaluationResult)
        assert result.sufficiency_score == 0.6
        assert result.missing_aspects == ["performance", "security"]
    
    def test_extract_json_with_unquoted_keys(self):
        """Test parsing JSON with unquoted keys (another common LLM error)."""
        response = '''
        {
          model_version: "1.0.0",
          relevance_score: 0.9,
          quality_score: 0.8,
          should_store: true,
          content_type: "reference",
          confidence: 0.9,
          created_at: "2024-01-15T10:30:00Z"
        }
        '''
        
        result = JSONParser.extract_and_parse(response, QualityAssessment)
        
        assert isinstance(result, QualityAssessment)
        assert result.relevance_score == 0.9
        assert result.content_type == "reference"
    
    def test_extract_json_with_missing_closing_brace(self):
        """Test parsing JSON with missing closing brace."""
        response = '''
        {
          "model_version": "1.0.0",
          "sufficiency_score": 0.5,
          "confidence": 0.6,
          "missing_aspects": ["documentation"],
          "should_enrich": false,
          "reasoning": "Sufficient information available.",
          "created_at": "2024-01-15T10:30:00Z"
        '''
        
        result = JSONParser.extract_and_parse(response, EvaluationResult)
        
        assert isinstance(result, EvaluationResult)
        assert result.sufficiency_score == 0.5
        assert result.should_enrich == False
    
    def test_empty_response_error(self):
        """Test error handling for empty responses."""
        with pytest.raises(JSONParsingError, match="Empty or whitespace-only response"):
            JSONParser.extract_and_parse("", EvaluationResult)
        
        with pytest.raises(JSONParsingError, match="Empty or whitespace-only response"):
            JSONParser.extract_and_parse("   \n  ", EvaluationResult)
    
    def test_no_json_found_error(self):
        """Test error handling when no JSON structure is found."""
        response = "This is just plain text with no JSON structure at all."
        
        with pytest.raises(JSONParsingError, match="No valid JSON structure found"):
            JSONParser.extract_and_parse(response, EvaluationResult)
    
    def test_invalid_json_syntax_error(self):
        """Test error handling for invalid JSON syntax."""
        response = '''
        {
          "model_version": "1.0.0",
          "sufficiency_score": "invalid_number",
          "confidence": 0.8,
          "missing_aspects": [unclosed string,
          "should_enrich": true
        '''
        
        with pytest.raises(JSONParsingError, match="Failed to parse JSON"):
            JSONParser.extract_and_parse(response, EvaluationResult)
    
    def test_validation_error_missing_required_field(self):
        """Test validation error for missing required fields."""
        response = '''
        {
          "model_version": "1.0.0",
          "confidence": 0.8,
          "missing_aspects": [],
          "should_enrich": true,
          "reasoning": "Missing sufficiency_score field"
        }
        '''
        
        with pytest.raises(JSONValidationError, match="JSON doesn't match expected schema"):
            JSONParser.extract_and_parse(response, EvaluationResult)
    
    def test_validation_error_invalid_field_type(self):
        """Test validation error for invalid field types."""
        response = '''
        {
          "model_version": "1.0.0",
          "sufficiency_score": "not_a_number",
          "confidence": 0.8,
          "missing_aspects": [],
          "should_enrich": true,
          "reasoning": "Score should be float",
          "created_at": "2024-01-15T10:30:00Z"
        }
        '''
        
        with pytest.raises(JSONValidationError, match="JSON doesn't match expected schema"):
            JSONParser.extract_and_parse(response, EvaluationResult)
    
    def test_validation_error_invalid_enum_value(self):
        """Test validation error for invalid enum values."""
        response = '''
        {
          "model_version": "1.0.0",
          "relevance_score": 0.8,
          "quality_score": 0.7,
          "should_store": true,
          "content_type": "invalid_type",
          "confidence": 0.9,
          "created_at": "2024-01-15T10:30:00Z"
        }
        '''
        
        with pytest.raises(JSONValidationError, match="JSON doesn't match expected schema"):
            JSONParser.extract_and_parse(response, QualityAssessment)
    
    def test_validation_error_out_of_range_values(self):
        """Test validation error for values outside allowed ranges."""
        response = '''
        {
          "model_version": "1.0.0",
          "sufficiency_score": 1.5,
          "confidence": -0.1,
          "missing_aspects": [],
          "should_enrich": false,
          "reasoning": "Scores out of valid range",
          "created_at": "2024-01-15T10:30:00Z"
        }
        '''
        
        with pytest.raises(JSONValidationError, match="JSON doesn't match expected schema"):
            JSONParser.extract_and_parse(response, EvaluationResult)
    
    def test_complex_nested_structure(self):
        """Test parsing complex nested JSON structures."""
        response = '''
        ```json
        {
          "model_version": "1.0.0",
          "target_repositories": [
            {
              "model_version": "1.0.0",
              "owner": "microsoft",
              "repo": "fastapi",
              "path": "docs/advanced",
              "priority": 0.9
            },
            {
              "model_version": "1.0.0", 
              "owner": "tiangolo",
              "repo": "fastapi",
              "path": "tutorial",
              "priority": 0.8
            }
          ],
          "search_queries": ["advanced fastapi", "dependency injection", "middleware"],
          "priority_sources": ["github", "official_docs", "web"],
          "estimated_value": 0.85,
          "created_at": "2024-01-15T10:30:00Z"
        }
        ```
        '''
        
        result = JSONParser.extract_and_parse(response, EnrichmentStrategy)
        
        assert isinstance(result, EnrichmentStrategy)
        assert len(result.target_repositories) == 2
        assert result.target_repositories[0].owner == "microsoft"
        assert result.target_repositories[1].owner == "tiangolo"
        assert len(result.search_queries) == 3
        assert "dependency injection" in result.search_queries
        assert result.priority_sources == ["github", "official_docs", "web"]
    
    def test_convenience_function(self):
        """Test the convenience parse_llm_response function."""
        response = '''
        {
          "model_version": "1.0.0",
          "relevance_score": 0.9,
          "quality_score": 0.8,
          "should_store": true,
          "content_type": "guide",
          "confidence": 0.95,
          "created_at": "2024-01-15T10:30:00Z"
        }
        '''
        
        result = parse_llm_response(response, QualityAssessment)
        
        assert isinstance(result, QualityAssessment)
        assert result.content_type == "guide"
        assert result.confidence == 0.95


class TestJSONParserInternals:
    """Test internal methods of JSONParser for thorough coverage."""
    
    def test_extract_variables(self):
        """Test variable extraction from template content."""
        variables = JSONParser._extract_variables("Hello {name}, your score is {score}")
        assert variables == {"name", "score"}
        
        # Test with format specifiers
        variables = JSONParser._extract_variables("Value: {value:0.2f} at {timestamp:%Y-%m-%d}")
        assert variables == {"value", "timestamp"}
        
        # Test with no variables
        variables = JSONParser._extract_variables("No variables here")
        assert variables == set()
    
    def test_is_valid_json_structure(self):
        """Test JSON structure validation."""
        assert JSONParser._is_valid_json_structure('{"key": "value"}')
        assert JSONParser._is_valid_json_structure('{"nested": {"key": "value"}}')
        assert not JSONParser._is_valid_json_structure('{"unclosed": true')
        assert not JSONParser._is_valid_json_structure('not json at all')
        assert not JSONParser._is_valid_json_structure('')
    
    def test_fix_trailing_commas(self):
        """Test trailing comma removal."""
        fixed = JSONParser._fix_trailing_commas('{"key": "value",}')
        assert fixed == '{"key": "value"}'
        
        fixed = JSONParser._fix_trailing_commas('{"array": [1, 2, 3,]}')
        assert fixed == '{"array": [1, 2, 3]}'
    
    def test_fix_missing_quotes(self):
        """Test missing quote addition for keys."""
        fixed = JSONParser._fix_missing_quotes('{key: "value"}')
        assert '"key"' in fixed
        
        fixed = JSONParser._fix_missing_quotes('{multiple_keys: "value", other_key: "value2"}')
        assert '"multiple_keys"' in fixed and '"other_key"' in fixed
    
    def test_fix_missing_braces(self):
        """Test missing brace addition."""
        fixed = JSONParser._fix_missing_braces('{"key": "value"')
        assert fixed == '{"key": "value"}'
        
        fixed = JSONParser._fix_missing_braces('{"nested": {"key": "value"')
        assert fixed == '{"nested": {"key": "value"}}'


class TestMockProviderResponses:
    """Test parsing responses that simulate real LLM provider outputs."""
    
    def test_ollama_style_response(self):
        """Test parsing Ollama-style verbose response."""
        response = '''
        I'll analyze these search results for you.
        
        Looking at the provided information, I can see that the results cover the basic concepts but are missing some important practical details.
        
        Here's my structured evaluation:
        
        ```
        {
          "model_version": "1.0.0",
          "sufficiency_score": 0.65,
          "confidence": 0.8,
          "missing_aspects": [
            "practical examples",
            "error handling patterns",
            "performance considerations"
          ],
          "should_enrich": true,
          "reasoning": "While the basic concepts are covered, the results lack practical implementation examples and best practices that would be valuable for developers.",
          "created_at": "2024-01-15T10:30:00Z"
        }
        ```
        
        This evaluation considers both the completeness and practical utility of the information.
        '''
        
        result = JSONParser.extract_and_parse(response, EvaluationResult)
        assert result.sufficiency_score == 0.65
        assert "practical examples" in result.missing_aspects
        assert result.should_enrich == True
    
    def test_openai_style_response(self):
        """Test parsing OpenAI-style structured response."""
        response = '''
        Based on the content analysis, here is my quality assessment:
        
        ```json
        {
          "model_version": "1.0.0",
          "relevance_score": 0.92,
          "quality_score": 0.88,
          "should_store": true,
          "content_type": "tutorial",
          "confidence": 0.91,
          "created_at": "2024-01-15T10:30:00Z"
        }
        ```
        
        The content demonstrates high relevance to the query context and maintains good quality standards throughout.
        '''
        
        result = JSONParser.extract_and_parse(response, QualityAssessment)
        assert result.relevance_score == 0.92
        assert result.quality_score == 0.88
        assert result.content_type == "tutorial"
    
    def test_malformed_llm_response_recovery(self):
        """Test recovery from common LLM formatting issues."""
        response = '''
        I'll provide the enrichment strategy:
        
        {
          model_version: "1.0.0",
          target_repositories: [
            {
              model_version: "1.0.0",
              owner: "fastapi",
              repo: "fastapi", 
              path: "docs",
              priority: 0.9,
            }
          ],
          search_queries: ["fastapi tutorial", "async patterns",],
          priority_sources: ["github", "official_docs"],
          estimated_value: 0.75,
          created_at: "2024-01-15T10:30:00Z",
        '''
        
        # Should successfully parse despite missing quotes and trailing commas
        result = JSONParser.extract_and_parse(response, EnrichmentStrategy)
        assert len(result.target_repositories) == 1
        assert result.target_repositories[0].owner == "fastapi"
        assert "fastapi tutorial" in result.search_queries


# Integration test with all model types
class TestModelIntegration:
    """Integration tests with all supported model types."""
    
    @pytest.mark.parametrize("model_class,sample_response", [
        (EvaluationResult, {
            "model_version": "1.0.0",
            "sufficiency_score": 0.7,
            "confidence": 0.8,
            "missing_aspects": ["examples"],
            "should_enrich": True,
            "reasoning": "Need more examples",
            "created_at": "2024-01-15T10:30:00Z"
        }),
        (QualityAssessment, {
            "model_version": "1.0.0", 
            "relevance_score": 0.9,
            "quality_score": 0.8,
            "should_store": True,
            "content_type": "reference",
            "confidence": 0.85,
            "created_at": "2024-01-15T10:30:00Z"
        }),
        (EnrichmentStrategy, {
            "model_version": "1.0.0",
            "target_repositories": [],
            "search_queries": ["test query"],
            "priority_sources": ["github"],
            "estimated_value": 0.6,
            "created_at": "2024-01-15T10:30:00Z"
        })
    ])
    def test_all_model_types(self, model_class, sample_response):
        """Test parsing for all supported model types."""
        response_json = json.dumps(sample_response)
        result = JSONParser.extract_and_parse(response_json, model_class)
        
        assert isinstance(result, model_class)
        assert result.model_version == "1.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])