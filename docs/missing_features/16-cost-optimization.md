# Feature Spec: Cost Optimization Engine

**ID**: 16-cost-optimization  
**Phase**: PLAN  
**Priority**: Tier 3 — Strategic  
**Status**: Not Started  
**Depends On**: Assessment (✅), Enrichment (✅), Pricing (✅)

## Problem Statement

The assessment recommends a single SKU per VM based on right-sizing, but doesn't recommend **which pricing commitment** is optimal per VM. A VM with steady 24/7 usage should get a 3yr RI; a dev/test VM used 8 hours/day should stay PAYG or use Dev/Test pricing. Without per-VM pricing guidance, customers either over-commit (waste RI spend on idle VMs) or under-commit (pay PAYG for steady-state workloads).

## Goal

Analyse each VM's usage pattern (from enrichment and perf data) and recommend the **optimal pricing model** per VM, plus a blended fleet recommendation that maximises savings.

## User Stories

### US-1: Per-VM Pricing Recommendation (P1)
**Given** a VM with perf/enrichment data, **When** cost optimisation runs, **Then** recommend:
- **3yr RI**: if CPU utilisation is steady (low variance), runs 24/7
- **1yr RI**: if steady but shorter commitment preferred
- **Savings Plan**: if VM may be resized or family-changed
- **AHUB**: if Windows with active Software Assurance
- **Dev/Test**: if in dev/test folder and <12h/day average usage
- **PAYG**: if usage is sporadic, short-lived, or unknown

### US-2: Blended Fleet Recommendation (P1)
**Given** all VMs with individual recommendations, **Then** show: "Apply 3yr RI to 120 VMs, 1yr SP to 30 VMs, Dev/Test to 25 VMs, PAYG to 27 VMs → total savings: $X/mo vs all-PAYG."

### US-3: Utilisation-Based Right-Sizing Alerts (P2)
**Given** perf data, **When** analysed, **Then** flag:
- **Oversized**: P95 CPU < 20% AND P95 Memory < 30% → recommend downsize
- **Undersized**: P95 CPU > 85% OR P95 Memory > 90% → recommend upsize
- **Zombie**: Powered on but P95 CPU < 2% → recommend decommission

### US-4: MCP Tool (P1)
Tool: `optimize_costs` returns per-VM and fleet-level recommendations.

## Functional Requirements

- **FR-001**: Analyse CPU/memory utilisation variance to determine workload pattern.
- **FR-002**: Map patterns to optimal pricing models.
- **FR-003**: Calculate fleet cost under blended pricing (different model per VM).
- **FR-004**: Detect oversized, undersized, and zombie VMs.
- **FR-005**: REST endpoint: `GET /api/cost-optimization`.
- **FR-006**: MCP tool: `optimize_costs`.
- **FR-007**: Include recommendations in executive report (spec 06).

## Acceptance Criteria

1. VMs with steady utilisation (low CoV) get RI/SP recommendation.
2. VMs in dev/test folders get Dev/Test pricing recommendation.
3. Windows VMs with eligible OS versions get AHUB recommendation.
4. Zombie VMs (< 2% CPU) are flagged for decommission.
5. Blended fleet savings are higher than any single-model approach.
