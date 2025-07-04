import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Simple health check
    return NextResponse.json({
      status: 'healthy',
      service: 'admin-ui',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        service: 'admin-ui',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 503 }
    );
  }
}