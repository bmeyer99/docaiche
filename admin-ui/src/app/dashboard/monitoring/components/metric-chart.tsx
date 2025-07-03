'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import ReactECharts from 'echarts-for-react';
import { EChartsOption, ECharts } from 'echarts';
import { format } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Maximize2, Download, RefreshCw, Info } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { MetricSeries } from '../services/prometheus-client';

export interface MetricChartProps {
  title: string;
  series: MetricSeries[];
  height?: string | number;
  onTimeRangeChange?: (start: number, end: number) => void;
  onDataPointClick?: (params: any) => void;
  onRefresh?: () => void;
  loading?: boolean;
  unit?: string;
  description?: string;
  fullscreen?: boolean;
  enableZoom?: boolean;
  enableBrush?: boolean;
  showLegend?: boolean;
  chartType?: 'line' | 'area' | 'bar' | 'scatter';
}

export const MetricChart: React.FC<MetricChartProps> = ({
  title,
  series,
  height = 300,
  onTimeRangeChange,
  onDataPointClick,
  onRefresh,
  loading = false,
  unit = '',
  description,
  fullscreen = false,
  enableZoom = true,
  enableBrush = true,
  showLegend = true,
  chartType = 'line'
}) => {
  const chartRef = useRef<ECharts | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState<any>(null);
  const [showDetails, setShowDetails] = useState(false);

  // Build ECharts option
  const getOption = useCallback((): EChartsOption => {
    const option: EChartsOption = {
      animation: true,
      animationDuration: 300,
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          animation: true,
          label: {
            backgroundColor: '#505765'
          }
        },
        formatter: (params: any) => {
          if (!Array.isArray(params)) return '';
          
          const time = format(new Date(params[0].value[0]), 'MMM dd, HH:mm:ss');
          let tooltip = `<strong>${time}</strong><br/>`;
          
          params.forEach((param: any) => {
            const value = param.value[1];
            const formattedValue = typeof value === 'number' 
              ? value.toFixed(2) 
              : value;
            
            tooltip += `
              <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${param.color};"></span>
              ${param.seriesName}: <strong>${formattedValue}${unit}</strong><br/>
            `;
          });
          
          tooltip += '<br/><em>Click for details</em>';
          return tooltip;
        }
      },
      legend: {
        show: showLegend,
        type: 'scroll',
        bottom: 0,
        data: series.map(s => s.name)
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: showLegend ? '15%' : '3%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'time',
        boundaryGap: chartType === 'bar' ? true : false,
        axisLabel: {
          formatter: (value: number) => format(new Date(value), 'HH:mm')
        },
        axisPointer: {
          label: {
            formatter: (params: any) => {
              return format(new Date(params.value), 'MMM dd, HH:mm:ss');
            }
          }
        }
      } as any,
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => `${value}${unit}`
        },
        splitLine: {
          show: true,
          lineStyle: {
            type: 'dashed',
            opacity: 0.3
          }
        }
      },
      dataZoom: enableZoom ? [
        {
          type: 'inside',
          start: 0,
          end: 100,
          filterMode: 'none'
        },
        {
          show: enableBrush,
          type: 'slider',
          start: 0,
          end: 100,
          filterMode: 'none',
          height: 20,
          bottom: showLegend ? 40 : 5
        }
      ] : [],
      series: series.map((s, index) => ({
        name: s.name,
        type: chartType === 'area' ? 'line' : chartType,
        stack: chartType === 'area' ? 'Total' : undefined,
        areaStyle: chartType === 'area' ? {} : undefined,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        sampling: 'average',
        itemStyle: {
          color: getSeriesColor(index)
        },
        lineStyle: {
          width: 2
        },
        emphasis: {
          focus: 'series',
          itemStyle: {
            symbolSize: 8,
            borderWidth: 2
          }
        },
        data: s.data.map(d => [d.timestamp, d.value])
      }))
    };

    return option;
  }, [series, unit, showLegend, enableZoom, enableBrush, chartType]);

  // Handle chart events
  const onChartReady = (chart: ECharts) => {
    chartRef.current = chart;

    // Handle click events
    chart.on('click', (params: any) => {
      if (params.componentType === 'series') {
        setSelectedPoint(params);
        setShowDetails(true);
        
        if (onDataPointClick) {
          onDataPointClick(params);
        }
      }
    });

    // Handle brush selection
    if (enableBrush) {
      chart.on('datazoom', (params: any) => {
        if (onTimeRangeChange && params.batch) {
          const { startValue, endValue } = params.batch[0];
          onTimeRangeChange(startValue, endValue);
        }
      });
    }
  };

  // Export chart as image
  const exportChart = () => {
    if (chartRef.current) {
      const url = chartRef.current.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
      });
      
      const link = document.createElement('a');
      link.download = `${title.replace(/\s+/g, '_')}_${Date.now()}.png`;
      link.href = url;
      link.click();
    }
  };

  // Get color for series
  const getSeriesColor = (index: number): string => {
    const colors = [
      '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
      '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
    ];
    return colors[index % colors.length];
  };

  const containerHeight = isFullscreen ? 'calc(100vh - 200px)' : height;

  return (
    <>
      <Card className={isFullscreen ? 'fixed inset-4 z-50' : ''}>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg font-medium">{title}</CardTitle>
            {description && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-6 w-6">
                    <Info className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <div className="p-2 text-sm">{description}</div>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
          <div className="flex items-center gap-1">
            {onRefresh && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onRefresh}
                disabled={loading}
                className="h-8 w-8"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Download className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={exportChart}>
                  Export as PNG
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => {
                  // Export data as CSV
                  const csv = series.map(s => 
                    s.data.map(d => `${s.name},${d.timestamp},${d.value}`).join('\n')
                  ).join('\n');
                  
                  const blob = new Blob([`Series,Timestamp,Value\n${csv}`], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.download = `${title.replace(/\s+/g, '_')}_data.csv`;
                  link.href = url;
                  link.click();
                }}>
                  Export as CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="h-8 w-8"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <ReactECharts
            option={getOption()}
            style={{ height: containerHeight, width: '100%' }}
            onChartReady={onChartReady}
            opts={{ renderer: 'canvas' }}
            notMerge={true}
            lazyUpdate={true}
          />
        </CardContent>
      </Card>

      <Dialog open={showDetails} onOpenChange={setShowDetails}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Data Point Details</DialogTitle>
            <DialogDescription>
              Click-through details for the selected data point
            </DialogDescription>
          </DialogHeader>
          {selectedPoint && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium">Time</h4>
                <p className="text-sm text-muted-foreground">
                  {format(new Date(selectedPoint.value[0]), 'PPpp')}
                </p>
              </div>
              <div>
                <h4 className="text-sm font-medium">Series</h4>
                <p className="text-sm text-muted-foreground">{selectedPoint.seriesName}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium">Value</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedPoint.value[1]}{unit}
                </p>
              </div>
              {selectedPoint.data?.metadata && (
                <div>
                  <h4 className="text-sm font-medium">Metadata</h4>
                  <pre className="text-xs bg-muted p-2 rounded">
                    {JSON.stringify(selectedPoint.data.metadata, null, 2)}
                  </pre>
                </div>
              )}
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    // Navigate to logs view for this time
                    window.open(
                      `/dashboard/logs?time=${selectedPoint.value[0]}`,
                      '_blank'
                    );
                  }}
                >
                  View Logs
                </Button>
                <Button
                  onClick={() => {
                    // Show correlated metrics
                    console.log('Show correlated metrics for', selectedPoint);
                  }}
                >
                  Correlate
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default MetricChart;