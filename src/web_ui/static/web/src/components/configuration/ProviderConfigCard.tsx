// ProviderConfigCard.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Card } from '../ui/Card';
import { FormGroup } from '../ui/FormGroup';
import { FormRow } from '../ui/FormRow';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Label } from '../ui/Label';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { Icon } from '../ui/Icon';
// import { Toast } from '../ui/Toast'; // TODO: Use when implementing toast notifications
import { Logger } from '../../utils/logger';
import type { ProviderConfig } from '../../types/configuration';

type ProviderType = 'ollama' | 'openai' | 'custom';

interface ProviderConfigCardProps {
  value: ProviderConfig;
  onChange: (value: ProviderConfig) => void;
  onTestConnection?: (config: ProviderConfig) => Promise<{ success: boolean; models?: string[]; error?: string }>;
  disabled?: boolean;
  testInProgress?: boolean;
  testStatus?: 'idle' | 'testing' | 'success' | 'error';
  testError?: string;
  availableModels?: string[];
  className?: string;
}

const PROVIDER_OPTIONS: { label: string; value: ProviderType }[] = [
  { label: 'Ollama', value: 'ollama' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Custom', value: 'custom' },
];

const BASE_URL_PLACEHOLDER = 'http://localhost:11434';

function sanitizeInput(str: string): string {
  // Remove script tags and encode special chars
  return str.replace(/<.*?>/g, '').replace(/[<>"'`]/g, '');
}

function isValidUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

function isValidApiKey(key: string): boolean {
  // Example: min 16 chars, alphanumeric + dashes/underscores
  return /^[A-Za-z0-9\-_]{16,}$/.test(key);
}

function isValidModel(model: string): boolean {
  // Example: non-empty, no spaces or script tags
  return !!model && !/<.*?>/.test(model) && !/\s/.test(model);
}

export const ProviderConfigCard: React.FC<ProviderConfigCardProps> = ({
  value,
  onChange,
  onTestConnection,
  disabled = false,
  testInProgress = false,
  testStatus = 'idle',
  testError,
  availableModels,
  className,
}) => {
  const [provider, setProvider] = useState<ProviderType>(value.provider);
  const [baseUrl, setBaseUrl] = useState(value.baseUrl);
  const [apiKey, setApiKey] = useState(value.apiKey || '');
  const [model, setModel] = useState(value.model);
  const [showApiKey, setShowApiKey] = useState(false);
  const [modelOptions, setModelOptions] = useState<string[]>(availableModels || []);
  const [validation, setValidation] = useState({
    provider: true,
    baseUrl: true,
    apiKey: true,
    model: true,
  });
  const [errors, setErrors] = useState({
    provider: '',
    baseUrl: '',
    apiKey: '',
    model: '',
  });
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>(testStatus);
  const [connectionError, setConnectionError] = useState<string | undefined>(testError);
  const [announceMsg, setAnnounceMsg] = useState('');
  const announceRef = useRef<HTMLDivElement>(null);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);

  // Accessibility: announce status changes
  useEffect(() => {
    if (connectionStatus === 'success') setAnnounceMsg('Connection successful');
    else if (connectionStatus === 'error') setAnnounceMsg('Connection failed');
    else setAnnounceMsg('');
  }, [connectionStatus]);

  useEffect(() => {
    if (announceMsg && announceRef.current) {
      announceRef.current.textContent = announceMsg;
    }
  }, [announceMsg]);

  // Debounced validation
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      validateAll();
    }, 400);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider, baseUrl, apiKey, model]);

  useEffect(() => {
    setModelOptions(availableModels || []);
  }, [availableModels]);

  function validateAll() {
    const newValidation = {
      provider: PROVIDER_OPTIONS.some(opt => opt.value === provider),
      baseUrl: isValidUrl(baseUrl),
      apiKey: !apiKey || isValidApiKey(apiKey),
      model: isValidModel(model),
    };
    const newErrors = {
      provider: newValidation.provider ? '' : 'Please select a valid provider.',
      baseUrl: newValidation.baseUrl ? '' : 'Enter a valid http(s) URL.',
      apiKey: newValidation.apiKey ? '' : 'API key must be at least 16 characters.',
      model: newValidation.model ? '' : 'Enter a valid model name.',
    };
    setValidation(newValidation);
    setErrors(newErrors);
    return newValidation;
  }

  function handleProviderChange(val: string) {
    const sanitized = sanitizeInput(val) as ProviderType;
    setProvider(sanitized);
    onChange({ ...value, provider: sanitized });
  }

  function handleBaseUrlChange(val: string) {
    const sanitized = sanitizeInput(val);
    setBaseUrl(sanitized);
    onChange({ ...value, baseUrl: sanitized });
  }

  function handleApiKeyChange(val: string) {
    const sanitized = sanitizeInput(val);
    setApiKey(sanitized);
    onChange({ ...value, apiKey: sanitized });
  }

  function handleModelChange(val: string) {
    const sanitized = sanitizeInput(val);
    setModel(sanitized);
    onChange({ ...value, model: sanitized });
  }

  async function handleTestConnection() {
    if (!onTestConnection) return;
    
    setConnectionStatus('testing');
    setConnectionError(undefined);
    Logger.info('Testing provider connection', {
      category: 'api',
      redactKeys: ['apiKey'],
      provider,
      baseUrl,
    });
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);
      const result = await onTestConnection(
        { provider, baseUrl, apiKey, model, settings: value.settings }
      );
      clearTimeout(timeout);
      if (result.success) {
        setConnectionStatus('success');
        setModelOptions(result.models || []);
        setAnnounceMsg('Connection successful');
        Logger.info('Provider connection successful', {
          category: 'api',
          provider,
          baseUrl,
        });
      } else {
        setConnectionStatus('error');
        setConnectionError(result.error || 'Unknown error');
        setAnnounceMsg('Connection failed');
        Logger.warn('Provider connection failed', {
          category: 'api',
          provider,
          baseUrl,
          error: result.error,
        });
      }
    } catch (e: any) {
      setConnectionStatus('error');
      setConnectionError(e?.message || 'Unknown error');
      setAnnounceMsg('Connection failed');
      Logger.error('Provider connection error', {
        category: 'api',
        provider,
        baseUrl,
        error: e?.message,
      });
    }
  }

  const isFormValid = Object.values(validation).every(Boolean);

  return (
    <Card className={`card ${className || ''}`} aria-labelledby="provider-config-title">
      <form aria-describedby="provider-config-errors">
        <h2 className="sr-only">Provider Configuration</h2>
        <FormGroup>
          <FormRow>
            <Label htmlFor="provider-select">Provider</Label>
            <Select
              value={provider}
              onChange={handleProviderChange}
              disabled={disabled}
              aria-invalid={!validation.provider}
              aria-describedby={!validation.provider ? 'provider-error' : undefined}
              className={validation.provider ? '' : 'inputError'}
            >
              <option value="" disabled>Select provider</option>
              {PROVIDER_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </Select>
            {!validation.provider && (
              <span className="inputError" role="alert">{errors.provider}</span>
            )}
          </FormRow>
          <FormRow>
            <Label htmlFor="base-url-input">Base URL</Label>
            <Input
              value={baseUrl}
              onChange={handleBaseUrlChange}
              placeholder={BASE_URL_PLACEHOLDER}
              disabled={disabled}
              aria-invalid={!validation.baseUrl}
              aria-describedby={!validation.baseUrl ? 'baseurl-error' : undefined}
              className={validation.baseUrl ? '' : 'inputError'}
              inputMode="url"
            />
            <span className="helperText">The endpoint for your provider (e.g., Ollama, OpenAI).</span>
            {!validation.baseUrl && (
              <span className="inputError" role="alert">{errors.baseUrl}</span>
            )}
          </FormRow>
          <FormRow>
            <Label htmlFor="api-key-input">API Key</Label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={handleApiKeyChange}
                placeholder="Enter API key"
                disabled={disabled}
                aria-invalid={!validation.apiKey}
                aria-describedby={!validation.apiKey ? 'apikey-error' : undefined}
                className={validation.apiKey ? '' : 'inputError'}
                inputMode="text"
                style={{ flex: 1 }}
              />
              <Button
                type="button"
                aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
                onClick={() => setShowApiKey(v => !v)}
                tabIndex={0}
                style={{ minWidth: 32 }}
              >
                <Icon name={showApiKey ? 'eyeOff' : 'eye'} />
              </Button>
            </div>
            <span className="helperText">Your provider API key (never stored in plaintext).</span>
            {!validation.apiKey && (
              <span className="inputError" role="alert">{errors.apiKey}</span>
            )}
          </FormRow>
          <FormRow>
            <Label htmlFor="model-select">Model</Label>
            {testInProgress ? (
              <Select disabled>
                <option>Loading models...</option>
              </Select>
            ) : modelOptions.length > 0 ? (
              <Select
                value={model}
                onChange={handleModelChange}
                disabled={disabled}
                aria-invalid={!validation.model}
                aria-describedby={!validation.model ? 'model-error' : undefined}
                className={validation.model ? '' : 'inputError'}
              >
                <option value="" disabled>Select model</option>
                {modelOptions.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </Select>
            ) : (
              <Input
                type="text"
                value={model}
                onChange={handleModelChange}
                placeholder="Enter model name"
                disabled={disabled}
                aria-invalid={!validation.model}
                aria-describedby={!validation.model ? 'model-error' : undefined}
                className={validation.model ? '' : 'inputError'}
                inputMode="text"
              />
            )}
            <span className="helperText">Select or enter the model to use.</span>
            {!validation.model && (
              <span className="inputError" role="alert">{errors.model}</span>
            )}
          </FormRow>
        </FormGroup>
        <FormRow>
          <Button
            type="button"
            onClick={handleTestConnection}
            disabled={disabled || !isFormValid || testInProgress}
            aria-busy={testInProgress}
            aria-live="polite"
            style={{ minWidth: 160 }}
          >
            {connectionStatus === 'testing' ? (
              <>
                <LoadingSpinner size="sm" /> Testing...
              </>
            ) : connectionStatus === 'success' ? (
              <>
                <Icon name="checkCircle" color="green" /> Connected
              </>
            ) : connectionStatus === 'error' ? (
              <>
                <Icon name="xCircle" color="red" /> Failed
              </>
            ) : (
              'Test Connection'
            )}
          </Button>
          {connectionStatus === 'error' && connectionError && (
            <span className="inputError" role="alert">{connectionError}</span>
          )}
        </FormRow>
        <div
          ref={announceRef}
          aria-live="polite"
          aria-atomic="true"
          style={{ position: 'absolute', left: -9999, height: 1, width: 1, overflow: 'hidden' }}
        />
      </form>
    </Card>
  );
};