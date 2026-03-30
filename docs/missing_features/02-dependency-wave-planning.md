# Feature Spec: Dependency-Aware Wave Planning

**ID**: 02-dependency-wave-planning  
**Phase**: PLAN  
**Priority**: Tier 1 — High Impact  
**Status**: Not Started  
**Depends On**: Guest Workload Discovery (✅), Wave Planning (✅)

## Problem Statement

Current wave planning uses **round-robin distribution** — VMs are evenly spread across waves without considering dependencies. This means a web server might be scheduled in Wave 1 while its database is in Wave 3, causing the web server to fail after migration until the database catches up. Customers must manually reorder waves, which is tedious for 200+ VMs.

## Goal

Automatically sequence VMs into waves based on **dependency topology** — databases and shared services migrate first, dependent application servers follow, and frontend/edge services migrate last. The system should use the TCP connection graph from guest discovery to determine dependency order.

## Existing Data Available

- `workload_discovery.json` → `dependencies[]` per VM: `{source_vm, target_vm, port, protocol, service_type}`
- `workload_discovery.json` → `established_connections[]`: TCP connections between VMs
- `workload_discovery.json` → workload types: database, webapp, container, orchestrator
- `vcenter_discovery.json` → VM folder hierarchy (can infer application groupings)
- `_wave_plan.json` → current wave assignments

## User Stories

### US-1: Auto-Sequence Waves by Dependency Order (P1)
**Given** discovered TCP dependencies between VMs, **When** the user generates a wave plan, **Then** VMs are ordered so that dependency targets (databases, shared services) appear in earlier waves than their dependents (web servers, app servers).

### US-2: Application Group Detection (P1)
**Given** TCP dependencies and VM naming patterns, **When** the wave plan is generated, **Then** VMs are grouped into logical applications (e.g., "ERP System: db01, app01, web01") and all VMs in an application group are placed in the same wave or consecutive waves.

### US-3: Dependency Conflict Warning (P2)
**Given** a user manually moves a VM to a later wave than its dependents, **When** the move is saved, **Then** a warning is shown: "VM 'db01' is a dependency of 'web01' (Wave 2). Moving db01 to Wave 3 may cause downtime."

### US-4: Wave Sequencing Rules (P2)
**Given** wave plan generation, **When** sequencing, **Then** the following priority rules apply:
1. **Wave 1**: Shared infrastructure (DNS, AD, file servers, shared databases)
2. **Wave 2**: Database tier (all discovered databases)
3. **Wave 3**: Application tier (app servers, middleware, containers)
4. **Wave 4+**: Frontend tier (web servers, load-balanced services)
5. **Last Wave**: "Requires Attention" VMs (Not Ready status)

### US-5: Circular Dependency Handling (P2)
**Given** two VMs with circular dependencies (A→B and B→A), **When** the wave plan is generated, **Then** both VMs are placed in the same wave with a note: "Circular dependency — migrate together."

### US-6: MCP Tool for Smart Wave Generation (P1)
**Given** the MCP server, **When** an agent calls `generate_smart_wave_plan`, **Then** a dependency-aware wave plan is generated and returned with dependency reasoning for each assignment.

## Functional Requirements

- **FR-001**: Build a directed dependency graph from discovered TCP connections.
- **FR-002**: Perform topological sort on the dependency graph to determine migration order.
- **FR-003**: Group VMs into application clusters using connected components in the dependency graph.
- **FR-004**: Assign waves based on topological depth: layer 0 (no dependencies) → Wave 1, layer 1 → Wave 2, etc.
- **FR-005**: Detect and handle circular dependencies by collapsing cycles into a single wave group.
- **FR-006**: Override wave assignment when workload type is known: databases always ≤ Wave 2, web apps always ≥ Wave 3.
- **FR-007**: Warn when manual wave moves violate dependency ordering.
- **FR-008**: Expose via REST API: `POST /api/waves/smart-plan`.
- **FR-009**: Expose via MCP tool: `generate_smart_wave_plan`.
- **FR-010**: Show dependency reasoning in wave plan output (why each VM is in its wave).

## Technical Approach

### Algorithm

```
1. Build adjacency list from workload dependencies
2. Detect strongly connected components (Tarjan's algorithm) → collapse cycles
3. Topological sort on the condensed DAG
4. Assign layers: sources (no incoming edges) = layer 0, others = max(predecessor layers) + 1
5. Map layers to waves (configurable compression: 10 layers → 4 waves)
6. Apply workload-type overrides (databases → early waves, web → late waves)
7. Balance wave sizes (move VMs between adjacent layers to equalize)
```

### New/Modified Files

- New: `src/azure_migrate_simulations/wave_planner.py` (~300 lines)
- Modified: `web/app.py` (new endpoint), `mcp_server.py` (new tool)
- Modified: `web/templates/index.html` (dependency warnings in wave UI)

## Acceptance Criteria

1. Database VMs are never in a later wave than their dependent web/app VMs.
2. Application groups (connected components) are kept in the same or consecutive waves.
3. Circular dependencies are detected and co-located in the same wave.
4. Manual wave moves that violate dependencies produce a warning.
5. Wave plan includes a `reason` field per VM explaining the assignment.
6. Works with 0 dependencies (falls back to round-robin).
