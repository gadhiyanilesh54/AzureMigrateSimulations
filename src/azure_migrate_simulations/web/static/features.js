/* =========================================================================
   Azure Migrate Simulations — Features Module (v2)
   Journey: Overview → Decide → Plan → Execute
   All sub-tab switching uses reliable show/hide. Each feature calls APIs
   directly — no fragile DOM content-moving.
   ========================================================================= */

// ═══════════════════════════════════════════════════════════════════
//  PHASE SUB-TAB SWITCHING
// ═══════════════════════════════════════════════════════════════════
// Helper: hide all phase sub-panes that live outside their parent tab-pane
function _hideAllPhaseSubs() {
    document.querySelectorAll('.decide-sub, .plan-sub, .plan-sub-content').forEach(el => el.style.display = 'none');
}

function showDecideSub(id) {
    // Hide all decide sub-tabs (both inside pane-decide and sibling content divs)
    _hideAllPhaseSubs();
    document.querySelectorAll('#decideSubTabs .nav-link').forEach(el => el.classList.remove('active'));
    const pane = document.getElementById(id);
    const tab = document.getElementById(id + '-tab');
    if (pane) pane.style.display = '';
    if (tab) tab.classList.add('active');
    if (id === 'decide-enrichment' && typeof loadEnrichmentTab === 'function') setTimeout(loadEnrichmentTab, 100);
}

function showPlanSub(id) {
    _hideAllPhaseSubs();
    document.querySelectorAll('#planSubTabs .nav-link').forEach(el => el.classList.remove('active'));
    const pane = document.getElementById(id);
    const tab = document.getElementById(id + '-tab');
    if (pane) pane.style.display = '';
    if (tab) tab.classList.add('active');
    // If showing CTD placeholder, also show the CTD content div
    if (id === 'plan-ctd') {
        const ctdContent = document.getElementById('plan-ctd-content');
        if (ctdContent) ctdContent.style.display = '';
    }
    // Auto-load saved wave plan when switching to Wave Planning
    if (id === 'plan-waves' && typeof loadSavedWavePlan === 'function') {
        setTimeout(loadSavedWavePlan, 100);
    }
}

function showExecSub(id) {
    _hideAllPhaseSubs();
    document.querySelectorAll('.exec-sub').forEach(el => el.style.display = 'none');
    document.querySelectorAll('#executeSubTabs .nav-link').forEach(el => el.classList.remove('active'));
    const pane = document.getElementById(id);
    const tab = document.getElementById(id + '-tab');
    if (pane) pane.style.display = '';
    if (tab) tab.classList.add('active');
}

// Init on load — no content moving needed, everything is inline
document.addEventListener('DOMContentLoaded', () => {
    // When Decide phase is shown, show its default sub-tab (discovery)
    document.getElementById('tab-decide')?.addEventListener('shown.bs.tab', () => {
        showDecideSub('decide-discovery');
    });
    // When Plan phase is shown, show its default sub-tab (CTD)
    document.getElementById('tab-plan')?.addEventListener('shown.bs.tab', () => {
        showPlanSub('plan-ctd');
    });
    // When Execute phase is shown, load tracker
    document.getElementById('tab-execute')?.addEventListener('shown.bs.tab', () => {
        _hideAllPhaseSubs();
        loadMigrationTracker();
    });
    // When leaving to Dashboard/Overview, hide all sibling content divs
    document.getElementById('tab-dashboard')?.addEventListener('shown.bs.tab', () => {
        _hideAllPhaseSubs();
    });
});

// ═══════════════════════════════════════════════════════════════════
//  PRICING COMPARISON
// ═══════════════════════════════════════════════════════════════════
async function loadPricingComparison() {
    const c = document.getElementById('pricing-results');
    c.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-2 text-muted">Comparing…</p></div>';
    try {
        const d = await (await fetch('/api/pricing/comparison')).json();
        const fmt = v => '$'+(v||0).toLocaleString(undefined,{maximumFractionDigits:0});
        const b = d.blended_optimal||{}, f = d.fleet_summary||{};
        let h = `<div class="row g-3 mb-4">
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-success">${fmt(b.monthly_total)}</div><div class="stat-label">Blended Monthly</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-primary">${fmt(b.savings_vs_payg)}</div><div class="stat-label">Savings vs PAYG</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value">${fmt(b.annual_savings)}</div><div class="stat-label">Annual Savings</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-info">${b.savings_pct||0}%</div><div class="stat-label">Savings %</div></div></div>
        </div><h6><i class="bi bi-table me-2"></i>Fleet Cost by Model</h6>
        <div class="table-responsive mb-4"><table class="table table-sm table-hover"><thead><tr><th>Model</th><th>Monthly</th><th>Savings</th><th>%</th></tr></thead><tbody>`;
        for (const [,i] of Object.entries(f)) h+=`<tr><td>${i.label}</td><td>${fmt(i.monthly_total)}</td><td>${fmt(i.savings_vs_payg)}</td><td>${i.savings_pct}%</td></tr>`;
        h+='</tbody></table></div>';
        c.innerHTML = h;
    } catch(e) { c.innerHTML = '<div class="alert alert-warning">Failed.</div>'; }
}

// ═══════════════════════════════════════════════════════════════════
//  APPLICATION GROUPS
// ═══════════════════════════════════════════════════════════════════
function _applicationComponentBadges(summary) {
    const items = [
        ['VMs', summary.virtual_machines || 0, 'primary'],
        ['Web Apps', summary.web_apps || 0, 'success'],
        ['Databases', summary.databases || 0, 'danger'],
        ['Containers', summary.containers || 0, 'info'],
        ['Orchestrators', summary.orchestrators || 0, 'warning'],
        ['File Shares', summary.file_shares || 0, 'secondary'],
    ];
    return items.map(([label, count, colour]) =>
        `<span class="badge bg-${colour} me-1 mb-1">${count} ${label}</span>`
    ).join('');
}

function _applicationMemberGroups(members) {
    const categories = [
        ['Virtual Machines', 'vm'],
        ['Web Apps', 'webapp'],
        ['Databases', 'database'],
        ['Containers', 'container'],
        ['Orchestrators', 'orchestrator'],
        ['File Shares', 'fileshare'],
    ];
    let html = '';
    for (const [label, type] of categories) {
        const typedMembers = members.filter(member => member.type === type);
        if (!typedMembers.length) continue;
        html += `<div class="mb-2"><strong class="small">${label} (${typedMembers.length})</strong><ul class="list-unstyled small ms-2 mb-0">`;
        html += typedMembers.slice(0, 20).map(member => {
            const target = member.target_service ? ` <span class="text-muted">→ ${esc(member.target_service)}</span>` : '';
            return `<li><i class="bi bi-dot"></i>${esc(member.name)}${target}</li>`;
        }).join('');
        if (typedMembers.length > 20) html += `<li class="text-muted">…and ${typedMembers.length - 20} more</li>`;
        html += '</ul></div>';
    }
    return html;
}

async function loadApplicationGroups() {
    const c = document.getElementById('appgroups-results');
    c.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    try {
        const response = await fetch('/api/applications');
        const d = await response.json();
        if (!response.ok) throw new Error(d.error || 'Unable to detect applications.');
        const totalMembers = (d.applications || []).reduce((sum, app) => sum + (app.member_count || 0), 0);
        let h = `<div class="d-flex flex-wrap gap-2 align-items-center mb-3">
            <span class="badge bg-primary fs-6">${d.application_count} Applications</span>
            <span class="badge bg-secondary fs-6">${totalMembers} Members</span>
            <span class="text-muted small">Each card is one complete migration application.</span>
        </div><div class="row g-3">`;
        for (const a of (d.applications||[])) {
            const cc = a.complexity_score>=7?'danger':a.complexity_score>=4?'warning':'success';
            h += `<div class="col-md-6 col-xl-4"><div class="card bg-dark border-secondary h-100 application-group-card">
                <div class="card-header d-flex justify-content-between align-items-center"><div><i class="bi bi-box me-2 text-primary"></i><strong>${esc(a.name)}</strong></div><span class="badge bg-${cc}">Complexity ${a.complexity_score}/10</span></div>
                <div class="card-body">
                <div class="mb-2">${_applicationComponentBadges(a.component_summary || {})}</div>
                <span class="badge bg-dark border me-1">${a.dependency_count} dependencies</span><span class="badge bg-info me-1">${esc(a.criticality)}</span><span class="badge bg-dark border">${esc(a.environment || 'Production')}</span>
                <div class="small mt-3"><span class="text-muted">Assessed target:</span> <strong>$${(a.target_monthly_cost||0).toLocaleString(undefined,{maximumFractionDigits:0})}/mo</strong></div>
                <details class="mt-2"><summary class="small text-info" style="cursor:pointer">Application members (${a.member_count || 0})</summary><div class="mt-2">${_applicationMemberGroups(a.members || [])}</div></details>
                </div></div></div>`;
        }
        c.innerHTML = h+'</div>';
    } catch(e) { c.innerHTML = `<div class="alert alert-warning">${esc(e.message || 'Failed.')}</div>`; }
}

// ═══════════════════════════════════════════════════════════════════
//  APPLICATION LANDING ZONES (CTD CATALOGUE)
// ═══════════════════════════════════════════════════════════════════
let _landingZoneData = null;
let _landingZoneCurrentApplicationId = null;

const _AZURE_ICON_BASE = '/static/icons/azure/';

function _svgEscape(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function _svgLabelLines(value, maxChars = 22, maxLines = 2) {
    const words = String(value || '').trim().split(/\s+/).filter(Boolean);
    if (!words.length) return ['Azure service'];
    const lines = [];
    let current = '';
    for (const word of words) {
        const candidate = current ? `${current} ${word}` : word;
        if (candidate.length <= maxChars || !current) {
            current = candidate;
        } else {
            lines.push(current);
            current = word;
        }
    }
    if (current) lines.push(current);
    if (lines.length > maxLines) {
        const visible = lines.slice(0, maxLines);
        visible[maxLines - 1] = visible[maxLines - 1].slice(0, Math.max(1, maxChars - 1)).trimEnd() + '…';
        return visible;
    }
    return lines;
}

function _svgTextBlock(lines, x, y, className, lineHeight = 16, anchor = 'middle') {
    return `<text x="${x}" y="${y}" class="${className}" text-anchor="${anchor}">` +
        lines.map((line, index) => `<tspan x="${x}" dy="${index ? lineHeight : 0}">${_svgEscape(line)}</tspan>`).join('') +
        '</text>';
}

function _azureIconForSlot(slot) {
    const target = String(slot.resolved_target || '').toLowerCase();
    const modules = (slot.group || []).join(' ').toLowerCase();
    const value = `${target} ${modules}`;
    if (value.includes('application gateway')) return 'application-gateway.svg';
    if (value.includes('postgres')) return 'azure-database-postgresql-server.svg';
    if (value.includes('cosmos')) return 'azure-cosmos-db.svg';
    if (value.includes('mysql') || value.includes('mariadb')) return 'azure-database-mysql-server.svg';
    if (value.includes('sql') || value.includes('oracle') || value.includes('redis')) return 'sql-database.svg';
    if (value.includes('kubernetes') || value.includes('aks') || value.includes('openshift') || value.includes('aro')) return 'kubernetes-services.svg';
    if (value.includes('container app') || value.includes('container instance')) return 'container-apps-environments.svg';
    if (value.includes('function')) return 'function-apps.svg';
    if (value.includes('virtual machine') || value.includes('sql-vm')) return 'virtual-machine.svg';
    if (value.includes('app service') || value.includes('spring')) return 'app-services.svg';
    if (value.includes('file') || value.includes('storage') || value.includes('blob') || value.includes('netapp') || value.includes('disk')) return 'azure-fileshares.svg';
    if (slot.domain === 'data') return 'sql-database.svg';
    if (slot.domain === 'storage') return 'azure-fileshares.svg';
    return 'app-services.svg';
}

function _slotVisual(slot) {
    const count = slot.count || (slot.members || []).length || 1;
    const cost = slot.monthly_cost || 0;
    const meta = [`${count} assessed ${count === 1 ? 'target' : 'targets'}`];
    if (cost > 0) meta.push(`$${cost.toLocaleString(undefined, {maximumFractionDigits: 0})}/mo`);
    return {
        id: slot.slot,
        label: slot.resolved_target || slot.slot,
        meta: meta.join(' · '),
        icon: _azureIconForSlot(slot),
        domain: slot.domain,
        title: `${slot.resolved_target || slot.slot}\n${meta.join(' · ')}`,
    };
}

function _aiComponentVisual(component) {
    const cost = Number(component.monthly_cost_usd || 0);
    return {
        id: component.id || component.name,
        label: component.name || 'Azure AI service',
        meta: cost > 0 ? `Proposed · $${cost.toLocaleString(undefined, {maximumFractionDigits: 0})}/mo` : 'Proposed AI component',
        icon: component.icon || 'ai-generic',
        domain: 'ai',
        title: `${component.name || 'Azure AI service'}\nProposed: ${component.role || 'AI capability'}`,
    };
}

function _azureServiceCard(item, x, y, width = 180, height = 118) {
    const iconSize = 48;
    const iconX = x + (width - iconSize) / 2;
    const labelLines = _svgLabelLines(item.label, 24, 2);
    const labelY = y + 76;
    const iconMarkup = item.icon === 'ai-generic'
        ? `<g aria-hidden="true"><rect x="${iconX}" y="${y + 12}" width="${iconSize}" height="${iconSize}" rx="12" fill="#7c3aed"/><circle cx="${iconX + 17}" cy="${y + 33}" r="7" fill="#50e6ff"/><circle cx="${iconX + 31}" cy="${y + 39}" r="8" fill="#fff" fill-opacity=".9"/><text x="${iconX + iconSize / 2}" y="${y + 56}" fill="#fff" font-size="9" font-weight="700" text-anchor="middle">AI</text></g>`
        : `<image href="${_AZURE_ICON_BASE}${_svgEscape(item.icon)}" x="${iconX}" y="${y + 12}" width="${iconSize}" height="${iconSize}" preserveAspectRatio="xMidYMid meet" />`;
    return `<g class="azure-service-node" data-service-id="${_svgEscape(item.id)}" tabindex="0" role="img" aria-label="${_svgEscape(item.title || item.label)}">
        <title>${_svgEscape(item.title || item.label)}</title>
        <rect class="azure-service-card" x="${x}" y="${y}" width="${width}" height="${height}" rx="4" />
        ${iconMarkup}
        ${_svgTextBlock(labelLines, x + width / 2, labelY, 'azure-service-title', 15)}
        <text x="${x + width / 2}" y="${y + height - 10}" class="azure-service-meta" text-anchor="middle">${_svgEscape(item.meta || '')}</text>
    </g>`;
}

function _layoutArchitectureCards(items, box, columns = 3) {
    const cardWidth = 180;
    const cardHeight = 118;
    const gapX = 18;
    const gapY = 18;
    const actualColumns = Math.max(1, Math.min(columns, items.length || 1));
    const gridWidth = actualColumns * cardWidth + (actualColumns - 1) * gapX;
    const startX = box.x + Math.max(20, (box.width - gridWidth) / 2);
    const startY = box.y + 52;
    return items.map((item, index) => ({
        item,
        x: startX + (index % actualColumns) * (cardWidth + gapX),
        y: startY + Math.floor(index / actualColumns) * (cardHeight + gapY),
        width: cardWidth,
        height: cardHeight,
    }));
}

function _orthogonalPath(x1, y1, x2, y2, mode = 'vertical') {
    if (mode === 'horizontal') {
        const middleX = (x1 + x2) / 2;
        return `M ${x1} ${y1} H ${middleX} V ${y2} H ${x2}`;
    }
    const middleY = (y1 + y2) / 2;
    return `M ${x1} ${y1} V ${middleY} H ${x2} V ${y2}`;
}

function _architectureSection(box, title, subtitle, accent = '#0078d4') {
    return `<rect class="azure-tier-boundary" x="${box.x}" y="${box.y}" width="${box.width}" height="${box.height}" rx="4" />
        <rect x="${box.x}" y="${box.y}" width="5" height="${box.height}" fill="${accent}" />
        <text x="${box.x + 16}" y="${box.y + 24}" class="azure-boundary-title">${_svgEscape(title)}</text>
        <text x="${box.x + 16}" y="${box.y + 41}" class="azure-service-meta">${_svgEscape(subtitle)}</text>`;
}

function _renderApplicationArchitectureSvg(app) {
    const slots = app.slots || [];
    const computeItems = slots.filter(slot => slot.origin === 'migrated' && slot.domain === 'compute').map(_slotVisual);
    const dataItems = slots.filter(slot => slot.origin === 'migrated' && slot.domain === 'data').map(_slotVisual);
    const storageItems = slots.filter(slot => slot.origin === 'migrated' && slot.domain === 'storage').map(_slotVisual);
    const targetItems = [...dataItems, ...storageItems];
    const aiItems = (app.ai_extension?.components || []).map(_aiComponentVisual);
    const aiReady = Boolean(app.ai_ready && aiItems.length);
    const hasSecurity = slots.some(slot => slot.domain === 'security');
    const hasMonitoring = slots.some(slot => slot.domain === 'monitoring');
    const hasBackup = slots.some(slot => slot.domain === 'backup-and-recovery');

    const platformItems = [];
    if (hasSecurity) {
        platformItems.push({id: 'managed-identities', label: 'Managed identities', meta: 'Passwordless access', icon: 'managed-identities.svg', title: 'Managed identities · Passwordless workload access'});
        platformItems.push({id: 'key-vault', label: 'Azure Key Vault', meta: 'Secrets & certificates', icon: 'key-vault.svg', title: 'Azure Key Vault · Secrets and certificates'});
    }
    if (hasMonitoring) platformItems.push({id: 'application-insights', label: 'Application Insights', meta: 'Telemetry & observability', icon: 'application-insights.svg', title: 'Application Insights and Azure Monitor'});
    if (hasBackup) platformItems.push({id: 'recovery-services', label: 'Recovery Services vault', meta: 'Backup & recovery', icon: 'recovery-services-vaults.svg', title: 'Recovery Services vault · Backup and recovery'});

    const width = 1800;
    const aiRows = Math.max(1, Math.ceil(Math.max(aiItems.length, 1) / 5));
    const aiBox = {x: 300, y: 535, width: 1330, height: aiRows * 136 + 78};
    const aiCards = aiReady ? _layoutArchitectureCards(aiItems, aiBox, 5) : [];
    const tierY = aiReady ? aiBox.y + aiBox.height + 38 : 550;
    const workloadRows = Math.max(1, Math.ceil(Math.max(computeItems.length, 1) / 3));
    const targetRows = Math.max(1, Math.ceil(Math.max(targetItems.length, 1) / 3));
    const tierHeight = Math.max(workloadRows, targetRows) * 136 + 78;
    const height = Math.max(930, tierY + tierHeight + 95);
    const workloadBox = {x: 300, y: tierY, width: 650, height: tierHeight};
    const targetBox = {x: 980, y: tierY, width: 650, height: tierHeight};
    const platformBox = {x: 1280, y: 165, width: 430, height: 340};
    const workloadCards = _layoutArchitectureCards(computeItems, workloadBox, 3);
    const targetCards = _layoutArchitectureCards(targetItems, targetBox, 3);
    const platformCards = _layoutArchitectureCards(platformItems, platformBox, 2).map(card => ({...card, width: 180, height: 112}));

    const gatewayCard = {x: 280, y: 275, width: 180, height: 118};
    const integrationCard = {x: 590, y: 275, width: 180, height: 118};
    const endpointCard = {x: 930, y: 275, width: 180, height: 118};
    const generated = _landingZoneData?.generated_at ? new Date(_landingZoneData.generated_at).toLocaleString() : 'Current assessment';
    const region = _landingZoneData?.region || 'eastus';
    const catalogueVersion = _landingZoneData?.catalogue?.version || '';
    const resourceGroup = app.landing_zone?.resource_group || '';
    const vnet = app.landing_zone?.vnet || {};

    const svgStyle = `.azure-boundary{fill:#fff;stroke:#0078d4;stroke-width:2}.azure-landing-boundary{fill:#f8fbfe;stroke:#5ea0ef;stroke-width:2;stroke-dasharray:10 6}.azure-vnet-boundary{fill:#f4f9fd;stroke:#0078d4;stroke-width:3}.azure-subnet-boundary{fill:#fff;stroke:#8ac2e8;stroke-width:2}.azure-tier-boundary{fill:#faf9f8;stroke:#c8c6c4;stroke-width:1.5}.azure-service-card{fill:#fff;stroke:#d2d0ce;stroke-width:1.5;filter:url(#azureCardShadow)}.azure-flow{fill:none;stroke:#323130;stroke-width:2}.azure-ai-flow{fill:none;stroke:#7c3aed;stroke-width:2.3}.azure-control-flow{fill:none;stroke:#605e5c;stroke-width:1.5;stroke-dasharray:7 5}.azure-boundary-title{fill:#005a9e;font-size:16px;font-weight:600}.azure-subnet-title{fill:#005a9e;font-size:13px;font-weight:600}.azure-service-title{fill:#201f1e;font-size:13px;font-weight:600}.azure-service-meta{fill:#605e5c;font-size:11px}.azure-diagram-title{fill:#201f1e;font-size:24px;font-weight:600}.azure-diagram-meta{fill:#605e5c;font-size:12px}`;

    let flows = `<path class="azure-flow" marker-end="url(#azureArrow)" d="M 120 334 H ${gatewayCard.x}" />
        <path class="azure-flow" marker-end="url(#azureArrow)" d="${_orthogonalPath(gatewayCard.x + gatewayCard.width, gatewayCard.y + gatewayCard.height / 2, integrationCard.x, integrationCard.y + integrationCard.height / 2, 'horizontal')}" />`;
    if (aiReady) {
        const aiAnchor = aiCards.find(card => card.item.id === 'orchestration') || aiCards[0];
        flows += `<path class="azure-ai-flow" marker-end="url(#azureAiArrow)" d="${_orthogonalPath(integrationCard.x + integrationCard.width / 2, integrationCard.y + integrationCard.height, aiAnchor.x + aiAnchor.width / 2, aiAnchor.y)}" />`;
        for (const card of aiCards) {
            if (card === aiAnchor) continue;
            flows += `<path class="azure-ai-flow" marker-end="url(#azureAiArrow)" d="${_orthogonalPath(aiAnchor.x + aiAnchor.width / 2, aiAnchor.y + aiAnchor.height, card.x + card.width / 2, card.y, 'horizontal')}" />`;
        }
        flows += `<path class="azure-ai-flow" marker-end="url(#azureAiArrow)" d="${_orthogonalPath(aiAnchor.x + aiAnchor.width / 2, aiAnchor.y + aiAnchor.height, workloadBox.x + workloadBox.width / 2, workloadBox.y)}" />`;
        flows += `<path class="azure-ai-flow" marker-end="url(#azureAiArrow)" d="${_orthogonalPath(aiAnchor.x + aiAnchor.width / 2, aiAnchor.y + aiAnchor.height, targetBox.x + targetBox.width / 2, targetBox.y)}" />`;
    } else {
        for (const card of workloadCards) {
            flows += `<path class="azure-flow" marker-end="url(#azureArrow)" d="${_orthogonalPath(integrationCard.x + integrationCard.width / 2, integrationCard.y + integrationCard.height, card.x + card.width / 2, card.y)}" />`;
        }
    }
    if (workloadCards.length && targetCards.length) {
        const workloadAnchor = workloadCards[Math.min(1, workloadCards.length - 1)];
        flows += `<path class="azure-flow" marker-end="url(#azureArrow)" d="${_orthogonalPath(workloadAnchor.x + workloadAnchor.width, workloadAnchor.y + workloadAnchor.height / 2, endpointCard.x + endpointCard.width / 2, endpointCard.y + endpointCard.height, 'horizontal')}" />`;
    }
    for (const card of targetCards) {
        flows += `<path class="azure-flow" marker-end="url(#azureArrow)" d="${_orthogonalPath(endpointCard.x + endpointCard.width / 2, endpointCard.y + endpointCard.height, card.x + card.width / 2, card.y)}" />`;
    }
    if (platformCards.length) {
        flows += `<path class="azure-control-flow" marker-end="url(#azureMutedArrow)" d="${_orthogonalPath(platformBox.x, platformBox.y + platformBox.height / 2, workloadBox.x + workloadBox.width, workloadBox.y + 24, 'horizontal')}" />`;
        flows += `<path class="azure-control-flow" marker-end="url(#azureMutedArrow)" d="${_orthogonalPath(platformBox.x + platformBox.width / 2, platformBox.y + platformBox.height, targetBox.x + targetBox.width / 2, targetBox.y)}" />`;
    }

    const computeMarkup = workloadCards.length
        ? workloadCards.map(card => _azureServiceCard(card.item, card.x, card.y, card.width, card.height)).join('')
        : `<text x="${workloadBox.x + workloadBox.width / 2}" y="${workloadBox.y + 105}" class="azure-service-meta" text-anchor="middle">No standalone compute target was assessed</text>`;
    const targetMarkup = targetCards.length
        ? targetCards.map(card => _azureServiceCard(card.item, card.x, card.y, card.width, card.height)).join('')
        : `<text x="${targetBox.x + targetBox.width / 2}" y="${targetBox.y + 105}" class="azure-service-meta" text-anchor="middle">No separate data or storage target was assessed</text>`;

    return `<svg class="azure-architecture-svg" data-application-id="${_svgEscape(app.id)}" xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMin meet" role="img" aria-labelledby="azureArchitectureTitle azureArchitectureDescription">
        <title id="azureArchitectureTitle">${_svgEscape(app.name)} Azure ${aiReady ? 'AI-ready ' : ''}application landing-zone architecture</title>
        <desc id="azureArchitectureDescription">Professional Azure solution architecture showing users, ingress, virtual network integration, private endpoints, assessed workload services, data and storage services, identity, monitoring, backup${aiReady ? ', and proposed AI services from the linked feasibility assessment' : ''}.</desc>
        <defs>
            <style>${svgStyle}</style>
            <filter id="azureCardShadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.14" /></filter>
            <marker id="azureArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" fill="#323130" /></marker>
            <marker id="azureAiArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" fill="#7c3aed" /></marker>
            <marker id="azureMutedArrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 8 4 L 0 8 z" fill="#605e5c" /></marker>
        </defs>
        <rect width="${width}" height="${height}" fill="#fff" />
        <text x="30" y="42" class="azure-diagram-title">${_svgEscape(app.name)} — ${aiReady ? 'AI-ready ' : ''}application landing zone</text>
        <text x="30" y="64" class="azure-diagram-meta">${_svgEscape(app.strategy_label)} · ${_svgEscape(app.environment)} · ${_svgEscape(app.architecture_entry_id)}</text>
        <text x="1765" y="42" class="azure-diagram-meta" text-anchor="end">Region: ${_svgEscape(region)}</text>
        <text x="1765" y="61" class="azure-diagram-meta" text-anchor="end">Estimated: $${Number(app.monthly_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}/month</text>

        <rect class="azure-boundary" x="150" y="82" width="1610" height="${height - 145}" rx="3" />
        <rect x="150" y="82" width="1610" height="34" fill="#deecf9" />
        <text x="168" y="105" class="azure-boundary-title">Azure subscription · ${_svgEscape(region)}</text>
        <rect class="azure-landing-boundary" x="180" y="128" width="1550" height="${height - 220}" rx="3" />
        <text x="198" y="153" class="azure-boundary-title">Application landing zone · ${_svgEscape(resourceGroup)}</text>

        <g aria-label="Application users">
            <circle cx="72" cy="292" r="18" fill="#32b0d4" />
            <path d="M 38 346 C 40 320, 52 311, 72 311 C 92 311, 104 320, 106 346 Z" fill="#32b0d4" />
            <text x="72" y="370" class="azure-service-title" text-anchor="middle">Users / clients</text>
        </g>

        <rect class="azure-vnet-boundary" x="220" y="178" width="1030" height="322" rx="2" />
        <image href="${_AZURE_ICON_BASE}virtual-network.svg" x="238" y="190" width="24" height="24" />
        <text x="269" y="208" class="azure-boundary-title">Virtual network · ${_svgEscape(vnet.name || '')} · ${_svgEscape(vnet.address_space || '')}</text>
        <rect class="azure-subnet-boundary" x="248" y="225" width="245" height="245" />
        <text x="262" y="248" class="azure-subnet-title">Ingress subnet</text>
        <rect class="azure-subnet-boundary" x="515" y="225" width="330" height="245" />
        <text x="529" y="248" class="azure-subnet-title">Workload integration subnet</text>
        <rect class="azure-subnet-boundary" x="870" y="225" width="350" height="245" />
        <text x="884" y="248" class="azure-subnet-title">Private endpoints subnet</text>

        ${_architectureSection(platformBox, 'Shared platform services', 'Identity, secrets, observability, and recovery', '#8764b8')}
        ${aiReady ? _architectureSection(aiBox, `AI capability extension · ${app.ai_feasibility?.category_label || 'AI opportunity'}`, 'Proposed components from a versioned AI Feasibility Assessment', '#7c3aed') : ''}
        ${_architectureSection(workloadBox, 'Workload services', 'Assessed application and compute targets', '#0078d4')}
        ${_architectureSection(targetBox, 'Data and storage services', 'Private PaaS dependencies assessed for this application', '#008272')}

        ${flows}
        <g aria-hidden="true">
            <rect x="166" y="316" width="62" height="20" rx="3" fill="#fff" />
            <text x="197" y="330" class="azure-service-meta" text-anchor="middle">HTTPS</text>
            <rect x="482" y="316" width="92" height="20" rx="3" fill="#fff" />
            <text x="528" y="330" class="azure-service-meta" text-anchor="middle">Private ingress</text>
            <rect x="807" y="456" width="82" height="20" rx="3" fill="#fff" />
            <text x="848" y="470" class="azure-service-meta" text-anchor="middle">Private Link</text>
        </g>
        ${_azureServiceCard({id: 'application-gateway', label: 'Application Gateway with WAF', meta: 'Secure HTTPS ingress', icon: 'application-gateway.svg', title: 'Azure Application Gateway with Web Application Firewall'}, gatewayCard.x, gatewayCard.y, gatewayCard.width, gatewayCard.height)}
        ${_azureServiceCard({id: 'workload-integration', label: 'Workload VNet integration', meta: `${computeItems.length} compute service${computeItems.length === 1 ? '' : 's'}`, icon: 'virtual-network.svg', title: 'Workload virtual network integration'}, integrationCard.x, integrationCard.y, integrationCard.width, integrationCard.height)}
        ${_azureServiceCard({id: 'private-endpoints', label: 'Private endpoints', meta: `${targetItems.length} private dependenc${targetItems.length === 1 ? 'y' : 'ies'}`, icon: 'private-endpoints.svg', title: 'Azure Private Link private endpoints'}, endpointCard.x, endpointCard.y, endpointCard.width, endpointCard.height)}
        ${platformCards.map(card => _azureServiceCard(card.item, card.x, card.y, card.width, card.height)).join('')}
        ${aiCards.map(card => _azureServiceCard(card.item, card.x, card.y, card.width, card.height)).join('')}
        ${computeMarkup}
        ${targetMarkup}

        <text x="168" y="${height - 32}" class="azure-diagram-meta">Generated ${_svgEscape(generated)} · CTD catalogue ${_svgEscape(catalogueVersion)} · Diagram type: application component and network view</text>
        <text x="1715" y="${height - 32}" class="azure-diagram-meta" text-anchor="end">Official Azure icons where available · Proposed AI nodes clearly marked</text>
    </svg>`;
}

async function loadLandingZones() {
    const c = document.getElementById('landing-zone-results');
    const detail = document.getElementById('landing-zone-detail');
    const button = document.getElementById('landing-zone-generate-btn');
    const strategy = document.getElementById('landing-zone-strategy')?.value || 'paas_preferred';
    const region = document.getElementById('landing-zone-region')?.value || 'eastus';
    const aiToggle = document.getElementById('landing-zone-ai-feasibility');
    const includeAi = Boolean(aiToggle?.checked);
    if (detail) detail.style.display = 'none';
    if (button) button.disabled = true;
    c.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="text-muted mt-2">Resolving application architectures…</p></div>';
    try {
        const params = new URLSearchParams({strategy, region, include_ai: String(includeAi)});
        if (includeAi && aiToggle?.dataset.assessmentId) params.set('ai_assessment_id', aiToggle.dataset.assessmentId);
        const response = await fetch('/api/landing-zones?' + params.toString());
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Unable to generate landing zones.');
        _landingZoneData = data;

        const summary = data.summary || {};
        let html = `<div class="row g-3 mb-3">
            <div class="col-md-3"><div class="stat-card"><div class="stat-value">${summary.application_count || 0}</div><div class="stat-label">Application Landing Zones</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-info">${summary.source_member_count || 0}</div><div class="stat-label">Assessed Members</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-success">$${(summary.monthly_cost || 0).toLocaleString(undefined,{maximumFractionDigits:0})}</div><div class="stat-label">Estimated Monthly</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-primary">${summary.catalogue_entry_count || 0}</div><div class="stat-label">Catalogue Patterns</div></div></div>
        </div>${includeAi ? `<div class="alert ${summary.ai_ready_application_count ? 'alert-primary' : 'alert-warning'} small py-2"><i class="bi bi-stars me-2"></i>${summary.ai_ready_application_count || 0} application(s) have an AI-ready architecture from a persisted assessment. Incremental modeled AI budget: <strong>$${(summary.ai_monthly_cost || 0).toLocaleString(undefined,{maximumFractionDigits:0})}/month</strong>. This is not an Azure quote.</div>` : ''}
        <div class="d-flex justify-content-between align-items-center mb-2"><h6 class="mb-0">Resolved Applications</h6><span class="small text-muted">Catalogue ${esc(data.catalogue?.version || '')}</span></div>
        <div class="row g-3">`;

        for (const app of (data.applications || [])) {
            const summaryBadges = _applicationComponentBadges(app.component_summary || {});
            html += `<div class="col-md-6 col-xl-4"><div class="card bg-dark border-secondary h-100 landing-zone-card" data-landing-zone-app="${esc(app.id)}">
                <div class="card-header"><i class="bi bi-boxes me-2 text-primary"></i><strong>${esc(app.name)}</strong></div>
                <div class="card-body">
                    <div class="small text-muted mb-2">${esc(app.landing_zone?.name || '')}</div>
                    <div class="mb-2">${summaryBadges}</div>
                    <div class="d-flex flex-wrap gap-1 mb-3"><span class="badge bg-dark border">${esc(app.strategy_label)}</span><span class="badge bg-dark border">${esc(app.environment)}</span><span class="badge bg-primary">${esc(app.architecture_entry_id)}</span>${app.ai_ready ? `<span class="ai-architecture-ready-badge"><i class="bi bi-stars"></i>${esc(app.ai_feasibility?.category_label || 'AI ready')}</span>` : ''}</div>
                    <div class="d-flex justify-content-between align-items-center"><div><strong>$${(app.monthly_cost || 0).toLocaleString(undefined,{maximumFractionDigits:0})}/mo</strong>${app.ai_ready ? `<div class="small text-muted">Base $${(app.base_monthly_cost || 0).toLocaleString(undefined,{maximumFractionDigits:0})} + AI $${(app.ai_monthly_cost || 0).toLocaleString(undefined,{maximumFractionDigits:0})}</div>` : ''}</div><button class="btn btn-sm btn-outline-primary landing-zone-view-btn" type="button" data-app-id="${esc(app.id)}">View Architecture</button></div>
                </div></div></div>`;
        }
        c.innerHTML = html + '</div>';
        c.querySelectorAll('.landing-zone-view-btn').forEach(viewButton => {
            viewButton.addEventListener('click', () => renderLandingZoneArchitecture(viewButton.dataset.appId));
        });
        if ((data.applications || []).length) renderLandingZoneArchitecture(data.applications[0].id);
    } catch (e) {
        c.innerHTML = `<div class="alert alert-warning"><i class="bi bi-exclamation-triangle me-2"></i>${esc(e.message || 'Failed.')}</div>`;
    } finally {
        if (button) button.disabled = false;
    }
}

function renderLandingZoneArchitecture(applicationId) {
    const app = (_landingZoneData?.applications || []).find(item => item.id === applicationId);
    if (!app) return;

    _landingZoneCurrentApplicationId = applicationId;

    const detail = document.getElementById('landing-zone-detail');
    detail.style.display = '';
    document.getElementById('landing-zone-detail-title').textContent = app.landing_zone?.name || app.name;
    document.getElementById('landing-zone-detail-meta').textContent = `${app.strategy_label} · ${app.environment} · ${app.source_member_count} assessed members · ${app.landing_zone?.vnet?.name || ''}${app.ai_ready ? ` · AI assessment ${app.ai_feasibility?.assessment_id || ''} r${app.ai_feasibility?.assessment_version || 1}` : ''}`;
    document.getElementById('landing-zone-catalogue-entry').textContent = app.architecture_entry_id;

    const container = document.getElementById('landing-zone-canvas');
    container.innerHTML = _renderApplicationArchitectureSvg(app);
    fitLandingZoneDiagram();

    const members = app.members || [];
    const rows = members.map(member => `<tr>
        <td><span class="badge bg-dark border">${esc(member.type)}</span></td>
        <td><strong>${esc(member.name)}</strong>${member.shared ? ' <span class="badge bg-secondary">shared</span>' : ''}<div class="small text-muted">${esc(member.source_vm || member.source_engine || '')}</div></td>
        <td>${esc(member.target_service || '')}<div class="small text-muted">${esc(member.target_sku || '')}</div></td>
        <td class="text-end">$${(member.allocated_monthly_cost ?? member.monthly_cost ?? 0).toLocaleString(undefined,{maximumFractionDigits:0})}</td>
    </tr>`).join('');
    document.getElementById('landing-zone-members').innerHTML = `<table class="table table-sm table-dark-custom mb-0"><thead><tr><th>Type</th><th>Source Member</th><th>Assessed Azure Target</th><th class="text-end">Monthly</th></tr></thead><tbody>${rows}</tbody></table>`;

    document.getElementById('landing-zone-reasoning').innerHTML = (app.reasoning || []).map(reason => `<div class="mb-3"><strong>${esc(reason.title)}</strong><p class="small text-muted mb-0">${esc(reason.detail)}</p></div>`).join('');
    detail.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function fitLandingZoneDiagram() {
    const container = document.getElementById('landing-zone-canvas');
    if (!container) return;
    container.scrollTo({left: 0, top: 0, behavior: 'smooth'});
}

function _blobAsDataUrl(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

async function downloadLandingZoneSvg() {
    const source = document.querySelector('#landing-zone-canvas svg');
    if (!source || !_landingZoneCurrentApplicationId) return;
    const clone = source.cloneNode(true);
    const images = [...clone.querySelectorAll('image')];
    await Promise.all(images.map(async image => {
        const href = image.getAttribute('href');
        if (!href || href.startsWith('data:')) return;
        const response = await fetch(href);
        if (!response.ok) return;
        image.setAttribute('href', await _blobAsDataUrl(await response.blob()));
    }));
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    const xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone);
    const url = URL.createObjectURL(new Blob([xml], {type: 'image/svg+xml;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${_landingZoneCurrentApplicationId}-azure-architecture.svg`;
    link.click();
    URL.revokeObjectURL(url);
}

// ═══════════════════════════════════════════════════════════════════
//  COST OPTIMIZATION
// ═══════════════════════════════════════════════════════════════════
async function loadCostOptimization() {
    const c = document.getElementById('costopt-results');
    c.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    try {
        const d = await (await fetch('/api/cost-optimization')).json();
        const fmt = v=>'$'+(v||0).toLocaleString(undefined,{maximumFractionDigits:0});
        let h = `<div class="row g-3 mb-4">
            <div class="col-md-3"><div class="stat-card"><div class="stat-value">${fmt(d.fleet_payg_monthly)}</div><div class="stat-label">PAYG Monthly</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-success">${fmt(d.fleet_optimized_monthly)}</div><div class="stat-label">Optimized</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-primary">${d.pricing_savings_pct}%</div><div class="stat-label">Savings</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-info">${fmt(d.total_optimization_annual)}</div><div class="stat-label">Annual Total</div></div></div>
        </div>`;
        if ((d.zombies||[]).length) {
            h += `<h6 class="text-danger"><i class="bi bi-slash-circle me-2"></i>Zombie VMs (${d.zombie_vms})</h6><div class="table-responsive mb-3"><table class="table table-sm"><thead><tr><th>VM</th><th>CPU P95</th><th>SKU</th><th>Cost</th></tr></thead><tbody>`;
            for (const z of d.zombies) h+=`<tr><td>${esc(z.vm_name)}</td><td>${z.cpu_p95}%</td><td>${z.sku}</td><td>${fmt(z.monthly_cost)}/mo</td></tr>`;
            h+='</tbody></table></div>';
        }
        if ((d.right_sizing||[]).length) {
            h += `<h6 class="text-warning"><i class="bi bi-exclamation-triangle me-2"></i>Right-Sizing (${d.right_sizing_alerts})</h6><div class="table-responsive mb-3"><table class="table table-sm"><thead><tr><th>VM</th><th>Alert</th><th>Current</th><th>Recommended</th><th>Savings</th></tr></thead><tbody>`;
            for (const r of d.right_sizing) h+=`<tr><td>${esc(r.vm_name)}</td><td><span class="badge bg-${r.alert==='oversized'?'warning':'danger'}">${r.alert}</span></td><td>${r.current_sku}</td><td><strong>${r.recommended_sku}</strong></td><td class="text-success">${fmt(r.monthly_savings)}/mo</td></tr>`;
            h+='</tbody></table></div>';
        }
        c.innerHTML = h;
    } catch(e) { c.innerHTML = '<div class="alert alert-warning">Failed.</div>'; }
}

// ═══════════════════════════════════════════════════════════════════
//  IAC EXPORT
// ═══════════════════════════════════════════════════════════════════
async function generateIaC(type) {
    const c = document.getElementById('iac-results');
    const prefix = (document.getElementById('iac-prefix')||{}).value||'migrate';
    const env = (document.getElementById('iac-env')||{}).value||'prod';
    c.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary"></div><p class="mt-2">Generating '+type+'…</p></div>';
    try {
        const d = await (await fetch('/api/export/'+type,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({naming_prefix:prefix,environment:env})})).json();
        if (d.error) { c.innerHTML = '<div class="alert alert-warning">'+esc(d.error)+'</div>'; return; }
        let h = '<div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>'+d.file_count+' files generated</div>';
        const files = d.files||{};
        const names = typeof files==='object'&&!Array.isArray(files)?Object.keys(files):Array.isArray(files)?files:[];
        for (const n of names) h+='<span class="badge bg-secondary me-1 mb-1"><i class="bi bi-file-code me-1"></i>'+n+'</span>';
        const mk = type==='terraform'?'main.tf':'main.bicep';
        if (d[mk]) h+='<details class="mt-3"><summary class="text-info" style="cursor:pointer">View '+mk+'</summary><pre class="bg-dark border rounded p-3 mt-2" style="max-height:500px;overflow:auto;font-size:0.8rem"><code>'+esc(d[mk].substring(0,10000))+'</code></pre></details>';
        c.innerHTML = h;
    } catch(e) { c.innerHTML = '<div class="alert alert-danger">Failed.</div>'; }
}

// ═══════════════════════════════════════════════════════════════════
//  RUNBOOKS
// ═══════════════════════════════════════════════════════════════════
async function loadRunbooks() {
    const c = document.getElementById('runbooks-results');
    c.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    try {
        const d = await (await fetch('/api/runbooks/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
        if (d.error) { c.innerHTML = '<div class="alert alert-warning">'+esc(d.error)+'</div>'; return; }
        const pre=d.pre_migration||[],exec=d.execution||[],post=d.post_migration||[];
        let h = `<div class="row g-3 mb-4">
            <div class="col-md-4"><div class="stat-card"><div class="stat-value text-warning">${pre.length}</div><div class="stat-label">Pre-Migration</div></div></div>
            <div class="col-md-4"><div class="stat-card"><div class="stat-value text-primary">${exec.length}</div><div class="stat-label">Execution</div></div></div>
            <div class="col-md-4"><div class="stat-card"><div class="stat-value text-success">${post.length}</div><div class="stat-label">Post-Migration</div></div></div>
        </div>`;
        h += _renderChecks('Pre-Migration',pre,'pre') + _renderChecks('Execution',exec,'exec') + _renderChecks('Post-Migration',post,'post');
        c.innerHTML = h;
    } catch(e) { c.innerHTML = '<div class="alert alert-warning">Run fleet simulation first.</div>'; }
}
function _renderChecks(title,checks,pfx) {
    let h='<h6 class="mt-3 mb-2">'+title+' ('+checks.length+')</h6><div class="accordion mb-3">';
    for (const ck of checks) {
        const uid=pfx+ck.id.replace(/[^a-z0-9]/gi,'');
        const tb=ck.type==='automated'?'success':ck.type==='manual'?'secondary':'info';
        h+=`<div class="accordion-item bg-dark border-secondary"><h2 class="accordion-header"><button class="accordion-button collapsed bg-dark text-light small" type="button" data-bs-toggle="collapse" data-bs-target="#${uid}">
            <span class="badge bg-dark border me-2">${ck.id}</span><span class="badge bg-${tb} me-2">${ck.type}</span>${ck.wave?'<span class="badge bg-primary me-2">W'+ck.wave+'</span>':''}${esc(ck.name)}
        </button></h2><div class="accordion-collapse collapse" id="${uid}"><div class="accordion-body small">
            ${ck.command?'<pre class="bg-dark border rounded p-2"><code>'+esc(ck.command)+'</code></pre>':'<em class="text-muted">Manual</em>'}
            <p class="mb-1"><strong>Expected:</strong> ${esc(ck.expected||ck.validation||'')}</p>
            ${ck.remediation?'<p class="mb-0"><strong>Fix:</strong> '+esc(ck.remediation)+'</p>':''}
        </div></div></div>`;
    }
    return h+'</div>';
}

// ═══════════════════════════════════════════════════════════════════
//  EXECUTIVE REPORT
// ═══════════════════════════════════════════════════════════════════
async function loadExecutiveReport() {
    const c = document.getElementById('report-results');
    c.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    try {
        const rpt = await (await fetch('/api/reports/executive')).json();
        const s=rpt.sections||{}, fmt=v=>'$'+(v||0).toLocaleString(undefined,{maximumFractionDigits:0}), bc=s.business_case||{}, est=s.estate_overview||{};
        let h = `<div class="d-flex justify-content-between mb-3"><h5 class="mb-0">Executive Report</h5>
            <button class="btn btn-sm btn-outline-primary" onclick="downloadReportMD()"><i class="bi bi-download me-1"></i>Markdown</button></div>
        <div class="card bg-dark border-primary mb-4"><div class="card-body"><p class="mb-0">${esc(s.executive_summary||'')}</p></div></div>
        <div class="row g-3 mb-4">
            <div class="col-md-2"><div class="stat-card"><div class="stat-value">${est.total_vms||0}</div><div class="stat-label">VMs</div></div></div>
            <div class="col-md-2"><div class="stat-card"><div class="stat-value">${fmt(bc.monthly_savings)}</div><div class="stat-label">Monthly Savings</div></div></div>
            <div class="col-md-2"><div class="stat-card"><div class="stat-value">${fmt(bc.annual_savings)}</div><div class="stat-label">Annual Savings</div></div></div>
            <div class="col-md-2"><div class="stat-card"><div class="stat-value">${bc.payback_period_months||'N/A'} mo</div><div class="stat-label">Payback</div></div></div>
        </div>`;
        for (const r of (s.risk_matrix||[])) h+=`<div class="alert alert-${r.severity==='High'?'danger':r.severity==='Medium'?'warning':'info'} py-2"><strong>${r.id}:</strong> ${esc(r.title)} — ${esc(r.mitigation)}</div>`;
        h+='<h6>Recommendations</h6><ul class="list-group mb-3">';
        for (const r of (s.recommendations||[])) h+=`<li class="list-group-item bg-dark border-secondary"><span class="badge bg-${r.priority==='High'?'danger':'warning'} me-2">${r.priority}</span>${esc(r.action)}</li>`;
        h+='</ul>';
        c.innerHTML = h;
    } catch(e) { c.innerHTML = '<div class="alert alert-warning">Failed.</div>'; }
}
async function downloadReportMD() { const t=await(await fetch('/api/reports/executive?format=markdown')).text(); const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([t],{type:'text/markdown'})); a.download='migration-report.md'; a.click(); }

// ═══════════════════════════════════════════════════════════════════
//  COMPLIANCE
// ═══════════════════════════════════════════════════════════════════
async function loadCompliance() {
    const c = document.getElementById('compliance-results');
    const fw=[]; document.querySelectorAll('#compliance-frameworks input:checked').forEach(cb=>fw.push(cb.value));
    if(!fw.length){c.innerHTML='<div class="alert alert-info">Select a framework.</div>';return;}
    c.innerHTML='<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    try {
        const d = await(await fetch('/api/compliance/assess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frameworks:fw,region:(document.getElementById('compliance-region')||{}).value||'eastus'})})).json();
        let h=`<div class="row g-3 mb-4">
            <div class="col-md-4"><div class="stat-card"><div class="stat-value text-${d.overall_compliance_pct>=80?'success':d.overall_compliance_pct>=50?'warning':'danger'}">${(d.overall_compliance_pct||0).toFixed(1)}%</div><div class="stat-label">Compliance</div></div></div>
            <div class="col-md-4"><div class="stat-card"><div class="stat-value text-success">${d.overall_passed}</div><div class="stat-label">Passed</div></div></div>
            <div class="col-md-4"><div class="stat-card"><div class="stat-value text-danger">${d.overall_failed}</div><div class="stat-label">Failed</div></div></div>
        </div>`;
        for(const fw of(d.results||[])){
            h+=`<div class="card bg-dark border-secondary mb-3"><div class="card-header d-flex justify-content-between"><strong>${esc(fw.framework)}</strong><span class="badge bg-${fw.compliance_pct>=80?'success':'warning'}">${fw.compliance_pct}%</span></div>
            <div class="card-body"><div class="table-responsive"><table class="table table-sm"><thead><tr><th>Control</th><th>Status</th><th>Detail</th></tr></thead><tbody>`;
            for(const ck of(fw.checks||[])){const sb=ck.status==='Pass'?'success':ck.status==='Fail'?'danger':'secondary';
                h+=`<tr><td><small class="text-muted">${ck.id}</small> ${esc(ck.control)}</td><td><span class="badge bg-${sb}">${ck.status}</span></td><td class="small">${esc(ck.detail)}${ck.remediation?'<br><em class="text-info">'+esc(ck.remediation)+'</em>':''}</td></tr>`;}
            h+='</tbody></table></div></div></div>';
        }
        c.innerHTML=h;
    } catch(e){c.innerHTML='<div class="alert alert-warning">Failed.</div>';}
}

// ═══════════════════════════════════════════════════════════════════
//  MIGRATION TRACKER
// ═══════════════════════════════════════════════════════════════════
async function loadMigrationTracker() {
    const c=document.getElementById('tracker-results'); if(!c)return;
    c.innerHTML='<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    try {
        const d=await(await fetch('/api/migration/progress')).json();
        const st=d.state_counts||{};
        let h=`<div class="row g-3 mb-4">
            <div class="col-md-3"><div class="stat-card"><div class="stat-value">${d.total_vms||0}</div><div class="stat-label">Tracked</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-success">${d.migrated||0}</div><div class="stat-label">Migrated</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-primary">${d.progress_pct||0}%</div><div class="stat-label">Progress</div></div></div>
            <div class="col-md-3"><div class="stat-card"><div class="stat-value text-danger">${d.blocker_count||0}</div><div class="stat-label">Blockers</div></div></div>
        </div><div class="progress mb-4" style="height:24px"><div class="progress-bar bg-success" style="width:${d.progress_pct||0}%">${d.progress_pct||0}%</div></div>`;
        const colors={'Not Started':'secondary','Planned':'info','Replicating':'primary','Test Failover':'warning','Migrated':'success','Validated':'success','Decommissioned':'dark'};
        h+='<div class="row g-2 mb-4">'; for(const[s,n]of Object.entries(st)){if(n>0)h+='<div class="col-auto"><span class="badge bg-'+(colors[s]||'secondary')+' fs-6">'+s+': '+n+'</span></div>';} h+='</div>';
        if(d.wave_progress&&d.wave_progress.length){h+='<h6>Wave Progress</h6><div class="table-responsive"><table class="table table-sm"><thead><tr><th>Wave</th><th>VMs</th><th>Migrated</th><th>Progress</th></tr></thead><tbody>';
            for(const w of d.wave_progress)h+='<tr><td>Wave '+w.wave+'</td><td>'+w.vm_count+'</td><td>'+w.migrated+'</td><td><div class="progress" style="height:16px"><div class="progress-bar bg-success" style="width:'+w.progress_pct+'%">'+w.progress_pct+'%</div></div></td></tr>';
            h+='</tbody></table></div>';}
        c.innerHTML=h;
    } catch(e){c.innerHTML='<div class="alert alert-warning">Failed.</div>';}
}

// ═══════════════════════════════════════════════════════════════════
//  NSG, TAGGING, POST-MIGRATION, SNAPSHOTS
// ═══════════════════════════════════════════════════════════════════
async function loadNsgRules(){const c=document.getElementById('nsg-results');c.innerHTML='<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';try{const d=await(await fetch('/api/nsg-rules')).json();if(d.error){c.innerHTML='<div class="alert alert-warning">'+esc(d.error)+'</div>';return;}let h=`<div class="row g-3 mb-4"><div class="col-md-4"><div class="stat-card"><div class="stat-value">${d.subnet_count}</div><div class="stat-label">Subnets</div></div></div><div class="col-md-4"><div class="stat-card"><div class="stat-value">${d.total_rules}</div><div class="stat-label">Total Rules</div></div></div><div class="col-md-4"><div class="stat-card"><div class="stat-value text-info">${d.dependency_rules}</div><div class="stat-label">From Dependencies</div></div></div></div>`;for(const nsg of(d.nsgs||[])){h+='<details class="mb-2"><summary class="text-info" style="cursor:pointer"><strong>'+esc(nsg.nsg_name)+'</strong> — '+nsg.rule_count+' rules</summary><div class="table-responsive mt-2"><table class="table table-sm"><thead><tr><th>Pri</th><th>Name</th><th>Access</th><th>Port</th></tr></thead><tbody>';for(const r of nsg.rules)h+='<tr class="'+(r.access==='Deny'?'table-danger':'')+'"><td>'+r.priority+'</td><td class="small">'+esc(r.name)+'</td><td>'+r.access+'</td><td>'+r.destination_port+'</td></tr>';h+='</tbody></table></div></details>';}c.innerHTML=h;}catch(e){c.innerHTML='<div class="alert alert-warning">Generate topology first.</div>';}}

async function loadTagging(){const c=document.getElementById('tagging-results');c.innerHTML='<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';try{const d=await(await fetch('/api/tags/strategy')).json();let h=`<div class="row g-3 mb-4"><div class="col-md-3"><div class="stat-card"><div class="stat-value">${d.vm_count}</div><div class="stat-label">VMs</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-value text-primary">${d.tag_key_count}</div><div class="stat-label">Tag Keys</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-value">${(d.environment_values||[]).length}</div><div class="stat-label">Environments</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-value">${(d.cost_center_values||[]).length}</div><div class="stat-label">Cost Centers</div></div></div></div>`;h+='<h6>Tag Keys</h6><div class="mb-3">';for(const k of(d.tag_keys_used||[]))h+='<span class="badge bg-primary me-1 mb-1">'+k+'</span>';h+='</div>';if(d.terraform_locals)h+='<h6>Terraform (sample)</h6><pre class="bg-dark border rounded p-3 small"><code>'+esc(d.terraform_locals)+'</code></pre>';h+='<h6 class="mt-3">Sample</h6><div class="table-responsive"><table class="table table-sm"><thead><tr><th>VM</th><th>Tags</th></tr></thead><tbody>';for(const vm of(d.per_vm||[]).slice(0,10))h+='<tr><td>'+esc(vm.vm_name)+'</td><td class="small">'+Object.entries(vm.tags||{}).map(([k,v])=>'<span class="badge bg-dark border me-1">'+k+'='+esc(v)+'</span>').join('')+'</td></tr>';h+='</tbody></table></div>';c.innerHTML=h;}catch(e){c.innerHTML='<div class="alert alert-warning">Failed.</div>';}}

async function loadPostMigrationChecks(){const c=document.getElementById('postval-results');c.innerHTML='<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';try{const d=await(await fetch('/api/validation/post-migration',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();const s=d.summary||{};let h=`<div class="row g-3 mb-4"><div class="col-md-3"><div class="stat-card"><div class="stat-value">${s.total_checks||0}</div><div class="stat-label">Total</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-value text-success">${s.health_checks||0}</div><div class="stat-label">Health</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-value text-primary">${s.connectivity_checks||0}</div><div class="stat-label">Connectivity</div></div></div><div class="col-md-3"><div class="stat-card"><div class="stat-value text-warning">${s.perf_checks||0}</div><div class="stat-label">Performance</div></div></div></div>`;if((d.connectivity_checks||[]).length){h+='<h6>Connectivity</h6><div class="table-responsive"><table class="table table-sm"><thead><tr><th>Source</th><th>Target</th><th>Port</th></tr></thead><tbody>';for(const ck of d.connectivity_checks.slice(0,15))h+='<tr><td>'+esc(ck.source_vm)+'</td><td>'+esc(ck.target_vm)+'</td><td>'+ck.port+'</td></tr>';h+='</tbody></table></div>';}c.innerHTML=h;}catch(e){c.innerHTML='<div class="alert alert-warning">Failed.</div>';}}

async function loadSnapshots(){const c=document.getElementById('snapshots-list');if(!c)return;try{const d=await(await fetch('/api/snapshots')).json();const snaps=d.snapshots||[];if(!snaps.length){c.innerHTML='<p class="text-muted">No snapshots.</p>';return;}let h='<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Name</th><th>Created</th><th>VMs</th><th></th></tr></thead><tbody>';for(const s of snaps)h+='<tr><td>'+esc(s.name)+'</td><td class="small">'+s.created_at+'</td><td>'+s.vm_count+'</td><td><button class="btn btn-sm btn-outline-warning" onclick="restoreSnap(\''+s.id+'\')"><i class="bi bi-arrow-counterclockwise"></i></button></td></tr>';h+='</tbody></table></div>';c.innerHTML=h;}catch(e){c.innerHTML='<p class="text-muted">Failed.</p>';}}
async function saveSnapshot(){const n=document.getElementById('snapshot-name');if(!n||!n.value)return;await fetch('/api/snapshots',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n.value,description:''})});n.value='';loadSnapshots();}
async function restoreSnap(name){if(!confirm('Restore "'+name+'"?'))return;await fetch('/api/snapshots/'+encodeURIComponent(name)+'/restore',{method:'POST'});location.reload();}

// ═══════════════════════════════════════════════════════════════════
function esc(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
