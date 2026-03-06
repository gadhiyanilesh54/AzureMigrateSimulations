# Feature Specification: Cloud Topology Diagram (CTD)

**Feature Branch**: `001-cloud-topology-diagram`  
**Created**: 2026-03-04  
**Status**: Draft  
**Input**: User description: "Create Cloud Topology Diagram backed by Azure Cloud Adoption Framework (CAF) and Azure Well-Architected Framework (WAF) principles"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Generate Azure Architecture Diagram (Priority: P1)

After discovering an on-premises VMware environment and generating Azure migration recommendations, the user navigates to a "Cloud Topology" tab and clicks "Generate Diagram." The system automatically translates every discovered VM, workload, and network dependency into a proposed Azure architecture — placing resources into appropriate resource groups, virtual networks, subnets, and Azure services — and renders an interactive, zoomable diagram on screen.

**Why this priority**: This is the core value proposition. Without the diagram, no other CTD features (CAF annotations, WAF scoring, export) have a surface to attach to. A user who sees only this story still gets a complete, actionable visual of their future Azure estate.

**Independent Test**: Can be fully tested by loading the included sample data (202 VMs, 35 workloads) and clicking "Generate Diagram." The resulting diagram should show resource groups, VNets, subnets, Azure VM icons, and PaaS service icons with connecting lines representing discovered dependencies.

**Acceptance Scenarios**:

1. **Given** discovery data with 202 VMs and 35 workloads is loaded, **When** the user clicks "Generate Diagram," **Then** an interactive diagram renders within 5 seconds showing all Azure resources organised into resource groups and VNets.
2. **Given** a generated diagram, **When** the user hovers over an Azure resource node, **Then** a tooltip shows: source VM name, recommended Azure SKU, monthly cost, and migration readiness.
3. **Given** a generated diagram, **When** the user zooms in on a subnet, **Then** individual VMs and PaaS services are visible with connecting edges showing dependency direction and port.
4. **Given** no discovery data is loaded, **When** the user navigates to the Cloud Topology tab, **Then** a helpful empty state message explains that discovery must be run first.

---

### User Story 2 — CAF Landing Zone Alignment (Priority: P2)

The generated diagram organises Azure resources according to Cloud Adoption Framework (CAF) landing zone patterns. Resources are grouped into platform landing zones (connectivity, identity, management) and application landing zones based on workload type and criticality. The user can see how their migration maps to a well-structured Azure environment.

**Why this priority**: CAF alignment transforms the diagram from a flat list of resources into a structured, enterprise-ready architecture. It adds strategic value but depends on Story 1's diagram being in place first.

**Independent Test**: Can be tested by generating a diagram and verifying that resources are placed into named landing zone groups (e.g., "Connectivity," "Identity," "App-LZ-Production," "App-LZ-Dev/Test") following CAF conventions.

**Acceptance Scenarios**:

1. **Given** a generated diagram, **When** the diagram renders, **Then** resources are grouped into CAF-aligned landing zones: at minimum a Connectivity zone (hub VNet, firewall placeholder), a Management zone (monitoring, backup), and one or more Application landing zones.
2. **Given** VMs tagged as dev/test workloads (based on folder name or VM name patterns), **When** the diagram renders, **Then** those resources appear in a separate "Dev/Test" application landing zone with distinct visual styling.
3. **Given** discovered network dependencies between VMs, **When** the diagram renders, **Then** cross-landing-zone dependencies are shown as dashed lines passing through the hub VNet.

---

### User Story 3 — WAF Pillar Scoring & Recommendations (Priority: P3)

Each resource or resource group in the diagram displays a Well-Architected Framework (WAF) score across five pillars: Reliability, Security, Cost Optimisation, Operational Excellence, and Performance Efficiency. The scores are derived from the discovered data (e.g., single-instance VMs score low on Reliability; VMs without backup score low on Security). Clicking a resource shows pillar-by-pillar recommendations.

**Why this priority**: WAF scoring enriches the diagram with actionable improvement suggestions. It builds on the diagram (P1) and CAF layout (P2) by overlaying quality assessments that help users prioritise architectural improvements.

**Independent Test**: Can be tested by generating a diagram and clicking any resource node to verify that a WAF score panel appears with per-pillar scores and at least one recommendation per pillar.

**Acceptance Scenarios**:

1. **Given** a generated diagram, **When** the user clicks an Azure VM node, **Then** a side panel shows WAF scores across all five pillars as a radar/spider chart with numerical scores (0–100).
2. **Given** a VM with no availability set or zone redundancy configured, **When** the WAF panel renders, **Then** the Reliability pillar score is below 40 and includes a recommendation to enable availability zones.
3. **Given** a workload mapped to Azure SQL Database, **When** the WAF panel renders, **Then** the Security pillar includes a recommendation to enable Transparent Data Encryption and firewall rules.

---

### User Story 4 — Export & Share Diagram (Priority: P4)

The user can export the Cloud Topology Diagram in multiple formats for use in documentation, presentations, and architecture review boards.

**Why this priority**: Export enables the diagram to be used outside the application. Important for stakeholder communication but depends on the diagram existing first.

**Independent Test**: Can be tested by generating a diagram and clicking each export button to verify a valid file is downloaded.

**Acceptance Scenarios**:

1. **Given** a generated diagram, **When** the user clicks "Export as PNG," **Then** a high-resolution PNG image of the diagram is downloaded.
2. **Given** a generated diagram, **When** the user clicks "Export as JSON," **Then** a structured JSON file containing all resource nodes, edges, landing zones, and WAF scores is downloaded.
3. **Given** a generated diagram, **When** the user clicks "Copy Mermaid," **Then** a Mermaid diagram definition is copied to the clipboard that renders correctly in any Mermaid-compatible viewer.

---

### User Story 5 — Interactive Customisation (Priority: P5)

The user can customise the generated diagram by manually moving resources between landing zones, changing suggested Azure services, adjusting redundancy levels, and toggling optional components (firewall, bastion, load balancer). Changes recalculate WAF scores and cost estimates in real time.

**Why this priority**: Customisation makes the diagram a planning tool rather than a static output. It's a power-user feature that adds significant value but depends on all prior stories.

**Independent Test**: Can be tested by dragging a VM from one landing zone to another and verifying the landing zone assignment updates in the underlying data model and the cost summary recalculates.

**Acceptance Scenarios**:

1. **Given** a generated diagram, **When** the user drags an Azure VM node from "App-LZ-Production" to "App-LZ-Dev/Test," **Then** the landing zone assignment updates, the visual grouping changes, and the cost summary recalculates.
2. **Given** a generated diagram with a hub VNet, **When** the user toggles "Add Azure Firewall," **Then** a firewall node is added to the Connectivity landing zone and the monthly cost increases accordingly.
3. **Given** a modified diagram, **When** the user clicks "Reset to Default," **Then** the diagram reverts to the originally generated layout.

---

### Edge Cases

- What happens when a VM has no Azure SKU recommendation (e.g., "Not Ready" readiness)? → Display the VM in a "Requires Attention" group with a warning icon and no Azure service mapping.
- What happens when two VMs have circular dependencies? → Show bidirectional edges between them without duplicating the dependency line.
- What happens when there are no workload dependencies discovered (no guest discovery run)? → Generate the diagram with resource groups and VNets but without dependency edges, and show a notice suggesting the user run workload discovery for richer topology.
- What happens when the fleet exceeds 500 VMs? → Apply progressive rendering: show landing zone summaries first, expand to individual resources on zoom or click.
- What happens when the user generates a diagram, then uploads new discovery data? → Invalidate the cached diagram and prompt the user to regenerate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a cloud architecture diagram from the discovered VM, workload, and network dependency data.
- **FR-002**: System MUST map each discovered VM to its recommended Azure resource (Azure VM SKU, or PaaS service if workload is mapped).
- **FR-003**: System MUST organise Azure resources into CAF-aligned landing zones:
  - **Connectivity** — hub VNet, network placeholders (firewall, VPN gateway, bastion)
  - **Identity** — placeholder zone for future Azure AD / Entra ID resources (no discovered VMs placed here in v1)
  - **Management** — monitoring, backup, security placeholders
  - **Application Landing Zones** — one per workload environment (production, dev/test) or per business unit (derived from vCenter folder structure)
- **FR-004**: System MUST create virtual network and subnet groupings within each **application** landing zone based on discovered workload type — one subnet per type (`webapp`, `database`, `container`, `orchestrator`) plus a "General Compute" subnet for VMs without workload discovery data. Platform landing zones (Connectivity) use dedicated subnet types (`gateway`, `firewall`) instead.
- **FR-005**: System MUST render dependency edges between resources based on discovered TCP connections from guest-level workload discovery.
- **FR-006**: System MUST calculate a WAF score (0–100) for each of the five pillars per resource, derived from discoverable attributes. When data for a pillar is insufficient, the system MUST display that pillar as "Insufficient Data" (grey/N/A) with a prompt indicating which data source is needed (e.g., "Run perf collector" or "Upload enrichment data") rather than assigning a default score:
  - **Reliability**: *Note: availability sets, zone redundancy, and backup status are not discoverable from vCenter.* The score is a proxy based on available signals (power state, perf data presence, workload group size)
  - **Security**: OS lifecycle status, encryption eligibility, network segmentation
  - **Cost Optimisation**: right-sizing confidence, reserved instance eligibility, AHUB eligibility
  - **Operational Excellence**: monitoring coverage (enrichment data), VMware tools status, automation readiness
  - **Performance Efficiency**: performance data availability, CPU/memory utilisation percentiles, IOPS headroom
- **FR-007**: System MUST display a WAF recommendation panel when a resource or landing zone is clicked, showing per-pillar scores and actionable suggestions.
- **FR-008**: System MUST provide export in at least two formats: PNG image (via canvas-native `toDataURL()` with auto-fit before capture, zero additional dependencies) and structured JSON.
- **FR-009**: System MUST provide a Mermaid diagram export option (copy to clipboard).
- **FR-010**: System MUST display a cost summary for the entire cloud topology, broken down by landing zone.
- **FR-011**: System MUST render the diagram as an interactive, zoomable, pannable canvas with node tooltips.
- **FR-012**: System MUST show a helpful empty state when no discovery data is available.
- **FR-013**: System MUST visually distinguish resource types using distinct colours or icons (VMs, databases, web apps, networking, security).
- **FR-014**: System MUST allow the user to toggle optional infrastructure components (firewall, bastion host, load balancer, VPN gateway) and reflect the cost impact using a hardcoded approximate cost table (East US PAYG base prices adjusted by the same region multipliers used for VM pricing): Azure Firewall Standard ~$912/mo, Bastion Standard ~$139/mo, Standard Load Balancer ~$18/mo, VPN Gateway S2S ~$138/mo.
- **FR-015**: System MUST regenerate the diagram when underlying data changes (new discovery, enrichment upload, what-if override).

### Key Entities

- **Cloud Topology**: The overall generated Azure architecture containing all landing zones, resources, and connections. Attributes: generation timestamp, source discovery ID, total cost, overall WAF scores.
- **Landing Zone**: A CAF-aligned grouping of resources. Attributes: name, type (connectivity/management/application), environment (production/dev-test), contained resources, aggregate WAF scores, aggregate cost.
- **Cloud Resource**: An Azure resource mapped from a discovered VM or workload. Attributes: source VM/workload name, Azure service type, SKU, monthly cost, landing zone, subnet, WAF scores per pillar.
- **Topology Edge**: A directed connection between two cloud resources representing a network dependency. Attributes: source resource, target resource, protocol, port, service type.
- **WAF Assessment**: Per-resource or per-landing-zone quality scores. Attributes: pillar name, score (0–100), recommendations list, data sources used for scoring.

## Clarifications

### Session 2026-03-04

- Q: How should workloads be classified into subnet tiers for the diagram? → A: Direct workload-type mapping — one subnet group per discovered workload type (`webapp`, `database`, `container`, `orchestrator`) plus a "General Compute" subnet for VMs with no workload discovery.
- Q: How should WAF pillar scores handle missing input data? → A: Score what you can, mark the rest "Insufficient Data" — calculate a score only for pillars with enough data; display pillars with insufficient data as grey/N/A with a prompt to run perf collection or enrichment.
- Q: How should PNG export be implemented? → A: Canvas-native export — use the existing vis-network canvas `toDataURL()` method to export the current viewport as PNG, adding zero new dependencies. The UI will auto-fit the diagram before export.
- Q: What should the default landing zone assignment be for VMs whose folder name doesn't match any dev/test/staging pattern? → A: Default to Production — any VM whose folder doesn't match dev/test/staging patterns is placed in the Production application landing zone. This ensures no production system is accidentally placed in a lower-SLA zone.
- Q: How should the cost of optional infrastructure components be estimated? → A: Hardcoded approximate costs — use a static cost table (e.g., Azure Firewall ~$912/mo, Bastion ~$139/mo, Standard LB ~$18/mo, VPN Gateway ~$138/mo) based on East US PAYG, adjusted by the same region multipliers used for VM pricing.

## Assumptions

- vCenter folder hierarchy is used as a heuristic for workload environment grouping (folders containing "dev," "test," "staging" → Dev/Test landing zone; all others default to Production). This ensures no production system is accidentally placed in a lower-SLA landing zone.
- For VMs with "Not Ready" migration readiness, the system places them in a "Requires Attention" group without assigning an Azure service.
- Hub-spoke network topology is used as the default CAF pattern. Flat network topologies are not supported in v1.
- WAF scores are derived solely from data already available in the discovery/enrichment/assessment pipeline — no external Azure Advisor or policy engine is required.
- Diagram layout uses a top-down hierarchical arrangement by default (landing zones → VNets → subnets → resources).
- The initial release (v1) does not include custom resource naming policies or tagging policies; CAF naming is applied with default conventions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate a complete cloud topology diagram from sample data (202 VMs, 35 workloads) within 5 seconds.
- **SC-002**: The generated diagram accurately maps 100% of discovered VMs with "Ready" or "Ready with Conditions" status to Azure resources.
- **SC-003**: 90% of users can identify which landing zone a specific VM belongs to within 10 seconds of viewing the diagram.
- **SC-004**: WAF score panel loads within 300 ms of clicking a resource node.
- **SC-005**: Exported PNG image renders at a minimum resolution of 1920×1080 with legible labels.
- **SC-006**: Exported JSON/Mermaid output can be re-imported or rendered by a third-party tool without errors.
- **SC-007**: Cost summary per landing zone matches the fleet simulation totals to within 1% rounding tolerance.
