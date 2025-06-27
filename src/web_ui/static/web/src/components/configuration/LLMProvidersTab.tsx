// src/web_ui/static/web/src/components/configuration/LLMProvidersTab.tsx

import React, { useCallback, useMemo, useState } from "react";
import { Card } from "../ui/Card";
import Tabs from "../ui/Tabs";
import TextGenerationTab from "./TextGenerationTab";
import EmbeddingTab from "./EmbeddingTab";

// XSS prevention: dynamic import for DOMPurify (fallback to identity if not installed)
let DOMPurify: { sanitize: (input: string) => string } | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  DOMPurify = require("dompurify");
} catch {
  DOMPurify = null;
}
const sanitize = (input: string) =>
  DOMPurify ? DOMPurify.sanitize(input) : input;

// Security: allowed tab IDs and secure labels
const ALLOWED_SECONDARY_TABS = ["text-generation", "embedding"] as const;
const SECURE_TAB_LABELS: Record<typeof ALLOWED_SECONDARY_TABS[number], string> = {
  "text-generation": "Text Generation",
  embedding: "Embedding",
};
const getSecureTabLabel = (tabId: string): string =>
  SECURE_TAB_LABELS[tabId as keyof typeof SECURE_TAB_LABELS] || "";

// Security: validate tab ID
const validateSecondaryTabId = (tabId: string): boolean =>
  ALLOWED_SECONDARY_TABS.includes(tabId as any);

export interface LLMProvidersTabProps {
  className?: string;
}

export const LLMProvidersTab: React.FC<LLMProvidersTabProps> = React.memo(
  ({ className }) => {
    // State isolation for secondary tabs
    const [activeTab, setActiveTab] = useState<string>("text-generation");

    // Security: validate and set tab
    const handleTabChange = useCallback(
      (tabId: string) => {
        if (!validateSecondaryTabId(tabId)) {
          // Security logging (replace with real logger)
          if (window && window.console) {
            window.console.warn("Blocked unauthorized tab access:", tabId);
          }
          return;
        }
        setActiveTab(tabId);
      },
      []
    );

    // Memoized tab definitions
    const secondaryTabs = useMemo(
      () =>
        ALLOWED_SECONDARY_TABS.map((tabId) => ({
          id: tabId,
          label: sanitize(getSecureTabLabel(tabId)),
          content:
            tabId === "text-generation" ? (
              <TextGenerationTab tabId={tabId} isActive={activeTab === tabId} />
            ) : (
              <EmbeddingTab tabId={tabId} isActive={activeTab === tabId} />
            ),
        })),
      [activeTab]
    );

    return (
      <Card className={className}>
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              LLM Providers Configuration
            </h3>
            <p className="text-text-secondary mb-4">
              Configure language model providers for text generation and embedding services.
              Set up API connections to Ollama, OpenAI, or custom LLM endpoints.
            </p>
          </div>
          <Tabs
            tabs={secondaryTabs}
            activeTab={activeTab}
            onTabChange={handleTabChange}
            variant="secondary"
            className="mb-4"
          />
        </div>
      </Card>
    );
  }
);

LLMProvidersTab.displayName = "LLMProvidersTab";

export default LLMProvidersTab;