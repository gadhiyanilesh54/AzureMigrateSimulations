# REST API Contract: GET /api/risk/heatmap

**Method**: GET  
**Path**: `/api/risk/heatmap`  
**Auth**: Optional API key (`X-API-Key` header when `MIGRATE_API_KEY` is set)  
**Content-Type**: `application/json`

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `sort_by` | string | No | `composite_score` | Sort field: `composite_score`, `vm_name`, or any factor name |
| `sort_order` | string | No | `desc` | Sort direction: `asc` or `desc` |
| `band` | string | No | (all) | Filter by band: `green`, `yellow`, or `red` |
| `top` | int | No | (all) | Limit to top-N VMs by composite score |

## Response: 200 OK

```json
{
  "total_vms": 202,
  "factor_names": [
    "dependency_count",
    "os_eol",
    "workload_complexity",
    "performance_sensitivity",
    "compliance_scope",
    "data_volume"
  ],
  "band_distribution": {
    "green": 120,
    "yellow": 55,
    "red": 27
  },
  "vm_scores": [
    {
      "vm_name": "SQL-PROD-01",
      "composite_score": 78,
      "composite_band": "red",
      "dominant_factor": "os_eol",
      "factors": [
        {
          "name": "dependency_count",
          "raw_value": "12 dependencies",
          "score": 85,
          "weight": 0.15,
          "weighted_score": 12.75,
          "band": "red",
          "data_available": true
        },
        {
          "name": "os_eol",
          "raw_value": "EOL: 2024-01-09 (Windows Server 2012 R2)",
          "score": 100,
          "weight": 0.25,
          "weighted_score": 25.0,
          "band": "red",
          "data_available": true
        },
        {
          "name": "workload_complexity",
          "raw_value": "MSSQL Enterprise (350 GB)",
          "score": 95,
          "weight": 0.20,
          "weighted_score": 19.0,
          "band": "red",
          "data_available": true
        },
        {
          "name": "performance_sensitivity",
          "raw_value": "P95 IOPS: 2400 (fleet 75th pctl: 800)",
          "score": 100,
          "weight": 0.10,
          "weighted_score": 10.0,
          "band": "red",
          "data_available": true
        },
        {
          "name": "compliance_scope",
          "raw_value": "PCI-DSS, HIPAA",
          "score": 80,
          "weight": 0.20,
          "weighted_score": 16.0,
          "band": "red",
          "data_available": true
        },
        {
          "name": "data_volume",
          "raw_value": "480 GB (fleet max: 2000 GB)",
          "score": 24,
          "weight": 0.10,
          "weighted_score": 2.4,
          "band": "green",
          "data_available": true
        }
      ],
      "mitigations": [
        {
          "factor": "os_eol",
          "severity": "red",
          "action": "Upgrade OS to a supported version before migration, or leverage Azure Extended Security Updates (ESU)",
          "expected_risk_reduction": 25
        }
      ]
    }
  ],
  "top_risky": [
    {
      "vm_name": "SQL-PROD-01",
      "composite_score": 78,
      "composite_band": "red",
      "dominant_factor": "os_eol",
      "factors": [],
      "mitigations": []
    }
  ]
}
```

## Response: 200 OK (empty fleet)

```json
{
  "total_vms": 0,
  "factor_names": [
    "dependency_count", "os_eol", "workload_complexity",
    "performance_sensitivity", "compliance_scope", "data_volume"
  ],
  "band_distribution": { "green": 0, "yellow": 0, "red": 0 },
  "vm_scores": [],
  "top_risky": [],
  "message": "No VMs available. Run discovery first."
}
```
