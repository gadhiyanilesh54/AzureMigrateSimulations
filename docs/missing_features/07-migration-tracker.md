# Feature Spec: Migration Status Tracker

**ID**: 07-migration-tracker  
**Phase**: MIGRATE  
**Priority**: Tier 2 — Medium Impact  
**Status**: Not Started  
**Depends On**: Wave Planning (✅)

## Problem Statement

Once migration begins, there is no way to track which VMs have been migrated, which are in progress, and which are pending. Customers use spreadsheets to track status, losing the connection to assessment data.

## Goal

Add a per-VM migration **state machine** that tracks each VM through the migration lifecycle, with timestamps, notes, and blockers. The status integrates with the wave plan and dashboard.

## User Stories

### US-1: Per-VM Status Tracking (P1)
Each VM has a status field: `Not Started` → `Planned` → `Replicating` → `Test Failover` → `Migrated` → `Validated` → `Decommissioned`. Status can be set via API, MCP tool, or web UI.

### US-2: Wave Progress Dashboard (P1)
**Given** a wave plan with status-tracked VMs, **When** the dashboard is viewed, **Then** a progress bar per wave shows: 34/50 migrated, 10 replicating, 6 not started.

### US-3: Blocker Tracking (P2)
**Given** a VM in any status, **When** a blocker is logged, **Then** the VM status shows a warning icon and the blocker text (e.g., "Waiting for database migration in Wave 1").

### US-4: MCP Tools (P1)
Tools: `set_vm_migration_status`, `get_migration_progress`, `log_migration_blocker`.

## Functional Requirements

- **FR-001**: Per-VM status with allowed state transitions.
- **FR-002**: Timestamps for each state transition.
- **FR-003**: Wave-level progress aggregation.
- **FR-004**: Blocker/notes field per VM.
- **FR-005**: Persist to `data/migration_status.json`.
- **FR-006**: REST endpoints: `POST /api/migration/status`, `GET /api/migration/progress`.
- **FR-007**: MCP tools for status updates.
