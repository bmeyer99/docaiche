/**
 * Browser-side logger that ships logs to backend Loki via API
 */

interface LogEntry {
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  timestamp: string;
  metadata?: Record<string, any>;
  stackTrace?: string;
}

class BrowserLogger {
  private buffer: LogEntry[] = [];
  private flushInterval: number = 5000; // 5 seconds
  private maxBufferSize: number = 50;
  private timer: NodeJS.Timeout | null = null;
  private endpoint: string = '/api/v1/logs/browser';
  private failedAttempts: number = 0;
  private maxFailedAttempts: number = 3;
  private isShipping: boolean = false;
  private retryDelay: number = 1000; // Initial retry delay: 1 second
  private maxRetryDelay: number = 30000; // Max retry delay: 30 seconds
  private retryTimer: NodeJS.Timeout | null = null;
  private lastFailureTime: number = 0;
  private recoveryCheckInterval: number = 30000; // Check for recovery every 30 seconds

  constructor() {
    // Start the flush timer
    this.startTimer();
    
    // Start recovery check timer
    this.startRecoveryTimer();
    
    // Flush on page unload
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => this.flush());
    }
  }

  private startTimer() {
    this.timer = setInterval(() => {
      if (this.buffer.length > 0) {
        this.flush();
      }
    }, this.flushInterval);
  }

  private startRecoveryTimer() {
    // Periodically check if we should retry after failures
    setInterval(() => {
      if (this.failedAttempts >= this.maxFailedAttempts && this.lastFailureTime > 0) {
        const timeSinceLastFailure = Date.now() - this.lastFailureTime;
        
        // Try to recover after the recovery interval
        if (timeSinceLastFailure >= this.recoveryCheckInterval) {
          console.info('[BrowserLogger] Attempting recovery after prolonged failure');
          this.resetFailedAttempts();
          
          // If we have buffered logs, try to flush them
          if (this.buffer.length > 0) {
            this.flush();
          }
        }
      }
    }, this.recoveryCheckInterval);
  }

  private resetFailedAttempts() {
    this.failedAttempts = 0;
    this.retryDelay = 1000; // Reset to initial retry delay
    this.lastFailureTime = 0;
    
    // Clear any existing retry timer
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }

  private scheduleRetry() {
    // Clear any existing retry timer
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
    }

    // Calculate exponential backoff delay
    const delay = Math.min(this.retryDelay * Math.pow(2, this.failedAttempts - 1), this.maxRetryDelay);
    
    console.warn(`[BrowserLogger] Scheduling retry in ${delay / 1000} seconds (attempt ${this.failedAttempts}/${this.maxFailedAttempts})`);
    
    this.retryTimer = setTimeout(() => {
      if (this.buffer.length > 0) {
        this.flush();
      }
    }, delay);
  }

  private async flush() {
    if (this.buffer.length === 0 || this.isShipping) return;
    
    // Don't immediately retry if we're in backoff period
    if (this.retryTimer && this.failedAttempts > 0) {
      return;
    }

    this.isShipping = true;
    const logs = [...this.buffer];
    this.buffer = [];

    try {
      const response = await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          streams: [{
            stream: {
              app: 'docaiche-admin-ui',
              component: 'browser',
              environment: 'production',
            },
            values: logs.map(log => [
              String(Date.now() * 1000000), // nanoseconds
              JSON.stringify(log)
            ])
          }]
        }),
      });
      
      // Check response status
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      // Reset failed attempts on success
      this.resetFailedAttempts();
      console.info('[BrowserLogger] Successfully shipped logs after recovery');
    } catch (error) {
      this.failedAttempts++;
      this.lastFailureTime = Date.now();
      
      // Put logs back in buffer if there's room
      if (this.buffer.length < this.maxBufferSize) {
        this.buffer.unshift(...logs.slice(0, this.maxBufferSize - this.buffer.length));
      }
      
      // Log detailed error information
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`[BrowserLogger] Failed to ship logs (attempt ${this.failedAttempts}): ${errorMessage}`, {
        endpoint: this.endpoint,
        logsCount: logs.length,
        bufferSize: this.buffer.length,
        error: error
      });
      
      // Schedule retry with exponential backoff
      if (this.failedAttempts < this.maxFailedAttempts) {
        this.scheduleRetry();
      } else {
        console.warn(`[BrowserLogger] Max failures reached. Will retry in ${this.recoveryCheckInterval / 1000} seconds`);
        // Don't stop the timer completely - let recovery mechanism handle it
      }
    } finally {
      this.isShipping = false;
    }
  }

  private log(level: LogEntry['level'], message: string, metadata?: Record<string, any>) {
    // Skip logging when on the logs page to prevent infinite loops
    if (window.location.pathname.includes('/dashboard/logs')) {
      // Still log to console for debugging
      if (process.env.NODE_ENV === 'development') {
        console[level](`[BrowserLogger-Skipped] ${message}`, metadata);
      }
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      metadata: {
        ...metadata,
        userAgent: navigator.userAgent,
        url: window.location.href,
      }
    };

    // Add to buffer
    this.buffer.push(entry);

    // Flush if buffer is full
    if (this.buffer.length >= this.maxBufferSize) {
      this.flush();
    }

    // Also log to console in development
    if (process.env.NODE_ENV === 'development') {
      console[level](`[BrowserLogger] ${message}`, metadata);
    }
  }

  debug(message: string, metadata?: Record<string, any>) {
    this.log('debug', message, metadata);
  }

  info(message: string, metadata?: Record<string, any>) {
    this.log('info', message, metadata);
  }

  warn(message: string, metadata?: Record<string, any>) {
    this.log('warn', message, metadata);
  }

  error(message: string, error?: Error | any, metadata?: Record<string, any>) {
    const errorData = error instanceof Error ? {
      name: error.name,
      message: error.message,
      stack: error.stack,
    } : error;

    this.log('error', message, {
      ...metadata,
      error: errorData,
      stackTrace: error?.stack,
    });
  }

  // Method to track API calls
  trackApiCall(method: string, url: string, status?: number, error?: any) {
    const message = `API ${method} ${url} - ${status || 'pending'}`;
    
    if (error || (status && status >= 400)) {
      this.error(message, error, {
        apiCall: { method, url, status }
      });
    } else if (process.env.NODE_ENV === 'development') {
      // Only log successful API calls in development
      this.debug(message, {
        apiCall: { method, url, status }
      });
    }
  }

  // Public method to manually reset the logger state
  reset() {
    console.info('[BrowserLogger] Manually resetting logger state');
    this.resetFailedAttempts();
    
    // Restart timer if it was stopped
    if (!this.timer) {
      this.startTimer();
    }
    
    // Try to flush any buffered logs
    if (this.buffer.length > 0) {
      this.flush();
    }
  }

  // Get current logger status for debugging
  getStatus() {
    return {
      bufferSize: this.buffer.length,
      failedAttempts: this.failedAttempts,
      isShipping: this.isShipping,
      hasRetryTimer: !!this.retryTimer,
      hasFlushTimer: !!this.timer,
      lastFailureTime: this.lastFailureTime ? new Date(this.lastFailureTime).toISOString() : null,
      timeSinceLastFailure: this.lastFailureTime ? Date.now() - this.lastFailureTime : null
    };
  }
}

// Create singleton instance
export const browserLogger = new BrowserLogger();

// Make logger available globally in development for debugging
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  (window as any).browserLogger = browserLogger;
  console.info('[BrowserLogger] Logger available at window.browserLogger for debugging');
}

// Monkey-patch fetch to track API calls
if (typeof window !== 'undefined') {
  const originalFetch = window.fetch;
  
  window.fetch = async (...args) => {
    const [input, init] = args;
    const method = init?.method || 'GET';
    const url = typeof input === 'string' ? input : (input instanceof Request ? input.url : input.toString());
    
    // Skip logging browser log endpoints to prevent infinite loops
    // Also skip logging pending requests in production
    if (!url.includes('/logs/browser') && process.env.NODE_ENV === 'development') {
      // Log the request
      browserLogger.trackApiCall(method, url);
    }
    
    try {
      const response = await originalFetch(...args);
      
      // Log the response (skip logging browser log endpoints)
      if (!url.includes('/logs/browser')) {
        browserLogger.trackApiCall(method, url, response.status);
      }
      
      // Only track model loading calls in development or if there's an error
      if (url.includes('/providers/') && url.includes('/models') && (process.env.NODE_ENV === 'development' || response.status >= 400)) {
        browserLogger.debug('Model loading API call', {
          url,
          status: response.status
        });
      }
      
      return response;
    } catch (error) {
      if (!url.includes('/logs/browser')) {
        browserLogger.trackApiCall(method, url, 0, error);
      }
      throw error;
    }
  };
}