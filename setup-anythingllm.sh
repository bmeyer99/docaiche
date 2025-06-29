#!/bin/bash
# Setup AnythingLLM for DocAIche with proper workspace initialization

echo "🚀 Setting up AnythingLLM for DocAIche..."

# Wait for AnythingLLM to be ready
echo "⏳ Waiting for AnythingLLM to be ready..."
for i in {1..60}; do
    if docker exec docaiche-anythingllm-1 curl -s http://localhost:3001 > /dev/null 2>&1; then
        echo "✅ AnythingLLM web interface is available"
        break
    fi
    echo "⏳ Waiting for AnythingLLM... ($i/60)"
    sleep 2
done

# Check if AnythingLLM needs onboarding
echo "🔍 Checking AnythingLLM setup status..."

# Try to check system preferences - this will tell us if setup is needed
SETUP_CHECK=$(docker exec docaiche-anythingllm-1 curl -s http://localhost:3001/api/system/system-preferences 2>/dev/null)
echo "📋 System preferences response: $SETUP_CHECK"

# If AnythingLLM is not set up, we'll check the setup endpoint
if echo "$SETUP_CHECK" | grep -q "error\|not found"; then
    echo "🔧 AnythingLLM appears to need initial setup..."
    
    # Check what the setup endpoint returns
    SETUP_STATUS=$(docker exec docaiche-anythingllm-1 curl -s http://localhost:3001/api/system/setup-complete 2>/dev/null)
    echo "🔍 Setup status: $SETUP_STATUS"
fi

# Try to create a workspace using the workspace creation endpoint
echo "📝 Attempting to create default workspace..."

# First try without authentication - AnythingLLM might allow workspace creation during initial setup
CREATE_WORKSPACE=$(docker exec docaiche-anythingllm-1 curl -s -X POST http://localhost:3001/api/workspace/new \
    -H "Content-Type: application/json" \
    -d '{
        "name": "DocAIche Default",
        "onboardingComplete": true
    }' 2>/dev/null)

echo "📋 Workspace creation response: $CREATE_WORKSPACE"

# Check if any workspaces exist now
echo "📂 Checking for existing workspaces..."
WORKSPACES=$(docker exec docaiche-anythingllm-1 curl -s http://localhost:3001/api/workspaces 2>/dev/null)
echo "📂 Available workspaces: $WORKSPACES"

# If workspace creation failed, try the v1 API endpoint
if echo "$CREATE_WORKSPACE" | grep -q "error"; then
    echo "🔄 Trying v1 API endpoint..."
    CREATE_WORKSPACE_V1=$(docker exec docaiche-anythingllm-1 curl -s -X POST http://localhost:3001/api/v1/workspace/new \
        -H "Content-Type: application/json" \
        -d '{
            "name": "DocAIche Default",
            "onboardingComplete": true
        }' 2>/dev/null)
    
    echo "📋 V1 workspace creation response: $CREATE_WORKSPACE_V1"
fi

echo "🎉 AnythingLLM setup attempt complete!"
echo "📋 Summary:"
echo "   - Setup status checked"
echo "   - Workspace creation attempted"
echo "   - Available workspaces listed"
echo ""
echo "💡 If workspaces still aren't available, you may need to:"
echo "   1. Access AnythingLLM at http://localhost:3001 through the browser"
echo "   2. Complete the initial onboarding process"
echo "   3. Create an API key in the settings"
echo "   4. Create a workspace manually"