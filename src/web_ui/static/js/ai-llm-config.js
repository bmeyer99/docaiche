// AI/LLM Configuration Management Module - Refactored for "Save-on-Change"
class AILLMConfigManager {
    constructor() {
        this.modelCache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
        this.providerDefaults = {
            ollama: { baseUrl: 'http://localhost:11434/api', requiresKey: false },
            openai: { baseUrl: 'https://api.openai.com/v1', requiresKey: true },
            'openai-compatible': { baseUrl: '', requiresKey: false },
            anthropic: { baseUrl: 'https://api.anthropic.com', requiresKey: true },
            custom: { baseUrl: '', requiresKey: false }
        };
        this.isConnecting = { text: false, embedding: false };
        this.configManager = null; // Will be set on init
        this.isInitializing = true; // Prevent saves during initialization
    }

    init(configManager) {
        this.configManager = configManager;
        this.bindDualProviderEvents();
        this.setupProviderDefaults();
        this.initializeProviderSharing();
    }

    bindDualProviderEvents() {
        // Provider sharing checkbox
        const sharingCheckbox = document.getElementById('use_same_provider');
        if (sharingCheckbox) {
            sharingCheckbox.addEventListener('change', () => this.onProviderSharingChange(sharingCheckbox));
        }

        // Text provider events
        const textProviderSelect = document.getElementById('text_provider');
        if (textProviderSelect) {
            textProviderSelect.addEventListener('change', () => this.onTextProviderChange(textProviderSelect));
        }
        document.getElementById('test-text-connection')?.addEventListener('click', () => this.testConnection('text'));
        document.getElementById('toggle-text-api-key')?.addEventListener('click', () => this.toggleApiKeyVisibility('text'));

        // Embedding provider events
        const embeddingProviderSelect = document.getElementById('embedding_provider');
        if (embeddingProviderSelect) {
            embeddingProviderSelect.addEventListener('change', () => this.onEmbeddingProviderChange(embeddingProviderSelect));
        }
        document.getElementById('test-embedding-connection')?.addEventListener('click', () => this.testConnection('embedding'));
        document.getElementById('toggle-embedding-api-key')?.addEventListener('click', () => this.toggleApiKeyVisibility('embedding'));

        // Model selection events
        const textModelSelect = document.getElementById('text_model_dropdown');
        if (textModelSelect) {
            textModelSelect.addEventListener('change', () => this.onTextModelChange(textModelSelect));
        }
        const embeddingModelSelect = document.getElementById('embedding_model_dropdown');
        if (embeddingModelSelect) {
            embeddingModelSelect.addEventListener('change', () => this.onEmbeddingModelChange(embeddingModelSelect));
        }

        // Refresh models buttons
        document.getElementById('refresh-embedding-models')?.addEventListener('click', () => this.refreshEmbeddingModels());

        // Advanced settings toggles
        document.getElementById('toggle-text-advanced')?.addEventListener('click', () => this.toggleAdvancedSettings('text'));
        document.getElementById('toggle-embedding-advanced')?.addEventListener('click', () => this.toggleAdvancedSettings('embedding'));

        // Test model response button
        document.getElementById('test-model-response')?.addEventListener('click', () => this.testModelResponse());
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
            this.onProviderSharingChange(checkbox);
        }
    }

    onProviderSharingChange(checkbox) {
        const embeddingSection = document.getElementById('embedding_provider_section');
        if (!embeddingSection) return;

        if (checkbox.checked) {
            embeddingSection.classList.add('hidden');
            this.copyTextToEmbeddingProvider();
        } else {
            embeddingSection.classList.remove('hidden');
        }
        
        // ONLY save if this is user-driven, not during initialization
        if (this.configManager && !this.isInitializing) {
            this.configManager.saveField(checkbox);
        }
    }

    copyTextToEmbeddingProvider() {
        const textProvider = document.getElementById('text_provider');
        const textBaseUrl = document.getElementById('text_base_url');
        const textApiKey = document.getElementById('text_api_key');

        const embeddingProvider = document.getElementById('embedding_provider');
        const embeddingBaseUrl = document.getElementById('embedding_base_url');
        const embeddingApiKey = document.getElementById('embedding_api_key');

        if (embeddingProvider) embeddingProvider.value = textProvider.value;
        if (embeddingBaseUrl) embeddingBaseUrl.value = textBaseUrl.value;
        if (embeddingApiKey) embeddingApiKey.value = textApiKey.value;

        this.updateProviderDefaults('embedding', textProvider.value);
        
        // ONLY save if this is user-driven, not during initialization
        if (this.configManager && !this.isInitializing) {
            if (embeddingProvider) this.configManager.saveField(embeddingProvider);
            if (embeddingBaseUrl) this.configManager.saveField(embeddingBaseUrl);
            if (embeddingApiKey) this.configManager.saveField(embeddingApiKey);
        }
    }

    onTextProviderChange(selectElement) {
        const provider = selectElement.value;
        this.updateProviderDefaults('text', provider);
        this.clearModels('text');
        this.updateConnectionStatus('text', 'disconnected', 'Not Configured');
        
        // ONLY save if this is user-driven, not during initialization
        if (this.configManager && !this.isInitializing) {
            this.configManager.saveField(selectElement);
        }

        if (document.getElementById('use_same_provider')?.checked) {
            this.copyTextToEmbeddingProvider();
            this.clearModels('embedding');
            this.updateConnectionStatus('embedding', 'disconnected', 'Not Configured');
        }
    }

    onEmbeddingProviderChange(selectElement) {
        const provider = selectElement.value;
        this.updateProviderDefaults('embedding', provider);
        this.clearModels('embedding');
        this.updateConnectionStatus('embedding', 'disconnected', 'Not Configured');
        
        // ONLY save if this is user-driven, not during initialization
        if (this.configManager && !this.isInitializing) {
            this.configManager.saveField(selectElement);
        }
    }

    updateProviderDefaults(providerType, provider) {
        const defaults = this.providerDefaults[provider];
        if (!defaults) return;

        const prefix = providerType;
        const baseUrlField = document.getElementById(`${prefix}_base_url`);
        const apiKeyField = document.getElementById(`${prefix}_api_key`);
        const testButton = document.getElementById(`test-${prefix}-connection`);

        // DO NOT SAVE ON CHANGE HERE. This causes initialization errors.
        // The main config manager will handle saving when the user blurs the field.
        if (baseUrlField && defaults.baseUrl && !baseUrlField.value) {
            baseUrlField.value = defaults.baseUrl;
        }

        const apiKeyContainer = apiKeyField?.closest('.mb-4');
        if (apiKeyContainer) {
            apiKeyContainer.classList.toggle('hidden', !defaults.requiresKey);
        }

        if (testButton) {
            testButton.disabled = !baseUrlField?.value;
        }
    }

    async testConnection(providerType) {
        console.log(`testConnection called for: ${providerType}`);
        if (this.isConnecting[providerType]) return;

        const prefix = providerType;
        const provider = document.getElementById(`${prefix}_provider`).value;
        const baseUrl = document.getElementById(`${prefix}_base_url`).value;
        const apiKey = document.getElementById(`${prefix}_api_key`).value;

        console.log(`Testing with: provider=${provider}, baseUrl=${baseUrl}`);

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
            console.log('Test request response:', response);
            
            if (response.success) {
                this.updateConnectionStatus(providerType, 'connected', 'Connected');
                this.showConnectionResults(providerType, `✓ Connection successful!`, 'success');
                await this.loadModels(providerType, provider, baseUrl, apiKey);
                
                if (document.getElementById('use_same_provider')?.checked && providerType === 'text') {
                    await this.loadModels('embedding', provider, baseUrl, apiKey);
                }
            } else {
                throw new Error(response.error || 'Connection failed');
            }
        } catch (error) {
            this.updateConnectionStatus(providerType, 'error', 'Connection Failed');
            this.showConnectionResults(providerType, `⚠️ Connection Failed: ${error.message}`, 'error');
        } finally {
            this.isConnecting[providerType] = false;
            if (testButton) {
                testButton.disabled = false;
                testButton.innerHTML = 'Test Connection';
            }
        }
    }

    async makeTestRequest(provider, baseUrl, apiKey) {
        try {
            // This now correctly calls the dedicated test endpoint
            const response = await api.post('/llm/test-connection', { provider, base_url: baseUrl, api_key: apiKey });
            return {
                success: response.success || false,
                error: response.message
            };
        } catch (error) {
            return { success: false, error: error.message };
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
            utils.showNotification('Failed to load models', 'error');
        } finally {
            this.showModelLoading(providerType, false);
        }
    }

    async fetchModels(provider, baseUrl, apiKey) {
        // This now correctly calls the dedicated list-models endpoint
        const data = await api.post('/llm/list-models', { provider, base_url: baseUrl, api_key: apiKey });
        if (!data.success) {
            throw new Error(data.message || 'Failed to fetch models');
        }
        return this.parseBackendModelsResponse(data, provider);
    }

    parseBackendModelsResponse(data, provider) {
        if (!data.models || !Array.isArray(data.models)) return [];
        return data.models.map(model => ({
            name: model.name || model.id || 'Unknown',
            description: this.getModelDescription(model.name || model.id || '', provider),
            size: this.formatSize(model.size),
            modified: this.formatDate(model.modified_at || model.created),
            type: this.getModelType(model.name || model.id || '')
        }));
    }

    getModelType(modelName) {
        const patterns = [/embed/i, /embedding/i, /nomic-embed/i, /sentence-transformer/i, /bge-/i, /e5-/i];
        return patterns.some(p => p.test(modelName)) ? 'embedding' : 'text-generation';
    }

    getModelDescription(modelName, provider) {
        const type = this.getModelType(modelName);
        return `${provider} ${type.replace('-', ' ')} model`;
    }

    formatSize(bytes) {
        if (!bytes) return 'N/A';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${['B', 'KB', 'MB', 'GB', 'TB'][i]}`;
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        try {
            const date = new Date(dateString);
            const diff = (new Date() - date) / (1000 * 60 * 60 * 24);
            if (diff < 1) return 'Today';
            if (diff < 30) return `${Math.floor(diff)} days ago`;
            if (diff < 365) return `${Math.floor(diff / 30)} months ago`;
            return `${Math.floor(diff / 365)} years ago`;
        } catch {
            return 'Unknown';
        }
    }

    populateModels(providerType, models) {
        const modelSelect = document.getElementById(`${providerType}_model_dropdown`);
        if (!modelSelect) return;

        const filterType = providerType === 'text' ? 'text-generation' : 'embedding';
        const filtered = models.filter(m => m.type === filterType);

        modelSelect.innerHTML = `<option value="">Select a ${providerType} model...</option>`;
        filtered.forEach(model => {
            const option = new Option(model.name, model.name);
            Object.assign(option.dataset, model);
            modelSelect.add(option);
        });
        modelSelect.disabled = false;
    }

    onTextModelChange(selectElement) {
        this.onModelChange('text', selectElement);
    }

    onEmbeddingModelChange(selectElement) {
        this.onModelChange('embedding', selectElement);
        const selectedModel = selectElement.value;
        if (selectedModel) {
            this.syncEmbeddingModelToAnythingLLM(selectedModel);
        }
    }

    onModelChange(modelType, selectElement) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        const hiddenInput = document.getElementById(modelType === 'text' ? 'llm_model' : 'llm_embedding_model');
        const modelInfo = document.getElementById(`${modelType}-model-info`);

        if (selectedOption && selectedOption.value) {
            if (hiddenInput) {
                hiddenInput.value = selectedOption.value;
                this.configManager.saveField(hiddenInput);
            }
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
        } else if (modelInfo) {
            modelInfo.classList.add('hidden');
        }
    }

    syncEmbeddingModelToAnythingLLM(embeddingModel) {
        const provider = document.getElementById(
            document.getElementById('use_same_provider')?.checked ? 'text_provider' : 'embedding_provider'
        )?.value || 'ollama';

        const modelField = document.getElementById('anythingllm_embedding_model');
        const providerField = document.getElementById('anythingllm_embedding_provider');

        if (modelField) {
            modelField.value = embeddingModel;
            this.configManager.saveField(modelField);
        }
        if (providerField) {
            providerField.value = provider;
            this.configManager.saveField(providerField);
        }
        utils.showNotification(`Synced ${embeddingModel} to AnythingLLM`, 'success');
    }

    refreshEmbeddingModels() {
        const useSame = document.getElementById('use_same_provider')?.checked;
        const prefix = useSame ? 'text' : 'embedding';
        const provider = document.getElementById(`${prefix}_provider`)?.value;
        const baseUrl = document.getElementById(`${prefix}_base_url`)?.value;
        const apiKey = document.getElementById(`${prefix}_api_key`)?.value;

        if (!baseUrl) {
            utils.showNotification('Please configure provider first', 'warning');
            return;
        }
        this.modelCache.delete(`embedding:${provider}:${baseUrl}`);
        this.loadModels('embedding', provider, baseUrl, apiKey);
    }

    clearModels(providerType) {
        const modelSelect = document.getElementById(`${providerType}_model_dropdown`);
        if (modelSelect) {
            modelSelect.innerHTML = '<option value="">Configure provider first</option>';
            modelSelect.disabled = true;
        }
        const hiddenInput = document.getElementById(providerType === 'text' ? 'llm_model' : 'llm_embedding_model');
        if (hiddenInput) hiddenInput.value = '';
        const modelInfo = document.getElementById(`${providerType}-model-info`);
        if (modelInfo) modelInfo.classList.add('hidden');
    }

    toggleApiKeyVisibility(providerType) {
        const field = document.getElementById(`${providerType}_api_key`);
        if (field) {
            field.type = field.type === 'password' ? 'text' : 'password';
        }
    }

    toggleAdvancedSettings(settingsType) {
        document.getElementById(`${settingsType}-advanced-settings`)?.classList.toggle('hidden');
    }

    updateConnectionStatus(providerType, status, text) {
        const dot = document.getElementById(`${providerType}-connection-status-dot`);
        const statusText = document.getElementById(`${providerType}-connection-status-text`);
        if (dot) {
            dot.className = 'inline-block w-2 h-2 rounded-full mr-2';
            const colors = {
                connected: ['bg-green-500'],
                testing: ['bg-yellow-500', 'animate-pulse'],
                error: ['bg-red-500']
            };
            const statusClasses = colors[status] || ['bg-gray-400'];
            statusClasses.forEach(cls => dot.classList.add(cls));
        }
        if (statusText) statusText.textContent = text;
    }

    showConnectionResults(providerType, message, type) {
        const container = document.getElementById(`${providerType}-connection-test-results`);
        if (!container) return;
        const colors = { info: 'blue', success: 'green', error: 'red' };
        container.className = `mt-4 p-3 rounded-md border bg-${colors[type]}-50 border-${colors[type]}-200 text-${colors[type]}-800`;
        container.innerHTML = message;
        container.classList.remove('hidden');
    }

    showModelLoading(providerType, show) {
        document.getElementById(`${providerType}-model-loading`)?.classList.toggle('hidden', !show);
        const modelSelect = document.getElementById(`${providerType}_model_dropdown`);
        if (modelSelect) modelSelect.disabled = show;
    }

    getModelsFromCache(key) {
        const cached = this.modelCache.get(key);
        return (cached && Date.now() - cached.timestamp < this.cacheTTL) ? cached.models : null;
    }

    setModelsCache(key, models) {
        this.modelCache.set(key, { models, timestamp: Date.now() });
    }

    async testModelResponse() {
        const model = document.getElementById('llm_model').value;
        if (!model) {
            utils.showNotification('Please select a text model first', 'warning');
            return;
        }
        
        const provider = document.getElementById('text_provider')?.value;
        const baseUrl = document.getElementById('text_base_url')?.value;
        const apiKey = document.getElementById('text_api_key')?.value;

        const testButton = document.getElementById('test-model-response');
        if (testButton) {
            testButton.disabled = true;
            testButton.textContent = 'Testing...';
        }

        this.showModelTestResults('Testing text generation model...', 'info');
        
        try {
            const data = await api.post('/llm/test-model', {
                provider, base_url: baseUrl, api_key: apiKey, model,
                prompt: "Hello, this is a test message. Please respond briefly."
            });

            if (data.success) {
                const time = data.response_time ? `${Math.round(data.response_time * 1000)}ms` : 'N/A';
                const formattedMessage = `
                    <div class="space-y-2">
                        <div class="font-semibold text-green-800">✓ Success!</div>
                        <div><span class="font-medium">Response:</span></div>
                        <div class="bg-white bg-opacity-50 p-2 rounded border text-sm font-mono whitespace-pre-wrap">${data.model_response}</div>
                        <div class="text-sm"><span class="font-medium">Time:</span> ${time}</div>
                    </div>
                `;
                this.showModelTestResults(formattedMessage, 'success');
            } else {
                throw new Error(data.message || 'Model test failed');
            }
        } catch (error) {
            const errorMessage = `
                <div class="space-y-2">
                    <div class="font-semibold text-red-800">⚠️ Test Failed</div>
                    <div class="bg-white bg-opacity-50 p-2 rounded border text-sm">${error.message}</div>
                </div>
            `;
            this.showModelTestResults(errorMessage, 'error');
        } finally {
            if (testButton) {
                testButton.disabled = false;
                testButton.textContent = 'Test Model Response';
            }
        }
    }

    showModelTestResults(message, type) {
        const container = document.getElementById('model-test-results');
        if (!container) return;
        const colors = { info: 'blue', success: 'green', error: 'red' };
        container.className = `mt-4 p-3 rounded-md border bg-${colors[type]}-50 border-${colors[type]}-200 text-${colors[type]}-800`;
        container.innerHTML = message;
        container.classList.remove('hidden');
    }

    setAILLMConfig(config) {
        // This method is now primarily for initial population.
        // The main configManager handles populating most fields.
        const sharingCheckbox = document.getElementById('use_same_provider');
        if (sharingCheckbox && config.use_same_provider !== undefined) {
            sharingCheckbox.checked = config.use_same_provider;
        }

        // Defer provider setup until after main config is initialized
        // This prevents race conditions where configManager is null.
    }
}

// Global AI/LLM config manager instance
window.aiLLMManager = new AILLMConfigManager();