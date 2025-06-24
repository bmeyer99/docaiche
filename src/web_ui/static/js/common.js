// API Configuration
const API_BASE = '/api/v1';
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

// HTTP Client with CSRF protection
class APIClient {
    constructor() {
        this.baseURL = API_BASE;
        this.headers = {
            'Content-Type': 'application/json',
            'X-CSRF-Token': CSRF_TOKEN
        };
    }

    async request(url, options = {}) {
        const config = {
            headers: {
                ...this.headers,
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(`${this.baseURL}${url}`, config);
            
            if (!response.ok) {
                let errorDetails = '';
                try {
                    const errorData = await response.json();
                    errorDetails = errorData.detail || errorData.message || response.statusText;
                } catch {
                    errorDetails = response.statusText;
                }
                
                const error = new Error(`HTTP ${response.status}: ${errorDetails}`);
                error.status = response.status;
                error.response = response;
                throw error;
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${error.message}`);
            
            // If it's a network error or other non-HTTP error
            if (!error.status) {
                error.message = 'Network error. Please check your connection.';
            }
            
            throw error;
        }
    }

    async get(url) {
        return this.request(url);
    }

    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
}

// Global API client instance
const api = new APIClient();

// Utility Functions
const utils = {
    // Debounce function for search inputs
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Format timestamp for display
    formatTime(timestamp) {
        return new Date(timestamp).toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    // Format relative time (e.g., "2 hours ago")
    formatRelativeTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 1) {
            const diffMins = Math.floor(diffMs / (1000 * 60));
            return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        }
    },

    // Show notification banner
    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('config-messages') || 
                         document.createElement('div');
        
        if (!document.getElementById('config-messages')) {
            container.id = 'config-messages';
            container.className = 'px-4 sm:px-6 lg:px-8 pt-4';
            document.querySelector('main').prepend(container);
        }

        const colors = {
            success: 'bg-green-50 border-green-200 text-green-700',
            error: 'bg-red-50 border-red-200 text-red-700',
            warning: 'bg-yellow-50 border-yellow-200 text-yellow-700',
            info: 'bg-blue-50 border-blue-200 text-blue-700'
        };

        const icons = {
            success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />',
            error: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />',
            warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z" />',
            info: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />'
        };

        container.innerHTML = `
            <div class="rounded-md border p-4 ${colors[type]}">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            ${icons[type]}
                        </svg>
                    </div>
                    <div class="ml-3">
                        <p class="text-sm font-medium">${message}</p>
                    </div>
                    <div class="ml-auto pl-3">
                        <button type="button" class="inline-flex rounded-md p-1.5 hover:bg-black hover:bg-opacity-10" onclick="this.parentElement.parentElement.parentElement.remove()">
                            <span class="sr-only">Dismiss</span>
                            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;

        container.classList.remove('hidden');

        if (duration > 0) {
            setTimeout(() => {
                container.classList.add('hidden');
            }, duration);
        }
    },

    // Show/hide modal
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            // Trap focus in modal
            const focusableElements = modal.querySelectorAll('button, input, select, textarea');
            if (focusableElements.length > 0) {
                focusableElements[0].focus();
            }
        }
    },

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
        }
    },

    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },

    // Generate status badge HTML
    getStatusBadge(status) {
        const badges = {
            healthy: '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Healthy</span>',
            degraded: '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Degraded</span>',
            unhealthy: '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Unhealthy</span>',
            active: '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Active</span>',
            inactive: '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Inactive</span>',
            error: '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Error</span>',
            processing: '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Processing</span>'
        };
        return badges[status] || `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">${status}</span>`;
    }
};

// Mobile menu functionality
document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
    const mobileMenuPanel = document.getElementById('mobile-menu-panel');
    const mobileMenuClose = document.getElementById('mobile-menu-close');

    function showMobileMenu() {
        mobileMenuOverlay.classList.remove('hidden');
        setTimeout(() => {
            mobileMenuPanel.classList.remove('-translate-x-full');
        }, 10);
    }

    function hideMobileMenu() {
        mobileMenuPanel.classList.add('-translate-x-full');
        setTimeout(() => {
            mobileMenuOverlay.classList.add('hidden');
        }, 300);
    }

    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', showMobileMenu);
    }

    if (mobileMenuClose) {
        mobileMenuClose.addEventListener('click', hideMobileMenu);
    }

    if (mobileMenuOverlay) {
        mobileMenuOverlay.addEventListener('click', (e) => {
            if (e.target === mobileMenuOverlay) {
                hideMobileMenu();
            }
        });
    }

    // Close mobile menu on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !mobileMenuOverlay.classList.contains('hidden')) {
            hideMobileMenu();
        }
    });
});

// WebSocket connection management
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.maxReconnectAttempts = 5;
        this.reconnectAttempts = 0;
        this.listeners = new Map();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus(false);
                // Use setTimeout to prevent blocking the UI thread
                setTimeout(() => this.attemptReconnect(), 100);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
                // Prevent rapid error loops from blocking UI
                setTimeout(() => {
                    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
                        this.ws.close();
                    }
                }, 100);
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.updateConnectionStatus(false);
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            // Use longer timeout to prevent rapid reconnection attempts that could freeze UI
            setTimeout(() => {
                // Only attempt reconnect if we don't already have an active connection
                if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
                    this.connect();
                }
            }, this.reconnectInterval * this.reconnectAttempts); // Exponential backoff
        } else {
            console.log('Max reconnection attempts reached. WebSocket will remain disconnected.');
            // Silently fail instead of showing error to prevent UI disruption
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            const dot = statusElement.querySelector('.w-2');
            const text = statusElement.querySelector('span');
            
            if (connected) {
                dot.className = 'w-2 h-2 bg-green-500 rounded-full';
                text.textContent = 'Connected';
            } else {
                dot.className = 'w-2 h-2 bg-red-500 rounded-full';
                text.textContent = 'Disconnected';
            }
        }
    }

    handleMessage(data) {
        // Dispatch to registered listeners
        if (this.listeners.has(data.type)) {
            this.listeners.get(data.type).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('Error in WebSocket message handler:', error);
                }
            });
        }
    }

    on(messageType, callback) {
        if (!this.listeners.has(messageType)) {
            this.listeners.set(messageType, []);
        }
        this.listeners.get(messageType).push(callback);
    }

    off(messageType, callback) {
        if (this.listeners.has(messageType)) {
            const callbacks = this.listeners.get(messageType);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }
}

// Global WebSocket manager
const wsManager = new WebSocketManager();

// Auto-connect WebSocket when page loads
document.addEventListener('DOMContentLoaded', () => {
    wsManager.connect();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    wsManager.disconnect();
});