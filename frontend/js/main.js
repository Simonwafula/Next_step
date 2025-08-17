// Main application controller
class CareerSearchApp {
    constructor() {
        this.currentSection = 'search';
        this.user = null;
        this.subscription = null;
        
        this.initializeApp();
    }
    
    async initializeApp() {
        // Initialize navigation
        this.initializeNavigation();
        
        // Initialize modals
        this.initializeModals();
        
        // Load user data if logged in
        await this.loadUserData();
        
        // Initialize sections
        this.initializeSections();
        
        // Set up periodic data refresh
        this.setupPeriodicRefresh();
        
        console.log('CareerSearch app initialized');
    }
    
    initializeNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.dataset.section;
                this.showSection(section);
            });
        });
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
        
        const activeLink = document.querySelector(`[data-section="${sectionName}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
        
        this.currentSection = sectionName;
        
        // Load section-specific data
        this.loadSectionData(sectionName);
    }
    
    async loadSectionData(sectionName) {
        switch (sectionName) {
            case 'insights':
                await this.loadMarketInsights();
                break;
            case 'career-tools':
                await this.loadCareerTools();
                break;
            case 'premium':
                await this.loadPremiumData();
                break;
        }
    }
    
    async loadMarketInsights() {
        try {
            // Load weekly insights
            const weeklyInsights = await api.getWeeklyInsights();
            this.displayWeeklyInsights(weeklyInsights);
            
            // Load trending skills
            const trendingSkills = await api.getTrendingSkills();
            this.displayTrendingSkills(trendingSkills);
            
            // Load trending transitions
            const trendingTransitions = await api.getTrendingTransitions();
            this.displayTrendingTransitions(trendingTransitions);
            
        } catch (error) {
            console.error('Error loading market insights:', error);
        }
    }
    
    displayWeeklyInsights(insights) {
        const container = document.getElementById('weeklyInsights');
        if (!container || !insights) return;
        
        container.innerHTML = `
            <div class="insights-summary">
                <div class="insight-stat">
                    <div class="stat-number">${insights.total_postings || 0}</div>
                    <div class="stat-label">New Jobs This Week</div>
                </div>
                <div class="insight-stat">
                    <div class="stat-number">${insights.active_companies || 0}</div>
                    <div class="stat-label">Companies Hiring</div>
                </div>
                <div class="insight-stat">
                    <div class="stat-number">${insights.median_salary ? UTILS.formatCurrency(insights.median_salary) : 'N/A'}</div>
                    <div class="stat-label">Median Salary</div>
                </div>
            </div>
            
            ${insights.top_role_families ? `
                <div class="top-roles">
                    <h5>Most In-Demand Roles</h5>
                    <div class="role-list">
                        ${insights.top_role_families.slice(0, 5).map(role => `
                            <div class="role-item">
                                <span class="role-name">${role.role_family}</span>
                                <span class="role-count">${role.count} jobs</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
    }
    
    displayTrendingSkills(skillsData) {
        const container = document.getElementById('trendingSkills');
        if (!container || !skillsData?.trending_skills) return;
        
        container.innerHTML = `
            <div class="skills-list">
                ${skillsData.trending_skills.slice(0, 10).map(skill => `
                    <div class="skill-item">
                        <span class="skill-name">${skill.skill}</span>
                        <span class="skill-growth ${skill.growth_rate > 0 ? 'positive' : 'negative'}">
                            ${skill.growth_rate > 0 ? '+' : ''}${skill.growth_rate}%
                        </span>
                    </div>
                `).join('')}
            </div>
            <p class="skills-note">Growth rates compared to previous week</p>
        `;
    }
    
    displayTrendingTransitions(transitionsData) {
        const container = document.getElementById('careerTransitions');
        if (!container || !transitionsData?.trending_roles) return;
        
        container.innerHTML = `
            <div class="transitions-list">
                ${transitionsData.trending_roles.slice(0, 5).map(transition => `
                    <div class="transition-item">
                        <div class="transition-role">${transition.target_role}</div>
                        <div class="transition-count">${transition.transition_count} professionals transitioning</div>
                    </div>
                `).join('')}
            </div>
            <p class="transitions-note">Based on ${transitionsData.period} of job market activity</p>
        `;
    }
    
    async loadCareerTools() {
        // Initialize career tools functionality
        this.initializeToolButtons();
    }
    
    initializeToolButtons() {
        const toolButtons = document.querySelectorAll('.tool-btn');
        
        toolButtons.forEach(button => {
            button.addEventListener('click', () => {
                const toolType = button.dataset.tool;
                this.openCareerTool(toolType);
            });
        });
    }
    
    openCareerTool(toolType) {
        // Check if user has access to premium tools
        if (this.isPremiumTool(toolType) && !this.hasFeatureAccess(toolType)) {
            this.showPremiumUpgradeModal(toolType);
            return;
        }
        
        // Open the appropriate tool modal
        this.showToolModal(toolType);
    }
    
    isPremiumTool(toolType) {
        const premiumTools = ['cv-builder', 'cover-letter', 'why-work-with'];
        return premiumTools.includes(toolType);
    }
    
    hasFeatureAccess(feature) {
        if (!this.subscription) return false;
        
        const featureMap = {
            'cv-builder': 'ai_cv_optimization',
            'cover-letter': 'personalized_cover_letters',
            'why-work-with': 'advanced_career_coaching'
        };
        
        const requiredFeature = featureMap[feature];
        return this.subscription.features.includes(requiredFeature);
    }
    
    showToolModal(toolType) {
        const modal = document.getElementById('toolModal');
        const content = document.getElementById('toolContent');
        
        // Generate tool content based on type
        content.innerHTML = this.generateToolContent(toolType);
        
        // Show modal
        modal.style.display = 'block';
        
        // Initialize tool-specific functionality
        this.initializeToolContent(toolType);
    }
    
    generateToolContent(toolType) {
        switch (toolType) {
            case 'cv-builder':
                return this.generateCVBuilderContent();
            case 'cover-letter':
                return this.generateCoverLetterContent();
            case 'why-work-with':
                return this.generateStatementContent();
            case 'career-advisor':
                return this.generateCareerAdvisorContent();
            default:
                return '<p>Tool content not available.</p>';
        }
    }
    
    generateCVBuilderContent() {
        return `
            <h2><i class="fas fa-file-alt"></i> CV Builder</h2>
            <div class="tool-form">
                <div class="form-group">
                    <label for="cvName">Full Name</label>
                    <input type="text" id="cvName" placeholder="Enter your full name">
                </div>
                
                <div class="form-group">
                    <label for="cvEmail">Email</label>
                    <input type="email" id="cvEmail" placeholder="your.email@example.com">
                </div>
                
                <div class="form-group">
                    <label for="cvPhone">Phone Number</label>
                    <input type="tel" id="cvPhone" placeholder="+254...">
                </div>
                
                <div class="form-group">
                    <label for="cvLocation">Location</label>
                    <input type="text" id="cvLocation" placeholder="City, Country">
                </div>
                
                <div class="form-group">
                    <label for="cvEducation">Education</label>
                    <textarea id="cvEducation" rows="3" placeholder="Your educational background..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="cvExperience">Work Experience</label>
                    <textarea id="cvExperience" rows="5" placeholder="Your work experience and achievements..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="cvSkills">Skills</label>
                    <textarea id="cvSkills" rows="3" placeholder="Your key skills and competencies..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="cvTargetRole">Target Role (Optional)</label>
                    <input type="text" id="cvTargetRole" placeholder="e.g., Data Analyst, Software Engineer">
                </div>
                
                <div class="tool-actions">
                    <button class="btn-primary" id="generateCV">
                        <i class="fas fa-magic"></i> Generate CV
                    </button>
                </div>
                
                <div id="cvOutput" class="tool-output" style="display: none;">
                    <!-- Generated CV will appear here -->
                </div>
            </div>
        `;
    }
    
    generateCoverLetterContent() {
        return `
            <h2><i class="fas fa-envelope"></i> Cover Letter Generator</h2>
            <div class="tool-form">
                <div class="form-group">
                    <label for="clJobTitle">Job Title</label>
                    <input type="text" id="clJobTitle" placeholder="e.g., Marketing Manager">
                </div>
                
                <div class="form-group">
                    <label for="clCompany">Company Name</label>
                    <input type="text" id="clCompany" placeholder="Company you're applying to">
                </div>
                
                <div class="form-group">
                    <label for="clJobDescription">Job Description</label>
                    <textarea id="clJobDescription" rows="4" placeholder="Paste the job description here..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="clYourBackground">Your Background</label>
                    <textarea id="clYourBackground" rows="3" placeholder="Brief summary of your relevant experience..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="clYourSkills">Relevant Skills</label>
                    <textarea id="clYourSkills" rows="2" placeholder="Skills relevant to this position..."></textarea>
                </div>
                
                <div class="tool-actions">
                    <button class="btn-primary" id="generateCoverLetter">
                        <i class="fas fa-magic"></i> Generate Cover Letter
                    </button>
                </div>
                
                <div id="coverLetterOutput" class="tool-output" style="display: none;">
                    <!-- Generated cover letter will appear here -->
                </div>
            </div>
        `;
    }
    
    generateStatementContent() {
        return `
            <h2><i class="fas fa-handshake"></i> Why Work With Me Statement</h2>
            <div class="tool-form">
                <div class="form-group">
                    <label for="stBackground">Professional Background</label>
                    <textarea id="stBackground" rows="3" placeholder="Brief overview of your professional background..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="stExperience">Key Experience</label>
                    <textarea id="stExperience" rows="3" placeholder="Your most relevant work experience..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="stSkills">Core Skills</label>
                    <textarea id="stSkills" rows="2" placeholder="Your strongest skills and competencies..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="stAchievements">Key Achievements</label>
                    <textarea id="stAchievements" rows="3" placeholder="Your notable achievements and accomplishments..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="stValues">Professional Values</label>
                    <textarea id="stValues" rows="2" placeholder="What drives you professionally..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="stTargetRole">Target Role Context (Optional)</label>
                    <input type="text" id="stTargetRole" placeholder="Role you're targeting">
                </div>
                
                <div class="tool-actions">
                    <button class="btn-primary" id="generateStatement">
                        <i class="fas fa-magic"></i> Generate Statement
                    </button>
                </div>
                
                <div id="statementOutput" class="tool-output" style="display: none;">
                    <!-- Generated statement will appear here -->
                </div>
            </div>
        `;
    }
    
    generateCareerAdvisorContent() {
        return `
            <h2><i class="fas fa-route"></i> Career Path Advisor</h2>
            <div class="tool-form">
                <div class="form-group">
                    <label for="caCurrentRole">Current Role/Background</label>
                    <input type="text" id="caCurrentRole" placeholder="e.g., Junior Developer, Recent Graduate">
                </div>
                
                <div class="form-group">
                    <label for="caExperienceLevel">Experience Level</label>
                    <select id="caExperienceLevel">
                        <option value="">Select experience level</option>
                        <option value="entry">Entry Level (0-2 years)</option>
                        <option value="mid">Mid Level (3-5 years)</option>
                        <option value="senior">Senior Level (6+ years)</option>
                        <option value="executive">Executive Level</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="caSkills">Current Skills</label>
                    <textarea id="caSkills" rows="2" placeholder="Your current skills and competencies..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="caGoals">Career Goals</label>
                    <textarea id="caGoals" rows="3" placeholder="What are your career aspirations?"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="caQuery">Specific Question</label>
                    <textarea id="caQuery" rows="3" placeholder="What specific career advice are you looking for?"></textarea>
                </div>
                
                <div class="tool-actions">
                    <button class="btn-primary" id="getCareerAdvice">
                        <i class="fas fa-lightbulb"></i> Get Career Advice
                    </button>
                </div>
                
                <div id="careerAdviceOutput" class="tool-output" style="display: none;">
                    <!-- Career advice will appear here -->
                </div>
            </div>
        `;
    }
    
    initializeToolContent(toolType) {
        switch (toolType) {
            case 'cv-builder':
                this.initializeCVBuilder();
                break;
            case 'cover-letter':
                this.initializeCoverLetterGenerator();
                break;
            case 'why-work-with':
                this.initializeStatementGenerator();
                break;
            case 'career-advisor':
                this.initializeCareerAdvisor();
                break;
        }
    }
    
    initializeCVBuilder() {
        const generateBtn = document.getElementById('generateCV');
        generateBtn.addEventListener('click', async () => {
            const userData = {
                name: document.getElementById('cvName').value,
                email: document.getElementById('cvEmail').value,
                phone: document.getElementById('cvPhone').value,
                location: document.getElementById('cvLocation').value,
                education: document.getElementById('cvEducation').value,
                experience: document.getElementById('cvExperience').value,
                skills: document.getElementById('cvSkills').value
            };
            
            const targetRole = document.getElementById('cvTargetRole').value;
            
            await this.generateCV(userData, targetRole);
        });
    }
    
    async generateCV(userData, targetRole) {
        const output = document.getElementById('cvOutput');
        const generateBtn = document.getElementById('generateCV');
        
        try {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
            
            // Mock API call - replace with actual API call
            const response = await this.mockGenerateCV(userData, targetRole);
            
            output.innerHTML = `
                <h3>Generated CV</h3>
                <div class="cv-preview">
                    <pre>${response.cv_content.content}</pre>
                </div>
                <div class="cv-actions">
                    <button class="btn-primary" onclick="this.downloadCV()">
                        <i class="fas fa-download"></i> Download CV
                    </button>
                    <button class="btn-secondary" onclick="this.editCV()">
                        <i class="fas fa-edit"></i> Edit CV
                    </button>
                </div>
            `;
            
            output.style.display = 'block';
            
        } catch (error) {
            notifications.error('Failed to generate CV. Please try again.');
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-magic"></i> Generate CV';
        }
    }
    
    async mockGenerateCV(userData, targetRole) {
        // Mock response - replace with actual API call
        return new Promise(resolve => {
            setTimeout(() => {
                resolve({
                    success: true,
                    cv_content: {
                        content: `${userData.name}
${userData.email} | ${userData.phone} | ${userData.location}

PROFESSIONAL SUMMARY
Results-driven professional with proven track record in delivering high-quality solutions and driving business growth. Strong analytical skills combined with excellent communication abilities and a passion for continuous learning.

EDUCATION
${userData.education}

WORK EXPERIENCE
${userData.experience}

KEY SKILLS
${userData.skills}

Generated for: ${targetRole || 'General Position'}`
                    }
                });
            }, 2000);
        });
    }
    
    async loadPremiumData() {
        if (this.user) {
            // Load user's subscription data
            this.subscription = await this.getUserSubscription();
            this.updatePremiumUI();
        }
    }
    
    async getUserSubscription() {
        try {
            // Mock subscription data - replace with actual API call
            return {
                plan_id: 'professional',
                plan_name: 'Professional',
                features: ['ai_cv_optimization', 'personalized_cover_letters'],
                days_remaining: 25
            };
        } catch (error) {
            return null;
        }
    }
    
    updatePremiumUI() {
        // Update premium section based on user's subscription
        const premiumCards = document.querySelectorAll('.pricing-card');
        
        if (this.subscription) {
            premiumCards.forEach(card => {
                const planName = card.querySelector('h3').textContent.toLowerCase();
                if (planName === this.subscription.plan_name.toLowerCase()) {
                    const button = card.querySelector('button');
                    button.textContent = 'Current Plan';
                    button.classList.remove('btn-primary');
                    button.classList.add('btn-secondary');
                }
            });
        }
    }
    
    initializeModals() {
        // Login modal
        const loginBtn = document.getElementById('loginBtn');
        const loginModal = document.getElementById('loginModal');
        
        loginBtn.addEventListener('click', () => {
            loginModal.style.display = 'block';
        });
        
        // Signup modal
        const signupBtn = document.getElementById('signupBtn');
        const signupModal = document.getElementById('signupModal');
        
        signupBtn.addEventListener('click', () => {
            signupModal.style.display = 'block';
        });
        
        // Close modal handlers
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                modal.style.display = 'none';
            });
        });
        
        // Click outside to close
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });
    }
    
    async loadUserData() {
        const token = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_TOKEN);
        if (token) {
            try {
                // Load user data from API
                this.user = JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.USER_DATA) || 'null');
                if (this.user) {
                    this.updateUIForLoggedInUser();
                }
            } catch (error) {
                console.error('Error loading user data:', error);
            }
        }
    }
    
    updateUIForLoggedInUser() {
        const loginBtn = document.getElementById('loginBtn');
        const signupBtn = document.getElementById('signupBtn');
        
        loginBtn.textContent = this.user.name || 'Profile';
        signupBtn.style.display = 'none';
    }
    
    setupPeriodicRefresh() {
        // Refresh market insights every 30 minutes
        setInterval(() => {
            if (this.currentSection === 'insights') {
                this.loadMarketInsights();
            }
        }, 30 * 60 * 1000);
    }
    
    showPremiumUpgradeModal(toolType) {
        notifications.warning(
            'This feature requires a premium subscription. Upgrade to access advanced career tools.',
            'Premium Feature'
        );
        
        // Switch to premium section
        this.showSection('premium');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.careerSearchApp = new CareerSearchApp();
});

// Global utility functions
window.downloadCV = function() {
    notifications.info('CV download functionality would be implemented here');
};

window.editCV = function() {
    notifications.info('CV editing functionality would be implemented here');
};
