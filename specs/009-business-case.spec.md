---
feature: business-case
status: implemented
module: web/app.py, web/templates/index.html
---

# Business Case

## Summary

Comprehensive on-premises Total Cost of Ownership (TCO) vs Azure cost comparison generator. Produces an executive summary, itemised cost breakdowns, comparison charts, strategic recommendations, risk assessment, and full assumptions list.

## User Stories

- As a CTO, I want an executive summary showing ROI and payback period so that I can justify migration to the board.
- As a finance lead, I want an itemised on-prem cost breakdown (hardware, licensing, staffing, facilities) so that I can validate the TCO model against our actuals.
- As a migration planner, I want strategic recommendations (RI vs SP, AHUB, right-sizing) so that I can maximize savings.
- As an analyst, I want to adjust the pricing model, region, and analysis period to run different scenarios.

## Functional Requirements

- **FR-1:** Controls: pricing model, target region (10 regions), analysis period (1–5 years), include PaaS toggle.
- **FR-2:** Executive summary cards: on-prem annual cost, Azure annual cost, annual savings, payback period, 3-year total savings.
- **FR-3:** On-prem cost breakdown: hardware depreciation, VMware licensing, OS licensing, storage, networking, data centre, IT staff, security, backup/DR, downtime.
- **FR-4:** Azure cost breakdown: compute (with RI/SP), managed disks, networking, Monitor, Backup, Defender, support plan, AHUB savings, optional PaaS.
- **FR-5:** 4 comparison charts: side-by-side bar (monthly/annual), two doughnut charts (on-prem/Azure category breakdown), cumulative TCO projection line chart.
- **FR-6:** Strategic recommendations section: wave planning, RI vs SP guidance, AHUB, right-sizing.
- **FR-7:** Risk assessment: migration risks with mitigation strategies.
- **FR-8:** Full assumptions list (editable for what-if scenarios).
- **FR-9:** Migration one-time costs included in payback calculation.

## Non-Functional Requirements

- **NFR-1:** Business case generation must complete within 2 seconds for up to 500 VMs.
- **NFR-2:** All cost assumptions must be documented and traceable.
- **NFR-3:** Charts must be print-friendly (clean layout at 100% zoom).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/businesscase` | Generate comprehensive business case report |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pricing_model` | string | `payg` | PAYG, 1yr_ri, 3yr_ri, 1yr_sp, 3yr_sp |
| `target_region` | string | `eastus` | Target Azure region |
| `analysis_years` | int | `3` | TCO analysis period (1–5) |
| `include_paas` | bool | `false` | Include PaaS workload costs |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — `/api/businesscase` handler with 15+ cost assumptions
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — Business Case tab layout, Chart.js charts

### Key Classes / Functions

- `/api/businesscase` handler — computes on-prem TCO using industry-standard assumptions (VMware per-CPU licensing at ~$5,000, server hardware at $10,000/host amortised, staffing at ~25 VMs per admin, etc.)
- Azure costs derived from SKU recommendations with RI/SP discounts and add-on service estimates

### Data Models

- Business case response: `{ executive_summary, on_prem_breakdown, azure_breakdown, charts_data, recommendations[], risks[], assumptions[] }`

## Dependencies

- Chart.js 4.4.1 — comparison and projection charts

## Test Coverage

- No dedicated business case tests yet.

## Acceptance Criteria

- [ ] GET `/api/businesscase` returns a complete report with all sections.
- [ ] On-prem breakdown includes all 10 cost categories.
- [ ] Azure breakdown includes compute, storage, networking, and add-on services.
- [ ] Changing pricing model from PAYG to 3yr RI reduces Azure cost by ~40%.
- [ ] Payback period calculation accounts for migration one-time costs.
- [ ] Analysis period slider adjusts the cumulative TCO projection chart.
- [ ] AHUB savings are applied when Windows Server or SQL Server VMs are detected.
