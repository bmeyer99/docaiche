'use client';

import * as React from 'react';
import { IconTrendingUp } from '@tabler/icons-react';
import { Label, Pie, PieChart } from 'recharts';

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
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

const chartConfig = {
  documents: {
    label: 'Documents'
  },
  python: {
    label: 'Python',
    color: 'var(--primary)'
  },
  javascript: {
    label: 'JavaScript',
    color: 'var(--primary)'
  },
  typescript: {
    label: 'TypeScript',
    color: 'var(--primary)'
  },
  react: {
    label: 'React',
    color: 'var(--primary)'
  },
  other: {
    label: 'Other',
    color: 'var(--primary)'
  }
} satisfies ChartConfig;

export function PieGraph() {
  const [chartData, setChartData] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const apiClient = new DocaicheApiClient();

  React.useEffect(() => {
    loadContentDistribution();
  }, []);

  const loadContentDistribution = async () => {
    try {
      // Try to get collections data to understand content distribution
      const collections = await apiClient.getCollections();
      
      // Group by technology
      const techCounts = collections.collections.reduce((acc: any, collection: any) => {
        const tech = collection.technology || 'other';
        acc[tech] = (acc[tech] || 0) + collection.document_count;
        return acc;
      }, {});

      // Convert to chart format
      const data = Object.entries(techCounts).map(([tech, count], index) => ({
        technology: tech,
        documents: count,
        fill: `url(#fill${tech})`
      }));

      setChartData(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load content distribution:', err);
      setError('Unable to load content distribution');
      setChartData([]);
    } finally {
      setLoading(false);
    }
  };

  const totalDocuments = React.useMemo(() => {
    return chartData.reduce((acc, curr) => acc + curr.documents, 0);
  }, [chartData]);

  const topTechnology = React.useMemo(() => {
    if (chartData.length === 0) return null;
    return chartData.reduce((prev, current) => 
      prev.documents > current.documents ? prev : current
    );
  }, [chartData]);

  if (loading) {
    return (
      <Card className='@container/card'>
        <CardHeader>
          <CardTitle>Content Distribution</CardTitle>
          <CardDescription>Loading content breakdown...</CardDescription>
        </CardHeader>
        <CardContent className='flex items-center justify-center h-[300px]'>
          <Icons.spinner className='w-8 h-8 animate-spin' />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className='@container/card'>
        <CardHeader>
          <CardTitle>Content Distribution</CardTitle>
          <CardDescription>Content breakdown unavailable</CardDescription>
        </CardHeader>
        <CardContent className='flex flex-col items-center justify-center h-[300px] text-center'>
          <Icons.alertCircle className='w-12 h-12 mb-4 text-red-500' />
          <div className='text-sm text-muted-foreground'>{error}</div>
          <div className='text-xs text-muted-foreground mt-1'>
            API connection required for content statistics
          </div>
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card className='@container/card'>
        <CardHeader>
          <CardTitle>Content Distribution</CardTitle>
          <CardDescription>No content data available</CardDescription>
        </CardHeader>
        <CardContent className='flex flex-col items-center justify-center h-[300px] text-center'>
          <Icons.circle className='w-12 h-12 mb-4 text-muted-foreground' />
          <div className='text-sm text-muted-foreground'>No content to analyze</div>
          <div className='text-xs text-muted-foreground mt-1'>
            Content distribution will appear after documents are indexed
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className='@container/card'>
      <CardHeader>
        <CardTitle>Content Distribution</CardTitle>
        <CardDescription>
          <span className='hidden @[540px]/card:block'>
            Documents by technology/framework
          </span>
          <span className='@[540px]/card:hidden'>Technology breakdown</span>
        </CardDescription>
      </CardHeader>
      <CardContent className='px-2 pt-4 sm:px-6 sm:pt-6'>
        <ChartContainer
          config={chartConfig}
          className='mx-auto aspect-square h-[250px]'
        >
          <PieChart>
            <defs>
              {chartData.map((item, index) => (
                <linearGradient
                  key={item.technology}
                  id={`fill${item.technology}`}
                  x1='0'
                  y1='0'
                  x2='0'
                  y2='1'
                >
                  <stop
                    offset='0%'
                    stopColor='var(--primary)'
                    stopOpacity={1 - index * 0.15}
                  />
                  <stop
                    offset='100%'
                    stopColor='var(--primary)'
                    stopOpacity={0.8 - index * 0.15}
                  />
                </linearGradient>
              ))}
            </defs>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Pie
              data={chartData}
              dataKey='documents'
              nameKey='technology'
              innerRadius={60}
              strokeWidth={2}
              stroke='var(--background)'
            >
              <Label
                content={({ viewBox }) => {
                  if (viewBox && 'cx' in viewBox && 'cy' in viewBox) {
                    return (
                      <text
                        x={viewBox.cx}
                        y={viewBox.cy}
                        textAnchor='middle'
                        dominantBaseline='middle'
                      >
                        <tspan
                          x={viewBox.cx}
                          y={viewBox.cy}
                          className='fill-foreground text-3xl font-bold'
                        >
                          {totalDocuments.toLocaleString()}
                        </tspan>
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy || 0) + 24}
                          className='fill-muted-foreground text-sm'
                        >
                          Total Documents
                        </tspan>
                      </text>
                    );
                  }
                }}
              />
            </Pie>
          </PieChart>
        </ChartContainer>
      </CardContent>
      <CardFooter className='flex-col gap-2 text-sm'>
        {topTechnology && (
          <div className='flex items-center gap-2 leading-none font-medium'>
            {topTechnology.technology} leads with{' '}
            {((topTechnology.documents / totalDocuments) * 100).toFixed(1)}%{' '}
            <IconTrendingUp className='h-4 w-4' />
          </div>
        )}
        <div className='text-muted-foreground leading-none'>
          Based on indexed documentation collections
        </div>
      </CardFooter>
    </Card>
  );
}
