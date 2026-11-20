# Repository Reference — Azure Migrate Container Discovery & Assessment

> Central index of all repositories used for planning, HLD, LLD, and implementation of the Container Assessment feature in Azure Migrate.

---

## 1. Resource Provider & ARM/ARG Onboarding

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-ApplicationMigration** | RPaaS — new resource type registration for containers, ARM & ARG onboarding | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-ApplicationMigration) |
| **AzureMigrate-ResourceProvider** | Microsoft.Migrate resource provider | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-ResourceProvider) |

---

## 2. Discovery — Agents & Service

### 2.1 Container Discovery Agent (new — to be created)

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-WebAppAgent** | Reference implementation — container discovery agent will follow this pattern | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-WebAppAgent) |

### 2.2 Fabric Agents

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-VMwareAgent** | VMware fabric agent | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-VMwareAgent) |
| **AzureMigrate-HyperVAgent** | Hyper-V fabric agent | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-HyperVAgent) |
| **AzureMigrate-ServerAgent** | Bare-metal / physical server agent | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-ServerAgent) |

### 2.3 Agent Core & Common

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrateAgents** | Azure Migrate agent core libraries | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrateAgents) |
| **AzureMigrate-ServiceCommon** | Shared service-common libraries | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-ServiceCommon) |

### 2.4 Appliance & Discovery Service

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-ApplianceComponents** | Appliance agent host / components | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-ApplianceComponents) |
| **AzureMigrate-DiscoveryService** | Discovery service — agent controllers | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-DiscoveryService?path=/src/WebRole/AgentControllers) |

---

## 3. Assessment — Extensibility Platform & Function Apps

### 3.1 Container Assessment (primary)

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-AssessmentServiceV2** | Assessment extensibility platform (partner pattern for containers) | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-AssessmentServiceV2) |
| **Assessment Function App** | Assessment function app for partner assessments | [Repo](https://dev.azure.com/msazure/One/_git/c89c40b2-272d-4b83-91f9-32494f3550c9) |

### 3.2 Existing AKS Assessment (reference)

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-Assessment-AKS-POS** | AKS assessment — POS (Web App support) | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-Assessment-AKS-POS) |
| **AzureMigrate-Assessment-AKS-Java** | AKS assessment — Java worker | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-Assessment-AKS-Java) |

### 3.3 Other Assessment References

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-AppCentricAssessments** | Heterogeneous & application-centric assessments | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-AppCentricAssessments) |
| **AzureMigrate-AssessmentService** | VM Assessment — reference for private endpoint & options API support | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-AssessmentService) |
| **azm-postgresql** | PostgreSQL assessment — reference for partner assessment pattern | [Repo](https://msdata.visualstudio.com/Database%20Systems/_git/azm-postgresql?path=/src/Microsoft.Postgres.Azm.Assessment) |
| **AzureMigrate-WebAppCompoundAssessment** | WACA report — reference for container report generation | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-WebAppCompoundAssessment) |

---

## 4. Portal UX

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-Portal** | Azure Migrate portal experience | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-Portal) |

---

## 5. AMA / Copilot Integration

| Repo | Purpose | Link |
|------|---------|------|
| **azure-migrate-ai-querynet-migrate-agent-tools** | Query-net — NL2KQL datasets | [PR #14798003](https://msazure.visualstudio.com/One/_git/azure-migrate-ai-querynet-migrate-agent-tools/pullrequest/14798003) |
| **azure-migrate-ai-agents** | Agent instructions & eval datasets | [PR #14798379](https://dev.azure.com/msazure/One/_git/azure-migrate-ai-agents/pullrequest/14798379) |
| **azure-migrate-ai-assistant-cortex** | CPS (Cortex Prompt Service) | [PR #14821261](https://msazure.visualstudio.com/One/_git/azure-migrate-ai-assistant-cortex/pullrequest/14821261) |
| **kaizen-evaluation** | Pre-prod eval datasets | [PR #294](https://github.com/azure-core/kaizen-evaluation/pull/294) |
| **AzureMigrateSimulations Migration Copilot** | Local-first, evidence-grounded chat over discovery, assessment, explainability, costs, application groups, CTD landing zones, and business case | [`migration_chat.py`](src/azure_migrate_simulations/migration_chat.py) |

### 5.1 Migration Copilot Runtime

The simulator includes a top-right **Chat** experience backed by `POST /api/chat` and `GET /api/chat/status`.

- **Generative runtime:** facts and calculations are selected from the currently loaded simulator data, then Microsoft Foundry generates the final evidence-constrained answer. Responses retain evidence citations and navigation actions.
- **Durable history:** conversations and message metadata persist in local SQLite at `data/chat_history.db` and can be restored or deleted from the chat panel.
- **Grounding boundary:** the model cannot execute mutations or introduce unsupported facts. The current question, recent turns, selected local analysis, and citation labels are sent to the configured endpoint.
- **AI Feasibility Assessment:** the chat now guides application and solution-pattern selection, then hands off to a consented assessment workspace. `ai_feasibility.py` owns the seven-versioned-pattern catalog, safe Markdown/text/DOCX intent extraction, explicit evidence provenance, six independent decision dimensions, deterministic usage/cost scenarios, PoC gates, JSON persistence, and AI architecture extensions.
- **AI-ready CTD variant:** `GET /api/landing-zones?include_ai=true` applies the latest assessment revision per application (or an explicit assessment ID), preserves base cost separately, and marks every AI component/flow as proposed. Without the checkbox, the existing architecture is unchanged.
- **Decision boundary:** Foundry may rewrite the grounded executive summary only. Pattern selection, costs, readiness/disposition, evidence gaps, and production gates remain deterministic and no result is labeled production-ready.
- **Production alignment:** QueryNet, AI Agents, Cortex, and kaizen remain the reference repositories for production AMA orchestration, prompts, and evaluation.
- **Azure runtime:** uses the `gpt-6.1-sol` (`2026-09-29`) Global Standard deployment on `lz-msft-sea-aifoundry` in subscription `beccbce3-7faf-496f-b571-1fd2462704df`. The deployment has 500K TPM capacity; the earlier deployments remain unchanged.

Foundry model configuration:

| Environment variable | Purpose |
|---|---|
| `AZURE_MIGRATE_CHAT_ENDPOINT` | Foundry/Azure OpenAI resource endpoint |
| `AZURE_MIGRATE_CHAT_DEPLOYMENT` | Model deployment name |
| `AZURE_MIGRATE_CHAT_API_VERSION` | API version; defaults to `2024-12-01-preview` |
| `AZURE_MIGRATE_CHAT_API_KEY` | Optional local-development key; when absent, `DefaultAzureCredential` is used |

---

## 6. Business Case, Export & Migration Management

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-Reporting** | Azure Migrate Export / reporting | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-Reporting) |
| **AzureMigrate-BusinessCaseService** | Business case service | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-BusinessCaseService) |
| **AzureMigrate-MigrationMgmtSvcs** | Wave planning & migration management | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-MigrationMgmtSvcs) |

---

## 7. End-to-End Testing

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-IntegrationTests** | GQL — end-to-end integration tests | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-IntegrationTests) |

---

## 8. Infrastructure & Deployment

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-RegionBuildout** | OneAKS cluster — Bicep templates for service deployment | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-RegionBuildout?path=/src/AzureMigrateAKSServices/ServiceGroupRoot/BicepTemplates) |

---

## 9. Telemetry & Monitoring

| Repo | Purpose | Link |
|------|---------|------|
| **AzureMigrate-Geneva** | Geneva telemetry & logging configuration | [Repo](https://msazure.visualstudio.com/One/_git/AzureMigrate-Geneva) |

---

## 10. Planned Work — Not Yet in a Repo

The following items are planned but do not have dedicated repositories yet. They will be implemented within existing repos or new repos as the project progresses.

| Feature | Notes |
|---------|-------|
| **Perf-based assessment** | Performance data collection & sizing — container assessment function app |
| **Offline Appliance / Collector** | Offline discovery support for air-gapped environments |
| **Resolve Scope** | Scoping mechanism for container workloads |
| **Report generation** | Container workload reports — follow WACA report pattern (see §3.3) |
| **Retain/Retire tag-based assessment** | Tag-based assessment for containers — follow AKS assessment pattern (see §3.2) |
| **Private endpoint support** | Follow VM Assessment pattern (see §3.3) |
| **Options API settings** | Follow AKS / VM Assessment options API pattern (see §3.2 / §3.3) |

---

## Quick Lookup — Repo → Workstream Mapping

| Workstream | Primary Repos |
|------------|---------------|
| WS1 — Container Discovery Agent | WebAppAgent (reference), AzureMigrateAgents, ServiceCommon |
| WS2 — RPaaS / ARM / ARG | ApplicationMigration, ResourceProvider |
| WS3 — Discovery Service | DiscoveryService |
| WS4 — Appliance Integration | ApplianceComponents, Fabric Agents |
| WS5 — Container Assessment | AssessmentServiceV2, Assessment Function App |
| WS6 — VM Fallback & HA | AssessmentService (VM), AppCentricAssessments |
| WS7 — Portal UX | AzureMigrate-Portal |
| WS8 — AMA / Copilot | AI agent repos (Query-net, Cortex, kaizen) |
| WS9 — Business Case & Export | Reporting, BusinessCaseService, MigrationMgmtSvcs |
| WS10 — E2E Tests (GQL) | IntegrationTests |
| WS11 — Cross-Cutting | ServiceCommon, AssessmentService (private endpoint, options) |
| WS12 — Fabric Agents | VMwareAgent, HyperVAgent, ServerAgent |
| WS13 — Infrastructure | RegionBuildout (OneAKS) |
| WS14 — Geneva Telemetry | AzureMigrate-Geneva |

