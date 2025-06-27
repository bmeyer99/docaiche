import { Metadata } from "next";
import AnalyticsPage from "@/features/analytics/components/analytics-page";

export const metadata: Metadata = {
  title: "Analytics Dashboard",
  description: "View usage analytics and system performance metrics",
};

export default function Page() {
  return <AnalyticsPage />;
}