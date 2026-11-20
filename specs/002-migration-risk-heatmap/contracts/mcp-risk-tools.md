# MCP Tools Contract: Risk Heatmap

**Server**: `azure-migrate-simulations` (existing MCP server)

## Tool: get_risk_heatmap

Compute the fleet-wide migration risk heatmap.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `top` | int | No | 10 | Number of top riskiest VMs to highlight |
| `band` | str | No | (all) | Filter by risk band: `green`, `yellow`, or `red` |
| `sort_by` | str | No | `composite_score` | Sort field |

**Returns**: JSON matching the `GET /api/risk/heatmap` response schema.

**Example invocation**:
```
Tool: get_risk_heatmap
Args: { "top": 5, "band": "red" }
```

**Example response**: (truncated)
```json
{
  "total_vms": 27,
  "factor_names": ["dependency_count", "os_eol", "workload_complexity", "performance_sensitivity", "compliance_scope", "data_volume"],
  "band_distribution": { "green": 0, "yellow": 0, "red": 27 },
  "vm_scores": [...],
  "top_risky": [...]
}
```

---

## Tool: get_risk_score

Get the detailed risk score for a single VM.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `vm_name` | str | Yes | — | VM name to score |

**Returns**: JSON matching the `GET /api/risk/score/<vm_name>` response schema.

**Example invocation**:
```
Tool: get_risk_score
Args: { "vm_name": "SQL-PROD-01" }
```

**Error handling**: Returns `{"error": "VM not found", "vm_name": "..."}` when VM does not exist.
