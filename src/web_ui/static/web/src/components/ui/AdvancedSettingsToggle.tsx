// src/web_ui/static/web/src/components/ui/AdvancedSettingsToggle.tsx

import React, { useRef, useState, useEffect, useCallback } from "react";
import { Icon } from "./Icon";
import { componentClasses } from "../../styles/componentClasses";
import { Logger } from "../../utils/logger";

interface AdvancedSettingsToggleProps {
  providerType: string;
  correlationId: string;
  initialOpen?: boolean;
  children: React.ReactNode;
  label?: string;
  className?: string;
}

const getSessionKey = (providerType: string) =>
  `advancedSettings_${providerType}`;

const validateSessionValue = (value: unknown): boolean =>
  value === "true" || value === "false";

/**
 * AdvancedSettingsToggle
 * - Secure, accessible, animated toggle for advanced settings sections.
 * - Persists state in sessionStorage with validation.
 * - Logs all toggle actions with correlationId and providerType.
 */
export const AdvancedSettingsToggle: React.FC<AdvancedSettingsToggleProps> = ({
  providerType,
  correlationId,
  initialOpen: _initialOpen = false,
  children,
  label = "Show advanced settings",
  className = "",
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState<boolean>(false);
  const [maxHeight, setMaxHeight] = useState<string>("0px");
  const [animating, setAnimating] = useState(false);

  // Securely initialize state from sessionStorage
  useEffect(() => {
    const key = getSessionKey(providerType);
    const stored = sessionStorage.getItem(key);
    if (validateSessionValue(stored)) {
      setOpen(stored === "true");
    } else {
      setOpen(false);
      sessionStorage.setItem(key, "false");
    }
  }, [providerType]);

  // Animate max-height on open/close
  useEffect(() => {
    if (!contentRef.current) return;
    setAnimating(true);
    if (open) {
      setMaxHeight(`${contentRef.current.scrollHeight}px`);
    } else {
      setMaxHeight("0px");
    }
    const timeout = setTimeout(() => setAnimating(false), 200);
    return () => clearTimeout(timeout);
  }, [open]);

  // Persist state securely
  useEffect(() => {
    const key = getSessionKey(providerType);
    sessionStorage.setItem(key, open ? "true" : "false");
  }, [open, providerType]);

  // Logging
  const logToggle = useCallback(
    (newState: boolean) => {
      Logger.info(
        `Advanced settings ${newState ? "opened" : "closed"}`,
        {
          category: "user",
          correlationId,
          providerType,
          action: "advanced_settings_toggle",
          newState,
        }
      );
    },
    [correlationId, providerType]
  );

  // Toggle handler
  const handleToggle = () => {
    setOpen((prev) => {
      const next = !prev;
      logToggle(next);
      return next;
    });
  };

  // ARIA
  const contentId = `advanced-settings-content-${providerType}`;

  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        className={`${componentClasses.advancedToggle} ${className}`}
        onClick={handleToggle}
        tabIndex={0}
      >
        <span>{label}</span>
        <span
          style={{
            transition: "transform 200ms ease-in-out",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            display: "inline-flex",
            alignItems: "center",
          }}
        >
          <Icon name="chevronDown" size="md" />
        </span>
      </button>
      <div
        id={contentId}
        ref={contentRef}
        className={componentClasses.advancedContent}
        style={{
          maxHeight,
          transition: "max-height 200ms ease-in-out",
          visibility: open || animating ? "visible" : "hidden",
          display: open || animating ? "block" : "none",
        }}
        aria-hidden={!open}
      >
        {open ? children : null}
      </div>
    </div>
  );
};