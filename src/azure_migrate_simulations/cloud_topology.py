"""Cloud Topology Diagram — generate Azure architecture from discovered infrastructure.

Translates discovered on-prem VMware VMs, workloads, and network dependencies
into a proposed Azure architecture diagram organised by Cloud Adoption Framework
(CAF) landing zones and scored by Well-Architected Framework (WAF) pillars.

Key functions:
    generate_cloud_topology()  — main entry point, returns full topology dict
    generate_mermaid()         — produces a Mermaid flowchart string
    compute_waf_scores()       — per-resource WAF pillar scores
    get_waf_assessment()       — detailed WAF breakdown for one resource

No external database is required — all CAF classification rules, WAF scoring
formulas, and infrastructure cost tables are maintained inline.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from azure_migrate_simulations.vulnerability_sla import _match_os


# ---------------------------------------------------------------------------
# Region cost multipliers (duplicated from web/app.py to keep module standalone)
# ---------------------------------------------------------------------------

_REGION_MULTIPLIERS: dict[str, float] = {
    "eastus": 1.0, "eastus2": 1.0, "southcentralus": 1.01,
    "westus2": 1.02, "westus3": 1.01, "centralus": 1.01,
    "northcentralus": 1.01, "westcentralus": 1.03, "westus": 1.04,
    "canadacentral": 1.05, "canadaeast": 1.07,
    "brazilsouth": 1.45, "brazilsoutheast": 1.48,
    "northeurope": 1.12, "westeurope": 1.15,
    "uksouth": 1.14, "ukwest": 1.16,
    "francecentral": 1.18, "francesouth": 1.20,
    "germanywestcentral": 1.16, "germanynorth": 1.22,
    "switzerlandnorth": 1.28, "switzerlandwest": 1.32,
    "norwayeast": 1.18, "norwaywest": 1.22,
    "swedencentral": 1.15, "polandcentral": 1.16,
    "italynorth": 1.18, "spaincentral": 1.17,
    "southeastasia": 1.10, "eastasia": 1.14,
    "japaneast": 1.18, "japanwest": 1.20,
    "australiaeast": 1.20, "australiasoutheast": 1.22, "australiacentral": 1.22,
    "koreacentral": 1.16, "koreasouth": 1.18,
    "centralindia": 0.88, "southindia": 0.90, "westindia": 0.92,
    "jioindiawest": 0.91,
    "uaenorth": 1.22, "uaecentral": 1.25, "qatarcentral": 1.24,
    "southafricanorth": 1.30, "southafricawest": 1.35, "israelcentral": 1.22,
}


def _get_region_multiplier(region: str) -> float:
    """Return the cost multiplier for *region* relative to East US (1.0)."""
    return _REGION_MULTIPLIERS.get(region, 1.0)


# ---------------------------------------------------------------------------
# Optional infrastructure components — hardcoded East US PAYG base prices
# ---------------------------------------------------------------------------

_OPTIONAL_COMPONENTS: dict[str, dict[str, Any]] = {
    "azure_firewall": {
        "name": "Azure Firewall Standard",
        "monthly_cost_base": 912.0,
        "landing_zone_type": "connectivity",
        "subnet_type": "firewall",
    },
    "bastion": {
        "name": "Azure Bastion Standard",
        "monthly_cost_base": 139.0,
        "landing_zone_type": "connectivity",
        "subnet_type": "gateway",
    },
    "load_balancer": {
        "name": "Standard Load Balancer",
        "monthly_cost_base": 18.0,
        "landing_zone_type": "application",
        "subnet_type": "general_compute",
    },
    "vpn_gateway": {
        "name": "VPN Gateway (S2S)",
        "monthly_cost_base": 138.0,
        "landing_zone_type": "connectivity",
        "subnet_type": "gateway",
    },
}


# ---------------------------------------------------------------------------
# Landing zone colour palette
# ---------------------------------------------------------------------------

_LZ_COLOURS: dict[str, str] = {
    "connectivity": "#0078d4",
    "identity": "#6366f1",
    "management": "#8b5cf6",
    "production": "#10b981",
    "devtest": "#f59e0b",
    "attention": "#ef4444",
}

_DEV_TEST_PATTERN = re.compile(
    r"dev|test|staging|qa|sandbox|lab", re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# CAF environment classifier
# ---------------------------------------------------------------------------

def _classify_environment(folder_name: str | None) -> str:
    """Classify a vCenter folder into a CAF environment.

    Returns ``"devtest"`` if the folder name matches common dev/test patterns,
    ``"production"`` otherwise (safe default — per clarification Q4).
    """
    if not folder_name:
        return "production"
    if _DEV_TEST_PATTERN.search(folder_name):
        return "devtest"
    return "production"


# ---------------------------------------------------------------------------
# Resource builder
# ---------------------------------------------------------------------------

_WORKLOAD_TYPE_MAP: dict[str, str] = {
    "database": "database",
    "webapp": "webapp",
    "container": "container",
    "orchestrator": "orchestrator",
}


def _safe_id(raw: str) -> str:
    """Sanitise a string for use as a vis-network / Mermaid node ID.

    Replaces any character that is not alphanumeric or underscore with an
    underscore, then collapses multiple underscores.
    """
    return re.sub(r'_+', '_', re.sub(r'[^a-zA-Z0-9_]', '_', raw)).strip('_')


def _build_cloud_resource(
    vm: dict[str, Any],
    recommendation: dict[str, Any],
    workload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a discovered VM + recommendation + optional workload to a CloudResource dict."""
    vm_name = vm.get("name", "unknown")
    readiness = recommendation.get("migration_readiness", "Unknown")

    # Determine resource type and Azure service
    if workload:
        wl_type = workload.get("workload_type", "")
        resource_type = _WORKLOAD_TYPE_MAP.get(wl_type, "vm")
        azure_service = workload.get("recommended_azure_service", "Azure VM")
    else:
        resource_type = "vm"
        azure_service = "Azure VM"

    azure_sku = recommendation.get("recommended_vm_sku", "")
    monthly_cost = recommendation.get("estimated_monthly_cost_usd", 0.0)

    # Sanitise the ID — VM names can contain brackets, spaces, parentheses
    # Workload suffix ensures uniqueness when the same VM has multiple workloads
    safe_name = _safe_id(vm_name)
    wl_suffix = ""
    if workload:
        wl_name = workload.get("workload_name", "")
        wl_suffix = f"_{_safe_id(wl_name)}" if wl_name else ""

    return {
        "id": f"res_{resource_type}_{safe_name}{wl_suffix}",
        "source_vm_name": vm_name,
        "source_workload_name": workload.get("workload_name") if workload else None,
        "azure_service": azure_service,
        "azure_sku": azure_sku,
        "monthly_cost": round(monthly_cost, 2),
        "migration_readiness": readiness,
        "resource_type": resource_type,
        "landing_zone_id": "",   # populated by _build_landing_zones
        "subnet_id": "",         # populated by _build_vnets_and_subnets
        "waf_scores": {
            "reliability": None,
            "security": None,
            "cost_optimisation": None,
            "operational_excellence": None,
            "performance_efficiency": None,
        },
    }


# ---------------------------------------------------------------------------
# Landing zone builder
# ---------------------------------------------------------------------------

def _build_landing_zones(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build CAF-aligned landing zones and cloud resources from discovery data.

    Returns (landing_zones, all_resources).
    """
    rec_by_vm: dict[str, dict] = {r["vm_name"]: r for r in recommendations}
    wl_by_vm: dict[str, list[dict]] = {}
    if workload_data and workload_data.get("recommendations"):
        for wl in workload_data["recommendations"]:
            wl_by_vm.setdefault(wl.get("vm_name", ""), []).append(wl)

    # Group resources by environment
    env_resources: dict[str, list[dict]] = {
        "production": [],
        "devtest": [],
        "attention": [],
    }
    all_resources: list[dict] = []

    # Track seen IDs to ensure uniqueness
    seen_ids: set[str] = set()

    def _add_resource(resource: dict, env_key: str) -> None:
        # Ensure unique ID — append counter suffix if duplicate
        base_id = resource["id"]
        unique_id = base_id
        counter = 2
        while unique_id in seen_ids:
            unique_id = f"{base_id}_{counter}"
            counter += 1
        resource["id"] = unique_id
        seen_ids.add(unique_id)
        env_resources[env_key].append(resource)
        all_resources.append(resource)

    for vm in vms:
        vm_name = vm.get("name", "")
        rec = rec_by_vm.get(vm_name, {})
        readiness = rec.get("migration_readiness", "Unknown")

        # Classify into environment
        if readiness == "Not Ready":
            env_key = "attention"
        else:
            env_key = _classify_environment(vm.get("folder", ""))

        # Build cloud resources — one per workload, or one VM if no workloads
        vm_workloads = wl_by_vm.get(vm_name, [])
        if vm_workloads:
            for wl in vm_workloads:
                resource = _build_cloud_resource(vm, rec, wl)
                _add_resource(resource, env_key)
        else:
            resource = _build_cloud_resource(vm, rec)
            _add_resource(resource, env_key)

    # Build landing zones (platform + application)
    landing_zones: list[dict] = []

    # Platform zones — always present
    landing_zones.append({
        "id": "lz-connectivity",
        "name": "Connectivity",
        "type": "connectivity",
        "environment": None,
        "colour": _LZ_COLOURS["connectivity"],
        "resource_groups": [],
        "resources": [],
        "aggregate_cost": 0.0,
    })
    landing_zones.append({
        "id": "lz-identity",
        "name": "Identity",
        "type": "identity",
        "environment": None,
        "colour": _LZ_COLOURS["identity"],
        "resource_groups": [],
        "resources": [],
        "aggregate_cost": 0.0,
    })
    landing_zones.append({
        "id": "lz-management",
        "name": "Management",
        "type": "management",
        "environment": None,
        "colour": _LZ_COLOURS["management"],
        "resource_groups": [],
        "resources": [],
        "aggregate_cost": 0.0,
    })

    # Application zones
    app_zone_defs = [
        ("lz-prod", "App-LZ-Production", "production"),
        ("lz-devtest", "App-LZ-Dev/Test", "devtest"),
        ("lz-attention", "Requires Attention", "attention"),
    ]
    for lz_id, lz_name, env_key in app_zone_defs:
        resources = env_resources.get(env_key, [])
        if not resources and env_key != "production":
            continue  # skip empty non-production zones (but always show production)
        for r in resources:
            r["landing_zone_id"] = lz_id
        cost = sum(r["monthly_cost"] for r in resources)
        landing_zones.append({
            "id": lz_id,
            "name": lz_name,
            "type": "application",
            "environment": env_key,
            "colour": _LZ_COLOURS.get(env_key, "#8b949e"),
            "resource_groups": [],
            "resources": resources,
            "aggregate_cost": round(cost, 2),
        })

    return landing_zones, all_resources


# ---------------------------------------------------------------------------
# VNet & subnet builder
# ---------------------------------------------------------------------------

_SUBNET_COUNTER = 0


def _next_subnet_cidr(vnet_base: int, subnet_idx: int) -> str:
    """Generate a /24 CIDR from a VNet base octet and subnet index."""
    return f"10.{vnet_base}.{subnet_idx}.0/24"


def _build_vnets_and_subnets(
    landing_zones: list[dict[str, Any]],
    workload_data: dict[str, Any] | None,
) -> None:
    """Mutate landing zones to add VNet and subnet structures."""
    vnet_base = 0

    for lz in landing_zones:
        lz_type = lz["type"]

        if lz_type == "connectivity":
            # Hub VNet with gateway and firewall subnets
            vnet = {
                "id": "vnet-hub",
                "name": f"hub-vnet (10.{vnet_base}.0.0/16)",
                "address_space": f"10.{vnet_base}.0.0/16",
                "subnets": [
                    {
                        "id": "sn-gateway",
                        "name": "GatewaySubnet",
                        "workload_type": "gateway",
                        "address_range": _next_subnet_cidr(vnet_base, 0),
                        "resources": [],
                    },
                    {
                        "id": "sn-firewall",
                        "name": "AzureFirewallSubnet",
                        "workload_type": "firewall",
                        "address_range": _next_subnet_cidr(vnet_base, 1),
                        "resources": [],
                    },
                ],
            }
            lz["resource_groups"] = [{
                "id": "rg-connectivity",
                "name": "rg-connectivity-001",
                "vnets": [vnet],
            }]
            vnet_base += 1

        elif lz_type in ("identity", "management"):
            # Placeholder — no VMs placed here in v1
            vnet = {
                "id": f"vnet-{lz_type}",
                "name": f"{lz_type}-vnet (10.{vnet_base}.0.0/16)",
                "address_space": f"10.{vnet_base}.0.0/16",
                "subnets": [{
                    "id": f"sn-{lz_type}-default",
                    "name": f"{lz_type}-default",
                    "workload_type": "general_compute",
                    "address_range": _next_subnet_cidr(vnet_base, 0),
                    "resources": [],
                }],
            }
            lz["resource_groups"] = [{
                "id": f"rg-{lz_type}",
                "name": f"rg-{lz_type}-001",
                "vnets": [vnet],
            }]
            vnet_base += 1

        elif lz_type == "application":
            resources = lz.get("resources", [])
            if not resources:
                continue

            # Group resources by workload type for subnet creation
            by_type: dict[str, list[dict]] = {}
            for r in resources:
                wt = r.get("resource_type", "vm")
                sn_type = _WORKLOAD_TYPE_MAP.get(wt, "general_compute")
                by_type.setdefault(sn_type, []).append(r)
            # Ensure VMs without workload discovery get general_compute
            if "vm" in by_type:
                by_type.setdefault("general_compute", []).extend(by_type.pop("vm"))

            subnets: list[dict] = []
            sn_idx = 0
            for wl_type, sn_resources in sorted(by_type.items()):
                sn_id = f"sn-{lz['id']}-{wl_type}-{sn_idx:03d}"
                for r in sn_resources:
                    r["subnet_id"] = sn_id
                subnets.append({
                    "id": sn_id,
                    "name": f"{wl_type}-subnet",
                    "workload_type": wl_type,
                    "address_range": _next_subnet_cidr(vnet_base, sn_idx),
                    "resources": [r["id"] for r in sn_resources],
                })
                sn_idx += 1

            env_label = lz.get("environment", "app")
            vnet = {
                "id": f"vnet-{lz['id']}",
                "name": f"spoke-{env_label}-vnet (10.{vnet_base}.0.0/16)",
                "address_space": f"10.{vnet_base}.0.0/16",
                "subnets": subnets,
            }
            lz["resource_groups"] = [{
                "id": f"rg-{lz['id']}",
                "name": f"rg-{env_label}-001",
                "vnets": [vnet],
            }]
            vnet_base += 1


# ---------------------------------------------------------------------------
# Topology edge builder
# ---------------------------------------------------------------------------

def _build_topology_edges(
    workload_data: dict[str, Any] | None,
    resource_id_map: dict[str, dict[str, Any]],
    resource_lz_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Build vis-network edges from workload dependency data."""
    edges: list[dict[str, Any]] = []
    if not workload_data or not workload_data.get("dependencies"):
        return edges

    seen: set[tuple[str, str]] = set()
    for dep in workload_data["dependencies"]:
        src_vm = dep.get("source_vm", "")
        dst_vm = dep.get("target_vm", dep.get("dest_vm", ""))
        if not src_vm or not dst_vm:
            continue

        # Find resource IDs matching these VMs (use sanitised IDs)
        src_id = f"res_vm_{_safe_id(src_vm)}"
        dst_id = f"res_vm_{_safe_id(dst_vm)}"
        if src_id not in resource_id_map or dst_id not in resource_id_map:
            continue

        pair = (min(src_id, dst_id), max(src_id, dst_id))
        if pair in seen:
            continue
        seen.add(pair)

        src_lz = resource_lz_map.get(src_id, "")
        dst_lz = resource_lz_map.get(dst_id, "")
        cross_zone = src_lz != dst_lz

        port = dep.get("port", "")
        protocol = dep.get("protocol", "TCP")
        service_type = dep.get("service_type", "")
        label = f"{protocol}/{port}" if port else protocol

        edges.append({
            "from": src_id,
            "to": dst_id,
            "label": label,
            "dashes": cross_zone,
            "arrows": "to",
            "color": "#f59e0b" if cross_zone else "#8b949e",
            "title": f"{label} {'(cross-zone via Hub VNet)' if cross_zone else ''}",
        })

    return edges


# ---------------------------------------------------------------------------
# Container builder (for vis-network beforeDrawing bounding boxes)
# ---------------------------------------------------------------------------

def _build_containers(
    landing_zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten the LZ → RG → VNet → Subnet hierarchy into container dicts."""
    containers: list[dict[str, Any]] = []

    for lz in landing_zones:
        lz_children: list[str] = []

        for rg in lz.get("resource_groups", []):
            for vnet in rg.get("vnets", []):
                vnet_children: list[str] = []

                for subnet in vnet.get("subnets", []):
                    containers.append({
                        "id": subnet["id"],
                        "label": subnet["name"],
                        "type": "subnet",
                        "parent": vnet["id"],
                        "color": "#30363d",
                        "children": subnet.get("resources", []),
                    })
                    vnet_children.append(subnet["id"])

                containers.append({
                    "id": vnet["id"],
                    "label": vnet["name"],
                    "type": "vnet",
                    "parent": lz["id"],
                    "color": "#58a6ff",
                    "children": vnet_children,
                })
                lz_children.append(vnet["id"])

        containers.append({
            "id": lz["id"],
            "label": lz["name"],
            "type": "landing_zone",
            "parent": None,
            "color": lz.get("colour", "#8b949e"),
            "children": lz_children,
        })

    return containers


# ---------------------------------------------------------------------------
# Vis-network node builder
# ---------------------------------------------------------------------------

def _build_vis_nodes(
    resources: list[dict[str, Any]],
    landing_zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert CloudResource dicts to vis-network node dicts.

    Pre-computes initial x,y positions laid out by subnet within each
    landing zone so the diagram is readable without physics.
    """
    # ── Layout parameters ──
    COLS = 6            # nodes per row within a subnet
    COL_GAP = 180       # horizontal pixels between columns
    ROW_GAP = 100       # vertical pixels between rows
    SUBNET_GAP = 200    # extra vertical gap between subnet groups
    LZ_GAP = 400        # extra vertical gap between landing zones

    # Collect subnets per landing zone (ordered)
    lz_subnets: dict[str, list[str]] = {}
    subnet_lz: dict[str, str] = {}
    for lz in landing_zones:
        sn_list: list[str] = []
        for rg in lz.get("resource_groups", []):
            for vnet in rg.get("vnets", []):
                for sn in vnet.get("subnets", []):
                    sn_list.append(sn["id"])
                    subnet_lz[sn["id"]] = lz["id"]
        lz_subnets[lz["id"]] = sn_list

    # Group resources by subnet
    subnet_resources: dict[str, list[dict]] = {}
    for r in resources:
        sn = r.get("subnet_id", "default")
        subnet_resources.setdefault(sn, []).append(r)

    # Compute y-origin for each subnet (stack vertically with gaps)
    subnet_y: dict[str, int] = {}
    y_cursor = 0
    for lz in landing_zones:
        for sn_id in lz_subnets.get(lz["id"], []):
            subnet_y[sn_id] = y_cursor
            res_count = len(subnet_resources.get(sn_id, []))
            rows = max(1, math.ceil(res_count / COLS))
            y_cursor += rows * ROW_GAP + SUBNET_GAP
        y_cursor += LZ_GAP  # gap between landing zones

    # Build nodes with positions
    nodes: list[dict[str, Any]] = []
    subnet_node_idx: dict[str, int] = {}

    for r in resources:
        readiness = r.get("migration_readiness", "Unknown")
        cost = r.get("monthly_cost", 0)
        # Short label — truncate at 18 chars
        short_label = r["source_vm_name"]
        if len(short_label) > 18:
            short_label = short_label[:16] + "…"

        tooltip = (
            f"{r['source_vm_name']}\n"
            f"Service: {r['azure_service']}\n"
            f"SKU: {r['azure_sku']}\n"
            f"Cost: ${cost:,.0f}/mo\n"
            f"Readiness: {readiness}"
        )

        sn_id = r.get("subnet_id", "default")
        lz_id = r.get("landing_zone_id", "") or subnet_lz.get(sn_id, "")

        node_idx = subnet_node_idx.get(sn_id, 0)
        subnet_node_idx[sn_id] = node_idx + 1

        col = node_idx % COLS
        row = node_idx // COLS
        x = col * COL_GAP
        y = subnet_y.get(sn_id, 0) + row * ROW_GAP

        nodes.append({
            "id": r["id"],
            "label": short_label,
            "group": r["resource_type"],
            "title": tooltip,
            "container": sn_id,
            "resource_type": r["resource_type"],
            "source_vm": r["source_vm_name"],
            "azure_sku": r["azure_sku"],
            "monthly_cost": cost,
            "readiness": readiness,
            "waf_scores": r.get("waf_scores", {}),
            "landing_zone_id": lz_id,
            "x": x,
            "y": y,
        })
    return nodes


# ---------------------------------------------------------------------------
# Cost summary builder
# ---------------------------------------------------------------------------

def _build_cost_summary(
    landing_zones: list[dict[str, Any]],
    optional_flags: dict[str, bool],
    region: str,
) -> dict[str, Any]:
    """Aggregate costs per landing zone plus optional component costs."""
    region_mult = _get_region_multiplier(region)
    by_lz: dict[str, dict[str, Any]] = {}
    total = 0.0

    for lz in landing_zones:
        cost = round(lz.get("aggregate_cost", 0.0) * region_mult, 2)
        by_lz[lz["id"]] = {"name": lz["name"], "cost": cost}
        total += cost

    # Optional component costs
    opt_cost = 0.0
    for comp_id, enabled in optional_flags.items():
        if enabled and comp_id in _OPTIONAL_COMPONENTS:
            comp = _OPTIONAL_COMPONENTS[comp_id]
            adjusted = round(comp["monthly_cost_base"] * region_mult, 2)
            opt_cost += adjusted
            # Add to the parent landing zone cost
            lz_type = comp["landing_zone_type"]
            for lz_id, lz_data in by_lz.items():
                if lz_type == "connectivity" and "connectivity" in lz_id.lower():
                    lz_data["cost"] = round(lz_data["cost"] + adjusted, 2)
                    break
                elif lz_type == "application" and "prod" in lz_id.lower():
                    lz_data["cost"] = round(lz_data["cost"] + adjusted, 2)
                    break

    total += opt_cost

    return {
        "by_landing_zone": by_lz,
        "total": round(total, 2),
        "optional_components_cost": round(opt_cost, 2),
    }


# ---------------------------------------------------------------------------
# WAF scoring (placeholder — computed per resource, wired in Phase 5 / US3)
# ---------------------------------------------------------------------------

def compute_waf_scores(
    vm: dict[str, Any],
    recommendation: dict[str, Any],
    vuln_data: dict[str, Any] | None = None,
    enrichment_data: dict[str, Any] | None = None,
    perf_data: dict[str, Any] | None = None,
    whatif_overrides: dict[str, Any] | None = None,
) -> dict[str, int | None]:
    """Compute WAF pillar scores for a single resource.

    Returns a dict with five pillar keys, each ``int`` (0–100) or ``None``
    when data is insufficient.  Full scoring logic is implemented in Phase 5
    (US3); this stub provides base scores from discoverable vCenter data.
    """
    # --- Reliability (proxy — HA/backup not discoverable from vCenter) ---
    reliability = 35
    if vm.get("power_state") == "poweredOn":
        reliability += 10
    if perf_data:
        reliability += 10
    reliability = min(reliability, 100)

    # --- Security ---
    from datetime import date as _date
    os_entry = _match_os(vm.get("guest_os", ""), _date.today())
    sev = os_entry.get("severity", "unknown")
    if sev == "critical":
        security = 20
    elif sev == "high":
        security = 40
    elif sev == "warning":
        security = 55
    elif sev == "ok":
        security = 65
    else:
        security = 50
    if enrichment_data:
        security = min(security + 15, 100)
    if vm.get("guest_os_family") == "windows":
        security = min(security + 10, 100)

    # --- Cost Optimisation ---
    confidence = recommendation.get("confidence_score", recommendation.get("confidence", 50))
    cost_opt = int((confidence / 100) * 60)
    if vm.get("guest_os_family") == "windows":
        cost_opt = min(cost_opt + 15, 100)
    if whatif_overrides and vm.get("name") in whatif_overrides:
        cost_opt = min(cost_opt + 15, 100)

    # --- Operational Excellence ---
    has_enrichment = enrichment_data is not None
    has_perf = perf_data is not None
    if not has_enrichment and not has_perf:
        op_ex = None
    else:
        op_ex = 0
        if has_enrichment:
            op_ex += 30
        if has_perf:
            op_ex += 20
        tools_status = vm.get("vmware_tools_status", "")
        if tools_status and "running" in str(tools_status).lower():
            op_ex += 15
        op_ex = min(op_ex + 15, 100)  # base buffer

    # --- Performance Efficiency ---
    if not has_perf:
        perf_eff = None
    else:
        # Stub: use a moderate default — detailed percentile scoring in US3
        perf_eff = 60

    return {
        "reliability": reliability,
        "security": security,
        "cost_optimisation": cost_opt,
        "operational_excellence": op_ex,
        "performance_efficiency": perf_eff,
    }


# ---------------------------------------------------------------------------
# WAF summary aggregator
# ---------------------------------------------------------------------------

def _build_waf_summary(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-pillar averages across all resources."""
    pillars = [
        "reliability", "security", "cost_optimisation",
        "operational_excellence", "performance_efficiency",
    ]
    sums: dict[str, float] = {p: 0.0 for p in pillars}
    counts: dict[str, int] = {p: 0 for p in pillars}
    insufficient: dict[str, int] = {p: 0 for p in pillars}

    for r in resources:
        waf = r.get("waf_scores", {})
        for p in pillars:
            val = waf.get(p)
            if val is not None:
                sums[p] += val
                counts[p] += 1
            else:
                insufficient[p] += 1

    avg_scores: dict[str, int | None] = {}
    for p in pillars:
        if counts[p] > 0:
            avg_scores[p] = round(sums[p] / counts[p])
        else:
            avg_scores[p] = None

    return {
        "scores": avg_scores,
        "resource_count": len(resources),
        "insufficient_data_count": insufficient,
    }


# ---------------------------------------------------------------------------
# Mermaid diagram generator
# ---------------------------------------------------------------------------

def _mermaid_id(raw_id: str) -> str:
    """Sanitise an ID for Mermaid — replace hyphens and special chars with underscores."""
    return re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9_]", "_", raw_id)).strip("_")


def _mermaid_label(raw: str) -> str:
    """Sanitise a display label for Mermaid.

    Mermaid interprets ``[``, ``]``, ``(``, ``)``, ``{``, ``}`` as shape
    delimiters even inside quoted labels in some renderers.
    """
    return (
        raw
        .replace('"', "'")
        .replace("[", "\u27E8")
        .replace("]", "\u27E9")
        .replace("{", "\u27E8")
        .replace("}", "\u27E9")
        .replace("<", "\u2039")
        .replace(">", "\u203A")
    )


def generate_mermaid(topology: dict[str, Any]) -> str:
    """Generate a Mermaid flowchart TB string from topology data.

    Uses a single level of subgraphs (one per landing zone) to avoid the
    deeply-nested subgraph issues that break many Mermaid renderers.
    Resource nodes are listed flat inside their landing zone subgraph.
    """
    lines: list[str] = ["flowchart TB"]

    nodes = topology.get("nodes", [])
    containers = topology.get("containers", [])

    # Build lookup: node_id → landing_zone container id
    container_map: dict[str, dict] = {c["id"]: c for c in containers}
    node_to_lz: dict[str, str] = {}
    for n in nodes:
        # Walk up from the node's container to find the landing_zone ancestor
        cid = n.get("container", "")
        lz_id = n.get("landing_zone_id", "")
        if lz_id:
            node_to_lz[n["id"]] = lz_id
        else:
            # Walk the container hierarchy
            visited: set[str] = set()
            while cid and cid in container_map and cid not in visited:
                visited.add(cid)
                c = container_map[cid]
                if c.get("type") == "landing_zone":
                    node_to_lz[n["id"]] = cid
                    break
                cid = c.get("parent", "")

    # Group nodes by landing zone
    lz_nodes: dict[str, list[dict]] = {}
    for n in nodes:
        lz = node_to_lz.get(n["id"], "lz_other")
        lz_nodes.setdefault(lz, []).append(n)

    # Get landing zone containers (sorted: platform first, then app)
    lz_containers = [c for c in containers if c.get("type") == "landing_zone"]

    # Emit one subgraph per landing zone
    for lz in lz_containers:
        lz_sid = _mermaid_id(lz["id"])
        lz_label = _mermaid_label(lz["label"])
        lz_node_list = lz_nodes.get(lz["id"], [])

        lines.append(f"    subgraph {lz_sid}[{lz_label}]")

        if lz_node_list:
            for n in lz_node_list:
                nid = _mermaid_id(n["id"])
                nlabel = _mermaid_label(n.get("label", n["id"]))
                cost = n.get("monthly_cost", 0)
                lines.append(f"        {nid}({nlabel} ${cost:.0f}/mo)")
        else:
            # Empty LZ — add a placeholder
            ph = f"{lz_sid}_ph"
            lines.append(f"        {ph}(empty)")
            lines.append(f"        style {ph} fill:none,stroke:none,color:#666")

        lines.append("    end")

    # Edges
    for edge in topology.get("edges", []):
        src = _mermaid_id(edge["from"])
        dst = _mermaid_id(edge["to"])
        label = edge.get("label", "")
        if label:
            safe_lbl = _mermaid_label(label)
            lines.append(f"    {src} -->|{safe_lbl}| {dst}")
        else:
            lines.append(f"    {src} --> {dst}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Optional component node builder
# ---------------------------------------------------------------------------

def _build_optional_nodes_and_update(
    optional_flags: dict[str, bool],
    landing_zones: list[dict[str, Any]],
    region: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build vis-network nodes and component metadata for enabled optional infra."""
    region_mult = _get_region_multiplier(region)
    opt_nodes: list[dict[str, Any]] = []
    opt_meta: list[dict[str, Any]] = []

    for comp_id, comp_def in _OPTIONAL_COMPONENTS.items():
        enabled = optional_flags.get(comp_id, False)
        adjusted_cost = round(comp_def["monthly_cost_base"] * region_mult, 2)

        meta = {
            "id": comp_id,
            "name": comp_def["name"],
            "monthly_cost_base": comp_def["monthly_cost_base"],
            "enabled": enabled,
            "landing_zone_id": (
                "lz-connectivity"
                if comp_def["landing_zone_type"] == "connectivity"
                else "lz-prod"
            ),
        }
        opt_meta.append(meta)

        if enabled:
            node_id = f"res_{_safe_id(comp_id)}"
            resource_type = (
                "security" if "firewall" in comp_id
                else "networking"
            )
            # Find the target subnet
            target_lz_id = meta["landing_zone_id"]
            target_subnet = ""
            for lz in landing_zones:
                if lz["id"] == target_lz_id:
                    for rg in lz.get("resource_groups", []):
                        for vnet in rg.get("vnets", []):
                            for sn in vnet.get("subnets", []):
                                if sn["workload_type"] == comp_def["subnet_type"]:
                                    target_subnet = sn["id"]
                                    sn["resources"].append(node_id)
                                    break

            opt_nodes.append({
                "id": node_id,
                "label": comp_def["name"],
                "group": resource_type,
                "title": f"{comp_def['name']}\nCost: ${adjusted_cost:,.0f}/mo\n(Optional component)",
                "container": target_subnet,
                "resource_type": resource_type,
                "source_vm": "",
                "azure_sku": "",
                "monthly_cost": adjusted_cost,
                "readiness": "N/A",
                "waf_scores": {},
                "landing_zone_id": meta["landing_zone_id"],
            })

    return opt_nodes, opt_meta


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def generate_cloud_topology(
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    workload_data: dict[str, Any] | None = None,
    region: str = "eastus",
    optional_flags: dict[str, bool] | None = None,
    enrichment_data: dict[str, dict] | None = None,
    perf_history: dict[str, list] | None = None,
    whatif_overrides: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Generate a complete cloud topology from discovery data.

    Parameters
    ----------
    vms : list[dict]
        VM dicts from ``_data["vms"]``.
    recommendations : list[dict]
        Recommendation dicts from ``_data["recommendations"]``.
    workload_data : dict | None
        Workload discovery results (``_workload_data``).
    region : str
        Target Azure region for cost multipliers.
    optional_flags : dict[str, bool] | None
        Which optional infrastructure components are enabled.
    enrichment_data : dict | None
        Enrichment telemetry keyed by VM name.
    perf_history : dict | None
        Performance history keyed by VM name.
    whatif_overrides : dict | None
        What-if overrides keyed by VM name.

    Returns
    -------
    dict matching the ``/api/cloud-topology`` JSON contract.
    """
    if optional_flags is None:
        optional_flags = {}

    # Build resources and landing zones
    landing_zones, all_resources = _build_landing_zones(
        vms, recommendations, workload_data,
    )

    # Compute WAF scores for each resource
    rec_by_vm = {r["vm_name"]: r for r in recommendations}
    vm_by_name = {v["name"]: v for v in vms}
    for r in all_resources:
        vm = vm_by_name.get(r["source_vm_name"], {})
        rec = rec_by_vm.get(r["source_vm_name"], {})
        vm_enrichment = enrichment_data.get(r["source_vm_name"]) if enrichment_data else None
        vm_perf = perf_history.get(r["source_vm_name"]) if perf_history else None
        r["waf_scores"] = compute_waf_scores(
            vm, rec,
            vuln_data=None,
            enrichment_data=vm_enrichment,
            perf_data=vm_perf,
            whatif_overrides=whatif_overrides,
        )

    # Build VNets and subnets
    _build_vnets_and_subnets(landing_zones, workload_data)

    # Build optional component nodes
    opt_nodes, opt_meta = _build_optional_nodes_and_update(
        optional_flags, landing_zones, region,
    )

    # Build containers (for bounding boxes)
    containers = _build_containers(landing_zones)

    # Build vis-network nodes
    vis_nodes = _build_vis_nodes(all_resources, landing_zones)
    vis_nodes.extend(opt_nodes)

    # Build resource lookups for edges
    resource_id_map = {r["id"]: r for r in all_resources}
    resource_lz_map = {r["id"]: r["landing_zone_id"] for r in all_resources}

    # Build edges
    edges = _build_topology_edges(workload_data, resource_id_map, resource_lz_map)

    # Build cost summary
    cost_summary = _build_cost_summary(landing_zones, optional_flags, region)

    # WAF summary
    waf_summary = _build_waf_summary(all_resources)

    # Build topology dict
    topology: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_vm_count": len(vms),
        "source_workload_count": (
            len(workload_data.get("recommendations", []))
            if workload_data else 0
        ),
        "total_monthly_cost": cost_summary["total"],
        "containers": containers,
        "nodes": vis_nodes,
        "edges": edges,
        "cost_summary": cost_summary,
        "waf_summary": waf_summary,
        "optional_components": opt_meta,
        "mermaid": "",  # filled below
        # T061a: Progressive rendering hint for large datasets
        "progressive": len(vms) > 500,
    }

    # Generate Mermaid
    topology["mermaid"] = generate_mermaid(topology)

    return topology


# ---------------------------------------------------------------------------
# WAF detail assessment (consumed by /api/cloud-topology/waf/<resource_id>)
# ---------------------------------------------------------------------------

_WAF_RECOMMENDATIONS: dict[str, list[dict[str, Any]]] = {
    "Reliability": [
        {
            "title": "Enable Availability Zones",
            "description": "Deploy this VM across availability zones for 99.99% SLA. Current single-instance SLA is 99.9%.",
            "impact": "high",
            "effort": "low",
        },
        {
            "title": "Configure Azure Backup",
            "description": "Enable Azure Backup with a daily policy to protect against data loss and ransomware.",
            "impact": "high",
            "effort": "low",
        },
        {
            "title": "Use Zone-Redundant Storage",
            "description": "Switch managed disks to ZRS for cross-zone data resilience.",
            "impact": "medium",
            "effort": "low",
        },
    ],
    "Security": [
        {
            "title": "Upgrade End-of-Life OS",
            "description": "This VM runs an OS past end of support. Upgrade to receive security patches.",
            "impact": "high",
            "effort": "medium",
        },
        {
            "title": "Enable Microsoft Defender for Servers",
            "description": "Enable Defender for Servers P2 for advanced threat detection and vulnerability scanning.",
            "impact": "high",
            "effort": "low",
        },
        {
            "title": "Enable Transparent Data Encryption",
            "description": "For database workloads, ensure TDE is enabled to encrypt data at rest.",
            "impact": "high",
            "effort": "low",
        },
        {
            "title": "Configure Network Security Groups",
            "description": "Apply NSG rules to restrict traffic to only required ports and sources.",
            "impact": "medium",
            "effort": "medium",
        },
    ],
    "Cost Optimisation": [
        {
            "title": "Apply Azure Hybrid Benefit",
            "description": "Reuse existing Windows Server or SQL Server licenses to eliminate compute charges.",
            "impact": "high",
            "effort": "low",
        },
        {
            "title": "Consider Reserved Instances",
            "description": "Commit to 1-year or 3-year reserved instances for up to 72% savings on stable workloads.",
            "impact": "high",
            "effort": "low",
        },
        {
            "title": "Right-Size the VM",
            "description": "Performance data suggests this VM may be over-provisioned. Consider a smaller SKU.",
            "impact": "medium",
            "effort": "low",
        },
    ],
    "Operational Excellence": [
        {
            "title": "Enable Azure Monitor",
            "description": "Configure Azure Monitor and Log Analytics for centralised logging and alerting.",
            "impact": "high",
            "effort": "medium",
        },
        {
            "title": "Upload Enrichment Data",
            "description": "Import telemetry from your APM tool (Dynatrace, New Relic, etc.) to improve assessment accuracy.",
            "impact": "medium",
            "effort": "low",
        },
        {
            "title": "Enable Update Management",
            "description": "Use Azure Update Manager to automate OS and application patching.",
            "impact": "medium",
            "effort": "low",
        },
    ],
    "Performance Efficiency": [
        {
            "title": "Run Performance Collector",
            "description": "Start the performance collector to capture CPU, memory, and IOPS metrics for data-driven sizing.",
            "impact": "high",
            "effort": "low",
        },
        {
            "title": "Enable Accelerated Networking",
            "description": "Enable accelerated networking for this VM to reduce latency and improve throughput.",
            "impact": "medium",
            "effort": "low",
        },
        {
            "title": "Review Disk IOPS Requirements",
            "description": "Ensure the recommended disk type meets the workload's IOPS needs.",
            "impact": "medium",
            "effort": "medium",
        },
    ],
}


def get_waf_assessment(
    resource_id: str,
    topology_data: dict[str, Any],
    vms: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    enrichment_data: dict[str, dict] | None = None,
    perf_history: dict[str, list] | None = None,
    vuln_data: dict[str, Any] | None = None,
    whatif_overrides: dict[str, dict] | None = None,
) -> dict[str, Any] | None:
    """Return a detailed WAF assessment for a single resource."""
    # Find the resource in the topology
    node = None
    for n in topology_data.get("nodes", []):
        if n["id"] == resource_id:
            node = n
            break
    if node is None:
        return None

    vm_name = node.get("source_vm", "")
    waf = node.get("waf_scores", {})

    pillars: list[dict[str, Any]] = []
    pillar_names = [
        ("reliability", "Reliability"),
        ("security", "Security"),
        ("cost_optimisation", "Cost Optimisation"),
        ("operational_excellence", "Operational Excellence"),
        ("performance_efficiency", "Performance Efficiency"),
    ]

    _missing_prompts = {
        "operational_excellence": "Upload enrichment data from your APM tool or start the performance collector to score this pillar.",
        "performance_efficiency": "Run the performance collector (sidebar → Start) to capture CPU, memory, and IOPS metrics.",
    }

    for key, display_name in pillar_names:
        score = waf.get(key)
        status = "scored" if score is not None else "insufficient_data"

        data_sources: list[str] = []
        if score is not None:
            data_sources.append("vcenter_discovery")
            if enrichment_data and vm_name in (enrichment_data or {}):
                data_sources.append("enrichment")
            if perf_history and vm_name in (perf_history or {}):
                data_sources.append("perf_history")

        recs = _WAF_RECOMMENDATIONS.get(display_name, [])

        pillars.append({
            "pillar": display_name,
            "score": score,
            "status": status,
            "data_sources_used": data_sources,
            "missing_data_prompt": _missing_prompts.get(key) if status == "insufficient_data" else None,
            "recommendations": recs,
        })

    return {
        "resource_id": resource_id,
        "resource_label": vm_name,
        "azure_service": node.get("azure_sku", ""),
        "azure_sku": node.get("azure_sku", ""),
        "pillars": pillars,
    }
