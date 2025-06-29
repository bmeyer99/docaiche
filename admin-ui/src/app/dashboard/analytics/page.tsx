import { Metadata } from "next";
import EnhancedAnalyticsPage from "@/features/analytics/components/enhanced-analytics-page";

export const metadata: Metadata = {
  title: "Analytics Dashboard",
  description: "View usage analytics and system performance metrics",
};

export default function Page() {
  return <EnhancedAnalyticsPage />;
}