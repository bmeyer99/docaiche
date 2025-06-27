# Configuration Web UI Design Specifications - PRD-012

## Executive Summary

This document provides comprehensive UI/UX design specifications for the Configuration Web UI, transforming placeholder HTML stubs into a professional admin dashboard for the AI Documentation Cache System.

## 1. Design System Foundation

### 1.1 Color Palette
```css
/* Primary Colors */
--primary-50: #eff6ff
--primary-100: #dbeafe  
--primary-500: #3b82f6
--primary-600: #2563eb
--primary-700: #1d4ed8
--primary-900: #1e3a8a

/* Status Colors */
--success-50: #f0fdf4
--success-500: #22c55e
--success-600: #16a34a

--warning-50: #fffbeb
--warning-500: #f59e0b
--warning-600: #d97706

--error-50: #fef2f2
--error-500: #ef4444
--error-600: #dc2626

/* Neutral Colors */
--gray-50: #f9fafb
--gray-100: #f3f4f6
--gray-200: #e5e7eb
--gray-300: #d1d5db
--gray-400: #9ca3af
--gray-500: #6b7280
--gray-600: #4b5563
--gray-700: #374151
--gray-800: #1f2937
--gray-900: #111827
```

### 1.2 Typography Scale
```css
/* Font Families */
--font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif
--font-mono: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace

/* Font Sizes */
--text-xs: 0.75rem     /* 12px */
--text-sm: 0.875rem    /* 14px */
--text-base: 1rem      /* 16px */
--text-lg: 1.125rem    /* 18px */
--text-xl: 1.25rem     /* 20px */
--text-2xl: 1.5rem     /* 24px */
--text-3xl: 1.875rem   /* 30px */
--text-4xl: 2.25rem    /* 36px */

/* Line Heights */
--leading-tight: 1.25
--leading-normal: 1.5
--leading-relaxed: 1.625
```

### 1.3 Spacing System (8px Grid)
```css
--spacing-1: 0.25rem   /* 4px */
--spacing-2: 0.5rem    /* 8px */
--spacing-3: 0.75rem   /* 12px */
--spacing-4: 1rem      /* 16px */
--spacing-5: 1.25rem   /* 20px */
--spacing-6: 1.5rem    /* 24px */
--spacing-8: 2rem      /* 32px */
--spacing-10: 2.5rem   /* 40px */
--spacing-12: 3rem     /* 48px */
--spacing-16: 4rem     /* 64px */
```

### 1.4 Responsive Breakpoints
```css
/* Mobile-first breakpoints */
--breakpoint-sm: 640px   /* Small devices */
--breakpoint-md: 768px   /* Medium devices (tablets) */
--breakpoint-lg: 1024px  /* Large devices */
--breakpoint-xl: 1200px  /* Extra large devices */
```

## 2. Layout Architecture

### 2.1 Overall Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Header Bar (64px height)                                    │
├─────────────────────────────────────────────────────────────┤
│ Side Nav │ Main Content Area                               │
│ (240px)  │ ┌─────────────────────────────────────────────┐ │
│          │ │ Page Header (80px)                          │ │
│          │ ├─────────────────────────────────────────────┤ │
│          │ │ Page Content                                │ │
│          │ │ (Responsive Grid System)                    │ │
│          │ │                                             │ │
│          │ │                                             │ │
│          │ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Navigation Structure
```
Dashboard (/)
├── System Overview
├── Health Status
└── Key Metrics

Configuration (/config)
├── Application Settings
├── Service Configuration
├── Cache Management
└── AI/LLM Settings

Content Management (/content)
├── Collections Browser
├── Content Search
├── Content Quality
└── Content Actions
```

## 3. Component Specifications

### 3.1 Status Indicator Component
```html
<!-- Visual Specification -->
<div class="status-indicator">
  <div class="status-dot status-{healthy|degraded|unhealthy}"></div>
  <span class="status-label">Component Name</span>
  <span class="status-detail">Status Message</span>
</div>
```

**CSS Classes:**
```css
.status-indicator {
  @apply flex items-center space-x-3 p-3 rounded-lg border;
}

.status-dot {
  @apply w-3 h-3 rounded-full flex-shrink-0;
}

.status-healthy { @apply bg-green-500; }
.status-degraded { @apply bg-yellow-500; }
.status-unhealthy { @apply bg-red-500; }

.status-label {
  @apply font-medium text-gray-900;
}

.status-detail {
  @apply text-sm text-gray-500;
}
```

### 3.2 Metric Card Component
```html
<!-- Visual Specification -->
<div class="metric-card">
  <div class="metric-header">
    <h3 class="metric-title">Metric Name</h3>
    <div class="metric-trend {up|down|neutral}">↑ 12%</div>
  </div>
  <div class="metric-value">1,234</div>
  <div class="metric-description">Description text</div>
</div>
```

**CSS Classes:**
```css
.metric-card {
  @apply bg-white rounded-lg shadow-sm border border-gray-200 p-6;
}

.metric-header {
  @apply flex justify-between items-start mb-2;
}

.metric-title {
  @apply text-sm font-medium text-gray-500;
}

.metric-trend {
  @apply text-xs font-medium px-2 py-1 rounded-full;
}

.metric-trend.up {
  @apply bg-green-100 text-green-700;
}

.metric-trend.down {
  @apply bg-red-100 text-red-700;
}

.metric-trend.neutral {
  @apply bg-gray-100 text-gray-700;
}

.metric-value {
  @apply text-3xl font-bold text-gray-900 mb-1;
}

.metric-description {
  @apply text-sm text-gray-500;
}
```

### 3.3 Data Table Component
```html
<!-- Visual Specification -->
<div class="data-table-container">
  <div class="table-header">
    <h3 class="table-title">Table Title</h3>
    <div class="table-actions">
      <input type="search" class="table-search" placeholder="Search...">
      <button class="btn-secondary">Filter</button>
    </div>
  </div>
  <table class="data-table">
    <thead>
      <tr>
        <th class="sortable">Column 1 <span class="sort-icon">↕</span></th>
        <th>Column 2</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Data</td>
        <td>Data</td>
        <td>
          <button class="btn-sm btn-outline">Edit</button>
          <button class="btn-sm btn-danger">Delete</button>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

### 3.4 Form Components
```html
<!-- Input Field -->
<div class="form-field">
  <label class="form-label">Field Label</label>
  <input type="text" class="form-input" placeholder="Enter value">
  <div class="form-help">Helper text</div>
  <div class="form-error">Error message</div>
</div>

<!-- Select Field -->
<div class="form-field">
  <label class="form-label">Select Label</label>
  <select class="form-select">
    <option>Option 1</option>
    <option>Option 2</option>
  </select>
</div>

<!-- Button Variants -->
<button class="btn btn-primary">Primary Action</button>
<button class="btn btn-secondary">Secondary Action</button>
<button class="btn btn-danger">Danger Action</button>
<button class="btn btn-outline">Outline Button</button>
```

## 4. Page-Specific Designs

### 4.1 Dashboard Page (/) Design

#### 4.1.1 Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Page Header: "System Dashboard"                             │
├─────────────────────────────────────────────────────────────┤
│ System Status Grid (4 columns)                             │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│ │Database │ │ Redis   │ │AnythingL│ │ Search  │           │
│ │Healthy  │ │Healthy  │ │  LM     │ │Orchestra│           │
│ │         │ │         │ │Degraded │ │ tor     │           │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Key Metrics Grid (3 columns)                               │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │Total        │ │Cache Hit    │ │Avg Response │           │
│ │Searches     │ │Rate         │ │Time         │           │
│ │1,247        │ │73%          │ │125ms        │           │
│ │↑ 12%        │ │↑ 5%         │ │↓ 8%         │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Recent Activity Table                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Time     │ Query           │ Status │ Response Time    │ │
│ │ 14:32:15 │ FastAPI routing │ ✓      │ 89ms            │ │
│ │ 14:31:45 │ React hooks     │ ✓      │ 156ms           │ │
│ │ 14:30:12 │ Python async    │ ✗      │ timeout         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 4.1.2 Real-time Updates
- **Auto-refresh interval**: 30 seconds for metrics, 10 seconds for activity
- **WebSocket integration**: Real-time status updates
- **Loading states**: Skeleton screens during data fetch
- **Error handling**: Graceful fallback with retry buttons

### 4.2 Configuration Page (/config) Design

#### 4.2.1 Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Page Header: "System Configuration"                [Save] [Reset] │
├─────────────────────────────────────────────────────────────┤
│ Configuration Sections (Accordion Layout)                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ▼ Application Settings                                  │ │
│ │   ┌─────────────────┐ ┌─────────────────┐              │ │
│ │   │Environment      │ │Debug Mode       │              │ │
│ │   │[Production  ▼]  │ │[✓] Enabled      │              │ │
│ │   └─────────────────┘ └─────────────────┘              │ │
│ │   ┌─────────────────┐ ┌─────────────────┐              │ │
│ │   │Log Level        │ │Workers          │              │ │
│ │   │[INFO        ▼]  │ │[4            ]  │              │ │
│ │   └─────────────────┘ └─────────────────┘              │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ► Service Configuration                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ► Cache Management                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2.2 Form Validation
- **Real-time validation**: Immediate feedback on field changes
- **Server-side validation**: Backend validation with error display
- **Save confirmation**: Visual feedback for successful updates
- **Dirty state tracking**: Warn on unsaved changes

### 4.3 Content Management Page (/content) Design

#### 4.3.1 Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Page Header: "Content Management"                           │
├─────────────────────────────────────────────────────────────┤
│ Collections Overview                                        │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │Python Docs  │ │React Docs   │ │FastAPI Docs │           │
│ │1,234 docs   │ │567 docs     │ │234 docs     │           │
│ │Active       │ │Active       │ │Active       │           │
│ │[View]       │ │[View]       │ │[View]       │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Content Search & Management                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Search content...           ] [Technology ▼] [Filter] │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Title                │ Type │ Tech │ Status │ Actions   │ │
│ │ FastAPI Tutorial     │ Doc  │ Py   │ Active │[Edit][🗑]│ │
│ │ React Hooks Guide    │ Doc  │ Js   │ Active │[Edit][🗑]│ │
│ │ Python Async Guide   │ Doc  │ Py   │ Error  │[Edit][🗑]│ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 5. Responsive Design Specifications

### 5.1 Desktop (1200px+)
- **Navigation**: Fixed sidebar (240px width)
- **Content**: Full grid layouts with 4-column metric cards
- **Tables**: Full-width with all columns visible
- **Forms**: Multi-column layout where appropriate

### 5.2 Tablet (768px-1199px)
- **Navigation**: Collapsible sidebar with hamburger menu
- **Content**: 2-column metric card grid
- **Tables**: Horizontal scroll for overflow
- **Forms**: Single column with grouped sections

### 5.3 Mobile (320px-767px)
- **Navigation**: Full-screen overlay menu
- **Content**: Single column layout
- **Tables**: Card-based responsive layout
- **Forms**: Stacked single column with touch-friendly controls

## 6. JavaScript Interaction Patterns

### 6.1 Auto-refresh Implementation
```javascript
// Dashboard auto-refresh
class DashboardRefresh {
  constructor() {
    this.metricsInterval = 30000; // 30 seconds
    this.activityInterval = 10000; // 10 seconds
  }
  
  startRefresh() {
    setInterval(() => this.updateMetrics(), this.metricsInterval);
    setInterval(() => this.updateActivity(), this.activityInterval);
  }
}
```

### 6.2 Form Validation
```javascript
// Configuration form validation
class ConfigForm {
  validateField(field, value) {
    // Real-time validation logic
  }
  
  showError(field, message) {
    // Display error message
  }
  
  markDirty() {
    // Track unsaved changes
  }
}
```

### 6.3 Search and Filtering
```javascript
// Content search functionality
class ContentSearch {
  debounceSearch(query) {
    // Debounced search with 300ms delay
  }
  
  applyFilters(filters) {
    // Apply technology/type filters
  }
}
```

## 7. Accessibility Requirements

### 7.1 WCAG 2.1 AA Compliance
- **Color contrast**: Minimum 4.5:1 ratio for normal text
- **Focus indicators**: Visible focus rings on interactive elements
- **Keyboard navigation**: Full keyboard accessibility
- **Screen reader support**: Proper ARIA labels and semantic HTML

### 7.2 Interactive Elements
- **Touch targets**: Minimum 44px touch target size
- **Error messaging**: Clear, descriptive error messages
- **Loading states**: Proper loading indicators with ARIA live regions

## 8. Performance Requirements

### 8.1 Loading Performance
- **Initial page load**: < 2 seconds
- **Data refresh**: < 500ms
- **Form submissions**: < 1 second with loading feedback

### 8.2 Asset Optimization
- **CSS**: Single optimized Tailwind build
- **JavaScript**: Minimal, optimized scripts
- **Images**: SVG icons, optimized images with proper sizing

## 9. Development Handoff Notes

### 9.1 Tailwind CSS Configuration
```javascript
// tailwind.config.js
module.exports = {
  content: ['./templates/**/*.html', './static/**/*.js'],
  theme: {
    extend: {
      colors: {
        // Custom color palette from section 1.1
      },
      spacing: {
        // Custom spacing from section 1.3
      }
    }
  }
}
```

### 9.2 Template Structure
- **Base template**: `base.html` with common layout and navigation
- **Page templates**: Individual templates for each route
- **Component templates**: Reusable template blocks for common UI elements

### 9.3 Static Asset Organization
```
static/
├── css/
│   └── dashboard.css (compiled Tailwind)
├── js/
│   ├── dashboard.js
│   ├── config.js
│   └── content.js
└── icons/
    └── feather-icons.svg (icon sprite)
```

## 10. Implementation Priority

### Phase 1: Core Layout and Navigation
1. Base template with header and sidebar
2. Navigation structure and routing
3. Basic responsive breakpoints

### Phase 2: Dashboard Implementation  
1. System status indicators
2. Metrics cards with real-time updates
3. Recent activity table

### Phase 3: Configuration Interface
1. Configuration sections with accordion layout
2. Form validation and submission
3. Save/reset functionality

### Phase 4: Content Management
1. Collections overview
2. Content search and filtering
3. Content management actions

This specification provides complete design guidance for transforming the placeholder Web UI into a production-ready admin dashboard. All visual elements, interactions, and responsive behaviors are clearly defined for immediate implementation.