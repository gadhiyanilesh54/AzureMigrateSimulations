# Tasks: Cloud Topology Diagram (CTD)

**Input**: Design documents from `/specs/001-cloud-topology-diagram/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-topology.md

**Tests**: Included — unit tests for backend logic (topology builder, CAF classifier, WAF scorer).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US5)
- All paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Project initialization and shared module structure

- [X] T001 Create src/digital_twin_migrate/cloud_topology.py with module docstring, imports (`from __future__ import annotations`, `re`, `math`, `datetime`, `typing`), and section header comment blocks matching the vulnerability_sla.py pattern
- [X] T002 [P] Create tests/test_cloud_topology.py with pytest imports, shared fixtures for sample VM data, sample recommendation data, and sample workload data (reuse patterns from tests/conftest.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures and helpers that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement `CloudResource` builder function `_build_cloud_resource(vm, recommendation, workload)` in src/digital_twin_migrate/cloud_topology.py — maps a VM dict + recommendation dict + optional workload dict to a CloudResource dict with fields: id, source_vm_name, azure_service, azure_sku, monthly_cost, migration_readiness, resource_type
- [X] T004 [P] Implement `_classify_environment(folder_name)` in src/digital_twin_migrate/cloud_topology.py — regex-based heuristic returning `"devtest"` if folder matches `dev|test|staging|qa|sandbox|lab` (case-insensitive), `"production"` otherwise
- [X] T005 [P] Implement optional components cost table `_OPTIONAL_COMPONENTS` in src/digital_twin_migrate/cloud_topology.py — static dict with keys `azure_firewall`, `bastion`, `load_balancer`, `vpn_gateway`, each having `name`, `monthly_cost_base`, `landing_zone_type` (connectivity or application)
- [X] T006 [P] Implement `_get_region_multiplier(region)` in src/digital_twin_migrate/cloud_topology.py — reuse the same region cost multiplier logic as the existing simulation endpoints (import or duplicate the small lookup dict from web/app.py)
- [X] T007 [P] Write unit tests for `_classify_environment()` in tests/test_cloud_topology.py — test dev/test/staging/qa/sandbox/lab matches, production default, case insensitivity, empty string, None
- [X] T008 [P] Write unit tests for `_build_cloud_resource()` in tests/test_cloud_topology.py — test VM-only mapping, VM+workload mapping (PaaS), "Not Ready" VM handling

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 — Generate Azure Architecture Diagram (Priority: P1) 🎯 MVP

**Goal**: Generate a complete cloud topology JSON from discovery data and render an interactive diagram

**Independent Test**: Load sample data → click "Generate Diagram" → interactive diagram with nodes, edges, tooltips

### Backend (src/digital_twin_migrate/cloud_topology.py)

- [X] T009 [US1] Implement `_build_landing_zones(vms, recommendations, workload_data)` — iterate VMs, classify each into production/devtest/attention, group into LandingZone dicts, always create Connectivity, Identity (placeholder, no VMs), and Management platform zones
- [X] T010 [US1] Implement `_build_vnets_and_subnets(landing_zone, resources, workload_data)` — within each application LZ, create one VNet with subnets per workload type (`webapp`, `database`, `container`, `orchestrator`, `general_compute`); for Connectivity LZ create hub VNet with GatewaySubnet and AzureFirewallSubnet
- [X] T011 [US1] Implement `_build_topology_edges(workload_data, resource_id_map)` — map discovered TCP connections from workload dependency data to TopologyEdge dicts, marking `cross_zone=True` when source and target are in different landing zones
- [X] T012 [US1] Implement `_build_containers(landing_zones)` — flatten the LZ→VNet→Subnet hierarchy into a list of container dicts with id, label, type, parent, color, children fields matching the API contract
- [X] T013 [US1] Implement `_build_vis_nodes(resources, container_map)` — convert CloudResource dicts to vis-network node dicts with id, label, group, title (tooltip), container reference
- [X] T014 [US1] Implement `_build_cost_summary(landing_zones, optional_components, region)` — aggregate costs per landing zone and add optional component costs adjusted by region multiplier
- [X] T015 [US1] Implement `generate_cloud_topology(vms, recommendations, workload_data, region, optional_flags)` — main public function orchestrating T009–T014, returning the complete topology dict matching the `/api/cloud-topology` contract
- [X] T016 [US1] Write unit tests for `generate_cloud_topology()` in tests/test_cloud_topology.py — test with sample 202 VMs: verify total node count, landing zone count (≥3), container hierarchy depth, cost summary totals

### API Endpoint (src/digital_twin_migrate/web/app.py)

- [X] T017 [US1] Add `from digital_twin_migrate.cloud_topology import generate_cloud_topology` import to src/digital_twin_migrate/web/app.py
- [X] T018 [US1] Implement `GET /api/cloud-topology` endpoint in src/digital_twin_migrate/web/app.py — parse query params (region, firewall, bastion, load_balancer, vpn_gateway), call `generate_cloud_topology()`, return JSON; 404 if no discovery data. **Cache the result in a global `_ctd_cache` dict** (same pattern as `_data` in app.py) so that `/api/cloud-topology/waf/<resource_id>` can look up resources without regenerating

### Frontend — Tab & Diagram Canvas (src/digital_twin_migrate/web/templates/index.html)

- [X] T019 [US1] Add "Cloud Topology" main tab button in the top navigation bar in src/digital_twin_migrate/web/templates/index.html — after the Enrichment tab, with icon `bi-diagram-3`
- [X] T020 [US1] Add Cloud Topology tab pane in src/digital_twin_migrate/web/templates/index.html — containing: "Generate Diagram" button, cost summary card row (empty initially), diagram canvas div (`id="ctd-canvas"`), empty state message div
- [X] T021 [US1] Implement `loadCloudTopology()` JS function in src/digital_twin_migrate/web/templates/index.html — fetch `/api/cloud-topology`, store response in `_ctdData`, call `renderCloudTopology()`
- [X] T022 [US1] Implement `renderCloudTopology(data)` JS function — initialise vis-network DataSet with nodes/edges, configure hierarchical layout (direction: UD, level property per node), add `beforeDrawing` callback to draw container bounding boxes, configure physics (hierarchicalRepulsion), call `ctdNetwork.fit()`
- [X] T023 [US1] Implement `_drawContainers(ctx, containers, nodePositions)` JS helper — called by `beforeDrawing`, iterates containers, computes bounding box from child node positions (with 30px padding), draws rounded rect with label, fills with semi-transparent colour per type (landing_zone, vnet, subnet)
- [X] T024 [US1] Implement tooltip rendering — vis-network `title` property on nodes (already set from backend), configure `interaction: { tooltipDelay: 100, hover: true }`
- [X] T025 [US1] Implement empty state — when `_ctdData` is null, show a message: "No discovery data available. Connect to vCenter or upload a report to generate a Cloud Topology Diagram."
- [X] T026 [US1] Implement cost summary card row in src/digital_twin_migrate/web/templates/index.html — display cards for each landing zone cost + total cost, populated from `data.cost_summary`
- [X] T026a [US1] Define vis-network group options for resource types in `renderCloudTopology()` in src/digital_twin_migrate/web/templates/index.html — configure `groups` object with colour, shape, and icon per `resource_type` following the Resource Type Visual Mapping table in data-model.md (vm=blue/dot, database=green/diamond, webapp=orange/dot, container=purple/square, orchestrator=teal/triangle, networking=grey/dot, security=red/star, monitoring=yellow/dot)

**Checkpoint**: User Story 1 complete — diagram generates and renders interactively with nodes, edges, containers, tooltips, and cost summary

---

## Phase 4: User Story 2 — CAF Landing Zone Alignment (Priority: P2)

**Goal**: Resources visually grouped into CAF-aligned landing zones with distinct styling

**Independent Test**: Generate diagram → verify Connectivity, Management, Production, Dev/Test zones visible with colour-coded bounding boxes and correct VM placement

### Backend

- [X] T027 [US2] Enhance `_build_landing_zones()` in src/digital_twin_migrate/cloud_topology.py — assign distinct colour palette per landing zone type: Connectivity=#0078d4, Management=#8b5cf6, Production=#10b981, Dev/Test=#f59e0b, Attention=#ef4444
- [X] T028 [US2] Implement cross-zone edge styling in `_build_topology_edges()` in src/digital_twin_migrate/cloud_topology.py — set `dashes: true` and route label "via Hub VNet" for edges where `cross_zone=True`
- [X] T029 [P] [US2] Write unit tests for `_build_landing_zones()` in tests/test_cloud_topology.py — test that Connectivity, Identity, and Management zones are always present; "Not Ready" VM → attention zone; folder "dev-servers" places VM in devtest zone; verify resource group creation within zones

### Frontend

- [X] T030 [US2] Add a diagram legend panel in src/digital_twin_migrate/web/templates/index.html — small floating legend showing colour swatches for each landing zone type with labels (Connectivity, Management, Production, Dev/Test, Requires Attention)
- [X] T031 [US2] Distinguish container border styles — landing zones get 3px solid border, VNets get 2px solid, subnets get 1px dashed in `_drawContainers()` in src/digital_twin_migrate/web/templates/index.html

**Checkpoint**: User Story 2 complete — diagram shows clearly labelled CAF landing zones with distinct colours

---

## Phase 5: User Story 3 — WAF Pillar Scoring & Recommendations (Priority: P3)

**Goal**: Per-resource WAF scores (5 pillars) with a detail panel on click showing radar chart and recommendations

**Independent Test**: Generate diagram → click any VM node → side panel shows radar chart with 5 pillars and recommendation list

### Backend — WAF Scorer (src/digital_twin_migrate/cloud_topology.py)

- [X] T032 [US3] Implement `_score_reliability(vm, recommendation)` in src/digital_twin_migrate/cloud_topology.py — base score 35 (no HA discoverable), +10 if perf data present, +10 if powered on, +5 for each additional VM in same workload group (max +15)
- [X] T033 [P] [US3] Implement `_score_security(vm, recommendation, vuln_data)` in src/digital_twin_migrate/cloud_topology.py — import `_match_os` from vulnerability_sla, score: EOL OS=20, near-EOL=40, supported=65, +15 if enrichment data present, +10 if Windows (AHUB/Defender eligible), cap at 100
- [X] T034 [P] [US3] Implement `_score_cost_optimisation(vm, recommendation, whatif_overrides)` in src/digital_twin_migrate/cloud_topology.py — base from recommendation confidence (confidence/100*60), +15 if AHUB eligible (Windows), +15 if what-if override saved, +10 if workload mapped to PaaS
- [X] T035 [P] [US3] Implement `_score_operational_excellence(vm, enrichment_data, perf_data)` in src/digital_twin_migrate/cloud_topology.py — return None if no enrichment AND no perf data; otherwise: +30 if enrichment present, +20 if perf data present, +15 if VMware tools running, +15 for good tool version
- [X] T036 [P] [US3] Implement `_score_performance_efficiency(vm, perf_data)` in src/digital_twin_migrate/cloud_topology.py — return None if no perf data; with perf: score based on headroom: P95 CPU<50%=80, 50-80%=60, >80%=40; similar for memory; average the two
- [X] T037 [US3] Implement `compute_waf_scores(vm, recommendation, vuln_data, enrichment_data, perf_data, whatif_overrides)` in src/digital_twin_migrate/cloud_topology.py — orchestrate T032–T036, return WAFScores dict
- [X] T038 [US3] Wire `compute_waf_scores()` into `_build_cloud_resource()` in src/digital_twin_migrate/cloud_topology.py — call it during resource construction so every node has `waf_scores`
- [X] T039 [US3] Implement `_build_waf_summary(resources)` in src/digital_twin_migrate/cloud_topology.py — aggregate per-pillar averages (excluding None), count insufficient data per pillar
- [X] T040 [P] [US3] Write unit tests for WAF scoring in tests/test_cloud_topology.py — test each pillar scorer independently: EOL OS → low security, no perf data → None for perf efficiency, high confidence → high cost optimisation

### Backend — WAF Detail Endpoint

- [X] T041 [US3] Implement `get_waf_assessment(resource_id, topology_data, vms, recommendations, enrichment, perf, vuln, whatif)` in src/digital_twin_migrate/cloud_topology.py — return WAFAssessment dict with per-pillar details and recommendations for one resource
- [X] T042 [US3] Implement WAF recommendations database `_WAF_RECOMMENDATIONS` in src/digital_twin_migrate/cloud_topology.py — dict keyed by pillar name, each entry a list of recommendation templates with title, description, impact, effort, and a condition function (e.g., reliability recommendations: "Enable Availability Zones", "Configure Azure Backup", "Use Zone-Redundant Storage")
- [X] T043 [US3] Implement `GET /api/cloud-topology/waf/<resource_id>` endpoint in src/digital_twin_migrate/web/app.py — look up resource in cached topology, call `get_waf_assessment()`, return JSON; 404 for unknown resource

### Frontend — WAF Panel (src/digital_twin_migrate/web/templates/index.html)

- [X] T044 [US3] Add WAF side panel HTML in src/digital_twin_migrate/web/templates/index.html — offcanvas panel (right side, 400px) with: resource name header, radar chart canvas (`id="ctd-waf-radar"`), pillar list with scores/badges, recommendations accordion
- [X] T045 [US3] Implement `openWafPanel(resourceId)` JS function — fetch `/api/cloud-topology/waf/{resourceId}`, render radar chart using Chart.js (type: radar, 5 axes), populate pillar badges (green >70, yellow 40-70, red <40, grey for null), populate recommendations accordion
- [X] T046 [US3] Wire node click handler — `ctdNetwork.on('click', function(params) { if (params.nodes.length) openWafPanel(params.nodes[0]); })` in src/digital_twin_migrate/web/templates/index.html
- [X] T047 [US3] Style "Insufficient Data" pillars — grey badge with `bi-question-circle` icon and the `missing_data_prompt` text below the pillar name

**Checkpoint**: User Story 3 complete — every node shows WAF scores, clicking opens detail panel with radar chart and recommendations

---

## Phase 6: User Story 4 — Export & Share Diagram (Priority: P4)

**Goal**: Export diagram as PNG, JSON, and Mermaid

**Independent Test**: Generate diagram → click each export button → valid PNG downloads, valid JSON downloads, valid Mermaid copied to clipboard

### Backend — Mermaid Generator (src/digital_twin_migrate/cloud_topology.py)

- [X] T048 [US4] Implement `generate_mermaid(topology_data)` in src/digital_twin_migrate/cloud_topology.py — build a Mermaid `flowchart TB` string with nested `subgraph` blocks for landing zones → VNets → subnets, leaf nodes for resources, edges for dependencies, `classDef` styling per type
- [X] T049 [US4] Wire Mermaid into `generate_cloud_topology()` in src/digital_twin_migrate/cloud_topology.py — call `generate_mermaid()` and include result as `mermaid` field in response
- [X] T050 [P] [US4] Write unit test for Mermaid export in tests/test_cloud_topology.py — verify output starts with "flowchart TB", contains "subgraph" for each landing zone, contains node IDs, valid Mermaid syntax (no unmatched brackets)

### Frontend — Export Buttons (src/digital_twin_migrate/web/templates/index.html)

- [X] T051 [US4] Add export button toolbar in src/digital_twin_migrate/web/templates/index.html — three buttons: "Export PNG" (`bi-image`), "Export JSON" (`bi-filetype-json`), "Copy Mermaid" (`bi-clipboard`); disabled when no diagram generated
- [X] T052 [US4] Implement `exportTopologyPng()` JS function — call `ctdNetwork.fit({animation:false})`, temporarily ensure canvas dimensions are at least 1920×1080 via `ctdNetwork.setSize('1920px','1080px')`, listen for `afterDrawing`, then `canvas.toDataURL('image/png')`, restore original canvas size, trigger download as `cloud-topology.png`
- [X] T053 [US4] Implement `exportTopologyJson()` JS function — stringify `_ctdData` with indent=2, create Blob, trigger download as `cloud-topology.json`
- [X] T054 [US4] Implement `copyTopologyMermaid()` JS function — copy `_ctdData.mermaid` to clipboard via `navigator.clipboard.writeText()`, show toast "Mermaid diagram copied to clipboard"

**Checkpoint**: User Story 4 complete — all three export formats work

---

## Phase 7: User Story 5 — Interactive Customisation (Priority: P5)

**Goal**: Toggle optional infrastructure components, see cost updates in real time

**Independent Test**: Generate diagram → toggle "Add Azure Firewall" → firewall node appears in Connectivity zone, cost summary increases by ~$912/mo

### Frontend — Toggle Controls (src/digital_twin_migrate/web/templates/index.html)

- [X] T055 [US5] Add optional component toggle switches in src/digital_twin_migrate/web/templates/index.html — row of Bootstrap switch inputs above the diagram for: Azure Firewall, Azure Bastion, Standard Load Balancer, VPN Gateway; each shows the base cost
- [X] T056 [US5] Implement `toggleOptionalComponent(componentId)` JS function in src/digital_twin_migrate/web/templates/index.html — re-fetch `/api/cloud-topology` with updated toggle query params, re-render diagram and cost summary
- [X] T057 [US5] Implement "Reset to Default" button in src/digital_twin_migrate/web/templates/index.html — clears all toggles to false, re-fetches and re-renders the diagram
- [X] T057a [US5] Implement drag-and-drop resource re-assignment in src/digital_twin_migrate/web/templates/index.html — enable vis-network `manipulation: { enabled: false }` with custom `dragEnd` handler; when a node is dropped into a different container bounding box, update its `landing_zone_id` in `_ctdData`, re-draw containers, and recalculate cost summary
- [X] T057b [US5] Implement Azure service override modal in src/digital_twin_migrate/web/templates/index.html — right-click a resource node to open a dropdown of alternative Azure services (from the existing workload mapping alternatives); selecting one updates the resource’s `azure_service`, `azure_sku`, `monthly_cost`, and recalculates cost summary and WAF scores

**Checkpoint**: User Story 5 complete — optional components toggle on/off with live cost updates

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting all user stories

- [X] T058 [P] Add ARIA labels to diagram container and WAF panel for accessibility in src/digital_twin_migrate/web/templates/index.html
- [X] T059 [P] Add keyboard navigation for WAF panel (Escape to close, Tab through recommendations) in src/digital_twin_migrate/web/templates/index.html
- [X] T060 Implement diagram invalidation — after discovery upload, enrichment upload, or what-if override save, set `_ctdData = null` and show regeneration prompt in src/digital_twin_migrate/web/templates/index.html
- [X] T061 [P] Add progressive rendering for >500 VMs in src/digital_twin_migrate/web/templates/index.html — if node count >500, initially show landing zone summary nodes (collapsed) that expand on double-click
- [X] T061a [P] Add backend progressive rendering support in `generate_cloud_topology()` in src/digital_twin_migrate/cloud_topology.py — when VM count >500, return `collapsed: true` summary nodes per landing zone (with aggregate counts and costs) instead of individual resource nodes; include a `_resources` field with the full per-LZ resource list for on-demand expansion via a new `GET /api/cloud-topology/expand/<lz_id>` endpoint
- [X] T062 Run quickstart.md validation — follow all steps in specs/001-cloud-topology-diagram/quickstart.md end-to-end and verify they work
- [X] T063 Update specs/012-vulnerability-sla.spec.md to note that `_match_os` is now also consumed by cloud_topology.py
- [X] T064 Update README.md to document the Cloud Topology tab, its 2 API endpoints, and the new `cloud_topology.py` module

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — renders the diagram (MVP)
- **US2 (Phase 4)**: Depends on Phase 2 — enhances diagram with CAF styling (can run in parallel with US1 backend tasks since it modifies the same functions)
- **US3 (Phase 5)**: Depends on Phase 2 — adds WAF scoring (backend can start in parallel with US1; frontend depends on US1 canvas being in place)
- **US4 (Phase 6)**: Depends on US1 (needs diagram canvas for PNG export)
- **US5 (Phase 7)**: Depends on US1 (needs diagram + cost summary to toggle)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — fully independent, delivers the MVP
- **US2 (P2)**: Foundational only — backend work can start in parallel with US1; visual enhancements layer on top
- **US3 (P3)**: Foundational only for backend (WAF scoring); frontend WAF panel depends on US1's canvas + node click handler
- **US4 (P4)**: Depends on US1 (canvas exists for PNG, data exists for JSON/Mermaid)
- **US5 (P5)**: Depends on US1 (diagram + cost summary present)

### Within Each User Story

- Backend tasks before frontend tasks (API must return data before UI can render it)
- Models/builders before orchestrators (e.g., `_build_cloud_resource` before `generate_cloud_topology`)
- Tests can be written in parallel with implementation (same user story, different files)

### Parallel Opportunities per Story

**US1**: T009, T010, T011 (backend builders — different functions, same file but no interdependencies) can be developed in sequence then T012–T015 depend on them. Frontend T019–T026 depend on T018 (endpoint).

**US3**: T032–T036 (individual pillar scorers) are fully parallel — each is an independent pure function in different code sections.

**US4**: T048 (Mermaid backend) is parallel with T051–T054 (frontend export buttons).

---

## Parallel Example: User Story 3 (WAF Scoring)

```bash
# All 5 pillar scorers can be written simultaneously:
T032: _score_reliability()
T033: _score_security()
T034: _score_cost_optimisation()
T035: _score_operational_excellence()
T036: _score_performance_efficiency()

# Then orchestrate:
T037: compute_waf_scores() — calls all 5 scorers
T038: Wire into _build_cloud_resource()
T039: _build_waf_summary() — aggregates

# Tests in parallel with implementation:
T040: Unit tests for all 5 scorers
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T008)
3. Complete Phase 3: US1 — Generate Diagram (T009–T026)
4. **STOP and VALIDATE**: Load sample data, click "Generate Diagram", verify interactive canvas
5. Deploy/demo if ready — this alone delivers a complete cloud topology diagram

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Interactive diagram with nodes, edges, containers, cost summary (**MVP!**)
3. US2 → Colour-coded CAF landing zones with legend
4. US3 → WAF scores on every node + detail panel with radar chart
5. US4 → PNG, JSON, Mermaid export
6. US5 → Toggle optional infrastructure components
7. Polish → Accessibility, progressive rendering, documentation

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (US1)** — 26 tasks delivering a fully functional cloud topology diagram.
