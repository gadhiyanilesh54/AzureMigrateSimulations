# Feature Spec: Pre-Migration Validation Runbooks

**ID**: 05-pre-migration-runbooks  
**Phase**: MIGRATE  
**Priority**: Tier 1 — High Impact  
**Status**: Not Started  
**Depends On**: Cloud Topology (✅), Wave Planning (✅), Assessment (✅)

## Problem Statement

After planning, there is no automated way to validate that the Azure environment is ready for migration. Customers manually create checklists in Excel/Word — missing critical checks (quota, network conflicts, DNS). Failed migrations due to missing prerequisites cost days of rework.

## Goal

Generate **executable runbooks** (YAML + shell scripts) for pre-migration validation, migration execution steps, and post-migration verification — customised per wave with the actual VM names, SKUs, network ranges, and dependencies from the assessment.

## User Stories

### US-1: Pre-Migration Validation Runbook (P1)
**Given** a wave plan with assigned VMs, **When** the user generates runbooks, **Then** a pre-migration runbook is produced with checks:
- Azure subscription vCPU quota vs required (per SKU family)
- Network address space conflicts (proposed CIDRs vs existing VNets)
- DNS resolution for internal domains
- Source VM snapshot creation commands
- Storage account capacity for replication staging
- Azure RBAC permissions validation

### US-2: Migration Execution Runbook (P1)
**Given** a wave plan, **When** generated, **Then** an execution runbook contains per-wave steps:
- Deploy landing zone infrastructure (Terraform/Bicep apply)
- Validate infrastructure deployment
- Enable replication per VM
- Test failover to isolated VNet
- Production failover
- DNS cutover commands

### US-3: Post-Migration Validation Runbook (P1)
**Given** migrated VMs, **When** generated, **Then** a post-migration runbook contains:
- VM health checks (power state, agent status)
- Application connectivity validation (Test-NetConnection for each dependency)
- Performance baseline comparison (Azure Monitor vs on-prem P95)
- DNS record verification
- Backup policy activation
- On-prem decommission checklist

### US-4: Runbook Export Formats (P2)
**Given** generated runbooks, **When** exported, **Then** available as:
- YAML (structured, parseable by automation tools)
- Markdown (human-readable for documentation)
- Shell script (directly executable `az` commands)

### US-5: MCP Tools for Runbooks (P1)
**Given** the MCP server, **When** an agent calls `generate_runbooks`, **Then** all three runbooks (pre/execution/post) are generated. Individual tools: `get_pre_migration_checks`, `get_migration_steps`, `get_post_migration_checks`.

## Functional Requirements

- **FR-001**: Generate pre-migration checks customised per wave (actual VM names, SKUs, CIDRs).
- **FR-002**: Generate `az` CLI commands for quota validation.
- **FR-003**: Generate network conflict detection commands.
- **FR-004**: Generate per-VM migration execution steps.
- **FR-005**: Generate post-migration connectivity tests from dependency data.
- **FR-006**: Generate performance comparison thresholds from enrichment/perf data.
- **FR-007**: Each check has: ID, name, type (automated/manual), command, expected result, remediation.
- **FR-008**: Add REST endpoints: `POST /api/runbooks/generate`, `GET /api/runbooks/{type}`.
- **FR-009**: Add MCP tools: `generate_runbooks`, `get_pre_migration_checks`.
- **FR-010**: Add web UI panel for runbook viewing and export.

## Technical Approach

### New Module: `src/azure_migrate_simulations/runbook_generator.py`

```python
def generate_runbooks(topology: dict, wave_plan: dict, discovery: dict) -> RunbookBundle:
    """Generate all three runbooks from topology + wave plan + discovery data."""

@dataclass
class RunbookCheck:
    id: str           # e.g., "PRE-001"
    name: str         # e.g., "Azure vCPU Quota Check"
    type: str         # "automated" | "manual" | "semi-automated"
    wave: int
    command: str | None
    expected: str
    remediation: str | None

@dataclass  
class RunbookBundle:
    pre_migration: list[RunbookCheck]
    execution: list[RunbookStep]
    post_migration: list[RunbookCheck]
```

## Acceptance Criteria

1. Pre-migration runbook includes vCPU quota check with actual required counts per SKU family.
2. Network validation uses actual proposed CIDR ranges from CTD.
3. Post-migration connectivity checks use actual dependency ports from discovery.
4. All `az` CLI commands are syntactically valid.
5. Runbooks are wave-specific (different checks per wave).
6. Export works in YAML, Markdown, and shell script formats.
