import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Perform basic health checks
    const timestamp = new Date().toISOString();
    
    // Check if we can connect to our API (optional - might timeout during startup)
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    
    return NextResponse.json({
      status: 'healthy',
      timestamp,
      service: 'docaiche-admin-ui',
      environment: process.env.NODE_ENV,
      api_configured: !!apiUrl,
      api_url: apiUrl
    });
  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    );
  }
}