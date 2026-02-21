const dashboardApp = document.getElementById('dashboardApp');
const dashboardGate = document.getElementById('dashboardGate');
const dashboardGreeting = document.getElementById('dashboardGreeting');
const dashboardPlan = document.getElementById('dashboardPlan');
const dashboardUserChip = document.getElementById('dashboardUserChip');

// Dashboard tab navigation
const dashboardTabs = document.querySelectorAll('.dashboard-tab');
const dashboardTabContents = document.querySelectorAll('.dashboard-tab-content');

const profileCompleteness = document.getElementById('profileCompleteness');
const profileLocationHint = document.getElementById('profileLocationHint');

const recommendationsList = document.getElementById('recommendationsList');
const savedJobsList = document.getElementById('savedJobsList');
const applicationsList = document.getElementById('applicationsList');
const notificationsList = document.getElementById('notificationsList');
const marketPulseList = document.getElementById('marketPulseList');
const roleEvolutionList = document.getElementById('roleEvolutionList');

const adviceForm = document.getElementById('adviceForm');
const adviceQuery = document.getElementById('adviceQuery');
const adviceResponse = document.getElementById('adviceResponse');
const upgradeBtn = document.getElementById('upgradeBtn');
const dashboardGateMessage = document.getElementById('dashboardGateMessage');
const dashboardSignOut = document.getElementById('dashboardSignOut');

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

const { escapeHtml, safeUrl } = window.NEXTSTEP_SANITIZE || {
    escapeHtml: (value) => String(value ?? ''),
    safeUrl: (value) => (value ? String(value) : '#'),
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

const setPaidVisibility = (isPaid) => {
    document.querySelectorAll('[data-paid-only]').forEach((el) => {
        el.hidden = !isPaid;
    });
    document.querySelectorAll('[data-free-only]').forEach((el) => {
        el.hidden = isPaid;
    });
};

const requestJson = async (url, options = {}) => {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        const error = new Error(payload.detail || `Request failed (${response.status})`);
        error.status = response.status;
        throw error;
    }
    return payload;
};

const showGate = (message) => {
    dashboardGate.hidden = false;
    if (dashboardGateMessage) {
        dashboardGateMessage.textContent = message || '';
    }
};

function editProfile() {
    switchDashboardTab('profile');
    const form = document.getElementById('profileEditPanel');
    if (form) {
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function setupAlerts() {
    // Switch to Profile tab and scroll to notifications panel
    switchDashboardTab('profile');
    const notifPanel = document.getElementById('notificationsList');
    if (notifPanel) {
        notifPanel.closest('article')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function viewActivity() {
    const section = document.getElementById('activityFeedList');
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }
    window.location.href = 'dashboard.html';
}

window.editProfile = editProfile;
window.setupAlerts = setupAlerts;
window.viewActivity = viewActivity;

const renderList = (target, items, emptyMessage) => {
    if (!items.length) {
        target.innerHTML = `<p class="panel-note">${escapeHtml(emptyMessage)}</p>`;
        return;
    }
    target.innerHTML = items
        .map(
            (item) => {
                const title = escapeHtml(item.title);
                const subtitle = escapeHtml(item.subtitle);
                const href = item.link ? escapeHtml(safeUrl(item.link)) : '';
                return `
                <div class="data-row">
                    <div>
                        <strong>${title}</strong>
                        <span>${subtitle}</span>
                    </div>
                    ${item.link ? `<a class="result-link" href="${href}" target="_blank" rel="noopener">Open</a>` : ''}
                </div>
            `;
            }
        )
        .join('');
};

const loadBetaProgress = async (token, email) => {
    const betaPanel = document.getElementById('betaProgressPanel');
    if (!betaPanel) return;

    try {
        const usersResponse = await requestJson(`${apiBase}/beta/users?limit=50`);
        const betaUser = (usersResponse.users || []).find(u => u.email === email);

        if (!betaUser) {
            betaPanel.style.display = 'none';
            return;
        }

        betaPanel.style.display = 'block';

        const signupDate = new Date(betaUser.signed_up_at);
        const endDate = new Date(signupDate);
        endDate.setDate(endDate.getDate() + 30);
        const today = new Date();
        const daysRemaining = Math.max(0, Math.ceil((endDate - today) / (1000 * 60 * 60 * 24)));

        let engagementScore = 0;
        if (betaUser.profile_completed) engagementScore += 25;
        if (betaUser.jobs_viewed > 0) engagementScore += 20;
        if (betaUser.jobs_saved > 0) engagementScore += 25;
        if (betaUser.jobs_applied > 0) engagementScore += 30;

        document.getElementById('betaDaysRemaining').textContent = daysRemaining;
        document.getElementById('betaEngagementScore').textContent = `${engagementScore}%`;
        document.getElementById('betaProfileStatus').textContent = betaUser.profile_completed ? '✅ Complete' : '⏳ Pending';
        document.getElementById('betaJobsViewed').textContent = betaUser.jobs_viewed || 0;
        document.getElementById('betaApplications').textContent = betaUser.jobs_applied || 0;

    } catch (error) {
        console.log('Not a beta user:', error);
        betaPanel.style.display = 'none';
    }
};

const renderProfileChecklist = (profile) => {
    const checklistContainer = document.getElementById('profileChecklistList');
    if (!checklistContainer) return;

    const checklist = [
        { label: 'Basic Info', completed: profile?.full_name && profile?.email },
        { label: 'Phone Number', completed: profile?.phone },
        { label: 'Location', completed: profile?.preferred_locations?.length > 0 },
        { label: 'Skills', completed: profile?.skills?.length > 0 },
        { label: 'Education', completed: profile?.education?.length > 0 },
        { label: 'Work Experience', completed: profile?.experience?.length > 0 },
    ];

    const completedCount = checklist.filter(item => item.completed).length;
    const totalCount = checklist.length;
    const percentage = Math.round((completedCount / totalCount) * 100);

    const pctEl = document.getElementById('profileCompletionPctPlan');
    if (pctEl) pctEl.textContent = `${percentage}% complete`;

    const html = checklist.map(item => `
        <div class="data-row" style="cursor: pointer;" onclick="editProfile()">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 20px;">${item.completed ? '✅' : '⭕'}</div>
                <div>
                    <strong>${escapeHtml(item.label)}</strong>
                    <span style="font-size: 12px; color: #718096;">${item.completed ? 'Completed' : 'Click to add'}</span>
                </div>
            </div>
        </div>
    `).join('');

    checklistContainer.innerHTML = html;
};

const loadActivityFeed = async (token) => {
    const activityContainer = document.getElementById('activityFeedList');
    if (!activityContainer) return;

    try {
        const data = await requestJson(`${apiBase}/users/activity?limit=10`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        const activities = data.activities || [];

        if (activities.length === 0) {
            activityContainer.innerHTML = '<p class="panel-placeholder">No recent activity. Start searching for jobs!</p>';
            return;
        }

        const html = activities.map(item => {
            const timeAgo = item.time ? _relativeTime(item.time) : '';
            return `
                <div class="data-row">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="font-size: 20px;">${item.icon || '📌'}</div>
                        <div>
                            <strong>${escapeHtml(item.text)}</strong>
                            <span style="font-size: 12px; color: #718096;">${escapeHtml(timeAgo)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        activityContainer.innerHTML = html;
    } catch {
        activityContainer.innerHTML = '<p class="panel-placeholder">Could not load activity.</p>';
    }
};

const _relativeTime = (isoString) => {
    const diff = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
};

const renderMomentumChart = async (token) => {
    const chartContainer = document.getElementById('momentumChart');
    if (!chartContainer) return;

    let data = [0, 0, 0, 0, 0, 0, 0];
    try {
        const resp = await requestJson(`${apiBase}/users/momentum`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        data = (resp.days || []).map(d => d.count);
    } catch { /* fall through to zero bars */ }

    const maxValue = Math.max(...data, 1);

    const bars = data.map((value) => {
        const height = (value / maxValue) * 100;
        const color = height > 70 ? '#48bb78' : height > 40 ? '#ed8936' : '#cbd5e0';

        return `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end;">
                <div style="
                    width: 100%;
                    height: ${height}%;
                    background: ${color};
                    border-radius: 4px 4px 0 0;
                    transition: all 0.3s;
                    min-height: 8px;
                " title="${value} activities"></div>
            </div>
        `;
    }).join('');

    chartContainer.innerHTML = bars;
};

// Dashboard Tab Switching
const switchDashboardTab = (tabName) => {
    // Update tab buttons
    dashboardTabs.forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    // Update tab content
    dashboardTabContents.forEach(content => {
        if (content.dataset.tabContent === tabName) {
            content.hidden = false;
        } else {
            content.hidden = true;
        }
    });

    // Save current tab to localStorage
    localStorage.setItem('dashboard_active_tab', tabName);
};

// Initialize tab listeners
dashboardTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        switchDashboardTab(tab.dataset.tab);
    });
});

// Restore last active tab on page load
const restoreActiveTab = () => {
    const lastTab = localStorage.getItem('dashboard_active_tab') || 'smart-feed';
    switchDashboardTab(lastTab);
};

// Render enhanced job recommendations with badges
const renderEnhancedRecommendations = (container, recommendations) => {
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = '<p class="panel-placeholder">No recommendations yet. Complete your profile to get personalized matches.</p>';
        return;
    }

    container.innerHTML = recommendations.map((rec) => {
        const title = escapeHtml(rec.title || 'Job opportunity');
        const company = escapeHtml(rec.company || 'Company');
        const matchScore = Math.round((rec.match_score || 0) * 100);
        const qualityScore = Math.round((rec.quality_score || 0) * 100);
        const badges = rec.badges || [];
        const url = safeUrl(rec.url);

        const badgeHtml = badges.map(badge => {
            let badgeClass = 'badge-default';
            if (badge === 'High match') badgeClass = 'badge-success';
            else if (badge === 'Good match') badgeClass = 'badge-info';
            else if (badge === 'Verified employer') badgeClass = 'badge-verified';
            else if (badge === 'Closing soon') badgeClass = 'badge-warning';
            else if (badge === 'New') badgeClass = 'badge-new';
            else if (badge === 'Remote') badgeClass = 'badge-remote';
            else if (badge === 'Skill stretch') badgeClass = 'badge-stretch';

            return `<span class="job-badge ${badgeClass}">${escapeHtml(badge)}</span>`;
        }).join('');

        return `
            <div class="job-card">
                <div class="job-card-header">
                    <div>
                        <strong class="job-title">${title}</strong>
                        <span class="job-company">${company}</span>
                    </div>
                    <div class="job-scores">
                        <span class="score-chip" title="Match score">🎯 ${matchScore}%</span>
                        <span class="score-chip" title="Quality score">⭐ ${qualityScore}%</span>
                    </div>
                </div>
                ${badges.length > 0 ? `<div class="job-badges">${badgeHtml}</div>` : ''}
                <div class="job-card-actions">
                    <a href="${url}" target="_blank" rel="noopener" class="solid-btn btn-sm">View job</a>
                    <button class="ghost-btn btn-sm" onclick="saveJob(${rec.job_id}, this)">Save</button>
                </div>
            </div>
        `;
    }).join('');
};

// Save a job via API and show inline feedback
window.saveJob = async (jobId, btn) => {
    const auth = getAuth();
    if (!auth) {
        window.location.href = 'index.html';
        return;
    }
    const originalText = btn ? btn.textContent : null;
    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
    try {
        await requestJson(`${apiBase}/users/saved-jobs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${auth.access_token}`,
            },
            body: JSON.stringify({ job_id: jobId }),
        });
        if (btn) { btn.textContent = 'Saved ✓'; btn.classList.add('btn-saved'); }
    } catch (error) {
        if (btn) { btn.disabled = false; btn.textContent = originalText || 'Save'; }
        if (error.message && error.message.toLowerCase().includes('already saved')) {
            if (btn) { btn.textContent = 'Already saved'; btn.classList.add('btn-saved'); btn.disabled = true; }
        } else {
            if (btn) { btn.textContent = 'Error – retry'; }
        }
    }
};

// Load and refresh Smart Feed recommendations
window.refreshRecommendations = async () => {
    const auth = getAuth();
    if (!auth) return;

    try {
        const data = await requestJson(`${apiBase}/users/recommendations?limit=20`, {
            headers: { Authorization: `Bearer ${auth.access_token}` },
        });

        const recommendationsList = document.getElementById('recommendationsList');
        if (data.recommendations && data.recommendations.length > 0) {
            renderEnhancedRecommendations(recommendationsList, data.recommendations);

            // Update counts in Smart Feed tab
            const recCountFeed = document.getElementById('recCountFeed');
            if (recCountFeed) recCountFeed.textContent = data.recommendations.length;
        }
    } catch (error) {
        console.error('Failed to load recommendations:', error);
    }
};

// Load and render Market Fit data
const loadMarketFit = async (token) => {
    try {
        const data = await requestJson(`${apiBase}/users/market-fit`, {
            headers: { Authorization: `Bearer ${token}` },
        });

        // Update match distribution
        document.getElementById('strongMatchCount').textContent = data.match_distribution.strong || 0;
        document.getElementById('closeMatchCount').textContent = data.match_distribution.close || 0;
        document.getElementById('pivotMatchCount').textContent = data.match_distribution.pivot || 0;

        // Render missing skills
        const missingSkillsList = document.getElementById('missingSkillsList');
        if (data.missing_skills && data.missing_skills.length > 0) {
            renderList(
                missingSkillsList,
                data.missing_skills.map((skill) => ({
                    title: skill.name,
                    subtitle: `${skill.demand_count} jobs mention this (${skill.percentage}% of market)`,
                    link: `index.html?q=${encodeURIComponent(skill.name)}`,
                })),
                'No missing skills identified. You\'re well-prepared!'
            );
        } else {
            missingSkillsList.innerHTML = '<p class="panel-placeholder">Complete your profile to see skill recommendations</p>';
        }

        // Render top counties
        const topCountiesList = document.getElementById('topCountiesList');
        if (data.top_counties && data.top_counties.length > 0) {
            renderList(
                topCountiesList,
                data.top_counties.map((county) => ({
                    title: county.name,
                    subtitle: `${county.count} jobs`,
                    link: `index.html?q=&county=${encodeURIComponent(county.name)}`,
                })),
                'No location data available'
            );
        } else {
            topCountiesList.innerHTML = '<p class="panel-placeholder">No location data available</p>';
        }

        // Render top industries
        const topIndustriesList = document.getElementById('topIndustriesList');
        if (data.top_industries && data.top_industries.length > 0) {
            renderList(
                topIndustriesList,
                data.top_industries.map((industry) => ({
                    title: industry.name,
                    subtitle: `${industry.count} jobs`,
                    link: `index.html?q=&sector=${encodeURIComponent(industry.name)}`,
                })),
                'No industry data available'
            );
        } else {
            topIndustriesList.innerHTML = '<p class="panel-placeholder">No industry data available</p>';
        }

        // Update target roles selector (placeholder for now)
        const targetRolesSelector = document.getElementById('targetRolesSelector');
        if (data.target_roles && data.target_roles.length > 0) {
            targetRolesSelector.innerHTML = `
                <p><strong>Current role:</strong> ${escapeHtml(data.target_roles[0])}</p>
                <p class="panel-note">${data.total_jobs_analyzed || 0} jobs analyzed in the last 60 days</p>
            `;
        } else {
            targetRolesSelector.innerHTML = '<p class="panel-placeholder">Set your target role in your profile</p>';
        }
    } catch (error) {
        console.error('Failed to load market fit data:', error);
    }
};

const initProfileEditForm = (profile, me, token) => {
    const form = document.getElementById('profileEditForm');
    if (!form) return;

    // Pre-fill from existing data
    const nameEl = document.getElementById('profileFullName');
    const roleEl = document.getElementById('profileCurrentRole');
    const expEl = document.getElementById('profileExperience');
    const eduEl = document.getElementById('profileEducation');
    const skillsEl = document.getElementById('profileSkillsInput');
    const locationEl = document.getElementById('profileLocation');
    const goalsEl = document.getElementById('profileCareerGoals');
    const linkedinEl = document.getElementById('profileLinkedin');
    const statusEl = document.getElementById('profileSaveStatus');

    if (nameEl) nameEl.value = me?.full_name || '';
    if (profile) {
        if (roleEl) roleEl.value = profile.current_role || '';
        if (expEl) expEl.value = profile.experience_level || '';
        if (eduEl) eduEl.value = profile.education || '';
        if (skillsEl) {
            const skills = Object.keys(profile.skills || {});
            skillsEl.value = skills.join(', ');
        }
        if (locationEl) locationEl.value = (profile.preferred_locations || [])[0] || '';
        if (goalsEl) goalsEl.value = profile.career_goals || '';
        if (linkedinEl) linkedinEl.value = profile.linkedin_url || '';
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('profileSaveBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
        if (statusEl) { statusEl.textContent = ''; statusEl.className = 'panel-note'; }

        const skillsRaw = skillsEl ? skillsEl.value : '';
        const skillsMap = skillsRaw
            ? Object.fromEntries(skillsRaw.split(',').map(s => s.trim()).filter(Boolean).map(s => [s, 0.7]))
            : undefined;

        const location = locationEl ? locationEl.value.trim() : '';

        const payload = {};
        if (roleEl && roleEl.value.trim()) payload.current_role = roleEl.value.trim();
        if (expEl && expEl.value) payload.experience_level = expEl.value;
        if (eduEl && eduEl.value.trim()) payload.education = eduEl.value.trim();
        if (skillsMap && Object.keys(skillsMap).length) payload.skills = skillsMap;
        if (location) payload.preferred_locations = [location];
        if (goalsEl && goalsEl.value.trim()) payload.career_goals = goalsEl.value.trim();
        if (linkedinEl && linkedinEl.value.trim()) payload.linkedin_url = linkedinEl.value.trim();

        try {
            const result = await requestJson(`${apiBase}/auth/profile`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(payload),
            });
            if (profileCompleteness) {
                profileCompleteness.textContent = `${Math.round(result.profile_completeness || 0)}%`;
            }
            if (profileLocationHint && location) {
                profileLocationHint.textContent = `Location: ${location}`;
            }
            if (statusEl) { statusEl.textContent = 'Saved'; statusEl.className = 'panel-note text-success'; }
        } catch (err) {
            if (statusEl) { statusEl.textContent = err.message || 'Save failed'; statusEl.className = 'panel-note auth-error'; }
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'Save profile'; }
        }
    });
};

const boot = async () => {
    const auth = getAuth();
    if (!auth || !auth.access_token) {
        if (window.location.hostname === '::') {
            showGate('You are on [::]. Use http://127.0.0.1:5173 so your login persists.');
        } else {
            showGate('No saved session found. Sign in again to load your dashboard.');
        }
        return;
    }

    try {
        const me = await requestJson(`${apiBase}/auth/me`, {
            headers: { Authorization: `Bearer ${auth.access_token}` },
        });

        const displayName = me.full_name || me.email || 'Account';
        dashboardGreeting.textContent = `Welcome back, ${me.full_name || 'there'}.`;
        dashboardPlan.textContent = `Plan: ${me.subscription_tier || 'basic'}`;
        dashboardUserChip.textContent = `Signed in as ${displayName}`;
        dashboardUserChip.title = displayName;

        const isPaid = me.subscription_tier && me.subscription_tier !== 'basic';
        setPaidVisibility(isPaid);

        const [profile, recommendations, savedJobs, applications, notifications] = await Promise.all([
            requestJson(`${apiBase}/auth/profile`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch(() => null),
            requestJson(`${apiBase}/users/recommendations?limit=5`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch(() => ({ recommendations: [] })),
            requestJson(`${apiBase}/users/saved-jobs?limit=5`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch(() => ({ saved_jobs: [] })),
            requestJson(`${apiBase}/users/applications?limit=5`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch(() => ({ applications: [] })),
            requestJson(`${apiBase}/users/notifications?limit=5`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch(() => ({ notifications: [] })),
        ]);

        if (profile) {
            profileCompleteness.textContent = `${Math.round(profile.profile_completeness || 0)}%`;
            const location = (profile.preferred_locations || [])[0];
            profileLocationHint.textContent = `Location: ${location || 'Not set'}`;
        } else {
            profileCompleteness.textContent = '0%';
            profileLocationHint.textContent = 'Location: Not set';
        }

        const recs = recommendations.recommendations || [];
        const saved = savedJobs.saved_jobs || [];
        const apps = applications.applications || [];
        const notes = notifications.notifications || [];

        // Update Smart Feed tab counts
        const recCountFeed = document.getElementById('recCountFeed');
        const savedCountFeed = document.getElementById('savedCountFeed');
        const applicationCountApp = document.getElementById('applicationCountApp');

        if (recCountFeed) recCountFeed.textContent = recs.length;
        if (savedCountFeed) savedCountFeed.textContent = saved.length;
        if (applicationCountApp) applicationCountApp.textContent = apps.length;

        renderList(
            recommendationsList,
            recs.map((item) => ({
                title: item.title || 'Role match',
                subtitle: `${item.company || 'Organization'} · score ${(item.match_score || 0).toFixed(2)}`,
                link: item.url,
            })),
            'No recommendations yet.'
        );
        renderList(
            savedJobsList,
            saved.map((item) => ({
                title: item.title || 'Saved role',
                subtitle: `${item.organization || 'Organization'} · ${item.location || 'Location'}`,
                link: item.url,
            })),
            'No saved roles yet.'
        );
        renderList(
            applicationsList,
            apps.map((item) => ({
                title: `Application ${item.job_id || ''}`.trim(),
                subtitle: `Status: ${item.status || 'applied'}`,
                link: null,
            })),
            'No applications tracked yet.'
        );
        renderList(
            notificationsList,
            notes.map((item) => ({
                title: item.title || 'Update',
                subtitle: item.message || '',
                link: null,
            })),
            'No notifications yet.'
        );

        if (marketPulseList || roleEvolutionList) {
            const [skillTrends, roleEvolution] = await Promise.all([
                requestJson(`${apiBase}/analytics/skill-trends?months=3&limit=5`).catch(() => ({ items: [] })),
                requestJson(`${apiBase}/analytics/role-evolution?months=3&limit=5`).catch(() => ({ items: [] })),
            ]);

            if (marketPulseList) {
                renderList(
                    marketPulseList,
                    (skillTrends.items || []).map((item) => ({
                        title: item.skill,
                        subtitle: `${item.role_family || 'all roles'} · ${item.count} mentions`,
                        link: null,
                    })),
                    'No market trends yet.'
                );
            }

            if (roleEvolutionList) {
                renderList(
                    roleEvolutionList,
                    (roleEvolution.items || []).map((item) => {
                        const skills = item.top_skills ? Object.keys(item.top_skills).slice(0, 3) : [];
                        return {
                            title: item.role_family || 'role family',
                            subtitle: skills.length ? `Top skills: ${skills.join(', ')}` : 'No skills captured',
                            link: null,
                        };
                    }),
                    'No role evolution data yet.'
                );
            }
        }

        if (adviceForm && isPaid) {
            adviceForm.addEventListener('submit', async (event) => {
                event.preventDefault();
                adviceResponse.textContent = '';
                adviceResponse.classList.remove('auth-error');
                try {
                    const data = await requestJson(`${apiBase}/users/career-advice`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${auth.access_token}`,
                        },
                        body: JSON.stringify({ query: adviceQuery.value.trim() }),
                    });
                    adviceResponse.textContent = data.advice || 'Advice generated.';
                } catch (error) {
                    adviceResponse.textContent = error.message;
                    adviceResponse.classList.add('auth-error');
                }
            });
        }

        if (upgradeBtn) {
            upgradeBtn.addEventListener('click', () => {
                window.location.href = 'index.html#results';
            });
        }

        if (dashboardSignOut) {
            dashboardSignOut.addEventListener('click', () => {
                clearAuth();
                window.location.href = 'index.html';
            });
        }

        await loadBetaProgress(auth.access_token, me.email);

        renderProfileChecklist(profile);
        initProfileEditForm(profile, me, auth.access_token);

        await loadActivityFeed(auth.access_token);

        await renderMomentumChart(auth.access_token);

        // Load market fit data
        await loadMarketFit(auth.access_token);

        // Load enhanced recommendations
        await refreshRecommendations();

        // Load applications Kanban
        await loadApplicationsKanban(auth.access_token);

        // Initialize Kanban drag-drop
        initKanbanDragDrop();

        // Restore last active tab
        restoreActiveTab();

        dashboardApp.hidden = false;
    } catch (error) {
        if (error.status === 401 || error.status === 403) {
            showGate('Session expired. Sign in again to continue.');
        } else {
            showGate('Backend not reachable. Make sure the API is running.');
        }
    }
};

boot();

// ========== Applications Kanban Board ==========

let applicationsData = null;

// Load and render applications Kanban
const loadApplicationsKanban = async (token) => {
    try {
        const data = await requestJson(`${apiBase}/users/applications/by-stage`, {
            headers: { Authorization: `Bearer ${token}` },
        });

        applicationsData = data;

        // Update analytics
        const applicationCountApp = document.getElementById('applicationCountApp');
        const interviewRate = document.getElementById('interviewRate');

        if (applicationCountApp) {
            applicationCountApp.textContent = data.analytics.total_applications || 0;
        }

        if (interviewRate) {
            interviewRate.textContent = `${data.analytics.interview_rate || 0}%`;
            // TODO: Add market average comparison when data available
        }

        // Render each stage
        const stages = ['saved', 'applied', 'interview', 'offer', 'rejected'];
        stages.forEach(stage => {
            renderKanbanStage(stage, data.stages[stage] || []);
        });

    } catch (error) {
        console.error('Failed to load applications:', error);
    }
};

// Render Kanban stage with cards
const renderKanbanStage = (stage, applications) => {
    const stageContainer = document.getElementById(`${stage}Stage`);
    const countBadge = document.getElementById(`${stage}StageCount`);

    if (!stageContainer) return;

    // Update count badge
    if (countBadge) countBadge.textContent = applications.length;

    // Clear existing cards
    stageContainer.innerHTML = '';

    if (applications.length === 0) {
        stageContainer.innerHTML = '<p class="kanban-empty">No applications</p>';
        return;
    }

    // Render cards
    applications.forEach(app => {
        const card = createKanbanCard(app);
        stageContainer.appendChild(card);
    });
};

// Create Kanban card element
const createKanbanCard = (app) => {
    const card = document.createElement('div');
    card.className = 'kanban-card';
    card.draggable = true;
    card.dataset.appId = app.id;
    card.dataset.stage = app.stage;

    // Deadline indicator
    let deadlineHtml = '';
    if (app.deadline) {
        const deadline = new Date(app.deadline);
        const today = new Date();
        const daysUntil = Math.ceil((deadline - today) / (1000 * 60 * 60 * 24));

        if (daysUntil < 0) {
            deadlineHtml = '<span class="deadline-indicator overdue">Overdue</span>';
        } else if (daysUntil <= 3) {
            deadlineHtml = `<span class="deadline-indicator urgent">Due in ${daysUntil}d</span>`;
        } else {
            deadlineHtml = `<span class="deadline-indicator">Due in ${daysUntil}d</span>`;
        }
    }

    card.innerHTML = `
        <div class="kanban-card-header">
            <strong class="kanban-card-title">${escapeHtml(app.job_title)}</strong>
            ${deadlineHtml}
        </div>
        <p class="kanban-card-company">${escapeHtml(app.company)}</p>
        <p class="kanban-card-meta">${app.days_since_applied} days ago</p>
        ${app.notes ? `<p class="kanban-card-notes">${escapeHtml(app.notes)}</p>` : ''}
    `;

    // Drag events
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);

    // Click to view job
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.kanban-card-actions')) {
            window.open(app.job_url, '_blank');
        }
    });

    return card;
};

// Drag and Drop handlers
let draggedElement = null;

const handleDragStart = (e) => {
    draggedElement = e.currentTarget;
    e.currentTarget.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.currentTarget.innerHTML);
};

const handleDragEnd = (e) => {
    e.currentTarget.classList.remove('dragging');
};

const handleDragOver = (e) => {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
};

const handleDrop = async (e) => {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    e.preventDefault();

    if (!draggedElement) return;

    const dropZone = e.currentTarget;
    const newStage = dropZone.dataset.stage;
    const appId = draggedElement.dataset.appId;
    const oldStage = draggedElement.dataset.stage;

    if (newStage === oldStage) return;

    // Update stage via API
    const auth = getAuth();
    if (!auth) return;

    try {
        await requestJson(`${apiBase}/users/applications/${appId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${auth.access_token}`,
            },
            body: JSON.stringify({ stage: newStage }),
        });

        // Reload Kanban
        await loadApplicationsKanban(auth.access_token);

    } catch (error) {
        console.error('Failed to update application stage:', error);
        alert('Failed to update application stage. Please try again.');
    }

    return false;
};

// Initialize drag-drop zones
const initKanbanDragDrop = () => {
    const dropZones = document.querySelectorAll('.kanban-cards');
    dropZones.forEach(zone => {
        zone.addEventListener('dragover', handleDragOver);
        zone.addEventListener('drop', handleDrop);
    });
};

