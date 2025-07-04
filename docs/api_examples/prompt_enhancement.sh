#!/bin/bash
# API Examples for Prompt Enhancement Endpoint

echo "Prompt Enhancement API Examples"
echo "==============================="

API_BASE="http://localhost:4080/api/v1/admin/search/text-ai"

echo -e "\n1. Get current prompt template:"
echo "curl -X GET \"${API_BASE}/prompts/query_understanding\""

echo -e "\n2. Enhance a prompt template:"
echo "curl -X POST \"${API_BASE}/prompts/query_understanding/enhance\""

echo -e "\n3. List all prompts:"
echo "curl -X GET \"${API_BASE}/prompts\""

echo -e "\n4. Get prompt version history:"
echo "curl -X GET \"${API_BASE}/prompts/query_understanding/versions\""

echo -e "\n\nExample: Enhance the external search decision prompt"
echo "===================================================="
cat << 'EOF'
curl -X POST "http://localhost:4080/api/v1/admin/search/text-ai/prompts/external_search_decision/enhance" \
  -H "Content-Type: application/json"

# Expected response:
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
      "Added explicit JSON output format specification",
      "Improved structure with better formatting"
    ],
    "enhanced_prompt": "Enhanced prompt text here..."
  }
}
EOF

echo -e "\n\nError Responses:"
echo "================"
echo "- 400: Invalid prompt type"
echo "- 404: Prompt type not found"
echo "- 503: TextAI provider not configured or unavailable"
echo "- 422: Enhanced prompt has different variables than original"