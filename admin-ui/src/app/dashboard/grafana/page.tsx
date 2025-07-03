'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Icons } from '@/components/icons';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface GrafanaDashboard {
  id: number;
  uid: string;
  title: string;
  tags: string[];
  type: string;
  url: string;
  isStarred: boolean;
  folderId: number;
  folderTitle: string;
}

interface GrafanaFolder {
  id: number;
  uid: string;
  title: string;
}

export default function GrafanaDashboardsPage() {
  const [dashboards, setDashboards] = useState<GrafanaDashboard[]>([]);
  const [folders, setFolders] = useState<GrafanaFolder[]>([]);
  const [selectedDashboard, setSelectedDashboard] = useState<string>('');
  const [selectedFolder, setSelectedFolder] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);

  const grafanaBaseUrl = '/grafana';

  // Fetch dashboards and folders from Grafana API
  useEffect(() => {
    const fetchGrafanaData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch folders
        const foldersResponse = await fetch('/grafana/api/folders', {
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          }
        });
        if (!foldersResponse.ok) throw new Error('Failed to fetch folders');
        const foldersData = await foldersResponse.json();
        setFolders([{ id: 0, uid: 'general', title: 'General' }, ...foldersData]);

        // Fetch dashboards
        const dashboardsResponse = await fetch('/grafana/api/search?type=dash-db', {
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          }
        });
        if (!dashboardsResponse.ok) throw new Error('Failed to fetch dashboards');
        const dashboardsData = await dashboardsResponse.json();
        setDashboards(dashboardsData);

        // Set default dashboard if available
        if (dashboardsData.length > 0) {
          setSelectedDashboard(dashboardsData[0].uid);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load Grafana data');
      } finally {
        setLoading(false);
      }
    };

    fetchGrafanaData();
  }, []);

  // Filter dashboards by folder
  const filteredDashboards = dashboards.filter(dashboard => 
    selectedFolder === 'all' || dashboard.folderId.toString() === selectedFolder
  );

  // Get current dashboard info
  const currentDashboard = dashboards.find(d => d.uid === selectedDashboard);

  // Refresh iframe
  const refreshDashboard = () => {
    setIframeKey(prev => prev + 1);
  };

  // Get dashboard URL for iframe
  const getDashboardUrl = (uid: string) => {
    if (!uid) return '';
    return `${grafanaBaseUrl}/d/${uid}?orgId=1&refresh=30s&kiosk=tv&theme=light`;
  };

  if (loading) {
    return (
      <div className="flex flex-col space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-64 mb-2" />
            <Skeleton className="h-4 w-96" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="lg:col-span-3">
            <Skeleton className="h-96 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">Grafana Dashboards</h1>
          <p className="text-muted-foreground">View and manage Grafana dashboards</p>
        </div>
        <Alert variant="destructive">
          <Icons.alertCircle className="h-4 w-4" />
          <AlertDescription>
            {error}. Make sure Grafana is running and accessible
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Grafana Dashboards</h1>
          <p className="text-muted-foreground">
            View and manage Grafana dashboards with real-time monitoring data
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={refreshDashboard}
            className="flex items-center space-x-2"
          >
            <Icons.refresh className="h-4 w-4" />
            <span>Refresh</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            asChild
          >
            <a
              href={grafanaBaseUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2"
            >
              <Icons.externalLink className="h-4 w-4" />
              <span>Open Grafana</span>
            </a>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar - Dashboard Selection */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Icons.dashboard className="h-5 w-5" />
                <span>Dashboards</span>
              </CardTitle>
              <CardDescription>
                Select a dashboard to view ({dashboards.length} available)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Folder Filter */}
              <div>
                <label className="text-sm font-medium mb-2 block">Filter by Folder</label>
                <Select value={selectedFolder} onValueChange={setSelectedFolder}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select folder" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Folders</SelectItem>
                    {folders.map((folder) => (
                      <SelectItem key={folder.id} value={folder.id.toString()}>
                        {folder.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              {/* Dashboard List */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Available Dashboards</label>
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {filteredDashboards.map((dashboard) => (
                    <button
                      key={dashboard.uid}
                      onClick={() => setSelectedDashboard(dashboard.uid)}
                      className={`w-full text-left p-2 rounded-md text-sm transition-colors ${
                        selectedDashboard === dashboard.uid
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted'
                      }`}
                    >
                      <div className="font-medium truncate">{dashboard.title}</div>
                      <div className="flex items-center space-x-1 mt-1">
                        {dashboard.isStarred && (
                          <Icons.checkCircle className="h-3 w-3 text-yellow-500" />
                        )}
                        {dashboard.tags.slice(0, 2).map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {filteredDashboards.length === 0 && (
                <div className="text-center text-muted-foreground text-sm py-4">
                  No dashboards found in selected folder
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Main Content - Dashboard Viewer */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center space-x-2">
                    <Icons.monitor className="h-5 w-5" />
                    <span>{currentDashboard?.title || 'Select a Dashboard'}</span>
                  </CardTitle>
                  {currentDashboard && (
                    <CardDescription className="flex items-center space-x-2 mt-2">
                      <span>UID: {currentDashboard.uid}</span>
                      <Separator orientation="vertical" className="h-4" />
                      <span>Folder: {currentDashboard.folderTitle}</span>
                      {currentDashboard.tags.length > 0 && (
                        <>
                          <Separator orientation="vertical" className="h-4" />
                          <div className="flex items-center space-x-1">
                            {currentDashboard.tags.map((tag) => (
                              <Badge key={tag} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </>
                      )}
                    </CardDescription>
                  )}
                </div>
                {currentDashboard && (
                  <Button
                    variant="outline"
                    size="sm"
                    asChild
                  >
                    <a
                      href={`${grafanaBaseUrl}/d/${currentDashboard.uid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2"
                    >
                      <Icons.externalLink className="h-4 w-4" />
                      <span>Full View</span>
                    </a>
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {selectedDashboard ? (
                <div className="relative">
                  <iframe
                    key={iframeKey}
                    src={getDashboardUrl(selectedDashboard)}
                    width="100%"
                    height="600"
                    frameBorder="0"
                    className="rounded-md border"
                    title={currentDashboard?.title || 'Grafana Dashboard'}
                  />
                  <div className="absolute top-2 right-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={refreshDashboard}
                      className="opacity-75 hover:opacity-100"
                    >
                      <Icons.refresh className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-96 text-muted-foreground">
                  <div className="text-center">
                    <Icons.monitor className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Select a dashboard from the sidebar to view it here</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}