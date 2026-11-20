# Quickstart: Migration Risk Heatmap

**Feature**: `002-migration-risk-heatmap`

## Prerequisites

- Python ≥ 3.10 with the project installed (`pip install -e ".[web,mcp]"`)
- Discovery data loaded (either from vCenter discovery or JSON upload via `data/vcenter_discovery.json`)
- (Optional) Workload discovery data in `data/workload_discovery.json`
- (Optional) Performance history in `data/perf_history.json`
- (Optional) Enrichment data in `data/enrichment_data.json`

## CLI Usage

### View fleet-wide heatmap (table)

```bash
dt-migrate risk heatmap
```

### View top-5 riskiest VMs as JSON

```bash
dt-migrate risk heatmap --top 5 --format json
```

### Check a specific VM's risk score

```bash
dt-migrate risk score SQL-PROD-01
```

### Get JSON output for automation

```bash
dt-migrate risk score SQL-PROD-01 --format json | jq '.composite_score'
```

## REST API Usage

### Start the web server

```bash
dt-migrate-web
```

### Get full heatmap

```bash
curl http://localhost:5000/api/risk/heatmap
```

### Get single VM risk score

```bash
curl http://localhost:5000/api/risk/score/SQL-PROD-01
```

### Filter by risk band

```bash
curl "http://localhost:5000/api/risk/heatmap?band=red&sort_by=composite_score"
```

## Web UI

1. Start the web server: `dt-migrate-web`
2. Open `http://localhost:5000` in a browser
3. Navigate to the **Decide** phase
4. Click the **Risk Heatmap** tab
5. View the color-coded grid — click any VM row to expand the breakdown

## MCP Server

When connected to an AI agent via MCP:

```
Use the get_risk_heatmap tool to see the fleet-wide risk matrix.
Use the get_risk_score tool with vm_name="SQL-PROD-01" to get detailed scoring.
```

## How Risk Scores Work

Each VM is scored on six factors (each 0–100), combined with weights:

| Factor | Weight | Data Source |
|--------|--------|-------------|
| Dependency Count | 15% | Workload discovery dependencies |
| OS EOL Status | 25% | vulnerability_sla.py OS lifecycle DB |
| Workload Complexity | 20% | Guest/workload discovery |
| Performance Sensitivity | 10% | Performance history (P95 IOPS) |
| Compliance Scope | 20% | VM tags & enrichment tags |
| Data Volume | 10% | Disk provisioned size |

**Color bands**: Green (0–30) = low risk, Yellow (31–60) = moderate, Red (61–100) = high risk.

Factors with missing data default to 0 and are flagged as "data unavailable."
