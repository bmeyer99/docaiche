import { redirect } from 'next/navigation';

export default async function Dashboard() {
  try {
    // Make direct server-side API call with absolute URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4080';
    const response = await fetch(`${apiUrl}/api/v1/providers`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Don't cache this request as provider status can change
      cache: 'no-store'
    });
    
    if (!response.ok) {
      // API error, redirect to providers for setup
      redirect('/dashboard/providers');
    }
    
    const providers = await response.json();
    
    // Check if any providers are actually configured and enabled
    const hasConfiguredProviders = Array.isArray(providers) && 
      providers.some((p: any) => p.configured === true || p.enabled === true);
    
    // If no providers configured, redirect to providers page for first-time setup
    if (!hasConfiguredProviders) {
      redirect('/dashboard/providers');
    }
    
    // If providers exist and are configured, redirect to analytics (normal usage)
    redirect('/dashboard/analytics');
  } catch (error) {
    // If API is unavailable or error occurs, default to providers page
    // This ensures users can still access the setup page even if backend is down
    console.error('Dashboard routing error:', error);
    redirect('/dashboard/providers');
  }
}
