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

  constructor() {
    // Start the flush timer
    this.startTimer();
    
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

  private async flush() {
    if (this.buffer.length === 0 || this.isShipping) return;
    
    // Skip if we've failed too many times
    if (this.failedAttempts >= this.maxFailedAttempts) {
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
      this.failedAttempts = 0;
    } catch (error) {
      this.failedAttempts++;
      
      // Put logs back in buffer if there's room and we haven't failed too many times
      if (this.buffer.length < this.maxBufferSize && this.failedAttempts < this.maxFailedAttempts) {
        this.buffer.unshift(...logs.slice(0, this.maxBufferSize - this.buffer.length));
      }
      
      // Stop trying after too many failures
      if (this.failedAttempts >= this.maxFailedAttempts && this.timer) {
        clearInterval(this.timer);
        this.timer = null;
        console.warn('[BrowserLogger] Stopped shipping logs due to repeated failures');
      }
    } finally {
      this.isShipping = false;
    }
  }

  private log(level: LogEntry['level'], message: string, metadata?: Record<string, any>) {
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
}

// Create singleton instance
export const browserLogger = new BrowserLogger();

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