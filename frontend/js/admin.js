const adminStatus = document.getElementById('adminStatus');
const adminApp = document.getElementById('adminApp');
const adminGate = document.getElementById('adminGate');
const adminUserChip = document.getElementById('adminUserChip');
const kpiGrid = document.getElementById('kpiGrid');
const pipelineStats = document.getElementById('pipelineStats');
const adminUsers = document.getElementById('adminUsers');
const adminJobs = document.getElementById('adminJobs');
const adminSources = document.getElementById('adminSources');
const adminActivity = document.getElementById('adminActivity');
const salaryCoverage = document.getElementById('salaryCoverage');
const salaryCoverageBar = document.getElementById('salaryCoverageBar');
const skillsCoverage = document.getElementById('skillsCoverage');
const skillsCoverageBar = document.getElementById('skillsCoverageBar');
const coverageUpdated = document.getElementById('coverageUpdated');
const adminGateMessage = document.getElementById('adminGateMessage');
const adminSignOut = document.getElementById('adminSignOut');
const adminActionProgress = document.getElementById('adminActionProgress');
const adminActionLabel = document.getElementById('adminActionLabel');
const adminSkillTrends = document.getElementById('adminSkillTrends');
const adminRoleEvolution = document.getElementById('adminRoleEvolution');
const adminSkillTrendsNote = document.getElementById('adminSkillTrendsNote');
const adminDriftSummary = document.getElementById('adminDriftSummary');
const summaryDimension = document.getElementById('summaryDimension');
const summaryTableBody = document.getElementById('summaryTableBody');
const summaryModal = document.getElementById('summaryModal');
const summaryModalTitle = document.getElementById('summaryModalTitle');
const summaryModalBody = document.getElementById('summaryModalBody');
const educationMappingForm = document.getElementById('educationMappingForm');
const educationMappingList = document.getElementById('educationMappingList');
const educationRaw = document.getElementById('educationRaw');
const educationNormalized = document.getElementById('educationNormalized');
const educationNotes = document.getElementById('educationNotes');

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

const setStatus = (message, isError = false) => {
    adminStatus.textContent = message || '';
    adminStatus.classList.toggle('auth-error', isError);
};

const setActionLoading = (isLoading, message) => {
    if (!adminActionProgress) {
        return;
    }
    adminActionProgress.hidden = !isLoading;
    if (adminActionLabel) {
        adminActionLabel.textContent = message || '';
    }
};

const setActionButtonsDisabled = (isDisabled) => {
    document.querySelectorAll('[data-admin-action]').forEach((button) => {
        button.disabled = isDisabled;
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
                    <span>${escapeHtml(item.label)}</span>
                    <strong>${escapeHtml(item.value)}</strong>
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
            (user) => {
                const name = escapeHtml(user.full_name || user.email);
                const email = escapeHtml(user.email);
                const tier = escapeHtml(user.subscription_tier);
                return `
                <div class="data-row">
                    <div>
                        <strong>${name}</strong>
                        <span>${email}</span>
                    </div>
                    <span class="badge">${tier}</span>
                </div>
            `;
            }
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
            (job) => {
                const title = escapeHtml(job.title);
                const org = escapeHtml(job.organization || 'Unknown');
                const location = escapeHtml(job.location || 'Unspecified');
                const href = escapeHtml(safeUrl(job.url));
                return `
                <div class="data-row">
                    <div>
                        <strong>${title}</strong>
                        <span>${org} · ${location}</span>
                    </div>
                    <a class="result-link" href="${href}" target="_blank" rel="noopener">Open</a>
                </div>
            `;
            }
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
            (source) => {
                const name = escapeHtml(source.name || source.org);
                const meta = escapeHtml(`${source.source_type} · ${source.status || 'active'}`);
                const href = source.url ? escapeHtml(safeUrl(source.url)) : '';
                return `
                <div class="data-row">
                    <div>
                        <strong>${name}</strong>
                        <span>${meta}</span>
                    </div>
                    ${source.url ? `<a class="result-link" href="${href}" target="_blank" rel="noopener">View</a>` : ''}
                </div>
            `;
            }
        )
        .join('');
};

const renderAnalyticsList = (target, items, emptyMessage) => {
    if (!target) {
        return;
    }
    if (!items.length) {
        target.innerHTML = `<p class="panel-note">${emptyMessage}</p>`;
        return;
    }
    target.innerHTML = items
        .map(
            (item) => `
                <div class="data-row">
                    <div>
                        <strong>${item.title}</strong>
                        <span>${item.subtitle}</span>
                    </div>
                    ${item.meta ? `<span class="badge">${item.meta}</span>` : ''}
                </div>
            `
        )
        .join('');
};

const renderSkillTrends = (payload) => {
    const items = (payload?.items || []).map((row) => ({
        title: row.skill,
        subtitle: `${row.role_family || 'all roles'} · ${row.count} mentions`,
        meta: row.month || '',
    }));
    renderAnalyticsList(adminSkillTrends, items, 'No skill trends yet.');
};

const renderRoleEvolution = (payload) => {
    const items = (payload?.items || []).map((row) => {
        const topSkills = row.top_skills ? Object.keys(row.top_skills).slice(0, 3) : [];
        return {
            title: row.role_family || 'role family',
            subtitle: topSkills.length ? `Top skills: ${topSkills.join(', ')}` : 'No skills captured',
            meta: row.month || '',
        };
    });
    renderAnalyticsList(adminRoleEvolution, items, 'No role evolution data yet.');
};

const renderDriftSummary = (payload) => {
    if (!adminDriftSummary) {
        return;
    }
    if (!payload || payload.status !== 'success') {
        adminDriftSummary.innerHTML = '<p class="panel-note">No drift data available.</p>';
        return;
    }
    adminDriftSummary.innerHTML = `
        <div class="metric-row">
            <span>Skill overlap</span>
            <strong>${Math.round((payload.skills.overlap_ratio || 0) * 100)}%</strong>
        </div>
        <div class="metric-row">
            <span>Title overlap</span>
            <strong>${Math.round((payload.titles.overlap_ratio || 0) * 100)}%</strong>
        </div>
        <div class="metric-row">
            <span>Salary delta</span>
            <strong>${payload.salary.delta_ratio === null ? 'n/a' : `${Math.round(payload.salary.delta_ratio * 100)}%`}</strong>
        </div>
    `;
};

const fetchAnalyticsSnapshot = async (token) => {
    const [skillPayload, evolutionPayload, driftPayload] = await Promise.all([
        requestJson(`${apiBase}/admin/analytics/skill-trends?months=3&limit=6`, {
            headers: { Authorization: `Bearer ${token}` },
        }).catch(() => ({ items: [] })),
        requestJson(`${apiBase}/admin/analytics/role-evolution?months=3&limit=6`, {
            headers: { Authorization: `Bearer ${token}` },
        }).catch(() => ({ items: [] })),
        requestJson(`${apiBase}/admin/monitoring/drift?recent_days=30&baseline_days=180`, {
            headers: { Authorization: `Bearer ${token}` },
        }).catch(() => null),
    ]);
    renderSkillTrends(skillPayload);
    renderRoleEvolution(evolutionPayload);
    renderDriftSummary(driftPayload);
};

const formatRunTimestamp = (value) => {
    if (!value) {
        return 'Not run yet';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
};

const summarizeOperation = (operation) => {
    if (!operation) {
        return 'No recent run';
    }
    const details = operation.details || {};
    if (operation.process_type === 'ingest_all' || operation.process_type === 'ingest_government') {
        const count = details.sources_ingested ?? 0;
        return `${count} sources`;
    }
    if (operation.process_type === 'test_scrapers') {
        const summary = details.summary || {};
        const total = summary.total_scrapers ?? 0;
        const ok = summary.successful_scrapers ?? 0;
        return `${ok}/${total} scrapers ok`;
    }
    if (operation.process_type === 'generate_insights' || operation.process_type === 'daily_insights') {
        return operation.status === 'error' ? 'Failed' : 'Completed';
    }
    if (operation.process_type === 'daily_workflow') {
        return operation.status === 'error' ? 'Failed' : 'Completed';
    }
    return operation.message || operation.status || 'Updated';
};

const renderAutomationActivity = (payload) => {
    if (!adminActivity) {
        return;
    }
    const latest = payload?.latest_by_type || {};
    const items = [
        { key: 'ingest_all', label: 'Ingest all sources' },
        { key: 'ingest_government', label: 'Government ingest' },
        { key: 'test_scrapers', label: 'Scraper tests' },
        { key: 'generate_insights', label: 'Insights generation' },
        { key: 'daily_workflow', label: 'Automated workflow' },
        { key: 'daily_insights', label: 'Daily insights job' },
    ];

    adminActivity.innerHTML = items
        .map((item) => {
            const entry = latest[item.key];
            const status = entry?.status || 'unknown';
            const summary = summarizeOperation(entry);
            const lastRun = formatRunTimestamp(entry?.processed_at);
            const summarySafe = escapeHtml(summary);
            const lastRunSafe = escapeHtml(lastRun);
            const statusSafe = escapeHtml(status);
            return `
                <div class="data-row">
                    <div>
                        <strong>${item.label}</strong>
                        <span>${summarySafe} · ${lastRunSafe}</span>
                    </div>
                    <span class="badge">${statusSafe}</span>
                </div>
            `;
        })
        .join('');
};

const refreshAutomationActivity = async (token) => {
    const payload = await requestJson(`${apiBase}/admin/operations?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    renderAutomationActivity(payload);
    return payload;
};

const pollAutomationStatus = (processType, token, limitMs = 90000) => {
    const start = Date.now();
    const interval = setInterval(async () => {
        try {
            const payload = await refreshAutomationActivity(token);
            const entry = payload?.latest_by_type?.[processType];
            if (entry && entry.status && entry.status !== 'started') {
                clearInterval(interval);
            }
        } catch (error) {
            clearInterval(interval);
        }
        if (Date.now() - start > limitMs) {
            clearInterval(interval);
        }
    }, 5000);
};

const renderSummaryTable = (items = []) => {
    if (!summaryTableBody) {
        return;
    }
    if (!items.length) {
        summaryTableBody.innerHTML = `
            <tr>
                <td colspan="4" class="panel-note">No data available.</td>
            </tr>
        `;
        return;
    }
    summaryTableBody.innerHTML = items
        .map(
            (item) => {
                const rawValue = item.specific_value ?? item.value;
                const rawValueSafe = escapeHtml(rawValue);
                const normalizedSafe = escapeHtml(
                    item.normalized_value ?? item.specific_value ?? item.value
                );
                const countSafe = escapeHtml(item.count);
                return `
                <tr>
                    <td class="summary-value">${rawValueSafe}</td>
                    <td>${normalizedSafe}</td>
                    <td>${countSafe}</td>
                    <td>
                        <button class="summary-action" type="button" data-summary-value="${rawValueSafe}">View</button>
                    </td>
                </tr>
            `;
            }
        )
        .join('');
};

const openSummaryModal = (title, jobs = []) => {
    if (!summaryModal || !summaryModalBody || !summaryModalTitle) {
        return;
    }
    summaryModalTitle.textContent = title;
    if (!jobs.length) {
        summaryModalBody.innerHTML = '<p class="panel-note">No jobs found.</p>';
    } else {
        summaryModalBody.innerHTML = jobs
            .map(
                (job) => {
                    const title = escapeHtml(job.title);
                    const org = escapeHtml(job.organization || 'Unknown');
                    const location = escapeHtml(job.location || 'Unspecified');
                    const href = escapeHtml(safeUrl(job.url));
                    return `
                    <div class="data-row">
                        <div>
                            <strong>${title}</strong>
                            <span>${org} · ${location}</span>
                        </div>
                        <a class="result-link" href="${href}" target="_blank" rel="noopener">Open</a>
                    </div>
                `;
                }
            )
            .join('');
    }
    summaryModal.classList.add('active');
};

const closeSummaryModal = () => {
    if (!summaryModal) {
        return;
    }
    summaryModal.classList.remove('active');
};

const fetchSummaries = async (dimension, token) => {
    if (!summaryTableBody) {
        return;
    }
    summaryTableBody.innerHTML = `
        <tr>
            <td colspan="4" class="panel-note">Loading...</td>
        </tr>
    `;
    const payload = await requestJson(`${apiBase}/admin/summaries?dimension=${dimension}&limit=12`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    renderSummaryTable(payload.items || []);
};

const wireSummaryActions = (token) => {
    if (summaryDimension) {
        summaryDimension.addEventListener('change', (event) => {
            fetchSummaries(event.target.value, token).catch(() => {
                renderSummaryTable([]);
            });
        });
    }

    if (summaryTableBody) {
        summaryTableBody.addEventListener('click', async (event) => {
            const button = event.target.closest('[data-summary-value]');
            if (!button) {
                return;
            }
            const value = button.dataset.summaryValue;
            const dimension = summaryDimension ? summaryDimension.value : 'title';
            const payload = await requestJson(
                `${apiBase}/admin/summaries/${dimension}/jobs?value=${encodeURIComponent(value)}&limit=20`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const titleMap = {
                title: 'Job title',
                skill: 'Skill',
                education: 'Education / degree',
            };
            openSummaryModal(`${titleMap[dimension]}: ${value}`, payload.jobs || []);
        });
    }

    if (summaryModal) {
        summaryModal.addEventListener('click', (event) => {
            if (event.target.matches('[data-modal-close]')) {
                closeSummaryModal();
            }
        });
    }
};

const renderEducationMappings = (mappings = []) => {
    if (!educationMappingList) {
        return;
    }
    if (!mappings.length) {
        educationMappingList.innerHTML = '<p class="panel-note">No mappings yet.</p>';
        return;
    }
    educationMappingList.innerHTML = mappings
        .map(
            (mapping) => {
                const rawSafe = escapeHtml(mapping.raw_value);
                const normalizedSafe = escapeHtml(mapping.normalized_value);
                const notesSafe = escapeHtml(mapping.notes || '');
                const notesFragment = mapping.notes ? ` · ${notesSafe}` : '';
                return `
                <div class="data-row">
                    <div>
                        <strong>${rawSafe}</strong>
                        <span>${normalizedSafe}${notesFragment}</span>
                    </div>
                    <button class="summary-action" type="button" data-edu-edit="${rawSafe}" data-edu-normalized="${normalizedSafe}" data-edu-notes="${notesSafe}">Edit</button>
                </div>
            `;
            }
        )
        .join('');
};

const fetchEducationMappings = async (token) => {
    const payload = await requestJson(`${apiBase}/admin/education-mappings?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    renderEducationMappings(payload.mappings || []);
    return payload;
};

const wireEducationMappingForm = (token) => {
    if (!educationMappingForm) {
        return;
    }
    educationMappingForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const rawValue = educationRaw ? educationRaw.value.trim() : '';
        const normalizedValue = educationNormalized ? educationNormalized.value.trim() : '';
        if (!rawValue || !normalizedValue) {
            setStatus('Education mapping needs both values.', true);
            return;
        }
        await requestJson(`${apiBase}/admin/education-mappings`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({
                raw_value: rawValue,
                normalized_value: normalizedValue,
                notes: educationNotes ? educationNotes.value.trim() : '',
            }),
        });
        if (educationRaw) educationRaw.value = '';
        if (educationNormalized) educationNormalized.value = '';
        if (educationNotes) educationNotes.value = '';
        await fetchEducationMappings(token);
    });

    if (educationMappingList) {
        educationMappingList.addEventListener('click', (event) => {
            const button = event.target.closest('[data-edu-edit]');
            if (!button) {
                return;
            }
            if (educationRaw) educationRaw.value = button.dataset.eduEdit || '';
            if (educationNormalized) educationNormalized.value = button.dataset.eduNormalized || '';
            if (educationNotes) educationNotes.value = button.dataset.eduNotes || '';
        });
    }
};
const wireActions = (token) => {
    document.querySelectorAll('[data-admin-action]').forEach((button) => {
        button.addEventListener('click', async () => {
            const action = button.dataset.adminAction;
            setStatus('');
            setActionButtonsDisabled(true);
            try {
                let response;
                if (action === 'ingest') {
                    setActionLoading(true, 'Queueing ingestion sources…');
                    response = await requestJson(`${apiBase}/admin/ingest`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    setStatus(`Ingest started. ${response.ingested || 0} sources queued.`);
                } else if (action === 'ingest-government') {
                    setActionLoading(true, 'Queueing government ingestion…');
                    response = await requestJson(`${apiBase}/admin/ingest/government`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    setStatus(`Gov ingest started. ${response.ingested || 0} sources queued.`);
                } else if (action === 'test-scrapers') {
                    setActionLoading(true, 'Running scraper diagnostics…');
                    response = await requestJson(`${apiBase}/workflow/test-scrapers`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    const summary = response.summary || {};
                    setStatus(
                        `Scraper test complete. ${summary.successful_scrapers || 0}/${summary.total_scrapers || 0} ok.`
                    );
                } else if (action === 'generate-insights') {
                    setActionLoading(true, 'Generating insights…');
                    await requestJson(`${apiBase}/workflow/generate-insights`, {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    setStatus('Insights generation started.');
                    pollAutomationStatus('generate_insights', token);
                }
                await refreshAutomationActivity(token);
            } catch (error) {
                setStatus(error.message, true);
            } finally {
                setActionLoading(false, '');
                setActionButtonsDisabled(false);
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

        const [overview, usersPayload, jobsPayload, sourcesPayload, operationsPayload] = await Promise.all([
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
            requestJson(`${apiBase}/admin/operations?limit=20`, {
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
        if (operationsPayload && !operationsPayload.error) {
            renderAutomationActivity(operationsPayload);
        }

        if (adminSkillTrends || adminRoleEvolution || adminDriftSummary) {
            await fetchAnalyticsSnapshot(auth.access_token);
        }

        if (summaryDimension) {
            await fetchSummaries(summaryDimension.value, auth.access_token);
            wireSummaryActions(auth.access_token);
        }
        if (educationMappingForm) {
            await fetchEducationMappings(auth.access_token);
            wireEducationMappingForm(auth.access_token);
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
