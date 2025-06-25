// src/styles/componentClasses.ts
export const componentClasses = {
  // Button variants
  buttonPrimary: "bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md font-medium transition-colors duration-200 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
  buttonSecondary: "bg-white hover:bg-neutral-50 text-neutral-700 border border-neutral-300 px-4 py-2 rounded-md font-medium transition-colors duration-200 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
  buttonDestructive: "bg-status-error hover:bg-red-600 text-white px-4 py-2 rounded-md font-medium transition-colors duration-200 focus:ring-2 focus:ring-red-500 focus:ring-offset-2",

  // Form controls
  input: "w-full px-3 py-2 border border-border-default rounded-md bg-surface-primary text-text-primary placeholder-text-tertiary focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-colors duration-200",
  inputError: "w-full px-3 py-2 border border-status-error rounded-md bg-surface-primary text-text-primary placeholder-text-tertiary focus:border-status-error focus:ring-1 focus:ring-status-error transition-colors duration-200",
  select: "w-full px-3 py-2 border border-border-default rounded-md bg-surface-primary text-text-primary focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-colors duration-200",
  label: "block text-sm font-medium text-text-secondary mb-1",
  errorText: "text-sm text-status-error mt-1",
  helperText: "text-sm text-text-tertiary mt-1",

  // Layout components
  card: "bg-surface-primary border border-border-light rounded-lg p-6 shadow-sm",
  pageContainer: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
  formGroup: "space-y-1",
  formRow: "grid grid-cols-1 md:grid-cols-2 gap-4",

  // Status indicators
  statusConnected: "flex items-center text-status-success",
  statusTesting: "flex items-center text-status-info",
  statusFailed: "flex items-center text-status-error",

  // Tab system
  primaryTabs: "border-b border-border-light",
  primaryTab: "px-4 py-2 text-sm font-medium text-text-tertiary hover:text-text-secondary border-b-2 border-transparent hover:border-border-default transition-colors duration-200",
  primaryTabActive: "px-4 py-2 text-sm font-medium text-primary-600 border-b-2 border-primary-600",
  mobileTabSelect: "w-full px-3 py-2 border border-border-default rounded-md bg-surface-primary text-text-primary focus:border-primary-500 focus:ring-1 focus:ring-primary-500 md:hidden",
  
  secondaryTabs: "border-b border-border-light bg-surface-secondary",
  secondaryTab: "px-4 py-2 text-sm font-medium text-text-tertiary hover:text-text-secondary border-b-2 border-transparent hover:border-border-default transition-colors duration-200",
  secondaryTabActive: "px-4 py-2 text-sm font-medium text-primary-600 border-b-2 border-primary-600",

  // Toggle switch
  toggle: "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
  toggleActive: "bg-primary-600",
  toggleInactive: "bg-neutral-200",
  toggleButton: "inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200",
  toggleButtonActive: "translate-x-6",
  toggleButtonInactive: "translate-x-1",
  toggleContainer: "flex items-center space-x-3",

  // Advanced settings toggle
  advancedToggle: "flex items-center space-x-2 text-sm font-medium text-text-secondary hover:text-text-primary cursor-pointer transition-colors duration-200",
  advancedContent: "mt-4 space-y-4 overflow-hidden transition-all duration-200 ease-in-out",

  // Global save bar
  saveBar: "fixed bottom-0 left-0 right-0 bg-surface-primary border-t border-border-light shadow-lg z-40 transform transition-transform duration-200 ease-in-out",
  saveBarContent: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between",
  saveBarText: "text-sm font-medium text-text-secondary",
  saveBarActions: "flex items-center space-x-3",
};
// Typography system
// Inter font assumed loaded globally via Tailwind config or index.html
export const typographyClasses = {
  heading1: "font-sans font-bold text-3xl leading-tight text-text-primary",
  heading2: "font-sans font-semibold text-2xl leading-snug text-text-primary",
  heading3: "font-sans font-semibold text-xl leading-snug text-text-primary",
  body: "font-sans text-base text-text-primary",
  bodySecondary: "font-sans text-base text-text-secondary",
  caption: "font-sans text-xs text-text-tertiary",
};