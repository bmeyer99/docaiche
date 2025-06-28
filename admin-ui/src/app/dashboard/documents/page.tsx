import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Icons } from "@/components/icons";

export default function DocumentsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Documents</h1>
        <div className="flex items-center space-x-2">
          <Button>
            <Icons.upload className="mr-2 h-4 w-4" />
            Upload
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Icons.search className="h-5 w-5" />
              <span>Search Documents</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Search through your document collection with AI-powered relevance.</p>
            <Badge variant="secondary" className="mt-2">Phase 4</Badge>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Icons.folder className="h-5 w-5" />
              <span>Collections</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Organize documents by technology and workspace.</p>
            <Badge variant="secondary" className="mt-2">Phase 4</Badge>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Icons.upload className="h-5 w-5" />
              <span>Upload Content</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Add new documents to your knowledge base.</p>
            <Badge variant="secondary" className="mt-2">Phase 4</Badge>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}