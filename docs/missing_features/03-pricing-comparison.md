# Feature Spec: Side-by-Side Pricing Comparison

**ID**: 03-pricing-comparison  
**Phase**: DECIDE  
**Priority**: Tier 1 — High Impact  
**Status**: Not Started  
**Depends On**: Azure Mapping (✅), Azure Pricing (✅)

## Problem Statement

Currently, customers can simulate costs with **one pricing model at a time** (PAYG, 1yr RI, 3yr RI, etc.). To compare, they must run multiple simulations and mentally track the numbers. Decision-makers need a single view showing all pricing options side-by-side to make informed commitment decisions.

## Goal

Generate a **pricing comparison matrix** showing fleet cost under all 7 pricing models simultaneously, with per-VM breakdowns and a recommendation of which model saves the most for each VM based on usage patterns.

## User Stories

### US-1: Fleet Pricing Matrix (P1)
**Given** assessed VMs with SKU recommendations, **When** the user requests a pricing comparison, **Then** a table shows total monthly cost under: PAYG, 1yr RI, 3yr RI, 1yr SP, 3yr SP, AHUB, Dev/Test — with savings percentages relative to PAYG.

### US-2: Per-VM Optimal Pricing Recommendation (P1)
**Given** each VM's usage pattern (from enrichment/perf data), **When** the comparison is generated, **Then** each VM gets a **recommended pricing model** based on:
- Steady-state workloads → 3yr RI (highest savings)
- Variable workloads → Savings Plan (flexibility)
- Dev/test workloads → Dev/Test pricing
- Windows workloads with SA → AHUB
- Short-lived/POC → PAYG

### US-3: Commitment Savings Summary (P2)
**Given** the pricing comparison, **When** rendered, **Then** show: "If you commit to 3yr RI for 150 VMs and use Dev/Test for 52 VMs, total monthly cost drops from $21,684 to $9,245 — saving $149,268/year."

### US-4: MCP Tool (P1)
**Given** the MCP server, **When** an agent calls `compare_pricing_models`, **Then** the full comparison matrix is returned.

## Functional Requirements

- **FR-001**: Calculate fleet cost under all 7 pricing models in a single call.
- **FR-002**: Show per-VM cost under each model.
- **FR-003**: Recommend optimal pricing model per VM based on workload characteristics.
- **FR-004**: Calculate blended savings when different VMs use different models.
- **FR-005**: Add REST endpoint: `GET /api/pricing/comparison`.
- **FR-006**: Add MCP tool: `compare_pricing_models`.
- **FR-007**: Add web UI tab/panel in assessment view.

## Acceptance Criteria

1. All 7 pricing models shown in one response.
2. Per-VM recommendation with reasoning.
3. Blended total shows mixed-model savings.
4. AHUB correctly applied only to Windows VMs with eligible licenses.
5. Dev/Test correctly applied only to VMs in dev/test folders.
