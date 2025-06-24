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
        
        // Simulate API call - replace with actual implementation
        return new Promise((resolve) => {
            setTimeout(() => {
                const responseTime = Date.now() - startTime;
                // Mock successful response for demo
                resolve({
                    success: true,
                    responseTime,
                    modelsCount: Math.floor(Math.random() * 10) + 5
                });
            }, 1000 + Math.random() * 2000);
        });
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
        // Mock model data - replace with actual API call
        const mockModels = [
            {
                name: 'llama3.2:3b',
                description: '3.2B parameters, Instruct-tuned',
                size: '2.0 GB',
                modified: '2 days ago'
            },
            {
                name: 'llama3.2:7b',
                description: '7B parameters, Instruct-tuned',
                size: '4.1 GB',
                modified: '5 days ago'
            },
            {
                name: 'codellama:13b',
                description: '13B parameters, Code generation',
                size: '7.3 GB',
                modified: '1 week ago'
            }
        ];

        return new Promise((resolve) => {
            setTimeout(() => resolve(mockModels), 500);
        });
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