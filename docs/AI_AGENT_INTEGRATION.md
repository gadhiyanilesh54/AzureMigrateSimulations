# Azure Migrate Simulations — AI Agent Integration Guide

## Multi-Agent Architecture

Azure Migrate Simulations exposes an **MCP (Model Context Protocol) server** that allows
**any AI agent** — GitHub Copilot, Claude Desktop, Cursor, Windsurf, Continue, Cline,
or custom agents — to interact with migration data and iterate on artefacts.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         AI AGENT INTERFACES                             │
│                                                                          │
│  ┌──────────┐ ┌───────────┐ ┌────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ GitHub   │ │  Claude    │ │ Cursor │ │ Windsurf │ │   Custom      │  │
│  │ Copilot  │ │  Desktop   │ │        │ │          │ │   Agent       │  │
│  └────┬─────┘ └─────┬─────┘ └───┬────┘ └────┬─────┘ └──────┬────────┘  │
│       │             │           │            │              │            │
│       ▼             ▼           ▼            ▼              ▼            │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │              MCP (Model Context Protocol)                        │    │
│  │              ┌──────────┐    ┌───────────┐                      │    │
│  │              │  stdio   │    │  SSE/HTTP  │                     │    │
│  │              │ (local)  │    │ (network)  │                     │    │
│  │              └─────┬────┘    └─────┬──────┘                     │    │
│  └────────────────────┼───────────────┼────────────────────────────┘    │
│                       │               │                                  │
│  ┌────────────────────▼───────────────▼────────────────────────────┐    │
│  │         Azure Migrate Simulations MCP Server                    │    │
│  │                                                                  │    │
│  │  22 Tools:                                                      │    │
│  │  ├─ Discovery:  get_migration_summary, list_vms, get_vm_details │    │
│  │  ├─ Workloads:  list_workloads                                  │    │
│  │  ├─ Topology:   generate_cloud_topology, get_topology_waf,      │    │
│  │  │              get_topology_mermaid                             │    │
│  │  ├─ What-If:    simulate_vm_whatif, simulate_fleet               │    │
│  │  ├─ Waves:      get_wave_plan, move_vm_to_wave,                 │    │
│  │  │              update_wave_plan                                 │    │
│  │  ├─ Overrides:  save_whatif_override, clear_whatif_overrides     │    │
│  │  ├─ Catalog:    get_sku_catalog, get_regions                    │    │
│  │  ├─ Business:   get_business_case                               │    │
│  │  ├─ Enrichment: get_enrichment_status                           │    │
│  │  ├─ Security:   get_vulnerability_sla                           │    │
│  │  └─ Export:     export_assessment_csv                            │    │
│  │                                                                  │    │
│  │  Resources:                                                     │    │
│  │  ├─ ams://data/vcenter_discovery.json                           │    │
│  │  ├─ ams://data/workload_discovery.json                          │    │
│  │  ├─ ams://data/enrichment_data.json                             │    │
│  │  └─ ams://data/*.json                                           │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                       │                                                  │
│  ┌────────────────────▼─────────────────────────────────────────────┐    │
│  │              Data Layer (JSON files in data/)                    │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Setup per Agent

### 1. GitHub Copilot (VS Code)

The MCP configuration is already in `.vscode/mcp.json`. Just:

```bash
pip install -e ".[mcp]"
```

Then in VS Code, Copilot will auto-discover the MCP server. You can ask:

> "Show me the migration summary"
> "Generate a cloud topology with firewall and bastion enabled"
> "Move WebServer01 to wave 2"
> "What's the WAF score for the database VMs?"

### 2. Claude Desktop

Add to `claude_desktop_config.json` (on Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "azure-migrate-simulations": {
      "command": "python",
      "args": ["-m", "azure_migrate_simulations.mcp_server"],
      "cwd": "C:\\path\\to\\AzureMigrateSimulations",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\AzureMigrateSimulations\\src"
      }
    }
  }
}
```

### 3. Cursor

Add to `.cursor/mcp.json` in the project root:

```json
{
  "mcpServers": {
    "azure-migrate-simulations": {
      "command": "python",
      "args": ["-m", "azure_migrate_simulations.mcp_server"],
      "env": {
        "PYTHONPATH": "./src"
      }
    }
  }
}
```

### 4. Windsurf

Add to Windsurf MCP settings:

```json
{
  "mcpServers": {
    "azure-migrate-simulations": {
      "command": "python",
      "args": ["-m", "azure_migrate_simulations.mcp_server"],
      "cwd": "/path/to/AzureMigrateSimulations",
      "env": {
        "PYTHONPATH": "./src"
      }
    }
  }
}
```

### 5. Continue (VS Code / JetBrains)

Add to `~/.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "python",
          "args": ["-m", "azure_migrate_simulations.mcp_server"],
          "env": {
            "PYTHONPATH": "./src"
          }
        }
      }
    ]
  }
}
```

### 6. SSE Mode (for network/remote agents)

For agents that connect over HTTP (custom agents, partner agents):

```bash
pip install -e ".[mcp-sse]"
dt-migrate-mcp --sse
# Starts on http://localhost:3001
```

Configure agent to connect:
```json
{
  "mcpServers": {
    "azure-migrate-simulations": {
      "transport": "sse",
      "url": "http://localhost:3001/sse"
    }
  }
}
```

### 7. Custom Agent (Python SDK)

```python
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    server = StdioServerParameters(
        command="python",
        args=["-m", "azure_migrate_simulations.mcp_server"],
        env={"PYTHONPATH": "./src"},
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available: {[t.name for t in tools.tools]}")

            # Get migration summary
            result = await session.call_tool("get_migration_summary", {})
            print(result.content[0].text)

            # Generate cloud topology
            topology = await session.call_tool("generate_cloud_topology", {
                "region": "westeurope",
                "firewall": True,
                "bastion": True,
            })
            print(topology.content[0].text)

            # Move VM to different wave
            await session.call_tool("move_vm_to_wave", {
                "vm_name": "WebServer01",
                "target_wave": 2,
            })
```

---

## Conversation Examples

### Example 1: Iterating on Cloud Topology

```
Customer: "Generate an Azure architecture for my estate"

Agent calls: generate_cloud_topology(region="eastus")
Agent: "I've generated a topology with 3 landing zones, 202 resources.
        Total cost: $45,230/mo. WAF scores: Reliability 38, Security 55..."

Customer: "Add a firewall and bastion for security"

Agent calls: generate_cloud_topology(region="eastus", firewall=True, bastion=True)
Agent: "Updated — added Azure Firewall ($912/mo) and Bastion ($139/mo).
        New total: $46,281/mo. Security WAF score improved."

Customer: "What about West Europe instead?"

Agent calls: generate_cloud_topology(region="westeurope", firewall=True, bastion=True)
Agent: "West Europe is 15% more expensive: $53,223/mo.
        Consider sticking with East US unless data residency requires EU."

Customer: "Show me the Mermaid diagram"

Agent calls: get_topology_mermaid()
Agent: "Here's the Mermaid diagram you can paste into your documentation..."
```

### Example 2: Wave Plan Optimization

```
Customer: "Create a 6-wave migration plan"

Agent calls: simulate_fleet(region="eastus", pricing_model="3yr_ri", wave_count=6)
Agent: "Created 6-wave plan. Wave 1: 34 VMs ($7,200/mo), Wave 2: 34 VMs..."

Customer: "Move all database VMs to wave 1 — they need to go first"

Agent calls: list_vms(filter_name="db")
Agent: "Found DB-01, DB-02, DB-03. Moving them..."
Agent calls: update_wave_plan(assignments=[
  {"vm_name": "DB-01", "target_wave": 1},
  {"vm_name": "DB-02", "target_wave": 1},
  {"vm_name": "DB-03", "target_wave": 1}
])
Agent: "Done. Wave 1 now has 37 VMs including all database servers."

Customer: "What's the cost if we use 3-year reserved instances?"

Agent calls: simulate_fleet(region="eastus", pricing_model="3yr_ri", wave_count=6)
Agent: "With 3yr RI: $18,092/mo (60% savings vs PAYG)."
```

### Example 3: Right-Sizing Iteration

```
Customer: "WebServer01 seems oversized — what are my options?"

Agent calls: get_vm_details(vm_name="WebServer01")
Agent: "WebServer01: 8 vCPUs, 32 GB RAM. Current SKU: Standard_D8s_v5 ($365/mo).
        CPU P95: 12%, Memory P95: 45%. This VM is CPU-underutilized."

Agent calls: simulate_vm_whatif(vm_name="WebServer01", sku_override="Standard_D4s_v5")
Agent: "Downsizing to D4s_v5 (4 vCPUs, 16 GB): $182/mo — saves $183/mo.
        But memory P95 is 45% of 32 GB = 14.4 GB. D4s_v5 has 16 GB — tight fit."

Agent calls: simulate_vm_whatif(vm_name="WebServer01", sku_override="Standard_E4s_v5")
Agent: "E4s_v5 (4 vCPUs, 32 GB): $210/mo — saves $155/mo with same memory.
        Better fit for memory-intensive workloads."

Customer: "Go with E4s_v5"

Agent calls: save_whatif_override(vm_name="WebServer01", sku="Standard_E4s_v5")
Agent: "Saved. WebServer01 will use Standard_E4s_v5 in all future simulations."
```

---

## Partner Agent Integration

Partners (TCS, Infosys, etc.) can run the MCP server in SSE mode on their infrastructure
and connect their own automation agents:

```bash
# On partner infrastructure
MCP_PORT=3001 dt-migrate-mcp --sse

# Partner's agent connects via SSE
```

Or embed the MCP server in their CI/CD pipeline:

```yaml
# GitHub Actions / Azure DevOps Pipeline
steps:
  - name: Generate Migration Artefacts
    run: |
      pip install azure-migrate-simulations[mcp]
      python -c "
      import asyncio
      from mcp import ClientSession
      from mcp.client.stdio import stdio_client, StdioServerParameters

      async def generate():
          server = StdioServerParameters(
              command='dt-migrate-mcp',
              env={'PYTHONPATH': './src'},
          )
          async with stdio_client(server) as (r, w):
              async with ClientSession(r, w) as s:
                  await s.initialize()
                  # Generate topology
                  await s.call_tool('generate_cloud_topology', {
                      'region': 'eastus', 'firewall': True, 'bastion': True
                  })
                  # Export CSV
                  result = await s.call_tool('export_assessment_csv', {'export_type': 'vms'})
                  with open('assessment.csv', 'w') as f:
                      f.write(result.content[0].text)

      asyncio.run(generate())
      "
```

---

## Why MCP?

| Approach | Pros | Cons |
|----------|------|------|
| **REST API only** | Simple, well-understood | Each agent needs custom integration code; no tool discovery |
| **Custom plugin per agent** | Deep integration | N plugins to maintain (Copilot, Claude, Cursor, ...) |
| **MCP (chosen)** | Single implementation, universal agent support | Needs MCP SDK (lightweight) |

MCP is the **universal standard** adopted by:
- GitHub Copilot (VS Code, JetBrains)
- Claude Desktop & Claude Code
- Cursor
- Windsurf
- Continue
- Cline
- Amazon Q
- Google Gemini CLI

**One MCP server = all agents supported.**
