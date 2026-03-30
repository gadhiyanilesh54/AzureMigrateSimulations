# Feature Spec: Tagging Strategy from Discovery Metadata

**ID**: 09-tagging-strategy  
**Phase**: PLAN  
**Priority**: Tier 2 — Medium Impact  
**Status**: Not Started  
**Depends On**: vCenter Discovery (✅), Assessment (✅), Wave Planning (✅)

## Problem Statement

Azure tags are critical for cost management, automation, and governance. Currently no tags are generated. Customers must manually define tag policies after migration — losing the rich metadata already captured from vCenter (folders, clusters, annotations, resource pools).

## Goal

Auto-generate an Azure tagging strategy from vCenter metadata, and include tags in CTD resources and IaC output.

## User Stories

### US-1: Auto-Tag Mapping (P1)
**Given** vCenter metadata, **When** tagging is generated, **Then** the following tags are applied:
| Tag Key | Source |
|---------|--------|
| `Environment` | vCenter folder name → dev/test/staging/production |
| `SourceVM` | Original VM name |
| `SourceHost` | ESXi host name |
| `MigrationWave` | Wave assignment number |
| `WorkloadType` | Discovered workload (database/webapp/container/general) |
| `OS` | Guest OS family |
| `CostCenter` | vCenter cluster name (configurable mapping) |
| `ManagedBy` | "AzureMigrateSimulations" |
| `MigrationDate` | Wave target date (if set) |

### US-2: Custom Tag Overrides (P2)
**Given** auto-generated tags, **When** the user provides custom mappings (e.g., "folder 'Finance' → CostCenter: CC-4200"), **Then** the overrides are applied.

### US-3: Tags in IaC Output (P1)
**Given** the tagging strategy, **When** Terraform/Bicep is generated, **Then** all resources include the tag block.

### US-4: MCP Tool (P1)
Tool: `get_tagging_strategy` returns the full tag plan. Tool: `set_tag_mapping` allows custom overrides.

## Functional Requirements

- **FR-001**: Extract tags from vCenter metadata (folder, cluster, annotation, resource pool).
- **FR-002**: Map folder names to Environment tag using pattern matching.
- **FR-003**: Allow custom tag key/value overrides per VM or per folder.
- **FR-004**: Include tags in CTD resource nodes.
- **FR-005**: Include tags in IaC output (Terraform `tags {}` block, Bicep `tags:` property).
- **FR-006**: Persist tag mappings to `data/tag_strategy.json`.
- **FR-007**: REST endpoints: `GET /api/tags/strategy`, `POST /api/tags/mappings`.
- **FR-008**: MCP tools: `get_tagging_strategy`, `set_tag_mapping`.
