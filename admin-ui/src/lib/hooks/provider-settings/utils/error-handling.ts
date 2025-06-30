/**
 * Comprehensive error handling and resilience utilities for provider settings system
 */

// ============================================================================
// Custom Error Classes
// ============================================================================

export abstract class ProviderSettingsError extends Error {
  public readonly timestamp: Date;
  public readonly context: Record<string, any>;
  public readonly recoverable: boolean;

  constructor(
    message: string,
    context: Record<string, any> = {},
    recoverable = true
  ) {
    super(message);
    this.name = this.constructor.name;
    this.timestamp = new Date();
    this.context = context;
    this.recoverable = recoverable;
    
    // Maintain proper stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      timestamp: this.timestamp.toISOString(),
      context: this.context,
      recoverable: this.recoverable,
      stack: this.stack,
    };
  }
}

export class NetworkError extends ProviderSettingsError {
  constructor(message: string, context: Record<string, any> = {}) {
    super(`Network error: ${message}`, context, true);
  }
}

export class ValidationError extends ProviderSettingsError {
  public readonly fieldPath: string;
  public readonly validationErrors: string[];

  constructor(
    fieldPath: string,
    validationErrors: string[],
    context: Record<string, any> = {}
  ) {
    super(
      `Validation failed for ${fieldPath}: ${validationErrors.join(', ')}`,
      { ...context, fieldPath, validationErrors },
      true
    );
    this.fieldPath = fieldPath;
    this.validationErrors = validationErrors;
  }
}

export class ConflictError extends ProviderSettingsError {
  public readonly conflictedFields: string[];
  public readonly serverVersion: string;
  public readonly clientVersion: string;

  constructor(
    conflictedFields: string[],
    serverVersion: string,
    clientVersion: string,
    context: Record<string, any> = {}
  ) {
    super(
      `Conflict detected in fields: ${conflictedFields.join(', ')}`,
      { ...context, conflictedFields, serverVersion, clientVersion },
      true
    );
    this.conflictedFields = conflictedFields;
    this.serverVersion = serverVersion;
    this.clientVersion = clientVersion;
  }
}

export class PartialFailureError extends ProviderSettingsError {
  public readonly successfulOperations: string[];
  public readonly failedOperations: Array<{ operation: string; error: Error }>;

  constructor(
    successfulOperations: string[],
    failedOperations: Array<{ operation: string; error: Error }>,
    context: Record<string, any> = {}
  ) {
    const failedOps = failedOperations.map(f => f.operation).join(', ');
    super(
      `Partial failure: succeeded ${successfulOperations.length}, failed ${failedOperations.length} operations (${failedOps})`,
      { ...context, successfulOperations, failedOperations },
      true
    );
    this.successfulOperations = successfulOperations;
    this.failedOperations = failedOperations;
  }
}

export class TimeoutError extends ProviderSettingsError {
  public readonly operation: string;
  public readonly timeoutMs: number;

  constructor(operation: string, timeoutMs: number, context: Record<string, any> = {}) {
    super(
      `Operation '${operation}' timed out after ${timeoutMs}ms`,
      { ...context, operation, timeoutMs },
      true
    );
    this.operation = operation;
    this.timeoutMs = timeoutMs;
  }
}

export class SystemError extends ProviderSettingsError {
  constructor(message: string, context: Record<string, any> = {}) {
    super(`System error: ${message}`, context, false);
  }
}

// ============================================================================
// Retry Mechanism with Exponential Backoff
// ============================================================================

export interface RetryOptions {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
  backoffFactor: number;
  jitter: boolean;
  retryCondition?: (error: Error) => boolean;
  onRetry?: (attempt: number, error: Error) => void;
}

export const DEFAULT_RETRY_OPTIONS: RetryOptions = {
  maxAttempts: 3,
  baseDelayMs: 1000,
  maxDelayMs: 10000,
  backoffFactor: 2,
  jitter: true,
  retryCondition: (error) => {
    // Retry on network errors, timeouts, and server errors
    if (error instanceof NetworkError || error instanceof TimeoutError) {
      return true;
    }
    
    // Retry on specific HTTP status codes
    if ('status' in error) {
      const status = (error as any).status;
      return status >= 500 || status === 408 || status === 429;
    }
    
    return false;
  },
};

export class RetryManager {
  private options: RetryOptions;

  constructor(options: Partial<RetryOptions> = {}) {
    this.options = { ...DEFAULT_RETRY_OPTIONS, ...options };
  }

  async execute<T>(
    operation: () => Promise<T>,
    operationName: string,
    signal?: AbortSignal
  ): Promise<T> {
    let lastError: Error | null = null;
    
    for (let attempt = 1; attempt <= this.options.maxAttempts; attempt++) {
      try {
        // Check if operation was cancelled
        if (signal?.aborted) {
          throw new Error('Operation cancelled');
        }

        return await operation();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        // Check if this is the last attempt
        if (attempt === this.options.maxAttempts) {
          break;
        }

        // Check if we should retry this error
        if (!this.options.retryCondition!(lastError)) {
          break;
        }

        // Check if operation was cancelled
        if (signal?.aborted) {
          throw new Error('Operation cancelled');
        }

        // Calculate delay with exponential backoff
        const delay = this.calculateDelay(attempt);
        
        // Call retry callback if provided
        this.options.onRetry?.(attempt, lastError);

        // Wait before retrying
        await this.delay(delay, signal);
      }
    }

    // If we get here, all attempts failed
    throw new Error(`Operation '${operationName}' failed after ${this.options.maxAttempts} attempts. Last error: ${lastError?.message}`);
  }

  private calculateDelay(attempt: number): number {
    let delay = this.options.baseDelayMs * Math.pow(this.options.backoffFactor, attempt - 1);
    
    // Apply maximum delay limit
    delay = Math.min(delay, this.options.maxDelayMs);
    
    // Add jitter to prevent thundering herd
    if (this.options.jitter) {
      delay = delay * (0.5 + Math.random() * 0.5);
    }
    
    return Math.floor(delay);
  }

  private delay(ms: number, signal?: AbortSignal): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(resolve, ms);
      
      const onAbort = () => {
        clearTimeout(timeout);
        reject(new Error('Operation cancelled'));
      };
      
      signal?.addEventListener('abort', onAbort, { once: true });
      
      // Clean up listener when promise resolves
      setTimeout(() => {
        signal?.removeEventListener('abort', onAbort);
      }, ms);
    });
  }
}

// ============================================================================
// Circuit Breaker Pattern
// ============================================================================

export interface CircuitBreakerOptions {
  failureThreshold: number;
  resetTimeoutMs: number;
  monitoringPeriodMs: number;
}

export enum CircuitState {
  CLOSED = 'closed',
  OPEN = 'open',
  HALF_OPEN = 'half_open',
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private lastFailureTime = 0;
  private successCount = 0;
  
  constructor(private options: CircuitBreakerOptions) {}

  async execute<T>(operation: () => Promise<T>, operationName: string): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() - this.lastFailureTime < this.options.resetTimeoutMs) {
        throw new Error(`Circuit breaker is OPEN for operation '${operationName}'`);
      } else {
        this.state = CircuitState.HALF_OPEN;
        this.successCount = 0;
      }
    }

    try {
      const result = await operation();
      
      if (this.state === CircuitState.HALF_OPEN) {
        this.successCount++;
        if (this.successCount >= 3) { // Require 3 successes to fully close
          this.state = CircuitState.CLOSED;
          this.failureCount = 0;
        }
      } else if (this.state === CircuitState.CLOSED) {
        this.failureCount = 0;
      }
      
      return result;
    } catch (error) {
      this.failureCount++;
      this.lastFailureTime = Date.now();
      
      if (this.state === CircuitState.HALF_OPEN || 
          this.failureCount >= this.options.failureThreshold) {
        this.state = CircuitState.OPEN;
      }
      
      throw error;
    }
  }

  getState(): CircuitState {
    return this.state;
  }

  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.lastFailureTime = 0;
    this.successCount = 0;
  }
}

// ============================================================================
// Error Recovery Strategies
// ============================================================================

export interface RecoveryStrategy {
  canRecover(error: Error): boolean;
  recover(error: Error, context: any): Promise<any>;
  name: string;
}

export class NetworkRecoveryStrategy implements RecoveryStrategy {
  name = 'network-recovery';

  canRecover(error: Error): boolean {
    return error instanceof NetworkError || 
           !!(error.message && error.message.includes('network')) ||
           !!(error.message && error.message.includes('fetch'));
  }

  async recover(error: Error, context: any): Promise<any> {
    // Wait a bit and try to check network connectivity
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Return a partial recovery instruction
    return {
      type: 'retry',
      message: 'Network error detected. Please check your connection and try again.',
      actions: ['retry', 'offline-mode']
    };
  }
}

export class ValidationRecoveryStrategy implements RecoveryStrategy {
  name = 'validation-recovery';

  canRecover(error: Error): boolean {
    return error instanceof ValidationError;
  }

  async recover(error: ValidationError, context: any): Promise<any> {
    return {
      type: 'user-input-required',
      message: `Please fix the following validation errors: ${error.validationErrors.join(', ')}`,
      fieldPath: error.fieldPath,
      validationErrors: error.validationErrors,
      actions: ['fix-validation']
    };
  }
}

export class ConflictRecoveryStrategy implements RecoveryStrategy {
  name = 'conflict-recovery';

  canRecover(error: Error): boolean {
    return error instanceof ConflictError;
  }

  async recover(error: ConflictError, context: any): Promise<any> {
    return {
      type: 'merge-required',
      message: 'Your changes conflict with recent server changes. Please review and merge.',
      conflictedFields: error.conflictedFields,
      serverVersion: error.serverVersion,
      clientVersion: error.clientVersion,
      actions: ['merge', 'overwrite', 'reload']
    };
  }
}

export class ErrorRecoveryManager {
  private strategies: RecoveryStrategy[] = [
    new NetworkRecoveryStrategy(),
    new ValidationRecoveryStrategy(),
    new ConflictRecoveryStrategy(),
  ];

  addStrategy(strategy: RecoveryStrategy): void {
    this.strategies.push(strategy);
  }

  async tryRecover(error: Error, context: any = {}): Promise<any> {
    for (const strategy of this.strategies) {
      if (strategy.canRecover(error)) {
        try {
          return await strategy.recover(error, context);
        } catch (recoveryError) {
          console.warn(`Recovery strategy '${strategy.name}' failed:`, recoveryError);
        }
      }
    }

    // No recovery strategy found
    return {
      type: 'unrecoverable',
      message: error.message,
      actions: ['reload', 'report']
    };
  }
}

// ============================================================================
// Optimistic Updates with Rollback
// ============================================================================

export interface OptimisticUpdate<T> {
  id: string;
  operation: string;
  previousState: T;
  newState: T;
  timestamp: Date;
  rollback: () => void;
}

export class OptimisticUpdateManager<T> {
  private updates: Map<string, OptimisticUpdate<T>> = new Map();
  private rollbackStack: string[] = [];

  addUpdate(
    id: string,
    operation: string,
    previousState: T,
    newState: T,
    rollback: () => void
  ): void {
    const update: OptimisticUpdate<T> = {
      id,
      operation,
      previousState,
      newState,
      timestamp: new Date(),
      rollback,
    };

    this.updates.set(id, update);
    this.rollbackStack.push(id);
  }

  confirmUpdate(id: string): void {
    this.updates.delete(id);
    const index = this.rollbackStack.indexOf(id);
    if (index > -1) {
      this.rollbackStack.splice(index, 1);
    }
  }

  rollbackUpdate(id: string): void {
    const update = this.updates.get(id);
    if (update) {
      update.rollback();
      this.confirmUpdate(id);
    }
  }

  rollbackAll(): void {
    // Rollback in reverse order (LIFO)
    const idsToRollback = [...this.rollbackStack].reverse();
    for (const id of idsToRollback) {
      this.rollbackUpdate(id);
    }
  }

  getPendingUpdates(): OptimisticUpdate<T>[] {
    return Array.from(this.updates.values());
  }

  hasPendingUpdates(): boolean {
    return this.updates.size > 0;
  }

  clear(): void {
    this.updates.clear();
    this.rollbackStack.length = 0;
  }
}

// ============================================================================
// Error Context Manager
// ============================================================================

export interface ErrorContext {
  component?: string;
  operation?: string;
  userId?: string;
  sessionId?: string;
  timestamp: Date;
  userAgent?: string;
  url?: string;
  additionalData?: Record<string, any>;
}

export class ErrorContextManager {
  private static instance: ErrorContextManager;
  private context: Partial<ErrorContext> = {};

  static getInstance(): ErrorContextManager {
    if (!ErrorContextManager.instance) {
      ErrorContextManager.instance = new ErrorContextManager();
    }
    return ErrorContextManager.instance;
  }

  setContext(context: Partial<ErrorContext>): void {
    this.context = { ...this.context, ...context };
  }

  getContext(): Partial<ErrorContext> {
    return {
      ...this.context,
      timestamp: new Date(),
      userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : undefined,
      url: typeof window !== 'undefined' ? window.location.href : undefined,
    };
  }

  clearContext(): void {
    this.context = {};
  }

  withContext<T>(context: Partial<ErrorContext>, fn: () => T): T {
    const originalContext = { ...this.context };
    this.setContext(context);
    
    try {
      return fn();
    } finally {
      this.context = originalContext;
    }
  }
}

// ============================================================================
// Error Reporting and Logging
// ============================================================================

export interface ErrorReport {
  error: ProviderSettingsError;
  context: ErrorContext;
  userActions: string[];
  resolution?: string;
}

export class ErrorReporter {
  private reports: ErrorReport[] = [];
  private maxReports = 100;

  report(error: Error, userActions: string[] = [], resolution?: string): void {
    const contextManager = ErrorContextManager.getInstance();
    const context = contextManager.getContext() as ErrorContext;
    
    const providerError = error instanceof ProviderSettingsError 
      ? error 
      : new SystemError(error.message, { originalError: error });

    const report: ErrorReport = {
      error: providerError,
      context,
      userActions,
      resolution,
    };

    this.reports.push(report);
    
    // Keep only the most recent reports
    if (this.reports.length > this.maxReports) {
      this.reports.shift();
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error Report:', report);
    }

    // In production, you might want to send to an error tracking service
    // this.sendToErrorTrackingService(report);
  }

  getReports(): ErrorReport[] {
    return [...this.reports];
  }

  clearReports(): void {
    this.reports.length = 0;
  }

  exportReports(): string {
    return JSON.stringify(this.reports, null, 2);
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

export function isRetryableError(error: Error): boolean {
  return DEFAULT_RETRY_OPTIONS.retryCondition!(error);
}

export function categorizeError(error: Error): string {
  if (error instanceof NetworkError) return 'network';
  if (error instanceof ValidationError) return 'validation';
  if (error instanceof ConflictError) return 'conflict';
  if (error instanceof PartialFailureError) return 'partial-failure';
  if (error instanceof TimeoutError) return 'timeout';
  if (error instanceof SystemError) return 'system';
  return 'unknown';
}

export function createUserFriendlyMessage(error: Error): string {
  if (error instanceof NetworkError) {
    return 'Unable to connect to the server. Please check your internet connection and try again.';
  }
  
  if (error instanceof ValidationError) {
    return `Please fix the following issues: ${error.validationErrors.join(', ')}`;
  }
  
  if (error instanceof ConflictError) {
    return 'Your changes conflict with recent updates. Please review and merge the changes.';
  }
  
  if (error instanceof TimeoutError) {
    return `The operation took too long to complete. Please try again.`;
  }
  
  if (error instanceof PartialFailureError) {
    return `Some changes were saved successfully, but ${error.failedOperations.length} operations failed. Please review and retry.`;
  }
  
  return error.message || 'An unexpected error occurred. Please try again.';
}

// ============================================================================
// Global Error Handler
// ============================================================================

export class GlobalErrorHandler {
  private static instance: GlobalErrorHandler;
  private reporter: ErrorReporter;
  private recoveryManager: ErrorRecoveryManager;
  private retryManager: RetryManager;

  private constructor() {
    this.reporter = new ErrorReporter();
    this.recoveryManager = new ErrorRecoveryManager();
    this.retryManager = new RetryManager();
  }

  static getInstance(): GlobalErrorHandler {
    if (!GlobalErrorHandler.instance) {
      GlobalErrorHandler.instance = new GlobalErrorHandler();
    }
    return GlobalErrorHandler.instance;
  }

  async handle(error: Error, context: any = {}): Promise<any> {
    // Report the error
    this.reporter.report(error);

    // Try to recover
    const recovery = await this.recoveryManager.tryRecover(error, context);

    return {
      error,
      recovery,
      userMessage: createUserFriendlyMessage(error),
      canRetry: isRetryableError(error),
      category: categorizeError(error),
    };
  }

  getReporter(): ErrorReporter {
    return this.reporter;
  }

  getRecoveryManager(): ErrorRecoveryManager {
    return this.recoveryManager;
  }

  getRetryManager(): RetryManager {
    return this.retryManager;
  }
}