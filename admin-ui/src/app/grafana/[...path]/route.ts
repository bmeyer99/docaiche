import { NextRequest } from 'next/server';

const GRAFANA_URL = 'http://grafana:3000';
const DEBUG = true;

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path?.join('/') || '';
  
  // Build the target URL
  const targetUrl = new URL(`/${pathStr}`, GRAFANA_URL);
  targetUrl.search = request.nextUrl.search;
  
  // Create headers
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    // Skip host header
    if (key.toLowerCase() !== 'host') {
      headers.set(key, value);
    }
  });
  
  // Set proper host header for Grafana to generate correct URLs
  headers.set('x-forwarded-host', request.headers.get('host') || 'localhost:4080');
  headers.set('x-forwarded-proto', 'http');
  headers.set('x-forwarded-for', request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || '');
  
  // Handle WebSocket upgrade
  const upgrade = request.headers.get('upgrade');
  const isWebSocket = upgrade?.toLowerCase() === 'websocket';
  
  try {
    // Make the request to Grafana
    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.arrayBuffer() : undefined,
      redirect: 'manual',
    });
    
    // Handle redirects by rewriting the location header
    if (response.status === 301 || response.status === 302 || response.status === 303 || response.status === 307 || response.status === 308) {
      const location = response.headers.get('location');
      if (location) {
        // If it's a relative redirect, prepend /grafana
        if (location.startsWith('/') && !location.startsWith('/grafana')) {
          const newHeaders = new Headers(response.headers);
          newHeaders.set('location', `/grafana${location}`);
          return new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: newHeaders,
          });
        }
      }
    }
    
    // For non-redirect responses, pass through
    const responseHeaders = new Headers(response.headers);
    
    // Remove any headers that might cause issues
    responseHeaders.delete('content-encoding');
    responseHeaders.delete('content-length');
    responseHeaders.delete('transfer-encoding');
    
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Grafana proxy error:', error);
    return new Response('Failed to connect to Grafana', { status: 502 });
  }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
export const HEAD = handler;
export const OPTIONS = handler;