const adminStatus = document.getElementById('adminStatus');
const adminApp = document.getElementById('adminApp');
const adminGate = document.getElementById('adminGate');
const adminUserChip = document.getElementById('adminUserChip');
const kpiGrid = document.getElementById('kpiGrid');
const pipelineStats = document.getElementById('pipelineStats');
const adminUsers = document.getElementById('adminUsers');
const adminJobs = document.getElementById('adminJobs');
const adminSources = document.getElementById('adminSources');
const salaryCoverage = document.getElementById('salaryCoverage');
const salaryCoverageBar = document.getElementById('salaryCoverageBar');
const skillsCoverage = document.getElementById('skillsCoverage');
const skillsCoverageBar = document.getElementById('skillsCoverageBar');
const coverageUpdated = document.getElementById('coverageUpdated');
const adminGateMessage = document.getElementById('adminGateMessage');
const adminSignOut = document.getElementById('adminSignOut');

const apiBase = document.body.dataset.apiBase || 'http://localhost:8000/api';
const authStorageKey = 'nextstep_auth';

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

const setStatus = (message, isError = false) => {
    adminStatus.textContent = message || '';
    adminStatus.classList.toggle('auth-error', isError);
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
    adminGate.hidden = false;
    adminApp.hidden = true;
    if (adminGateMessage) {
        adminGateMessage.textContent = message || '';
    }
};

const showAdminApp = () => {
    adminGate.hidden = true;
    adminApp.hidden = false;
    if (adminGateMessage) {
        adminGateMessage.textContent = '';
    }
};

const renderKpis = (overview) => {
    const { kpis, sources } = overview;
    const kpiValues = {
        users_total: kpis.users_total,
        users_active_7d: kpis.users_active_7d,
        jobs_total: kpis.jobs_total,
        sources_total: sources.total,
    };
    const kpiNotes = {
        users_new_7d: kpis.users_new_7d,
        jobs_new_7d: kpis.jobs_new_7d,
        sources_active: sources.active,
    };

    kpiGrid.querySelectorAll('[data-kpi]').forEach((card) => {
        const key = card.dataset.kpi;
        const valueEl = card.querySelector('.kpi-value');
        if (valueEl && key in kpiValues) {
            valueEl.textContent = kpiValues[key];
        }
    });

    kpiGrid.querySelectorAll('[data-kpi-note]').forEach((el) => {
        const key = el.dataset.kpiNote;
        if (key in kpiNotes) {
            el.textContent = kpiNotes[key];
        }
    });
};

const renderCoverage = (overview) => {
    const salaryPct = overview.coverage.salary.percentage || 0;
    const skillsPct = overview.coverage.skills.percentage || 0;
    salaryCoverage.textContent = `${salaryPct}%`;
    skillsCoverage.textContent = `${skillsPct}%`;
    salaryCoverageBar.style.width = `${salaryPct}%`;
    skillsCoverageBar.style.width = `${skillsPct}%`;
    coverageUpdated.textContent = overview.recent.latest_job_seen
        ? `Last job: ${new Date(overview.recent.latest_job_seen).toLocaleDateString()}`
        : 'No jobs yet';
};

const renderPipelineStats = (overview) => {
    const stats = [
        { label: 'Organizations', value: overview.kpis.organizations_total },
        { label: 'Locations', value: overview.kpis.locations_total },
        { label: 'Saved jobs', value: overview.kpis.saved_jobs_total },
        { label: 'Applications', value: overview.kpis.applications_total },
        { label: 'Searches', value: overview.kpis.searches_total },
        { label: 'Alerts', value: overview.kpis.alerts_total },
        { label: 'Notifications', value: overview.kpis.notifications_total },
    ];
    pipelineStats.innerHTML = stats
        .map(
            (item) => `
                <div class="metric-row">
                    <span>${item.label}</span>
                    <strong>${item.value}</strong>
                </div>
            `
        )
        .join('');
};

const renderUserList = (users) => {
    if (!users.length) {
        adminUsers.innerHTML = '<p class="panel-note">No users yet.</p>';
        return;
    }
    adminUsers.innerHTML = users
        .map(
            (user) => `
                <div class="data-row">
                    <div>
                        <strong>${user.full_name || user.email}</strong>
                        <span>${user.email}</span>
                    </div>
                    <span class="badge">${user.subscription_tier}</span>
                </div>
            `
        )
        .join('');
};

const renderJobList = (jobs) => {
    if (!jobs.length) {
        adminJobs.innerHTML = '<p class="panel-note">No jobs yet.</p>';
        return;
    }
    adminJobs.innerHTML = jobs
        .map(
            (job) => `
                <div class="data-row">
                    <div>
                        <strong>${job.title}</strong>
                        <span>${job.organization || 'Unknown'} · ${job.location || 'Unspecified'}</span>
                    </div>
                    <a class="result-link" href="${job.url}" target="_blank" rel="noopener">Open</a>
                </div>
            `
        )
        .join('');
};

const renderSourceList = (sources) => {
    if (!sources.length) {
        adminSources.innerHTML = '<p class="panel-note">No sources loaded.</p>';
        return;
    }
    adminSources.innerHTML = sources
        .slice(0, 10)
        .map(
            (source) => `
                <div class="data-row">
                    <div>
                        <strong>${source.name || source.org}</strong>
                        <span>${source.source_type} · ${source.status || 'active'}</span>
                    </div>
                    ${source.url ? `<a class="result-link" href="${source.url}" target="_blank" rel="noopener">View</a>` : ''}
                </div>
            `
        )
        .join('');
};

const wireActions = (token) => {
    document.querySelectorAll('[data-admin-action]').forEach((button) => {
        button.addEventListener('click', async () => {
            const action = button.dataset.adminAction;
            setStatus('');
            try {
                let response;
                if (action === 'ingest') {
                    response = await requestJson(`${apiBase}/admin/ingest`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    setStatus(`Ingest started. ${response.ingested || 0} sources queued.`);
                } else if (action === 'ingest-government') {
                    response = await requestJson(`${apiBase}/admin/ingest/government`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    setStatus(`Gov ingest started. ${response.ingested || 0} sources queued.`);
                } else if (action === 'test-scrapers') {
                    response = await requestJson(`${apiBase}/workflow/test-scrapers`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    const summary = response.summary || {};
                    setStatus(
                        `Scraper test complete. ${summary.successful_scrapers || 0}/${summary.total_scrapers || 0} ok.`
                    );
                } else if (action === 'generate-insights') {
                    await requestJson(`${apiBase}/workflow/generate-insights`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    setStatus('Insights generation started.');
                }
            } catch (error) {
                setStatus(error.message, true);
            }
        });
    });
};

const boot = async () => {
    const auth = getAuth();
    if (!auth || !auth.access_token) {
        if (window.location.hostname === '::') {
            showGate('You are on [::]. Use http://127.0.0.1:5173 so your admin session persists.');
        } else {
            showGate('No saved session found. Sign in with an admin account.');
        }
        return;
    }

    try {
        const me = await requestJson(`${apiBase}/auth/me`, {
            headers: { Authorization: `Bearer ${auth.access_token}` },
        });
        if (!me.is_admin) {
            showGate('Signed in, but this account is not an admin.');
            return;
        }

        const displayName = me.full_name || me.email || 'Admin';
        adminUserChip.textContent = `Signed in as ${displayName}`;
        adminUserChip.title = displayName;
        showAdminApp();
        wireActions(auth.access_token);

        const [overview, usersPayload, jobsPayload, sourcesPayload] = await Promise.all([
            requestJson(`${apiBase}/admin/overview`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch((error) => ({ error })),
            requestJson(`${apiBase}/admin/users?limit=8`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch((error) => ({ error })),
            requestJson(`${apiBase}/admin/jobs?limit=8`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch((error) => ({ error })),
            requestJson(`${apiBase}/admin/sources?source_type=government`, {
                headers: { Authorization: `Bearer ${auth.access_token}` },
            }).catch((error) => ({ error })),
        ]);

        if (overview && overview.error) {
            if (overview.error.status === 401 || overview.error.status === 403) {
                showGate('Session expired. Sign in again with an admin account.');
                return;
            }
            setStatus('Backend not reachable. Make sure the API is running.', true);
        } else if (overview) {
            renderKpis(overview);
            renderCoverage(overview);
            renderPipelineStats(overview);
        }

        if (usersPayload && !usersPayload.error) {
            renderUserList(usersPayload.users || []);
        }
        if (jobsPayload && !jobsPayload.error) {
            renderJobList(jobsPayload.jobs || []);
        }
        if (sourcesPayload && !sourcesPayload.error) {
            renderSourceList(sourcesPayload.sources || []);
        }

        if (adminSignOut) {
            adminSignOut.addEventListener('click', () => {
                clearAuth();
                window.location.href = 'index.html';
            });
        }
    } catch (error) {
        if (error.status === 401 || error.status === 403) {
            showGate('Session expired. Sign in again with an admin account.');
        } else {
            showGate('Backend not reachable. Make sure the API is running.');
        }
        setStatus(error.message, true);
    }
};

boot();
