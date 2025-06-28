# Docaiche Admin UI - Component Library Specification

## Core Design Principles

1. **Progressive Disclosure**: Show essential information first, details on demand
2. **Visual Hierarchy**: Size, color, and spacing guide the eye
3. **Consistent Feedback**: Every action has a clear response
4. **Delightful Details**: Smooth animations and thoughtful micro-interactions

---

## Component Specifications

### 1. Provider Card Component

```typescript
interface ProviderCardProps {
  provider: {
    id: string;
    name: string;
    status: 'connected' | 'configured' | 'error' | 'disabled' | 'not_configured';
    category: 'cloud' | 'local' | 'gateway';
    modelCount?: number;
    capabilities: string[];
    lastTested?: Date;
  };
  onClick: () => void;
  onQuickTest?: () => void;
}
```

**Visual States:**
```scss
.provider-card {
  // Base state
  background: white;
  border: 2px solid transparent;
  transition: all 200ms ease-out;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }
  
  &.status-connected { border-color: #10B981; }
  &.status-error { border-color: #EF4444; }
  &.status-configured { border-color: #F59E0B; }
}
```

**Status Indicator Animation:**
```scss
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.status-indicator {
  &.connected {
    animation: pulse 2s infinite;
  }
}
```

### 2. Configuration Dual-Track Component

```typescript
interface DualTrackConfigProps {
  textConfig: ProviderConfig;
  embeddingConfig?: ProviderConfig;
  onCopyConfig: () => void;
  onTestText: () => void;
  onTestEmbedding: () => void;
}
```

**Layout Grid:**
```scss
.dual-track-config {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.config-section {
  padding: 24px;
  border-radius: 8px;
  background: #F9FAFB;
  
  &.active {
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
}
```

### 3. Quality Score Visualizer

```typescript
interface QualityScoreProps {
  score: number; // 0-1
  breakdown?: {
    structure: number;
    authority: number;
    completeness: number;
    relevance: number;
    freshness: number;
  };
  size?: 'small' | 'medium' | 'large';
}
```

**Visual Representation:**
```scss
.quality-bar {
  height: 8px;
  background: #E5E7EB;
  border-radius: 4px;
  overflow: hidden;
  
  .quality-fill {
    height: 100%;
    transition: width 500ms ease-out;
    
    &.high { background: linear-gradient(90deg, #10B981, #059669); }
    &.medium { background: linear-gradient(90deg, #F59E0B, #D97706); }
    &.low { background: linear-gradient(90deg, #EF4444, #DC2626); }
  }
}
```

### 4. Analytics Chart Components

#### Sparkline Chart
```typescript
interface SparklineProps {
  data: number[];
  color?: string;
  showArea?: boolean;
  height?: number;
  animate?: boolean;
}
```

#### Technology Donut Chart
```typescript
interface TechDonutProps {
  data: { technology: string; count: number; color: string }[];
  centerLabel?: string;
  interactive?: boolean;
}
```

**Chart Animations:**
```scss
.chart-container {
  opacity: 0;
  animation: fadeInUp 600ms ease-out forwards;
  
  &.in-viewport {
    animation-play-state: running;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### 5. Document Status Pipeline

```typescript
interface PipelineProps {
  stages: {
    name: string;
    status: 'completed' | 'active' | 'pending' | 'failed';
    progress?: number;
  }[];
}
```

**Pipeline Visualization:**
```scss
.pipeline {
  display: flex;
  align-items: center;
  
  .stage {
    flex: 1;
    position: relative;
    
    &::after {
      content: '';
      position: absolute;
      top: 50%;
      right: -50%;
      width: 100%;
      height: 2px;
      background: #E5E7EB;
      transform: translateY(-50%);
    }
    
    &.completed::after {
      background: #10B981;
      animation: fillProgress 300ms ease-out;
    }
  }
}
```

### 6. Real-time Activity Feed

```typescript
interface ActivityFeedProps {
  activities: {
    id: string;
    type: 'search' | 'upload' | 'config' | 'error';
    message: string;
    timestamp: Date;
    details?: any;
  }[];
  onFilter: (type: string) => void;
}
```

**Activity Item Animation:**
```scss
.activity-item {
  animation: slideInRight 300ms ease-out;
  
  &.exit {
    animation: fadeOut 200ms ease-out forwards;
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
}
```

### 7. Configuration Field Components

#### Slider with Value
```typescript
interface SliderFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (value: number) => void;
}
```

**Slider Styling:**
```scss
.slider-field {
  .slider-track {
    height: 6px;
    background: #E5E7EB;
    border-radius: 3px;
    
    .slider-fill {
      background: #3B82F6;
      transition: width 150ms ease-out;
    }
  }
  
  .slider-thumb {
    width: 20px;
    height: 20px;
    background: white;
    border: 2px solid #3B82F6;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    
    &:active {
      box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.1);
    }
  }
}
```

### 8. Search and Filter Components

```typescript
interface AdvancedSearchProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  technologies: string[];
  savedFilters?: SavedFilter[];
}

interface SearchFilters {
  technology?: string[];
  qualityRange?: [number, number];
  status?: string[];
  dateRange?: [Date, Date];
}
```

**Search Input Enhancement:**
```scss
.search-input {
  position: relative;
  
  input {
    padding-left: 40px;
    transition: box-shadow 200ms ease-out;
    
    &:focus {
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
  }
  
  .search-icon {
    position: absolute;
    left: 12px;
    transition: color 200ms ease-out;
  }
  
  &.has-value .clear-button {
    opacity: 1;
    pointer-events: auto;
  }
}
```

### 9. Toast Notifications

```typescript
interface ToastProps {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}
```

**Toast Animations:**
```scss
.toast {
  animation: slideInUp 300ms ease-out;
  
  &.exit {
    animation: slideOutRight 200ms ease-out forwards;
  }
}

.toast-progress {
  height: 3px;
  background: currentColor;
  opacity: 0.2;
  
  .progress-bar {
    height: 100%;
    background: currentColor;
    animation: shrink var(--duration) linear;
  }
}

@keyframes shrink {
  from { width: 100%; }
  to { width: 0%; }
}
```

### 10. Loading States

#### Skeleton Loader
```typescript
interface SkeletonProps {
  variant: 'text' | 'circular' | 'rectangular' | 'card';
  width?: string | number;
  height?: string | number;
  animate?: boolean;
}
```

**Skeleton Animation:**
```scss
.skeleton {
  background: linear-gradient(
    90deg,
    #F3F4F6 25%,
    #E5E7EB 50%,
    #F3F4F6 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

### 11. Empty States

```typescript
interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}
```

**Empty State Styling:**
```scss
.empty-state {
  text-align: center;
  padding: 48px 24px;
  
  .icon {
    font-size: 48px;
    color: #9CA3AF;
    margin-bottom: 16px;
  }
  
  .title {
    font-size: 18px;
    font-weight: 600;
    color: #111827;
    margin-bottom: 8px;
  }
  
  .description {
    color: #6B7280;
    margin-bottom: 24px;
  }
}
```

### 12. Data Table with Actions

```typescript
interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  selectable?: boolean;
  actions?: Action<T>[];
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  loading?: boolean;
}
```

**Table Interactions:**
```scss
.data-table {
  tbody tr {
    transition: background-color 150ms ease-out;
    
    &:hover {
      background-color: #F9FAFB;
    }
    
    &.selected {
      background-color: #EFF6FF;
    }
  }
  
  .sortable-header {
    cursor: pointer;
    user-select: none;
    
    &:hover {
      color: #3B82F6;
    }
  }
}
```

---

## Animation Timing Guidelines

- **Micro-interactions**: 150-200ms
- **Page transitions**: 300-400ms
- **Loading states**: 500-600ms
- **Complex animations**: 800-1000ms

## Accessibility Patterns

### Focus Management
```scss
// Custom focus style
:focus-visible {
  outline: 2px solid #3B82F6;
  outline-offset: 2px;
}

// Skip navigation link
.skip-nav {
  position: absolute;
  top: -40px;
  left: 0;
  
  &:focus {
    top: 0;
  }
}
```

### ARIA Live Regions
```typescript
// For real-time updates
<div aria-live="polite" aria-atomic="true">
  {activityCount} new activities
</div>

// For critical alerts
<div role="alert" aria-live="assertive">
  Configuration saved successfully
</div>
```

---

## Responsive Utilities

```scss
// Breakpoint mixins
@mixin tablet-up {
  @media (min-width: 768px) { @content; }
}

@mixin desktop-up {
  @media (min-width: 1280px) { @content; }
}

// Container sizing
.container {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 16px;
  
  @include tablet-up {
    padding: 0 24px;
  }
  
  @include desktop-up {
    padding: 0 32px;
  }
}
```

---

## Theme Variables

```scss
:root {
  // Colors
  --color-primary: #3B82F6;
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  
  // Spacing
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  
  // Shadows
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  
  // Transitions
  --transition-fast: 150ms ease-out;
  --transition-base: 200ms ease-out;
  --transition-slow: 300ms ease-out;
}
```

This component library provides all the building blocks needed to implement the comprehensive admin UI design with consistency and polish.