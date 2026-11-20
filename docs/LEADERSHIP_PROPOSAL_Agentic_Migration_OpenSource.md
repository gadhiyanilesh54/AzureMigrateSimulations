# Proposal: An Open-Source v-Team for an Agentic, Conversational Migration Planner in Azure Migrate

**Audience:** Azure Migrate leadership (Product + Engineering). Decisions that need CVP/EVP altitude — open-source strategy and AI/inference economics — are flagged inline.
**Author:** _(your name)_
**Date:** July 2026
**Status:** For decision — requesting sponsorship for a chartered open-source v-team

---

## Executive brief (TL;DR)

- **Decision requested:** Fund a small (4–6 person) open-source v-team for two quarters to ship an agentic, conversational migration planner on GitHub, seeded from a working prototype that already exists in this repo.
- **Why now:** AWS Transform is GA and setting the pace on agentic VMware migration. A closed, quarterly release cadence cannot match it; open source lets us ship weekly and turn community/partner effort into Azure migrations.
- **Strategic fit (pro-Azure, model-agnostic):** The planner works with the customer's preferred model — *including Azure OpenAI / Foundry models*. It reaches regulated, air-gapped, and model-committed customers who cannot use the hosted agent today, and pulls their workloads onto Azure.
- **Complements, not competes:** A fast-moving upstream that graduates validated capabilities into the first-party Azure Migrate service and the Copilot migration agent.
- **What we need:** headcount + a governed GitHub org + OSPO/legal/security review + field help sourcing 3–5 design partners.

---

## 1. Executive summary

The migration planning market has shifted from *tools* to *agents*. AWS shipped **AWS Transform** — the first agentic AI service for migrating VMware workloads at scale — and is publicly claiming outcomes like **up to 80x faster network conversion** and **10x faster application discovery and wave planning** at real customers (CSL, Vector Limited). Azure Migrate has responded with the **Azure Copilot migration agent (preview)**, a strong planning-focused conversational experience — but it is SaaS-bound, tied to Azure Copilot tenant enablement, plan-only (execution stays in the portal), and it runs entirely on **Microsoft's models and Microsoft's tokens**.

We cannot out-ship a competitor moving at agentic speed using traditional, closed, quarterly release trains. **This proposal asks leadership to charter a small open-source v-team inside Azure Migrate** to build and iterate — in the open, on GitHub — an **agentic conversational migration planner** that:

- **Meets customers where they are:** runs in the customer's environment (including air-gapped), plugs into the AI tools they already use (Copilot, Claude, Cursor, Continue, custom agents) via open protocols (MCP).
- **Uses the customer's own model and tokens (BYOM/BYOK):** cost-effective for the customer, and it **removes token/inference cost and scaling burden from the Azure Migrate service**.
- **Puts customers in control:** they can customize, extend, and re-generate their own migration plan — and partners (TCS, Infosys, Wipro, Accenture) can tailor it per engagement.
- **Ships at AI-era pace:** open source lets us release features weekly, accept community/partner PRs, and validate with real customers before we invest in productizing the winners into the first-party service.

We already have a **working prototype in this repository** — an offline migration intelligence platform exposing an **MCP server with 60+ agent tools** (discovery, assessment, what-if, wave planning, cloud topology, IaC generation, business case, enrichment). This de-risks the MVP: the hard architectural questions are answered; what we need is a charter, a team, and a place to ship.

**The ask:** Sponsor a 4–6 person open-source v-team for two quarters to deliver an agentic planner MVP on GitHub, meeting customers where they are, on their own tokens.

---

## 2. First-principles: re-imagining the migration journey in the AI era

Strip migration planning down to what a customer actually needs, independent of any existing product:

1. **"Show me what I have"** — an accurate, correlated picture of the estate (infra + apps + dependencies + business context).
2. **"Tell me what it costs and why"** — TCO/ROI they can trust, with the assumptions exposed and editable.
3. **"Give me a safe plan"** — dependency-aware waves that respect their constraints (timeline, team capacity, risk, compliance).
4. **"Build the target for me"** — landing zone + network design as deployable IaC.
5. **"Let me change my mind"** — re-plan on demand as reality changes, with an audit trail.

Three assumptions from the pre-AI era no longer hold:

| Old assumption | AI-era reality |
|---|---|
| Discovery must be a heavy appliance-first, upload-first pipeline. | A useful *first glimpse* can come from an RVTools export, a CMDB dump, or an offline scan **in minutes** — then deepen with the appliance for workloads that matter. |
| Business context (owners, criticality, app boundaries) is manual tribal knowledge. | LLMs can **read meeting notes, wiki exports, Zoom transcripts, ticket dumps** and correlate them into an application catalog automatically. |
| The vendor must host the model, own the tokens, and gate every feature behind a portal release. | The customer brings their **own model and tokens**; the vendor ships **open, composable tools** that any agent can orchestrate. |

**Re-imagined journey — staged from "first glimpse" to "deep discovery":**

```
Stage 0  First glimpse    RVTools / CMDB / quick offline infra snapshot  →  instant app catalog + rough TCO + draft waves
Stage 1  Business context Meeting notes / wiki / Zoom transcripts / tickets → owners, criticality, app boundaries
Stage 2  Deep discovery   Azure Migrate appliance + guest agents          →  per-workload detail, real dependency graph
Stage 3  Plan             Conversational wave planning under constraints  →  move groups, sequencing, rationale
Stage 4  Architect        Network translation + landing zone              →  VNets/NSGs/UDRs/Hub-Spoke as ARM/Bicep/Terraform
Stage 5  Execute + audit  Iterative re-planning during execution          →  persisted artifacts, audit-grade reports
Stage 6  Optimize (cont.) Post-migration right-sizing + modernization     →  ongoing cost/PaaS optimization, continuous re-plan
```

The key insight: **the customer should get value at Stage 0 in minutes, using data they already have and a model they already pay for** — not weeks later after an appliance rollout and a portal onboarding. And the journey does not end at cutover: **Stage 6 keeps the loop open** — post-move right-sizing and modernization sustain both customer value and Azure consumption.

---

## 3. How the conversational planner accelerates migration (value levers)

Beyond matching competitor features, a conversational, agentic planner boosts migration through levers that traditional tooling cannot. These are the outcomes leadership should hold us to — and several tie directly to **Azure consumption (ACR)**.

| # | Value lever | How the conversational planner delivers it | Business impact |
|---|---|---|---|
| 1 | **Time-to-value** | Stage-0 "first glimpse" from RVTools/CMDB in minutes, on data the customer already has | Weeks → minutes to a first credible plan; faster deal momentum |
| 2 | **Skills democratization** | Natural-language UX lets junior staff *and the customer themselves* plan migrations without deep Azure/CAF expertise; the agent encodes the expert playbooks | Removes the scarce-architect bottleneck; more migrations run in parallel with the same headcount |
| 3 | **Modernization pull-through** | The agent actively steers rehost → **replatform to PaaS/containers/AVD** (App Service, Azure SQL MI, AKS) where it fits, with the TCO trade-off explained | Higher-value landings and **higher Azure consumption**, not just lift-and-shift VMs |
| 4 | **Planning at scale / parallelism** | Plan **hundreds of apps in parallel** — the agent groups, sizes, and sequences the whole estate at once instead of app-by-app | Data-center-exit timelines that were infeasible manually become achievable |
| 5 | **Pre-sales / deal-cycle acceleration** | Field and partners compress assessment→business-case→commit into a single conversational session | Shorter sales cycles, higher win-rate, faster pipeline conversion |
| 6 | **Multi-stakeholder alignment** | Shared, explainable artifacts (catalog, TCO, waves) that app owners, finance, security, and infra can each interrogate | Migration is a committee sport; alignment is the real blocker the planner removes |
| 7 | **Business-context capture** | Ingests meeting notes, wiki, transcripts, CMDB into an application catalog automatically | Eliminates weeks of manual app-mapping workshops |
| 8 | **Funding approval** | Explainable TCO with editable assumptions + PPT/PDF/XLS exports | Unblocks the CFO/steering-committee sign-off that gates every migration |
| 9 | **Data-sovereignty unlock** | Offline, air-gapped, BYO-model operation | Converts regulated/air-gapped estates that are **unreachable today** into Azure migrations |
| 10 | **Partner/GSI throughput** | Extensible, forkable tooling GSIs tailor per engagement | Every partner engagement becomes leverage that defaults to Azure |
| 11 | **Continuous optimization (Stage 6)** | Post-migration right-sizing, cost optimization, and further modernization via the same agent | Keeps the customer relationship — and Azure consumption — growing after cutover |

**The two levers to emphasize with leadership:** *skills democratization* (removes the architect bottleneck that caps migration velocity) and *modernization pull-through* (turns migrations into higher Azure consumption) — because they most directly move both migration throughput and Azure ACR.

---

## 4. Competitive landscape — deep research

### 4.1 AWS Transform (the pace-setter)

AWS positions AWS Transform as *"the first agentic AI service for migrating VMware workloads at scale."* Publicly documented capabilities:

- **End-to-end agentic automation:** Discover & assess → Plan → Create landing zone → Automate network conversion → Migrate.
- **Discovery & assessment:** auto-collects performance data, network connections, database metadata, server specs; **supports RVTools and other ingestion formats**; generates **TCO projections and business cases in minutes**.
- **Migration planning:** analyzes dependencies, groups workloads into **optimized migration waves** by technical *and* business priority; **conversational workflows** let teams adjust wave composition, sequencing, and timing.
- **Landing zone creation:** generates Landing Zone Accelerator (LZA) network configs — multi-account, governed, secure by default — *before* any VM moves.
- **Network conversion:** converts on-prem network config to AWS equivalents (VPCs, subnets, security groups, transit gateways, route tables) **up to 80x faster than manual**; outputs **CloudFormation, CDK, Terraform, and LZA** IaC.
- **Execution:** rehost (managed replication, test instances, cutover) or **replatform to containers** (analyzes source, generates Dockerfiles, builds images with security scanning, produces IaC for ECS/EKS).
- **Collaboration:** real-time, collaborative **web experience** to align stakeholders; human-in-the-loop validation; IAM Identity Center governance.
- **Beyond VMware:** AWS Transform also covers **mainframe** and **.NET** modernization use cases — a multi-workload agentic modernization play, not a point tool.
- **Proof points:** CSL (>10x faster discovery + wave planning), Vector Limited (30% infra team effectiveness boost via partner Slalom).

**What this tells us:** the competitor's message is *speed, agentic automation, conversational re-planning, multi-format ingestion, and IaC in the customer's toolchain of choice.* That is precisely the surface where we must not fall behind.

### 4.2 Azure Migrate today (our strengths + gaps)

Azure Migrate is a mature, **free**, unified platform: discovery (appliance, **Collector for air-gapped/quick snapshot**, RVTools import), assessment/right-sizing, **dependency analysis**, **business case** (TCO, CapEx→OpEx, year-over-year cash flow), and execution (agentless/agent-based migration for VMware/Hyper-V/physical, DB and web app modernization, Data Box).

The **Azure Copilot migration agent (preview)** adds a genuinely strong conversational planning layer:

- Conversational **migration strategy analysis**, **inventory/discovery summarization** (appliance, Collector, **RVTools**), **business case + ROI** (create/summarize/compare; **downloadable as PowerPoint**), **readiness interpretation**, and **landing zone configuration reasoning** (downloadable PLZ templates).
- Natural-language tagging/grouping of workloads into applications; compares lift-and-shift vs modernization.

**But structurally it is:**

- **SaaS- and portal-bound** — requires an Azure subscription, Azure Copilot tenant enablement, and Agents (preview) enablement; not usable in air-gapped/restricted planning environments.
- **First-party model + tokens** — runs on Microsoft's models and inference; the customer cannot bring their own model, and cost/scale is Microsoft's burden. (Note: it is explicitly **not supported with Bring-Your-Own-Storage for conversation history** — a signal of how tightly coupled it is to the hosted stack.)
- **Plan-only** — execution stays in the portal; limited iterative re-planning *during* execution.
- **Not extensible by customers or partners** — there is no way to fork it, add parsers/connectors, or customize the agent's tools for a specific engagement.

### 4.3 Side-by-side gap analysis

| Capability (the 5 questions) | AWS Transform | Azure Migrate + Copilot agent (preview) | Proposed open-source agentic planner |
|---|---|---|---|
| **Agentic conversational planner** that ingests mixed files, answers arbitrary questions, re-generates waves on demand | ✅ Conversational, adjustable waves | ⚠️ Conversational **planning**, re-plan supported but portal/model-bound | ✅ Any agent (Copilot/Claude/Cursor/custom) via **MCP**, offline, **BYO model** |
| **Multi-format business-context ingestion** (meeting notes, Zoom, wiki, CMDB + technical traces → app catalog) | ⚠️ Technical formats + RVTools; business docs less emphasized | ⚠️ RVTools + discovery; NL tagging, but not transcript/wiki correlation | ✅ **Modular parsers + LLM extraction** of owners/criticality/app boundaries from unstructured docs |
| **Automated TCO with explainability + multi-format export** (PPT/PDF/XLS) | ✅ TCO/business case in minutes | ✅ Business case + **PPT export**; explains savings | ✅ Explainable TCO, **editable assumptions** (BYOL, bin-packing), PPT/PDF/XLS/CSV |
| **Network translation + IaC** (NSX/ACI/firewall → VNet/NSG/UDR/Hub-Spoke; ARM/Bicep/Terraform) | ✅ 80x network conversion; CFN/CDK/TF/LZA | ⚠️ Landing zone config reasoning + downloadable PLZ; **not** firewall/NSX config translation | ✅ **Translation templates** for NSX/FortiGate/Palo Alto/Cisco ACI → Azure; ARM/Bicep/Terraform |
| **Flow to execution + audit-grade artifacts** (persist, iterate, report) | ✅ Managed execution + governance | ⚠️ Execution in portal; artifacts in project | ✅ **Persisted artifacts, change history, provenance**, audit-grade export |

**Conclusion:** On the conversational-planning axis we are competitive (thanks to the Copilot agent). We are **behind or closed** on: open extensibility, BYO-model/offline, unstructured business-context ingestion, network-config translation, and partner customizability. Those gaps are exactly where **an open-source model wins fastest.**

---

## 5. Why an open-source GitHub team — and why now

### 5.1 Speed: we cannot catch up building the old way

Agentic capabilities are compounding monthly. A first-party-only, portal-gated release train (design → privacy/compliance review → deployment rings → GA) is measured in **quarters**. AWS Transform is already GA and iterating in public. **Open source lets us ship weekly**, accept partner/community PRs, and turn the winners into first-party features once validated — instead of guessing behind a closed door.

### 5.2 Meet the customer where they are

Customers are already standardized on AI tools — GitHub Copilot, Claude, Cursor, Continue, internal agents. An **open, MCP-based tool layer** plugs the migration planner directly into those tools. No portal onboarding, no tenant enablement, no data egress for regulated/air-gapped estates. This is a structural advantage the hosted competitor cannot match.

### 5.3 BYO model + BYO tokens: cost-effective for the customer, lower burden for us

- **For the customer:** they use their **own preferred model and their own tokens** — no premium AI markup, full control over data residency and model choice.
- **For Azure Migrate:** we **offload inference cost and scale** from the service. Instead of paying to run everyone's planning conversations on our tokens, we ship the tools and let the customer's model do the reasoning. This materially reduces the cost and operational burden of scaling an agentic feature to every migration customer.

### 5.4 Put customers and partners in control

Open source turns a single-tenant SaaS experience into an extensible **platform**. Customers customize their own plans; GSIs/partners tailor it per engagement (a top partner request); ISVs add connectors. Every external contribution is leverage we didn't have to staff — and it seeds a community that *defaults to Azure* as the migration target.

### 5.5 Trust, provenance, and enterprise credibility

Migration decisions move millions of dollars. **Open, inspectable logic** for sizing, wave grouping, and TCO math is a trust advantage over a black-box SaaS — and it produces **audit-grade artifacts** procurement and risk teams demand.

### 5.6 De-risked: the prototype already exists

This repository is a working proof: an offline platform with an **MCP server exposing 60+ agent tools**, discovery/assessment/what-if/wave-planning/cloud-topology/IaC/business-case, consumable today by Copilot, Claude, Cursor, Continue, and custom agents. We are not asking to fund a research bet — we are asking to **productize and open-source a working MVP**.

---

## 6. The proposed product — agentic conversational migration planner

**One line:** *An open-source, agent-native migration planner that any AI tool can drive, running on the customer's data and the customer's model — from first glimpse to audit-grade plan.*

### Architecture principles

1. **Agent-native, protocol-first:** every capability is an **MCP tool**; any MCP-capable agent orchestrates it. No bespoke chat client required (though we ship a reference chat UI).
2. **BYO model / BYO tokens:** the reasoning model is the customer's choice; we ship deterministic tools + prompt scaffolding, not a hosted model.
3. **Local-first, offline-capable:** runs in the customer's environment; **zero data egress** by default; air-gap friendly.
4. **Composable ingestion:** modular parsers (RVTools, CMDB/CSV, vSphere, wiki/markdown, transcripts) + an LLM extraction step for business metadata.
5. **Artifacts + provenance:** every plan, override, and decision is persisted with change history for audit and re-planning.
6. **Graduation path:** validated OSS capabilities graduate into the first-party Azure Migrate service and the Copilot migration agent.

### Reference flow

```
 Mixed inputs                Open tool layer (MCP)              Outputs
 ───────────                 ─────────────────────              ───────
 RVTools / CMDB   ─┐                                     ┌─►  Application catalog + dependency groups
 Meeting notes    ─┤    ┌───────────────────────────┐    ├─►  Explainable TCO (PPT/PDF/XLS/CSV)
 Wiki / MD dumps  ─┼──► │  Customer's AI agent +     │────┤─►  Dependency-aware wave plan + rationale
 Zoom transcripts ─┤    │  customer's model/tokens   │    ├─►  Landing zone + network IaC (ARM/Bicep/TF)
 Network traces   ─┤    │  driving open MCP tools    │    ├─►  Audit-grade report + change history
 vCenter / appl.  ─┘    └───────────────────────────┘    └─►  Re-plan on demand
```

---

## 7. Capability deep-dives (answering the five questions)

Section 4.3 covers the competitive gaps. This table maps each customer question to what we ship and how far the prototype already takes us — so the reader sees exactly what is *new build* versus *already working*.

| # | Customer question | What we ship | Prototype status → gap to close |
|---|---|---|---|
| **Q1** | Agentic conversational planner (mixed files, arbitrary Q&A, on-demand re-plan) | Reference chat UI **and** MCP tools so the customer's own agent ingests mixed files, answers arbitrary questions, and re-generates waves on demand — offline, on their model | MCP server + 60+ tools exist → **add** multi-file ingest + chat UX |
| **Q2** | Multi-format business-context ingestion → application catalog | Modular parsers (RVTools, vSphere, CMDB/CSV, wiki/markdown, transcripts) + an **LLM extraction step** for app names, owners, and criticality, correlated with technical discovery | Parsers + enrichment loop exist → **add** unstructured-doc (transcript/wiki) extraction |
| **Q3** | Explainable TCO with multi-format export | Current-vs-target cost modeling with **editable assumptions** (BYOL/AHUB, bin-packing, right-sizing); PPT/PDF/XLS/CSV export (see §8 for the explainability model) | 6 pricing models + business case exist → **add** explainability layer + PPT/PDF export |
| **Q4** | Network translation + IaC generation | Translation templates for **NSX / FortiGate / Palo Alto / Cisco ACI → Azure VNets, NSGs, UDRs/route tables, Azure Firewall, Hub-Spoke, ExpressRoute/Virtual WAN**, output as ARM/Bicep/Terraform with a preview/edit canvas | Cloud topology + Terraform/Bicep generation exist → **add** network-config translators |
| **Q5** | Flow to execution + audit-grade artifacts | Persist all artifacts and agent decisions with change history and provenance; **iterative re-planning during execution**; audit-grade reports | Snapshot/restore + override persistence exist → **add** provenance log + audit report |

---

## 8. Explainability — the trust layer that wins enterprise migrations

Explainability is not a nice-to-have feature bolted onto one screen — it is a **cross-cutting requirement** and one of our strongest structural advantages over a black-box hosted competitor. A migration plan moves millions of dollars and reshapes a production estate; a steering committee will not approve a number or a wave sequence it cannot interrogate. **Every material output must be able to answer "why?"**

### 8.1 What "explainable" means here

For each of the four decision surfaces, the planner must expose the inputs, the rule/assumption applied, the calculation, and the confidence — in natural language *and* in a machine-readable trace:

| Decision surface | The customer can ask… | What we surface |
|---|---|---|
| **Right-sizing / SKU** | "Why D8s_v5 and not D4s_v5?" | Source metric (P95 CPU/mem/IOPS), the percentile rule, enrichment data used, confidence score (50–100), and the alternative SKUs considered |
| **TCO / cost** | "Why is Azure cheaper here, and by how much?" | Line-item current-vs-target math, pricing model chosen (PAYG/RI/SP/AHUB), BYOL assumption, bin-packing decision, and the delta each assumption contributes |
| **Wave / grouping** | "Why is this VM in Wave 2, not Wave 1?" | The dependency edges (TCP/port/process), business-criticality signal, constraint that bound it (timeline/capacity/risk), and the rule that placed it |
| **Network / landing zone** | "Why this NSG rule / this hub-spoke split?" | The source firewall/NSX rule it was translated from, the CAF/WAF pattern applied, and the mapping template used |

### 8.2 Explainability by design — how we build it

1. **Deterministic tools do the math; the model explains it.** The MCP tools return not just a *result* but a **rationale object** (inputs, rule id, formula, intermediate values, confidence). The customer's model turns that structured rationale into plain-language narrative. This keeps the numbers reproducible even though the prose is model-generated — critical when the customer brings their own model.
2. **Every assumption is editable and re-costs live.** BYOL/AHUB, bin-packing density, right-sizing percentile, region, pricing term — each is a first-class, visible input. Change one and the affected outputs (and their explanations) recompute, so stakeholders can see *exactly* which assumption drives which dollar.
3. **Provenance chain from output back to source file.** Each catalog entry, cost line, and wave placement links back to the exact input artifact (the RVTools row, the CMDB record, the transcript sentence that named the app owner). Nothing is asserted without a traceable source.
4. **Decision log / change history.** Every agent action and human override is recorded with timestamp, actor, before/after, and reason — producing an **audit-grade trail** that risk, finance, and compliance teams can review.
5. **Confidence, not false certainty.** Outputs carry a confidence score that rises as enrichment data improves; the planner is explicit about what it does *not* know rather than presenting a single unqualified number.

### 8.3 Why open source makes explainability a differentiator

A hosted, closed agent can *narrate* a decision, but the customer cannot inspect the underlying logic. Because our tool logic is **open and inspectable**, an enterprise (or its GSI/auditor) can read exactly how sizing, TCO, and wave grouping are computed — and even extend or override a rule for their context. **Open + explainable + provenance-tracked** is a trust posture a black-box SaaS structurally cannot match, and it is precisely what unblocks steering-committee approval.

### 8.4 Explainable exports

Explainability travels with the artifact: **PPT/PDF/XLS/CSV** exports include not just the numbers but an assumptions appendix, the rationale per recommendation, and the provenance/decision log — so the plan defends itself in a room the agent is not in.

*Prototype status: confidence scoring, editable what-if overrides, 6 pricing models, and snapshot/restore already exist. To close the gap we add: (a) a structured **rationale object** on each tool response, (b) a **provenance link** from every output to its source artifact, and (c) an **explanations appendix** in exports.*

---

## 9. Recommended priorities and roadmap

Ordered by impact ÷ cost. All delivered **in the open, on GitHub**, with the customer's model/tokens.

| # | Initiative | Impact | Dev cost | Notes |
|---|---|---|---|---|
| 1 | **Agentic planner MVP** — chat UI + MCP tools accepting mixed files, returning app catalog, dependency groups, suggested waves + rationale; persist artifacts for export | 🔴 High | 🟡 Medium | Biggest UX gap; prototype de-risks it |
| 2 | **Flexible ingestion pipeline + LM connectors** — modular parsers + LLM business-metadata extraction (RVTools, vSphere, CMDB, wiki/MD, transcripts) | 🔴 High | 🟡 Medium | Clearest differentiator |
| 3 | **Explainable TCO + downloadable artifacts** — current vs target, BYOL rules, bin-packing/sizing; PPT/PDF/XLS | 🔴 High | 🟡 Medium | Matches + exceeds competitor TCO |
| 4 | **Dependency analysis + wave optimizer** — network/port/process + CMDB business mapping → move groups; constraint controls (timeline, capacity, risk) | 🟠 High | 🟡 Medium | Directly answers AWS wave story |
| 5 | **Network translation + IaC export** — NSX/FortiGate/Palo Alto/ACI → Azure networking; ARM/Bicep/Terraform; preview/edit canvas | 🟠 High | 🔴 Higher | Answers "80x network conversion" |
| 6 | **Explainability, provenance, auditable artifacts** (see §8) — rationale object per tool output, source-to-output provenance, change/decision log, audit-grade export | 🔴 High | 🟢 Lower | **Cross-cutting** trust layer; unblocks steering-committee sign-off |

**Phasing:**
- **Phase 1 (Q1):** Initiatives 1–2 → agentic MVP + ingestion on GitHub; 3–5 design-partner customers on their own tokens.
- **Phase 2 (Q2):** Initiatives 3–4 → explainable TCO + wave optimizer; begin graduating validated pieces into the first-party service / Copilot agent.
- **Phase 3 (next):** Initiatives 5–6 → network translation + audit; partner (GSI) onboarding and community contribution model.

---

## 10. How this complements — not competes with — the first-party service

This is **not** a replacement for Azure Migrate or the Copilot migration agent. It is a **fast-moving upstream** and a **reach extender**:

- **Upstream innovation funnel:** try capabilities in the open, at speed; graduate the winners into the first-party service and the Copilot agent with real usage evidence.
- **Reach extender:** serves customers the hosted agent structurally cannot — **air-gapped, BYO-model, partner-customized** engagements.
- **Cost deflection:** moves inference cost/scale to the customer's tokens, lowering the burden of scaling agentic planning across the entire Azure Migrate base.
- **Ecosystem flywheel:** every partner/community contribution defaults migrations to Azure and strengthens the first-party roadmap.

---

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Brand/quality of an open repo** | Ship under a governed org with clear "reference/preview" labeling, CI, security scanning, and a graduation bar into first-party. |
| **Fragmentation vs first-party** | Single roadmap owner; explicit graduation pipeline; shared data models with the service. |
| **Support expectations** | Community-support model for OSS; first-party SLA only for graduated features. |
| **Security / data handling** | Local-first, zero-egress default; no secrets in repo; provenance + audit built in; align with MSFT OSS + security review. |
| **BYO-model output variability** | Deterministic tools do the math; the model orchestrates and explains. Guardrails + eval harness on tool outputs. |
| **Competitive optics** | Frame as customer empowerment + ecosystem, consistent with Microsoft's open-source leadership (VS Code, TypeScript, .NET, MCP). |

---

## 12. The ask

We request leadership sponsorship to:

1. **Charter a 4–6 person open-source v-team** within Azure Migrate for two quarters.
2. **Stand up a governed public GitHub repo** for the agentic migration planner (MCP tools + reference chat UI + ingestion + IaC), seeded from the existing prototype.
3. **Recruit 3–5 design-partner customers/GSIs** to validate on their own models/tokens.
4. **Define the graduation pipeline** from OSS → first-party Azure Migrate service and Copilot migration agent.

**Success metrics (2 quarters):**

*Delivery (did we ship):*
- MVP live on GitHub; **Stage-0 "first glimpse"** (upload → app catalog + rough TCO + draft waves) in **< 10 minutes** on customer data.
- **3+ design partners** running on **their own model/tokens** (including at least one on **Azure OpenAI / Foundry**); **1+ GSI** customization.
- **2+ capabilities graduated** into the first-party service/Copilot agent.

*Customer outcome (did it move the business):*
- At ≥1 design partner, measurably **reduce time-to-first-credible-plan** (target: weeks → days), and progress **≥1 planned wave into actual migration/replication** within the pilot.
- Demonstrated **inference-cost deflection** vs hosting equivalent conversations on first-party tokens, plus **qualified Azure migration pipeline** influenced by the pilots.

---

## Appendix A — Prototype evidence (this repository)

The existing `AzureMigrateSimulations` prototype already demonstrates the core architecture:

- **MCP server, 60+ agent tools** (discovery, list/inspect VMs & workloads, cloud topology + WAF, what-if simulation, wave planning, overrides, SKU catalog, business case, enrichment, vulnerability/SLA, CSV export) — consumable **today** by GitHub Copilot, Claude Desktop, Cursor, Windsurf, Continue, Cline, and custom agents.
- **Offline / air-gapped:** discovery via pyVmomi *or* JSON/RVTools import; **zero data egress**.
- **Assessment depth:** 70+ SKUs, **6 pricing models** (PAYG, 1yr/3yr RI, 1yr/3yr SP, AHUB, Dev/Test), P95 right-sizing, confidence scoring.
- **Enrichment loop:** ingests **8 APM tools** (Dynatrace, New Relic, Datadog, Splunk, Prometheus, AppDynamics, Zabbix, custom).
- **Cloud Topology Diagram + IaC:** CAF-aligned landing zone with WAF scoring; **Terraform/Bicep generation**.
- **What-if + wave planning:** per-VM/per-workload overrides, fleet simulation, 12-month projection, drag-and-drop waves, snapshot/restore.

## Appendix B — Sources

- Azure Migrate overview & migration phases — Microsoft Learn (`migrate-services-overview`), incl. **Azure Migrate Collector** for air-gapped/quick-snapshot discovery and **business case** (TCO, CapEx→OpEx, YoY cash flow).
- **Azure Copilot migration agent (preview)** — Microsoft Learn (`azure-copilot-migration-agent`): conversational strategy/inventory/business-case/readiness/landing-zone reasoning; RVTools ingestion; **PPT export**; plan-only (execution in portal); requires Azure Copilot + Agents preview; **not supported with BYO storage for conversation history**.
- **AWS Transform for VMware** — aws.amazon.com/transform/vmware: *"first agentic AI service for migrating VMware workloads at scale"*; discovery/dependency mapping/wave planning/network conversion/execution; **up to 80x** network conversion; RVTools ingestion; TCO/business case in minutes; IaC output (CloudFormation/CDK/Terraform/LZA); rehost or replatform to ECS/EKS; customer proof points (CSL >10x, Vector Limited +30%).
- **AWS Transform** also spans **mainframe** and **.NET** modernization use cases (aws.amazon.com/transform).
- Prototype: `docs/PRODUCT_STORY.md`, `docs/AI_AGENT_INTEGRATION.md` in this repository.

> _Note: competitive figures (80x, 10x, 30%) are the vendor's own published marketing/case-study claims and should be cited as such in leadership discussions._
