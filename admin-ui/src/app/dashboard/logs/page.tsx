import { Metadata } from "next";
import LogsViewer from "@/features/monitoring/components/logs-viewer";

export const metadata: Metadata = {
  title: "Logs | DocAIche Admin",
  description: "View and search system logs",
};

export default function LogsPage() {
  return <LogsViewer />;
}