---
feature: topology-views
status: implemented
module: web/app.py, web/templates/index.html
---

# Topology Views

## Summary

Interactive vis-network graph visualisations showing infrastructure hierarchy (vCenter → DCs → Clusters → Hosts → VMs) and cross-VM workload dependency maps built from discovered TCP connections.

## User Stories

- As an infrastructure engineer, I want to see a visual hierarchy of my vCenter environment so that I understand the physical-to-virtual mapping.
- As a migration planner, I want to see dependency links between VMs so that I can group co-dependent workloads into the same migration wave.
- As a user, I want to click a VM node to open its What-If assessment so that I can drill down without leaving the topology view.

## Functional Requirements

- **FR-1:** **Infrastructure Topology** — hierarchical graph: vCenter → Datacenter → Cluster → ESXi Host → VM, with Datastore and Network associations.
- **FR-2:** Nodes are colour-coded by type (blue = VM, green = host, orange = datastore, purple = network).
- **FR-3:** Clickable legend toggles visibility of each node type.
- **FR-4:** Hover tooltips show node details (vCPU, RAM, disk for VMs; cores, ESXi version for hosts).
- **FR-5:** **Dependency Topology** — directed graph showing cross-VM TCP connections discovered during guest probing.
- **FR-6:** Edge labels show service type and port number.
- **FR-7:** Physics-based layout with drag-and-zoom navigation.
- **FR-8:** Clicking a VM node opens the VM What-If modal.

## Non-Functional Requirements

- **NFR-1:** Graph must render smoothly for up to 300 nodes / 500 edges.
- **NFR-2:** Physics simulation must stabilize within 3 seconds.
- **NFR-3:** Graph canvas must be responsive (fills available width).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/topology` | Infrastructure topology graph (nodes + edges) |
| `GET` | `/api/workloads/topology` | Workload dependency topology graph |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — topology endpoint handlers building vis-network compatible JSON
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — vis-network initialisation, legend, node click handlers

### Key Classes / Functions

- `/api/topology` handler — builds node/edge arrays from `DiscoveredEnvironment` hierarchy
- `/api/workloads/topology` handler — analyses `EstablishedConnection` records from guest discovery
- Client-side `renderTopology(data)` — vis-network graph initialisation

### Data Models

- Topology response: `{ nodes: [{id, label, group, title, ...}], edges: [{from, to, label, ...}] }`

## Dependencies

- vis-network 9.1.6 (CDN)

## Test Coverage

- No dedicated topology tests; endpoint response shape to be validated.

## Acceptance Criteria

- [ ] GET `/api/topology` returns valid vis-network node/edge JSON.
- [ ] Infrastructure topology renders hierarchical layout with correct parent-child edges.
- [ ] Node colour and shape matches the type legend.
- [ ] Clicking a VM node opens the What-If modal with correct VM data.
- [ ] Dependency topology shows directed edges with service/port labels.
- [ ] Graph is zoomable, pannable, and nodes are draggable.
