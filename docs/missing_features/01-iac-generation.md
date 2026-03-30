# Feature Spec: Terraform / Bicep IaC Generation

**ID**: 01-iac-generation  
**Phase**: PLAN  
**Priority**: Tier 1 — High Impact  
**Status**: Not Started  
**Depends On**: Cloud Topology Diagram (✅ implemented)

## Problem Statement

After generating a Cloud Topology Diagram (CTD) with CAF-aligned landing zones, VNets, subnets, and resource placements, the customer has **no deployable artefact**. They must manually author Terraform or Bicep templates from the diagram — a process that takes weeks and is error-prone. Azure Migrate (SaaS) also does not generate IaC.

## Goal

Generate deployment-ready **Terraform modules** and **Bicep templates** directly from the CTD output. The generated code should be modular, parameterised, and follow CAF naming conventions — ready for `terraform plan` or `az deployment` with zero hand-editing for basic scenarios.

## Existing Data Available

All prerequisite data already exists in the CTD output (`_last_topology.json`):
- Landing zones (Connectivity, Identity, Management, App-LZ-Production, App-LZ-Dev/Test)
- VNets with CIDR ranges (hub: `10.0.0.0/16`, spokes: `10.1.0.0/16`+)
- Subnets per workload type (database, webapp, container, orchestrator, general_compute)
- Resource placements: VM SKU, disk recommendations, PaaS service mappings
- Optional components: Firewall, Bastion, LB, VPN Gateway (with costs)
- Dependencies: TCP edges (source → dest, port, protocol)
- WAF scores per resource

Additionally from discovery data:
- OS type per VM (Windows/Linux) → `azurerm_windows_virtual_machine` vs `azurerm_linux_virtual_machine`
- Disk count and IOPS → managed disk configuration
- Network info (IPs, NICs) → NIC and NSG configuration

## User Stories

### US-1: Generate Terraform from CTD (P1)
**Given** a generated Cloud Topology Diagram, **When** the user clicks "Export Terraform" or calls `POST /api/export/terraform`, **Then** a downloadable ZIP containing modular `.tf` files is produced with:
- `main.tf` — provider configuration and module calls
- `variables.tf` — all configurable parameters
- `outputs.tf` — resource IDs, IPs, connection strings
- `terraform.tfvars.example` — sample values
- `modules/connectivity/` — hub VNet, firewall, bastion, VPN
- `modules/landing-zone/` — reusable app LZ (VNet, subnets, NSGs)
- `modules/vm/` — VM + disks + NIC + NSG rules
- `environments/production.tfvars`, `environments/devtest.tfvars`

### US-2: Generate Bicep from CTD (P1)
**Given** a generated Cloud Topology Diagram, **When** the user clicks "Export Bicep" or calls `POST /api/export/bicep`, **Then** a downloadable ZIP containing modular `.bicep` files is produced with:
- `main.bicep` — orchestrator with module references
- `parameters.json` — default parameter values
- `modules/connectivity.bicep` — hub VNet + optional components
- `modules/landingZone.bicep` — app LZ template
- `modules/vm.bicep` — VM + disks + NIC
- `environments/production.bicepparam`, `environments/devtest.bicepparam`

### US-3: NSG Rules from Dependencies (P2)
**Given** discovered TCP dependencies between VMs, **When** IaC is generated, **Then** NSG allow rules are auto-generated for each dependency edge (source subnet → dest subnet, port, protocol).

### US-4: CAF Naming Convention (P2)
**Given** generated resources, **When** IaC is produced, **Then** all resource names follow CAF convention: `<type>-<workload>-<env>-<region>-<instance>` (e.g., `rg-contoso-prod-eastus-001`, `vnet-hub-prod-eastus-001`).

### US-5: Tags from Discovery Metadata (P2)
**Given** vCenter folder, cluster, and annotation data, **When** IaC is generated, **Then** Azure tags are auto-applied: `Environment`, `SourceVM`, `MigrationWave`, `WorkloadType`, `CostCenter`.

### US-6: MCP Tool Integration (P1)
**Given** the MCP server is running, **When** an agent calls `generate_terraform` or `generate_bicep`, **Then** the IaC is generated and returned as structured content that the agent can present to the user.

## Functional Requirements

- **FR-001**: Generate syntactically valid Terraform (HCL) that passes `terraform validate`.
- **FR-002**: Generate syntactically valid Bicep that passes `az bicep build`.
- **FR-003**: Use Terraform modules for reusable components (one module per resource type).
- **FR-004**: Use Bicep modules for reusable components.
- **FR-005**: Parameterise all environment-specific values (region, naming prefix, address spaces).
- **FR-006**: Generate NSG rules from discovered TCP dependencies.
- **FR-007**: Apply CAF naming conventions to all resources.
- **FR-008**: Include conditional resource creation for optional components (firewall, bastion, etc.).
- **FR-009**: Generate separate `.tfvars` / `.bicepparam` files per environment (prod, devtest).
- **FR-010**: Add REST API endpoints: `POST /api/export/terraform`, `POST /api/export/bicep`.
- **FR-011**: Add MCP tools: `generate_terraform`, `generate_bicep`.
- **FR-012**: Add web UI export buttons in the Cloud Topology tab.

## Technical Approach

### New Module: `src/azure_migrate_simulations/iac_generator.py`

```python
def generate_terraform(topology: dict, options: IaCOptions) -> dict[str, str]:
    """Returns {filename: content} dict of all .tf files."""

def generate_bicep(topology: dict, options: IaCOptions) -> dict[str, str]:
    """Returns {filename: content} dict of all .bicep files."""

@dataclass
class IaCOptions:
    naming_prefix: str = "contoso"
    environment: str = "prod"
    region: str = "eastus"
    backend: str = "local"  # or "azurerm" for remote state
    include_nsg_rules: bool = True
    include_tags: bool = True
    tag_overrides: dict[str, str] | None = None
```

### Template Approach
Use Python string templates (not Jinja2 — avoid new dependency) with the topology data to generate HCL/Bicep. Each resource type has a template function.

## Acceptance Criteria

1. Generated Terraform passes `terraform validate` with no errors.
2. Generated Bicep passes `az bicep build` with no errors.
3. Generated code creates the same architecture shown in the CTD.
4. NSG rules match discovered TCP dependencies.
5. Resource names follow CAF convention.
6. Tags include source VM name, migration wave, workload type.
7. MCP tools return downloadable IaC bundles.
8. Web UI shows export buttons in Cloud Topology tab.

## Out of Scope (v1)

- ARM template generation (Terraform + Bicep cover all scenarios)
- Pulumi generation
- State migration between backends
- Module registry publishing
- CI/CD pipeline generation (future feature)

## Estimated Scope

- New file: `iac_generator.py` (~800-1200 lines)
- Updates: `web/app.py` (2 new endpoints), `mcp_server.py` (2 new tools), `web/templates/index.html` (2 buttons)
- Test file: `tests/test_iac_generator.py`
