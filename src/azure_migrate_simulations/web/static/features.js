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
async function loadApplicationGroups() {
    const c = document.getElementById('appgroups-results');
    c.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    try {
        const d = await (await fetch('/api/applications')).json();
        let h = `<p class="text-muted">${d.application_count} groups</p><div class="row g-3">`;
        for (const a of (d.applications||[])) {
            const cc = a.complexity_score>=7?'danger':a.complexity_score>=4?'warning':'success';
            h += `<div class="col-md-6 col-lg-4"><div class="card bg-dark border-secondary h-100">
                <div class="card-header d-flex justify-content-between"><strong>${esc(a.name)}</strong><span class="badge bg-${cc}">C:${a.complexity_score}/10</span></div>
                <div class="card-body"><span class="badge bg-primary me-1">${a.vm_count} VMs</span><span class="badge bg-secondary me-1">${a.dependency_count} deps</span><span class="badge bg-info me-1">${a.criticality}</span>
                <div class="text-muted small mt-2">$${(a.total_monthly_cost||0).toLocaleString()}/mo</div>
                <details class="mt-1"><summary class="small text-info" style="cursor:pointer">VMs</summary><ul class="list-unstyled small mt-1">${(a.vms||[]).map(v=>'<li>'+esc(v.name)+'</li>').join('')}</ul></details>
                </div></div></div>`;
        }
        c.innerHTML = h+'</div>';
    } catch(e) { c.innerHTML = '<div class="alert alert-warning">Failed.</div>'; }
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
