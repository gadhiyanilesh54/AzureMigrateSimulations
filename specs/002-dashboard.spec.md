---
feature: dashboard
status: implemented
module: web/app.py, web/templates/index.html
---

# Dashboard

## Summary

Fleet-wide overview tab displaying aggregated VMware environment statistics and Azure migration insights through summary cards and interactive charts. Renders immediately after data is loaded.

## User Stories

- As a migration planner, I want a single-page overview of the entire VMware fleet so that I can quickly assess scale and migration readiness.
- As a stakeholder, I want to see estimated Azure monthly cost at a glance so that I can gauge budget impact.
- As an analyst, I want interactive charts breaking down readiness, OS distribution, and cost by VM family so that I can prioritize migration effort.

## Functional Requirements

- **FR-1:** Display 6 summary cards: VMs, ESXi Hosts, Total vCPUs, Memory (GB), Disk (TB), Est. Azure Cost/mo.
- **FR-2:** Render 6 interactive charts:
  1. Migration Readiness (doughnut)
  2. OS Distribution (doughnut)
  3. Power State (doughnut)
  4. Azure VM Family Distribution (horizontal bar)
  5. Monthly Cost by Family (horizontal bar)
  6. VMs by Folder (horizontal bar)
- **FR-3:** Charts must update when underlying data changes (e.g., enrichment upload, what-if override).
- **FR-4:** Summary cards show real-time aggregated values computed from loaded VM and recommendation data.
- **FR-5:** Charts support hover tooltips with detailed values.

## Non-Functional Requirements

- **NFR-1:** Dashboard must render within 500 ms for up to 500 VMs.
- **NFR-2:** Charts must be responsive and retain legibility on viewports ≥ 768 px.
- **NFR-3:** Azure-themed colour palette for visual consistency.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/summary` | Dashboard summary statistics and chart data |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — `/api/summary` handler computing aggregates
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — Chart.js rendering, tab layout

### Key Classes / Functions

- `/api/summary` endpoint — aggregates VM counts, CPU/memory/disk totals, cost sums, readiness breakdown, OS distribution, family distribution, folder distribution
- Chart.js v4.4.1 — client-side charting library

### Data Models

- Summary response JSON containing `total_vms`, `total_hosts`, `total_vcpus`, `total_memory_gb`, `total_disk_tb`, `estimated_monthly_cost`, and chart data arrays.

## Dependencies

- Chart.js 4.4.1 (CDN)
- Bootstrap 5.3.3 dark theme (CDN)

## Test Coverage

- `tests/test_visualization.py` — validates summary data formatting

## Acceptance Criteria

- [ ] GET `/api/summary` returns all 6 summary card values and chart dataset arrays.
- [ ] Dashboard renders 6 cards with correct aggregated numbers matching loaded data.
- [ ] Doughnut charts show correct proportions for readiness, OS, and power state.
- [ ] Bar charts display correct VM counts and costs per Azure family.
- [ ] Charts respond to window resize without overflow or clipping.
- [ ] Cards update after enrichment data is uploaded.
