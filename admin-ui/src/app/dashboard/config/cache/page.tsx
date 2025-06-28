import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Cache Management',
  description: 'Manage and monitor cache settings for the Docaiche system',
};

export default function CacheConfigPage() {
  return (
    <div className="container mx-auto py-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Cache Management</h1>
          <p className="text-muted-foreground mt-2">
            Monitor and manage the cache system for improved performance.
          </p>
        </div>

        <div className="space-y-6">
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Cache Status</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Redis Connection</h3>
                  <p className="text-sm text-muted-foreground">Current cache backend status</p>
                </div>
                <span className="inline-flex items-center rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                  Connected
                </span>
              </div>
              
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Cache Hit Rate</h3>
                  <p className="text-sm text-muted-foreground">Percentage of requests served from cache</p>
                </div>
                <span className="text-sm text-muted-foreground">N/A</span>
              </div>
            </div>
          </div>

          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Cache Settings</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Default TTL</h3>
                  <p className="text-sm text-muted-foreground">Default time-to-live for cached items</p>
                </div>
                <span className="text-sm text-muted-foreground">3600 seconds</span>
              </div>
              
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Max Memory</h3>
                  <p className="text-sm text-muted-foreground">Maximum memory allocated for cache</p>
                </div>
                <span className="text-sm text-muted-foreground">256 MB</span>
              </div>
            </div>
          </div>

          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Cache Operations</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Clear Cache</h3>
                  <p className="text-sm text-muted-foreground">Remove all cached items</p>
                </div>
                <button 
                  className="px-4 py-2 text-sm font-medium text-destructive border border-destructive rounded-md hover:bg-destructive hover:text-destructive-foreground"
                  disabled
                >
                  Clear All Cache
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}