/**
 * MCP Provider Form Component
 * 
 * Form for creating and editing external search providers.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { useMCPProviders } from '../../hooks/use-mcp-providers';
import type { MCPProvider, MCPProviderConfig } from '@/lib/config/api';

const formSchema = z.object({
  provider_id: z.string().min(1, 'Provider ID is required'),
  provider_type: z.string().min(1, 'Provider type is required'),
  enabled: z.boolean().default(true),
  api_key: z.string().optional(),
  api_endpoint: z.string().url().optional().or(z.literal('')),
  priority: z.number().min(1).max(10).default(1),
  max_results: z.number().min(1).max(50).default(10),
  timeout_seconds: z.number().min(0.5).max(10).default(3),
  rate_limit_per_minute: z.number().min(1).max(1000).default(60),
  custom_headers: z.string().optional(),
  custom_params: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

interface MCPProviderFormProps {
  isOpen: boolean;
  provider?: MCPProvider;
  onClose: () => void;
  onSuccess: () => void;
}

const PROVIDER_TYPES = [
  { value: 'brave', label: 'Brave Search' },
  { value: 'google', label: 'Google Search' },
  { value: 'duckduckgo', label: 'DuckDuckGo' },
  { value: 'bing', label: 'Bing Search' },
  { value: 'searxng', label: 'SearXNG' },
];

export function MCPProviderForm({ isOpen, provider, onClose, onSuccess }: MCPProviderFormProps) {
  const { createProvider, updateProvider } = useMCPProviders();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEditing = !!provider;

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      provider_id: '',
      provider_type: '',
      enabled: true,
      api_key: '',
      api_endpoint: '',
      priority: 1,
      max_results: 10,
      timeout_seconds: 3,
      rate_limit_per_minute: 60,
      custom_headers: '',
      custom_params: '',
    },
  });

  // Populate form when editing
  useEffect(() => {
    if (provider) {
      form.reset({
        provider_id: provider.config.provider_id,
        provider_type: provider.config.provider_type,
        enabled: provider.config.enabled,
        api_key: provider.config.api_key || '',
        api_endpoint: provider.config.api_endpoint || '',
        priority: provider.config.priority,
        max_results: provider.config.max_results,
        timeout_seconds: provider.config.timeout_seconds,
        rate_limit_per_minute: provider.config.rate_limit_per_minute,
        custom_headers: JSON.stringify(provider.config.custom_headers, null, 2),
        custom_params: JSON.stringify(provider.config.custom_params, null, 2),
      });
    }
  }, [provider, form]);

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    
    try {
      // Parse JSON fields
      let customHeaders = {};
      let customParams = {};
      
      if (data.custom_headers) {
        try {
          customHeaders = JSON.parse(data.custom_headers);
        } catch (e) {
          form.setError('custom_headers', { message: 'Invalid JSON format' });
          setIsSubmitting(false);
          return;
        }
      }
      
      if (data.custom_params) {
        try {
          customParams = JSON.parse(data.custom_params);
        } catch (e) {
          form.setError('custom_params', { message: 'Invalid JSON format' });
          setIsSubmitting(false);
          return;
        }
      }

      const config: MCPProviderConfig = {
        provider_id: data.provider_id,
        provider_type: data.provider_type,
        enabled: data.enabled,
        api_key: data.api_key || undefined,
        api_endpoint: data.api_endpoint || undefined,
        priority: data.priority,
        max_results: data.max_results,
        timeout_seconds: data.timeout_seconds,
        rate_limit_per_minute: data.rate_limit_per_minute,
        custom_headers: customHeaders,
        custom_params: customParams,
      };

      if (isEditing) {
        await updateProvider(provider.provider_id, config);
      } else {
        await createProvider(config);
      }
      
      onSuccess();
    } catch (error) {
      console.error('Failed to save provider:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Provider' : 'Add External Search Provider'}
          </DialogTitle>
          <DialogDescription>
            Configure an external search provider to enhance search results with web content.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Basic Configuration */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Basic Configuration</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="provider_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Provider ID</FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="brave_search" 
                          {...field}
                          disabled={isEditing}
                        />
                      </FormControl>
                      <FormDescription>
                        Unique identifier for this provider
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="provider_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Provider Type</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {PROVIDER_TYPES.map((type) => (
                            <SelectItem key={type.value} value={type.value}>
                              {type.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="enabled"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Enable Provider</FormLabel>
                      <FormDescription>
                        Whether this provider should be used for searches
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>

            <Separator />

            {/* API Configuration */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">API Configuration</h3>
              
              <FormField
                control={form.control}
                name="api_key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>API Key</FormLabel>
                    <FormControl>
                      <Input 
                        type="password" 
                        placeholder="Enter API key" 
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      API key for authenticating with the provider
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="api_endpoint"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Custom API Endpoint (Optional)</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="https://api.example.com/search" 
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      Override the default API endpoint URL
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Separator />

            {/* Performance Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Performance Settings</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="priority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Priority</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={1} 
                          max={10} 
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>
                        1 = highest priority, 10 = lowest
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="max_results"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Max Results</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={1} 
                          max={50} 
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>
                        Maximum results per request
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="timeout_seconds"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Timeout (seconds)</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={0.5} 
                          max={10} 
                          step={0.1}
                          {...field}
                          onChange={(e) => field.onChange(parseFloat(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>
                        Request timeout in seconds
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="rate_limit_per_minute"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Rate Limit</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          min={1} 
                          max={1000} 
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value))}
                        />
                      </FormControl>
                      <FormDescription>
                        Requests per minute
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <Separator />

            {/* Advanced Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Advanced Settings</h3>
              
              <FormField
                control={form.control}
                name="custom_headers"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Custom Headers (JSON)</FormLabel>
                    <FormControl>
                      <Textarea 
                        placeholder='{"User-Agent": "MyApp/1.0"}'
                        rows={3}
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      Additional HTTP headers as JSON object
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="custom_params"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Custom Parameters (JSON)</FormLabel>
                    <FormControl>
                      <Textarea 
                        placeholder='{"region": "us", "lang": "en"}'
                        rows={3}
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      Additional API parameters as JSON object
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : isEditing ? 'Update Provider' : 'Create Provider'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}