import { Metadata } from "next";
import WebSocketAnalyticsPage from "@/features/analytics/components/websocket-analytics-page";

export const metadata: Metadata = {
  title: "DocAIche Dashboard",
  description: "Real-time analytics and system performance monitoring",
};

export default function Page() {
  return <WebSocketAnalyticsPage />;
}