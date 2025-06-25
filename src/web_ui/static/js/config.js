// Configuration Management Class - SystemConfiguration Integration
class ConfigManager {
    constructor() {
        this.originalConfig = {};
        this.isDirty = false;
        this.isLoading = false;
        this.accordionState = {
            'app-settings': true,  // Expanded by default
            'service-config': false,
            'cache-config': false,
            'ai-config': false
        };
    }

    async init() {
        try {
            await this.loadSystemConfiguration();
            this.setupAccordions();
            this.bindEvents();
            this.setupFormValidation();
            
            // Initialize AI/LLM configuration manager
            if (window.aiLLMManager) {
                window.aiLLMManager.init();
            }
        } catch (error) {
            console.error('Configuration initialization failed:', error);
            utils.showNotification('Failed to load system configuration', 'error');
        }
    }

    async loadSystemConfiguration() {
        this.isLoading = true;
        try {
            console.log('Loading system configuration from /api/v1/config');
            const systemConfig = await api.get('/config');
            console.log('Loaded system configuration:', systemConfig);
            
            this.originalConfig = JSON.parse(JSON.stringify(systemConfig));
            this.populateSystemConfigForm(systemConfig);
        } catch (error) {
            console.error('Failed to load system configuration:', error);
            utils.showNotification('Failed to load system configuration data', 'error');
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    async loadConfiguration() {
        // Legacy method - delegates to new system config loader
        return this.loadSystemConfiguration();
    }

    populateSystemConfigForm(systemConfig) {
        console.log('Populating form with SystemConfiguration:', systemConfig);
        
        // Application Settings (app section)
        const app = systemConfig.app || {};
        this.setFieldValue('environment', app.environment || 'production');
        this.setFieldValue('debug_mode', app.debug || false);
        this.setFieldValue('log_level', app.log_level || 'INFO');
        this.setFieldValue('workers', app.workers || 4);

        // Service Configuration (using app section for API settings)
        const apiHost = `http://${app.api_host || '0.0.0.0'}:${app.api_port || 8080}`;
        this.setFieldValue('api_host', apiHost);
        this.setFieldValue('api_timeout', 30); // Default timeout
        this.setFieldValue('websocket_url', `ws://${app.api_host || '0.0.0.0'}:${app.web_port || 8081}/ws/updates`);
        this.setFieldValue('max_retries', 3); // Default retries

        // Cache Management (redis section)
        const redis = systemConfig.redis || {};
        this.setFieldValue('cache_ttl', systemConfig.ai?.cache_ttl_seconds || 3600);
        this.setFieldValue('cache_max_size', 1000); // Default size
        this.setFieldValue('auto_refresh', true); // Default enabled
        this.setFieldValue('refresh_interval', 300); // Default interval

        // AI/LLM Settings - delegate to AI/LLM manager with full SystemConfiguration
        if (window.aiLLMManager) {
            window.aiLLMManager.setSystemConfig(systemConfig);
        } else {
            // Fallback if AI/LLM manager not available
            const ai = systemConfig.ai || {};
            const ollama = ai.ollama || {};
            this.setFieldValue('llm_provider', ai.primary_provider || 'ollama');
            this.setFieldValue('llm_model', ollama.model || 'llama2');
            this.setFieldValue('max_tokens', ollama.max_tokens || 4096);
            this.setFieldValue('temperature', ollama.temperature || 0.7);
        }
    }

    populateForm(config) {
        // Legacy method - check if this is SystemConfiguration or legacy format
        if (config.app && config.ai && config.redis) {
            // This is SystemConfiguration format
            return this.populateSystemConfigForm(config);
        } else {
            // This is legacy format - convert to SystemConfiguration-like structure
            const systemConfig = {
                app: {
                    environment: config.environment || 'production',
                    debug: config.debug_mode || false,
                    log_level: config.log_level || 'INFO',
                    workers: config.workers || 4,
                    api_host: '0.0.0.0',
                    api_port: 8080,
                    web_port: 8081
                },
                ai: {
                    primary_provider: config.llm_provider || 'ollama',
                    cache_ttl_seconds: config.cache_ttl || 3600,
                    ollama: {
                        model: config.llm_model || 'llama2',
                        max_tokens: config.max_tokens || 4096,
                        temperature: config.temperature || 0.7
                    }
                },
                redis: {}
            };
            return this.populateSystemConfigForm(systemConfig);
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

            // Set initial state
            if (this.accordionState[sectionId]) {
                content.classList.remove('hidden');
                icon.classList.remove('rotate-180');
            } else {
                content.classList.add('hidden');
                icon.classList.add('rotate-180');
            }

            trigger.addEventListener('click', () => {
                this.toggleAccordion(sectionId, content, icon);
            });
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

    bindEvents() {
        // Save button
        const saveButton = document.getElementById('save-config');
        if (saveButton) {
            saveButton.addEventListener('click', () => this.saveConfiguration());
        }

        // Reset button
        const resetButton = document.getElementById('reset-config');
        if (resetButton) {
            resetButton.addEventListener('click', () => this.showResetModal());
        }

        // Reset modal events
        const confirmReset = document.getElementById('confirm-reset');
        const cancelReset = document.getElementById('cancel-reset');
        
        if (confirmReset) {
            confirmReset.addEventListener('click', () => this.resetConfiguration());
        }
        
        if (cancelReset) {
            cancelReset.addEventListener('click', () => utils.hideModal('reset-modal'));
        }

        // Form change detection
        const form = document.getElementById('config-form');
        if (form) {
            form.addEventListener('input', () => this.onFormChange());
            form.addEventListener('change', () => this.onFormChange());
        }

        // Close modal on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                utils.hideModal('reset-modal');
            }
        });
    }

    setupFormValidation() {
        // Workers validation
        const workersField = document.getElementById('workers');
        if (workersField) {
            workersField.addEventListener('input', () => this.validateWorkers());
        }

        // URL validation
        const urlFields = ['api_host', 'websocket_url'];
        urlFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('blur', () => this.validateUrl(fieldId));
            }
        });

        // Number validation
        const numberFields = ['api_timeout', 'max_retries', 'cache_ttl', 'cache_max_size', 'refresh_interval', 'max_tokens'];
        numberFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('input', () => this.validateNumber(fieldId));
            }
        });

        // Temperature validation
        const temperatureField = document.getElementById('temperature');
        if (temperatureField) {
            temperatureField.addEventListener('input', () => this.validateTemperature());
        }
    }

    validateWorkers() {
        const field = document.getElementById('workers');
        const errorElement = document.getElementById('workers-error');
        
        if (!field) {
            console.error('❌ Workers field not found');
            return false;
        }
        
        const value = parseInt(field.value);
        console.log(`🔢 Validating workers: value="${field.value}", parsed=${value}`);

        if (value < 1 || value > 16) {
            console.log(`❌ Workers validation failed: ${value} not between 1-16`);
            field.classList.add('border-red-500');
            if (errorElement) errorElement.classList.remove('hidden');
            return false;
        } else {
            console.log(`✅ Workers validation passed: ${value}`);
            field.classList.remove('border-red-500');
            if (errorElement) errorElement.classList.add('hidden');
            return true;
        }
    }

    validateUrl(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) {
            console.error(`❌ URL field not found: ${fieldId}`);
            return false;
        }

        console.log(`🔗 Validating URL field "${fieldId}": value="${field.value}"`);
        
        if (!field.value) {
            console.log(`❌ URL validation failed for ${fieldId}: empty value`);
            field.classList.add('border-red-500');
            return false;
        }

        try {
            new URL(field.value);
            console.log(`✅ URL validation passed for ${fieldId}: ${field.value}`);
            field.classList.remove('border-red-500');
            return true;
        } catch (error) {
            console.log(`❌ URL validation failed for ${fieldId}: invalid URL - ${error.message}`);
            field.classList.add('border-red-500');
            return false;
        }
    }

    validateNumber(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) {
            console.error(`❌ Number field not found: ${fieldId}`);
            return false;
        }

        const value = parseFloat(field.value);
        const min = parseFloat(field.getAttribute('min')) || 0;
        const max = parseFloat(field.getAttribute('max')) || Infinity;
        
        console.log(`🔢 Validating number field "${fieldId}": value="${field.value}", parsed=${value}, min=${min}, max=${max}`);

        if (!field.value) {
            console.log(`❌ Number validation failed for ${fieldId}: empty value`);
            field.classList.add('border-red-500');
            return false;
        }

        if (isNaN(value) || value < min || value > max) {
            console.log(`❌ Number validation failed for ${fieldId}: ${value} not between ${min}-${max}`);
            field.classList.add('border-red-500');
            return false;
        } else {
            console.log(`✅ Number validation passed for ${fieldId}: ${value}`);
            field.classList.remove('border-red-500');
            return true;
        }
    }

    validateTemperature() {
        const field = document.getElementById('temperature');
        const value = parseFloat(field.value);

        if (isNaN(value) || value < 0 || value > 2) {
            field.classList.add('border-red-500');
            return false;
        } else {
            field.classList.remove('border-red-500');
            return true;
        }
    }

    validateForm() {
        console.log('🔍 Starting form validation...');
        let isValid = true;
        const validationResults = {};

        // Clear previous global error
        this.hideGlobalError();

        // Validate basic config fields
        console.log('📋 Validating basic configuration fields...');
        
        validationResults.workers = this.validateWorkers();
        console.log(`  - Workers: ${validationResults.workers}`);
        isValid &= validationResults.workers;
        
        validationResults.api_host = this.validateUrl('api_host');
        console.log(`  - API Host: ${validationResults.api_host}`);
        isValid &= validationResults.api_host;
        
        validationResults.websocket_url = this.validateUrl('websocket_url');
        console.log(`  - WebSocket URL: ${validationResults.websocket_url}`);
        isValid &= validationResults.websocket_url;
        
        validationResults.api_timeout = this.validateNumber('api_timeout');
        console.log(`  - API Timeout: ${validationResults.api_timeout}`);
        isValid &= validationResults.api_timeout;
        
        validationResults.max_retries = this.validateNumber('max_retries');
        console.log(`  - Max Retries: ${validationResults.max_retries}`);
        isValid &= validationResults.max_retries;
        
        validationResults.cache_ttl = this.validateNumber('cache_ttl');
        console.log(`  - Cache TTL: ${validationResults.cache_ttl}`);
        isValid &= validationResults.cache_ttl;
        
        validationResults.cache_max_size = this.validateNumber('cache_max_size');
        console.log(`  - Cache Max Size: ${validationResults.cache_max_size}`);
        isValid &= validationResults.cache_max_size;
        
        validationResults.refresh_interval = this.validateNumber('refresh_interval');
        console.log(`  - Refresh Interval: ${validationResults.refresh_interval}`);
        isValid &= validationResults.refresh_interval;
        
        validationResults.max_tokens = this.validateNumber('max_tokens');
        console.log(`  - Max Tokens: ${validationResults.max_tokens}`);
        isValid &= validationResults.max_tokens;
        
        validationResults.temperature = this.validateTemperature();
        console.log(`  - Temperature: ${validationResults.temperature}`);
        isValid &= validationResults.temperature;

        console.log('📊 Basic validation results:', validationResults);
        console.log(`📋 Basic validation overall: ${Boolean(isValid)}`);

        // Validate AI/LLM configuration if manager is available
        if (window.aiLLMManager) {
            console.log('🤖 Validating AI/LLM configuration...');
            const aiLLMValid = window.aiLLMManager.validateConfiguration();
            console.log(`🤖 AI/LLM validation result: ${aiLLMValid}`);
            isValid &= aiLLMValid;
        } else {
            console.warn('⚠️ AI/LLM manager not available - skipping AI/LLM validation');
        }

        console.log(`🎯 Final validation result: ${Boolean(isValid)}`);

        // Show global error if any validation failed
        if (!isValid) {
            console.log('❌ Validation failed - showing global error');
            this.showGlobalError();
            this.logFailedFields();
        } else {
            console.log('✅ All validation passed');
        }

        return Boolean(isValid);
    }

    onFormChange() {
        this.updateDirtyState();
        this.updateSaveButton();
    }

    updateDirtyState() {
        const currentConfig = this.getCurrentConfig();
        this.isDirty = JSON.stringify(currentConfig) !== JSON.stringify(this.originalConfig);
    }

    updateSaveButton() {
        const saveButton = document.getElementById('save-config');
        if (saveButton) {
            saveButton.disabled = !this.isDirty || this.isLoading;
            
            if (this.isDirty && !this.isLoading) {
                saveButton.classList.remove('opacity-50');
            } else {
                saveButton.classList.add('opacity-50');
            }
        }
    }

    getCurrentSystemConfig() {
        console.log('Building SystemConfiguration from form values');
        
        // Start with original config and update changed values
        const currentConfig = JSON.parse(JSON.stringify(this.originalConfig));
        
        // Update app section
        const app = currentConfig.app || {};
        app.environment = this.getFieldValue('environment') || 'production';
        app.debug = this.getFieldValue('debug_mode') || false;
        app.log_level = this.getFieldValue('log_level') || 'INFO';
        app.workers = this.getFieldValue('workers') || 4;
        currentConfig.app = app;

        // Update AI/LLM config from dedicated manager
        if (window.aiLLMManager) {
            const aiConfig = window.aiLLMManager.getSystemConfigUpdate();
            if (aiConfig) {
                currentConfig.ai = { ...currentConfig.ai, ...aiConfig };
            }
        } else {
            // Fallback for basic AI settings
            const ai = currentConfig.ai || {};
            const ollama = ai.ollama || {};
            
            ai.primary_provider = this.getFieldValue('llm_provider') || 'ollama';
            ollama.model = this.getFieldValue('llm_model') || 'llama2';
            ollama.max_tokens = this.getFieldValue('max_tokens') || 4096;
            ollama.temperature = this.getFieldValue('temperature') || 0.7;
            
            ai.ollama = ollama;
            currentConfig.ai = ai;
        }

        console.log('Built SystemConfiguration:', currentConfig);
        return currentConfig;
    }

    getCurrentConfig() {
        // Try to get full SystemConfiguration first
        if (this.originalConfig.app || this.originalConfig.ai) {
            return this.getCurrentSystemConfig();
        }
        
        // Legacy fallback
        const baseConfig = {
            environment: this.getFieldValue('environment'),
            debug_mode: this.getFieldValue('debug_mode'),
            log_level: this.getFieldValue('log_level'),
            workers: this.getFieldValue('workers'),
            api_host: this.getFieldValue('api_host'),
            api_timeout: this.getFieldValue('api_timeout'),
            websocket_url: this.getFieldValue('websocket_url'),
            max_retries: this.getFieldValue('max_retries'),
            cache_ttl: this.getFieldValue('cache_ttl'),
            cache_max_size: this.getFieldValue('cache_max_size'),
            auto_refresh: this.getFieldValue('auto_refresh'),
            refresh_interval: this.getFieldValue('refresh_interval')
        };

        // Get AI/LLM config from dedicated manager or fallback to basic fields
        const aiLLMConfig = window.aiLLMManager
            ? window.aiLLMManager.getAILLMConfig()
            : {
                llm_provider: this.getFieldValue('llm_provider'),
                llm_model: this.getFieldValue('llm_model'),
                max_tokens: this.getFieldValue('max_tokens'),
                temperature: this.getFieldValue('temperature')
            };

        return { ...baseConfig, ...aiLLMConfig };
    }

    async saveConfiguration() {
        if (!this.validateForm()) {
            utils.showNotification('Please fix validation errors before saving', 'error');
            return;
        }

        this.isLoading = true;
        this.updateSaveButton();
        this.showLoadingState();

        try {
            const config = this.getCurrentConfig();
            const response = await api.post('/config', config);
            
            this.originalConfig = { ...config };
            this.isDirty = false;
            this.updateSaveButton();
            this.hideLoadingState();
            
            utils.showNotification('Configuration saved successfully', 'success');
        } catch (error) {
            console.error('Failed to save configuration:', error);
            this.hideLoadingState();
            
            // Extract detailed error message from API response
            let errorMessage = 'Failed to save configuration';
            if (error.message && error.message.includes('HTTP')) {
                const statusMatch = error.message.match(/HTTP (\d+)/);
                if (statusMatch) {
                    const statusCode = parseInt(statusMatch[1]);
                    if (statusCode === 422) {
                        errorMessage = 'Invalid configuration data. Please check your inputs.';
                    } else if (statusCode === 400) {
                        errorMessage = 'Bad request. Please verify all required fields are filled correctly.';
                    } else if (statusCode >= 500) {
                        errorMessage = 'Server error. Please try again later.';
                    }
                }
            }
            
            utils.showNotification(errorMessage, 'error', 10000);
            this.highlightErrorFields();
        } finally {
            this.isLoading = false;
            this.updateSaveButton();
        }
    }

    showResetModal() {
        utils.showModal('reset-modal');
    }

    async resetConfiguration() {
        utils.hideModal('reset-modal');
        
        try {
            this.populateForm(this.originalConfig);
            this.isDirty = false;
            this.updateSaveButton();
            this.clearValidationErrors();
            
            utils.showNotification('Configuration reset to last saved values', 'info');
        } catch (error) {
            console.error('Failed to reset configuration:', error);
            utils.showNotification('Failed to reset configuration', 'error');
        }
    }

    clearValidationErrors() {
        const form = document.getElementById('config-form');
        if (!form) return;

        const errorFields = form.querySelectorAll('.border-red-500');
        errorFields.forEach(field => {
            field.classList.remove('border-red-500');
        });

        const errorMessages = form.querySelectorAll('.text-red-600:not(.hidden)');
        errorMessages.forEach(message => {
            message.classList.add('hidden');
        });
    }

    showLoadingState() {
        const saveButton = document.getElementById('save-config');
        if (saveButton) {
            const originalText = saveButton.textContent;
            saveButton.innerHTML = `
                <svg class="animate-spin -ml-1 mr-3 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
            `;
        }
    }

    hideLoadingState() {
        const saveButton = document.getElementById('save-config');
        if (saveButton) {
            saveButton.innerHTML = 'Save Configuration';
        }
    }

    highlightErrorFields() {
        // Re-run validation to highlight problematic fields
        this.validateForm();
        
        // Show a visual indicator that there are errors
        const form = document.getElementById('config-form');
        if (form) {
            const errorFields = form.querySelectorAll('.border-red-500');
            if (errorFields.length > 0) {
                // Scroll to first error field
                errorFields[0].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
                errorFields[0].focus();
            }
        }
    }

    showGlobalError() {
        const errorAlert = document.getElementById('validation-error-alert');
        if (errorAlert) {
            errorAlert.classList.remove('hidden');
        }
    }

    hideGlobalError() {
        const errorAlert = document.getElementById('validation-error-alert');
        if (errorAlert) {
            errorAlert.classList.add('hidden');
        }
    }

    logFailedFields() {
        console.log('🔍 Analyzing failed validation fields...');
        const form = document.getElementById('config-form');
        if (!form) {
            console.error('❌ Config form not found');
            return;
        }

        const failedFields = form.querySelectorAll('.border-red-500');
        console.log(`📊 Found ${failedFields.length} fields with validation errors:`);
        
        failedFields.forEach((field, index) => {
            const fieldName = field.id || field.name || 'unknown';
            const fieldValue = field.value || '';
            const fieldType = field.type || 'unknown';
            console.log(`  ${index + 1}. Field: "${fieldName}" (${fieldType}) = "${fieldValue}"`);
            
            // Check if there's an associated error message
            const errorElement = document.getElementById(`${fieldName}-error`);
            if (errorElement && !errorElement.classList.contains('hidden')) {
                console.log(`     Error message: "${errorElement.textContent}"`);
            }
        });

        // Also log any visible error messages
        const visibleErrors = form.querySelectorAll('.text-red-600:not(.hidden)');
        console.log(`📋 Found ${visibleErrors.length} visible error messages:`);
        
        visibleErrors.forEach((error, index) => {
            console.log(`  ${index + 1}. "${error.textContent}"`);
        });
    }
}

// Global config manager instance
let configManager;

// Initialize configuration manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    configManager = new ConfigManager();
    configManager.init();
});

// Warn about unsaved changes before leaving
window.addEventListener('beforeunload', (e) => {
    if (configManager && configManager.isDirty) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
    }
});