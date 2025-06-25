# Configuration Web UI Wireframes - PRD-012

## Visual Wireframes and Layout Specifications

### 1. Dashboard Page (/) - Desktop Layout

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER BAR (64px height, bg-gray-50, border-b border-gray-200)                                                                                             │
│ ┌─ DocAI Cache System (text-xl font-bold text-gray-900) ──────────────────────────────────────────────────────────────────────────────────── [Profile] │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR (240px width, bg-white, border-r border-gray-200) │ MAIN CONTENT AREA (flex-1, bg-gray-50)                                                      │
│                                                            │                                                                                              │
│ ┌─ Navigation Menu ──────────────────────────────────────┐ │ ┌─ Page Header (80px height, bg-white, p-6) ────────────────────────────────────────────┐ │
│ │ • Dashboard (active, bg-blue-50, text-blue-700)       │ │ │ System Dashboard (text-3xl font-bold text-gray-900)                                   │ │
│ │ • Configuration                                        │ │ │ Real-time system monitoring and performance metrics (text-gray-500)                   │ │
│ │ • Content Management                                   │ │ └────────────────────────────────────────────────────────────────────────────────────┘ │
│ └────────────────────────────────────────────────────────┘ │                                                                                              │
│                                                            │ ┌─ System Status Grid (grid-cols-4, gap-4, p-6) ────────────────────────────────────────┐ │
│                                                            │ │ ┌─ Status Card 1 ──────────────┐ ┌─ Status Card 2 ──────────────┐                   │ │
│                                                            │ │ │ Database                     │ │ Redis Cache                  │                   │ │
│                                                            │ │ │ ● Healthy (green)           │ │ ● Healthy (green)           │                   │ │
│                                                            │ │ │ Connected                    │ │ Connected                    │                   │ │
│                                                            │ │ │ 15ms response                │ │ 2ms response                 │                   │ │
│                                                            │ │ └──────────────────────────────┘ └──────────────────────────────┘                   │ │
│                                                            │ │ ┌─ Status Card 3 ──────────────┐ ┌─ Status Card 4 ──────────────┐                   │ │
│                                                            │ │ │ AnythingLLM                  │ │ Search Orchestrator          │                   │ │
│                                                            │ │ │ ● Degraded (yellow)         │ │ ● Healthy (green)           │                   │ │
│                                                            │ │ │ Slow response                │ │ Ready                        │                   │ │
│                                                            │ │ │ 2.3s response                │ │ 45ms response                │                   │ │
│                                                            │ │ └──────────────────────────────┘ └──────────────────────────────┘                   │ │
│                                                            │ └──────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                            │                                                                                              │
│                                                            │ ┌─ Key Metrics Grid (grid-cols-3, gap-6, p-6) ──────────────────────────────────────────┐ │
│                                                            │ │ ┌─ Metric Card 1 ──────────────────────────┐ ┌─ Metric Card 2 ─────────────────────┐ │ │
│                                                            │ │ │ Total Searches                           │ │ Cache Hit Rate                      │ │ │
│                                                            │ │ │ 1,247 (text-3xl font-bold)              │ │ 73% (text-3xl font-bold)            │ │ │
│                                                            │ │ │ ↑ 12% (bg-green-100 text-green-700)     │ │ ↑ 5% (bg-green-100 text-green-700)  │ │ │
│                                                            │ │ │ vs last hour                             │ │ last 24 hours                       │ │ │
│                                                            │ │ └──────────────────────────────────────────┘ └─────────────────────────────────────┘ │ │
│                                                            │ │ ┌─ Metric Card 3 ──────────────────────────┐                                          │ │
│                                                            │ │ │ Avg Response Time                        │                                          │ │
│                                                            │ │ │ 125ms (text-3xl font-bold)               │                                          │ │
│                                                            │ │ │ ↓ 8% (bg-green-100 text-green-700)      │                                          │ │
│                                                            │ │ │ performance improved                     │                                          │ │
│                                                            │ │ └──────────────────────────────────────────┘                                          │ │
│                                                            │ └──────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                            │                                                                                              │
│                                                            │ ┌─ Recent Activity Table (bg-white, rounded-lg, shadow-sm) ─────────────────────────────┐ │
│                                                            │ │ Recent Queries (text-lg font-semibold, p-4)                    [Auto-refresh: ON]     │ │
│                                                            │ │ ┌─────────────────────────────────────────────────────────────────────────────────────┐ │ │
│                                                            │ │ │ Time     │ Query            │ Collection  │ Status │ Response Time │ Actions      │ │ │
│                                                            │ │ │ 14:32:15 │ FastAPI routing  │ python-docs │ ✓      │ 89ms          │ [View]       │ │ │
│                                                            │ │ │ 14:31:45 │ React hooks      │ react-docs  │ ✓      │ 156ms         │ [View]       │ │ │
│                                                            │ │ │ 14:30:12 │ Python async     │ python-docs │ ✗      │ timeout       │ [Retry]      │ │ │
│                                                            │ │ │ 14:29:33 │ Vue components   │ vue-docs    │ ✓      │ 203ms         │ [View]       │ │ │
│                                                            │ │ │ 14:28:21 │ API documentation│ fastapi-docs│ ✓      │ 134ms         │ [View]       │ │ │
│                                                            │ │ └─────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                                                            │ └──────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2. Configuration Page (/config) - Desktop Layout

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER BAR (same as dashboard)                                                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR (same navigation) │ MAIN CONTENT AREA                                                                                                                │
│                           │                                                                                                                                  │
│ ┌─ Navigation Menu ──────┐ │ ┌─ Page Header (flex justify-between items-center) ────────────────────────────────────────────────────────────────────────┐ │
│ │ • Dashboard           │ │ │ System Configuration (text-3xl font-bold)                                    [Reset] [Save Changes] (buttons)           │ │
│ │ • Configuration       │ │ │ Manage system settings and service configuration (text-gray-500)                                                      │ │
│ │   (active)            │ │ └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ │ • Content Management  │ │                                                                                                                                  │
│ └───────────────────────┘ │ ┌─ Configuration Sections (space-y-4, p-6) ─────────────────────────────────────────────────────────────────────────────┐ │
│                           │ │                                                                                                                            │ │
│                           │ │ ┌─ Application Settings (accordion, border rounded-lg) ─────────────────────────────────────────────────────────────┐ │ │
│                           │ │ │ ▼ Application Settings (text-lg font-semibold, cursor-pointer, p-4 bg-gray-50)                                    │ │ │
│                           │ │ │ ┌─ Settings Grid (grid-cols-2 gap-6, p-4) ──────────────────────────────────────────────────────────────────────┐ │ │ │
│                           │ │ │ │ ┌─ Environment Setting ────────────────┐ ┌─ Debug Mode Setting ────────────────────┐                          │ │ │ │
│                           │ │ │ │ │ Environment (font-medium)            │ │ Debug Mode (font-medium)                │                          │ │ │ │
│                           │ │ │ │ │ [Production          ▼] (select)     │ │ [✓] Enable Debug Mode (checkbox)       │                          │ │ │ │
│                           │ │ │ │ │ Current: production                  │ │ For development only                    │                          │ │ │ │
│                           │ │ │ │ └──────────────────────────────────────┘ └─────────────────────────────────────────┘                          │ │ │ │
│                           │ │ │ │ ┌─ Log Level Setting ──────────────────┐ ┌─ Workers Setting ───────────────────────┐                          │ │ │ │
│                           │ │ │ │ │ Log Level (font-medium)              │ │ Worker Processes (font-medium)          │                          │ │ │ │
│                           │ │ │ │ │ [INFO            ▼] (select)         │ │ [4                    ] (input number)  │                          │ │ │ │
│                           │ │ │ │ │ Controls logging verbosity           │ │ Number of worker processes              │                          │ │ │ │
│                           │ │ │ │ └──────────────────────────────────────┘ └─────────────────────────────────────────┘                          │ │ │ │
│                           │ │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │ │
│                           │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                           │ │                                                                                                                            │ │
│                           │ │ ┌─ Service Configuration (accordion, border rounded-lg) ────────────────────────────────────────────────────────────┐ │ │
│                           │ │ │ ► Service Configuration (text-lg font-semibold, cursor-pointer, p-4 bg-gray-50)                                   │ │ │
│                           │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                           │ │                                                                                                                            │ │
│                           │ │ ┌─ Cache Management (accordion, border rounded-lg) ─────────────────────────────────────────────────────────────────┐ │ │
│                           │ │ │ ► Cache Management (text-lg font-semibold, cursor-pointer, p-4 bg-gray-50)                                        │ │ │
│                           │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                           │ │                                                                                                                            │ │
│                           │ │ ┌─ AI/LLM Settings (accordion, border rounded-lg) ──────────────────────────────────────────────────────────────────┐ │ │
│                           │ │ │ ► AI/LLM Settings (text-lg font-semibold, cursor-pointer, p-4 bg-gray-50)                                         │ │ │
│                           │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                           │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3. Content Management Page (/content) - Desktop Layout

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER BAR (same as dashboard)                                                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR (same navigation) │ MAIN CONTENT AREA                                                                                                                │
│                           │                                                                                                                                  │
│ ┌─ Navigation Menu ──────┐ │ ┌─ Page Header ──────────────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ • Dashboard           │ │ │ Content Management (text-3xl font-bold)                                                                                   │ │
│ │ • Configuration       │ │ │ Manage documentation collections and content quality (text-gray-500)                                                   │ │
│ │ • Content Management  │ │ └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ │   (active)            │ │                                                                                                                                  │
│ └───────────────────────┘ │ ┌─ Collections Overview (grid-cols-3 gap-6, p-6) ───────────────────────────────────────────────────────────────────────┐ │
│                           │ │ ┌─ Collection Card 1 ─────────────────────────┐ ┌─ Collection Card 2 ─────────────────────────┐                        │ │
│                           │ │ │ Python Documentation                        │ │ React Documentation                         │                        │ │
│                           │ │ │ 1,234 documents (text-2xl font-bold)       │ │ 567 documents (text-2xl font-bold)         │                        │ │
│                           │ │ │ ● Active (text-green-600)                   │ │ ● Active (text-green-600)                   │                        │ │
│                           │ │ │ Last updated: 2 hours ago                   │ │ Last updated: 4 hours ago                   │                        │ │
│                           │ │ │ Quality Score: 0.87                         │ │ Quality Score: 0.91                         │                        │ │
│                           │ │ │ [View Collection] [Settings]                │ │ [View Collection] [Settings]                │                        │ │
│                           │ │ └─────────────────────────────────────────────┘ └─────────────────────────────────────────────┘                        │ │
│                           │ │ ┌─ Collection Card 3 ─────────────────────────┐                                                                          │ │
│                           │ │ │ FastAPI Documentation                       │                                                                          │ │
│                           │ │ │ 234 documents (text-2xl font-bold)         │                                                                          │ │
│                           │ │ │ ● Active (text-green-600)                   │                                                                          │ │
│                           │ │ │ Last updated: 1 day ago                     │                                                                          │ │
│                           │ │ │ Quality Score: 0.79                         │                                                                          │ │
│                           │ │ │ [View Collection] [Settings]                │                                                                          │ │
│                           │ │ └─────────────────────────────────────────────┘                                                                          │ │
│                           │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                           │                                                                                                                                  │
│                           │ ┌─ Content Search & Management (bg-white rounded-lg shadow-sm) ─────────────────────────────────────────────────────────┐ │
│                           │ │ Content Library (text-lg font-semibold, p-4)                                                                            │ │
│                           │ │ ┌─ Search Controls (flex gap-4, p-4 border-b) ──────────────────────────────────────────────────────────────────────┐ │ │
│                           │ │ │ [🔍 Search content...                    ] [Technology ▼] [Type ▼] [Status ▼] [Search]                             │ │ │
│                           │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                           │ │ ┌─ Content Table ────────────────────────────────────────────────────────────────────────────────────────────────────┐ │ │
│                           │ │ │ Title                    │ Type │ Tech   │ Collection  │ Status │ Quality │ Size │ Actions                          │ │ │
│                           │ │ │ FastAPI Tutorial Intro   │ Doc  │ Python │ python-docs │ Active │ 0.89    │ 15KB │ [Edit] [Preview] [🗑 Delete]     │ │ │
│                           │ │ │ React Hooks Guide        │ Doc  │ React  │ react-docs  │ Active │ 0.94    │ 23KB │ [Edit] [Preview] [🗑 Delete]     │ │ │
│                           │ │ │ Python Async Programming │ Doc  │ Python │ python-docs │ Error  │ 0.72    │ 31KB │ [Edit] [Preview] [🗑 Delete]     │ │ │
│                           │ │ │ Vue Component Basics     │ Doc  │ Vue    │ vue-docs    │ Active │ 0.86    │ 18KB │ [Edit] [Preview] [🗑 Delete]     │ │ │
│                           │ │ │ API Documentation        │ Doc  │ Python │ fastapi-docs│ Active │ 0.81    │ 27KB │ [Edit] [Preview] [🗑 Delete]     │ │ │
│                           │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                           │ │ ┌─ Pagination (flex justify-between items-center, p-4) ─────────────────────────────────────────────────────────────┐ │ │
│                           │ │ │ Showing 1-5 of 23 results                                                                    [Previous] [1] [2] [Next] │ │ │
│                           │ │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│                           │ └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Mobile Responsive Layouts

### 4.1 Dashboard Page - Mobile (320px-767px)

```
┌─────────────────────────────────────────────────────┐
│ HEADER BAR (64px height)                           │
│ [☰] DocAI Cache System                     [👤]    │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│ MAIN CONTENT (full width, no sidebar)              │
│                                                     │
│ ┌─ Page Header (p-4) ─────────────────────────────┐ │
│ │ System Dashboard (text-2xl font-bold)          │ │
│ │ Real-time monitoring (text-sm text-gray-500)   │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ System Status (grid-cols-1 gap-4, p-4) ───────┐ │
│ │ ┌─ Status Card ─────────────────────────────────┐ │ │
│ │ │ Database                    ● Healthy        │ │ │
│ │ │ Connected - 15ms response                    │ │ │
│ │ └───────────────────────────────────────────────┘ │ │
│ │ ┌─ Status Card ─────────────────────────────────┐ │ │
│ │ │ Redis Cache                 ● Healthy        │ │ │
│ │ │ Connected - 2ms response                     │ │ │
│ │ └───────────────────────────────────────────────┘ │ │
│ │ [Show All Components]                           │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ Key Metrics (grid-cols-1 gap-4, p-4) ─────────┐ │
│ │ ┌─ Metric Card ─────────────────────────────────┐ │ │
│ │ │ Total Searches              ↑ 12%            │ │ │
│ │ │ 1,247 (text-2xl font-bold)                   │ │ │
│ │ └───────────────────────────────────────────────┘ │ │
│ │ ┌─ Metric Card ─────────────────────────────────┐ │ │
│ │ │ Cache Hit Rate              ↑ 5%             │ │ │
│ │ │ 73% (text-2xl font-bold)                     │ │ │
│ │ └───────────────────────────────────────────────┘ │ │
│ │ [Show All Metrics]                              │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ Recent Activity (p-4) ─────────────────────────┐ │
│ │ Recent Queries                      [🔄 Refresh] │ │
│ │ ┌─ Activity Card ───────────────────────────────┐ │ │
│ │ │ 14:32 FastAPI routing                        │ │ │
│ │ │ ✓ 89ms - python-docs                         │ │ │
│ │ └───────────────────────────────────────────────┘ │ │
│ │ ┌─ Activity Card ───────────────────────────────┐ │ │
│ │ │ 14:31 React hooks                            │ │ │
│ │ │ ✓ 156ms - react-docs                         │ │ │
│ │ └───────────────────────────────────────────────┘ │ │
│ │ [View All Activity]                             │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 4.2 Mobile Navigation Menu (Overlay)

```
┌─────────────────────────────────────────────────────┐
│ OVERLAY MENU (fixed inset-0, bg-black bg-opacity-50)│
│ ┌─ Menu Panel (w-64, bg-white, shadow-xl) ─────────┐ │
│ │ ┌─ Menu Header (p-4, border-b) ───────────────────┐│ │
│ │ │ Navigation                             [✕]    ││ │
│ │ └─────────────────────────────────────────────────┘│ │
│ │                                                  │ │
│ │ ┌─ Menu Items (p-2) ──────────────────────────────┐│ │
│ │ │ • Dashboard (active, bg-blue-50, text-blue-700)││ │
│ │ │ • Configuration                                ││ │
│ │ │ • Content Management                           ││ │
│ │ │                                                ││ │
│ │ │ ── Settings ──                                 ││ │
│ │ │ • System Settings                              ││ │
│ │ │ • User Profile                                 ││ │
│ │ └─────────────────────────────────────────────────┘│ │
│ └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 5. Interactive State Specifications

### 5.1 Loading States

#### Dashboard Loading State
```
┌─ Status Card Loading ─────────────────────────────┐
│ Database                                          │
│ ┌─ Loading Skeleton ──────────────────────────────┐ │
│ │ ▓▓▓▓▓▓▓▓░░░░░░░░ (animated loading bar)        │ │
│ └─────────────────────────────────────────────────┘ │
│ Loading status...                                 │
└───────────────────────────────────────────────────┘
```

#### Table Loading State  
```
┌─ Content Table Loading ───────────────────────────┐
│ ┌─ Row Skeleton ────────────────────────────────┐ │
│ │ ▓▓▓▓▓▓▓▓▓░░░ ▓▓▓ ▓▓▓▓ ▓▓▓▓▓▓▓ ▓▓▓▓▓           │ │
│ │ ▓▓▓▓▓▓▓░░░░░ ▓▓▓ ▓▓▓▓ ▓▓▓▓▓▓▓ ▓▓▓▓▓           │ │
│ │ ▓▓▓▓▓▓▓▓░░░░ ▓▓▓ ▓▓▓▓ ▓▓▓▓▓▓▓ ▓▓▓▓▓           │ │
│ └───────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

### 5.2 Error States

#### Component Error State
```
┌─ Status Card Error ───────────────────────────────┐
│ Database                       ● Unavailable      │
│ ⚠ Connection failed: timeout                      │
│ Last seen: 2 minutes ago                          │
│ [Retry Connection] [View Logs]                    │
└───────────────────────────────────────────────────┘
```

#### Form Validation Error
```
┌─ Form Field Error ────────────────────────────────┐
│ Worker Processes *                                │
│ [4                     ] (border-red-500)         │
│ ⚠ Must be between 1 and 16 (text-red-600)        │
└───────────────────────────────────────────────────┘
```

### 5.3 Success States

#### Configuration Save Success
```
┌─ Success Banner (bg-green-50, border-green-200) ─┐
│ ✓ Configuration updated successfully              │
│ Changes will take effect after service restart   │
│                                            [Dismiss] │
└───────────────────────────────────────────────────┘
```

## 6. Component Interaction Patterns

### 6.1 Accordion Behavior (Configuration Sections)
```
State: Collapsed
┌─ Section Header ──────────────────────────────────┐
│ ► Application Settings (cursor-pointer)           │
└───────────────────────────────────────────────────┘

State: Expanded  
┌─ Section Header ──────────────────────────────────┐
│ ▼ Application Settings (cursor-pointer)           │
│ ┌─ Section Content (slide-down animation) ──────┐ │
│ │ [Configuration form fields]                   │ │
│ │ [Save] [Reset]                                │ │
│ └───────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

### 6.2 Table Sorting Behavior
```
Column Header: Unsorted
│ Title ↕ │

Column Header: Ascending  
│ Title ↑ │

Column Header: Descending
│ Title ↓ │
```

### 6.3 Search Autocomplete
```
┌─ Search Input ────────────────────────────────────┐
│ [FastAPI                    ] 🔍                  │
│ ┌─ Suggestions Dropdown ──────────────────────────┐ │
│ │ FastAPI Tutorial                               │ │
│ │ FastAPI Authentication                         │ │
│ │ FastAPI Database Integration                   │ │
│ └────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

These wireframes provide pixel-perfect layout specifications for implementing the Configuration Web UI, ensuring consistent spacing, typography, and interaction patterns across all devices and states.