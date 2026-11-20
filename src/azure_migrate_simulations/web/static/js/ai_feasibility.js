/* AI Feasibility Assessment — guided application/workflow decision flow. */
(() => {
    'use strict';

    const state = {
        loaded: false,
        loading: null,
        applications: [],
        categories: [],
        assessments: [],
        selectedApplicationId: '',
        selectedCategoryId: '',
        inputSource: {type: 'guided', name: 'Interactive assessment'},
        currentAssessment: null,
    };

    const byId = (id) => document.getElementById(id);
    const escapeHtml = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    const formatMoney = (value) => `$${Number(value || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}`;

    async function fetchJson(url, options) {
        const response = await fetch(url, options);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
        return payload;
    }

    function selectedApplication() {
        return state.applications.find((item) => item.id === state.selectedApplicationId) || null;
    }

    function selectedCategory() {
        return state.categories.find((item) => item.id === state.selectedCategoryId) || null;
    }

    function renderApplicationOptions() {
        const select = byId('ai-feasibility-application');
        if (!select) return;
        const priorValue = state.selectedApplicationId || select.value;
        select.innerHTML = '<option value="">Choose an application…</option>' + state.applications.map((app) => (
            `<option value="${escapeHtml(app.id)}">${escapeHtml(app.name)} · ${Number(app.member_count || 0)} members</option>`
        )).join('');
        if (state.applications.some((item) => item.id === priorValue)) {
            state.selectedApplicationId = priorValue;
            select.value = priorValue;
        }
        renderApplicationContext();
    }

    function renderApplicationContext() {
        const container = byId('ai-feasibility-application-context');
        if (!container) return;
        const app = selectedApplication();
        if (!app) {
            container.innerHTML = '<span class="text-muted small">Application members and assessed targets will appear here.</span>';
            return;
        }
        const summary = app.component_summary || {};
        const badges = [
            ['VMs', summary.virtual_machines || 0, 'primary'],
            ['Web apps', summary.web_apps || 0, 'success'],
            ['Databases', summary.databases || 0, 'danger'],
            ['Containers', summary.containers || 0, 'info'],
            ['Orchestrators', summary.orchestrators || 0, 'warning'],
            ['File shares', summary.file_shares || 0, 'secondary'],
        ].map(([label, count, color]) => `<span class="badge bg-${color} me-1 mb-1">${count} ${label}</span>`).join('');
        const targets = [...new Set((app.members || []).map((item) => item.target_service).filter(Boolean))].slice(0, 4);
        container.innerHTML = `<div class="d-flex justify-content-between gap-2 align-items-start">
            <div><strong>${escapeHtml(app.name)}</strong><div class="small text-muted">${escapeHtml(app.environment || 'Production')} · ${escapeHtml(app.criticality || 'Tier-2')} · Complexity ${Number(app.complexity_score || 0)}/10</div></div>
            <span class="badge bg-dark border">${Number(app.dependency_count || 0)} dependencies</span>
        </div><div class="mt-2">${badges}</div>
        <div class="small text-muted mt-2">Assessed targets: ${targets.length ? targets.map(escapeHtml).join(' · ') : 'No workload target available'}</div>`;
    }

    function renderCategories() {
        const container = byId('ai-feasibility-categories');
        if (!container) return;
        container.innerHTML = state.categories.map((category) => `<button type="button" class="ai-solution-card ${category.id === state.selectedCategoryId ? 'selected' : ''}" data-category-id="${escapeHtml(category.id)}" aria-pressed="${category.id === state.selectedCategoryId}">
            <span class="ai-solution-icon"><i class="bi ${escapeHtml(category.icon || 'bi-stars')}"></i></span>
            <span><span class="ai-solution-label">${escapeHtml(category.label)}</span><span class="ai-solution-copy d-block">${escapeHtml(category.description)}</span></span>
        </button>`).join('');
        container.querySelectorAll('[data-category-id]').forEach((button) => {
            button.addEventListener('click', () => {
                state.selectedCategoryId = button.dataset.categoryId || '';
                renderCategories();
                renderUsageFields();
            });
        });
    }

    function renderUsageFields() {
        const container = byId('ai-feasibility-usage');
        if (!container) return;
        const category = selectedCategory();
        if (!category) {
            container.innerHTML = '<div class="col-12 small text-muted">Select a solution idea to see its cost-driving assumptions.</div>';
            return;
        }
        container.innerHTML = (category.usage_fields || []).map((field) => `<div class="col-md-6">
            <label class="form-label small mb-1" for="ai-usage-${escapeHtml(field.id)}">${escapeHtml(field.label)}</label>
            <div class="input-group input-group-sm">
                <input type="number" min="${Number(field.minimum || 0)}" step="any" class="form-control ai-usage-input" id="ai-usage-${escapeHtml(field.id)}" data-usage-id="${escapeHtml(field.id)}" placeholder="Default ${Number(field.default).toLocaleString()}">
                <span class="input-group-text">${escapeHtml(field.unit)}</span>
            </div>
        </div>`).join('');
    }

    function renderSavedAssessments() {
        const container = byId('ai-feasibility-saved');
        if (!container) return;
        if (!state.assessments.length) {
            container.innerHTML = '';
            return;
        }
        container.innerHTML = `<div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div><strong><i class="bi bi-clock-history me-2 text-info"></i>Saved assessment revisions</strong><div class="small text-muted">Open a prior decision record or create a new revision.</div></div>
            <select class="form-select form-select-sm" id="ai-feasibility-saved-select" style="max-width:430px">
                <option value="">Select a saved assessment…</option>
                ${state.assessments.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.application?.name)} · ${escapeHtml(item.solution_category?.label)} · r${Number(item.version || 1)}</option>`).join('')}
            </select>
        </div>`;
        byId('ai-feasibility-saved-select')?.addEventListener('change', (event) => {
            const assessment = state.assessments.find((item) => item.id === event.target.value);
            if (assessment) {
                state.currentAssessment = assessment;
                renderAssessment(assessment);
            }
        });
    }

    async function loadWorkspace(force = false) {
        if (state.loaded && !force) return;
        if (state.loading && !force) return state.loading;
        const status = byId('ai-feasibility-generate-status');
        if (status) status.textContent = 'Loading applications and assessment patterns…';
        state.loading = Promise.all([
            fetchJson('/api/applications'),
            fetchJson('/api/ai-feasibility/categories'),
            fetchJson('/api/ai-feasibility/assessments'),
        ]).then(([applications, catalog, saved]) => {
            state.applications = applications.applications || [];
            state.categories = catalog.categories || [];
            state.assessments = saved.assessments || [];
            state.loaded = true;
            const version = byId('ai-pattern-version');
            if (version) version.textContent = `Catalog ${catalog.catalog_version || ''}`;
            renderApplicationOptions();
            renderCategories();
            renderUsageFields();
            renderSavedAssessments();
            if (status) status.textContent = 'Ready when application, solution idea, intent, outcome, and consent are complete.';
        }).catch((error) => {
            if (status) status.innerHTML = `<span class="text-danger">${escapeHtml(error.message)}</span>`;
            throw error;
        }).finally(() => {
            state.loading = null;
        });
        return state.loading;
    }

    function setWorkspaceSelections(applicationId = '', categoryId = '', intent = '') {
        if (applicationId && state.applications.some((item) => item.id === applicationId)) {
            state.selectedApplicationId = applicationId;
            const select = byId('ai-feasibility-application');
            if (select) select.value = applicationId;
        }
        if (categoryId && state.categories.some((item) => item.id === categoryId)) {
            state.selectedCategoryId = categoryId;
        }
        if (intent) {
            const input = byId('ai-feasibility-intent');
            if (input) input.value = String(intent).slice(0, 12000);
            updateIntentCount();
        }
        renderApplicationContext();
        renderCategories();
        renderUsageFields();
    }

    async function openWorkspace(applicationId = '', categoryId = '', intent = '') {
        if (window.bootstrap) {
            bootstrap.Tab.getOrCreateInstance(byId('tab-decide')).show();
            window.showDecideSub?.('decide-discovery');
            bootstrap.Tab.getOrCreateInstance(byId('subtab-assessment')).show();
        }
        const workspace = byId('ai-feasibility-workspace');
        if (workspace) workspace.style.display = '';
        await loadWorkspace();
        setWorkspaceSelections(applicationId, categoryId, intent);
        workspace?.scrollIntoView({behavior: 'smooth', block: 'start'});
    }

    function closeWorkspace() {
        const workspace = byId('ai-feasibility-workspace');
        if (workspace) workspace.style.display = 'none';
    }

    function updateIntentCount() {
        const input = byId('ai-feasibility-intent');
        const count = byId('ai-feasibility-intent-count');
        if (count) count.textContent = String(input?.value.length || 0);
    }

    async function uploadIntent(file) {
        if (!file) return;
        const status = byId('ai-feasibility-upload-status');
        if (status) status.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Reading intent document…';
        const formData = new FormData();
        formData.append('file', file);
        try {
            const result = await fetchJson('/api/ai-feasibility/intent-upload', {method: 'POST', body: formData});
            const input = byId('ai-feasibility-intent');
            if (input) input.value = result.text || '';
            state.inputSource = {type: 'upload', name: result.filename, sha256: result.sha256};
            if (result.inference?.category_id && state.categories.some((item) => item.id === result.inference.category_id)) {
                state.selectedCategoryId = result.inference.category_id;
                renderCategories();
                renderUsageFields();
            }
            updateIntentCount();
            if (status) status.innerHTML = `<span class="text-success"><i class="bi bi-check-circle me-1"></i>${escapeHtml(result.filename)} read · ${Number(result.character_count || 0).toLocaleString()} characters · ${escapeHtml(result.inference?.confidence || 'low')} category confidence</span>`;
        } catch (error) {
            if (status) status.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>${escapeHtml(error.message)}</span>`;
        }
    }

    function collectUsageAssumptions() {
        const values = {};
        document.querySelectorAll('.ai-usage-input').forEach((input) => {
            if (input.value !== '') values[input.dataset.usageId] = Number(input.value);
        });
        return values;
    }

    async function generateAssessment() {
        const status = byId('ai-feasibility-generate-status');
        const button = byId('ai-feasibility-generate');
        const payload = {
            application_id: state.selectedApplicationId,
            category_id: state.selectedCategoryId,
            intent: byId('ai-feasibility-intent')?.value.trim() || '',
            business_outcome: byId('ai-feasibility-outcome')?.value.trim() || '',
            region: byId('ai-feasibility-region')?.value || 'eastus',
            usage_assumptions: collectUsageAssumptions(),
            consent_confirmed: Boolean(byId('ai-feasibility-consent')?.checked),
            input_source: state.inputSource,
        };
        button.disabled = true;
        if (status) status.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Applying evidence gates, costing the pattern, and generating the decision narrative…';
        try {
            const assessment = await fetchJson('/api/ai-feasibility/assessments', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload),
            });
            state.currentAssessment = assessment;
            state.assessments = [assessment, ...state.assessments.filter((item) => item.id !== assessment.id)];
            renderSavedAssessments();
            renderAssessment(assessment);
            if (status) status.innerHTML = `<span class="text-success"><i class="bi bi-check-circle me-1"></i>Assessment ${escapeHtml(assessment.id)} revision ${Number(assessment.version || 1)} generated and persisted.</span>`;
            byId('ai-feasibility-result')?.scrollIntoView({behavior: 'smooth', block: 'start'});
        } catch (error) {
            if (status) status.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>${escapeHtml(error.message)}</span>`;
        } finally {
            button.disabled = false;
        }
    }

    function renderAssessment(assessment) {
        const container = byId('ai-feasibility-result');
        if (!container) return;
        const decision = assessment.executive_decision || {};
        const dispositionClass = decision.disposition === 'poc_candidate' ? '' : 'needs-evidence';
        const dimensions = (assessment.dimension_findings || []).map((item) => `<div class="ai-dimension-card">
            <span class="status ${escapeHtml(item.status)}">${escapeHtml(String(item.status || '').replaceAll('_', ' '))}</span>
            <div class="fw-semibold small mb-1">${escapeHtml(item.label)}</div>
            <div class="small text-muted">${escapeHtml(item.finding)}</div>
        </div>`).join('');
        const services = (assessment.recommended_services || []).map((item) => `<div class="ai-service-item">
            <div class="fw-semibold small"><i class="bi bi-microsoft me-1 text-info"></i>${escapeHtml(item.name)}</div>
            <div class="small text-muted mt-1">${escapeHtml(item.role)}</div>
            <div class="small text-warning mt-1"><i class="bi bi-exclamation-circle me-1"></i>Proposed · validation required</div>
        </div>`).join('');
        const scenarios = assessment.cost_estimate?.scenarios || {};
        const scenarioCards = ['low', 'base', 'high'].map((key) => {
            const item = scenarios[key] || {};
            return `<div class="col-md-4"><div class="ai-cost-scenario ${key === 'base' ? 'base' : ''}">
                <div class="small text-muted">${escapeHtml(item.name || key)}</div>
                <div class="ai-cost-value">${formatMoney(item.budget_with_reserve_usd)}<span class="fs-6">/mo</span></div>
                <div class="small text-muted">Services ${formatMoney(item.service_subtotal_usd)} + 20% reserve</div>
            </div></div>`;
        }).join('');
        const costRows = (assessment.cost_estimate?.line_items || []).map((line) => `<tr>
            <td><strong>${escapeHtml(line.service)}</strong><div class="small text-muted">${escapeHtml(line.description)}</div></td>
            <td>${Number(line.quantity || 0).toLocaleString()} ${escapeHtml(line.unit)}</td>
            <td class="text-end">${formatMoney(line.monthly_cost_usd)}</td>
        </tr>`).join('');
        const extension = assessment.architecture_extension || {};
        const integration = extension.integration_point || {};
        const componentChips = (extension.components || []).map((item) => `<span class="ai-component-chip"><i class="bi bi-stars"></i>${escapeHtml(item.name)}</span>`).join('');
        const gaps = (assessment.gaps || []).map((item) => `<li class="mb-1">${escapeHtml(item)}</li>`).join('');
        const tests = (assessment.poc_plan?.acceptance_tests || []).map((item) => `<li class="mb-1">${escapeHtml(item)}</li>`).join('');
        const generation = assessment.generation || {};

        container.innerHTML = `<div class="ai-assessment-banner mb-3">
            <div class="d-flex flex-wrap justify-content-between gap-3 align-items-start position-relative" style="z-index:1">
                <div class="flex-grow-1">
                    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                        <span class="ai-disposition ${dispositionClass}"><i class="bi bi-${decision.disposition === 'poc_candidate' ? 'check-circle' : 'search'}"></i>${escapeHtml(decision.disposition_label || 'Needs evidence')}</span>
                        <span class="badge bg-dark border">Revision ${Number(assessment.version || 1)}</span>
                        <span class="badge bg-dark border">${escapeHtml(assessment.status)}</span>
                        <span class="badge bg-primary">${escapeHtml(assessment.solution_category?.label)}</span>
                    </div>
                    <h4 class="mb-1">${escapeHtml(assessment.application?.name)} AI opportunity decision</h4>
                    <div class="small text-muted mb-3">${escapeHtml(assessment.id)} · ${escapeHtml(assessment.cost_estimate?.region)} · ${escapeHtml(generation.narrative_provider || 'local-grounded')}${generation.model_deployment ? ` · ${escapeHtml(generation.model_deployment)}` : ''}</div>
                    <p class="mb-0" style="white-space:pre-line">${escapeHtml(decision.summary)}</p>
                </div>
                <div class="d-flex flex-column gap-2">
                    <button class="btn btn-sm btn-primary" type="button" data-ai-architecture="${escapeHtml(assessment.id)}"><i class="bi bi-boxes me-1"></i>View AI-ready architecture</button>
                    <button class="btn btn-sm btn-outline-info" type="button" data-ai-download="${escapeHtml(assessment.id)}"><i class="bi bi-download me-1"></i>Download JSON</button>
                    <button class="btn btn-sm btn-outline-danger" type="button" data-ai-delete="${escapeHtml(assessment.id)}"><i class="bi bi-trash me-1"></i>Delete revision</button>
                </div>
            </div>
        </div>

        <div class="card-dark mb-3"><div class="card-header"><i class="bi bi-clipboard-data me-2"></i>Feasibility by decision dimension</div><div class="card-body p-3"><div class="ai-dimension-grid">${dimensions}</div></div></div>

        <div class="row g-3 mb-3">
            <div class="col-lg-6"><div class="card-dark h-100"><div class="card-header"><i class="bi bi-microsoft me-2"></i>Proposed Azure capability set</div><div class="card-body p-3"><div class="ai-service-list">${services}</div></div></div></div>
            <div class="col-lg-6"><div class="card-dark h-100"><div class="card-header"><i class="bi bi-diagram-3 me-2"></i>Where AI fits</div><div class="card-body p-3">
                <div class="ai-architecture-fit"><div class="small text-muted text-uppercase mb-1">Existing integration point</div><div class="fw-semibold">${escapeHtml(integration.name || assessment.application?.name)}</div><div class="small text-muted mb-3">${escapeHtml(integration.type || 'application')} · ${escapeHtml(integration.assessed_target || 'Target requires validation')}</div>
                <div class="small text-muted text-uppercase mb-1">Proposed AI extension</div>${componentChips}<p class="small text-muted mt-3 mb-0">${escapeHtml(extension.fallback || '')}</p></div>
            </div></div></div>
        </div>

        <div class="card-dark mb-3"><div class="card-header d-flex justify-content-between align-items-center"><span><i class="bi bi-cash-stack me-2"></i>Indicative incremental AI cost</span><span class="badge bg-warning text-dark">Not an Azure quote</span></div><div class="card-body p-3">
            <div class="row g-2 mb-3">${scenarioCards}</div>
            <div class="table-responsive"><table class="table table-sm table-dark-custom mb-2"><thead><tr><th>Planning line</th><th>Quantity</th><th class="text-end">Base monthly</th></tr></thead><tbody>${costRows}</tbody></table></div>
            <div class="small text-muted">${escapeHtml(assessment.cost_estimate?.pricing_notice || '')}</div>
        </div></div>

        <div class="row g-3">
            <div class="col-lg-6"><div class="card-dark h-100"><div class="card-header"><i class="bi bi-exclamation-diamond me-2"></i>Evidence gaps and decision conditions</div><div class="card-body p-3"><ul class="small mb-0">${gaps}</ul></div></div></div>
            <div class="col-lg-6"><div class="card-dark h-100"><div class="card-header"><i class="bi bi-beaker me-2"></i>Bounded PoC acceptance plan</div><div class="card-body p-3"><div class="small mb-2"><strong>${assessment.poc_plan?.recommended_duration_weeks?.join('–')} weeks</strong> · ${assessment.poc_plan?.estimated_effort_person_weeks?.join('–')} person-weeks indicative effort</div><ul class="small mb-0">${tests}</ul></div></div></div>
        </div>`;

        container.querySelector('[data-ai-architecture]')?.addEventListener('click', () => openAILandingZone(assessment));
        container.querySelector('[data-ai-download]')?.addEventListener('click', () => downloadAssessment(assessment));
        container.querySelector('[data-ai-delete]')?.addEventListener('click', () => deleteAssessment(assessment.id));
    }

    function downloadAssessment(assessment) {
        const blob = new Blob([JSON.stringify(assessment, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `${assessment.id}-ai-feasibility.json`;
        anchor.click();
        URL.revokeObjectURL(url);
    }

    async function deleteAssessment(assessmentId) {
        if (!window.confirm('Delete this local AI feasibility assessment revision?')) return;
        try {
            await fetchJson(`/api/ai-feasibility/assessments/${encodeURIComponent(assessmentId)}`, {method: 'DELETE'});
            state.assessments = state.assessments.filter((item) => item.id !== assessmentId);
            if (state.currentAssessment?.id === assessmentId) state.currentAssessment = null;
            renderSavedAssessments();
            const result = byId('ai-feasibility-result');
            if (result) result.innerHTML = '<div class="alert alert-info">Assessment revision deleted.</div>';
        } catch (error) {
            window.alert(error.message);
        }
    }

    function openAILandingZone(assessment) {
        if (window.bootstrap) bootstrap.Tab.getOrCreateInstance(byId('tab-plan')).show();
        window.showPlanSub?.('plan-landing-zone');
        const toggle = byId('landing-zone-ai-feasibility');
        if (toggle) {
            toggle.checked = true;
            toggle.dataset.assessmentId = assessment.id;
        }
        const region = byId('landing-zone-region');
        if (region && assessment.cost_estimate?.region) region.value = assessment.cost_estimate.region;
        window.loadLandingZones?.();
    }

    function initialize() {
        byId('ai-feasibility-open')?.addEventListener('click', () => openWorkspace());
        byId('ai-feasibility-close')?.addEventListener('click', closeWorkspace);
        byId('ai-feasibility-refresh')?.addEventListener('click', async () => {
            state.loaded = false;
            await loadWorkspace(true);
        });
        byId('ai-feasibility-application')?.addEventListener('change', (event) => {
            state.selectedApplicationId = event.target.value;
            renderApplicationContext();
        });
        byId('ai-feasibility-file')?.addEventListener('change', (event) => uploadIntent(event.target.files?.[0]));
        byId('ai-feasibility-intent')?.addEventListener('input', updateIntentCount);
        byId('ai-feasibility-generate')?.addEventListener('click', generateAssessment);
        byId('landing-zone-ai-feasibility')?.addEventListener('change', (event) => {
            if (!event.target.checked) delete event.target.dataset.assessmentId;
        });
    }

    document.addEventListener('DOMContentLoaded', initialize);
    window.openAIFeasibilityAssessment = openWorkspace;
    window.renderAIFeasibilityAssessment = renderAssessment;
    window.openAILandingZone = openAILandingZone;
})();
