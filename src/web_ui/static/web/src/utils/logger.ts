// Basic logger utility for the frontend application
// TODO: Integrate with proper logging service in production

export interface LogEvent {
  type: string;
  component?: string;
  action?: string;
  data?: any;
  timestamp?: Date;
  correlationId?: string;
}

export interface ValidationFailure {
  field: string;
  value: any;
  rule: string;
  message: string;
  correlationId?: string;
}

export interface ApiEvent {
  method: string;
  url: string;
  status?: number;
  duration?: number;
  error?: string;
  correlationId?: string;
}

// Static Logger class for consistent logging across the application
export class Logger {
  private static correlationId: string = Math.random().toString(36).substr(2, 9);

  static setCorrelationId(id: string): void {
    Logger.correlationId = id;
  }

  static log(level: 'info' | 'warn' | 'error' | 'debug', message: string, data?: any): void {
    if (process.env.NODE_ENV === 'development') {
      const logData = {
        level,
        message,
        data,
        correlationId: Logger.correlationId,
        timestamp: new Date()
      };
      
      switch (level) {
        case 'error':
          console.error('[Logger]', logData);
          break;
        case 'warn':
          console.warn('[Logger]', logData);
          break;
        case 'debug':
          console.debug('[Logger]', logData);
          break;
        default:
          console.log('[Logger]', logData);
      }
    }
  }

  static info(message: string, data?: any): void {
    Logger.log('info', message, data);
  }

  static warn(message: string, data?: any): void {
    Logger.log('warn', message, data);
  }

  static error(message: string, data?: any): void {
    Logger.log('error', message, data);
  }

  static debug(message: string, data?: any): void {
    Logger.log('debug', message, data);
  }
}

// Log application events (supports both single object and legacy two-argument format)
export function logEvent(eventOrType: LogEvent | string, data?: any): void {
  let event: LogEvent;
  
  if (typeof eventOrType === 'string') {
    // Legacy format: logEvent('type', { data })
    event = {
      type: eventOrType,
      ...data,
      timestamp: new Date()
    };
  } else {
    // New format: logEvent({ type: 'type', data: {} })
    event = {
      ...eventOrType,
      timestamp: eventOrType.timestamp || new Date()
    };
  }

  if (process.env.NODE_ENV === 'development') {
    console.log('[Event]', event);
  }
  // TODO: Send to analytics service in production
}

// Log validation failures for debugging
export function logValidationFailure(failure: ValidationFailure): void {
  if (process.env.NODE_ENV === 'development') {
    console.warn('[Validation]', failure);
  }
  // TODO: Send to error tracking service
}

// Log API events for monitoring (supports both single object and legacy two-argument format)
export function logApiEvent(eventOrType: ApiEvent | string, data?: any): void {
  let event: ApiEvent;
  
  if (typeof eventOrType === 'string') {
    // Legacy format: logApiEvent('type', { data })
    event = {
      method: 'GET', // default
      url: eventOrType,
      ...data
    };
  } else {
    // New format: logApiEvent({ method: 'GET', url: '/api', ... })
    event = eventOrType;
  }

  if (process.env.NODE_ENV === 'development') {
    console.log('[API]', event);
  }
  // TODO: Send to monitoring service
}

// Redact sensitive information from objects
export function redactSecrets(obj: any): any {
  if (!obj || typeof obj !== 'object') return obj;
  
  const redacted = { ...obj };
  const sensitiveKeys = ['password', 'apiKey', 'token', 'secret', 'key'];
  
  Object.keys(redacted).forEach(key => {
    if (sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive))) {
      redacted[key] = '[REDACTED]';
    } else if (typeof redacted[key] === 'object') {
      redacted[key] = redactSecrets(redacted[key]);
    }
  });
  
  return redacted;
}