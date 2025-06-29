import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function ProfileViewPage() {
  return (
    <div className='flex w-full flex-col gap-6 p-6'>
      <div>
        <h1 className='text-3xl font-bold'>System Information</h1>
        <p className='text-muted-foreground'>
          Current deployment and environment details
        </p>
      </div>

      <div className='grid gap-6 md:grid-cols-2'>
        <Card>
          <CardHeader>
            <CardTitle>Environment</CardTitle>
            <CardDescription>Current deployment configuration</CardDescription>
          </CardHeader>
          <CardContent className='space-y-2'>
            <div className='flex justify-between'>
              <span>Environment:</span>
              <Badge variant="secondary">Lab</Badge>
            </div>
            <div className='flex justify-between'>
              <span>Authentication:</span>
              <Badge variant="outline">Disabled</Badge>
            </div>
            <div className='flex justify-between'>
              <span>API Endpoint:</span>
              <code className='text-sm'>http://localhost:4080/api/v1</code>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Admin Access</CardTitle>
            <CardDescription>Current user information</CardDescription>
          </CardHeader>
          <CardContent className='space-y-2'>
            <div className='flex justify-between'>
              <span>User:</span>
              <span>Admin User</span>
            </div>
            <div className='flex justify-between'>
              <span>Email:</span>
              <span>admin@docaiche.local</span>
            </div>
            <div className='flex justify-between'>
              <span>Role:</span>
              <Badge variant="default">Administrator</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
