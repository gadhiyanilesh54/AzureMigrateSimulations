# Tasks: Migration Risk Heatmap

**Input**: Design documents from `/specs/002-migration-risk-heatmap/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Project structure and shared data model additions

- [X] T001 Add RiskFactorName and RiskBand enums to src/azure_migrate_simulations/models.py
- [X] T002 Add MitigationAction dataclass to src/azure_migrate_simulations/models.py
- [X] T003 Add RiskFactor dataclass to src/azure_migrate_simulations/models.py
- [X] T004 Add RiskScore dataclass to src/azure_migrate_simulations/models.py
- [X] T005 Add RiskHeatmap dataclass to src/azure_migrate_simulations/models.py

---

## Phase 2: Foundational (Core Scoring Engine)

**Purpose**: The risk_heatmap.py module — the single scoring engine consumed by ALL user stories (CLI, API, MCP, Web). MUST be complete before any interface work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create src/azure_migrate_simulations/risk_heatmap.py with module docstring, imports, and DEFAULT_WEIGHTS constant dict
- [X] T007 Implement _get_band(score: int) -> str helper that maps score to color band (green 0–30, yellow 31–60, red 61–100) in src/azure_migrate_simulations/risk_heatmap.py
- [X] T008 Implement _score_dependency_count(vm, workload_data, enrichment_data) -> RiskFactor in src/azure_migrate_simulations/risk_heatmap.py using WorkloadDependency edges and EstablishedConnection lists per research R-001
- [X] T009 Implement _score_os_eol(vm) -> RiskFactor in src/azure_migrate_simulations/risk_heatmap.py reusing vulnerability_sla._match_os() per research R-002
- [X] T010 Implement _score_workload_complexity(vm, workload_data) -> RiskFactor in src/azure_migrate_simulations/risk_heatmap.py with tiered scoring (database=high, orchestrator=medium, webapp=low) per research R-003
- [X] T011 Implement _score_performance_sensitivity(vm, fleet_iops_p75) -> RiskFactor in src/azure_migrate_simulations/risk_heatmap.py using disk_iops_p95 with realtime fallback per research R-004
- [X] T012 Implement _score_compliance_scope(vm, enrichment_data) -> RiskFactor in src/azure_migrate_simulations/risk_heatmap.py scanning VM tags and enrichment tags for compliance patterns per research R-005
- [X] T013 Implement _score_data_volume(vm, fleet_max_disk_gb) -> RiskFactor in src/azure_migrate_simulations/risk_heatmap.py with fleet-relative linear scoring per research R-006
- [X] T014 Implement _suggest_mitigations(factors: list[RiskFactor]) -> list[MitigationAction] in src/azure_migrate_simulations/risk_heatmap.py with hardcoded lookup table per research R-011
- [X] T015 Implement compute_risk_score(vm, workload_data, enrichment_data, fleet_iops_p75, fleet_max_disk_gb, weights) -> RiskScore in src/azure_migrate_simulations/risk_heatmap.py combining all six factor scorers and composite formula per research R-007
- [X] T016 Implement compute_heatmap(vms, workload_data, enrichment_data, weights) -> RiskHeatmap in src/azure_migrate_simulations/risk_heatmap.py that computes fleet statistics (IOPS P75, max disk), scores all VMs, builds band distribution, and extracts top-10

**Checkpoint**: Core scoring engine complete — all interfaces can now be built in parallel

---

## Phase 3: User Story 1 — View Fleet-Wide Risk Heatmap (Priority: P1) 🎯 MVP

**Goal**: Display a color-coded heatmap grid in the web UI under the Decide phase tab, showing every VM with per-factor scores and composite score

**Independent Test**: Load discovery data, navigate to Decide > Risk Heatmap tab, verify the grid renders with colored cells and sorting works

### Implementation for User Story 1

- [X] T017 [US1] Add GET /api/risk/heatmap route to src/azure_migrate_simulations/web/app.py that calls compute_heatmap() with loaded discovery/workload/enrichment data and returns JSON per contracts/api-risk-heatmap.md, supporting query params sort_by, sort_order, band, top
- [X] T018 [US1] Add "Risk Heatmap" tab markup to the Decide phase section in src/azure_migrate_simulations/web/templates/index.html with a placeholder div for the heatmap grid
- [X] T019 [US1] Add JavaScript in src/azure_migrate_simulations/web/static/js/risk_heatmap.js that fetches /api/risk/heatmap, renders an HTML table with color-coded cells (green/yellow/red backgrounds), composite score column, and column-header click sorting

**Checkpoint**: User Story 1 complete — fleet-wide heatmap visible in browser with colored grid and sortable columns

---

## Phase 4: User Story 2 — Drill Into Individual VM Risk Score (Priority: P2)

**Goal**: Allow users to view a detailed per-factor breakdown with mitigation suggestions for a single VM via UI click or API call

**Independent Test**: Click a VM row in the heatmap grid, verify the expanded panel shows all six factors with raw values, weighted scores, bands, and mitigation suggestions for high-risk factors

### Implementation for User Story 2

- [X] T020 [US2] Add GET /api/risk/score/<vm_name> route to src/azure_migrate_simulations/web/app.py that calls compute_risk_score() for the named VM and returns JSON per contracts/api-risk-score.md, returning 404 for unknown VMs
- [X] T021 [US2] Add click-to-expand behavior in src/azure_migrate_simulations/web/static/js/risk_heatmap.js that fetches /api/risk/score/<vm_name> on VM row click and renders a detail panel showing per-factor breakdown table and mitigation suggestions list

**Checkpoint**: User Story 2 complete — VM drill-down works from heatmap grid and via direct API call

---

## Phase 5: User Story 3 — Top-10 Riskiest VMs Report (Priority: P2)

**Goal**: Highlight the top-10 riskiest VMs with composite scores, dominant risk factors, and mitigation suggestions

**Independent Test**: View the heatmap page or call the API with top=10, verify a ranked list of the 10 highest-scoring VMs with dominant factor and mitigation per entry

### Implementation for User Story 3

- [X] T022 [US3] Add a "Top Riskiest VMs" summary panel in src/azure_migrate_simulations/web/static/js/risk_heatmap.js that renders the top_risky array from the heatmap response as a ranked card list above the main grid, showing VM name, composite score badge, dominant factor, and first mitigation suggestion

**Checkpoint**: User Story 3 complete — top-10 riskiest VMs are highlighted in the web UI and available via API top parameter

---

## Phase 6: User Story 4 — CLI Risk Commands (Priority: P3)

**Goal**: Expose risk heatmap and per-VM score as CLI subcommands for automation

**Independent Test**: Run `dt-migrate risk heatmap --format json` and `dt-migrate risk score <vm_name> --format json` against sample data, verify valid JSON output and correct exit codes

### Implementation for User Story 4

- [X] T023 [P] [US4] Add argparse subparser group "risk" with subcommands "heatmap" and "score" to src/azure_migrate_simulations/main.py per contracts/cli-risk.md, with --top, --format, --band flags for heatmap and positional vm_name + --format for score
- [X] T024 [P] [US4] Implement _cmd_risk_heatmap(args) handler in src/azure_migrate_simulations/main.py that loads discovery/workload/enrichment data from data/*.json, calls compute_heatmap(), and outputs as JSON (--format json) or Rich table (--format table) with colored score cells
- [X] T025 [US4] Implement _cmd_risk_score(args) handler in src/azure_migrate_simulations/main.py that loads data, calls compute_risk_score() for the specified VM, outputs as JSON or Rich panel, and returns exit code 1 for unknown VMs

**Checkpoint**: User Story 4 complete — CLI commands produce correct JSON/table output with proper exit codes

---

## Phase 7: User Story 5 — REST API and MCP Server Exposure (Priority: P3)

**Goal**: Expose risk tools via MCP Server for AI agent integration

**Independent Test**: Start MCP server, invoke get_risk_heatmap and get_risk_score tools, verify response matches REST API schema

### Implementation for User Story 5

- [X] T026 [P] [US5] Add get_risk_heatmap MCP tool to src/azure_migrate_simulations/mcp_server.py per contracts/mcp-risk-tools.md with top, band, sort_by parameters, loading data and calling compute_heatmap()
- [X] T027 [P] [US5] Add get_risk_score MCP tool to src/azure_migrate_simulations/mcp_server.py per contracts/mcp-risk-tools.md with vm_name parameter, returning error dict for unknown VMs

**Checkpoint**: User Story 5 complete — AI agents can query risk heatmap and per-VM scores via MCP

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, and edge case handling

- [X] T028 [P] Verify edge case: empty fleet returns empty matrix with message in both API and CLI
- [X] T029 [P] Verify edge case: VM with no workload/dependency/perf data gets all-green default scores
- [X] T030 [P] Verify determinism: same discovery data produces identical scores across repeated runs
- [X] T031 Run quickstart.md validation steps (CLI, API, Web UI, MCP) end-to-end against data/vcenter_discovery.json

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (models) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (scoring engine)
- **User Story 2 (Phase 4)**: Depends on Phase 2 (scoring engine); integrates with US1 web tab but independently testable via API
- **User Story 3 (Phase 5)**: Depends on Phase 2 (scoring engine); integrates with US1 web tab
- **User Story 4 (Phase 6)**: Depends on Phase 2 (scoring engine) only — no web dependency
- **User Story 5 (Phase 7)**: Depends on Phase 2 (scoring engine) only — no web dependency
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependencies on other stories
- **US2 (P2)**: After Phase 2 — integrates with US1 web tab (T018) but API route (T020) is independently testable
- **US3 (P2)**: After Phase 2 — integrates with US1 web tab; API data already available from heatmap endpoint
- **US4 (P3)**: After Phase 2 — fully independent from web stories; can parallel with US1/US2/US3
- **US5 (P3)**: After Phase 2 — fully independent from web and CLI; can parallel with all others

### Within Each User Story

- Models before scoring functions
- Scoring functions before interface handlers
- API routes before web UI JS (US1, US2)
- Core implementation before integration

### Parallel Opportunities

Once Phase 2 (Foundational) is complete, all user stories can proceed in parallel:

```
Phase 2 complete
├── US1 (Web heatmap tab)      ─┐
├── US2 (VM detail drill-down) ─┤── These three share the web tab
├── US3 (Top-10 panel)         ─┘
├── US4 (CLI commands)         ── Independent, different files
└── US5 (MCP tools)            ── Independent, different files
```

Within Phase 2:
- T008–T013 (individual factor scorers) can all run in parallel — each is a self-contained function
- T014 (mitigations) can parallel with T008–T013
- T015 (compute_risk_score) depends on T007–T014
- T016 (compute_heatmap) depends on T015

Within Phase 6 (CLI):
- T023 (argparse setup) and T024 (heatmap handler) can parallel
- T025 (score handler) can parallel with T024

Within Phase 7 (MCP):
- T026 and T027 can parallel — different tool registrations

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005) — add dataclasses to models.py
2. Complete Phase 2: Foundational (T006–T016) — build scoring engine
3. Complete Phase 3: User Story 1 (T017–T019) — web heatmap tab
4. **STOP and VALIDATE**: Open browser, navigate to Decide > Risk Heatmap, verify colored grid
5. Deploy/demo if ready — heatmap is usable with just US1

### Incremental Delivery

1. Setup + Foundational → Scoring engine ready
2. Add US1 → Web heatmap visible → Deploy/Demo (MVP!)
3. Add US2 → VM drill-down works → Deploy/Demo
4. Add US3 → Top-10 panel visible → Deploy/Demo
5. Add US4 → CLI commands available → Deploy/Demo
6. Add US5 → MCP tools registered → Deploy/Demo
7. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- All data model additions (Phase 1) go into existing models.py
- All scoring logic (Phase 2) goes into a single new file risk_heatmap.py
- Web routes (US1, US2) modify existing web/app.py
- CLI commands (US4) modify existing main.py
- MCP tools (US5) modify existing mcp_server.py
- The JS file (risk_heatmap.js) is new and serves US1, US2, US3
- Commit after each completed phase or user story
