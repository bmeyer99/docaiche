// src/web_ui/static/web/src/components/configuration/EmbeddingTab.tsx

import React, { memo, useState, useRef } from "react";
import ToggleSwitch from "../ui/ToggleSwitch";
import { ProviderConfigCard } from "./ProviderConfigCard";
import { Logger } from "../../utils/logger";
import type { EmbeddingProviderConfig, ProviderConfig } from "../../types/configuration";

interface EmbeddingTabProps {
  tabId: string;
  isActive: boolean;
  correlationId?: string;
  initialConfig?: EmbeddingProviderConfig;
  textGenConfig?: ProviderConfig;
  onConfigChange?: (config: EmbeddingProviderConfig) => void;
}

const validateTabProps = (props: EmbeddingTabProps): boolean => {
  return (
    props.tabId === "embedding" &&
    typeof props.isActive === "boolean"
  );
};

const EMBEDDING_FORM_ID = "embedding-provider-form-section";

const EmbeddingTab: React.FC<EmbeddingTabProps> = memo((props) => {
  if (!validateTabProps(props)) {
    Logger.error("Invalid tab properties detected", {
      category: "validation",
      correlationId: props.correlationId,
    });
    return (
      <div role="alert" aria-live="assertive" className="text-red-600">
        Invalid tab properties detected.
      </div>
    );
  }

  // State
  const [useTextGenConfig, setUseTextGenConfig] = useState<boolean>(
    props.initialConfig?.use_text_generation_config ?? false
  );
  const [embeddingConfig, setEmbeddingConfig] = useState<EmbeddingProviderConfig>(
    props.initialConfig ?? { use_text_generation_config: false }
  );
  const [dirty, setDirty] = useState(false);
  const announceRef = useRef<HTMLDivElement>(null);

  // Toggle handler with logging and state validation
  const handleToggle = (checked: boolean) => {
    setUseTextGenConfig(checked);
    setDirty(true);
    const newConfig: EmbeddingProviderConfig = {
      ...embeddingConfig,
      use_text_generation_config: checked,
    };
    if (checked) {
      // Clear provider-specific fields for security
      newConfig.provider = undefined;
      newConfig.baseUrl = undefined;
      newConfig.apiKey = undefined;
      newConfig.model = undefined;
      if (announceRef.current) {
        announceRef.current.textContent = "Embedding provider now using text generation settings";
      }
      Logger.info("Embedding provider set to use text generation config", {
        category: "state",
        correlationId: props.correlationId,
      });
    } else {
      if (announceRef.current) {
        announceRef.current.textContent = "Embedding provider custom configuration enabled";
      }
      Logger.info("Embedding provider custom config enabled", {
        category: "state",
        correlationId: props.correlationId,
      });
    }
    setEmbeddingConfig(newConfig);
    props.onConfigChange?.(newConfig);
  };

  // Provider config change handler
  const handleProviderConfigChange = (cfg: EmbeddingProviderConfig) => {
    setEmbeddingConfig(cfg);
    setDirty(true);
    props.onConfigChange?.(cfg);
  };

  return (
    <section aria-labelledby="embedding-heading">
      <h2 id="embedding-heading" className="text-lg font-semibold mb-2">
        Configuration for the embedding provider
      </h2>
      <div className="bg-surface-secondary p-4 rounded-md">
        <ToggleSwitch
          checked={useTextGenConfig}
          onChange={handleToggle}
          id="use-text-gen-config-toggle"
          ariaControls={EMBEDDING_FORM_ID}
          label="Use Text Generation Provider settings"
        />
        <div
          ref={announceRef}
          aria-live="polite"
          aria-atomic="true"
          style={{ position: "absolute", left: -9999, height: 1, width: 1, overflow: "hidden" }}
        />
        <div id={EMBEDDING_FORM_ID} className="mt-4">
          {useTextGenConfig ? (
            <div className="p-3 bg-gray-100 rounded text-gray-700" aria-readonly="true">
              Embedding provider settings are inherited from the text generation provider and cannot be edited.
            </div>
          ) : (
            <ProviderConfigCard
              value={{
                provider: embeddingConfig.provider ?? "ollama",
                baseUrl: embeddingConfig.baseUrl ?? "",
                apiKey: embeddingConfig.apiKey ?? "",
                model: embeddingConfig.model ?? "",
                settings: { temperature: 0, maxTokens: 0 },
              }}
              onChange={(val) =>
                handleProviderConfigChange({
                  ...embeddingConfig,
                  ...val,
                  use_text_generation_config: false,
                })
              }
              disabled={useTextGenConfig}
            />
          )}
        </div>
      </div>
    </section>
  );
});

EmbeddingTab.displayName = "EmbeddingTab";

export default EmbeddingTab;