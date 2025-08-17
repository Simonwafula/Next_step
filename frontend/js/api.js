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

    // Authentication endpoints
    async login(email, password) {
        return this.post('/auth/login', { email, password });
    }

    async register(userData) {
        return this.post('/auth/register', userData);
    }

    async refreshToken() {
        return this.post('/auth/refresh');
    }

    async logout() {
        return this.post('/auth/logout');
    }

    async getCurrentUser() {
        return this.get('/auth/me');
    }

    // User profile endpoints
    async getUserProfile() {
        return this.get('/user/profile');
    }

    async updateUserProfile(profileData) {
        return this.put('/user/profile', profileData);
    }

    async getUserSubscription() {
        return this.get('/user/subscription');
    }

    // User dashboard endpoints
    async getUserRecommendations(params = {}) {
        return this.get('/user/recommendations', params);
    }

    async getSavedJobs(params = {}) {
        return this.get('/user/saved-jobs', params);
    }

    async saveJob(jobId) {
        return this.post('/user/save-job', { job_id: jobId });
    }

    async removeSavedJob(jobId) {
        return this.delete(`/user/saved-jobs/${jobId}`);
    }

    async getUserApplications(params = {}) {
        return this.get('/user/applications', params);
    }

    async getUserNotifications() {
        return this.get('/user/notifications');
    }

    async markNotificationRead(notificationId) {
        return this.post(`/user/notifications/${notificationId}/read`);
    }

    async markAllNotificationsRead() {
        return this.post('/user/notifications/mark-all-read');
    }

    async clearAllNotifications() {
        return this.delete('/user/notifications');
    }

    async getUserRecentActivity() {
        return this.get('/user/recent-activity');
    }

    async getUserApplicationStats() {
        return this.get('/user/application-stats');
    }

    // Career tools endpoints (MCP server integration)
    async generateCV(userData) {
        try {
            // Try to use MCP server first
            const response = await this.post('/career-tools/generate-cv', userData);
            return response;
        } catch (error) {
            console.error('MCP CV generation failed, using fallback:', error);
            // Fallback to mock response
            return {
                content: this.generateMockCV(userData)
            };
        }
    }

    async generateCoverLetter(data) {
        try {
            // Try to use MCP server first
            const response = await this.post('/career-tools/generate-cover-letter', data);
            return response;
        } catch (error) {
            console.error('MCP cover letter generation failed, using fallback:', error);
            // Fallback to mock response
            return {
                content: this.generateMockCoverLetter(data)
            };
        }
    }

    async generateWhyWorkWithStatement(data) {
        try {
            // Try to use MCP server first
            const response = await this.post('/career-tools/generate-statement', data);
            return response;
        } catch (error) {
            console.error('MCP statement generation failed, using fallback:', error);
            // Fallback to mock response
            return {
                content: this.generateMockStatement(data)
            };
        }
    }

    async generateCareerAdvice(data) {
        try {
            // Try to use MCP server first
            const response = await this.post('/career-tools/generate-advice', data);
            return response;
        } catch (error) {
            console.error('MCP career advice generation failed, using fallback:', error);
            // Fallback to mock response
            return {
                advice: this.generateMockAdvice(data),
                next_steps: [
                    "Update your resume with relevant skills",
                    "Network with professionals in your target field",
                    "Consider additional training or certifications",
                    "Apply to entry-level positions in your desired area"
                ],
                resources: [
                    "LinkedIn Learning courses",
                    "Industry-specific online communities",
                    "Professional development workshops",
                    "Mentorship programs"
                ]
            };
        }
    }

    // Mock generation methods (fallbacks)
    generateMockCV(userData) {
        const profile = userData.user_profile;
        return `${profile.name}
${profile.email} | ${profile.phone || ''} | ${profile.location || ''}

PROFESSIONAL SUMMARY
Dedicated professional with strong analytical and communication skills. Proven ability to work effectively in team environments and deliver high-quality results. Passionate about continuous learning and professional development.

EDUCATION
${profile.education || 'Education details to be added'}

WORK EXPERIENCE
${profile.experience || 'Work experience details to be added'}

KEY SKILLS
${profile.skills || 'Skills to be added'}

${userData.target_role ? `\nTailored for: ${userData.target_role}` : ''}`;
    }

    generateMockCoverLetter(data) {
        const profile = data.user_profile;
        const job = data.job_data;
        
        return `Dear Hiring Manager,

I am writing to express my strong interest in the ${job.title} position at ${job.company}. With my background in ${profile.background || 'relevant field'} and skills in ${profile.skills || 'key areas'}, I am confident I would be a valuable addition to your team.

${profile.background ? `My professional background includes ${profile.background}, which has equipped me with the skills and experience necessary for this role.` : ''}

${job.description ? 'Based on the job description, I believe my experience aligns well with your requirements.' : ''} I am particularly excited about the opportunity to contribute to ${job.company}'s continued success.

I would welcome the opportunity to discuss how my skills and enthusiasm can benefit your organization. Thank you for considering my application.

Sincerely,
${profile.name}`;
    }

    generateMockStatement(data) {
        const profile = data.user_profile;
        
        return `Why Work With ${profile.name}

${profile.background ? `Professional Background: ${profile.background}` : ''}

${profile.experience ? `Key Experience: ${profile.experience}` : ''}

${profile.skills ? `Core Competencies: ${profile.skills}` : ''}

${profile.achievements ? `Notable Achievements: ${profile.achievements}` : ''}

${profile.values ? `Professional Values: ${profile.values}` : ''}

I bring a unique combination of technical expertise, strong work ethic, and collaborative approach that drives results and adds value to any organization.

${data.target_role ? `Specifically for ${data.target_role} roles, I offer relevant experience and a passion for excellence that would benefit your team.` : ''}`;
    }

    generateMockAdvice(data) {
        const profile = data.user_profile;
        
        return `Based on your current role as ${profile.current_role || 'professional'} with ${profile.experience_level || 'your level of'} experience, here are my recommendations:

Your skills in ${profile.skills || 'various areas'} provide a strong foundation for career growth. ${profile.career_goals ? `Given your goal of ${profile.career_goals}, I recommend focusing on building expertise in related areas and networking within your target industry.` : ''}

Consider developing both technical and soft skills that are in high demand in your field. Stay updated with industry trends and consider pursuing relevant certifications or additional training.

The job market is constantly evolving, so maintaining a growth mindset and being adaptable to change will serve you well in achieving your career objectives.`;
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
