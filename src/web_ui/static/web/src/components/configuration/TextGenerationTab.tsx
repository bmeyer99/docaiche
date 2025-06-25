// src/web_ui/static/web/src/components/configuration/TextGenerationTab.tsx

import React, { memo } from "react";

interface TextGenerationTabProps {
  tabId: string;
  isActive: boolean;
}

const validateTabProps = (props: TextGenerationTabProps): boolean => {
  return (
    props.tabId === "text-generation" &&
    typeof props.isActive === "boolean"
  );
};

const TextGenerationTab: React.FC<TextGenerationTabProps> = memo((props) => {
  if (!validateTabProps(props)) {
    // Security logging can be added here
    return (
      <div role="alert" aria-live="assertive" className="text-red-600">
        Invalid tab properties detected.
      </div>
    );
  }

  // Placeholder for provider configuration form
  return (
    <section aria-labelledby="text-generation-heading">
      <h2 id="text-generation-heading" className="text-lg font-semibold mb-2">
        Configuration for the primary text generation provider
      </h2>
      <div className="bg-surface-secondary p-4 rounded-md">
        <p className="text-text-secondary">
          Configure your main text generation provider here. (Form coming soon)
        </p>
      </div>
    </section>
  );
});

TextGenerationTab.displayName = "TextGenerationTab";

export default TextGenerationTab;