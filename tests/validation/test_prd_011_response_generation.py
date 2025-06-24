import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.response.generator import ResponseGenerator
from src.response.template_engine import TemplateEngine
from src.response.content_synthesizer import ContentSynthesizer
from src.response.builder import ResponseBuilder
from src.response.formatter import ResponseFormatter
from src.response.validator import ResponseValidator
from src.response.exceptions import ResponseGenerationError, TemplateNotFoundError

@pytest.fixture
def mock_dependencies():
    """Provides a standard set of mocked dependencies for the ResponseGenerator."""
    return {
        "builder": MagicMock(spec=ResponseBuilder),
        "template_engine": MagicMock(spec=TemplateEngine),
        "content_synthesizer": MagicMock(spec=ContentSynthesizer),
        "formatter": MagicMock(spec=ResponseFormatter),
        "validator": MagicMock(spec=ResponseValidator),
    }

@pytest.mark.asyncio
async def test_successful_generation_workflow(mock_dependencies):
    """
    Tests the complete, successful workflow from end to end with correct async handling.
    """
    # Arrange
    mock_dependencies["content_synthesizer"].synthesize.return_value = [{"id": 1, "text": "Synthesized"}]
    mock_dependencies["builder"].build.return_value = {"content": [{"id": 1, "text": "Synthesized"}], "meta": {}}
    
    # Mock the async render method
    async def mock_render(*args, **kwargs):
        return "Rendered Content"
    mock_dependencies["template_engine"].render = AsyncMock(side_effect=mock_render)

    mock_dependencies["validator"].validate.return_value = True
    mock_dependencies["formatter"].format.return_value = "Final Formatted Response"

    generator = ResponseGenerator(**mock_dependencies)

    # Act
    result = await generator.generate_response(
        search_results=[{"id": 1, "text": "Original"}],
        enrichment_results=[],
        query="test query"
    )

    # Assert
    assert result == "Final Formatted Response"
    mock_dependencies["content_synthesizer"].synthesize.assert_called_once()
    mock_dependencies["template_engine"].render.assert_awaited_once()
    mock_dependencies["validator"].validate.assert_called_once()
    mock_dependencies["formatter"].format.assert_called_once()

@pytest.mark.asyncio
async def test_validation_failure_stops_workflow(mock_dependencies):
    """
    Ensures that if the validator returns False, a ResponseGenerationError is raised.
    """
    # Arrange
    mock_dependencies["validator"].validate.return_value = False
    mock_dependencies["template_engine"].render = AsyncMock(return_value="Rendered Content")
    generator = ResponseGenerator(**mock_dependencies)

    # Act & Assert
    with pytest.raises(ResponseGenerationError, match="Response validation failed"):
        await generator.generate_response(search_results=[])

def test_synthesizer_handles_none_and_deduplicates():
    """
    Tests that the ContentSynthesizer correctly handles None inputs and deduplicates results.
    """
    # Arrange
    synthesizer = ContentSynthesizer()
    search = [{"id": 1, "text": "A"}, {"id": 2, "text": "B"}]
    enrich = [{"id": 2, "text": "B"}, {"id": 3, "text": "C"}]

    # Act
    result = synthesizer.synthesize(search, enrich)
    
    # Assert
    assert len(result) == 3
    assert {"id": 1, "text": "A"} in result
    assert {"id": 2, "text": "B"} in result
    assert {"id": 3, "text": "C"} in result
    
    # Test with None inputs
    assert synthesizer.synthesize(None, None) == []
    assert synthesizer.synthesize(search, None) == search

def test_validator_enforces_schema(tmp_path):
    """
    Tests that the ResponseValidator correctly enforces a schema.
    """
    # Arrange
    validator = ResponseValidator()
    schema = {"content": list, "meta": dict}
    
    # Act & Assert
    assert validator.validate({"content": [], "meta": {}}, schema) == True
    assert validator.validate({"content": "not a list", "meta": {}}, schema) == False
    assert validator.validate({"content": []}, schema) == False # Missing meta
    assert validator.validate({}, schema) == False

@pytest.mark.asyncio
async def test_template_engine_loads_and_renders(tmp_path):
    """
    Tests that the TemplateEngine can load a template and render it.
    """
    # Arrange
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "test.prompt").write_text("Hello, {name}!")
    
    engine = TemplateEngine(template_dir=str(template_dir))
    
    # Act
    rendered = await engine.render("test", {"name": "World"})
    
    # Assert
    assert rendered == "Hello, World!"

@pytest.mark.asyncio
async def test_template_not_found_raises_correct_exception(tmp_path):
    """
    Ensures TemplateNotFoundError is raised for missing templates.
    """
    # Arrange
    engine = TemplateEngine(template_dir=str(tmp_path))

    # Act & Assert
    with pytest.raises(TemplateNotFoundError):
        await engine.render("nonexistent", {})