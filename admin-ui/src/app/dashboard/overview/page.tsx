import { Metadata } from "next";
import OverviewPage from "@/features/overview/components/overview-page";

export const metadata: Metadata = {
  title: "Dashboard Overview",
  description: "Comprehensive overview of the Docaiche system status and activity",
};

export default function Page() {
  return <OverviewPage />;
}