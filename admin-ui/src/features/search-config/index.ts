/**
 * Search Configuration Feature
 * 
 * Exports all components and types for the search configuration admin UI
 */

// Main layout
export { SearchConfigLayout } from './components/search-config-layout';

// Tab components
export { SearchConfigDashboard } from './components/tabs/dashboard';
export { VectorSearchConfig } from './components/tabs/vector-search';
export { TextAIConfig } from './components/tabs/text-ai';
export { IngestionConfig } from './components/tabs/ingestion';
export { MonitoringConfig } from './components/tabs/monitoring';
export { SystemSettings } from './components/tabs/settings';

// Shared components
export { MetricCard } from './components/shared/metric-card';
export { HealthIndicator } from './components/shared/health-indicator';
export { ProviderCard } from './components/shared/provider-card';
export { ConfigurationForm } from './components/shared/configuration-form';

// System Prompts Manager
export { SystemPromptsManager } from './components/system-prompts-manager';
export type { SystemPrompt, SystemPromptsResponse } from './components/system-prompts-manager';

// Hooks
export * from './hooks/use-search-config-websocket';

// Types
export * from './types';

// Utils (if any)
// export * from './utils';