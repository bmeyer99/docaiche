# Dashboard Overview Page Specification

## 1. Overview
This document specifies the design for the main **Dashboard Overview** page. This page will serve as the primary entry point for the application, providing at-a-glance information about system health and key metrics.

**Objective**: Create a "mission control" view for the AI Documentation Cache System.

## 2. Information Architecture & Routing
- **Route**: This page will be rendered at the root path (`/`).
- **Navigation**: The main navigation should provide a clear link to this "Overview" or "Dashboard" page, and a separate link to the "Configuration" page (at `/configuration`).

## 3. Page Layout & Components
The page will use a two-column grid layout on desktop, stacking to a single column on mobile.

### 3.1. Page Header
- **Title**: "Dashboard Overview"
- **Subtitle**: "Real-time system health and performance metrics."

### 3.2. Component Grid

#### Column 1 (Main Content):

**1. System Status Summary Card (`SystemStatusCard.tsx`)**
- **Title**: "System Status"
- **Content**: A list of core services with real-time status indicators.
  - **AnythingLLM**: `[Green/Yellow/Red Indicator]` "Operational" / "Degraded" / "Offline"
  - **Ollama**: `[Green/Yellow/Red Indicator]` "Operational" / "Degraded" / "Offline"
  - **Redis Cache**: `[Green/Yellow/Red Indicator]` "Connected" / "Issues" / "Disconnected"
  - **Database (SQLite)**: `[Green/Yellow/Red Indicator]` "Connected" / "Issues" / "Disconnected"
- **Design**: Use `statusConnected`, `statusFailed` styles for indicators.

**2. Search Analytics Card (`SearchAnalyticsCard.tsx`)**
- **Title**: "Search Analytics (Last 24 Hours)"
- **Content**: Display key metrics using `DashboardMetric.tsx` components.
  - **Total Queries**: e.g., "1,428"
  - **Avg. Response Time**: e.g., "1.2s"
  - **Cache Hit Rate**: e.g., "78%"
- **Visualization**: A simple line chart showing query volume over the last 24 hours.

#### Column 2 (Secondary Content):

**1. Content Management Summary Card (`ContentSummaryCard.tsx`)**
- **Title**: "Content Library"
- **Content**: Key metrics about the ingested documents.
  - **Total Documents**: e.g., "5,982"
  - **Workspaces**: e.g., "12"
  - **Pending Ingestion**: e.g., "5" (styled with a warning indicator)
- **Action**: A button "Manage Content" that links to the future content management section.

**2. Recent Activity Feed (`RecentActivityFeed.tsx`)**
- **Title**: "Recent Activity"
- **Content**: A scrollable list of recent system events.
  - "User 'admin' updated LLM configuration." (2 minutes ago)
  - "Document 'API_GUIDE.md' successfully ingested." (15 minutes ago)
  - "System health check passed." (30 minutes ago)

### 3. New UI Components

**1. `DashboardMetric.tsx`**
- **Props**: `label: string`, `value: string`
- **Layout**: A small component displaying a label and a large metric value.

**2. Chart Component**
- **Recommendation**: Use a lightweight charting library like `recharts` or `chart.js`.
- **Requirement**: The chart must be responsive and performant.

## 4. Implementation Guidance
- Create placeholder components for each new card.
- Use the existing `Card` component as a base.
- Fetch data asynchronously for each card to avoid blocking the UI. Display skeleton loaders for each card while its data is loading.