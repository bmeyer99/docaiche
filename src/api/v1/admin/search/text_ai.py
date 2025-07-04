"""
Text AI Configuration API Endpoints
====================================

LLM integration and prompt management endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
import logging
import re

from .models import (
    TextAIModelConfig,
    TextAIStatus,
    PromptTemplate,
    PromptListResponse,
    PromptUpdateRequest,
    PromptTestRequest,
    PromptEnhanceRequest,
    APIResponse
)
from src.database.manager import create_database_manager
from src.database.prompt_repository import PromptTemplateRepository
from src.mcp.text_ai.prompts import PromptType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/text-ai", tags=["text-ai"])


# Dependency injection for database and repository
async def get_db_manager():
    """Get database manager instance."""
    db_manager = await create_database_manager()
    try:
        yield db_manager
    finally:
        await db_manager.disconnect()


async def get_prompt_repository(db_manager = Depends(get_db_manager)):
    """Get prompt repository instance."""
    repository = PromptTemplateRepository(db_manager)
    # Initialize default templates if needed
    await repository.initialize_default_templates()
    return repository


# Placeholder for dependency injection
async def get_text_ai_service():
    """Get Text AI service instance."""
    # TODO: Implement in Phase 2
    pass


@router.get("/status", response_model=TextAIStatus)
async def get_text_ai_status():
    """
    Get Text AI service status and health.
    
    Returns:
    - Connection status to LLM provider
    - Current model configuration
    - Service availability
    - Usage statistics for the day
    - Error information if any
    """
    try:
        # TODO: Phase 2 - Check actual LLM connection
        return TextAIStatus(
            connected=True,
            provider="openai",
            model="gpt-4",
            available=True,
            last_check=datetime.utcnow(),
            error=None,
            usage_today={
                "requests": 1250,
                "tokens": 450000,
                "cost_usd": 13.50
            }
        )
    except Exception as e:
        logger.error(f"Failed to get Text AI status: {e}")
        return TextAIStatus(
            connected=False,
            provider="unknown",
            model="unknown",
            available=False,
            last_check=datetime.utcnow(),
            error=str(e)
        )


@router.get("/model", response_model=TextAIModelConfig)
async def get_text_ai_model_config():
    """
    Get current Text AI model configuration.
    
    Returns model settings including:
    - Provider (OpenAI, Anthropic, etc.)
    - Model name and version
    - Temperature and token limits
    - Custom parameters
    - Timeout settings
    """
    try:
        # TODO: Phase 2 - Load from configuration
        return TextAIModelConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-...",  # Masked in response
            base_url=None,
            temperature=0.3,
            max_tokens=2000,
            timeout_seconds=30.0,
            custom_parameters={}
        )
    except Exception as e:
        logger.error(f"Failed to get model config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/model", response_model=APIResponse)
async def update_text_ai_model_config(
    config: TextAIModelConfig = Body(...)
):
    """
    Update Text AI model configuration.
    
    Updates LLM settings and validates:
    - API key authentication
    - Model availability
    - Parameter ranges
    - Connection to provider
    """
    try:
        # TODO: Phase 2 - Implement model config update
        # 1. Validate configuration
        # 2. Test connection with new settings
        # 3. Save configuration
        # 4. Reinitialize LLM client
        
        return APIResponse(
            success=True,
            message="Text AI model configuration updated successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update model config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Prompt management endpoints

@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts(
    prompt_type: Optional[str] = Query(None),
    active_only: bool = Query(False),
    repository: PromptTemplateRepository = Depends(get_prompt_repository)
):
    """
    List all prompt templates with versions.
    
    Returns all configured prompts including:
    - Template content
    - Variable definitions
    - Version information
    - Performance metrics
    - Active status
    
    Supports filtering by:
    - Prompt type (query_analysis, result_evaluation, etc.)
    - Active status
    """
    try:
        # Get all prompts from database
        db_prompts = await repository.get_all_prompts(active_only=active_only)
        
        # Filter by prompt type if specified
        if prompt_type:
            db_prompts = [p for p in db_prompts if p["prompt_type"] == prompt_type]
        
        # Convert to response model
        prompts = []
        for db_prompt in db_prompts:
            metadata = db_prompt.get("metadata", {})
            
            # Map prompt type to friendly name
            prompt_type_enum = db_prompt["prompt_type"]
            friendly_names = {
                "query_understanding": "Query Understanding",
                "result_relevance": "Result Relevance Evaluation",
                "query_refinement": "Query Refinement",
                "external_search_decision": "External Search Decision",
                "external_search_query": "External Search Query Generation",
                "content_extraction": "Content Extraction",
                "response_format": "Response Formatting",
                "learning_opportunities": "Learning Opportunities Analysis",
                "provider_selection": "Provider Selection",
                "failure_analysis": "Failure Analysis"
            }
            
            prompt = PromptTemplate(
                id=db_prompt["id"],
                name=friendly_names.get(prompt_type_enum, prompt_type_enum),
                type=prompt_type_enum,
                version=db_prompt["version"],
                template=db_prompt["content"],
                variables=metadata.get("required_variables", []),
                active=metadata.get("active", True),
                performance_metrics=metadata.get("performance_metrics", {
                    "avg_latency_ms": 0,
                    "success_rate": 0.0
                }),
                last_updated=datetime.fromisoformat(db_prompt["updated_at"]) if db_prompt.get("updated_at") else datetime.utcnow()
            )
            prompts.append(prompt)
        
        return PromptListResponse(
            prompts=prompts,
            total=len(prompts)
        )
    except Exception as e:
        logger.error(f"Failed to list prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{prompt_type}", response_model=PromptTemplate)
async def get_prompt(
    prompt_type: str = Path(...),
    version: Optional[str] = Query(None),
    repository: PromptTemplateRepository = Depends(get_prompt_repository)
):
    """Get a specific prompt template by type with full details."""
    try:
        # Validate prompt type
        if prompt_type not in [pt.value for pt in PromptType]:
            raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")
        
        # Get prompt from database
        db_prompt = await repository.get_prompt_by_type(prompt_type, version)
        
        if not db_prompt:
            raise HTTPException(status_code=404, detail=f"Prompt type '{prompt_type}' not found")
        
        metadata = db_prompt.get("metadata", {})
        
        # Map prompt type to friendly name
        friendly_names = {
            "query_understanding": "Query Understanding",
            "result_relevance": "Result Relevance Evaluation",
            "query_refinement": "Query Refinement",
            "external_search_decision": "External Search Decision",
            "external_search_query": "External Search Query Generation",
            "content_extraction": "Content Extraction",
            "response_format": "Response Formatting",
            "learning_opportunities": "Learning Opportunities Analysis",
            "provider_selection": "Provider Selection",
            "failure_analysis": "Failure Analysis"
        }
        
        return PromptTemplate(
            id=db_prompt["id"],
            name=friendly_names.get(prompt_type, prompt_type),
            type=prompt_type,
            version=db_prompt["version"],
            template=db_prompt["content"],
            variables=metadata.get("required_variables", []),
            active=metadata.get("active", True),
            performance_metrics=metadata.get("performance_metrics", {
                "avg_latency_ms": 0,
                "success_rate": 0.0
            }),
            last_updated=datetime.fromisoformat(db_prompt["updated_at"]) if db_prompt.get("updated_at") else datetime.utcnow()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/prompts/{prompt_type}", response_model=APIResponse)
async def update_prompt(
    prompt_type: str = Path(...),
    request: PromptUpdateRequest = Body(...),
    repository: PromptTemplateRepository = Depends(get_prompt_repository)
):
    """
    Update a prompt template.
    
    Creates a new version of the prompt with:
    - Template content changes
    - Variable updates
    - Version incrementing
    - Optional activation
    
    Previous versions are preserved for rollback.
    """
    try:
        # Validate prompt type
        if prompt_type not in [pt.value for pt in PromptType]:
            raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")
        
        # Validate template syntax (check for balanced braces)
        if request.template.count('{') != request.template.count('}'):
            raise ValueError("Invalid template syntax: unbalanced braces")
        
        # Prepare metadata
        metadata = {
            "active": request.active if hasattr(request, 'active') else True,
            "notes": request.notes if hasattr(request, 'notes') else "",
            "performance_metrics": request.performance_metrics if hasattr(request, 'performance_metrics') else {}
        }
        
        # Update the prompt (creates new version)
        updated_prompt = await repository.update_prompt(
            prompt_type=prompt_type,
            content=request.template,
            metadata=metadata
        )
        
        return APIResponse(
            success=True,
            message="Prompt updated successfully",
            data={"new_version": updated_prompt["version"], "id": updated_prompt["id"]}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{prompt_type}/versions")
async def get_prompt_versions(
    prompt_type: str = Path(...),
    repository: PromptTemplateRepository = Depends(get_prompt_repository)
):
    """
    Get version history for a prompt.
    
    Returns all versions with:
    - Version numbers
    - Change timestamps
    - Change authors
    - Performance metrics
    - Active status
    """
    try:
        # Validate prompt type
        if prompt_type not in [pt.value for pt in PromptType]:
            raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")
        
        # Get all versions from database
        versions = await repository.get_prompt_versions(prompt_type)
        
        # Format response
        version_history = []
        for i, version in enumerate(versions):
            metadata = version.get("metadata", {})
            
            # Determine what changed (compare with previous version if exists)
            changes = "Initial version"
            if i < len(versions) - 1:
                changes = f"Updated from version {versions[i+1]['version']}"
            
            version_history.append({
                "version": version["version"],
                "created_at": version["created_at"],
                "created_by": metadata.get("created_by", "system"),
                "active": metadata.get("active", True),
                "changes": metadata.get("notes", changes),
                "performance_metrics": metadata.get("performance_metrics", {})
            })
        
        return version_history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prompt versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompts/{prompt_id}/test", response_model=Dict[str, Any])
async def test_prompt(
    prompt_id: str = Path(...),
    request: PromptTestRequest = Body(...)
):
    """
    Test a prompt with sample data.
    
    Executes the prompt with provided test data and returns:
    - Rendered prompt text
    - LLM response
    - Execution time
    - Token usage
    - Comparison results if multiple versions tested
    """
    try:
        # TODO: Phase 2 - Implement prompt testing
        return {
            "prompt_id": prompt_id,
            "version": "1.0.0",
            "rendered_prompt": "Analyze the following query: \"test query\"...",
            "response": {
                "intent": "information_seeking",
                "domain": "general",
                "entities": ["test", "query"]
            },
            "execution_time_ms": 450,
            "tokens_used": 125
        }
    except Exception as e:
        logger.error(f"Failed to test prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompts/{prompt_id}/enhance", response_model=APIResponse)
async def enhance_prompt(
    prompt_id: str = Path(...),
    request: PromptEnhanceRequest = Body(...)
):
    """
    Enhance a prompt using AI assistance.
    
    Uses AI to improve the prompt based on:
    - Optimization goals (clarity, accuracy, efficiency)
    - Example inputs and outputs
    - Performance metrics
    
    Creates a new version with the enhanced prompt.
    """
    # This endpoint is deprecated in favor of the type-based enhancement endpoint
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. Please use POST /prompts/{prompt_type}/enhance instead."
    )


@router.post("/prompts/{prompt_type}/enhance", response_model=APIResponse)
async def enhance_prompt_by_type(
    prompt_type: str = Path(...),
    repository: PromptTemplateRepository = Depends(get_prompt_repository),
    db_manager = Depends(get_db_manager)
):
    """
    Enhance a prompt template using the current TextAI provider.
    
    This endpoint:
    - Gets the current prompt template for the specified type
    - Uses the configured TextAI provider to enhance the prompt
    - Creates a new version with the enhanced prompt
    
    The enhancement considers:
    - The specific decision point context
    - System type and purpose
    - Clarity and efficiency improvements
    - Structured output requirements
    """
    try:
        # Validate prompt type
        if prompt_type not in [pt.value for pt in PromptType]:
            raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")
        
        # Get current prompt template
        db_prompt = await repository.get_prompt_by_type(prompt_type)
        if not db_prompt:
            raise HTTPException(status_code=404, detail=f"Prompt type '{prompt_type}' not found")
        
        # Get current TextAI provider configuration
        from src.core.config import get_system_configuration
        from src.llm.client import LLMProviderClient
        
        config = get_system_configuration()
        if not config or not hasattr(config, 'ai'):
            raise HTTPException(
                status_code=503, 
                detail="TextAI provider not configured. Please configure an AI provider first."
            )
        
        # Initialize LLM client
        try:
            llm_client = LLMProviderClient(
                config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict()
            )
            
            # Check if LLM client has working providers
            if not llm_client._check_providers_available():
                raise HTTPException(
                    status_code=503,
                    detail="No working TextAI providers available. Please check your AI configuration."
                )
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to initialize TextAI provider: {str(e)}"
            )
        
        # Map prompt types to context descriptions
        prompt_contexts = {
            "query_understanding": "analyzing user search queries to determine intent, domain, and search strategy",
            "result_relevance": "evaluating whether search results adequately answer the user's query",
            "query_refinement": "generating improved search queries when initial results are insufficient",
            "external_search_decision": "deciding whether to search external sources when internal results are inadequate",
            "external_search_query": "creating optimized queries for external search providers",
            "content_extraction": "extracting relevant content from external documentation",
            "response_format": "formatting search results based on user preferences (raw vs synthesized)",
            "learning_opportunities": "identifying knowledge gaps for future content ingestion",
            "provider_selection": "selecting the optimal external search provider for a query",
            "failure_analysis": "analyzing failed searches to improve system performance"
        }
        
        # Create enhancement prompt
        context_description = prompt_contexts.get(prompt_type, "making search-related decisions")
        
        enhancement_prompt = f"""You are an expert prompt engineer specializing in search and retrieval systems.

Current prompt template for {context_description}:

```
{db_prompt['content']}
```

Please enhance this prompt to be more effective. Consider:

1. **Clarity**: Make instructions crystal clear and unambiguous
2. **Structure**: Ensure the prompt guides the AI to produce well-structured output
3. **Efficiency**: Reduce unnecessary words while maintaining effectiveness
4. **Output Format**: Ensure the desired output format is clearly specified
5. **Context**: The prompt is used in a technical documentation search system that combines internal knowledge bases with external search

The enhanced prompt should:
- Be direct and action-oriented
- Specify the exact format expected (JSON, markdown, plain text)
- Include any necessary examples inline if helpful
- Avoid redundancy while being complete
- Consider edge cases relevant to {context_description}

IMPORTANT: Respond with ONLY the enhanced prompt text. Do not include any explanations, metadata, or formatting around it."""

        # Call LLM for enhancement
        try:
            enhanced_prompt_text = await llm_client.generate(
                prompt=enhancement_prompt,
                temperature=0.7,
                max_tokens=2000
            )
            
            # Clean up the response
            enhanced_prompt_text = enhanced_prompt_text.strip()
            
            # Remove any markdown code block formatting if present
            if enhanced_prompt_text.startswith('```'):
                lines = enhanced_prompt_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].startswith('```'):
                    lines = lines[:-1]
                enhanced_prompt_text = '\n'.join(lines).strip()
            
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to enhance prompt: {str(e)}"
            )
        
        # Validate the enhanced prompt has the same variables
        import re
        original_vars = set(re.findall(r'\{(\w+)\}', db_prompt['content']))
        enhanced_vars = set(re.findall(r'\{(\w+)\}', enhanced_prompt_text))
        
        if original_vars != enhanced_vars:
            missing_vars = original_vars - enhanced_vars
            extra_vars = enhanced_vars - original_vars
            error_msg = []
            if missing_vars:
                error_msg.append(f"Missing variables: {', '.join(missing_vars)}")
            if extra_vars:
                error_msg.append(f"Extra variables: {', '.join(extra_vars)}")
            
            raise HTTPException(
                status_code=422,
                detail=f"Enhanced prompt has different variables. {' '.join(error_msg)}"
            )
        
        # Create new version with enhanced prompt
        metadata = db_prompt.get("metadata", {})
        metadata["enhanced"] = True
        metadata["enhancement_date"] = datetime.utcnow().isoformat()
        metadata["notes"] = "AI-enhanced version for improved clarity and effectiveness"
        
        # Update the prompt (creates new version)
        updated_prompt = await repository.update_prompt(
            prompt_type=prompt_type,
            content=enhanced_prompt_text,
            metadata=metadata
        )
        
        # Identify improvements made
        improvements = []
        
        # Simple analysis of improvements
        if len(enhanced_prompt_text) < len(db_prompt['content']):
            reduction = int((1 - len(enhanced_prompt_text) / len(db_prompt['content'])) * 100)
            improvements.append(f"Reduced prompt length by {reduction}%")
        
        if "JSON" in enhanced_prompt_text and "JSON" not in db_prompt['content']:
            improvements.append("Added explicit JSON output format specification")
        elif "json" in enhanced_prompt_text.lower() and "json" not in db_prompt['content'].lower():
            improvements.append("Clarified output format requirements")
        
        if enhanced_prompt_text.count('\n') > db_prompt['content'].count('\n'):
            improvements.append("Improved structure with better formatting")
        
        if "IMPORTANT:" in enhanced_prompt_text or "NOTE:" in enhanced_prompt_text:
            improvements.append("Added emphasis on critical instructions")
        
        if not improvements:
            improvements = ["Refined wording for clarity", "Optimized instruction flow"]
        
        return APIResponse(
            success=True,
            message="Prompt enhanced successfully",
            data={
                "prompt_type": prompt_type,
                "old_version": db_prompt["version"],
                "new_version": updated_prompt["version"],
                "new_id": updated_prompt["id"],
                "improvements": improvements,
                "enhanced_prompt": enhanced_prompt_text
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enhance prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# A/B Testing endpoints

@router.get("/prompts/ab-tests")
async def list_ab_tests():
    """
    List active A/B tests for prompts.
    
    Returns all running tests with:
    - Test configuration
    - Variant performance
    - Statistical significance
    - Test duration
    """
    try:
        # TODO: Phase 2 - Load A/B tests
        return {
            "tests": [
                {
                    "id": "test_001",
                    "prompt_type": "query_understanding",
                    "status": "running",
                    "variants": [
                        {"id": "control", "version": "1.0.0", "traffic": 50},
                        {"id": "variant_a", "version": "1.1.0", "traffic": 50}
                    ],
                    "metrics": {
                        "control": {"success_rate": 0.98, "avg_latency": 450},
                        "variant_a": {"success_rate": 0.99, "avg_latency": 420}
                    },
                    "significance": 0.92,
                    "started_at": datetime.utcnow().isoformat()
                }
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list A/B tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompts/ab-tests", response_model=APIResponse)
async def create_ab_test(test_config: Dict[str, Any] = Body(...)):
    """
    Create a new A/B test for prompts.
    
    Configures test with:
    - Prompt variants to test
    - Traffic split percentages
    - Success metrics
    - Test duration
    """
    try:
        # TODO: Phase 2 - Create A/B test
        return APIResponse(
            success=True,
            message="A/B test created successfully",
            data={"test_id": "test_002"}
        )
    except Exception as e:
        logger.error(f"Failed to create A/B test: {e}")
        raise HTTPException(status_code=500, detail=str(e))