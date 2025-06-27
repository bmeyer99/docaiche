'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';
import { DocaicheApiClient } from '@/lib/utils/api-client';
import { useToast } from '@/hooks/use-toast';

interface UploadFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
  result?: {
    documentId: string;
    extractedText: string;
    pageCount?: number;
  };
}

interface UploadMetadata {
  collection: string;
  technology: string;
  description: string;
  tags: string;
}

export default function ContentUploadPage() {
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [metadata, setMetadata] = useState<UploadMetadata>({
    collection: '',
    technology: '',
    description: '',
    tags: ''
  });
  const [dragActive, setDragActive] = useState(false);
  const { toast } = useToast();
  const apiClient = new DocaicheApiClient();

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    addFiles(files);
    // Reset the input
    e.target.value = '';
  }, []);

  const addFiles = (files: File[]) => {
    const supportedTypes = [
      'application/pdf',
      'text/plain',
      'text/markdown',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/html'
    ];

    const validFiles = files.filter(file => {
      if (!supportedTypes.includes(file.type)) {
        toast({
          title: "Unsupported File Type",
          description: `${file.name} is not a supported file type`,
          variant: "destructive",
        });
        return false;
      }
      if (file.size > 50 * 1024 * 1024) { // 50MB limit
        toast({
          title: "File Too Large",
          description: `${file.name} exceeds the 50MB size limit`,
          variant: "destructive",
        });
        return false;
      }
      return true;
    });

    const newUploadFiles: UploadFile[] = validFiles.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      status: 'pending',
      progress: 0
    }));

    setUploadFiles(prev => [...prev, ...newUploadFiles]);
  };

  const removeFile = (fileId: string) => {
    setUploadFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const uploadFile = async (uploadFile: UploadFile) => {
    const { id, file } = uploadFile;

    // Update status to uploading
    setUploadFiles(prev => prev.map(f => 
      f.id === id ? { ...f, status: 'uploading', progress: 0 } : f
    ));

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadFiles(prev => prev.map(f => {
          if (f.id === id && f.status === 'uploading') {
            const newProgress = Math.min(f.progress + Math.random() * 30, 95);
            return { ...f, progress: newProgress };
          }
          return f;
        }));
      }, 500);

      const response = await apiClient.uploadContent(file, {
        collection: metadata.collection || undefined,
        technology: metadata.technology || undefined
      });

      clearInterval(progressInterval);

      // Update to processing
      setUploadFiles(prev => prev.map(f => 
        f.id === id ? { ...f, status: 'processing', progress: 100 } : f
      ));

      // Simulate processing time
      setTimeout(() => {
        setUploadFiles(prev => prev.map(f => 
          f.id === id ? { 
            ...f, 
            status: 'completed', 
            result: {
              documentId: response.documentId,
              extractedText: response.extractedText || '',
              pageCount: response.pageCount
            }
          } : f
        ));
      }, 2000);

      toast({
        title: "Upload Successful",
        description: `${file.name} has been uploaded and indexed successfully`,
      });

    } catch (error) {
      setUploadFiles(prev => prev.map(f => 
        f.id === id ? { 
          ...f, 
          status: 'error', 
          error: error instanceof Error ? error.message : 'Upload failed'
        } : f
      ));

      toast({
        title: "Upload Failed",
        description: `Failed to upload ${file.name}`,
        variant: "destructive",
      });
    }
  };

  const uploadAllFiles = async () => {
    const pendingFiles = uploadFiles.filter(f => f.status === 'pending');
    
    if (pendingFiles.length === 0) {
      toast({
        title: "No Files to Upload",
        description: "All files have already been processed",
        variant: "destructive",
      });
      return;
    }

    // Upload files sequentially to avoid overwhelming the server
    for (const file of pendingFiles) {
      await uploadFile(file);
      // Small delay between uploads
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  };

  const clearCompleted = () => {
    setUploadFiles(prev => prev.filter(f => f.status !== 'completed'));
  };

  const getFileIcon = (file: File) => {
    if (file.type.includes('pdf')) return <Icons.fileText className="w-8 h-8 text-red-600" />;
    if (file.type.includes('word')) return <Icons.fileText className="w-8 h-8 text-blue-600" />;
    if (file.type.includes('text')) return <Icons.fileText className="w-8 h-8 text-gray-600" />;
    if (file.type.includes('markdown')) return <Icons.fileText className="w-8 h-8 text-blue-500" />;
    if (file.type.includes('html')) return <Icons.globe className="w-8 h-8 text-orange-600" />;
    return <Icons.file className="w-8 h-8" />;
  };

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'pending': return <Icons.clock className="w-4 h-4 text-gray-500" />;
      case 'uploading': return <Icons.upload className="w-4 h-4 text-blue-500" />;
      case 'processing': return <Icons.spinner className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'completed': return <Icons.checkCircle className="w-4 h-4 text-green-500" />;
      case 'error': return <Icons.alertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const getStatusBadge = (status: UploadFile['status']) => {
    switch (status) {
      case 'pending': return <Badge variant="secondary">Pending</Badge>;
      case 'uploading': return <Badge className="bg-blue-100 text-blue-800">Uploading</Badge>;
      case 'processing': return <Badge className="bg-yellow-100 text-yellow-800">Processing</Badge>;
      case 'completed': return <Badge className="bg-green-100 text-green-800">Completed</Badge>;
      case 'error': return <Badge className="bg-red-100 text-red-800">Error</Badge>;
    }
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Upload Content</h1>
        <p className="text-muted-foreground">
          Upload documents to be indexed and made searchable
        </p>
      </div>

      {/* Upload Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Settings</CardTitle>
          <CardDescription>
            Configure metadata for uploaded documents
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="collection">Collection</Label>
            <Select
              value={metadata.collection}
              onValueChange={(value) => setMetadata(prev => ({ ...prev, collection: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select collection" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="documentation">Documentation</SelectItem>
                <SelectItem value="api-docs">API Docs</SelectItem>
                <SelectItem value="tutorials">Tutorials</SelectItem>
                <SelectItem value="guides">Guides</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="technology">Technology</Label>
            <Select
              value={metadata.technology}
              onValueChange={(value) => setMetadata(prev => ({ ...prev, technology: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select technology" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="react">React</SelectItem>
                <SelectItem value="nextjs">Next.js</SelectItem>
                <SelectItem value="nodejs">Node.js</SelectItem>
                <SelectItem value="python">Python</SelectItem>
                <SelectItem value="typescript">TypeScript</SelectItem>
                <SelectItem value="javascript">JavaScript</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2 md:col-span-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              value={metadata.description}
              onChange={(e) => setMetadata(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Describe the content of these documents"
            />
          </div>

          <div className="grid gap-2 md:col-span-2">
            <Label htmlFor="tags">Tags (Optional)</Label>
            <Input
              id="tags"
              value={metadata.tags}
              onChange={(e) => setMetadata(prev => ({ ...prev, tags: e.target.value }))}
              placeholder="Enter tags separated by commas"
            />
          </div>
        </CardContent>
      </Card>

      {/* File Drop Zone */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Files</CardTitle>
          <CardDescription>
            Drag and drop files or click to select. Supported formats: PDF, TXT, MD, DOCX, HTML
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive ? 'border-primary bg-primary/10' : 'border-muted-foreground/25'
            }`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <Icons.upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <div className="text-lg font-medium mb-2">
              Drag and drop files here, or click to select
            </div>
            <div className="text-sm text-muted-foreground mb-4">
              Maximum file size: 50MB per file
            </div>
            <input
              type="file"
              multiple
              accept=".pdf,.txt,.md,.docx,.doc,.html"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <Button asChild>
              <label htmlFor="file-upload" className="cursor-pointer">
                <Icons.plus className="w-4 h-4 mr-2" />
                Select Files
              </label>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Upload Queue */}
      {uploadFiles.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Upload Queue</CardTitle>
                <CardDescription>
                  {uploadFiles.length} file{uploadFiles.length !== 1 ? 's' : ''} ready for upload
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={uploadAllFiles}
                  disabled={uploadFiles.every(f => f.status !== 'pending')}
                >
                  <Icons.upload className="w-4 h-4 mr-2" />
                  Upload All
                </Button>
                <Button variant="outline" onClick={clearCompleted}>
                  <Icons.trash2 className="w-4 h-4 mr-2" />
                  Clear Completed
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {uploadFiles.map((uploadFile) => (
                <div key={uploadFile.id} className="border rounded-lg p-4">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0">
                      {getFileIcon(uploadFile.file)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <div className="font-medium truncate">{uploadFile.file.name}</div>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(uploadFile.status)}
                          {getStatusBadge(uploadFile.status)}
                        </div>
                      </div>
                      
                      <div className="text-sm text-muted-foreground mb-2">
                        {formatFileSize(uploadFile.file.size)} • {uploadFile.file.type}
                      </div>

                      {uploadFile.status === 'uploading' && (
                        <div className="mb-2">
                          <Progress value={uploadFile.progress} className="h-2" />
                          <div className="text-xs text-muted-foreground mt-1">
                            {uploadFile.progress.toFixed(0)}% uploaded
                          </div>
                        </div>
                      )}

                      {uploadFile.status === 'error' && uploadFile.error && (
                        <div className="text-sm text-red-600 mb-2">
                          Error: {uploadFile.error}
                        </div>
                      )}

                      {uploadFile.status === 'completed' && uploadFile.result && (
                        <div className="text-sm text-green-600 mb-2">
                          Successfully indexed • Document ID: {uploadFile.result.documentId}
                          {uploadFile.result.pageCount && ` • ${uploadFile.result.pageCount} pages`}
                        </div>
                      )}
                    </div>

                    <div className="flex-shrink-0">
                      {uploadFile.status === 'pending' && (
                        <div className="flex gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => uploadFile(uploadFile)}
                          >
                            <Icons.upload className="w-3 h-3" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => removeFile(uploadFile.id)}
                          >
                            <Icons.x className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                      {uploadFile.status === 'completed' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => removeFile(uploadFile.id)}
                        >
                          <Icons.x className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}