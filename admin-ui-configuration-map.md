# Admin UI Configuration Pages Map

## Overview
This document provides a comprehensive map of all configuration pages in the admin-ui, their current state, API endpoints they use, and functional status.

## Configuration Pages

### 1. Search Configuration Page (`/dashboard/search-config`)

Located at: `/home/lab/docaiche/admin-ui/src/app/dashboard/search-config/page.tsx`

This page contains 6 tabs for configuring the search system:

#### Tab 1: AI Providers
- **Purpose**: Configure and test AI providers (OpenAI, Anthropic, Ollama, etc.)
- **API Endpoints Used**:
  - `GET /api/v1/providers` - ✅ EXISTS (provider_endpoints.py)
  - `POST /api/v1/providers/{providerId}/config` - ✅ EXISTS
  - `POST /api/v1/providers/{providerId}/test` - ✅ EXISTS
  - `GET /api/v1/providers/{providerId}/models` - ✅ EXISTS
  - `POST /api/v1/providers/{providerId}/models` - ✅ EXISTS (add custom model)
  - `DELETE /api/v1/providers/{providerId}/models/{modelName}` - ✅ EXISTS (remove custom model)
- **Status**: FUNCTIONAL - Provider management is working

#### Tab 2: Vector Search
- **Purpose**: Configure Weaviate vector database connection and embedding settings
- **API Endpoints Used**:
  - `GET /api/v1/weaviate/config` - ✅ EXISTS (weaviate_endpoints.py)
  - `PUT /api/v1/weaviate/config` - ✅ EXISTS (returns success but doesn't save)
  - `POST /api/v1/weaviate/test` - ✅ EXISTS
  - `GET /api/v1/weaviate/workspaces` - ✅ EXISTS
  - `PUT /api/v1/weaviate/embeddings` - ✅ EXISTS
- **Status**: PARTIALLY FUNCTIONAL
  - Connection testing works
  - Workspace listing works
  - Configuration updates return success but don't persist (TODO in backend)

#### Tab 3: Text AI
- **Purpose**: Configure model parameters for text generation (temperature, tokens, etc.)
- **API Endpoints Used**:
  - `GET /api/v1/providers/{provider}/models/{model}/parameters` - ❌ NOT FOUND
  - `PUT /api/v1/providers/{provider}/models/{model}/parameters` - ❌ NOT FOUND
- **Status**: NON-FUNCTIONAL - Endpoints don't exist, using hardcoded defaults

#### Tab 4: Ingestion
- **Purpose**: Configure content ingestion rules and settings
- **API Endpoints Used**:
  - `GET /api/v1/ingestion/rules` - ❌ NOT FOUND
  - `POST /api/v1/ingestion/rules` - ❌ NOT FOUND
  - `PUT /api/v1/ingestion/rules/{ruleId}` - ❌ NOT FOUND
  - `DELETE /api/v1/ingestion/rules/{ruleId}` - ❌ NOT FOUND
  - `GET /api/v1/ingestion/settings` - ❌ NOT FOUND
  - `PUT /api/v1/ingestion/settings` - ❌ NOT FOUND
  - `GET /api/v1/ingestion/jobs` - ❌ NOT FOUND
  - `POST /api/v1/ingestion/rules/{ruleId}/trigger` - ❌ NOT FOUND
- **Status**: NON-FUNCTIONAL - No backend implementation

#### Tab 5: Monitoring
- **Purpose**: View logs, alerts, and monitoring dashboards
- **API Endpoints Used**:
  - `GET /api/v1/monitoring/alerts` - ❌ NOT FOUND
  - `PUT /api/v1/monitoring/alerts/{alertId}` - ❌ NOT FOUND
  - `GET /api/v1/monitoring/logs` - ❌ NOT FOUND
  - `GET /api/v1/metrics/dashboards` - ✅ EXISTS (metrics_endpoints.py)
- **Status**: PARTIALLY FUNCTIONAL
  - Dashboard URLs endpoint exists
  - Alert and log endpoints missing

#### Tab 6: Settings
- **Purpose**: System-wide settings and maintenance operations
- **API Endpoints Used**:
  - `GET /api/v1/system/settings` - ❌ NOT FOUND
  - `PUT /api/v1/system/settings` - ❌ NOT FOUND
  - `POST /api/v1/system/settings/reset` - ❌ NOT FOUND
  - `POST /api/v1/system/cache/clear` - ❌ NOT FOUND
  - `POST /api/v1/system/indexes/rebuild` - ❌ NOT FOUND
- **Status**: NON-FUNCTIONAL - No backend implementation

### 2. External Search Page (`/dashboard/external-search`)

Located at: `/home/lab/docaiche/admin-ui/src/app/dashboard/external-search/page.tsx`

This page manages MCP (Model Context Protocol) external search providers:

#### Tab 1: Providers
- **Purpose**: Manage external search providers (Brave, Google, DuckDuckGo)
- **API Endpoints Used**:
  - `GET /api/v1/mcp/providers` - ✅ EXISTS (mcp_endpoints.py)
  - `GET /api/v1/mcp/providers/{id}` - ✅ EXISTS
  - `POST /api/v1/mcp/providers` - ✅ EXISTS
  - `PUT /api/v1/mcp/providers/{id}` - ✅ EXISTS
  - `DELETE /api/v1/mcp/providers/{id}` - ✅ EXISTS
- **Status**: FUNCTIONAL - Full CRUD operations available

#### Tab 2: Configuration
- **Purpose**: Configure search settings and caching
- **API Endpoints Used**:
  - `GET /api/v1/mcp/config` - ✅ EXISTS
  - `POST /api/v1/mcp/config` - ✅ EXISTS
- **Status**: FUNCTIONAL

#### Tab 3: Performance
- **Purpose**: View performance metrics and statistics
- **API Endpoints Used**:
  - `GET /api/v1/mcp/stats` - ✅ EXISTS
- **Status**: FUNCTIONAL

#### Tab 4: Testing
- **Purpose**: Test providers and compare results
- **API Endpoints Used**:
  - `POST /api/v1/mcp/providers/{id}/test` - ✅ EXISTS
  - `POST /api/v1/mcp/search` - ✅ EXISTS
- **Status**: FUNCTIONAL

## Summary

### Working Features:
1. **AI Provider Management** - Full configuration and testing
2. **External Search (MCP)** - Complete functionality for managing web search providers
3. **Vector Database Connection** - Connection testing and workspace listing
4. **Metrics Dashboards** - Dashboard URL retrieval

### Partially Working:
1. **Vector Search Configuration** - Updates don't persist (backend TODO)
2. **Monitoring** - Only dashboard URLs work, logs and alerts missing

### Non-Functional (No Backend):
1. **Text AI Parameters** - Model parameter configuration
2. **Ingestion Rules** - Content ingestion configuration
3. **System Settings** - General system configuration
4. **Monitoring Alerts/Logs** - Alert rules and log viewing

### Key Issues:
1. Many configuration endpoints return success but don't actually persist changes
2. The ConfigProvider pre-loads only working endpoints to avoid errors
3. Several tabs show UI but have no backend functionality
4. Some features use hardcoded/default values when endpoints fail

### Recommendations:
1. Implement missing backend endpoints for full functionality
2. Add proper error handling in UI for missing endpoints
3. Consider hiding or disabling non-functional tabs
4. Implement persistence for vector configuration updates
5. Add backend support for model parameters, ingestion, and system settings