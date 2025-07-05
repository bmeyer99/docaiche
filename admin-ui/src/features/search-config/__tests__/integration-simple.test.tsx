/**
 * Simplified integration tests for Search Configuration feature
 * 
 * These tests verify the core issues are fixed without complex UI rendering
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useDeferredValidation } from '../utils/deferred-validator';
import { validateSearchConfig } from '@/lib/utils/config-validator';

// Mock the config validator
jest.mock('@/lib/utils/config-validator', () => ({
  validateSearchConfig: jest.fn(() => ({
    isValid: true,
    errors: [],
    warnings: []
  }))
}));

// Test component to verify deferred validation behavior
function TestValidationComponent({ 
  providers, 
  isLoading = false 
}: { 
  providers: any; 
  isLoading?: boolean; 
}) {
  const validation = useDeferredValidation({
    vectorConfig: { enabled: true },
    embeddingConfig: { provider: 'openai' },
    modelSelection: { textGeneration: { provider: 'openai', model: 'gpt-4' } },
    modelParameters: {},
    providers,
    isLoading: { providers: isLoading }
  });

  return (
    <div>
      <div data-testid="validation-status">
        {validation.isValid ? 'valid' : 'invalid'}
      </div>
      <div data-testid="warnings-count">
        {validation.warnings.length}
      </div>
      <div data-testid="errors-count">
        {validation.errors.length}
      </div>
      {validation.warnings.map((warning, index) => (
        <div key={index} data-testid={`warning-${index}`}>
          {warning.message}
        </div>
      ))}
    </div>
  );
}

describe('Search Configuration Integration Tests (Simplified)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (validateSearchConfig as jest.Mock).mockReturnValue({
      isValid: true,
      errors: [],
      warnings: []
    });
  });

  describe('Issue 1: No warnings during initial load', () => {
    it('should not run validation while data is loading', async () => {
      render(
        <TestValidationComponent 
          providers={{}}
          isLoading={true}
        />
      );

      // Should show loading message
      expect(screen.getByText(/Loading configuration data/i)).toBeInTheDocument();
      
      // Validation should not have been called yet
      expect(validateSearchConfig).not.toHaveBeenCalled();
    });

    it('should run validation only after data loads', async () => {
      // First test with different data to trigger validation
      render(
        <TestValidationComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          isLoading={false}
        />
      );

      await waitFor(() => {
        // Validation should have been called for the non-loading state
        expect(validateSearchConfig).toHaveBeenCalled();
      }, { timeout: 2000 });
    });

    it('should show appropriate warnings for empty providers after loading', async () => {
      (validateSearchConfig as jest.Mock).mockReturnValue({
        isValid: false,
        errors: [],
        warnings: [{
          field: 'providers',
          message: 'No AI providers configured',
          severity: 'warning'
        }]
      });

      render(
        <TestValidationComponent 
          providers={{}}
          isLoading={false}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('No AI providers configured')).toBeInTheDocument();
        expect(screen.getByTestId('warnings-count')).toHaveTextContent('1');
      });
    });

    it('should not show warnings when providers are properly configured', async () => {
      render(
        <TestValidationComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] },
            ollama: { status: 'connected', models: ['llama2'] }
          }}
          isLoading={false}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('validation-status')).toHaveTextContent('valid');
        expect(screen.getByTestId('warnings-count')).toHaveTextContent('0');
        expect(screen.getByTestId('errors-count')).toHaveTextContent('0');
      });
    });
  });

  describe('Issue 2: Change detection logic', () => {
    it('should show loading state and not run validation prematurely', async () => {
      render(
        <TestValidationComponent 
          providers={{}}
          isLoading={true}
        />
      );

      // Should show loading message, not validation results
      expect(screen.getByText(/Loading configuration data/i)).toBeInTheDocument();
      
      // Should not call validation during loading
      expect(validateSearchConfig).not.toHaveBeenCalled();
    });

    it('should validate after loading completes', async () => {
      // Clear previous calls
      jest.clearAllMocks();
      
      render(
        <TestValidationComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          isLoading={false}
        />
      );

      // Allow some time for validation to process
      await new Promise(resolve => setTimeout(resolve, 200));

      // Validation should have been called
      expect(validateSearchConfig).toHaveBeenCalled();
    });
  });

  describe('Loading state management', () => {
    it('should handle transition from loading to loaded', async () => {
      const { rerender } = render(
        <TestValidationComponent 
          providers={{}}
          isLoading={true}
        />
      );

      // Initially loading
      expect(screen.getByText(/Loading configuration data/i)).toBeInTheDocument();
      expect(validateSearchConfig).not.toHaveBeenCalled();

      // Transition to loaded
      rerender(
        <TestValidationComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          isLoading={false}
        />
      );

      await waitFor(() => {
        expect(screen.queryByText(/Loading configuration data/i)).not.toBeInTheDocument();
        expect(validateSearchConfig).toHaveBeenCalled();
      });
    });

    it('should not show false positives during loading transitions', async () => {
      // Mock a scenario where validation would show warnings if run prematurely
      (validateSearchConfig as jest.Mock).mockImplementation((vectorConfig, embeddingConfig, modelSelection, modelParameters, providers) => {
        if (!providers || Object.keys(providers).length === 0) {
          return {
            isValid: false,
            errors: [],
            warnings: [{
              field: 'providers',
              message: 'No AI providers configured',
              severity: 'warning'
            }]
          };
        }
        return {
          isValid: true,
          errors: [],
          warnings: []
        };
      });

      const { rerender } = render(
        <TestValidationComponent 
          providers={{}}
          isLoading={true}
        />
      );

      // Should show loading, not warnings
      expect(screen.getByText(/Loading configuration data/i)).toBeInTheDocument();
      expect(screen.queryByText('No AI providers configured')).not.toBeInTheDocument();

      // Load actual data
      rerender(
        <TestValidationComponent 
          providers={{
            openai: { status: 'tested', models: ['gpt-4'] }
          }}
          isLoading={false}
        />
      );

      await waitFor(() => {
        // Should show valid state, not warnings
        expect(screen.getByTestId('validation-status')).toHaveTextContent('valid');
        expect(screen.queryByText('No AI providers configured')).not.toBeInTheDocument();
      });
    });
  });
});