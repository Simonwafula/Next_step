const getApiBaseUrl = () => {
    if (typeof document !== 'undefined' && document.body) {
        const dataApiBase = document.body.dataset.apiBase;
        if (dataApiBase) {
            return dataApiBase;
        }
    }

    if (typeof window !== 'undefined' && window.location) {
        const host = window.location.hostname;
        if (host === 'localhost' || host === '127.0.0.1') {
            return 'http://localhost:8000/api';
        }
        return `${window.location.origin}/api`;
    }

    if (typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'production') {
        return 'https://api.nextstep.co.ke/api';
    }

    return 'http://localhost:8000/api';
};

const getWhatsappUrl = (apiBaseUrl) => {
    if (!apiBaseUrl) {
        return 'http://localhost:8000/whatsapp';
    }
    const base = apiBaseUrl.endsWith('/api') ? apiBaseUrl.slice(0, -4) : apiBaseUrl;
    return `${base}/whatsapp`;
};

const runtimeApiBaseUrl = getApiBaseUrl();

// Configuration settings for the frontend application
const CONFIG = {
    // API Base URL - adjust this based on your backend deployment
    API_BASE_URL: runtimeApiBaseUrl,
    
    // WhatsApp webhook URL
    WHATSAPP_URL: getWhatsappUrl(runtimeApiBaseUrl),
    
    // Application settings
    APP_NAME: 'NextStep',
    VERSION: '1.0.0',
    DOMAIN: 'nextstep.co.ke',
    WEBSITE_URL: 'https://nextstep.co.ke',
    
    // Search settings
    SEARCH_DEBOUNCE_MS: 300,
    RESULTS_PER_PAGE: 20,
    
    // Notification settings
    NOTIFICATION_DURATION: 5000, // 5 seconds
    
    // Premium features
    PREMIUM_PLANS: {
        professional: {
            name: 'Professional',
            price: 2500,
            currency: 'KSh',
            features: [
                'AI-powered CV optimization',
                'Personalized cover letters',
                'Advanced career coaching',
                'Priority job alerts',
                'Salary negotiation tips'
            ]
        },
        enterprise: {
            name: 'Enterprise',
            price: 5000,
            currency: 'KSh',
            features: [
                '1-on-1 career coaching',
                'Interview preparation',
                'LinkedIn profile optimization',
                'Direct recruiter connections',
                'Custom job alerts'
            ]
        }
    },
    
    // Local storage keys
    STORAGE_KEYS: {
        USER_TOKEN: 'career_search_token',
        USER_DATA: 'career_search_user',
        SEARCH_HISTORY: 'career_search_history',
        PREFERENCES: 'career_search_preferences'
    },
    
    // API endpoints
    ENDPOINTS: {
        // Search and jobs
        SEARCH: '/search',
        TRANSLATE_TITLE: '/translate-title',
        CAREERS_FOR_DEGREE: '/careers-for-degree',
        RECOMMEND: '/recommend',
        TRENDING_TRANSITIONS: '/trending-transitions',
        TRANSITION_SALARY: '/transition-salary',
        
        // Market insights
        WEEKLY_INSIGHTS: '/lmi/weekly-insights',
        MARKET_TRENDS: '/lmi/market-trends',
        SALARY_INSIGHTS: '/lmi/salary-insights',
        TRENDING_SKILLS: '/lmi/trending-skills',
        COVERAGE_STATS: '/lmi/coverage-stats',
        
        // Attachments and programs
        ATTACHMENTS: '/attachments',
        GRADUATE_PROGRAMS: '/graduate-programs',
        
        // Admin and scrapers
        SCRAPER_STATUS: '/scrapers/status',
        RUN_SCRAPER: '/scrapers/run',
        RUN_ALL_SCRAPERS: '/scrapers/run-all',
        RECENT_JOBS: '/scrapers/recent-jobs'
    },
    
    // Error messages
    ERROR_MESSAGES: {
        NETWORK_ERROR: 'Network error. Please check your connection and try again.',
        SERVER_ERROR: 'Server error. Please try again later.',
        VALIDATION_ERROR: 'Please check your input and try again.',
        AUTH_ERROR: 'Authentication failed. Please login again.',
        NOT_FOUND: 'The requested resource was not found.',
        RATE_LIMIT: 'Too many requests. Please wait a moment and try again.'
    },
    
    // Success messages
    SUCCESS_MESSAGES: {
        SEARCH_COMPLETE: 'Search completed successfully',
        DATA_SAVED: 'Data saved successfully',
        EMAIL_SENT: 'Email sent successfully',
        PROFILE_UPDATED: 'Profile updated successfully'
    },
    
    // Job categories for filtering
    JOB_CATEGORIES: [
        'Technology',
        'Finance',
        'Healthcare',
        'Education',
        'Marketing',
        'Sales',
        'Operations',
        'Human Resources',
        'Legal',
        'Consulting',
        'Engineering',
        'Design',
        'Research',
        'Administration'
    ],
    
    // Kenyan locations
    LOCATIONS: [
        'Nairobi',
        'Mombasa',
        'Kisumu',
        'Nakuru',
        'Eldoret',
        'Thika',
        'Malindi',
        'Kitale',
        'Garissa',
        'Kakamega',
        'Nyeri',
        'Machakos',
        'Meru',
        'Kericho',
        'Embu',
        'Remote'
    ],
    
    // Seniority levels
    SENIORITY_LEVELS: [
        'Internship',
        'Entry Level',
        'Mid Level',
        'Senior Level',
        'Lead',
        'Manager',
        'Director',
        'Executive'
    ],
    
    // Skills categories
    SKILL_CATEGORIES: {
        technical: [
            'Python', 'JavaScript', 'Java', 'SQL', 'Excel', 'PowerBI', 
            'Tableau', 'R', 'SPSS', 'AutoCAD', 'Photoshop', 'WordPress'
        ],
        soft: [
            'Communication', 'Leadership', 'Project Management', 'Problem Solving',
            'Teamwork', 'Time Management', 'Critical Thinking', 'Adaptability'
        ],
        business: [
            'Financial Analysis', 'Market Research', 'Strategic Planning',
            'Business Development', 'Sales', 'Marketing', 'Operations'
        ]
    }
};

// Utility functions
const UTILS = {
    // Format currency
    formatCurrency: (amount, currency = 'KSh') => {
        return `${currency} ${amount.toLocaleString()}`;
    },
    
    // Format date
    formatDate: (date) => {
        return new Date(date).toLocaleDateString('en-KE', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },
    
    // Format relative time
    formatRelativeTime: (date) => {
        const now = new Date();
        const diff = now - new Date(date);
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (days === 0) return 'Today';
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days} days ago`;
        if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
        return `${Math.floor(days / 30)} months ago`;
    },
    
    // Debounce function
    debounce: (func, wait) => {
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
    
    // Generate unique ID
    generateId: () => {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },
    
    // Validate email
    isValidEmail: (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },
    
    // Validate phone number (Kenyan format)
    isValidPhone: (phone) => {
        const phoneRegex = /^(\+254|0)[17]\d{8}$/;
        return phoneRegex.test(phone.replace(/\s/g, ''));
    },
    
    // Truncate text
    truncateText: (text, maxLength = 150) => {
        if (text.length <= maxLength) return text;
        return text.substr(0, maxLength) + '...';
    },
    
    // Capitalize first letter
    capitalize: (str) => {
        return str.charAt(0).toUpperCase() + str.slice(1);
    },
    
    // Convert to slug
    toSlug: (str) => {
        return str
            .toLowerCase()
            .replace(/[^\w ]+/g, '')
            .replace(/ +/g, '-');
    },
    
    // Get query parameters
    getQueryParams: () => {
        const params = new URLSearchParams(window.location.search);
        const result = {};
        for (const [key, value] of params) {
            result[key] = value;
        }
        return result;
    },
    
    // Set query parameters
    setQueryParams: (params) => {
        const url = new URL(window.location);
        Object.keys(params).forEach(key => {
            if (params[key]) {
                url.searchParams.set(key, params[key]);
            } else {
                url.searchParams.delete(key);
            }
        });
        window.history.replaceState({}, '', url);
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CONFIG, UTILS };
}
