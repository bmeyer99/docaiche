import { Metadata } from "next";
import ContentSearchPage from "@/features/content/components/content-search-page";

export const metadata: Metadata = {
  title: "Content Search",
  description: "Search and manage indexed documents and content",
};

export default function Page() {
  return <ContentSearchPage />;
}