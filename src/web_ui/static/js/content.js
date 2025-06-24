// Content Management Class
class ContentManager {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalItems = 0;
        this.currentSort = { field: 'title', direction: 'asc' };
        this.currentFilters = {
            search: '',
            technology: '',
            type: '',
            status: ''
        };
        this.debounceTimeout = null;
        this.isLoading = false;
    }

    async init() {
        try {
            await this.loadCollections();
            await this.loadContent();
            this.bindEvents();
            this.setupSearch();
        } catch (error) {
            console.error('Content management initialization failed:', error);
            utils.showNotification('Failed to load content data', 'error');
        }
    }

    async loadCollections() {
        try {
            const response = await api.get('/collections');
            this.renderCollections(response.collections || []);
        } catch (error) {
            console.error('Failed to load collections:', error);
            this.renderCollectionsError();
        }
    }

    async loadContent() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showTableLoading();

        try {
            const params = new URLSearchParams({
                page: this.currentPage.toString(),
                limit: this.pageSize.toString(),
                sort_by: this.currentSort.field,
                sort_order: this.currentSort.direction,
                ...this.currentFilters
            });

            // Remove empty filters
            for (const [key, value] of params.entries()) {
                if (!value) params.delete(key);
            }

            const response = await api.get(`/admin/search-content?${params}`);
            this.renderContent(response.data || [], response.total || 0);
            this.renderPagination(response.total || 0);
        } catch (error) {
            console.error('Failed to load content:', error);
            this.renderContentError();
        } finally {
            this.isLoading = false;
        }
    }

    renderCollections(collections) {
        const container = document.getElementById('collections-grid');
        if (!container) return;

        if (collections.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8 text-gray-500">
                    No collections found
                </div>
            `;
            return;
        }

        container.innerHTML = collections.map(collection => `
            <div class="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <h3 class="text-lg font-medium text-gray-900 mb-2">${collection.name}</h3>
                <p class="text-2xl font-bold text-gray-900 mb-1">${collection.document_count || 0} documents</p>
                <div class="flex items-center mb-2">
                    <div class="w-2 h-2 rounded-full mr-2 ${collection.status === 'active' ? 'bg-green-500' : 'bg-gray-400'}"></div>
                    <span class="text-sm text-gray-600">${collection.status || 'Unknown'}</span>
                </div>
                <p class="text-sm text-gray-500 mb-2">Last updated: ${utils.formatRelativeTime(collection.last_updated)}</p>
                <p class="text-sm text-gray-500 mb-4">Quality Score: ${(collection.quality_score || 0).toFixed(2)}</p>
                <div class="flex space-x-2">
                    <button class="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50" onclick="contentManager.viewCollection('${collection.id}')">
                        View Collection
                    </button>
                    <button class="px-3 py-1 text-sm text-gray-600 hover:text-gray-900" onclick="contentManager.manageCollection('${collection.id}')">
                        Settings
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderContent(content, total) {
        const tbody = document.getElementById('content-table-body');
        if (!tbody) return;

        this.totalItems = total;

        if (content.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-6 py-8 text-center text-gray-500">
                        No content found matching your criteria
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = content.map(item => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4">
                    <div class="max-w-xs">
                        <div class="font-medium text-gray-900 truncate">${item.title || 'Untitled'}</div>
                        <div class="text-sm text-gray-500 truncate">${item.description || ''}</div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        ${item.type || 'Doc'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${item.technology || 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${item.collection || 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${utils.getStatusBadge(item.status || 'unknown')}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                            <div class="bg-green-500 h-2 rounded-full" style="width: ${(item.quality_score || 0) * 100}%"></div>
                        </div>
                        <span class="text-sm text-gray-600">${(item.quality_score || 0).toFixed(2)}</span>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${utils.formatFileSize(item.size || 0)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <div class="flex space-x-2">
                        <button class="text-blue-600 hover:text-blue-900" onclick="contentManager.editContent('${item.id}')">
                            Edit
                        </button>
                        <button class="text-blue-600 hover:text-blue-900" onclick="contentManager.previewContent('${item.id}')">
                            Preview
                        </button>
                        <button class="text-red-600 hover:text-red-900" onclick="contentManager.showDeleteModal('${item.id}')">
                            🗑
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    renderPagination(total) {
        const totalPages = Math.ceil(total / this.pageSize);
        const paginationInfo = document.getElementById('pagination-info');
        const paginationControls = document.getElementById('pagination-controls');

        if (paginationInfo) {
            const start = (this.currentPage - 1) * this.pageSize + 1;
            const end = Math.min(this.currentPage * this.pageSize, total);
            paginationInfo.innerHTML = `
                Showing <span class="font-medium">${start}</span> to 
                <span class="font-medium">${end}</span> of 
                <span class="font-medium">${total}</span> results
            `;
        }

        if (paginationControls && totalPages > 1) {
            let pages = [];
            const maxVisible = 5;
            const half = Math.floor(maxVisible / 2);
            let start = Math.max(1, this.currentPage - half);
            let end = Math.min(totalPages, start + maxVisible - 1);

            if (end - start < maxVisible - 1) {
                start = Math.max(1, end - maxVisible + 1);
            }

            for (let i = start; i <= end; i++) {
                pages.push(i);
            }

            paginationControls.innerHTML = `
                <button type="button" class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 ${this.currentPage <= 1 ? 'opacity-50 cursor-not-allowed' : ''}" 
                        onclick="contentManager.goToPage(${this.currentPage - 1})" ${this.currentPage <= 1 ? 'disabled' : ''}>
                    <span class="sr-only">Previous</span>
                    <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                    </svg>
                </button>
                ${pages.map(page => `
                    <button type="button" class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium ${page === this.currentPage ? 'bg-blue-50 text-blue-600' : 'bg-white text-gray-700 hover:bg-gray-50'}"
                            onclick="contentManager.goToPage(${page})">
                        ${page}
                    </button>
                `).join('')}
                <button type="button" class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 ${this.currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : ''}"
                        onclick="contentManager.goToPage(${this.currentPage + 1})" ${this.currentPage >= totalPages ? 'disabled' : ''}>
                    <span class="sr-only">Next</span>
                    <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                </button>
            `;
        }
    }

    showTableLoading() {
        const tbody = document.getElementById('content-table-body');
        if (!tbody) return;

        tbody.innerHTML = Array(5).fill().map(() => `
            <tr class="animate-pulse">
                <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-48"></div></td>
                <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-12"></div></td>
                <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-16"></div></td>
                <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-20"></div></td>
                <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-12"></div></td>
                <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-16"></div></td>
                <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-12"></div></td>
                <td class="px-6 py-4"><div class="flex space-x-2"><div class="h-4 bg-gray-200 rounded w-12"></div></div></td>
            </tr>
        `).join('');
    }

    renderCollectionsError() {
        const container = document.getElementById('collections-grid');
        if (!container) return;

        container.innerHTML = `
            <div class="col-span-full bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-center">
                    <svg class="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <p class="text-sm text-red-700">Failed to load collections</p>
                </div>
            </div>
        `;
    }

    renderContentError() {
        const tbody = document.getElementById('content-table-body');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="px-6 py-4">
                    <div class="flex items-center justify-center text-red-600">
                        <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                        Failed to load content
                    </div>
                </td>
            </tr>
        `;
    }

    setupSearch() {
        const searchInput = document.getElementById('content-search');
        if (searchInput) {
            searchInput.addEventListener('input', utils.debounce((e) => {
                this.currentFilters.search = e.target.value;
                this.currentPage = 1;
                this.loadContent();
            }, 300));
        }
    }

    bindEvents() {
        // Filter dropdowns
        ['technology-filter', 'type-filter', 'status-filter'].forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.addEventListener('change', (e) => {
                    const filterKey = id.replace('-filter', '');
                    this.currentFilters[filterKey] = e.target.value;
                    this.currentPage = 1;
                    this.loadContent();
                });
            }
        });

        // Search button
        const searchButton = document.getElementById('search-button');
        if (searchButton) {
            searchButton.addEventListener('click', () => {
                this.currentPage = 1;
                this.loadContent();
            });
        }

        // Sort headers
        const sortHeaders = document.querySelectorAll('[data-sort]');
        sortHeaders.forEach(header => {
            header.addEventListener('click', () => {
                this.handleSort(header.getAttribute('data-sort'));
            });
        });

        // Modal events
        this.bindModalEvents();
    }

    bindModalEvents() {
        const closePreview = document.getElementById('close-preview');
        const confirmDelete = document.getElementById('confirm-delete');
        const cancelDelete = document.getElementById('cancel-delete');

        if (closePreview) {
            closePreview.addEventListener('click', () => utils.hideModal('preview-modal'));
        }

        if (confirmDelete) {
            confirmDelete.addEventListener('click', () => this.confirmDelete());
        }

        if (cancelDelete) {
            cancelDelete.addEventListener('click', () => utils.hideModal('delete-modal'));
        }
    }

    handleSort(field) {
        if (this.currentSort.field === field) {
            this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort.field = field;
            this.currentSort.direction = 'asc';
        }
        this.loadContent();
    }

    goToPage(page) {
        if (page < 1 || page > Math.ceil(this.totalItems / this.pageSize)) return;
        this.currentPage = page;
        this.loadContent();
    }

    async previewContent(contentId) {
        try {
            const content = await api.get(`/content/${contentId}`);
            this.showPreviewModal(content);
        } catch (error) {
            console.error('Failed to load content preview:', error);
            utils.showNotification('Failed to load content preview', 'error');
        }
    }

    showPreviewModal(content) {
        const modal = document.getElementById('preview-modal');
        const title = document.getElementById('preview-title');
        const contentDiv = document.getElementById('preview-content');
        const metadata = document.getElementById('preview-metadata');
        const qualityBar = document.getElementById('preview-quality-bar');
        const qualityScore = document.getElementById('preview-quality-score');

        if (title) title.textContent = content.title || 'Content Preview';
        if (contentDiv) contentDiv.innerHTML = `<pre class="whitespace-pre-wrap text-sm">${content.content || 'No content available'}</pre>`;
        
        if (metadata) {
            metadata.innerHTML = `
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <dt class="text-gray-500">Type:</dt><dd>${content.type || 'N/A'}</dd>
                    <dt class="text-gray-500">Technology:</dt><dd>${content.technology || 'N/A'}</dd>
                    <dt class="text-gray-500">Collection:</dt><dd>${content.collection || 'N/A'}</dd>
                    <dt class="text-gray-500">Size:</dt><dd>${utils.formatFileSize(content.size || 0)}</dd>
                    <dt class="text-gray-500">Created:</dt><dd>${utils.formatRelativeTime(content.created_at)}</dd>
                    <dt class="text-gray-500">Updated:</dt><dd>${utils.formatRelativeTime(content.updated_at)}</dd>
                </div>
            `;
        }

        const quality = content.quality_score || 0;
        if (qualityBar) qualityBar.style.width = `${quality * 100}%`;
        if (qualityScore) qualityScore.textContent = quality.toFixed(2);

        utils.showModal('preview-modal');
    }

    showDeleteModal(contentId) {
        this.contentToDelete = contentId;
        utils.showModal('delete-modal');
    }

    async confirmDelete() {
        if (!this.contentToDelete) return;

        try {
            await api.delete(`/content/${this.contentToDelete}`);
            utils.hideModal('delete-modal');
            utils.showNotification('Content flagged for deletion', 'success');
            this.loadContent();
        } catch (error) {
            console.error('Failed to delete content:', error);
            utils.showNotification('Failed to delete content', 'error');
        } finally {
            this.contentToDelete = null;
        }
    }

    editContent(contentId) {
        console.log('Edit content:', contentId);
        // TODO: Implement content editing modal or redirect
    }

    viewCollection(collectionId) {
        console.log('View collection:', collectionId);
        // TODO: Implement collection detail view
    }

    manageCollection(collectionId) {
        console.log('Manage collection:', collectionId);
        // TODO: Implement collection management modal
    }
}

// Global content manager instance
let contentManager;

// Initialize content manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    contentManager = new ContentManager();
    contentManager.init();
});