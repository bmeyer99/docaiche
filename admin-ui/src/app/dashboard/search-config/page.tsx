import { Metadata } from "next";
import { SearchConfigLayout } from "@/features/search-config";

export const metadata: Metadata = {
  title: "Search Configuration | Admin",
  description: "Configure and manage the MCP search system",
};

export default function SearchConfigPage() {
  return <SearchConfigLayout />;
}