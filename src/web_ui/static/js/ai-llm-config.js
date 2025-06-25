// AI/LLM Configuration Management Module - Dual Provider Support
class AILLMConfigManager {
    constructor() {
        this.modelCache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
        this.providerDefaults = {
            ollama: {
                baseUrl: 'http://localhost:11434/api',
                modelsEndpoint: '/api/tags',
                requiresKey: false
            },
            openai: {
                baseUrl: 'https://api.openai.com/v1',
                modelsEndpoint: '/models',
                requiresKey: true
            },
            'openai-compatible': {
                baseUrl: '',
                modelsEndpoint: '/models',
                requiresKey: false
            },
            anthropic: {
                baseUrl: 'https://api.anthropic.com',
                modelsEndpoint: '/models',
                requiresKey: true
            },
            custom: {
                baseUrl: '',
                modelsEndpoint: '',
                requiresKey: false
            }
        };
        this.isConnecting = {
            text: false,
            embedding: false
        };
    }

    init() {
        this.bindDualProviderEvents();
        this.setupProviderDefaults();
        this.initializeProviderSharing();
    }

    bindDualProviderEvents() {
        // Provider sharing checkbox
        const sharingCheckbox = document.getElementById('use_same_provider');
        if (sharingCheckbox) {
            sharingCheckbox.addEventListener('change', () => this.onProviderSharingChange());
        }

        // Text provider events
        const textProviderSelect = document.getElementById('text_provider');
        if (textProviderSelect) {
            textProviderSelect.addEventListener('change', () => this.onTextProviderChange());
        }

        const testTextConnectionBtn = document.getElementById('test-text-connection');
        if (testTextConnectionBtn) {
            testTextConnectionBtn.addEventListener('click', () => this.testTextConnection());
        }

        const toggleTextKeyBtn = document.getElementById('toggle-text-api-key');
        if (toggleTextKeyBtn) {
            toggleTextKeyBtn.addEventListener('click', () => this.toggleApiKeyVisibility('text'));
        }

        // Embedding provider events
        const embeddingProviderSelect = document.getElementById('embedding_provider');
        if (embeddingProviderSelect) {
            embeddingProviderSelect.addEventListener('change', () => this.onEmbeddingProviderChange());
        }

        const testEmbeddingConnectionBtn = document.getElementById('test-embedding-connection');
        if (testEmbeddingConnectionBtn) {
            testEmbeddingConnectionBtn.addEventListener('click', () => this.testEmbeddingConnection());
        }

        const toggleEmbeddingKeyBtn = document.getElementById('toggle-embedding-api-key');
        if (toggleEmbeddingKeyBtn) {
            toggleEmbeddingKeyBtn.addEventListener('click', () => this.toggleApiKeyVisibility('embedding'));
        }

        // Model selection events
        const textModelSelect = document.getElementById('text_model_dropdown');
        if (textModelSelect) {
            textModelSelect.addEventListener('change', () => this.onTextModelChange());
        }

        const embeddingModelSelect = document.getElementById('embedding_model_dropdown');
        if (embeddingModelSelect) {
            embeddingModelSelect.addEventListener('change', () => this.onEmbeddingModelChange());
        }

        // Refresh models buttons
        const refreshEmbeddingBtn = document.getElementById('refresh-embedding-models');
        if (refreshEmbeddingBtn) {
            refreshEmbeddingBtn.addEventListener('click', () => this.refreshEmbeddingModels());
        }

        // Advanced settings toggles (gear icons)
        const textAdvancedToggle = document.getElementById('toggle-text-advanced');
        if (textAdvancedToggle) {
            textAdvancedToggle.addEventListener('click', () => this.toggleAdvancedSettings('text'));
        }

        const embeddingAdvancedToggle = document.getElementById('toggle-embedding-advanced');
        if (embeddingAdvancedToggle) {
            embeddingAdvancedToggle.addEventListener('click', () => this.toggleAdvancedSettings('embedding'));
        }

        // Test model response button
        const testModelButton = document.getElementById('test-model-response');
        if (testModelButton) {
            testModelButton.addEventListener('click', () => this.testModelResponse());
        }
    }

    setupProviderDefaults() {
        const textProvider = document.getElementById('text_provider')?.value || 'ollama';
        const embeddingProvider = document.getElementById('embedding_provider')?.value || 'ollama';
        
        this.updateProviderDefaults('text', textProvider);
        this.updateProviderDefaults('embedding', embeddingProvider);
    }

    initializeProviderSharing() {
        const checkbox = document.getElementById('use_same_provider');
        if (checkbox) {
            this.onProviderSharingChange();
        }
    }

    onProviderSharingChange() {
        const checkbox = document.getElementById('use_same_provider');
        const embeddingSection = document.getElementById('embedding_provider_section');
        
        if (!checkbox || !embeddingSection) return;

        if (checkbox.checked) {
            // Hide embedding provider section
            embeddingSection.classList.add('hidden');
            // Copy text provider settings to embedding
            this.copyTextToEmbeddingProvider();
        } else {
            // Show embedding provider section
            embeddingSection.classList.remove('hidden');
        }
    }

    copyTextToEmbeddingProvider() {
        const textProvider = document.getElementById('text_provider')?.value;
        const textBaseUrl = document.getElementById('text_base_url')?.value;
        const textApiKey = document.getElementById('text_api_key')?.value;

        const embeddingProvider = document.getElementById('embedding_provider');
        const embeddingBaseUrl = document.getElementById('embedding_base_url');
        const embeddingApiKey = document.getElementById('embedding_api_key');

        if (embeddingProvider && textProvider) {
            embeddingProvider.value = textProvider;
        }
        if (embeddingBaseUrl && textBaseUrl) {
            embeddingBaseUrl.value = textBaseUrl;
        }
        if (embeddingApiKey && textApiKey) {
            embeddingApiKey.value = textApiKey;
        }

        // Update embedding provider defaults
        if (textProvider) {
            this.updateProviderDefaults('embedding', textProvider);
        }
    }

    onTextProviderChange() {
        const provider = document.getElementById('text_provider').value;
        this.updateProviderDefaults('text', provider);
        this.clearModels('text');
        this.updateConnectionStatus('text', 'disconnected', 'Not Configured');

        // If using same provider, update embedding too
        const sharingCheckbox = document.getElementById('use_same_provider');
        if (sharingCheckbox?.checked) {
            this.copyTextToEmbeddingProvider();
            this.clearModels('embedding');
            this.updateConnectionStatus('embedding', 'disconnected', 'Not Configured');
        }
    }

    onEmbeddingProviderChange() {
        const provider = document.getElementById('embedding_provider').value;
        this.updateProviderDefaults('embedding', provider);
        this.clearModels('embedding');
        this.updateConnectionStatus('embedding', 'disconnected', 'Not Configured');
    }

    updateProviderDefaults(providerType, provider) {
        const defaults = this.providerDefaults[provider];
        if (!defaults) return;

        const prefix = providerType === 'text' ? 'text' : 'embedding';
        const baseUrlField = document.getElementById(`${prefix}_base_url`);
        const apiKeyField = document.getElementById(`${prefix}_api_key`);
        const testButton = document.getElementById(`test-${prefix}-connection`);

        if (baseUrlField && defaults.baseUrl) {
            baseUrlField.value = defaults.baseUrl;
        }

        // Show/hide API key field based on provider requirements
        const apiKeyContainer = apiKeyField?.closest('.mb-4');
        if (apiKeyContainer) {
            if (defaults.requiresKey) {
                apiKeyContainer.classList.remove('hidden');
            } else {
                apiKeyContainer.classList.add('hidden');
            }
        }

        // Enable test button if base URL is provided
        if (testButton) {
            testButton.disabled = !baseUrlField?.value;
        }
    }

    async testTextConnection() {
        await this.testConnection('text');
    }

    async testEmbeddingConnection() {
        await this.testConnection('embedding');
    }

    async testConnection(providerType) {
        if (this.isConnecting[providerType]) return;

        const prefix = providerType === 'text' ? 'text' : 'embedding';
        const provider = document.getElementById(`${prefix}_provider`).value;
        const baseUrl = document.getElementById(`${prefix}_base_url`).value;
        const apiKey = document.getElementById(`${prefix}_api_key`).value;

        if (!baseUrl) {
            utils.showNotification('Please enter a base URL', 'error');
            return;
        }

        this.isConnecting[providerType] = true;
        this.updateConnectionStatus(providerType, 'testing', 'Testing...');
        this.showConnectionResults(providerType, `Testing connection to ${baseUrl}`, 'info');

        const testButton = document.getElementById(`test-${prefix}-connection`);
        if (testButton) {
            testButton.disabled = true;
            testButton.innerHTML = 'Testing...';
        }

        try {
            const response = await this.makeTestRequest(provider, baseUrl, apiKey);
            
            if (response.success) {
                this.updateConnectionStatus(providerType, 'connected', 'Connected');
                this.showConnectionResults(
                    providerType,
                    `✓ Connection successful!<br>` +
                    `✓ Response time: ${response.responseTime}ms<br>` +
                    `✓ Found ${response.modelsCount} models`,
                    'success'
                );
                // Load models for this provider type
                await this.loadModels(providerType, provider, baseUrl, apiKey);
                
                // If using same provider and this is a text connection test, also refresh embedding models
                const sharingCheckbox = document.getElementById('use_same_provider');
                if (sharingCheckbox?.checked && providerType === 'text') {
                    console.log('Auto-refreshing embedding models since same provider is enabled');
                    await this.loadModels('embedding', provider, baseUrl, apiKey);
                }
            } else {
                throw new Error(response.error || 'Connection failed');
            }
        } catch (error) {
            this.updateConnectionStatus(providerType, 'error', 'Connection Failed');
            this.showConnectionResults(
                providerType,
                `⚠️ Connection Failed<br><br>` +
                `Cannot reach endpoint at ${baseUrl}<br><br>` +
                `Details:<br>` +
                `• ${error.message}<br>` +
                `• Check if the service is running<br>` +
                `• Verify the URL is correct`,
                'error'
            );
        } finally {
            this.isConnecting[providerType] = false;
            if (testButton) {
                testButton.disabled = false;
                testButton.innerHTML = 'Test Connection';
            }
        }
    }

    async makeTestRequest(provider, baseUrl, apiKey) {
        const startTime = Date.now();
        
        try {
            console.log(`Testing connection to ${provider} at ${baseUrl}`);
            
            const endpoint = '/api/v1/llm/test-connection';
            const requestData = {
                provider: provider,
                base_url: baseUrl,
                api_key: apiKey || null
            };
            
            console.log(`Making request to: ${endpoint}`);
            console.log('Request data:', requestData);
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log('Request timed out');
                controller.abort();
            }, 15000);
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            console.log(`Response status: ${response.status}`);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const responseTime = Date.now() - startTime;
            console.log('Response data:', data);
            
            return {
                success: data.success || false,
                responseTime,
                modelsCount: data.model_count || 0,
                rawData: data
            };
            
        } catch (error) {
            const responseTime = Date.now() - startTime;
            console.error('Connection test failed:', error);
            
            let errorMessage = error.message;
            
            if (error.name === 'AbortError') {
                errorMessage = 'Request timed out after 15 seconds';
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Network error - check if the service is running and accessible';
            } else if (error.message.includes('NetworkError')) {
                errorMessage = 'Network error - service may not be accessible from this domain';
            }
            
            return {
                success: false,
                responseTime,
                error: errorMessage
            };
        }
    }

    async loadModels(providerType, provider, baseUrl, apiKey) {
        const cacheKey = `${providerType}:${provider}:${baseUrl}`;
        const cached = this.getModelsFromCache(cacheKey);
        
        if (cached) {
            this.populateModels(providerType, cached);
            return;
        }

        this.showModelLoading(providerType, true);

        try {
            const models = await this.fetchModels(provider, baseUrl, apiKey);
            this.setModelsCache(cacheKey, models);
            this.populateModels(providerType, models);
        } catch (error) {
            console.error('Failed to load models:', error);
            utils.showNotification('Failed to load models', 'error');
        } finally {
            this.showModelLoading(providerType, false);
        }
    }

    async fetchModels(provider, baseUrl, apiKey) {
        try {
            const endpoint = '/api/v1/llm/test-connection';
            const requestData = {
                provider: provider,
                base_url: baseUrl,
                api_key: apiKey || null
            };

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000);
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.message || 'Failed to fetch models');
            }
            
            return this.parseBackendModelsResponse(data, provider);
            
        } catch (error) {
            console.error('Failed to fetch models:', error);
            throw new Error(`Failed to fetch models: ${error.message}`);
        }
    }

    parseBackendModelsResponse(data, provider) {
        if (!data.models || !Array.isArray(data.models)) {
            return [];
        }
        
        switch (provider) {
            case 'ollama':
                return data.models.map(model => ({
                    name: model.name || '',
                    description: this.getModelDescription(model.name || '', 'Ollama model'),
                    size: this.formatSize(model.size) || 'N/A',
                    modified: this.formatDate(model.modified_at) || 'Unknown',
                    type: this.getModelType(model.name || '')
                }));
                
            case 'openai':
                return data.models.map(model => ({
                    name: model.name || model.id || '',
                    description: this.getModelDescription(model.name || model.id || '', 'OpenAI model'),
                    size: 'N/A',
                    modified: this.formatDate(model.created) || 'Unknown',
                    type: this.getModelType(model.name || model.id || '')
                }));
                
            case 'anthropic':
                return data.models.map(model => ({
                    name: model.name || '',
                    description: 'Anthropic model',
                    size: 'N/A',
                    modified: 'Unknown',
                    type: 'text-generation'
                }));
                
            default:
                return data.models.map(model => ({
                    name: model.name || model.id || 'Unknown',
                    description: this.getModelDescription(model.name || model.id || '', model.description || 'Model'),
                    size: this.formatSize(model.size) || 'N/A',
                    modified: this.formatDate(model.modified_at || model.created) || 'Unknown',
                    type: this.getModelType(model.name || model.id || '')
                }));
        }
    }

    getModelType(modelName) {
        const embeddingPatterns = [
            /embed/i,
            /embedding/i,
            /nomic-embed/i,
            /text-embedding/i,
            /sentence-transformer/i,
            /bge-/i,
            /e5-/i
        ];
        
        return embeddingPatterns.some(pattern => pattern.test(modelName)) ? 'embedding' : 'text-generation';
    }

    getModelDescription(modelName, defaultDescription) {
        const modelType = this.getModelType(modelName);
        const typeLabel = modelType === 'embedding' ? '(Embedding)' : '(Text Generation)';
        return `${defaultDescription} ${typeLabel}`;
    }

    formatSize(bytes) {
        if (!bytes || bytes === 0) return 'N/A';
        
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return '1 day ago';
            if (diffDays < 30) return `${diffDays} days ago`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
            return `${Math.floor(diffDays / 365)} years ago`;
        } catch (error) {
            return 'Unknown';
        }
    }

    populateModels(providerType, models) {
        const modelSelect = document.getElementById(`${providerType}_model_dropdown`);
        if (!modelSelect) return;

        // Filter models by type
        const filteredModels = models.filter(model => {
            if (providerType === 'text') {
                return model.type === 'text-generation';
            } else {
                return model.type === 'embedding';
            }
        });

        // Clear existing options
        modelSelect.innerHTML = `<option value="">Select a ${providerType} model...</option>`;

        // Populate models
        filteredModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = model.name;
            option.dataset.description = model.description;
            option.dataset.size = model.size;
            option.dataset.modified = model.modified;
            option.dataset.type = model.type;
            modelSelect.appendChild(option);
        });

        // Enable dropdown
        modelSelect.disabled = false;
        
        console.log(`Populated ${filteredModels.length} ${providerType} models`);
    }

    onTextModelChange() {
        this.onModelChange('text');
    }

    onEmbeddingModelChange() {
        this.onModelChange('embedding');
        
        // Auto-sync with AnythingLLM
        const embeddingModelSelect = document.getElementById('embedding_model_dropdown');
        const selectedOption = embeddingModelSelect?.selectedOptions[0];
        if (selectedOption?.value) {
            this.syncEmbeddingModelToAnythingLLM(selectedOption.value);
        }
    }

    onModelChange(modelType) {
        const modelSelect = document.getElementById(`${modelType}_model_dropdown`);
        const selectedOption = modelSelect?.selectedOptions[0];
        const hiddenInput = document.getElementById(modelType === 'text' ? 'llm_model' : 'llm_embedding_model');
        const modelInfo = document.getElementById(`${modelType}-model-info`);

        if (selectedOption && selectedOption.value) {
            if (hiddenInput) {
                hiddenInput.value = selectedOption.value;
            }
            
            // Show model information
            if (modelInfo) {
                const nameEl = document.getElementById(`${modelType}-model-info-name`);
                const descEl = document.getElementById(`${modelType}-model-info-description`);
                const sizeEl = document.getElementById(`${modelType}-model-size`);
                const modifiedEl = document.getElementById(`${modelType}-model-modified`);

                if (nameEl) nameEl.textContent = selectedOption.value;
                if (descEl) descEl.textContent = selectedOption.dataset.description || '';
                if (sizeEl) sizeEl.textContent = selectedOption.dataset.size || '';
                if (modifiedEl) modifiedEl.textContent = selectedOption.dataset.modified || '';

                modelInfo.classList.remove('hidden');
            }
            
            console.log(`Selected ${modelType} model: ${selectedOption.value}`);
        } else {
            if (hiddenInput) {
                hiddenInput.value = '';
            }
            if (modelInfo) {
                modelInfo.classList.add('hidden');
            }
        }
    }

    syncEmbeddingModelToAnythingLLM(embeddingModel) {
        const sharingCheckbox = document.getElementById('use_same_provider');
        let provider;
        
        if (sharingCheckbox?.checked) {
            provider = document.getElementById('text_provider')?.value || 'ollama';
        } else {
            provider = document.getElementById('embedding_provider')?.value || 'ollama';
        }
        
        // Set AnythingLLM embedding model fields
        const embeddingModelField = document.getElementById('anythingllm_embedding_model');
        const embeddingProviderField = document.getElementById('anythingllm_embedding_provider');
        
        if (embeddingModelField) {
            embeddingModelField.value = embeddingModel;
            console.log(`Auto-synced embedding model to AnythingLLM: ${embeddingModel}`);
        }
        
        if (embeddingProviderField) {
            embeddingProviderField.value = provider;
            console.log(`Auto-synced embedding provider to AnythingLLM: ${provider}`);
        }
        
        // Show notification about auto-sync
        utils.showNotification(`Embedding model ${embeddingModel} auto-synced to AnythingLLM (manual save required)`, 'success');
        
        console.log('AnythingLLM auto-sync completed - configuration will be saved with form submission');
    }

    refreshEmbeddingModels() {
        const sharingCheckbox = document.getElementById('use_same_provider');
        let provider, baseUrl, apiKey;
        
        if (sharingCheckbox?.checked) {
            provider = document.getElementById('text_provider')?.value;
            baseUrl = document.getElementById('text_base_url')?.value;
            apiKey = document.getElementById('text_api_key')?.value;
        } else {
            provider = document.getElementById('embedding_provider')?.value;
            baseUrl = document.getElementById('embedding_base_url')?.value;
            apiKey = document.getElementById('embedding_api_key')?.value;
        }

        if (!baseUrl) {
            utils.showNotification('Please configure provider first', 'warning');
            return;
        }

        // Clear cache and reload
        const cacheKey = `embedding:${provider}:${baseUrl}`;
        this.modelCache.delete(cacheKey);
        this.loadModels('embedding', provider, baseUrl, apiKey);
    }

    clearModels(providerType) {
        const modelSelect = document.getElementById(`${providerType}_model_dropdown`);
        const hiddenInput = document.getElementById(providerType === 'text' ? 'llm_model' : 'llm_embedding_model');
        const modelInfo = document.getElementById(`${providerType}-model-info`);

        if (modelSelect) {
            modelSelect.innerHTML = '<option value="">Configure provider first</option>';
            modelSelect.disabled = true;
        }

        if (hiddenInput) {
            hiddenInput.value = '';
        }

        if (modelInfo) {
            modelInfo.classList.add('hidden');
        }
    }

    toggleApiKeyVisibility(providerType) {
        const apiKeyField = document.getElementById(`${providerType}_api_key`);
        const toggleButton = document.getElementById(`toggle-${providerType}-api-key`);
        
        if (apiKeyField && toggleButton) {
            const isPassword = apiKeyField.type === 'password';
            apiKeyField.type = isPassword ? 'text' : 'password';
            
            const svg = toggleButton.querySelector('svg');
            if (svg) {
                svg.classList.toggle('text-gray-600');
            }
        }
    }

    toggleAdvancedSettings(settingsType) {
        const content = document.getElementById(`${settingsType}-advanced-settings`);
        
        if (content) {
            const isHidden = content.classList.contains('hidden');
            
            if (isHidden) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        }
    }

    updateConnectionStatus(providerType, status, text) {
        const prefix = providerType === 'text' ? 'text' : 'embedding';
        const statusDot = document.getElementById(`${prefix}-connection-status-dot`);
        const statusText = document.getElementById(`${prefix}-connection-status-text`);

        if (statusDot) {
            statusDot.className = `inline-block w-2 h-2 rounded-full mr-2`;
            switch (status) {
                case 'connected':
                    statusDot.classList.add('bg-green-500');
                    break;
                case 'testing':
                    statusDot.classList.add('bg-yellow-500', 'animate-pulse');
                    break;
                case 'error':
                    statusDot.classList.add('bg-red-500');
                    break;
                default:
                    statusDot.classList.add('bg-gray-400');
            }
        }

        if (statusText) {
            statusText.textContent = text;
        }
    }

    showConnectionResults(providerType, message, type) {
        const prefix = providerType === 'text' ? 'text' : 'embedding';
        const resultsContainer = document.getElementById(`${prefix}-connection-test-results`);
        if (!resultsContainer) return;

        const typeClasses = {
            info: 'bg-blue-50 border-blue-200 text-blue-800',
            success: 'bg-green-50 border-green-200 text-green-800',
            error: 'bg-red-50 border-red-200 text-red-800'
        };

        resultsContainer.className = `mt-4 p-3 rounded-md border ${typeClasses[type] || typeClasses.info}`;
        resultsContainer.innerHTML = message;
        resultsContainer.classList.remove('hidden');
    }

    showModelLoading(providerType, show) {
        const loadingSpinner = document.getElementById(`${providerType}-model-loading`);
        const modelSelect = document.getElementById(`${providerType}_model_dropdown`);

        if (loadingSpinner) {
            if (show) {
                loadingSpinner.classList.remove('hidden');
            } else {
                loadingSpinner.classList.add('hidden');
            }
        }

        if (modelSelect) {
            modelSelect.disabled = show;
        }
    }

    getModelsFromCache(key) {
        const cached = this.modelCache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
            return cached.models;
        }
        return null;
    }

    setModelsCache(key, models) {
        this.modelCache.set(key, {
            models,
            timestamp: Date.now()
        });
    }

    async testModelResponse() {
        const textModel = document.getElementById('llm_model').value;
        const embeddingModel = document.getElementById('llm_embedding_model').value;

        // Test text generation model if available
        if (textModel) {
            await this.testTextGenerationModel();
        } else if (embeddingModel) {
            await this.testEmbeddingModel();
        } else {
            utils.showNotification('Please select a model first', 'warning');
        }
    }

    async testTextGenerationModel() {
        const sharingCheckbox = document.getElementById('use_same_provider');
        let provider, baseUrl, apiKey;
        
        if (sharingCheckbox?.checked) {
            provider = document.getElementById('text_provider')?.value;
            baseUrl = document.getElementById('text_base_url')?.value;
            apiKey = document.getElementById('text_api_key')?.value;
        } else {
            provider = document.getElementById('text_provider')?.value;
            baseUrl = document.getElementById('text_base_url')?.value;
            apiKey = document.getElementById('text_api_key')?.value;
        }

        const model = document.getElementById('llm_model').value;

        if (!model || !baseUrl) {
            utils.showNotification('Please configure provider and select a model first', 'warning');
            return;
        }

        const testButton = document.getElementById('test-model-response');
        const originalText = testButton ? testButton.textContent : 'Test Model Response';

        if (testButton) {
            testButton.disabled = true;
            testButton.textContent = 'Testing...';
        }

        this.showModelTestResults('Testing text generation model...', 'info');
        
        try {
            const endpoint = '/api/v1/llm/test-model';
            const requestData = {
                provider: provider,
                base_url: baseUrl,
                api_key: apiKey || null,
                model: model,
                prompt: "Hello, this is a test message. Please respond briefly."
            };
            
            console.log(`Testing text generation model ${model} on ${provider}`);
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 45000);
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                const responseTime = data.response_time ? `${Math.round(data.response_time * 1000)}ms` : 'N/A';
                this.showModelTestResults(
                    `✓ Model test successful!<br>` +
                    `✓ Model: ${data.model}<br>` +
                    `✓ Response time: ${responseTime}<br><br>` +
                    `<strong>Prompt:</strong><br>${data.prompt}<br><br>` +
                    `<strong>Model Response:</strong><br>${data.model_response}`,
                    'success'
                );
                utils.showNotification('Model test successful!', 'success');
            } else {
                throw new Error(data.message || 'Model test failed');
            }
            
        } catch (error) {
            console.error('Model test failed:', error);
            
            let errorMessage = error.message;
            if (error.name === 'AbortError') {
                errorMessage = 'Model test timed out after 45 seconds';
            }
            
            this.showModelTestResults(
                `⚠️ Model Test Failed<br><br>` +
                `Model: ${model}<br>` +
                `Provider: ${provider}<br><br>` +
                `Error: ${errorMessage}`,
                'error'
            );
            utils.showNotification('Model test failed: ' + errorMessage, 'error');
            
        } finally {
            if (testButton) {
                testButton.disabled = false;
                testButton.textContent = originalText;
            }
        }
    }

    showModelTestResults(message, type) {
        const resultsContainer = document.getElementById('model-test-results');
        if (!resultsContainer) {
            const container = document.createElement('div');
            container.id = 'model-test-results';
            container.className = 'mt-4 p-3 rounded-md border hidden';
            
            const testButton = document.getElementById('test-model-response');
            if (testButton?.parentNode) {
                testButton.parentNode.insertBefore(container, testButton.nextSibling);
            }
            return this.showModelTestResults(message, type);
        }

        const typeClasses = {
            info: 'bg-blue-50 border-blue-200 text-blue-800',
            success: 'bg-green-50 border-green-200 text-green-800',
            error: 'bg-red-50 border-red-200 text-red-800'
        };

        resultsContainer.className = `mt-4 p-3 rounded-md border ${typeClasses[type] || typeClasses.info}`;
        resultsContainer.innerHTML = message;
        resultsContainer.classList.remove('hidden');
    }

    getSystemConfigUpdate() {
        console.log('Building AI SystemConfiguration update from form values');
        
        const textProvider = document.getElementById('text_provider')?.value || 'ollama';
        const textBaseUrl = document.getElementById('text_base_url')?.value || '';
        const textApiKey = document.getElementById('text_api_key')?.value || '';
        const textModel = document.getElementById('llm_model')?.value || '';
        
        // Get advanced parameters
        const maxTokens = parseInt(document.getElementById('text_max_tokens')?.value) || 4096;
        const temperature = parseFloat(document.getElementById('text_temperature')?.value) || 0.7;
        const timeout = parseInt(document.getElementById('text_timeout')?.value) || 30;
        
        // Build AI configuration in SystemConfiguration format
        const aiUpdate = {
            primary_provider: textProvider,
            cache_ttl_seconds: 3600, // Default cache TTL
            enable_failover: true
        };
        
        // Add provider-specific configuration
        if (textProvider === 'ollama') {
            aiUpdate.ollama = {
                endpoint: textBaseUrl || 'http://localhost:11434',
                model: textModel || 'llama2',
                temperature: temperature,
                max_tokens: maxTokens,
                timeout_seconds: timeout
            };
        } else if (textProvider === 'openai') {
            aiUpdate.openai = {
                api_key: textApiKey,
                model: textModel || 'gpt-3.5-turbo',
                temperature: temperature,
                max_tokens: maxTokens,
                timeout_seconds: timeout
            };
            aiUpdate.fallback_provider = 'ollama'; // Set fallback
        }
        
        console.log('Built AI SystemConfiguration update:', aiUpdate);
        return aiUpdate;
    }

    getAILLMConfig() {
        const sharingCheckbox = document.getElementById('use_same_provider');
        const useSameProvider = sharingCheckbox?.checked || false;
        
        // Sync advanced settings to legacy hidden fields for validation
        this.syncAdvancedSettingsToLegacyFields();
        
        return {
            // Text generation provider
            text_provider: document.getElementById('text_provider')?.value || '',
            text_base_url: document.getElementById('text_base_url')?.value || '',
            text_api_key: document.getElementById('text_api_key')?.value || '',
            
            // Embedding provider
            use_same_provider: useSameProvider,
            embedding_provider: useSameProvider ?
                (document.getElementById('text_provider')?.value || '') :
                (document.getElementById('embedding_provider')?.value || ''),
            embedding_base_url: useSameProvider ?
                (document.getElementById('text_base_url')?.value || '') :
                (document.getElementById('embedding_base_url')?.value || ''),
            embedding_api_key: useSameProvider ?
                (document.getElementById('text_api_key')?.value || '') :
                (document.getElementById('embedding_api_key')?.value || ''),
            
            // Models
            llm_model: document.getElementById('llm_model')?.value || '',
            llm_embedding_model: document.getElementById('llm_embedding_model')?.value || '',
            
            // Text generation advanced parameters
            text_max_tokens: parseInt(document.getElementById('text_max_tokens')?.value) || 2048,
            text_temperature: parseFloat(document.getElementById('text_temperature')?.value) || 0.7,
            text_top_p: parseFloat(document.getElementById('text_top_p')?.value) || 1.0,
            text_top_k: parseInt(document.getElementById('text_top_k')?.value) || 40,
            text_timeout: parseInt(document.getElementById('text_timeout')?.value) || 30,
            text_retries: parseInt(document.getElementById('text_retries')?.value) || 3,
            
            // Embedding advanced parameters
            embedding_batch_size: parseInt(document.getElementById('embedding_batch_size')?.value) || 10,
            embedding_timeout: parseInt(document.getElementById('embedding_timeout')?.value) || 30,
            embedding_retries: parseInt(document.getElementById('embedding_retries')?.value) || 3,
            embedding_chunk_size: parseInt(document.getElementById('embedding_chunk_size')?.value) || 512,
            embedding_overlap: parseInt(document.getElementById('embedding_overlap')?.value) || 50,
            embedding_normalize: document.getElementById('embedding_normalize')?.checked || true,
            
            // Legacy compatibility
            max_tokens: parseInt(document.getElementById('text_max_tokens')?.value) || 2048,
            temperature: parseFloat(document.getElementById('text_temperature')?.value) || 0.7,
            top_p: parseFloat(document.getElementById('text_top_p')?.value) || 1.0,
            top_k: parseInt(document.getElementById('text_top_k')?.value) || 40,
            llm_timeout: parseInt(document.getElementById('text_timeout')?.value) || 30,
            llm_retries: parseInt(document.getElementById('text_retries')?.value) || 3,
            
            // Legacy compatibility
            llm_provider: document.getElementById('text_provider')?.value || '',
            llm_base_url: document.getElementById('text_base_url')?.value || '',
            llm_api_key: document.getElementById('text_api_key')?.value || ''
        };
    }

    syncAdvancedSettingsToLegacyFields() {
        console.log('🔄 Syncing advanced settings to legacy hidden fields...');
        
        // Sync max_tokens
        const textMaxTokens = document.getElementById('text_max_tokens')?.value || '2048';
        const legacyMaxTokens = document.getElementById('max_tokens');
        if (legacyMaxTokens) {
            legacyMaxTokens.value = textMaxTokens;
            console.log(`  ✅ Synced max_tokens: ${textMaxTokens}`);
        }
        
        // Sync temperature
        const textTemperature = document.getElementById('text_temperature')?.value || '0.7';
        const legacyTemperature = document.getElementById('temperature');
        if (legacyTemperature) {
            legacyTemperature.value = textTemperature;
            console.log(`  ✅ Synced temperature: ${textTemperature}`);
        }
        
        // Sync other legacy fields
        const textTopP = document.getElementById('text_top_p')?.value || '1.0';
        const legacyTopP = document.getElementById('top_p');
        if (legacyTopP) {
            legacyTopP.value = textTopP;
            console.log(`  ✅ Synced top_p: ${textTopP}`);
        }
        
        const textTopK = document.getElementById('text_top_k')?.value || '40';
        const legacyTopK = document.getElementById('top_k');
        if (legacyTopK) {
            legacyTopK.value = textTopK;
            console.log(`  ✅ Synced top_k: ${textTopK}`);
        }
        
        const textTimeout = document.getElementById('text_timeout')?.value || '30';
        const legacyTimeout = document.getElementById('llm_timeout');
        if (legacyTimeout) {
            legacyTimeout.value = textTimeout;
            console.log(`  ✅ Synced llm_timeout: ${textTimeout}`);
        }
        
        const textRetries = document.getElementById('text_retries')?.value || '3';
        const legacyRetries = document.getElementById('llm_retries');
        if (legacyRetries) {
            legacyRetries.value = textRetries;
            console.log(`  ✅ Synced llm_retries: ${textRetries}`);
        }
    }

    setSystemConfig(systemConfig) {
        console.log('Setting AI/LLM configuration from SystemConfiguration:', systemConfig);
        
        const ai = systemConfig.ai || {};
        const ollama = ai.ollama || {};
        const openai = ai.openai || {};
        
        // Set text provider from AI configuration
        const textProvider = document.getElementById('text_provider');
        if (textProvider) {
            textProvider.value = ai.primary_provider || 'ollama';
        }
        
        // Set provider-specific settings based on primary provider
        if (ai.primary_provider === 'ollama') {
            const textBaseUrl = document.getElementById('text_base_url');
            const textApiKey = document.getElementById('text_api_key');
            
            if (textBaseUrl) textBaseUrl.value = ollama.endpoint || 'http://localhost:11434';
            if (textApiKey) textApiKey.value = ''; // Ollama typically doesn't need API key
            
            // Set Ollama-specific model settings
            const textModel = document.getElementById('llm_model');
            if (textModel) textModel.value = ollama.model || 'llama2';
            
            // Set advanced parameters
            const textMaxTokens = document.getElementById('text_max_tokens');
            const textTemperature = document.getElementById('text_temperature');
            const textTimeout = document.getElementById('text_timeout');
            
            if (textMaxTokens) textMaxTokens.value = ollama.max_tokens || 4096;
            if (textTemperature) textTemperature.value = ollama.temperature || 0.7;
            if (textTimeout) textTimeout.value = ollama.timeout_seconds || 60;
            
        } else if (ai.primary_provider === 'openai' && openai) {
            const textBaseUrl = document.getElementById('text_base_url');
            const textApiKey = document.getElementById('text_api_key');
            
            if (textBaseUrl) textBaseUrl.value = 'https://api.openai.com/v1';
            if (textApiKey) textApiKey.value = openai.api_key || '';
            
            // Set OpenAI-specific model settings
            const textModel = document.getElementById('llm_model');
            if (textModel) textModel.value = openai.model || 'gpt-3.5-turbo';
            
            // Set advanced parameters
            const textMaxTokens = document.getElementById('text_max_tokens');
            const textTemperature = document.getElementById('text_temperature');
            const textTimeout = document.getElementById('text_timeout');
            
            if (textMaxTokens) textMaxTokens.value = openai.max_tokens || 4096;
            if (textTemperature) textTemperature.value = openai.temperature || 0.7;
            if (textTimeout) textTimeout.value = openai.timeout_seconds || 30;
        }
        
        // Set embedding provider (for now, use same as text generation)
        const embeddingProvider = document.getElementById('embedding_provider');
        if (embeddingProvider) {
            embeddingProvider.value = ai.primary_provider || 'ollama';
        }
        
        // Set provider sharing to true by default
        const sharingCheckbox = document.getElementById('use_same_provider');
        if (sharingCheckbox) {
            sharingCheckbox.checked = true;
        }
        
        // Trigger provider setup
        this.setupProviderDefaults();
        this.onProviderSharingChange();
        
        console.log('SystemConfiguration applied to AI/LLM settings');
    }

    setAILLMConfig(config) {
        // Check if this is SystemConfiguration format
        if (config.ai || config.app) {
            return this.setSystemConfig(config);
        }
        
        // Legacy format handling
        console.log('Setting AI/LLM configuration from legacy format:', config);
        
        // Set text provider fields
        const textProviderFields = ['text_provider', 'text_base_url', 'text_api_key'];
        textProviderFields.forEach(field => {
            const element = document.getElementById(field);
            if (element && config[field] !== undefined) {
                element.value = config[field];
            }
        });

        // Set embedding provider fields
        const embeddingProviderFields = ['embedding_provider', 'embedding_base_url', 'embedding_api_key'];
        embeddingProviderFields.forEach(field => {
            const element = document.getElementById(field);
            if (element && config[field] !== undefined) {
                element.value = config[field];
            }
        });

        // Set provider sharing checkbox
        const sharingCheckbox = document.getElementById('use_same_provider');
        if (sharingCheckbox && config.use_same_provider !== undefined) {
            sharingCheckbox.checked = config.use_same_provider;
        }

        // Set models
        const modelFields = ['llm_model', 'llm_embedding_model'];
        modelFields.forEach(field => {
            const element = document.getElementById(field);
            if (element && config[field] !== undefined) {
                element.value = config[field];
            }
        });

        // Set advanced parameters
        const advancedFields = ['max_tokens', 'temperature', 'top_p', 'top_k', 'llm_timeout', 'llm_retries'];
        advancedFields.forEach(field => {
            const element = document.getElementById(field);
            if (element && config[field] !== undefined) {
                element.value = config[field];
            }
        });

        // Handle legacy compatibility
        if (config.llm_provider && !config.text_provider) {
            const textProvider = document.getElementById('text_provider');
            if (textProvider) textProvider.value = config.llm_provider;
        }

        if (config.llm_base_url && !config.text_base_url) {
            const textBaseUrl = document.getElementById('text_base_url');
            if (textBaseUrl) textBaseUrl.value = config.llm_base_url;
        }

        if (config.llm_api_key && !config.text_api_key) {
            const textApiKey = document.getElementById('text_api_key');
            if (textApiKey) textApiKey.value = config.llm_api_key;
        }

        // Trigger provider setup
        this.setupProviderDefaults();
        this.onProviderSharingChange();
    }

    validateConfiguration() {
        console.log('🤖 Starting AI/LLM configuration validation...');
        let isValid = true;
        const validationResults = {};

        // Validate text generation provider fields
        const textProvider = document.getElementById('text_provider')?.value;
        const textBaseUrl = document.getElementById('text_base_url')?.value;
        const textModel = document.getElementById('llm_model')?.value;

        console.log('📋 Text generation provider validation:');
        console.log(`  - Provider: "${textProvider}"`);
        console.log(`  - Base URL: "${textBaseUrl}"`);
        console.log(`  - Model: "${textModel}"`);

        if (!textProvider) {
            console.log('❌ Text provider validation failed: empty value');
            this.showFieldError('text_provider', 'Text generation provider is required');
            validationResults.text_provider = false;
            isValid = false;
        } else {
            console.log('✅ Text provider validation passed');
            this.hideFieldError('text_provider');
            validationResults.text_provider = true;
        }

        if (!textBaseUrl) {
            console.log('❌ Text base URL validation failed: empty value');
            this.showFieldError('text_base_url', 'Base URL is required');
            validationResults.text_base_url = false;
            isValid = false;
        } else if (!this.isValidUrl(textBaseUrl)) {
            console.log('❌ Text base URL validation failed: invalid URL format');
            this.showFieldError('text_base_url', 'Please enter a valid URL');
            validationResults.text_base_url = false;
            isValid = false;
        } else {
            console.log('✅ Text base URL validation passed');
            this.hideFieldError('text_base_url');
            validationResults.text_base_url = true;
        }

        if (!textModel) {
            console.log('❌ Text model validation failed: empty value');
            this.showFieldError('llm_model', 'Text model is required');
            validationResults.llm_model = false;
            isValid = false;
        } else {
            console.log('✅ Text model validation passed');
            this.hideFieldError('llm_model');
            validationResults.llm_model = true;
        }

        // Validate embedding configuration if not using same provider
        const useSameProvider = document.getElementById('use_same_provider')?.checked;
        console.log(`🔄 Use same provider for embedding: ${useSameProvider}`);

        if (!useSameProvider) {
            console.log('📋 Embedding provider validation (separate provider):');
            const embeddingProvider = document.getElementById('embedding_provider')?.value;
            const embeddingBaseUrl = document.getElementById('embedding_base_url')?.value;
            const embeddingModel = document.getElementById('llm_embedding_model')?.value;

            console.log(`  - Provider: "${embeddingProvider}"`);
            console.log(`  - Base URL: "${embeddingBaseUrl}"`);
            console.log(`  - Model: "${embeddingModel}"`);

            if (!embeddingProvider) {
                console.log('❌ Embedding provider validation failed: empty value');
                this.showFieldError('embedding_provider', 'Embedding provider is required');
                validationResults.embedding_provider = false;
                isValid = false;
            } else {
                console.log('✅ Embedding provider validation passed');
                this.hideFieldError('embedding_provider');
                validationResults.embedding_provider = true;
            }

            if (!embeddingBaseUrl) {
                console.log('❌ Embedding base URL validation failed: empty value');
                this.showFieldError('embedding_base_url', 'Base URL is required');
                validationResults.embedding_base_url = false;
                isValid = false;
            } else if (!this.isValidUrl(embeddingBaseUrl)) {
                console.log('❌ Embedding base URL validation failed: invalid URL format');
                this.showFieldError('embedding_base_url', 'Please enter a valid URL');
                validationResults.embedding_base_url = false;
                isValid = false;
            } else {
                console.log('✅ Embedding base URL validation passed');
                this.hideFieldError('embedding_base_url');
                validationResults.embedding_base_url = true;
            }

            if (!embeddingModel) {
                console.log('❌ Embedding model validation failed: empty value');
                this.showFieldError('llm_embedding_model', 'Embedding model is required');
                validationResults.llm_embedding_model = false;
                isValid = false;
            } else {
                console.log('✅ Embedding model validation passed');
                this.hideFieldError('llm_embedding_model');
                validationResults.llm_embedding_model = true;
            }
        } else {
            console.log('📋 Embedding validation skipped (using same provider as text generation)');
            validationResults.embedding_provider = 'same-as-text';
            validationResults.embedding_base_url = 'same-as-text';
            validationResults.llm_embedding_model = textModel ? true : false; // Embedding model still needs to be selected
            
            if (!textModel) {
                console.log('❌ Since using same provider, embedding model validation failed because text model is empty');
            }
        }

        console.log('📊 AI/LLM validation results:', validationResults);
        console.log(`🎯 AI/LLM validation overall result: ${isValid}`);

        return isValid;
    }

    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    showFieldError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.add('border-red-500');
            
            // Find or create error message element
            let errorElement = document.getElementById(`${fieldId}-error`);
            if (!errorElement) {
                errorElement = document.createElement('div');
                errorElement.id = `${fieldId}-error`;
                errorElement.className = 'text-red-600 text-sm mt-1';
                field.parentNode.appendChild(errorElement);
            }
            
            errorElement.textContent = message;
            errorElement.classList.remove('hidden');
        }
    }

    hideFieldError(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.remove('border-red-500');
            
            const errorElement = document.getElementById(`${fieldId}-error`);
            if (errorElement) {
                errorElement.classList.add('hidden');
            }
        }
    }
}

// Global AI/LLM config manager instance
window.aiLLMManager = new AILLMConfigManager();