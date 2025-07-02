'use client';

import { useState, useEffect } from 'react';
import { LazyLog } from '@melloware/react-logviewer';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DownloadIcon, RefreshCwIcon, CopyIcon } from 'lucide-react';
import { apiClient } from '@/lib/utils/api-client';
import { useToast } from '@/hooks/use-toast';
import { format } from 'date-fns';

interface HistoricalLogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  serviceId: string;
  serviceName: string;
}

export function HistoricalLogsModal({
  isOpen,
  onClose,
  serviceId,
  serviceName,
}: HistoricalLogsModalProps) {
  const [logs, setLogs] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [logLevel, setLogLevel] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [timeRange, setTimeRange] = useState('1h');
  const [customStartTime, setCustomStartTime] = useState('');
  const [customEndTime, setCustomEndTime] = useState('');
  const { toast } = useToast();

  const fetchLogs = async () => {
    setLoading(true);
    try {
      // Calculate time range
      let startTime = new Date();
      const endTime = new Date();
      
      if (timeRange === 'custom' && customStartTime && customEndTime) {
        startTime = new Date(customStartTime);
      } else {
        switch (timeRange) {
          case '15m':
            startTime.setMinutes(startTime.getMinutes() - 15);
            break;
          case '1h':
            startTime.setHours(startTime.getHours() - 1);
            break;
          case '6h':
            startTime.setHours(startTime.getHours() - 6);
            break;
          case '24h':
            startTime.setHours(startTime.getHours() - 24);
            break;
          case '7d':
            startTime.setDate(startTime.getDate() - 7);
            break;
        }
      }

      const params = new URLSearchParams({
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        limit: '5000',
      });

      if (logLevel !== 'all') {
        params.append('level', logLevel);
      }

      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const response = await apiClient.get<{
        logs: Array<{
          timestamp: string;
          level: string;
          service: string;
          message: string;
          metadata?: Record<string, any>;
        }>;
        total: number;
        has_more: boolean;
      }>(`/logs/${serviceId}?${params}`);
      
      if (response.logs && response.logs.length > 0) {
        // Format logs for display
        const formattedLogs = response.logs
          .map((log) => {
            const timestamp = new Date(log.timestamp).toLocaleString();
            const level = log.level.padEnd(5);
            const message = log.message;
            
            // Add ANSI color codes for log levels
            let levelColor = '';
            switch (log.level) {
              case 'ERROR':
              case 'FATAL':
                levelColor = '\x1b[31m'; // Red
                break;
              case 'WARN':
              case 'WARNING':
                levelColor = '\x1b[33m'; // Yellow
                break;
              case 'INFO':
                levelColor = '\x1b[36m'; // Cyan
                break;
              case 'DEBUG':
                levelColor = '\x1b[90m'; // Gray
                break;
            }
            
            return `[${timestamp}] ${levelColor}[${level}]\x1b[0m ${message}`;
          })
          .join('\n');
        
        setLogs(formattedLogs);
        toast({
          title: 'Logs loaded',
          description: `Found ${response.logs.length} logs`,
        });
      } else {
        setLogs('No logs found for the selected criteria.');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch historical logs',
        variant: 'destructive',
      });
      setLogs('Error loading logs. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen, serviceId, fetchLogs]);

  const handleCopy = async () => {
    if (!logs || logs === 'No logs found for the selected criteria.') {
      toast({
        title: 'No logs to copy',
        description: 'There are no logs to copy to clipboard',
        variant: 'destructive'
      });
      return;
    }

    try {
      await navigator.clipboard.writeText(logs);
      toast({
        title: 'Copied to clipboard',
        description: 'Logs copied successfully',
      });
    } catch (error) {
      toast({
        title: 'Copy failed',
        description: 'Failed to copy logs to clipboard',
        variant: 'destructive',
      });
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams({
        format: 'txt',
        start_time: customStartTime || new Date(Date.now() - 3600000).toISOString(),
        end_time: customEndTime || new Date().toISOString(),
      });

      if (logLevel !== 'all') {
        params.append('level', logLevel);
      }

      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const response = await fetch(`/api/v1/logs/${serviceId}/export?${params}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${serviceId}-logs-${format(new Date(), 'yyyyMMdd-HHmmss')}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: 'Success',
        description: 'Logs exported successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to export logs',
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Historical Logs - {serviceName}</DialogTitle>
          <DialogDescription>
            View and search through historical logs for {serviceName}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <div className="flex-1 min-w-[200px]">
              <Label htmlFor="search">Search</Label>
              <Input
                id="search"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className="w-[150px]">
              <Label htmlFor="level">Log Level</Label>
              <Select value={logLevel} onValueChange={setLogLevel}>
                <SelectTrigger id="level">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Levels</SelectItem>
                  <SelectItem value="DEBUG">Debug</SelectItem>
                  <SelectItem value="INFO">Info</SelectItem>
                  <SelectItem value="WARN">Warning</SelectItem>
                  <SelectItem value="ERROR">Error</SelectItem>
                  <SelectItem value="FATAL">Fatal</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="w-[150px]">
              <Label htmlFor="timeRange">Time Range</Label>
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger id="timeRange">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="15m">Last 15 minutes</SelectItem>
                  <SelectItem value="1h">Last hour</SelectItem>
                  <SelectItem value="6h">Last 6 hours</SelectItem>
                  <SelectItem value="24h">Last 24 hours</SelectItem>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="custom">Custom range</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {timeRange === 'custom' && (
              <>
                <div className="w-[200px]">
                  <Label htmlFor="startTime">Start Time</Label>
                  <Input
                    id="startTime"
                    type="datetime-local"
                    value={customStartTime}
                    onChange={(e) => setCustomStartTime(e.target.value)}
                  />
                </div>
                <div className="w-[200px]">
                  <Label htmlFor="endTime">End Time</Label>
                  <Input
                    id="endTime"
                    type="datetime-local"
                    value={customEndTime}
                    onChange={(e) => setCustomEndTime(e.target.value)}
                  />
                </div>
              </>
            )}

            <div className="flex items-end gap-2">
              <Button onClick={fetchLogs} disabled={loading}>
                <RefreshCwIcon className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button onClick={handleCopy} variant="outline">
                <CopyIcon className="h-4 w-4 mr-2" />
                Copy
              </Button>
              <Button onClick={handleExport} variant="outline">
                <DownloadIcon className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>

          {/* Log Viewer */}
          <div className="flex-1 border rounded-lg overflow-hidden bg-black">
            {loading ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                Loading logs...
              </div>
            ) : logs ? (
              <div style={{ height: '100%', width: '100%' }}>
                <LazyLog
                  text={logs}
                  follow={false}
                  enableSearch
                  searchWords={searchTerm ? [searchTerm] : undefined}
                  caseInsensitive
                  height="100%"
                  style={{
                    backgroundColor: '#000',
                    color: '#fff',
                    fontFamily: 'monospace',
                    fontSize: '13px',
                  }}
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                No logs to display
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}