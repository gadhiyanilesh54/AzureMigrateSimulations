"""Post-migration validation generator — automated health, connectivity, and perf checks.

Generates executable validation scripts that compare the Azure environment
against the on-prem baseline captured during discovery and enrichment.
"""

from __future__ import annotations

from typing import Any


def generate_post_migration_checks(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    enrichment_data: dict[str, Any] | None = None,
    perf_history: dict[str, Any] | None = None,
    wave_plan: dict[str, Any] | None = None,
    region: str = "eastus",
    resource_group: str = "rg-migrate-prod",
) -> dict[str, Any]:
    """Generate post-migration validation checks per VM."""
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}
    deps = workload_data.get("result", {}).get("dependencies", []) if workload_data else []

    health_checks: list[dict] = []
    connectivity_checks: list[dict] = []
    perf_checks: list[dict] = []

    vm_names = [v.get("name", "") for v in vms]

    # Health checks per VM
    for vm in vms:
        vm_name = vm.get("name", "")
        rec = rec_by_vm.get(vm_name, {})
        if rec.get("migration_readiness") == "Not Ready":
            continue

        health_checks.append({
            "vm_name": vm_name,
            "check": "power_state",
            "command": f'az vm get-instance-view --name "{vm_name}" --resource-group "{resource_group}" --query "instanceView.statuses[1].displayStatus" -o tsv',
            "expected": "VM running",
            "severity": "Critical",
        })

        health_checks.append({
            "vm_name": vm_name,
            "check": "agent_status",
            "command": f'az vm get-instance-view --name "{vm_name}" --resource-group "{resource_group}" --query "instanceView.vmAgent.statuses[0].displayStatus" -o tsv',
            "expected": "Ready",
            "severity": "High",
        })

    # Connectivity checks from dependencies
    for dep in deps:
        src = dep.get("source_vm", "")
        tgt = dep.get("target_vm", "")
        port = dep.get("port", "")
        if src in vm_names and tgt in vm_names:
            connectivity_checks.append({
                "source_vm": src,
                "target_vm": tgt,
                "port": port,
                "protocol": dep.get("protocol", "tcp"),
                "command": f'az vm run-command invoke --name RunPowerShellScript --resource-group "{resource_group}" --vm-name "{src}" --scripts "Test-NetConnection -ComputerName {tgt} -Port {port}"',
                "expected": f"TcpTestSucceeded: True",
                "severity": "High",
            })

    # Performance baseline checks (if enrichment/perf data available)
    for vm in vms:
        vm_name = vm.get("name", "")
        vm_perf = (perf_history or {}).get(vm_name, [])
        vm_enrich = (enrichment_data or {}).get(vm_name, {})

        if not vm_perf and not vm_enrich:
            continue

        # Determine baseline CPU P95
        cpu_baseline = None
        if vm_perf:
            cpu_vals = sorted([s.get("cpu_pct", 0) for s in vm_perf if s.get("cpu_pct") is not None])
            if cpu_vals:
                cpu_baseline = cpu_vals[int(len(cpu_vals) * 0.95)]
        elif isinstance(vm_enrich, dict) and vm_enrich.get("metrics", {}).get("p95_cpu_pct"):
            cpu_baseline = vm_enrich["metrics"]["p95_cpu_pct"]

        if cpu_baseline is not None:
            threshold = round(cpu_baseline * 1.2, 1)  # 120% of baseline
            perf_checks.append({
                "vm_name": vm_name,
                "metric": "cpu_pct",
                "baseline_p95": round(cpu_baseline, 1),
                "threshold": threshold,
                "command": f'az monitor metrics list --resource "/subscriptions/{{sub}}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}" --metric "Percentage CPU" --interval PT1H --aggregation Average --output table',
                "expected": f"Average CPU <= {threshold}% (120% of on-prem P95: {round(cpu_baseline, 1)}%)",
                "severity": "Medium",
            })

    return {
        "region": region,
        "resource_group": resource_group,
        "summary": {
            "health_checks": len(health_checks),
            "connectivity_checks": len(connectivity_checks),
            "perf_checks": len(perf_checks),
            "total_checks": len(health_checks) + len(connectivity_checks) + len(perf_checks),
        },
        "health_checks": health_checks,
        "connectivity_checks": connectivity_checks,
        "performance_checks": perf_checks,
    }
