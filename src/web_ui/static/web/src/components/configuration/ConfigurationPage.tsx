import React, { useState } from "react";
import { PageContainer } from "../layout/PageContainer";
import { PageHeader } from "../layout/PageHeader";
import { Tabs } from "../ui/Tabs";
import { LLMProvidersTab } from "./LLMProvidersTab";
import { GeneralSettingsTab } from "./GeneralSettingsTab";
import { ConnectionSettingsTab } from "./ConnectionSettingsTab";
import { CacheSettingsTab } from "./CacheSettingsTab";
import { AdvancedSettingsTab } from "./AdvancedSettingsTab";
import componentClasses from "../../styles/componentClasses";

export interface ConfigurationPageProps {
  className?: string;
}

const tabs = [
  {
    id: "llm-providers",
    label: "LLM Providers",
    content: <LLMProvidersTab />
  },
  {
    id: "general-settings",
    label: "General Settings",
    content: <GeneralSettingsTab />
  },
  {
    id: "connection-settings",
    label: "Connection Settings",
    content: <ConnectionSettingsTab />
  },
  {
    id: "cache-settings",
    label: "Cache Settings",
    content: <CacheSettingsTab />
  },
  {
    id: "advanced-settings",
    label: "Advanced Settings",
    content: <AdvancedSettingsTab />
  }
];

export const ConfigurationPage: React.FC<ConfigurationPageProps> = ({ className }) => {
  const [activeTab, setActiveTab] = useState<string>("llm-providers");

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
  };

  const activeTabContent = tabs.find(tab => tab.id === activeTab)?.content;

  return (
    <PageContainer className={className}>
      <PageHeader title="System Configuration" />
      <Tabs
        tabs={tabs.map(({ id, label }) => ({ id, label }))}
        activeTab={activeTab}
        onTabChange={handleTabChange}
        variant="primary"
        className={componentClasses.tabs}
      />
      <div className={componentClasses.tabPanel} role="tabpanel" tabIndex={0}>
        {activeTabContent}
      </div>
    </PageContainer>
  );
};