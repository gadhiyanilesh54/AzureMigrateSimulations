# Azure Migrate AI Feasibility Assessment

## Executive Decision Memo

**From application discovery to an actionable AI modernization decision**

**Audience:** Vice President, Azure Migrate, and cross-Microsoft stakeholders  
**Date:** 22 September 2026  
**Status:** Proposal for investment discussion, not an approved roadmap

**Simulator prototype update (2 October 2026):** This repository now implements a bounded,
local demonstration of the proposed customer decision flow: application selection, seven solution
ideas, guided or uploaded intent, evidence provenance, deterministic indicative costing, persisted
assessment revisions, Foundry-assisted narrative generation, and optional AI-ready landing-zone
composition. This implementation does not change the proposal's production, security, ownership,
commercial, or roadmap caveats.

For the source-backed customer/FDE journey, application example, AI service choices, costing, CTD integration, and PoC plan, see [the end-to-end walkthrough](Azure_Migrate_AI_Feasibility_EndToEnd_Walkthrough.md). It distinguishes existing implementation from proposed capabilities and includes a stakeholder demo script.

### The Proposal

Help customers answer: **"How can I use AI in my applications and organization, and where should I start?"**

Introduce an opt-in AI Feasibility Assessment in Azure Migrate that combines discovered application context with customer-confirmed business goals and data constraints. It produces a prioritized set of AI opportunities, the evidence and gaps behind each one, a proposed architecture, an indicative business case, and an owner-ready path into a proof of concept (PoC).

Azure Migrate would own the application-to-opportunity assessment and decision record. Microsoft Foundry, Copilot Studio, GitHub Copilot modernization, customer teams, forward-deployed engineers (FDEs), and qualified AI consulting partners would provide the appropriate implementation path. These are proposed collaboration roles, not agreed commitments.

### Why This Matters

Migration conversations establish what customers run, how applications depend on one another, and what modernization could cost. The next investment question is what new business capability those applications could deliver with AI. Today, that question often requires a separate consulting exercise to reconstruct application context and connect it to a business workflow.

The opportunity is to shorten that transition: **reuse discovery, qualify the opportunity, and transfer a usable brief to the team that can deliver it.** The differentiated asset is the permissioned application context and assessment workflow, not a general-purpose chatbot or a proprietary foundation model. Existing application assessment and portfolio-to-code-modernization capabilities provide relevant foundations, but do not by themselves prove that the proposed AI opportunity assessment exists or will work. [S1, S2]

### The Customer And Microsoft Value

| Beneficiary | Proposed value | Evidence needed before scaling |
| --- | --- | --- |
| CIO and business owner | Prioritized AI investments tied to owned workflows. | An approved next step and budget. |
| Architect and application owner | Reusable context, explicit gaps, and defensible choices. | Less assessment effort at equal quality. |
| Microsoft field and partners | Qualified engagements with evidence and an owner. | Accepted handoffs and customer-owned PoCs. |
| Azure Migrate and Microsoft | Modernization relevance and incremental AI adoption. | Attributable production outcomes and usage. |

### The Investment Decision

**Recommendation: approve a gated, 12-week validation program, not a general-availability commitment.** Recruit 10 design-partner customers and evaluate 30 application/workflow pairs. Start with internal knowledge assistance and document-workflow assistance; make read-only, human-reviewed recommendations. Produce an assessment report and partner handoff before investing in broad automation.

The planning envelope is **7 full-time-equivalent contributors for three months**, including shared specialists. At an illustrative fully loaded rate of **USD 25,000 per FTE-month**, plus **USD 25,000 of non-labor reserve**, the envelope is **USD 550,000**. Finance and engineering must replace these assumptions with internal rates and availability before spending approval. No headcount, partner capacity, or funding is committed by this proposal.

Authorize one Azure Migrate accountable owner and request counterpart owners from CoreAI/Foundry and the field delivery organization. At weeks 2, 6, and 12, review evidence, quality, cost, and customer commitment. Continue only if the pilot demonstrates useful recommendations, reduced assessment effort, secure handling, and accepted delivery handoffs. Stop or narrow the scope if a questionnaire-only approach performs just as well.

### What We Will Not Promise

Infrastructure discovery does not establish business value, document quality, data-use rights, API safety, or organizational readiness. Missing evidence must remain visible. The assessment is not a production-readiness certification, autonomous deployment service, or replacement for an enterprise AI strategy.

The recommendation may be to adopt an existing Copilot or SaaS capability, use conventional automation, remediate data first, or not use AI. Full application migration is not a prerequisite for every AI scenario. A credible negative recommendation is a successful assessment, not a failure to sell AI.

### Decisions Requested From Leadership

1. Sponsor the bounded validation program and nominate the Azure Migrate decision owner.
2. Endorse the ownership boundary: Azure Migrate qualifies opportunities; implementation platforms and delivery teams build them.
3. Sponsor exploratory agreements with CoreAI/Foundry, FDE leadership, and AI consulting partners, with named owners and capacity confirmed at the first gate.
4. Approve customer recruitment and the proposed evidence, safety, and commercial evaluation criteria, subject to privacy and legal review.
5. Require a week-12 investment review before committing to preview scale, pricing, or a launch date.

---

## 1. Customer Problem And Strategic Opportunity

### The Unanswered Investment Question

A customer can know which servers to migrate and still not know which business workflow is worth transforming with AI. Application owners need a decision about a specific outcome: reduce time spent finding answers, extract information from documents, improve decision support, or remove repetitive work. They also need to understand why a scenario is feasible, what could prevent it, and who will implement it.

The proposed product connects three perspectives that are often evaluated separately: **business opportunity, application feasibility, and delivery readiness**. It should answer six questions:

1. Where could AI improve a named workflow, for which users, and against what baseline?
2. Why is this application a credible candidate, and what evidence is missing?
3. Should the customer adopt, extend, build, use non-AI automation, or defer?
4. What data, application changes, controls, skills, and operating model are required?
5. What are the cost range, expected benefit, and conditions for a worthwhile investment?
6. What is the smallest safe PoC, who owns it, and what must it prove?

At organizational level, aggregate validated application opportunities into a portfolio view of common data gaps, reusable capabilities, skills needs, and investment waves. Do not infer an entire organization's AI strategy from the subset of its estate visible to Azure Migrate. Microsoft Cloud Adoption Framework guidance already provides a business-first adoption framework; this feature would operationalize an application-specific part of it. [S3, S4]

### Initial Customer And Buyer

Start with enterprise customers already assessing .NET or Java line-of-business applications in Azure Migrate, with identifiable application owners and a business sponsor. Favor internal support and document-handling workflows where assistance can be human-reviewed and a baseline can be measured.

The CIO or modernization sponsor is the economic buyer; enterprise architects and application owners are the primary users. Business process owners validate the benefit. Data owners and security teams authorize access. Delivery teams consume the handoff. This creates a bridge from an infrastructure-led engagement to business and AI stakeholders without assuming the infrastructure owner can approve every data source.

Exclude from the initial pilot autonomous financial transactions, high-impact eligibility decisions, safety-critical workflows, unrestricted production database access, and applications with no accountable owner. Customers without adequate discovery can use a clearly labeled questionnaire-led starting point, but must not receive the same evidence confidence as an observed estate.

### Why Now, And Why Azure Migrate?

Azure Migrate already supports application assessment and dependency-informed modernization planning. Documented integration with GitHub Copilot modernization provides a relevant precedent for moving from portfolio assessment to developer action. Foundry and Copilot Studio provide downstream implementation choices. The proposed investment is the missing decision and handoff layer between estate understanding and an AI implementation engagement. [S1-S4]

The hypothesis is that reusing application context reduces assessment effort and improves relevance compared with a generic AI workshop. It is not yet a proven market demand or defensible revenue forecast. Validate willingness to share context, accept recommendations, and sponsor a PoC before broad engineering investment.

## 2. Positioning And Product Boundaries

**Positioning:** Azure Migrate AI Feasibility Assessment turns discovered application context into evidence-backed AI investment choices and implementation briefs.

| Adjacent offering | Its role | Proposed Azure Migrate role |
| --- | --- | --- |
| Existing Azure Migrate assessments and assistant experiences | Migration readiness, target configuration, cost, and help navigating the migration journey. | Decide which business capabilities could benefit from AI; reuse existing assessment results and surfaces. |
| Microsoft Foundry / CoreAI capabilities | AI model and application development, evaluation, and operations. | Supply a qualified use case, permissioned context, constraints, and an evaluation brief. Do not build another AI development platform. |
| GitHub Copilot modernization | Code-level modernization and remediation. | Identify prerequisite modernization and hand over an approved plan. Do not replace developer tools. |
| Microsoft 365 Copilot, Copilot Studio, and business SaaS | Packaged productivity, extensibility, low-code agents, and domain capabilities. | Recommend adopt or extend when this is better than a custom application. |
| FDEs, solution architects, and AI consultants | Domain discovery, solution design, implementation, and customer adoption. | Reduce repeated fact gathering and provide qualified demand; retain human accountability for delivery. |

These boundaries are recommendations for alignment, not assertions about current reporting lines or a completed competitive analysis. At the first gate, compare the actual roadmaps with their owners and merge overlapping work rather than launch a competing experience.

### Options Considered

| Option | Strength and limitation | Recommendation |
| --- | --- | --- |
| Content and questionnaire only | Fast and inexpensive; weak use of estate evidence. | Use as the pilot comparator and a fallback for incomplete discovery. |
| Evidence-backed assessment plus partner handoff | Reuses Migrate context while keeping implementation with established platforms and teams. | Recommended investment boundary. |
| End-to-end autonomous AI builder in Azure Migrate | Broader ambition, but duplicates platforms and substantially increases access, safety, and support obligations. | Not proposed. |
| Consulting-only offering | Strong domain depth, but less repeatable and harder to scale. | Use a concierge pilot to discover repeatable product behavior, not as the permanent default. |

The unit of assessment is an **application plus a business workflow**, not a server and not the organization as a whole. One application may have several opportunities; one workflow may cross multiple applications. Preserve this distinction in scope, counting, cost attribution, and ownership.

## 3. Customer Experience And Outputs

### Discover To Deliver

1. **Select and confirm scope.** Choose applications in a Migrate project. Confirm owners, dependencies, missing components, and the freshness of discovery. Show coverage before asking for AI goals.
2. **Describe the outcome.** Capture the workflow, users, current volume and effort, pain point, target KPI, data owner, compliance restrictions, budget, and delivery owner. Offer a short guided interview; do not require a long consulting questionnaire to start.
3. **Authorize assessment.** Show the exact data categories, model-processing boundary, retention policy, and optional partner sharing. Existing Migrate access is not blanket permission to inspect business documents or source code.
4. **Evaluate alternatives.** Apply evidence and policy gates, select from approved patterns, and compare adopt, extend, custom build, non-AI, and defer. Generate zero to three qualified opportunities, not a quota of ideas.
5. **Review the decision.** Show benefits, feasibility by dimension, confidence, gaps, architecture, cost assumptions, and a next step. Let owners correct facts, reject recommendations, and request reassessment.
6. **Accept a handoff.** Export a reviewable brief or, after separate approval and integration work, send it to the chosen delivery platform or partner. Track acceptance, owner, planned PoC, and reasons for rejection.
7. **Close the loop.** Record PoC findings, production decisions, adoption, and outcomes at 30, 60, and 90 days. Use permissioned outcome metadata to improve patterns; do not silently reuse customer content for model training.

### The Assessment Pack

| Artifact | Required contents |
| --- | --- |
| Executive decision | Recommended action, business outcome, accountable owner, benefit range, investment range, and decision conditions. |
| Opportunity card | Named workflow, users, alternatives considered, evidence, missing information, controls, confidence, and why this opportunity ranks ahead of others. |
| Readiness and gaps | Business, data, integration, security, operating-model, and economic findings; gap owner and remediation action. |
| Architecture pair | Observed current-state topology and proposed target pattern, visibly separated; data flows, trust boundaries, and components that require verification. |
| PoC and delivery brief | Acceptance tests, representative evaluation data requirements, work packages, skills, effort range, rollback, handoff recipient, and production gates. |
| Portfolio view | Ranked opportunities, common blockers, shared investments, and delivery waves; avoid double-counting shared data platforms or workflow benefits. |

A technical shortlist can be produced without complete business context. An investment recommendation cannot. The product must state which kind of output the customer is reading.

## 4. Evidence And Assessment Method

### What Discovery Can And Cannot Tell Us

| Signal | Legitimate use | What it does not prove |
| --- | --- | --- |
| Runtime, framework, hosting, versions | Identify likely integration options and modernization prerequisites. | The application's business purpose, source-code quality, or effort to change it. |
| Application groupings and dependency observations | Establish a starting scope and possible integration boundaries. | A callable API, supported business operation, or complete business-process map. |
| Database or file-service presence | Identify candidate systems to discuss with data owners. | Document contents, data quality, usage rights, labels, or retrieval permissions. |
| Performance metadata | Inform existing application capacity and the integration baseline. | Token demand, AI quality, model throughput, GPU needs, or AI run cost. |
| Owner-supplied workflow and data context | Establish goals, constraints, and benefit assumptions. | Independent validation; record who supplied it and what remains to be tested. |

The original concept's inference that a document repository or an API exists must become a hypothesis until corroborated. An architecture diagram can show observed connections, but inferred edges and proposed components need different labels. Absence of an observed dependency is not evidence that no dependency exists. [S1, R7]

### Progressive Evidence Collection

**Baseline:** reuse authorized configuration, application, dependency, and assessment metadata. Do not expand appliance privileges or collect source code, credentials, production records, or document contents for the pilot.

**Qualification:** require customer confirmation of the workflow, pain point, owner, data availability, rights, volume, and restrictions. Unknown answers are acceptable and become explicit gaps. Business context is optional for initial exploration but required to claim business fit.

**Deep validation:** a delivery team may later perform separately consented code analysis, data profiling, API testing, or sample evaluation in an approved customer environment. Those capabilities are not assumed to exist in the Migrate discovery pipeline. Carry validated findings back as signed-off evidence summaries.

Each evidence item needs an identifier, source, timestamp, application/workflow scope, authorization context, and classification: **observed, customer-provided, inferred, or missing**. An inference cannot be cited as an observation. Contradictory or stale evidence triggers review rather than a silent confidence increase.

### Decision Logic

Apply hard gates first: permitted use, authorized data, owner, regional constraints, and prohibited actions. Then assess dimensions independently:

| Dimension | Assessment question | Evidence required to improve confidence |
| --- | --- | --- |
| Business fit | Is there a measurable workflow problem worth solving? | Owner-confirmed baseline, users, volume, outcome, and alternatives. |
| Data readiness | Can the scenario use relevant, current, permitted data? | Data owner, sample-quality findings, access model, and usage rights. |
| Integration readiness | Can the capability connect safely and reliably? | Verified API or approved integration design, authentication, and change ownership. |
| Security and governance | Can the intended use meet policy and control requirements? | Risk review, identity boundaries, audit needs, residency, and approval requirements. |
| Delivery and operations | Can the customer build, support, and adopt it? | Named team, skills, monitoring, fallback, adoption plan, and support budget. |
| Economics | Is the expected outcome worth the full incremental cost? | Customer-approved assumptions, downside case, and PoC measurement plan. |

Use explicit dispositions: **PoC candidate**, **remediate first**, **insufficient evidence**, **adopt/extend an existing product**, or **do not pursue AI**. "PoC candidate" means justified experimentation, not production-ready.

If a portfolio ranking is useful, use transparent, customer-adjustable prioritization criteria after safety gates. Keep feasibility separate from business value and evidence confidence. Do not present model confidence as a calibrated probability of success. Explain rank changes and preserve prior assessment versions.

The rules engine controls eligibility and missing evidence. An LLM can match approved patterns and draft explanations. Deterministic validation checks evidence references, contract shape, disallowed actions, catalog versions, and cost arithmetic. Expert review remains mandatory in the pilot. Platform evaluators can assist with groundedness and safety, but do not substitute for domain validation. [S6]

## 5. Initial Scope And Illustrative Customer Case

### Focused Scenario Catalog

| Scenario | Initial scope | Qualification and boundary |
| --- | --- | --- |
| Internal knowledge assistance | Pilot | Permission-aware retrieval and cited answers; human review and an explicit "cannot answer" path. |
| Document-workflow assistance | Pilot | Extraction, classification, or draft summaries for human approval; verify document rights and representative quality. |
| Read-only operational assistance | Follow-on | Query approved business APIs; never infer API suitability from a network edge. |
| Predictive analytics or forecasting | Referral first | Route to appropriate Fabric / Azure Machine Learning expertise; requires historical data and statistical validation. |
| Autonomous, write-capable agents | Outside initial scope | Separate controls, transaction authorization, reversibility, and production approval are required. |

For each opportunity, compare packaged capabilities before custom build. Microsoft's published adoption guidance explicitly distinguishes ready-to-use Copilots, low-code development, managed AI platforms, and self-managed infrastructure. The proposal follows that choice model. [S3]

### Example: Contoso Order Management

**Illustrative only. No customer findings or performance results are claimed.** Assume discovery shows a legacy .NET web tier, SQL Server, and several service connections. The application owner confirms that support employees repeatedly search policy documents and order records; the data owner confirms a candidate document repository. Discovery has not inspected those documents or validated the service interfaces.

The preferred first experiment is an **internal support assistant**, not an autonomous order-management agent. Compare an existing service-product capability, a Copilot Studio extension, and a custom Foundry application before selecting the implementation.

| Finding | Disposition and next action |
| --- | --- |
| Repeated support searches, supplied by the workflow owner | Measure task volume, completion time, and answer quality against the existing workflow. |
| Candidate policy content, supplied by the data owner | Verify currency, rights, document-level permissions, and answerability on an approved sample. |
| Service dependencies observed, API semantics unknown | Validate a read-only order-status endpoint; omit live order access until authorization and tenant isolation are proven. |
| Legacy application runtime | Evaluate a side-by-side assistant integration; do not presume a full rewrite or migration is necessary. |
| No verified financial baseline | Provide a scenario model, not a claimed ROI; request owner approval before qualification. |

Illustrative target pattern:

```text
Employee + enterprise identity
		 |
    Assistant in approved user experience
		 |
    Application-owned authorization boundary
	    /                         \
 Permission-filtered retrieval   Read-only business API
	    |                      (only after validation)
 Approved knowledge content            |
	    |                       Order application
 Model inference + cited answer
		 |
 Human decision / existing workflow

Across the flow: audit, quality evaluation, cost limits,
access controls, monitoring, and fallback to existing search.
```

The customer retains the existing workflow when the assistant is unavailable or uncertain. A model has no direct database credential and cannot submit payments, refunds, or order changes in this experiment.

### PoC To Production

The handoff proposes a four-to-six-week customer PoC after approvals, with duration dependent on access and integration work. Build a representative, permissioned evaluation set and hold back examples for final validation. Include unanswered questions, stale content, unauthorized users, and incorrect order identifiers.

Agree task-specific targets before implementation: answer usefulness and correctness, permission enforcement, human-review effort, task completion time, acceptable latency, and cost per completed task. Permission-leak tests must pass with no known unresolved violations; passing a finite test set is not a guarantee of zero future incidents.

A pilot then tests actual adoption in a limited user group. Production approval requires the application owner, data owner, security reviewer, and delivery team to accept measured quality, monitoring, escalation, rollback, support ownership, and costs. An assessment report alone cannot authorize production deployment.

## 6. Cross-Microsoft And Partner Operating Model

### Give Each Partner A Concrete Role

All engagements below are **proposed**. Confirm organizational ownership, program eligibility, staffing, commercial terms, and willingness to participate; do not represent internal organizations as committed delivery capacity.

| Proposed counterpart | Contribution and benefit | Initial agreement to request |
| --- | --- | --- |
| Azure Migrate product and engineering | Own customer entry point, consent, evidence profile, assessment record, prioritization, and handoff tracking. | One accountable PM and engineering lead; approved scope and service boundary. |
| CoreAI / Microsoft Foundry | Advise on model selection, evaluation, safety, approved solution patterns, and platform handoff. Receives qualified application opportunities and implementation feedback. | Named product and engineering counterparts; joint rubric and two reviewed patterns by week 6. |
| FDE leadership and participating teams | Validate difficult integrations and the first repeatable reference implementations. Receives bounded problems with owners and evidence. | Capacity for a small number of nominated cases, not a standing dependency for every assessment. |
| Field solution architects and account teams | Recruit customers, identify business sponsors, qualify demand, and coordinate delivery. | Ten design partners, qualification criteria, and an accountable engagement owner per customer. |
| AI consultants, systems integrators, and specialist partners | Supply domain context, scope and build solutions, support adoption, and return outcome findings. Gains qualified services opportunities. | Two or three opt-in pilot partners; standard handoff, customer consent, delivery scope, and feedback obligations. |
| GitHub Copilot modernization team | Handle code-level remediation prerequisites and developer execution. | Reuse an agreed report/task handoff where supported; no assumed new automation. |
| Copilot Studio / Microsoft 365 counterparts | Validate adopt/extend routes so a custom build is not the default. | Catalog decision criteria and route qualified opportunities to the right team. |
| Data, security, and governance counterparts | Review data readiness, identity, protection, and compliance needs; involve Fabric, Purview, and Entra expertise where relevant. | Shared review checklist and escalation path, not mandatory attachment of every service. |

### Handoff As A Product Contract

The receiving team gets a versioned brief containing the business sponsor, application/workflow identifier, consent scope, evidence snapshot, baseline, selected pattern, alternatives, blockers, architecture, cost assumptions, evaluation plan, delivery owner, and expected decision date. No credentials or unrestricted source data are included.

A handoff is complete only when the recipient accepts ownership and a next action. Record decline reasons and allow customer reassignment. Propose a five-business-day response target for pilot participants, subject to their agreement. Use downloadable artifacts first; add direct Foundry, developer-tool, or partner-system integrations only after owners approve contracts and permissions.

Azure Migrate remains responsible for assessment behavior and defects. Delivery teams own implementation quality within the agreed statement of work. The customer owns data-use authorization, business acceptance, and production operation. Security and legal approval follows existing organizational processes; the feature does not confer a new certification.

### Governance And Partner Incentives

Run a weekly product/field triage and a monthly cross-team steering review. Maintain one backlog for evidence gaps, rejected recommendations, and reusable patterns. Azure Migrate is accountable for the customer decision experience; platform teams remain accountable for their services. Resolve duplicate roadmap work before adding a new service.

Partners should gain better-scoped engagements, not compete against a free implementation service. Keep partner selection transparent and customer-controlled. Disclose relevant commercial relationships, avoid pay-to-rank recommendations, and do not reward teams merely for generating AI opportunities. Reward accepted handoffs and verified outcomes, including justified no-build decisions.

## 7. Economics And Commercial Strategy

### Customer Value Model

Treat benefit as a hypothesis to measure. Use customer inputs for workflow volume, minutes saved, adoption, realized productive use, and loaded labor rate. Separate productivity capacity from actual cash savings; only the customer can establish whether released capacity reduces cost or improves output.

```text
Monthly capacity value = eligible tasks x minutes saved / 60
			     x adoption x realization x hourly value
Monthly net benefit   = monthly capacity value - incremental run cost
Simple payback        = one-time cost / positive monthly net benefit
```

Include integration and data preparation, licensing, inference, retrieval, storage, hosting, network transfer, evaluations, security, human review, content upkeep, support, training, and change management. Do not infer usage from CPU utilization. Quote the region, model, date, usage assumptions, and commercial agreement for any actual estimate. Keep base migration costs and savings separate to avoid double-counting.

**Illustrative customer sensitivity, not Azure pricing or a forecast:** 12,000 eligible tasks per month, USD 35/hour, USD 90,000 total one-time investment, and USD 4,500 incremental monthly run cost. The run-cost allowance comprises USD 1,500 technology/services and USD 3,000 review, content maintenance, and operations; all must be replaced by measured or quoted inputs.

| Scenario | Minutes / adoption / realization | Monthly value / net benefit | Simple payback |
| --- | --- | --- | --- |
| Downside | 3 / 30% / 50% | USD 3,150 / -1,350 | No payback under these assumptions. |
| Base | 5 / 50% / 70% | USD 12,250 / 7,750 | 11.6 months at steady state. |
| Upside | 6 / 70% / 80% | USD 23,520 / 19,020 | 4.7 months at steady state. |

In the base case, first-year value is USD 147,000 and total first-year cost is USD 144,000: USD 3,000 net benefit, or about 2.1% simple first-year ROI. This assumes immediate steady-state adoption, excludes discounting and tax effects, and is optimistic relative to a ramped rollout. A ramp could make year-one ROI negative. The example illustrates why a plausible AI use case is not automatically an attractive investment.

### Microsoft Value And Attribution

Measure a funnel from consented assessment to validated opportunity, sponsored PoC, production deployment, and sustained incremental usage. Count unique application/workflow decisions, not repeated report runs. Track packaged-product adoption separately from Azure consumption.

For sensitivity only: 1,000 consented assessments x 30% qualified opportunities x 40% sponsored PoCs x 25% production conversion = 30 production solutions. At an assumed USD 2,000 incremental Azure consumption per solution per month, this is USD 60,000 exit monthly consumption, or USD 720,000 annualized run rate. It is **not** a bookings forecast, first-year realized revenue, or proof of incremental attribution.

Before sizing the business, obtain actual eligible-project counts, opt-in rate, workflow mix, conversion lag, capacity, delivery cost, and cannibalization. Compare participating accounts with matched or staged-rollout cohorts where practical. Subtract existing consumption and avoid claiming the same benefit for migration, AI assessment, and partner activity. Finance and field operations must agree the attribution method.

### Packaging And Route To Market

Recommend a metered, no-additional-assessment-charge design-partner pilot with explicit usage limits. Customer implementation, licenses, and Azure service charges remain separate and disclosed. This is a proposed pilot policy, not a claim that the future feature is free.

At the investment review, compare an included basic assessment with limits against a paid deep-assessment or partner-led offer. Decide based on conversion, cost-to-serve, willingness to pay, and channel feedback. Do not create a pricing dependency before usefulness is demonstrated.

Start through existing modernization engagements, then build a joint field motion with AI specialists and delivery partners. Lead with a business workflow and measured value, not a required list of Azure products. Validate a design partner's eligibility for any Microsoft funding program rather than implying automatic funding. Expansion to organizations not already using Migrate is a later distribution experiment.

## 8. Delivery Plan, Investment, And Gates

### What The 12-Week Program Delivers

The minimum viable product (MVP) is a report-first, expert-reviewed assessment using existing discovery plus a structured interview. It includes a normalized evidence profile, two approved scenario families, deterministic eligibility checks, constrained recommendation generation, indicative economics, a current/proposed architecture view, a PoC brief, and a feedback loop. A lightweight review experience is sufficient; a fully integrated production portal is not a week-12 promise.

| Period | Deliverable and accountable role | Exit decision |
| --- | --- | --- |
| Weeks 1-2: qualify | Azure Migrate PM and field lead confirm customer pain, 10 customers / 30 pairs, data rights, counterpart owners, and manual baseline. Engineering identifies actual evidence coverage. | Proceed only with approved data handling, feasible scope, and committed pilot capacity. Otherwise narrow or stop. |
| Weeks 3-6: prototype | Engineering and AI/evaluation lead implement profiles, rules, two patterns, report, evidence validation, and offline evaluation. Architects review representative and negative cases. | Approve customer-facing use only after quality, isolation, security, and cost checks. |
| Weeks 7-10: design-partner pilot | Field and partner leads run assessments, customer reviews, controlled comparisons, and accepted handoffs. | Correct material defects immediately; pause affected processing on a safety or privacy failure. |
| Weeks 11-12: investment review | PM, engineering, finance, and counterparts report full-cohort outcomes, gaps, spend, partner acceptance, and preview estimate. | Expand, narrow to a higher-value segment, remain partner-led, or stop. No automatic promotion. |

Subject to a successful gate, plan a further 12-16 weeks for a bounded private preview: product UX, contract approval, support, quotas, deletion, regional controls, telemetry, and approved integrations. Broader preview and general availability require a separate estimate, security/compliance review, operational readiness, and evidence across more customers and workload types. All timings are planning assumptions measured from approval.

### Illustrative Team And Funding

| Contribution | Average FTE for three months |
| --- | --- |
| Product management | 1.0 |
| Engineering, including backend and review experience | 3.0 |
| Applied AI and evaluation engineering | 1.0 |
| Design and research | 0.5 |
| Shared architecture, privacy, and security | 0.5 |
| Field / delivery / partner coordination | 1.0 |
| Total | 7.0 |

The USD 550,000 illustrative envelope is 21 FTE-months x USD 25,000 plus USD 25,000 non-labor reserve. It assumes fractional partner/specialist participation fits the allocation; any separately funded FDE or consulting delivery must be approved and added explicitly. It excludes broad production rollout and customer PoC implementation. Reusing people still has opportunity cost: leadership must identify displaced roadmap work, not treat reuse as free capacity.

### Success Scorecard

All thresholds are **proposed pilot gates**, not forecasts or existing results. Agree definitions before running the evaluation and report failures, abstentions, and exclusions.

| Measure | Proposed gate | How it is measured |
| --- | --- | --- |
| Useful decisions | At least 24 of 30 application/workflow pairs yield a decision accepted by the application owner and an independent architect. | Includes substantiated no-AI or remediate-first decisions; report those separately from qualified AI opportunities. |
| Factual integrity | 100% of material factual claims have resolvable evidence; no fabricated decision-critical facts in released reports. | Automated reference checks plus human evidence review. A citation must support the claim, not merely exist. |
| Assessment efficiency | At least 30% median reduction in total expert effort against manual assessment with equivalent inputs. | Include collection, correction, review, and handoff time, not just generation latency. |
| Discovery adds value | At least a 10-percentage-point acceptance improvement, or 20% less expert effort at comparable quality, versus questionnaire-only output. | Pre-specified comparison using the same workflow context and pattern catalog. If neither improves, reconsider Migrate-specific investment. |
| Customer commitment | At least 4 of 10 customers nominate a sponsor and approve a next step; at least 3 handoffs accepted and 2 PoCs started. | Written customer/recipient confirmation, not an expression of interest or a downloaded report. |
| Service cost and responsiveness | Pilot target: average variable service cost no more than USD 5 per assessment; 95th-percentile generation within 30 minutes for the agreed input cap. | Include inference, retries, retrieval, compute, and storage. Track human cost separately; set input cap at week 2. |
| Safety and privacy | No unresolved critical/high-severity assessment-control findings before pilot release; consent, isolation, access, and deletion tests pass. | Security review and negative tests, including prompt injection and cross-tenant access. |

Select 30 pairs across the 10 customers, including incomplete-data and unsuitable cases. Lock a small holdout set before tuning. Compare manual, questionnaire-only, and evidence-enriched outputs with independent reviewers blinded to the method where possible; randomize review order and avoid reusing the same reviewer in ways that transfer answers. Report customer-level variation, uncertainty, and inter-reviewer disagreement. This is directional pilot evidence, not a statistically conclusive market study.

Follow PoCs beyond week 12 to measure deployment, adoption, task success, actual costs, and value. Production conversion and attributable consumption are later outcomes; do not manufacture them to meet a short pilot deadline.

## 9. Trust, Safety, And Operational Requirements

Treat the **assessment service's own use of AI** and the **customer's eventual AI application** as separate risk boundaries. An assessment can be trustworthy while its proposed application still needs data, evaluation, and production approval.

| Risk | Required control and accountable role |
| --- | --- |
| Generic or fabricated recommendations | Rules-first eligibility, evidence-linked claims, explicit unknowns, approved patterns, and human release review. AI/evaluation lead owns regression quality. |
| Sensitive metadata or content exposure | Minimize inputs, redact secrets and personal data, separate tenants, enforce role-based access, encrypt data, and audit reads and shares. Security/privacy owner approves the data flow. |
| Prompt injection in customer-supplied text | Treat text as untrusted data; isolate instructions, validate outputs, use no write-capable model tools, and run adversarial tests. Never let the model change authorization or policy gates. |
| Wrong residency or retention assumptions | Validate the exact model, deployment type, region, stateful features, and terms. Global or DataZone processing does not imply processing stays in the resource's region. [S5] |
| Inappropriate AI scenario | Risk classification, restricted-use screening, alternatives, refusal/deferral, and specialist review. No autonomous production actions in the pilot. |
| Runaway spend or dependency failure | Input/token limits, per-project quotas, bounded retries, cancellation, budget alerts, circuit breakers, and a manual/rules-only fallback. Existing migration assessment must remain usable. |
| Stale recommendations and platform changes | Record evidence, catalog, prompt, model, policy, and price versions; expire or flag stale recommendations; re-evaluate before handoff or deployment. |
| Poor adoption or unclaimed ownership | Customer sponsor, accepted handoff, user training, task-level KPIs, and support ownership before PoC expansion. |

For the pilot, propose no raw prompts or business content in application telemetry, short-lived minimized staging, and final assessment retention under an approved project policy. Privacy review must specify durations, deletion across caches/exports, legal holds, and audit retention before onboarding customers. Platform-side storage and abuse monitoring are governed by the selected service's terms, not by the absence of application logs.

Published protections for Models sold by Azure include restrictions on use of customer inputs for model training without permission. Do not generalize those protections to every catalog model, hosting arrangement, preview feature, or partner product. Review actual terms, including abuse monitoring and stateful APIs, and disclose them accurately. [S5]

Use separate authorization for external partner sharing and for any reuse in evaluation datasets. Offer a usable metadata-only path and an explicit way to withdraw consent. The receiving partner's copy and retention obligations must be included in the handoff agreement; deleting a Migrate record does not automatically delete a downloaded report.

## 10. Product Architecture And Implementation Boundaries

### Proposed Flow

```text
Existing Migrate inventory, dependencies, assessments
			+ customer-approved workflow context
					    |
			  Consent and scope enforcement
					    |
		     Minimized, versioned evidence profile
					    |
		Deterministic gates + approved pattern catalog
					    |
		 Constrained model-assisted recommendation draft
					    |
		 Evidence / schema / policy / cost validation
					    |
			Customer and architect review
					    |
		 Assessment record + report + handoff package
					    |
	     Customer-selected platform and delivery partner
					    |
		    PoC / pilot / production outcome feedback
```

The new engineering is principally the evidence adapter, workflow questionnaire, scenario catalog, feasibility logic, evaluation suite, economics model, review experience, and handoff tracking. Reuse platform identity, assessment lifecycle, persistence, export, and operational patterns where they fit. Do not treat existing LLM integration as proof of trustworthy opportunity assessment.

The local Mongo partner pattern demonstrates versioned input contracts, asynchronous compute, output validation, persisted results, and downstream business-case integration. It is useful implementation precedent, not a complete AI contract. AI opportunities are application/workflow decisions, not compute SKU recommendations: do not force benefits, evidence gaps, or delivery ownership into infrastructure fields. [R1-R6]

### Five-Layer Mapping

| Layer | Proposed treatment | Basis and required divergence |
| --- | --- | --- |
| 1. ARM/API surface | Start with an internal pilot contract; review public resource shape before private preview. | Existing partner assessments have versioned public interfaces. No AI resource name or API version is approved here. [R1] |
| 2. ARM-facing model | Represent scope, settings, consent reference, status, and result links. | Adapt existing controller/helper separation; keep detailed business context access-controlled. [R1] |
| 3. Persisted assessment | Store evidence snapshots/references, opportunity dispositions, versions, reviews, and handoff state. | Follow entity/operations separation; add AI-specific lifecycle and deletion requirements. [R2] |
| 4. Compute contract | Version evidence, pattern/rule configuration, constraints, and structured results. Validate both input and output. | Adapt create/consume and asynchronous orchestration patterns; do not copy raw-input logging from a reference. [R3, R4] |
| 5. Integration contracts | Provide minimal, consented projections for application views, business case, reports, assistant access, and delivery handoffs. | Existing partner and application-report consumers are precedent; keep AI benefits separate from infrastructure TCO. [R5, R6] |

The output must preserve four familiar assessment dimensions: **readiness**, **sizing/capacity**, **cost**, and **modernization complexity**. For AI, sizing is conditional on measured task volume, tokens, concurrency, latency, and hosting choices, not inherited from server CPU. Complexity includes data preparation, integration, governance, and operational work. Business value and evidence confidence are additional, distinct dimensions.

The pilot does not create or repurpose container ARM resources. Existing container endpoint specifications and models remain unchanged. Container Phase 1/2a/2b target phasing is separate from this cross-application AI proposal. AKS readiness rules apply only if a later hosting choice requires that assessment; they are not evidence that an AI workflow is feasible.

### Workstreams And Dependencies

The mapping below uses the repository's workstream vocabulary for ownership discovery, not an approved implementation assignment. Primary files actually inspected are recorded in Appendix D; other integration boundaries require owner-led design during the first gate.

| Workstream and candidate repos | Pilot / follow-on boundary |
| --- | --- |
| WS3: DiscoveryService; WS6: AppCentricAssessments / AssessmentService | Read existing scoped inventory, dependencies, application membership, and assessments. Preserve lineage; no new VM-fallback logic. |
| WS5: AssessmentServiceV2 and AssessmentFunctionApps | Candidate home for lifecycle adapters and compute patterns; validate fit before adding a new assessment type. See R1-R4. |
| WS2: ApplicationMigration and ResourceProvider | Public API, authorization, and resource registration review before productized preview, not a pilot prerequisite. |
| WS7: Portal | Application entry point, consent, evidence review, comparison, and export. Start lightweight; integrate after contract agreement. |
| WS8: Query-net, agent, and Cortex repos | Expose approved structured results through existing assistant experiences; no separate general-purpose chatbot. Scope read permissions and evaluation before enabling. |
| WS9: BusinessCaseService, Reporting, MigrationMgmtSvcs | Separate AI opportunity economics, export, ownership, and delivery milestones from migration costs. See R5-R6 for existing patterns. |
| WS10: IntegrationTests; WS11: ServiceCommon / AssessmentService | Contract, tenancy, consent, deletion, failure, export, and regression tests; align common identity and settings. |
| WS13: RegionBuildout; WS14: Geneva | Reuse approved service deployment and telemetry conventions where applicable; validate regional compute, cost, model-call metadata, and incident routing. |
| WS1, WS4, WS12: discovery agent, appliance, and fabric-agent repos | No new agent collection or privilege changes proposed in the pilot. Any new collector capability requires a separate consent and scope decision. |

Dependency order is: scope and data rights -> evidence contract -> rules/patterns and evaluation -> controlled pilot outputs -> accepted handoff -> public contract and operational hardening. Portal, HA/application views, business case, assistant, and reporting consume the same validated record rather than regenerate contradictory recommendations. Reuse OneAKS/Geneva conventions where the owning service uses them; do not assume model inference must run on that cluster. Production topology remains an engineering decision.

## 11. Leadership Decision And Immediate Actions

Approve the validation program only with a named owner, an agreed capacity envelope, and permission to stop. The product thesis is attractive because it uses an existing customer decision point; the pilot must prove that it adds material value beyond a questionnaire and a skilled consultant.

Within the first two weeks, the accountable team should return with customer commitments, counterpart names, a product-overlap review, authorized data flows, confirmed evidence coverage, evaluation definitions, and an internal-cost estimate replacing the illustrative envelope. Before customer-facing generation, security and domain reviewers must approve the release controls.

At week 12, leadership should see actual assessment packs, customer corrections, negative decisions, paired baseline results, accepted handoffs, incurred cost, and a scoped next-stage proposal. The decision is not "Can an LLM write a convincing AI roadmap?" It is **"Can Azure Migrate help customers make better AI investments and reach a measurable next step?"**

---

## Appendix A. Leadership Questions And Answers

### 1. What Is The One-Sentence Value Proposition?

Use the application's discovered context and customer goals to identify credible AI opportunities, explain what makes them feasible, and connect the customer to an accountable implementation path.

### 2. Why Should Azure Migrate Own This?

Migrate already participates in the decision about an existing application's future. Reusing that context can reduce discovery repetition and connect migration investment with new business value. Ownership should stop at qualification and handoff; the pilot must prove the context is useful enough to justify the feature.

### 3. Is This Just Another Copilot?

No. The product is a structured assessment and decision record, accessible through existing interfaces. Conversation can help collect context or explain findings, but the deliverable is a reviewable opportunity, evidence, economics, and implementation brief.

### 4. Does It Compete With CoreAI Or Foundry?

It should supply their development and runtime platforms with better-qualified opportunities. Joint ownership of patterns and evaluations can reduce duplication. This boundary requires roadmap alignment; it cannot be assumed from organizational labels.

### 5. Why Not Let A Generic LLM Read A Questionnaire?

That is the explicit comparator. If scoped discovery does not improve recommendation acceptance or reduce expert effort, a lighter shared questionnaire or partner offering may be the better investment. The proposal is designed to test this, not dismiss it.

### 6. Can We Really Answer An Organization-Wide AI Strategy Question?

We can provide an application-grounded starting point and portfolio insights within observed coverage. We cannot infer business priorities, workforce readiness, legal constraints, or undiscovered SaaS/processes. Enterprise strategy still requires business leadership and specialist input.

### 7. Do We Need Source Code Or Customer Documents?

Not for initial triage. Discovery metadata plus a structured interview can support hypotheses. Code remediation, data-quality claims, API safety, and application-level accuracy require additional authorized validation. Those deeper activities belong in a separately scoped engagement.

### 8. What If The Customer Has No Clear Use Case?

Use a short workflow interview and approved patterns to surface candidate problems. Keep outputs exploratory until an owner confirms a measurable outcome. Do not manufacture business intent from database names or application frameworks.

### 9. Will Every Application Get An AI Recommendation?

No. The correct decision may be insufficient evidence, remediate first, use an existing product, conventional automation, or no AI. Requiring a fixed number of opportunities encourages generic recommendations and damages trust.

### 10. Must The Customer Migrate First?

No. A side-by-side or hybrid integration may be the best first experiment. Compare add-AI-now, modernize-then-add-AI, and migrate-without-AI where relevant. Document network, identity, and latency constraints instead of requiring migration to justify an AI project.

### 11. How Is It Different From AI-Assisted Code Modernization?

Code modernization changes how an application is built or hosted. This assessment asks which new business capability is worth adding and what must be true to deliver it. Code tools can execute prerequisites; they are not replaced.

### 12. How Do We Prevent Hallucinated Facts And False Precision?

Separate observed, supplied, inferred, and missing evidence; validate claim references; use deterministic gates and calculations; constrain pattern choices; require expert release review. Use ranges and explicit unknowns rather than a universal AI-readiness score.

### 13. What Can We Tell Customers About Privacy?

Only what the approved data flow and selected service terms support. Explain input categories, access, residency, retention, model processing, and partner sharing. Do not say data never leaves a region or is never retained without checking deployment and feature behavior. [S5]

### 14. Who Is Accountable For A Bad Recommendation?

Azure Migrate owns assessment defects and correction mechanisms. Delivery teams validate implementation assumptions; the customer authorizes data use and production operation. Legal and support teams must define appropriate product terms and escalation before release. Human review does not eliminate Microsoft's product responsibility.

### 15. How Do We Avoid Building A Services Organization?

Use human-led early assessments to identify repeatable work, then productize evidence assembly and decision artifacts. Keep implementation with customer teams and delivery partners. Track human hours per assessment; a permanently high-touch result is a signal to retain a partner-led offer rather than hide the cost.

### 16. Will Partners View This As Competition?

Some may if the assessment is positioned as replacing consultants. Position it as a qualified starting brief, give partners useful context and delivery opportunities, and preserve customer choice. Test partner acceptance and engagement economics, not just partner enthusiasm.

### 17. What If FDE Capacity Is Unavailable?

FDE participation accelerates difficult reference cases but must not be required for every customer. Use field architects, willing delivery partners, and customer teams for routine pilots. Narrow the scenario scope if specialist capacity is essential and unavailable.

### 18. How Much Will It Cost, And What Is Displaced?

The illustrative pilot is USD 550,000 over 12 weeks, subject to internal rates and confirmed staffing. Production and customer implementation costs are additional. Identify the work displaced by shared engineering and field capacity; reuse is an allocation decision, not free funding.

### 19. What Is The Revenue Or Consumption Opportunity?

It is not yet quantified from real funnel data. The scenario in Section 7 demonstrates the drivers, not a forecast. Use qualified opportunities, production conversion, time lag, incremental usage, cost-to-serve, and an agreed attribution method before claiming a financial return.

### 20. How Do We Prove Customer ROI?

Baseline the task, instrument adoption and completion quality, include human review and operating cost, and compare outcomes with an appropriate control or staged rollout. Distinguish productive capacity from cash savings. The downside case must remain visible when seeking approval.

### 21. What Will We Actually Ship In 12 Weeks?

A bounded, reviewed assessment experience and exportable handoff for two scenario families, plus pilot evidence. Not autonomous implementation, broad connector coverage, universal compliance, or a production SLA. Private preview requires a separate hardening phase.

### 22. How Will We Handle Model And Service Changes?

Version inputs, rules, patterns, prompts, models, and prices. Run regression and safety checks before promoting a change, preserve prior decisions, and flag stale reports. Reassess before an implementation decision when constraints or service availability change.

### 23. Is The Approach Defensible Against Competitors?

The potential advantage is context continuity, customer trust, integration into modernization decisions, and a delivery ecosystem. Competitors and partners can also assess portfolios. Validate differentiation through comparative customer outcomes, not an unsupported claim of unique technology.

### 24. When Do We Stop Or Pivot?

Stop or narrow when discovery adds no measurable value, customers will not provide needed context, recommendation quality is inadequate, controls cannot be met, or handoffs do not lead to committed action. A useful but consistently consulting-heavy result may justify a partner-led offer instead of a broadly self-service feature.

### 25. What Is The Expansion Path?

After evidence supports it: more workflow patterns, richer opt-in validation, portfolio prioritization, deeper platform handoffs, and reusable industry packages. Expand to higher-risk automation only with separate controls and measured reliability. Do not make broad coverage a prerequisite for proving the initial value.

---

## Appendix B. Proposed Assessment And Handoff Record

This is a conceptual contract for discussion, not a new ARM schema or approved API. A machine-readable record should accompany the human report so recipients do not have to reconstruct assumptions from prose.

| Record group | Minimum fields and validation |
| --- | --- |
| Identity and lifecycle | Assessment ID, project/tenant scope, application/workflow IDs, version, status, owner, timestamps, expiry, and superseded record. |
| Authorization | Allowed input categories, purpose, approver, consent reference, permitted recipients, retention/deletion policy reference. |
| Evidence | Evidence ID, source reference, observation time, provenance category, scope, freshness, validation state, and access restrictions. |
| Opportunity | Business problem, users, pattern, disposition, alternatives, dimension findings, evidence references, assumptions, gaps, and priority rationale. |
| Economics and architecture | Usage inputs, low/base/high assumptions, deterministic calculation version, cost/price basis, diagram nodes/edges, and observed/proposed labels. |
| Delivery | PoC acceptance tests, evaluation data requirements, prerequisites, work packages, owner, partner, acknowledgement, milestones, and production approval gates. |
| Quality and feedback | Catalog/rule/model/prompt versions, validation results, expert decisions, corrections, rejection reasons, and permissioned outcome metrics. |

Reject a report when cited evidence is missing, scope crosses an unauthorized boundary, cost inputs are fabricated, a proposed component is presented as discovered, or a blocked action is recommended. Mark partial results explicitly; model failure must not produce a misleading completed investment recommendation.

## Appendix C. Pilot Interview And Decision Agenda

### Customer Interview

Ask the application and business owners to identify the workflow, users, repeated friction, current alternatives, monthly volume, task time, quality baseline, and the KPI they are willing to measure. Ask data owners what relevant data exists, who may use it, its known quality gaps, where it may be processed, and whether a representative evaluation sample can be approved. Ask engineering who owns integration, operations, rollback, and change capacity. Ask the sponsor what evidence would cause them to fund a PoC or reject the idea.

### First Cross-Microsoft Working Session

Confirm the customer problem and current product overlap; agree Azure Migrate's decision boundary; nominate CoreAI/Foundry and field counterparts; select two initial patterns; agree a small FDE/partner contribution; establish security/privacy review; and assign owners for customer recruitment, measurement, cost estimation, and the week-2 gate. Record disagreements and unresolved dependencies rather than implying alignment.

### Suggested VP Discussion

Spend the first five minutes on the customer question and decision ask, ten minutes on a concrete application example and differentiation, ten minutes on the operating model and economics, and five minutes on gates, risks, and owner nominations. The meeting should end with an explicit validation decision, not an implied launch commitment.

---

## Appendix D. Evidence, Assumptions, And Source Register

### Evidence Status

This proposal builds on the supplied draft, the repository workstream index, selected local implementation paths, and official Microsoft documentation accessed on 22 September 2026. Local code inspection establishes reusable patterns only: it is not a full repository audit, current deployment verification, or proof that the proposed AI feature is already available. No application code, cloud resource, or partner system was modified to create this proposal.

Customer demand, counterpart participation, staffing, pricing, conversion, timelines, and pilot thresholds remain hypotheses or proposed decisions. Every numerical business example and investment estimate is illustrative. Confirm live service availability, regional support, licensing, and terms before customer use. Organizational names identify intended conversations, not approved reporting-line ownership.

### Official Product And Adoption Sources

- **S1.** [Create an application assessment](https://learn.microsoft.com/azure/migrate/create-application-assessment?view=migrate). Supports the existing application assessment, scope selection, and readiness/sizing/cost foundation; not the proposed AI capability.
- **S2.** [Integrate portfolio assessment with GitHub Copilot modernization](https://learn.microsoft.com/azure/developer/java/migration/github-copilot-app-modernization-for-java-portfolio-assessment-integration). Supports the assessment-to-developer handoff precedent; not an assertion that an AI opportunity integration already exists.
- **S3.** [Cloud Adoption Framework: AI strategy](https://learn.microsoft.com/azure/cloud-adoption-framework/ai/strategy). Supports business-first use-case selection and adopt/extend/build choices.
- **S4.** [Plan for AI adoption](https://learn.microsoft.com/azure/cloud-adoption-framework/ai/plan). Supports prioritization, skills, responsible AI, and focused PoC validation.
- **S5.** [Data, privacy, and security for Models sold by Azure in Microsoft Foundry](https://learn.microsoft.com/azure/foundry/responsible-ai/openai/data-privacy). Supports narrowly scoped data-handling statements; deployment types and stateful features require specific review.
- **S6.** [Observability in generative AI](https://learn.microsoft.com/azure/foundry/concepts/observability). Supports model/application evaluation, monitoring, and tracing capabilities; does not certify this assessment's quality.

### Local Implementation Evidence

All local repositories below are under `C:/Users/nigadh/source/repos/`. Commit identifiers record the local HEAD inspected, not the current production version. Paths describe evidence locations and candidate extension boundaries, not approved edits. The repository index is [RepoRef.md](../RepoRef.md).

**R1. Assessment lifecycle and API/model separation**  
Repository: `AzureMigrate-AssessmentServiceV2`, local HEAD `28f74cec59e3`.  
File: `src/Workloads/RestApi/Controllers/Helpers/Mongo/Versioned/2025-09-09-preview/MongoAssessmentControllerHelper.cs`.  
Observed: `MongoAssessmentControllerHelper` derives from `AssessmentControllerHelperBase`, validates common settings, creates/updates the entity, and maps ARM properties. Follow that separation if this platform hosts the feature; do not treat Mongo settings or its API version as an AI contract.

**R2. Assessment persistence**  
Same repository and HEAD as R1.  
Files: `src/Workloads/DataModel/Mongo/Entities/MongoAssessmentEntity.cs`; `src/Workloads/DataModel/Mongo/Operations/MongoAssessmentEntityOperations.cs`.  
Observed: `MongoAssessmentEntity : AssessmentEntityBase` carries partner-specific settings, counts, and summaries; operations derive from the shared assessment operations base. Reuse lifecycle/persistence conventions, but model AI evidence and workflow decisions explicitly. Partner counts are not assumed to be inherited.

**R3. Compute input, consume, and report boundaries**  
Same repository and HEAD as R1.  
Files: `src/Workloads/Workflows/Assessment/CreateAssessment/Mongo/CreateMongoAssessmentHelper.cs`; `src/Workloads/Workflows/Assessment/CreateAssessment/Mongo/ConsumeMongoAssessmentHelper.cs`.  
Observed: versioned `AssessmentInput` is built from scoped resources and settings; output is transformed into assessed entities and summaries, with report generation. Follow structured contracts and scope guards; AI opportunity economics must not be merged into infrastructure cost fields.

**R4. Asynchronous execution and validation**  
Repository: `AzureMigrate-AssessmentFunctionApps`, local HEAD `42781da2594d`.  
Files: `src/Mongo/Mongo.FunctionApp/MongoAssessmentTriggerFunction.cs`; `src/Mongo/Mongo.FunctionApp/MongoAssessmentClient.cs`; `src/AssessmentFunctions/AssessmentOrchestrator.cs`.  
Observed: the blob trigger schedules a durable orchestration; the orchestrator separates input validation, computation, output validation, and persistence. Adopt those boundaries where useful, but add evidence/policy validation, bounded model calls, redacted logging, and AI evaluation. Reference behavior is not a blanket endorsement of every implementation detail.

**R5. Business-case partner integration**  
Repository: `AzureMigrate-BusinessCaseService`, local HEAD `138e7235fc26`.  
File: `src/BusinessCaseService/AppMod/Partners/MongoWorkload/MongoAssessmentPartnerActions.cs`.  
Observed: `MongoAssessmentPartnerActions : IPartnerAssessmentActions` declares assessment dependencies and creates/reads/deletes assessment resources through an ARM client. Reuse an explicit integration boundary; AI benefit assumptions and opportunity ownership require a separate business contract.

**R6. Application-level report composition**  
Repository: `AzureMigrate-AppCentricAssessments`, local HEAD `b554c79e47ad`.  
File: `src/Common/MdFileGenerator.Partners/ApplicationUtils/ApplicationComposerUtils.cs`.  
Observed: report helpers interpret application recommendations, strategies, source counts, and costs. Use validated application context in reports; do not reinterpret existing pricing or confidence fields as AI feasibility or value.

**R7. Dependency-map scope**  
Repository: `AzureMigrate-DiscoveryService`, local HEAD `ff9c82302d22`.  
File: `src/WebRole/Versioned/2020-01-01-preview/Controllers/VMWare/DependencyMapController.cs`.  
Observed: authorized, validated requests initiate scoped coarse/detailed dependency-map workflows. This is evidence of dependency discovery infrastructure, not of business API semantics, application authorization, or data-use rights.

**R8. Neighboring test patterns**  
Repositories and HEADs as R1 and R4.  
Files: `test/UnitTests/Workflows.MySQL/Assessment/CreateAssessment/Mongo/CreateMongoAssessmentHelperTests.cs`; `test/UnitTests.Mongo/MongoAssessmentTriggerFunctionTests.cs`.  
Observed: mocked scope/resource/manifest dependencies and durable scheduling tests. Extend ordinary contract/workflow testing with held-out recommendation evaluation, negative/no-AI cases, permission failures, evidence validation, and consent/deletion tests. The existing tests were inspected, not executed for this document-only proposal.

### Decisions Still Requiring Evidence

Before preview funding, confirm owner-level roadmap fit, eligible customer population, quality of available evidence, customer data-sharing willingness, partner capacity, production service ownership, regional inference availability, true unit cost, commercial packaging, and realized customer outcomes. These are the program's validation agenda, not hidden prerequisites assumed to be solved.