// Authentication management for Next_KE Platform
class AuthManager {
    constructor() {
        this.baseURL = CONFIG.API_BASE_URL;
        this.token = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_TOKEN);
        this.user = JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.USER_DATA) || 'null');
        this.refreshToken = localStorage.getItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN);
        
        // Set up axios interceptors for authentication
        this.setupInterceptors();
        
        // Check authentication status on load
        this.checkAuthStatus();
    }

    setupInterceptors() {
        // Request interceptor to add auth token
        axios.interceptors.request.use(
            (config) => {
                if (this.token) {
                    config.headers.Authorization = `Bearer ${this.token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor to handle token refresh
        axios.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;
                
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    
                    try {
                        await this.refreshAccessToken();
                        originalRequest.headers.Authorization = `Bearer ${this.token}`;
                        return axios(originalRequest);
                    } catch (refreshError) {
                        this.logout();
                        return Promise.reject(refreshError);
                    }
                }
                
                return Promise.reject(error);
            }
        );
    }

    async register(userData) {
        try {
            const response = await axios.post(`${this.baseURL}/auth/register`, userData);
            const { access_token, refresh_token, user } = response.data;
            
            this.setAuthData(access_token, refresh_token, user);
            this.showNotification('Registration successful! Welcome to Next_KE!', 'success');
            
            return { success: true, user };
        } catch (error) {
            const message = error.response?.data?.detail || 'Registration failed';
            this.showNotification(message, 'error');
            return { success: false, error: message };
        }
    }

    async login(email, password) {
        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);
            
            const response = await axios.post(`${this.baseURL}/auth/login`, formData);
            const { access_token, refresh_token, user } = response.data;
            
            this.setAuthData(access_token, refresh_token, user);
            this.showNotification(`Welcome back, ${user.full_name}!`, 'success');
            
            return { success: true, user };
        } catch (error) {
            const message = error.response?.data?.detail || 'Login failed';
            this.showNotification(message, 'error');
            return { success: false, error: message };
        }
    }

    async refreshAccessToken() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }

        try {
            const formData = new FormData();
            formData.append('refresh_token', this.refreshToken);
            
            const response = await axios.post(`${this.baseURL}/auth/refresh`, formData);
            const { access_token, refresh_token, user } = response.data;
            
            this.setAuthData(access_token, refresh_token, user);
            return access_token;
        } catch (error) {
            this.logout();
            throw error;
        }
    }

    async logout() {
        try {
            if (this.token) {
                await axios.post(`${this.baseURL}/auth/logout`);
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearAuthData();
            this.showNotification('Logged out successfully', 'info');
            window.location.reload();
        }
    }

    async getProfile() {
        try {
            const response = await axios.get(`${this.baseURL}/auth/profile`);
            return { success: true, profile: response.data };
        } catch (error) {
            return { success: false, error: error.response?.data?.detail || 'Failed to load profile' };
        }
    }

    async updateProfile(profileData) {
        try {
            const response = await axios.put(`${this.baseURL}/auth/profile`, profileData);
            this.showNotification('Profile updated successfully!', 'success');
            return { success: true, data: response.data };
        } catch (error) {
            const message = error.response?.data?.detail || 'Failed to update profile';
            this.showNotification(message, 'error');
            return { success: false, error: message };
        }
    }

    setAuthData(accessToken, refreshToken, user) {
        this.token = accessToken;
        this.refreshToken = refreshToken;
        this.user = user;
        
        localStorage.setItem(CONFIG.STORAGE_KEYS.USER_TOKEN, accessToken);
        localStorage.setItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
        localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
        
        // Update UI
        this.updateAuthUI();
    }

    clearAuthData() {
        this.token = null;
        this.refreshToken = null;
        this.user = null;
        
        localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_DATA);
        
        // Update UI
        this.updateAuthUI();
    }

    checkAuthStatus() {
        if (this.token && this.user) {
            this.updateAuthUI();
        }
    }

    updateAuthUI() {
        const loginBtn = document.getElementById('loginBtn');
        const signupBtn = document.getElementById('signupBtn');
        const userActions = document.querySelector('.user-actions');
        
        if (this.isAuthenticated()) {
            // Show authenticated state
            if (userActions) {
                userActions.innerHTML = `
                    <div class="user-menu">
                        <button class="btn-secondary user-menu-toggle" id="userMenuToggle">
                            <i class="fas fa-user"></i> ${this.user.full_name}
                        </button>
                        <div class="user-dropdown" id="userDropdown">
                            <a href="#" class="dropdown-item" onclick="authManager.showProfile()">
                                <i class="fas fa-user"></i> Profile
                            </a>
                            <a href="#" class="dropdown-item" onclick="authManager.showDashboard()">
                                <i class="fas fa-tachometer-alt"></i> Dashboard
                            </a>
                            <a href="#" class="dropdown-item" onclick="authManager.showRecommendations()">
                                <i class="fas fa-star"></i> Recommendations
                            </a>
                            <a href="#" class="dropdown-item" onclick="authManager.showSavedJobs()">
                                <i class="fas fa-bookmark"></i> Saved Jobs
                            </a>
                            <a href="#" class="dropdown-item" onclick="authManager.showApplications()">
                                <i class="fas fa-briefcase"></i> Applications
                            </a>
                            <div class="dropdown-divider"></div>
                            <a href="#" class="dropdown-item" onclick="authManager.logout()">
                                <i class="fas fa-sign-out-alt"></i> Logout
                            </a>
                        </div>
                    </div>
                `;
                
                // Add dropdown functionality
                this.setupUserDropdown();
            }
        } else {
            // Show unauthenticated state
            if (userActions) {
                userActions.innerHTML = `
                    <button class="btn-secondary" id="loginBtn">Login</button>
                    <button class="btn-primary" id="signupBtn">Sign Up</button>
                `;
                
                // Re-attach event listeners
                this.setupAuthModals();
            }
        }
    }

    setupUserDropdown() {
        const toggle = document.getElementById('userMenuToggle');
        const dropdown = document.getElementById('userDropdown');
        
        if (toggle && dropdown) {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('show');
            });
            
            // Close dropdown when clicking outside
            document.addEventListener('click', () => {
                dropdown.classList.remove('show');
            });
        }
    }

    setupAuthModals() {
        const loginBtn = document.getElementById('loginBtn');
        const signupBtn = document.getElementById('signupBtn');
        
        if (loginBtn) {
            loginBtn.addEventListener('click', () => this.showLoginModal());
        }
        
        if (signupBtn) {
            signupBtn.addEventListener('click', () => this.showSignupModal());
        }
    }

    showLoginModal() {
        const modal = document.getElementById('loginModal');
        if (modal) {
            modal.style.display = 'block';
            
            // Setup form submission
            const form = document.getElementById('loginForm');
            if (form) {
                form.onsubmit = async (e) => {
                    e.preventDefault();
                    const email = document.getElementById('loginEmail').value;
                    const password = document.getElementById('loginPassword').value;
                    
                    const result = await this.login(email, password);
                    if (result.success) {
                        modal.style.display = 'none';
                        form.reset();
                    }
                };
            }
        }
    }

    showSignupModal() {
        const modal = document.getElementById('signupModal');
        if (modal) {
            modal.style.display = 'block';
            
            // Setup form submission
            const form = document.getElementById('signupForm');
            if (form) {
                form.onsubmit = async (e) => {
                    e.preventDefault();
                    const userData = {
                        email: document.getElementById('signupEmail').value,
                        password: document.getElementById('signupPassword').value,
                        full_name: document.getElementById('signupName').value,
                        phone: document.getElementById('signupPhone').value
                    };
                    
                    const result = await this.register(userData);
                    if (result.success) {
                        modal.style.display = 'none';
                        form.reset();
                    }
                };
            }
        }
    }

    showProfile() {
        // Navigate to profile section or show profile modal
        this.showSection('profile');
    }

    showDashboard() {
        // Navigate to dashboard section
        this.showSection('dashboard');
    }

    showRecommendations() {
        // Navigate to recommendations section
        this.showSection('recommendations');
    }

    showSavedJobs() {
        // Navigate to saved jobs section
        this.showSection('saved-jobs');
    }

    showApplications() {
        // Navigate to applications section
        this.showSection('applications');
    }

    showSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Show target section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.add('active');
        }
        
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        const navLink = document.querySelector(`[data-section="${sectionName}"]`);
        if (navLink) {
            navLink.classList.add('active');
        }
    }

    isAuthenticated() {
        return !!(this.token && this.user);
    }

    isPremiumUser() {
        return this.user && ['professional', 'enterprise'].includes(this.user.subscription_tier);
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        container.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
        
        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
    }
}

// Initialize auth manager
const authManager = new AuthManager();

// Setup modal close functionality
document.addEventListener('DOMContentLoaded', () => {
    // Close modals when clicking the X or outside
    document.querySelectorAll('.modal').forEach(modal => {
        const closeBtn = modal.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
});
