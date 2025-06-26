// Configuration Management Class - Refactored for "Save-on-Change"
class ConfigManager {
    constructor() {
        this.isLoading = false;
        this.accordionState = {
            'app-settings': false,
            'cache-config': false,
            'ai-config': true
        };

        // Centralized key map for frontend-backend alignment
        this.keyMap = {
            environment: "app.environment",
            debug_mode: "app.debug",
            log_level: "app.log_level",
            workers: "app.workers",
            api_host: "app.api_host",
            api_timeout: "app.api_timeout",
            websocket_url: "app.websocket_url",
            max_retries: "app.max_retries",
            auto_refresh: "app.auto_refresh",
            refresh_interval: "app.refresh_interval",
            cache_ttl: "ai.cache_ttl_seconds",
            cache_max_size: "redis.max_connections",
            use_same_provider: "ai.use_same_provider",
            text_provider: "ai.text_provider",
            text_base_url: "ai.text_base_url",
            text_api_key: "ai.text_api_key",
            llm_model: "ai.llm_model",
            embedding_provider: "ai.embedding_provider",
            embedding_base_url: "ai.embedding_base_url",
            embedding_api_key: "ai.embedding_api_key",
            llm_embedding_model: "ai.llm_embedding_model",
            text_max_tokens: "ai.text_max_tokens",
            text_temperature: "ai.text_temperature",
            text_top_p: "ai.text_top_p",
            text_top_k: "ai.text_top_k",
            text_timeout: "ai.text_timeout",
            text_retries: "ai.text_retries",
            embedding_batch_size: "ai.embedding_batch_size",
            embedding_timeout: "ai.embedding_timeout",
            embedding_retries: "ai.embedding_retries",
            embedding_chunk_size: "ai.embedding_chunk_size",
            embedding_overlap: "ai.embedding_overlap",
            embedding_normalize: "ai.embedding_normalize",
            anythingllm_embedding_model: "anythingllm.embedding_model",
            anythingllm_embedding_provider: "anythingllm.embedding_provider"
        };
        
        this.invertedKeyMap = Object.fromEntries(Object.entries(this.keyMap).map(([k, v]) => [v, k]));
    }

    async init() {
        try {
            await this.loadConfiguration();
            this.setupAccordions();
            this.bindSaveOnChangeEvents();
            this.setupFormValidation();
            
            if (window.aiLLMManager) {
                window.aiLLMManager.init(this); // Pass configManager instance
            }
        } catch (error) {
            console.error('Configuration initialization failed:', error);
            utils.showNotification('Failed to load configuration', 'error');
        }
    }

    async loadConfiguration() {
        this.isLoading = true;
        try {
            const response = await api.get('/config');
            const config = {};
            if (response && Array.isArray(response.items)) {
                response.items.forEach(item => {
                    const frontendKey = this.invertedKeyMap[item.key];
                    if (frontendKey) {
                        config[frontendKey] = item.value;
                    } else {
                        console.warn(`Unmapped configuration key from backend: ${item.key}`);
                    }
                });
            }
            this.populateForm(config);
        } catch (error) {
            console.error('Failed to load configuration:', error);
            utils.showNotification('Failed to load configuration data', 'error');
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    populateForm(config) {
        Object.keys(this.keyMap).forEach(fieldName => {
            if (config[fieldName] !== undefined) {
                this.setFieldValue(fieldName, config[fieldName]);
            }
        });

        if (window.aiLLMManager) {
            window.aiLLMManager.setAILLMConfig(config);
        }
    }

    setFieldValue(fieldName, value) {
        const field = document.getElementById(fieldName);
        if (!field) return;

        if (field.type === 'checkbox') {
            field.checked = Boolean(value);
        } else {
            field.value = value;
        }
    }

    getFieldValue(fieldName) {
        const field = document.getElementById(fieldName);
        if (!field) return null;

        if (field.type === 'checkbox') {
            return field.checked;
        } else if (field.type === 'number') {
            return parseFloat(field.value) || 0;
        } else {
            return field.value;
        }
    }

    setupAccordions() {
        const triggers = document.querySelectorAll('[data-accordion-trigger]');
        triggers.forEach(trigger => {
            const sectionId = trigger.getAttribute('data-accordion-trigger');
            const content = document.querySelector(`[data-accordion-content="${sectionId}"]`);
            const icon = trigger.querySelector('svg');
            if (!content || !icon) return;

            if (this.accordionState[sectionId]) {
                content.classList.remove('hidden');
                icon.classList.remove('rotate-180');
            } else {
                content.classList.add('hidden');
                icon.classList.add('rotate-180');
            }

            trigger.addEventListener('click', () => this.toggleAccordion(sectionId, content, icon));
        });
    }

    toggleAccordion(sectionId, content, icon) {
        const isExpanded = !content.classList.contains('hidden');
        if (isExpanded) {
            content.classList.add('hidden');
            icon.classList.add('rotate-180');
            this.accordionState[sectionId] = false;
        } else {
            content.classList.remove('hidden');
            icon.classList.remove('rotate-180');
            this.accordionState[sectionId] = true;
        }
    }

    bindSaveOnChangeEvents() {
        const form = document.getElementById('config-form');
        if (!form) return;

        // Bind events to all relevant form elements
        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
            const eventType = (input.type === 'checkbox' || input.tagName === 'SELECT') ? 'change' : 'blur';
            input.addEventListener(eventType, () => this.saveField(input));
        });

        // Refresh button
        const refreshButton = document.getElementById('refresh-config');
        if (refreshButton) {
            refreshButton.addEventListener('click', async () => {
                await this.loadConfiguration();
                this.clearValidationErrors();
                utils.showNotification('Configuration refreshed from server', 'info');
            });
        }
    }

    async saveField(fieldElement) {
        if (!fieldElement || !fieldElement.id) return;

        const fieldName = fieldElement.id;
        const backendKey = this.keyMap[fieldName];
        
        if (!backendKey) {
            console.warn(`No backend key found for field: ${fieldName}`);
            return;
        }

        // Validate field before saving
        if (!this.validateField(fieldName)) {
            utils.showNotification(`Invalid value for ${fieldName}. Not saved.`, 'error');
            return;
        }

        const value = this.getFieldValue(fieldName);

        try {
            const response = await api.post('/config', { key: backendKey, value: value });
            if (response.status === 'success') {
                this.showSaveConfirmation(fieldElement);
            } else {
                throw new Error(response.detail || 'Save failed');
            }
        } catch (error) {
            console.error(`Failed to save ${fieldName}:`, error);
            utils.showNotification(`Error saving ${fieldName}: ${error.message}`, 'error');
            this.showSaveError(fieldElement);
        }
    }

    showSaveConfirmation(fieldElement) {
        let feedbackEl = fieldElement.nextElementSibling;
        if (!feedbackEl || !feedbackEl.classList.contains('save-feedback')) {
            feedbackEl = document.createElement('span');
            feedbackEl.className = 'save-feedback ml-2 text-green-500';
            fieldElement.parentNode.insertBefore(feedbackEl, fieldElement.nextSibling);
        }
        
        feedbackEl.innerHTML = '✓ Saved';
        feedbackEl.classList.remove('text-red-500');
        feedbackEl.classList.add('text-green-500');
        
        setTimeout(() => {
            feedbackEl.innerHTML = '';
        }, 2000);
    }

    showSaveError(fieldElement) {
        let feedbackEl = fieldElement.nextElementSibling;
        if (!feedbackEl || !feedbackEl.classList.contains('save-feedback')) {
            feedbackEl = document.createElement('span');
            feedbackEl.className = 'save-feedback ml-2 text-red-500';
            fieldElement.parentNode.insertBefore(feedbackEl, fieldElement.nextSibling);
        }
        
        feedbackEl.innerHTML = '✗ Error';
        feedbackEl.classList.remove('text-green-500');
        feedbackEl.classList.add('text-red-500');
    }

    setupFormValidation() {
        Object.keys(this.keyMap).forEach(fieldName => {
            const field = document.getElementById(fieldName);
            if (field) {
                field.addEventListener('input', () => this.validateField(fieldName));
            }
        });
    }

    validateField(fieldName) {
        switch(fieldName) {
            case 'workers': return this.validateWorkers();
            case 'api_host':
            case 'websocket_url': return this.validateUrl(fieldName);
            case 'api_timeout':
            case 'max_retries':
            case 'cache_ttl':
            case 'cache_max_size':
            case 'refresh_interval':
            case 'text_max_tokens':
            case 'text_top_k':
            case 'text_timeout':
            case 'text_retries':
            case 'embedding_batch_size':
            case 'embedding_timeout':
            case 'embedding_retries':
            case 'embedding_chunk_size':
            case 'embedding_overlap':
                return this.validateNumber(fieldName);
            case 'text_temperature':
            case 'text_top_p':
                return this.validateFloat(fieldName);
            default:
                return true; // No validation for other fields
        }
    }

    validateWorkers() {
        const field = document.getElementById('workers');
        const errorElement = document.getElementById('workers-error');
        const value = parseInt(field.value);

        if (value < 1 || value > 16) {
            field.classList.add('border-red-500');
            if (errorElement) errorElement.classList.remove('hidden');
            return false;
        } else {
            field.classList.remove('border-red-500');
            if (errorElement) errorElement.classList.add('hidden');
            return true;
        }
    }

    validateUrl(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return true;
        try {
            new URL(field.value);
            field.classList.remove('border-red-500');
            return true;
        } catch {
            field.classList.add('border-red-500');
            return false;
        }
    }

    validateNumber(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return true;
        const value = parseInt(field.value);
        const min = parseInt(field.getAttribute('min')) || 0;
        const max = parseInt(field.getAttribute('max')) || Infinity;

        if (isNaN(value) || value < min || value > max) {
            field.classList.add('border-red-500');
            return false;
        } else {
            field.classList.remove('border-red-500');
            return true;
        }
    }

    validateFloat(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return true;
        const value = parseFloat(field.value);
        const min = parseFloat(field.getAttribute('min')) || 0.0;
        const max = parseFloat(field.getAttribute('max')) || 2.0;

        if (isNaN(value) || value < min || value > max) {
            field.classList.add('border-red-500');
            return false;
        } else {
            field.classList.remove('border-red-500');
            return true;
        }
    }

    clearValidationErrors() {
        const form = document.getElementById('config-form');
        if (!form) return;
        const errorFields = form.querySelectorAll('.border-red-500');
        errorFields.forEach(field => field.classList.remove('border-red-500'));
        const errorMessages = form.querySelectorAll('.text-red-600:not(.hidden)');
        errorMessages.forEach(message => message.classList.add('hidden'));
    }
}

// Global config manager instance
let configManager;

// Initialize configuration manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    configManager = new ConfigManager();
    configManager.init();

    // Listen for config_update events from WebSocket and reload config
    if (window.wsManager) {
        window.wsManager.on('config_update', async (data) => {
            console.log('Config update received from WebSocket:', data);
            // Optimistically update the field value without a full reload
            const frontendKey = configManager.invertedKeyMap[data.key];
            if (frontendKey) {
                configManager.setFieldValue(frontendKey, data.value);
                utils.showNotification(`Setting '${data.key}' updated from server`, 'info');
            }
        });
    }
});