// src/web_ui/static/web/src/components/ui/ToggleSwitch.tsx

import React, { useEffect } from "react";
import { sanitizeAriaString } from "../../utils/sanitizeAriaString";
import { Logger } from "../../utils/logger";

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  id: string;
  ariaControls: string;
  disabled?: boolean;
  label?: string;
  className?: string;
}

function supportsCSSProperty(property: string): boolean {
  if (typeof window === "undefined" || !window.CSS || !window.CSS.supports) return false;
  return window.CSS.supports(property, "initial");
}

export const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  checked,
  onChange,
  id,
  ariaControls,
  disabled = false,
  label,
  className = "",
}) => {
  // Keyboard: Space/Enter toggles
  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      if (!disabled) onChange(!checked);
    }
  };

  // Log fallback if CSS property not supported (e.g., 'transition-property')
  useEffect(() => {
    const fallbackNeeded = !supportsCSSProperty("transition-property");
    if (fallbackNeeded) {
      Logger.warn("CSS fallback triggered: 'transition-property' not supported", {
        category: "compatibility",
        fallbackTriggered: true,
        component: "ToggleSwitch",
      });
    }
  }, []);

  return (
    <div className={`toggle-switch ${className}`}>
      <button
        type="button"
        id={id}
        role="switch"
        aria-checked={checked}
        aria-controls={sanitizeAriaString(ariaControls)}
        aria-label={sanitizeAriaString(label)}
        disabled={disabled}
        tabIndex={0}
        className={`inline-flex items-center px-3 py-1 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary ${checked ? "bg-primary" : "bg-gray-300"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        onClick={() => !disabled && onChange(!checked)}
        onKeyDown={handleKeyDown}
        data-testid="toggle-switch"
        style={{ minWidth: 44, minHeight: 44 }}
      >
        <span
          className={`w-5 h-5 bg-white rounded-full shadow transform transition-transform duration-200 ${checked ? "translate-x-5" : ""}`}
          aria-hidden="true"
        />
        <span className="ml-3 text-sm font-medium select-none">{label}</span>
      </button>
    </div>
  );
};

export default ToggleSwitch;