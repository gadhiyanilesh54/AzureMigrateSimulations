---
feature: csv-export
status: implemented
module: web/app.py
---

# CSV Export

## Summary

Download VM and workload assessment data as CSV files for offline analysis, reporting, or import into Excel / Power BI.

## User Stories

- As a consultant, I want to download VM assessments as CSV so that I can share them with stakeholders who don't have access to the dashboard.
- As an analyst, I want workload assessment data in CSV so that I can build custom reports in Power BI.

## Functional Requirements

- **FR-1:** **VM Assessment CSV** — columns: VM Name, Recommended SKU, VM Family, Disk Type, Disk Size (GB), Monthly Cost, Readiness, Migration Approach, Confidence Score.
- **FR-2:** **Workload Assessment CSV** — columns: VM Name, Workload Name, Type, Engine, Version, Azure Service, Migration Approach, Complexity, Monthly Cost, Confidence.
- **FR-3:** Export type selected via `type` query parameter (`vms` or `workloads`).
- **FR-4:** File is returned as a downloadable attachment with `Content-Type: text/csv`.
- **FR-5:** CSV is generated in-memory using Python `csv.DictWriter`.

## Non-Functional Requirements

- **NFR-1:** Export must handle 500+ rows without timeout.
- **NFR-2:** CSV must use UTF-8 encoding with BOM for Excel compatibility.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/export/csv?type=vms` | Download VM assessment CSV |
| `GET` | `/api/export/csv?type=workloads` | Download workload assessment CSV |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — `/api/export/csv` handler

### Key Classes / Functions

- `csv.DictWriter` — standard library CSV writer
- `flask.Response` with `Content-Disposition: attachment` header

## Dependencies

- Python standard library `csv` — no external dependencies.

## Test Coverage

- No dedicated CSV export tests yet.

## Acceptance Criteria

- [ ] GET `/api/export/csv?type=vms` returns a valid CSV with all VM assessment columns.
- [ ] GET `/api/export/csv?type=workloads` returns a valid CSV with all workload assessment columns.
- [ ] CSV opens correctly in Excel without encoding issues.
- [ ] Invalid `type` parameter returns 400 with descriptive error.
- [ ] Row count matches the number of VMs/workloads in the current dataset.
