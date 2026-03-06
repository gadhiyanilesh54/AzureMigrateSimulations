# Data Model: Cloud Topology Diagram (CTD)

**Feature**: `001-cloud-topology-diagram` | **Date**: 2026-03-04

## Entities

### CloudTopology

Top-level container for the entire generated Azure architecture.

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `str` (ISO 8601) | Timestamp of diagram generation |
| `source_vm_count` | `int` | Number of VMs used as input |
| `source_workload_count` | `int` | Number of workloads used as input |
| `total_monthly_cost` | `float` | Sum of all resource costs + optional components |
| `waf_summary` | `WAFScoreSummary` | Aggregate WAF scores across all resources |
| `landing_zones` | `list[LandingZone]` | CAF-aligned landing zones |
| `optional_components` | `dict[str, OptionalComponent]` | Toggleable infra (firewall, bastion, etc.) |

### LandingZone

CAF-aligned grouping of resources.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (e.g., `lz-connectivity`, `lz-prod`, `lz-devtest`) |
| `name` | `str` | Display name (e.g., "Connectivity", "App-LZ-Production") |
| `type` | `str` | One of: `connectivity`, `identity`, `management`, `application` |
| `environment` | `str \| None` | `production`, `devtest`, `attention`, or `None` for platform zones |
| `resource_groups` | `list[ResourceGroup]` | Resource groups within this landing zone |
| `aggregate_cost` | `float` | Sum of all resource costs in this zone |
| `waf_scores` | `WAFScoreSummary` | Aggregate WAF scores for this zone |

### ResourceGroup

Logical grouping of related resources within a landing zone, mapped to an Azure Resource Group.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (e.g., `rg-prod-web`, `rg-connectivity`) |
| `name` | `str` | Display name following CAF convention (e.g., "rg-prod-web-001") |
| `vnets` | `list[VNet]` | Virtual networks in this resource group |

### VNet

Virtual network containing subnets.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (e.g., `vnet-hub`, `vnet-prod-001`) |
| `name` | `str` | Display name (e.g., "hub-vnet", "spoke-prod-vnet") |
| `address_space` | `str` | CIDR block (generated, e.g., `10.0.0.0/16`) |
| `subnets` | `list[Subnet]` | Subnets within this VNet |

### Subnet

Workload-type subnet grouping resources.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (e.g., `sn-webapp-001`) |
| `name` | `str` | Display name (e.g., "webapp-subnet", "database-subnet", "general-compute") |
| `workload_type` | `str` | One of: `webapp`, `database`, `container`, `orchestrator`, `general_compute`, `gateway`, `firewall` |
| `address_range` | `str` | CIDR block (generated, e.g., `10.1.1.0/24`) |
| `resources` | `list[str]` | List of `CloudResource.id` values in this subnet |

### CloudResource

An Azure resource mapped from a discovered VM or workload.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier (e.g., `res-vm-WindowsVM175`) |
| `source_vm_name` | `str` | Original on-prem VM name |
| `source_workload_name` | `str \| None` | Workload name if from workload discovery |
| `azure_service` | `str` | Azure service type (e.g., "Azure VM", "Azure SQL Database", "App Service") |
| `azure_sku` | `str` | Recommended SKU (e.g., "Standard_D4s_v5") |
| `monthly_cost` | `float` | Estimated monthly cost in USD |
| `migration_readiness` | `str` | "Ready", "Ready with conditions", "Not Ready" |
| `landing_zone_id` | `str` | Parent landing zone ID |
| `subnet_id` | `str` | Parent subnet ID |
| `resource_type` | `str` | Visual category: `vm`, `database`, `webapp`, `container`, `orchestrator`, `networking`, `security`, `monitoring` |
| `waf_scores` | `WAFScores` | Per-pillar WAF scores |

### TopologyEdge

Directed connection between two cloud resources.

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Source `CloudResource.id` |
| `target_id` | `str` | Target `CloudResource.id` |
| `protocol` | `str` | TCP, UDP, or unknown |
| `port` | `int \| None` | Port number |
| `service_type` | `str \| None` | Service type label (e.g., "HTTP", "SQL") |
| `cross_zone` | `bool` | True if edge crosses landing zone boundaries |

### WAFScores

Per-resource WAF pillar scores.

| Field | Type | Description |
|-------|------|-------------|
| `reliability` | `int \| None` | 0–100 or `None` (insufficient data) |
| `security` | `int \| None` | 0–100 or `None` |
| `cost_optimisation` | `int \| None` | 0–100 or `None` |
| `operational_excellence` | `int \| None` | 0–100 or `None` |
| `performance_efficiency` | `int \| None` | 0–100 or `None` |

### WAFScoreSummary

Aggregate WAF scores with resource counts.

| Field | Type | Description |
|-------|------|-------------|
| `scores` | `WAFScores` | Average scores (excluding None values) |
| `resource_count` | `int` | Number of resources included |
| `insufficient_data_count` | `dict[str, int]` | Per-pillar count of resources with None |

### WAFAssessment

Detailed per-resource WAF breakdown returned by the detail endpoint.

| Field | Type | Description |
|-------|------|-------------|
| `resource_id` | `str` | `CloudResource.id` |
| `pillars` | `list[WAFPillarDetail]` | Detailed per-pillar breakdown |

### WAFPillarDetail

Single WAF pillar detail.

| Field | Type | Description |
|-------|------|-------------|
| `pillar` | `str` | Pillar name |
| `score` | `int \| None` | 0–100 or None |
| `status` | `str` | `scored`, `insufficient_data` |
| `data_sources_used` | `list[str]` | Which data contributed (e.g., "vcenter_discovery", "enrichment", "perf_history") |
| `missing_data_prompt` | `str \| None` | Prompt for user action if status is `insufficient_data` |
| `recommendations` | `list[WAFRecommendation]` | Actionable suggestions |

### WAFRecommendation

Single recommendation within a WAF pillar.

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Short title (e.g., "Enable Availability Zones") |
| `description` | `str` | Detailed recommendation text |
| `impact` | `str` | `high`, `medium`, `low` |
| `effort` | `str` | `low`, `medium`, `high` |

### OptionalComponent

Toggleable infrastructure component.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Component key (e.g., `azure_firewall`, `bastion`, `load_balancer`, `vpn_gateway`) |
| `name` | `str` | Display name |
| `monthly_cost_base` | `float` | East US PAYG base cost |
| `enabled` | `bool` | Current toggle state (default: `false`) |
| `landing_zone_id` | `str` | Which landing zone this belongs to |
| `subnet_id` | `str` | Which subnet (e.g., `AzureFirewallSubnet`) |

## Relationships

```
CloudTopology
  └── LandingZone (1:N)
        └── ResourceGroup (1:N)
              └── VNet (1:N)
                    └── Subnet (1:N)
                          └── CloudResource (1:N) ← references by ID
                                └── WAFScores (1:1)

TopologyEdge → CloudResource (source_id)
TopologyEdge → CloudResource (target_id)

WAFAssessment → CloudResource (resource_id)
WAFAssessment → WAFPillarDetail (1:N)
WAFPillarDetail → WAFRecommendation (1:N)

OptionalComponent → LandingZone (belongs to)
OptionalComponent → Subnet (placed in)
```

## Validation Rules

- `CloudResource.monthly_cost` must be ≥ 0.
- `WAFScores` pillar values must be `None` or in range [0, 100].
- `TopologyEdge.source_id` and `target_id` must reference existing `CloudResource.id` values.
- `Subnet.resources` must contain only valid `CloudResource.id` values.
- `LandingZone.type` must be one of: `connectivity`, `identity`, `management`, `application`.
- `CloudResource.resource_type` must be one of: `vm`, `database`, `webapp`, `container`, `orchestrator`, `networking`, `security`, `monitoring`.

## Resource Type Visual Mapping

| `resource_type` | Colour | Icon (Bootstrap) | Shape |
|-----------------|--------|-------------------|-------|
| `vm` | `#58a6ff` (blue) | `bi-hdd` | dot |
| `database` | `#3fb950` (green) | `bi-database` | diamond |
| `webapp` | `#f0883e` (orange) | `bi-globe` | dot |
| `container` | `#bc8cff` (purple) | `bi-box` | square |
| `orchestrator` | `#39d2c0` (teal) | `bi-diagram-3` | triangle |
| `networking` | `#8b949e` (grey) | `bi-router` | dot |
| `security` | `#f85149` (red) | `bi-shield-lock` | star |
| `monitoring` | `#d29922` (yellow) | `bi-graph-up` | dot |

## State Transitions

No state machine applies — the topology is generated fresh on each request. The only mutable state is the `optional_components[].enabled` toggle, which is sent as a query parameter on the request.
