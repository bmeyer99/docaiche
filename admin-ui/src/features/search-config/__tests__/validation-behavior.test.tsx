/**
 * Tests specifically for validation behavior during loading and after loading completes
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useDeferredValidation } from '../utils/deferred-validator';

// Mock the config validator
jest.mock('@/lib/utils/config-validator', () => ({
  validateSearchConfig: jest.fn(() => ({
    isValid: true,
    errors: [],
    warnings: []
  }))
}));

const mockValidateSearchConfig = require('@/lib/utils/config-validator').validateSearchConfig;

// Test component that uses the deferred validation hook
function ValidationTestComponent({ 
  providers = {}, 
  loadingStates = {}
}: { 
  providers?: any; 
  loadingStates?: any; 
}) {
  const validation = useDeferredValidation({
    vectorConfig: { enabled: true },
    embeddingConfig: { provider: 'openai' },
    modelSelection: { textGeneration: { provider: 'openai', model: 'gpt-4' } },
    modelParameters: {},
    providers,
    isLoading: {
      providers: false,
      vectorConfig: false,
      embeddingConfig: false,
      modelSelection: false,
      modelParameters: false,
      ...loadingStates
    }
  });

  return (
    <div>
      <div data-testid="validation-result">
        {JSON.stringify({
          isValid: validation.isValid,
          errorCount: validation.errors.length,
          warningCount: validation.warnings.length,
          warnings: validation.warnings.map(w => w.message)
        })}
      </div>
    </div>
  );
}

describe('Validation Behavior Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Issue 1: Loading state behavior', () => {
    it('should show loading state when providers are loading', async () => {
      render(
        <ValidationTestComponent 
          providers={{}}
          loadingStates={{ providers: true }}
        />
      );

      // Should show loading message in warnings
      await waitFor(() => {
        const result = JSON.parse(screen.getByTestId('validation-result').textContent || '{}');
        expect(result.warnings).toContain('Loading configuration data...');
      });

      // Should not call the validator during loading
      expect(mockValidateSearchConfig).not.toHaveBeenCalled();
    });

    it('should validate after all loading states are false', async () => {
      // Mock validator to return specific warnings for empty providers
      mockValidateSearchConfig.mockReturnValue({
        isValid: false,
        errors: [],
        warnings: [{
          field: 'providers',
          message: 'No AI providers configured',
          severity: 'warning'
        }]
      });

      render(
        <ValidationTestComponent 
          providers={{}}
          loadingStates={{ 
            providers: false,
            vectorConfig: false,
            embeddingConfig: false,
            modelSelection: false,
            modelParameters: false
          }}
        />
      );

      await waitFor(() => {
        // Should call the validator
        expect(mockValidateSearchConfig).toHaveBeenCalled();
        
        // Should show the warning
        const result = JSON.parse(screen.getByTestId('validation-result').textContent || '{}');
        expect(result.warnings).toContain('No AI providers configured');
      });
    });

    it('should not show warnings when providers are configured', async () => {
      // Reset mock to return valid state
      mockValidateSearchConfig.mockReturnValue({
        isValid: true,
        errors: [],
        warnings: []
      });

      render(
        <ValidationTestComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] },
            ollama: { status: 'connected', models: ['llama2'] }
          }}
          loadingStates={{ 
            providers: false,
            vectorConfig: false,
            embeddingConfig: false,
            modelSelection: false,
            modelParameters: false
          }}
        />
      );

      await waitFor(() => {
        // Should call the validator
        expect(mockValidateSearchConfig).toHaveBeenCalled();
        
        // Should show valid state
        const result = JSON.parse(screen.getByTestId('validation-result').textContent || '{}');
        expect(result.isValid).toBe(true);
        expect(result.warningCount).toBe(0);
      });
    });
  });

  describe('Issue 2: Proper validation timing', () => {
    it('should not validate until all data is loaded', async () => {
      const { rerender } = render(
        <ValidationTestComponent 
          providers={{}}
          loadingStates={{ providers: true, vectorConfig: true }}
        />
      );

      // Should not validate yet
      expect(mockValidateSearchConfig).not.toHaveBeenCalled();

      // Still some data loading
      rerender(
        <ValidationTestComponent 
          providers={{}}
          loadingStates={{ providers: false, vectorConfig: true }}
        />
      );

      // Still should not validate
      expect(mockValidateSearchConfig).not.toHaveBeenCalled();

      // All data loaded
      rerender(
        <ValidationTestComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          loadingStates={{ 
            providers: false,
            vectorConfig: false,
            embeddingConfig: false,
            modelSelection: false,
            modelParameters: false
          }}
        />
      );

      await waitFor(() => {
        // Now should validate
        expect(mockValidateSearchConfig).toHaveBeenCalled();
      });
    });

    it('should handle the transition from loading to loaded smoothly', async () => {
      // Start with loading state
      const { rerender } = render(
        <ValidationTestComponent 
          providers={{}}
          loadingStates={{ providers: true }}
        />
      );

      // Should show loading
      expect(screen.getByText(/Loading configuration data/)).toBeInTheDocument();

      // Transition to loaded with good data
      rerender(
        <ValidationTestComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          loadingStates={{ 
            providers: false,
            vectorConfig: false,
            embeddingConfig: false,
            modelSelection: false,
            modelParameters: false
          }}
        />
      );

      await waitFor(() => {
        // Should no longer show loading
        expect(screen.queryByText(/Loading configuration data/)).not.toBeInTheDocument();
        
        // Should have called validation
        expect(mockValidateSearchConfig).toHaveBeenCalled();
      });
    });
  });

  describe('Validation caching behavior', () => {
    it('should cache validation results for the same data', async () => {
      const { rerender } = render(
        <ValidationTestComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          loadingStates={{ 
            providers: false,
            vectorConfig: false,
            embeddingConfig: false,
            modelSelection: false,
            modelParameters: false
          }}
        />
      );

      await waitFor(() => {
        expect(mockValidateSearchConfig).toHaveBeenCalledTimes(1);
      });

      // Re-render with same data
      rerender(
        <ValidationTestComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          loadingStates={{ 
            providers: false,
            vectorConfig: false,
            embeddingConfig: false,
            modelSelection: false,
            modelParameters: false
          }}
        />
      );

      // Should not call validation again due to caching
      await new Promise(resolve => setTimeout(resolve, 200));
      expect(mockValidateSearchConfig).toHaveBeenCalledTimes(1);
    });
  });
});