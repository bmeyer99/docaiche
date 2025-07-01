# AnythingLLM Authentication Setup Guide

## Problem Summary
The AnythingLLM integration is failing with "Token expired or failed validation" because:
- The `AUTH_TOKEN` environment variable is for web interface access, not API access
- API keys must be created separately through the AnythingLLM interface
- The automatic initialization script cannot create API keys without proper authentication

## Current Configuration
- **AUTH_TOKEN**: `docaiche-lab-default-key-2025` (for web interface)
- **ANYTHINGLLM_API_KEY**: `docaiche-lab-default-key-2025` (incorrect - this should be an actual API key)

## Manual Setup Steps

### Option 1: Create API Key via Web Interface
1. Access AnythingLLM at http://localhost:3001
2. When prompted for authentication, use the token: `docaiche-lab-default-key-2025`
3. Complete any initial setup if required
4. Navigate to Settings → Developer API → API Keys
5. Create a new API key (name it "DocAIche Default")
6. Copy the generated API key
7. Update `docker-compose.yml`:
   ```yaml
   ANYTHINGLLM_API_KEY=<your-generated-api-key>
   ```
8. Rebuild and restart containers:
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

### Option 2: Temporary Workaround (Development Only)
If you need to bypass authentication temporarily for development:

1. Modify the AnythingLLM configuration to disable authentication (NOT RECOMMENDED for production)
2. Use a mock AnythingLLM service for testing

## Verification Steps
After setting up the API key:

```bash
# Test the API key
docker exec docaiche-api-1 curl -s \
  -H "Authorization: Bearer <your-api-key>" \
  http://anythingllm:3001/api/v1/workspaces

# Check DocAIche collections endpoint
curl http://localhost:4080/api/v1/collections
```

## Alternative Solutions

### 1. Use Environment Variable for API Key
Instead of hardcoding the API key, use an environment variable:
- Create a `.env` file with: `ANYTHINGLLM_API_KEY=<your-api-key>`
- Update docker-compose.yml to use `${ANYTHINGLLM_API_KEY}`

### 2. Implement Fallback Strategy
Modify the DocAIche code to handle AnythingLLM unavailability gracefully:
- Cache results when AnythingLLM is available
- Provide degraded functionality when it's not
- Log warnings instead of failing requests

## Next Steps
1. Complete manual API key setup
2. Update configuration
3. Test the integration
4. Consider implementing automatic API key provisioning for future releases