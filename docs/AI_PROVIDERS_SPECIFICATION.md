# AI Providers Specification for Docaiche

## Overview
This document outlines the AI provider integration requirements for the Docaiche backend API. The system must support 20+ providers with flexible configuration for both text generation and embedding models.

## Provider Categories

### 1. Cloud Providers (API Key Required)

#### Anthropic
- **Provider ID**: `anthropic`
- **Models Supported**:
  - claude-3-opus-20240229
  - claude-3-5-sonnet-20241022
  - claude-3-haiku-20240307
  - claude-3-5-haiku-20241022
  - claude-3-7-sonnet-20250219
  - claude-sonnet-4-20250514
  - claude-opus-4-20250514
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional, default: "https://api.anthropic.com")
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional, 0-1)
  - `streaming` (optional, default: true)
- **Special Features**:
  - Prompt caching support
  - Hybrid reasoning models (with `:thinking` suffix)
  - System prompt support

#### OpenAI
- **Provider ID**: `openai`
- **Models Supported**:
  - gpt-4o
  - gpt-4o-mini
  - gpt-4-turbo
  - gpt-3.5-turbo
  - o1-preview
  - o1-mini
  - Custom models via configuration
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional, default: "https://api.openai.com/v1")
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional, 0-2)
  - `streaming` (optional, default: true)
  - `organization_id` (optional)
- **Special Features**:
  - Azure OpenAI compatibility
  - Function calling support
  - JSON mode support

#### Google Gemini
- **Provider ID**: `gemini`
- **Models Supported**:
  - gemini-2.0-flash-exp
  - gemini-1.5-flash
  - gemini-1.5-pro
  - gemini-1.0-pro
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional, default: "https://generativelanguage.googleapis.com")
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional, 0-1)
  - `streaming` (optional, default: true)
- **Special Features**:
  - OAuth authentication support (coming)
  - Multi-modal capabilities
  - Safety settings configuration

#### AWS Bedrock
- **Provider ID**: `bedrock`
- **Models Supported**:
  - Claude models (via Bedrock)
  - Llama models
  - Mistral models
  - Amazon Titan
- **Configuration Fields**:
  - `aws_access_key_id` (required)
  - `aws_secret_access_key` (required)
  - `aws_region` (required)
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional)
- **Special Features**:
  - IAM role support
  - Cross-region failover

#### Mistral
- **Provider ID**: `mistral`
- **Models Supported**:
  - mistral-tiny
  - mistral-small
  - mistral-medium
  - mistral-large
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional, default: "https://api.mistral.ai")
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional)

#### DeepSeek
- **Provider ID**: `deepseek`
- **Models Supported**:
  - deepseek-chat
  - deepseek-coder
  - deepseek-r1
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional)
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional)

#### Groq
- **Provider ID**: `groq`
- **Models Supported**:
  - llama2-70b-4096
  - mixtral-8x7b-32768
  - gemma-7b-it
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional, default: "https://api.groq.com")
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional)
- **Special Features**:
  - Ultra-low latency inference
  - High throughput

#### XAI (Grok)
- **Provider ID**: `xai`
- **Models Supported**:
  - grok-1
  - grok-2
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional)
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional)

### 2. Local/Self-Hosted Providers (No API Key)

#### Ollama
- **Provider ID**: `ollama`
- **Models Supported**:
  - Dynamic model discovery via `/api/tags` endpoint
  - Common models: llama3, mistral, phi3, qwen, gemma
  - **Embedding models**: nomic-embed-text, all-minilm, mxbai-embed-large
- **Configuration Fields**:
  - `base_url` (required, default: "http://localhost:11434")
  - `model_id` (required)
  - `embedding_model_id` (optional, for embeddings)
  - `max_tokens` (optional)
  - `temperature` (optional)
- **Special Features**:
  - Model discovery API
  - Supports both text generation AND embeddings
  - Model pulling/downloading
  - Custom model support

#### LM Studio
- **Provider ID**: `lmstudio`
- **Models Supported**:
  - Any GGUF format model
  - User-installed models
- **Configuration Fields**:
  - `base_url` (required, default: "http://localhost:1234")
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional)
- **Special Features**:
  - OpenAI-compatible API
  - Local model management

### 3. Gateway/Proxy Providers

#### OpenRouter
- **Provider ID**: `openrouter`
- **Models Supported**:
  - 100+ models from various providers
  - Dynamic model list via API
- **Configuration Fields**:
  - `api_key` (required)
  - `base_url` (optional, default: "https://openrouter.ai/api/v1")
  - `model_id` (required, format: "provider/model")
  - `max_tokens` (optional)
  - `temperature` (optional)
- **Special Features**:
  - Multi-provider routing
  - Cost optimization
  - Fallback support

#### LiteLLM
- **Provider ID**: `litellm`
- **Models Supported**:
  - Supports 100+ LLM providers
  - Provider-prefixed models (e.g., "openai/gpt-4")
- **Configuration Fields**:
  - `base_url` (required)
  - `api_key` (optional, depends on backend)
  - `model_id` (required)
  - `max_tokens` (optional)
  - `temperature` (optional)
- **Special Features**:
  - Universal LLM proxy
  - Load balancing
  - Caching support

### 4. Specialized Providers

#### Claude Code
- **Provider ID**: `claude-code`
- **Description**: Specialized Claude integration for code-focused tasks
- **Configuration**: Inherits from Anthropic with code-optimized defaults

#### Human Relay
- **Provider ID**: `human-relay`
- **Description**: Human-in-the-loop provider for quality control
- **Configuration Fields**:
  - `relay_endpoint` (required)
  - `auth_token` (required)
  - `timeout_ms` (optional, default: 300000)

#### VSCode LM
- **Provider ID**: `vscode-lm`
- **Description**: VS Code's built-in language model API
- **Configuration**: Automatic when running in VS Code

## API Requirements

### 1. Provider Listing Endpoint
```
GET /api/v1/providers
Response: Array of provider definitions with capabilities
```

### 2. Provider Testing Endpoint
```
POST /api/v1/providers/{provider_id}/test
Body: {
  "config": { ...provider-specific config },
  "test_mode": "text" | "embedding"
}
Response: {
  "success": boolean,
  "latency": number,
  "models": string[], // Available models
  "capabilities": {
    "text_generation": boolean,
    "embeddings": boolean,
    "streaming": boolean,
    "function_calling": boolean
  }
}
```

### 3. Model Discovery Endpoint
```
GET /api/v1/providers/{provider_id}/models
Headers: { ...auth headers if needed }
Response: {
  "text_models": [...],
  "embedding_models": [...] // If supported
}
```

### 4. Configuration Management
```
PUT /api/v1/config/providers/{provider_id}
Body: {
  "text_config": { ...config for text generation },
  "embedding_config": { ...config for embeddings }
}
```

## Model Capabilities Matrix

| Provider | Text Generation | Embeddings | Streaming | Function Calling | Local |
|----------|----------------|------------|-----------|------------------|--------|
| Anthropic | ✅ | ❌ | ✅ | ✅ | ❌ |
| OpenAI | ✅ | ✅* | ✅ | ✅ | ❌ |
| Gemini | ✅ | ❌ | ✅ | ✅ | ❌ |
| Ollama | ✅ | ✅ | ✅ | ❌ | ✅ |
| Bedrock | ✅ | ✅* | ✅ | ❌ | ❌ |
| Mistral | ✅ | ❌ | ✅ | ✅ | ❌ |
| DeepSeek | ✅ | ❌ | ✅ | ❌ | ❌ |
| Groq | ✅ | ❌ | ✅ | ❌ | ❌ |
| LM Studio | ✅ | ❌ | ✅ | ❌ | ✅ |
| OpenRouter | ✅ | ✅* | ✅ | ✅* | ❌ |
| LiteLLM | ✅ | ✅* | ✅ | ✅* | ❌ |

*Depends on underlying provider

## Configuration Schema

### Base Configuration
```typescript
interface BaseProviderConfig {
  provider_id: string;
  enabled: boolean;
  display_name?: string;
  description?: string;
  category: "cloud" | "local" | "gateway";
  
  // For text generation
  text_config?: {
    model_id: string;
    max_tokens?: number;
    temperature?: number;
    streaming?: boolean;
    // Provider-specific fields
    [key: string]: any;
  };
  
  // For embeddings (if supported)
  embedding_config?: {
    model_id: string;
    batch_size?: number;
    dimensions?: number;
    // Provider-specific fields
    [key: string]: any;
  };
}
```

### Provider-Specific Extensions
```typescript
interface CloudProviderConfig extends BaseProviderConfig {
  api_key: string;
  base_url?: string;
  organization_id?: string;
}

interface LocalProviderConfig extends BaseProviderConfig {
  base_url: string;
  // No API key needed
}

interface AwsProviderConfig extends BaseProviderConfig {
  aws_access_key_id: string;
  aws_secret_access_key: string;
  aws_region: string;
}
```

## Implementation Notes

1. **Model Selection UI**:
   - Separate dropdowns for text and embedding models
   - Show only models that support the required capability
   - Display model metadata (context window, cost tier, speed)

2. **Configuration Inheritance**:
   - Allow copying text provider config to embedding config
   - Override only necessary fields (model_id)
   - Visual diff showing changes

3. **Testing Workflow**:
   - Test text generation and embeddings separately
   - Show latency metrics
   - Validate model availability
   - Display error messages with remediation steps

4. **Provider Status**:
   - Real-time health checks
   - Connection status indicators
   - Usage statistics per provider
   - Cost tracking (where applicable)

5. **Error Handling**:
   - Provider-specific error messages
   - Fallback suggestions
   - Configuration validation
   - Rate limit warnings

## Security Considerations

1. **API Key Storage**:
   - Encrypt sensitive fields in database
   - Never return full API keys in responses
   - Support environment variable references

2. **Access Control**:
   - Provider configuration requires admin privileges
   - Audit log for configuration changes
   - IP whitelist support for local providers

3. **Rate Limiting**:
   - Implement per-provider rate limits
   - Queue management for high-volume requests
   - Automatic backoff strategies

## Future Enhancements

1. **Additional Providers**:
   - Cohere
   - AI21 Labs
   - Replicate
   - Together AI
   - Anyscale

2. **Advanced Features**:
   - Multi-provider load balancing
   - Automatic failover
   - Cost optimization routing
   - A/B testing support
   - Custom provider plugins

3. **Monitoring**:
   - Prometheus metrics per provider
   - Grafana dashboards for provider performance
   - Alert configuration for failures
   - Usage analytics and reporting

---

This specification should enable the backend team to implement comprehensive provider support that matches the UI design requirements.