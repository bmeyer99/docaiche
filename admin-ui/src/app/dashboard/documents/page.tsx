import { Metadata } from "next";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Icons } from "@/components/icons";

export const metadata: Metadata = {
  title: "Document Management",
  description: "Browse and manage your AI document cache",
};

export default function Page() {
  const stats = {
    totalDocuments: 45680,
    collections: 127,
    indexedToday: 234,
    totalSize: "87.3 GB"
  };

  const features = [
    {
      title: "Search Documents",
      description: "AI-powered search across all indexed content",
      icon: Icons.search,
      href: "/dashboard/search",
      color: "text-blue-600"
    },
    {
      title: "Upload Content", 
      description: "Add new documents to your knowledge base",
      icon: Icons.upload,
      href: "/dashboard/upload",
      color: "text-green-600"
    },
    {
      title: "Collections",
      description: "Organize documents by technology and workspace",
      icon: Icons.folder,
      href: "/dashboard/collections",
      color: "text-purple-600"
    }
  ];

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Document Management</h1>
          <p className="text-muted-foreground">
            Browse, search, and manage your AI document cache
          </p>
        </div>
        <Link href="/dashboard/upload">
          <Button>
            <Icons.upload className="mr-2 h-4 w-4" />
            Upload Documents
          </Button>
        </Link>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <Icons.fileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDocuments.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              +{stats.indexedToday} indexed today
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collections</CardTitle>
            <Icons.folder className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.collections}</div>
            <p className="text-xs text-muted-foreground">
              Organized by technology
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Size</CardTitle>
            <Icons.database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalSize}</div>
            <p className="text-xs text-muted-foreground">
              Indexed content size
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Search Accuracy</CardTitle>
            <Icons.trendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">98.5%</div>
            <p className="text-xs text-muted-foreground">
              Relevance score average
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Feature Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        {features.map((feature) => {
          const IconComponent = feature.icon;
          return (
            <Card key={feature.title} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <IconComponent className={`h-8 w-8 ${feature.color}`} />
                </div>
                <CardTitle className="mt-4">{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Link href={feature.href}>
                  <Button className="w-full">
                    Access
                    <Icons.arrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Document Activity</CardTitle>
          <CardDescription>
            Latest indexed documents and searches
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { title: "React Hooks Documentation", type: "PDF", time: "2 minutes ago", action: "indexed" },
              { title: "Python Async Guide", type: "MD", time: "15 minutes ago", action: "searched" },
              { title: "Docker Best Practices", type: "TXT", time: "1 hour ago", action: "indexed" },
              { title: "AWS Lambda Tutorial", type: "PDF", time: "2 hours ago", action: "updated" }
            ].map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg hover:bg-accent">
                <div className="flex items-center gap-3">
                  <Icons.fileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{item.title}</p>
                    <p className="text-sm text-muted-foreground">{item.type} • {item.action}</p>
                  </div>
                </div>
                <span className="text-sm text-muted-foreground">{item.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}