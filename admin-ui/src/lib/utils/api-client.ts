/**
 * Centralized API Client for Docaiche Admin Interface
 * 
 * This class provides a unified interface for all API communications
 * with proper error handling, retry logic, and response parsing.
 */

import { 
  API_CONFIG, 
  API_ENDPOINTS, 
  type ConfigurationResponse,
  type ConfigurationUpdateRequest,
  type HealthResponse,
  type StatsResponse,
  type CollectionsResponse,
  type AdminSearchParams,
  type AdminSearchResponse,
  type UploadResponse,
  type ProblemDetail,
  type ActivityItem
} from '../config/api';
import { type ProviderConfiguration } from '../config/providers';

// Request options interface
interface RequestOptions {
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
}

// Circuit breaker state
interface CircuitBreakerState {
  isOpen: boolean;
  failureCount: number;
  lastFailureTime: number;
  nextAttemptTime: number;
}

// API Client Class
export class DocaicheApiClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;
  private circuitBreaker: Map<string, CircuitBreakerState> = new Map();
  private readonly CIRCUIT_BREAKER_THRESHOLD = 5;
  private readonly CIRCUIT_BREAKER_TIMEOUT = 30000; // 30 seconds
  private readonly CIRCUIT_BREAKER_RESET_TIMEOUT = 60000; // 1 minute

  constructor() {
    this.baseUrl = '/api/v1';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Check circuit breaker state for an endpoint
   */
  private checkCircuitBreaker(endpoint: string): boolean {
    const state = this.circuitBreaker.get(endpoint);
    if (!state) {
      this.circuitBreaker.set(endpoint, {
        isOpen: false,
        failureCount: 0,
        lastFailureTime: 0,
        nextAttemptTime: 0
      });
      return false;
    }

    const now = Date.now();
    
    // If circuit is open and reset timeout has passed, try half-open state
    if (state.isOpen && now >= state.nextAttemptTime) {
      state.isOpen = false;
      state.failureCount = 0;
      return false;
    }

    return state.isOpen;
  }

  /**
   * Record success for circuit breaker
   */
  private recordSuccess(endpoint: string): void {
    const state = this.circuitBreaker.get(endpoint);
    if (state) {
      state.failureCount = 0;
      state.isOpen = false;
      state.lastFailureTime = 0;
      state.nextAttemptTime = 0;
    }
  }

  /**
   * Record failure for circuit breaker
   */
  private recordFailure(endpoint: string): void {
    const state = this.circuitBreaker.get(endpoint);
    if (!state) return;

    state.failureCount++;
    state.lastFailureTime = Date.now();

    if (state.failureCount >= this.CIRCUIT_BREAKER_THRESHOLD) {
      state.isOpen = true;
      state.nextAttemptTime = Date.now() + this.CIRCUIT_BREAKER_RESET_TIMEOUT;
      console.warn(`Circuit breaker opened for endpoint: ${endpoint}`);
    }
  }

  /**
   * Generic HTTP request method with retry logic and error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit & RequestOptions = {}
  ): Promise<T> {
    // Check circuit breaker
    if (this.checkCircuitBreaker(endpoint)) {
      throw this.createApiError(
        'Circuit Breaker Open',
        `Circuit breaker is open for endpoint: ${endpoint}. Too many recent failures.`
      );
    }

    const { timeout = API_CONFIG.TIMEOUTS.DEFAULT, retries = Math.min(API_CONFIG.RETRY.MAX_ATTEMPTS, 3), ...fetchOptions } = options;
    let lastError: Error = new Error('Unknown error');
    
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      ...this.defaultHeaders,
      ...options.headers
    };
    
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(url, {
          ...fetchOptions,
          headers,
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        // Handle response based on content type and status
        const result = await this.handleResponse<T>(response);
        this.recordSuccess(endpoint);
        return result;

      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on certain errors
        if (error instanceof TypeError || (error as Error).name === 'AbortError') {
          this.recordFailure(endpoint);
          throw this.createApiError('Network Error', (error as Error).message);
        }

        // For server errors (5xx), record failure and limit retries more aggressively
        if (lastError.message.includes('500') || lastError.message.includes('502') || lastError.message.includes('503')) {
          this.recordFailure(endpoint);
          
          // Break early for server errors to prevent overwhelming the server
          if (attempt >= 2) {
            break;
          }
        }

        // Wait before retry (exponential backoff)
        if (attempt < retries) {
          const delay = Math.min(
            API_CONFIG.RETRY.DELAY_MS * Math.pow(API_CONFIG.RETRY.BACKOFF_MULTIPLIER, attempt - 1),
            10000 // Cap at 10 seconds
          );
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    this.recordFailure(endpoint);
    throw this.createApiError('Request Failed', `Failed after ${retries} attempts: ${lastError.message}`);
  }

  /**
   * Handle HTTP response and parse based on content type
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type');
    
    // Handle different response types
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      
      // Check if response is successful
      if (response.ok) {
        return data;
      }
      
      // Handle API error responses (RFC 7807 Problem Details)
      if (this.isProblemDetail(data)) {
        throw this.createApiError(data.title, data.detail || 'Unknown error', data);
      }
      
      // Handle other error formats
      throw this.createApiError(
        `API Error ${response.status}`, 
        data.message || data.error || `Server returned ${response.status} error`
      );
    }
    
    // Handle non-JSON responses
    if (response.ok) {
      const text = await response.text();
      return text as unknown as T;
    }
    
    // Handle HTTP errors without JSON body
    throw this.createApiError(
      `HTTP ${response.status}`,
      response.statusText || `Server error: ${response.status}`
    );
  }

  /**
   * Check if response data matches RFC 7807 Problem Details format
   */
  private isProblemDetail(data: unknown): data is ProblemDetail {
    return !!(data && typeof data === 'object' && 'type' in data && 'title' in data && 'status' in data);
  }

  /**
   * Create standardized API error
   */
  private createApiError(title: string, detail: string, problemDetail?: ProblemDetail): Error {
    const error = new Error(`${title}: ${detail}`) as Error & { 
      title: string; 
      detail: string; 
      status?: number;
      problemDetail?: ProblemDetail;
    };
    
    error.title = title;
    error.detail = detail;
    error.status = problemDetail?.status;
    error.problemDetail = problemDetail;
    
    return error;
  }

  // HTTP Method Helpers
  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', ...options });
  }

  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      ...options
    });
  }

  async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      ...options
    });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', ...options });
  }

  // Specialized API Methods

  /**
   * Configuration Management
   */
  async getConfiguration(): Promise<ConfigurationResponse> {
    return this.get<ConfigurationResponse>(API_ENDPOINTS.CONFIG.GET);
  }

  async updateConfiguration(request: ConfigurationUpdateRequest): Promise<ConfigurationResponse> {
    return this.post<ConfigurationResponse>(API_ENDPOINTS.CONFIG.UPDATE, request);
  }

  /**
   * System Monitoring
   */
  async getHealth(): Promise<HealthResponse> {
    return this.get<HealthResponse>(API_ENDPOINTS.HEALTH, {
      timeout: API_CONFIG.TIMEOUTS.HEALTH_CHECK
    });
  }

  async getStats(): Promise<StatsResponse> {
    return this.get<StatsResponse>(API_ENDPOINTS.STATS);
  }

  async getCollections(): Promise<CollectionsResponse> {
    return this.get<CollectionsResponse>(API_ENDPOINTS.COLLECTIONS);
  }

  /**
   * Content Management
   */
  async searchContent(params: AdminSearchParams): Promise<AdminSearchResponse> {
    const queryParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const endpoint = `${API_ENDPOINTS.CONTENT.SEARCH}?${queryParams.toString()}`;
    return this.get<AdminSearchResponse>(endpoint);
  }

  async uploadContent(file: File, metadata?: { collection?: string; technology?: string }): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (metadata?.collection) {
      formData.append('collection', metadata.collection);
    }
    if (metadata?.technology) {
      formData.append('technology', metadata.technology);
    }

    return this.request<UploadResponse>(API_ENDPOINTS.CONTENT.UPLOAD, {
      method: 'POST',
      body: formData,
      timeout: API_CONFIG.TIMEOUTS.UPLOAD,
      headers: {} // Don't set Content-Type for FormData
    });
  }

  async deleteContent(contentId: string): Promise<void> {
    return this.delete<void>(API_ENDPOINTS.CONTENT.DELETE(contentId));
  }

  /**
   * Connection Testing
   */
  async testConnection(endpoint?: string): Promise<{ success: boolean; latency: number; error?: string }> {
    const startTime = Date.now();
    
    try {
      await this.get<any>(endpoint || API_ENDPOINTS.HEALTH, {
        timeout: API_CONFIG.TIMEOUTS.CONNECTION_TEST,
        retries: 1
      });
      
      const latency = Date.now() - startTime;
      return { success: true, latency };
    } catch (error) {
      const latency = Date.now() - startTime;
      return { 
        success: false, 
        latency,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Provider Management
   */
  async getProviderConfigurations(): Promise<any[]> {
    try {
      return await this.get<any[]>('/providers');
    } catch (error) {
      // Return empty array on circuit breaker or repeated failures
      if (error instanceof Error && error.message.includes('Circuit Breaker')) {
        console.warn('Provider configurations unavailable due to circuit breaker');
        return [];
      }
      throw error;
    }
  }

  async updateProviderConfiguration(providerId: string, config: ProviderConfiguration): Promise<ProviderConfiguration> {
    // Transform frontend ProviderConfiguration to backend ProviderConfigRequest format
    const backendConfig = {
      base_url: config.config?.base_url as string || undefined,
      api_key: config.config?.api_key as string || undefined,
      model: config.config?.model as string || undefined,
    };
    
    // Remove undefined values to send only provided fields
    const cleanConfig = Object.fromEntries(
      Object.entries(backendConfig).filter(([, value]) => value !== undefined)
    );

    return this.post<any>(`/providers/${providerId}/config`, cleanConfig);
  }

  async testProviderConnection(providerId: string, config: Record<string, string | number>): Promise<{ success: boolean; message: string; models?: string[] }> {
    try {
      const response = await this.post<{ success: boolean; message: string; models?: string[] }>(
        `/providers/${providerId}/test`,
        config,
        { timeout: API_CONFIG.TIMEOUTS.CONNECTION_TEST }
      );
      return response;
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed'
      };
    }
  }

  async getProviderModels(providerId: string): Promise<{ provider: string; models: string[]; queryable: boolean; custom_count?: number }> {
    // This will be logged by the browser logger via fetch monkey-patch
    return this.get<any>(`/providers/${providerId}/models`);
  }

  async addCustomModel(providerId: string, modelName: string): Promise<any> {
    return this.post<any>(`/providers/${providerId}/models`, { model_name: modelName });
  }

  async removeCustomModel(providerId: string, modelName: string): Promise<any> {
    return this.delete<any>(`/providers/${providerId}/models/${encodeURIComponent(modelName)}`);
  }

  /**
   * Model Selection Configuration
   */
  async updateModelSelection(config: {
    textGeneration: { provider: string; model: string };
    embeddings: { provider: string; model: string };
    sharedProvider: boolean;
  }): Promise<void> {
    // Save the complete model selection configuration
    await this.updateConfiguration({
      key: 'ai.model_selection',
      value: config
    });
    
    // Update system AI configuration with primary provider
    if (config.textGeneration.provider) {
      await this.updateConfiguration({
        key: 'ai.primary_provider',
        value: config.textGeneration.provider
      });
      
      // If using different providers, set fallback provider for embeddings
      if (!config.sharedProvider && config.embeddings.provider !== config.textGeneration.provider) {
        await this.updateConfiguration({
          key: 'ai.embedding_provider',
          value: config.embeddings.provider
        });
      }
    }
  }

  async getModelSelection(): Promise<{
    textGeneration: { provider: string; model: string };
    embeddings: { provider: string; model: string };
    sharedProvider: boolean;
  } | null> {
    try {
      const response = await this.get<any>('/config');
      return response.model_selection || null;
    } catch (error) {
      console.warn('Failed to load model selection configuration:', error);
      return null;
    }
  }

  /**
   * Health and Monitoring Methods
   */

  async getDashboardStats(): Promise<any> {
    return this.get<any>('/stats');
  }

  async getRecentActivity(): Promise<ActivityItem[]> {
    return this.get<ActivityItem[]>('/admin/activity/recent');
  }



  async createCollection(data: { name: string; description?: string; metadata?: Record<string, unknown> }): Promise<{ id: string; name: string; description?: string; created_at: string }> {
    return this.post<any>('/content/collections', data);
  }

  async deleteCollection(collectionId: string): Promise<void> {
    return this.delete<void>(`/content/collections/${collectionId}`);
  }

  async reindexCollection(collectionId: string): Promise<any> {
    return this.post<any>(`/content/collections/${collectionId}/reindex`, {});
  }


  /**
   * Analytics Methods
   */
  async getAnalytics(timeRange: string = '24h'): Promise<any> {
    return this.get<any>(`/analytics?timeRange=${timeRange}`);
  }
}

// Export singleton instance
export const apiClient = new DocaicheApiClient();

// Export class for testing or custom instances
export default DocaicheApiClient;