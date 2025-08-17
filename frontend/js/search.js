// Search functionality for the career search platform
class SearchManager {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.searchBtn = document.getElementById('searchBtn');
        this.locationFilter = document.getElementById('locationFilter');
        this.seniorityFilter = document.getElementById('seniorityFilter');
        this.sortBy = document.getElementById('sortBy');
        this.searchResults = document.getElementById('searchResults');
        this.resultsList = document.getElementById('resultsList');
        this.resultsTitle = document.getElementById('resultsTitle');
        this.resultsCount = document.getElementById('resultsCount');
        this.careerInsights = document.getElementById('careerInsights');
        this.salaryInsights = document.getElementById('salaryInsights');
        
        this.currentQuery = '';
        this.currentFilters = {};
        this.searchHistory = this.loadSearchHistory();
        
        this.initializeEventListeners();
        this.initializeQuickSearches();
    }
    
    initializeEventListeners() {
        // Search input with debounced search
        const debouncedSearch = UTILS.debounce(() => {
            this.performSearch();
        }, CONFIG.SEARCH_DEBOUNCE_MS);
        
        this.searchInput.addEventListener('input', debouncedSearch);
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.performSearch();
            }
        });
        
        // Search button
        this.searchBtn.addEventListener('click', () => {
            this.performSearch();
        });
        
        // Filter changes
        this.locationFilter.addEventListener('change', () => {
            this.performSearch();
        });
        
        this.seniorityFilter.addEventListener('change', () => {
            this.performSearch();
        });
        
        // Sort changes
        if (this.sortBy) {
            this.sortBy.addEventListener('change', () => {
                this.performSearch();
            });
        }
        
        // Handle URL parameters on page load
        this.handleUrlParameters();
    }
    
    initializeQuickSearches() {
        const quickSearchBtns = document.querySelectorAll('.quick-search-btn');
        quickSearchBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const query = btn.dataset.query;
                this.searchInput.value = query;
                this.performSearch();
            });
        });
    }
    
    handleUrlParameters() {
        const params = UTILS.getQueryParams();
        if (params.q) {
            this.searchInput.value = params.q;
            if (params.location) this.locationFilter.value = params.location;
            if (params.seniority) this.seniorityFilter.value = params.seniority;
            this.performSearch();
        }
    }
    
    async performSearch() {
        const query = this.searchInput.value.trim();
        
        if (!query) {
            this.hideSearchResults();
            return;
        }
        
        // Update current search state
        this.currentQuery = query;
        this.currentFilters = {
            location: this.locationFilter.value,
            seniority: this.seniorityFilter.value
        };
        
        // Update URL parameters
        UTILS.setQueryParams({
            q: query,
            location: this.currentFilters.location || null,
            seniority: this.currentFilters.seniority || null
        });
        
        // Show loading state
        this.showLoadingState();
        
        try {
            // Perform the search
            const results = await api.searchJobs(query, this.currentFilters);
            
            // Display results
            this.displaySearchResults(results, query);
            
            // Load additional insights
            await this.loadSearchInsights(query);
            
            // Save to search history
            this.saveToSearchHistory(query, this.currentFilters);
            
        } catch (error) {
            console.error('Search error:', error);
            notifications.error('Search failed. Please try again.');
            this.hideSearchResults();
        }
    }
    
    showLoadingState() {
        this.searchResults.style.display = 'block';
        this.resultsList.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <span>Searching for opportunities...</span>
            </div>
        `;
        this.resultsTitle.textContent = 'Searching...';
        this.resultsCount.textContent = '';
    }
    
    displaySearchResults(results, query) {
        if (!results || results.length === 0) {
            this.displayNoResults(query);
            return;
        }
        
        // Update results header
        this.resultsTitle.textContent = `Search Results for "${query}"`;
        this.resultsCount.textContent = `${results.length} jobs found`;
        
        // Display job cards
        this.resultsList.innerHTML = results.map(job => this.createJobCard(job)).join('');
        
        // Add click handlers to job cards
        this.addJobCardHandlers();
        
        // Show results section
        this.searchResults.style.display = 'block';
    }
    
    displayNoResults(query) {
        this.resultsTitle.textContent = `No results found for "${query}"`;
        this.resultsCount.textContent = '0 jobs found';
        
        this.resultsList.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">
                    <i class="fas fa-search"></i>
                </div>
                <h3>No jobs found</h3>
                <p>We couldn't find any jobs matching your search criteria.</p>
                <div class="no-results-suggestions">
                    <h4>Try:</h4>
                    <ul>
                        <li>Using different keywords</li>
                        <li>Removing location or seniority filters</li>
                        <li>Checking for spelling mistakes</li>
                        <li>Using more general terms</li>
                    </ul>
                </div>
                <div class="suggested-searches">
                    <h4>Popular searches:</h4>
                    <div class="suggested-search-buttons">
                        <button class="btn-secondary suggested-search" data-query="data analyst">Data Analyst</button>
                        <button class="btn-secondary suggested-search" data-query="software engineer">Software Engineer</button>
                        <button class="btn-secondary suggested-search" data-query="marketing">Marketing</button>
                        <button class="btn-secondary suggested-search" data-query="finance">Finance</button>
                    </div>
                </div>
            </div>
        `;
        
        // Add handlers for suggested searches
        document.querySelectorAll('.suggested-search').forEach(btn => {
            btn.addEventListener('click', () => {
                this.searchInput.value = btn.dataset.query;
                this.performSearch();
            });
        });
        
        this.searchResults.style.display = 'block';
    }
    
    createJobCard(job) {
        const salaryInfo = job.salary_min && job.salary_max 
            ? `<div class="job-salary">${UTILS.formatCurrency(job.salary_min)} - ${UTILS.formatCurrency(job.salary_max)}</div>`
            : job.salary_min 
            ? `<div class="job-salary">From ${UTILS.formatCurrency(job.salary_min)}</div>`
            : '';
            
        const description = job.description 
            ? UTILS.truncateText(job.description, 200)
            : 'No description available.';
            
        const skills = job.skills && job.skills.length > 0
            ? job.skills.slice(0, 5).map(skill => `<span class="job-tag">${skill}</span>`).join('')
            : '';
            
        const postedDate = job.created_at 
            ? UTILS.formatRelativeTime(job.created_at)
            : 'Recently posted';
            
        return `
            <div class="job-card" data-job-id="${job.id}" data-job-url="${job.url}">
                <div class="job-header">
                    <div class="job-info">
                        <h3 class="job-title">${job.title_raw || job.title}</h3>
                        <div class="job-company">${job.organization?.name || 'Company not specified'}</div>
                        <div class="job-location">
                            <i class="fas fa-map-marker-alt"></i>
                            ${job.location?.city || job.location?.raw || 'Location not specified'}
                        </div>
                        <div class="job-posted">
                            <i class="fas fa-clock"></i>
                            ${postedDate}
                        </div>
                    </div>
                    <div class="job-actions">
                        ${salaryInfo}
                        <div class="job-seniority">${job.seniority || 'Not specified'}</div>
                    </div>
                </div>
                
                <div class="job-description">
                    ${description}
                </div>
                
                ${skills ? `<div class="job-tags">${skills}</div>` : ''}
                
                <div class="job-footer">
                    <div class="job-meta">
                        <span class="job-type">${job.role_family || 'General'}</span>
                        ${job.source ? `<span class="job-source">via ${UTILS.capitalize(job.source)}</span>` : ''}
                    </div>
                    <div class="job-actions-buttons">
                        <button class="btn-secondary job-save" data-job-id="${job.id}">
                            <i class="fas fa-bookmark"></i> Save
                        </button>
                        <button class="btn-primary job-apply" data-job-url="${job.url}">
                            Apply Now <i class="fas fa-external-link-alt"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    addJobCardHandlers() {
        // Job card click handlers
        document.querySelectorAll('.job-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't trigger if clicking on buttons
                if (e.target.closest('button')) return;
                
                const jobUrl = card.dataset.jobUrl;
                if (jobUrl) {
                    window.open(jobUrl, '_blank');
                }
            });
        });
        
        // Apply button handlers
        document.querySelectorAll('.job-apply').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const jobUrl = btn.dataset.jobUrl;
                if (jobUrl) {
                    window.open(jobUrl, '_blank');
                }
            });
        });
        
        // Save button handlers
        document.querySelectorAll('.job-save').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const jobId = btn.dataset.jobId;
                this.toggleJobSave(jobId, btn);
            });
        });
    }
    
    async loadSearchInsights(query) {
        try {
            // Load career insights based on search query
            const insights = await this.getCareerInsights(query);
            this.displayCareerInsights(insights);
            
            // Load salary insights
            const salaryInsights = await this.getSalaryInsights(query);
            this.displaySalaryInsights(salaryInsights);
            
        } catch (error) {
            console.error('Error loading search insights:', error);
        }
    }
    
    async getCareerInsights(query) {
        // Check if query is about degree/education
        if (query.toLowerCase().includes('i studied') || query.toLowerCase().includes('degree')) {
            const degree = query.replace(/i studied|degree/gi, '').trim();
            if (degree) {
                return await api.getCareersForDegree(degree);
            }
        }
        
        // Get career recommendations
        try {
            return await api.getRecommendations(query);
        } catch (error) {
            return null;
        }
    }
    
    async getSalaryInsights(query) {
        try {
            const location = this.currentFilters.location;
            return await api.getSalaryInsights(query, location);
        } catch (error) {
            return null;
        }
    }
    
    displayCareerInsights(insights) {
        if (!insights) {
            this.careerInsights.innerHTML = '<p>No career insights available.</p>';
            return;
        }
        
        if (insights.relevant_careers) {
            // Display degree-based career suggestions
            this.careerInsights.innerHTML = `
                <h5>Relevant Career Paths</h5>
                <div class="career-suggestions">
                    ${insights.relevant_careers.slice(0, 5).map(career => `
                        <div class="career-suggestion">
                            <strong>${career}</strong>
                        </div>
                    `).join('')}
                </div>
                <p class="insight-explanation">${insights.explanation}</p>
            `;
        } else if (insights.length > 0) {
            // Display career transition recommendations
            this.careerInsights.innerHTML = `
                <h5>Career Transition Opportunities</h5>
                <div class="transition-suggestions">
                    ${insights.slice(0, 3).map(rec => `
                        <div class="transition-suggestion">
                            <strong>${rec.target_role}</strong>
                            <div class="skill-overlap">${rec.overlap_percentage}% skill match</div>
                            ${rec.missing_skills && rec.missing_skills.length > 0 ? `
                                <div class="missing-skills">
                                    Skills to develop: ${rec.missing_skills.join(', ')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            this.careerInsights.innerHTML = '<p>No specific career insights available for this search.</p>';
        }
    }
    
    displaySalaryInsights(insights) {
        if (!insights || !insights.salary_insights) {
            this.salaryInsights.innerHTML = '<p>No salary data available.</p>';
            return;
        }
        
        const salary = insights.salary_insights;
        this.salaryInsights.innerHTML = `
            <h5>Salary Insights</h5>
            <div class="salary-breakdown">
                ${salary.percentile_25 ? `
                    <div class="salary-item">
                        <span class="salary-label">25th percentile:</span>
                        <span class="salary-value">${UTILS.formatCurrency(salary.percentile_25)}</span>
                    </div>
                ` : ''}
                ${salary.median ? `
                    <div class="salary-item">
                        <span class="salary-label">Median:</span>
                        <span class="salary-value">${UTILS.formatCurrency(salary.median)}</span>
                    </div>
                ` : ''}
                ${salary.percentile_75 ? `
                    <div class="salary-item">
                        <span class="salary-label">75th percentile:</span>
                        <span class="salary-value">${UTILS.formatCurrency(salary.percentile_75)}</span>
                    </div>
                ` : ''}
            </div>
            ${salary.data_coverage ? `
                <p class="salary-coverage">Based on ${salary.data_coverage.count} job postings</p>
            ` : ''}
        `;
    }
    
    toggleJobSave(jobId, button) {
        // Get saved jobs from localStorage
        let savedJobs = JSON.parse(localStorage.getItem('saved_jobs') || '[]');
        
        if (savedJobs.includes(jobId)) {
            // Remove from saved jobs
            savedJobs = savedJobs.filter(id => id !== jobId);
            button.innerHTML = '<i class="fas fa-bookmark"></i> Save';
            button.classList.remove('saved');
            notifications.info('Job removed from saved jobs');
        } else {
            // Add to saved jobs
            savedJobs.push(jobId);
            button.innerHTML = '<i class="fas fa-bookmark"></i> Saved';
            button.classList.add('saved');
            notifications.success('Job saved successfully');
        }
        
        localStorage.setItem('saved_jobs', JSON.stringify(savedJobs));
    }
    
    saveToSearchHistory(query, filters) {
        const searchItem = {
            query,
            filters,
            timestamp: Date.now()
        };
        
        // Add to beginning of history
        this.searchHistory.unshift(searchItem);
        
        // Keep only last 10 searches
        this.searchHistory = this.searchHistory.slice(0, 10);
        
        // Save to localStorage
        localStorage.setItem(CONFIG.STORAGE_KEYS.SEARCH_HISTORY, JSON.stringify(this.searchHistory));
    }
    
    loadSearchHistory() {
        try {
            return JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.SEARCH_HISTORY) || '[]');
        } catch (error) {
            return [];
        }
    }
    
    hideSearchResults() {
        this.searchResults.style.display = 'none';
    }
    
    clearSearch() {
        this.searchInput.value = '';
        this.locationFilter.value = '';
        this.seniorityFilter.value = '';
        this.hideSearchResults();
        UTILS.setQueryParams({ q: null, location: null, seniority: null });
    }
}

// Initialize search manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.searchManager = new SearchManager();
});
