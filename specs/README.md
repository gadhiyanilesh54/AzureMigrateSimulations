# Spec Index — Azure Migrate Simulations

This directory contains SpecKit-compatible feature specifications for every implemented feature. Each spec documents the feature's purpose, user stories, functional/non-functional requirements, API surface, implementation details, and acceptance criteria.

## How to Use

1. **Before implementing a new feature:** create a new spec file following the numbering convention (`NNN-feature-slug.spec.md`).
2. **Before modifying an existing feature:** read its spec to understand the contract and acceptance criteria.
3. **After implementing:** update the spec's acceptance criteria checkboxes and adjust requirements if scope changed.
4. **Use with SpecKit agents:** reference specs from `speckit.analyze`, `speckit.plan`, `speckit.implement`, and `speckit.tasks` prompts.

## Spec Template

New specs should follow this structure:

```markdown
---
feature: <feature-slug>
status: proposed | in-progress | implemented
module: <primary source file(s)>
---

# <Feature Name>

## Summary
## User Stories
## Functional Requirements
## Non-Functional Requirements
## API Endpoints
## Implementation Details
## Dependencies
## Test Coverage
## Acceptance Criteria
```

---

## Feature Specs

### Foundation

| # | Spec | Feature | Module(s) | Status |
|---|------|---------|-----------|--------|
| 000 | [Core Data Models](000-core-data-models.spec.md) | Infrastructure & workload models, configuration | `models.py`, `models_workload.py`, `config.py` | Implemented |

### Features

| # | Spec | Feature | Module(s) | Status |
|---|------|---------|-----------|--------|
| 001 | [Connect & Data Ingestion](001-connect-data-ingestion.spec.md) | vCenter connection, JSON upload | `vcenter_discovery.py`, `web/app.py` | Implemented |
| 002 | [Dashboard](002-dashboard.spec.md) | Fleet overview cards & charts | `web/app.py`, `web/templates/index.html` | Implemented |
| 003 | [Inventory](003-inventory.spec.md) | Unified searchable resource table | `web/app.py`, `web/templates/index.html` | Implemented |
| 004 | [Topology Views](004-topology-views.spec.md) | Infrastructure & dependency graphs | `web/app.py`, `web/templates/index.html` | Implemented |
| 005 | [VM Assessment](005-vm-assessment.spec.md) | Azure SKU recommendations per VM | `azure_mapping.py`, `web/app.py` | Implemented |
| 006 | [Workload Assessment](006-workload-assessment.spec.md) | Guest discovery & PaaS mapping | `guest_discovery.py`, `workload_mapping.py` | Implemented |
| 007 | [VM Simulation & What-If](007-vm-simulation-whatif.spec.md) | Per-VM & fleet cost simulation | `azure_pricing.py`, `web/app.py` | Implemented |
| 008 | [Workload Simulation & What-If](008-workload-simulation-whatif.spec.md) | Workload PaaS cost simulation | `workload_mapping.py`, `azure_pricing.py` | Implemented |
| 009 | [Business Case](009-business-case.spec.md) | On-prem TCO vs Azure comparison | `web/app.py` | Implemented |
| 010 | [Enrichment Data Loop](010-enrichment-data-loop.spec.md) | APM telemetry ingestion & confidence boost | `enrichment.py`, `web/app.py` | Implemented |
| 011 | [Performance Monitoring](011-performance-monitoring.spec.md) | Background perf data collector | `perf_aggregator.py`, `web/app.py` | Implemented |
| 012 | [Vulnerability & SLA](012-vulnerability-sla.spec.md) | OS/software lifecycle & licensing | `web/app.py` | Implemented |
| 013 | [CSV Export](013-csv-export.spec.md) | Assessment CSV download | `web/app.py` | Implemented |

### System

| # | Spec | Feature | Module(s) | Status |
|---|------|---------|-----------|--------|
| 014 | [CLI Interface](014-cli-interface.spec.md) | Command-line discovery workflow | `main.py`, `visualization.py` | Implemented |
| 015 | [Web Application](015-web-application.spec.md) | Flask dashboard, 57 REST endpoints | `web/app.py`, `web/templates/index.html` | Implemented |

---

## Coverage Summary

| Metric | Count |
|--------|-------|
| Total spec files | 16 |
| Features specified | 16 |
| API endpoints covered | 57 |
| Source modules covered | 15 |
| Status: Implemented | 16 |
| Status: Proposed | 0 |

## Adding a New Feature

1. Copy the template above into a new file: `specs/NNN-your-feature.spec.md`
2. Set `status: proposed` in the frontmatter
3. Fill in Summary, User Stories, and Functional Requirements
4. Run `@speckit.clarify` to identify gaps
5. Run `@speckit.plan` to generate implementation tasks
6. Run `@speckit.implement` to start building
7. Update status to `in-progress`, then `implemented`
8. Add the spec to this index table
