# Implementation Plan: Cloud Topology Diagram (CTD)

**Branch**: `001-cloud-topology-diagram` | **Date**: 2026-03-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-cloud-topology-diagram/spec.md`

## Summary

Generate an interactive Azure architecture diagram from discovered on-prem VMware infrastructure, organised by Cloud Adoption Framework (CAF) landing zones and scored by Well-Architected Framework (WAF) pillars. The backend builds a topology graph (landing zones → VNets → subnets → resources + edges), the frontend renders it with vis-network, and a side-panel shows WAF radar charts with recommendations. Exports to PNG (canvas-native), JSON, and Mermaid.

## Technical Context

**Language/Version**: Python 3.10+ (backend), vanilla JavaScript ES2020+ (frontend)
**Primary Dependencies**: Flask (backend), vis-network 9.1.6, Chart.js 4.4.1, Bootstrap 5.3.3 (all existing CDN deps — zero new dependencies)
**Storage**: In-memory dict (consistent with existing app pattern) + optional JSON persistence to `data/`
**Testing**: pytest (existing) — unit tests for topology builder, WAF scorer, CAF classifier
**Target Platform**: Web browser (desktop, ≥768 px viewport for diagram usability)
**Project Type**: Web application (single-page Flask dashboard — existing)
**Performance Goals**: Diagram generation <5 s for 500 VMs, WAF panel render <300 ms
**Constraints**: Zero new dependencies (constitution §4), canvas-native PNG export only, all data from existing discovery/enrichment pipeline
**Scale/Scope**: Up to 500 VMs, 100 workloads, 500 dependency edges

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| 1 | Clean Code | ✅ PASS | New module `cloud_topology.py` follows single-responsibility. Helper functions <30 lines each. Full type annotations. |
| 2 | Simple UX | ✅ PASS | One-click "Generate Diagram," progressive disclosure (WAF panel on click), empty state, tooltips. |
| 3 | Responsive Design | ✅ PASS | Diagram canvas fills available width. Side panel collapses on small viewports. |
| 4 | Minimal Dependencies | ✅ PASS | Zero new dependencies. Reuses vis-network (existing), Chart.js (existing), canvas toDataURL (browser API). |
| 5 | Testing | ✅ PASS | Unit tests for topology builder, WAF scorer, CAF classifier. Integration test for API endpoint. Contract tests for API response shape. |
| 6 | Accessibility | ✅ PASS | Diagram nodes have ARIA labels. WAF panel uses semantic HTML. Colour + icon + text for severity. Keyboard-navigable panel. |
| 7 | Performance | ✅ PASS | Backend computation <5 s. Lazy-load diagram on tab activation. Progressive rendering for >500 VMs. |
| 8 | Security | ✅ PASS | No new user input beyond existing discovery data. API key protection (existing). No secrets. |
| 9 | Architecture | ✅ PASS | Separate backend module (`cloud_topology.py`) from endpoint wiring (`app.py`). API-first: JSON endpoint drives the UI. |
| 10 | Documentation | ✅ PASS | API documented in spec. Inline comments for scoring formulas. |
| 11 | CI / CD | ✅ PASS | New tests run in existing pytest suite. No deployment changes. |

**Gate result: PASS — no violations.**

## Project Structure

### Documentation (this feature)

```text
specs/001-cloud-topology-diagram/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api-topology.md  # /api/cloud-topology endpoint contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/digital_twin_migrate/
├── cloud_topology.py          # NEW — topology builder, CAF classifier, WAF scorer, Mermaid exporter
├── web/
│   ├── app.py                 # MODIFIED — add /api/cloud-topology, /api/cloud-topology/waf/<resource>
│   └── templates/
│       └── index.html         # MODIFIED — add Cloud Topology tab, diagram canvas, WAF panel, export buttons

tests/
├── test_cloud_topology.py     # NEW — unit tests for topology builder, CAF classifier, WAF scorer
```

**Structure Decision**: Single new backend module `cloud_topology.py` following the same pattern as `vulnerability_sla.py` — a standalone module with pure functions, imported and wired to Flask endpoints in `app.py`. Frontend additions go into the existing `index.html` SPA.
