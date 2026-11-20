/* Risk Heatmap — fleet-wide migration risk visualization */

function _bandColor(band) {
    if (band === 'green') return '#d1fae5';
    if (band === 'yellow') return '#fef3c7';
    if (band === 'red') return '#fee2e2';
    return '#f3f4f6';
}

function _bandTextColor(band) {
    if (band === 'green') return '#065f46';
    if (band === 'yellow') return '#92400e';
    if (band === 'red') return '#991b1b';
    return '#374151';
}

function _badgeClass(band) {
    if (band === 'green') return 'bg-success';
    if (band === 'yellow') return 'bg-warning text-dark';
    if (band === 'red') return 'bg-danger';
    return 'bg-secondary';
}

const _factorLabels = {
    dependency_count: 'Deps',
    os_eol: 'OS EOL',
    workload_complexity: 'Wkload',
    performance_sensitivity: 'Perf',
    compliance_scope: 'Compliance',
    data_volume: 'Data Vol',
};

let _heatmapData = null;
let _sortCol = 'composite_score';
let _sortAsc = false;

async function loadRiskHeatmap() {
    const grid = document.getElementById('risk-heatmap-grid');
    grid.innerHTML = '<p class="text-muted"><i class="bi bi-hourglass-split me-1"></i>Computing risk scores...</p>';
    try {
        const resp = await fetch('/api/risk/heatmap?sort_by=composite_score&sort_order=desc');
        if (!resp.ok) throw new Error('API error ' + resp.status);
        _heatmapData = await resp.json();
        _renderTop10(_heatmapData);
        _renderHeatmapGrid(_heatmapData);
    } catch (e) {
        grid.innerHTML = '<div class="alert alert-danger">Failed to load risk heatmap: ' + e.message + '</div>';
    }
}

function _renderTop10(data) {
    const panel = document.getElementById('risk-top10-panel');
    const topVms = data.top_risky || [];
    if (!topVms.length) { panel.innerHTML = ''; return; }

    const dist = data.band_distribution || {};
    let html = '<div class="mb-3">';
    html += '<div class="d-flex align-items-center gap-3 mb-2">';
    html += '<span class="badge bg-success">' + (dist.green || 0) + ' Low Risk</span>';
    html += '<span class="badge bg-warning text-dark">' + (dist.yellow || 0) + ' Medium Risk</span>';
    html += '<span class="badge bg-danger">' + (dist.red || 0) + ' High Risk</span>';
    html += '<span class="text-muted ms-2">Total: ' + (data.total_vms || 0) + ' VMs</span>';
    html += '</div>';
    html += '<h6 class="mb-2"><i class="bi bi-exclamation-triangle me-1"></i>Top ' + topVms.length + ' Riskiest VMs</h6>';
    html += '<div class="row g-2">';
    for (const vm of topVms) {
        const badge = _badgeClass(vm.composite_band);
        const mitigation = (vm.mitigations && vm.mitigations.length) ? vm.mitigations[0].action : '';
        const dominantLabel = _factorLabels[vm.dominant_factor] || vm.dominant_factor;
        html += '<div class="col-md-6 col-lg-4"><div class="card border-0 shadow-sm">';
        html += '<div class="card-body p-2">';
        html += '<div class="d-flex justify-content-between align-items-center">';
        html += '<strong class="text-truncate" style="max-width:160px" title="' + vm.vm_name + '">' + vm.vm_name + '</strong>';
        html += '<span class="badge ' + badge + '">' + vm.composite_score + '</span>';
        html += '</div>';
        html += '<small class="text-muted">Dominant: ' + dominantLabel + '</small>';
        if (mitigation) html += '<br><small class="text-muted fst-italic">' + mitigation + '</small>';
        html += '</div></div></div>';
    }
    html += '</div></div>';
    panel.innerHTML = html;
}

function _renderHeatmapGrid(data) {
    const grid = document.getElementById('risk-heatmap-grid');
    const vmScores = data.vm_scores || [];
    if (!vmScores.length) {
        grid.innerHTML = '<div class="alert alert-info">' + (data.message || 'No VMs to display.') + '</div>';
        return;
    }

    const factors = data.factor_names || [];

    let html = '<div class="table-responsive"><table class="table table-sm table-hover align-middle" style="font-size:0.85rem">';
    html += '<thead class="table-light"><tr>';
    html += '<th style="cursor:pointer" onclick="_sortHeatmap(\'vm_name\')">VM Name ' + _sortIcon('vm_name') + '</th>';
    for (const f of factors) {
        const label = _factorLabels[f] || f;
        html += '<th class="text-center" style="cursor:pointer" onclick="_sortHeatmap(\'' + f + '\')">' + label + ' ' + _sortIcon(f) + '</th>';
    }
    html += '<th class="text-center" style="cursor:pointer" onclick="_sortHeatmap(\'composite_score\')">Composite ' + _sortIcon('composite_score') + '</th>';
    html += '</tr></thead><tbody>';

    for (const vm of vmScores) {
        html += '<tr style="cursor:pointer" onclick="_showVmDetail(\'' + vm.vm_name.replace(/'/g, "\\'") + '\')">';
        html += '<td class="fw-bold text-truncate" style="max-width:200px" title="' + vm.vm_name + '">' + vm.vm_name + '</td>';
        for (const f of factors) {
            const factor = (vm.factors || []).find(x => x.name === f);
            const score = factor ? factor.score : 0;
            const band = factor ? factor.band : 'green';
            html += '<td class="text-center" style="background:' + _bandColor(band) + ';color:' + _bandTextColor(band) + '">' + score + '</td>';
        }
        const cBand = vm.composite_band;
        html += '<td class="text-center fw-bold" style="background:' + _bandColor(cBand) + ';color:' + _bandTextColor(cBand) + '">' + vm.composite_score + '</td>';
        html += '</tr>';
    }
    html += '</tbody></table></div>';
    grid.innerHTML = html;
}

function _sortIcon(col) {
    if (_sortCol !== col) return '<i class="bi bi-arrow-down-up text-muted" style="font-size:0.7em"></i>';
    return _sortAsc
        ? '<i class="bi bi-sort-up" style="font-size:0.7em"></i>'
        : '<i class="bi bi-sort-down" style="font-size:0.7em"></i>';
}

function _sortHeatmap(col) {
    if (!_heatmapData) return;
    if (_sortCol === col) { _sortAsc = !_sortAsc; } else { _sortCol = col; _sortAsc = false; }

    const vms = _heatmapData.vm_scores || [];
    vms.sort((a, b) => {
        let va, vb;
        if (col === 'vm_name') {
            va = a.vm_name; vb = b.vm_name;
            return _sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        } else if (col === 'composite_score') {
            va = a.composite_score; vb = b.composite_score;
        } else {
            va = ((a.factors || []).find(f => f.name === col) || {}).score || 0;
            vb = ((b.factors || []).find(f => f.name === col) || {}).score || 0;
        }
        return _sortAsc ? va - vb : vb - va;
    });
    _renderHeatmapGrid(_heatmapData);
}

async function _showVmDetail(vmName) {
    const panel = document.getElementById('risk-detail-panel');
    panel.style.display = 'block';
    panel.innerHTML = '<p class="text-muted">Loading details for ' + vmName + '...</p>';
    try {
        const resp = await fetch('/api/risk/score/' + encodeURIComponent(vmName));
        if (!resp.ok) throw new Error('VM not found');
        const data = await resp.json();
        let html = '<div class="card mt-3 shadow-sm"><div class="card-body">';
        html += '<div class="d-flex justify-content-between align-items-center mb-2">';
        html += '<h6 class="mb-0"><i class="bi bi-shield-exclamation me-1"></i>Risk Detail: ' + data.vm_name + '</h6>';
        html += '<span class="badge ' + _badgeClass(data.composite_band) + ' fs-6">Score: ' + data.composite_score + '</span>';
        html += '<button type="button" class="btn-close ms-2" onclick="document.getElementById(\'risk-detail-panel\').style.display=\'none\'"></button>';
        html += '</div>';

        html += '<table class="table table-sm mb-2" style="font-size:0.85rem"><thead><tr>';
        html += '<th>Factor</th><th>Raw Value</th><th class="text-center">Score</th><th class="text-center">Weight</th><th class="text-center">Weighted</th><th class="text-center">Band</th>';
        html += '</tr></thead><tbody>';
        for (const f of data.factors || []) {
            const label = _factorLabels[f.name] || f.name;
            html += '<tr>';
            html += '<td>' + label + (!f.data_available ? ' <i class="bi bi-exclamation-circle text-warning" title="No data"></i>' : '') + '</td>';
            html += '<td class="text-muted">' + f.raw_value + '</td>';
            html += '<td class="text-center" style="background:' + _bandColor(f.band) + ';color:' + _bandTextColor(f.band) + '">' + f.score + '</td>';
            html += '<td class="text-center">' + (f.weight * 100).toFixed(0) + '%</td>';
            html += '<td class="text-center">' + f.weighted_score.toFixed(1) + '</td>';
            html += '<td class="text-center"><span class="badge ' + _badgeClass(f.band) + '">' + f.band + '</span></td>';
            html += '</tr>';
        }
        html += '</tbody></table>';

        if (data.mitigations && data.mitigations.length) {
            html += '<h6 class="mt-2 mb-1"><i class="bi bi-lightbulb me-1"></i>Mitigation Suggestions</h6><ul class="mb-0" style="font-size:0.85rem">';
            for (const m of data.mitigations) {
                const fLabel = _factorLabels[m.factor] || m.factor;
                html += '<li><span class="badge ' + _badgeClass(m.severity) + ' me-1">' + fLabel + '</span>' + m.action + '</li>';
            }
            html += '</ul>';
        }
        html += '</div></div>';
        panel.innerHTML = html;
    } catch (e) {
        panel.innerHTML = '<div class="alert alert-warning mt-3">Could not load risk detail: ' + e.message + '</div>';
    }
}
