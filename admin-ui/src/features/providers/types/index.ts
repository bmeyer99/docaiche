// TypeScript interfaces and types for the providers feature

export type ProviderCategory = 'local' | 'cloud' | 'enterprise'

export type ProviderStatus = 'configured' | 'not_configured' | 'failed' | 'testing'

export type ModelType = 'text_generation' | 'embeddings'

export interface ProviderInfo {
  id: string
  name: string
  category: ProviderCategory
  description: string
  icon?: string
  requiresApiKey: boolean
  supportsEmbedding: boolean
  supportsChat: boolean
  isQueryable: boolean
  status: ProviderStatus
  lastTested?: string
  configured: boolean
  enabled: boolean
}

export interface ProviderConfig {
  id: string
  apiKey?: string
  baseUrl?: string
  timeout?: number
  maxRetries?: number
  organizationId?: string
  projectId?: string
  region?: string
  customHeaders?: Record<string, string>
  [key: string]: string | number | boolean | Record<string, string> | undefined // For provider-specific fields
}

export interface Model {
  id: string
  name: string
  displayName?: string
  description?: string
  contextLength?: number
  capabilities?: string[]
  isCustom?: boolean
  pricing?: {
    inputCost?: number
    outputCost?: number
  }
}

export interface TestResult {
  success: boolean
  message: string
  timestamp: string
  availableModels?: Model[]
  error?: string
}

export interface ModelSelection {
  textGeneration: {
    provider: string | null
    model: string | null
  }
  embeddings: {
    provider: string | null
    model: string | null
  }
  useSharedProvider: boolean
}

export interface ProvidersPageState {
  // UI State
  activeStep: 'select' | 'configure' | 'test' | 'models'
  selectedProvider: string | null
  selectedCategory: ProviderCategory
  isTestingConnection: boolean
  isSavingConfig: boolean
  showAddCustomModel: boolean
  
  // Data State
  providers: ProviderInfo[]
  configurations: Map<string, ProviderConfig>
  testResults: Map<string, TestResult>
  availableModels: Map<string, Model[]>
  modelSelection: ModelSelection
  
  // Error State
  errors: Map<string, Error>
}

// Props interfaces for components
export interface ProviderCardsProps {
  providers: ProviderInfo[]
  selectedProvider: string | null
  selectedCategory: ProviderCategory
  onProviderSelect: (providerId: string) => void
  onCategoryChange: (category: ProviderCategory) => void
}

export interface ConfigurationPanelProps {
  provider: ProviderInfo | null
  configuration: ProviderConfig | undefined
  isTestingConnection: boolean
  testResult: TestResult | undefined
  onConfigurationChange: (config: ProviderConfig) => void
  onTestConnection: () => Promise<void>
  onSaveConfiguration: () => Promise<void>
  isSaving?: boolean
}

export interface ModelSelectionPanelProps {
  providers: ProviderInfo[]
  availableModels: Map<string, Model[]>
  modelSelection: ModelSelection
  onModelSelectionChange: (selection: ModelSelection) => void
  onAddCustomModel: (providerId: string, model: Model) => Promise<void>
  onRemoveCustomModel: (providerId: string, modelId: string) => Promise<void>
  onSaveModelSelection: () => Promise<void>
  isSaving?: boolean
}

export interface CurrentConfigurationProps {
  modelSelection: ModelSelection
  providers: ProviderInfo[]
  onEditConfiguration: () => void
}

export interface ProgressTrackerProps {
  activeStep: ProvidersPageState['activeStep']
  completedSteps: Set<ProvidersPageState['activeStep']>
  onStepClick: (step: ProvidersPageState['activeStep']) => void
}

// Form validation schemas
export interface ProviderFormData {
  apiKey?: string
  baseUrl?: string
  timeout?: number
  maxRetries?: number
  organizationId?: string
  projectId?: string
  region?: string
  serviceAccountKey?: string
  accessKeyId?: string
  secretAccessKey?: string
  siteUrl?: string
  siteName?: string
  [key: string]: string | number | boolean | undefined
}

// API response types
export interface ProviderResponse {
  id: string
  name: string
  type: string
  status: string
  configured: boolean
  category: string
  description: string
  requires_api_key: boolean
  supports_embedding: boolean
  supports_chat: boolean
  config?: Record<string, any>
  enabled: boolean
  last_tested?: string
  models?: string[]
}

export interface ModelSelectionConfig {
  text_generation: {
    provider: string
    model: string
  }
  embeddings: {
    provider: string
    model: string
  }
  use_shared_provider: boolean
}