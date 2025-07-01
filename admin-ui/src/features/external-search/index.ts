/**
 * External Search Feature Module
 * 
 * This module provides components and hooks for managing MCP external search providers.
 */

export { ExternalSearchLayout } from './components/external-search-layout';
export { MCPProvidersTab } from './components/tabs/mcp-providers';
export { MCPConfigTab } from './components/tabs/mcp-config';
export { MCPPerformanceTab } from './components/tabs/mcp-performance';
export { useMCPProviders } from './hooks/use-mcp-providers';
export { useMCPConfig } from './hooks/use-mcp-config';
export { useMCPStats } from './hooks/use-mcp-stats';