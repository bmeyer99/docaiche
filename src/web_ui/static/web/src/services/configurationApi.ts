// src/web_ui/static/web/src/services/configurationApi.ts

import { redactSecrets, logApiEvent } from '../utils/logger';

export interface Configuration {
  // Define all config fields as per API contract
  [key: string]: any;
}

export interface SaveConfigRequest {
  config: Configuration;
  csrfToken: string;
}

export interface TestConnectionRequest {
  baseUrl: string;
  apiKey?: string;
  [key: string]: any;
}

export interface TestConnectionResponse {
  models: string[];
  correlationId: string;
}

export interface ApiError {
  status: number;
  message: string;
  fieldErrors?: Record<string, string>;
  correlationId?: string;
}

const API_TIMEOUT = 30000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('timeout')), ms);
    promise
      .then((res) => {
        clearTimeout(timeout);
        resolve(res);
      })
      .catch((err) => {
        clearTimeout(timeout);
        reject(err);
      });
  });
}

function sanitizeError(error: any): ApiError {
  if (error.name === 'AbortError' || error.message === 'timeout') {
    return { status: 0, message: 'Connection timed out' };
  }
  if (error.response) {
    const { status, data } = error.response;
    if (status === 400 || status === 422) {
      return {
        status,
        message: data?.message || 'Validation error',
        fieldErrors: data?.errors,
        correlationId: data?.correlationId,
      };
    }
    if (status === 401) {
      return {
        status,
        message: 'Unauthorized. Please log in again.',
        correlationId: data?.correlationId,
      };
    }
    if (status === 500) {
      return {
        status,
        message: 'An unexpected error occurred. Please try again.',
        correlationId: data?.correlationId,
      };
    }
    return {
      status,
      message: data?.message || 'API error',
      correlationId: data?.correlationId,
    };
  }
  return { status: 0, message: 'Network error' };
}

function redactConfig(config: any) {
  // Redact known secret fields
  const redacted = { ...config };
  if ('apiKey' in redacted) redacted.apiKey = 'REDACTED';
  if ('password' in redacted) redacted.password = 'REDACTED';
  return redacted;
}

export async function fetchConfiguration(): Promise<Configuration> {
  const start = Date.now();
  try {
    const resp = await withTimeout(
      fetch('/api/v1/config', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' },
      }).then(async (r) => {
        if (!r.ok) throw { response: { status: r.status, data: await r.json() } };
        return r.json();
      }),
      API_TIMEOUT
    );
    logApiEvent('fetchConfiguration', {
      status: 200,
      duration: Date.now() - start,
      response: redactConfig(resp),
    });
    return resp;
  } catch (error) {
    const err = sanitizeError(error);
    logApiEvent('fetchConfiguration', {
      status: err.status,
      duration: Date.now() - start,
      error: redactSecrets(error),
      correlationId: err.correlationId,
    });
    throw err;
  }
}

export async function saveConfiguration(config: Configuration, csrfToken: string): Promise<void> {
  const start = Date.now();
  try {
    const resp = await withTimeout(
      fetch('/api/v1/config', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken,
          'Accept': 'application/json',
        },
        body: JSON.stringify(config),
      }).then(async (r) => {
        if (!r.ok) throw { response: { status: r.status, data: await r.json() } };
        return r.json();
      }),
      API_TIMEOUT
    );
    logApiEvent('saveConfiguration', {
      status: 200,
      duration: Date.now() - start,
      request: redactConfig(config),
      response: redactConfig(resp),
    });
    return;
  } catch (error) {
    const err = sanitizeError(error);
    logApiEvent('saveConfiguration', {
      status: err.status,
      duration: Date.now() - start,
      request: redactConfig(config),
      error: redactSecrets(error),
      correlationId: err.correlationId,
    });
    throw err;
  }
}

export async function testConnection(request: TestConnectionRequest): Promise<TestConnectionResponse> {
  const start = Date.now();
  try {
    const resp = await withTimeout(
      fetch('/api/v1/config/test-connection', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(redactConfig(request)),
      }).then(async (r) => {
        if (!r.ok) throw { response: { status: r.status, data: await r.json() } };
        return r.json();
      }),
      API_TIMEOUT
    );
    logApiEvent('testConnection', {
      status: 200,
      duration: Date.now() - start,
      request: redactConfig(request),
      response: redactConfig(resp),
      correlationId: resp?.correlationId,
    });
    return resp;
  } catch (error) {
    const err = sanitizeError(error);
    logApiEvent('testConnection', {
      status: err.status,
      duration: Date.now() - start,
      request: redactConfig(request),
      error: redactSecrets(error),
      correlationId: err.correlationId,
    });
    throw err;
  }
}