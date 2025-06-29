import { Metadata } from "next";
import CollectionsPage from "@/features/content/components/collections-page";

export const metadata: Metadata = {
  title: "Collections | Docaiche Admin",
  description: "Manage your document collections",
};

export default function Page() {
  return <CollectionsPage />;
}