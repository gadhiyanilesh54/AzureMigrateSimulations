---
feature: vm-simulation-whatif
status: implemented
module: azure_pricing.py, web/app.py
---

# VM Simulation & What-If

## Summary

Two-level scenario modelling: a per-VM What-If modal for deep-dive cost analysis with SKU/region/pricing overrides, and a fleet-wide cost simulation with 12-month projection and migration wave planning.

## User Stories

- As a cost analyst, I want to change a VM's Azure SKU and see the cost impact so that I can right-size recommendations.
- As a migration planner, I want to compare PAYG vs Reserved Instance pricing so that I can optimize costs.
- As a manager, I want a 12-month cost projection chart showing wave-based rollout so that I can plan budget.
- As a user, I want to drag VMs between migration waves so that I can customize the migration schedule.

## Functional Requirements

### Per-VM What-If (full-screen modal)

- **FR-1:** Display VM on-prem specs alongside the Azure SKU recommendation and cost estimate.
- **FR-2:** Show performance sparklines (CPU, memory, IOPS, network I/O) with avg/min/max/P95 stats.
- **FR-3:** Present full Azure SKU catalog grid (20+ SKUs) for alternative selection.
- **FR-4:** Allow region override with 10 Azure regions and cost multipliers.
- **FR-5:** Allow pricing model override: PAYG, 1yr/3yr Reserved Instance, 1yr/3yr Savings Plan.
- **FR-6:** Show bar chart comparing original vs. what-if monthly cost with savings percentage.
- **FR-7:** Persist overrides so they carry through to fleet simulation.

### Fleet-Wide Simulation

- **FR-8:** Accept target region, pricing model, wave count (1–8), and VM name filter.
- **FR-9:** Display side-by-side on-prem vs Azure total monthly cost with savings percentage.
- **FR-10:** Render 12-month projection line chart with wave-based migration rollout.
- **FR-11:** Show migration wave plan with drag-and-drop re-assignment between waves.
- **FR-12:** Per-VM comparison table showing original vs. adjusted SKU/region/pricing with cost deltas.
- **FR-13:** Optionally pull real-time prices from Azure Retail Prices API.

## Non-Functional Requirements

- **NFR-1:** Azure Retail Prices API responses must be cached for 6 hours.
- **NFR-2:** Fallback to hardcoded prices when API is unavailable.
- **NFR-3:** What-if overrides must be persisted to `data/whatif_overrides.json`.
- **NFR-4:** Fleet simulation for 500 VMs must complete within 3 seconds.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/simulate` | Run fleet-wide cost simulation |
| `POST` | `/api/simulate_vm` | Per-VM what-if scenario |
| `POST` | `/api/simulate_comparison` | Compare original vs. override costs |
| `GET` | `/api/regions` | Azure regions with cost multipliers |
| `GET` | `/api/pricing_models` | Available pricing models |
| `GET` | `/api/pricing/status` | Live pricing API status |
| `POST` | `/api/pricing/refresh` | Refresh live pricing from Azure |
| `GET` | `/api/whatif_overrides` | Get saved per-VM what-if overrides |
| `POST` | `/api/whatif_overrides` | Save a what-if override |
| `DELETE` | `/api/whatif_overrides/<vm>` | Delete one VM override |
| `DELETE` | `/api/whatif_overrides` | Clear all VM overrides |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/azure_pricing.py](../src/digital_twin_migrate/azure_pricing.py) — Azure Retail Prices API client, caching, pricing models (648 lines)
- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — simulation endpoints
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — What-If modal, charts, drag-and-drop waves

### Key Classes / Functions

- `AzureRetailPricing` — API client with in-memory + file-based cache
- `PRICING_MODELS` — tuple of supported models (PAYG, RI, SP, dev/test, EA/MCA)
- `HOURS_PER_MONTH = 730`
- Region cost multipliers (e.g., West Europe = 1.10×, Southeast Asia = 0.95×)
- Client-side wave drag-and-drop using HTML5 Drag API

### Data Models

- Simulation request: `{ region, pricing_model, waves, vm_filter }`
- Simulation response: `{ on_prem_cost, azure_cost, savings_pct, projection_12m[], wave_plan[], per_vm_comparison[] }`
- Override: `{ vm_name, sku, region, pricing_model }`

## Dependencies

- `requests` — HTTP client for Azure Retail Prices API

## Test Coverage

- No dedicated simulation tests yet; pricing logic to be tested.

## Acceptance Criteria

- [ ] POST `/api/simulate_vm` returns cost comparison with original and overridden values.
- [ ] POST `/api/simulate` returns fleet-wide totals, 12-month projection, and wave plan.
- [ ] Saved what-if overrides are reflected in fleet simulation results.
- [ ] Region multiplier correctly adjusts base prices.
- [ ] Reserved Instance pricing applies correct discount (e.g., ~40% for 3yr RI).
- [ ] 12-month projection chart shows gradual cost ramp as waves migrate.
- [ ] Drag-and-drop between waves updates the wave plan correctly.
