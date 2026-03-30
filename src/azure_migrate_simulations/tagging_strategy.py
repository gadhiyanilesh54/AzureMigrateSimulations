"""Tagging strategy generator — auto-generate Azure tags from vCenter metadata.

Maps vCenter folder, cluster, annotation, and resource pool data to Azure tags
following governance best practices.
"""

from __future__ import annotations

import re
from typing import Any


# Default tag mappings
DEFAULT_TAG_KEYS = {
    "environment": "Environment",
    "source_vm": "SourceVM",
    "source_host": "SourceHost",
    "migration_wave": "MigrationWave",
    "workload_type": "WorkloadType",
    "os_type": "OS",
    "cost_center": "CostCenter",
    "managed_by": "ManagedBy",
    "migration_date": "MigrationDate",
}

# Folder → Environment mapping patterns
_ENV_PATTERNS = {
    "production": ["prod", "prd", "production", "live"],
    "development": ["dev", "development"],
    "testing": ["test", "testing", "qa", "quality"],
    "staging": ["stag", "staging", "uat", "preprod", "pre-prod"],
    "sandbox": ["sandbox", "lab", "poc", "demo"],
}


def generate_tagging_strategy(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    wave_plan: dict[str, Any] | None = None,
    custom_mappings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a tagging strategy for all VMs.

    Returns per-VM tag assignments plus a tag policy summary.
    """
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}
    wl_types = _get_workload_types(workload_data)
    vm_waves = _get_vm_waves(wave_plan)
    overrides = custom_mappings or {}

    # Collect unique values for policy summary
    environments: set[str] = set()
    cost_centers: set[str] = set()
    workload_types: set[str] = set()

    per_vm: list[dict[str, Any]] = []
    for vm in vms:
        vm_name = vm.get("name", "")
        rec = rec_by_vm.get(vm_name, {})

        # Determine environment from folder
        folder = vm.get("folder", "")
        env = _classify_environment(folder, overrides.get("folder_env_map", {}))
        environments.add(env)

        # Cost center from cluster (or custom mapping)
        cluster = vm.get("cluster", "")
        cost_center = overrides.get("cluster_cost_center", {}).get(cluster, cluster or "default")
        cost_centers.add(cost_center)

        # Workload type
        wl_type = wl_types.get(vm_name, "general_compute")
        workload_types.add(wl_type)

        tags = {
            DEFAULT_TAG_KEYS["environment"]: env,
            DEFAULT_TAG_KEYS["source_vm"]: vm_name,
            DEFAULT_TAG_KEYS["source_host"]: vm.get("host", ""),
            DEFAULT_TAG_KEYS["migration_wave"]: str(vm_waves.get(vm_name, "")),
            DEFAULT_TAG_KEYS["workload_type"]: wl_type,
            DEFAULT_TAG_KEYS["os_type"]: rec.get("os_type", vm.get("guest_os_family", "")),
            DEFAULT_TAG_KEYS["cost_center"]: cost_center,
            DEFAULT_TAG_KEYS["managed_by"]: "AzureMigrateSimulations",
        }

        # Apply any per-VM custom tag overrides
        vm_overrides = overrides.get("vm_tags", {}).get(vm_name, {})
        tags.update(vm_overrides)

        # Remove empty tags
        tags = {k: v for k, v in tags.items() if v}

        per_vm.append({
            "vm_name": vm_name,
            "tags": tags,
            "tag_count": len(tags),
        })

    # Tag policy summary
    all_tag_keys = set()
    for vm_tags in per_vm:
        all_tag_keys.update(vm_tags["tags"].keys())

    return {
        "vm_count": len(per_vm),
        "tag_keys_used": sorted(all_tag_keys),
        "tag_key_count": len(all_tag_keys),
        "environment_values": sorted(environments),
        "cost_center_values": sorted(cost_centers),
        "workload_type_values": sorted(workload_types),
        "policy_summary": {
            "required_tags": [
                DEFAULT_TAG_KEYS["environment"],
                DEFAULT_TAG_KEYS["managed_by"],
                DEFAULT_TAG_KEYS["workload_type"],
            ],
            "recommended_tags": [
                DEFAULT_TAG_KEYS["cost_center"],
                DEFAULT_TAG_KEYS["source_vm"],
                DEFAULT_TAG_KEYS["migration_wave"],
            ],
        },
        "per_vm": per_vm,
        "terraform_locals": _generate_tf_tags_block(per_vm[:5]),
    }


def _classify_environment(folder: str, custom_map: dict[str, str]) -> str:
    """Classify vCenter folder into environment."""
    if folder in custom_map:
        return custom_map[folder]
    folder_lower = folder.lower()
    for env, patterns in _ENV_PATTERNS.items():
        if any(p in folder_lower for p in patterns):
            return env
    return "production"  # Default


def _get_workload_types(workload_data: dict | None) -> dict[str, str]:
    types: dict[str, str] = {}
    if not workload_data:
        return types
    for vm_wl in workload_data.get("result", {}).get("vm_workloads", []):
        vm_name = vm_wl.get("vm_name", "")
        if vm_wl.get("databases"):
            types[vm_name] = "database"
        elif vm_wl.get("orchestrators"):
            types[vm_name] = "orchestrator"
        elif vm_wl.get("containers"):
            types[vm_name] = "container"
        elif vm_wl.get("web_apps"):
            types[vm_name] = "webapp"
        else:
            types[vm_name] = "general_compute"
    return types


def _get_vm_waves(wave_plan: dict | None) -> dict[str, int]:
    waves: dict[str, int] = {}
    if not wave_plan:
        return waves
    for wave in wave_plan.get("waves", []):
        for vm_name in wave.get("vms", []):
            waves[vm_name] = wave["wave"]
    return waves


def _generate_tf_tags_block(sample_vms: list[dict]) -> str:
    """Generate a sample Terraform tags locals block."""
    if not sample_vms:
        return ""
    sample = sample_vms[0]
    tags = sample.get("tags", {})
    lines = ["locals {", "  common_tags = {"]
    for k, v in sorted(tags.items()):
        lines.append(f'    {k} = "{v}"')
    lines += ["  }", "}"]
    return "\n".join(lines)
