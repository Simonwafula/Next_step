const dashboardApp = document.getElementById('dashboardApp');
const dashboardGate = document.getElementById('dashboardGate');
const dashboardGreeting = document.getElementById('dashboardGreeting');
const dashboardPlan = document.getElementById('dashboardPlan');
const dashboardUserChip = document.getElementById('dashboardUserChip');

const profileCompleteness = document.getElementById('profileCompleteness');
const profileLocationHint = document.getElementById('profileLocationHint');
const recCount = document.getElementById('recCount');
const savedCount = document.getElementById('savedCount');
const applicationCount = document.getElementById('applicationCount');

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

const apiBase = document.body.dataset.apiBase || 'http://localhost:8000/api';
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
    window.location.href = 'index.html#account';
}

function setupAlerts() {
    window.location.href = 'index.html#alerts';
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

    document.getElementById('profileCompletionPct').textContent = `${percentage}% complete`;

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

        recCount.textContent = recs.length;
        savedCount.textContent = saved.length;
        applicationCount.textContent = apps.length;

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

        await loadActivityFeed(auth.access_token);

        await renderMomentumChart(auth.access_token);

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
