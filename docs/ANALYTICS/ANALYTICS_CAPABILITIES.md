# Docaiche Analytics Capabilities

## Overview
Docaiche provides comprehensive analytics through multiple endpoints designed to support beautiful dashboard visualizations and real-time monitoring.

## Analytics Endpoints

### 1. `/api/v1/stats` - System Statistics
Real-time system performance and usage metrics.

**Response Structure:**
```json
{
  "search_stats": {
    "total_searches": 0,           // Total searches performed
    "avg_response_time_ms": 0,     // Average response time
    "cache_hit_rate": 0,           // Cache efficiency (0-1)
    "successful_searches": 0,       // Successful search count
    "failed_searches": 0            // Failed search count
  },
  "cache_stats": {
    "hit_rate": 0,                 // Cache hit rate (0-1)
    "miss_rate": 0,                // Cache miss rate (0-1)
    "total_keys": 0,               // Keys in cache
    "memory_usage_mb": 0,          // Cache memory usage
    "evictions": 0                 // Cache evictions
  },
  "content_stats": {
    "total_documents": 0,          // Total documents
    "total_chunks": 0,             // Document chunks
    "avg_quality_score": 0,        // Average quality (0-1)
    "workspaces": 0,               // Number of workspaces
    "last_enrichment": "2025-..."  // Last enrichment time
  },
  "system_stats": {
    "uptime_seconds": 123456,      // System uptime
    "cpu_usage_percent": 15.5,     // CPU usage
    "memory_usage_mb": 512.3,      // Memory usage
    "disk_usage_mb": 1024.5        // Disk usage
  }
}
```

### 2. `/api/v1/analytics` - Time-Based Analytics
Aggregated metrics for specific time ranges (24h, 7d, 30d).

**Response Structure:**
```json
{
  "timeRange": "24h",
  "searchMetrics": {
    "totalSearches": 12,
    "avgResponseTime": 125,
    "successRate": 0.95,
    "topQueries": [
      {"query": "python async", "count": 45},
      {"query": "react hooks", "count": 32}
    ]
  },
  "contentMetrics": {
    "totalDocuments": 15432,
    "totalChunks": 89765,
    "avgQualityScore": 0.82,
    "documentsByTechnology": [
      {"technology": "Python", "count": 5432},
      {"technology": "JavaScript", "count": 3245}
    ]
  },
  "userMetrics": {
    "activeUsers": 8,
    "totalSessions": 15,
    "avgSessionDuration": 245000  // milliseconds
  }
}
```

### 3. `/api/v1/admin/activity/recent` - Real-Time Activity Feed
Live stream of system activity for activity monitors.

**Response Structure:**
```json
[
  {
    "id": "activity_123",
    "type": "search",              // search, config, content, error
    "message": "Search: python async",
    "timestamp": "2025-06-28T19:00:00Z",
    "details": "Additional context"
  }
]
```

### 4. `/api/v1/admin/dashboard` - Aggregated Dashboard Data
Single endpoint providing all dashboard data to minimize API calls.

**Response Structure:**
```json
{
  "stats": {
    // All stats from /stats endpoint
  },
  "recent_activity": [
    // Recent activity items
  ],
  "providers": {
    "configured": 2,
    "available": 3,
    "active": 1
  },
  "health": {
    "overall_status": "healthy",
    "services_up": 4,
    "services_total": 4
  }
}
```

## User Behavior Tracking

### Feedback Signals
Track explicit user feedback on search results:
- `helpful` / `not_helpful` - Result usefulness
- `outdated` - Content needs updating
- `incorrect` - Content has errors
- `flag` - Content needs review

### Usage Signals
Track implicit user behavior:
- `click` - Result clicks
- `dwell_time` - Time spent on content
- `copy` - Content copying
- `share` - Result sharing
- `scroll_depth` - Reading depth

## Dashboard Visualization Ideas

### 1. Search Analytics Dashboard
- **Search Volume Chart**: Time series of search queries
- **Response Time Graph**: Performance metrics over time
- **Cache Efficiency Gauge**: Real-time cache hit rate
- **Top Queries Word Cloud**: Most popular search terms
- **Technology Filter Usage**: Pie chart of tech preferences

### 2. Content Analytics Dashboard
- **Document Growth**: Time series of content additions
- **Quality Score Distribution**: Histogram of content quality
- **Technology Coverage**: Stacked bar chart by technology
- **Workspace Activity**: Heatmap of workspace usage
- **Content Freshness**: Age distribution of documents

### 3. User Engagement Dashboard
- **Active Users**: Real-time user count
- **Session Duration**: Average time on site
- **Engagement Funnel**: Search → Click → Dwell → Action
- **Feedback Sentiment**: Positive vs negative feedback ratio
- **Popular Content**: Most accessed documents

### 4. System Health Dashboard
- **Service Status Grid**: Health of all components
- **Resource Usage**: CPU, Memory, Disk gauges
- **Error Rate**: Time series of errors
- **API Response Times**: Latency distribution
- **Uptime Percentage**: System availability

## Grafana Integration

Access pre-built dashboards at: `http://localhost:4080/grafana/`

Available dashboards:
- **System Overview**: All services health and metrics
- **Search Performance**: Query patterns and performance
- **Content Analytics**: Document statistics and quality
- **User Behavior**: Engagement and feedback metrics

## Data Collection Best Practices

1. **Session Tracking**: Include `session_id` in search requests
2. **Feedback Loop**: Submit both explicit feedback and implicit signals
3. **Error Context**: Include query and position for better analysis
4. **Time Ranges**: Use appropriate ranges for different visualizations

## Current Data Availability

- **Real Data**: System stats, health metrics, activity logs
- **Demo Data**: Analytics endpoint shows example structure
- **Growing Data**: Metrics improve as system usage increases

## Frontend Implementation Tips

1. **Polling Intervals**:
   - Health/Stats: Every 30 seconds
   - Activity Feed: Every 5 seconds
   - Analytics: Every 5 minutes

2. **Caching Strategy**:
   - Cache analytics data for time range duration
   - Invalidate on user actions

3. **Error Handling**:
   - Gracefully handle empty data sets
   - Show meaningful empty states

4. **Performance**:
   - Use `/admin/dashboard` for initial load
   - Update individual components as needed

---

For additional details, refer to the OpenAPI specification at `/openapi_spec.yaml`