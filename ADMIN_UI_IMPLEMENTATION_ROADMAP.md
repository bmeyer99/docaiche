# Docaiche Admin UI - Implementation Roadmap

## Overview
This roadmap transforms the existing shadcn/ui admin template into a focused AI document cache management interface by leveraging existing components and patterns while removing template bloat.

---

## Phase 1: Cleanup & Foundation (Day 1-2)

### 1.1 Remove Template Bloat

#### Delete Unused Features
```bash
# Remove kanban feature entirely
rm -rf src/features/kanban/
rm -rf src/app/dashboard/kanban/

# Remove product management
rm -rf src/features/products/
rm -rf src/app/dashboard/product/

# Remove profile management (keep basic user display)
rm -rf src/features/profile/
rm -rf src/app/dashboard/profile/
```

#### Clean Package Dependencies
```bash
# Remove unused packages
npm uninstall @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities @faker-js/faker

# Keep essential packages for our design:
# - @tanstack/react-table (for document management)
# - recharts (for analytics)
# - lucide-react (for icons)
```

#### Update Navigation Data
**File: `src/constants/data.ts`**
```typescript
// Replace existing navigation with simplified structure
export const navItems = [
  {
    title: "Overview",
    href: "/dashboard",
    icon: "dashboard",
    label: "Dashboard"
  },
  {
    title: "AI Providers", 
    href: "/dashboard/providers",
    icon: "bot",
    label: "Providers"
  },
  {
    title: "Analytics",
    href: "/dashboard/analytics", 
    icon: "barChart3",
    label: "Analytics"
  },
  {
    title: "Documents",
    href: "/dashboard/documents",
    icon: "fileText",
    label: "Documents"
  },
  {
    title: "System Health",
    href: "/dashboard/health",
    icon: "activity",
    label: "Health"
  }
];
```

### 1.2 Simplify Navigation Structure

#### Update App Sidebar
**File: `src/components/layout/app-sidebar.tsx`**
```typescript
// Remove multi-level menu, use flat structure
export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Docaiche Admin</SidebarGroupLabel>
          <SidebarMenu>
            {navItems.map((item) => (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton asChild>
                  <Link href={item.href}>
                    <Icon name={item.icon} />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
```

---

## Phase 2: AI Provider Configuration (Day 3-5)

### 2.1 Provider Hub Page
**File: `src/app/dashboard/providers/page.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function ProvidersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">AI Providers</h1>
        <Button variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Test All
        </Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {providers.map((provider) => (
          <ProviderCard key={provider.id} provider={provider} />
        ))}
      </div>
    </div>
  );
}
```

### 2.2 Provider Card Component
**File: `src/components/providers/provider-card.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ProviderCardProps {
  provider: {
    id: string;
    name: string;
    status: 'connected' | 'configured' | 'error' | 'disabled';
    modelCount?: number;
    category: 'cloud' | 'local' | 'gateway';
  };
}

export function ProviderCard({ provider }: ProviderCardProps) {
  const statusColors = {
    connected: "bg-green-500",
    configured: "bg-yellow-500", 
    error: "bg-red-500",
    disabled: "bg-gray-500"
  };

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{provider.name}</CardTitle>
          <div className={`h-3 w-3 rounded-full ${statusColors[provider.status]}`} />
        </div>
        <Badge variant="secondary">{provider.category}</Badge>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {provider.modelCount} models
          </span>
          <Button size="sm" variant="outline">
            Configure
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 2.3 Dual-Track Configuration
**File: `src/components/providers/provider-config.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";

export function ProviderConfig({ provider }: { provider: Provider }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Text Generation Config */}
      <Card>
        <CardHeader>
          <CardTitle>Text Generation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="model">Model</Label>
            <Select>
              <SelectTrigger>
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {provider.textModels.map(model => (
                  <SelectItem key={model} value={model}>{model}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="api-key">API Key</Label>
            <Input type="password" placeholder="Enter API key" />
          </div>
          
          <div className="space-y-2">
            <Label>Temperature: {temperature}</Label>
            <Slider 
              value={[temperature]} 
              onValueChange={setTemperature}
              max={1} 
              step={0.1} 
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <Switch id="streaming" />
            <Label htmlFor="streaming">Enable Streaming</Label>
          </div>
          
          <Button className="w-full">
            <TestTube className="mr-2 h-4 w-4" />
            Test Configuration
          </Button>
        </CardContent>
      </Card>

      {/* Embeddings Config */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Embeddings</CardTitle>
            <Button variant="ghost" size="sm">
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {provider.supportsEmbeddings ? (
            <EmbeddingConfig provider={provider} />
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Bot className="mx-auto h-8 w-8 mb-2" />
              <p>No embedding support</p>
              <Button variant="link" size="sm">
                Suggest Ollama for embeddings
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Phase 3: Analytics Dashboard (Day 6-8)

### 3.1 Analytics Page Structure
**File: `src/app/dashboard/analytics/page.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Analytics</h1>
        <div className="flex items-center space-x-2">
          <Select defaultValue="24h">
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">24 hours</SelectItem>
              <SelectItem value="7d">7 days</SelectItem>
              <SelectItem value="30d">30 days</SelectItem>
            </SelectContent>
          </Select>
          <Badge variant="outline">Auto-refresh</Badge>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Searches" value="1,247" change="+12%" />
        <MetricCard title="Cache Hit Rate" value="94.2%" change="+2.1%" />
        <MetricCard title="Avg Quality" value="0.82" change="+0.03" />
        <MetricCard title="Uptime" value="99.9%" change="30d" />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SearchVolumeChart />
        <TechnologyMixChart />
        <TopQueriesCloud />
        <ActivityFeed />
      </div>
    </div>
  );
}
```

### 3.2 Metric Cards
**File: `src/components/analytics/metric-card.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  trend?: 'up' | 'down' | 'neutral';
}

export function MetricCard({ title, value, change, trend = 'up' }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <TrendingUp className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <Badge variant={trend === 'up' ? 'default' : 'secondary'} className="text-xs">
          {change}
        </Badge>
      </CardContent>
    </Card>
  );
}
```

### 3.3 Charts Using Recharts
**File: `src/components/analytics/search-volume-chart.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function SearchVolumeChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Search Volume</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={searchData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Line 
              type="monotone" 
              dataKey="searches" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

---

## Phase 4: Document Management (Day 9-11)

### 4.1 Document Browser
**File: `src/app/dashboard/documents/page.tsx`**
```typescript
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function DocumentsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Documents</h1>
        <div className="flex items-center space-x-2">
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </Button>
          <Button variant="outline">
            <MoreHorizontal className="mr-2 h-4 w-4" />
            Bulk Actions
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <Input 
            placeholder="Search documents..." 
            className="max-w-sm"
          />
        </div>
        <Select>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Technology" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="python">Python</SelectItem>
            <SelectItem value="javascript">JavaScript</SelectItem>
            <SelectItem value="react">React</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Document Table */}
      <DataTable 
        columns={documentColumns} 
        data={documents}
        searchKey="title"
      />
    </div>
  );
}
```

### 4.2 Quality Score Component
**File: `src/components/documents/quality-score.tsx`**
```typescript
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

interface QualityScoreProps {
  score: number; // 0-1
  size?: 'sm' | 'md' | 'lg';
}

export function QualityScore({ score, size = 'md' }: QualityScoreProps) {
  const percentage = Math.round(score * 100);
  const variant = score >= 0.8 ? 'default' : score >= 0.5 ? 'secondary' : 'destructive';
  
  if (size === 'sm') {
    return <Badge variant={variant}>{percentage}%</Badge>;
  }
  
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Quality Score</span>
        <span className="text-sm text-muted-foreground">{percentage}%</span>
      </div>
      <Progress value={percentage} className="h-2" />
    </div>
  );
}
```

### 4.3 Document Status Pipeline
**File: `src/components/documents/status-pipeline.tsx`**
```typescript
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

const stages = [
  { name: 'Upload', icon: Upload },
  { name: 'Validate', icon: Shield },
  { name: 'Extract', icon: FileText },
  { name: 'Chunk', icon: Scissors },
  { name: 'Embed', icon: Brain },
  { name: 'Index', icon: Database }
];

export function StatusPipeline({ currentStage, progress }: StatusPipelineProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        {stages.map((stage, index) => (
          <div key={stage.name} className="flex items-center">
            <Badge 
              variant={index <= currentStage ? 'default' : 'secondary'}
              className="flex items-center space-x-1"
            >
              <stage.icon className="h-3 w-3" />
              <span>{stage.name}</span>
            </Badge>
            {index < stages.length - 1 && (
              <div className={`w-8 h-0.5 mx-2 ${
                index < currentStage ? 'bg-primary' : 'bg-muted'
              }`} />
            )}
          </div>
        ))}
      </div>
      <Progress value={progress} />
    </div>
  );
}
```

---

## Phase 5: System Health & Configuration (Day 12-14)

### 5.1 Health Dashboard
**File: `src/app/dashboard/health/page.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export default function HealthPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">System Health</h1>
      
      {/* Component Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <ComponentStatus name="Database" status="healthy" />
        <ComponentStatus name="Redis" status="healthy" />
        <ComponentStatus name="AnythingLLM" status="healthy" />
        <ComponentStatus name="Providers" status="warning" message="1 error" />
      </div>

      {/* Resource Usage */}
      <Card>
        <CardHeader>
          <CardTitle>Resource Usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ResourceMeter label="CPU" value={42} unit="%" />
          <ResourceMeter label="Memory" value={63} unit="%" detail="2.1 GB / 3.3 GB" />
          <ResourceMeter label="Disk" value={24} unit="%" detail="48 GB / 200 GB" />
        </CardContent>
      </Card>
    </div>
  );
}
```

### 5.2 Configuration Management
**File: `src/app/dashboard/config/page.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";

export default function ConfigPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Configuration</h1>
        <Badge variant="outline">
          <Zap className="mr-1 h-3 w-3" />
          Hot-reload: ON
        </Badge>
      </div>

      <div className="space-y-4">
        <ConfigSection 
          title="Application (8)" 
          configs={appConfigs}
          defaultOpen 
        />
        <ConfigSection 
          title="Content Processing (6)" 
          configs={contentConfigs} 
        />
        <ConfigSection 
          title="AI Providers (25+)" 
          configs={providerConfigs} 
        />
        <ConfigSection 
          title="Redis Cache (12)" 
          configs={redisConfigs} 
        />
      </div>
    </div>
  );
}
```

---

## Phase 6: API Integration (Day 15-17)

### 6.1 API Client Setup
**File: `src/lib/utils/api-client.ts`**
```typescript
class DocaicheAPI {
  private baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4080/api/v1';

  async getProviders() {
    return this.fetch('/providers');
  }

  async testProvider(providerId: string, config: any) {
    return this.fetch(`/providers/${providerId}/test`, {
      method: 'POST',
      body: JSON.stringify(config)
    });
  }

  async getAnalytics(timeRange: string = '24h') {
    return this.fetch(`/analytics?timeRange=${timeRange}`);
  }

  async getDashboardData() {
    return this.fetch('/admin/dashboard');
  }

  async getDocuments(filters?: any) {
    const params = new URLSearchParams(filters);
    return this.fetch(`/admin/search?${params}`);
  }

  async getHealth() {
    return this.fetch('/health');
  }

  async getConfiguration(category?: string) {
    const params = category ? `?category=${category}` : '';
    return this.fetch(`/config${params}`);
  }

  private async fetch(endpoint: string, options?: RequestInit) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }
}

export const api = new DocaicheAPI();
```

### 6.2 React Query Setup
**File: `src/hooks/use-api.ts`**
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/utils/api-client';

export function useProviders() {
  return useQuery({
    queryKey: ['providers'],
    queryFn: api.getProviders,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useAnalytics(timeRange: string) {
  return useQuery({
    queryKey: ['analytics', timeRange],
    queryFn: () => api.getAnalytics(timeRange),
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

export function useTestProvider() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ providerId, config }: { providerId: string; config: any }) =>
      api.testProvider(providerId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });
}
```

---

## Phase 7: Real-time Features (Day 18-19)

### 7.1 Activity Feed with Auto-refresh
**File: `src/components/analytics/activity-feed.tsx`**
```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useQuery } from '@tanstack/react-query';

export function ActivityFeed() {
  const { data: activities } = useQuery({
    queryKey: ['activities'],
    queryFn: () => api.getRecentActivity(),
    refetchInterval: 5000, // 5 seconds
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {activities?.map((activity) => (
            <div key={activity.id} className="flex items-center space-x-3">
              <ActivityIcon type={activity.type} />
              <div className="flex-1">
                <p className="text-sm">{activity.message}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(activity.timestamp))} ago
                </p>
              </div>
              <Badge variant="outline">{activity.type}</Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Implementation Notes

### Leveraging Existing Components
- **Cards**: Use for all container elements (provider cards, metric cards, config sections)
- **Tables**: Use existing data-table for document management
- **Forms**: Use shadcn form components for all configuration inputs
- **Navigation**: Modify existing sidebar rather than rebuilding
- **Charts**: Integrate Recharts with existing theme system

### File Structure Changes
```
src/
├── app/dashboard/
│   ├── page.tsx (overview)
│   ├── providers/page.tsx (new)
│   ├── analytics/page.tsx (transform existing)
│   ├── documents/page.tsx (new)
│   ├── health/page.tsx (transform existing)
│   └── config/page.tsx (new)
├── components/
│   ├── providers/ (new)
│   ├── analytics/ (enhance existing)
│   ├── documents/ (new)
│   └── health/ (new)
└── lib/
    └── utils/api-client.ts (new)
```

### Theme Integration
All components use existing CSS variables:
- `hsl(var(--primary))` for main actions
- `hsl(var(--muted))` for secondary content
- Existing spacing scale (space-y-4, gap-6, etc.)
- Current typography scale

This roadmap transforms the existing template into a focused AI document cache admin interface while maximizing reuse of the excellent shadcn/ui foundation.