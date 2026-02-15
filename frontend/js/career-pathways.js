const apiBase = document.body.dataset.apiBase || '/api';

const form = document.getElementById('pathwayForm');
const roleSlug = document.getElementById('roleSlug');
const pathwayMessage = document.getElementById('pathwayMessage');
const pathwayResults = document.getElementById('pathwayResults');

const pathwayTitle = document.getElementById('pathwayTitle');
const pathwaySkills = document.getElementById('pathwaySkills');
const pathwayCerts = document.getElementById('pathwayCerts');
const pathwayLadder = document.getElementById('pathwayLadder');
const pathwayEmployers = document.getElementById('pathwayEmployers');
const pathwayResources = document.getElementById('pathwayResources');
const pathwayProjects = document.getElementById('pathwayProjects');

const { escapeHtml } = window.NEXTSTEP_SANITIZE || {
    escapeHtml: (value) => String(value ?? ''),
};

const getAuth = () => {
    const raw = localStorage.getItem('nextstep_auth');
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

const startUpgradeCheckout = async (authToken, planCode = 'professional_monthly', provider = 'stripe') => {
    const checkout = await requestJson(`${apiBase}/users/subscription/checkout`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ plan_code: planCode, provider }),
    });
    window.location.href = checkout.checkout_url;
};

const showUpgradePrompt = (authToken) => {
    pathwayMessage.classList.add('auth-error');
    pathwayMessage.innerHTML = 'Career pathways are a Professional feature. <button id="pathwayUpgradeBtn" type="button" class="solid-btn">Upgrade Now</button>';
    const button = document.getElementById('pathwayUpgradeBtn');
    if (!button) {
        return;
    }
    button.addEventListener('click', async () => {
        button.disabled = true;
        try {
            await startUpgradeCheckout(authToken);
        } catch (error) {
            pathwayMessage.textContent = error.message;
            pathwayMessage.classList.add('auth-error');
            button.disabled = false;
        }
    });
};

const renderChipList = (container, items) => {
    container.innerHTML = '';
    if (!items?.length) {
        container.innerHTML = '<span>Not available</span>';
        return;
    }

    items.forEach((item) => {
        const chip = document.createElement('span');
        chip.textContent = item;
        container.appendChild(chip);
    });
};

const renderRows = (container, items) => {
    container.innerHTML = '';
    if (!items?.length) {
        container.innerHTML = '<p class="panel-note">No data available.</p>';
        return;
    }

    container.innerHTML = items
        .map((item) => `<div class="data-row"><strong>${escapeHtml(item)}</strong></div>`)
        .join('');
};

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    pathwayMessage.textContent = '';
    const auth = getAuth();

    if (!auth?.access_token) {
        pathwayResults.hidden = true;
        pathwayMessage.classList.add('auth-error');
        pathwayMessage.textContent = 'Please sign in to access career pathways.';
        return;
    }

    try {
        const payload = await requestJson(`${apiBase}/career-pathways/${roleSlug.value}`, {
            headers: {
                Authorization: `Bearer ${auth.access_token}`,
            },
        });

        pathwayTitle.textContent = payload.title || '--';
        renderChipList(pathwaySkills, payload.required_skills || []);
        renderRows(pathwayCerts, payload.certifications || []);
        renderRows(
            pathwayLadder,
            (payload.experience_ladder || []).map(
                (row) => `${row.level}: ${row.salary_range}`
            )
        );
        renderRows(pathwayEmployers, payload.employers_hiring || []);
        renderRows(pathwayResources, payload.learning_resources || []);
        renderRows(pathwayProjects, payload.project_ideas || []);

        pathwayResults.hidden = false;
        pathwayMessage.classList.remove('auth-error');
        pathwayMessage.textContent = 'Roadmap loaded.';
    } catch (error) {
        pathwayResults.hidden = true;
        if (error.status === 403) {
            showUpgradePrompt(auth.access_token);
            return;
        }
        pathwayMessage.classList.add('auth-error');
        pathwayMessage.textContent = error.message;
    }
});
