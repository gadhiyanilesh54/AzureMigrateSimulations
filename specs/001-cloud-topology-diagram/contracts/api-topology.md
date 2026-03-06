# API Contract: Cloud Topology

**Feature**: `001-cloud-topology-diagram` | **Date**: 2026-03-04

## `GET /api/cloud-topology`

Generate the full Azure architecture topology from discovered data.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `region` | string | `eastus` | Target Azure region (for cost multipliers) |
| `firewall` | bool | `false` | Enable Azure Firewall in Connectivity zone |
| `bastion` | bool | `false` | Enable Azure Bastion in Connectivity zone |
| `load_balancer` | bool | `false` | Enable Standard LB per application landing zone |
| `vpn_gateway` | bool | `false` | Enable VPN Gateway in Connectivity zone |

### Success Response — `200 OK`

```json
{
  "generated_at": "2026-03-04T12:00:00Z",
  "source_vm_count": 202,
  "source_workload_count": 35,
  "total_monthly_cost": 45230.50,

  "containers": [
    {
      "id": "lz-connectivity",
      "label": "Connectivity",
      "type": "landing_zone",
      "parent": null,
      "color": "#0078d4",
      "children": ["vnet-hub"]
    },
    {
      "id": "vnet-hub",
      "label": "hub-vnet (10.0.0.0/16)",
      "type": "vnet",
      "parent": "lz-connectivity",
      "color": "#58a6ff",
      "children": ["sn-gateway", "sn-firewall"]
    },
    {
      "id": "sn-gateway",
      "label": "GatewaySubnet (10.0.0.0/24)",
      "type": "subnet",
      "parent": "vnet-hub",
      "color": "#30363d",
      "children": []
    }
  ],

  "nodes": [
    {
      "id": "res-vm-WindowsVM175",
      "label": "WindowsVM175",
      "group": "vm",
      "title": "WindowsVM175\nSKU: Standard_D4s_v5\nCost: $182/mo\nReady",
      "container": "sn-general-compute-001",
      "resource_type": "vm",
      "source_vm": "WindowsVM175",
      "azure_sku": "Standard_D4s_v5",
      "monthly_cost": 182.0,
      "readiness": "Ready",
      "waf_scores": {
        "reliability": 35,
        "security": 62,
        "cost_optimisation": 55,
        "operational_excellence": null,
        "performance_efficiency": null
      }
    }
  ],

  "edges": [
    {
      "from": "res-vm-web01",
      "to": "res-vm-db01",
      "label": "TCP/3306",
      "dashes": false,
      "arrows": "to",
      "color": "#8b949e"
    }
  ],

  "cost_summary": {
    "by_landing_zone": {
      "lz-connectivity": { "name": "Connectivity", "cost": 912.0 },
      "lz-prod": { "name": "App-LZ-Production", "cost": 38200.50 },
      "lz-devtest": { "name": "App-LZ-Dev/Test", "cost": 6118.00 }
    },
    "total": 45230.50,
    "optional_components_cost": 912.0
  },

  "waf_summary": {
    "scores": {
      "reliability": 38,
      "security": 55,
      "cost_optimisation": 62,
      "operational_excellence": null,
      "performance_efficiency": null
    },
    "resource_count": 202,
    "insufficient_data_count": {
      "reliability": 0,
      "security": 0,
      "cost_optimisation": 0,
      "operational_excellence": 180,
      "performance_efficiency": 195
    }
  },

  "optional_components": [
    {
      "id": "azure_firewall",
      "name": "Azure Firewall Standard",
      "monthly_cost_base": 912.0,
      "enabled": true,
      "landing_zone_id": "lz-connectivity"
    },
    {
      "id": "bastion",
      "name": "Azure Bastion Standard",
      "monthly_cost_base": 139.0,
      "enabled": false,
      "landing_zone_id": "lz-connectivity"
    },
    {
      "id": "load_balancer",
      "name": "Standard Load Balancer",
      "monthly_cost_base": 18.0,
      "enabled": false,
      "landing_zone_id": "lz-prod"
    },
    {
      "id": "vpn_gateway",
      "name": "VPN Gateway (S2S)",
      "monthly_cost_base": 138.0,
      "enabled": false,
      "landing_zone_id": "lz-connectivity"
    }
  ],

  "mermaid": "flowchart TB\n  subgraph LZ1[\"Connectivity\"]\n    ..."
}
```

### Error Response — `404 Not Found`

```json
{ "error": "No discovery data loaded. Connect to vCenter or upload a report." }
```

---

## `GET /api/cloud-topology/waf/<resource_id>`

Get detailed WAF assessment for a single resource.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `resource_id` | string | Cloud resource ID (e.g., `res-vm-WindowsVM175`) |

### Success Response — `200 OK`

```json
{
  "resource_id": "res-vm-WindowsVM175",
  "resource_label": "WindowsVM175",
  "azure_service": "Azure VM",
  "azure_sku": "Standard_D4s_v5",
  "pillars": [
    {
      "pillar": "Reliability",
      "score": 35,
      "status": "scored",
      "data_sources_used": ["vcenter_discovery"],
      "missing_data_prompt": null,
      "recommendations": [
        {
          "title": "Enable Availability Zones",
          "description": "Deploy this VM across availability zones for 99.99% SLA. Current single-instance SLA is 99.9%.",
          "impact": "high",
          "effort": "low"
        },
        {
          "title": "Configure Azure Backup",
          "description": "Enable Azure Backup with a daily policy to protect against data loss.",
          "impact": "high",
          "effort": "low"
        }
      ]
    },
    {
      "pillar": "Performance Efficiency",
      "score": null,
      "status": "insufficient_data",
      "data_sources_used": [],
      "missing_data_prompt": "Run the performance collector (sidebar → Start) to capture CPU, memory, and IOPS metrics for right-sizing validation.",
      "recommendations": []
    }
  ]
}
```

### Error Response — `404 Not Found`

```json
{ "error": "Resource 'res-vm-unknown' not found in the current topology." }
```
