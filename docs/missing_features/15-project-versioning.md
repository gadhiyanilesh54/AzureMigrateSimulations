# Feature Spec: Project Versioning & Snapshots

**ID**: 15-project-versioning  
**Phase**: PLATFORM  
**Priority**: Tier 3 — Strategic  
**Status**: Not Started  
**Depends On**: Multi-Project (Spec 12)

## Problem Statement

Every operation overwrites existing data. A customer who generates a wave plan, then changes the pricing model, loses the previous wave plan. There is no undo, no comparison between versions, and no audit trail of decisions made.

## Goal

Add **versioned snapshots** of project state — allowing save, restore, compare, and audit of migration planning iterations.

## User Stories

### US-1: Save Snapshot (P1)
**Given** a project with current data, **When** the user saves a snapshot named "v1-initial-assessment", **Then** all data files are copied to `data/snapshots/v1-initial-assessment/` with a timestamp.

### US-2: Restore Snapshot (P1)
**Given** a saved snapshot, **When** restored, **Then** all data files are replaced with the snapshot's versions. Current state is auto-saved as "pre-restore-{timestamp}" first.

### US-3: Compare Snapshots (P2)
**Given** two snapshots, **When** compared, **Then** show deltas: VMs added/removed, SKU changes, cost differences, wave reassignments.

### US-4: Snapshot History (P1)
**Given** multiple snapshots, **When** listed, **Then** show: name, timestamp, VM count, total cost, wave count.

### US-5: MCP Tools (P1)
Tools: `save_snapshot`, `restore_snapshot`, `list_snapshots`, `compare_snapshots`.

## Functional Requirements

- **FR-001**: Snapshots stored as timestamped copies of all `data/*.json` files.
- **FR-002**: Save snapshot: copy current state to `data/snapshots/{name}/`.
- **FR-003**: Restore snapshot: swap current state with snapshot (with auto-backup).
- **FR-004**: Compare: diff two snapshots and summarise changes.
- **FR-005**: REST endpoints: `POST /api/snapshots`, `GET /api/snapshots`, `POST /api/snapshots/{name}/restore`.
- **FR-006**: MCP tools for all operations.

## Acceptance Criteria

1. Saving a snapshot preserves all data files.
2. Restoring a snapshot returns the project to exact previous state.
3. Current state is auto-saved before restore (no data loss).
4. Comparison shows cost delta, VM count delta, wave changes.
