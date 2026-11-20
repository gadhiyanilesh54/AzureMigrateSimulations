# Proposal: An Open-Source Incubation Team for an Agentic Migration Planner in Azure Migrate

**Audience:** Azure Migrate leadership (Product + Engineering). Decisions requiring CVP/EVP sponsorship—open-source strategy and AI economics—are flagged inline.  
**Author:** _(your name)_  
**Date:** July 2026  
**Status:** For decision—requesting sponsorship for a two-quarter open-source incubation team

---

## Executive decision

- **Decision requested:** Charter a 4–6 person team for two quarters to ship and validate an open-source, conversational migration-planning MVP, seeded from the working prototype in this repository.
- **Why now:** AWS Transform is GA and has established an agentic VMware-migration narrative. An open-source incubation path gives Azure Migrate an additional way to validate capabilities with customers and partners at high cadence while the first-party service retains its governed productization path.
- **Strategic fit:** Azure Migrate remains the system of record and execution plane. The open-source planner is an upstream innovation funnel and reach extender for customer-managed, partner-customized, and restricted planning environments.
- **Product posture:** Azure OpenAI and Microsoft Foundry are the preferred reference path; customers may use another approved model or a local model when their operating constraints require it.
- **What we need:** Headcount, a governed Microsoft GitHub repository, OSPO/legal/security/privacy review, a named long-term owner, and field support to recruit 3–5 design partners.

---

## 1. Opportunity and customer problem

Migration planning is moving from disconnected tools toward conversational, agent-assisted workflows. AWS Transform for VMware automates discovery, dependency mapping, wave planning, network conversion, and migration execution. AWS publicly markets outcomes including up to 80x faster network conversion, more than 10x faster discovery and wave planning at CSL, and a 30% improvement in infrastructure-team effectiveness at Vector Limited.

Azure Migrate already provides a mature, free platform for discovery, assessment, business cases, dependency analysis, and execution. The Azure Copilot migration agent (preview) adds conversational strategy, inventory analysis, business-case comparison, readiness interpretation, and landing-zone configuration. Its documented experience is planning-focused, runs through Azure Copilot and Azure Migrate, and does not expose customer-selectable models or customer-managed inference capacity.

The remaining opportunity is not to reproduce Azure Migrate. It is to help customers and partners get to a credible Azure plan sooner, especially when they need local processing, custom connectors, or integration with an existing AI toolchain.

Customers ultimately need five answers:

1. **What do I have?** A correlated estate view across infrastructure, applications, dependencies, and business context.
2. **What will it cost?** Explainable TCO with visible, editable assumptions.
3. **What is a safe sequence?** Dependency-aware waves constrained by timeline, capacity, risk, and criticality.
4. **What should the target look like?** A landing-zone design and reviewable infrastructure artifacts.
5. **What changed?** Re-planning, provenance, and an audit trail as the migration evolves.

The proposed planner starts with a rapid “first glimpse” from RVTools, CSV, JSON, or an offline snapshot, then deepens the plan with Azure Migrate appliance/Collector data and other approved sources. It does not replace high-fidelity discovery or migration execution.

---

## 2. Business value

The six-month charter will test four business hypotheses:

| Value lever | How the planner contributes | Measure |
|---|---|---|
| **Faster time to evidence** | Produces an initial inventory, TCO, and draft waves from data the customer already has | Time to first credible plan |
| **Architect leverage** | Encodes repeatable assessment and planning practices in deterministic tools | Plans completed per architect/partner team |
| **Modernization pull-through** | Compares rehost with suitable Azure PaaS/container targets and exposes trade-offs | Azure services selected and qualified pipeline influenced |
| **Restricted-environment reach** | Supports a fully local configuration when the model, pricing data, and tools are local and outbound calls are disabled | Pilots that could not use a hosted planning experience in-place |

Model flexibility supports Azure consumption indirectly: fewer planning blockers create more qualified Azure plans, which can move workloads into replication and migration sooner. When customers can use Microsoft Foundry or Azure OpenAI, Azure also receives planning-inference consumption. The primary business outcome remains migrated and modernized workloads, not token deflection alone.

---

## 3. Why an open-source incubation path

This proposal is not an either/or choice between open source and the Azure Copilot migration agent.

1. **Incubate before productizing.** Validate workflows, schemas, evaluations, and customer outcomes before committing full first-party engineering investment.
2. **Reach additional operating environments.** Support customer-managed deployment, local models, and partner-specific connectors where the hosted experience cannot run in-place or cannot be customized sufficiently.
3. **Enable ecosystem contribution.** Give GSIs and ISVs governed extension points for parsers and planning rules while keeping one canonical Microsoft upstream.
4. **Improve transparency.** Make deterministic sizing, TCO, and wave-planning rules inspectable; use the model to orchestrate and explain rather than invent the underlying numbers.
5. **Create a graduation path.** Move proven capabilities into Azure Migrate or the Copilot migration agent with evidence, contracts, schemas, tests, and—where production standards permit—reusable code.

Open source does not bypass Microsoft review. The repository launches only after OSPO, legal, trademark, security, privacy, and responsible-AI gates are satisfied. Public releases follow normal secure-development, dependency, release, and incident-response practices.

### Alternatives considered

| Option | Benefit | Constraint |
|---|---|---|
| **Extend only the first-party agent** | One supported experience, existing Azure Migrate integration, and established service governance | Does not address customer-managed deployment, local-model, or partner-extension scenarios; experimentation remains coupled to the service roadmap |
| **Partner-led solution with no Microsoft upstream** | Lowest direct engineering investment | Higher risk of incompatible implementations, uneven quality, fragmented schemas, and limited ability to graduate learning into Azure Migrate |
| **Governed OSS incubation plus first-party graduation** | Tests customer-managed and extensible scenarios while preserving Azure Migrate as the supported execution plane | Requires explicit ownership, open-source governance, security review, and clear stop conditions |

The recommended option is governed incubation plus first-party graduation. It creates a controlled place to test the scenarios that are difficult to validate inside the hosted product while keeping one Azure Migrate roadmap and one supported execution experience. This is not a commitment to maintain every experiment indefinitely: the Day-90 and Day-180 gates determine whether a capability graduates, remains community-supported, is narrowed, or is retired.

The design-partner program is also an evidence-gathering mechanism. We should not claim that named customers requested this exact product until that demand is documented. Partners qualify only when they have an active Azure migration engagement, an accountable sponsor, approved representative or customer data, and a commitment to run the end-to-end workflow. Interviews alone indicate interest; completion of the planning loop and movement toward migration indicate adoption.

---

## 4. Product boundary and competitive position

**One line:** An Azure-first, model-flexible migration planner that turns customer-provided discovery data into explainable planning artifacts and hands execution to Azure Migrate.

| Capability | Azure Migrate + migration agent | Six-month OSS MVP | Later exploration |
|---|---|---|---|
| Conversational planning | First-party hosted experience over Azure Migrate data | Reference UI plus MCP tools over local/customer-managed data | Additional approved agent clients |
| Ingestion | Appliance, Collector, RVTools, Azure Migrate artifacts | RVTools, CSV, JSON; modular connector contract | Limited transcript/wiki extraction after security and privacy validation |
| TCO | Business case, ROI analysis, PowerPoint export | Editable assumptions, structured rationale, baseline executive export | Broader finance-system integration |
| Wave planning | Planning insights in the hosted experience | Dependency-aware draft waves and human overrides | Advanced capacity and schedule optimization |
| Target artifacts | Landing-zone configuration for downstream deployment | Reviewable landing-zone/IaC prototype with validation gates | Network-device translation for NSX/firewalls |
| Execution | Replication, test migration, and cutover in the Azure Migrate portal | Explicit handoff to Azure Migrate; no autonomous execution | Deeper status synchronization after validation |

AWS’s 80x, 10x, and 30% figures are vendor-published marketing or case-study claims. They establish market urgency but are not Azure targets. The MVP will be measured against customer planning time, plan quality, adoption, and Azure migration progress.

---

## 5. Six-month charter

### In scope

1. **Structured ingestion:** RVTools, CSV, and JSON with source metadata and validation.
2. **First-glimpse plan:** Inventory, basic application grouping, initial TCO, and dependency-aware draft waves.
3. **Explainability:** Structured rationale for material recommendations, editable assumptions, confidence indicators, and source provenance.
4. **Human-controlled re-planning:** Wave and cost overrides with versioned artifacts and decision history.
5. **Reference experience:** MCP tool layer and a small reference UI, with Microsoft Foundry/Azure OpenAI as the preferred deployment path and documented local-model configuration.
6. **Exports and handoff:** CSV/JSON plus a baseline executive artifact; clear next steps into Azure Migrate for execution.
7. **Evaluation and governance:** Functional tests, adversarial evaluations, threat model, privacy review, telemetry policy, and secure-release automation.

### Explicit non-goals for the charter

- No autonomous replication, migration, cutover, or Azure deployment.
- No promise of complete NSX, FortiGate, Palo Alto, or Cisco ACI translation.
- No unrestricted arbitrary code or shell execution.
- No ingestion of every unstructured business-document format.
- No support commitment for every model, AI client, or partner fork.
- No Azure SLA for the open-source release; first-party SLA applies only to graduated service capabilities.

This boundary concentrates the team on proving the planning loop rather than attempting to match every competitor feature in two quarters.

---

## 6. Architecture, data handling, and trust

### Architecture principles

1. **Deterministic tools perform calculations.** The model orchestrates tools and explains structured results; it does not own pricing, sizing, or dependency math.
2. **Azure-first, model-flexible.** Microsoft Foundry/Azure OpenAI is the reference implementation. Approved local or alternate endpoints are supported where customer constraints require them.
3. **Local-capable, not universally zero-egress.** A fully local configuration is possible only when the model, caches, inputs, and tools are local and all outbound calls are disabled. Hosted models, live Azure pricing, telemetry, or update checks introduce explicit, configurable egress.
4. **Untrusted-input posture.** Prompts, uploaded documents, generated artifacts, and external MCP servers are treated as untrusted.
5. **Artifacts and provenance.** Material outputs retain source references, assumptions, tool versions, human overrides, and timestamps.
6. **Human approval.** Recommendations and generated IaC are proposals. No deployment occurs without deterministic validation and explicit customer approval under the customer’s identity.

### Minimum security and privacy controls

- File type/size validation, malware scanning, sanitization, and isolation of extracted content.
- Prompt- and document-attack detection on the Azure reference path, with configurable equivalent controls for other deployments.
- Allowlisted tools and outbound endpoints; least-privilege identity and no deployment credentials in the planning agent.
- Data minimization, configurable redaction, encryption, customer-controlled retention/deletion, and no customer content in telemetry by default.
- Bicep compilation and what-if; Terraform formatting, validation, and plan; policy/security and secret scanning before any IaC can be considered deployable.
- Audit logs for tool calls, accessed artifacts, generated outputs, approvals, and overrides.

“Offline-capable” therefore describes a tested deployment configuration, not a blanket claim that every deployment has zero data egress.

---

## 7. Delivery plan and decision gates

### Day 90: governed planning-loop release candidate

- Governed repository, license, contribution policy, threat model, telemetry policy, CI, and security scanning.
- Containerized local/reference deployment with MCP tools and a minimal UI.
- RVTools/CSV/JSON ingestion through inventory, TCO, and dependency-aware draft waves.
- Baseline rationale, confidence, provenance, override, and export support.
- Evaluation harness covering calculation correctness, prompt/document attacks, and tool authorization.
- At least **two active design partners**, with at least one completing the workflow on representative or real approved data.

**Day-90 gate:** Continue to the second phase only if two independent partners are actively engaged, one completes the end-to-end planning loop, no unresolved critical security/legal blocker exists, and Azure Migrate names a credible long-term owner. Otherwise narrow the scope, keep the work internal, or stop.

### Day 180: hardened pilot and graduation decisions

- Hardened identity, privacy, data-handling, and local-deployment controls.
- Editable TCO assumptions, executive export, constraint-aware wave re-planning, and versioned decision history.
- Documented Azure Migrate execution handoff; no autonomous migration execution.
- **Three or more active/completed pilots**, including one Microsoft Foundry/Azure OpenAI deployment and one validated GSI extension.
- Measured change in time to first credible plan and at least one pilot moving a planned wave toward replication or migration.
- At least **two graduation decision packages** containing evidence, contracts, schemas, tests/evaluations, security requirements, and reusable code where appropriate.

**Day-180 gate:** Continue the standalone project only if adoption and business outcomes justify permanent ownership. If the project cannot demonstrate active adoption, material planning improvement, or movement toward execution, archive the standalone release and retain only validated requirements, schemas, tests, and reusable components.

---

## 8. Relationship to the first-party service

Azure Migrate remains the supported discovery, assessment, system-of-record, and execution experience. The OSS planner has three roles:

- **Incubation:** Test new planning capabilities with real engagements before first-party investment.
- **Reach extension:** Serve approved local, restricted, or partner-customized planning scenarios.
- **Ecosystem leverage:** Accept governed connectors and rules that make Azure the target of partner migration work.

“Graduation” means a validated capability enters the first-party roadmap. What must graduate is customer evidence, behavior contracts, schemas, evaluation suites, and security requirements. Source code may be reused when it meets first-party standards; otherwise the capability can be reimplemented for service scale, reliability, and compliance.

To prevent fragmentation, Microsoft maintains one canonical upstream, one roadmap owner, versioned compatibility contracts, conformance tests, trademark guidance, and clear labels distinguishing the community-supported planner from supported Azure Migrate capabilities.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Brand or quality risk | Governed repository, reference/preview labeling, release gates, CI, security scanning, and trademark guidance |
| Fragmentation | One canonical upstream, shared contracts, conformance tests, and a single Azure Migrate roadmap owner |
| Unfunded maintenance | Name the permanent DRI and baseline maintainer capacity before public launch; otherwise keep the experiment time-boxed |
| Security/privacy | Untrusted-input design, least privilege, local controls, explicit egress configuration, threat modeling, and audit logs |
| Model variability | Deterministic calculations, structured outputs, model-agnostic evaluations, and human approval |
| Weak adoption | Day-90 and Day-180 stop gates tied to real design-partner use and migration progress |

---

## 10. The ask and success measures

Leadership sponsorship is requested to:

1. Charter a **4–6 person incubation team** for two quarters, with named Product and Engineering DRIs.
2. Approve a governed Microsoft GitHub repository after OSPO, legal, security, privacy, trademark, and responsible-AI review.
3. Recruit **3–5 design partners/GSIs** with active Azure migration engagements and approved data access.
4. Name the long-term owner and minimum maintainer capacity before public launch.
5. Establish the graduation review with the Azure Migrate and Copilot migration-agent owners.

### Success after two quarters

**Delivery and adoption**

- Hardened pilot release covering structured ingestion through explainable TCO and draft waves.
- Three or more active/completed pilots; one Foundry/Azure OpenAI deployment; one GSI extension.
- Two or more first-party graduation decisions—not necessarily direct code merges.

**Customer and Azure outcomes**

- At least one partner demonstrates a material reduction in time to first credible plan.
- At least one planned wave progresses toward replication or migration.
- Qualified Azure migration pipeline and target Azure services influenced by the pilots are recorded.
- The team produces a measured recommendation to continue, narrow, graduate, or archive the project.

---

## Appendix A—Prototype evidence

The existing `AzureMigrateSimulations` prototype reduces architecture risk but is not yet a supported product:

- MCP server with **67 declared tools** across discovery, assessment, simulation, topology, wave planning, business case, enrichment, and exports.
- RVTools CSV/XLSX and JSON ingestion; pyVmomi-based vCenter discovery.
- Dependency-aware wave-planning implementation, what-if overrides, and snapshot/restore.
- Side-by-side pricing comparison across seven scenarios, right-sizing, and confidence scoring.
- Eight enrichment-source types, including Dynatrace, New Relic, Datadog, Splunk, Prometheus, AppDynamics, Zabbix, and custom data.
- CAF-aligned cloud-topology generation and prototype Terraform/Bicep output. These outputs require compilation, validation, policy/security scanning, and deployment testing before being described as deployment-ready.

## Appendix B—Sources

- Microsoft Learn, **What is Azure Migrate?**—discovery, Collector, assessment, business case, dependency analysis, and execution.
- Microsoft Learn, **Azure Copilot migration agent (preview)**—prerequisites, supported planning scenarios, PowerPoint business-case export, landing-zone configuration, BYOS limitation, and portal execution boundary.
- AWS, **AWS Transform for VMware migrations**—discovery, wave planning, network conversion, execution, IaC formats, and published customer outcomes.

> Competitive figures are vendor-published claims and should be attributed as such in leadership discussions.