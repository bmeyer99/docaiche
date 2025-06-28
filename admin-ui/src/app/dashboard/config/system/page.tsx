import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'System Settings',
  description: 'Configure system-wide settings for the Docaiche application',
};

export default function SystemConfigPage() {
  return (
    <div className="container mx-auto py-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
          <p className="text-muted-foreground mt-2">
            Configure system-wide settings and preferences for the Docaiche application.
          </p>
        </div>

        <div className="space-y-6">
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">General Settings</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Application Name</h3>
                  <p className="text-sm text-muted-foreground">The display name for the application</p>
                </div>
                <span className="text-sm text-muted-foreground">Docaiche Admin</span>
              </div>
              
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Environment</h3>
                  <p className="text-sm text-muted-foreground">Current deployment environment</p>
                </div>
                <span className="text-sm text-muted-foreground">Production</span>
              </div>
            </div>
          </div>

          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Security Settings</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">Authentication</h3>
                  <p className="text-sm text-muted-foreground">User authentication status</p>
                </div>
                <span className="text-sm text-muted-foreground">Disabled (Lab Environment)</span>
              </div>
            </div>
          </div>

          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">API Configuration</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div>
                  <h3 className="font-medium">API Base URL</h3>
                  <p className="text-sm text-muted-foreground">Base URL for API communications</p>
                </div>
                <span className="text-sm text-muted-foreground font-mono">http://localhost:4000/api/v1</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}