import { useEffect } from "react";
import { Logger } from "../../utils/logger";

/**
 * AccessibilityEventListener
 * - Logs high-contrast mode activation/deactivation
 * - Logs significant keyboard navigation patterns
 * Mount this component once at the app root.
 */
const AccessibilityEventListener = () => {
  useEffect(() => {
    // High-contrast mode detection (forced-colors media query)
    const logHighContrast = (enabled: boolean) => {
      Logger.info(
        enabled
          ? "High-contrast mode activated"
          : "High-contrast mode deactivated",
        {
          category: "user",
          component: "AccessibilityEventListener",
          event: "high-contrast",
          enabled,
        }
      );
    };

    const match = window.matchMedia("(forced-colors: active)");
    const handleContrastChange = (e: MediaQueryListEvent) => {
      logHighContrast(e.matches);
    };
    // Initial log
    logHighContrast(match.matches);
    match.addEventListener("change", handleContrastChange);

    // Keyboard navigation logging
    let tabCount = 0;
    let arrowCount = 0;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Tab") {
        tabCount++;
        if (tabCount === 1) {
          Logger.info("Keyboard navigation started (Tab key)", {
            category: "user",
            component: "AccessibilityEventListener",
            event: "keyboard-nav-start",
          });
        }
        if (tabCount % 10 === 0) {
          Logger.debug("High Tab navigation count", {
            category: "user",
            component: "AccessibilityEventListener",
            event: "keyboard-nav-tab-milestone",
            count: tabCount,
          });
        }
      }
      if (
        e.key === "ArrowUp" ||
        e.key === "ArrowDown" ||
        e.key === "ArrowLeft" ||
        e.key === "ArrowRight"
      ) {
        arrowCount++;
        if (arrowCount === 1) {
          Logger.info("Keyboard navigation started (Arrow keys)", {
            category: "user",
            component: "AccessibilityEventListener",
            event: "keyboard-nav-arrow-start",
          });
        }
        if (arrowCount % 10 === 0) {
          Logger.debug("High Arrow navigation count", {
            category: "user",
            component: "AccessibilityEventListener",
            event: "keyboard-nav-arrow-milestone",
            count: arrowCount,
          });
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      match.removeEventListener("change", handleContrastChange);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return null;
};

export default AccessibilityEventListener;