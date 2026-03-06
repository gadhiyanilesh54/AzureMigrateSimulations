---
feature: inventory
status: implemented
module: web/app.py, web/templates/index.html
---

# Inventory

## Summary

Unified, searchable resource table under the Discovery & Assessment tab. Aggregates VMs, databases, web apps, containers, networks, and file shares into a single filterable view.

## User Stories

- As an infrastructure engineer, I want a single table listing all discovered resources so that I can see the full scope of my environment.
- As a migration planner, I want to filter by resource type (VMs, databases, web apps, etc.) so that I can focus on specific workload categories.
- As a user, I want to search across all columns so that I can quickly find a specific resource.

## Functional Requirements

- **FR-1:** Display 6 clickable filter cards: VMs, Databases, Web Apps, Containers, Networks, File Shares.
- **FR-2:** Clicking a card toggles filter to show only that resource type; clicking again shows all.
- **FR-3:** Full-text search box filters across all columns: Parent VM, Type, Workload, Version, Port, Details.
- **FR-4:** Table populates from both vCenter discovery data (VMs, networks, datastores) and guest-level workload results (databases, web apps, containers).
- **FR-5:** Each row displays: Parent VM, Resource Type, Workload Name, Version, Port, Details.
- **FR-6:** Card badges show the count of resources per type.

## Non-Functional Requirements

- **NFR-1:** Table must handle 500+ rows without perceptible lag during search.
- **NFR-2:** Filter state persists within the current session (tab switch and back retains filter).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/vms` | List all discovered VMs with Azure recommendations |
| `GET` | `/api/hosts` | List ESXi hosts |
| `GET` | `/api/fileshares` | List datastores / file shares |
| `GET` | `/api/networks` | List discovered networks |
| `GET` | `/api/data/files` | List saved data files |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — REST endpoints serving resource lists
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — inventory table markup, JS filter logic

### Key Classes / Functions

- Client-side `filterInventory(type)` — toggles resource type filter
- Client-side `searchInventory(query)` — full-text row filtering

### Data Models

- VM list response: array of objects with `name`, `os`, `cpu`, `memory_mb`, `disks`, `power_state`, `recommendation`
- Host list response: array with `name`, `cpu_model`, `cpu_cores`, `memory_gb`, `esxi_version`
- Datastore / network list responses

## Dependencies

- Bootstrap 5.3.3 — table styling and filter card components

## Test Coverage

- No dedicated inventory tests; endpoint responses covered indirectly by integration test fixtures.

## Acceptance Criteria

- [ ] All 6 filter cards render with correct resource counts.
- [ ] Clicking a filter card shows only matching rows; clicking again shows all.
- [ ] Search box filters rows in real time across all displayed columns.
- [ ] Table includes both vCenter resources and guest-discovered workloads when workload data is available.
- [ ] Empty state message appears when no resources match the current filter/search.
