import { redirect } from 'next/navigation';

export default async function Dashboard() {
  // Redirect to analytics since it provides comprehensive dashboard functionality
  redirect('/dashboard/analytics');
}
