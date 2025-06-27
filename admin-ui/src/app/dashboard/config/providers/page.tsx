import { Metadata } from "next";
import ProvidersConfigPage from "@/features/config/components/providers-config-page";

export const metadata: Metadata = {
  title: "AI Providers Configuration",
  description: "Configure and manage AI providers for the Docaiche system",
};

export default function Page() {
  return <ProvidersConfigPage />;
}