'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icons } from '@/components/icons';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { ScrollArea } from '@/components/ui/scroll-area';
import { HistoricalLogsModal } from './historical-logs-modal';
import { HistoryIcon, ClipboardCopyIcon } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level: string;
  service: string;
  message: string;
  metadata?: Record<string, any>;
}

interface Service {
  id: string;
  name: string;
  status: string;
  log_level: string;
}

const LOG_LEVELS = [
  { value: 'all', label: 'All Levels' },
  { value: 'DEBUG', label: 'Debug' },
  { value: 'INFO', label: 'Info' },
  { value: 'WARN', label: 'Warning' },
  { value: 'ERROR', label: 'Error' },
  { value: 'FATAL', label: 'Fatal' }
];

const LOG_LEVEL_COLORS = {
  DEBUG: 'text-gray-500',
  INFO: 'text-blue-600',
  WARN: 'text-yellow-600',
  WARNING: 'text-yellow-600',
  ERROR: 'text-red-600',
  FATAL: 'text-red-800 font-bold'
};

export default function LogsViewer() {
  const [services, setServices] = useState<Service[]>([]);
  const [selectedService, setSelectedService] = useState<string>('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(true); // Auto-stream by default
  const [searchTerm, setSearchTerm] = useState('');
  const [logLevel, setLogLevel] = useState('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [showHistorical, setShowHistorical] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const apiClient = useApiClient();
  const { toast } = useToast();

  // Fetch available services
  useEffect(() => {
    const fetchServices = async () => {
      try {
        const response = await apiClient.get<{ services: Service[] }>('/logs/services');
        setServices(response.services);
        // Auto-select browser logs if available
        const browserService = response.services.find(s => s.id === 'browser');
        if (browserService) {
          setSelectedService('browser');
        } else if (response.services.length > 0) {
          setSelectedService(response.services[0].id);
        }
      } catch (error) {
        toast({
          title: 'Failed to fetch services',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive'
        });
      }
    };

    fetchServices();
  }, [apiClient, toast]); // Added dependencies

  // Initial log fetch - reduced to 100 logs to prevent rate limiting issues
  useEffect(() => {
    if (!selectedService) return;

    const fetchInitialLogs = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          limit: '100' // Reduced from 500 to prevent overwhelming the API
        });

        if (logLevel !== 'all') {
          params.append('level', logLevel);
        }

        if (searchTerm) {
          params.append('search', searchTerm);
        }

        const response = await apiClient.get<{ logs: LogEntry[] }>(`/logs/${selectedService}?${params}`);
        setLogs(response.logs);
      } catch (error) {
        // Don't show error toast if it's due to circuit breaker or connection issues
        // The global health provider will handle these notifications
        if (error instanceof Error && !error.message.includes('Circuit Breaker') && !error.message.includes('Connection')) {
          toast({
            title: 'Failed to fetch logs',
            description: error instanceof Error ? error.message : 'Unknown error',
            variant: 'destructive'
          });
        }
      } finally {
        setLoading(false);
      }
    };

    fetchInitialLogs();
  }, [selectedService, apiClient, logLevel, searchTerm, toast]); // Added dependencies

  // Start WebSocket connection for real-time updates
  useEffect(() => {
    if (!selectedService) return;

    // Auto-start streaming for real-time updates
    startStreaming();

    return () => {
      stopStreaming();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedService, logLevel, searchTerm]); // startStreaming is defined below

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [logs, autoScroll]);

  // Start/stop real-time streaming
  const toggleStreaming = () => {
    // Since we auto-stream, this button just controls visibility
    setStreaming(!streaming);
  };

  const startStreaming = () => {
    if (!selectedService || wsRef.current) return;

    const wsUrl = new URL(window.location.href);
    wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:';
    wsUrl.pathname = `/api/v1/logs/ws/${selectedService}`;
    
    const params = new URLSearchParams();
    if (logLevel !== 'all') params.append('level', logLevel);
    if (searchTerm) params.append('search', searchTerm);
    if (params.toString()) wsUrl.search = params.toString();

    const ws = new WebSocket(wsUrl.toString());
    
    ws.onopen = () => {
      setStreaming(true);
      toast({
        title: 'Connected',
        description: 'Real-time log streaming started'
      });
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'connected') {
        // Connection successful, no need to show another toast
        // as we already show one in onopen
      } else if (data.type === 'error') {
        toast({
          title: 'Log Stream Error',
          description: data.data?.message || 'Failed to stream logs',
          variant: 'destructive'
        });
        setStreaming(false);
      } else if (data.type === 'log') {
        // Only add new logs if streaming is enabled
        if (streaming) {
          setLogs(prev => {
            // Prevent duplicates by checking timestamp
            const exists = prev.some(log => 
              log.timestamp === data.data.timestamp && 
              log.message === data.data.message
            );
            if (!exists) {
              return [...prev.slice(-499), data.data];
            }
            return prev;
          });
        }
      }
    };

    ws.onerror = () => {
      // Don't show toast here as the server will send an error message
      // This prevents duplicate error toasts
      setStreaming(false);
    };

    ws.onclose = () => {
      setStreaming(false);
      wsRef.current = null;
    };

    wsRef.current = ws;
  };

  const stopStreaming = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStreaming(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const copyLogsToClipboard = async () => {
    if (logs.length === 0) {
      toast({
        title: 'No logs to copy',
        description: 'There are no logs to copy to clipboard',
        variant: 'destructive'
      });
      return;
    }

    try {
      // Format logs as text
      const textContent = logs.map(log => {
        const timestamp = format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss.SSS');
        return `[${timestamp}] [${log.level}] [${log.service}] ${log.message}`;
      }).join('\n');

      await navigator.clipboard.writeText(textContent);
      
      toast({
        title: 'Copied to clipboard',
        description: `${logs.length} log entries copied`
      });
    } catch (error) {
      toast({
        title: 'Copy failed',
        description: 'Failed to copy logs to clipboard',
        variant: 'destructive'
      });
    }
  };

  const exportLogs = async (format: 'json' | 'csv' | 'txt') => {
    if (!selectedService) return;

    try {
      const params = new URLSearchParams({ format });
      if (logLevel !== 'all') params.append('level', logLevel);
      if (searchTerm) params.append('search', searchTerm);

      const response = await fetch(`/api/v1/logs/${selectedService}/export?${params}`);
      const blob = await response.blob();
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedService}_logs_${new Date().toISOString()}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: 'Logs exported',
        description: `Logs exported as ${format.toUpperCase()}`
      });
    } catch (error) {
      toast({
        title: 'Export failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive'
      });
    }
  };

  const renderLogEntry = (log: LogEntry) => {
    const levelColor = LOG_LEVEL_COLORS[log.level as keyof typeof LOG_LEVEL_COLORS] || 'text-gray-600';
    
    return (
      <div key={`${log.timestamp}-${Math.random()}`} className="py-2 px-3 hover:bg-muted/50 font-mono text-sm">
        <div className="flex items-start gap-2">
          <span className="text-muted-foreground text-xs whitespace-nowrap">
            {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
          </span>
          <span className={cn('font-semibold text-xs w-12', levelColor)}>
            {log.level}
          </span>
          <span className="text-xs text-muted-foreground">
            [{log.service}]
          </span>
          <span className="flex-1 break-all">{log.message}</span>
        </div>
        {log.metadata && Object.keys(log.metadata).length > 0 && (
          <div className="mt-1 ml-24 text-xs text-muted-foreground">
            {Object.entries(log.metadata).map(([key, value]) => (
              <span key={key} className="mr-3">
                {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Logs</h1>
          <p className="text-muted-foreground">View and search logs from all services</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoScroll(!autoScroll)}
            className={cn(autoScroll && 'bg-primary text-primary-foreground')}
          >
            <Icons.trendingUp className="w-4 h-4 mr-1" />
            Auto-scroll
          </Button>
          <Button
            variant={streaming ? 'destructive' : 'default'}
            size="sm"
            onClick={toggleStreaming}
            disabled={!selectedService}
          >
            {streaming ? (
              <>
                <Icons.close className="w-4 h-4 mr-1" />
                Stop
              </>
            ) : (
              <>
                <Icons.arrowRight className="w-4 h-4 mr-1" />
                Stream
              </>
            )}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Log Viewer</span>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowHistorical(true)}
                disabled={!selectedService}
              >
                <HistoryIcon className="w-4 h-4 mr-1" />
                Historical Logs
              </Button>
              <div className="border-l h-6 mx-2" />
              <Button variant="outline" size="sm" onClick={() => copyLogsToClipboard()}>
                <ClipboardCopyIcon className="w-4 h-4 mr-1" />
                Copy
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportLogs('json')}>
                <Icons.externalLink className="w-4 h-4 mr-1" />
                JSON
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportLogs('csv')}>
                <Icons.externalLink className="w-4 h-4 mr-1" />
                CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportLogs('txt')}>
                <Icons.externalLink className="w-4 h-4 mr-1" />
                TXT
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <Select value={selectedService} onValueChange={setSelectedService}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select service" />
              </SelectTrigger>
              <SelectContent>
                {services.map(service => (
                  <SelectItem key={service.id} value={service.id}>
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        'w-2 h-2 rounded-full',
                        service.status === 'running' ? 'bg-green-500' : 'bg-gray-400'
                      )} />
                      {service.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={logLevel} onValueChange={setLogLevel}>
              <SelectTrigger className="w-[150px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LOG_LEVELS.map(level => (
                  <SelectItem key={level.value} value={level.value}>
                    {level.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex-1 relative">
              <Icons.search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            <Button
              variant="outline"
              onClick={async () => {
                setLoading(true);
                try {
                  const params = new URLSearchParams({ limit: '100' }); // Reduced from 500
                  if (logLevel !== 'all') params.append('level', logLevel);
                  if (searchTerm) params.append('search', searchTerm);
                  
                  const response = await apiClient.get<{ logs: LogEntry[] }>(`/logs/${selectedService}?${params}`);
                  setLogs(response.logs);
                } catch (error) {
                  // Don't show error toast if it's due to circuit breaker or connection issues
                  if (error instanceof Error && !error.message.includes('Circuit Breaker') && !error.message.includes('Connection')) {
                    toast({
                      title: 'Failed to refresh logs',
                      description: error instanceof Error ? error.message : 'Unknown error',
                      variant: 'destructive'
                    });
                  }
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading || !selectedService}
            >
              {loading ? (
                <Icons.spinner className="w-4 h-4 animate-spin" />
              ) : (
                <Icons.refresh className="w-4 h-4" />
              )}
            </Button>
          </div>

          <div className="border rounded-lg bg-background">
            <ScrollArea ref={scrollAreaRef} className="h-[600px]">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <Icons.spinner className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
              ) : logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <Icons.folder className="w-12 h-12 mb-2" />
                  <p>No logs found</p>
                </div>
              ) : (
                <div className="divide-y">
                  {logs.map((log, index) => (
                    <div key={index}>
                      {renderLogEntry(log)}
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>

          {wsRef.current && wsRef.current.readyState === WebSocket.OPEN && (
            <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              {streaming ? 'Live streaming' : 'Connected (paused)'} - {logs.length} logs
            </div>
          )}
        </CardContent>
      </Card>

      {selectedService && (
        <HistoricalLogsModal
          isOpen={showHistorical}
          onClose={() => setShowHistorical(false)}
          serviceId={selectedService}
          serviceName={services.find(s => s.id === selectedService)?.name || selectedService}
        />
      )}
    </div>
  );
}