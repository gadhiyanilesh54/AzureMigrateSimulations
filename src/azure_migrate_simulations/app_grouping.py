"""Application grouping — detect logical applications from dependency graph.

Uses TCP dependency edges and VM naming patterns to cluster VMs into
application groups, with complexity scoring and criticality tagging.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any


def detect_application_groups(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    saved_groups: dict[str, Any] | None = None,
    datastores: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Detect application groups from dependency graph and naming patterns.

    Steps:
    1. Build undirected dependency graph from TCP connections
    2. Find connected components → each component = candidate app group
    3. Group remaining (unconnected) VMs by vCenter folder
    4. Infer application names from common VM name prefixes
    5. Attach heterogeneous workload and file-share members
    6. Calculate complexity score per group
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
    workload_members_by_vm = _get_workload_members_by_vm(workload_data)
    datastore_by_name = {
        d.get("name", ""): d for d in (datastores or []) if d.get("name")
    }
    fileshare_recommendations = _get_fileshare_recommendations(workload_data)

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

        # Application members follow the application-centric assessment model:
        # one heterogeneous collection owns machines and their child workloads.
        members: list[dict[str, Any]] = []
        group_wl_types: set[str] = set()
        vms_with_assessed_workloads: set[str] = set()

        for vm_name in sorted(component):
            vm = vm_by_name.get(vm_name, {})
            rec = rec_by_vm.get(vm_name, {})
            members.append(_build_vm_member(vm, rec))

            workload_members = workload_members_by_vm.get(vm_name, [])
            if workload_members:
                vms_with_assessed_workloads.add(vm_name)
            else:
                group_wl_types.add("general_compute")

            for member in workload_members:
                members.append(member.copy())
                group_wl_types.add(member["type"])

        # A datastore is an application member when at least one VM in the
        # application has a disk on it. Shared datastores may therefore appear
        # in multiple applications and are marked as shared below.
        datastore_names = sorted({
            disk.get("datastore_name", "")
            for vm_name in component
            for disk in vm_by_name.get(vm_name, {}).get("disks", [])
            if disk.get("datastore_name")
        })
        for datastore_name in datastore_names:
            datastore = datastore_by_name.get(datastore_name, {"name": datastore_name})
            members.append(_build_fileshare_member(
                datastore,
                fileshare_recommendations.get(datastore_name.lower()),
            ))
            group_wl_types.add("fileshare")

        # Total cost
        source_vm_cost = sum(
            rec_by_vm.get(vm, {}).get(
                "estimated_monthly_cost_usd",
                rec_by_vm.get(vm, {}).get("estimated_monthly_cost", 0),
            )
            for vm in component
        )

        # PaaS recommendations replace their host VM in the target estimate.
        # Machines without an assessed child workload retain the VM fallback.
        target_cost = sum(
            member.get("monthly_cost", 0)
            for member in members
            if member["type"] not in ("vm", "fileshare")
        )
        target_cost += sum(
            rec_by_vm.get(vm, {}).get(
                "estimated_monthly_cost_usd",
                rec_by_vm.get(vm, {}).get("estimated_monthly_cost", 0),
            )
            for vm in component
            if vm not in vms_with_assessed_workloads
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
                "cost": rec.get(
                    "estimated_monthly_cost_usd",
                    rec.get("estimated_monthly_cost", 0),
                ),
                "readiness": rec.get("migration_readiness", "Unknown"),
                "workload_types": sorted({
                    member["type"]
                    for member in workload_members_by_vm.get(vm_name, [])
                } or {"general_compute"}),
            })

        component_summary = _component_summary(members)
        environments = {
            _classify_environment(vm_by_name.get(vm_name, {}).get("folder", ""))
            for vm_name in component
        }
        environment = "DevTest" if environments == {"DevTest"} else "Production"

        groups.append({
            "id": group_id,
            "name": app_name,
            "application_type": "Custom",
            "architecture_pattern": "n-tier",
            "environment": environment,
            "vm_count": len(component),
            "vms": vm_details,
            "member_count": len(members),
            "members": members,
            "component_summary": component_summary,
            "dependencies": internal_deps,
            "dependency_count": len(internal_deps),
            "workload_types": sorted(group_wl_types),
            "total_monthly_cost": round(source_vm_cost, 2),
            "target_monthly_cost": round(target_cost, 2),
            "complexity_score": complexity,
            "criticality": criticality,
            "grouping_method": "dependency" if any(v in adj for v in component) else "folder",
        })

    # Allocate shared storage cost across applications that consume it. This
    # avoids multiplying a shared datastore's full target cost in fleet totals.
    fileshare_usage = Counter(
        member["name"].lower()
        for group in groups
        for member in group["members"]
        if member["type"] == "fileshare"
    )
    for group in groups:
        allocated_storage_cost = 0.0
        for member in group["members"]:
            if member["type"] != "fileshare":
                continue
            usage_count = max(fileshare_usage[member["name"].lower()], 1)
            member["shared"] = usage_count > 1
            member["shared_by_application_count"] = usage_count
            member["allocated_monthly_cost"] = round(
                member.get("monthly_cost", 0) / usage_count,
                2,
            )
            allocated_storage_cost += member["allocated_monthly_cost"]
        group["target_monthly_cost"] = round(
            group["target_monthly_cost"] + allocated_storage_cost,
            2,
        )

    groups.sort(key=lambda g: (-g["complexity_score"], -g["vm_count"]))

    return groups


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _extract_deps(workload_data: dict | None) -> list[dict]:
    if not workload_data:
        return []
    return workload_data.get("result", {}).get("dependencies", [])


def _get_workload_members_by_vm(
    workload_data: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Build assessed heterogeneous members from workload recommendations."""
    members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not workload_data:
        return members

    supported_types = {"database", "webapp", "container", "orchestrator"}
    seen: set[str] = set()
    for recommendation in workload_data.get("recommendations", []):
        member_type = recommendation.get("workload_type", "")
        vm_name = recommendation.get("vm_name", "")
        if member_type not in supported_types or not vm_name:
            continue

        workload_name = recommendation.get("workload_name", "") or member_type
        member_id = f"{member_type}:{vm_name}:{workload_name}".lower()
        if member_id in seen:
            continue
        seen.add(member_id)

        members[vm_name].append({
            "id": member_id,
            "type": member_type,
            "name": workload_name,
            "source_vm": vm_name,
            "source_engine": recommendation.get("source_engine", ""),
            "source_version": recommendation.get("source_version", ""),
            "target_service": recommendation.get("recommended_azure_service", ""),
            "target_sku": recommendation.get("recommended_sku", ""),
            "migration_approach": recommendation.get("migration_approach", ""),
            "migration_complexity": recommendation.get("migration_complexity", ""),
            "readiness": "Assessed",
            "monthly_cost": recommendation.get("estimated_monthly_cost_usd", 0),
            "confidence": recommendation.get("confidence", 0),
        })

    for vm_members in members.values():
        vm_members.sort(key=lambda member: (member["type"], member["name"].lower()))
    return members


def _get_fileshare_recommendations(
    workload_data: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    recommendations: dict[str, dict[str, Any]] = {}
    if not workload_data:
        return recommendations
    for recommendation in workload_data.get("recommendations", []):
        if recommendation.get("workload_type") != "fileshare":
            continue
        name = recommendation.get("workload_name", "")
        if name.lower().startswith("file share:"):
            name = name.split(":", 1)[1].strip()
        if name:
            recommendations[name.lower()] = recommendation
    return recommendations


def _build_vm_member(vm: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    vm_name = vm.get("name", "unknown")
    return {
        "id": f"vm:{vm_name}".lower(),
        "type": "vm",
        "name": vm_name,
        "source_vm": vm_name,
        "source_engine": vm.get("guest_os_family", ""),
        "source_version": vm.get("guest_os", ""),
        "target_service": "Azure Virtual Machine",
        "target_sku": recommendation.get("recommended_vm_sku", ""),
        "migration_approach": "rehost",
        "migration_complexity": "low",
        "readiness": recommendation.get("migration_readiness", "Unknown"),
        "monthly_cost": recommendation.get(
            "estimated_monthly_cost_usd",
            recommendation.get("estimated_monthly_cost", 0),
        ),
        "confidence": recommendation.get("confidence_score", 0),
    }


def _build_fileshare_member(
    datastore: dict[str, Any],
    recommendation: dict[str, Any] | None,
) -> dict[str, Any]:
    recommendation = recommendation or {}
    name = datastore.get("name", "unknown")
    return {
        "id": f"fileshare:{name}".lower(),
        "type": "fileshare",
        "name": name,
        "source_vm": "",
        "source_engine": datastore.get("type", "vmfs"),
        "source_version": f"{round(datastore.get('capacity_gb', 0) or 0)} GB",
        "target_service": recommendation.get("recommended_azure_service", "Azure Files"),
        "target_sku": recommendation.get("recommended_sku", ""),
        "migration_approach": recommendation.get("migration_approach", "replatform"),
        "migration_complexity": recommendation.get("migration_complexity", "low"),
        "readiness": "Assessed",
        "monthly_cost": recommendation.get("estimated_monthly_cost_usd", 0),
        "confidence": recommendation.get("confidence", 0),
    }


def _component_summary(members: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(member["type"] for member in members)
    return {
        "virtual_machines": counts["vm"],
        "web_apps": counts["webapp"],
        "databases": counts["database"],
        "containers": counts["container"],
        "orchestrators": counts["orchestrator"],
        "file_shares": counts["fileshare"],
    }


def _classify_environment(folder_name: str) -> str:
    if re.search(r"dev|test|staging|qa|sandbox|lab", folder_name, re.IGNORECASE):
        return "DevTest"
    return "Production"


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
