"""MCP (Model Context Protocol) server for Azure Migrate Simulations.

Exposes the platform's discovery, assessment, topology, IaC, runbook, and
wave-planning capabilities as MCP tools so that **any** AI agent — GitHub
Copilot, Claude Desktop, Cursor, Windsurf, Continue, Cline, or custom
agents — can iterate on migration artefacts conversationally.

Run standalone:
    python -m azure_migrate_simulations.mcp_server          # stdio (default)
    python -m azure_migrate_simulations.mcp_server --sse     # SSE  (HTTP)

Or via the entry-point:
    dt-migrate-mcp           # stdio
    dt-migrate-mcp --sse     # SSE
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# MCP SDK – the universal agent-integration protocol
# ---------------------------------------------------------------------------
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

logger = logging.getLogger("ams.mcp")

# ---------------------------------------------------------------------------
# Shared helpers – reuse the same data layer as the web app
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = _PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Canonical data files (same as web/app.py)
_VCENTER_DATA_FILE = DATA_DIR / "vcenter_discovery.json"
_WORKLOAD_DATA_FILE = DATA_DIR / "workload_discovery.json"
_WHATIF_OVERRIDES_FILE = DATA_DIR / "whatif_overrides.json"
_WL_WHATIF_OVERRIDES_FILE = DATA_DIR / "workload_whatif_overrides.json"
_PERF_HISTORY_FILE = DATA_DIR / "perf_history.json"
_ENRICHMENT_DATA_FILE = DATA_DIR / "enrichment_data.json"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _get_discovery() -> dict:
    return _load_json(_VCENTER_DATA_FILE)


def _get_workloads() -> dict:
    return _load_json(_WORKLOAD_DATA_FILE)


def _get_whatif() -> dict:
    return _load_json(_WHATIF_OVERRIDES_FILE)


def _get_enrichment() -> dict:
    return _load_json(_ENRICHMENT_DATA_FILE)


def _get_perf() -> dict:
    return _load_json(_PERF_HISTORY_FILE)


# ═══════════════════════════════════════════════════════════════════════════
#  MCP Server definition
# ═══════════════════════════════════════════════════════════════════════════
server = Server("azure-migrate-simulations")


# ---------------------------------------------------------------------------
#  RESOURCES – expose project data as browsable resources
# ---------------------------------------------------------------------------
@server.list_resources()
async def list_resources() -> list[Resource]:
    """Expose data files as MCP resources so agents can browse them."""
    resources: list[Resource] = []
    for fpath in sorted(DATA_DIR.glob("*.json")):
        resources.append(
            Resource(
                uri=f"ams://data/{fpath.name}",
                name=fpath.name,
                mimeType="application/json",
                description=f"Data file: {fpath.name}",
            )
        )
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a data file by its ams:// URI."""
    # uri = "ams://data/vcenter_discovery.json"
    name = uri.split("/")[-1]
    fpath = DATA_DIR / name
    if not fpath.exists() or not fpath.suffix == ".json":
        return json.dumps({"error": f"Resource not found: {uri}"})
    data = _load_json(fpath)
    # Truncate large payloads for agent context windows
    text = json.dumps(data, indent=2, default=str)
    if len(text) > 100_000:
        return text[:100_000] + "\n\n... [truncated — use specific tools to query subsets]"
    return text


# ---------------------------------------------------------------------------
#  TOOLS – the core MCP interface for AI agents
# ---------------------------------------------------------------------------
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Register all MCP tools that agents can call."""
    return [
        # ── Discovery & Inventory ────────────────────────────────────
        Tool(
            name="get_migration_summary",
            description=(
                "Get a high-level summary of the discovered VMware environment: "
                "VM count, host count, total vCPUs, total RAM, total disk, "
                "migration readiness distribution, estimated Azure cost, "
                "and SKU family distribution."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_vms",
            description=(
                "List all discovered VMs with their Azure recommendations. "
                "Supports filtering by readiness, OS, SKU family, or name pattern. "
                "Returns: name, vCPUs, memory, disks, OS, recommended SKU, cost, readiness, confidence."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_readiness": {
                        "type": "string",
                        "description": "Filter by readiness: 'Ready', 'Ready with Conditions', 'Not Ready'",
                    },
                    "filter_os": {
                        "type": "string",
                        "description": "Filter by OS type: 'windows' or 'linux'",
                    },
                    "filter_name": {
                        "type": "string",
                        "description": "Filter by VM name pattern (substring match, case-insensitive)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of VMs to return (default: 50)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_vm_details",
            description=(
                "Get detailed information about a specific VM: compute, storage, "
                "network, performance metrics, Azure recommendation, enrichment data, "
                "what-if overrides, and WAF scores."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "Exact VM name to look up",
                    },
                },
                "required": ["vm_name"],
            },
        ),
        Tool(
            name="list_workloads",
            description=(
                "List all discovered workloads (databases, web apps, containers, "
                "orchestrators) with their Azure PaaS recommendations and migration "
                "playbooks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workload_type": {
                        "type": "string",
                        "description": "Filter: 'database', 'webapp', 'container', 'orchestrator'",
                    },
                },
                "required": [],
            },
        ),

        # ── Cloud Topology Diagram (CTD) ────────────────────────────
        Tool(
            name="generate_cloud_topology",
            description=(
                "Generate a Cloud Topology Diagram (CTD) — a CAF-aligned Azure "
                "landing zone architecture from the discovered estate. Returns "
                "landing zones, VNets, subnets, resource placements, WAF scores, "
                "cost summary, and dependency edges. The agent can iterate on "
                "options (firewall, bastion, VPN, load balancer, region) "
                "until the customer is satisfied."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Target Azure region (default: eastus). Examples: eastus, westus2, westeurope, southeastasia",
                    },
                    "firewall": {
                        "type": "boolean",
                        "description": "Include Azure Firewall in Connectivity zone ($912/mo)",
                    },
                    "bastion": {
                        "type": "boolean",
                        "description": "Include Azure Bastion in Connectivity zone ($139/mo)",
                    },
                    "vpn_gateway": {
                        "type": "boolean",
                        "description": "Include VPN Gateway for site-to-site connectivity ($138/mo)",
                    },
                    "load_balancer": {
                        "type": "boolean",
                        "description": "Include Standard Load Balancer per app landing zone ($18/mo)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_topology_waf_assessment",
            description=(
                "Get the Well-Architected Framework (WAF) assessment for a specific "
                "resource in the cloud topology. Shows scores (0-100) across 5 pillars: "
                "Reliability, Security, Cost Optimisation, Operational Excellence, "
                "Performance Efficiency — with actionable recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {
                        "type": "string",
                        "description": "Cloud resource ID from the topology (e.g. 'res-vm-WebServer01')",
                    },
                },
                "required": ["resource_id"],
            },
        ),
        Tool(
            name="get_topology_mermaid",
            description=(
                "Get the cloud topology as a Mermaid diagram definition that can "
                "be rendered in documentation, markdown, or presentation tools."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── What-If Simulation ──────────────────────────────────────
        Tool(
            name="simulate_vm_whatif",
            description=(
                "Run a what-if simulation for a single VM: override the Azure SKU, "
                "region, or pricing model. Returns cost comparison (original vs override) "
                "with monthly savings/increase. Use this to iterate on right-sizing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {
                        "type": "string",
                        "description": "VM name to simulate",
                    },
                    "sku_override": {
                        "type": "string",
                        "description": "Azure VM SKU to test (e.g. 'Standard_D4s_v5')",
                    },
                    "region": {
                        "type": "string",
                        "description": "Target Azure region",
                    },
                    "pricing_model": {
                        "type": "string",
                        "description": "Pricing: payg, 1yr_ri, 3yr_ri, 1yr_sp, 3yr_sp, ahub, devtest",
                    },
                },
                "required": ["vm_name"],
            },
        ),
        Tool(
            name="simulate_fleet",
            description=(
                "Run a fleet-wide migration simulation: calculate total Azure cost, "
                "generate wave plan, produce 12-month cost projection. "
                "Supports region, pricing model, and wave count parameters."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "Target Azure region (default: eastus)"},
                    "pricing_model": {"type": "string", "description": "Pricing model for all VMs"},
                    "wave_count": {"type": "integer", "description": "Number of migration waves (default: 4)"},
                },
                "required": [],
            },
        ),

        # ── Wave Planning ────────────────────────────────────────────
        Tool(
            name="get_wave_plan",
            description=(
                "Get the current migration wave plan showing which VMs are in "
                "each wave, wave costs, and timeline."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="move_vm_to_wave",
            description=(
                "Move a VM from one migration wave to another. Use this to "
                "rebalance waves or group dependent VMs together."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {"type": "string", "description": "VM name to move"},
                    "target_wave": {"type": "integer", "description": "Target wave number (1-based)"},
                },
                "required": ["vm_name", "target_wave"],
            },
        ),
        Tool(
            name="update_wave_plan",
            description=(
                "Bulk-update the wave plan: move multiple VMs between waves "
                "in a single operation. Accepts a list of {vm_name, target_wave} "
                "assignments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "assignments": {
                        "type": "array",
                        "description": "List of wave assignments",
                        "items": {
                            "type": "object",
                            "properties": {
                                "vm_name": {"type": "string"},
                                "target_wave": {"type": "integer"},
                            },
                            "required": ["vm_name", "target_wave"],
                        },
                    },
                },
                "required": ["assignments"],
            },
        ),

        # ── What-If Overrides (persist choices) ─────────────────────
        Tool(
            name="save_whatif_override",
            description=(
                "Persist a what-if override for a VM: save the chosen SKU, "
                "region, and pricing model so it's used in fleet simulations "
                "and topology generation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {"type": "string", "description": "VM name"},
                    "sku": {"type": "string", "description": "Azure SKU to use"},
                    "region": {"type": "string", "description": "Target region"},
                    "pricing_model": {"type": "string", "description": "Pricing model"},
                },
                "required": ["vm_name"],
            },
        ),
        Tool(
            name="clear_whatif_overrides",
            description="Clear all saved what-if overrides, resetting to default recommendations.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Target Recommendations ──────────────────────────────────
        Tool(
            name="get_sku_catalog",
            description=(
                "Browse the Azure VM SKU catalog: list available SKUs with vCPUs, "
                "memory, max data disks, max IOPS, and monthly cost. Filter by "
                "family (B, D, E, F, M, N, L, etc.) or vCPU range."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "family": {"type": "string", "description": "SKU family filter (e.g. 'D', 'E', 'F')"},
                    "min_vcpus": {"type": "integer", "description": "Minimum vCPU count"},
                    "max_vcpus": {"type": "integer", "description": "Maximum vCPU count"},
                    "min_memory_gb": {"type": "number", "description": "Minimum memory in GB"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_regions",
            description=(
                "List available Azure regions with their cost multipliers. "
                "Use this to compare regional pricing for right-sizing decisions."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Business Case ────────────────────────────────────────────
        Tool(
            name="get_business_case",
            description=(
                "Generate a business case: on-prem TCO vs Azure cost comparison, "
                "ROI, payback period, 3/5-year projection, strategic recommendations."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Enrichment ──────────────────────────────────────────────
        Tool(
            name="get_enrichment_status",
            description=(
                "Check enrichment data coverage: which VMs have monitoring data, "
                "from which tools, and the confidence boost applied."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Vulnerability & SLA ─────────────────────────────────────
        Tool(
            name="get_vulnerability_sla",
            description=(
                "Get OS/software lifecycle analysis: which VMs run end-of-life "
                "operating systems, AHUB eligibility, extended security update "
                "recommendations."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Export ───────────────────────────────────────────────────
        Tool(
            name="export_assessment_csv",
            description=(
                "Export VM or workload assessment as CSV data. Returns CSV text "
                "that can be saved to a file."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "export_type": {
                        "type": "string",
                        "description": "'vms' for VM assessment, 'workloads' for workload assessment",
                    },
                },
                "required": [],
            },
        ),

        # ── Tier 1: IaC Generation ───────────────────────────────────
        Tool(
            name="generate_terraform",
            description=(
                "Generate Terraform modules from the cloud topology. Returns "
                "deployment-ready .tf files (main.tf, variables.tf, outputs.tf) "
                "with CAF naming, modular structure, and parameterised variables."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "naming_prefix": {"type": "string", "description": "Naming prefix (default: migrate)"},
                    "environment": {"type": "string", "description": "Environment: prod, devtest"},
                    "backend": {"type": "string", "description": "Terraform backend: local or azurerm"},
                },
                "required": [],
            },
        ),
        Tool(
            name="generate_bicep",
            description=(
                "Generate Bicep templates from the cloud topology. Returns "
                "deployment-ready .bicep files with modules and parameters."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "naming_prefix": {"type": "string", "description": "Naming prefix (default: migrate)"},
                    "environment": {"type": "string", "description": "Environment: prod, devtest"},
                },
                "required": [],
            },
        ),

        # ── Tier 1: Smart Wave Planning ──────────────────────────────
        Tool(
            name="generate_smart_wave_plan",
            description=(
                "Generate a dependency-aware wave plan using topological sort "
                "on the TCP dependency graph. Databases and shared services are "
                "placed in early waves; dependent apps follow. Includes reasoning "
                "for each VM's wave assignment."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "wave_count": {"type": "integer", "description": "Number of waves (default: 4)"},
                },
                "required": [],
            },
        ),

        # ── Tier 1: Pricing Comparison ───────────────────────────────
        Tool(
            name="compare_pricing_models",
            description=(
                "Compare fleet cost across all 7 pricing models side-by-side: "
                "PAYG, 1yr RI, 3yr RI, 1yr SP, 3yr SP, AHUB, Dev/Test. Returns "
                "per-VM optimal model recommendation with blended fleet savings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "Azure region for pricing (default: eastus)"},
                },
                "required": [],
            },
        ),

        # ── Tier 1: Application Grouping ─────────────────────────────
        Tool(
            name="list_applications",
            description=(
                "Detect and list application groups — VMs clustered by TCP "
                "dependencies and naming patterns. Each group shows VMs, "
                "workload types, complexity score, and criticality tier."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Tier 1: Runbooks ─────────────────────────────────────────
        Tool(
            name="generate_runbooks",
            description=(
                "Generate pre-migration, execution, and post-migration validation "
                "runbooks customised per wave with actual VM names, SKUs, network "
                "ranges, and az CLI commands."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Tier 1: Executive Report ─────────────────────────────────
        Tool(
            name="generate_executive_report",
            description=(
                "Generate a boardroom-ready executive migration report with 9 "
                "sections: summary, estate overview, readiness, business case, "
                "architecture, wave plan, risk matrix, recommendations, appendix."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {"type": "string", "description": "'json' or 'markdown' (default: json)"},
                },
                "required": [],
            },
        ),

        # ── Tier 2: Migration Tracker ────────────────────────────────
        Tool(
            name="set_vm_migration_status",
            description="Update a VM's migration status (Not Started → Planned → Replicating → Test Failover → Migrated → Validated → Decommissioned).",
            inputSchema={
                "type": "object",
                "properties": {
                    "vm_name": {"type": "string", "description": "VM name"},
                    "state": {"type": "string", "description": "New state"},
                    "note": {"type": "string", "description": "Optional note"},
                    "blocker": {"type": "string", "description": "Optional blocker text (empty to clear)"},
                },
                "required": ["vm_name", "state"],
            },
        ),
        Tool(
            name="get_migration_progress",
            description="Get migration progress: per-wave status breakdown, overall completion %, and blockers.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Tier 2: NSG Rules ────────────────────────────────────────
        Tool(
            name="generate_nsg_rules",
            description="Generate Azure NSG rules from discovered TCP dependencies. Returns per-subnet rule sets with least-privilege allow rules and default deny.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Tier 2: Tagging Strategy ─────────────────────────────────
        Tool(
            name="get_tagging_strategy",
            description="Generate an Azure tagging strategy from vCenter metadata (folder → Environment, cluster → CostCenter, etc). Returns per-VM tag assignments.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Tier 3: Compliance Assessment ────────────────────────────
        Tool(
            name="assess_compliance",
            description="Assess the migration architecture against regulatory frameworks: PCI-DSS, HIPAA, SOX, GDPR, ISO 27001. Returns pass/fail per control with remediation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "frameworks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Frameworks to assess: pci-dss, hipaa, sox, gdpr, iso27001",
                    },
                },
                "required": [],
            },
        ),

        # ── Tier 3: Post-Migration Validation ────────────────────────
        Tool(
            name="generate_post_migration_checks",
            description="Generate post-migration validation checks: VM health, connectivity tests, performance baseline comparison.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Tier 3: Snapshots ────────────────────────────────────────
        Tool(
            name="save_snapshot",
            description="Save a point-in-time snapshot of the current project state for versioning.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Snapshot name"},
                    "description": {"type": "string", "description": "Optional description"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="list_snapshots",
            description="List all saved project snapshots with metadata.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="restore_snapshot",
            description="Restore a previously saved snapshot (auto-saves current state first).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Snapshot name to restore"},
                },
                "required": ["name"],
            },
        ),

        # ── Tier 3: Cost Optimization ────────────────────────────────
        Tool(
            name="optimize_costs",
            description="Run cost optimization: per-VM pricing model recommendation (RI/SP/AHUB/DevTest), right-sizing alerts (oversized/undersized), and zombie VM detection.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Tier 2: Projects ─────────────────────────────────────────
        Tool(
            name="list_projects",
            description="List all migration projects.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="create_project",
            description="Create a new migration project with isolated data.",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Project name"}},
                "required": ["name"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
#  TOOL EXECUTION — dispatch to the core engine
# ---------------------------------------------------------------------------
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute an MCP tool and return the result."""
    try:
        result = await _dispatch(name, arguments)
        text = json.dumps(result, indent=2, default=str) if isinstance(result, (dict, list)) else str(result)
        # Cap response size for agent context windows
        if len(text) > 120_000:
            text = text[:120_000] + "\n\n... [truncated — use filters to narrow results]"
        return [TextContent(type="text", text=text)]
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]


async def _dispatch(name: str, args: dict[str, Any]) -> Any:
    """Route tool calls to implementation functions."""

    # ── Discovery & Inventory ────────────────────────────────────────
    if name == "get_migration_summary":
        return _tool_summary()

    elif name == "list_vms":
        return _tool_list_vms(
            filter_readiness=args.get("filter_readiness"),
            filter_os=args.get("filter_os"),
            filter_name=args.get("filter_name"),
            limit=args.get("limit", 50),
        )

    elif name == "get_vm_details":
        return _tool_vm_details(args["vm_name"])

    elif name == "list_workloads":
        return _tool_list_workloads(args.get("workload_type"))

    # ── Cloud Topology Diagram ───────────────────────────────────────
    elif name == "generate_cloud_topology":
        return _tool_generate_topology(
            region=args.get("region", "eastus"),
            firewall=args.get("firewall", False),
            bastion=args.get("bastion", False),
            vpn_gateway=args.get("vpn_gateway", False),
            load_balancer=args.get("load_balancer", False),
        )

    elif name == "get_topology_waf_assessment":
        return _tool_waf_assessment(args["resource_id"])

    elif name == "get_topology_mermaid":
        return _tool_mermaid()

    # ── What-If Simulation ───────────────────────────────────────────
    elif name == "simulate_vm_whatif":
        return _tool_simulate_vm(
            vm_name=args["vm_name"],
            sku_override=args.get("sku_override"),
            region=args.get("region"),
            pricing_model=args.get("pricing_model"),
        )

    elif name == "simulate_fleet":
        return _tool_simulate_fleet(
            region=args.get("region", "eastus"),
            pricing_model=args.get("pricing_model", "payg"),
            wave_count=args.get("wave_count", 4),
        )

    # ── Wave Planning ────────────────────────────────────────────────
    elif name == "get_wave_plan":
        return _tool_get_wave_plan()

    elif name == "move_vm_to_wave":
        return _tool_move_vm_to_wave(args["vm_name"], args["target_wave"])

    elif name == "update_wave_plan":
        return _tool_update_wave_plan(args["assignments"])

    # ── What-If Overrides ────────────────────────────────────────────
    elif name == "save_whatif_override":
        return _tool_save_override(
            vm_name=args["vm_name"],
            sku=args.get("sku"),
            region=args.get("region"),
            pricing_model=args.get("pricing_model"),
        )

    elif name == "clear_whatif_overrides":
        return _tool_clear_overrides()

    # ── SKU Catalog & Regions ────────────────────────────────────────
    elif name == "get_sku_catalog":
        return _tool_sku_catalog(
            family=args.get("family"),
            min_vcpus=args.get("min_vcpus"),
            max_vcpus=args.get("max_vcpus"),
            min_memory_gb=args.get("min_memory_gb"),
        )

    elif name == "get_regions":
        return _tool_regions()

    # ── Business Case ────────────────────────────────────────────────
    elif name == "get_business_case":
        return _tool_business_case()

    # ── Enrichment ───────────────────────────────────────────────────
    elif name == "get_enrichment_status":
        return _tool_enrichment_status()

    # ── Vulnerability & SLA ──────────────────────────────────────────
    elif name == "get_vulnerability_sla":
        return _tool_vulnerability_sla()

    # ── Export ────────────────────────────────────────────────────────
    elif name == "export_assessment_csv":
        return _tool_export_csv(args.get("export_type", "vms"))

    # ── Tier 1: IaC Generation ───────────────────────────────────────
    elif name == "generate_terraform":
        return _tool_generate_terraform(
            naming_prefix=args.get("naming_prefix", "migrate"),
            environment=args.get("environment", "prod"),
            backend=args.get("backend", "local"),
        )
    elif name == "generate_bicep":
        return _tool_generate_bicep(
            naming_prefix=args.get("naming_prefix", "migrate"),
            environment=args.get("environment", "prod"),
        )

    # ── Tier 1: Smart Wave Planning ──────────────────────────────────
    elif name == "generate_smart_wave_plan":
        return _tool_smart_wave_plan(wave_count=args.get("wave_count", 4))

    # ── Tier 1: Pricing Comparison ───────────────────────────────────
    elif name == "compare_pricing_models":
        return _tool_compare_pricing(region=args.get("region", "eastus"))

    # ── Tier 1: Application Grouping ─────────────────────────────────
    elif name == "list_applications":
        return _tool_list_applications()

    # ── Tier 1: Runbooks ─────────────────────────────────────────────
    elif name == "generate_runbooks":
        return _tool_generate_runbooks()

    # ── Tier 1: Executive Report ─────────────────────────────────────
    elif name == "generate_executive_report":
        return _tool_executive_report(fmt=args.get("format", "json"))

    # ── Tier 2: Migration Tracker ────────────────────────────────────
    elif name == "set_vm_migration_status":
        return _tool_set_migration_status(args["vm_name"], args["state"], args.get("note"), args.get("blocker"))
    elif name == "get_migration_progress":
        return _tool_migration_progress()

    # ── Tier 2: NSG Rules ────────────────────────────────────────────
    elif name == "generate_nsg_rules":
        return _tool_nsg_rules()

    # ── Tier 2: Tagging Strategy ─────────────────────────────────────
    elif name == "get_tagging_strategy":
        return _tool_tagging_strategy()

    # ── Tier 3: Compliance ───────────────────────────────────────────
    elif name == "assess_compliance":
        return _tool_compliance(args.get("frameworks", ["pci-dss", "hipaa", "gdpr"]))

    # ── Tier 3: Post-Migration Validation ────────────────────────────
    elif name == "generate_post_migration_checks":
        return _tool_post_migration()

    # ── Tier 3: Snapshots ────────────────────────────────────────────
    elif name == "save_snapshot":
        return _tool_save_snapshot(args["name"], args.get("description", ""))
    elif name == "list_snapshots":
        return _tool_list_snapshots()
    elif name == "restore_snapshot":
        return _tool_restore_snapshot(args["name"])

    # ── Tier 3: Cost Optimization ────────────────────────────────────
    elif name == "optimize_costs":
        return _tool_optimize_costs()

    # ── Tier 2: Projects ─────────────────────────────────────────────
    elif name == "list_projects":
        return _tool_list_projects()
    elif name == "create_project":
        return _tool_create_project(args["name"])

    else:
        return {"error": f"Unknown tool: {name}"}


# ═══════════════════════════════════════════════════════════════════════════
#  Tool implementations
# ═══════════════════════════════════════════════════════════════════════════

def _tool_summary() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded. Upload a vCenter export first."}

    vms = data.get("vms", [])
    recs = data.get("recommendations", [])
    hosts = data.get("hosts", [])

    total_vcpus = sum(v.get("num_cpus", 0) for v in vms)
    total_ram_gb = round(sum(v.get("memory_mb", 0) for v in vms) / 1024, 1)
    total_disk_gb = round(sum(v.get("total_disk_gb", 0) for v in vms), 1)

    readiness_dist = {}
    total_cost = 0.0
    sku_families: dict[str, int] = {}
    for r in recs:
        rd = r.get("migration_readiness", "Unknown")
        readiness_dist[rd] = readiness_dist.get(rd, 0) + 1
        total_cost += r.get("estimated_monthly_cost", 0)
        fam = r.get("recommended_vm_family", "Unknown")
        sku_families[fam] = sku_families.get(fam, 0) + 1

    return {
        "vm_count": len(vms),
        "host_count": len(hosts),
        "total_vcpus": total_vcpus,
        "total_ram_gb": total_ram_gb,
        "total_disk_gb": total_disk_gb,
        "estimated_monthly_cost_usd": round(total_cost, 2),
        "readiness_distribution": readiness_dist,
        "sku_family_distribution": sku_families,
        "networks": len(data.get("networks", [])),
        "datastores": len(data.get("datastores", [])),
        "clusters": len(data.get("clusters", [])),
    }


def _tool_list_vms(
    filter_readiness: str | None = None,
    filter_os: str | None = None,
    filter_name: str | None = None,
    limit: int = 50,
) -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    vms = data.get("vms", [])
    recs = {r.get("vm_name"): r for r in data.get("recommendations", [])}
    enrichment = _get_enrichment()
    overrides = _get_whatif()

    results = []
    for vm in vms:
        name = vm.get("name", "")
        rec = recs.get(name, {})

        if filter_readiness and rec.get("migration_readiness") != filter_readiness:
            continue
        if filter_os and rec.get("os_type", "").lower() != filter_os.lower():
            continue
        if filter_name and filter_name.lower() not in name.lower():
            continue

        entry = {
            "name": name,
            "vcpus": vm.get("num_cpus"),
            "memory_gb": round(vm.get("memory_mb", 0) / 1024, 1),
            "total_disk_gb": round(vm.get("total_disk_gb", 0), 1),
            "os": rec.get("os_type"),
            "power_state": vm.get("power_state"),
            "recommended_sku": rec.get("recommended_vm_sku"),
            "monthly_cost_usd": rec.get("estimated_monthly_cost"),
            "readiness": rec.get("migration_readiness"),
            "confidence": rec.get("confidence_score"),
            "has_enrichment": name in enrichment,
            "has_override": name in overrides,
        }
        results.append(entry)

    results.sort(key=lambda x: x.get("monthly_cost_usd") or 0, reverse=True)

    return {
        "total_matching": len(results),
        "showing": min(limit, len(results)),
        "vms": results[:limit],
    }


def _tool_vm_details(vm_name: str) -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    vm = next((v for v in data.get("vms", []) if v.get("name") == vm_name), None)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}

    rec = next((r for r in data.get("recommendations", []) if r.get("vm_name") == vm_name), None)
    enrichment_data = _get_enrichment().get(vm_name)
    override = _get_whatif().get(vm_name)
    perf = _get_perf().get(vm_name)

    result: dict[str, Any] = {
        "vm": vm,
        "recommendation": rec,
        "enrichment": enrichment_data,
        "override": override,
        "perf_samples": len(perf) if perf else 0,
    }

    if perf:
        # Include latest + aggregated stats
        latest = perf[-1] if perf else {}
        cpu_vals = [s.get("cpu_pct", 0) for s in perf if s.get("cpu_pct") is not None]
        mem_vals = [s.get("mem_pct", 0) for s in perf if s.get("mem_pct") is not None]
        result["perf_summary"] = {
            "latest": latest,
            "cpu_avg": round(sum(cpu_vals) / len(cpu_vals), 1) if cpu_vals else None,
            "cpu_p95": round(sorted(cpu_vals)[int(len(cpu_vals) * 0.95)] if cpu_vals else 0, 1),
            "mem_avg": round(sum(mem_vals) / len(mem_vals), 1) if mem_vals else None,
            "mem_p95": round(sorted(mem_vals)[int(len(mem_vals) * 0.95)] if mem_vals else 0, 1),
        }

    return result


def _tool_list_workloads(workload_type: str | None = None) -> dict:
    wl_data = _get_workloads()
    if not wl_data:
        return {"error": "No workload data. Run workload discovery first."}

    result: dict[str, Any] = {"workload_type_filter": workload_type}
    types = ["databases", "web_apps", "containers", "orchestrators"]

    for wtype in types:
        if workload_type and workload_type.lower() not in wtype:
            continue
        items = wl_data.get(wtype, [])
        result[wtype] = items

    recs = wl_data.get("recommendations", [])
    if workload_type:
        recs = [r for r in recs if workload_type.lower() in r.get("workload_type", "").lower()]
    result["recommendations"] = recs

    return result


def _tool_generate_topology(
    region: str = "eastus",
    firewall: bool = False,
    bastion: bool = False,
    vpn_gateway: bool = False,
    load_balancer: bool = False,
) -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    from azure_migrate_simulations.cloud_topology import generate_cloud_topology

    vms = data.get("vms", [])
    recs = data.get("recommendations", [])
    wl_data = _get_workloads()
    enrichment = _get_enrichment()
    perf = _get_perf()
    overrides = _get_whatif()

    optional_flags = {
        "firewall": firewall,
        "bastion": bastion,
        "load_balancer": load_balancer,
        "vpn_gateway": vpn_gateway,
    }

    topology = generate_cloud_topology(
        vms=vms,
        recommendations=recs,
        workload_data=wl_data if wl_data else None,
        region=region,
        optional_flags=optional_flags,
        enrichment_data=enrichment if enrichment else None,
        perf_history=perf if perf else None,
        whatif_overrides=overrides if overrides else None,
    )

    # Return a summary suitable for agent context (full topology can be huge)
    summary = {
        "generated_at": topology.get("generated_at"),
        "region": region,
        "source_vm_count": topology.get("source_vm_count"),
        "total_monthly_cost": topology.get("total_monthly_cost"),
        "landing_zones": [
            {"id": c["id"], "label": c["label"], "type": c["type"]}
            for c in topology.get("containers", [])
            if c.get("type") == "landing_zone"
        ],
        "resource_count": len(topology.get("nodes", [])),
        "dependency_count": len(topology.get("edges", [])),
        "cost_summary": topology.get("cost_summary"),
        "waf_summary": topology.get("waf_summary"),
        "optional_components": topology.get("optional_components"),
        "options_used": {
            "region": region,
            "firewall": firewall,
            "bastion": bastion,
            "vpn_gateway": vpn_gateway,
            "load_balancer": load_balancer,
        },
    }

    # Cache full topology for subsequent WAF/mermaid requests
    _save_json(DATA_DIR / "_last_topology.json", topology)

    return summary


def _tool_waf_assessment(resource_id: str) -> dict:
    topology = _load_json(DATA_DIR / "_last_topology.json")
    if not topology:
        return {"error": "No topology generated yet. Call generate_cloud_topology first."}

    data = _get_discovery()
    vms = data.get("vms", [])
    recs = data.get("recommendations", [])
    enrichment = _get_enrichment()
    perf = _get_perf()

    from azure_migrate_simulations.cloud_topology import get_waf_assessment

    waf = get_waf_assessment(
        resource_id=resource_id,
        topology_data=topology,
        vms=vms,
        recommendations=recs,
        enrichment_data=enrichment if enrichment else None,
        perf_history=perf if perf else None,
    )
    return waf


def _tool_mermaid() -> dict:
    topology = _load_json(DATA_DIR / "_last_topology.json")
    if not topology:
        return {"error": "No topology generated yet. Call generate_cloud_topology first."}

    mermaid = topology.get("mermaid", "")
    return {"mermaid": mermaid, "note": "Paste this into any Mermaid renderer (GitHub, Notion, etc.)"}


def _tool_simulate_vm(
    vm_name: str,
    sku_override: str | None = None,
    region: str | None = None,
    pricing_model: str | None = None,
) -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    rec = next((r for r in data.get("recommendations", []) if r.get("vm_name") == vm_name), None)
    if not rec:
        return {"error": f"No recommendation found for VM '{vm_name}'."}

    from azure_migrate_simulations.azure_mapping import VM_CATALOG

    original_cost = rec.get("estimated_monthly_cost", 0)
    original_sku = rec.get("recommended_vm_sku", "")

    # Determine override SKU
    target_sku = sku_override or original_sku
    sku_info = next((s for s in VM_CATALOG if s.name == target_sku), None)

    if not sku_info:
        return {"error": f"SKU '{target_sku}' not found in catalog."}

    # Apply region multiplier
    from azure_migrate_simulations.cloud_topology import _REGION_MULTIPLIERS
    region_mult = _REGION_MULTIPLIERS.get(region or "eastus", 1.0)

    # Apply pricing model discount
    pricing_discounts = {
        "payg": 1.0, "1yr_ri": 0.62, "3yr_ri": 0.40,
        "1yr_sp": 0.75, "3yr_sp": 0.54, "ahub": 0.60, "devtest": 0.56,
    }
    model = pricing_model or "payg"
    discount = pricing_discounts.get(model, 1.0)

    new_cost = round(sku_info.monthly_cost_usd * region_mult * discount, 2)
    savings = round(original_cost - new_cost, 2)

    return {
        "vm_name": vm_name,
        "original_sku": original_sku,
        "original_cost": original_cost,
        "simulated_sku": target_sku,
        "simulated_region": region or "eastus",
        "simulated_pricing": model,
        "simulated_cost": new_cost,
        "monthly_savings": savings,
        "annual_savings": round(savings * 12, 2),
        "sku_details": {
            "vcpus": sku_info.vcpus,
            "memory_gb": sku_info.memory_gb,
            "family": sku_info.family,
        },
    }


def _tool_simulate_fleet(
    region: str = "eastus",
    pricing_model: str = "payg",
    wave_count: int = 4,
) -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    recs = data.get("recommendations", [])
    overrides = _get_whatif()

    from azure_migrate_simulations.azure_mapping import VM_CATALOG
    from azure_migrate_simulations.cloud_topology import _REGION_MULTIPLIERS

    region_mult = _REGION_MULTIPLIERS.get(region, 1.0)
    pricing_discounts = {
        "payg": 1.0, "1yr_ri": 0.62, "3yr_ri": 0.40,
        "1yr_sp": 0.75, "3yr_sp": 0.54, "ahub": 0.60, "devtest": 0.56,
    }
    discount = pricing_discounts.get(pricing_model, 1.0)
    sku_lookup = {s.name: s for s in VM_CATALOG}

    original_total = 0.0
    azure_total = 0.0
    vm_costs = []

    for rec in recs:
        vm_name = rec.get("vm_name", "")
        orig_cost = rec.get("estimated_monthly_cost", 0)
        original_total += orig_cost

        override = overrides.get(vm_name, {})
        sku_name = override.get("sku", rec.get("recommended_vm_sku", ""))
        sku_info = sku_lookup.get(sku_name)
        cost = (sku_info.monthly_cost_usd if sku_info else orig_cost) * region_mult * discount
        azure_total += cost

        vm_costs.append({"vm_name": vm_name, "original": orig_cost, "azure": round(cost, 2)})

    # Distribute VMs into waves
    wave_count = max(1, min(wave_count, len(recs)))
    waves: list[list[dict]] = [[] for _ in range(wave_count)]
    for i, vc in enumerate(vm_costs):
        waves[i % wave_count].append(vc)

    wave_summary = []
    for i, wave_vms in enumerate(waves, 1):
        wave_summary.append({
            "wave": i,
            "vm_count": len(wave_vms),
            "monthly_cost": round(sum(v["azure"] for v in wave_vms), 2),
            "vms": [v["vm_name"] for v in wave_vms],
        })

    # Save wave plan for subsequent operations
    _save_json(DATA_DIR / "_wave_plan.json", {"waves": wave_summary, "region": region, "pricing_model": pricing_model})

    return {
        "region": region,
        "pricing_model": pricing_model,
        "original_monthly_total": round(original_total, 2),
        "azure_monthly_total": round(azure_total, 2),
        "monthly_savings": round(original_total - azure_total, 2),
        "annual_savings": round((original_total - azure_total) * 12, 2),
        "wave_count": wave_count,
        "waves": wave_summary,
    }


def _tool_get_wave_plan() -> dict:
    plan = _load_json(DATA_DIR / "_wave_plan.json")
    if not plan:
        return {"error": "No wave plan generated yet. Run simulate_fleet first."}
    return plan


def _tool_move_vm_to_wave(vm_name: str, target_wave: int) -> dict:
    plan = _load_json(DATA_DIR / "_wave_plan.json")
    if not plan:
        return {"error": "No wave plan generated yet. Run simulate_fleet first."}

    waves = plan.get("waves", [])
    if target_wave < 1 or target_wave > len(waves):
        return {"error": f"Wave {target_wave} does not exist. Valid: 1-{len(waves)}"}

    # Find and remove VM from current wave
    found = False
    source_wave = None
    for wave in waves:
        if vm_name in wave.get("vms", []):
            wave["vms"].remove(vm_name)
            wave["vm_count"] = len(wave["vms"])
            source_wave = wave["wave"]
            found = True
            break

    if not found:
        return {"error": f"VM '{vm_name}' not found in any wave."}

    # Add to target wave
    target = waves[target_wave - 1]
    target["vms"].append(vm_name)
    target["vm_count"] = len(target["vms"])

    _save_json(DATA_DIR / "_wave_plan.json", plan)

    return {
        "moved": vm_name,
        "from_wave": source_wave,
        "to_wave": target_wave,
        "updated_waves": waves,
    }


def _tool_update_wave_plan(assignments: list[dict]) -> dict:
    plan = _load_json(DATA_DIR / "_wave_plan.json")
    if not plan:
        return {"error": "No wave plan generated yet. Run simulate_fleet first."}

    moved = []
    errors = []
    for assignment in assignments:
        vm_name = assignment.get("vm_name", "")
        target = assignment.get("target_wave", 0)
        result = _tool_move_vm_to_wave(vm_name, target)
        if "error" in result:
            errors.append({"vm_name": vm_name, "error": result["error"]})
        else:
            moved.append({"vm_name": vm_name, "to_wave": target})

    return {"moved": moved, "errors": errors}


def _tool_save_override(
    vm_name: str,
    sku: str | None = None,
    region: str | None = None,
    pricing_model: str | None = None,
) -> dict:
    overrides = _get_whatif()
    entry = overrides.get(vm_name, {})

    if sku:
        entry["sku"] = sku
    if region:
        entry["region"] = region
    if pricing_model:
        entry["pricing_model"] = pricing_model

    overrides[vm_name] = entry
    _save_json(_WHATIF_OVERRIDES_FILE, overrides)

    return {"saved": vm_name, "override": entry}


def _tool_clear_overrides() -> dict:
    _save_json(_WHATIF_OVERRIDES_FILE, {})
    return {"cleared": True, "message": "All what-if overrides cleared."}


def _tool_sku_catalog(
    family: str | None = None,
    min_vcpus: int | None = None,
    max_vcpus: int | None = None,
    min_memory_gb: float | None = None,
) -> dict:
    from azure_migrate_simulations.azure_mapping import VM_CATALOG

    skus = VM_CATALOG
    if family:
        skus = [s for s in skus if s.family.upper().startswith(family.upper())]
    if min_vcpus is not None:
        skus = [s for s in skus if s.vcpus >= min_vcpus]
    if max_vcpus is not None:
        skus = [s for s in skus if s.vcpus <= max_vcpus]
    if min_memory_gb is not None:
        skus = [s for s in skus if s.memory_gb >= min_memory_gb]

    return {
        "count": len(skus),
        "skus": [
            {
                "name": s.name,
                "family": s.family,
                "vcpus": s.vcpus,
                "memory_gb": s.memory_gb,
                "max_data_disks": s.max_data_disks,
                "max_iops": s.max_iops,
                "monthly_cost_usd": s.monthly_cost_usd,
                "gpu": s.gpu,
            }
            for s in skus
        ],
    }


def _tool_regions() -> dict:
    from azure_migrate_simulations.cloud_topology import _REGION_MULTIPLIERS
    regions = [
        {"name": k, "cost_multiplier": v}
        for k, v in sorted(_REGION_MULTIPLIERS.items(), key=lambda x: x[1])
    ]
    return {"regions": regions}


def _tool_business_case() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    vms = data.get("vms", [])
    recs = data.get("recommendations", [])

    # On-prem TCO estimation (simplified)
    total_vcpus = sum(v.get("num_cpus", 0) for v in vms)
    total_ram_gb = sum(v.get("memory_mb", 0) for v in vms) / 1024
    total_disk_tb = sum(v.get("total_disk_gb", 0) for v in vms) / 1024

    onprem_monthly = (
        total_vcpus * 25  # CPU cost per core
        + total_ram_gb * 5  # Memory cost per GB
        + total_disk_tb * 100  # Storage cost per TB
        + len(vms) * 15  # Per-VM overhead (licensing, mgmt)
        + 2000  # Fixed infrastructure cost
    )

    azure_monthly = sum(r.get("estimated_monthly_cost", 0) for r in recs)

    monthly_savings = onprem_monthly - azure_monthly
    payback_months = round(onprem_monthly * 3 / monthly_savings, 1) if monthly_savings > 0 else None

    return {
        "on_prem_monthly_tco": round(onprem_monthly, 2),
        "azure_monthly_cost": round(azure_monthly, 2),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(monthly_savings * 12, 2),
        "three_year_savings": round(monthly_savings * 36, 2),
        "payback_period_months": payback_months,
        "vm_count": len(vms),
        "recommendation": (
            "Migration recommended — Azure cost is lower than on-prem TCO"
            if monthly_savings > 0
            else "Review sizing — Azure cost exceeds on-prem TCO"
        ),
    }


def _tool_enrichment_status() -> dict:
    data = _get_discovery()
    enrichment = _get_enrichment()

    if not data:
        return {"error": "No discovery data loaded."}

    vm_names = [v.get("name") for v in data.get("vms", [])]
    enriched_vms = [n for n in vm_names if n in enrichment]

    tools_used = set()
    total_boost = 0.0
    for name, edata in enrichment.items():
        if isinstance(edata, dict):
            tools_used.add(edata.get("monitoring_tool", "unknown"))
            total_boost += edata.get("confidence_boost", 0)

    return {
        "total_vms": len(vm_names),
        "enriched_vms": len(enriched_vms),
        "coverage_pct": round(len(enriched_vms) / len(vm_names) * 100, 1) if vm_names else 0,
        "tools_used": sorted(tools_used),
        "avg_confidence_boost": round(total_boost / len(enriched_vms), 1) if enriched_vms else 0,
    }


def _tool_vulnerability_sla() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    from azure_migrate_simulations.vulnerability_sla import analyse_vulnerability_sla

    vms = data.get("vms", [])
    recs = data.get("recommendations", [])
    wl_data = _get_workloads()

    result = analyse_vulnerability_sla(vms, recs, wl_data if wl_data else None)
    return result


def _tool_export_csv(export_type: str = "vms") -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}

    import csv
    import io

    output = io.StringIO()
    if export_type == "workloads":
        wl_data = _get_workloads()
        if not wl_data:
            return {"error": "No workload data available."}
        recs = wl_data.get("recommendations", [])
        if not recs:
            return {"csv": "", "rows": 0}
        writer = csv.DictWriter(output, fieldnames=recs[0].keys())
        writer.writeheader()
        writer.writerows(recs)
    else:
        recs = data.get("recommendations", [])
        if not recs:
            return {"csv": "", "rows": 0}
        fields = ["vm_name", "recommended_vm_sku", "recommended_vm_family",
                   "estimated_monthly_cost", "migration_readiness", "confidence_score", "os_type"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(recs)

    return {"csv": output.getvalue(), "rows": len(recs), "type": export_type}


# ═══════════════════════════════════════════════════════════════════════════
#  Tier 1 tool implementations
# ═══════════════════════════════════════════════════════════════════════════

def _tool_generate_terraform(naming_prefix: str = "migrate", environment: str = "prod", backend: str = "local") -> dict:
    topology = _load_json(DATA_DIR / "_last_topology.json")
    if not topology:
        return {"error": "No topology generated yet. Call generate_cloud_topology first."}
    from azure_migrate_simulations.iac_generator import generate_terraform
    files = generate_terraform(topology, naming_prefix=naming_prefix, environment=environment, backend=backend)
    # Return file listing + key files content (main.tf, variables.tf)
    summary = {"file_count": len(files), "files": list(files.keys())}
    for key_file in ["main.tf", "variables.tf", "outputs.tf", "terraform.tfvars.example"]:
        if key_file in files:
            content = files[key_file]
            if len(content) > 20000:
                content = content[:20000] + "\n\n... [truncated]"
            summary[key_file] = content
    return summary


def _tool_generate_bicep(naming_prefix: str = "migrate", environment: str = "prod") -> dict:
    topology = _load_json(DATA_DIR / "_last_topology.json")
    if not topology:
        return {"error": "No topology generated yet. Call generate_cloud_topology first."}
    from azure_migrate_simulations.iac_generator import generate_bicep
    files = generate_bicep(topology, naming_prefix=naming_prefix, environment=environment)
    summary = {"file_count": len(files), "files": list(files.keys())}
    for key_file in ["main.bicep", "parameters.json"]:
        if key_file in files:
            content = files[key_file]
            if len(content) > 20000:
                content = content[:20000] + "\n\n... [truncated]"
            summary[key_file] = content
    return summary


def _tool_smart_wave_plan(wave_count: int = 4) -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.wave_planner import generate_smart_wave_plan
    plan = generate_smart_wave_plan(
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        workload_data=_get_workloads() or None,
        wave_count=wave_count,
    )
    _save_json(DATA_DIR / "_wave_plan.json", plan)
    return plan


def _tool_compare_pricing(region: str = "eastus") -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.pricing_comparison import compare_pricing_models
    from azure_migrate_simulations.cloud_topology import _REGION_MULTIPLIERS
    result = compare_pricing_models(
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        region_multiplier=_REGION_MULTIPLIERS.get(region, 1.0),
        enrichment_data=_get_enrichment() or None,
        perf_history=_get_perf() or None,
    )
    # Truncate per-VM list for agent context
    if len(result.get("per_vm", [])) > 30:
        result["per_vm"] = result["per_vm"][:30]
        result["per_vm_truncated"] = True
    return result


def _tool_list_applications() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.app_grouping import detect_application_groups
    groups = detect_application_groups(
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        workload_data=_get_workloads() or None,
    )
    return {"application_count": len(groups), "applications": groups[:30]}


def _tool_generate_runbooks() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    topology = _load_json(DATA_DIR / "_last_topology.json")
    wave_plan = _load_json(DATA_DIR / "_wave_plan.json")
    if not wave_plan.get("waves"):
        return {"error": "Generate a wave plan first (simulate_fleet or generate_smart_wave_plan)."}
    from azure_migrate_simulations.runbook_generator import generate_runbooks
    runbooks = generate_runbooks(
        topology=topology or {},
        wave_plan=wave_plan,
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        workload_data=_get_workloads() or None,
    )
    return runbooks


def _tool_executive_report(fmt: str = "json") -> dict | str:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.executive_report import generate_executive_report, render_report_markdown
    topology = _load_json(DATA_DIR / "_last_topology.json") or None
    wave_plan = _load_json(DATA_DIR / "_wave_plan.json") or None
    report = generate_executive_report(
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        workload_data=_get_workloads() or None,
        topology=topology,
        wave_plan=wave_plan,
        enrichment_data=_get_enrichment() or None,
    )
    if fmt == "markdown":
        return render_report_markdown(report)
    return report


# ═══════════════════════════════════════════════════════════════════════════
#  Tier 2 + Tier 3 tool implementations
# ═══════════════════════════════════════════════════════════════════════════

_STATUS_FILE = DATA_DIR / "migration_status.json"


def _tool_set_migration_status(vm_name: str, state: str, note: str | None = None, blocker: str | None = None) -> dict:
    from azure_migrate_simulations.migration_tracker import set_vm_status
    status_data = _load_json(_STATUS_FILE)
    result = set_vm_status(status_data, vm_name, state, note, blocker)
    if "error" not in result:
        _save_json(_STATUS_FILE, status_data)
    return result


def _tool_migration_progress() -> dict:
    from azure_migrate_simulations.migration_tracker import get_migration_progress
    status_data = _load_json(_STATUS_FILE)
    wave_plan = _load_json(DATA_DIR / "_wave_plan.json")
    return get_migration_progress(status_data, wave_plan if wave_plan else None)


def _tool_nsg_rules() -> dict:
    topology = _load_json(DATA_DIR / "_last_topology.json")
    if not topology:
        return {"error": "No topology generated yet. Call generate_cloud_topology first."}
    from azure_migrate_simulations.nsg_generator import generate_nsg_rules
    return generate_nsg_rules(topology, _get_workloads() or None)


def _tool_tagging_strategy() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.tagging_strategy import generate_tagging_strategy
    wave_plan = _load_json(DATA_DIR / "_wave_plan.json")
    result = generate_tagging_strategy(
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        workload_data=_get_workloads() or None,
        wave_plan=wave_plan if wave_plan else None,
    )
    # Truncate per-VM for agent context
    if len(result.get("per_vm", [])) > 20:
        result["per_vm"] = result["per_vm"][:20]
        result["per_vm_truncated"] = True
    return result


def _tool_compliance(frameworks: list[str]) -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.compliance_assessment import assess_compliance
    topology = _load_json(DATA_DIR / "_last_topology.json")
    return assess_compliance(
        frameworks=frameworks,
        topology=topology,
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        enrichment_data=_get_enrichment() or None,
    )


def _tool_post_migration() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.post_migration import generate_post_migration_checks
    return generate_post_migration_checks(
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        workload_data=_get_workloads() or None,
        enrichment_data=_get_enrichment() or None,
        perf_history=_get_perf() or None,
    )


def _tool_save_snapshot(name: str, description: str = "") -> dict:
    from azure_migrate_simulations.project_versioning import save_snapshot
    return save_snapshot(DATA_DIR, name, description)


def _tool_list_snapshots() -> dict:
    from azure_migrate_simulations.project_versioning import list_snapshots
    return {"snapshots": list_snapshots(DATA_DIR)}


def _tool_restore_snapshot(name: str) -> dict:
    from azure_migrate_simulations.project_versioning import restore_snapshot
    return restore_snapshot(DATA_DIR, name)


def _tool_optimize_costs() -> dict:
    data = _get_discovery()
    if not data:
        return {"error": "No discovery data loaded."}
    from azure_migrate_simulations.cost_optimization import optimize_costs
    result = optimize_costs(
        vms=data.get("vms", []),
        recommendations=data.get("recommendations", []),
        enrichment_data=_get_enrichment() or None,
        perf_history=_get_perf() or None,
    )
    return result


def _tool_list_projects() -> dict:
    from azure_migrate_simulations.multi_project import list_projects
    return {"projects": list_projects(DATA_DIR)}


def _tool_create_project(name: str) -> dict:
    from azure_migrate_simulations.multi_project import create_project
    return create_project(DATA_DIR, name)


# ═══════════════════════════════════════════════════════════════════════════
#  Server startup
# ═══════════════════════════════════════════════════════════════════════════
async def run_stdio():
    """Run MCP server over stdin/stdout (default for Copilot, Claude, Cursor)."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point for the MCP server."""
    import asyncio

    mode = "stdio"
    if "--sse" in sys.argv:
        mode = "sse"

    if mode == "sse":
        # SSE mode for HTTP-based agents
        try:
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Route, Mount
            import uvicorn

            sse = SseServerTransport("/messages/")

            async def handle_sse(request):
                async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                    await server.run(streams[0], streams[1], server.create_initialization_options())

            starlette_app = Starlette(
                routes=[
                    Route("/sse", endpoint=handle_sse),
                    Mount("/messages/", app=sse.handle_post_message),
                ],
            )

            port = int(os.environ.get("MCP_PORT", "3001"))
            print(f"Azure Migrate Simulations MCP server (SSE) on http://localhost:{port}")
            uvicorn.run(starlette_app, host="0.0.0.0", port=port)
        except ImportError:
            print("SSE mode requires: pip install 'mcp[server]' starlette uvicorn")
            sys.exit(1)
    else:
        # Stdio mode (default) — used by Copilot, Claude Desktop, Cursor
        print("Azure Migrate Simulations MCP server (stdio)", file=sys.stderr)
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
