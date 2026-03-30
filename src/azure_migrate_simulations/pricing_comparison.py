"""Pricing comparison engine — side-by-side cost analysis across all pricing models.

Compares fleet cost under PAYG, 1yr RI, 3yr RI, 1yr SP, 3yr SP, AHUB, and
Dev/Test simultaneously, with per-VM optimal model recommendations.
"""

from __future__ import annotations

from typing import Any

from azure_migrate_simulations.azure_mapping import VM_CATALOG


# ---------------------------------------------------------------------------
# Pricing model discounts (relative to PAYG East US)
# ---------------------------------------------------------------------------

PRICING_MODELS = {
    "payg":    {"label": "Pay-As-You-Go",           "discount": 1.00},
    "1yr_ri":  {"label": "1-Year Reserved Instance", "discount": 0.62},
    "3yr_ri":  {"label": "3-Year Reserved Instance", "discount": 0.40},
    "1yr_sp":  {"label": "1-Year Savings Plan",      "discount": 0.75},
    "3yr_sp":  {"label": "3-Year Savings Plan",      "discount": 0.54},
    "ahub":    {"label": "Azure Hybrid Benefit",     "discount": 0.60},
    "devtest": {"label": "Dev/Test Pricing",         "discount": 0.56},
}


def compare_pricing_models(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    region_multiplier: float = 1.0,
    enrichment_data: dict | None = None,
    perf_history: dict | None = None,
) -> dict[str, Any]:
    """Compare fleet cost under all pricing models.

    Returns per-VM costs under each model plus fleet totals and recommendations.
    """
    sku_lookup = {s.name: s for s in VM_CATALOG}
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}

    fleet_totals: dict[str, float] = {model: 0.0 for model in PRICING_MODELS}
    per_vm: list[dict[str, Any]] = []
    model_recommendations: dict[str, int] = {model: 0 for model in PRICING_MODELS}

    for vm in vms:
        vm_name = vm.get("name", "")
        rec = rec_by_vm.get(vm_name, {})
        sku_name = rec.get("recommended_vm_sku", "")
        sku_info = sku_lookup.get(sku_name)
        base_cost = sku_info.monthly_cost_usd if sku_info else rec.get("estimated_monthly_cost", 0)
        os_type = rec.get("os_type", "linux")
        folder = vm.get("folder", "")

        # Calculate cost under each model
        costs: dict[str, float] = {}
        for model_id, model_info in PRICING_MODELS.items():
            cost = round(base_cost * region_multiplier * model_info["discount"], 2)

            # AHUB only applies to Windows VMs
            if model_id == "ahub" and os_type != "windows":
                cost = round(base_cost * region_multiplier, 2)  # No discount

            # Dev/Test only for dev/test workloads
            if model_id == "devtest":
                is_devtest = any(p in folder.lower() for p in ["dev", "test", "staging", "sandbox"]) if folder else False
                if not is_devtest:
                    cost = round(base_cost * region_multiplier, 2)  # No discount

            costs[model_id] = cost
            fleet_totals[model_id] += cost

        # Determine optimal model for this VM
        optimal_model = _recommend_pricing(
            vm_name, os_type, folder, costs,
            enrichment_data.get(vm_name) if enrichment_data else None,
            perf_history.get(vm_name) if perf_history else None,
        )
        model_recommendations[optimal_model] += 1

        savings_vs_payg = round(costs["payg"] - costs[optimal_model], 2)

        per_vm.append({
            "vm_name": vm_name,
            "sku": sku_name,
            "os_type": os_type,
            "costs": costs,
            "recommended_model": optimal_model,
            "recommended_model_label": PRICING_MODELS[optimal_model]["label"],
            "recommended_cost": costs[optimal_model],
            "savings_vs_payg": savings_vs_payg,
            "reason": _pricing_reason(optimal_model, os_type, folder),
        })

    # Fleet summary
    payg_total = fleet_totals["payg"]
    blended_total = sum(vm["recommended_cost"] for vm in per_vm)

    fleet_summary = {
        model_id: {
            "label": info["label"],
            "monthly_total": round(fleet_totals[model_id], 2),
            "savings_vs_payg": round(payg_total - fleet_totals[model_id], 2),
            "savings_pct": round((1 - fleet_totals[model_id] / payg_total) * 100, 1) if payg_total > 0 else 0,
        }
        for model_id, info in PRICING_MODELS.items()
    }

    return {
        "region_multiplier": region_multiplier,
        "vm_count": len(per_vm),
        "fleet_summary": fleet_summary,
        "blended_optimal": {
            "monthly_total": round(blended_total, 2),
            "savings_vs_payg": round(payg_total - blended_total, 2),
            "annual_savings": round((payg_total - blended_total) * 12, 2),
            "savings_pct": round((1 - blended_total / payg_total) * 100, 1) if payg_total > 0 else 0,
            "model_distribution": model_recommendations,
        },
        "per_vm": per_vm,
    }


def _recommend_pricing(
    vm_name: str,
    os_type: str,
    folder: str,
    costs: dict[str, float],
    enrichment: dict | None,
    perf: list | None,
) -> str:
    """Recommend the optimal pricing model for a VM."""
    is_devtest = any(p in folder.lower() for p in ["dev", "test", "staging", "sandbox"]) if folder else False
    is_windows = os_type == "windows"

    # Dev/Test gets its own pricing if folder indicates it
    if is_devtest and costs["devtest"] < costs["payg"]:
        return "devtest"

    # Windows with AHUB (if cheaper than RI)
    if is_windows and costs["ahub"] <= costs["3yr_ri"]:
        return "ahub"

    # If we have perf data, check utilisation stability
    if perf and len(perf) >= 10:
        cpu_vals = [s.get("cpu_pct", 0) for s in perf if s.get("cpu_pct") is not None]
        if cpu_vals:
            avg = sum(cpu_vals) / len(cpu_vals)
            variance = sum((x - avg) ** 2 for x in cpu_vals) / len(cpu_vals)
            cov = (variance ** 0.5) / avg if avg > 0 else 999

            # Steady workload (low CoV) → 3yr RI
            if cov < 0.3:
                return "3yr_ri"
            # Moderate variability → Savings Plan
            if cov < 0.6:
                return "3yr_sp"
            # High variability → 1yr SP or PAYG
            return "1yr_sp"

    # No perf data — safe default: 3yr RI (most savings for committed workloads)
    return "3yr_ri"


def _pricing_reason(model: str, os_type: str, folder: str) -> str:
    reasons = {
        "payg": "Sporadic or short-lived workload — no commitment needed",
        "1yr_ri": "Moderate commitment — 1 year reserved instance",
        "3yr_ri": "Steady workload — maximum savings with 3-year commitment",
        "1yr_sp": "Variable workload — flexibility with 1-year savings plan",
        "3yr_sp": "Variable workload — good savings with 3-year savings plan",
        "ahub": f"Windows VM with Azure Hybrid Benefit (Software Assurance)",
        "devtest": f"Dev/Test workload (folder: {folder}) — reduced pricing",
    }
    return reasons.get(model, "")
