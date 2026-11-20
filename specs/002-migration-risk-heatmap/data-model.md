# Data Model: Migration Risk Heatmap

**Feature**: `002-migration-risk-heatmap` | **Date**: 2026-03-31

## Entity Definitions

All entities are Python `dataclasses` added to `models.py`, following Constitution III (Dataclass Models as Contracts). Serialization via `dataclasses.asdict()`.

---

### RiskFactorName (Enum)

Enumerates the six risk evaluation dimensions.

| Member | Value (str) | Description |
|--------|------------|-------------|
| `DEPENDENCY_COUNT` | `"dependency_count"` | Cross-VM dependency count |
| `OS_EOL` | `"os_eol"` | Operating system end-of-life status |
| `WORKLOAD_COMPLEXITY` | `"workload_complexity"` | Detected workload type complexity |
| `PERFORMANCE_SENSITIVITY` | `"performance_sensitivity"` | IOPS-driven storage sensitivity |
| `COMPLIANCE_SCOPE` | `"compliance_scope"` | Regulatory framework applicability |
| `DATA_VOLUME` | `"data_volume"` | Total provisioned disk size |

---

### RiskBand (Enum)

Color band classification for scores.

| Member | Value (str) | Range |
|--------|------------|-------|
| `GREEN` | `"green"` | 0–30 |
| `YELLOW` | `"yellow"` | 31–60 |
| `RED` | `"red"` | 61–100 |

---

### MitigationAction

A single remediation suggestion tied to a risk factor.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `factor` | `str` | — | Risk factor name (from `RiskFactorName.value`) |
| `severity` | `str` | — | Band that triggered the suggestion (`"yellow"` or `"red"`) |
| `action` | `str` | — | Actionable recommendation text |
| `expected_risk_reduction` | `int` | `0` | Estimated score reduction if action is taken (0–30) |

---

### RiskFactor

Per-factor scoring detail for a single VM.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | — | Factor name (from `RiskFactorName.value`) |
| `raw_value` | `str` | `""` | Human-readable raw observation (e.g., `"5 dependencies"`, `"EOL: 2024-01-09"`, `"480 GB"`) |
| `score` | `int` | `0` | Normalized factor score (0–100) |
| `weight` | `float` | `0.0` | Configured weight for this factor (0.0–1.0) |
| `weighted_score` | `float` | `0.0` | `score * weight` (contribution to composite) |
| `band` | `str` | `"green"` | Color band for this factor's score |
| `data_available` | `bool` | `True` | Whether source data was present for this factor |

---

### RiskScore

Complete risk assessment for a single VM.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vm_name` | `str` | — | VM identifier (matches `DiscoveredVM.name`) |
| `composite_score` | `int` | `0` | Weighted composite score (0–100) |
| `composite_band` | `str` | `"green"` | Color band for composite score |
| `factors` | `list[RiskFactor]` | `field(default_factory=list)` | Per-factor breakdown (6 entries) |
| `mitigations` | `list[MitigationAction]` | `field(default_factory=list)` | Suggestions for factors scoring >30 |
| `dominant_factor` | `str` | `""` | Name of the factor with the highest weighted contribution |

---

### RiskHeatmap

Fleet-wide risk matrix.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vm_scores` | `list[RiskScore]` | `field(default_factory=list)` | All VM risk scores, ordered by VM name |
| `factor_names` | `list[str]` | `field(default_factory=list)` | Ordered list of factor names (column headers) |
| `top_risky` | `list[RiskScore]` | `field(default_factory=list)` | Top-10 (or fewer) VMs by composite score, descending |
| `total_vms` | `int` | `0` | Count of scored VMs |
| `band_distribution` | `dict` | `field(default_factory=dict)` | Count of VMs per band: `{"green": N, "yellow": N, "red": N}` |

---

## Relationships

```
RiskHeatmap
├── vm_scores: list[RiskScore]          # One per discovered VM
│   ├── factors: list[RiskFactor]       # Exactly 6 per VM
│   └── mitigations: list[MitigationAction]  # 0–N per VM (only for factors >30)
├── top_risky: list[RiskScore]          # Subset (top-10) of vm_scores
└── factor_names: list[str]             # Column headers for the matrix
```

## Data Flow

```
DiscoveredEnvironment.vms ──┐
                            │
workload_discovery.json ────┤
  (VMWorkloads,             │
   WorkloadDependency)      ├──▶ risk_heatmap.compute_heatmap() ──▶ RiskHeatmap
                            │
perf_history.json ──────────┤
  (PerformanceMetrics)      │
                            │
enrichment_data.json ───────┤
  (EnrichmentTelemetry.tags)│
                            │
vulnerability_sla ──────────┘
  (_match_os function)
```

## Validation Rules

1. **composite_score**: Integer, clamped to [0, 100]
2. **factor.score**: Integer, clamped to [0, 100]
3. **factor.weight**: Float, all weights must sum to 1.0 (±0.001 tolerance)
4. **factors list**: Must contain exactly 6 entries, one per `RiskFactorName`
5. **band assignment**: Deterministic from score — 0–30 → green, 31–60 → yellow, 61–100 → red
6. **top_risky**: Sorted descending by `composite_score`; ties broken alphabetically by `vm_name`
7. **vm_name**: Must match an existing `DiscoveredVM.name` in the discovery dataset

## State Transitions

Risk scores are stateless — computed on-demand from the current discovery/enrichment/perf data. No persisted risk state. When source data changes (re-discovery, new enrichment, perf sample), the next heatmap computation reflects the updated state.

## Default Weights

| Factor | Weight | Justification |
|--------|--------|---------------|
| `dependency_count` | 0.15 | Dependencies increase coordination complexity but can be managed with wave planning |
| `os_eol` | 0.25 | EOL OS is a binary, high-impact factor — requires upgrade or ESU commitment |
| `workload_complexity` | 0.20 | Database migrations are inherently riskier than stateless workload migrations |
| `performance_sensitivity` | 0.10 | High IOPS affects storage tier selection but is addressable with proper sizing |
| `compliance_scope` | 0.20 | Regulated workloads require audit trails, landing zone controls, and approval gates |
| `data_volume` | 0.10 | Large disks extend migration duration but are addressable with offline transfer |
