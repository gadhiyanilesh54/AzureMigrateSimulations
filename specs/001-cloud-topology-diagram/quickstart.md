# Quickstart: Cloud Topology Diagram (CTD)

**Feature**: `001-cloud-topology-diagram` | **Date**: 2026-03-04

## Prerequisites

- Python ≥ 3.10, `uv` package manager
- Repository cloned and dependencies installed (`uv sync`)
- Sample data present in `data/` (shipped with the repo)

## 1. Start the Dashboard

```bash
uv run python -m digital_twin_migrate.web.app
# Open http://localhost:5000
```

## 2. Load Data

Either connect to vCenter (enter credentials on the Connect screen) or simply open the dashboard — sample data auto-loads from `data/vcenter_discovery.json` and `data/workload_discovery.json`.

## 3. Generate the Cloud Topology

1. Click the **"Cloud Topology"** tab in the main navigation.
2. Click **"Generate Diagram"**.
3. The diagram renders within a few seconds, showing:
   - **Landing zones** as large labelled containers (Connectivity, Management, Production, Dev/Test)
   - **VNets** as nested containers within landing zones
   - **Subnets** grouped by workload type (webapp, database, container, general compute)
   - **Azure resources** as individual nodes with colour-coded icons
   - **Dependency edges** as arrows between resources (if workload discovery data is available)

## 4. Explore WAF Scores

Click any resource node to open the **WAF Assessment Panel** on the right side. It shows:
- A radar chart with scores for all 5 pillars (Reliability, Security, Cost Optimisation, Operational Excellence, Performance Efficiency)
- Pillar scores as numbers (0–100), or "Insufficient Data" with a prompt to collect more data
- Actionable recommendations per pillar

## 5. Toggle Optional Components

Above the diagram, toggle switches control optional infrastructure:
- **Azure Firewall** (~$912/mo)
- **Azure Bastion** (~$139/mo)
- **Standard Load Balancer** (~$18/mo)
- **VPN Gateway** (~$138/mo)

Toggling a component updates the diagram and the cost summary.

## 6. Export

Use the toolbar buttons:
- **Export PNG** — downloads a PNG screenshot of the diagram
- **Export JSON** — downloads the full topology data as structured JSON
- **Copy Mermaid** — copies a Mermaid flowchart definition to the clipboard

## 7. Run Tests

```bash
uv sync --extra dev
uv run python -m pytest tests/test_cloud_topology.py -v
```

## API Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cloud-topology` | Generate full topology JSON |
| `GET` | `/api/cloud-topology/waf/<resource_id>` | WAF detail for one resource |

### Example

```bash
curl http://localhost:5000/api/cloud-topology?firewall=true
curl http://localhost:5000/api/cloud-topology/waf/res-vm-WindowsVM175
```
