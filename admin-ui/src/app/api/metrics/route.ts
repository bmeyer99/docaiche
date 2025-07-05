import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const uptime = process.uptime();
    const memoryUsage = process.memoryUsage();
    
    // Simple Prometheus-style metrics
    const metrics = `
# HELP admin_ui_up Whether the admin UI is up
# TYPE admin_ui_up gauge
admin_ui_up 1

# HELP admin_ui_uptime_seconds Uptime in seconds
# TYPE admin_ui_uptime_seconds counter
admin_ui_uptime_seconds ${uptime}

# HELP admin_ui_memory_usage_bytes Memory usage in bytes
# TYPE admin_ui_memory_usage_bytes gauge
admin_ui_memory_usage_bytes{type="rss"} ${memoryUsage.rss}
admin_ui_memory_usage_bytes{type="heapUsed"} ${memoryUsage.heapUsed}
admin_ui_memory_usage_bytes{type="heapTotal"} ${memoryUsage.heapTotal}
admin_ui_memory_usage_bytes{type="external"} ${memoryUsage.external}
`.trim();

    return new NextResponse(metrics, {
      headers: {
        'Content-Type': 'text/plain; version=0.0.4; charset=utf-8',
      },
    });
  } catch (error) {
    return new NextResponse('# ERROR: Failed to generate metrics', {
      status: 500,
      headers: {
        'Content-Type': 'text/plain; version=0.0.4; charset=utf-8',
      },
    });
  }
}