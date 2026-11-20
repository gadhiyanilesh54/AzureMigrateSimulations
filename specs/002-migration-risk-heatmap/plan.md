# Implementation Plan: Migration Risk Heatmap

**Branch**: `002-migration-risk-heatmap` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-migration-risk-heatmap/spec.md`

## Summary

Compute a composite risk score (0–100) for each discovered VM by combining six weighted factors: dependency count, OS EOL status, workload complexity, performance sensitivity, compliance scope, and data volume. Produce a fleet-wide heatmap as a JSON matrix (VM × risk-factor) with color bands (green/yellow/red). Identify top-10 riskiest VMs with mitigation suggestions. Expose via a new `risk_heatmap.py` module consumed by CLI (`dt-migrate risk heatmap`, `dt-migrate risk score <vm_name>`), REST API (`/api/risk/heatmap`, `/api/risk/score/<vm_name>`), MCP Server tools, and a web UI tab under the Decide phase.

## Technical Context

**Language/Version**: Python ≥ 3.10 (type hints, dataclasses, match statements)
**Primary Dependencies**: Flask ≥ 3.0 (web), argparse + Rich (CLI), mcp[server] (MCP), no new PyPI deps required
**Storage**: JSON persistence (`data/*.json`) — no database; risk scores computed on-demand from existing discovery data
**Testing**: pytest (unit tests in `tests/`), Playwright (e2e in `e2e/`)
**Target Platform**: Cross-platform (Windows/Linux/macOS), offline-capable, air-gapped deployable
**Project Type**: CLI + Web service + MCP server (all three interfaces)
**Performance Goals**: Heatmap computation for 500 VMs in <5 seconds
**Constraints**: Offline-first (no Azure calls), single-file module per Constitution VII, deterministic scoring (same input → same output)
**Scale/Scope**: Up to 500 VMs per fleet, 6 risk factors, 1 new module + route/CLI/MCP additions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Offline-First & Data Sovereignty | ✅ PASS | Risk scoring uses only local discovery data (`data/*.json`). No Azure API calls. No telemetry egress. |
| II. Src-Layout Python Package | ✅ PASS | New module `risk_heatmap.py` placed in `src/azure_migrate_simulations/`. Single file. Fully-qualified imports. |
| III. Dataclass Models as Contracts | ✅ PASS | `RiskScore`, `RiskFactor`, `RiskHeatmap`, `MitigationAction` will be added to `models.py` as dataclasses with `dataclasses.asdict()` serialisation. |
| IV. Dual Interface — CLI + Web | ✅ PASS | Exposed via CLI (`dt-migrate risk heatmap/score`), REST API (`/api/risk/*`), and MCP tools. Not web-only. |
| V. Test Discipline | ✅ PASS | Unit tests in `tests/test_risk_heatmap.py` using fixture data. No external service dependencies. |
| VI. Spec-Driven Features | ✅ PASS | Spec exists at `specs/002-migration-risk-heatmap/spec.md`. |
| VII. Simplicity & YAGNI | ✅ PASS | Single-file module. No new dependencies. No ORM. Hardcoded mitigation suggestion lookup. |

**Pre-design gate result: ALL PASS** — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-migration-risk-heatmap/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (REST API contracts)
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/azure_migrate_simulations/
├── models.py            # MODIFY: Add RiskScore, RiskFactor, RiskHeatmap, MitigationAction dataclasses
├── risk_heatmap.py      # NEW: Core scoring engine (compute_risk_score, compute_heatmap, get_top_risky_vms, suggest_mitigations)
├── main.py              # MODIFY: Add "risk" subcommand group with "heatmap" and "score" sub-subcommands
├── mcp_server.py        # MODIFY: Add get_risk_heatmap and get_risk_score MCP tools
└── web/
    └── app.py           # MODIFY: Add /api/risk/heatmap, /api/risk/score/<vm_name> routes and Risk Heatmap tab

tests/
└── test_risk_heatmap.py # NEW: Unit tests for scoring engine, edge cases, determinism
```

**Structure Decision**: Single-project src-layout (existing pattern). One new module (`risk_heatmap.py`) plus modifications to existing files. Follows Constitution II (single-file module) and VII (simplicity).

## Complexity Tracking

> No constitution violations. Table not needed.
