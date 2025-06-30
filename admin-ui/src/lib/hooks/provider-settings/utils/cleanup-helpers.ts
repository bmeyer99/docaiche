/**
 * Cleanup utilities for preventing memory leaks
 */

import { useRef, useEffect, useCallback, MutableRefObject } from 'react';

/**
 * Hook to track if component is mounted
 */
export function useIsMounted(): () => boolean {
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return useCallback(() => isMountedRef.current, []);
}

/**
 * Hook to create a mounted ref
 */
export function useMountedRef(): MutableRefObject<boolean> {
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return mountedRef;
}

/**
 * Creates a cancellable promise wrapper
 */
export interface CancellablePromise<T> {
  promise: Promise<T>;
  cancel: () => void;
}

export function makeCancellable<T>(promise: Promise<T>): CancellablePromise<T> {
  let hasCancelled = false;

  const wrappedPromise = new Promise<T>((resolve, reject) => {
    promise
      .then((val) => {
        if (!hasCancelled) {
          resolve(val);
        }
      })
      .catch((error) => {
        if (!hasCancelled) {
          reject(error);
        }
      });
  });

  return {
    promise: wrappedPromise,
    cancel() {
      hasCancelled = true;
    },
  };
}

/**
 * Creates an AbortController with timeout
 */
export function createAbortController(timeoutMs?: number): AbortController {
  const controller = new AbortController();

  if (timeoutMs) {
    const timeoutId = setTimeout(() => {
      controller.abort(new Error('Request timeout'));
    }, timeoutMs);

    // Cleanup timeout when abort is called manually
    const originalAbort = controller.abort.bind(controller);
    controller.abort = (reason?: any) => {
      clearTimeout(timeoutId);
      originalAbort(reason);
    };
  }

  return controller;
}

/**
 * Request deduplication helper
 */
export class RequestDeduplicator<T> {
  private pendingRequests = new Map<string, CancellablePromise<T>>();

  async deduplicate(
    key: string,
    requestFn: (signal: AbortSignal) => Promise<T>,
    signal?: AbortSignal
  ): Promise<T> {
    // Check if there's already a pending request
    const pending = this.pendingRequests.get(key);
    if (pending) {
      return pending.promise;
    }

    // Create new abortable request
    const controller = new AbortController();
    
    // Forward parent abort signal
    if (signal) {
      signal.addEventListener('abort', () => {
        controller.abort(signal.reason);
      });
    }

    const cancellable = makeCancellable(
      requestFn(controller.signal).finally(() => {
        this.pendingRequests.delete(key);
      })
    );

    this.pendingRequests.set(key, cancellable);

    return cancellable.promise;
  }

  cancelAll(): void {
    this.pendingRequests.forEach((request) => {
      request.cancel();
    });
    this.pendingRequests.clear();
  }

  cancel(key: string): void {
    const request = this.pendingRequests.get(key);
    if (request) {
      request.cancel();
      this.pendingRequests.delete(key);
    }
  }
}

/**
 * Save queue to prevent overlapping saves
 */
export class SaveQueue<T> {
  private queue: Array<() => Promise<T>> = [];
  private isProcessing = false;
  private currentRequest: CancellablePromise<T> | null = null;

  async enqueue(saveFn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await saveFn();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });

      if (!this.isProcessing) {
        this.processQueue();
      }
    });
  }

  private async processQueue(): Promise<void> {
    if (this.queue.length === 0) {
      this.isProcessing = false;
      return;
    }

    this.isProcessing = true;
    const task = this.queue.shift()!;

    try {
      const cancellable = makeCancellable(task());
      this.currentRequest = cancellable;
      await cancellable.promise;
    } catch (error) {
      // Log error but continue processing queue
      console.error('Save queue error:', error);
    } finally {
      this.currentRequest = null;
      // Process next item
      this.processQueue();
    }
  }

  cancelAll(): void {
    this.queue = [];
    if (this.currentRequest) {
      this.currentRequest.cancel();
      this.currentRequest = null;
    }
    this.isProcessing = false;
  }
}

/**
 * Cleanup manager for handling multiple cleanup tasks
 */
export class CleanupManager {
  private cleanupTasks: Array<() => void> = [];

  register(cleanup: () => void): void {
    this.cleanupTasks.push(cleanup);
  }

  cleanup(): void {
    this.cleanupTasks.forEach((task) => {
      try {
        task();
      } catch (error) {
        console.error('Cleanup error:', error);
      }
    });
    this.cleanupTasks = [];
  }
}

/**
 * Hook for managing cleanup tasks
 */
export function useCleanup(): CleanupManager {
  const managerRef = useRef<CleanupManager | null>(null);

  if (!managerRef.current) {
    managerRef.current = new CleanupManager();
  }

  useEffect(() => {
    return () => {
      managerRef.current?.cleanup();
    };
  }, []);

  return managerRef.current;
}