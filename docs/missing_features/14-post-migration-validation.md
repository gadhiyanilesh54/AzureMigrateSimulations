# Feature Spec: Post-Migration Validation

**ID**: 14-post-migration-validation  
**Phase**: MIGRATE  
**Priority**: Tier 3 — Strategic  
**Status**: Not Started  
**Depends On**: Runbooks (Spec 05), Migration Tracker (Spec 07)

## Problem Statement

After VMs are migrated, there is no automated way to verify that applications are healthy, network connectivity works, and performance meets the on-prem baseline. Customers rely on manual testing, which misses issues until production users report problems.

## Goal

Generate and optionally execute **post-migration validation checks** that compare the Azure environment against the on-prem baseline captured during discovery and enrichment.

## User Stories

### US-1: Health Check Generation (P1)
**Given** migrated VMs, **When** post-migration validation is requested, **Then** generate checks per VM:
- VM power state is "running"
- VM agent status is "ready"
- All discovered listening ports are reachable
- DNS records resolve to new Azure IPs

### US-2: Connectivity Validation (P1)
**Given** dependency edges from discovery, **When** validating, **Then** for each dependency: `Test-NetConnection` from source VM to target VM on the discovered port.

### US-3: Performance Baseline Comparison (P2)
**Given** enrichment/perf data from on-prem, **When** validating, **Then** compare Azure Monitor metrics (CPU%, Memory%) against on-prem P95 baseline. Flag if Azure metrics exceed 120% of on-prem P95.

### US-4: Validation Dashboard (P2)
**Given** validation results, **When** displayed, **Then** show a pass/fail matrix per VM with drill-down to individual check results.

### US-5: MCP Tool (P1)
Tool: `validate_post_migration` returns check results per VM.

## Functional Requirements

- **FR-001**: Generate `az vm run-command` scripts for connectivity tests.
- **FR-002**: Generate Azure Monitor metric queries for performance comparison.
- **FR-003**: Compare actual vs baseline thresholds (configurable tolerance, default 20%).
- **FR-004**: Produce pass/fail summary per VM and per wave.
- **FR-005**: REST endpoint: `POST /api/validation/post-migration`.
- **FR-006**: MCP tool: `validate_post_migration`.
