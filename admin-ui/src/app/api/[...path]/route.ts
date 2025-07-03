import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://api:4000';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second
const REQUEST_TIMEOUT = 30000; // 30 seconds

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = MAX_RETRIES
): Promise<Response> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok && retries > 0 && response.status >= 500) {
      // Retry on server errors
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return fetchWithRetry(url, options, retries - 1);
    }
    
    return response;
  } catch (error) {
    if (retries > 0 && (error as any).code === 'ECONNRESET') {
      // Retry on connection reset
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return fetchWithRetry(url, options, retries - 1);
    }
    throw error;
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path.join('/');
  const url = `${API_BASE_URL}/api/${pathStr}${request.nextUrl.search}`;
  
  try {
    const response = await fetchWithRetry(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.text();
    
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error(`Failed to proxy GET ${url}:`, error);
    return NextResponse.json(
      { error: 'Failed to connect to API server' },
      { status: 503 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path.join('/');
  const url = `${API_BASE_URL}/api/${pathStr}${request.nextUrl.search}`;
  
  try {
    const body = await request.text();
    
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: {
        'Content-Type': request.headers.get('Content-Type') || 'application/json',
      },
      body: body,
    });
    
    const data = await response.text();
    
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error(`Failed to proxy POST ${url}:`, error);
    return NextResponse.json(
      { error: 'Failed to connect to API server' },
      { status: 503 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path.join('/');
  const url = `${API_BASE_URL}/api/${pathStr}${request.nextUrl.search}`;
  
  try {
    const body = await request.text();
    
    const response = await fetchWithRetry(url, {
      method: 'PUT',
      headers: {
        'Content-Type': request.headers.get('Content-Type') || 'application/json',
      },
      body: body,
    });
    
    const data = await response.text();
    
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error(`Failed to proxy PUT ${url}:`, error);
    return NextResponse.json(
      { error: 'Failed to connect to API server' },
      { status: 503 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path.join('/');
  const url = `${API_BASE_URL}/api/${pathStr}${request.nextUrl.search}`;
  
  try {
    const response = await fetchWithRetry(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.text();
    
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error) {
    console.error(`Failed to proxy DELETE ${url}:`, error);
    return NextResponse.json(
      { error: 'Failed to connect to API server' },
      { status: 503 }
    );
  }
}