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
  type ActivityItem,
  type MCPProvidersResponse,
  type MCPProvider,
  type MCPProviderConfig,
  type MCPConfigResponse,
  type MCPSearchConfig,
  type MCPExternalSearchRequest,
  type MCPExternalSearchResponse,
  type MCPStatsResponse
} from '../config/api';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { type ProviderConfiguration } from '../config/providers';

// Request options interface
interface RequestOptions {
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

// Circuit breaker state
interface CircuitBreakerState {
  isOpen: boolean;
  failureCount: number;
  lastFailureTime: number;
  nextAttemptTime: number;
}

// Retry state for tracking ongoing retries with user feedback
interface RetryState {
  isRetrying: boolean;
  nextRetryTime: number;
  retryCount: number;
  toastId?: string;
}

// API Client Class
export class DocaicheApiClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;
  private circuitBreaker: Map<string, CircuitBreakerState> = new Map();
  private retryStates: Map<string, RetryState> = new Map();
  private toastCallbacks: {
    showToast?: (message: string, type: 'info' | 'error' | 'warning', options?: { id?: string; duration?: number }) => void;
    updateToast?: (id: string, message: string, type: 'info' | 'error' | 'warning') => void;
    dismissToast?: (id: string) => void;
  } = {};
  private readonly CIRCUIT_BREAKER_THRESHOLD = 3; // Reduced threshold
  private readonly CIRCUIT_BREAKER_TIMEOUT = 30000; // 30 seconds
  private readonly CIRCUIT_BREAKER_RESET_TIMEOUT = 60000; // 1 minute
  private readonly RETRY_DELAY = 30000; // 30 seconds between retries
  private readonly MAX_RETRIES = Infinity; // Continuous retries

  constructor() {
    this.baseUrl = '/api/v1';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Register toast callbacks for user feedback during retries
   */
  setToastCallbacks(callbacks: {
    showToast?: (message: string, type: 'info' | 'error' | 'warning', options?: { id?: string; duration?: number }) => void;
    updateToast?: (id: string, message: string, type: 'info' | 'error' | 'warning') => void;
    dismissToast?: (id: string) => void;
  }): void {
    this.toastCallbacks = callbacks;
  }

  /**
   * Format time remaining until next retry in HH:MM:SS format
   */
  private formatTimeRemaining(timestamp: number): string {
    const now = Date.now();
    const remaining = Math.max(0, timestamp - now);
    const seconds = Math.floor(remaining / 1000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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
   * Generic HTTP request method with controlled retry logic and user feedback
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit & RequestOptions = {}
  ): Promise<T> {
    // Check circuit breaker
    if (this.checkCircuitBreaker(endpoint)) {
      throw this.createApiError(
        'Service Unavailable',
        `Backend service is temporarily unavailable. Please try again later.`
      );
    }

    // Check if this endpoint is already in a retry state
    const retryState = this.retryStates.get(endpoint);
    if (retryState?.isRetrying && Date.now() < retryState.nextRetryTime) {
      const timeRemaining = this.formatTimeRemaining(retryState.nextRetryTime);
      throw this.createApiError(
        'Retry In Progress',
        `Connection lost. Retrying in ${timeRemaining}. Please wait.`
      );
    }

    const { timeout = API_CONFIG.TIMEOUTS.DEFAULT, retries = 1, signal: externalSignal, ...fetchOptions } = options;
    let lastError: Error = new Error('Unknown error');
    
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      ...this.defaultHeaders,
      ...options.headers
    };
    
    // Single attempt first
    let timeoutId: NodeJS.Timeout | undefined;
    let signalAbortHandler: (() => void) | undefined;
    
    try {
      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort('Request timeout'), timeout);

      // Handle external abort signal
      if (externalSignal) {
        if (externalSignal.aborted) {
          controller.abort(externalSignal.reason);
        } else {
          signalAbortHandler = () => controller.abort(externalSignal.reason);
          externalSignal.addEventListener('abort', signalAbortHandler);
        }
      }

      const response = await fetch(url, {
        ...fetchOptions,
        headers,
        signal: controller.signal
      });

      if (timeoutId) clearTimeout(timeoutId);
      if (signalAbortHandler && externalSignal) {
        externalSignal.removeEventListener('abort', signalAbortHandler);
      }

      // Success - clear any retry state and circuit breaker
      this.recordSuccess(endpoint);
      this.clearRetryState(endpoint);
      
      return await this.handleResponse<T>(response);

    } catch (error) {
      lastError = error as Error;
      
      // Cleanup
      if (timeoutId) clearTimeout(timeoutId);
      if (signalAbortHandler && externalSignal) {
        externalSignal.removeEventListener('abort', signalAbortHandler);
      }
      
      // Don't retry on certain errors (user cancellation, etc.)
      if (error instanceof TypeError && error.message.includes('aborted') || 
          (error as Error).name === 'AbortError') {
        throw this.createApiError('Request Cancelled', 'Request was cancelled');
      }

      // For network errors or server errors, initiate controlled retry with user feedback
      if (this.shouldRetry(lastError, endpoint)) {
        this.initializeRetryState(endpoint);
        throw this.createApiError(
          'Connection Lost',
          'Lost connection to backend. Automatic retry scheduled.'
        );
      }

      // Record failure and throw
      this.recordFailure(endpoint);
      throw this.createApiError('Request Failed', lastError.message);
    }
  }

  /**
   * Determine if an error should trigger the retry mechanism
   */
  private shouldRetry(error: Error, _endpoint: string): boolean {
    // Always retry on network errors, timeouts, and server errors
    // No retry limit - will continue trying every 30 seconds
    return error.message.includes('fetch') || 
           error.message.includes('network') ||
           error.message.includes('timeout') ||
           error.message.includes('500') ||
           error.message.includes('502') ||
           error.message.includes('503') ||
           error.message.includes('504');
  }

  /**
   * Initialize or update retry state for an endpoint
   */
  private initializeRetryState(endpoint: string): void {
    const existing = this.retryStates.get(endpoint);
    const retryCount = (existing?.retryCount || 0) + 1;
    const nextRetryTime = Date.now() + this.RETRY_DELAY;
    
    const retryState: RetryState = {
      isRetrying: true,
      nextRetryTime,
      retryCount,
      toastId: existing?.toastId
    };

    this.retryStates.set(endpoint, retryState);
    
    // Show user feedback
    this.showRetryToast(endpoint, retryState);
    
    // Schedule the actual retry
    this.scheduleRetry(endpoint);
  }

  /**
   * Clear retry state for an endpoint
   */
  private clearRetryState(endpoint: string): void {
    const retryState = this.retryStates.get(endpoint);
    if (retryState?.toastId && this.toastCallbacks.dismissToast) {
      this.toastCallbacks.dismissToast(retryState.toastId);
    }
    this.retryStates.delete(endpoint);
  }

  /**
   * Show toast notification about retry status
   */
  private showRetryToast(endpoint: string, retryState: RetryState): void {
    if (!this.toastCallbacks.showToast) return;

    const timeRemaining = this.formatTimeRemaining(retryState.nextRetryTime);
    const message = `Backend disconnected. Retrying in ${timeRemaining}`;
    
    if (retryState.toastId && this.toastCallbacks.updateToast) {
      this.toastCallbacks.updateToast(retryState.toastId, message, 'warning');
    } else {
      const toastId = `retry-${endpoint}-${Date.now()}`;
      retryState.toastId = toastId;
      this.toastCallbacks.showToast(message, 'warning', { 
        id: toastId, 
        duration: this.RETRY_DELAY + 5000 // Keep toast visible until after retry
      });
    }

    // Update countdown every second
    this.startCountdownUpdate(endpoint, retryState);
  }

  /**
   * Update toast countdown every second
   */
  private startCountdownUpdate(endpoint: string, retryState: RetryState): void {
    if (!retryState.toastId || !this.toastCallbacks.updateToast) return;

    const updateInterval = setInterval(() => {
      const currentState = this.retryStates.get(endpoint);
      if (!currentState || !currentState.isRetrying) {
        clearInterval(updateInterval);
        return;
      }

      const timeRemaining = this.formatTimeRemaining(currentState.nextRetryTime);
      const now = Date.now();
      
      if (now >= currentState.nextRetryTime) {
        clearInterval(updateInterval);
        if (this.toastCallbacks.updateToast && currentState.toastId) {
          this.toastCallbacks.updateToast(
            currentState.toastId,
            `Retrying connection... (${currentState.retryCount}/${this.MAX_RETRIES})`,
            'info'
          );
        }
        return;
      }

      if (this.toastCallbacks.updateToast && currentState.toastId) {
        const message = `Backend disconnected. Retrying in ${timeRemaining}`;
        this.toastCallbacks.updateToast(currentState.toastId, message, 'warning');
      }
    }, 1000);
  }

  /**
   * Schedule a retry for an endpoint
   */
  private scheduleRetry(endpoint: string): void {
    const retryState = this.retryStates.get(endpoint);
    if (!retryState) return;

    const delay = retryState.nextRetryTime - Date.now();
    
    setTimeout(async () => {
      const currentState = this.retryStates.get(endpoint);
      if (!currentState || !currentState.isRetrying) return;

      // Update toast to show retry is happening
      if (currentState.toastId && this.toastCallbacks.updateToast) {
        this.toastCallbacks.updateToast(
          currentState.toastId,
          `Retrying connection...`,
          'info'
        );
      }

      try {
        // Attempt the retry with minimal options to avoid recursion
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
          method: 'GET',
          headers: this.defaultHeaders,
          signal: AbortSignal.timeout(30000) // 30 second timeout for retry
        });

        if (response.ok) {
          // Success - clear retry state
          this.recordSuccess(endpoint);
          this.clearRetryState(endpoint);
          
          if (this.toastCallbacks.showToast) {
            this.toastCallbacks.showToast('Connection restored!', 'info', { duration: 3000 });
          }
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error) {
        // Retry failed - always schedule next retry
        // Will continue retrying every 30 seconds indefinitely
        this.initializeRetryState(endpoint);
      }
    }, Math.max(0, delay));
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
      await this.get<HealthResponse>(endpoint || API_ENDPOINTS.HEALTH, {
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
  async getProviderConfigurations(): Promise<Array<{
    id: string;
    enabled?: boolean;
    config?: Record<string, any>;
    status?: string;
    last_tested?: string;
    models?: string[];
  }>> {
    try {
      return await this.get<Array<{
        id: string;
        enabled?: boolean;
        config?: Record<string, any>;
        status?: string;
        last_tested?: string;
        models?: string[];
      }>>('/providers');
    } catch (error) {
      // Return empty array on circuit breaker or repeated failures
      if (error instanceof Error && error.message.includes('Circuit Breaker')) {
        console.warn('Provider configurations unavailable due to circuit breaker');
        return [];
      }
      throw error;
    }
  }

  async updateProviderConfiguration(providerId: string, config: { config: Record<string, any> }): Promise<{
    id: string;
    enabled?: boolean;
    config?: Record<string, any>;
    status?: string;
    last_tested?: string;
    models?: string[];
  }> {
    // Send the config object directly
    return this.post<{
      id: string;
      enabled?: boolean;
      config?: Record<string, any>;
      status?: string;
      last_tested?: string;
      models?: string[];
    }>(`/providers/${providerId}/config`, config.config);
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
    return this.get<{ provider: string; models: string[]; queryable: boolean; custom_count?: number }>(`/providers/${providerId}/models`);
  }

  async addCustomModel(providerId: string, modelName: string): Promise<{ success: boolean; message: string }> {
    return this.post<{ success: boolean; message: string }>(`/providers/${providerId}/models`, { model_name: modelName });
  }

  async removeCustomModel(providerId: string, modelName: string): Promise<{ success: boolean; message: string }> {
    return this.delete<{ success: boolean; message: string }>(`/providers/${providerId}/models/${encodeURIComponent(modelName)}`);
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
      const response = await this.get<{
        items: Array<{
          key: string;
          value: any;
          description: string;
        }>;
        timestamp: string;
      }>('/config');
      
      // Look for model selection in the configuration items
      const modelSelectionItem = response.items?.find(item => item.key === 'ai.model_selection');
      
      if (modelSelectionItem && modelSelectionItem.value) {
        // Validate the structure
        const selection = modelSelectionItem.value;
        if (selection.textGeneration && selection.embeddings && 
            typeof selection.sharedProvider === 'boolean') {
          return selection;
        }
      }
      
      return null;
    } catch (error) {
      console.warn('Failed to load model selection configuration:', error);
      return null;
    }
  }

  /**
   * Health and Monitoring Methods
   */

  async getDashboardStats(): Promise<StatsResponse> {
    return this.get<StatsResponse>('/stats');
  }

  async getRecentActivity(): Promise<ActivityItem[]> {
    return this.get<ActivityItem[]>('/admin/activity/recent');
  }



  async createCollection(data: { name: string; description?: string; metadata?: Record<string, unknown> }): Promise<{ id: string; name: string; description?: string; created_at: string }> {
    return this.post<{ id: string; name: string; description?: string; created_at: string }>('/content/collections', data);
  }

  async deleteCollection(collectionId: string): Promise<void> {
    return this.delete<void>(`/content/collections/${collectionId}`);
  }

  async reindexCollection(collectionId: string): Promise<{ success: boolean; message: string }> {
    return this.post<{ success: boolean; message: string }>(`/content/collections/${collectionId}/reindex`, {});
  }


  /**
   * Analytics Methods
   */
  async getAnalytics(timeRange: string = '24h'): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(`/analytics?timeRange=${timeRange}`);
  }

  /**
   * MCP (Model Context Protocol) Methods
   */
  
  // MCP Provider Management
  async getMCPProviders(enabledOnly: boolean = false): Promise<MCPProvidersResponse> {
    const params = enabledOnly ? '?enabled_only=true' : '';
    return this.get<MCPProvidersResponse>(`${API_ENDPOINTS.MCP.PROVIDERS}${params}`);
  }

  async getMCPProvider(providerId: string): Promise<MCPProvider> {
    return this.get<MCPProvider>(API_ENDPOINTS.MCP.PROVIDER(providerId));
  }

  async createMCPProvider(config: MCPProviderConfig): Promise<MCPProvider> {
    return this.post<MCPProvider>(API_ENDPOINTS.MCP.PROVIDERS, { config });
  }

  async updateMCPProvider(providerId: string, updates: Partial<MCPProviderConfig>): Promise<MCPProvider> {
    return this.put<MCPProvider>(API_ENDPOINTS.MCP.PROVIDER(providerId), updates);
  }

  async deleteMCPProvider(providerId: string): Promise<{ message: string }> {
    return this.delete<{ message: string }>(API_ENDPOINTS.MCP.PROVIDER(providerId));
  }

  // MCP Configuration
  async getMCPConfig(): Promise<MCPConfigResponse> {
    return this.get<MCPConfigResponse>(API_ENDPOINTS.MCP.CONFIG);
  }

  async updateMCPConfig(config: MCPSearchConfig): Promise<MCPConfigResponse> {
    return this.post<MCPConfigResponse>(API_ENDPOINTS.MCP.CONFIG, { config });
  }

  // MCP Search
  async performExternalSearch(request: MCPExternalSearchRequest): Promise<MCPExternalSearchResponse> {
    return this.post<MCPExternalSearchResponse>(API_ENDPOINTS.MCP.SEARCH, request);
  }

  // MCP Performance Statistics
  async getMCPStats(): Promise<MCPStatsResponse> {
    return this.get<MCPStatsResponse>(API_ENDPOINTS.MCP.STATS);
  }

  // MCP Provider Testing
  async testMCPProvider(providerId: string, testQuery: string = 'test'): Promise<{
    provider_id: string;
    success: boolean;
    response_time_ms: number;
    results_count: number;
    error_message?: string;
  }> {
    return this.post<{
      provider_id: string;
      success: boolean;
      response_time_ms: number;
      results_count: number;
      error_message?: string;
    }>(`${API_ENDPOINTS.MCP.PROVIDER(providerId)}/test`, { test_query: testQuery });
  }

  /**
   * Ingestion Management Methods
   */
  
  // Ingestion Rules
  async getIngestionRules(): Promise<any[]> {
    return this.get<any[]>('/ingestion/rules');
  }

  async createIngestionRule(rule: any): Promise<any> {
    return this.post<any>('/ingestion/rules', rule);
  }

  async updateIngestionRule(ruleId: string, updates: any): Promise<any> {
    return this.put<any>(`/ingestion/rules/${ruleId}`, updates);
  }

  async deleteIngestionRule(ruleId: string): Promise<void> {
    return this.delete<void>(`/ingestion/rules/${ruleId}`);
  }

  // Ingestion Settings
  async getIngestionSettings(): Promise<any> {
    return this.get<any>('/ingestion/settings');
  }

  async updateIngestionSettings(settings: any): Promise<any> {
    return this.put<any>('/ingestion/settings', settings);
  }

  // Ingestion Jobs
  async getIngestionJobs(params?: { limit?: number; status?: string }): Promise<any[]> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.status) searchParams.set('status', params.status);
    
    const query = searchParams.toString();
    return this.get<any[]>(`/ingestion/jobs${query ? `?${query}` : ''}`);
  }

  async triggerIngestionJob(ruleId: string): Promise<any> {
    return this.post<any>(`/ingestion/rules/${ruleId}/trigger`, {});
  }

  /**
   * Monitoring and Alerts Methods
   */
  
  // Alert Rules
  async getAlertRules(): Promise<any[]> {
    return this.get<any[]>('/monitoring/alerts');
  }

  async updateAlertRule(alertId: string, updates: any): Promise<any> {
    return this.put<any>(`/monitoring/alerts/${alertId}`, updates);
  }

  // Logs
  async getLogs(params?: { limit?: number; level?: string; component?: string }): Promise<any[]> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.level) searchParams.set('level', params.level);
    if (params?.component) searchParams.set('component', params.component);
    
    const query = searchParams.toString();
    return this.get<any[]>(`/monitoring/logs${query ? `?${query}` : ''}`);
  }

  // Dashboard URLs
  async getDashboardUrls(): Promise<any> {
    return this.get<any>('/metrics/dashboards');
  }

  /**
   * System Settings Methods
   */
  
  async getSystemSettings(): Promise<any> {
    return this.get<any>('/system/settings');
  }

  async updateSystemSettings(settings: any): Promise<any> {
    return this.put<any>('/system/settings', settings);
  }

  async resetSystemSettings(): Promise<any> {
    return this.post<any>('/system/settings/reset', {});
  }

  async clearCache(): Promise<any> {
    return this.post<any>('/system/cache/clear', {});
  }

  async rebuildIndexes(): Promise<any> {
    return this.post<any>('/system/indexes/rebuild', {});
  }

  /**
   * Weaviate Vector Database Methods
   */
  
  async getWeaviateConfig(): Promise<any> {
    return this.get<any>('/weaviate/config');
  }

  async updateWeaviateConfig(config: any): Promise<any> {
    return this.put<any>('/weaviate/config', config);
  }

  async testWeaviateConnection(config: any): Promise<{
    success: boolean;
    message: string;
    version?: string;
    workspaces_count?: number;
  }> {
    return this.post<{
      success: boolean;
      message: string;
      version?: string;
      workspaces_count?: number;
    }>('/weaviate/test', config);
  }

  async getWeaviateWorkspaces(): Promise<any[]> {
    return this.get<any[]>('/weaviate/workspaces');
  }

  async getEmbeddingConfig(): Promise<any> {
    // Use central configuration to get embedding config
    try {
      const config = await this.getConfiguration();
      const modelSelectionItem = config.items?.find(item => item.key === 'ai.model_selection');
      if (modelSelectionItem?.value && typeof modelSelectionItem.value === 'object' && 'embeddings' in modelSelectionItem.value) {
        const embeddings = (modelSelectionItem.value as any).embeddings;
        return {
          useDefaultEmbedding: false,
          provider: embeddings.provider || '',
          model: embeddings.model || '',
          dimensions: 768,
          chunkSize: 1000,
          chunkOverlap: 200
        };
      }
    } catch (error) {
      console.warn('[API] Failed to get embedding config from central store:', error);
    }
    
    // Return default config if not found
    return {
      useDefaultEmbedding: true,
      provider: '',
      model: '',
      dimensions: 768,
      chunkSize: 1000,
      chunkOverlap: 200
    };
  }

  async updateEmbeddingConfig(config: any): Promise<any> {
    // Save to central configuration
    if (!config.useDefaultEmbedding && config.provider && config.model) {
      const currentConfig = await this.getConfiguration();
      const modelSelectionItem = currentConfig.items?.find(i => i.key === 'ai.model_selection');
      const currentModelSelection = modelSelectionItem?.value || {};
      
      return this.updateConfiguration({
        key: 'ai.model_selection',
        value: {
          ...(typeof currentModelSelection === 'object' ? currentModelSelection : {}),
          embeddings: {
            provider: config.provider,
            model: config.model
          }
        }
      });
    }
    return config;
  }

  // Model Parameters
  async getModelParameters(provider: string, model: string): Promise<any> {
    // Use central configuration instead of dedicated endpoint
    try {
      const config = await this.getConfiguration();
      const paramKey = `ai.models.${provider}.${model}.parameters`;
      const paramItem = config.items?.find(item => item.key === paramKey);
      return paramItem?.value || null;
    } catch (error) {
      console.warn(`[API] Failed to get model parameters for ${provider}/${model}:`, error);
      return null;
    }
  }

  async updateModelParameters(provider: string, model: string, parameters: any): Promise<any> {
    // Use central configuration instead of dedicated endpoint
    return this.updateConfiguration({
      key: `ai.models.${provider}.${model}.parameters`,
      value: parameters
    });
  }
}

// Export singleton instance
export const apiClient = new DocaicheApiClient();

// Export class for testing or custom instances
export default DocaicheApiClient;