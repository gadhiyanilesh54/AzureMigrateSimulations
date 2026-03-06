# Research: Cloud Topology Diagram (CTD)

**Feature**: `001-cloud-topology-diagram` | **Date**: 2026-03-04

## Decision 1: Diagram Rendering Approach

**Decision**: Use vis-network with `beforeDrawing` canvas callback for nested bounding boxes, combined with the hierarchical layout and `level` property for vertical ordering.

**Rationale**: vis-network is already loaded via CDN (zero new dependencies, constitution §4). While it has no native "subgraph" support, the `beforeDrawing` callback provides full control to draw labeled bounding rectangles around groups of nodes. This is the standard community approach. The hierarchical layout with explicit `level` values controls the vertical layering (landing zones at top, resources at bottom).

**Alternatives considered**:
- **Cytoscape.js compound nodes** — native nested containers, but would require adding a new CDN dependency (~300 KB) and rewriting the two existing topology views for consistency. Rejected: violates minimal dependencies principle.
- **ELK.js** — powerful hierarchical layout, but heavyweight (~1 MB) and requires a separate layout engine. Rejected: bundle size.
- **vis-network clustering** — built-in collapse/expand, but doesn't show simultaneous nesting. Rejected: hides context the user needs.
- **D3.js** — maximum flexibility but requires building everything from scratch. Rejected: excessive effort for the benefit.

## Decision 2: Nested Visual Containers

**Decision**: Implement bounding boxes via the `beforeDrawing` canvas callback. Each landing zone, VNet, and subnet is represented as a "container" entry in the topology data (not a vis-network node). On each draw cycle, iterate over container definitions, compute the bounding box from contained node positions (with padding), and draw labeled rounded rectangles with distinct colours per container type.

**Rationale**: This approach gives the visual effect of nested subgraphs (similar to Mermaid's `subgraph`) while keeping node interaction (click, hover, drag) handled by vis-network natively. The backend returns both `nodes[]`, `edges[]`, and a new `containers[]` array describing the containment hierarchy.

**Alternatives considered**:
- **Background "box" nodes** — fragile, doesn't scale, interferes with physics. Rejected.
- **Multiple vis-network instances** (one per landing zone) — breaks cross-zone edges. Rejected.

## Decision 3: Mermaid Export Format

**Decision**: Use Mermaid `flowchart TB` with nested `subgraph` blocks. Landing zones → VNets → Subnets as nested subgraphs; resources as leaf nodes; edges between nodes represent dependencies.

**Rationale**: Flowchart with subgraphs is the most mature and widely supported Mermaid diagram type. It supports arbitrary nesting depth, `classDef` styling, and directional edges — a perfect match for the topology structure.

**Alternatives considered**:
- **Mermaid C4 diagram** — designed for software architecture levels, not infrastructure grouping. Rejected: wrong abstraction.
- **Mermaid architecture-beta** — newer, has icons, but limited nesting support and unstable syntax. Rejected: maturity.

## Decision 4: WAF Scoring Data Sources

**Decision**: Score each WAF pillar using only data already available in the discovery/enrichment/assessment pipeline. No external Azure Advisor or policy engine calls.

| Pillar | Data Sources | Score Basis |
|--------|-------------|-------------|
| **Reliability** | VM power state, OS family, perf data availability | No HA config discoverable from vCenter → base score ~35; bonus for perf data (indicates monitoring); bonus for multiple VMs in same workload |
| **Security** | `vulnerability_sla.py` OS/software lifecycle analysis, guest OS family, enrichment data | EOL OS → low score; supported OS → higher; enrichment data boosts (indicates monitoring coverage) |
| **Cost Optimisation** | Recommendation confidence score, AHUB eligibility, what-if overrides | High confidence → higher score; AHUB eligible → bonus; what-if override saved → bonus (indicates user validated sizing) |
| **Operational Excellence** | Enrichment data presence, VMware tools status, perf collector status | Enrichment uploaded → major bonus; VMware tools running → bonus; perf data → bonus |
| **Performance Efficiency** | Perf data availability, CPU/memory P95 percentiles, IOPS | No perf data → "Insufficient Data"; with perf data: low utilisation → high score (headroom); high utilisation → lower score (needs right-sizing) |

**Rationale**: This leverages all existing data pipelines without new external calls. The vulnerability_sla module already analyses OS lifecycle, enrichment already provides monitoring coverage, and perf_aggregator already computes percentiles. The scoring function simply reads these existing data points.

## Decision 5: CAF Landing Zone Classification

**Decision**: Use a regex-based heuristic on the vCenter `folder` field to classify VMs into environments, then map environments to CAF landing zones.

**Classification rules (ordered)**:
1. Folder contains `dev|test|staging|qa|sandbox|lab` (case-insensitive) → **Dev/Test** landing zone
2. VM `migration_readiness` is "Not Ready" → **Requires Attention** group
3. All others → **Production** landing zone

**Platform landing zones** (always generated):
- **Connectivity**: Hub VNet with optional firewall, VPN gateway, bastion (FR-014 toggleable components)
- **Management**: Azure Monitor, Backup placeholders (no discovered VMs placed here)

**Rationale**: The folder heuristic was validated against the actual sample data (202 VMs). Most VMs have organizational folder names that don't match dev/test patterns, so they correctly default to Production (per clarification Q4). The regex approach is extensible — users could refine patterns later.

## Decision 6: PNG Export Approach

**Decision**: Use vis-network's underlying canvas element via `network.canvas.frame.canvas.toDataURL('image/png')`. Before capture, call `network.fit({animation: false})` and listen for `afterDrawing` event.

**Rationale**: Zero new dependencies. The `fit()` + `afterDrawing` + `toDataURL()` pattern is the standard vis-network community approach. The auto-fit ensures all nodes are visible in the export.

## Decision 7: Backend API Shape

**Decision**: Two new endpoints:

1. `GET /api/cloud-topology` — generates and returns the full topology graph:
   ```json
   {
     "containers": [...],      // landing zones, vnets, subnets (hierarchical)
     "nodes": [...],           // vis-network nodes (Azure resources)
     "edges": [...],           // vis-network edges (dependencies)
     "cost_summary": {...},    // per-landing-zone cost breakdown
     "waf_summary": {...},     // aggregate WAF scores
     "optional_components": {...},  // toggleable infra with costs
     "mermaid": "..."          // pre-generated Mermaid diagram string
   }
   ```

2. `GET /api/cloud-topology/waf/<resource_id>` — returns detailed WAF assessment for one resource (loaded on click from the frontend, keeping the initial payload light).

**Rationale**: Splitting WAF details into a separate endpoint avoids sending ~50 KB of recommendation text for 200+ resources upfront. The main endpoint returns the graph structure and summary scores; details are fetched on demand.
