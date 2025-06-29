#!/bin/bash
# Initialize AnythingLLM with default workspace for DocAIche
# This script runs inside the AnythingLLM container

echo "AnythingLLM initialization script - setting up default workspace for DocAIche"

# Since this runs inside the container, we can't wait for the service to start
# The container entrypoint will handle that
# Instead, we'll create a marker file to ensure this only runs once

INIT_MARKER="/app/server/storage/.docaiche-initialized"

if [ -f "$INIT_MARKER" ]; then
    echo "AnythingLLM already initialized for DocAIche"
    exit 0
fi

# Create storage directories if they don't exist
mkdir -p /app/server/storage/workspaces
mkdir -p /app/server/storage/documents
mkdir -p /app/server/storage/exports

# Create initialization marker
touch "$INIT_MARKER"

echo "AnythingLLM directories initialized for DocAIche"