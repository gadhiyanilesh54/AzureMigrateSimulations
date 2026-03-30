"""Application grouping — detect logical applications from dependency graph.

Uses TCP dependency edges and VM naming patterns to cluster VMs into
application groups, with complexity scoring and criticality tagging.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def detect_application_groups(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    saved_groups: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Detect application groups from dependency graph and naming patterns.

    Steps:
    1. Build undirected dependency graph from TCP connections
    2. Find connected components → each component = candidate app group
    3. Group remaining (unconnected) VMs by vCenter folder
    4. Infer application names from common VM name prefixes
    5. Calculate complexity score per group
    """
    vm_names = {v.get("name", "") for v in vms}
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}
    vm_by_name = {v.get("name", ""): v for v in vms}

    # Load saved criticality overrides
    saved = saved_groups or {}

    # 1. Build undirected adjacency from dependencies
    adj: dict[str, set[str]] = defaultdict(set)
    deps = _extract_deps(workload_data)
    for d in deps:
        src = d.get("source_vm", "")
        tgt = d.get("target_vm", "")
        if src in vm_names and tgt in vm_names and src != tgt:
            adj[src].add(tgt)
            adj[tgt].add(src)

    # 2. Connected components via BFS
    visited: set[str] = set()
    components: list[set[str]] = []
    for vm_name in sorted(vm_names):
        if vm_name in visited or vm_name not in adj:
            continue
        component: set[str] = set()
        queue = [vm_name]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        if component:
            components.append(component)

    # 3. Group remaining VMs by folder
    folder_groups: dict[str, set[str]] = defaultdict(set)
    for vm_name in vm_names:
        if vm_name in visited:
            continue
        vm = vm_by_name.get(vm_name, {})
        folder = vm.get("folder", "ungrouped") or "ungrouped"
        folder_groups[folder].add(vm_name)

    # Merge folder groups into components
    for folder, folder_vms in folder_groups.items():
        if len(folder_vms) > 1:
            components.append(folder_vms)
        else:
            # Singletons → one group per VM (standalone)
            components.append(folder_vms)

    # 4. Build application group objects
    groups: list[dict[str, Any]] = []
    workload_types = _get_wl_types(workload_data)

    for i, component in enumerate(components):
        # Infer name from common prefix
        app_name = _infer_app_name(component)
        group_id = f"app-{i+1:03d}-{_sanitize(app_name)}"

        # Get saved criticality or default to Tier-2
        saved_entry = saved.get(group_id, {})
        criticality = saved_entry.get("criticality", "Tier-2")

        # Get dependency edges within group
        internal_deps = []
        for d in deps:
            if d.get("source_vm") in component and d.get("target_vm") in component:
                internal_deps.append(d)

        # Workload types in group
        group_wl_types = set()
        for vm_name in component:
            group_wl_types.add(workload_types.get(vm_name, "general_compute"))

        # Total cost
        total_cost = sum(
            rec_by_vm.get(vm, {}).get("estimated_monthly_cost", 0)
            for vm in component
        )

        # Complexity score (1-10)
        complexity = _calc_complexity(
            vm_count=len(component),
            dep_count=len(internal_deps),
            wl_types=group_wl_types,
            has_database="database" in group_wl_types,
            has_container="container" in group_wl_types,
        )

        # VM details
        vm_details = []
        for vm_name in sorted(component):
            rec = rec_by_vm.get(vm_name, {})
            vm_details.append({
                "name": vm_name,
                "sku": rec.get("recommended_vm_sku", ""),
                "cost": rec.get("estimated_monthly_cost", 0),
                "readiness": rec.get("migration_readiness", "Unknown"),
                "workload_type": workload_types.get(vm_name, "general_compute"),
            })

        groups.append({
            "id": group_id,
            "name": app_name,
            "vm_count": len(component),
            "vms": vm_details,
            "dependencies": internal_deps,
            "dependency_count": len(internal_deps),
            "workload_types": sorted(group_wl_types),
            "total_monthly_cost": round(total_cost, 2),
            "complexity_score": complexity,
            "criticality": criticality,
            "grouping_method": "dependency" if any(v in adj for v in component) else "folder",
        })

    groups.sort(key=lambda g: (-g["complexity_score"], -g["vm_count"]))

    return groups


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _extract_deps(workload_data: dict | None) -> list[dict]:
    if not workload_data:
        return []
    return workload_data.get("result", {}).get("dependencies", [])


def _get_wl_types(workload_data: dict | None) -> dict[str, str]:
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


def _infer_app_name(vms: set[str]) -> str:
    """Infer application name from common prefix of VM names."""
    if len(vms) == 1:
        return next(iter(vms))
    names = sorted(vms)

    # Try common prefix
    prefix = names[0]
    for name in names[1:]:
        while not name.lower().startswith(prefix.lower()) and len(prefix) > 2:
            prefix = prefix[:-1]
    prefix = prefix.rstrip("-_ .")

    if len(prefix) >= 3:
        return prefix

    # Fallback: use shortest name
    return min(names, key=len)


def _sanitize(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")[:30]


def _calc_complexity(
    vm_count: int,
    dep_count: int,
    wl_types: set[str],
    has_database: bool,
    has_container: bool,
) -> int:
    """Calculate complexity score 1-10."""
    score = 1
    if vm_count >= 2:
        score += 1
    if vm_count >= 5:
        score += 1
    if vm_count >= 10:
        score += 1
    if dep_count >= 3:
        score += 1
    if dep_count >= 10:
        score += 1
    if len(wl_types) >= 3:
        score += 1
    if has_database:
        score += 1
    if has_container:
        score += 1
    if vm_count >= 20:
        score += 1
    return min(score, 10)
