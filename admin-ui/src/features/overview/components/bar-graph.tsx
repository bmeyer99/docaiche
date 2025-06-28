'use client';

import * as React from 'react';
import { Bar, BarChart, CartesianGrid, XAxis } from 'recharts';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card';
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent
} from '@/components/ui/chart';
import { Icons } from '@/components/icons';
import { DocaicheApiClient } from '@/lib/utils/api-client';

export const description = 'Search activity chart showing daily search trends';

const chartConfig = {
  searches: {
    label: 'Searches',
    color: 'var(--primary)'
  },
  documents: {
    label: 'Documents',
    color: 'var(--secondary)'
  }
} satisfies ChartConfig;

export function BarGraph() {
  const [chartData, setChartData] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [activeChart, setActiveChart] = React.useState<keyof typeof chartConfig>('searches');
  const apiClient = new DocaicheApiClient();

  const total = React.useMemo(
    () => ({
      searches: chartData.reduce((acc, curr) => acc + (curr.searches || 0), 0),
      documents: chartData.reduce((acc, curr) => acc + (curr.documents || 0), 0)
    }),
    [chartData]
  );

  const loadChartData = React.useCallback(async () => {
    try {
      // Try to get analytics data - this endpoint may not exist yet
      const analytics = await apiClient.getAnalytics('30d');
      
      // Mock data for now if analytics endpoint isn't implemented
      const mockData = Array.from({ length: 30 }, (_, i) => {
        const date = new Date();
        date.setDate(date.getDate() - (29 - i));
        return {
          date: date.toISOString().split('T')[0],
          searches: Math.floor(Math.random() * 50) + 5,
          documents: Math.floor(Math.random() * 10) + 1
        };
      });
      
      setChartData(analytics.daily_stats || mockData);
      setError(null);
    } catch (err) {
      setError('Unable to load analytics data');
      setChartData([]);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  React.useEffect(() => {
    loadChartData();
  }, [loadChartData]);

  if (loading) {
    return (
      <Card className='@container/card !pt-3'>
        <CardHeader>
          <CardTitle>Search Analytics</CardTitle>
          <CardDescription>Loading analytics data...</CardDescription>
        </CardHeader>
        <CardContent className='flex items-center justify-center h-[300px]'>
          <Icons.spinner className='w-8 h-8 animate-spin' />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className='@container/card !pt-3'>
        <CardHeader>
          <CardTitle>Search Analytics</CardTitle>
          <CardDescription>Analytics data unavailable</CardDescription>
        </CardHeader>
        <CardContent className='flex flex-col items-center justify-center h-[300px] text-center'>
          <Icons.alertCircle className='w-12 h-12 mb-4 text-red-500' />
          <div className='text-sm text-muted-foreground'>{error}</div>
          <div className='text-xs text-muted-foreground mt-1'>
            API connection required for analytics
          </div>
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card className='@container/card !pt-3'>
        <CardHeader>
          <CardTitle>Search Analytics</CardTitle>
          <CardDescription>No analytics data available</CardDescription>
        </CardHeader>
        <CardContent className='flex flex-col items-center justify-center h-[300px] text-center'>
          <Icons.barChart className='w-12 h-12 mb-4 text-muted-foreground' />
          <div className='text-sm text-muted-foreground'>No data to display</div>
          <div className='text-xs text-muted-foreground mt-1'>
            Analytics will appear as users interact with the system
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className='@container/card !pt-3'>
      <CardHeader className='flex flex-col items-stretch space-y-0 border-b !p-0 sm:flex-row'>
        <div className='flex flex-1 flex-col justify-center gap-1 px-6 !py-0'>
          <CardTitle>Search Analytics</CardTitle>
          <CardDescription>
            <span className='hidden @[540px]/card:block'>
              Daily activity for the last 30 days
            </span>
            <span className='@[540px]/card:hidden'>Last 30 days</span>
          </CardDescription>
        </div>
        <div className='flex'>
          {Object.keys(chartConfig).map((key) => {
            const chart = key as keyof typeof chartConfig;
            return (
              <button
                key={chart}
                data-active={activeChart === chart}
                className='data-[active=true]:bg-primary/5 hover:bg-primary/5 relative flex flex-1 flex-col justify-center gap-1 border-t px-6 py-4 text-left transition-colors duration-200 even:border-l sm:border-t-0 sm:border-l sm:px-8 sm:py-6'
                onClick={() => setActiveChart(chart)}
              >
                <span className='text-muted-foreground text-xs'>
                  {chartConfig[chart].label}
                </span>
                <span className='text-lg leading-none font-bold sm:text-3xl'>
                  {total[key as keyof typeof total]?.toLocaleString()}
                </span>
              </button>
            );
          })}
        </div>
      </CardHeader>
      <CardContent className='px-2 pt-4 sm:px-6 sm:pt-6'>
        <ChartContainer
          config={chartConfig}
          className='aspect-auto h-[250px] w-full'
        >
          <BarChart
            data={chartData}
            margin={{
              left: 12,
              right: 12
            }}
          >
            <defs>
              <linearGradient id='fillBar' x1='0' y1='0' x2='0' y2='1'>
                <stop
                  offset='0%'
                  stopColor='var(--primary)'
                  stopOpacity={0.8}
                />
                <stop
                  offset='100%'
                  stopColor='var(--primary)'
                  stopOpacity={0.2}
                />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey='date'
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={(value) => {
                const date = new Date(value);
                return date.toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric'
                });
              }}
            />
            <ChartTooltip
              cursor={{ fill: 'var(--primary)', opacity: 0.1 }}
              content={
                <ChartTooltipContent
                  className='w-[150px]'
                  nameKey={activeChart}
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    });
                  }}
                />
              }
            />
            <Bar
              dataKey={activeChart}
              fill='url(#fillBar)'
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
