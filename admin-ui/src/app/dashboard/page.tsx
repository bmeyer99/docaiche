import { redirect } from 'next/navigation';

export default async function Dashboard() {
  // Redirect to overview since auth is disabled for lab environment
  redirect('/dashboard/overview');
}
