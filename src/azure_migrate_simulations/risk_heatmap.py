"""Migration Risk Heatmap — composite risk scoring for discovered VMs.

Computes a weighted risk score (0-100) per VM across six factors:
dependency count, OS EOL status, workload complexity, performance
sensitivity, compliance scope, and data volume.  Produces a fleet-wide
heatmap matrix and identifies the top-10 riskiest VMs with mitigation
suggestions.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date
from typing import Any

from azure_migrate_simulations.models import (
    MitigationAction,
    RiskBand,
    RiskFactor,
    RiskFactorName,
    RiskHeatmap,
    RiskScore,
)
from azure_migrate_simulations.vulnerability_sla import _match_os

# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    RiskFactorName.DEPENDENCY_COUNT.value: 0.15,
    RiskFactorName.OS_EOL.value: 0.25,
    RiskFactorName.WORKLOAD_COMPLEXITY.value: 0.20,
    RiskFactorName.PERFORMANCE_SENSITIVITY.value: 0.10,
    RiskFactorName.COMPLIANCE_SCOPE.value: 0.20,
    RiskFactorName.DATA_VOLUME.value: 0.10,
}

# Compliance-related tag patterns (case-insensitive)
_COMPLIANCE_PATTERNS = re.compile(
    r"pci|hipaa|sox|gdpr|fedramp|compliance|regulated|phi|pii|itar|nist",
    re.IGNORECASE,
)

# Mitigation lookup: (factor_name, band) -> list of suggestions
_MITIGATION_TABLE: dict[str, list[dict[str, Any]]] = {
    RiskFactorName.DEPENDENCY_COUNT.value: [
        {
            "action": "Reduce dependencies by extracting shared services into independent VMs or PaaS",
            "expected_risk_reduction": 10,
        },
        {
            "action": "Use wave planning to group dependent VMs for coordinated migration",
            "expected_risk_reduction": 8,
        },
    ],
    RiskFactorName.OS_EOL.value: [
        {
            "action": "Upgrade OS to a supported version before migration, or leverage Azure Extended Security Updates (ESU)",
            "expected_risk_reduction": 25,
        },
    ],
    RiskFactorName.WORKLOAD_COMPLEXITY.value: [
        {
            "action": "Plan a phased migration: migrate the database to Azure PaaS first, then redirect application connections",
            "expected_risk_reduction": 15,
        },
        {
            "action": "Run a test migration to validate schema compatibility and performance characteristics",
            "expected_risk_reduction": 10,
        },
    ],
    RiskFactorName.PERFORMANCE_SENSITIVITY.value: [
        {
            "action": "Enable Azure Migrate replication to measure actual Azure disk IOPS before cutover",
            "expected_risk_reduction": 8,
        },
        {
            "action": "Consider Premium SSD or Ultra Disk for high-IOPS workloads",
            "expected_risk_reduction": 5,
        },
    ],
    RiskFactorName.COMPLIANCE_SCOPE.value: [
        {
            "action": "Engage compliance team for pre-migration audit; deploy to Azure landing zone with regulatory controls",
            "expected_risk_reduction": 15,
        },
        {
            "action": "Document data residency requirements and select an Azure region with the required certifications",
            "expected_risk_reduction": 10,
        },
    ],
    RiskFactorName.DATA_VOLUME.value: [
        {
            "action": "Use Azure Data Box or offline transfer for disks >2TB; enable incremental replication for smaller volumes",
            "expected_risk_reduction": 8,
        },
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_band(score: int) -> str:
    """Map a score (0-100) to a color band string."""
    if score <= 30:
        return RiskBand.GREEN.value
    if score <= 60:
        return RiskBand.YELLOW.value
    return RiskBand.RED.value


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Individual factor scorers
# ---------------------------------------------------------------------------


def _score_dependency_count(
    vm_name: str,
    workload_data: dict,
    enrichment_data: dict,
    fleet_max_deps: int,
    weight: float,
) -> RiskFactor:
    """Score based on cross-VM dependency count (fleet-relative)."""
    deps: set[str] = set()

    # Source 1: WorkloadDependency edges
    for dep in workload_data.get("dependencies", []):
        src = dep.get("source_vm", "")
        tgt = dep.get("target_vm", "")
        if src == vm_name and tgt and tgt != vm_name:
            deps.add(tgt)
        elif tgt == vm_name and src and src != vm_name:
            deps.add(src)

    # Source 2: VMWorkloads established connections
    for wl in workload_data.get("workloads", []):
        if wl.get("vm_name") == vm_name:
            for conn in wl.get("established_connections", []):
                remote = conn.get("remote_vm", "") or conn.get("remote_host", "")
                if remote and remote != vm_name:
                    deps.add(remote)

    # Source 3: Enrichment dependencies (supplementary)
    for key, enrichment in enrichment_data.items():
        if isinstance(enrichment, dict) and enrichment.get("entity_name") == vm_name:
            for d in enrichment.get("dependencies", []):
                if d and d != vm_name:
                    deps.add(d)

    dep_count = len(deps)
    raw_score = _clamp(round((dep_count / max(fleet_max_deps, 1)) * 100))
    band = _get_band(raw_score)

    return RiskFactor(
        name=RiskFactorName.DEPENDENCY_COUNT.value,
        raw_value=f"{dep_count} dependencies",
        score=raw_score,
        weight=weight,
        weighted_score=round(raw_score * weight, 2),
        band=band,
        data_available=True,
    )


def _score_os_eol(vm: dict, weight: float) -> RiskFactor:
    """Score based on OS end-of-life status. EOL = 100, non-EOL = 0."""
    guest_os = vm.get("guest_os", "")
    if not guest_os:
        return RiskFactor(
            name=RiskFactorName.OS_EOL.value,
            raw_value="Unknown OS",
            score=15,
            weight=weight,
            weighted_score=round(15 * weight, 2),
            band=_get_band(15),
            data_available=False,
        )

    info = _match_os(guest_os, date.today())
    severity = info.get("severity", "unknown")
    eol_date = info.get("eol_date", "")
    normalized = info.get("normalized_os", guest_os)

    if severity in ("critical", "high"):
        raw_score = 100
        raw_value = f"EOL: {eol_date} ({normalized})"
    elif severity == "warning":
        raw_score = 50
        raw_value = f"Approaching EOL: {eol_date} ({normalized})"
    elif severity == "unknown":
        raw_score = 15
        raw_value = f"Unverified: {normalized}"
    else:
        raw_score = 0
        raw_value = f"Supported ({normalized})"

    return RiskFactor(
        name=RiskFactorName.OS_EOL.value,
        raw_value=raw_value,
        score=raw_score,
        weight=weight,
        weighted_score=round(raw_score * weight, 2),
        band=_get_band(raw_score),
        data_available=severity != "unknown",
    )


def _score_workload_complexity(
    vm_name: str, workload_data: dict, weight: float
) -> RiskFactor:
    """Score based on detected workload type. Databases = high, orchestrators = medium, webapps = low."""
    max_score = 0
    best_label = "No workload detected"

    for wl in workload_data.get("workloads", []):
        if wl.get("vm_name") != vm_name:
            continue

        # Databases — highest complexity
        for db in wl.get("databases", []):
            engine = db.get("engine", "Unknown")
            edition = db.get("edition", "")
            size_gb = db.get("total_size_gb", 0) or db.get("size_mb", 0) / 1024
            base = 80
            if edition and "enterprise" in str(edition).lower():
                base = 95
            if size_gb > 100:
                base = min(100, base + 5)
            if base > max_score:
                max_score = base
                size_str = f"{size_gb:.0f} GB" if size_gb else ""
                ed_str = f" {edition}" if edition else ""
                best_label = f"{engine}{ed_str} ({size_str})" if size_str else f"{engine}{ed_str}"

        # Orchestrators — medium-high
        for orch in wl.get("orchestrators", []):
            score = 65
            if score > max_score:
                max_score = score
                best_label = f"{orch.get('type', 'Orchestrator')} ({orch.get('role', 'node')})"

        # Container runtimes — medium
        for cr in wl.get("container_runtimes", []):
            running = cr.get("running_containers", 0)
            score = 50 if running > 0 else 35
            if score > max_score:
                max_score = score
                best_label = f"{cr.get('runtime', 'Container')} ({running} containers)"

        # Web apps — low
        for wa in wl.get("web_apps", []):
            score = 25
            if score > max_score:
                max_score = score
                best_label = f"{wa.get('runtime', 'WebApp')} ({wa.get('framework', '')})"

    has_data = max_score > 0
    return RiskFactor(
        name=RiskFactorName.WORKLOAD_COMPLEXITY.value,
        raw_value=best_label,
        score=_clamp(max_score),
        weight=weight,
        weighted_score=round(_clamp(max_score) * weight, 2),
        band=_get_band(_clamp(max_score)),
        data_available=has_data,
    )


def _score_performance_sensitivity(
    vm: dict, fleet_iops_p75: float, weight: float
) -> RiskFactor:
    """Score based on IOPS. High IOPS relative to fleet P75 = higher risk."""
    perf = vm.get("perf", {}) or {}

    # Priority: historical P95, then realtime sum
    iops = perf.get("disk_iops_p95", 0) or 0
    if not iops:
        read = perf.get("disk_iops_read", 0) or 0
        write = perf.get("disk_iops_write", 0) or 0
        iops = read + write

    if not iops:
        return RiskFactor(
            name=RiskFactorName.PERFORMANCE_SENSITIVITY.value,
            raw_value="No perf data",
            score=0,
            weight=weight,
            weighted_score=0.0,
            band=_get_band(0),
            data_available=False,
        )

    if fleet_iops_p75 > 0:
        raw_score = _clamp(round((iops / fleet_iops_p75) * 75))
    else:
        raw_score = 0

    return RiskFactor(
        name=RiskFactorName.PERFORMANCE_SENSITIVITY.value,
        raw_value=f"P95 IOPS: {iops:.0f} (fleet 75th pctl: {fleet_iops_p75:.0f})",
        score=raw_score,
        weight=weight,
        weighted_score=round(raw_score * weight, 2),
        band=_get_band(raw_score),
        data_available=True,
    )


def _score_compliance_scope(
    vm: dict, enrichment_data: dict, weight: float
) -> RiskFactor:
    """Score based on compliance/regulatory tags."""
    matched_tags: list[str] = []

    # Source 1: VM tags
    for key, val in (vm.get("tags") or {}).items():
        combined = f"{key} {val}"
        if _COMPLIANCE_PATTERNS.search(combined):
            matched_tags.append(val if val else key)

    # Source 2: Enrichment tags
    vm_name = vm.get("name", "")
    for _key, enrichment in enrichment_data.items():
        if isinstance(enrichment, dict) and enrichment.get("entity_name") == vm_name:
            for tk, tv in (enrichment.get("tags") or {}).items():
                combined = f"{tk} {tv}"
                if _COMPLIANCE_PATTERNS.search(combined):
                    matched_tags.append(tv if tv else tk)

    if not matched_tags:
        return RiskFactor(
            name=RiskFactorName.COMPLIANCE_SCOPE.value,
            raw_value="No compliance tags",
            score=0,
            weight=weight,
            weighted_score=0.0,
            band=_get_band(0),
            data_available=True,
        )

    unique_tags = sorted(set(matched_tags))
    # More frameworks = higher risk; cap at 100
    raw_score = _clamp(min(100, 40 + len(unique_tags) * 20))
    return RiskFactor(
        name=RiskFactorName.COMPLIANCE_SCOPE.value,
        raw_value=", ".join(unique_tags),
        score=raw_score,
        weight=weight,
        weighted_score=round(raw_score * weight, 2),
        band=_get_band(raw_score),
        data_available=True,
    )


def _score_data_volume(
    vm: dict, fleet_max_disk_gb: float, weight: float
) -> RiskFactor:
    """Score based on total provisioned disk size (fleet-relative)."""
    disk_gb = vm.get("total_disk_gb", 0) or 0
    if fleet_max_disk_gb > 0:
        raw_score = _clamp(round((disk_gb / fleet_max_disk_gb) * 100))
    else:
        raw_score = 0

    return RiskFactor(
        name=RiskFactorName.DATA_VOLUME.value,
        raw_value=f"{disk_gb:.0f} GB (fleet max: {fleet_max_disk_gb:.0f} GB)",
        score=raw_score,
        weight=weight,
        weighted_score=round(raw_score * weight, 2),
        band=_get_band(raw_score),
        data_available=True,
    )


# ---------------------------------------------------------------------------
# Mitigation engine
# ---------------------------------------------------------------------------


def _suggest_mitigations(factors: list[RiskFactor]) -> list[MitigationAction]:
    """Generate mitigation suggestions for factors scoring above 30."""
    mitigations: list[MitigationAction] = []
    for f in factors:
        if f.score <= 30:
            continue
        band = _get_band(f.score)
        for sug in _MITIGATION_TABLE.get(f.name, []):
            mitigations.append(
                MitigationAction(
                    factor=f.name,
                    severity=band,
                    action=sug["action"],
                    expected_risk_reduction=sug["expected_risk_reduction"],
                )
            )
    return mitigations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_risk_score(
    vm: dict,
    workload_data: dict,
    enrichment_data: dict,
    fleet_max_deps: int,
    fleet_iops_p75: float,
    fleet_max_disk_gb: float,
    weights: dict[str, float] | None = None,
) -> RiskScore:
    """Compute the composite risk score for a single VM."""
    w = weights or DEFAULT_WEIGHTS

    factors = [
        _score_dependency_count(
            vm.get("name", ""), workload_data, enrichment_data,
            fleet_max_deps, w.get(RiskFactorName.DEPENDENCY_COUNT.value, 0.15),
        ),
        _score_os_eol(vm, w.get(RiskFactorName.OS_EOL.value, 0.25)),
        _score_workload_complexity(
            vm.get("name", ""), workload_data,
            w.get(RiskFactorName.WORKLOAD_COMPLEXITY.value, 0.20),
        ),
        _score_performance_sensitivity(
            vm, fleet_iops_p75,
            w.get(RiskFactorName.PERFORMANCE_SENSITIVITY.value, 0.10),
        ),
        _score_compliance_scope(
            vm, enrichment_data,
            w.get(RiskFactorName.COMPLIANCE_SCOPE.value, 0.20),
        ),
        _score_data_volume(
            vm, fleet_max_disk_gb,
            w.get(RiskFactorName.DATA_VOLUME.value, 0.10),
        ),
    ]

    composite = _clamp(round(sum(f.weighted_score for f in factors)))
    mitigations = _suggest_mitigations(factors)

    # Dominant factor = highest weighted_score
    dominant = max(factors, key=lambda f: f.weighted_score)

    return RiskScore(
        vm_name=vm.get("name", ""),
        composite_score=composite,
        composite_band=_get_band(composite),
        factors=factors,
        mitigations=mitigations,
        dominant_factor=dominant.name,
    )


def _compute_fleet_stats(
    vms: list[dict],
    workload_data: dict,
    enrichment_data: dict,
) -> tuple[int, float, float]:
    """Compute fleet-level statistics needed for relative scoring.

    Returns (max_deps, iops_p75, max_disk_gb).
    """
    # Max dependency count across fleet
    dep_counts: list[int] = []
    for vm in vms:
        vm_name = vm.get("name", "")
        deps: set[str] = set()
        for dep in workload_data.get("dependencies", []):
            src = dep.get("source_vm", "")
            tgt = dep.get("target_vm", "")
            if src == vm_name and tgt and tgt != vm_name:
                deps.add(tgt)
            elif tgt == vm_name and src and src != vm_name:
                deps.add(src)
        for wl in workload_data.get("workloads", []):
            if wl.get("vm_name") == vm_name:
                for conn in wl.get("established_connections", []):
                    remote = conn.get("remote_vm", "") or conn.get("remote_host", "")
                    if remote and remote != vm_name:
                        deps.add(remote)
        dep_counts.append(len(deps))

    max_deps = max(dep_counts) if dep_counts else 1

    # IOPS P75 across fleet
    all_iops: list[float] = []
    for vm in vms:
        perf = vm.get("perf", {}) or {}
        iops = perf.get("disk_iops_p95", 0) or 0
        if not iops:
            iops = (perf.get("disk_iops_read", 0) or 0) + (
                perf.get("disk_iops_write", 0) or 0
            )
        if iops > 0:
            all_iops.append(iops)

    if all_iops:
        all_iops.sort()
        idx = int(len(all_iops) * 0.75)
        iops_p75 = all_iops[min(idx, len(all_iops) - 1)]
    else:
        iops_p75 = 0.0

    # Max disk
    max_disk = max((vm.get("total_disk_gb", 0) or 0 for vm in vms), default=1.0)
    if max_disk == 0:
        max_disk = 1.0

    return max_deps, iops_p75, max_disk


def compute_heatmap(
    vms: list[dict],
    workload_data: dict,
    enrichment_data: dict,
    weights: dict[str, float] | None = None,
    top_n: int = 10,
) -> RiskHeatmap:
    """Compute the fleet-wide risk heatmap.

    Parameters
    ----------
    vms : list[dict]
        List of VM dicts (from discovery JSON).
    workload_data : dict
        Workload discovery data (dependencies, workloads).
    enrichment_data : dict
        Enrichment telemetry indexed by entity.
    weights : dict | None
        Custom factor weights; defaults to DEFAULT_WEIGHTS.
    top_n : int
        Number of top riskiest VMs to highlight (default 10).

    Returns
    -------
    RiskHeatmap
    """
    if not vms:
        return RiskHeatmap(
            vm_scores=[],
            factor_names=[f.value for f in RiskFactorName],
            top_risky=[],
            total_vms=0,
            band_distribution={"green": 0, "yellow": 0, "red": 0},
        )

    max_deps, iops_p75, max_disk = _compute_fleet_stats(
        vms, workload_data, enrichment_data
    )

    scores: list[RiskScore] = []
    for vm in vms:
        score = compute_risk_score(
            vm, workload_data, enrichment_data,
            max_deps, iops_p75, max_disk, weights,
        )
        scores.append(score)

    # Sort by VM name for stable default order
    scores.sort(key=lambda s: s.vm_name)

    # Band distribution
    dist = {"green": 0, "yellow": 0, "red": 0}
    for s in scores:
        dist[s.composite_band] = dist.get(s.composite_band, 0) + 1

    # Top-N riskiest (descending score, alpha tiebreak)
    top = sorted(scores, key=lambda s: (-s.composite_score, s.vm_name))[:top_n]

    return RiskHeatmap(
        vm_scores=scores,
        factor_names=[f.value for f in RiskFactorName],
        top_risky=top,
        total_vms=len(scores),
        band_distribution=dist,
    )
