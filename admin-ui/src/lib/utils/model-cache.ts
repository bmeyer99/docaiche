/**
 * Model Cache Manager
 * Manages caching of provider models in localStorage to minimize API calls
 */

interface ModelCacheEntry {
  models: string[];
  timestamp: string;
  ttl?: number; // Time to live in milliseconds
}

interface ModelCache {
  [providerId: string]: ModelCacheEntry;
}

const CACHE_KEY = 'docaiche_provider_models';
const DEFAULT_TTL = 24 * 60 * 60 * 1000; // 24 hours

export class ModelCacheManager {
  /**
   * Get cached models for a provider
   * Returns null if not found or expired
   */
  static getModels(providerId: string): string[] | null {
    try {
      const cacheStr = localStorage.getItem(CACHE_KEY);
      if (!cacheStr) return null;

      const cache: ModelCache = JSON.parse(cacheStr);
      const entry = cache[providerId];
      
      if (!entry) return null;

      // Check if cache is expired
      const entryTime = new Date(entry.timestamp).getTime();
      const ttl = entry.ttl || DEFAULT_TTL;
      const now = Date.now();

      if (now - entryTime > ttl) {
        // Cache expired, remove this entry
        this.removeProvider(providerId);
        return null;
      }

      return entry.models;
    } catch (error) {
      console.error('Error reading model cache:', error);
      return null;
    }
  }

  /**
   * Set models for a provider
   */
  static setModels(providerId: string, models: string[], ttl?: number): void {
    try {
      const cacheStr = localStorage.getItem(CACHE_KEY);
      const cache: ModelCache = cacheStr ? JSON.parse(cacheStr) : {};

      cache[providerId] = {
        models,
        timestamp: new Date().toISOString(),
        ttl: ttl || DEFAULT_TTL
      };

      localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
    } catch (error) {
      console.error('Error setting model cache:', error);
    }
  }

  /**
   * Remove a specific provider from cache
   */
  static removeProvider(providerId: string): void {
    try {
      const cacheStr = localStorage.getItem(CACHE_KEY);
      if (!cacheStr) return;

      const cache: ModelCache = JSON.parse(cacheStr);
      delete cache[providerId];

      if (Object.keys(cache).length === 0) {
        localStorage.removeItem(CACHE_KEY);
      } else {
        localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
      }
    } catch (error) {
      console.error('Error removing from model cache:', error);
    }
  }

  /**
   * Clear all cached models
   */
  static clearAll(): void {
    try {
      localStorage.removeItem(CACHE_KEY);
    } catch (error) {
      console.error('Error clearing model cache:', error);
    }
  }

  /**
   * Get all cached data (for debugging)
   */
  static getAll(): ModelCache | null {
    try {
      const cacheStr = localStorage.getItem(CACHE_KEY);
      return cacheStr ? JSON.parse(cacheStr) : null;
    } catch (error) {
      console.error('Error getting all cache:', error);
      return null;
    }
  }

  /**
   * Check if provider has cached models (without checking expiry)
   */
  static hasProvider(providerId: string): boolean {
    try {
      const cacheStr = localStorage.getItem(CACHE_KEY);
      if (!cacheStr) return false;

      const cache: ModelCache = JSON.parse(cacheStr);
      return providerId in cache;
    } catch (error) {
      return false;
    }
  }
}

// Export for convenience
export const modelCache = ModelCacheManager;