"""Application-centric Azure landing-zone architecture generation.

The production Azure Migrate App-Centric Assessments service resolves one
Cloud Topology Design (CTD) catalogue entry for every application and migration
strategy.  This module mirrors that contract locally: a heterogeneous assessed
application (machines, web apps, databases, containers, and file shares) is
resolved to an N-tier Azure architecture and returned as a renderable graph.

The catalogue metadata is intentionally vendored.  The service also resolves
from a versioned local catalogue at runtime rather than depending on GitHub.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


CATALOGUE_SOURCE = (
    "https://github.com/azure-core/"
    "CloudTopologyDesign-ArchitectureCatalog/tree/main/catalogue"
)
CTD_SERVICE_SOURCE = (
    "https://dev.azure.com/msazure/One/_git/"
    "AzureMigrate-AppCentricAssessments"
)
CATALOGUE_VERSION = "1.0.0"
CATALOGUE_COMMIT = "1f04b44fb7dcc200ba47ccc122bf7984cca24d81"

_CATALOGUE_ENTRY_IDS = [
    "n-tier-rehost-low",
    "n-tier-rehost-medium",
    "n-tier-rehost-high",
    "n-tier-replatform-low",
    "n-tier-replatform-medium",
    "n-tier-replatform-high",
]

_STRATEGIES: dict[str, dict[str, str]] = {
    "lift_and_shift": {
        "service_name": "LiftAndShift",
        "label": "Lift & Shift",
        "migration_intent": "rehost",
        "description": "Retain machine boundaries and move compute to Azure VMs.",
    },
    "paas_preferred": {
        "service_name": "PaaSPreferred",
        "label": "PaaS Preferred",
        "migration_intent": "replatform",
        "description": "Prefer assessed managed services with VM fallback when required.",
    },
    "paas_centric": {
        "service_name": "PaaSCentric",
        "label": "PaaS Centric",
        "migration_intent": "replatform",
        "description": "Maximise managed-service targets while retaining unsupported fallbacks.",
    },
}

_STRATEGY_ALIASES = {
    "liftandshift": "lift_and_shift",
    "lift-and-shift": "lift_and_shift",
    "paaspreferred": "paas_preferred",
    "paas-preferred": "paas_preferred",
    "paascentric": "paas_centric",
    "paas-centric": "paas_centric",
}

_REGION_MULTIPLIERS = {
    "eastus": 1.0,
    "eastus2": 1.0,
    "centralus": 1.01,
    "westus2": 1.02,
    "westus3": 1.01,
    "canadacentral": 1.05,
    "northeurope": 1.12,
    "westeurope": 1.15,
    "uksouth": 1.14,
    "centralindia": 0.88,
    "southeastasia": 1.10,
    "australiaeast": 1.20,
    "japaneast": 1.18,
}

_NODE_COLOURS = {
    "application": "#0078d4",
    "networking": "#38bdf8",
    "security": "#f59e0b",
    "monitoring": "#8b5cf6",
    "backup-and-recovery": "#64748b",
    "compute": "#10b981",
    "data": "#ef4444",
    "storage": "#06b6d4",
    "ai": "#7c3aed",
}


def _safe_id(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9_]", "_", value)).strip("_")


def _normalise_strategy(strategy: str) -> str:
    value = (strategy or "paas_preferred").strip()
    normalised = _STRATEGY_ALIASES.get(value.lower(), value.lower())
    if normalised not in _STRATEGIES:
        valid = ", ".join(_STRATEGIES)
        raise ValueError(f"Unknown landing-zone strategy '{strategy}'. Valid values: {valid}")
    return normalised


def _criticality_bucket(criticality: str) -> str:
    value = (criticality or "").strip().lower()
    if "tier-1" in value or "mission" in value or value == "critical" or value == "high":
        return "high"
    if "tier-3" in value or value == "low":
        return "low"
    return "medium"


def _catalogue_entry_id(strategy: str, criticality: str) -> str:
    intent = _STRATEGIES[strategy]["migration_intent"]
    return f"n-tier-{intent}-{_criticality_bucket(criticality)}"


def _catalogue_module_id(service: str) -> str:
    """Map an assessed Azure target to a CTD service-module identifier."""
    value = service.lower()
    mappings = [
        ("red hat openshift", "aro"),
        ("kubernetes", "aks"),
        ("container apps", "container-apps"),
        ("container instances", "container-instances"),
        ("functions", "functions"),
        ("app service", "app-service"),
        ("sql managed instance", "sql-managed-instance"),
        ("sql database", "azure-sql-database"),
        ("sql server on azure vm", "sql-vm"),
        ("mysql", "mysql-flexible"),
        ("postgresql", "postgresql-flexible"),
        ("cosmos", "cosmos-db"),
        ("redis", "azure-managed-redis"),
        ("netapp", "azure-netapp-files"),
        ("blob", "blob-storage"),
        ("azure files", "azure-files"),
        ("managed disk", "managed-disk"),
        ("virtual machine", "virtual-machine"),
        ("azure vm", "virtual-machine"),
    ]
    for marker, module_id in mappings:
        if marker in value:
            return module_id
    return _safe_id(service).lower() or "virtual-machine"


def _domain_for_member(member_type: str) -> str:
    if member_type == "database":
        return "data"
    if member_type == "fileshare":
        return "storage"
    return "compute"


def _members_for_strategy(
    application: dict[str, Any],
    strategy: str,
) -> list[dict[str, Any]]:
    members = application.get("members", [])
    if strategy == "lift_and_shift":
        return [member for member in members if member.get("type") in ("vm", "fileshare")]

    assessed_hosts = {
        member.get("source_vm", "")
        for member in members
        if member.get("type") not in ("vm", "fileshare")
    }
    return [
        member
        for member in members
        if member.get("type") != "vm"
        or member.get("source_vm", "") not in assessed_hosts
    ]


def _platform_slots(environment: str) -> list[dict[str, Any]]:
    slots = [
        {
            "slot": "networking/foundation",
            "domain": "networking",
            "origin": "architecture-required",
            "count": 1,
            "group": ["vnet", "subnet", "nsg", "route-table"],
            "depends_on": [],
            "resolved_target": "Azure Virtual Network",
            "monthly_cost": 0.0,
            "members": [],
            "machines": [],
            "placement": None,
        },
        {
            "slot": "networking/ingress",
            "domain": "networking",
            "origin": "architecture-required",
            "count": 1,
            "group": ["application-gateway"],
            "depends_on": ["networking/foundation"],
            "resolved_target": "Application Gateway WAF v2",
            "monthly_cost": 0.0,
            "members": [],
            "machines": [],
            "placement": {"subnet": "snet-ingress"},
        },
        {
            "slot": "security",
            "domain": "security",
            "origin": "architecture-required",
            "count": 1,
            "group": ["key-vault", "managed-identity", "private-endpoint"],
            "depends_on": ["networking/foundation"],
            "resolved_target": "Identity, secrets & private endpoints",
            "monthly_cost": 0.0,
            "members": [],
            "machines": [],
            "placement": {"subnet": "snet-private-endpoints"},
        },
        {
            "slot": "monitoring",
            "domain": "monitoring",
            "origin": "architecture-required",
            "count": 1,
            "group": ["log-analytics", "app-insights", "alert-rules"],
            "depends_on": [],
            "resolved_target": "Azure Monitor & Application Insights",
            "monthly_cost": 0.0,
            "members": [],
            "machines": [],
            "placement": None,
        },
    ]
    if environment != "DevTest":
        slots.append({
            "slot": "backup-and-recovery",
            "domain": "backup-and-recovery",
            "origin": "architecture-required",
            "count": 1,
            "group": ["recovery-services-vault", "backup-policy"],
            "depends_on": [],
            "resolved_target": "Azure Backup",
            "monthly_cost": 0.0,
            "members": [],
            "machines": [],
            "placement": None,
        })
    return slots


def _resolved_slots(
    application: dict[str, Any],
    strategy: str,
    region: str,
) -> list[dict[str, Any]]:
    environment = application.get("environment", "Production")
    slots = _platform_slots(environment)
    selected_members = _members_for_strategy(application, strategy)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for member in selected_members:
        member_type = member.get("type", "vm")
        domain = _domain_for_member(member_type)
        target = member.get("target_service", "") or "Azure Virtual Machine"
        if strategy == "lift_and_shift" and member_type == "vm":
            target = "Azure Virtual Machine"
        grouped[(domain, target)].append(member)

    compute_slots: list[str] = []
    multiplier = _REGION_MULTIPLIERS.get(region, 1.0)
    for (domain, target), members in sorted(grouped.items()):
        slot_id = f"{domain}/{_safe_id(target).lower()}"
        skus = sorted({member.get("target_sku", "") for member in members if member.get("target_sku")})
        sku = skus[0] if len(skus) == 1 else (f"{len(skus)} assessed SKUs" if skus else "")
        if domain == "compute":
            compute_slots.append(slot_id)

        if domain == "compute":
            dependencies = ["networking/ingress", "security"]
            subnet = "snet-compute"
        elif domain == "data":
            dependencies = ["security", *compute_slots]
            subnet = "snet-data"
        else:
            dependencies = ["security", *compute_slots]
            subnet = "snet-storage"

        monthly_cost = sum(
            member.get("allocated_monthly_cost", member.get("monthly_cost", 0))
            for member in members
        ) * multiplier
        slots.append({
            "slot": slot_id,
            "domain": domain,
            "origin": "migrated",
            "count": len(members),
            "group": [_catalogue_module_id(target)],
            "depends_on": list(dict.fromkeys(dependencies)),
            "resolved_target": target,
            "sku_id": sku,
            "monthly_cost": round(monthly_cost, 2),
            "members": members,
            "machines": sorted({
                member.get("source_vm", "")
                for member in members
                if member.get("source_vm")
            }),
            "placement": {"subnet": subnet},
        })
    return slots


def _architecture_graph(
    application: dict[str, Any],
    slots: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    app_node_id = f"application_{_safe_id(application['id'])}"
    nodes = [{
        "id": app_node_id,
        "label": application["name"],
        "group": "application",
        "level": 0,
        "title": f"Application: {application['name']}\nMembers: {application.get('member_count', 0)}",
        "member_count": application.get("member_count", 0),
        "color": _NODE_COLOURS["application"],
        "shape": "box",
    }]
    edges: list[dict[str, Any]] = []
    slot_node_ids: dict[str, str] = {}

    domain_levels = {
        "networking": 1,
        "security": 2,
        "monitoring": 2,
        "backup-and-recovery": 2,
        "compute": 3,
        "data": 4,
        "storage": 4,
    }
    for slot in slots:
        node_id = f"slot_{_safe_id(application['id'])}_{_safe_id(slot['slot'])}"
        slot_node_ids[slot["slot"]] = node_id
        target = slot.get("resolved_target", slot["slot"])
        sku = slot.get("sku_id", "")
        count = slot.get("count", 1) or 1
        label = target
        if sku:
            label += f"\n{sku}"
        if count > 1:
            label += f"\n× {count}"
        nodes.append({
            "id": node_id,
            "label": label,
            "group": slot["domain"],
            "level": domain_levels.get(slot["domain"], 3),
            "title": (
                f"{target}\nSlot: {slot['slot']}\n"
                f"Source members: {len(slot.get('members', []))}\n"
                f"Cost: ${slot.get('monthly_cost', 0):,.0f}/mo"
            ),
            "member_count": len(slot.get("members", [])),
            "monthly_cost": slot.get("monthly_cost", 0),
            "color": _NODE_COLOURS.get(slot["domain"], "#8b949e"),
            "shape": "box" if slot["domain"] in ("compute", "data", "storage") else "ellipse",
        })

    seen_edges: set[tuple[str, str]] = set()
    for slot in slots:
        target_id = slot_node_ids[slot["slot"]]
        dependencies = slot.get("depends_on", [])
        if not dependencies:
            pair = (app_node_id, target_id)
            if pair not in seen_edges:
                edges.append({"from": app_node_id, "to": target_id, "arrows": "to"})
                seen_edges.add(pair)
        for dependency in dependencies:
            source_id = slot_node_ids.get(dependency)
            if not source_id:
                continue
            pair = (source_id, target_id)
            if pair in seen_edges:
                continue
            edges.append({"from": source_id, "to": target_id, "arrows": "to"})
            seen_edges.add(pair)
    return nodes, edges


def _subnets_for_slots(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    subnet_names = {
        slot.get("placement", {}).get("subnet")
        for slot in slots
        if slot.get("placement")
    }
    address_octet = 1
    subnets = []
    for subnet_name in sorted(name for name in subnet_names if name):
        subnets.append({
            "name": subnet_name,
            "address_prefix": f"10.20.{address_octet}.0/24",
        })
        address_octet += 1
    return subnets


def _resolve_application(
    application: dict[str, Any],
    strategy: str,
    region: str,
) -> dict[str, Any]:
    criticality = application.get("criticality", "Tier-2")
    entry_id = _catalogue_entry_id(strategy, criticality)
    strategy_data = _STRATEGIES[strategy]
    slots = _resolved_slots(application, strategy, region)
    nodes, edges = _architecture_graph(application, slots)
    total_cost = round(sum(slot.get("monthly_cost", 0) for slot in slots), 2)
    environment = application.get("environment", "Production")
    lz_id = f"lz-{_safe_id(application['id']).lower()}"

    return {
        "id": application["id"],
        "name": application["name"],
        "application_type": application.get("application_type", "Custom"),
        "owner_application_id": application["id"],
        "criticality": criticality,
        "environment": environment,
        "strategy": strategy_data["service_name"],
        "strategy_label": strategy_data["label"],
        "architecture_entry_id": entry_id,
        "catalogue_version": CATALOGUE_VERSION,
        "description": strategy_data["description"],
        "tags": {
            "architecture_pattern": "n-tier",
            "migration_intent": strategy_data["migration_intent"],
            "criticality": _criticality_bucket(criticality),
            "environment": "dev-test" if environment == "DevTest" else "production",
            "hybrid_multicloud": "cloud-only",
        },
        "component_summary": application.get("component_summary", {}),
        "source_member_count": application.get("member_count", 0),
        "members": application.get("members", []),
        "dependencies": application.get("dependencies", []),
        "monthly_cost": total_cost,
        "landing_zone": {
            "id": lz_id,
            "name": f"{application['name']} Application Landing Zone",
            "type": "application",
            "environment": environment,
            "resource_group": f"rg-{_safe_id(application['name']).lower()}-{region}-001",
            "vnet": {
                "name": f"vnet-{_safe_id(application['name']).lower()}-{region}",
                "address_space": "10.20.0.0/16",
                "subnets": _subnets_for_slots(slots),
            },
        },
        "reasoning": [
            {
                "title": "Application boundary",
                "detail": (
                    f"Keeps {application.get('member_count', 0)} assessed members "
                    "together as one deployment and migration unit."
                ),
            },
            {
                "title": "Catalogue selection",
                "detail": (
                    f"Selected {entry_id} from architecture pattern n-tier using "
                    f"{strategy_data['label']} and {criticality}."
                ),
            },
            {
                "title": "Network isolation",
                "detail": "Uses dedicated ingress, compute, data, storage, and private-endpoint subnets.",
            },
        ],
        "slots": slots,
        "nodes": nodes,
        "edges": edges,
    }


def _apply_ai_feasibility_extension(
    application: dict[str, Any],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """Replace a base view with its reviewed AI-ready architecture variant."""
    result = application
    extension = assessment.get("architecture_extension", {})
    category = assessment.get("solution_category", {})
    cost_estimate = assessment.get("cost_estimate", {})
    base_scenario = cost_estimate.get("scenarios", {}).get("base", {})
    ai_monthly_cost = float(base_scenario.get("budget_with_reserve_usd", 0) or 0)
    base_monthly_cost = float(result.get("monthly_cost", 0) or 0)
    base_entry_id = result.get("architecture_entry_id", "n-tier")

    result["ai_ready"] = True
    result["base_architecture_entry_id"] = base_entry_id
    result["architecture_entry_id"] = f"{base_entry_id}+ai-ready"
    result["base_monthly_cost"] = round(base_monthly_cost, 2)
    result["ai_monthly_cost"] = round(ai_monthly_cost, 2)
    result["monthly_cost"] = round(base_monthly_cost + ai_monthly_cost, 2)
    result["tags"]["ai_pattern"] = category.get("id", "")
    result["tags"]["architecture_variant"] = "ai-ready"
    result["ai_feasibility"] = {
        "assessment_id": assessment.get("id", ""),
        "assessment_version": assessment.get("version", 1),
        "status": assessment.get("status", "needs_evidence"),
        "disposition": assessment.get("executive_decision", {}).get("disposition", "needs_evidence"),
        "category_id": category.get("id", ""),
        "category_label": category.get("label", "AI capability"),
        "business_outcome": assessment.get("customer_intent", {}).get("business_outcome", ""),
        "pricing_status": cost_estimate.get("pricing_status", "illustrative_unquoted"),
    }
    result["ai_extension"] = extension

    previous_slot = "security"
    ai_slots = []
    for component in extension.get("components", []):
        slot_id = f"ai/{_safe_id(component.get('id', 'service')).lower()}"
        ai_slots.append({
            "slot": slot_id,
            "domain": "ai",
            "origin": "proposed-ai",
            "count": 1,
            "group": [component.get("id", "ai-service")],
            "depends_on": [previous_slot],
            "resolved_target": component.get("name", "Azure AI service"),
            "monthly_cost": component.get("monthly_cost_usd", 0),
            "members": [],
            "machines": [],
            "placement": {"subnet": "snet-ai"},
            "purpose": component.get("role", ""),
            "provenance": "proposed",
        })
        previous_slot = slot_id
    result["slots"].extend(ai_slots)

    subnets = result.get("landing_zone", {}).get("vnet", {}).setdefault("subnets", [])
    if not any(item.get("name") == "snet-ai" for item in subnets):
        subnets.append({"name": "snet-ai", "address_prefix": "10.20.5.0/24"})

    app_node_id = f"application_{_safe_id(result['id'])}"
    previous_node_id = app_node_id
    for index, component in enumerate(extension.get("components", [])):
        node_id = f"ai_{_safe_id(result['id'])}_{_safe_id(component.get('id', str(index)))}"
        result["nodes"].append({
            "id": node_id,
            "label": component.get("name", "Azure AI service"),
            "group": "ai",
            "level": 3 + index,
            "title": f"Proposed: {component.get('role', '')}",
            "monthly_cost": component.get("monthly_cost_usd", 0),
            "color": _NODE_COLOURS["ai"],
            "shape": "box",
            "provenance": "proposed",
        })
        result["edges"].append({
            "from": previous_node_id,
            "to": node_id,
            "arrows": "to",
            "label": "proposed AI flow",
        })
        previous_node_id = node_id

    result["reasoning"].append({
        "title": "AI-ready extension",
        "detail": (
            f"Replaced the base diagram with the {category.get('label', 'AI')} variant from "
            f"AI Feasibility Assessment {assessment.get('id', '')} revision {assessment.get('version', 1)}. "
            "All AI components and flows are proposed; customer data access and production readiness remain subject to the assessment gates."
        ),
    })
    return result


def generate_application_landing_zones(
    applications: list[dict[str, Any]],
    strategy: str = "paas_preferred",
    region: str = "eastus",
    ai_assessments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve a CTD application landing zone for every assessed application."""
    normalised_strategy = _normalise_strategy(strategy)
    ai_by_application: dict[str, dict[str, Any]] = {}
    for assessment in ai_assessments or []:
        application_id = assessment.get("application", {}).get("id", "")
        if application_id and application_id not in ai_by_application:
            ai_by_application[application_id] = assessment

    resolved = []
    for application in applications:
        architecture = _resolve_application(application, normalised_strategy, region)
        assessment = ai_by_application.get(application.get("id", ""))
        if assessment:
            architecture = _apply_ai_feasibility_extension(architecture, assessment)
        resolved.append(architecture)
    total_members = sum(app["source_member_count"] for app in resolved)
    total_cost = round(sum(app["monthly_cost"] for app in resolved), 2)
    ai_monthly_cost = round(sum(app.get("ai_monthly_cost", 0) for app in resolved), 2)

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "strategy": normalised_strategy,
        "strategy_label": _STRATEGIES[normalised_strategy]["label"],
        "application_count": len(resolved),
        "applications": resolved,
        "summary": {
            "application_count": len(resolved),
            "source_member_count": total_members,
            "monthly_cost": total_cost,
            "catalogue_entry_count": len({app["architecture_entry_id"] for app in resolved}),
            "ai_ready_application_count": sum(bool(app.get("ai_ready")) for app in resolved),
            "ai_monthly_cost": ai_monthly_cost,
        },
        "catalogue": {
            "source": CATALOGUE_SOURCE,
            "service_source": CTD_SERVICE_SOURCE,
            "version": CATALOGUE_VERSION,
            "commit": CATALOGUE_COMMIT,
            "architecture_pattern": "n-tier",
            "available_entry_ids": _CATALOGUE_ENTRY_IDS,
            "available_strategies": [
                {
                    "id": strategy_id,
                    "service_name": data["service_name"],
                    "label": data["label"],
                }
                for strategy_id, data in _STRATEGIES.items()
            ],
        },
    }