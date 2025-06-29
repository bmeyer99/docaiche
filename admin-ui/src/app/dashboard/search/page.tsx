import { Metadata } from "next";
import ContentSearchPage from "@/features/content/components/content-search-page";

export const metadata: Metadata = {
  title: "Search Documents",
  description: "AI-powered search across all your documentation",
};

export default function Page() {
  return <ContentSearchPage />;
}