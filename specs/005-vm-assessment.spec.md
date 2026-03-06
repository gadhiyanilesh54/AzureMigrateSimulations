---
feature: vm-assessment
status: implemented
module: azure_mapping.py, web/app.py
---

# VM Assessment

## Summary

Sortable, filterable table presenting per-VM Azure migration recommendations. The Azure SKU mapping engine evaluates each VM's CPU, memory, disk, and OS against a catalog of 70+ Azure VM SKUs to recommend the best-fit size, disk type, and pricing.

## User Stories

- As a migration planner, I want each VM to have an Azure SKU recommendation so that I know what to provision.
- As an architect, I want to filter VMs by readiness level so that I can prioritize migration-ready workloads.
- As a cost analyst, I want to see estimated monthly Azure cost per VM so that I can build a migration budget.
- As an engineer, I want to see migration issues per VM so that I can address blockers.

## Functional Requirements

- **FR-1:** Display a table with columns: VM Name, Power State, OS, vCPU, RAM (GB), Disk (GB), Azure SKU, Disk Type, Monthly Cost ($), Readiness, Confidence, Issues.
- **FR-2:** Filter by readiness level (Ready, Ready with Conditions, Not Ready), OS type, and power state.
- **FR-3:** Full-text search by VM name.
- **FR-4:** Sort by any column.
- **FR-5:** Readiness is derived from compatibility checks: unsupported OS, excessive disk size, missing VMware tools, etc.
- **FR-6:** Confidence scores range 0–98; base 50–70 from vCenter data, up to +30 boost from enrichment.
- **FR-7:** Clicking a VM row opens the VM What-If modal.
- **FR-8:** SKU catalog covers B, D, E, F, M, L, NC families with approximate East US PAYG prices.

## Non-Functional Requirements

- **NFR-1:** Recommendation generation for 500 VMs must complete within 2 seconds.
- **NFR-2:** SKU catalog must be extensible without code changes (data-driven).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/vms` | List VMs with recommendations and confidence scores |
| `GET` | `/api/recommendations` | Azure VM SKU recommendations |
| `GET` | `/api/sku_catalog` | Full Azure VM SKU catalog |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/azure_mapping.py](../src/digital_twin_migrate/azure_mapping.py) — SKU catalog (`VM_CATALOG`), recommendation engine
- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — REST endpoint handlers
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — table rendering, filters, row click handler

### Key Classes / Functions

- `AzureVMSku` — dataclass (name, family, vcpus, memory_gb, max_disks, max_iops, price_monthly)
- `VM_CATALOG` — list of ~70+ `AzureVMSku` instances
- `generate_recommendations(env, target_region)` — maps each `DiscoveredVM` to best-fit SKU
- Recommendation result includes: SKU, disk type, monthly cost, readiness, confidence, issues list

### Data Models

- `DiscoveredVM` — vCPU, memory, disks, OS, power state, perf metrics
- `AzureVMSku` — Azure VM size definition
- Recommendation response: per-VM object with SKU, cost, readiness, confidence, issues

## Dependencies

- None beyond standard library for the mapping engine itself.

## Test Coverage

- `tests/test_azure_mapping.py` — validates SKU selection logic, readiness classification, confidence scoring
- `tests/test_models.py` — validates `DiscoveredVM` model construction

## Acceptance Criteria

- [ ] Every powered-on VM receives a SKU recommendation.
- [ ] SKU recommendation satisfies VM's CPU, memory, and disk requirements.
- [ ] Readiness is "Not Ready" when VM has unsupported OS or exceeds max disk count.
- [ ] Confidence score increases after enrichment data is applied.
- [ ] GET `/api/vms` response includes recommendation, confidence, and issues for each VM.
- [ ] GET `/api/sku_catalog` returns the full catalog with pricing.
- [ ] Table sorts correctly by numeric columns (cost, vCPU, RAM).
