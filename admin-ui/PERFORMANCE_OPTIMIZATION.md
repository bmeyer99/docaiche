# Performance Optimization Guide
## Docaiche Admin UI

### Current Performance Issues

#### 1. API Client Instantiation (Critical)
**Problem**: Creating new `DocaicheApiClient` instances on every render
**Impact**: Unnecessary re-renders, memory leaks, multiple API connections

**Solution**:
```typescript
// src/lib/hooks/use-api-client.ts
import { useContext, createContext } from 'react';
import { DocaicheApiClient } from '@/lib/utils/api-client';

const ApiClientContext = createContext<DocaicheApiClient | null>(null);

export function useApiClient() {
  const client = useContext(ApiClientContext);
  if (!client) {
    throw new Error('useApiClient must be used within ApiClientProvider');
  }
  return client;
}

// In app/layout.tsx - wrap the app
<ApiClientProvider>
  {children}
</ApiClientProvider>
```

#### 2. Large Component Files
**Problem**: Analytics pages are 900+ lines
**Impact**: Slow parsing, difficult maintenance

**Solution**: Split into smaller components
```typescript
// Before: One large file
// analytics-page.tsx (900 lines)

// After: Multiple focused files
// analytics-page.tsx (main container, 100 lines)
// components/analytics-charts.tsx
// components/analytics-filters.tsx
// components/analytics-summary.tsx
// hooks/use-analytics-data.ts
```

#### 3. Missing React.memo
**Problem**: Heavy components re-render unnecessarily
**Impact**: Poor performance with data updates

**Solution**:
```typescript
// Wrap expensive components
export const AnalyticsChart = React.memo(({ data, options }) => {
  return <ResponsiveContainer>...</ResponsiveContainer>;
});

// With custom comparison
export const DataTable = React.memo(
  ({ data, columns }) => { ... },
  (prevProps, nextProps) => {
    return prevProps.data.length === nextProps.data.length;
  }
);
```

#### 4. Bundle Size Optimization
**Current Issues**:
- Analytics page: 386 kB
- Multiple Radix UI imports
- Large dependencies

**Solutions**:

1. **Dynamic Imports for Heavy Components**
```typescript
const AnalyticsChart = dynamic(
  () => import('@/components/analytics-chart'),
  { 
    loading: () => <Skeleton className="h-[400px]" />,
    ssr: false 
  }
);
```

2. **Tree Shaking Radix UI**
```typescript
// Bad - imports entire library
import * as Dialog from '@radix-ui/react-dialog';

// Good - imports only what's needed
import { Root, Trigger, Content } from '@radix-ui/react-dialog';
```

3. **Optimize Images**
```typescript
import Image from 'next/image';

// Use Next.js Image component for automatic optimization
<Image
  src="/logo.png"
  alt="Logo"
  width={100}
  height={100}
  priority // for above-the-fold images
/>
```

#### 5. Data Fetching Optimization

**Current**: Multiple API calls on component mount
**Solution**: Parallel data fetching with proper caching

```typescript
// Bad - Sequential
useEffect(() => {
  const data1 = await api.getData1();
  const data2 = await api.getData2();
  const data3 = await api.getData3();
}, []);

// Good - Parallel
useEffect(() => {
  Promise.all([
    api.getData1(),
    api.getData2(),
    api.getData3()
  ]).then(([data1, data2, data3]) => {
    // Handle all data
  });
}, []);

// Better - With React Query or SWR
const { data: stats } = useSWR('/api/stats', fetcher, {
  refreshInterval: 30000, // 30 seconds
  revalidateOnFocus: false,
});
```

### Performance Monitoring

#### 1. Add Performance Metrics
```typescript
// utils/performance.ts
export function measureComponentPerformance(componentName: string) {
  if (typeof window !== 'undefined' && window.performance) {
    performance.mark(`${componentName}-start`);
    
    return () => {
      performance.mark(`${componentName}-end`);
      performance.measure(
        componentName,
        `${componentName}-start`,
        `${componentName}-end`
      );
      
      const measure = performance.getEntriesByName(componentName)[0];
      console.log(`${componentName} render time:`, measure.duration);
    };
  }
  return () => {};
}
```

#### 2. Use React DevTools Profiler
- Install React DevTools extension
- Use Profiler tab to identify slow components
- Look for unnecessary re-renders

### Optimization Checklist

- [ ] Implement API client singleton pattern
- [ ] Split large components (>400 lines)
- [ ] Add React.memo to data-heavy components
- [ ] Implement dynamic imports for charts
- [ ] Optimize Radix UI imports
- [ ] Add loading states for all async operations
- [ ] Implement proper error boundaries
- [ ] Use Next.js Image component
- [ ] Enable React Strict Mode for development
- [ ] Add performance monitoring
- [ ] Implement data caching strategy
- [ ] Optimize re-renders with useCallback/useMemo
- [ ] Lazy load below-the-fold content
- [ ] Implement virtual scrolling for long lists
- [ ] Minimize main thread work

### Quick Wins
1. **Remove unused dependencies**: `npm prune`
2. **Analyze bundle**: `npm run build && npm run analyze`
3. **Enable compression**: Already handled by Next.js
4. **Preload critical resources**: Add to `_document.tsx`
5. **Optimize fonts**: Use `next/font` for automatic optimization

### Measuring Success
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.5s
- Cumulative Layout Shift: < 0.1
- Bundle size reduction: Target 20-30%
- API calls reduction: 50% through caching