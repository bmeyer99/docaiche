/**
 * Optimized Provider Form Components
 * Implements React.memo, debounced inputs, and smart re-rendering
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Icons } from '@/components/icons';
import { ProviderDefinition, ProviderConfiguration } from '@/lib/config/providers';
import { 
  withPerformanceOptimization,
  useDebounce,
  useStableCallback,
  useStableHandlers,
  usePerformanceMonitor,
  shallowEqual
} from '@/lib/utils/performance-helpers';

// ========================== OPTIMIZED FIELD COMPONENTS ==========================

interface OptimizedFieldProps {
  fieldKey: string;
  field: any;
  providerId: string;
  value: any;
  onChange: (key: string, value: any) => void;
  placeholder?: string;
}

const OptimizedTextField = React.memo<OptimizedFieldProps>(({
  fieldKey,
  field,
  providerId,
  value,
  onChange,
  placeholder
}) => {
  usePerformanceMonitor(`OptimizedTextField-${fieldKey}`, [value]);
  
  const [localValue, setLocalValue] = useState(String(value || ''));
  const debouncedValue = useDebounce(localValue, 300);

  // Update parent when debounced value changes
  React.useEffect(() => {
    if (debouncedValue !== String(value || '')) {
      onChange(fieldKey, debouncedValue);
    }
  }, [debouncedValue, fieldKey, onChange, value]);

  // Update local value when prop changes (e.g., from reset)
  React.useEffect(() => {
    setLocalValue(String(value || ''));
  }, [value]);

  const handleChange = useStableCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalValue(e.target.value);
  }, []);

  const inputId = `${providerId}-${fieldKey}`;

  return (
    <div className="grid gap-2">
      <Label htmlFor={inputId}>
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </Label>
      <div className="relative">
        <Input
          id={inputId}
          type={field.type === 'password' ? 'password' : 'text'}
          value={localValue}
          onChange={handleChange}
          placeholder={placeholder || field.placeholder}
          className={field.type === 'password' ? 'font-mono' : ''}
        />
      </div>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  );
}, shallowEqual);

OptimizedTextField.displayName = 'OptimizedTextField';

const OptimizedTextareaField = React.memo<OptimizedFieldProps>(({
  fieldKey,
  field,
  providerId,
  value,
  onChange,
  placeholder
}) => {
  usePerformanceMonitor(`OptimizedTextareaField-${fieldKey}`, [value]);
  
  const [localValue, setLocalValue] = useState(String(value || ''));
  const debouncedValue = useDebounce(localValue, 500); // Longer debounce for textarea

  React.useEffect(() => {
    if (debouncedValue !== String(value || '')) {
      onChange(fieldKey, debouncedValue);
    }
  }, [debouncedValue, fieldKey, onChange, value]);

  React.useEffect(() => {
    setLocalValue(String(value || ''));
  }, [value]);

  const handleChange = useStableCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalValue(e.target.value);
  }, []);

  const inputId = `${providerId}-${fieldKey}`;

  return (
    <div className="grid gap-2">
      <Label htmlFor={inputId}>
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </Label>
      <Textarea
        id={inputId}
        value={localValue}
        onChange={handleChange}
        placeholder={placeholder || field.placeholder}
        className="min-h-[100px]"
      />
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  );
}, shallowEqual);

OptimizedTextareaField.displayName = 'OptimizedTextareaField';

const OptimizedNumberField = React.memo<OptimizedFieldProps>(({
  fieldKey,
  field,
  providerId,
  value,
  onChange
}) => {
  usePerformanceMonitor(`OptimizedNumberField-${fieldKey}`, [value]);
  
  const [localValue, setLocalValue] = useState(String(value || ''));
  const debouncedValue = useDebounce(localValue, 300);

  React.useEffect(() => {
    const numValue = parseInt(debouncedValue) || 0;
    if (numValue !== (value || 0)) {
      onChange(fieldKey, numValue);
    }
  }, [debouncedValue, fieldKey, onChange, value]);

  React.useEffect(() => {
    setLocalValue(String(value || ''));
  }, [value]);

  const handleChange = useStableCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalValue(e.target.value);
  }, []);

  const inputId = `${providerId}-${fieldKey}`;

  return (
    <div className="grid gap-2">
      <Label htmlFor={inputId}>
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </Label>
      <Input
        id={inputId}
        type="number"
        value={localValue}
        onChange={handleChange}
        placeholder={field.placeholder}
        min={field.validation?.min}
        max={field.validation?.max}
      />
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  );
}, shallowEqual);

OptimizedNumberField.displayName = 'OptimizedNumberField';

// ========================== PROVIDER FORM COMPONENT ==========================

interface OptimizedProviderFormProps {
  provider: ProviderDefinition & { id: string };
  config: ProviderConfiguration;
  onUpdateProvider: (providerId: string, config: Partial<ProviderConfiguration['config']>) => void;
  onTestConnection: (providerId: string) => void;
  isLoading?: boolean;
}

const OptimizedProviderForm = React.memo<OptimizedProviderFormProps>(({
  provider,
  config,
  onUpdateProvider,
  onTestConnection,
  isLoading = false
}) => {
  usePerformanceMonitor(`OptimizedProviderForm-${provider.id}`, [provider.id, config]);

  // Memoize field change handler to prevent recreation
  const handleFieldChange = useStableCallback((fieldKey: string, value: any) => {
    onUpdateProvider(provider.id, { [fieldKey]: value });
  }, [provider.id, onUpdateProvider]);

  // Memoize enabled toggle handler
  const handleEnabledToggle = useStableCallback((enabled: boolean) => {
    onUpdateProvider(provider.id, { enabled });
  }, [provider.id, onUpdateProvider]);

  // Memoize test connection handler
  const handleTestConnection = useStableCallback(() => {
    onTestConnection(provider.id);
  }, [provider.id, onTestConnection]);

  // Memoize stable handlers object
  const handlers = useStableHandlers({
    onFieldChange: handleFieldChange,
    onEnabledToggle: handleEnabledToggle,
    onTestConnection: handleTestConnection
  }, [handleFieldChange, handleEnabledToggle, handleTestConnection]);

  // Memoize field renderers
  const fieldComponents = useMemo(() => {
    return provider.configFields?.map((field) => {
      const fieldValue = config.config?.[field.key] || 
        (field.key === 'base_url' ? provider.defaultBaseUrl || '' : '');

      const key = `${provider.id}-${field.key}`;

      if (field.type === 'textarea') {
        return (
          <OptimizedTextareaField
            key={key}
            fieldKey={field.key}
            field={field}
            providerId={provider.id}
            value={fieldValue}
            onChange={handlers.onFieldChange}
            placeholder={field.placeholder}
          />
        );
      } else if (field.type === 'number') {
        return (
          <OptimizedNumberField
            key={key}
            fieldKey={field.key}
            field={field}
            providerId={provider.id}
            value={fieldValue}
            onChange={handlers.onFieldChange}
          />
        );
      } else {
        return (
          <OptimizedTextField
            key={key}
            fieldKey={field.key}
            field={field}
            providerId={provider.id}
            value={fieldValue}
            onChange={handlers.onFieldChange}
            placeholder={field.placeholder}
          />
        );
      }
    }) || [];
  }, [provider, config.config, handlers.onFieldChange]);

  // Memoize API key help text
  const apiKeyHelpText = useMemo(() => {
    const apiKeyField = provider.configFields?.find(f => f.key === 'api_key');
    if (!apiKeyField) return null;

    const helpTexts: Record<string, string> = {
      'openai': 'Get your API key from platform.openai.com',
      'anthropic': 'Get your API key from console.anthropic.com',
      'groq': 'Get your API key from console.groq.com',
      'openrouter': 'Get your API key from openrouter.ai',
      'mistral': 'Get your API key from console.mistral.ai'
    };

    return helpTexts[provider.id];
  }, [provider.id, provider.configFields]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">{provider.displayName} Configuration</h3>
          <p className="text-sm text-muted-foreground">{provider.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Enable Provider</span>
          <Switch
            checked={config.enabled || false}
            onCheckedChange={handlers.onEnabledToggle}
          />
        </div>
      </div>

      <Separator />

      <div className="grid gap-4">
        {fieldComponents}
        {apiKeyHelpText && (
          <div className="text-xs text-muted-foreground bg-muted/50 p-3 rounded-md">
            <Icons.info className="w-4 h-4 inline mr-2" />
            {apiKeyHelpText}
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={handlers.onTestConnection}
          disabled={isLoading}
          className="flex items-center gap-2"
        >
          {isLoading ? (
            <Icons.spinner className="w-4 h-4 animate-spin" />
          ) : (
            <Icons.activity className="w-4 h-4" />
          )}
          Test Connection
        </Button>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison to prevent unnecessary re-renders
  return (
    prevProps.provider.id === nextProps.provider.id &&
    prevProps.isLoading === nextProps.isLoading &&
    shallowEqual(prevProps.config, nextProps.config) &&
    prevProps.onUpdateProvider === nextProps.onUpdateProvider &&
    prevProps.onTestConnection === nextProps.onTestConnection
  );
});

OptimizedProviderForm.displayName = 'OptimizedProviderForm';

// ========================== PROVIDER CARD COMPONENT ==========================

interface OptimizedProviderCardProps {
  provider: ProviderDefinition & { id: string };
  config: ProviderConfiguration;
  isActive: boolean;
  onClick: (providerId: string) => void;
}

const OptimizedProviderCard = React.memo<OptimizedProviderCardProps>(({
  provider,
  config,
  isActive,
  onClick
}) => {
  usePerformanceMonitor(`OptimizedProviderCard-${provider.id}`, [isActive, config.enabled]);

  const handleClick = useStableCallback(() => {
    onClick(provider.id);
  }, [provider.id, onClick]);

  const isConfigured = useMemo(() => {
    return config?.enabled || Object.keys(config?.config || {}).length > 0;
  }, [config]);

  const cardClassName = useMemo(() => {
    return `p-3 rounded-lg border cursor-pointer transition-colors ${
      isActive 
        ? 'bg-selection text-selection-foreground border-selection shadow-sm' 
        : 'hover:bg-selection-hover hover:text-selection-hover-foreground hover:border-selection-hover'
    }`;
  }, [isActive]);

  return (
    <div
      className={cardClassName}
      onClick={handleClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div 
            className="w-3 h-3 rounded" 
            style={{ backgroundColor: provider.color || '#6b7280' }}
          />
          <span className="font-medium">{provider.displayName}</span>
        </div>
        {isConfigured && (
          <div className="w-2 h-2 bg-success rounded-full" title="Configured" />
        )}
      </div>
      <p className="text-xs text-muted-foreground mt-1">
        {provider.description}
      </p>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for optimal re-rendering
  return (
    prevProps.provider.id === nextProps.provider.id &&
    prevProps.isActive === nextProps.isActive &&
    prevProps.onClick === nextProps.onClick &&
    shallowEqual(prevProps.config, nextProps.config)
  );
});

OptimizedProviderCard.displayName = 'OptimizedProviderCard';

// ========================== PROVIDER LIST COMPONENT ==========================

interface OptimizedProviderListProps {
  providers: (ProviderDefinition & { id: string })[];
  configs: Record<string, ProviderConfiguration>;
  activeProvider: string;
  onProviderSelect: (providerId: string) => void;
}

const OptimizedProviderList = React.memo<OptimizedProviderListProps>(({
  providers,
  configs,
  activeProvider,
  onProviderSelect
}) => {
  usePerformanceMonitor('OptimizedProviderList', [providers.length, activeProvider]);

  // Memoize provider cards to prevent recreation
  const providerCards = useMemo(() => {
    return providers.map(provider => {
      const config = configs[provider.id];
      return (
        <OptimizedProviderCard
          key={provider.id}
          provider={provider}
          config={config}
          isActive={activeProvider === provider.id}
          onClick={onProviderSelect}
        />
      );
    });
  }, [providers, configs, activeProvider, onProviderSelect]);

  return (
    <div className="space-y-2">
      {providerCards}
    </div>
  );
}, shallowEqual);

OptimizedProviderList.displayName = 'OptimizedProviderList';

// ========================== EXPORTS ==========================

export {
  OptimizedProviderForm,
  OptimizedProviderCard,
  OptimizedProviderList,
  OptimizedTextField,
  OptimizedTextareaField,
  OptimizedNumberField
};

// HOC versions for additional optimization
export const HighlyOptimizedProviderForm = withPerformanceOptimization(OptimizedProviderForm);
export const HighlyOptimizedProviderCard = withPerformanceOptimization(OptimizedProviderCard);
export const HighlyOptimizedProviderList = withPerformanceOptimization(OptimizedProviderList);