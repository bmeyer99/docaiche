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
                    description: 'Ollama model',
                    size: this.formatSize(model.size) || 'N/A',
                    modified: this.formatDate(model.modified_at) || 'Unknown'
                }));
                
            case 'openai':
                return data.models.map(model => ({
                    name: model.name || model.id || '',
                    description: 'OpenAI model',
                    size: 'N/A',
                    modified: this.formatDate(model.created) || 'Unknown'
                }));
                
            case 'anthropic':
                return data.models.map(model => ({
                    name: model.name || '',
                    description: 'Anthropic model',
                    size: 'N/A',
                    modified: 'Unknown'
                }));
                
            default:
                return data.models.map(model => ({
                    name: model.name || model.id || 'Unknown',
                    description: model.description || 'Model',
                    size: this.formatSize(model.size) || 'N/A',
                    modified: this.formatDate(model.modified_at || model.created) || 'Unknown'
                }));
        }
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

        if (!model) {
            utils.showNotification('Please select a model first', 'warning');
            return;
        }

        utils.showNotification('Testing model response...', 'info');
        
        try {
            // Mock test response - replace with actual implementation
            await new Promise(resolve => setTimeout(resolve, 2000));
            utils.showNotification('Model test successful!', 'success');
        } catch (error) {
            utils.showNotification('Model test failed: ' + error.message, 'error');
        }
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
            llm_retries: parseInt(document.getElementById('llm_retries')?.value) || 3
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