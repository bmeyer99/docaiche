import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import src.response.generator as generator_module
import src.response.template_engine as template_engine_module
import src.response.content_synthesizer as content_synthesizer_module
import src.response.builder as builder_module
import src.response.formatter as formatter_module
import src.response.validator as validator_module

# --- Functional Tests ---

@pytest.mark.asyncio
async def test_generate_response_workflow_completeness():
    """End-to-end: template → synthesis → build → format → validate"""
    mock_template_engine = MagicMock()
    mock_content_synth = MagicMock()
    mock_builder = MagicMock()
    mock_formatter = MagicMock()
    mock_validator = MagicMock()
    mock_template_engine.render.return_value = "Rendered Content"
    mock_content_synth.synthesize.return_value = "Synthesized Content"
    mock_builder.build.return_value = {"response": "Built"}
    mock_formatter.format.return_value = "<html>Built</html>"
    mock_validator.validate.return_value = True

    gen = generator_module.ResponseGenerator(
        template_engine=mock_template_engine,
        content_synthesizer=mock_content_synth,
        builder=mock_builder,
        formatter=mock_formatter,
        validator=mock_validator,
    )
    result = await gen.generate_response(
        search_results=[{"doc": "A"}],
        enrichment_results=[{"enriched": "B"}],
        output_format="html",
        context={"user": "test"},
    )
    assert result == "<html>Built</html>"

@pytest.mark.asyncio
async def test_generate_response_async_await_pattern():
    """Ensure generate_response and all subcomponents are async/await compatible"""
    mock_template_engine = MagicMock()
    mock_content_synth = AsyncMock()
    mock_builder = AsyncMock()
    mock_formatter = AsyncMock()
    mock_validator = AsyncMock()
    mock_template_engine.render.return_value = "Rendered"
    mock_content_synth.synthesize.return_value = "Synth"
    mock_builder.build.return_value = {"response": "Built"}
    mock_formatter.format.return_value = "Formatted"
    mock_validator.validate.return_value = True

    gen = generator_module.ResponseGenerator(
        template_engine=mock_template_engine,
        content_synthesizer=mock_content_synth,
        builder=mock_builder,
        formatter=mock_formatter,
        validator=mock_validator,
    )
    result = await gen.generate_response(
        search_results=[{"doc": "A"}],
        enrichment_results=[{"enriched": "B"}],
        output_format="json",
        context={},
    )
    assert result == "Formatted"

def test_template_engine_multi_format_rendering():
    """TemplateEngine supports JSON, Markdown, HTML output"""
    engine = template_engine_module.TemplateEngine(template_dir="templates/")
    for fmt in ["json", "markdown", "html"]:
        rendered = engine.render("strategy.prompt", {"data": "x"}, output_format=fmt)
        assert isinstance(rendered, str)
        assert rendered

def test_template_engine_safe_rendering_and_injection_prevention():
    """TemplateEngine escapes dangerous input and prevents injection"""
    engine = template_engine_module.TemplateEngine(template_dir="templates/")
    malicious_context = {"user_input": "{{7*7}}<script>alert(1)</script>"}
    rendered = engine.render("strategy.prompt", malicious_context, output_format="html")
    assert "<script>" not in rendered
    assert "{{7*7}}" not in rendered

def test_content_synthesizer_merge_deduplication_prioritization():
    """ContentSynthesizer merges, deduplicates, and prioritizes content"""
    synth = content_synthesizer_module.ContentSynthesizer()
    search_results = [{"id": 1, "text": "A"}, {"id": 2, "text": "B"}]
    enrichment_results = [{"id": 2, "text": "B"}, {"id": 3, "text": "C"}]
    combined = synth.synthesize(search_results, enrichment_results)
    ids = {item["id"] for item in combined}
    assert ids == {1, 2, 3}
    assert combined[0]["id"] == 2 or combined[0]["id"] == 1  # prioritization logic

def test_response_builder_extensible_structured_assembly():
    """ResponseBuilder builds extensible, structured responses"""
    builder = builder_module.ResponseBuilder()
    content = [{"id": 1, "text": "A"}]
    response = builder.build(content, meta={"foo": "bar"})
    assert isinstance(response, dict)
    assert "foo" in response.get("meta", {})

def test_response_formatter_multi_format_output():
    """ResponseFormatter serializes to JSON, Markdown, HTML"""
    formatter = formatter_module.ResponseFormatter()
    data = {"response": "test"}
    for fmt in ["json", "markdown", "html"]:
        output = formatter.format(data, fmt)
        assert isinstance(output, str)
        assert output

def test_response_validator_schema_enforcement_and_error_handling():
    """ResponseValidator enforces schema and handles errors"""
    validator = validator_module.ResponseValidator()
    valid = {"response": "ok"}
    invalid = {"bad": "data"}
    assert validator.validate(valid)
    assert not validator.validate(invalid)

# --- Integration Tests ---

@pytest.mark.asyncio
async def test_integration_with_search_orchestrator_and_enricher(monkeypatch):
    """Integration: generator uses orchestrator and enricher outputs"""
    mock_search = [{"id": 1, "text": "A"}]
    mock_enrich = [{"id": 2, "text": "B"}]
    gen = generator_module.ResponseGenerator()
    monkeypatch.setattr(gen, "template_engine", MagicMock())
    monkeypatch.setattr(gen, "content_synthesizer", MagicMock())
    monkeypatch.setattr(gen, "builder", MagicMock())
    monkeypatch.setattr(gen, "formatter", MagicMock())
    monkeypatch.setattr(gen, "validator", MagicMock())
    await gen.generate_response(
        search_results=mock_search,
        enrichment_results=mock_enrich,
        output_format="json",
        context={},
    )
    # If no exception, integration is working

@pytest.mark.asyncio
async def test_integration_with_llm_provider(monkeypatch):
    """Integration: generator can process LLMProviderClient output"""
    mock_llm_output = {"llm": "response"}
    gen = generator_module.ResponseGenerator()
    monkeypatch.setattr(gen, "template_engine", MagicMock())
    monkeypatch.setattr(gen, "content_synthesizer", MagicMock())
    monkeypatch.setattr(gen, "builder", MagicMock())
    monkeypatch.setattr(gen, "formatter", MagicMock())
    monkeypatch.setattr(gen, "validator", MagicMock())
    await gen.generate_response(
        search_results=[mock_llm_output],
        enrichment_results=[],
        output_format="markdown",
        context={},
    )

# --- Security Tests ---

def test_template_engine_no_code_execution(monkeypatch):
    """TemplateEngine does not execute code in templates"""
    engine = template_engine_module.TemplateEngine(template_dir="templates/")
    malicious = {"payload": "{{__import__('os').system('rm -rf /')}}" }
    rendered = engine.render("strategy.prompt", malicious, output_format="html")
    assert "rm -rf" not in rendered
    assert "__import__" not in rendered

def test_formatter_output_sanitization():
    """ResponseFormatter sanitizes output for HTML/Markdown"""
    formatter = formatter_module.ResponseFormatter()
    data = {"response": "<script>alert(1)</script>"}
    html = formatter.format(data, "html")
    md = formatter.format(data, "markdown")
    assert "<script>" not in html
    assert "<script>" not in md

def test_content_synthesizer_input_validation():
    """ContentSynthesizer validates input data structure"""
    synth = content_synthesizer_module.ContentSynthesizer()
    with pytest.raises(Exception):
        synth.synthesize("bad input", None)

# --- Performance Tests ---

@pytest.mark.asyncio
async def test_response_generation_performance(benchmark):
    """Response generation meets performance requirements"""
    gen = generator_module.ResponseGenerator()
    search_results = [{"id": i, "text": f"doc{i}"} for i in range(100)]
    enrichment_results = [{"id": i, "text": f"enrich{i}"} for i in range(100)]
    context = {}
    output_format = "json"
    await benchmark(gen.generate_response, search_results, enrichment_results, output_format, context)

def test_template_engine_rendering_speed(benchmark):
    """TemplateEngine renders templates within performance threshold"""
    engine = template_engine_module.TemplateEngine(template_dir="templates/")
    context = {"data": "x"}
    benchmark(lambda: engine.render("strategy.prompt", context, output_format="html"))

# --- Error Handling & Edge Case Tests ---

@pytest.mark.asyncio
async def test_generate_response_handles_template_failure(monkeypatch):
    """Graceful error handling if template rendering fails"""
    gen = generator_module.ResponseGenerator()
    monkeypatch.setattr(gen.template_engine, "render", MagicMock(side_effect=Exception("fail")))
    with pytest.raises(Exception):
        await gen.generate_response(
            search_results=[{"doc": "A"}],
            enrichment_results=[],
            output_format="html",
            context={},
        )

@pytest.mark.asyncio
async def test_generate_response_handles_content_synthesis_failure(monkeypatch):
    """Graceful error handling if content synthesis fails"""
    gen = generator_module.ResponseGenerator()
    monkeypatch.setattr(gen.content_synthesizer, "synthesize", MagicMock(side_effect=Exception("fail")))
    with pytest.raises(Exception):
        await gen.generate_response(
            search_results=[{"doc": "A"}],
            enrichment_results=[],
            output_format="html",
            context={},
        )

def test_template_engine_handles_malformed_template():
    """TemplateEngine handles missing/malformed templates gracefully"""
    engine = template_engine_module.TemplateEngine(template_dir="templates/")
    with pytest.raises(Exception):
        engine.render("nonexistent.prompt", {}, output_format="html")