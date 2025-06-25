import React, { useCallback, useMemo, useRef, useState, Suspense, lazy } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet';
import DOMPurify from 'dompurify';

// Lazy-load configuration tabs for bundle/code splitting
const LLMProvidersTab = lazy(() => import('./LLMProvidersTab'));
const GeneralSettingsTab = lazy(() => import('./GeneralSettingsTab'));
const ConnectionSettingsTab = lazy(() => import('./ConnectionSettingsTab'));
const CacheSettingsTab = lazy(() => import('./CacheSettingsTab'));
const AdvancedSettingsTab = lazy(() => import('./AdvancedSettingsTab'));

import { logEvent } from '../../utils/logger';
import styles from './ConfigurationPage.module.css';

// UUID generator for correlationId if not provided
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0,
      v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

interface TabConfig {
  id: TabId;
  label: string;
  component: React.ComponentType;
}

type TabId =
  | 'llm-providers'
  | 'general-settings'
  | 'connection-settings'
  | 'cache-settings'
  | 'advanced-settings';

const TABS: TabConfig[] = [
  {
    id: 'llm-providers',
    label: 'LLM Providers',
    component: LLMProvidersTab,
  },
  {
    id: 'general-settings',
    label: 'General Settings',
    component: GeneralSettingsTab,
  },
  {
    id: 'connection-settings',
    label: 'Connection Settings',
    component: ConnectionSettingsTab,
  },
  {
    id: 'cache-settings',
    label: 'Cache Settings',
    component: CacheSettingsTab,
  },
  {
    id: 'advanced-settings',
    label: 'Advanced Settings',
    component: AdvancedSettingsTab,
  },
];

const ALLOWED_TAB_IDS: TabId[] = TABS.map((tab) => tab.id);

function validateTabId(tabId: string): tabId is TabId {
  return ALLOWED_TAB_IDS.includes(tabId as TabId);
}

function sanitizeHtml(input: string): string {
  return DOMPurify.sanitize(input, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
}

const ConfigurationPage: React.FC = React.memo(() => {
  const location = useLocation();
  const navigate = useNavigate();
  const tabListRef = useRef<HTMLDivElement>(null);

  // Parse tab from URL (e.g., /configuration/:tabId)
  const urlTabId = useMemo(() => {
    const match = location.pathname.match(/\/configuration\/([a-z-]+)/);
    return match && validateTabId(match[1]) ? (match[1] as TabId) : 'llm-providers';
  }, [location.pathname]);

  const [activeTab, setActiveTab] = useState<TabId>(urlTabId);

  // Keep state in sync with URL
  React.useEffect(() => {
    if (activeTab !== urlTabId) setActiveTab(urlTabId);
  }, [urlTabId, activeTab]);

  // Log tab changes
  const handleTabChange = useCallback(
    (tabId: TabId) => {
      if (!validateTabId(tabId)) return;
      setActiveTab(tabId);
      navigate(`/configuration/${tabId}`, { replace: true });
      logEvent('tab_change', { tab: tabId });
    },
    [navigate]
  );

  // Keyboard navigation for tabs
  const handleKeyboardNavigation = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, tabId: TabId) => {
      const idx = TABS.findIndex((tab) => tab.id === tabId);
      if (idx === -1) return;
      let nextIdx = idx;
      if (e.key === 'ArrowRight') nextIdx = (idx + 1) % TABS.length;
      if (e.key === 'ArrowLeft') nextIdx = (idx - 1 + TABS.length) % TABS.length;
      if (e.key === 'Home') nextIdx = 0;
      if (e.key === 'End') nextIdx = TABS.length - 1;
      if (nextIdx !== idx) {
        e.preventDefault();
        handleTabChange(TABS[nextIdx].id);
        // Move focus to new tab
        const tabButtons = tabListRef.current?.querySelectorAll<HTMLButtonElement>('button[role="tab"]');
        tabButtons?.[nextIdx]?.focus();
      }
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleTabChange(tabId);
      }
    },
    [handleTabChange]
  );

  // Responsive: show dropdown on mobile, tabs on desktop/tablet
  const [isMobile, setIsMobile] = React.useState(false);

  // CorrelationId for logging
  const [correlationId] = React.useState(() => generateUUID());

  // Track last breakpoint for logging
  const lastBreakpoint = React.useRef<string>('');

  React.useEffect(() => {
    function getBreakpoint(width: number) {
      if (width < 768) return 'mobile';
      if (width < 1200) return 'tablet';
      return 'desktop';
    }

    const checkBreakpoint = () => {
      const width = window.innerWidth;
      const breakpoint = getBreakpoint(width);
      setIsMobile(width < 768);

      if (lastBreakpoint.current !== breakpoint) {
        logEvent('breakpoint_change', {
          breakpoint,
          correlationId,
        });
        lastBreakpoint.current = breakpoint;
      }
    };

    checkBreakpoint();
    window.addEventListener('resize', checkBreakpoint);
    return () => window.removeEventListener('resize', checkBreakpoint);
  }, [correlationId]);

  // Error boundary for tab content
  const [tabError, setTabError] = React.useState<Error | null>(null);

  const ActiveTabComponent = useMemo(() => {
    const found = TABS.find((tab) => tab.id === activeTab);
    return found ? found.component : LLMProvidersTab;
  }, [activeTab]);

  // Accessibility: announce tab changes
  const [ariaAnnouncement, setAriaAnnouncement] = React.useState('');
  React.useEffect(() => {
    const found = TABS.find((tab) => tab.id === activeTab);
    if (found) setAriaAnnouncement(`${found.label} tab selected`);
  }, [activeTab]);

  // Render
  return (
    <div className={styles['configuration-page']} data-testid="configuration-page">
      <Helmet>
        <title>System Configuration</title>
      </Helmet>
      <h1 className={styles['page-title']} tabIndex={-1}>
        {sanitizeHtml('System Configuration')}
      </h1>
      <div aria-live="polite" className={styles['sr-only']} role="status">
        {ariaAnnouncement}
      </div>
      <nav
        className={isMobile ? styles.mobileTabSelect : styles.primaryTabs}
        aria-label="Configuration sections"
      >
        {isMobile ? (
          <label htmlFor="tab-select" className={styles['sr-only']}>
            Select configuration section
          </label>
        ) : null}
        {isMobile ? (
          <select
            id="tab-select"
            value={activeTab}
            onChange={(e) => {
              const tabId = e.target.value;
              if (validateTabId(tabId)) handleTabChange(tabId);
            }}
            aria-label="Select configuration section"
            style={{ minHeight: 44 }}
          >
            {TABS.map((tab) => (
              <option key={tab.id} value={tab.id}>
                {sanitizeHtml(tab.label)}
              </option>
            ))}
          </select>
        ) : (
          <div
            role="tablist"
            aria-label="Configuration sections"
            ref={tabListRef}
            className={styles.tablist}
          >
            {TABS.map((tab, idx) => (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`panel-${tab.id}`}
                tabIndex={activeTab === tab.id ? 0 : -1}
                className={`tab-btn${activeTab === tab.id ? ' active' : ''}`}
                onClick={() => handleTabChange(tab.id)}
                onKeyDown={(e) => handleKeyboardNavigation(e, tab.id)}
                style={{ minWidth: 44, minHeight: 44 }}
                type="button"
                dangerouslySetInnerHTML={{
                  __html: sanitizeHtml(tab.label),
                }}
              />
            ))}
          </div>
        )}
      </nav>
      <section
        id={`panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        tabIndex={0}
        className={styles.tabPanel}
      >
        {tabError ? (
          <div className={styles.tabError} role="alert">
            <span>Error loading tab: {sanitizeHtml(tabError.message)}</span>
          </div>
        ) : (
          <Suspense fallback={<div className={styles.skeletonCard}><div className={styles.skeletonHeader} /><div className={styles.skeletonContent} /></div>}>
            <ErrorBoundary onError={setTabError}>
              <ActiveTabComponent />
            </ErrorBoundary>
          </Suspense>
        )}
      </section>
    </div>
  );
});

interface ErrorBoundaryProps {
  onError: (error: Error) => void;
  children: React.ReactNode;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, { hasError: boolean }> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error: Error) {
    this.props.onError(error);
    logEvent('tab_error', { error: error.message });
  }
  render() {
    if (this.state.hasError) return null;
    return this.props.children;
  }
}

export default ConfigurationPage;