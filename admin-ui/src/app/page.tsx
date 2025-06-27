import { redirect } from 'next/navigation';

export default async function Page() {
  // Redirect directly to dashboard since auth is disabled for lab environment
  redirect('/dashboard');
}
