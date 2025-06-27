import { Metadata } from "next";
import ContentUploadPage from "@/features/content/components/content-upload-page";

export const metadata: Metadata = {
  title: "Upload Content",
  description: "Upload and index new documents and files",
};

export default function Page() {
  return <ContentUploadPage />;
}