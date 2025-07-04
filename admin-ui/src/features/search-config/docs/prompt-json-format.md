# System Prompts JSON Format Documentation

## Overview

The SystemPromptsManager supports importing and exporting prompts in JSON format. This document describes the expected format for import/export operations.

## Export Formats

### Full Export Format

When exporting all prompts, the JSON structure is:

```json
{
  "version": "1.0.0",
  "timestamp": "2024-01-20T10:30:00.000Z",
  "metadata": {
    "totalPrompts": 10,
    "description": "System prompts export from Docaiche admin"
  },
  "prompts": [
    {
      "id": "intent_interpretation",
      "name": "Intent Interpretation",
      "description": "intent_interpretation",
      "category": "search",
      "template": "Given the search query: \"{query}\", identify...",
      "variables": ["query"],
      "version": "1.0.0",
      "active": true,
      "lastModified": "2024-01-20T10:30:00.000Z",
      "metadata": {
        "author": "system",
        "tags": ["search", "intent"],
        "usage_count": 1500,
        "performance_score": 95.5
      }
    }
    // ... more prompts
  ]
}
```

### Single Prompt Export Format

When exporting a single prompt, the JSON structure is:

```json
{
  "version": "1.0.0",
  "timestamp": "2024-01-20T10:30:00.000Z",
  "prompt": {
    "id": "intent_interpretation",
    "name": "Intent Interpretation",
    "description": "intent_interpretation",
    "category": "search",
    "template": "Given the search query: \"{query}\", identify...",
    "variables": ["query"],
    "version": "1.0.0",
    "active": true,
    "lastModified": "2024-01-20T10:30:00.000Z",
    "metadata": {
      "author": "system",
      "tags": ["search", "intent"],
      "usage_count": 1500,
      "performance_score": 95.5
    }
  }
}
```

## Import Format

The import functionality supports both full and partial imports:

### Full Import

You can import a complete set of prompts using the full export format shown above.

### Partial Import

You can import a subset of prompts by providing only the prompts you want to update:

```json
{
  "prompts": [
    {
      "id": "intent_interpretation",
      "name": "Intent Interpretation",
      "template": "Updated template content...",
      "category": "search"
    }
  ]
}
```

### Single Prompt Import

You can import a single prompt using either format:

```json
{
  "prompt": {
    "id": "intent_interpretation",
    "name": "Intent Interpretation",
    "template": "Updated template content...",
    "category": "search"
  }
}
```

## Field Descriptions

### Required Fields

- `id`: Unique identifier for the prompt
- `name`: Human-readable name for the prompt
- `template`: The actual prompt template content
- `category`: One of: "search", "refinement", "evaluation", "enhancement", "system"

### Optional Fields

- `description`: Detailed description of the prompt's purpose
- `variables`: Array of variable names used in the template (e.g., ["query", "context"])
- `version`: Version string (e.g., "1.0.0")
- `active`: Boolean indicating if the prompt is active
- `lastModified`: ISO 8601 timestamp
- `metadata`: Object containing additional information:
  - `author`: Author of the prompt
  - `tags`: Array of tags for categorization
  - `usage_count`: Number of times the prompt has been used
  - `performance_score`: Performance metric (0-100)

## Categories

Prompts are organized into these categories:

- **search**: Processing and understanding search queries
- **refinement**: Improving and expanding queries
- **evaluation**: Evaluating and ranking search results
- **enhancement**: Extracting and formatting content
- **system**: System behavior and analysis prompts

## Import Behavior

### New Prompts
- Prompts with IDs that don't exist will be added as new prompts

### Existing Prompts
- Prompts with matching IDs will be updated
- Only the `template` field is compared for changes
- Unchanged prompts are skipped

### Validation
- The import process validates:
  - JSON structure
  - Required fields presence
  - Category values
  - Data types

### Preview
- Before applying changes, a preview is shown with:
  - Number of prompts to add
  - Number of prompts to update
  - List of unchanged prompts
  - Side-by-side comparison for updates

## Example Use Cases

### Backup and Restore
Export all prompts regularly for backup:
```bash
# Export filename: system-prompts-2024-01-20.json
```

### Team Collaboration
Share specific prompts with team members by exporting individual prompts.

### Version Control
Track prompt changes by committing exported JSON files to version control.

### A/B Testing
Import different prompt versions for testing:
```json
{
  "prompts": [
    {
      "id": "intent_interpretation",
      "name": "Intent Interpretation v2",
      "template": "Alternative template for testing...",
      "category": "search",
      "version": "2.0.0"
    }
  ]
}
```