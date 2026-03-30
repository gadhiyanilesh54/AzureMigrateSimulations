# Azure Migrate Simulations — Product Story

## The Offline Migration Intelligence Platform

**Tagline**: *Discover, Assess, Simulate, Architect, and Deploy — entirely from the customer's environment, without a single byte leaving the network.*

---

## 1. The Problem

Enterprises migrating VMware estates to Azure face a paradox:

| Challenge | Azure Migrate (SaaS) | Reality on the Ground |
|-----------|----------------------|----------------------|
| **Data sovereignty** | Discovery data uploaded to Azure | Regulated industries (banking, defence, healthcare) prohibit data egress before migration approval |
| **Network dependency** | Requires persistent Azure connectivity | Many data centres have air-gapped or restricted networks |
| **What-if agility** | Limited scenario modelling | Migration architects need to model 50+ scenarios before presenting to a steering committee |
| **Workload depth** | VM-level discovery only | Real migrations need database, web app, container, and orchestrator awareness |
| **Template generation** | None — manual IaC authoring | Landing zone Terraform/Bicep must be hand-built after assessment |
| **Validation** | Manual runbook creation | No automated pre-flight checks or execution runbooks |
| **Partner customisation** | Locked SaaS — no API for resellers | TCS, Infosys, Wipro, Accenture build bespoke tooling per engagement |
| **Enrichment** | vCenter perf counters only | Customers already have Dynatrace, New Relic, Datadog — that data is wasted |

**Azure Migrate Simulations** solves every one of these.

---

## 2. Product Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CUSTOMER'S DATA CENTRE (AIR-GAPPED)                     │
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ vCenter  │    │ Dynatrace│    │ New Relic│    │ Datadog  │              │
│  │ vSphere  │    │  Export  │    │  Export  │    │  Export  │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │               │                     │
│       ▼               ▼               ▼               ▼                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │          AZURE MIGRATE SIMULATIONS (localhost:5000)                 │    │
│  │                                                                     │    │
│  │  Discovery ──► Assessment ──► What-If ──► Wave Planning            │    │
│  │      │              │             │             │                    │    │
│  │      ▼              ▼             ▼             ▼                    │    │
│  │  Enrichment    Business Case   Simulation   Cloud Topology          │    │
│  │      │              │             │         Diagram (CTD)           │    │
│  │      │              │             │             │                    │    │
│  │      │              │             │             ▼                    │    │
│  │      │              │             │      ┌──────────────┐           │    │
│  │      │              │             │      │  Terraform/  │           │    │
│  │      │              │             │      │  Bicep Gen   │  ◄─ NEW  │    │
│  │      │              │             │      ├──────────────┤           │    │
│  │      │              │             │      │  Validation  │           │    │
│  │      │              │             │      │  Runbooks    │  ◄─ NEW  │    │
│  │      │              │             │      └──────────────┘           │    │
│  │                                                                     │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │  Partner API Layer (REST + Token Auth)              ◄─ NEW │    │    │
│  │  │  /api/v1/partner/* — reseller-scoped endpoints             │    │    │
│  │  │  Agent/Token authentication for TCS, Infosys, etc.         │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│                    ZERO DATA LEAVES THIS BOX                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. End-to-End Journey — The 10-Stage Pipeline

### Stage 1: Offline Discovery

**What it does**: Connects to vCenter via pyVmomi or accepts a JSON upload. Discovers datacentres, clusters, hosts, VMs (202 in sample), datastores, networks — with per-VM metrics (CPU, memory, disk IOPS, network I/O, snapshots, NUMA topology, boot type).

**Differentiation from Azure Migrate**:
- Works in **air-gapped environments** — no Azure subscription required for discovery
- Accepts **pre-exported JSON** — a consultant can carry a USB drive into a classified environment
- Captures **hardware version, NUMA, CPU/memory shares** — data Azure Migrate ignores
- **Zero appliance deployment** — no VM to deploy inside vCenter; runs from a laptop

**Existing**: ✅ Fully implemented (`vcenter_discovery.py`, `models.py`)

---

### Stage 2: Guest-Level Workload Discovery

**What it does**: SSH into Linux, WinRM into Windows — discovers databases (SQL Server, MySQL, PostgreSQL, Oracle, MongoDB, Redis, MariaDB), web apps (.NET, Java, Node.js, Python, PHP, Ruby, Go), container runtimes (Docker, containerd, Podman, CRI-O), and orchestrators (Kubernetes, Docker Swarm, OpenShift, Nomad). Maps listening ports and TCP connections to build a dependency graph.

**Differentiation**:
- **7 database engines** vs Azure Migrate's SQL-only focus
- **8 web app runtimes** with framework detection
- **4 container runtimes** + orchestrator role detection
- **Dependency graph from TCP connections** — not just port scanning but actual established connection mapping

**Existing**: ✅ Fully implemented (`guest_discovery.py`, `models_workload.py`)

---

### Stage 3: Assessment & Right-Sizing

**What it does**: Maps every VM to an Azure SKU from a catalogue of 70+ SKUs across 10+ families (B/D/E/F/M/N/L/A/HB/HC/DC). Uses P95 percentile-based right-sizing when performance data is available. Checks OS lifecycle (Windows Server 2008→2025, RHEL, Ubuntu, CentOS, SLES, Debian, Oracle Linux), detects AHUB eligibility, and calculates migration readiness (Ready / Ready with Conditions / Not Ready).

**Differentiation**:
- **6 pricing models** compared simultaneously: PAYG, 1yr RI, 3yr RI, 1yr SP, 3yr SP, AHUB, Dev/Test
- **Confidence scoring** (50–100) that improves with enrichment data
- **Per-disk recommendations** (HDD / SSD / Premium SSD / Ultra based on IOPS)
- **24 workload migration playbooks** — step-by-step guidance for each DB/webapp → Azure PaaS mapping

**Existing**: ✅ Fully implemented (`azure_mapping.py`, `workload_mapping.py`, `vulnerability_sla.py`)

---

### Stage 4: Enrichment Data Loop

**What it does**: Ingests telemetry exports from **8 APM tools** — Dynatrace, New Relic, Datadog, Splunk, Prometheus, AppDynamics, Zabbix, and custom format. Fuzzy-matches entities to discovered VMs. Extracts CPU%, memory%, IOPS, network, response time, error rate, dependencies. Boosts assessment confidence by up to +30 points using a weighted formula.

**Differentiation**:
- Azure Migrate uses **vCenter perf counters only** — this ingests the monitoring tools customers already own
- **Fuzzy matching** (exact → case-insensitive → FQDN prefix → substring) bridges naming gaps
- **Application-level metrics** (response time, error rate, request rate) that vCenter cannot provide
- Confidence scores directly improve right-sizing accuracy

**Existing**: ✅ Fully implemented (`enrichment.py`, `perf_aggregator.py`)

---

### Stage 5: What-If Analysis & Simulation

**What it does**: Per-VM and per-workload interactive modelling — override SKU, region, pricing model, see cost impact instantly. Fleet-wide simulation with 12-month projection. Drag-and-drop wave planning with auto-distribution.

**Differentiation**:
- **Per-VM granularity** — not just fleet average
- **Live Azure Retail Pricing API** with 6-hour cache + static fallback for offline
- **Wave planning** with drag-and-drop reassignment
- **Saved scenarios** — persist overrides, compare versions

**Existing**: ✅ Fully implemented (web dashboard, `/api/simulate_vm`, `/api/simulate`)

---

### Stage 6: Wave Planning

**What it does**: Groups VMs into migration waves based on dependencies, workload type, and criticality. Auto-distributes VMs evenly across configurable wave count. Supports manual override via drag-and-drop. Generates 12-month cumulative cost projection showing on-prem rundown and Azure ramp-up.

**Differentiation**:
- **Dependency-aware wave assignment** — databases before web servers, shared services first
- **Interactive drag-and-drop** — move VMs between waves in the UI
- **12-month financial projection** per wave
- Azure Migrate has no concept of wave planning

**Existing**: ✅ Partially implemented (fleet simulation with waves, manual drag-and-drop)

---

### Stage 7: Cloud Topology Diagram (CTD)

**What it does**: Translates the entire assessed estate into a CAF-aligned Azure landing zone architecture. Generates:
- **Platform landing zones**: Connectivity (hub VNet, firewall, bastion, VPN), Identity, Management
- **Application landing zones**: Production, Dev/Test, Requires Attention
- **Hub-spoke network**: VNets with subnets grouped by workload type
- **WAF scoring**: 5 pillars (Reliability, Security, Cost, Operational Excellence, Performance) per resource
- **Interactive diagram**: vis-network canvas with zoom, pan, click-through to WAF panel

**Differentiation**:
- Azure Migrate produces **no architecture diagram**
- **CAF landing zone structure** is automatically derived, not manually drawn
- **WAF scores from discovered data** — no Azure Advisor required
- **Toggle optional components** (Firewall $912/mo, Bastion $139/mo, LB $18/mo, VPN $138/mo)
- Export: PNG, JSON, Mermaid

**Existing**: ✅ Fully implemented (`cloud_topology.py`, web dashboard Cloud Topology tab)

---

### Stage 8: Terraform / Bicep Template Generation 🆕

**What it does**: Takes the Cloud Topology Diagram output and generates deployment-ready IaC templates:

#### Terraform Output
```
generated/terraform/
├── main.tf                    # Provider config, backend
├── variables.tf               # Parameterised inputs
├── outputs.tf                 # Resource IDs, IPs, connection strings
├── terraform.tfvars.example   # Sample variable values
├── modules/
│   ├── connectivity/          # Hub VNet, firewall, bastion, VPN
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── landing-zone/          # Reusable app LZ module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── vm/                    # Azure VM with managed disks
│   ├── sql-database/          # Azure SQL DB / MI
│   ├── app-service/           # App Service Plan + Web App
│   ├── container-apps/        # Container Apps environment
│   └── networking/            # NSGs, route tables, peering
└── environments/
    ├── production.tfvars
    └── devtest.tfvars
```

#### Bicep Output
```
generated/bicep/
├── main.bicep                 # Orchestrator
├── parameters.json            # Default parameters
├── modules/
│   ├── connectivity.bicep     # Hub VNet + optional components
│   ├── landingZone.bicep      # Application landing zone
│   ├── vm.bicep               # VM + disks + NIC + NSG
│   ├── sqlDatabase.bicep      # Azure SQL
│   ├── appService.bicep       # App Service
│   └── networking.bicep       # VNet peering, route tables
└── environments/
    ├── production.bicepparam
    └── devtest.bicepparam
```

#### Key Generation Logic
- **Resource naming**: CAF naming convention (`rg-<workload>-<env>-<region>-001`)
- **Network addressing**: Derived from CTD (`10.0.0.0/16` hub, `10.1.0.0/16`+ spokes)
- **NSG rules**: Generated from discovered dependencies (source → dest, port, protocol)
- **Tags**: Environment, workload type, migration wave, source VM name
- **Conditional resources**: Firewall, bastion, LB, VPN based on user toggles in CTD

**Status**: 🆕 To be implemented — all prerequisite data (CTD, SKUs, network topology, dependencies) exists

---

### Stage 9: Validation Runbooks 🆕

**What it does**: Generates executable validation runbooks for pre-migration checks, migration execution, and post-migration verification.

#### Pre-Migration Runbook
```yaml
runbook: pre-migration-validation
version: 1.0
generated_from: cloud-topology-<timestamp>
waves:
  - wave: 1
    name: "Foundation & Shared Services"
    checks:
      - id: PRE-001
        name: "Azure subscription quota check"
        type: automated
        command: |
          az vm list-usage --location eastus --output table
          # Verify vCPU quota >= {total_vcpus_wave_1}
        expected: "Available vCPUs >= {required_vcpus}"
        remediation: "az quota request create --resource-name standardDSv5Family ..."

      - id: PRE-002
        name: "Network address space conflict check"
        type: automated
        command: |
          az network vnet list --query "[].addressSpace.addressPrefixes" -o tsv
          # Verify no overlap with {hub_cidr} or {spoke_cidrs}
        expected: "No overlapping address spaces"

      - id: PRE-003
        name: "DNS resolution validation"
        type: manual
        instructions: |
          Verify DNS forwarding configured for:
          {list_of_internal_domains}

      - id: PRE-004
        name: "Source VM snapshot"
        type: automated
        command: |
          # PowerCLI: Create snapshots for wave 1 VMs
          {foreach_vm_in_wave_1}
          New-Snapshot -VM "{vm_name}" -Name "pre-migration" -Memory:$false
        expected: "Snapshot created for all {wave_1_vm_count} VMs"
```

#### Migration Execution Runbook
```yaml
runbook: migration-execution
waves:
  - wave: 1
    steps:
      - step: 1
        name: "Deploy landing zone infrastructure"
        type: automated
        command: |
          cd generated/terraform
          terraform init
          terraform plan -var-file=environments/production.tfvars -out=wave1.tfplan
          terraform apply wave1.tfplan

      - step: 2
        name: "Validate infrastructure deployment"
        type: automated
        command: |
          az resource list --resource-group rg-prod-eastus-001 --output table
          # Verify {expected_resource_count} resources created
        validation:
          - "VNet exists with correct address space"
          - "NSGs applied to subnets"
          - "Route tables configured"

      - step: 3
        name: "Migrate VMs — Wave 1"
        type: semi-automated
        for_each_vm: "{wave_1_vms}"
        instructions: |
          # For each VM in wave 1:
          # 1. Enable replication (Azure Migrate replication appliance)
          # 2. Wait for initial sync
          # 3. Test failover to isolated VNet
          # 4. Validate application connectivity
          # 5. Production failover
```

#### Post-Migration Validation Runbook
```yaml
runbook: post-migration-validation
waves:
  - wave: 1
    checks:
      - id: POST-001
        name: "VM health check"
        type: automated
        command: |
          az vm list --resource-group rg-prod-eastus-001 \
            --query "[].{Name:name, Status:powerState}" -o table
        expected: "All VMs running"

      - id: POST-002
        name: "Application connectivity validation"
        type: automated
        for_each_dependency: "{wave_1_dependencies}"
        command: |
          # From {source_vm}: Test-NetConnection {target_vm} -Port {port}
          az vm run-command invoke --name RunPowerShellScript \
            --resource-group {rg} --vm-name {source_vm} \
            --scripts "Test-NetConnection {target_ip} -Port {port}"

      - id: POST-003
        name: "Performance baseline comparison"
        type: automated
        command: |
          # Compare Azure Monitor metrics against on-prem baselines
          az monitor metrics list --resource {vm_resource_id} \
            --metric "Percentage CPU" --interval PT1H
          # Expected: CPU% within 20% of on-prem P95 ({onprem_p95_cpu}%)

      - id: POST-004
        name: "DNS cutover"
        type: manual
        instructions: |
          Update DNS records for:
          {list_of_dns_records_to_update}
          TTL: Set to 300s during migration, revert to 3600s after 48h
```

**Status**: 🆕 To be implemented — all prerequisite data (waves, VMs, dependencies, perf baselines, network topology) exists

---

### Stage 10: Business Case & Executive Reporting

**What it does**: Generates a comprehensive on-prem TCO vs Azure cost comparison with 15+ cost categories, ROI calculation, payback period analysis, and strategic recommendations.

**Existing**: ✅ Fully implemented (web dashboard Business Case tab)

---

## 4. Differentiation Matrix: Azure Migrate vs Azure Migrate Simulations

| Capability | Azure Migrate (SaaS) | Azure Migrate Simulations (Offline) |
|------------|---------------------|-------------------------------------|
| **Deployment model** | Cloud SaaS — requires Azure subscription | Self-hosted — runs on `localhost:5000` |
| **Data residency** | Data uploaded to Azure | Zero data egress — runs entirely on-prem |
| **Air-gap support** | ❌ Requires internet | ✅ Full offline operation |
| **Appliance required** | Yes — deploy VM in vCenter | No — runs from any machine with Python |
| **Discovery depth** | VM-level only | VM + guest workloads (7 DBs, 8 webapps, 4 containers, orchestrators) |
| **Dependency mapping** | Agent-based (requires endpoint agent install) | Agentless — SSH/WinRM probing of TCP connections |
| **Enrichment** | vCenter perf counters only | 8 APM tools (Dynatrace, New Relic, Datadog, Splunk, Prometheus, AppDynamics, Zabbix, Custom) |
| **What-if modelling** | Limited | Per-VM + per-workload + fleet-wide with drag-and-drop waves |
| **Pricing models** | PAYG + RI | PAYG, 1yr RI, 3yr RI, 1yr SP, 3yr SP, AHUB, Dev/Test, EA |
| **Wave planning** | ❌ | ✅ Auto-distribution + manual drag-and-drop + 12-month projection |
| **Cloud topology diagram** | ❌ | ✅ CAF landing zones + WAF scoring + interactive vis-network |
| **Terraform/Bicep generation** | ❌ | ✅ Module-based IaC from assessed topology (planned) |
| **Validation runbooks** | ❌ | ✅ Pre/during/post migration runbooks (planned) |
| **Business case** | Basic cost estimate | Full TCO with 15+ categories, ROI, payback, strategic recommendations |
| **API for partners** | ❌ Limited | ✅ 60+ REST endpoints + partner API layer (planned) |
| **Partner customisation** | ❌ Locked SaaS | ✅ Open architecture — resellers build on top |
| **Authentication** | Azure AD only | API key + partner token + agent-based auth |
| **Cost** | Azure subscription billing | Free — self-hosted |

---

## 5. Partner & Reseller API Strategy

### The Opportunity

Microsoft's reseller ecosystem (TCS, Infosys, Wipro, Accenture, HCL, Cognizant, Tech Mahindra, Capgemini, DXC, NTT) collectively manages **thousands of migration engagements per year**. Each builds bespoke tooling per engagement. Azure Migrate Simulations becomes their **shared platform**.

### Architecture: Partner API Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PARTNER / RESELLER                              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ TCS Migration│  │ Infosys Cloud│  │ Accenture Migration      │  │
│  │ Accelerator  │  │ Planner Pro  │  │ Workbench                │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
│         │                 │                      │                   │
│         ▼                 ▼                      ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Partner API Gateway                            │    │
│  │                                                             │    │
│  │  Authentication:                                            │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │ Option A: API Key (X-API-Key header)                │   │    │
│  │  │ Option B: Partner Token (JWT, scoped to partner ID) │   │    │
│  │  │ Option C: Agent Certificate (mTLS for automation)   │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                             │    │
│  │  Rate Limiting: per-partner quotas                         │    │
│  │  Audit Logging: every API call logged with partner ID      │    │
│  │  Tenant Isolation: partner sees only their projects        │    │
│  └─────────────────────────────────────────┬───────────────────┘    │
│                                             │                       │
│  ┌──────────────────────────────────────────▼───────────────────┐   │
│  │              Core Engine (existing 60+ endpoints)            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Partner API Endpoints

#### Project Management
```
POST   /api/v1/partner/projects                      # Create migration project
GET    /api/v1/partner/projects                      # List partner's projects
GET    /api/v1/partner/projects/{id}                 # Get project details
DELETE /api/v1/partner/projects/{id}                 # Archive project
```

#### Discovery (scoped to project)
```
POST   /api/v1/partner/projects/{id}/discovery/upload     # Upload vCenter JSON
POST   /api/v1/partner/projects/{id}/discovery/connect    # Live vCenter connect
GET    /api/v1/partner/projects/{id}/discovery/status      # Discovery status
GET    /api/v1/partner/projects/{id}/inventory             # All discovered resources
```

#### Enrichment
```
POST   /api/v1/partner/projects/{id}/enrichment/upload     # Upload APM data
GET    /api/v1/partner/projects/{id}/enrichment/coverage   # Coverage report
```

#### Assessment
```
POST   /api/v1/partner/projects/{id}/assessment/generate   # Generate recommendations
GET    /api/v1/partner/projects/{id}/assessment/vms         # VM assessment results
GET    /api/v1/partner/projects/{id}/assessment/workloads   # Workload assessment
GET    /api/v1/partner/projects/{id}/assessment/readiness   # Migration readiness summary
```

#### What-If & Simulation
```
POST   /api/v1/partner/projects/{id}/whatif/vm              # Single VM what-if
POST   /api/v1/partner/projects/{id}/whatif/workload        # Single workload what-if
POST   /api/v1/partner/projects/{id}/simulation/fleet       # Fleet simulation
POST   /api/v1/partner/projects/{id}/simulation/waves       # Wave planning
```

#### Cloud Topology Diagram
```
POST   /api/v1/partner/projects/{id}/topology/generate      # Generate CTD
GET    /api/v1/partner/projects/{id}/topology               # Get CTD data
GET    /api/v1/partner/projects/{id}/topology/waf/{res_id}  # WAF for resource
POST   /api/v1/partner/projects/{id}/topology/customise     # Modify CTD
GET    /api/v1/partner/projects/{id}/topology/export/json   # Export JSON
GET    /api/v1/partner/projects/{id}/topology/export/png    # Export PNG
GET    /api/v1/partner/projects/{id}/topology/export/mermaid # Export Mermaid
```

#### IaC Generation 🆕
```
POST   /api/v1/partner/projects/{id}/iac/terraform          # Generate Terraform
POST   /api/v1/partner/projects/{id}/iac/bicep              # Generate Bicep
GET    /api/v1/partner/projects/{id}/iac/terraform/download  # Download .tf bundle
GET    /api/v1/partner/projects/{id}/iac/bicep/download      # Download .bicep bundle
POST   /api/v1/partner/projects/{id}/iac/validate            # Validate generated IaC
```

#### Runbooks 🆕
```
POST   /api/v1/partner/projects/{id}/runbooks/generate       # Generate all runbooks
GET    /api/v1/partner/projects/{id}/runbooks/pre-migration   # Pre-migration checks
GET    /api/v1/partner/projects/{id}/runbooks/execution       # Migration execution
GET    /api/v1/partner/projects/{id}/runbooks/post-migration  # Post-migration validation
POST   /api/v1/partner/projects/{id}/runbooks/execute/{step}  # Execute a runbook step
GET    /api/v1/partner/projects/{id}/runbooks/status          # Execution status
```

#### Business Case & Reporting
```
GET    /api/v1/partner/projects/{id}/business-case            # Full business case
GET    /api/v1/partner/projects/{id}/reports/executive-summary # Executive PDF data
GET    /api/v1/partner/projects/{id}/reports/csv/vm-assessment # CSV export
GET    /api/v1/partner/projects/{id}/reports/csv/workloads     # CSV export
```

### Authentication Model

#### Option A: API Key (Simple — for single-tenant deployments)
```http
GET /api/v1/partner/projects HTTP/1.1
Host: localhost:5000
X-API-Key: ams_pk_TCS_2026_a1b2c3d4e5f6
X-Partner-ID: tcs-migration-team
```

#### Option B: JWT Partner Token (Multi-tenant — for shared deployments)
```http
POST /api/v1/auth/token HTTP/1.1
Content-Type: application/json

{
  "partner_id": "tcs-migration-team",
  "client_secret": "...",
  "scope": ["discovery", "assessment", "topology", "iac"]
}

# Response:
{
  "access_token": "eyJhbGciOi...",
  "expires_in": 3600,
  "scope": ["discovery", "assessment", "topology", "iac"],
  "partner_id": "tcs-migration-team"
}
```

Then use:
```http
GET /api/v1/partner/projects HTTP/1.1
Authorization: Bearer eyJhbGciOi...
```

#### Option C: Agent Certificate (mTLS — for automated pipelines)
```yaml
# Partner deploys an agent in their CI/CD pipeline
agent:
  name: "tcs-migration-agent"
  certificate: "/certs/tcs-agent.pem"
  key: "/certs/tcs-agent-key.pem"
  ca: "/certs/ams-ca.pem"
  endpoint: "https://ams.customer-dc.local:5000"
  scopes:
    - discovery
    - assessment
    - topology
    - iac
    - runbooks
```

### How Partners Use Their Own Agents/Tokens

```
┌─────────────────────────────────────────────────────────────────────┐
│  TCS Example: "TCS Cloud Migration Factory"                        │
│                                                                     │
│  1. TCS registers as partner:                                       │
│     POST /api/v1/admin/partners                                    │
│     { "name": "TCS", "contact": "...", "scopes": ["*"] }          │
│     → Returns: partner_id + client_secret                          │
│                                                                     │
│  2. TCS obtains token:                                              │
│     POST /api/v1/auth/token                                       │
│     → Returns: JWT with partner_id claim                           │
│                                                                     │
│  3. TCS creates project per customer:                               │
│     POST /api/v1/partner/projects                                  │
│     { "name": "Contoso Bank Migration", "customer": "contoso" }    │
│     → Returns: project_id (tenant-isolated)                        │
│                                                                     │
│  4. TCS uploads discovery (from customer's vCenter export):         │
│     POST /api/v1/partner/projects/{id}/discovery/upload            │
│     Body: vcenter_discovery.json                                    │
│                                                                     │
│  5. TCS generates CTD:                                              │
│     POST /api/v1/partner/projects/{id}/topology/generate           │
│     → Returns: CAF-aligned architecture                            │
│                                                                     │
│  6. TCS generates Terraform:                                        │
│     POST /api/v1/partner/projects/{id}/iac/terraform               │
│     → Returns: downloadable .tf module bundle                      │
│                                                                     │
│  7. TCS generates runbooks:                                         │
│     POST /api/v1/partner/projects/{id}/runbooks/generate           │
│     → Returns: pre/during/post migration runbooks                  │
│                                                                     │
│  8. TCS's own agent executes runbook steps:                         │
│     POST /api/v1/partner/projects/{id}/runbooks/execute/PRE-001    │
│     → Agent runs az CLI commands, reports results                  │
│                                                                     │
│  Result: TCS has a fully branded migration report + IaC + runbooks  │
│  that they deliver to Contoso Bank under TCS branding               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Partner Customisation Points

### What Partners Can Build On Top

| Customisation | How | Example |
|---------------|-----|---------|
| **Custom workload detection** | Add detection patterns to guest discovery | TCS adds SAP HANA detection for manufacturing clients |
| **Custom Azure service mappings** | Extend workload mapping playbooks | Infosys adds Azure VMware Solution (AVS) mapping |
| **Custom WAF rules** | Add industry-specific WAF scoring criteria | Wipro adds PCI-DSS compliance scoring for banking |
| **Custom landing zone templates** | Provide pre-built CTD templates | Accenture's "Secure Landing Zone for Financial Services" |
| **Custom runbook steps** | Inject partner-specific validation steps | HCL adds Oracle license compliance checks |
| **Custom enrichment parsers** | Add monitoring tools not yet supported | Cognizant adds ServiceNow CMDB import |
| **Branded reports** | Use API to generate data, render in partner's template | DXC's branded executive migration report |
| **Custom pricing** | Override pricing with customer's EA/CSP rates | NTT applies customer-specific CSP pricing |

### SDK / Client Libraries (planned)

```python
# Python SDK
from ams_sdk import AMSClient

client = AMSClient(
    endpoint="https://ams.customer-dc.local:5000",
    partner_token="eyJhbGciOi..."
)

# Create project
project = client.projects.create(name="Contoso Migration", customer="contoso")

# Upload discovery
project.discovery.upload("vcenter_export.json")

# Upload enrichment
project.enrichment.upload("dynatrace_export.json", tool="dynatrace")

# Generate assessment
assessment = project.assessment.generate(
    region="eastus",
    pricing_model="3yr_ri",
    sizing="performance_p95"
)

# Generate cloud topology
topology = project.topology.generate(
    firewall=True,
    bastion=True,
    vpn_gateway=False
)

# Generate Terraform
tf_bundle = project.iac.terraform(
    backend="azurerm",           # or "local", "s3"
    naming_convention="caf",     # or "custom"
    tag_strategy="auto"          # from discovered metadata
)
tf_bundle.download("./output/terraform/")

# Generate Bicep
bicep_bundle = project.iac.bicep(
    target_scope="subscription",
    parameter_files=True
)
bicep_bundle.download("./output/bicep/")

# Generate runbooks
runbooks = project.runbooks.generate(wave_count=4)
runbooks.download("./output/runbooks/")

# Execute pre-migration checks
for check in runbooks.pre_migration.checks:
    result = check.execute()  # Runs via partner's agent
    print(f"{check.id}: {result.status}")
```

```typescript
// TypeScript SDK
import { AMSClient } from '@azure-migrate-simulations/sdk';

const client = new AMSClient({
  endpoint: 'https://ams.customer-dc.local:5000',
  partnerToken: 'eyJhbGciOi...'
});

const project = await client.projects.create({
  name: 'Contoso Migration',
  customer: 'contoso'
});

const topology = await project.topology.generate({
  firewall: true,
  bastion: true
});

const terraform = await project.iac.terraform({
  backend: 'azurerm'
});

await terraform.download('./output/terraform/');
```

---

## 7. Complete Pipeline — "One Click to Cloud"

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         THE 10-STAGE PIPELINE                                  │
│                                                                                │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │   1.    │   │   2.    │   │   3.    │   │   4.    │   │   5.    │       │
│  │ Offline │──►│ Guest   │──►│ Assess  │──►│ Enrich  │──►│ What-If│       │
│  │Discovery│   │Workload │   │ & Size  │   │  Loop   │   │Analysis│       │
│  │         │   │Discovery│   │         │   │         │   │        │       │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └────┬────┘       │
│                                                                 │            │
│       ┌─────────────────────────────────────────────────────────┘            │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │   6.    │   │   7.    │   │   8.    │   │   9.    │   │  10.   │     │
│  │  Wave   │──►│ Cloud   │──►│Terraform│──►│Validate │──►│Business│     │
│  │Planning │   │Topology │   │/ Bicep  │   │Runbooks │   │  Case  │     │
│  │         │   │ Diagram │   │  Gen    │   │         │   │        │     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘     │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Partner API Layer — Every stage exposed as REST endpoints          │    │
│  │  Token/Agent-authenticated — Multi-tenant — Audit-logged            │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Deployment Models

### Model A: Customer Self-Hosted (Default)
```
Customer DC → pip install azure-migrate-simulations → localhost:5000
```
- Customer runs the tool themselves
- No data leaves the data centre
- Full control over discovery credentials

### Model B: Partner-Hosted (Multi-Tenant)
```
Partner DC → AMS deployed on partner infra → multiple customer projects
```
- Partner (e.g., TCS) hosts AMS centrally
- Each customer = isolated project via Partner API
- Partner manages authentication and access
- Customer discovery data uploaded via secure channel

### Model C: Hybrid (Customer DC + Partner Remote Access)
```
Customer DC → AMS running → Partner accesses via VPN/bastion → Partner API
```
- AMS runs in customer's DC (data sovereignty)
- Partner team accesses via secure remote connection
- Partner uses API tokens for automation
- Audit trail shows all partner actions

### Model D: Container-Based (Portable)
```
docker run -p 5000:5000 -v ./data:/app/data azure-migrate-simulations:latest
```
- Ship as Docker container
- Mount data volume for persistence
- Portable across any environment
- Easy to deploy in Kubernetes for scale

---

## 9. Security & Compliance

| Control | Implementation |
|---------|---------------|
| **Data at rest** | JSON files on local disk — customer controls encryption (BitLocker, LUKS) |
| **Data in transit** | HTTPS (TLS 1.2+) for web interface and API |
| **Authentication** | API key / JWT token / mTLS certificate |
| **Authorisation** | Partner-scoped projects — tenant isolation |
| **Audit logging** | Every API call logged: timestamp, partner ID, action, resource |
| **Credential handling** | vCenter/SSH/WinRM credentials never persisted — held in memory only during discovery |
| **Data residency** | Zero egress — all processing local |
| **Compliance** | Designed for HIPAA, PCI-DSS, ITAR, SOX environments where data cannot leave the network |

---

## 10. Roadmap

### Phase 1: Current State (✅ Delivered)
- Offline vCenter discovery + guest workload discovery
- Azure VM SKU recommendations (70+ SKUs, 6 pricing models)
- Per-VM and per-workload what-if modelling
- Fleet simulation with wave planning
- Enrichment loop (8 APM tools)
- Cloud Topology Diagram (CAF + WAF)
- Business case generation
- Vulnerability & SLA tracking
- 60+ REST API endpoints
- CLI orchestration
- Single-page web dashboard

### Phase 2: IaC & Runbooks (🔄 Next)
- Terraform module generation from CTD
- Bicep template generation from CTD
- Pre-migration validation runbooks
- Migration execution runbooks
- Post-migration validation runbooks
- Runbook execution engine (via partner agent)

### Phase 3: Partner Platform (📋 Planned)
- Partner API layer (`/api/v1/partner/*`)
- JWT token authentication
- Multi-tenant project isolation
- Python & TypeScript SDKs
- Partner registration and management
- Rate limiting and quota management
- Audit logging for compliance
- OpenAPI/Swagger documentation

### Phase 4: Enterprise Features (📋 Planned)
- Azure AD / Entra ID integration (SSO)
- Role-based access control (RBAC)
- Scenario versioning and comparison
- Custom landing zone templates
- Industry-specific WAF rules (PCI-DSS, HIPAA, ITAR)
- Azure VMware Solution (AVS) mapping
- SAP workload detection
- Docker/Kubernetes deployment packaging
- Helm charts for partner-hosted deployments

### Phase 5: Ecosystem (📋 Future)
- Azure DevOps pipeline integration
- GitHub Actions for IaC deployment
- ServiceNow CMDB import/export
- JIRA migration project tracking integration
- Power BI report connector
- ARM template generation (alongside Terraform/Bicep)
- Multi-cloud support (AWS, GCP target mapping)
- AI-powered right-sizing recommendations

---

## 11. The Elevator Pitch

> **Azure Migrate Simulations** is an offline migration intelligence platform that runs entirely in the customer's data centre — no Azure subscription, no data egress, no appliance deployment. It discovers VMware estates at VM and workload depth, assesses them against 70+ Azure SKUs with 6 pricing models, models unlimited what-if scenarios with wave planning, generates CAF-aligned cloud topology diagrams with WAF scoring, produces deployment-ready Terraform and Bicep templates, and creates validated migration runbooks. 
>
> For Microsoft resellers like TCS, Infosys, and Accenture, it exposes a full Partner API with token-based authentication — enabling them to build branded migration factories on top of a shared platform. Every stage of the pipeline — from discovery to deployment — is an API call away.
>
> **Where Azure Migrate requires cloud connectivity and produces assessments, Azure Migrate Simulations works offline and produces deployable infrastructure.**

---

## 12. Competitive Positioning

```
                    Assessment Depth
                         ▲
                         │
                         │  ┌──────────────────────────┐
                         │  │  Azure Migrate            │
                         │  │  Simulations              │
                         │  │  (This Product)           │
                         │  │                          │
                    High │  │  • Offline               │
                         │  │  • VM + Workload depth   │
                         │  │  • IaC generation        │
                         │  │  • Partner API           │
                         │  │  • Runbooks              │
                         │  └──────────────────────────┘
                         │
                         │        ┌───────────────────┐
                    Med  │        │  Azure Migrate     │
                         │        │  (SaaS)            │
                         │        │  • Cloud-hosted    │
                         │        │  • VM-level only   │
                         │        │  • No IaC gen      │
                         │        └───────────────────┘
                         │
                         │  ┌──────────────┐
                    Low  │  │ RVTools /    │
                         │  │ Manual Excel │
                         │  └──────────────┘
                         │
                         └──────────────────────────────────►
                              Offline         Online
                            (Air-Gapped)    (Cloud-Connected)
                                    Deployment Model
```

---

*This document is the product story for Azure Migrate Simulations. It serves as the north star for product development, partner engagement, and sales positioning.*
