/**
 * Example component demonstrating how to use the validated provider settings
 * This shows proper type safety and validation in action
 */

import React, { useState } from 'react';
import { useProviderSettings } from '../hooks/use-provider-settings';
import { useProviderConfig } from '../hooks/use-provider-config';
import { 
  validateUrl, 
  validateApiKey, 
  validateNumber,
  containsMaliciousContent 
} from '../utils/validation';
import { AI_PROVIDERS } from '@/lib/config/providers';

interface FieldError {
  field: string;
  message: string;
}

export function ValidatedProviderForm({ providerId }: { providerId: string }) {
  const { updateProvider } = useProviderSettings();
  const { provider } = useProviderConfig(providerId);
  const [errors, setErrors] = useState<FieldError[]>([]);
  
  const providerDef = AI_PROVIDERS[providerId];
  
  if (!provider || !providerDef) {
    return <div>Provider not found</div>;
  }
  
  const handleFieldChange = (fieldKey: string, value: string) => {
    // Clear existing error for this field
    setErrors(prev => prev.filter(e => e.field !== fieldKey));
    
    // Check for malicious content first
    if (typeof value === 'string' && containsMaliciousContent(value)) {
      setErrors(prev => [...prev, {
        field: fieldKey,
        message: 'Invalid input detected'
      }]);
      return;
    }
    
    // Find field definition
    const fieldDef = providerDef.configFields.find(f => f.key === fieldKey);
    if (!fieldDef) return;
    
    // Validate based on field type
    let validationResult: { isValid: boolean; error?: string } = { isValid: true };
    
    switch (fieldDef.type) {
      case 'url':
        if (value) {
          validationResult = validateUrl(value);
        }
        break;
        
      case 'password':
        if (fieldDef.key === 'api_key' && value) {
          validationResult = validateApiKey(providerId, value);
        }
        break;
        
      case 'number':
        if (value) {
          validationResult = validateNumber(
            value,
            fieldDef.validation?.min,
            fieldDef.validation?.max
          );
        }
        break;
    }
    
    if (!validationResult.isValid && validationResult.error) {
      setErrors(prev => [...prev, {
        field: fieldKey,
        message: validationResult.error!
      }]);
      return;
    }
    
    // Update the provider config
    updateProvider(providerId, {
      [fieldKey]: fieldDef.type === 'number' ? Number(value) : value
    });
  };
  
  const getFieldError = (fieldKey: string): string | undefined => {
    return errors.find(e => e.field === fieldKey)?.message;
  };
  
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{providerDef.displayName} Configuration</h3>
      
      {providerDef.configFields.map(field => (
        <div key={field.key} className="space-y-2">
          <label className="block text-sm font-medium">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          
          {field.type === 'select' ? (
            <select
              value={provider.config[field.key] || ''}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="">Select {field.label}</option>
              {field.options?.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ) : field.type === 'textarea' ? (
            <textarea
              value={provider.config[field.key] || ''}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              className="w-full p-2 border rounded"
              rows={4}
            />
          ) : (
            <input
              type={field.type === 'password' ? 'password' : 'text'}
              value={provider.config[field.key] || ''}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              className="w-full p-2 border rounded"
            />
          )}
          
          {field.description && (
            <p className="text-sm text-gray-600">{field.description}</p>
          )}
          
          {getFieldError(field.key) && (
            <p className="text-sm text-red-500">{getFieldError(field.key)}</p>
          )}
        </div>
      ))}
      
      {errors.length > 0 && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-sm font-medium text-red-800">
            Please fix the following errors:
          </p>
          <ul className="mt-2 list-disc list-inside text-sm text-red-700">
            {errors.map((error, idx) => (
              <li key={idx}>{error.message}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}