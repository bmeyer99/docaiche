import { Metadata } from "next";
import WebSocketAnalyticsPage from "@/features/analytics/components/websocket-analytics-page";

export const metadata: Metadata = {
  title: "Real-time Analytics Dashboard",
  description: "Live analytics and system performance metrics via WebSocket",
};

export default function Page() {
  return <WebSocketAnalyticsPage />;
}