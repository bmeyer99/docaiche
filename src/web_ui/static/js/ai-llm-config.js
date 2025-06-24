// AI/LLM Configuration Management Module
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
        this.isConnecting = false;
    }

    init() {
        this.bindAILLMEvents();
        this.setupProviderDefaults();
    }

    bindAILLMEvents() {
        // Provider change handler
        const providerSelect = document.getElementById('llm_provider');
        if (providerSelect) {
            providerSelect.addEventListener('change', () => this.onProviderChange());
        }

        // Test connection button
        const testButton = document.getElementById('test-connection');
        if (testButton) {
            testButton.addEventListener('click', () => this.testConnection());
        }

        // Refresh models button
        const refreshButton = document.getElementById('refresh-models');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => this.refreshModels());
        }

        // API key toggle visibility
        const toggleKeyButton = document.getElementById('toggle-api-key');
        if (toggleKeyButton) {
            toggleKeyButton.addEventListener('click', () => this.toggleApiKeyVisibility());
        }

        // Model selection handler
        const modelSelect = document.getElementById('llm_model_dropdown');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => this.onModelChange());
        }

        // Advanced settings toggle
        const advancedToggle = document.getElementById('toggle-advanced-settings');
        if (advancedToggle) {
            advancedToggle.addEventListener('click', () => this.toggleAdvancedSettings());
        }

        // Test model response button
        const testModelButton = document.getElementById('test-model-response');
        if (testModelButton) {
            testModelButton.addEventListener('click', () => this.testModelResponse());
        }
    }

    setupProviderDefaults() {
        const provider = document.getElementById('llm_provider')?.value || 'ollama';
        this.updateProviderDefaults(provider);
    }

    onProviderChange() {
        const provider = document.getElementById('llm_provider').value;
        this.updateProviderDefaults(provider);
        this.clearModels();
        this.updateConnectionStatus('disconnected', 'Not Configured');
    }

    updateProviderDefaults(provider) {
        const defaults = this.providerDefaults[provider];
        if (!defaults) return;

        const baseUrlField = document.getElementById('llm_base_url');
        const apiKeyField = document.getElementById('llm_api_key');
        const testButton = document.getElementById('test-connection');

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

    async testConnection() {
        if (this.isConnecting) return;

        const provider = document.getElementById('llm_provider').value;
        const baseUrl = document.getElementById('llm_base_url').value;
        const apiKey = document.getElementById('llm_api_key').value;

        if (!baseUrl) {
            utils.showNotification('Please enter a base URL', 'error');
            return;
        }

        this.isConnecting = true;
        this.updateConnectionStatus('testing', 'Testing...');
        this.showConnectionResults('Testing connection to ' + baseUrl, 'info');

        const testButton = document.getElementById('test-connection');
        if (testButton) {
            testButton.disabled = true;
            testButton.innerHTML = 'Testing...';
        }

        try {
            const response = await this.makeTestRequest(provider, baseUrl, apiKey);
            
            if (response.success) {
                this.updateConnectionStatus('connected', 'Connected');
                this.showConnectionResults(
                    `✓ Connection successful!<br>` +
                    `✓ Response time: ${response.responseTime}ms<br>` +
                    `✓ Found ${response.modelsCount} models`,
                    'success'
                );
                // Load models using the existing function but with real data
                await this.loadModels(provider, baseUrl, apiKey);
            } else {
                throw new Error(response.error || 'Connection failed');
            }
        } catch (error) {
            this.updateConnectionStatus('error', 'Connection Failed');
            this.showConnectionResults(
                `⚠️ Connection Failed<br><br>` +
                `Cannot reach endpoint at ${baseUrl}<br><br>` +
                `Details:<br>` +
                `• ${error.message}<br>` +
                `• Check if the service is running<br>` +
                `• Verify the URL is correct`,
                'error'
            );
        } finally {
            this.isConnecting = false;
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
            
            // Use backend proxy endpoint to avoid CSP issues
            const endpoint = '/api/v1/llm/test-connection';
            
            const requestData = {
                provider: provider,
                base_url: baseUrl,
                api_key: apiKey || null
            };
            
            console.log(`Making request to: ${endpoint}`);
            console.log('Request data:', requestData);
            
            // Create AbortController for timeout
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
            
            // Provide more specific error messages
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

    async loadModels(provider, baseUrl, apiKey) {
        const cacheKey = `${provider}:${baseUrl}`;
        const cached = this.getModelsFromCache(cacheKey);
        
        if (cached) {
            this.populateModels(cached);
            return;
        }

        this.showModelLoading(true);

        try {
            const models = await this.fetchModels(provider, baseUrl, apiKey);
            this.setModelsCache(cacheKey, models);
            this.populateModels(models);
        } catch (error) {
            console.error('Failed to load models:', error);
            utils.showNotification('Failed to load models', 'error');
        } finally {
            this.showModelLoading(false);
        }
    }

    async fetchModels(provider, baseUrl, apiKey) {
        try {
            // Use backend proxy endpoint to avoid CSP issues
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
            
            // Parse backend response format
            return this.parseBackendModelsResponse(data, provider);
            
        } catch (error) {
            console.error('Failed to fetch models:', error);
            throw new Error(`Failed to fetch models: ${error.message}`);
        }
    }

    parseModelsResponse(data, provider) {
        const models = [];
        
        switch (provider) {
            case 'ollama':
                // Ollama returns { models: [...] }
                if (data.models && Array.isArray(data.models)) {
                    return data.models.map(model => ({
                        name: model.name,
                        description: model.details?.family || 'Ollama model',
                        size: this.formatSize(model.size),
                        modified: this.formatDate(model.modified_at)
                    }));
                }
                break;
                
            case 'openai':
            case 'openai-compatible':
                // OpenAI API returns { data: [...] }
                if (data.data && Array.isArray(data.data)) {
                    return data.data.map(model => ({
                        name: model.id,
                        description: model.description || 'OpenAI model',
                        size: 'N/A',
                        modified: this.formatDate(model.created)
                    }));
                }
                break;
                
            default:
                // Try to handle generic format
                const modelArray = data.models || data.data || data;
                if (Array.isArray(modelArray)) {
                    return modelArray.map(model => ({
                        name: model.name || model.id || model.model,
                        description: model.description || model.details?.family || 'Model',
                        size: this.formatSize(model.size) || 'N/A',
                        modified: this.formatDate(model.modified_at || model.created) || 'Unknown'
                    }));
                }
        }
        
        return [];
    }

    parseBackendModelsResponse(data, provider) {
        // Parse models from backend API response format
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
        // Determine model type based on name patterns
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

    populateModels(models) {
        const modelSelect = document.getElementById('llm_model_dropdown');
        if (!modelSelect) return;

        // Clear existing options
        modelSelect.innerHTML = '<option value="">Select a model...</option>';

        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = model.name;
            option.dataset.description = model.description;
            option.dataset.size = model.size;
            option.dataset.modified = model.modified;
            modelSelect.appendChild(option);
        });

        modelSelect.disabled = false;
        const refreshButton = document.getElementById('refresh-models');
        if (refreshButton) {
            refreshButton.disabled = false;
        }
    }

    onModelChange() {
        const modelSelect = document.getElementById('llm_model_dropdown');
        const selectedOption = modelSelect.selectedOptions[0];
        const hiddenInput = document.getElementById('llm_model');
        const modelInfo = document.getElementById('model-info');

        if (selectedOption && selectedOption.value) {
            hiddenInput.value = selectedOption.value;
            
            // Check if this is an embedding model and auto-sync with AnythingLLM
            const modelType = this.getModelType(selectedOption.value);
            if (modelType === 'embedding') {
                this.syncEmbeddingModelToAnythingLLM(selectedOption.value);
            }
            
            // Show model information
            if (modelInfo) {
                const nameEl = document.getElementById('model-info-name');
                const descEl = document.getElementById('model-info-description');
                const sizeEl = document.getElementById('model-size');
                const modifiedEl = document.getElementById('model-modified');

                if (nameEl) nameEl.textContent = selectedOption.value;
                if (descEl) descEl.textContent = selectedOption.dataset.description || '';
                if (sizeEl) sizeEl.textContent = selectedOption.dataset.size || '';
                if (modifiedEl) modifiedEl.textContent = selectedOption.dataset.modified || '';

                modelInfo.classList.remove('hidden');
            }
        } else {
            hiddenInput.value = '';
            if (modelInfo) {
                modelInfo.classList.add('hidden');
            }
        }
    }

    syncEmbeddingModelToAnythingLLM(embeddingModel) {
        // Auto-sync embedding model selection to AnythingLLM configuration
        const provider = document.getElementById('llm_provider')?.value || 'ollama';
        
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
        utils.showNotification(`Embedding model ${embeddingModel} auto-synced to AnythingLLM`, 'success');
        
        // Trigger AnythingLLM configuration update
        this.updateAnythingLLMEmbeddingConfig(embeddingModel, provider);
    }

    async updateAnythingLLMEmbeddingConfig(embeddingModel, provider) {
        // Update AnythingLLM configuration via API
        try {
            const configData = {
                anythingllm: {
                    embedding_model: embeddingModel,
                    embedding_provider: provider
                }
            };
            
            const response = await fetch('/api/v1/config', {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configData)
            });
            
            if (response.ok) {
                console.log(`AnythingLLM embedding configuration updated: ${embeddingModel}`);
            } else {
                console.warn('Failed to update AnythingLLM embedding configuration');
            }
        } catch (error) {
            console.error('Error updating AnythingLLM embedding configuration:', error);
        }
    }

    refreshModels() {
        const provider = document.getElementById('llm_provider').value;
        const baseUrl = document.getElementById('llm_base_url').value;
        const apiKey = document.getElementById('llm_api_key').value;

        if (!baseUrl) {
            utils.showNotification('Please configure endpoint first', 'warning');
            return;
        }

        // Clear cache and reload
        const cacheKey = `${provider}:${baseUrl}`;
        this.modelCache.delete(cacheKey);
        this.loadModels(provider, baseUrl, apiKey);
    }

    clearModels() {
        const modelSelect = document.getElementById('llm_model_dropdown');
        const hiddenInput = document.getElementById('llm_model');
        const modelInfo = document.getElementById('model-info');

        if (modelSelect) {
            modelSelect.innerHTML = '<option value="">Configure endpoint first</option>';
            modelSelect.disabled = true;
        }

        if (hiddenInput) {
            hiddenInput.value = '';
        }

        if (modelInfo) {
            modelInfo.classList.add('hidden');
        }

        const refreshButton = document.getElementById('refresh-models');
        if (refreshButton) {
            refreshButton.disabled = true;
        }
    }

    toggleApiKeyVisibility() {
        const apiKeyField = document.getElementById('llm_api_key');
        const toggleButton = document.getElementById('toggle-api-key');
        
        if (apiKeyField && toggleButton) {
            const isPassword = apiKeyField.type === 'password';
            apiKeyField.type = isPassword ? 'text' : 'password';
            
            const svg = toggleButton.querySelector('svg');
            if (svg) {
                // Toggle eye icon state (you might want to change the SVG)
                svg.classList.toggle('text-gray-600');
            }
        }
    }

    toggleAdvancedSettings() {
        const content = document.getElementById('advanced-settings-content');
        const arrow = document.getElementById('advanced-settings-arrow');

        if (content && arrow) {
            const isHidden = content.classList.contains('hidden');
            
            if (isHidden) {
                content.classList.remove('hidden');
                arrow.style.transform = 'rotate(90deg)';
            } else {
                content.classList.add('hidden');
                arrow.style.transform = 'rotate(0deg)';
            }
        }
    }

    updateConnectionStatus(status, text) {
        const statusDot = document.getElementById('connection-status-dot');
        const statusText = document.getElementById('connection-status-text');

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

    showConnectionResults(message, type) {
        const resultsContainer = document.getElementById('connection-test-results');
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

    showModelLoading(show) {
        const loadingSpinner = document.getElementById('model-loading');
        const modelSelect = document.getElementById('llm_model_dropdown');

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
        const provider = document.getElementById('llm_provider').value;
        const model = document.getElementById('llm_model').value;
        const baseUrl = document.getElementById('llm_base_url').value;
        const apiKey = document.getElementById('llm_api_key').value;

        if (!model) {
            utils.showNotification('Please select a model first', 'warning');
            return;
        }

        if (!baseUrl) {
            utils.showNotification('Please configure the base URL first', 'warning');
            return;
        }

        // Check model type and test appropriately
        const modelType = this.getModelType(model);
        if (modelType === 'embedding') {
            return this.testEmbeddingModel(provider, baseUrl, apiKey, model, testButton, originalText);
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
            console.log('Request data:', requestData);
            
            // Create AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log('Model test request timed out');
                controller.abort();
            }, 45000); // 45 second timeout for model testing
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            console.log(`Model test response status: ${response.status}`);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Model test error response:', errorText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Model test response data:', data);
            
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
            
            // Provide more specific error messages
            if (error.name === 'AbortError') {
                errorMessage = 'Model test timed out after 45 seconds';
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Network error - check if the service is running and accessible';
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
            // Create results container if it doesn't exist
            const container = document.createElement('div');
            container.id = 'model-test-results';
            container.className = 'mt-4 p-3 rounded-md border hidden';
            
            // Insert after the test button
            const testButton = document.getElementById('test-model-response');
            if (testButton && testButton.parentNode) {
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

    getAILLMConfig() {
        return {
            llm_provider: document.getElementById('llm_provider')?.value || '',
            llm_base_url: document.getElementById('llm_base_url')?.value || '',
            llm_api_key: document.getElementById('llm_api_key')?.value || '',
            llm_model: document.getElementById('llm_model')?.value || '',
            max_tokens: parseInt(document.getElementById('max_tokens')?.value) || 2048,
            temperature: parseFloat(document.getElementById('temperature')?.value) || 0.7,
            top_p: parseFloat(document.getElementById('top_p')?.value) || 1.0,
            top_k: parseInt(document.getElementById('top_k')?.value) || 40,
            llm_timeout: parseInt(document.getElementById('llm_timeout')?.value) || 30,
            llm_retries: parseInt(document.getElementById('llm_retries')?.value) || 3,
            // AnythingLLM embedding configuration
            anythingllm_embedding_model: document.getElementById('anythingllm_embedding_model')?.value || '',
            anythingllm_embedding_provider: document.getElementById('anythingllm_embedding_provider')?.value || 'ollama'
        };
    }

    setAILLMConfig(config) {
        const fields = [
            'llm_provider', 'llm_base_url', 'llm_api_key', 'llm_model',
            'max_tokens', 'temperature', 'top_p', 'top_k', 'llm_timeout', 'llm_retries'
        ];

        fields.forEach(field => {
            const element = document.getElementById(field);
            if (element && config[field] !== undefined) {
                element.value = config[field];
            }
        });

        // Trigger provider change to set up defaults
        this.onProviderChange();
    }
}

// Global AI/LLM config manager instance
window.aiLLMManager = new AILLMConfigManager();
async testEmbeddingModel(provider, baseUrl, apiKey, model, testButton, originalText) {
        if (testButton) {
            testButton.disabled = true;
            testButton.textContent = 'Testing Embedding...';
        }

        this.showModelTestResults('Testing embedding model...', 'info');
        
        try {
            const endpoint = '/api/v1/llm/test-embedding';
            const requestData = {
                provider: provider,
                base_url: baseUrl,
                api_key: apiKey || null,
                model: model,
                text: "This is a test sentence for embedding generation."
            };
            
            console.log(`Testing embedding model ${model} on ${provider}`);
            console.log('Request data:', requestData);
            
            // Create AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log('Embedding test request timed out');
                controller.abort();
            }, 30000); // 30 second timeout for embedding testing
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            console.log(`Embedding test response status: ${response.status}`);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Embedding test error response:', errorText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Embedding test response data:', data);
            
            if (data.success) {
                const responseTime = data.response_time ? `${Math.round(data.response_time * 1000)}ms` : 'N/A';
                const dimensions = data.embedding_dimensions || 'Unknown';
                this.showModelTestResults(
                    `✓ Embedding model test successful!<br>` +
                    `✓ Model: ${data.model}<br>` +
                    `✓ Response time: ${responseTime}<br>` +
                    `✓ Embedding dimensions: ${dimensions}<br><br>` +
                    `<strong>Test Text:</strong><br>${data.text}<br><br>` +
                    `<strong>Result:</strong><br>Generated ${dimensions}-dimensional embedding vector`,
                    'success'
                );
                utils.showNotification('Embedding model test successful!', 'success');
            } else {
                throw new Error(data.message || 'Embedding model test failed');
            }
            
        } catch (error) {
            console.error('Embedding model test failed:', error);
            
            let errorMessage = error.message;
            
            // Provide more specific error messages
            if (error.name === 'AbortError') {
                errorMessage = 'Embedding test timed out after 30 seconds';
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Network error - check if the service is running and accessible';
            }
            
            this.showModelTestResults(
                `⚠️ Embedding Model Test Failed<br><br>` +
                `Model: ${model}<br>` +
                `Provider: ${provider}<br><br>` +
                `Error: ${errorMessage}<br><br>` +
                `Note: If this endpoint is not implemented yet, embedding models can still be used for AnythingLLM vector operations.`,
                'error'
            );
            utils.showNotification('Embedding model test failed: ' + errorMessage, 'error');
            
        } finally {
            if (testButton) {
                testButton.disabled = false;
                testButton.textContent = originalText;
            }
        }
    }