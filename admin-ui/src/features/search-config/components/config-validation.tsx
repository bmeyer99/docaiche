'use client';

/**
 * Configuration validation display component
 * Shows validation errors and warnings with actionable suggestions
 */

import React from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  CheckCircle,
  ExternalLink
} from 'lucide-react';
import { ValidationResult, ValidationError } from '@/lib/utils/config-validator';

interface ConfigValidationProps {
  validation: ValidationResult;
  onNavigateToTab?: (tab: string) => void;
  className?: string;
}

export function ConfigValidation({ validation, onNavigateToTab, className }: ConfigValidationProps) {
  const { isValid, errors, warnings } = validation;

  // Don't show anything if configuration is perfect
  if (isValid && warnings.length === 0) {
    return (
      <Alert className={className}>
        <CheckCircle className="h-4 w-4 text-green-500" />
        <AlertDescription className="text-green-700">
          Configuration is valid and complete
        </AlertDescription>
      </Alert>
    );
  }

  const getActionButton = (error: ValidationError) => {
    const actionMap: Record<string, string> = {
      'vectorConfig.base_url': 'connection',
      'vectorConfig.connection': 'connection', 
      'embeddingConfig.provider': 'models',
      'embeddingConfig.model': 'models',
      'textGeneration.provider': 'providers',
      'textGeneration.model': 'model',
      'textGeneration.parameters': 'parameters',
      'providers': 'providers'
    };

    const targetTab = actionMap[error.field];
    if (targetTab && onNavigateToTab) {
      return (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onNavigateToTab(targetTab)}
          className="ml-2"
        >
          Fix This
          <ExternalLink className="h-3 w-3 ml-1" />
        </Button>
      );
    }
    return null;
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Errors */}
      {errors.length > 0 && (
        <Card className="border-red-200">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-red-800">
              <AlertCircle className="h-4 w-4" />
              Configuration Errors ({errors.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {errors.map((error, index) => (
              <Alert key={index} className="border-red-200 bg-red-50">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <AlertDescription>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-red-800">{error.message}</p>
                      {error.suggestion && (
                        <p className="text-sm text-red-600 mt-1">{error.suggestion}</p>
                      )}
                    </div>
                    {getActionButton(error)}
                  </div>
                </AlertDescription>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <Card className="border-rose-200 dark:border-rose-800">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-rose-700 dark:text-rose-400">
              <AlertTriangle className="h-4 w-4" />
              Configuration Warnings ({warnings.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {warnings.map((warning, index) => (
              <Alert key={index} className="border-rose-200 bg-rose-50 dark:border-rose-800 dark:bg-rose-950/30">
                <AlertTriangle className="h-4 w-4 text-rose-500 dark:text-rose-400" />
                <AlertDescription>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-rose-700 dark:text-rose-300">{warning.message}</p>
                      {warning.suggestion && (
                        <p className="text-sm text-rose-600 dark:text-rose-400 mt-1">{warning.suggestion}</p>
                      )}
                    </div>
                    {getActionButton(warning)}
                  </div>
                </AlertDescription>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Overall Status */}
      <Alert className={isValid ? "border-rose-200 bg-rose-50 dark:border-rose-800 dark:bg-rose-950/30" : "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30"}>
        {isValid ? (
          <Info className="h-4 w-4 text-rose-500 dark:text-rose-400" />
        ) : (
          <AlertCircle className="h-4 w-4 text-red-500 dark:text-red-400" />
        )}
        <AlertDescription className={isValid ? "text-rose-700 dark:text-rose-300" : "text-red-700 dark:text-red-300"}>
          <div className="flex items-center justify-between">
            <div>
              {isValid ? (
                <span>Configuration is functional but has some recommendations</span>
              ) : (
                <span>Configuration has critical issues that must be resolved</span>
              )}
            </div>
            <Badge variant={isValid ? "secondary" : "destructive"}>
              {errors.length} errors, {warnings.length} warnings
            </Badge>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
}

/**
 * Compact validation status for tab headers or summary views
 */
export function ValidationStatusBadge({ validation }: { validation: ValidationResult }) {
  const { isValid, errors, warnings } = validation;

  if (isValid && warnings.length === 0) {
    return (
      <Badge variant="outline" className="text-green-600 border-green-600">
        <CheckCircle className="h-3 w-3 mr-1" />
        Valid
      </Badge>
    );
  }

  if (isValid && warnings.length > 0) {
    return (
      <Badge variant="outline" className="text-rose-600 border-rose-600 dark:text-rose-400 dark:border-rose-400">
        <AlertTriangle className="h-3 w-3 mr-1" />
        {warnings.length} warning{warnings.length > 1 ? 's' : ''}
      </Badge>
    );
  }

  return (
    <Badge variant="destructive">
      <AlertCircle className="h-3 w-3 mr-1" />
      {errors.length} error{errors.length > 1 ? 's' : ''}
    </Badge>
  );
}