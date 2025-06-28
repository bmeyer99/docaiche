// Dashboard Management Class
class DashboardManager {
    constructor() {
        this.refreshIntervals = {
            health: 30000,    // 30 seconds
            stats: 30000,     // 30 seconds  
            activity: 10000   // 10 seconds
        };
        this.intervalIds = {};
        this.isLoading = false;
    }

    async init() {
        try {
            await this.loadInitialData();
            this.startAutoRefresh();
            this.setupWebSocket();
            this.bindEvents();
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            this.showErrorState();
        }
    }

    async loadInitialData() {
        this.isLoading = true;
        try {
            await Promise.all([
                this.updateSystemHealth(),
                this.updateSystemStats(),
                this.updateRecentActivity()
            ]);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showErrorState();
        } finally {
            this.isLoading = false;
        }
    }

    async updateSystemHealth() {
        try {
            const health = await api.get('/health');
            this.renderHealthStatus(health);
        } catch (error) {
            console.error('Failed to fetch system health:', error);
            this.renderHealthError();
        }
    }

    async updateSystemStats() {
        try {
            const stats = await api.get('/stats');
            this.renderSystemStats(stats);
        } catch (error) {
            console.error('Failed to fetch system stats:', error);
            this.renderStatsError();
        }
    }

    async updateRecentActivity() {
        try {
            const response = await api.get('/admin/search-content?limit=10&recent=true');
            this.renderRecentActivity(response.data || []);
        } catch (error) {
            console.error('Failed to fetch recent activity:', error);
            this.renderActivityError();
        }
    }

    renderHealthStatus(health) {
        const statusContainer = document.getElementById('system-status');
        if (!statusContainer) return;

        const components = health.components || {};
        statusContainer.innerHTML = Object.entries(components).map(([name, status]) => 
            this.generateStatusCard(name, status)
        ).join('');
    }

    generateStatusCard(name, status) {
        const statusClass = this.getStatusClass(status.status);
        const formattedName = this.formatComponentName(name);
        
        return `
            <div class="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
                <div class="flex items-center justify-between">
                    <h3 class="font-medium text-gray-900">${formattedName}</h3>
                    <div class="flex items-center">
                        <div class="w-3 h-3 rounded-full mr-2 ${statusClass}"></div>
                        <span class="text-sm font-medium ${this.getStatusTextClass(status.status)}">
                            ${this.formatStatus(status.status)}
                        </span>
                    </div>
                </div>
                <p class="text-sm text-gray-500 mt-2">${status.message || 'No additional information'}</p>
                ${status.response_time ? `<div class="mt-2 text-xs text-gray-400">Response time: ${status.response_time}</div>` : ''}
            </div>
        `;
    }

    renderSystemStats(stats) {
        const metricsContainer = document.getElementById('key-metrics');
        if (!metricsContainer) return;

        const metrics = [
            {
                name: 'Total Searches',
                value: stats.total_searches || 0,
                change: stats.searches_change || 0,
                description: 'vs last hour'
            },
            {
                name: 'Cache Hit Rate',
                value: `${Math.round((stats.cache_hit_rate || 0) * 100)}%`,
                change: stats.cache_hit_change || 0,
                description: 'last 24 hours'
            },
            {
                name: 'Avg Response Time',
                value: `${stats.avg_response_time || 0}ms`,
                change: -(stats.response_time_change || 0), // Negative because lower is better
                description: 'performance trend'
            }
        ];

        metricsContainer.innerHTML = metrics.map(metric => 
            this.generateMetricCard(metric)
        ).join('');
    }

    generateMetricCard(metric) {
        const trendClass = this.getTrendClass(metric.change);
        const trendIcon = metric.change > 0 ? '↑' : metric.change < 0 ? '↓' : '→';
        
        return `
            <div class="bg-white rounded-lg border border-gray-200 p-6">
                <div class="flex items-start justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-500">${metric.name}</p>
                        <p class="text-3xl font-bold text-gray-900 mt-2">${metric.value}</p>
                    </div>
                    <div class="flex items-center px-2 py-1 rounded-full text-xs font-medium ${trendClass}">
                        ${trendIcon} ${Math.abs(metric.change)}%
                    </div>
                </div>
                <p class="text-sm text-gray-500 mt-4">${metric.description}</p>
            </div>
        `;
    }

    renderRecentActivity(activities) {
        const activityContainer = document.getElementById('recent-activity');
        if (!activityContainer) return;

        if (activities.length === 0) {
            activityContainer.innerHTML = `
                <tr>
                    <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                        No recent activity
                    </td>
                </tr>
            `;
            return;
        }

        activityContainer.innerHTML = activities.map(activity => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${utils.formatTime(activity.timestamp)}
                </td>
                <td class="px-6 py-4 text-sm text-gray-900">
                    <div class="max-w-xs truncate">${activity.query || 'N/A'}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${activity.collection || 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${activity.status === 'success' ? 
                        '<span class="text-green-600">✓</span>' : 
                        '<span class="text-red-600">✗</span>'
                    }
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${activity.response_time || 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <button class="text-blue-600 hover:text-blue-900" onclick="dashboard.viewQuery('${activity.id}')">
                        View
                    </button>
                </td>
            </tr>
        `).join('');
    }

    renderHealthError() {
        const statusContainer = document.getElementById('system-status');
        if (!statusContainer) return;

        statusContainer.innerHTML = `
            <div class="col-span-full bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-center">
                    <svg class="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <p class="text-sm text-red-700">Failed to load system health status</p>
                </div>
            </div>
        `;
    }

    renderStatsError() {
        const metricsContainer = document.getElementById('key-metrics');
        if (!metricsContainer) return;

        metricsContainer.innerHTML = `
            <div class="col-span-full bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-center">
                    <svg class="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <p class="text-sm text-red-700">Failed to load system metrics</p>
                </div>
            </div>
        `;
    }

    renderActivityError() {
        const activityContainer = document.getElementById('recent-activity');
        if (!activityContainer) return;

        activityContainer.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4">
                    <div class="flex items-center justify-center text-red-600">
                        <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                        Failed to load recent activity
                    </div>
                </td>
            </tr>
        `;
    }

    startAutoRefresh() {
        // Clear existing intervals
        Object.values(this.intervalIds).forEach(clearInterval);

        // Set up new intervals
        this.intervalIds.health = setInterval(() => {
            if (!this.isLoading) this.updateSystemHealth();
        }, this.refreshIntervals.health);

        this.intervalIds.stats = setInterval(() => {
            if (!this.isLoading) this.updateSystemStats();
        }, this.refreshIntervals.stats);

        this.intervalIds.activity = setInterval(() => {
            if (!this.isLoading) this.updateRecentActivity();
        }, this.refreshIntervals.activity);
    }

    setupWebSocket() {
        // Listen for real-time updates
        wsManager.on('health_update', (data) => {
            this.renderHealthStatus(data);
        });

        wsManager.on('stats_update', (data) => {
            this.renderSystemStats(data);
        });

        wsManager.on('activity_update', (data) => {
            this.updateRecentActivity();
        });
    }

    bindEvents() {
        // Manual refresh button
        const refreshButton = document.getElementById('manual-refresh');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => {
                this.loadInitialData();
            });
        }
    }

    // Utility methods
    getStatusClass(status) {
        const classes = {
            healthy: 'bg-green-500',
            degraded: 'bg-yellow-500',
            unhealthy: 'bg-red-500'
        };
        return classes[status] || 'bg-gray-500';
    }

    getStatusTextClass(status) {
        const classes = {
            healthy: 'text-green-700',
            degraded: 'text-yellow-700',
            unhealthy: 'text-red-700'
        };
        return classes[status] || 'text-gray-700';
    }

    getTrendClass(change) {
        if (change > 0) return 'bg-green-100 text-green-700';
        if (change < 0) return 'bg-red-100 text-red-700';
        return 'bg-gray-100 text-gray-700';
    }

    formatComponentName(name) {
        return name.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    formatStatus(status) {
        return status.charAt(0).toUpperCase() + status.slice(1);
    }

    viewQuery(queryId) {
        // Implementation for viewing query details
        console.log('View query:', queryId);
        // TODO: Implement query detail modal or redirect
    }

    showErrorState() {
        utils.showNotification('Failed to load dashboard data. Please refresh the page.', 'error');
    }

    destroy() {
        // Cleanup intervals and listeners
        Object.values(this.intervalIds).forEach(clearInterval);
        wsManager.off('health_update');
        wsManager.off('stats_update');
        wsManager.off('activity_update');
    }
}

// Global dashboard instance
let dashboard;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new DashboardManager();
    dashboard.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (dashboard) {
        dashboard.destroy();
    }
});