"""Migration runbook generator — pre/execution/post-migration validation runbooks.

Generates executable runbooks (YAML-like dicts, Markdown, and shell scripts)
customised per wave with actual VM names, SKUs, network ranges, and dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from azure_migrate_simulations.azure_mapping import VM_CATALOG


def generate_runbooks(
    topology: dict[str, Any],
    wave_plan: dict[str, Any],
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    region: str = "eastus",
) -> dict[str, Any]:
    """Generate all three runbooks from topology + wave plan + discovery data."""
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}
    vm_by_name = {v.get("name", ""): v for v in vms}
    deps = workload_data.get("result", {}).get("dependencies", []) if workload_data else []

    # Extract network info from topology
    containers = topology.get("containers", [])
    vnets = [c for c in containers if c.get("type") == "vnet"]
    cidrs = [_extract_cidr(v.get("label", "")) for v in vnets]

    waves = wave_plan.get("waves", [])

    # Compute required quotas per SKU family
    sku_lookup = {s.name: s for s in VM_CATALOG}
    family_vcpus: dict[str, int] = {}
    for rec in recommendations:
        sku_name = rec.get("recommended_vm_sku", "")
        sku = sku_lookup.get(sku_name)
        if sku:
            family_vcpus[sku.family] = family_vcpus.get(sku.family, 0) + sku.vcpus

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "wave_count": len(waves),
        "pre_migration": _gen_pre_migration(waves, rec_by_vm, vm_by_name, family_vcpus, cidrs, region),
        "execution": _gen_execution(waves, rec_by_vm, deps, region),
        "post_migration": _gen_post_migration(waves, rec_by_vm, deps, region),
    }


def _gen_pre_migration(
    waves: list[dict], rec_by_vm: dict, vm_by_name: dict,
    family_vcpus: dict, cidrs: list[str], region: str,
) -> list[dict[str, Any]]:
    """Generate pre-migration validation checks."""
    checks = []
    check_id = 0

    # Global checks (not wave-specific)
    check_id += 1
    quota_lines = [f"  # {family}: {vcpus} vCPUs needed" for family, vcpus in sorted(family_vcpus.items())]
    checks.append({
        "id": f"PRE-{check_id:03d}",
        "name": "Azure subscription vCPU quota validation",
        "wave": 0,
        "type": "automated",
        "command": f"az vm list-usage --location {region} --output table\n" + "\n".join(quota_lines),
        "expected": f"Available vCPUs >= required for each family",
        "remediation": "az quota request create --resource-name <family> --new-limit <needed>",
    })

    check_id += 1
    cidr_list = ", ".join(cidrs) if cidrs else "10.0.0.0/16"
    checks.append({
        "id": f"PRE-{check_id:03d}",
        "name": "Network address space conflict check",
        "wave": 0,
        "type": "automated",
        "command": f'az network vnet list --query "[].addressSpace.addressPrefixes" -o tsv\n  # Verify no overlap with: {cidr_list}',
        "expected": "No overlapping address spaces with proposed CIDRs",
        "remediation": "Adjust proposed address space in topology or re-address existing VNets",
    })

    check_id += 1
    checks.append({
        "id": f"PRE-{check_id:03d}",
        "name": "Azure RBAC permissions validation",
        "wave": 0,
        "type": "automated",
        "command": 'az role assignment list --assignee $(az account show --query user.name -o tsv) --query "[].roleDefinitionName" -o tsv',
        "expected": "Contributor or Owner role on target subscription",
        "remediation": "Request Contributor role assignment from subscription owner",
    })

    check_id += 1
    checks.append({
        "id": f"PRE-{check_id:03d}",
        "name": "Resource provider registration",
        "wave": 0,
        "type": "automated",
        "command": "az provider register --namespace Microsoft.Compute\naz provider register --namespace Microsoft.Network\naz provider register --namespace Microsoft.Storage",
        "expected": "All providers in 'Registered' state",
        "remediation": "az provider register --namespace <missing-provider>",
    })

    # Per-wave checks
    for wave in waves:
        wave_num = wave.get("wave", 0)
        wave_vms = wave.get("vms", [])
        if not wave_vms:
            continue

        check_id += 1
        vm_list = "\n".join(f"  # - {vm}" for vm in wave_vms[:20])
        if len(wave_vms) > 20:
            vm_list += f"\n  # ... and {len(wave_vms) - 20} more"
        checks.append({
            "id": f"PRE-{check_id:03d}",
            "name": f"Wave {wave_num} — source VM snapshot creation",
            "wave": wave_num,
            "type": "semi-automated",
            "command": f"# PowerCLI: Create pre-migration snapshots for Wave {wave_num}\n{vm_list}\n# Get-VM -Name <vm> | New-Snapshot -Name 'pre-migration-w{wave_num}' -Memory:$false",
            "expected": f"Snapshots created for all {len(wave_vms)} VMs in Wave {wave_num}",
            "remediation": "Verify sufficient datastore space for snapshots",
        })

        check_id += 1
        checks.append({
            "id": f"PRE-{check_id:03d}",
            "name": f"Wave {wave_num} — DNS readiness check",
            "wave": wave_num,
            "type": "manual",
            "command": None,
            "expected": f"DNS records identified for {len(wave_vms)} VMs; cutover plan documented",
            "remediation": "Document DNS records to update and set TTL to 300s before migration",
        })

    return checks


def _gen_execution(
    waves: list[dict], rec_by_vm: dict, deps: list[dict], region: str,
) -> list[dict[str, Any]]:
    """Generate migration execution steps."""
    steps = []
    step_id = 0

    for wave in waves:
        wave_num = wave.get("wave", 0)
        wave_vms = wave.get("vms", [])
        if not wave_vms:
            continue

        step_id += 1
        steps.append({
            "id": f"EXEC-{step_id:03d}",
            "name": f"Wave {wave_num} — deploy landing zone infrastructure",
            "wave": wave_num,
            "type": "automated",
            "command": f"cd generated/terraform\nterraform init\nterraform plan -var-file=environments/production.tfvars -out=wave{wave_num}.tfplan\nterraform apply wave{wave_num}.tfplan",
            "validation": "All resources created without errors",
        })

        step_id += 1
        steps.append({
            "id": f"EXEC-{step_id:03d}",
            "name": f"Wave {wave_num} — validate infrastructure deployment",
            "wave": wave_num,
            "type": "automated",
            "command": f"az resource list --resource-group rg-migrate-prod-{region}-001 --output table",
            "validation": f"VNet, subnets, NSGs created for Wave {wave_num}",
        })

        step_id += 1
        vm_names_str = ", ".join(wave_vms[:10])
        steps.append({
            "id": f"EXEC-{step_id:03d}",
            "name": f"Wave {wave_num} — enable replication ({len(wave_vms)} VMs)",
            "wave": wave_num,
            "type": "semi-automated",
            "command": f"# Enable replication for: {vm_names_str}\n# Use Azure Migrate replication appliance or ASR",
            "validation": f"Initial replication completed for all {len(wave_vms)} VMs",
        })

        step_id += 1
        steps.append({
            "id": f"EXEC-{step_id:03d}",
            "name": f"Wave {wave_num} — test failover",
            "wave": wave_num,
            "type": "semi-automated",
            "command": f"# Run test failover to isolated VNet for Wave {wave_num}\n# Validate application connectivity in isolated environment",
            "validation": "Applications accessible in test environment; no impact on production",
        })

        step_id += 1
        steps.append({
            "id": f"EXEC-{step_id:03d}",
            "name": f"Wave {wave_num} — production failover",
            "wave": wave_num,
            "type": "semi-automated",
            "command": f"# Execute production failover for Wave {wave_num} ({len(wave_vms)} VMs)\n# Coordinate with change management window",
            "validation": f"All {len(wave_vms)} VMs running in Azure",
        })

        step_id += 1
        steps.append({
            "id": f"EXEC-{step_id:03d}",
            "name": f"Wave {wave_num} — DNS cutover",
            "wave": wave_num,
            "type": "manual",
            "command": f"# Update DNS records for Wave {wave_num} VMs\n# Set TTL to 300s during migration, revert to 3600s after 48h",
            "validation": "DNS resolves to new Azure IP addresses",
        })

    return steps


def _gen_post_migration(
    waves: list[dict], rec_by_vm: dict, deps: list[dict], region: str,
) -> list[dict[str, Any]]:
    """Generate post-migration validation checks."""
    checks = []
    check_id = 0

    for wave in waves:
        wave_num = wave.get("wave", 0)
        wave_vms = wave.get("vms", [])
        if not wave_vms:
            continue

        check_id += 1
        checks.append({
            "id": f"POST-{check_id:03d}",
            "name": f"Wave {wave_num} — VM health check",
            "wave": wave_num,
            "type": "automated",
            "command": f'az vm list -g rg-migrate-prod-{region}-001 --query "[?name==\'{{vm_name}}\'].{{Name:name, Status:powerState}}" -o table',
            "expected": f"All {len(wave_vms)} VMs in 'running' state with healthy agent",
            "remediation": "Check VM boot diagnostics and serial console",
        })

        # Connectivity checks from dependencies
        wave_deps = [d for d in deps if d.get("source_vm") in wave_vms or d.get("target_vm") in wave_vms]
        if wave_deps:
            check_id += 1
            dep_checks = []
            for d in wave_deps[:10]:
                src = d.get("source_vm", "")
                tgt = d.get("target_vm", "")
                port = d.get("port", "")
                dep_checks.append(f"  # {src} -> {tgt}:{port}")
            checks.append({
                "id": f"POST-{check_id:03d}",
                "name": f"Wave {wave_num} — application connectivity validation",
                "wave": wave_num,
                "type": "automated",
                "command": f"# Test connectivity for {len(wave_deps)} dependencies:\n" + "\n".join(dep_checks),
                "expected": "All dependency connections successful",
                "remediation": "Check NSG rules and routing; verify target VM is migrated",
            })

        check_id += 1
        checks.append({
            "id": f"POST-{check_id:03d}",
            "name": f"Wave {wave_num} — performance baseline validation",
            "wave": wave_num,
            "type": "automated",
            "command": f'az monitor metrics list --resource {{vm_resource_id}} --metric "Percentage CPU" --interval PT1H --output table',
            "expected": "CPU/Memory within 120% of on-prem P95 baseline",
            "remediation": "If metrics exceed baseline, consider upsizing VM SKU",
        })

        check_id += 1
        checks.append({
            "id": f"POST-{check_id:03d}",
            "name": f"Wave {wave_num} — enable Azure Backup",
            "wave": wave_num,
            "type": "automated",
            "command": f"# Enable backup for Wave {wave_num} VMs\naz backup protection enable-for-vm --vault-name bkv-migrate-{region} --resource-group rg-migrate-prod-{region}-001 --vm {{vm_name}} --policy-name DefaultPolicy",
            "expected": f"Backup enabled for all {len(wave_vms)} VMs",
            "remediation": "Create backup vault first: az backup vault create ...",
        })

        check_id += 1
        checks.append({
            "id": f"POST-{check_id:03d}",
            "name": f"Wave {wave_num} — decommission on-prem snapshots",
            "wave": wave_num,
            "type": "manual",
            "command": None,
            "expected": "Pre-migration snapshots removed after 48h validation period",
            "remediation": "Keep snapshots for an additional week if issues are found",
        })

    return checks


def render_runbook_markdown(runbook: dict[str, Any]) -> str:
    """Render a runbook as Markdown."""
    lines = [
        f"# Migration Runbook",
        f"",
        f"Generated: {runbook.get('generated_at', '')}",
        f"Region: {runbook.get('region', 'eastus')}",
        f"Waves: {runbook.get('wave_count', 0)}",
        "",
    ]

    for section_key, section_title in [
        ("pre_migration", "Pre-Migration Validation"),
        ("execution", "Migration Execution"),
        ("post_migration", "Post-Migration Validation"),
    ]:
        checks = runbook.get(section_key, [])
        lines.append(f"## {section_title}")
        lines.append("")
        for check in checks:
            wave_str = f" (Wave {check['wave']})" if check.get("wave") else " (Global)"
            lines.append(f"### {check['id']}: {check['name']}{wave_str}")
            lines.append(f"- **Type**: {check.get('type', '')}")
            if check.get("command"):
                lines.append(f"- **Command**:")
                lines.append(f"```bash")
                lines.append(check["command"])
                lines.append(f"```")
            expected = check.get("expected") or check.get("validation", "")
            if expected:
                lines.append(f"- **Expected**: {expected}")
            if check.get("remediation"):
                lines.append(f"- **Remediation**: {check['remediation']}")
            lines.append("")

    return "\n".join(lines)


def _extract_cidr(label: str) -> str:
    import re
    m = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)", label)
    return m.group(1) if m else "10.0.0.0/16"
