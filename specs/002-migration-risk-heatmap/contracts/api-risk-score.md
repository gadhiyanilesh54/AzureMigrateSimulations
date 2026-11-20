# REST API Contract: GET /api/risk/score/<vm_name>

**Method**: GET  
**Path**: `/api/risk/score/<vm_name>`  
**Auth**: Optional API key (`X-API-Key` header when `MIGRATE_API_KEY` is set)  
**Content-Type**: `application/json`

## Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vm_name` | string | Yes | Exact VM name (case-sensitive, matching `DiscoveredVM.name`) |

## Response: 200 OK

```json
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
      "factor": "dependency_count",
      "severity": "red",
      "action": "Reduce dependencies by extracting shared services into independent VMs or PaaS",
      "expected_risk_reduction": 10
    },
    {
      "factor": "os_eol",
      "severity": "red",
      "action": "Upgrade OS to a supported version before migration, or leverage Azure Extended Security Updates (ESU)",
      "expected_risk_reduction": 25
    },
    {
      "factor": "workload_complexity",
      "severity": "red",
      "action": "Plan a phased migration: migrate the database to Azure PaaS first, then redirect application connections",
      "expected_risk_reduction": 15
    },
    {
      "factor": "performance_sensitivity",
      "severity": "red",
      "action": "Enable Azure Migrate replication to measure actual Azure disk IOPS before cutover",
      "expected_risk_reduction": 8
    },
    {
      "factor": "compliance_scope",
      "severity": "red",
      "action": "Engage compliance team for pre-migration audit; deploy to Azure landing zone with regulatory controls",
      "expected_risk_reduction": 15
    }
  ]
}
```

## Response: 404 Not Found

```json
{
  "error": "VM not found",
  "vm_name": "nonexistent-vm",
  "message": "No VM named 'nonexistent-vm' exists in the discovery dataset. Use GET /api/risk/heatmap to see all available VMs."
}
```
