# Feature Specification: Migration Risk Heatmap

**Feature Branch**: `002-migration-risk-heatmap`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Build a Migration Risk Heatmap that computes a composite risk score (0-100) for each discovered VM by combining weighted factors: dependency count (more deps = higher risk), OS EOL status (EOL = +30 risk), workload complexity (database = higher than static web), performance sensitivity (high IOPS = riskier), compliance scope (PCI/HIPAA workloads = higher risk), and data volume (large disks = longer migration). Produce a fleet-wide heatmap as a JSON matrix (VM x risk-factor) with color bands (green 0-30, yellow 31-60, red 61-100). Identify the top-10 riskiest VMs and suggest risk mitigation actions. Expose via CLI (dt-migrate risk heatmap, dt-migrate risk score <vm_name>) and REST API (/api/risk/heatmap, /api/risk/score/<vm_name>) and via MCP Server. Add a web UI tab under the Decide phase with a visual grid."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Fleet-Wide Risk Heatmap (Priority: P1)

A migration architect opens the web dashboard and navigates to the "Risk Heatmap" tab under the Decide phase. They see a color-coded grid showing every discovered VM on one axis and risk factors on the other. Each cell is shaded green (0–30), yellow (31–60), or red (61–100). A composite score column summarizes each VM's overall risk. The architect quickly identifies clusters of high-risk VMs and decides which workloads need special attention before migration.

**Why this priority**: The heatmap is the core deliverable — without it, no other risk feature has value. It provides the primary visual and data artifact that all other stories build upon.

**Independent Test**: Can be fully tested by loading a discovery dataset, computing scores, and rendering the heatmap grid. Delivers immediate value by surfacing fleet-wide risk at a glance.

**Acceptance Scenarios**:

1. **Given** a discovery dataset with at least one VM, **When** the user opens the Risk Heatmap tab, **Then** a grid displays every VM with per-factor scores and a composite score, each cell colored by risk band (green 0–30, yellow 31–60, red 61–100).
2. **Given** a discovery dataset with 500+ VMs, **When** the heatmap loads, **Then** the grid renders within 5 seconds and supports scrolling and sorting by composite score.
3. **Given** a VM with no dependencies, non-EOL OS, low IOPS, no compliance tags, and small disks, **When** its risk is computed, **Then** the composite score is in the green band (0–30).
4. **Given** a VM running an EOL operating system with 10+ dependencies and a database workload, **When** its risk is computed, **Then** the composite score is in the red band (61–100).

---

### User Story 2 - Drill Into Individual VM Risk Score (Priority: P2)

A migration engineer selects a specific VM from the heatmap (or queries it by name via CLI or API) and sees a detailed risk breakdown: each factor's raw value, its weighted contribution to the composite score, the resulting risk band, and suggested mitigation actions specific to that VM's risk profile.

**Why this priority**: After identifying risky VMs in the heatmap, users need per-VM detail to plan remediation. This is the natural next step in the risk assessment workflow.

**Independent Test**: Can be tested by querying a single VM's risk score and verifying the breakdown includes all six factors, weights, and at least one mitigation suggestion per high-risk factor.

**Acceptance Scenarios**:

1. **Given** a VM name that exists in the discovery dataset, **When** the user queries its risk score (via UI click, CLI command, or API call), **Then** a detailed breakdown shows each of the six risk factors with raw value, weighted score, and color band.
2. **Given** a VM with at least one factor scoring above 60, **When** the risk detail is displayed, **Then** at least one actionable mitigation suggestion is shown for each red-band factor.
3. **Given** a VM name that does not exist in the dataset, **When** the user queries it, **Then** the system returns a clear "VM not found" message.

---

### User Story 3 - Top-10 Riskiest VMs Report (Priority: P2)

A project manager runs a CLI command or views a section of the heatmap that highlights the top-10 VMs by composite risk score. For each VM, the report includes the score, the dominant risk factor, and a recommended first mitigation step. This enables rapid triage and sprint planning for pre-migration remediation.

**Why this priority**: Enables rapid triage without requiring the user to mentally sort through the entire fleet. Directly supports migration planning and prioritization.

**Independent Test**: Can be tested by computing scores for a fleet and verifying the top-10 list is correctly sorted in descending order by composite score, with mitigation suggestions attached.

**Acceptance Scenarios**:

1. **Given** a fleet of 20+ VMs with computed risk scores, **When** the user requests the top-10 riskiest VMs, **Then** a ranked list of exactly 10 VMs (or fewer if the fleet is smaller) is returned, sorted descending by composite score.
2. **Given** the top-10 list, **When** the user reviews each entry, **Then** each entry includes the VM name, composite score, dominant risk factor, and a mitigation suggestion.
3. **Given** a fleet with fewer than 10 VMs, **When** the top-10 is requested, **Then** all VMs are listed without error.

---

### User Story 4 - CLI Risk Commands (Priority: P3)

A DevOps engineer working in a terminal runs `dt-migrate risk heatmap` to produce the full heatmap as JSON output, and `dt-migrate risk score <vm_name>` to get a single VM's risk detail. These commands integrate with existing automation pipelines and scripting workflows.

**Why this priority**: CLI access is essential for automation and CI/CD integration but depends on the core scoring engine being built first.

**Independent Test**: Can be tested by running each CLI command against a sample discovery dataset and verifying correct JSON output structure and exit codes.

**Acceptance Scenarios**:

1. **Given** a valid discovery dataset is available, **When** the user runs `dt-migrate risk heatmap`, **Then** the system outputs the full VM × risk-factor JSON matrix to stdout with zero exit code.
2. **Given** a valid VM name, **When** the user runs `dt-migrate risk score <vm_name>`, **Then** the system outputs the per-factor breakdown as JSON with zero exit code.
3. **Given** an invalid VM name, **When** the user runs `dt-migrate risk score nonexistent-vm`, **Then** the system outputs an error message and returns a non-zero exit code.

---

### User Story 5 - REST API and MCP Server Exposure (Priority: P3)

An external tool or AI agent queries the risk heatmap via REST API (`/api/risk/heatmap`, `/api/risk/score/<vm_name>`) or MCP Server tools to integrate risk data into automated migration planning, dashboards, or reports.

**Why this priority**: API and MCP exposure extends value to external integrations but depends on the scoring engine and data structures being stable.

**Independent Test**: Can be tested by sending HTTP requests to each endpoint and verifying response structure, status codes, and correctness of returned data.

**Acceptance Scenarios**:

1. **Given** the web server is running with loaded discovery data, **When** a GET request is made to `/api/risk/heatmap`, **Then** the response is a JSON object containing the full VM × risk-factor matrix with composite scores and color bands.
2. **Given** a valid VM name, **When** a GET request is made to `/api/risk/score/<vm_name>`, **Then** the response is a JSON object with per-factor breakdown, composite score, color band, and mitigation suggestions.
3. **Given** the MCP server is running, **When** an AI agent invokes the risk heatmap tool, **Then** the tool returns the same data structure as the REST API heatmap endpoint.
4. **Given** an invalid VM name, **When** a GET request is made to `/api/risk/score/nonexistent`, **Then** the response has a 404 status code and a descriptive error message.

---

### Edge Cases

- What happens when a VM has no dependency data (dependencies not yet discovered)? The dependency factor defaults to 0 (lowest risk) and the heatmap marks that cell as "data unavailable."
- What happens when OS EOL data is missing for a VM's operating system? The OS EOL factor defaults to a medium value (15) and is flagged as "unverified" in the breakdown.
- What happens when the fleet has zero VMs? The heatmap endpoint returns an empty matrix with a message indicating no VMs are available.
- What happens when performance history has not been collected for a VM? The performance sensitivity factor defaults to 0 and is marked "no data" in the breakdown.
- What happens when two VMs have identical composite scores in the top-10? Both appear in the list, sorted alphabetically by VM name as a tiebreaker.
- How does the system handle VMs with extremely large disk counts (50+ disks)? The data volume factor caps at 100; the score does not exceed the maximum.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute a composite risk score (integer 0–100) for each discovered VM by combining six weighted risk factors.
- **FR-002**: System MUST evaluate the **dependency count** factor — VMs with more cross-VM dependencies receive a higher risk contribution. A VM with 0 dependencies scores 0 for this factor; the score scales linearly up to the factor maximum based on relative dependency count within the fleet.
- **FR-003**: System MUST evaluate the **OS EOL status** factor — VMs running an end-of-life operating system receive a fixed +30 risk contribution to their composite score. Non-EOL systems receive 0 for this factor.
- **FR-004**: System MUST evaluate the **workload complexity** factor — database workloads (SQL Server, MySQL, PostgreSQL, Oracle, etc.) score highest; application servers and containers score medium; static web servers and file servers score lowest. VMs with no detected workload default to a low score.
- **FR-005**: System MUST evaluate the **performance sensitivity** factor — VMs with high IOPS (above the fleet's 75th percentile) receive higher risk; VMs below the 25th percentile receive low risk. When no performance data is available, the factor defaults to 0.
- **FR-006**: System MUST evaluate the **compliance scope** factor — VMs tagged or classified under PCI, HIPAA, SOX, or other regulatory frameworks receive a higher risk contribution. VMs with no compliance tags score 0.
- **FR-007**: System MUST evaluate the **data volume** factor — total provisioned disk size contributes to risk, reflecting longer migration windows. The score scales linearly from 0 (small) to the factor maximum based on fleet-relative disk size.
- **FR-008**: System MUST produce a fleet-wide heatmap as a JSON matrix with VMs on one axis and the six risk factors plus composite score on the other axis.
- **FR-009**: System MUST assign color bands to each score: green (0–30), yellow (31–60), red (61–100).
- **FR-010**: System MUST identify the top-10 riskiest VMs (by composite score, descending) and include a mitigation suggestion for each.
- **FR-011**: System MUST provide mitigation suggestions for each risk factor when it scores above the yellow threshold (>30). Suggestions must be actionable (e.g., "Upgrade OS to supported version," "Reduce dependencies by extracting shared services," "Enable replication for large disks to reduce cutover time").
- **FR-012**: System MUST expose a CLI command `dt-migrate risk heatmap` that outputs the full heatmap JSON matrix.
- **FR-013**: System MUST expose a CLI command `dt-migrate risk score <vm_name>` that outputs a single VM's per-factor risk breakdown with mitigation suggestions.
- **FR-014**: System MUST expose a REST API endpoint `GET /api/risk/heatmap` that returns the full heatmap matrix as JSON.
- **FR-015**: System MUST expose a REST API endpoint `GET /api/risk/score/<vm_name>` that returns a single VM's risk breakdown as JSON.
- **FR-016**: System MUST expose risk heatmap and risk score as MCP Server tools, returning the same data structures as the REST API.
- **FR-017**: System MUST display a "Risk Heatmap" tab in the web UI under the Decide phase, rendering the heatmap as a visual color-coded grid.
- **FR-018**: System MUST allow users to click on a VM row in the web heatmap to view the detailed per-factor breakdown and mitigation suggestions.
- **FR-019**: System MUST allow sorting the heatmap grid by composite score or by any individual risk factor column.
- **FR-020**: System MUST recompute risk scores when underlying data changes (new discovery, enrichment updates, or performance data refresh).

### Key Entities

- **RiskScore**: Represents the computed risk assessment for a single VM. Contains the VM identifier, six individual factor scores (each 0–100), factor weights, the weighted composite score (0–100), the color band assignment, and a list of mitigation suggestions for high-risk factors.
- **RiskFactor**: Represents one of the six evaluation dimensions (dependency count, OS EOL status, workload complexity, performance sensitivity, compliance scope, data volume). Each has a name, raw value, normalized score (0–100), configured weight, and weighted contribution to the composite.
- **RiskHeatmap**: The fleet-wide matrix aggregating all VM risk scores. Contains the ordered list of VMs, the ordered list of factors, the score matrix, color band assignments, and the top-10 riskiest VMs with mitigation suggestions.
- **MitigationAction**: A suggested remediation step tied to a specific risk factor for a specific VM. Contains the factor name, severity level, action description, and expected risk reduction.

## Assumptions

- Discovery data (VMs, dependencies, OS info, disk sizes) is already available from the existing vCenter discovery or JSON upload pipeline.
- OS EOL status is available from the existing vulnerability/SLA module (vulnerability_sla.py).
- Workload classification data is available from the existing guest discovery and workload assessment modules.
- Performance metrics (IOPS) are available from the existing performance monitoring module when performance history has been collected.
- Compliance tags (PCI, HIPAA, etc.) are user-supplied via enrichment data or manual tagging; the system does not auto-detect compliance scope.
- Default factor weights are: dependency count (15%), OS EOL (25%), workload complexity (20%), performance sensitivity (10%), compliance scope (20%), data volume (10%). Weights sum to 100%.
- The heatmap recalculates on demand (not in real-time); there is no background refresh process.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view the fleet-wide risk heatmap within 5 seconds of navigation for a fleet of up to 500 VMs.
- **SC-002**: Every VM in the discovery dataset receives a composite risk score, with 100% coverage — no VM is left unscored.
- **SC-003**: The top-10 riskiest VMs list correctly identifies the 10 highest-scoring VMs (verified against manual calculation on a test dataset).
- **SC-004**: Each VM with at least one red-band (61–100) factor has at least one actionable mitigation suggestion displayed.
- **SC-005**: CLI commands (`dt-migrate risk heatmap` and `dt-migrate risk score <vm_name>`) produce valid JSON output that can be consumed by standard JSON tools (jq, Python json module).
- **SC-006**: REST API endpoints return correct HTTP status codes (200 for success, 404 for unknown VM) and valid JSON response bodies.
- **SC-007**: 90% of users can identify the riskiest VMs in their fleet within 30 seconds of viewing the heatmap (usability goal).
- **SC-008**: Risk scores are deterministic — the same input data always produces the same scores.
