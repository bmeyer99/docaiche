import { Metadata } from "next";
import ContentUploadPage from "@/features/content/components/content-upload-page";

export const metadata: Metadata = {
  title: "Upload Content | Docaiche Admin",
  description: "Upload documents to your knowledge base",
};

export default function Page() {
  return <ContentUploadPage />;
}