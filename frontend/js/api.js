// API handling module for making requests to the backend
class APIClient {
    constructor() {
        this.baseURL = CONFIG.API_BASE_URL;
        this.token = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_TOKEN);
    }

    // Set authentication token
    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem(CONFIG.STORAGE_KEYS.USER_TOKEN, token);
        } else {
            localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_TOKEN);
        }
    }

    // Get default headers
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        return headers;
    }

    // Make HTTP request
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: this.getHeaders(),
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            // Handle different response types
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new APIError(
                    errorData.message || CONFIG.ERROR_MESSAGES.SERVER_ERROR,
                    response.status,
                    errorData
                );
            }

            // Handle empty responses
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
            
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }
            
            // Network or other errors
            throw new APIError(
                CONFIG.ERROR_MESSAGES.NETWORK_ERROR,
                0,
                { originalError: error.message }
            );
        }
    }

    // GET request
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        
        return this.request(url, {
            method: 'GET'
        });
    }

    // POST request
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // PUT request
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    // DELETE request
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    // Search jobs
    async searchJobs(query, filters = {}) {
        const params = {
            q: query,
            ...filters
        };
        
        return this.get(CONFIG.ENDPOINTS.SEARCH, params);
    }

    // Translate job title
    async translateTitle(title) {
        return this.get(CONFIG.ENDPOINTS.TRANSLATE_TITLE, { title });
    }

    // Get careers for degree
    async getCareersForDegree(degree) {
        return this.get(CONFIG.ENDPOINTS.CAREERS_FOR_DEGREE, { degree });
    }

    // Get career recommendations
    async getRecommendations(current) {
        return this.get(CONFIG.ENDPOINTS.RECOMMEND, { current });
    }

    // Get trending transitions
    async getTrendingTransitions(days = 30) {
        return this.get(CONFIG.ENDPOINTS.TRENDING_TRANSITIONS, { days });
    }

    // Get transition salary insights
    async getTransitionSalary(targetRole) {
        return this.get(CONFIG.ENDPOINTS.TRANSITION_SALARY, { target_role: targetRole });
    }

    // Get weekly insights
    async getWeeklyInsights(location = null) {
        const params = location ? { location } : {};
        return this.get(CONFIG.ENDPOINTS.WEEKLY_INSIGHTS, params);
    }

    // Get market trends
    async getMarketTrends(days = 30, location = null) {
        const params = { days };
        if (location) params.location = location;
        return this.get(CONFIG.ENDPOINTS.MARKET_TRENDS, params);
    }

    // Get salary insights
    async getSalaryInsights(roleFamily = null, location = null) {
        const params = {};
        if (roleFamily) params.role_family = roleFamily;
        if (location) params.location = location;
        return this.get(CONFIG.ENDPOINTS.SALARY_INSIGHTS, params);
    }

    // Get trending skills
    async getTrendingSkills(days = 7) {
        return this.get(CONFIG.ENDPOINTS.TRENDING_SKILLS, { days });
    }

    // Get coverage statistics
    async getCoverageStats() {
        return this.get(CONFIG.ENDPOINTS.COVERAGE_STATS);
    }

    // Get attachment opportunities
    async getAttachments(location = null) {
        const params = location ? { location } : {};
        return this.get(CONFIG.ENDPOINTS.ATTACHMENTS, params);
    }

    // Get graduate programs
    async getGraduatePrograms(location = null, sector = null) {
        const params = {};
        if (location) params.location = location;
        if (sector) params.sector = sector;
        return this.get(CONFIG.ENDPOINTS.GRADUATE_PROGRAMS, params);
    }

    // Get scraper status
    async getScraperStatus() {
        return this.get(CONFIG.ENDPOINTS.SCRAPER_STATUS);
    }

    // Run specific scraper
    async runScraper(siteName) {
        return this.post(`${CONFIG.ENDPOINTS.RUN_SCRAPER}/${siteName}`);
    }

    // Run all scrapers
    async runAllScrapers() {
        return this.post(CONFIG.ENDPOINTS.RUN_ALL_SCRAPERS);
    }

    // Get recent jobs
    async getRecentJobs(limit = 10) {
        return this.get(CONFIG.ENDPOINTS.RECENT_JOBS, { limit });
    }
}

// Custom error class for API errors
class APIError extends Error {
    constructor(message, status, data = {}) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }
}

// Notification service for user feedback
class NotificationService {
    constructor() {
        this.container = document.getElementById('notifications');
        if (!this.container) {
            this.createContainer();
        }
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notifications';
        this.container.className = 'notifications-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', title = null, duration = CONFIG.NOTIFICATION_DURATION) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const content = `
            ${title ? `<div class="notification-title">${title}</div>` : ''}
            <div class="notification-message">${message}</div>
        `;
        
        notification.innerHTML = content;
        this.container.appendChild(notification);

        // Auto remove after duration
        setTimeout(() => {
            this.remove(notification);
        }, duration);

        // Allow manual removal by clicking
        notification.addEventListener('click', () => {
            this.remove(notification);
        });

        return notification;
    }

    remove(notification) {
        if (notification && notification.parentNode) {
            notification.style.animation = 'notificationSlideOut 0.3s ease';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }

    success(message, title = 'Success') {
        return this.show(message, 'success', title);
    }

    error(message, title = 'Error') {
        return this.show(message, 'error', title);
    }

    warning(message, title = 'Warning') {
        return this.show(message, 'warning', title);
    }

    info(message, title = null) {
        return this.show(message, 'info', title);
    }
}

// Loading service for showing loading states
class LoadingService {
    constructor() {
        this.activeLoaders = new Set();
    }

    show(element, message = 'Loading...') {
        const loaderId = UTILS.generateId();
        
        const loader = document.createElement('div');
        loader.className = 'loading';
        loader.dataset.loaderId = loaderId;
        loader.innerHTML = `
            <div class="spinner"></div>
            <span>${message}</span>
        `;

        // Store original content
        const originalContent = element.innerHTML;
        element.dataset.originalContent = originalContent;
        
        // Show loader
        element.innerHTML = '';
        element.appendChild(loader);
        
        this.activeLoaders.add(loaderId);
        return loaderId;
    }

    hide(element, loaderId = null) {
        if (loaderId) {
            this.activeLoaders.delete(loaderId);
        }

        // Restore original content
        const originalContent = element.dataset.originalContent;
        if (originalContent) {
            element.innerHTML = originalContent;
            delete element.dataset.originalContent;
        }
    }

    hideAll() {
        this.activeLoaders.clear();
        document.querySelectorAll('.loading').forEach(loader => {
            const element = loader.parentElement;
            this.hide(element);
        });
    }
}

// Cache service for storing API responses
class CacheService {
    constructor() {
        this.cache = new Map();
        this.ttl = 5 * 60 * 1000; // 5 minutes default TTL
    }

    set(key, data, ttl = this.ttl) {
        const expiry = Date.now() + ttl;
        this.cache.set(key, { data, expiry });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;

        if (Date.now() > item.expiry) {
            this.cache.delete(key);
            return null;
        }

        return item.data;
    }

    has(key) {
        return this.get(key) !== null;
    }

    delete(key) {
        this.cache.delete(key);
    }

    clear() {
        this.cache.clear();
    }

    // Generate cache key from endpoint and params
    generateKey(endpoint, params = {}) {
        const paramString = JSON.stringify(params);
        return `${endpoint}:${paramString}`;
    }
}

// Enhanced API client with caching and loading states
class EnhancedAPIClient extends APIClient {
    constructor() {
        super();
        this.cache = new CacheService();
        this.loading = new LoadingService();
        this.notifications = new NotificationService();
    }

    // Enhanced request method with caching and error handling
    async enhancedRequest(endpoint, options = {}, useCache = true, showLoading = false, loadingElement = null) {
        const cacheKey = this.cache.generateKey(endpoint, options.params || {});
        
        // Check cache first
        if (useCache && this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        let loaderId = null;
        if (showLoading && loadingElement) {
            loaderId = this.loading.show(loadingElement);
        }

        try {
            const response = await this.request(endpoint, options);
            
            // Cache successful responses
            if (useCache) {
                this.cache.set(cacheKey, response);
            }

            return response;
            
        } catch (error) {
            // Show error notification
            this.notifications.error(error.message);
            throw error;
            
        } finally {
            if (loaderId && loadingElement) {
                this.loading.hide(loadingElement, loaderId);
            }
        }
    }

    // Enhanced search with loading and caching
    async searchJobsEnhanced(query, filters = {}, element = null) {
        const params = { q: query, ...filters };
        return this.enhancedRequest(
            CONFIG.ENDPOINTS.SEARCH,
            { method: 'GET', params },
            true,
            !!element,
            element
        );
    }
}

// Global instances
const api = new EnhancedAPIClient();
const notifications = new NotificationService();
const loading = new LoadingService();
const cache = new CacheService();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        APIClient, 
        EnhancedAPIClient, 
        APIError, 
        NotificationService, 
        LoadingService, 
        CacheService,
        api,
        notifications,
        loading,
        cache
    };
}
