const form = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const locationFilter = document.getElementById('locationFilter');
const seniorityFilter = document.getElementById('seniorityFilter');
const guidedModeWrap = document.getElementById('guidedModeWrap');
const guidedModeButtons = document.querySelectorAll('[data-guided-mode]');
const resultsGrid = document.getElementById('resultsGrid');
const resultsMeta = document.getElementById('resultsMeta');
const resultsTitle = document.getElementById('resultsTitle');
const saveSearchAlertBtn = document.getElementById('saveSearchAlertBtn');
const guidedResults = document.getElementById('guidedResults');
const guidedResultsGrid = document.getElementById('guidedResultsGrid');
const guidedModeError = document.getElementById('guidedModeError');
const resultsFilters = document.getElementById('resultsFilters');
const roleFamilyClustersEl = document.getElementById('roleFamilyClusters');
const seniorityClustersEl = document.getElementById('seniorityClusters');
const countyClustersEl = document.getElementById('countyClusters');
const sectorClustersEl = document.getElementById('sectorClusters');
const qualityClustersEl = document.getElementById('qualityClusters');
const focusSearchBtn = document.getElementById('focusSearch');
const authModal = document.getElementById('authModal');
const authTabs = document.querySelectorAll('[data-auth-tab]');
const authViews = {
    signin: document.getElementById('authSignin'),
    signup: document.getElementById('authSignup'),
    reset: document.getElementById('authReset'),
};
const authOpenButtons = document.querySelectorAll('[data-auth-open]');
const authCloseButtons = document.querySelectorAll('[data-auth-close]');
const authActions = document.getElementById('authActions');
const userActions = document.getElementById('userActions');
const userGreeting = document.getElementById('userGreeting');
const userMenuBtn = document.getElementById('userMenuBtn');
const userDropdown = document.getElementById('userDropdown');
const logoutBtn = document.getElementById('logoutBtn');
const dashboardNav = document.getElementById('dashboardNav');
const dashboardMenuLink = document.getElementById('dashboardMenuLink');
const adminMenuLink = document.getElementById('adminMenuLink');
const signinForm = document.getElementById('signinForm');
const signupForm = document.getElementById('signupForm');
const resetRequestForm = document.getElementById('resetRequestForm');
const resetConfirmForm = document.getElementById('resetConfirmForm');
const resetMessage = document.getElementById('resetMessage');
const signinError = document.getElementById('signinError');
const signupError = document.getElementById('signupError');
const googleButtons = document.querySelectorAll('[data-google-auth]');
const accountSection = document.getElementById('account');
const accountTabs = document.querySelectorAll('.account-tabs [data-account-tab]');
const dropdownTabs = document.querySelectorAll('#userDropdown [data-account-tab]');
const accountViews = {
    profile: document.getElementById('accountProfile'),
    saved: document.getElementById('accountSaved'),
    alerts: document.getElementById('accountAlerts'),
};
const profileName = document.getElementById('profileName');
const profileEmail = document.getElementById('profileEmail');
const profileLocation = document.getElementById('profileLocation');
const profileSkills = document.getElementById('profileSkills');
const savedJobsList = document.getElementById('savedJobsList');
const savedJobsEmpty = document.getElementById('savedJobsEmpty');
const jobAlertForm = document.getElementById('jobAlertForm');
const jobAlertName = document.getElementById('jobAlertName');
const jobAlertQuery = document.getElementById('jobAlertQuery');
const jobAlertFrequency = document.getElementById('jobAlertFrequency');
const jobAlertStatus = document.getElementById('jobAlertStatus');
const jobAlertsList = document.getElementById('jobAlertsList');
const jobAlertsEmpty = document.getElementById('jobAlertsEmpty');

const { escapeHtml, safeUrl } = window.NEXTSTEP_SANITIZE || {
    escapeHtml: (value) => String(value ?? ''),
    safeUrl: (value) => (value ? String(value) : '#'),
};

const getApiBaseUrl = () => {
    if (document.body && document.body.dataset.apiBase) {
        return document.body.dataset.apiBase;
    }
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
        return 'http://localhost:8000/api';
    }
    return `${window.location.origin}/api`;
};

const apiBase = getApiBaseUrl();

const authStorageKey = 'nextstep_auth';
const pendingProfileKey = 'nextstep_pending_profile';

let selectedTitleCluster = null;
let selectedCompany = null;
let selectedRoleFamily = null;
let selectedSeniority = null;
let selectedCounty = null;
let selectedSector = null;
let highConfidenceOnly = false;
let currentGuidedMode = 'jobs';
let currentUserProfile = null;
let savedJobIds = new Set();
let trackedJobIds = new Set();
let currentJobAlerts = [];

const saveAuth = (payload) => {
    localStorage.setItem(authStorageKey, JSON.stringify(payload));
};

const getAuth = () => {
    const raw = localStorage.getItem(authStorageKey);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch (error) {
        return null;
    }
};

const clearAuth = () => {
    localStorage.removeItem(authStorageKey);
};

const savePendingProfile = (payload) => {
    localStorage.setItem(pendingProfileKey, JSON.stringify(payload));
};

const clearPendingProfile = () => {
    localStorage.removeItem(pendingProfileKey);
};

const resetAuthState = () => {
    clearAuth();
    clearPendingProfile();
    setAuthState(null);
};

const setAuthState = (user) => {
    if (user) {
        authActions.hidden = true;
        userActions.hidden = false;
        userGreeting.textContent = user.full_name || user.email;
        accountSection.hidden = false;
        setAccountTab('profile');
        if (dashboardNav) dashboardNav.hidden = false;
        if (dashboardMenuLink) dashboardMenuLink.hidden = false;
        if (adminMenuLink) adminMenuLink.hidden = !user.is_admin;
        if (guidedModeWrap) {
            guidedModeWrap.hidden = false;
            // Keep the user's current mode — don't silently switch it on login
        }
        updateSearchAlertButtonVisibility();
    } else {
        authActions.hidden = false;
        userActions.hidden = true;
        userGreeting.textContent = '';
        accountSection.hidden = true;
        if (dashboardNav) dashboardNav.hidden = true;
        if (dashboardMenuLink) dashboardMenuLink.hidden = true;
        if (adminMenuLink) adminMenuLink.hidden = true;
        currentUserProfile = null;
        savedJobIds = new Set();
        trackedJobIds = new Set();
        currentJobAlerts = [];
        if (guidedModeWrap) {
            guidedModeWrap.hidden = true;
            setGuidedMode('jobs', { refresh: false });
        }
        renderGuidedResults({ guided_results: null, mode_error: null }, 'jobs');
        renderJobAlerts([]);
        updateSearchAlertButtonVisibility();
    }
};

const setGuidedMode = (mode, options = {}) => {
    const { refresh = true } = options;
    currentGuidedMode = mode;

    guidedModeButtons.forEach((button) => {
        const selected = button.dataset.guidedMode === mode;
        button.setAttribute('aria-pressed', selected ? 'true' : 'false');
    });

    if (refresh && searchInput.value.trim()) {
        fetchResults();
    }
};

const redirectAfterAuth = (user) => {
    const params = new URLSearchParams(window.location.search);
    const next = params.get('next');
    if (next) {
        window.location.href = next;
        return;
    }
    if (user && user.is_admin) {
        window.location.href = 'admin.html';
        return;
    }
    window.location.href = 'dashboard.html';
};

const openAuthModal = (view) => {
    authModal.classList.add('active');
    authModal.setAttribute('aria-hidden', 'false');
    setAuthView(view);
};

const closeAuthModal = () => {
    authModal.classList.remove('active');
    authModal.setAttribute('aria-hidden', 'true');
};

const setAuthView = (view) => {
    authTabs.forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.authTab === view);
    });
    Object.entries(authViews).forEach(([key, element]) => {
        element.classList.toggle('active', key === view);
    });
    setAuthError(signinError, '');
    setAuthError(signupError, '');
    setResetMessage('');
};

const requestJson = async (url, options = {}) => {
    const response = await fetch(url, options);
    if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        const message = errorPayload.detail || `Request failed (${response.status})`;
        const error = new Error(message);
        error.status = response.status;
        throw error;
    }
    return response.json();
};

const ensureProfileData = async (token, location, skillsMap) => {
    if (!location && (!skillsMap || !Object.keys(skillsMap).length)) return;
    const payload = {};
    if (location) payload.preferred_locations = [location];
    if (skillsMap && Object.keys(skillsMap).length) payload.skills = skillsMap;
    await requestJson(`${apiBase}/auth/profile`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
    });
};

const parseSkills = (value) => {
    if (!value) return {};
    return value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
        .reduce((acc, skill) => {
            acc[skill] = 0.7;
            return acc;
        }, {});
};

const startGoogleAuth = async (context) => {
    if (context) {
        savePendingProfile(context);
    } else {
        clearPendingProfile();
    }
    const redirectUri = `${window.location.origin}/auth-callback.html`;
    const data = await requestJson(
        `${apiBase}/auth/google/url?redirect_uri=${encodeURIComponent(redirectUri)}`
    );
    window.location.href = data.authorization_url;
};

const setAuthError = (element, message) => {
    if (!element) return;
    element.textContent = message || '';
};

const setResetMessage = (message, isError = false) => {
    resetMessage.textContent = message || '';
    resetMessage.classList.toggle('auth-error', Boolean(isError));
};

const setAccountTab = (tab) => {
    accountTabs.forEach((button) => {
        button.classList.toggle('active', button.dataset.accountTab === tab);
    });
    Object.entries(accountViews).forEach(([key, view]) => {
        view.classList.toggle('active', key === tab);
    });
};

const renderSkills = (skills) => {
    profileSkills.innerHTML = '';
    if (!skills || !Object.keys(skills).length) {
        profileSkills.innerHTML = '<span>None yet</span>';
        return;
    }
    Object.keys(skills).forEach((skill) => {
        const chip = document.createElement('span');
        chip.textContent = skill;
        profileSkills.appendChild(chip);
    });
};

const renderSavedJobs = (items) => {
    savedJobsList.innerHTML = '';
    if (!items || !items.length) {
        savedJobsEmpty.hidden = false;
        return;
    }
    savedJobsEmpty.hidden = true;
    items.forEach((item) => {
        const card = document.createElement('div');
        card.className = 'saved-item';
        const title = escapeHtml(item.title || 'Untitled role');
        const org = escapeHtml(item.organization || 'Unknown organization');
        const location = escapeHtml(item.location || 'Location unspecified');
        const href = escapeHtml(safeUrl(item.url));
        card.innerHTML = `
            <div>
                <h4>${title}</h4>
                <div class="saved-meta">${org} · ${location}</div>
            </div>
            <a class="result-link" href="${href}" target="_blank" rel="noopener">Open</a>
        `;
        savedJobsList.appendChild(card);
    });
};

const setJobAlertStatus = (message, isError = false) => {
    if (!jobAlertStatus) return;
    jobAlertStatus.textContent = message || '';
    jobAlertStatus.classList.toggle('auth-error', Boolean(isError));
};

const currentSearchFilters = () => {
    const filters = {};
    if (locationFilter.value) filters.location = locationFilter.value;
    if (seniorityFilter.value) filters.seniority = seniorityFilter.value;
    if (selectedTitleCluster) filters.title = selectedTitleCluster;
    if (selectedCompany) filters.company = selectedCompany;
    if (selectedRoleFamily) filters.role_family = selectedRoleFamily;
    if (selectedCounty) filters.county = selectedCounty;
    if (selectedSector) filters.sector = selectedSector;
    if (highConfidenceOnly) filters.high_confidence_only = true;
    return filters;
};

const buildAlertNameFromSearch = () => {
    const query = searchInput.value.trim();
    const location = locationFilter.value.trim();
    const parts = [query || 'Saved search'];
    if (location) {
        parts.push(location);
    }
    return parts.join(' · ').slice(0, 120);
};

const populateJobAlertDraft = () => {
    if (!jobAlertName || !jobAlertQuery || !jobAlertFrequency) return;
    jobAlertName.value = buildAlertNameFromSearch();
    jobAlertQuery.value = searchInput.value.trim();
    jobAlertFrequency.value = 'daily';
};

const renderJobAlerts = (alerts) => {
    currentJobAlerts = Array.isArray(alerts) ? alerts : [];
    if (!jobAlertsList || !jobAlertsEmpty) return;

    jobAlertsList.innerHTML = '';
    if (!currentJobAlerts.length) {
        jobAlertsEmpty.hidden = false;
        return;
    }

    jobAlertsEmpty.hidden = true;
    currentJobAlerts.forEach((alertItem) => {
        const card = document.createElement('div');
        card.className = 'alert-item';
        const filters = alertItem.filters || {};
        const filterSummary = [
            filters.location,
            filters.seniority,
            filters.role_family,
            filters.county,
            filters.sector,
            filters.high_confidence_only ? 'High confidence only' : '',
        ].filter(Boolean).join(' · ');
        const lastTriggered = alertItem.last_triggered
            ? new Date(alertItem.last_triggered).toLocaleDateString()
            : 'Not triggered yet';

        card.innerHTML = `
            <div>
                <h4>${escapeHtml(alertItem.name || 'Job alert')}</h4>
                <div class="alert-meta">${escapeHtml(alertItem.query || '')}</div>
                <div class="alert-submeta">
                    ${escapeHtml(`${alertItem.frequency || 'daily'} · ${alertItem.jobs_found_total || 0} jobs found · Last: ${lastTriggered}`)}
                </div>
                ${filterSummary ? `<div class="alert-submeta">${escapeHtml(filterSummary)}</div>` : ''}
            </div>
            <div class="alert-item-actions">
                <button type="button" class="ghost-btn btn-sm js-delete-alert" data-alert-id="${alertItem.id}">Delete</button>
            </div>
        `;
        jobAlertsList.appendChild(card);
    });
};

const loadJobAlerts = async (token) => {
    const payload = await requestJson(`${apiBase}/users/job-alerts`, {
        headers: { Authorization: `Bearer ${token}` },
    }).catch(() => ({ alerts: [] }));
    renderJobAlerts(payload.alerts || []);
};

const updateSearchAlertButtonVisibility = () => {
    if (!saveSearchAlertBtn) return;
    const auth = getAuth();
    const query = searchInput.value.trim();
    saveSearchAlertBtn.hidden = !(auth?.access_token && query);
};

const syncUserActionState = async (token, options = {}) => {
    const { renderSaved = false } = options;

    const [savedPayload, applicationsPayload] = await Promise.all([
        requestJson(`${apiBase}/users/saved-jobs?limit=100`, {
            headers: { Authorization: `Bearer ${token}` },
        }).catch(() => ({ saved_jobs: [] })),
        requestJson(`${apiBase}/users/applications?limit=100`, {
            headers: { Authorization: `Bearer ${token}` },
        }).catch(() => ({ applications: [] })),
    ]);

    const savedItems = Array.isArray(savedPayload.saved_jobs)
        ? savedPayload.saved_jobs
        : [];
    const trackedItems = Array.isArray(applicationsPayload.applications)
        ? applicationsPayload.applications
        : [];

    savedJobIds = new Set(
        savedItems
            .map((item) => item.job_id)
            .filter((value) => Number.isInteger(value))
    );
    trackedJobIds = new Set(
        trackedItems
            .map((item) => item.job_id)
            .filter((value) => Number.isInteger(value))
    );

    if (renderSaved) {
        renderSavedJobs(savedItems);
    }
};

const showHomepageActionAuthPrompt = () => {
    openAuthModal('signin');
    setAuthError(signinError, 'Sign in to save jobs and track applications.');
};

const setResultActionMessage = (container, message, isError = false) => {
    if (!container) return;
    container.textContent = message || '';
    container.classList.toggle('error', Boolean(isError));
};

const saveJobFromResults = async ({ token, jobId, button, statusEl }) => {
    if (!token) {
        showHomepageActionAuthPrompt();
        return;
    }

    if (!jobId || savedJobIds.has(jobId)) {
        if (button) {
            button.disabled = true;
            button.textContent = 'Saved';
            button.classList.add('btn-saved');
        }
        setResultActionMessage(statusEl, 'Already saved to your account.');
        return;
    }

    const originalLabel = button?.textContent || 'Save';
    if (button) {
        button.disabled = true;
        button.textContent = 'Saving...';
    }

    try {
        await requestJson(`${apiBase}/users/saved-jobs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ job_id: jobId }),
        });
        savedJobIds.add(jobId);
        if (button) {
            button.textContent = 'Saved';
            button.classList.add('btn-saved');
        }
        setResultActionMessage(statusEl, 'Saved to your account.');
        await syncUserActionState(token, { renderSaved: true });
    } catch (error) {
        const alreadySaved = error.message?.toLowerCase().includes('already saved');
        if (alreadySaved) {
            savedJobIds.add(jobId);
            if (button) {
                button.textContent = 'Saved';
                button.classList.add('btn-saved');
                button.disabled = true;
            }
            setResultActionMessage(statusEl, 'Already saved to your account.');
            await syncUserActionState(token, { renderSaved: true });
            return;
        }

        if (button) {
            button.disabled = false;
            button.textContent = originalLabel;
        }
        setResultActionMessage(statusEl, error.message || 'Could not save this job.', true);
    }
};

const trackApplicationFromResults = async ({ token, jobId, button, statusEl }) => {
    if (!token) {
        showHomepageActionAuthPrompt();
        return;
    }

    if (!jobId || trackedJobIds.has(jobId)) {
        if (button) {
            button.disabled = true;
            button.textContent = 'Tracked';
            button.classList.add('btn-saved');
        }
        setResultActionMessage(statusEl, 'Already in your applications tracker.');
        return;
    }

    const originalLabel = button?.textContent || 'Track';
    if (button) {
        button.disabled = true;
        button.textContent = 'Tracking...';
    }

    try {
        await requestJson(`${apiBase}/users/applications`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
                job_id: jobId,
                application_source: 'homepage_search',
            }),
        });
        trackedJobIds.add(jobId);
        if (button) {
            button.textContent = 'Tracked';
            button.classList.add('btn-saved');
        }
        setResultActionMessage(statusEl, 'Added to your applications tracker.');
    } catch (error) {
        const alreadyTracked = error.message?.toLowerCase().includes('already applied');
        if (alreadyTracked) {
            trackedJobIds.add(jobId);
            if (button) {
                button.textContent = 'Tracked';
                button.classList.add('btn-saved');
                button.disabled = true;
            }
            setResultActionMessage(statusEl, 'Already in your applications tracker.');
            return;
        }

        if (button) {
            button.disabled = false;
            button.textContent = originalLabel;
        }
        setResultActionMessage(statusEl, error.message || 'Could not track this application.', true);
    }
};

const loadAccountData = async (token) => {
    try {
        const me = await requestJson(`${apiBase}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        profileName.textContent = me.full_name || '-';
        profileEmail.textContent = me.email || '-';
    } catch (error) {
        if (error.status === 401 || error.status === 403) {
            resetAuthState();
            return;
        }
    }

    try {
        const profile = await requestJson(`${apiBase}/auth/profile`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        currentUserProfile = profile;
        const location = (profile.preferred_locations || [])[0];
        profileLocation.textContent = location || 'Not set';
        if (location && !locationFilter.value) {
            locationFilter.value = location;
        }
        renderSkills(profile.skills || {});
    } catch (error) {
        currentUserProfile = null;
        profileLocation.textContent = 'Not set';
        renderSkills({});
    }

    await syncUserActionState(token, { renderSaved: true }).catch(() => {
        savedJobIds = new Set();
        trackedJobIds = new Set();
        renderSavedJobs([]);
    });
    await loadJobAlerts(token).catch(() => {
        renderJobAlerts([]);
    });
};

const renderGuidedResults = (payload, mode) => {
    if (!guidedResults || !guidedResultsGrid || !guidedModeError) return;

    if (mode === 'jobs') {
        guidedResults.hidden = true;
        guidedResultsGrid.innerHTML = '';
        guidedModeError.hidden = true;
        guidedModeError.textContent = '';
        return;
    }

    guidedResults.hidden = false;
    guidedResultsGrid.innerHTML = '';

    const modeError = payload?.mode_error;
    if (modeError) {
        guidedModeError.hidden = false;
        guidedModeError.textContent = modeError;
        return;
    }

    guidedModeError.hidden = true;
    guidedModeError.textContent = '';

    const guidedItems = Array.isArray(payload?.guided_results)
        ? payload.guided_results
        : [];

    if (!guidedItems.length) {
        const empty = document.createElement('article');
        empty.className = 'result-card';
        empty.innerHTML = '<p class="result-meta">No guided insights available yet for this query.</p>';
        guidedResultsGrid.appendChild(empty);
        return;
    }

    guidedItems.forEach((item) => {
        const card = document.createElement('article');
        card.className = 'result-card';

        if (mode === 'explore') {
            const skillTags = (item.top_skills || [])
                .slice(0, 5)
                .map((row) => `<span>${escapeHtml(row.skill_name || '')}</span>`)
                .join(', ');
            const demandCount = item.demand?.count_ads ?? 0;
            const lowConfidence = item.low_confidence
                ? `<div class="result-meta">Limited data (${escapeHtml(item.demand?.count_total_jobs_used || 0)} jobs)</div>`
                : '';
            card.innerHTML = `
                <h3 class="result-title">${escapeHtml(item.role_family || 'Role')}</h3>
                <div class="result-meta">Demand: ${escapeHtml(demandCount)}</div>
                ${lowConfidence}
                <div class="result-meta">Top skills: ${skillTags || 'Not available'}</div>
            `;
        } else if (mode === 'match') {
            const score = Math.round((Number(item.match_score || 0) * 100));
            const missing = (item.missing_skills || []).slice(0, 5).join(', ');
            const starterJobs = (item.starter_jobs || [])
                .slice(0, 3)
                .map((job) => {
                    const href = escapeHtml(safeUrl(job.url));
                    return `<a class="result-link" href="${href}" target="_blank" rel="noopener">${escapeHtml(job.title || 'Starter role')}</a>`;
                })
                .join('<br>');
            card.innerHTML = `
                <h3 class="result-title">${escapeHtml(item.role_family || 'Role')}</h3>
                <div class="result-match">${escapeHtml(score)}% match</div>
                <div class="result-meta">Missing skills: ${escapeHtml(missing || 'None')}</div>
                <div class="result-meta">${starterJobs || 'No starter jobs available.'}</div>
            `;
        } else {
            const gap = (item.skill_gap || []).slice(0, 6).join(', ');
            const shared = (item.shared_skills || []).slice(0, 5).join(', ');
            const jobs = (item.target_jobs || [])
                .slice(0, 3)
                .map((job) => {
                    const href = escapeHtml(safeUrl(job.url));
                    return `<a class="result-link" href="${href}" target="_blank" rel="noopener">${escapeHtml(job.title || 'Target role')}</a>`;
                })
                .join('<br>');
            card.innerHTML = `
                <h3 class="result-title">${escapeHtml(item.target_role || 'Transition role')}</h3>
                <div class="result-match">Difficulty: ${escapeHtml(item.difficulty_proxy || 'Unknown')}</div>
                <div class="result-meta">Skill gap: ${escapeHtml(gap || 'None')}</div>
                <div class="result-meta">Shared skills: ${escapeHtml(shared || 'None')}</div>
                <div class="result-meta">${jobs || 'No target jobs available.'}</div>
            `;
        }

        guidedResultsGrid.appendChild(card);
    });
};

const fetchJobMatch = async (token, jobId) => {
    try {
        return await requestJson(`${apiBase}/users/job-match/${jobId}`, {
            headers: { Authorization: `Bearer ${token}` },
        });
    } catch (error) {
        return null;
    }
};

const renderResults = async (items) => {
    resultsGrid.innerHTML = '';

    if (!items.length) {
        resultsMeta.textContent = 'No matches yet. Try another skill or course.';
        resultsTitle.textContent = 'No results';
        if (resultsFilters) resultsFilters.hidden = true;
        return;
    }

    resultsMeta.textContent = `${items.length} openings found.`;
    resultsTitle.textContent = 'Openings you can act on';

    const auth = getAuth();
    const token = auth?.access_token;
    const matchByJobId = new Map();

    if (token) {
        const matchRequests = items.map(async (item) => {
            const jobId = item.id || item.job_id;
            if (!jobId) return;

            const matchData = await fetchJobMatch(token, jobId);
            if (matchData && typeof matchData.match_percentage === 'number') {
                matchByJobId.set(jobId, matchData);
            }
        });
        await Promise.all([
            syncUserActionState(token),
            Promise.all(matchRequests),
        ]);
    }

    items.forEach((item) => {
        const card = document.createElement('article');
        card.className = 'result-card';
        const jobId = item.id || item.job_id;
        const matchData = jobId ? matchByJobId.get(jobId) : null;
        const org = escapeHtml(item.organization || item.org || 'Unknown organization');
        const location = escapeHtml(
            item.location || item.location_raw || 'Location unspecified'
        );
        const salaryText = item.salary_range
            ? `${item.salary_estimated ? 'Estimated: ' : ''}${item.salary_range}`
            : 'Salary not provided';
        const applyLink = escapeHtml(safeUrl(item.apply_url || item.url));
        const hasApplyLink = Boolean(item.apply_url || item.url);
        const matchLabel = matchData
            ? `${matchData.match_percentage}% match`
            : '';
        const missingSkills = Array.isArray(matchData?.missing_skills)
            ? matchData.missing_skills.slice(0, 2).join(', ')
            : '';
        const missingLabel = missingSkills
            ? ` · Missing: ${missingSkills}`
            : '';

        const skillTags = (item.top_skills || [])
            .slice(0, 3)
            .map((s) => `<span class="skill-chip">${escapeHtml(s)}</span>`)
            .join(' ');
        const qualityTag = item.quality_tag
            ? `<span class="quality-tag ${item.high_confidence ? 'high' : 'medium'}">${escapeHtml(item.quality_tag)}</span>`
            : '';
        const dataQualityIssues = Array.isArray(item.data_quality_issues) ? item.data_quality_issues : [];
        const qualityNotes = [];
        if (item.source_quality_tier && item.source_quality_tier !== 'high') {
            qualityNotes.push(`Source: ${item.source_quality_tier}`);
        }
        if (item.location_confidence && item.location_confidence !== 'high') {
            qualityNotes.push(`Location: ${item.location_confidence} confidence`);
        }
        if (dataQualityIssues.includes('duplicate_candidate')) {
            qualityNotes.push('Possible duplicate');
        }
        if (dataQualityIssues.includes('listing_page')) {
            qualityNotes.push('Listing-style title');
        }
        const contractLabel = item.contract_type
            ? escapeHtml(item.contract_type)
            : '';
        const postedLabel = item.posted_at
            ? escapeHtml(new Date(item.posted_at).toLocaleDateString())
            : '';
        const roleFamilyLabel = item.role_family
            ? escapeHtml(item.role_family)
            : '';
        const metaExtra = [contractLabel, roleFamilyLabel, postedLabel].filter(Boolean).join(' · ');
        const canPersist = Boolean(token && Number.isInteger(jobId) && jobId > 0);
        const isSaved = canPersist && savedJobIds.has(jobId);
        const isTracked = canPersist && trackedJobIds.has(jobId);
        const actionsHtml = [
            hasApplyLink
                ? `<a class="solid-btn btn-sm" href="${applyLink}" target="_blank" rel="noopener">Apply</a>`
                : '',
            canPersist
                ? `<button type="button" class="ghost-btn btn-sm js-save-job ${isSaved ? 'btn-saved' : ''}" ${isSaved ? 'disabled' : ''}>${isSaved ? 'Saved' : 'Save'}</button>`
                : '',
            canPersist
                ? `<button type="button" class="ghost-btn btn-sm js-track-job ${isTracked ? 'btn-saved' : ''}" ${isTracked ? 'disabled' : ''}>${isTracked ? 'Tracked' : 'Track'}</button>`
                : '',
        ].filter(Boolean).join('');

        card.innerHTML = `
            <div class="result-card-header">
                <h3 class="result-title">${escapeHtml(item.title || 'Untitled role')}</h3>
                ${qualityTag}
            </div>
            <div class="result-meta">${org} · ${location}</div>
            ${metaExtra ? `<div class="result-meta">${metaExtra}</div>` : ''}
            <div class="result-meta">${escapeHtml(salaryText)}</div>
            ${qualityNotes.length ? `<div class="result-meta">${escapeHtml(qualityNotes.join(' · '))}</div>` : ''}
            ${skillTags ? `<div class="result-skills">${skillTags}</div>` : ''}
            ${matchLabel
                ? `<div class="result-match">${escapeHtml(`${matchLabel}${missingLabel}`)}</div>`
                : ''}
            ${actionsHtml ? `<div class="result-actions">${actionsHtml}</div>` : ''}
            ${canPersist ? '<p class="result-action-status"></p>' : ''}
        `;

        if (canPersist) {
            const statusEl = card.querySelector('.result-action-status');
            const saveBtn = card.querySelector('.js-save-job');
            const trackBtn = card.querySelector('.js-track-job');

            saveBtn?.addEventListener('click', () => {
                saveJobFromResults({ token, jobId, button: saveBtn, statusEl }).catch((error) => {
                    setResultActionMessage(statusEl, error.message || 'Could not save this job.', true);
                });
            });
            trackBtn?.addEventListener('click', () => {
                trackApplicationFromResults({ token, jobId, button: trackBtn, statusEl }).catch((error) => {
                    setResultActionMessage(statusEl, error.message || 'Could not track this application.', true);
                });
            });
        }

        resultsGrid.appendChild(card);
    });
};

const renderAggregates = (payload) => {
    if (!payload || !resultsFilters) return;

    const roleFamilies = Array.isArray(payload.role_families) ? payload.role_families : [];
    const seniorityBuckets = Array.isArray(payload.seniority_buckets) ? payload.seniority_buckets : [];
    const counties = Array.isArray(payload.counties_hiring) ? payload.counties_hiring : [];
    const sectors = Array.isArray(payload.sectors_hiring) ? payload.sectors_hiring : [];

    const hasFacets = roleFamilies.length || seniorityBuckets.length || counties.length || sectors.length;
    if (!hasFacets) {
        resultsFilters.hidden = true;
        return;
    }

    resultsFilters.hidden = false;

    const makeChip = ({ label, pressed, onClick }) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'chip';
        btn.setAttribute('aria-pressed', pressed ? 'true' : 'false');
        btn.textContent = label;
        btn.addEventListener('click', onClick);
        return btn;
    };

    const renderFacet = (el, items, labelKey, selected, onSelect, onClear) => {
        if (!el) return;
        el.innerHTML = '';
        if (!items.length) { el.closest('.filter-block')?.classList.add('empty'); return; }
        el.closest('.filter-block')?.classList.remove('empty');
        el.appendChild(makeChip({ label: 'All', pressed: !selected, onClick: onClear }));
        items.slice(0, 20).forEach((row) => {
            const value = row[labelKey];
            el.appendChild(makeChip({
                label: `${value} (${row.count_ads})`,
                pressed: selected === value,
                onClick: () => onSelect(value),
            }));
        });
    };

    renderFacet(roleFamilyClustersEl, roleFamilies, 'role_family', selectedRoleFamily,
        (v) => { selectedRoleFamily = v; fetchResults(); },
        () => { selectedRoleFamily = null; fetchResults(); }
    );
    renderFacet(seniorityClustersEl, seniorityBuckets, 'seniority', selectedSeniority,
        (v) => { selectedSeniority = v; fetchResults(); },
        () => { selectedSeniority = null; fetchResults(); }
    );
    renderFacet(countyClustersEl, counties, 'county', selectedCounty,
        (v) => { selectedCounty = v; fetchResults(); },
        () => { selectedCounty = null; fetchResults(); }
    );
    renderFacet(sectorClustersEl, sectors, 'sector', selectedSector,
        (v) => { selectedSector = v; fetchResults(); },
        () => { selectedSector = null; fetchResults(); }
    );

    if (qualityClustersEl) {
        qualityClustersEl.innerHTML = '';
        qualityClustersEl.appendChild(makeChip({
            label: 'All quality',
            pressed: !highConfidenceOnly,
            onClick: () => { highConfidenceOnly = false; fetchResults(); },
        }));
        qualityClustersEl.appendChild(makeChip({
            label: 'High confidence only',
            pressed: highConfidenceOnly,
            onClick: () => { highConfidenceOnly = true; fetchResults(); },
        }));
    }
};

const fetchResults = async () => {
    const query = searchInput.value.trim();
    if (!query) return;

    resultsMeta.textContent = 'Searching...';
    resultsTitle.textContent = 'Finding matches';
    updateSearchAlertButtonVisibility();

    const params = new URLSearchParams({
        q: query,
    });
    if (locationFilter.value) params.append('location', locationFilter.value);
    if (seniorityFilter.value) params.append('seniority', seniorityFilter.value);
    if (selectedTitleCluster) params.append('title', selectedTitleCluster);
    if (selectedCompany) params.append('company', selectedCompany);
    if (selectedRoleFamily) params.append('role_family', selectedRoleFamily);
    if (selectedCounty) params.append('county', selectedCounty);
    if (selectedSector) params.append('sector', selectedSector);
    if (highConfidenceOnly) params.append('high_confidence_only', 'true');
    if (currentGuidedMode !== 'jobs') {
        params.append('mode', currentGuidedMode);
        if (currentUserProfile?.skills && !params.get('skills')) {
            const profileSkills = Object.keys(currentUserProfile.skills);
            if (profileSkills.length) params.append('skills', profileSkills.join(','));
        }
        if (currentUserProfile?.education) {
            params.append('education', currentUserProfile.education);
        }
        if (currentUserProfile?.current_role) {
            params.append('current_role', currentUserProfile.current_role);
        }
    }

    try {
        const response = await fetch(`${apiBase}/search?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`Server responded ${response.status}`);
        }

        const payload = await response.json();
        const rawItems = Array.isArray(payload?.results) ? payload.results : [];
        renderGuidedResults(payload, currentGuidedMode);
        renderAggregates(payload);
        await renderResults(rawItems);
        updateSearchAlertButtonVisibility();
        document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        resultsMeta.textContent = 'We could not reach the API. Is the backend running?';
        resultsTitle.textContent = 'Search unavailable';
        resultsGrid.innerHTML = '';
        renderGuidedResults({ guided_results: null, mode_error: null }, 'jobs');
        if (resultsFilters) resultsFilters.hidden = true;
        updateSearchAlertButtonVisibility();
        console.error(error);
    }
};

form.addEventListener('submit', (event) => {
    event.preventDefault();
    fetchResults();
});

focusSearchBtn.addEventListener('click', () => {
    searchInput.focus();
});

// High-confidence toggle
const highConfidenceToggle = document.getElementById('highConfidenceToggle');
if (highConfidenceToggle) {
    highConfidenceToggle.addEventListener('change', () => {
        highConfidenceOnly = highConfidenceToggle.checked;
        if (searchInput.value.trim()) {
            fetchResults();
        }
    });
}

// Load trending chips
const loadTrendingChips = async () => {
    try {
        const response = await fetch(`${apiBase}/trending`);
        if (!response.ok) return;
        const data = await response.json();

        const trendingChipsContainer = document.getElementById('trendingChips');
        if (!trendingChipsContainer) return;

        trendingChipsContainer.innerHTML = '';

        // Add top 3 roles
        if (data.top_roles && data.top_roles.length > 0) {
            data.top_roles.slice(0, 3).forEach(role => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'chip';
                btn.dataset.query = role.name;
                btn.textContent = `${role.name} (${role.count})`;
                trendingChipsContainer.appendChild(btn);
            });
        }

        // Add remote jobs if count > 0
        if (data.remote_jobs && data.remote_jobs > 0) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'chip';
            btn.dataset.query = 'Remote jobs';
            btn.textContent = `Remote (${data.remote_jobs})`;
            trendingChipsContainer.appendChild(btn);
        }

        // Add top 3 skills
        if (data.top_skills && data.top_skills.length > 0) {
            data.top_skills.slice(0, 3).forEach(skill => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'chip';
                btn.dataset.query = skill.name;
                btn.textContent = skill.name;
                trendingChipsContainer.appendChild(btn);
            });
        }

        // Re-attach click handlers to new chips
        const newChips = trendingChipsContainer.querySelectorAll('.chip');
        newChips.forEach((chip) => {
            chip.addEventListener('click', () => {
                searchInput.value = chip.dataset.query || '';
                fetchResults();
            });
        });
    } catch (error) {
        console.error('Failed to load trending data:', error);
    }
};

// Load trending chips on page load
loadTrendingChips();

const chips = document.querySelectorAll('.chips .chip');
chips.forEach((chip) => {
    chip.addEventListener('click', () => {
        searchInput.value = chip.dataset.query || '';
        fetchResults();
    });
});

guidedModeButtons.forEach((button) => {
    button.addEventListener('click', () => {
        setGuidedMode(button.dataset.guidedMode || 'jobs');
    });
});

saveSearchAlertBtn?.addEventListener('click', () => {
    const auth = getAuth();
    if (!auth?.access_token) {
        openAuthModal('signin');
        setAuthError(signinError, 'Sign in to save job alerts.');
        return;
    }

    populateJobAlertDraft();
    setAccountTab('alerts');
    setJobAlertStatus('');
    accountSection.hidden = false;
    accountSection.scrollIntoView({ behavior: 'smooth' });
});

authOpenButtons.forEach((button) => {
    button.addEventListener('click', () => openAuthModal(button.dataset.authOpen));
});

authCloseButtons.forEach((button) => {
    button.addEventListener('click', closeAuthModal);
});

authTabs.forEach((tab) => {
    tab.addEventListener('click', () => setAuthView(tab.dataset.authTab));
});

signinForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setAuthError(signinError, '');
    const email = document.getElementById('signinEmail').value.trim();
    const password = document.getElementById('signinPassword').value;

    const body = new URLSearchParams();
    body.set('username', email);
    body.set('password', password);

    try {
        const data = await requestJson(`${apiBase}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body,
        });
        saveAuth(data);
        setAuthState(data.user);
        await loadAccountData(data.access_token);
        closeAuthModal();
        redirectAfterAuth(data.user);
    } catch (error) {
        setAuthError(signinError, error.message);
    }
});

signupForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setAuthError(signupError, '');
    const payload = {
        full_name: document.getElementById('signupName').value.trim(),
        email: document.getElementById('signupEmail').value.trim(),
        password: document.getElementById('signupPassword').value,
    };
    const location = document.getElementById('signupLocation').value;
    const skills = parseSkills(document.getElementById('signupSkills').value);

    try {
        const data = await requestJson(`${apiBase}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        saveAuth(data);
        await ensureProfileData(data.access_token, location, skills);
        setAuthState(data.user);
        await loadAccountData(data.access_token);
        closeAuthModal();
        redirectAfterAuth(data.user);
    } catch (error) {
        setAuthError(signupError, error.message);
    }
});

resetRequestForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setResetMessage('');
    const email = document.getElementById('resetEmail').value.trim();
    try {
        const data = await requestJson(`${apiBase}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });
        setResetMessage(data.reset_token
            ? `Reset token (dev): ${data.reset_token}`
            : 'Check your email for a reset link.');
    } catch (error) {
        setResetMessage(error.message, true);
    }
});

resetConfirmForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setResetMessage('');
    const token = document.getElementById('resetToken').value.trim();
    const newPassword = document.getElementById('resetNewPassword').value;
    try {
        await requestJson(`${apiBase}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, new_password: newPassword }),
        });
        setResetMessage('Password updated. You can sign in now.');
        setAuthView('signin');
    } catch (error) {
        setResetMessage(error.message, true);
    }
});

googleButtons.forEach((button) => {
    button.addEventListener('click', async () => {
        const view = button.closest('.auth-view');
        const context = view && view.id === 'authSignup'
            ? {
                location: document.getElementById('signupLocation').value,
                skills: parseSkills(document.getElementById('signupSkills').value),
            }
            : null;
        try {
            await startGoogleAuth(context);
        } catch (error) {
            const targetError = view && view.id === 'authSignup' ? signupError : signinError;
            setAuthError(targetError, error.message);
        }
    });
});

logoutBtn.addEventListener('click', () => {
    resetAuthState();
    userDropdown.classList.remove('active');
});

const bootstrapAuth = async () => {
    const existingAuth = getAuth();
    if (!existingAuth || !existingAuth.access_token) {
        setAuthState(null);
        return;
    }

    try {
        const me = await requestJson(`${apiBase}/auth/me`, {
            headers: { Authorization: `Bearer ${existingAuth.access_token}` },
        });
        saveAuth({ ...existingAuth, user: me });
        setAuthState(me);
        await loadAccountData(existingAuth.access_token);
    } catch (error) {
        if (error.status === 401 || error.status === 403) {
            resetAuthState();
            return;
        }
        if (existingAuth.user) {
            setAuthState(existingAuth.user);
        } else {
            setAuthState(null);
        }
    }
};

bootstrapAuth();

userMenuBtn.addEventListener('click', () => {
    userDropdown.classList.toggle('active');
});

document.addEventListener('click', (event) => {
    if (!userDropdown.contains(event.target) && !userMenuBtn.contains(event.target)) {
        userDropdown.classList.remove('active');
    }
});

accountTabs.forEach((button) => {
    button.addEventListener('click', () => {
        setAccountTab(button.dataset.accountTab);
        accountSection.scrollIntoView({ behavior: 'smooth' });
        userDropdown.classList.remove('active');
    });
});

dropdownTabs.forEach((button) => {
    button.addEventListener('click', () => {
        setAccountTab(button.dataset.accountTab);
        accountSection.scrollIntoView({ behavior: 'smooth' });
        userDropdown.classList.remove('active');
    });
});

jobAlertForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const auth = getAuth();
    if (!auth?.access_token) {
        openAuthModal('signin');
        setAuthError(signinError, 'Sign in to create job alerts.');
        return;
    }

    const query = jobAlertQuery?.value.trim() || searchInput.value.trim();
    const name = jobAlertName?.value.trim() || buildAlertNameFromSearch();
    if (!query) {
        setJobAlertStatus('Enter a search query before creating an alert.', true);
        return;
    }

    setJobAlertStatus('');
    const submitBtn = jobAlertForm.querySelector('button[type="submit"]');
    const originalLabel = submitBtn?.textContent || 'Create alert';
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';
    }

    try {
        await requestJson(`${apiBase}/users/job-alerts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${auth.access_token}`,
            },
            body: JSON.stringify({
                name,
                query,
                filters: currentSearchFilters(),
                frequency: jobAlertFrequency?.value || 'daily',
                delivery_methods: ['email'],
            }),
        });
        setJobAlertStatus('Job alert created.');
        await loadJobAlerts(auth.access_token);
    } catch (error) {
        setJobAlertStatus(error.message || 'Could not create alert.', true);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalLabel;
        }
    }
});

jobAlertsList?.addEventListener('click', async (event) => {
    const button = event.target.closest('.js-delete-alert');
    if (!button) return;

    const auth = getAuth();
    if (!auth?.access_token) {
        openAuthModal('signin');
        setAuthError(signinError, 'Sign in to manage job alerts.');
        return;
    }

    const alertId = Number(button.dataset.alertId);
    if (!alertId) return;

    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = 'Deleting...';
    setJobAlertStatus('');

    try {
        await requestJson(`${apiBase}/users/job-alerts/${alertId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${auth.access_token}` },
        });
        setJobAlertStatus('Job alert deleted.');
        await loadJobAlerts(auth.access_token);
    } catch (error) {
        button.disabled = false;
        button.textContent = originalLabel;
        setJobAlertStatus(error.message || 'Could not delete alert.', true);
    }
});
