#!/bin/bash
# Initialize AnythingLLM workspace for DocAIche

echo "🚀 Initializing DocAIche workspace in AnythingLLM..."

# Wait for all services to be healthy
echo "⏳ Waiting for services to be healthy..."
for i in {1..60}; do
    if docker exec docaiche-api-1 curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        break
    fi
    echo "⏳ Waiting for API... ($i/60)"
    sleep 2
done

# Check if AnythingLLM is accessible
echo "🔍 Checking AnythingLLM connectivity..."
if docker exec docaiche-anythingllm-1 curl -s http://localhost:3001/api/v1/health > /dev/null 2>&1; then
    echo "✅ AnythingLLM is accessible"
else
    echo "❌ AnythingLLM is not accessible"
    exit 1
fi

# Try to create a workspace using the AnythingLLM API directly
echo "📝 Creating default workspace..."

# First, try without authentication to see what AnythingLLM expects
RESULT=$(docker exec docaiche-anythingllm-1 curl -s -X POST http://localhost:3001/api/v1/workspace/new \
    -H "Content-Type: application/json" \
    -d '{
        "name": "DocAIche Default",
        "onboardingComplete": true
    }' 2>/dev/null)

echo "📋 AnythingLLM response: $RESULT"

# Check if workspace was created
WORKSPACES=$(docker exec docaiche-anythingllm-1 curl -s http://localhost:3001/api/v1/workspaces 2>/dev/null)
echo "📂 Available workspaces: $WORKSPACES"

echo "🎉 Workspace initialization complete!"