import pytest
from types import SimpleNamespace

from src.response.generator import ResponseGenerator
from src.response.template_engine import TemplateEngine
from src.response.builder import ResponseBuilder
from src.response.formatter import ResponseFormatter
from src.response.validator import ResponseValidator
from src.response.content_synthesizer import ContentSynthesizer

# --- Interface Compliance ---

def test_response_generator_signature():
    gen = ResponseGenerator()
    assert hasattr(gen, "generate")
    assert callable(gen.generate)
    assert "content_synthesizer" in gen.__init__.__code__.co_varnames

def test_template_engine_render_signature():
    engine = TemplateEngine()
    assert hasattr(engine, "render")
    assert callable(engine.render)
    params = engine.render.__code__.co_varnames
    assert params[:3] == ("template_name", "context", "output_format")

def test_response_builder_signature():
    builder = ResponseBuilder()
    assert hasattr(builder, "build")
    params = builder.build.__code__.co_varnames
    assert "meta" in params
    assert "metadata" not in params

def test_response_formatter_signature():
    formatter = ResponseFormatter()
    assert hasattr(formatter, "format")
    assert callable(formatter.format)

def test_response_validator_signature():
    validator = ResponseValidator()
    assert hasattr(validator, "validate")
    assert callable(validator.validate)

def test_content_synthesizer_signature():
    synth = ContentSynthesizer()
    assert hasattr(synth, "synthesize")
    assert callable(synth.synthesize)

# --- Constructor Compatibility ---

def test_response_generator_default_and_custom_constructor():
    default_gen = ResponseGenerator()
    custom_synth = ContentSynthesizer()
    custom_gen = ResponseGenerator(content_synthesizer=custom_synth)
    assert isinstance(default_gen, ResponseGenerator)
    assert isinstance(custom_gen, ResponseGenerator)
    assert custom_gen.content_synthesizer is custom_synth

# --- Template Rendering ---

@pytest.mark.parametrize("output_format", ["json", "html", "markdown"])
def test_template_engine_render_formats(output_format):
    engine = TemplateEngine()
    template_name = "test_template"
    context = {"key": "value"}
    result = engine.render(template_name, context, output_format)
    assert isinstance(result, str)
    assert result.strip() != ""

# --- Response Building ---

def test_response_builder_meta_parameter():
    builder = ResponseBuilder()
    data = {"foo": "bar"}
    meta = {"source": "test"}
    response = builder.build(data=data, meta=meta)
    assert "meta" in response
    assert response["meta"] == meta

# --- Response Formatting ---

@pytest.mark.parametrize("fmt,data", [
    ("json", {"foo": "bar"}),
    ("html", "<div>foo</div>"),
    ("markdown", "# Title"),
])
def test_response_formatter_valid_output(fmt, data):
    formatter = ResponseFormatter()
    result = formatter.format(data, fmt)
    assert isinstance(result, str)
    assert result.strip() != ""

# --- Response Validation ---

def test_response_validator_valid_and_invalid():
    validator = ResponseValidator()
    valid = {"data": {"foo": "bar"}, "meta": {"ok": True}}
    invalid = {"data": None}
    assert validator.validate(valid) is True
    assert validator.validate(invalid) is False
    with pytest.raises(Exception):
        validator.validate(None)

# --- Content Synthesis ---

def test_content_synthesizer_input_validation_and_merge():
    synth = ContentSynthesizer()
    valid_inputs = [{"text": "A"}, {"text": "B"}]
    result = synth.synthesize(valid_inputs)
    assert isinstance(result, dict)
    assert "text" in result
    with pytest.raises(ValueError):
        synth.synthesize(None)
    with pytest.raises(ValueError):
        synth.synthesize([{"bad": "input"}])

# --- Workflow Integration ---

def test_response_generation_workflow(monkeypatch):
    # Mock SearchOrchestrator and KnowledgeEnricher outputs
    search_result = {"results": [{"id": 1, "text": "foo"}]}
    enriched = {"enriched": True, "details": "bar"}
    # Synthesize content
    synth = ContentSynthesizer()
    synthesized = synth.synthesize([search_result, enriched])
    # Build response
    builder = ResponseBuilder()
    response = builder.build(data=synthesized, meta={"workflow": "test"})
    # Format response
    formatter = ResponseFormatter()
    formatted = formatter.format(response, "json")
    # Validate response
    validator = ResponseValidator()
    assert validator.validate(response) is True
    assert isinstance(formatted, str)
    assert formatted.strip() != ""

# --- Security Assessment ---

def test_template_engine_injection_prevention():
    engine = TemplateEngine()
    template_name = "test_template"
    context = {"user_input": "{{7*7}}<script>alert(1)</script>"}
    output = engine.render(template_name, context, "html")
    assert "<script>" not in output
    assert "{{7*7}}" not in output

def test_content_synthesizer_input_sanitization():
    synth = ContentSynthesizer()
    malicious = [{"text": "<img src=x onerror=alert(1)>"}]
    result = synth.synthesize(malicious)
    assert "<img" not in result["text"]
    assert "onerror" not in result["text"]

# --- Performance Benchmarks ---

import time

def test_response_generation_performance():
    gen = ResponseGenerator()
    start = time.time()
    for _ in range(10):
        data = [{"text": f"item {_}"}]
        response = gen.generate(data)
        assert response
    elapsed = time.time() - start
    assert elapsed < 2.0  # 10 responses in under 2 seconds