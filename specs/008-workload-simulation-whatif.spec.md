---
feature: workload-simulation-whatif
status: implemented
module: workload_mapping.py, azure_pricing.py, web/app.py
---

# Workload Simulation & What-If

## Summary

Workload-level Azure PaaS migration cost simulation with per-workload What-If modelling (alternative Azure services, pricing) and fleet-wide workload simulation with 12-month projection and wave planning.

## User Stories

- As a migration planner, I want to compare Azure SQL Database vs Azure SQL Managed Instance for a discovered SQL Server so that I can choose the best migration path.
- As a cost analyst, I want a fleet-wide workload cost projection so that I can budget for PaaS adoption.
- As an architect, I want to see a migration playbook for each alternative so that I know the effort involved.

## Functional Requirements

### Per-Workload What-If (modal)

- **FR-1:** Display workload details: type, version, port, source VM, recommended Azure PaaS service.
- **FR-2:** Show step-by-step migration playbook with complexity rating.
- **FR-3:** Present alternative Azure services grid with cost comparison and complexity.
- **FR-4:** Allow region and pricing model override (PAYG, RI, Dev/Test, EA).

### Fleet-Wide Workload Simulation

- **FR-5:** Accept region, pricing model, wave count, and workload type filter.
- **FR-6:** Show per-type cost cards: databases, web apps, containers.
- **FR-7:** Render 12-month cumulative cost projection chart.
- **FR-8:** Group workloads into migration waves.

## Non-Functional Requirements

- **NFR-1:** PaaS pricing uses Azure Retail Prices API with same caching as VM pricing.
- **NFR-2:** Workload overrides persisted separately from VM overrides.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/workloads/whatif` | Per-workload what-if scenario |
| `POST` | `/api/workloads/simulate` | Fleet-wide workload simulation |
| `GET` | `/api/workloads/whatif_overrides` | Get saved workload overrides |
| `POST` | `/api/workloads/whatif_overrides` | Save a workload override |
| `DELETE` | `/api/workloads/whatif_overrides/<key>` | Delete one workload override |
| `DELETE` | `/api/workloads/whatif_overrides` | Clear all workload overrides |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/workload_mapping.py](../src/digital_twin_migrate/workload_mapping.py) — PaaS service catalogs, playbooks
- [src/digital_twin_migrate/azure_pricing.py](../src/digital_twin_migrate/azure_pricing.py) — PaaS meter map, Retail Prices API
- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — workload simulation endpoints
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — workload What-If modal

### Key Classes / Functions

- `_PAAS_METER_MAP` — maps PaaS service+SKU to Azure Retail API query filters
- `generate_workload_recommendations()` — primary mapping function
- `AzureServiceOption` — service name, tier, monthly cost, migration approach, complexity, playbook steps

### Data Models

- Workload What-If response: `{ workload, recommended, alternatives[], playbook }`
- Workload simulation response: `{ total_cost, per_type_costs, projection_12m[], wave_plan[] }`

## Dependencies

- Same as VM simulation (requests, Azure Retail Prices API).

## Test Coverage

- No dedicated workload simulation tests yet.

## Acceptance Criteria

- [ ] POST `/api/workloads/whatif` returns recommended and alternative Azure services.
- [ ] Each alternative includes a step-by-step migration playbook.
- [ ] POST `/api/workloads/simulate` returns per-type cost breakdown and 12-month projection.
- [ ] Saved workload overrides are reflected in fleet simulation.
- [ ] SQL Server workload shows at least 3 alternatives (SQL DB, SQL MI, SQL VM).
