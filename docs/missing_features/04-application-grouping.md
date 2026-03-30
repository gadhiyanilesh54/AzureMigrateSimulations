# Feature Spec: Application Grouping

**ID**: 04-application-grouping  
**Phase**: DECIDE  
**Priority**: Tier 1 — High Impact  
**Status**: Not Started  
**Depends On**: Guest Workload Discovery (✅), Dependency Topology (✅)

## Problem Statement

Customers see a flat list of 202 VMs. They don't see "applications." A migration architect needs to know: "This is a 3-tier ERP system (db01 + app01 + web01)" — not three unrelated VMs. Without application grouping, wave planning, impact assessment, and stakeholder communication are all harder.

## Goal

Automatically detect and group VMs into **logical applications** using dependency edges, naming patterns, and vCenter folder structure. Each application group gets a name, criticality tier, component list, and migration complexity score.

## User Stories

### US-1: Auto-Detect Application Groups (P1)
**Given** TCP dependency data between VMs, **When** application grouping is run, **Then** connected components in the dependency graph are identified as application groups.

### US-2: Name Inference (P2)
**Given** VMs in an application group with names like `erp-db01`, `erp-app01`, `erp-web01`, **When** grouping, **Then** the group is named "ERP" (common prefix extraction).

### US-3: Folder-Based Grouping Fallback (P2)
**Given** VMs with no TCP dependencies but in the same vCenter folder, **When** grouping, **Then** they are grouped by folder name.

### US-4: Application Criticality Tagging (P1)
**Given** an application group, **When** displayed, **Then** the user can assign criticality: Tier-1 (mission-critical), Tier-2 (business-important), Tier-3 (non-critical). Default is Tier-2.

### US-5: Application Complexity Score (P2)
**Given** an application group, **When** assessed, **Then** a complexity score (1-10) is calculated based on: number of VMs, number of dependencies, cross-subnet connections, database count, container presence.

### US-6: MCP Tool (P1)
**Given** the MCP server, **When** an agent calls `list_applications`, **Then** all detected application groups are returned with their VMs, dependencies, criticality, and complexity.

## Functional Requirements

- **FR-001**: Build application groups from connected components in TCP dependency graph.
- **FR-002**: Merge groups that share a common VM name prefix (≥3 chars).
- **FR-003**: Fall back to vCenter folder grouping for VMs with no dependencies.
- **FR-004**: Allow user to override group names and criticality via API.
- **FR-005**: Calculate complexity score per group.
- **FR-006**: Persist application groups to `data/application_groups.json`.
- **FR-007**: Add REST endpoints: `GET /api/applications`, `POST /api/applications/{id}/criticality`.
- **FR-008**: Add MCP tools: `list_applications`, `set_application_criticality`.

## Acceptance Criteria

1. VMs connected by TCP dependencies are in the same application group.
2. Standalone VMs (no dependencies) are grouped by vCenter folder.
3. Application names are inferred from shared VM name prefixes.
4. Each group shows: VM list, dependency edges, workload types, total cost, complexity score.
5. Criticality can be set per group and persists across sessions.
