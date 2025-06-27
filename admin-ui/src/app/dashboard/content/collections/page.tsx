import { Metadata } from "next";
import CollectionsPage from "@/features/content/components/collections-page";

export const metadata: Metadata = {
  title: "Collections Management",
  description: "Manage document collections and organize content",
};

export default function Page() {
  return <CollectionsPage />;
}