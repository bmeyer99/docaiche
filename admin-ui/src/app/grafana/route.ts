import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  // Redirect /grafana to /grafana/
  return NextResponse.redirect(new URL('/grafana/', request.url), 301);
}