#!/usr/bin/env python3
"""Test script to verify JSON export format from SystemPromptsManager"""

import json
from datetime import datetime

# Sample export format for testing
sample_export = {
    "version": "1.0.0",
    "timestamp": datetime.now().isoformat(),
    "metadata": {
        "totalPrompts": 3,
        "description": "System prompts export from Docaiche admin"
    },
    "prompts": [
        {
            "id": "intent_interpretation",
            "name": "Intent Interpretation",
            "description": "intent_interpretation",
            "category": "search",
            "template": "Given the search query: \"{query}\", identify the key concepts, technical terms, and user intent.",
            "variables": ["query"],
            "version": "1.0.0",
            "active": True,
            "lastModified": datetime.now().isoformat(),
            "metadata": {
                "usage_count": 1500,
                "performance_score": 95.5
            }
        },
        {
            "id": "query_refinement",
            "name": "Query Refinement",
            "description": "query_refinement",
            "category": "refinement",
            "template": "Refine the following query: \"{query}\" to improve search results.",
            "variables": ["query"],
            "version": "1.0.0",
            "active": True,
            "lastModified": datetime.now().isoformat()
        },
        {
            "id": "relevance_evaluation",
            "name": "Relevance Evaluation",
            "description": "relevance_evaluation",
            "category": "evaluation",
            "template": "Evaluate the relevance of this result: {result} for query: \"{query}\"",
            "variables": ["result", "query"],
            "version": "1.0.0",
            "active": True,
            "lastModified": datetime.now().isoformat()
        }
    ]
}

# Write sample export file
with open('sample-prompts-export.json', 'w') as f:
    json.dump(sample_export, f, indent=2)

print("✅ Created sample-prompts-export.json")

# Sample partial import for testing
sample_import = {
    "prompts": [
        {
            "id": "intent_interpretation",
            "name": "Intent Interpretation",
            "template": "Updated template: Given the search query: \"{query}\", analyze intent and context.",
            "category": "search"
        }
    ]
}

# Write sample import file
with open('sample-prompts-import.json', 'w') as f:
    json.dump(sample_import, f, indent=2)

print("✅ Created sample-prompts-import.json")

# Sample single prompt export
single_prompt = {
    "version": "1.0.0",
    "timestamp": datetime.now().isoformat(),
    "prompt": {
        "id": "content_extraction",
        "name": "Content Extraction",
        "type": "content_extraction",
        "template": "Extract relevant content from: {document}",
        "variables": ["document"],
        "version": "1.0.0",
        "active": True,
        "last_updated": datetime.now().isoformat()
    }
}

# Write single prompt file
with open('sample-single-prompt.json', 'w') as f:
    json.dump(single_prompt, f, indent=2)

print("✅ Created sample-single-prompt.json")
print("\nThese JSON files can be used to test the import functionality in the SystemPromptsManager.")