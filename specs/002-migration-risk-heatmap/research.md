# Research: Migration Risk Heatmap

**Feature**: `002-migration-risk-heatmap` | **Date**: 2026-03-31

## R-001: How to access VM dependency data

**Decision**: Read dependency data from two sources: (1) `WorkloadDependency` entries in `workload_discovery.json` keyed by `source_vm`/`target_vm`, and (2) `EstablishedConnection` lists in each `VMWorkloads.established_connections`.

**Rationale**: The existing `models_workload.py` defines `WorkloadDependency` (directed edges with `source_vm`, `target_vm`, `target_port`, `protocol`, `connection_count`) and `EstablishedConnection` (per-process outbound connections). Both are populated by guest discovery and stored in `workload_discovery.json`. Counting unique `target_vm` values where a VM appears as `source_vm` (plus unique sources where it appears as `target_vm`) gives the bidirectional dependency count.

**Alternatives considered**:
- Enrichment-only dependencies (`EnrichmentTelemetry.dependencies` list): Rejected because enrichment is optional and may not be present. Used as supplementary source when available.
- Network topology inference from `EstablishedConnection`: Included as secondary source to catch dependencies not formalized as `WorkloadDependency` edges.

---

## R-002: How to determine OS EOL status

**Decision**: Reuse the existing `_match_os(guest_os, today)` function from `vulnerability_sla.py`. It returns a dict with `severity` (critical|high|warning|ok), `eol_date`, `days_until_eol`, and `esu_eligible`.

**Rationale**: The module already has an 80+ entry OS lifecycle database (`_OS_LIFECYCLE_DB`) covering Windows Server, RHEL, CentOS, Ubuntu, Debian, SUSE, and Oracle Linux. The `_match_os` function takes `guest_os` (string from vCenter) and the current date and returns a severity classification. Severity `critical` or `high` indicates EOL → apply the +30 risk factor. Severity `warning` could warrant a partial score.

**Alternatives considered**:
- Building a separate EOL database: Rejected — duplicates existing data and creates maintenance burden.
- Using only binary EOL/not-EOL: Adopted for the +30 factor as specified, but the `severity` field allows nuanced scoring if needed in future.

---

## R-003: How to classify workload complexity

**Decision**: Map workload types from `VMWorkloads` to complexity tiers:
- **High (score 80–100)**: Database engines (MSSQL, Oracle, PostgreSQL, MySQL, MariaDB, MongoDB, Redis) — especially Enterprise edition or large (`total_size_gb > 100`)
- **Medium (score 40–60)**: Application servers, orchestrators (Kubernetes, Docker Swarm), container runtimes with running containers
- **Low (score 10–30)**: Web apps (IIS, Apache, Nginx, Tomcat, Node.js), file server patterns
- **Minimal (score 0)**: No detected workload

**Rationale**: Database workloads have the highest migration complexity due to schema conversion, data migration, downtime sensitivity, and state management. Orchestrators (Kubernetes) require cluster re-architecture. Web apps are typically stateless and simpler to migrate. The workload data is available in `workload_discovery.json` via `VMWorkloads` per VM, with typed collections (`databases`, `web_apps`, `container_runtimes`, `orchestrators`).

**Alternatives considered**:
- Flat score per workload type: Rejected — Enterprise SQL Server with 500GB is riskier than Community MySQL with 1GB. Edition and size should modulate the score.
- User-defined complexity mapping: Rejected per YAGNI — hardcoded tiers are sufficient for the initial implementation and match Constitution VII.

---

## R-004: How to access IOPS/performance data

**Decision**: Read IOPS from `PerformanceMetrics` on each `DiscoveredVM`. Use `disk_iops_p95` (from `perf_aggregator.py` historical enrichment) as the primary metric. Fall back to `disk_iops_read + disk_iops_write` (realtime) if no historical data. When neither is available, default to 0 and flag as "no data."

**Rationale**: The `perf_aggregator.py` module computes P95 IOPS from historical samples and writes them to `PerformanceMetrics.disk_iops_p95`. This is the most representative metric for sustained load. The realtime `disk_iops_read` + `disk_iops_write` values are available from vCenter but reflect a single point in time and are less reliable.

**Alternatives considered**:
- Using only P95: Rejected because many VMs may not have historical data (perf collection is opt-in).
- Using average IOPS: Rejected — P95 better represents burst sensitivity, which is the migration risk driver (sustained high IOPS means the VM is sensitive to storage performance changes).

---

## R-005: How to discover compliance tags

**Decision**: Check three sources for compliance tags:
1. `DiscoveredVM.tags` dict — vCenter tags may include compliance labels
2. `EnrichmentTelemetry.tags` dict — APM tools may include compliance metadata
3. Convention-based detection — scan `tags` for keys/values matching patterns: `pci`, `hipaa`, `sox`, `gdpr`, `fedramp`, `compliance`, `regulated`

**Rationale**: The spec states compliance tags are "user-supplied via enrichment data or manual tagging." The existing `DiscoveredVM.tags` field (dict[str, str]) and `EnrichmentTelemetry.tags` (dict[str, str]) are the natural locations. Pattern-based detection provides a reasonable default when tags aren't formally structured.

**Alternatives considered**:
- Dedicated compliance field on DiscoveredVM: Rejected — would require modifying the discovery pipeline and vCenter API. Tags are the established mechanism.
- Prompting users to manually classify VMs: Rejected for initial implementation — the system should work automatically with available data and allow enrichment to improve accuracy.

---

## R-006: How to compute fleet-relative data volume scores

**Decision**: Use `DiscoveredVM.total_disk_gb` for each VM. Compute the fleet maximum. Score each VM as `min(100, (vm_disk_gb / fleet_max_disk_gb) * 100)`. This gives a linear 0–100 scale relative to the largest VM in the fleet.

**Rationale**: Absolute disk size thresholds would not account for fleet variation. A fleet with all small VMs (10–50 GB) should still differentiate risk. Fleet-relative scoring ensures the largest VMs always surface as higher risk within their context. The `total_disk_gb` field is populated from vCenter discovery and is always available.

**Alternatives considered**:
- Absolute thresholds (e.g., >500GB = high): Rejected — does not adapt to fleet composition. A 200GB VM is high-risk in a fleet of 20GB VMs.
- Percentile-based scoring: Considered but linear relative scoring is simpler and achieves the same goal for typical fleet distributions.

---

## R-007: Composite score formula

**Decision**: Weighted average of the six factor scores (each normalized to 0–100), with configurable weights:

```
composite = round(
    dependency_score * 0.15 +
    os_eol_score * 0.25 +
    workload_complexity_score * 0.20 +
    performance_sensitivity_score * 0.10 +
    compliance_score * 0.20 +
    data_volume_score * 0.10
)
```

Clamped to integer 0–100. Weights sum to 1.0.

**Rationale**: The spec defines default weights (15%, 25%, 20%, 10%, 20%, 10%). OS EOL carries the highest weight because it's a binary, high-impact factor. Compliance is weighted equally high because regulated workloads have strict migration requirements. Data volume and performance sensitivity are lower because they affect migration duration/approach rather than feasibility.

**Alternatives considered**:
- Additive scoring (sum of raw factors): Rejected — factors have different scales and meanings; weighted average is more principled.
- ML-based scoring: Rejected per YAGNI and offline-first constraint. No training data exists for this domain.

---

## R-008: CLI subcommand architecture

**Decision**: Extend `main.py` with an argparse subparser group `risk` containing two subcommands: `heatmap` and `score`. The `score` subcommand takes a positional `vm_name` argument.

```
dt-migrate risk heatmap [--top N] [--format json|table]
dt-migrate risk score <vm_name> [--format json|table]
```

**Rationale**: The existing CLI in `main.py` uses argparse with top-level flags. Adding a subparser group follows argparse best practices for grouped commands. The `--format` flag supports both JSON (for automation) and table (for human readability via Rich).

**Alternatives considered**:
- Top-level flags (`--risk-heatmap`): Rejected — the risk feature has multiple sub-operations that warrant a command group.
- Click/Typer: Rejected — Constitution specifies argparse as the CLI framework.

---

## R-009: MCP tool registration pattern

**Decision**: Add two MCP tools to `mcp_server.py` following the existing registration pattern:
1. `get_risk_heatmap` — returns the full heatmap matrix (same schema as `/api/risk/heatmap`)
2. `get_risk_score` — takes `vm_name` parameter, returns per-VM breakdown (same schema as `/api/risk/score/<vm_name>`)

**Rationale**: Existing MCP tools in the codebase follow the pattern: `@server.tool()` decorator, function docstring as tool description, typed parameters, returns dict serializable to JSON. The new tools reuse the same `risk_heatmap.py` engine functions, ensuring consistency across CLI/API/MCP.

**Alternatives considered**:
- Single MCP tool with mode parameter: Rejected — separate tools are more discoverable by AI agents and follow the existing pattern.

---

## R-010: Web UI integration approach

**Decision**: Add a "Risk Heatmap" tab to the Decide phase in the existing tabbed dashboard. The tab renders an HTML table with color-coded cells using inline styles (green/yellow/red backgrounds). Clicking a VM row expands to show the per-factor breakdown and mitigation suggestions. Column headers are sortable via vanilla JavaScript.

**Rationale**: The existing web UI uses server-rendered HTML (Jinja2) + vanilla JS + Bootstrap 5. No build step or frontend framework is used per Constitution. The heatmap tab follows the same pattern as existing dashboard tabs (e.g., Business Case, What-If). Data is fetched via the REST API endpoints.

**Alternatives considered**:
- D3.js heatmap visualization: Rejected — adds a dependency and build complexity for marginal benefit. An HTML table with colored cells achieves the heatmap visualization with zero new dependencies.
- Separate page: Rejected — the existing UI uses tabs; a dedicated page would break the navigation pattern.

---

## R-011: Mitigation suggestion engine

**Decision**: Use a hardcoded lookup table mapping (risk_factor, severity_band) → list of actionable suggestions. Each factor has 1–3 suggestions for the yellow and red bands.

| Factor | Red-Band Suggestion |
|--------|-------------------|
| dependency_count | "Reduce dependencies by extracting shared services into independent VMs or PaaS" |
| os_eol | "Upgrade OS to a supported version before migration, or leverage Azure Extended Security Updates (ESU)" |
| workload_complexity | "Plan a phased migration: migrate the database to Azure PaaS first, then redirect application connections" |
| performance_sensitivity | "Enable Azure Migrate replication to measure actual Azure disk IOPS before cutover" |
| compliance_scope | "Engage compliance team for pre-migration audit; deploy to Azure landing zone with regulatory controls" |
| data_volume | "Use Azure Data Box or offline transfer for disks >2TB; enable incremental replication for smaller volumes" |

**Rationale**: Hardcoded suggestions are appropriate per Constitution VII (simplicity). The suggestions are migration-domain-specific and unlikely to change frequently. If customization is needed in future, the lookup can be externalized to a config file.

**Alternatives considered**:
- LLM-generated suggestions: Rejected — offline-first requirement precludes AI API calls. Determinism requirement also conflicts.
- User-defined suggestion database: Rejected per YAGNI.
