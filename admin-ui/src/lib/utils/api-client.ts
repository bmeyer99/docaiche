/**
 * Centralized API Client for Docaiche Admin Interface
 * 
 * This class provides a unified interface for all API communications
 * with proper error handling, retry logic, and response parsing.
 */

import { 
  API_CONFIG, 
  API_ENDPOINTS, 
  type ApiResponse,
  type ConfigurationResponse,
  type ConfigurationUpdateRequest,
  type HealthResponse,
  type StatsResponse,
  type CollectionsResponse,
  type AdminSearchParams,
  type AdminSearchResponse,
  type UploadResponse,
  type ProblemDetail,
  HTTP_STATUS
} from '../config/api';

// Request options interface
interface RequestOptions {
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
}

// API Client Class
export class DocaicheApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || API_CONFIG.BASE_URL;
    this.defaultHeaders = { ...API_CONFIG.HEADERS };
  }

  /**
   * Generic HTTP request method with retry logic and error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit & RequestOptions = {}
  ): Promise<T> {
    const { timeout = API_CONFIG.TIMEOUTS.DEFAULT, retries = API_CONFIG.RETRY.MAX_ATTEMPTS, ...fetchOptions } = options;
    
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      ...this.defaultHeaders,
      ...options.headers
    };

    let lastError: Error = new Error('Unknown error');
    
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
        return result;

      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on certain errors
        if (error instanceof TypeError || (error as Error).name === 'AbortError') {
          throw this.createApiError('Network Error', (error as Error).message);
        }

        // Wait before retry (exponential backoff)
        if (attempt < retries) {
          const delay = API_CONFIG.RETRY.DELAY_MS * Math.pow(API_CONFIG.RETRY.BACKOFF_MULTIPLIER, attempt - 1);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

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
      throw this.createApiError('API Error', data.message || data.error || 'Unknown error');
    }
    
    // Handle non-JSON responses
    if (response.ok) {
      const text = await response.text();
      return text as unknown as T;
    }
    
    // Handle HTTP errors without JSON body
    throw this.createApiError(
      `HTTP ${response.status}`,
      response.statusText || 'Unknown error'
    );
  }

  /**
   * Check if response data matches RFC 7807 Problem Details format
   */
  private isProblemDetail(data: any): data is ProblemDetail {
    return data && typeof data === 'object' && 'type' in data && 'title' in data && 'status' in data;
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

  async post<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      ...options
    });
  }

  async put<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
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
    return this.get<any[]>('/providers');
  }

  async updateProviderConfiguration(providerId: string, config: any): Promise<any> {
    return this.post<any>(`/providers/${providerId}/config`, config);
  }

  async testProviderConnection(providerId: string, config: any): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.post<{ success: boolean; message: string }>(
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

  /**
   * Health and Monitoring Methods
   */
  async getSystemHealth(): Promise<any> {
    return this.get<any>('/system/health');
  }

  async getSystemMetrics(): Promise<any> {
    return this.get<any>('/system/metrics');
  }

  async getDashboardStats(): Promise<any> {
    return this.get<any>('/stats');
  }

  async getRecentActivity(): Promise<any[]> {
    return this.get<any[]>('/admin/activity/recent');
  }



  async createCollection(data: any): Promise<any> {
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