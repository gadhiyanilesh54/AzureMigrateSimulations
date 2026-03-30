# Feature Spec: Multi-Project Support

**ID**: 12-multi-project  
**Phase**: PLATFORM  
**Priority**: Tier 2 — Medium Impact  
**Status**: Not Started  
**Depends On**: All existing features (✅)

## Problem Statement

The application uses a single global `data/` directory. A consultant working with multiple customers must back up and swap data files manually. Partners running multiple engagements simultaneously cannot use the tool concurrently.

## Goal

Support **multiple isolated projects**, each with its own data directory, that can be created, listed, switched, and archived independently.

## User Stories

### US-1: Create Project (P1)
**Given** the application, **When** a user creates a project named "Contoso-Migration", **Then** a new directory `data/projects/contoso-migration/` is created with empty data files.

### US-2: Switch Project (P1)
**Given** multiple projects exist, **When** the user switches to "Contoso-Migration", **Then** all API calls read/write from that project's directory.

### US-3: List Projects (P1)
**Given** multiple projects, **When** listed, **Then** show: name, created date, VM count, last modified.

### US-4: Archive/Delete Project (P2)
**Given** a project, **When** archived, **Then** it's moved to `data/archive/` and no longer appears in the active list.

### US-5: MCP Tools (P1)
Tools: `list_projects`, `create_project`, `switch_project`.

## Functional Requirements

- **FR-001**: Projects stored as subdirectories under `data/projects/`.
- **FR-002**: Active project tracked in `data/_active_project.json`.
- **FR-003**: All data access functions (`_get_discovery()`, etc.) resolve to active project's directory.
- **FR-004**: Default project "default" created if no projects exist (backward compatible).
- **FR-005**: REST endpoints: `GET /api/projects`, `POST /api/projects`, `POST /api/projects/{id}/activate`.
- **FR-006**: MCP tools: `list_projects`, `create_project`, `switch_project`.
- **FR-007**: Web UI project switcher in navigation bar.

## Acceptance Criteria

1. Two projects can exist simultaneously with different discovery data.
2. Switching projects changes all API responses to that project's data.
3. Existing data (before this feature) is automatically migrated to a "default" project.
4. MCP tools respect the active project context.
