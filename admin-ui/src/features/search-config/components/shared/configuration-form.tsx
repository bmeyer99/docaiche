'use client';

/**
 * Base configuration form component with validation
 */

import React, { useEffect } from 'react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { ConfigurationFormProps } from '../../types';

export function ConfigurationForm({
  initialValues,
  onSubmit,
  onChange,
  validationSchema,
  disabled = false,
  children
}: ConfigurationFormProps & { children: React.ReactNode }) {
  const methods = useForm({
    defaultValues: initialValues,
    resolver: validationSchema ? zodResolver(validationSchema) : undefined,
    mode: 'onChange'
  });

  const {
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    watch,
    reset
  } = methods;

  // Watch for changes
  useEffect(() => {
    const subscription = watch((values) => {
      onChange?.(values);
    });
    return () => subscription.unsubscribe();
  }, [watch, onChange]);

  // Reset form when initial values change
  useEffect(() => {
    reset(initialValues);
  }, [initialValues, reset]);

  const onFormSubmit = async (data: any) => {
    try {
      await onSubmit(data);
      reset(data); // Reset form state after successful save
    } catch (error) {
      console.error('Form submission error:', error);
    }
  };

  const hasErrors = Object.keys(errors).length > 0;

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
        {hasErrors && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Please fix the errors below before saving.
            </AlertDescription>
          </Alert>
        )}

        {children}

        {isDirty && (
          <div className="sticky bottom-0 bg-background border-t p-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              You have unsaved changes
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => reset()}
                disabled={isSubmitting || disabled}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting || disabled || hasErrors}
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </div>
          </div>
        )}
      </form>
    </FormProvider>
  );
}