# Progressive WebSocket Analytics API

## Overview

The progressive WebSocket endpoint (`/api/v1/ws/analytics/progressive`) provides analytics data progressively as it becomes available, rather than waiting for all data to be gathered before sending. This improves the perceived performance and user experience by showing data as soon as it's ready.

## Endpoint

```
ws://localhost:4080/api/v1/ws/analytics/progressive
```

## Key Differences from Regular Analytics WebSocket

### Regular WebSocket (`/ws/analytics`)
- Gathers ALL data before sending
- Frontend waits with no feedback until complete
- Single message with all data at once
- Can take several seconds before any data appears

### Progressive WebSocket (`/ws/analytics/progressive`)
- Sends data in chunks as each section becomes available
- Immediate connection acknowledgment
- Progressive loading with multiple messages
- Users see data appearing progressively

## Message Flow

1. **Initial Connection** (`section: "init"`)
   ```json
   {
     "type": "analytics_update",
     "section": "init",
     "timestamp": "2025-07-02T07:00:00.000Z",
     "data": {
       "status": "connected",
       "message": "Loading analytics data..."
     }
   }
   ```

2. **System Health** (`section: "health"`) - Quick to gather
   ```json
   {
     "type": "analytics_update",
     "section": "health",
     "timestamp": "2025-07-02T07:00:00.100Z",
     "data": {
       "systemHealth": {
         "database": { "status": "healthy", ... },
         "cache": { "status": "healthy", ... },
         "api_core": { "status": "healthy", ... }
       }
     }
   }
   ```

3. **Basic Statistics** (`section: "basic_stats"`) - Relatively quick
   ```json
   {
     "type": "analytics_update",
     "section": "basic_stats",
     "timestamp": "2025-07-02T07:00:00.300Z",
     "data": {
       "stats": {
         "search_stats": { "total_searches": 1234, ... },
         "content_stats": { "total_documents": 567, ... }
       }
     }
   }
   ```

4. **Detailed Analytics** (`section: "detailed_analytics"`) - May take longer
   ```json
   {
     "type": "analytics_update",
     "section": "detailed_analytics",
     "timestamp": "2025-07-02T07:00:01.500Z",
     "data": {
       "analytics": {
         "searchMetrics": { ... },
         "contentMetrics": { ... }
       }
     }
   }
   ```

5. **Service Metrics** (`section: "service_metrics"`) - Optional, may be slow
   ```json
   {
     "type": "analytics_update",
     "section": "service_metrics",
     "timestamp": "2025-07-02T07:00:02.000Z",
     "data": {
       "service_metrics": { ... }
     }
   }
   ```

6. **Load Complete** (`section: "complete"`)
   ```json
   {
     "type": "analytics_update",
     "section": "complete",
     "timestamp": "2025-07-02T07:00:02.100Z",
     "data": {
       "loadComplete": true
     }
   }
   ```

## Periodic Updates

After initial load, the WebSocket sends periodic updates every 5 seconds:

- **Health Updates** (`section: "health_update"`)
- **Stats Updates** (`section: "stats_update"`)

## Client Messages

### Change Time Range
```json
{
  "type": "change_timerange",
  "timeRange": "7d"  // Options: "24h", "7d", "30d"
}
```

### Ping/Pong (Keep-alive)
```json
{
  "type": "ping"
}
```

## Frontend Integration

The progressive WebSocket maintains compatibility with the existing message format (`type: "analytics_update"`), but adds a `section` field to indicate which part of the data is being sent.

### Example Frontend Handler

```javascript
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'analytics_update') {
    switch(data.section) {
      case 'init':
        // Show loading state
        break;
      case 'health':
        // Update health section
        updateHealthDisplay(data.data.systemHealth);
        break;
      case 'basic_stats':
        // Update basic stats
        updateStatsDisplay(data.data.stats);
        break;
      case 'detailed_analytics':
        // Update detailed analytics
        updateAnalyticsDisplay(data.data.analytics);
        break;
      case 'complete':
        // Hide loading indicators
        setLoadingComplete();
        break;
    }
  }
};
```

## Testing

A test HTML page is available at `/home/lab/docaiche/src/api/v1/websocket_progressive_test.html` that demonstrates:
- Progressive loading timeline
- Comparison with regular WebSocket
- Visual feedback for each data section
- Raw message logging

## Benefits

1. **Improved User Experience**: Users see data immediately instead of waiting
2. **Better Feedback**: Clear indication of what's loading and when
3. **Resilience**: If one section fails, others still load
4. **Flexibility**: Easy to add new sections without breaking existing clients
5. **Performance**: Expensive queries don't block quick data from appearing