"""Cost optimization engine — per-VM pricing model recommendations.

Analyses each VM's utilisation pattern (from perf/enrichment data) and recommends
the optimal pricing model (PAYG, RI, SP, AHUB, Dev/Test) plus right-sizing alerts
(oversized, undersized, zombie detection).
"""

from __future__ import annotations

from typing import Any

from azure_migrate_simulations.azure_mapping import VM_CATALOG


def optimize_costs(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    enrichment_data: dict[str, Any] | None = None,
    perf_history: dict[str, Any] | None = None,
    region_multiplier: float = 1.0,
) -> dict[str, Any]:
    """Analyse fleet and recommend per-VM pricing + right-sizing.

    Returns pricing recommendations, right-sizing alerts, and fleet savings.
    """
    sku_lookup = {s.name: s for s in VM_CATALOG}
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}

    pricing_recs: list[dict] = []
    right_sizing: list[dict] = []
    zombies: list[dict] = []

    total_payg = 0.0
    total_optimized = 0.0

    for vm in vms:
        vm_name = vm.get("name", "")
        rec = rec_by_vm.get(vm_name, {})
        sku_name = rec.get("recommended_vm_sku", "")
        sku = sku_lookup.get(sku_name)
        base_cost = sku.monthly_cost_usd if sku else 0
        payg_cost = base_cost * region_multiplier
        total_payg += payg_cost

        os_type = rec.get("os_type", "linux")
        folder = vm.get("folder", "")

        # Get perf data
        vm_perf = (perf_history or {}).get(vm_name, [])
        vm_enrich = (enrichment_data or {}).get(vm_name, {})

        cpu_vals = [s.get("cpu_pct", 0) for s in vm_perf if s.get("cpu_pct") is not None] if vm_perf else []
        mem_vals = [s.get("mem_pct", 0) for s in vm_perf if s.get("mem_pct") is not None] if vm_perf else []

        # Compute stats
        cpu_avg = sum(cpu_vals) / len(cpu_vals) if cpu_vals else None
        cpu_p95 = sorted(cpu_vals)[int(len(cpu_vals) * 0.95)] if cpu_vals else None
        mem_avg = sum(mem_vals) / len(mem_vals) if mem_vals else None
        mem_p95 = sorted(mem_vals)[int(len(mem_vals) * 0.95)] if mem_vals else None

        # ── Right-sizing alerts ──
        if cpu_p95 is not None and mem_p95 is not None:
            if cpu_p95 < 2.0 and mem_p95 < 5.0:
                # Zombie VM
                zombies.append({
                    "vm_name": vm_name,
                    "cpu_p95": round(cpu_p95, 1),
                    "mem_p95": round(mem_p95, 1),
                    "sku": sku_name,
                    "monthly_cost": round(payg_cost, 2),
                    "recommendation": "Decommission — VM appears idle",
                    "annual_savings": round(payg_cost * 12, 2),
                })
            elif cpu_p95 < 20.0 and mem_p95 < 30.0:
                # Oversized
                # Find a smaller SKU
                smaller = _find_smaller_sku(sku, cpu_p95, mem_p95, sku_lookup)
                if smaller:
                    right_sizing.append({
                        "vm_name": vm_name,
                        "alert": "oversized",
                        "cpu_p95": round(cpu_p95, 1),
                        "mem_p95": round(mem_p95, 1),
                        "current_sku": sku_name,
                        "recommended_sku": smaller.name,
                        "current_cost": round(payg_cost, 2),
                        "recommended_cost": round(smaller.monthly_cost_usd * region_multiplier, 2),
                        "monthly_savings": round(payg_cost - smaller.monthly_cost_usd * region_multiplier, 2),
                    })
            elif cpu_p95 > 85.0 or mem_p95 > 90.0:
                # Undersized
                larger = _find_larger_sku(sku, sku_lookup)
                if larger:
                    right_sizing.append({
                        "vm_name": vm_name,
                        "alert": "undersized",
                        "cpu_p95": round(cpu_p95, 1),
                        "mem_p95": round(mem_p95, 1),
                        "current_sku": sku_name,
                        "recommended_sku": larger.name,
                        "current_cost": round(payg_cost, 2),
                        "recommended_cost": round(larger.monthly_cost_usd * region_multiplier, 2),
                    })

        # ── Pricing model recommendation ──
        is_devtest = any(p in folder.lower() for p in ["dev", "test", "staging", "sandbox"]) if folder else False
        is_windows = os_type == "windows"

        model, reason, discount = _recommend_model(
            cpu_vals, is_windows, is_devtest, os_type
        )

        optimized_cost = payg_cost * discount
        total_optimized += optimized_cost

        pricing_recs.append({
            "vm_name": vm_name,
            "sku": sku_name,
            "payg_cost": round(payg_cost, 2),
            "recommended_model": model,
            "optimized_cost": round(optimized_cost, 2),
            "monthly_savings": round(payg_cost - optimized_cost, 2),
            "reason": reason,
            "has_perf_data": len(cpu_vals) > 0,
        })

    # Aggregate
    model_dist: dict[str, int] = {}
    for pr in pricing_recs:
        m = pr["recommended_model"]
        model_dist[m] = model_dist.get(m, 0) + 1

    zombie_savings = sum(z["annual_savings"] for z in zombies)
    rightsizing_savings = sum(r.get("monthly_savings", 0) for r in right_sizing) * 12

    return {
        "vm_count": len(vms),
        "fleet_payg_monthly": round(total_payg, 2),
        "fleet_optimized_monthly": round(total_optimized, 2),
        "pricing_savings_monthly": round(total_payg - total_optimized, 2),
        "pricing_savings_annual": round((total_payg - total_optimized) * 12, 2),
        "pricing_savings_pct": round((1 - total_optimized / total_payg) * 100, 1) if total_payg > 0 else 0,
        "model_distribution": model_dist,
        "right_sizing_alerts": len(right_sizing),
        "zombie_vms": len(zombies),
        "total_optimization_annual": round((total_payg - total_optimized) * 12 + zombie_savings + rightsizing_savings, 2),
        "pricing_recommendations": pricing_recs[:50],
        "right_sizing": right_sizing[:30],
        "zombies": zombies[:20],
    }


def _recommend_model(
    cpu_vals: list[float],
    is_windows: bool,
    is_devtest: bool,
    os_type: str,
) -> tuple[str, str, float]:
    """Returns (model_name, reason, discount_multiplier)."""
    if is_devtest:
        return "devtest", "Dev/Test workload — reduced pricing", 0.56

    if is_windows:
        # AHUB gives ~40% discount on Windows license
        if cpu_vals and len(cpu_vals) >= 10:
            avg = sum(cpu_vals) / len(cpu_vals)
            variance = sum((x - avg) ** 2 for x in cpu_vals) / len(cpu_vals)
            cov = (variance ** 0.5) / avg if avg > 0 else 999
            if cov < 0.3:
                return "3yr_ri_ahub", "Steady Windows workload — 3yr RI + AHUB", 0.24
            return "ahub", "Windows VM with Azure Hybrid Benefit", 0.60

        return "ahub", "Windows VM — AHUB recommended (no perf data for RI analysis)", 0.60

    # Linux
    if cpu_vals and len(cpu_vals) >= 10:
        avg = sum(cpu_vals) / len(cpu_vals)
        variance = sum((x - avg) ** 2 for x in cpu_vals) / len(cpu_vals)
        cov = (variance ** 0.5) / avg if avg > 0 else 999

        if cov < 0.3:
            return "3yr_ri", "Steady workload (low utilisation variance) — maximum RI savings", 0.40
        if cov < 0.6:
            return "3yr_sp", "Moderate variability — savings plan for flexibility", 0.54
        return "1yr_sp", "High variability — short-term savings plan", 0.75

    # No perf data — default to 3yr RI
    return "3yr_ri", "No perf data — defaulting to 3yr RI (safest long-term commitment)", 0.40


def _find_smaller_sku(current_sku, cpu_p95: float, mem_p95: float, sku_lookup: dict):
    """Find a smaller SKU that still fits the workload."""
    if not current_sku:
        return None
    # Need at least cpu_p95% of current vCPUs and mem_p95% of current memory
    needed_vcpus = max(1, int(current_sku.vcpus * cpu_p95 / 100 * 1.5))
    needed_mem = max(1, current_sku.memory_gb * mem_p95 / 100 * 1.3)

    candidates = [
        s for s in VM_CATALOG
        if s.vcpus >= needed_vcpus and s.memory_gb >= needed_mem
        and s.family == current_sku.family
        and s.monthly_cost_usd < current_sku.monthly_cost_usd
    ]
    if candidates:
        return min(candidates, key=lambda s: s.monthly_cost_usd)
    return None


def _find_larger_sku(current_sku, sku_lookup: dict):
    """Find the next size up in the same family."""
    if not current_sku:
        return None
    candidates = [
        s for s in VM_CATALOG
        if s.family == current_sku.family
        and s.vcpus > current_sku.vcpus
        and s.monthly_cost_usd > current_sku.monthly_cost_usd
    ]
    if candidates:
        return min(candidates, key=lambda s: s.monthly_cost_usd)
    return None
