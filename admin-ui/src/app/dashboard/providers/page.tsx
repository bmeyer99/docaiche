import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function ProvidersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">AI Providers</h1>
        <Button variant="outline">
          Test All
        </Button>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Provider Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Configure your AI providers for text generation and embeddings.
            This page will be enhanced in Phase 2 of the implementation.
          </p>
          <div className="mt-4">
            <Badge variant="secondary">Coming Soon</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}