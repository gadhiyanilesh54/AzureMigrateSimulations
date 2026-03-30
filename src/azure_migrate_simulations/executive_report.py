"""Executive report generator — produces boardroom-ready migration reports.

Aggregates data from discovery, assessment, business case, CTD, wave plan,
and vulnerability analysis into a structured report with 9 sections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from azure_migrate_simulations.azure_mapping import VM_CATALOG


def generate_executive_report(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    topology: dict[str, Any] | None = None,
    wave_plan: dict[str, Any] | None = None,
    enrichment_data: dict[str, Any] | None = None,
    vuln_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a structured executive migration report.

    Returns a dict with all 9 report sections, suitable for JSON or Markdown export.
    """
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}
    sku_lookup = {s.name: s for s in VM_CATALOG}

    # ── Section 1: Executive Summary ──
    total_vms = len(vms)
    ready = sum(1 for r in recommendations if r.get("migration_readiness") == "Ready")
    ready_cond = sum(1 for r in recommendations if "condition" in r.get("migration_readiness", "").lower())
    ready_pct = round((ready + ready_cond) / total_vms * 100) if total_vms else 0

    total_vcpus = sum(v.get("num_cpus", 0) for v in vms)
    total_ram_gb = round(sum(v.get("memory_mb", 0) for v in vms) / 1024, 1)

    # On-prem TCO
    total_disk_tb = sum(v.get("total_disk_gb", 0) for v in vms) / 1024
    onprem_monthly = (
        total_vcpus * 25 + total_ram_gb * 5 + total_disk_tb * 100
        + total_vms * 15 + 2000
    )
    azure_monthly = sum(
        sku_lookup.get(r.get("recommended_vm_sku", ""), type("", (), {"monthly_cost_usd": 0})).monthly_cost_usd
        for r in recommendations
    )
    monthly_savings = onprem_monthly - azure_monthly
    payback_months = round(onprem_monthly * 3 / monthly_savings, 1) if monthly_savings > 0 else None

    exec_summary = (
        f"The discovered VMware estate comprises {total_vms} virtual machines "
        f"({total_vcpus} vCPUs, {total_ram_gb} GB RAM) with {ready_pct}% migration readiness. "
        f"Migration to Azure is projected to save ${round(monthly_savings * 12):,}/year "
        f"with a {payback_months}-month payback period." if payback_months else
        f"The discovered VMware estate comprises {total_vms} virtual machines "
        f"({total_vcpus} vCPUs, {total_ram_gb} GB RAM) with {ready_pct}% migration readiness."
    )

    # ── Section 2: Estate Overview ──
    hosts = set(v.get("host", "") for v in vms) - {""}
    datacenters = set(v.get("datacenter", "") for v in vms) - {""}
    os_dist: dict[str, int] = {}
    for r in recommendations:
        os_type = r.get("os_type", "unknown")
        os_dist[os_type] = os_dist.get(os_type, 0) + 1

    estate = {
        "total_vms": total_vms,
        "total_vcpus": total_vcpus,
        "total_ram_gb": total_ram_gb,
        "total_disk_tb": round(total_disk_tb, 1),
        "host_count": len(hosts),
        "datacenter_count": len(datacenters),
        "os_distribution": os_dist,
    }

    # ── Section 3: Migration Readiness ──
    readiness_dist: dict[str, int] = {}
    blockers: list[dict[str, str]] = []
    for r in recommendations:
        rd = r.get("migration_readiness", "Unknown")
        readiness_dist[rd] = readiness_dist.get(rd, 0) + 1
        if rd == "Not Ready":
            blockers.append({
                "vm": r.get("vm_name", ""),
                "reason": r.get("readiness_notes", "Unsupported configuration"),
            })

    readiness = {
        "distribution": readiness_dist,
        "ready_pct": ready_pct,
        "top_blockers": blockers[:10],
    }

    # ── Section 4: Business Case ──
    business_case = {
        "on_prem_monthly_tco": round(onprem_monthly, 2),
        "azure_monthly_cost": round(azure_monthly, 2),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(monthly_savings * 12, 2),
        "three_year_savings": round(monthly_savings * 36, 2),
        "payback_period_months": payback_months,
    }

    # ── Section 5: Target Architecture (from CTD) ──
    architecture = {"available": False}
    if topology:
        containers = topology.get("containers", [])
        lzs = [c for c in containers if c.get("type") == "landing_zone"]
        architecture = {
            "available": True,
            "landing_zones": [{"id": c["id"], "label": c["label"]} for c in lzs],
            "resource_count": len(topology.get("nodes", [])),
            "dependency_count": len(topology.get("edges", [])),
            "total_monthly_cost": topology.get("total_monthly_cost"),
            "waf_summary": topology.get("waf_summary"),
            "cost_summary": topology.get("cost_summary"),
        }

    # ── Section 6: Wave Plan ──
    wave_section = {"available": False}
    if wave_plan and wave_plan.get("waves"):
        waves = wave_plan["waves"]
        wave_section = {
            "available": True,
            "wave_count": len(waves),
            "waves": [
                {
                    "wave": w["wave"],
                    "vm_count": w["vm_count"],
                    "monthly_cost": w.get("monthly_cost", 0),
                }
                for w in waves
            ],
        }

    # ── Section 7: Risk Matrix ──
    risks = []
    # EOL OS risk
    eol_count = sum(1 for r in recommendations if "condition" in r.get("migration_readiness", "").lower())
    if eol_count > 0:
        risks.append({
            "id": "RISK-001",
            "category": "Security",
            "severity": "High" if eol_count > total_vms * 0.2 else "Medium",
            "title": "End-of-life operating systems",
            "description": f"{eol_count} VMs run OS versions approaching or past end-of-life",
            "mitigation": "Apply Extended Security Updates (ESU) or upgrade OS before migration",
        })

    # Low confidence risk
    low_conf = sum(1 for r in recommendations if (r.get("confidence_score") or 0) < 60)
    if low_conf > 0:
        risks.append({
            "id": "RISK-002",
            "category": "Accuracy",
            "severity": "Medium",
            "title": "Low assessment confidence",
            "description": f"{low_conf} VMs have confidence scores below 60% — sizing may be inaccurate",
            "mitigation": "Upload enrichment data from Dynatrace/New Relic/Datadog to boost confidence",
        })

    # No workload discovery
    if not workload_data or not workload_data.get("result", {}).get("vm_workloads"):
        risks.append({
            "id": "RISK-003",
            "category": "Completeness",
            "severity": "Medium",
            "title": "Workload discovery not performed",
            "description": "Guest-level workload discovery has not been run — databases and web apps may be missed",
            "mitigation": "Run workload discovery with SSH/WinRM credentials to detect databases, web apps, and containers",
        })

    # No enrichment
    enrichment_coverage = 0
    if enrichment_data:
        enrichment_coverage = sum(1 for v in vms if v.get("name") in enrichment_data)
    if enrichment_coverage < total_vms * 0.5:
        risks.append({
            "id": "RISK-004",
            "category": "Accuracy",
            "severity": "Low" if enrichment_coverage > 0 else "Medium",
            "title": "Limited monitoring enrichment",
            "description": f"Only {enrichment_coverage}/{total_vms} VMs have monitoring enrichment data",
            "mitigation": "Upload telemetry from existing APM tools (Dynatrace, New Relic, Datadog, etc.)",
        })

    # ── Section 8: Recommendations ──
    strategic_recs = [
        {
            "priority": "High",
            "action": "Commit to 3-year Reserved Instances for steady-state workloads",
            "impact": "Up to 60% cost savings on compute",
            "timeline": "Before migration",
        },
        {
            "priority": "High",
            "action": "Address end-of-life operating systems before migration",
            "impact": "Improved security posture and Azure support eligibility",
            "timeline": "Wave 1 preparation",
        },
    ]
    if enrichment_coverage < total_vms * 0.5:
        strategic_recs.insert(0, {
            "priority": "High",
            "action": "Upload monitoring enrichment data to improve assessment confidence",
            "impact": "More accurate right-sizing (potential 15-30% cost reduction)",
            "timeline": "Before finalizing assessment",
        })
    if not workload_data or not workload_data.get("result", {}).get("vm_workloads"):
        strategic_recs.insert(0, {
            "priority": "High",
            "action": "Run guest-level workload discovery",
            "impact": "Identify PaaS opportunities (database → Azure SQL, web → App Service)",
            "timeline": "Before wave planning",
        })

    # ── Section 9: Appendix (summary tables) ──
    appendix_vms = []
    for r in recommendations:
        appendix_vms.append({
            "vm_name": r.get("vm_name"),
            "sku": r.get("recommended_vm_sku"),
            "family": r.get("recommended_vm_family"),
            "cost": r.get("estimated_monthly_cost"),
            "readiness": r.get("migration_readiness"),
            "confidence": r.get("confidence_score"),
            "os": r.get("os_type"),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {
            "executive_summary": exec_summary,
            "estate_overview": estate,
            "migration_readiness": readiness,
            "business_case": business_case,
            "target_architecture": architecture,
            "wave_plan": wave_section,
            "risk_matrix": risks,
            "recommendations": strategic_recs,
            "appendix_vm_assessment": appendix_vms[:100],  # Cap for context window
        },
    }


def render_report_markdown(report: dict[str, Any]) -> str:
    """Render the executive report as Markdown."""
    s = report.get("sections", {})
    lines = [
        "# Azure Migration — Executive Report",
        f"*Generated: {report.get('generated_at', '')}*",
        "",
        "## 1. Executive Summary",
        s.get("executive_summary", ""),
        "",
        "## 2. Estate Overview",
    ]

    estate = s.get("estate_overview", {})
    lines += [
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| VMs | {estate.get('total_vms', 0)} |",
        f"| vCPUs | {estate.get('total_vcpus', 0)} |",
        f"| RAM (GB) | {estate.get('total_ram_gb', 0)} |",
        f"| Disk (TB) | {estate.get('total_disk_tb', 0)} |",
        f"| Hosts | {estate.get('host_count', 0)} |",
        "",
    ]

    lines += ["## 3. Migration Readiness", ""]
    rd = s.get("migration_readiness", {})
    for status, count in rd.get("distribution", {}).items():
        lines.append(f"- **{status}**: {count} VMs")
    lines.append("")

    lines += ["## 4. Business Case", ""]
    bc = s.get("business_case", {})
    lines += [
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| On-Prem Monthly TCO | ${bc.get('on_prem_monthly_tco', 0):,.2f} |",
        f"| Azure Monthly Cost | ${bc.get('azure_monthly_cost', 0):,.2f} |",
        f"| Monthly Savings | ${bc.get('monthly_savings', 0):,.2f} |",
        f"| Annual Savings | ${bc.get('annual_savings', 0):,.2f} |",
        f"| 3-Year Savings | ${bc.get('three_year_savings', 0):,.2f} |",
        f"| Payback Period | {bc.get('payback_period_months', 'N/A')} months |",
        "",
    ]

    lines += ["## 5. Target Architecture", ""]
    arch = s.get("target_architecture", {})
    if arch.get("available"):
        for lz in arch.get("landing_zones", []):
            lines.append(f"- **{lz['label']}**")
        lines.append(f"\nTotal monthly cost: ${arch.get('total_monthly_cost', 0):,.2f}")
    else:
        lines.append("*Generate a Cloud Topology Diagram to populate this section.*")
    lines.append("")

    lines += ["## 6. Wave Plan", ""]
    wp = s.get("wave_plan", {})
    if wp.get("available"):
        lines += [f"| Wave | VMs | Monthly Cost |", f"|------|-----|-------------|"]
        for w in wp.get("waves", []):
            lines.append(f"| Wave {w['wave']} | {w['vm_count']} | ${w.get('monthly_cost', 0):,.2f} |")
    else:
        lines.append("*Run fleet simulation to generate wave plan.*")
    lines.append("")

    lines += ["## 7. Risk Matrix", ""]
    for risk in s.get("risk_matrix", []):
        lines.append(f"### {risk['id']}: {risk['title']} ({risk['severity']})")
        lines.append(f"- **Category**: {risk['category']}")
        lines.append(f"- **Description**: {risk['description']}")
        lines.append(f"- **Mitigation**: {risk['mitigation']}")
        lines.append("")

    lines += ["## 8. Strategic Recommendations", ""]
    for rec in s.get("recommendations", []):
        lines.append(f"- **[{rec['priority']}]** {rec['action']} — {rec['impact']} (Timeline: {rec['timeline']})")
    lines.append("")

    lines += ["## 9. Appendix — VM Assessment", ""]
    lines += [f"| VM | SKU | Cost | Readiness | OS |", f"|----|----|------|-----------|----|"]
    for vm in s.get("appendix_vm_assessment", [])[:50]:
        lines.append(f"| {vm.get('vm_name','')} | {vm.get('sku','')} | ${vm.get('cost',0)} | {vm.get('readiness','')} | {vm.get('os','')} |")

    return "\n".join(lines)
