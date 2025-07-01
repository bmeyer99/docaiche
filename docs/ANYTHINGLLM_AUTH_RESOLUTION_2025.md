# AnythingLLM Authentication Resolution Guide (2025)

## Problem Summary

The AnythingLLM integration was failing with authentication errors because the system was attempting to use the `AUTH_TOKEN` environment variable as an API key. However, these serve different purposes:

- **AUTH_TOKEN**: Used for web interface login/authentication
- **API Key**: Required for programmatic API access (must be created through the interface)

## Key Findings from 2025 Documentation

### 1. Authentication Types

AnythingLLM supports multiple authentication methods:

1. **AUTH_TOKEN + JWT_SECRET**: For securing the web interface
   - Set via environment variables
   - Used for initial login to the web UI
   - Requires JWT_SECRET (minimum 12-20 characters)

2. **API Keys**: For programmatic access
   - Created through the web interface after login
   - Managed under Settings > API Keys
   - Can be created/deleted on the fly

3. **Simple SSO** (New in 2025): For enterprise integration
   - Enabled via `SIMPLE_SSO_ENABLED` environment variable
   - Allows temporary authentication tokens
   - Best for internal-facing instances

### 2. Current Configuration

```yaml
anythingllm:
  image: mintplexlabs/anythingllm:latest
  environment:
    STORAGE_DIR: /app/server/storage
    SERVER_PORT: 3001
    JWT_SECRET: docaiche-lab-jwt-secret-2025  # ✅ Correctly set
    AUTH_TOKEN: docaiche-lab-default-key-2025  # ✅ For web UI access
    # ❌ Missing: ANYTHINGLLM_API_KEY (needs to be created)
```

### 3. Solution Implementation

#### Step 1: Manual API Key Creation (One-time setup)

1. Access AnythingLLM web interface:
   ```
   http://localhost:3001
   ```

2. Login with AUTH_TOKEN:
   ```
   Password: docaiche-lab-default-key-2025
   ```

3. Navigate to Settings > API Keys

4. Create a new API key with appropriate permissions

5. Save the API key securely

#### Step 2: Update Docker Configuration

Add the API key to docker-compose.yml:

```yaml
anythingllm:
  environment:
    # ... existing config ...
    ANYTHINGLLM_API_KEY: <your-generated-api-key>
```

Or create a `.env` file:
```
ANYTHINGLLM_API_KEY=your-generated-api-key
```

#### Step 3: Rebuild and Restart

```bash
docker-compose down
docker-compose up -d --build
```

### 4. Implemented Fixes

1. **Graceful Degradation**: 
   - Modified `/api/v1/collections` to return empty list when AnythingLLM is unavailable
   - System continues to function without document search

2. **Enhanced Logging**:
   - Clear messages about AUTH_TOKEN vs API key distinction
   - Instructions for manual setup when needed

3. **API Key File Support**:
   - System can read API key from `/data/.anythingllm-api-key`
   - Allows persistence across container restarts

4. **Startup Validation**:
   - Workspace initialization skips if no valid API key
   - Provides clear setup instructions

### 5. Alternative Solutions

#### Option A: Simple SSO (For automated setup)

Enable Simple SSO for programmatic token generation:

```yaml
anythingllm:
  environment:
    SIMPLE_SSO_ENABLED: "enable"
    # ... other config ...
```

Then use the API to generate temporary auth tokens.

#### Option B: Direct Database API Key Injection

For automated deployments, you could potentially:
1. Start AnythingLLM
2. Create API key via database manipulation
3. Use that key for API access

However, this is not recommended as it bypasses AnythingLLM's security model.

### 6. Best Practices

1. **Security**:
   - Never commit API keys to version control
   - Use environment variables or secrets management
   - Rotate API keys regularly

2. **Monitoring**:
   - Check AnythingLLM health endpoint regularly
   - Monitor authentication failures
   - Set up alerts for API quota limits

3. **Documentation**:
   - Document which API key is used for what purpose
   - Keep track of API key permissions
   - Document the manual setup process for new deployments

## Verification Steps

After setup, verify the integration:

```bash
# 1. Check if AnythingLLM is healthy
curl http://localhost:3001/api/v1/health

# 2. Test API authentication (with your API key)
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:3001/api/v1/workspaces

# 3. Check DocAIche collections endpoint
curl http://localhost:4080/api/v1/collections
```

## Conclusion

The AnythingLLM authentication issue is resolved by understanding the distinction between AUTH_TOKEN (web UI) and API keys (programmatic access). While this requires a manual one-time setup, it follows AnythingLLM's security model and ensures proper access control.

The system now gracefully handles the absence of AnythingLLM API configuration, allowing other features to function while document search remains unavailable until properly configured.