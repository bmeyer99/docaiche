// Configuration Management Class
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
            await this.loadConfiguration();
            this.setupAccordions();
            this.bindEvents();
            this.setupFormValidation();
        } catch (error) {
            console.error('Configuration initialization failed:', error);
            utils.showNotification('Failed to load configuration', 'error');
        }
    }

    async loadConfiguration() {
        this.isLoading = true;
        try {
            const config = await api.get('/config');
            this.originalConfig = { ...config };
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
        // Application Settings
        this.setFieldValue('environment', config.environment || 'development');
        this.setFieldValue('debug_mode', config.debug_mode || false);
        this.setFieldValue('log_level', config.log_level || 'INFO');
        this.setFieldValue('workers', config.workers || 4);

        // Service Configuration
        this.setFieldValue('api_host', config.api_host || 'http://localhost:8080');
        this.setFieldValue('api_timeout', config.api_timeout || 30);
        this.setFieldValue('websocket_url', config.websocket_url || 'ws://localhost:8080/ws');
        this.setFieldValue('max_retries', config.max_retries || 3);

        // Cache Management
        this.setFieldValue('cache_ttl', config.cache_ttl || 3600);
        this.setFieldValue('cache_max_size', config.cache_max_size || 1000);
        this.setFieldValue('auto_refresh', config.auto_refresh || true);
        this.setFieldValue('refresh_interval', config.refresh_interval || 300);

        // AI/LLM Settings
        this.setFieldValue('llm_provider', config.llm_provider || 'ollama');
        this.setFieldValue('llm_model', config.llm_model || 'llama2');
        this.setFieldValue('max_tokens', config.max_tokens || 2000);
        this.setFieldValue('temperature', config.temperature || 0.7);
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
        const value = parseInt(field.value);

        if (value < 1 || value > 16) {
            field.classList.add('border-red-500');
            errorElement.classList.remove('hidden');
            return false;
        } else {
            field.classList.remove('border-red-500');
            errorElement.classList.add('hidden');
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

        const value = parseFloat(field.value);
        const min = parseFloat(field.getAttribute('min')) || 0;
        const max = parseFloat(field.getAttribute('max')) || Infinity;

        if (isNaN(value) || value < min || value > max) {
            field.classList.add('border-red-500');
            return false;
        } else {
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
        let isValid = true;

        isValid &= this.validateWorkers();
        isValid &= this.validateUrl('api_host');
        isValid &= this.validateUrl('websocket_url');
        isValid &= this.validateNumber('api_timeout');
        isValid &= this.validateNumber('max_retries');
        isValid &= this.validateNumber('cache_ttl');
        isValid &= this.validateNumber('cache_max_size');
        isValid &= this.validateNumber('refresh_interval');
        isValid &= this.validateNumber('max_tokens');
        isValid &= this.validateTemperature();

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

    getCurrentConfig() {
        return {
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
            refresh_interval: this.getFieldValue('refresh_interval'),
            llm_provider: this.getFieldValue('llm_provider'),
            llm_model: this.getFieldValue('llm_model'),
            max_tokens: this.getFieldValue('max_tokens'),
            temperature: this.getFieldValue('temperature')
        };
    }

    async saveConfiguration() {
        if (!this.validateForm()) {
            utils.showNotification('Please fix validation errors before saving', 'error');
            return;
        }

        this.isLoading = true;
        this.updateSaveButton();

        try {
            const config = this.getCurrentConfig();
            await api.post('/config', config);
            
            this.originalConfig = { ...config };
            this.isDirty = false;
            this.updateSaveButton();
            
            utils.showNotification('Configuration saved successfully', 'success');
        } catch (error) {
            console.error('Failed to save configuration:', error);
            utils.showNotification('Failed to save configuration', 'error');
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