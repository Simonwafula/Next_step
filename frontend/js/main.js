const form = document.getElementById('searchForm');
const searchInput = document.getElementById('searchInput');
const locationFilter = document.getElementById('locationFilter');
const seniorityFilter = document.getElementById('seniorityFilter');
const guidedModeWrap = document.getElementById('guidedModeWrap');
const guidedModeButtons = document.querySelectorAll('[data-guided-mode]');
const resultsGrid = document.getElementById('resultsGrid');
const resultsMeta = document.getElementById('resultsMeta');
const resultsTitle = document.getElementById('resultsTitle');
const guidedResults = document.getElementById('guidedResults');
const guidedResultsGrid = document.getElementById('guidedResultsGrid');
const guidedModeError = document.getElementById('guidedModeError');
const resultsFilters = document.getElementById('resultsFilters');
const titleClustersEl = document.getElementById('titleClusters');
const companyClustersEl = document.getElementById('companyClusters');
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
};
const profileName = document.getElementById('profileName');
const profileEmail = document.getElementById('profileEmail');
const profileLocation = document.getElementById('profileLocation');
const profileSkills = document.getElementById('profileSkills');
const savedJobsList = document.getElementById('savedJobsList');
const savedJobsEmpty = document.getElementById('savedJobsEmpty');

const { escapeHtml, safeUrl } = window.NEXTSTEP_SANITIZE || {
    escapeHtml: (value) => String(value ?? ''),
    safeUrl: (value) => (value ? String(value) : '#'),
};

const apiBase = (() => {
    const fromAttr = document.body.dataset.apiBase;
    if (fromAttr) return fromAttr;
    if (window.location.origin && window.location.origin !== 'null') {
        return `${window.location.origin}/api`;
    }
    return 'http://localhost:8000/api';
})();

const authStorageKey = 'nextstep_auth';
const pendingProfileKey = 'nextstep_pending_profile';

let selectedTitleCluster = null;
let selectedCompany = null;
let currentGuidedMode = 'jobs';
let currentUserProfile = null;

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
            if (currentGuidedMode === 'jobs') {
                setGuidedMode('explore', { refresh: false });
            }
        }
    } else {
        authActions.hidden = false;
        userActions.hidden = true;
        userGreeting.textContent = '';
        accountSection.hidden = true;
        if (dashboardNav) dashboardNav.hidden = true;
        if (dashboardMenuLink) dashboardMenuLink.hidden = true;
        if (adminMenuLink) adminMenuLink.hidden = true;
        currentUserProfile = null;
        if (guidedModeWrap) {
            guidedModeWrap.hidden = true;
            setGuidedMode('jobs', { refresh: false });
        }
        renderGuidedResults({ guided_results: null, mode_error: null }, 'jobs');
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

    try {
        const saved = await requestJson(`${apiBase}/users/saved-jobs`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        renderSavedJobs(saved.saved_jobs || []);
    } catch (error) {
        renderSavedJobs([]);
    }
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
        await Promise.all(matchRequests);
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
        const matchLabel = matchData
            ? `${matchData.match_percentage}% match`
            : '';
        const missingSkills = Array.isArray(matchData?.missing_skills)
            ? matchData.missing_skills.slice(0, 2).join(', ')
            : '';
        const missingLabel = missingSkills
            ? ` · Missing: ${missingSkills}`
            : '';

        card.innerHTML = `
            <h3 class="result-title">${escapeHtml(item.title || 'Untitled role')}</h3>
            <div class="result-meta">${org} · ${location}</div>
            <div class="result-meta">${escapeHtml(salaryText)}</div>
            ${matchLabel
                ? `<div class="result-match">${escapeHtml(`${matchLabel}${missingLabel}`)}</div>`
                : ''}
            <a class="result-link" href="${applyLink}" target="_blank" rel="noopener">Apply</a>
        `;
        resultsGrid.appendChild(card);
    });
};

const renderAggregates = (payload) => {
    if (!payload || !resultsFilters || !titleClustersEl || !companyClustersEl) return;

    const titleClusters = Array.isArray(payload.title_clusters) ? payload.title_clusters : [];
    const companies = Array.isArray(payload.companies_hiring) ? payload.companies_hiring : [];

    if (!titleClusters.length && !companies.length) {
        resultsFilters.hidden = true;
        return;
    }

    resultsFilters.hidden = false;
    titleClustersEl.innerHTML = '';
    companyClustersEl.innerHTML = '';

    const makeChip = ({ label, pressed, onClick }) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'chip';
        btn.setAttribute('aria-pressed', pressed ? 'true' : 'false');
        btn.textContent = label;
        btn.addEventListener('click', onClick);
        return btn;
    };

    titleClustersEl.appendChild(
        makeChip({
            label: 'All',
            pressed: !selectedTitleCluster,
            onClick: () => {
                selectedTitleCluster = null;
                selectedCompany = null;
                fetchResults();
            },
        })
    );

    titleClusters.slice(0, 24).forEach((row) => {
        const t = row.title;
        const c = row.count_ads;
        titleClustersEl.appendChild(
            makeChip({
                label: `${t} (${c})`,
                pressed: selectedTitleCluster === t,
                onClick: () => {
                    selectedTitleCluster = t;
                    selectedCompany = null;
                    fetchResults();
                },
            })
        );
    });

    const companiesForTitle = selectedTitleCluster
        ? companies.filter((row) => row.title === selectedTitleCluster)
        : companies;

    companyClustersEl.appendChild(
        makeChip({
            label: 'All',
            pressed: !selectedCompany,
            onClick: () => {
                selectedCompany = null;
                fetchResults();
            },
        })
    );

    companiesForTitle.slice(0, 24).forEach((row) => {
        const co = row.company;
        const c = row.count_ads;
        companyClustersEl.appendChild(
            makeChip({
                label: `${co} (${c})`,
                pressed: selectedCompany === co,
                onClick: () => {
                    selectedCompany = co;
                    fetchResults();
                },
            })
        );
    });
};

const fetchResults = async () => {
    const query = searchInput.value.trim();
    if (!query) return;

    resultsMeta.textContent = 'Searching...';
    resultsTitle.textContent = 'Finding matches';

    const params = new URLSearchParams({
        q: query,
    });
    if (locationFilter.value) params.append('location', locationFilter.value);
    if (seniorityFilter.value) params.append('seniority', seniorityFilter.value);
    if (selectedTitleCluster) params.append('title', selectedTitleCluster);
    if (selectedCompany) params.append('company', selectedCompany);
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
        const rawItems = Array.isArray(payload) ? payload : payload.results || payload.jobs || [];
        renderGuidedResults(payload, currentGuidedMode);
        renderAggregates(Array.isArray(payload) ? null : payload);
        await renderResults(rawItems);
        document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        resultsMeta.textContent = 'We could not reach the API. Is the backend running?';
        resultsTitle.textContent = 'Search unavailable';
        resultsGrid.innerHTML = '';
        renderGuidedResults({ guided_results: null, mode_error: null }, 'jobs');
        if (resultsFilters) resultsFilters.hidden = true;
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
