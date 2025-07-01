'use client'

import React, { useEffect } from 'react'
import { ConfigurationPanelProps, ProviderFormData } from '../types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { getProviderSchema, getProviderDefaults, getProviderFields } from '../utils/provider-schemas'

/**
 * ConfigurationPanel - Dynamic form for provider-specific configuration
 * 
 * Renders appropriate form fields based on the selected provider,
 * handles validation, and provides connection testing functionality.
 */
export function ConfigurationPanel({
  provider,
  configuration,
  isTestingConnection,
  testResult,
  onConfigurationChange,
  onTestConnection,
  onSaveConfiguration,
  isSaving = false
}: ConfigurationPanelProps) {
  const [saveError, setSaveError] = React.useState<string | null>(null)
  
  // Initialize form with provider-specific schema and defaults
  const form = useForm<ProviderFormData>({
    resolver: provider ? zodResolver(getProviderSchema(provider.id)) : undefined,
    defaultValues: provider ? {
      ...getProviderDefaults(provider.id),
      ...configuration
    } : {}
  })
  
  // Update form when provider changes or configuration changes
  useEffect(() => {
    if (provider) {
      const defaults = getProviderDefaults(provider.id)
      const values = {
        ...defaults,
        ...configuration
      }
      form.reset(values)
      setSaveError(null) // Clear errors on provider change
      
      // Force validation to clear any stale errors
      setTimeout(() => {
        form.trigger()
      }, 100)
    }
  }, [provider?.id, configuration, form]) // Include configuration and form to ensure proper updates
  
  // Handle form submission with error handling
  const handleSubmit = async (data: ProviderFormData) => {
    if (!provider || isSaving) return
    
    setSaveError(null)
    
    try {
      const config = {
        id: provider.id,
        ...data
      }
      onConfigurationChange(config)
      await onSaveConfiguration()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save configuration'
      setSaveError(message)
      // Log error for debugging
    }
  }
  
  if (!provider) {
    return (
      <Card className="flex-1">
        <CardHeader>
          <CardTitle>Select a Provider</CardTitle>
          <CardDescription>
            Choose a provider from the left to begin configuration
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }
  
  // Get fields for the selected provider
  const fields = getProviderFields(provider.id)
  
  // Field type interface
  interface FieldConfig {
    name: string
    label: string
    type: string
    placeholder?: string
    description?: string
    required?: boolean
  }
  
  // Render form field based on type
  const renderField = (field: FieldConfig) => {
    return (
      <FormField
        key={field.name}
        control={form.control}
        name={field.name}
        render={({ field: formField }) => (
          <FormItem>
            <FormLabel>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </FormLabel>
            <FormControl>
              {field.type === 'textarea' ? (
                <Textarea
                  placeholder={field.placeholder}
                  className="min-h-[100px]"
                  {...formField}
                  value={String(formField.value || '')}
                />
              ) : (
                <Input
                  {...formField}
                  type={field.type}
                  placeholder={field.placeholder}
                  value={field.type === 'number' 
                    ? String(formField.value ?? '') 
                    : String(formField.value || '')
                  }
                  onChange={(e) => {
                    const value = field.type === 'number' 
                      ? e.target.value === '' ? undefined : Number(e.target.value)
                      : e.target.value
                    formField.onChange(value)
                  }}
                />
              )}
            </FormControl>
            {field.description && (
              <FormDescription>{field.description}</FormDescription>
            )}
            <FormMessage />
          </FormItem>
        )}
      />
    )
  }
  
  return (
    <Card className="flex-1">
      <CardHeader>
        <CardTitle>Configure {provider.name}</CardTitle>
        <CardDescription>{provider.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            {/* Render dynamic form fields */}
            {fields.map(renderField)}
            
            {/* Test result display */}
            {testResult && (
              <Alert variant={testResult.success ? 'default' : 'destructive'} className={testResult.success ? 'border-green-200 bg-green-50' : ''}>
                {testResult.success ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                <AlertDescription className={testResult.success ? 'text-green-800' : ''}>
                  {testResult.success ? (
                    <>
                      <strong>✅ Connection Successful!</strong><br />
                      {testResult.message}
                      <br />
                      <em>Configuration and available models have been saved automatically.</em>
                    </>
                  ) : (
                    testResult.message
                  )}
                </AlertDescription>
              </Alert>
            )}
            
            {/* Save error display */}
            {saveError && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>{saveError}</AlertDescription>
              </Alert>
            )}
            
            {/* Action buttons */}
            <div className="flex gap-2 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onTestConnection}
                disabled={isTestingConnection || isSaving}
              >
                {isTestingConnection ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Testing...
                  </>
                ) : (
                  'Test Connection'
                )}
              </Button>
              {/* Save Configuration button removed - auto-saves on successful test */}
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}