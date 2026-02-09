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
