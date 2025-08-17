/**
 * Dashboard Management System
 * Handles user dashboard functionality including profile, recommendations, saved jobs, applications, and notifications
 */

class DashboardManager {
    constructor() {
        this.currentTab = 'overview';
        this.authManager = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDashboardData();
    }

    setAuthManager(authManager) {
        this.authManager = authManager;
    }

    bindEvents() {
        // Tab switching
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-btn')) {
                this.switchTab(e.target.dataset.tab);
            }
        });

        // Profile form submission
        const profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => this.handleProfileUpdate(e));
        }

        // Dashboard navigation from user menu
        const profileLink = document.getElementById('profileLink');
        const savedJobsLink = document.getElementById('savedJobsLink');
        const applicationsLink = document.getElementById('applicationsLink');
        const notificationsLink = document.getElementById('notificationsLink');

        if (profileLink) profileLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.navigateToDashboard('profile');
        });

        if (savedJobsLink) savedJobsLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.navigateToDashboard('saved-jobs');
        });

        if (applicationsLink) applicationsLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.navigateToDashboard('applications');
        });

        if (notificationsLink) notificationsLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.navigateToDashboard('notifications');
        });

        // Other dashboard actions
        this.bindDashboardActions();
    }

    bindDashboardActions() {
        // Complete profile button
        const completeProfileBtn = document.getElementById('completeProfileBtn');
        if (completeProfileBtn) {
            completeProfileBtn.addEventListener('click', () => {
                this.switchTab('profile');
            });
        }

        // View all recommendations
        const viewAllRecommendations = document.getElementById('viewAllRecommendations');
        if (viewAllRecommendations) {
            viewAllRecommendations.addEventListener('click', () => {
                this.switchTab('recommendations');
            });
        }

        // Refresh recommendations
        const refreshRecommendations = document.getElementById('refreshRecommendations');
        if (refreshRecommendations) {
            refreshRecommendations.addEventListener('click', () => {
                this.loadRecommendations();
            });
        }

        // Notification actions
        const markAllRead = document.getElementById('markAllRead');
        const clearNotifications = document.getElementById('clearNotifications');

        if (markAllRead) {
            markAllRead.addEventListener('click', () => this.markAllNotificationsRead());
        }

        if (clearNotifications) {
            clearNotifications.addEventListener('click', () => this.clearAllNotifications());
        }

        // Search and filter handlers
        this.bindSearchAndFilters();
    }

    bindSearchAndFilters() {
        // Saved jobs search
        const savedJobsSearch = document.getElementById('savedJobsSearch');
        if (savedJobsSearch) {
            savedJobsSearch.addEventListener('input', (e) => {
                this.filterSavedJobs(e.target.value);
            });
        }

        // Sort handlers
        const sortElements = [
            'recommendationSort',
            'savedJobsSort',
            'applicationSort'
        ];

        sortElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', (e) => {
                    this.handleSort(id, e.target.value);
                });
            }
        });

        // Application status filter
        const applicationStatus = document.getElementById('applicationStatus');
        if (applicationStatus) {
            applicationStatus.addEventListener('change', (e) => {
                this.filterApplications(e.target.value);
            });
        }
    }

    navigateToDashboard(tab) {
        // Switch to dashboard section
        const sections = document.querySelectorAll('.section');
        const navLinks = document.querySelectorAll('.nav-link');

        sections.forEach(section => section.classList.remove('active'));
        navLinks.forEach(link => link.classList.remove('active'));

        document.getElementById('dashboard-section').classList.add('active');
        document.querySelector('[data-section="dashboard"]').classList.add('active');

        // Switch to specific tab
        this.switchTab(tab);
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        this.loadTabData(tabName);
    }

    async loadDashboardData() {
        if (!this.authManager || !this.authManager.isAuthenticated()) {
            return;
        }

        try {
            // Load overview data
            await this.loadOverviewData();
            
            // Load profile data
            await this.loadProfileData();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showNotification('Error loading dashboard data', 'error');
        }
    }

    async loadTabData(tabName) {
        switch (tabName) {
            case 'overview':
                await this.loadOverviewData();
                break;
            case 'profile':
                await this.loadProfileData();
                break;
            case 'recommendations':
                await this.loadRecommendations();
                break;
            case 'saved-jobs':
                await this.loadSavedJobs();
                break;
            case 'applications':
                await this.loadApplications();
                break;
            case 'notifications':
                await this.loadNotifications();
                break;
        }
    }

    async loadOverviewData() {
        try {
            const token = this.authManager.getToken();
            
            // Load profile completeness
            const profileResponse = await fetch('/api/user/profile', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (profileResponse.ok) {
                const profile = await profileResponse.json();
                this.updateProfileCompleteness(profile.completeness_percentage || 0);
            }

            // Load recent activity
            const activityResponse = await fetch('/api/user/recent-activity', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (activityResponse.ok) {
                const activity = await activityResponse.json();
                this.updateRecentActivity(activity);
            }

            // Load quick recommendations
            const recommendationsResponse = await fetch('/api/user/recommendations?limit=3', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (recommendationsResponse.ok) {
                const recommendations = await recommendationsResponse.json();
                this.updateQuickRecommendations(recommendations);
            }

            // Load application stats
            const statsResponse = await fetch('/api/user/application-stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                this.updateApplicationStats(stats);
            }

        } catch (error) {
            console.error('Error loading overview data:', error);
        }
    }

    async loadProfileData() {
        try {
            const token = this.authManager.getToken();
            const response = await fetch('/api/user/profile', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const profile = await response.json();
                this.populateProfileForm(profile);
            }
        } catch (error) {
            console.error('Error loading profile data:', error);
        }
    }

    async loadRecommendations() {
        try {
            const token = this.authManager.getToken();
            const sort = document.getElementById('recommendationSort')?.value || 'score';
            
            const response = await fetch(`/api/user/recommendations?sort=${sort}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const recommendations = await response.json();
                this.displayRecommendations(recommendations);
            }
        } catch (error) {
            console.error('Error loading recommendations:', error);
        }
    }

    async loadSavedJobs() {
        try {
            const token = this.authManager.getToken();
            const sort = document.getElementById('savedJobsSort')?.value || 'date';
            
            const response = await fetch(`/api/user/saved-jobs?sort=${sort}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const savedJobs = await response.json();
                this.displaySavedJobs(savedJobs);
            }
        } catch (error) {
            console.error('Error loading saved jobs:', error);
        }
    }

    async loadApplications() {
        try {
            const token = this.authManager.getToken();
            const status = document.getElementById('applicationStatus')?.value || '';
            const sort = document.getElementById('applicationSort')?.value || 'date';
            
            let url = `/api/user/applications?sort=${sort}`;
            if (status) url += `&status=${status}`;
            
            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const applications = await response.json();
                this.displayApplications(applications);
            }
        } catch (error) {
            console.error('Error loading applications:', error);
        }
    }

    async loadNotifications() {
        try {
            const token = this.authManager.getToken();
            const response = await fetch('/api/user/notifications', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const notifications = await response.json();
                this.displayNotifications(notifications);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    updateProfileCompleteness(percentage) {
        const progressElement = document.getElementById('profileProgress');
        const percentageElement = document.getElementById('profilePercentage');
        
        if (progressElement && percentageElement) {
            percentageElement.textContent = `${percentage}%`;
            progressElement.style.setProperty('--progress', `${percentage}%`);
            
            // Add color based on completeness
            progressElement.className = 'progress-circle';
            if (percentage >= 80) {
                progressElement.classList.add('high');
            } else if (percentage >= 50) {
                progressElement.classList.add('medium');
            } else {
                progressElement.classList.add('low');
            }
        }
    }

    updateRecentActivity(activities) {
        const container = document.getElementById('recentActivity');
        if (!container) return;

        if (!activities || activities.length === 0) {
            container.innerHTML = '<p class="no-data">No recent activity</p>';
            return;
        }

        const html = activities.slice(0, 5).map(activity => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas ${this.getActivityIcon(activity.type)}"></i>
                </div>
                <div class="activity-content">
                    <p>${activity.description}</p>
                    <span class="activity-time">${this.formatTimeAgo(activity.created_at)}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    updateQuickRecommendations(recommendations) {
        const container = document.getElementById('quickRecommendations');
        const countElement = document.getElementById('recommendationCount');
        
        if (countElement) {
            countElement.textContent = recommendations.total || 0;
        }

        if (!container) return;

        if (!recommendations.items || recommendations.items.length === 0) {
            container.innerHTML = '<p class="no-data">No recommendations available</p>';
            return;
        }

        const html = recommendations.items.map(rec => `
            <div class="recommendation-item">
                <h4>${rec.job_title}</h4>
                <p>${rec.company_name}</p>
                <div class="match-score">
                    <span class="score">${Math.round(rec.match_score * 100)}% match</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    updateApplicationStats(stats) {
        const appliedCount = document.getElementById('appliedCount');
        const interviewCount = document.getElementById('interviewCount');
        const offerCount = document.getElementById('offerCount');

        if (appliedCount) appliedCount.textContent = stats.applied || 0;
        if (interviewCount) interviewCount.textContent = stats.interview || 0;
        if (offerCount) offerCount.textContent = stats.offer || 0;
    }

    populateProfileForm(profile) {
        const fields = {
            'profileName': profile.full_name,
            'profileEmail': profile.email,
            'profilePhone': profile.phone_number,
            'profileLocation': profile.location,
            'profileBio': profile.bio,
            'profileExperience': profile.years_of_experience,
            'profileSalaryRange': profile.desired_salary_range,
            'profileSkills': profile.skills ? profile.skills.join(', ') : ''
        };

        Object.entries(fields).forEach(([fieldId, value]) => {
            const field = document.getElementById(fieldId);
            if (field && value) {
                field.value = value;
            }
        });
    }

    async handleProfileUpdate(e) {
        e.preventDefault();
        
        try {
            const formData = new FormData(e.target);
            const profileData = {
                full_name: formData.get('profileName') || document.getElementById('profileName').value,
                phone_number: formData.get('profilePhone') || document.getElementById('profilePhone').value,
                location: formData.get('profileLocation') || document.getElementById('profileLocation').value,
                bio: formData.get('profileBio') || document.getElementById('profileBio').value,
                years_of_experience: formData.get('profileExperience') || document.getElementById('profileExperience').value,
                desired_salary_range: formData.get('profileSalaryRange') || document.getElementById('profileSalaryRange').value,
                skills: (formData.get('profileSkills') || document.getElementById('profileSkills').value)
                    .split(',').map(s => s.trim()).filter(s => s)
            };

            const token = this.authManager.getToken();
            const response = await fetch('/api/user/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(profileData)
            });

            if (response.ok) {
                this.showNotification('Profile updated successfully!', 'success');
                // Refresh overview data to update completeness
                await this.loadOverviewData();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Failed to update profile', 'error');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            this.showNotification('Failed to update profile', 'error');
        }
    }

    displayRecommendations(recommendations) {
        const container = document.getElementById('recommendationsList');
        if (!container) return;

        if (!recommendations.items || recommendations.items.length === 0) {
            container.innerHTML = '<div class="no-data">No recommendations available</div>';
            return;
        }

        const html = recommendations.items.map(rec => `
            <div class="recommendation-card">
                <div class="job-header">
                    <h3>${rec.job_title}</h3>
                    <div class="match-score">
                        <span class="score">${Math.round(rec.match_score * 100)}% match</span>
                    </div>
                </div>
                <div class="job-details">
                    <p class="company">${rec.company_name}</p>
                    <p class="location">${rec.location || 'Location not specified'}</p>
                    <p class="salary">${rec.salary_range || 'Salary not specified'}</p>
                </div>
                <div class="job-description">
                    <p>${rec.description ? rec.description.substring(0, 200) + '...' : 'No description available'}</p>
                </div>
                <div class="recommendation-actions">
                    <button class="btn-primary" onclick="window.open('${rec.job_url}', '_blank')">
                        View Job
                    </button>
                    <button class="btn-secondary save-job-btn" data-job-id="${rec.job_id}">
                        <i class="fas fa-bookmark"></i> Save
                    </button>
                </div>
                <div class="match-explanation">
                    <small>${rec.explanation || 'Good match based on your profile'}</small>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;

        // Bind save job buttons
        container.querySelectorAll('.save-job-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.saveJob(e.target.dataset.jobId);
            });
        });
    }

    displaySavedJobs(savedJobs) {
        const container = document.getElementById('savedJobsList');
        if (!container) return;

        if (!savedJobs.items || savedJobs.items.length === 0) {
            container.innerHTML = '<div class="no-data">No saved jobs</div>';
            return;
        }

        const html = savedJobs.items.map(job => `
            <div class="saved-job-card">
                <div class="job-header">
                    <h3>${job.job_title}</h3>
                    <button class="remove-btn" data-job-id="${job.job_id}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="job-details">
                    <p class="company">${job.company_name}</p>
                    <p class="location">${job.location || 'Location not specified'}</p>
                    <p class="saved-date">Saved ${this.formatTimeAgo(job.saved_at)}</p>
                </div>
                <div class="job-actions">
                    <button class="btn-primary" onclick="window.open('${job.job_url}', '_blank')">
                        View Job
                    </button>
                    <button class="btn-secondary apply-btn" data-job-id="${job.job_id}">
                        Apply Now
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;

        // Bind remove buttons
        container.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.removeSavedJob(e.target.dataset.jobId);
            });
        });

        // Bind apply buttons
        container.querySelectorAll('.apply-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.applyToJob(e.target.dataset.jobId);
            });
        });
    }

    displayApplications(applications) {
        const container = document.getElementById('applicationsList');
        if (!container) return;

        if (!applications.items || applications.items.length === 0) {
            container.innerHTML = '<div class="no-data">No applications found</div>';
            return;
        }

        const html = applications.items.map(app => `
            <div class="application-card">
                <div class="application-header">
                    <h3>${app.job_title}</h3>
                    <span class="status-badge ${app.status}">${app.status.toUpperCase()}</span>
                </div>
                <div class="application-details">
                    <p class="company">${app.company_name}</p>
                    <p class="applied-date">Applied ${this.formatTimeAgo(app.applied_at)}</p>
                    ${app.interview_date ? `<p class="interview-date">Interview: ${new Date(app.interview_date).toLocaleDateString()}</p>` : ''}
                </div>
                <div class="application-actions">
                    <button class="btn-secondary" onclick="window.open('${app.job_url}', '_blank')">
                        View Job
                    </button>
                    <button class="btn-primary update-status-btn" data-app-id="${app.id}">
                        Update Status
                    </button>
                </div>
                ${app.notes ? `<div class="application-notes"><p>${app.notes}</p></div>` : ''}
            </div>
        `).join('');

        container.innerHTML = html;

        // Bind update status buttons
        container.querySelectorAll('.update-status-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.updateApplicationStatus(e.target.dataset.appId);
            });
        });
    }

    displayNotifications(notifications) {
        const container = document.getElementById('notificationsList');
        if (!container) return;

        if (!notifications.items || notifications.items.length === 0) {
            container.innerHTML = '<div class="no-data">No notifications</div>';
            return;
        }

        const html = notifications.items.map(notif => `
            <div class="notification-item ${notif.is_read ? 'read' : 'unread'}">
                <div class="notification-icon">
                    <i class="fas ${this.getNotificationIcon(notif.type)}"></i>
                </div>
                <div class="notification-content">
                    <h4>${notif.title}</h4>
                    <p>${notif.message}</p>
                    <span class="notification-time">${this.formatTimeAgo(notif.created_at)}</span>
                </div>
                <div class="notification-actions">
                    ${!notif.is_read ? `<button class="mark-read-btn" data-notif-id="${notif.id}">Mark Read</button>` : ''}
                    <button class="delete-notif-btn" data-notif-id="${notif.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;

        // Bind notification actions
        container.querySelectorAll('.mark-read-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.markNotificationRead(e.target.dataset.notifId);
            });
        });

        container.querySelectorAll('.delete-notif-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.deleteNotification(e.target.dataset.notifId);
            });
        });
    }

    // Utility methods
    getActivityIcon(type) {
        const icons = {
            'search': 'fa-search',
            'save': 'fa-bookmark',
            'apply': 'fa-paper-plane',
            'profile_update': 'fa-user-edit',
            'recommendation': 'fa-star'
        };
        return icons[type] || 'fa-info-circle';
    }

    getNotificationIcon(type) {
        const icons = {
            'job_alert': 'fa-briefcase',
            'application_update': 'fa-file-alt',
            'recommendation': 'fa-star',
            'system': 'fa-cog'
        };
        return icons[type] || 'fa-bell';
    }

    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
        
        return date.toLocaleDateString();
    }

    // Action methods
    async saveJob(jobId) {
        try {
            const token = this.authManager.getToken();
            const response = await fetch('/api/user/save-job', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ job_id: jobId })
            });

            if (response.ok) {
                this.showNotification('Job saved successfully!', 'success');
            } else {
                this.showNotification('Failed to save job', 'error');
            }
        } catch (error) {
            console.error('Error saving job:', error);
            this.showNotification('Failed to save job', 'error');
        }
    }

    async removeSavedJob(jobId) {
        try {
            const token = this.authManager.getToken();
            const response = await fetch(`/api/user/saved-jobs/${jobId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                this.showNotification('Job removed from saved list', 'success');
                await this.loadSavedJobs();
            } else {
                this.showNotification('Failed to remove job', 'error');
            }
        } catch (error) {
            console.error('Error removing saved job:', error);
            this.showNotification('Failed to remove job', 'error');
        }
    }

    async markAllNotificationsRead() {
        try {
            const token = this.authManager.getToken();
            const response = await fetch('/api/user/notifications/mark-all-read', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                this.showNotification('All notifications marked as read', 'success');
                await this.loadNotifications();
            }
        } catch (error) {
            console.error('Error marking notifications as read:', error);
        }
    }

    async clearAllNotifications() {
        if (!confirm('Are you sure you want to clear all notifications?')) {
            return;
        }

        try {
            const token = this.authManager.getToken();
            const response = await fetch('/api/user/notifications', {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                this.showNotification('All notifications cleared', 'success');
                await this.loadNotifications();
            }
        } catch (error) {
            console.error('Error clearing notifications:', error);
        }
    }

    // Filter and sort methods
    filterSavedJobs(searchTerm) {
        const cards = document.querySelectorAll('.saved-job-card');
        cards.forEach(card => {
            const title = card.querySelector('h3').textContent.toLowerCase();
            const company = card.querySelector('.company').textContent.toLowerCase();
            const matches = title.includes(searchTerm.toLowerCase()) || 
                          company.includes(searchTerm.toLowerCase());
            card.style.display = matches ? 'block' : 'none';
        });
    }

    filterApplications(status) {
        if (status) {
            this.loadApplications();
        }
    }

    handleSort(sortType, value) {
        switch (sortType) {
            case 'recommendationSort':
                this.loadRecommendations();
                break;
            case 'savedJobsSort':
                this.loadSavedJobs();
                break;
            case 'applicationSort':
                this.loadApplications();
                break;
        }
    }

    showNotification(message, type = 'info') {
        // Use the existing notification system
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
}

// Initialize dashboard manager
const dashboardManager = new DashboardManager();

// Export for use in other modules
window.dashboardManager = dashboardManager;
