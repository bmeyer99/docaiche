import React, { useEffect, useRef } from "react";
import { componentClasses } from "../../styles/componentClasses";
import classNames from "classnames";

export interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
}

export interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  variant?: "primary" | "secondary";
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onTabChange,
  variant = "primary",
  className,
}) => {
  const tabListRef = useRef<HTMLDivElement>(null);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!tabListRef.current) return;
      const tabElements = Array.from(
        tabListRef.current.querySelectorAll('[role="tab"]')
      ) as HTMLElement[];
      const currentIdx = tabElements.findIndex(
        (el) => el.getAttribute("aria-selected") === "true"
      );
      if (currentIdx === -1) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        const nextIdx = (currentIdx + 1) % tabElements.length;
        tabElements[nextIdx].focus();
        onTabChange(tabs[nextIdx].id);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const prevIdx =
          (currentIdx - 1 + tabElements.length) % tabElements.length;
        tabElements[prevIdx].focus();
        onTabChange(tabs[prevIdx].id);
      }
    };
    const node = tabListRef.current;
    node?.addEventListener("keydown", handleKeyDown);
    return () => node?.removeEventListener("keydown", handleKeyDown);
  }, [tabs, onTabChange]);

  // Responsive: show dropdown on mobile, tabs on desktop
  return (
    <div className={className}>
      <div className="md:hidden">
        <select
          className={componentClasses.mobileTabSelect}
          value={activeTab}
          aria-label="Select tab"
          onChange={(e) => onTabChange(e.target.value)}
        >
          {tabs.map((tab) => (
            <option key={tab.id} value={tab.id}>
              {tab.label}
            </option>
          ))}
        </select>
      </div>
      <div
        className={classNames(
          "hidden md:flex",
          variant === "primary"
            ? componentClasses.primaryTabs
            : componentClasses.secondaryTabs
        )}
        role="tablist"
        aria-orientation="horizontal"
        ref={tabListRef}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            className={classNames(
              variant === "primary"
                ? activeTab === tab.id
                  ? componentClasses.primaryTabActive
                  : componentClasses.primaryTab
                : activeTab === tab.id
                ? componentClasses.secondaryTabActive
                : componentClasses.secondaryTab
            )}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onTabChange(tab.id);
              }
            }}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div>
        {tabs.map(
          (tab) =>
            tab.id === activeTab && (
              <div
                key={tab.id}
                id={`tabpanel-${tab.id}`}
                role="tabpanel"
                aria-labelledby={`tab-${tab.id}`}
                tabIndex={0}
                className="mt-4 transition-opacity duration-200"
              >
                {tab.content}
              </div>
            )
        )}
      </div>
    </div>
  );
};

export default Tabs;