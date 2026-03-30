"""Dependency-aware wave planner using topological sort.

Uses TCP dependency graph from workload discovery to sequence migration waves
so that databases and shared services migrate before their dependents.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


# ---------------------------------------------------------------------------
# Workload-type priority (lower = earlier wave)
# ---------------------------------------------------------------------------
_WORKLOAD_PRIORITY = {
    "shared_infrastructure": 0,  # DNS, AD, file servers
    "database": 1,
    "orchestrator": 2,
    "container": 3,
    "webapp": 3,
    "general_compute": 4,
}


def generate_smart_wave_plan(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    wave_count: int = 4,
    region: str = "eastus",
    pricing_model: str = "payg",
) -> dict[str, Any]:
    """Generate a dependency-aware wave plan.

    Algorithm:
    1. Build directed dependency graph from workload discovery
    2. Detect strongly connected components (cycles) → collapse
    3. Topological sort on condensed DAG
    4. Assign layers (depth from sources)
    5. Apply workload-type overrides
    6. Compress layers into requested wave count
    7. Balance wave sizes
    """
    vm_names = {v.get("name", "") for v in vms}
    rec_by_vm = {r.get("vm_name", ""): r for r in recommendations}

    # 1. Build dependency graph
    deps = _extract_dependencies(workload_data)
    adj: dict[str, set[str]] = defaultdict(set)   # vm → set of VMs it depends on (targets)
    rev: dict[str, set[str]] = defaultdict(set)    # vm → set of VMs that depend on it
    for d in deps:
        src = d.get("source_vm", "")
        tgt = d.get("target_vm", "")
        if src in vm_names and tgt in vm_names and src != tgt:
            adj[src].add(tgt)
            rev[tgt].add(src)

    # 2. Detect SCCs (Tarjan's simplified via iterative Kosaraju)
    sccs = _find_sccs(vm_names, adj, rev)
    # Map each VM → its SCC group id
    vm_to_scc: dict[str, int] = {}
    for i, scc in enumerate(sccs):
        for vm in scc:
            vm_to_scc[vm] = i

    # Build condensed DAG (SCC → SCC edges)
    scc_adj: dict[int, set[int]] = defaultdict(set)
    for src, targets in adj.items():
        src_scc = vm_to_scc.get(src)
        for tgt in targets:
            tgt_scc = vm_to_scc.get(tgt)
            if src_scc is not None and tgt_scc is not None and src_scc != tgt_scc:
                scc_adj[src_scc].add(tgt_scc)

    # 3. Topological sort + layer assignment on condensed DAG
    scc_layers = _assign_layers(len(sccs), scc_adj)

    # 4. Map layers to VMs, apply workload-type overrides
    vm_layer: dict[str, int] = {}
    vm_reasons: dict[str, str] = {}
    workload_types = _get_vm_workload_types(workload_data)

    for vm_name in vm_names:
        scc_id = vm_to_scc.get(vm_name)
        base_layer = scc_layers.get(scc_id, 0) if scc_id is not None else 0

        # Apply workload priority override
        wl_type = workload_types.get(vm_name, "general_compute")
        wl_priority = _WORKLOAD_PRIORITY.get(wl_type, 4)

        # If dependency layer puts it later than workload type suggests, use dependency layer
        # If workload type puts it earlier, use workload type (databases first)
        final_layer = max(base_layer, wl_priority) if base_layer > 0 else wl_priority

        # Readiness check: Not Ready → last layer
        rec = rec_by_vm.get(vm_name, {})
        readiness = rec.get("migration_readiness", "Ready")
        if readiness == "Not Ready":
            final_layer = 99
            vm_reasons[vm_name] = "Not Ready — requires attention before migration"
        elif scc_id is not None and len(sccs[scc_id]) > 1:
            vm_reasons[vm_name] = f"Circular dependency with {', '.join(sorted(sccs[scc_id] - {vm_name})[:3])} — migrating together"
        elif vm_name in rev and rev[vm_name]:
            dependents = sorted(rev[vm_name])[:3]
            vm_reasons[vm_name] = f"Dependency target — {', '.join(dependents)} depend on this VM"
        elif vm_name in adj and adj[vm_name]:
            targets = sorted(adj[vm_name])[:3]
            vm_reasons[vm_name] = f"Depends on {', '.join(targets)} (scheduled in earlier wave)"
        elif wl_type == "database":
            vm_reasons[vm_name] = "Database workload — scheduled in early wave"
        else:
            vm_reasons[vm_name] = "No dependencies detected — assigned by workload type"

        vm_layer[vm_name] = final_layer

    # 5. Compress layers into wave_count waves
    unique_layers = sorted(set(vm_layer.values()))
    if 99 in unique_layers:
        unique_layers.remove(99)

    wave_count = max(1, min(wave_count, len(vm_names)))
    layer_to_wave: dict[int, int] = {}
    if unique_layers:
        bins = max(1, len(unique_layers))
        per_bin = max(1, bins // wave_count)
        for i, layer in enumerate(unique_layers):
            wave_num = min(i // per_bin + 1, wave_count)
            layer_to_wave[layer] = wave_num
    layer_to_wave[99] = wave_count  # Not Ready → last wave

    # 6. Build wave assignments
    waves: dict[int, list[dict]] = defaultdict(list)
    for vm_name in sorted(vm_names):
        layer = vm_layer.get(vm_name, 0)
        wave_num = layer_to_wave.get(layer, wave_count)
        rec = rec_by_vm.get(vm_name, {})
        waves[wave_num].append({
            "vm_name": vm_name,
            "reason": vm_reasons.get(vm_name, ""),
            "workload_type": workload_types.get(vm_name, "general_compute"),
            "readiness": rec.get("migration_readiness", "Unknown"),
        })

    # Ensure all wave numbers from 1..wave_count exist
    wave_summary = []
    for w in range(1, wave_count + 1):
        wave_vms = waves.get(w, [])
        wave_summary.append({
            "wave": w,
            "vm_count": len(wave_vms),
            "vms": [v["vm_name"] for v in wave_vms],
            "details": wave_vms,
        })

    return {
        "wave_count": wave_count,
        "total_vms": len(vm_names),
        "dependency_count": len(deps),
        "circular_dependencies": sum(1 for scc in sccs if len(scc) > 1),
        "region": region,
        "pricing_model": pricing_model,
        "waves": wave_summary,
    }


def check_dependency_conflicts(
    vm_name: str,
    target_wave: int,
    wave_plan: dict[str, Any],
    workload_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Check if moving a VM to a target wave violates dependency ordering.

    Returns list of conflict warnings (empty = no conflicts).
    """
    deps = _extract_dependencies(workload_data)
    conflicts = []

    # Build current wave assignment
    vm_wave: dict[str, int] = {}
    for wave in wave_plan.get("waves", []):
        for v in wave.get("vms", []):
            vm_wave[v] = wave["wave"]

    # Check: VMs that depend on this VM should not be in an earlier wave
    for d in deps:
        if d.get("target_vm") == vm_name:
            dependent = d.get("source_vm", "")
            dep_wave = vm_wave.get(dependent, 999)
            if dep_wave < target_wave:
                conflicts.append({
                    "type": "dependent_in_earlier_wave",
                    "vm": dependent,
                    "vm_wave": dep_wave,
                    "target_wave": target_wave,
                    "message": f"'{dependent}' (Wave {dep_wave}) depends on '{vm_name}'. Moving '{vm_name}' to Wave {target_wave} means it migrates after its dependent.",
                })

        # Check: VMs this VM depends on should not be in a later wave
        if d.get("source_vm") == vm_name:
            target = d.get("target_vm", "")
            tgt_wave = vm_wave.get(target, 0)
            if tgt_wave > target_wave:
                conflicts.append({
                    "type": "dependency_in_later_wave",
                    "vm": target,
                    "vm_wave": tgt_wave,
                    "target_wave": target_wave,
                    "message": f"'{vm_name}' depends on '{target}' (Wave {tgt_wave}). Moving to Wave {target_wave} means migrating before its dependency.",
                })

    return conflicts


# ═══════════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _extract_dependencies(workload_data: dict | None) -> list[dict]:
    if not workload_data:
        return []
    result = workload_data.get("result", {})
    return result.get("dependencies", [])


def _get_vm_workload_types(workload_data: dict | None) -> dict[str, str]:
    """Map VM name → primary workload type."""
    types: dict[str, str] = {}
    if not workload_data:
        return types
    result = workload_data.get("result", {})
    for vm_wl in result.get("vm_workloads", []):
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


def _find_sccs(all_nodes: set[str], adj: dict[str, set[str]], rev: dict[str, set[str]]) -> list[set[str]]:
    """Find strongly connected components using Kosaraju's algorithm."""
    visited: set[str] = set()
    finish_order: list[str] = []

    def _dfs(start: str, graph: dict[str, set[str]], vis: set[str], result: list[str]) -> None:
        stack = [start]
        while stack:
            node = stack[-1]
            if node not in vis:
                vis.add(node)
            all_visited = True
            for neighbor in graph.get(node, set()):
                if neighbor not in vis:
                    stack.append(neighbor)
                    all_visited = False
                    break
            if all_visited:
                stack.pop()
                if node not in set(result):
                    result.append(node)

    # Pass 1: DFS on original graph
    for node in all_nodes:
        if node not in visited:
            _dfs(node, adj, visited, finish_order)

    # Pass 2: DFS on reversed graph in reverse finish order
    visited.clear()
    sccs: list[set[str]] = []
    for node in reversed(finish_order):
        if node not in visited:
            component: list[str] = []
            _dfs(node, rev, visited, component)
            sccs.append(set(component))

    return sccs


def _assign_layers(num_sccs: int, scc_adj: dict[int, set[int]]) -> dict[int, int]:
    """Assign topological depth layers to SCCs."""
    in_degree: dict[int, int] = defaultdict(int)
    for i in range(num_sccs):
        in_degree.setdefault(i, 0)
    for src, targets in scc_adj.items():
        for tgt in targets:
            in_degree[tgt] += 1

    # BFS from sources
    queue: deque[int] = deque()
    layers: dict[int, int] = {}
    for node in range(num_sccs):
        if in_degree[node] == 0:
            queue.append(node)
            layers[node] = 0

    while queue:
        node = queue.popleft()
        for neighbor in scc_adj.get(node, set()):
            layers[neighbor] = max(layers.get(neighbor, 0), layers[node] + 1)
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return layers
