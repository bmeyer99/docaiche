import { Metadata } from "next";
import SystemHealthPage from "@/features/health/components/system-health-page";

export const metadata: Metadata = {
  title: "System Health",
  description: "Monitor system health and service status in real-time",
};

export default function Page() {
  return <SystemHealthPage />;
}