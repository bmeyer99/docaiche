// src/components/configuration/GlobalSaveBar.tsx
import React, { useEffect, useRef, useState, lazy, Suspense } from "react";
import { Button } from "../ui/Button";
import LoadingSpinner from "../ui/LoadingSpinner";
import { Logger } from "../../utils/logger";

// Lazy-load ConfirmationModal for bundle/code splitting
const ConfirmationModal = lazy(() => import("./ConfirmationModal"));

// Utility to sanitize dynamic text (basic, for XSS prevention)
function sanitize(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

interface GlobalSaveBarProps {
  isDirty: boolean;
  isValid: boolean;
  errors: Record<string, string>;
  saveState: "idle" | "saving" | "success" | "error";
  saveError?: string | null;
  saveConfiguration: () => Promise<boolean | void>;
  revertChanges: () => void;
  correlationId: string;
}

export const GlobalSaveBar: React.FC<GlobalSaveBarProps> = ({
  isDirty,
  isValid,
  errors,
  saveState,
  saveError,
  saveConfiguration,
  revertChanges,
  correlationId,
}) => {
  const [show, setShow] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [focusSet, setFocusSet] = useState(false);
  const barRef = useRef<HTMLDivElement>(null);
  const liveRegionRef = useRef<HTMLDivElement>(null);

  // Accessibility: Announce state changes
  useEffect(() => {
    if (isDirty) {
      setShow(true);
      Logger.info("Save bar appeared", {
        category: "user",
        correlationId,
        action: "save_bar_appear",
      });
    } else {
      setShow(false);
      setFocusSet(false);
      Logger.info("Save bar disappeared", {
        category: "user",
        correlationId,
        action: "save_bar_disappear",
      });
    }
  }, [isDirty, correlationId]);

  // Focus management: Focus bar when it appears (but don't trap)
  useEffect(() => {
    if (show && !focusSet && barRef.current) {
      barRef.current.focus();
      setFocusSet(true);
    }
  }, [show, focusSet]);

  // Show success state briefly after save
  useEffect(() => {
    if (saveState === "success") {
      setShowSuccess(true);
      if (liveRegionRef.current) {
        liveRegionRef.current.textContent = "All changes saved.";
      }
      const timeout = setTimeout(() => {
        setShowSuccess(false);
      }, 1200);
      return () => clearTimeout(timeout);
    }
    if (saveState === "idle") {
      setShowSuccess(false);
    }
  }, [saveState]);

  // Logging for save/revert actions
  const handleSave = async () => {
    Logger.info("Save button clicked", {
      category: "user",
      correlationId,
      action: "save_attempt",
    });
    await saveConfiguration();
  };

  const handleRevert = () => {
    setShowConfirm(true);
  };

  const handleConfirmRevert = () => {
    Logger.info("Revert confirmed", {
      category: "user",
      correlationId,
      action: "revert_confirmed",
    });
    setShowConfirm(false);
    revertChanges();
  };

  const handleCancelRevert = () => {
    setShowConfirm(false);
  };

  // Dynamic content logic
  let barMessage = "You have unsaved changes.";
  if (!isValid && isDirty) {
    const count = Object.keys(errors).length;
    barMessage = `Please fix ${count} error${count !== 1 ? "s" : ""} before saving.`;
  } else if (saveState === "saving") {
    barMessage = "Saving...";
  } else if (showSuccess) {
    barMessage = "All changes saved.";
  } else if (saveState === "error" && saveError) {
    barMessage = sanitize(saveError);
  }

  // Security: Prevent clickjacking (UI redressing)
  useEffect(() => {
    if (show) {
      document.body.style.pointerEvents = "auto";
    }
    return () => {
      document.body.style.pointerEvents = "";
    };
  }, [show]);

  // Hide bar visually when not shown
  if (!show && !showSuccess) return null;

  return (
    <>
      <div
        ref={barRef}
        tabIndex={-1}
        aria-live="polite"
        aria-label="Save bar"
        className={`fixed left-0 right-0 bottom-0 z-50 flex items-center justify-between px-6 py-3 bg-white border-t border-gray-200 shadow-lg transition-transform duration-200 ease-in-out
          ${show || showSuccess ? "translate-y-0" : "translate-y-full"}
        `}
        style={{
          minHeight: 64,
          outline: "none",
          boxShadow: "0 -2px 16px rgba(0,0,0,0.08)",
        }}
        role="region"
      >
        {/* Visually hidden live region for screen readers */}
        <div
          ref={liveRegionRef}
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {barMessage}
        </div>
        <span className="text-base font-medium text-gray-900" id="save-bar-message">
          {sanitize(barMessage)}
          {saveState === "saving" && (
            <span className="ml-2 align-middle">
              <LoadingSpinner size="sm" />
            </span>
          )}
        </span>
        <div className="flex gap-3">
          <Button
            variant="primary"
            size="md"
            disabled={!isValid || saveState === "saving"}
            loading={saveState === "saving"}
            onClick={handleSave}
            aria-disabled={!isValid || saveState === "saving"}
            aria-label="Save changes"
          >
            Save Changes
          </Button>
          <Button
            variant="secondary"
            size="md"
            disabled={saveState === "saving"}
            onClick={handleRevert}
            aria-label="Revert all changes"
          >
            Revert All
          </Button>
        </div>
      </div>
      <Suspense fallback={null}>
        <ConfirmationModal
          isOpen={showConfirm}
          onClose={handleCancelRevert}
          onConfirm={handleConfirmRevert}
          title="Revert All Changes?"
          message="Are you sure you want to revert all unsaved changes? This action cannot be undone."
          confirmText="Revert"
          cancelText="Cancel"
          variant="danger"
        />
      </Suspense>
      <style>
        {`
        .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0,0,0,0);
          border: 0;
        }
        .fixed[aria-label="Save bar"] {
          animation: slideUpSaveBar 0.2s cubic-bezier(0.4,0,0.2,1);
        }
        @keyframes slideUpSaveBar {
          from { transform: translateY(100%);}
          to { transform: translateY(0);}
        }
        `}
      </style>
    </>
  );
};

export default GlobalSaveBar;