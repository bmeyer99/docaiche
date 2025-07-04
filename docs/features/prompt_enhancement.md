# Prompt Enhancement Feature

## Overview

The prompt enhancement feature allows administrators to use AI to automatically improve prompt templates used throughout the Docaiche search system. This feature leverages the configured TextAI provider to analyze and enhance prompts for better clarity, efficiency, and effectiveness.

## API Endpoint

### Enhance Prompt by Type

**Endpoint:** `POST /api/v1/admin/search/text-ai/prompts/{prompt_type}/enhance`

**Purpose:** Enhance a specific prompt template using AI assistance.

**Parameters:**
- `prompt_type` (path parameter): The type of prompt to enhance. Valid values include:
  - `query_understanding`
  - `result_relevance`
  - `query_refinement`
  - `external_search_decision`
  - `external_search_query`
  - `content_extraction`
  - `response_format`
  - `learning_opportunities`
  - `provider_selection`
  - `failure_analysis`

**Response:**
```json
{
  "success": true,
  "message": "Prompt enhanced successfully",
  "data": {
    "prompt_type": "external_search_decision",
    "old_version": "1.0.0",
    "new_version": "1.1.0",
    "new_id": "uuid-here",
    "improvements": [
      "Reduced prompt length by 15%",
      "Added explicit JSON output format specification"
    ],
    "enhanced_prompt": "Enhanced prompt text..."
  }
}
```

## How It Works

1. **Retrieval**: The system retrieves the current active prompt template for the specified type
2. **Context Building**: An enhancement prompt is created that includes:
   - The current prompt template
   - Context about the specific decision point
   - Guidelines for improvement
3. **AI Enhancement**: The TextAI provider analyzes the prompt and generates an enhanced version
4. **Validation**: The system validates that the enhanced prompt maintains the same variables
5. **Version Creation**: A new version of the prompt is created with the enhancements
6. **Analysis**: The system identifies and reports the improvements made

## Enhancement Considerations

The AI enhancement process considers:

- **Clarity**: Making instructions crystal clear and unambiguous
- **Structure**: Ensuring well-structured output guidance
- **Efficiency**: Reducing unnecessary words while maintaining effectiveness
- **Output Format**: Clearly specifying the expected format (JSON, markdown, etc.)
- **Context**: The technical documentation search system context

## Error Handling

The endpoint handles several error scenarios:

- **400 Bad Request**: Invalid prompt type specified
- **404 Not Found**: Prompt type doesn't exist in the system
- **503 Service Unavailable**: TextAI provider not configured or unavailable
- **422 Unprocessable Entity**: Enhanced prompt has different variables than the original

## Prerequisites

Before using this feature:

1. Configure a TextAI provider (OpenAI, Anthropic, etc.) in the system configuration
2. Ensure the provider has sufficient credits/quota
3. Initialize default prompt templates in the database

## Example Usage

```bash
# Enhance the external search decision prompt
curl -X POST "http://localhost:4080/api/v1/admin/search/text-ai/prompts/external_search_decision/enhance" \
  -H "Content-Type: application/json"
```

## Benefits

- **Consistency**: AI ensures consistent prompt quality across all decision points
- **Optimization**: Prompts are optimized for token usage and clarity
- **Versioning**: All changes are versioned, allowing rollback if needed
- **Transparency**: The system reports what improvements were made
- **Validation**: Enhanced prompts are validated to ensure compatibility

## Implementation Details

The enhancement process:

1. Uses the same LLM client configured for the system
2. Creates a specialized meta-prompt for enhancement
3. Preserves all template variables from the original
4. Creates a new version rather than overwriting
5. Tracks enhancement metadata for auditing