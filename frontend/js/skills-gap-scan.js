const authStorageKey = 'nextstep_auth';
const apiBase = document.body.dataset.apiBase || '/api';

const form = document.getElementById('skillsGapForm');
const targetRoleInput = document.getElementById('targetRole');
const scanMessage = document.getElementById('scanMessage');
const scanResults = document.getElementById('scanResults');

const scanTargetRole = document.getElementById('scanTargetRole');
const scanMatchPercentage = document.getElementById('scanMatchPercentage');
const scanExpectedPay = document.getElementById('scanExpectedPay');
const scanMissingSkills = document.getElementById('scanMissingSkills');
const scanMatchingSkills = document.getElementById('scanMatchingSkills');
const scanProjects = document.getElementById('scanProjects');
const scanActionPlan = document.getElementById('scanActionPlan');

const { escapeHtml } = window.NEXTSTEP_SANITIZE || {
    escapeHtml: (value) => String(value ?? ''),
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

const renderSkillChips = (container, skills) => {
    container.innerHTML = '';
    if (!Array.isArray(skills) || !skills.length) {
        container.innerHTML = '<span>None</span>';
        return;
    }

    skills.forEach((skill) => {
        const chip = document.createElement('span');
        chip.textContent = skill;
        container.appendChild(chip);
    });
};

const renderRows = (container, rows) => {
    container.innerHTML = '';
    if (!rows.length) {
        container.innerHTML = '<p class="panel-note">No items yet.</p>';
        return;
    }

    container.innerHTML = rows
        .map((row) => `<div class="data-row"><strong>${escapeHtml(row)}</strong></div>`)
        .join('');
};

const renderActionPlan = (plan) => {
    const rows = [
        `30 days: ${plan?.['30_days'] || 'Not available'}`,
        `60 days: ${plan?.['60_days'] || 'Not available'}`,
        `90 days: ${plan?.['90_days'] || 'Not available'}`,
    ];
    renderRows(scanActionPlan, rows);
};

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    scanMessage.textContent = '';

    const auth = getAuth();
    if (!auth?.access_token) {
        scanMessage.textContent = 'Please sign in first to run your skills gap scan.';
        scanMessage.classList.add('auth-error');
        return;
    }

    try {
        const result = await requestJson(`${apiBase}/users/skills-gap-scan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${auth.access_token}`,
            },
            body: JSON.stringify({ target_role: targetRoleInput.value.trim() }),
        });

        scanTargetRole.textContent = result.target_role || '--';
        scanMatchPercentage.textContent = `${result.match_percentage || 0}%`;
        scanExpectedPay.textContent = result.expected_pay_range || '--';

        renderSkillChips(scanMissingSkills, result.missing_skills || []);
        renderSkillChips(scanMatchingSkills, result.matching_skills || []);
        renderRows(scanProjects, result.recommended_projects || []);
        renderActionPlan(result.action_plan_30_60_90 || {});

        scanResults.hidden = false;
        scanMessage.textContent = 'Scan complete.';
        scanMessage.classList.remove('auth-error');
    } catch (error) {
        scanResults.hidden = true;
        scanMessage.classList.add('auth-error');
        scanMessage.textContent = error.message;
    }
});
