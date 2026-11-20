# Azure Migrate AI Feasibility: An End-to-End Application Walkthrough

**Audience:** Azure Migrate stakeholders, AMA owners, Cloud Topology Design (CTD) engineers, and forward-deployed engineering (FDE) teams.  
**Research date:** 27 September 2026.  
**Demo narrative revision:** 28 September 2026, informed by the supplied strategy/leadership materials; the technical research snapshot is unchanged.  
**Status:** A bounded local simulator prototype was implemented on 2 October 2026. The production
Azure Migrate contracts, partner commitments, deployment automation, pricing, and customer outcome
claims described here remain proposed and require the stated validation gates.

**For presenting:** start with the [ten-minute demo and executive readout](#14-a-stakeholder-demo-script). Sections 4-13 supply technical and delivery detail; [Section 15.6](#156-how-the-supplied-materials-improve-this-demo) explains which ideas were adapted from the transcripts and decks.

## 1. Reading The Example

This walkthrough follows **Contoso Order and Returns**, a fictional application spanning web apps, background services, databases, file storage, virtual machines, and container workloads. Its proposed AI capability assists support employees with order questions and return-document review. No real customer inventory, costs, or AI evaluation results are claimed.

Three evidence labels apply throughout:

- **Existing code:** behavior traced in a specified local repository snapshot. This does not prove production availability, feature-flag enablement, or complete discovery coverage.
- **Customer-confirmed:** business meaning, scope, permissions, or requirements supplied and approved by the responsible customer owner. This is not automatically an observed or experimentally verified fact.
- **Proposed:** a new assessment, contract, interaction, integration, or AI capability required to implement this journey.

The repository index is [RepoRef.md](../RepoRef.md). The investment case remains in [Azure_Migrate_AI_Feasibility_Assessment_Proposal.md](Azure_Migrate_AI_Feasibility_Assessment_Proposal.md).

## 2. The Boundary We Must Preserve

An **AI opportunity brief** is an evidence-backed starting point for a conversation: what might be worth exploring, why this application could be relevant, and which questions remain unanswered. It must not claim a validated business benefit or usable business data based on infrastructure discovery alone.

An **AI Feasibility Assessment** is the reviewed decision artifact for a selected application and workflow: customer goal, evidence, alternatives, data and integration requirements, architecture, cost assumptions, risks, PoC scope, and acceptance criteria. It can recommend a bounded experiment while recording unresolved prerequisites; it is not production certification.

**AMA** is the existing conversational entry point to extend. **CTD** composes an application-level target topology from supported assessment inputs and catalog rules. **FDEs and delivery partners** validate the customer problem and engineer the implementation. A diagram or a generated roadmap is not itself a deployed solution.

### A Verified CTD Limitation

The inspected `CollectedDataResolverMapper.BuildDiscovery` handles database, web, host, and file-share members, but does not route container members. Its source explicitly notes that container members are dropped. Therefore, an end-to-end example containing existing container workloads cannot honestly be presented as an already complete CTD output.

The required follow-on is to preserve container workload and recommended-plan identity at the application-to-CTD boundary, then separately represent the proposed AI components. Adding an AI catalog diagram alone would not fix missing base-application components. This finding will remain visible in the implementation map and acceptance criteria.

Source anchor: `AzureMigrate-AppCentricAssessments/src/ApplicationAssessments/ApplicationAssessments.Workflows/Resolver/CollectedDataResolverMapper.cs`, `BuildDiscovery`, `DbTypes`, `WebTypes`, `HostTypes`, and the explicit container exclusion note. Local HEAD: `b554c79e47ad`. See the source register below for the connected paths and research limits.

## 3. The Story In Two Minutes

Contoso has an existing order-and-returns application. Its support employees open several screens, search returns guidance, and manually read scanned forms before responding to a customer. The infrastructure administrator is already using Azure Migrate. The business process owner knows the pain; the application owner knows the integration; neither needs to prepare an AI architecture before starting.

1. **Discover the estate:** reuse the supported collectors to identify machines, web apps, databases, container workloads, and observed connections. Record missing coverage.
2. **Form and review the application:** run the existing auto-application operation where supported, then correct membership and shared dependencies with the customer.
3. **Assess the existing application:** obtain workload readiness, sizing, target choices, and a consistent migration cost baseline.
4. **Prepare an AI opportunity brief:** AMA gives the FDE an application-specific conversation starter, with hypotheses and open questions rather than a premature recommendation.
5. **Capture and confirm intent:** the FDE and customer use AMA to agree a workflow, intended users, success criteria, permitted data, and boundaries.
6. **Produce the AI Feasibility Assessment:** compare solution options, identify required services, plan validation, and calculate a conditional estimate from explicit usage assumptions.
7. **Review the AI target architecture:** CTD should compose the supported base topology plus an approved AI extension. Missing adapters/catalog modules remain explicit implementation work.
8. **Approve and run the PoC:** the FDE/customer delivery team builds and evaluates a limited solution in a separately authorized environment. Findings update the same assessment record.

The pitch is not "a model looked at our servers and decided we need a chatbot." It is "Migrate already knows much of the technical context; AMA and the FDE add the business context, then turn both into a justified, testable implementation decision."

## 4. Stage A: Discover The Existing Estate

### 4.1 Fictional Inventory

The example contains **15 discovered machine records**: eight production application hosts, five shared dependency hosts, and two DevTest hosts. Workloads running on those hosts are separate inventory objects or observations; they are not another 15 machines.

| Inventory slice | Example assets | What we can use | What remains unproven |
| --- | --- | --- | --- |
| VMware Windows VMs | `ord-prd-web01/02`, IIS/.NET portal | Host configuration, supported web-app discovery metadata, runtime/bindings, readiness results. | Customer workflow, API semantics, and code-level change effort. |
| Hyper-V Linux VMs | `ord-prd-svc01/02`, Java order services | OS/software/process observations, observed connections; web-app details if discovered by the relevant supported workload collector. | A process is not automatically a first-class business service or an OpenAPI contract. |
| Physical Windows server | `ord-prd-batch01`, legacy ERP export service | Server inventory, installed software and process/dependency evidence where collected. | Transaction semantics and whether an AI capability may invoke it. |
| VMware database VMs | `ord-prd-sql01/02`, SQL order databases; `ord-prd-pg01`, PostgreSQL audit database | Supported database discovery/configuration and assessment results. Identify replication/HA only from relevant evidence. | Table meaning, data quality, record-level access, and a usable AI evaluation dataset. |
| Shared Kubernetes hosts | `shared-k8s-cp01`, `shared-k8s-w01/02/03` | Four machine records plus cluster/node context and discovered workload resources where that discovery integration is available. | That every workload on those nodes belongs to Orders, or that the source is a microservices architecture. |
| Container workloads | Three Orders workloads: `return-worker`, `document-intake`, `order-sync`; unrelated warehouse workloads also use the cluster | Workload/controller identity, images, requests/limits, services/storage and topology fields that the relevant collector actually supplies. | End-to-end API behavior, data rights, or support for every field in downstream CTD. |
| Shared physical file server | `shared-files01` | Host and dependency observations; file-share metadata only if the applicable discovery path has collected it. | That a share contains approved policies or scanned forms. A file-server connection does not reveal content. |
| Hyper-V DevTest VMs | `ord-dev-web01`, `ord-dev-db01` | Separate environment inventory and tagged scope. | Permission to use copied production data in a PoC. |
| Network observations | Web-to-service, service-to-database, service-to-file-server connections | Endpoint/process/port relationships and observation times, with unresolved/missing endpoints exposed. | A complete firewall/routing model, application API paths, authentication rules, or all intermittent dependencies. |

**Existing code:** `WebAppEngine/Workflows/RefreshFabricLayout.cs` refreshes target-machine context, invokes web discovery helpers, and records results/errors. `AzureMigrateAgents/src/DependencyMap/DataAggregrator.cs` deduplicates processes and separates resolved, unresolved, and time-wait connections. `ConnectionInfo` carries machine/process identifiers, IPs, ports, counts, and timestamps. [E1-E3]

Use the appliance-based path for the rich dependency example. The published disconnected Collector and CSV modes do not provide identical evidence; a server-only CSV cannot produce the same workload or network conclusions. Existing collectors must remain read-only within their supported permissions. This proposal does not turn discovery into a business-document crawler. [S1]

Container evidence here is conditional on the relevant container discovery being available and populated. The local container packaging/scripts and assessment code are not proof of general availability or populated live ARM resources. The existing proposal's container phases remain separate from this AI feature.

### 4.2 Preserve Provenance Instead Of Inventing Meaning

The AI adapter should store a scoped evidence snapshot: source resource ID, source/collector, capture time, applicable fields, completeness/errors, and the originating assessment when relevant. Only approved, minimized metadata goes to model-assisted processing. Do not pass raw process arguments or configuration indiscriminately; they may contain sensitive values.

The inventory may identify `shared-files01`. The customer later explains that its approved returns-guidance share and restricted return-form share support this workflow. Those are new, owner-supplied facts with separate access decisions, not discoveries retroactively attributed to the appliance.

## 5. Stage B: Create And Confirm The Application

### 5.1 Automatic Grouping Is Not Business Discovery

**Published behavior:** auto-application discovery groups servers and their workloads using **server-naming patterns, inferred environments, and derived server roles**. It derives names, type, criticality, complexity, and a grouping confidence score. Inadequate metadata can produce default names and medium criticality/complexity. Those defaults are not customer-approved business importance. The documented operation is currently one-time and should follow adequate discovery. [S1]

**Existing code:** the Portal's `AutoAppDiscoveryHelper.startAutoDiscovery` creates/links a discovery hub if required, then posts `{}` to `{hubId}/startAutoAppDiscovery`. It reads `appDiscovery.status`, errors, summary, and last-attempt time. `ApplicationData` reads application members through scoped ARG queries and supports updates. DiscoveryService also calls the same action after supported offline-import hydration. [E4]

The actual grouping algorithm was not found in the inspected backend checkouts. Consequently, the following group is an **illustrative expected starting point**, not the output of a locally executed grouping algorithm. Dependency analysis helps the customer review the group; the inspected source does not establish that the auto-grouping algorithm uses network graph clustering.

### 5.2 Customer Review Of Contoso

Assume auto discovery suggests an `ord-prd` application containing the eight production application hosts and a separate `ord-dev` application. The FDE and application owner then:

1. Rename/describe the production group as **Contoso Order and Returns** and confirm its business criticality.
2. Confirm the two service VMs are instances of one service, not two independent business applications.
3. Review the shared file-server connection and identify the relevant shares, keeping shared ownership explicit.
4. Identify the three Orders container workloads on the shared cluster. Associate those workloads with the reviewed application context; do not claim the entire cluster, warehouse namespace, or control plane is Orders-owned compute.
5. Keep DevTest out of the production assessment. Record an approved PoC environment separately.
6. Record a missing/unknown dependency as a validation task, not as proof the application is isolated.

Use supported member-management interfaces for resource types the current implementation accepts. If container-level membership or a shared-dependency relationship is not available through those interfaces, preserve it in the proposed evidence adapter and flag that integration requirement. Do not silently substitute all cluster VMs for workload-level application ownership.

The published application model allows shared workload membership and customer edits; reviewed system applications become user-managed. The proposed AI record adds explicit confirmation history and evidence provenance; it must not treat the existing grouping confidence as AI-feasibility confidence. [S1, E4]

### 5.3 Grouping And Assessment Order

There is no need to wait for an AI intent to discover or assess workloads. A customer can assess the estate first, then group/review applications and consume those results; or group first and assess the selected application. For the walkthrough we use **discovery -> reviewed application -> workload/application assessment**, because it makes the scope easiest to explain. Recompute or invalidate derived outputs when scope changes.

## 6. Stage C: Assess The Application We Have Today

### 6.1 Existing Assessment Paths

The following results are illustrative, not live SKU recommendations:

| Application slice | Existing assessment path | Example planning outcome |
| --- | --- | --- |
| IIS/.NET portal | Web-app/App Service assessment through the existing WebApp compound path; WebApp-to-AKS through its separate AKS path | App Service candidate with specific prerequisites, with a VM alternative. |
| Java service hosts and physical batch service | Appropriate discovered web workload assessment where eligible; otherwise machine assessment | Preserve the batch service on an Azure VM unless a separately validated modernization changes it. |
| SQL workloads | SQL assessment | Compare eligible Azure SQL targets and SQL-on-VM using collected compatibility/capacity data. |
| PostgreSQL audit workload | Partner assessment in AssessmentServiceV2/FunctionApps | PostgreSQL target recommendation, issues, sizing, and cost. |
| Existing container workloads | Container workload assessment in AssessmentServiceV2/FunctionApps | Per-workload suitability and shared AKS plan for eligible Kubernetes source workloads; VM fallback when applicable. |
| File data and network/supporting services | Applicable file-share/network/peripheral assessment paths | Carry assessed findings only for types and properties actually supported; keep missing/unpriced components visible. |
| Whole application | AppCentricAssessments | Consolidate workload recommendations into strategy-specific application views and a consistent cost baseline. |

**Existing code:** QueryNet's `AssessmentService.create_or_update_assessment` resolves the selected resource scope, determines assessment resource types, and deploys an assessment ARM template. An ARM deployment that creates **assessment resources** is not a deployment of the target business application. [E5]

For container workloads, `CreateContainerAssessmentHelper` retrieves linked clusters/nodes and builds a versioned input. `ContainerWorkloadAssessmentClient` parses/enriches workloads and runs eligible target pipelines. The generic assessment orchestration separates input validation, compute, output validation, and output persistence. Existing WebApp-to-AKS and already-containerized-workload assessment are different producers and must not be treated as interchangeable contracts. [E6-E8]

### 6.2 Reuse Results Without Overclaiming

For this teaching example, assume the selected full Azure migration strategy has an **illustrative USD 6,200/month baseline**, after the owning assessment has reconciled workloads, shared plans, and supported peripherals. This is not a quote or a value extracted from the repository.

Preserve the baseline's assessment ID/version, currency, region, scope, pricing assumptions, and included costs. Do not sum per-workload shared-cluster or multi-parent VM-fallback totals indiscriminately. Keep full shared-resource cost and application-attributed cost distinct; a platform dependency does not disappear simply because its incremental charge is zero.

If the customer runs the AI PoC beside the still-on-premises application, the USD 6,200 is a **migration scenario comparator**, not a new monthly bill. If they later migrate the base application too, add only the incremental AI costs not already included in that baseline.

These assessments answer where and how the current workload can run. They do not establish that the support workflow is valuable to automate, that order records may be sent to a model, or that OCR will meet extraction-quality requirements.

## 7. Stage D: Produce The AI Opportunity Brief

### 7.1 What The FDE Asks AMA

> **FDE:** "Prepare an AI opportunity conversation for Contoso Order and Returns. Use its reviewed application group and latest assessment. Focus on employee productivity and document handling; do not assume access to business records."

The initial intent theme only narrows the exploration. It is not a business case. If nobody has confirmed what the application does, AMA first asks for a short application description instead of inferring the business process from a name.

### 7.2 Example Brief, Before Deep Validation

**Proposed artifact: AI opportunity brief, revision 1.**

| Brief field | Illustrative content |
| --- | --- |
| Known technical context | Reviewed Orders application, .NET portal, Java service instances, SQL/PostgreSQL, shared file-service connection, three associated container workloads, and migration assessment results. |
| Opportunity hypothesis | Employees may benefit from a single assisted workflow for finding guidance and preparing an order/returns response. This is a conversation hypothesis, not an inferred fact about employee effort. |
| Why this application merits discussion | It already has a user-facing surface and several information/integration boundaries. Migrate can identify where an extension might connect and what legacy components should remain isolated. |
| Candidate capabilities | Policy retrieval; read-only order summary; extraction from scanned forms **if** those forms and a measurable manual task exist. No fixed quota of AI ideas. |
| Questions for the business owner | Which task takes time? Who performs it? How is it done now? What does success look like? Would an existing product or non-AI improvement solve it? |
| Questions for data/application owners | Where are authoritative answers? Who may read them? Is a supported read-only API available? Can representative examples be used for evaluation? |
| Confidence and limits | Technical context is evidence-backed; business value, document suitability, API semantics, and AI run cost are not yet validated. |
| Next action | Schedule a targeted workflow session with the support lead, application owner, data owner, and FDE. |

This is useful before a sales pitch: it lets the FDE bring a relevant hypothesis and a focused agenda instead of generic AI slides. A negative finding can end the exploration without buying or deploying an AI service.

## 8. Stage E: Capture Intent, Business Context, And Requirements

### 8.1 The Actual AMA Conversation

| AMA question | Customer response in this example | Recorded consequence |
| --- | --- | --- |
| "What task should improve?" | Support lead: "Prepare an accurate response to an order or return inquiry." | Workflow and outcome, not merely the theme "GenAI." |
| "Who does it, and where?" | "100 internal support employees use the existing portal." | Internal audience and experience boundary; no customer-facing release assumed. |
| "What do they do today?" | "Open the order screen, find returns guidance, read attached forms, then draft a reply." | Candidate read-only API, knowledge retrieval, and document-extraction steps. |
| "What is the baseline and desired goal?" | "Our rough sample suggests eight minutes. Measure the median properly, including review time, and aim for six or less without reducing answer quality." | A **customer-proposed** 25% time-reduction target; baseline, population, and measurement method still need confirmation. |
| "What business result should that recovered time enable?" | "Give employees more time for aged, complex cases and reduce that backlog. Do not assume a headcount saving." | A benefit hypothesis connecting task improvement to business value, with backlog and quality measures to agree. |
| "Who owns the outcome, and when will we review it?" | "Our Head of Support will sponsor the decision. Review results by the week-6 PoC gate after access approval." | Named role and review horizon; assign the actual person and calendar date before starting. |
| "Can the team adopt and support the change?" | "The ten pilot users need training and time to test. The application team must commit integration and support capacity." | Organizational readiness and resource commitments remain explicit prerequisites. |
| "How much usage should we plan for?" | "About 40,000 assisted interactions and 6,000 scanned pages each month; peaks are not measured yet." | Usage inputs and an explicit missing concurrency/latency measurement. Not derived from VM CPU. |
| "Where are correct answers today?" | Data owner: "Approved guidance is on one share; individual return forms are in a restricted case store." | Separate sources, permissions, ingestion strategies, and owners. |
| "Can another application read order status?" | Application owner: "There is a read API. I can provide its sanitized contract and arrange a test." | API declared, not yet validated. No credentials entered into AMA. |
| "What must the assistant never do?" | "No refunds, order edits, or automatic customer communications. An employee approves every response." | Prohibited actions and mandatory human review. |
| "What controls apply?" | "Keep processing in our approved geography, restrict data to the employee's cases, audit access, and meet our retention policy." | Requirements for security review; not a claim that they are already implemented. |
| "What is the PoC boundary?" | Sponsor: "Ten employees, approved samples/test accounts, and a separately approved budget and environment." | Explicit PoC scope, owner, and approval gate. |

AMA should present one confirmed summary for approval and save its structured fields. The FDE can correct it with the customer. "Unknown" remains a valid answer, with an owner assigned to obtain the missing evidence. Do not make the infrastructure administrator answer for the business, data, or security owners.

### 8.2 Evidence Requests, Not Unrestricted Uploads

| Required evidence | Who provides it | What validates it | Outcome if unavailable |
| --- | --- | --- | --- |
| Workflow baseline and representative questions | Support lead and participating employees | Review actual task samples and define quality/time measurement. | Mark benefit unquantified; do not publish ROI as fact. |
| Authoritative returns guidance | Content/data owner | Confirm usage rights, permitted audience, currency, coverage, and conflicts on approved samples. | Defer policy answers or start with an approved limited corpus. |
| Scanned forms and expected fields | Data owner and subject-matter expert | Use de-identified/approved examples and expected outputs to test extraction accuracy. | Omit OCR/extraction; file-server presence alone is insufficient. |
| Read-only order interface | Application engineering owner | Review contract/authentication and test per-user/case authorization in an approved environment. | Use synthetic fixtures for a clearly labeled UX prototype, or make an integration adapter a prerequisite. |
| Identity, networking, retention, and regional rules | Security/platform owners | Review the end-to-end data flow and selected deployment types. | Block affected data processing until approved. |

The assessment can start with metadata and owner declarations. Content review, source-code inspection, API invocation, customer-data ingestion, and partner sharing each require the relevant authorization. A source reference or uploaded API specification is not proof of runtime behavior. A synthetic demo is not evidence of production feasibility.

### 8.3 Example Confirmed Requirement

> **Goal:** Assist internal support employees in preparing order/return responses inside the existing portal. Retrieve approved guidance, summarize an authorized order, and extract selected fields from approved scanned forms. Target a reduction from eight to six minutes per task while maintaining the agreed quality bar. Keep all business-system access read-only and require an employee to approve the final response. Begin with a ten-user, controlled PoC; validate data rights, API authorization, extraction quality, latency, usage, and cost before considering production.

This is the decision input for the AI Feasibility Assessment. It is not stored by repurposing the existing migration-intent tag, environment tag, application-grouping confidence, or workload readiness score.

### 8.4 The One-Page Decision Charter

AMA should summarize the conversation into the existing proposed `AiIntentBrief`, not create another independent strategy document. The FDE reviews it with the responsible customer owners. The supplied strategy material recommends connecting baseline, target, metric, timeframe, and accountable owner; the leadership material adds explicit decision and intervention authority. [T1, T3, T4]

| Charter field | Contoso example, subject to customer confirmation |
| --- | --- |
| Problem and intended outcome | Support employees spend time gathering information before responding. Test whether assistance can release capacity for aged, complex cases without degrading response quality. |
| Baseline, target, and measure | Validate median minutes per comparable completed support task, including review/rework. Eight to six minutes is the proposed target, not measured performance. Track backlog/quality separately from task time. |
| Timeframe and accountable owner | Week-6 PoC decision after prerequisites are met; customer Head of Support owns the business outcome. Name the person, review date, and measurement owner before approval. |
| People and delivery capacity | Ten trained pilot employees and participating subject-matter experts; committed application, AI, data, and security capacity. A willing sponsor is not a substitute for available implementers. |
| Decision rights | Employees approve any response in their normal workflow. The application operations owner can disable the assistant; the designated risk owner can require a pause. Business actions, data access, and production release need their respective owners' approval. |
| Boundaries and next decision | Approved guidance first; order lookup/extraction remain conditional. No refunds, order writes, or automatic customer messages. Approve the next evidence/experiment step, not all future stages. |

These are requirements to confirm, not organizational facts inferred from the workload inventory. Unknown ownership or capacity keeps the opportunity at **NeedsEvidence**. Keep business accountability, engineering responsibility, and permission to stop or expand the system distinct.

## 9. Stage F: Produce The AI Feasibility Assessment

### 9.1 Example Decision

**Proposed artifact:** `Contoso Orders / support-assistance / revision 2`. This is a human-readable example identifier, not an approved ARM resource name.

**Recommendation:** proceed with a limited internal support-assistance PoC. Begin with approved policy retrieval and draft responses. Add order lookup only after API access and case-level authorization pass validation. Include scanned-form extraction only after the data owner approves representative samples and the extraction approach meets the agreed field-level accuracy bar. Do not automate refunds or change the transactional application.

| Dimension | Finding at assessment time | Consequence |
| --- | --- | --- |
| Business fit | A named support workflow and customer-proposed eight-to-six-minute target exist. Baseline sampling is not complete. | Worth testing; no claimed productivity saving or ROI yet. |
| Data readiness | Owners identify guidance and case documents; their suitability and permissions still require validation. | Approved-sample scope first; do not index the full shared file server. |
| Integration | An order API is declared. Its contract can be reviewed, but authorization and behavior need testing. | Read-only adapter is conditional; no direct model-to-SQL connection. |
| Technical readiness | A portal extension and separately hosted assistant appear plausible. Hosting recommendations and legacy constraints are available. | Preserve base application components; validate actual extension points and hybrid connectivity. |
| Sizing and cost | Volume assumptions support a first estimate; peak concurrency, token lengths, corpus size, and scaling are unmeasured. | Publish low/base/high estimates with explicit provisional inputs. |
| Complexity and operations | Retrieval, extraction, authentication, content operations, evaluation, and user review all require work. | Named owners, work packages, rollback, and acceptance criteria must accompany the design. |

A released assessment should include the accepted intent, source versions, dispositions per capability, alternatives, gap owners, proposed design, estimate, PoC plan, and review history. It may legitimately say "remediate first" or "insufficient evidence" for part or all of the opportunity.

### 9.2 Service Selection With Reasons

| Service or component | Why this example needs it | Selection or omission rule |
| --- | --- | --- |
| **Microsoft Foundry model access and evaluation** | Compose a draft from permitted policy passages and authorized order facts; compare model quality, latency, and cost. | Select model/deployment after evaluation and residency/capacity review. Do not add an unexplained flat "Foundry fee" on top of the actual metered services. |
| **Azure AI Search** | Retrieve relevant, approved policy content with citations and permission-aware filtering. | Compare dedicated and other eligible offerings; estimate the chosen pricing model correctly. Do not index live order data merely because a SQL database exists. |
| **Document Intelligence / OCR and extraction** | Read scanned return forms and extract the selected fields for employee review. | Compare Read/Layout and suitable extraction models on samples. Omit OCR for usable digital text; no double OCR charge unless the design really calls two services. |
| **Assistant backend on App Service** | Enforce identity, retrieve context, call approved APIs, apply validation, and return a draft to the existing portal. | Reuse suitable hosting or consider Container Apps if justified. Existing AKS deployment is not a reason to require new GPU nodes. |
| **Controlled ingestion plus Blob Storage** | Stage only approved content, preserve source/permission metadata, and refresh/delete indexed material. | The implementation may use a small worker/function. Price its compute, operations, and storage; avoid an unnecessary copy of restricted case data. |
| **Existing customer identity; managed identity for service calls** | Authenticate employees and authorize both retrieval and order lookups outside the model. | Map the existing identity to verified permissions. No API keys or production passwords in AMA, the report, or a prompt. |
| **Application Insights / approved monitoring** | Observe technical quality, latency, errors, and cost without default logging of sensitive content. | Add business and AI evaluation metrics; telemetry alone does not measure answer correctness. |
| **Private connectivity, DNS, and controls** | Meet the approved network/residency policy and connect to the existing application where required. | Confirm actual topology and region. Private endpoints do not, by themselves, establish the model's processing geography. |
| **API Management / Agent Service / extra orchestration** | Potentially useful for API governance or a more complex tool workflow. | Optional, not a mandatory bundle. The first bounded flow may use ordinary backend orchestration. Add capability and cost only when justified. |
| **Existing Copilot/SaaS option** | May already solve the workflow with lower implementation effort. | Compare licensing, data access, integration, quality, and operating responsibilities before approving a custom build. |

OCR and retrieval are different jobs: extraction turns an approved scan into usable data; retrieval finds relevant guidance; the language model composes the draft. A model is neither an authorization engine nor the source of truth for a refund decision. [S2-S4]

### 9.3 Intent Changes The Analysis

| Customer intent theme | What AMA must clarify | Likely assessment emphasis |
| --- | --- | --- |
| General AI modernization / GenAI opportunities | Which users and workflows matter, and what evidence supports each idea? | Compare several candidate patterns, including no-build options. |
| AI automation | Which actions may occur, what must be approved, and how can failures be reversed? | Verified operations, transaction controls, exceptions, and human approvals. |
| Customer-facing AI | Who may see which data, what quality is required, and how is support escalation handled? | Per-customer isolation, safety, availability, and staged release. |
| Developer productivity | What engineering task is slow, and what code-tool permissions exist? | Existing GitHub/code-modernization tools, not automatically an application RAG backend. |
| Reporting / data analysis | Which metrics and decisions matter, and what governed data/model defines them? | Approved reporting/semantic models and query access; Fabric/Power BI or conventional analytics may fit better than Search/OCR. |

Themes route the conversation; they do not determine the Azure bill of materials on their own.

### 9.4 Show Why This Scope Comes First

Compare **business value, organizational readiness, technical feasibility, and resource needs**, following the supplied prioritization guidance. Use evidence and disagreements rather than an invented 1-5 average. A high potential benefit cannot cancel a failed access-control gate. The table below is an illustrative review, not a completed customer decision. [T3, T4]

| Option | Value and organizational fit | Technical/resource evidence | Proposed disposition |
| --- | --- | --- | --- |
| Improve existing search or use an existing product | Could reduce information-finding effort with less workflow change. | Check current capabilities, licensing, configuration effort, and measurable results. | Keep as the comparator; choose it if it solves the problem adequately. |
| Approved-policy retrieval and cited drafts | A bounded test of assistance for internal users, provided they can participate and review outputs. | Content approval, retrieval quality, integration, evaluation, and support work remain necessary. | First experiment candidate after prerequisites and a revised scoped budget are approved. |
| Add live order lookup and scanned-form extraction | Could remove more manual steps, but extends data access and review responsibilities. | API authorization and field-level extraction quality are unverified; additional engineering/data-owner capacity is needed. | Preserve as conditional increments. Resolve these uncertainties before including them in execution. |

Autonomous refunds are outside the accepted scope, not merely a lower-ranked option. The draft-assistance versus business-action distinction must remain visible in the assessment and architecture. The full conditional scenario's cost is not the price of the policy-only option; changing the selected scope requires repricing.

## 10. Stage G: Calculate The Cost Transparently

### 10.1 Three Separate Costs

1. **Existing application scenario:** the migration assessment's base hosting/capacity cost, with its own scope and pricing basis.
2. **Customer AI solution:** incremental inference, retrieval, extraction, hosting, storage, networking, monitoring, and ongoing operational work.
3. **The assessment feature itself:** Microsoft's cost to generate/review this assessment. This is not the customer's eventual inference bill and should be measured separately for product economics.

One-time engineering, integration, content preparation, training, and evaluation are also separate from recurring Azure service charges. FDE participation must not be represented as a published fee or a guaranteed free entitlement.

### 10.2 Inputs And Their Owners

| Input | Initial source | How to improve it |
| --- | --- | --- |
| Existing application costs and resource identities | Versioned workload/application assessments | Reconcile shared resources and refresh the selected scenario. |
| Interactions/month, growth, peak concurrency | Support owner, initially an estimate | Instrument a representative PoC and account for seasonality. |
| Model calls per interaction, input/output tokens, retries | Proposed flow and approved sample measurements | Include all model calls, retrieved context, history, evaluation and retry traffic. |
| Search replicas/partitions or serverless usage; premium features | Selected design and approved corpus/load test | Size storage, throughput, indexing, and required availability for the actual pricing model. |
| Scanned pages, extraction model, reprocessing | Data owner and approved document profile | Measure pages actually processed per model, not just file count. |
| Region, deployment type, currency, rate validity, commercial agreement | Customer preferences and approved price source | Resolve current meters/rates; record source and timestamp per line. |
| One-time work and ongoing human review/support | FDE/delivery team and business owner | Replace estimates with an agreed plan and measured effort. |

An implementation should resolve rates from the appropriate Azure pricing/catalog/contract source, normalize units deterministically, preserve input provenance, and calculate outside the LLM. A service or meter with no verified rate must be marked **unpriced**, never silently zero. Changed topology, workload volume, or model choices must trigger repricing.

### 10.3 Worked Monthly Estimate

**Demonstration arithmetic only. Every rate below is invented for this walkthrough, not an Azure price quote, model recommendation, SLA commitment, or measured customer result.** Use USD and a 730-hour planning month; select and validate the actual geography, model, service tier, and rates before an approved estimate.

Base assumptions: 40,000 assisted interactions/month; one generation call per interaction averaging 4,000 input and 500 output tokens; 10% extra generation traffic for retries/evaluation; 12 million embedding tokens across query and changed-source embedding; 6,000 scanned pages; two dedicated Search replicas and one partition; semantic ranking on each interaction.

| Incremental line | Quantity and invented unit rate | Base monthly USD |
| --- | --- | ---: |
| Model input | 40,000 x 1.10 x 4,000 = 176 million tokens; USD 0.40/million | 70.40 |
| Model output | 40,000 x 1.10 x 500 = 22 million tokens; USD 1.60/million | 35.20 |
| Embeddings | 12 million tokens; USD 0.10/million | 1.20 |
| Document extraction | 6,000 processed pages; USD 10/1,000 pages | 60.00 |
| Dedicated Search capacity | 2 replicas x 1 partition x 730 hours x USD 0.20/SU-hour | 292.00 |
| Semantic ranking | 40,000 requests; USD 1/1,000 requests; no free allowance assumed | 40.00 |
| Backend and ingestion compute | Provisional monthly allowance, including staging/refresh worker | 120.00 |
| Blob storage and operations | Provisional monthly allowance | 20.00 |
| Monitoring/logging | Provisional monthly allowance | 30.00 |
| Private endpoints, DNS, and incremental connectivity | Provisional allowance; existing connectivity reuse must be verified | 60.00 |
| **Modeled service subtotal** | Sum of the ten lines above | **728.80** |
| **Planning reserve, 20%** | Explicit reserve, not a billing meter | **145.76** |
| **Illustrative monthly service budget** | Subtotal plus reserve | **874.56** |

The allowance lines are not sufficient detail for an implementation-ready quote: the FDE must replace them with SKU/meter/quantity lines. The base design does not claim query-and-indexing SLA coverage with two replicas; if that SLA or more capacity is required, change the replica count and reprice. Serverless Search has different meters and must not be costed as search units. Agentic retrieval, additional model calls, regional networking, identity licenses, safety features, or other selected capabilities require separate line items where billed. [S2-S4]

### 10.4 Sensitivity And PoC Budget

The following scenarios use the same invented rates, not an assurance that each capacity meets demand:

| Scenario | Explicit changes | Service subtotal / budget with 20% reserve |
| --- | --- | --- |
| Low adoption | 10,000 interactions; 3 million embedding tokens; 1,500 pages; two Search replicas; other allowance lines unchanged. | USD 573.70 / **688.44** per month. |
| Base | Assumptions in the detailed table. | USD 728.80 / **874.56** per month. |
| High demand | 120,000 interactions; 36 million embedding tokens; 18,000 pages; three Search replicas; compute/storage/monitoring/network allowances USD 240/40/60/80. | USD 1,478.40 / **1,774.08** per month. |

Low usage does not eliminate dedicated Search, hosting, or networking costs. These scenarios illustrate both usage sensitivity and provisioned-capacity floors. Quality/latency tests may require a more expensive model or more capacity, while an existing approved shared service may reduce incremental cost.

**PoC-only example:** 4,000 planned interactions including the planned evaluation set, 10% generation overhead, 2 million embedding tokens, 1,000 scanned pages, one dedicated Search unit for one 730-hour month, semantic ranking on 4,000 requests, and compute/storage/monitoring/network allowances of USD 80/10/10/60. The service subtotal is **USD 330.76**, or **USD 396.91 with a 20% reserve**. This is an isolated, non-production design, not a production SLA configuration. Approval, access controls, and retention still apply.

Example one-time implementation effort is **six person-weeks**, which may span a four-to-six-week elapsed PoC depending on staffing and prerequisites. At an invented internal planning rate of **USD 4,000/person-week**, that is **USD 24,000 of effort**, not a Microsoft FDE service price. Procurement, access delays, customer labor, and partner statements of work require their own agreements. The illustrative one-month PoC envelope is therefore **USD 24,396.91**, before any additional approved scope.

For a full migration scenario, **USD 6,200 base application + USD 728.80 incremental AI service subtotal = USD 6,928.80/month before the AI reserve and ongoing human costs**. With that reserve, the planning figure is **USD 7,074.56/month**. Do not add a second copy of a gateway, compute plan, or shared cluster already present in the baseline. For a hybrid PoC, do not add the hypothetical Azure migration baseline to the actual pilot bill.

### 10.5 Cost Does Not Establish Value

If the eight-to-six-minute goal is achieved, calculate benefit using measured completed tasks, adoption, realized productive use, and the customer's approved labor-value assumptions. Deduct review, content maintenance, operations, integration, and service costs. Forty thousand model interactions are not necessarily forty thousand distinct completed business tasks. Do not turn an estimated Azure bill into a claimed business ROI.

## 11. Stage H: Build And Review The AI CTD

### 11.1 What CTD Does In The Inspected Code

After workload results are available, `ComputeApplicationAssessmentWorkflow` computes application results. With `EnableCatalogueWorkflow` enabled, it invokes `CatalogueWorkflow`: collect/cache assessment data, resolve architectures, merge peripheral cost, and finalize the cache. `ResolveArchitecturesWorkflow` resolves application/strategy slices, then invokes the peripheral and network-design paths. The source configuration flags default to false; a local implementation is not proof of a customer-enabled feature. [E9]

The mapper translates collected application members into resolver inputs. `ResolutionPipeline.BuildUserTags` currently supplies `architecture_pattern = n-tier` and `hybrid_multicloud = cloud-only`, as well as strategy, criticality, and environment tags. Those are defaults in this path, not proof of customer intent or discovered architecture. Container members are still excluded by the mapper. [E10]

The runtime loads a vendored catalog using `FileSystemCatalogueSource`; it does not automatically consume changes from the catalog repository. The inspected catalog has N-tier canonical entries and infrastructure modules, but no Foundry, AI Search, or Document Intelligence modules in its generated service-module listing. Existing parameter resolution uses assessment values, rules, and defaults. [E9, E13]

`PeripheralComponentDeriver` emits only resource types recognized by its mapping. `PeripheralServiceModuleMap` does not contain the Search/Cognitive Services mappings needed for this example. `PeripheralCostMerger` tracks prior peripheral cost and applies a delta on repeat merges. Adding an AI component to a diagram does not automatically make it price-supported, and repeated AI assessment must not double-charge an existing resource. [E11]

### 11.2 Proposed CTD Extension

The new AI Feasibility Assessment supplies a reviewed **AI design extension**, separate from the base migration recommendation:

- Selected AI scenario and capability scope, linked to the accepted intent revision.
- Existing application resource/plan identities to retain or reuse, including shared dependencies and container plans.
- Proposed AI components, purpose, quantity, SKU/deployment options, allowed data flows, and authorization boundaries.
- Customer constraints: geography, retention, reliability, private connectivity, human approvals, and cost limits.
- Usage/capacity assumptions and evidence for cost-driving parameters, with unknowns explicitly represented.
- Versioned catalog/model/rule/estimate references and the outstanding validations required before execution.

The resolver must preserve base application identity, validate approved constraints, add only justified components, and reject or visibly report unsupported coverage. Its current "overlay" variant vocabulary must not be assumed to provide a ready-made additive AI composition contract. New signals, modules, parameter provenance, and composition semantics need schema and owner review.

Contribution of AI patterns/modules goes through the catalog's KG contribution and review/release process. Update the runtime's pinned/vendored snapshot and the IaC module support together where required. A new page in the catalog repository alone does not change the running resolver. [E13]

### 11.3 Contoso's Reviewed Target Pattern

This is the **proposed customer solution**, not the internal architecture of AMA or the AI assessment service. It shows the relationships the FDE must validate; it is not claimed as current CTD-generated output.

```text
Internal support employee + existing identity
		     |
	Existing Contoso portal / support screen
		     |
       NEW assistant backend + authorization checks
	  |                     |                 |
	  v                     v                 v
  NEW AI Search          Validated read-only    NEW model access
  approved guidance      order API / adapter    through Foundry
  and source citations          |                 ^
	  ^                     v                 |
  Permission-preserving  Existing order service --+
  ingestion worker       on reviewed app hosts
	  ^                     |
	  |                     v
  Approved guidance      Existing SQL order store
  from the source share

Selected return form from authorized case
		     |
      Approved staging / document-processing worker
		     |
     NEW Document Intelligence extraction
		     |
       Field checks + employee review
		     |
       Permitted context for the response draft

Unchanged application dependencies remain visible:
  Orders container workloads -> shared Kubernetes platform
  Batch/ERP integration -> existing physical/VM-hosted service
  Audit path -> PostgreSQL; shared file services -> data owners

Across the design: authorized access, approved connectivity,
monitoring, content lifecycle, evaluation, and manual fallback.
```

The backend orchestrates retrieval/API calls and passes only permitted context to the model. Query filters and API authorization are enforced by application code and underlying services, not by a prompt. Raw case documents are not put into a global knowledge index. Extracted fields and generated drafts are untrusted until validated and reviewed; the assistant does not invoke refund or order-update operations.

The PoC may remain hybrid while base workloads stay where they are. A later fully migrated scenario can use the existing assessed Azure targets. Keep these as distinct designs with distinct costs; do not allow `cloud-only` defaults to remove required on-premises connectivity from the PoC diagram.

### 11.4 From Topology To Deployable Artifacts

The inspected HA implementation already registers `TerraformIaCGenerator`. It can generate a Terraform archive from a resolved architecture, run `terraform init -backend=false -input=false` and `terraform validate`, and report generation gaps. It also has a configurable static-input mode; verify that the real accepted architecture, not packaged sample input, is used. `EnableIaCGeneration` is independently gated. [E12]

This is valuable reuse, but **Terraform validation is not deployment, live policy/quota validation, or application testing**. The underlying generation engine is a package dependency; its complete internal implementation and AI module support were not established by this review.

For the AI extension, the FDE must review the generated resources, IAM and network configuration, model deployment choices, cost implications, and unsupported gaps. Application integration code, policy-content ingestion, permissions, evaluation datasets, and user-experience changes require additional implementation. A successfully generated infrastructure archive does not deliver those automatically.

Keep four explicit artifacts: **architecture**, **costed bill of materials**, **reviewable infrastructure/application changes**, and **approved execution plan**. They share a versioned scope and assumptions but have different validation bars.

## 12. Stage I: FDE-Led PoC And Deployment Path

### 12.1 The FDE Uses AMA Throughout

| Moment | Example AMA request | Result and owner |
| --- | --- | --- |
| Before the customer session | "Summarize the application, assessment blockers, and missing AI evidence." | Opportunity brief and targeted agenda; FDE reviews before sharing. |
| During the session | "Capture the support workflow and read back the proposed goal and restrictions." | Structured intent draft; customer owner confirms or corrects it. |
| After technical validation | "Record the API review and approved document sample; regenerate the conditional assessment." | Evidence-linked feasibility revision; findings remain scoped to what was tested. |
| During solution design | "Compare policy-only assistance with policy plus order lookup and scanned-form extraction." | Alternative capability sets, architectures, prerequisite lists, and cost deltas. |
| Before the PoC | "Prepare the ten-user PoC backlog and deployment review pack from the accepted revision." | Work packages, evaluation plan, resource estimate, ownership, and approval gates. |
| After the PoC | "Compare observed quality, effort, latency, and cost with the agreed targets." | Proceed, revise, or stop recommendation; no automatic production deployment. |

The new AMA operations are **proposed**. The current planner, QueryNet tool service, and Cortex control plane provide extension surfaces, but the inspected code does not already implement this conversation/state machine or these artifacts. [E5]

### 12.2 Concrete Work Packages

The elapsed timeline below is indicative and begins after scope, access, and funding approvals. It is not a promised Microsoft delivery SLA.

| Work package | Accountable participants | Deliverable and gate |
| --- | --- | --- |
| 1. Scope and evidence, week 1 | Customer support/app/data owners + FDE | Confirm task baseline, approved samples, API boundaries, negative cases, and PoC scope. No production-data processing before approval. |
| 2. Environment and integration, weeks 1-2 | Platform/security owner + FDE/customer engineers | Review architecture and current prices; obtain capacity/quota; prepare IaC, secrets/identity, connectivity, monitoring, and an approved deployment pipeline. |
| 3. Retrieval and draft response, weeks 2-3 | AI/app engineers + content owner | Limited guidance corpus, permission enforcement, citations, fallback, and response draft in the portal/test experience. |
| 4. Order lookup and extraction, weeks 3-4 | Application engineers + data/subject-matter owners | Only the validated read-only API and approved forms; field checks, least-privilege access, and explicit failure behavior. |
| 5. Controlled evaluation, weeks 4-5 | FDE + support users + security reviewer | Held-out evaluation, representative user trial, cost/latency measurement, and permission/failure tests. |
| 6. Decision and handoff, weeks 5-6 if needed | Sponsor + application/platform owners + delivery lead | Accept results, narrow/rescope, or stop. Production backlog and operational handoff only after separate approval. |

A six-person-week estimate is an effort assumption, not six weeks of every person's full-time participation. Waiting for data access or an application change can extend the elapsed timeline; do not hide it in model-generation latency.

### 12.3 Proposed Acceptance Criteria

Agree these before testing; the numbers are example targets, not measured results:

- Support-task median time falls from the validated baseline of eight minutes to six or less on comparable tasks, including employee review time.
- At least 90% of held-out answers meet the jointly defined correctness/usefulness rubric; separately report material factual errors, citations, and abstentions.
- Required extracted fields meet an owner-agreed field-level accuracy threshold; an aggregate average cannot hide errors in important fields.
- Tests cover users without case access, cross-user/cross-tenant requests, stale or conflicting policy content, prompt injection in documents, unavailable APIs, and unanswerable questions. No known unresolved authorization leaks or prohibited writes.
- For the agreed load, normal answer generation meets the proposed latency target, for example p95 under eight seconds. Report asynchronous form-processing latency separately.
- Actual billed usage and estimated human operating effort remain within the approved PoC envelope, or deviations are understood and explicitly accepted.
- Pilot users receive training and a way to report problems. Measure eligible-user adoption, completed tasks, corrections, overrides, and review effort against agreed criteria; logins or generated answers alone do not establish useful adoption.
- Fallback to the existing workflow works; disabling the assistant does not prevent the order application from operating.

Use held-out data and an appropriate baseline/staged comparison. Ten users and a small dataset provide directional evidence, not a proof of universal reliability. A customer-facing extension would require a new risk and rollout assessment.

### 12.4 Where Execution Lives

`GenerateWaveRunbookExecutionPlanWorkflow` in MigrationMgmtSvcs currently filters to supported VMware agentless VM rehost and Azure Files/Storage Mover scenarios, then builds steps from provider manifests and inserts approval gates. It does not establish native deployment of this AI solution. [E14]

For the first pilot, export the reviewed backlog/design/estimate and use an FDE/customer-owned repository and approved deployment pipeline. Link status and results back to the assessment. A later native runbook integration needs new task/provider contracts, preflight checks, approval semantics, rollback, identity, and testing. Do not run an arbitrary generated script just because it appears in the assessment.

### 12.5 Production Is A Separate Decision

Before production, require approved data lifecycle/retention, end-to-end identity and security review, representative scale/quality results, region/model capacity, fresh price estimates, operational ownership, user training, incident response, rollback, and controlled release. Recheck base-application integration after migration or other material changes.

The FDE contributes engineering judgment and delivery. The customer sponsor accepts business value; data/security owners authorize their domains; the platform/application owners accept production operation. FDE assignment and commercial terms depend on the actual program and account arrangements, not on an automatic entitlement created by Azure Migrate. [S5]

### 12.6 Report Evidence, Not Just Schedule Status

The materials distinguish delivery progress from quality, adoption, and value. Demonstrate that distinction through a proposed review of the same assessment, not a new dashboard that silently turns estimates into results. [T1, T2, T5]

**Rehearsal-only branch:** assume a prototype milestone is on schedule, but a fabricated evaluation result is **87% against the proposed 90% quality threshold**. This is a teaching input, not a test we ran or a result from the supplied courses.

| Review question | Evidence the owner needs | Decision in this rehearsal branch |
| --- | --- | --- |
| Did we deliver the planned artifact? | Delivery lead: milestone completion and unresolved dependencies. | On schedule does not imply ready to expand. |
| Is it reliable enough for the agreed use? | AI/app engineering lead and subject-matter reviewer: representative cases, quality distribution, material errors, and access tests. | 87% fails the proposed 90% bar: correct the failures and retest; pause expansion. |
| Are users benefiting? | Support owner: comparable completed-task timings, quality/rework, eligible-user adoption, and backlog outcome. | Not measured in this branch: no time-saving or business-value claim. |
| Is the investment still justified? | Sponsor/finance: current-scope cost, actual spend, full operating effort, and evidence for benefits. | Refresh the estimate and decide whether further validation is worth funding. |
| Who acts when something crosses a boundary? | Named operations/risk owners: issue escalation, stop authority, manual fallback, and approved resumption criteria. | Any suspected unauthorized access triggers immediate protective action, not a wait for the next steering meeting. |

For the pilot, propose weekly engineering/user reviews and a sponsor review at each decision gate. Agree any ongoing reporting cadence with the customer according to risk. Feed approved, sanitized failure examples into regression evaluation without contaminating the final holdout set. Changing models, source data, permissions, user groups, or allowed actions triggers proportionate revalidation and repricing, not automatic reuse of a previous approval.

## 13. How We Build This In Azure Migrate

### 13.1 Proposed Internal Flow

```text
Existing inventory + reviewed application + assessment snapshots
			      |
		    NEW evidence/profile adapter
			      |
Existing AMA conversation -> NEW confirmed intent + evidence tasks
			      |
		 NEW opportunity brief and review state
			      |
	    NEW feasibility coordinator and pattern evaluation
		 |                         |
	deterministic policy gates   bounded model assistance
		 |                         |
		 +---- validated structured result ----+
			      |
		  NEW usage-based AI costing
			      |
	  Existing CTD + NEW AI composition/catalog support
			      |
	 Versioned assessment + design + estimate + PoC backlog
			      |
	      Explicit customer/FDE acceptance and handoff
			      |
    Existing IaC/export surfaces where supported; approved delivery
			      |
		    Evidence-based outcome update
```

Do not put an application's AI business intent inside the Container FunctionApp or interpret it as another AKS suitability rule. The coordinator should be application/workflow-oriented, with workload assessments supplying facts and reusable compute infrastructure used only where its contracts fit.

### 13.2 Five-Layer Implementation Map

Candidate locations below are **proposed ownership boundaries**, not existing AI endpoints or committed team assignments. Source references explain the precedent and the change required.

| Layer / workstream | Reuse and candidate home | New work and reason |
| --- | --- | --- |
| ARM/API, WS2 | ApplicationMigration/ResourceProvider registration patterns; existing application assessment interfaces. | Review the new resource/action shape, permissions, asynchronous status, and versioning. No AI resource name/API version is approved in this document. |
| ARM-facing models, WS5/WS6 | AppCentricAssessments `ApplicationAssessments.RestApi` and existing controller/helper separation; partner precedent in ASV2. [E8-E9] | Application/workflow scope, intent/evidence revision references, capability dispositions, review status, and links to outputs. Do not reuse infrastructure readiness as AI feasibility. |
| Persistence, WS5/WS6/WS11 | AppCentricAssessments `ApplicationAssessments.DataModel`, Cosmos operations, collected-data cache, and resolved-architecture store. [E9-E10] | Versioned opportunity and feasibility records, evidence provenance/consent, gaps, owners, approvals, expiry, and deletion. Chat history is not the system of record. |
| Compute contract, WS5 | ASV2/FunctionApps input/compute/validation/output patterns; application workflow coordinator. [E6-E8] | Separate evidence, pattern eligibility, model-assisted drafting, policy/output validation, and metered AI cost calculations. Use namespaced internal contracts before a public API. |
| Integration, WS7/WS8/WS9 | Portal application entry point; AMA planner, QueryNet tools, Cortex; HA/BizCase/report consumers. [E4-E5, E15] | Read/update/approve tools for intent and evidence, opportunity/assessment generation, scenario comparison, export, and accepted FDE handoff. Preserve source authorization. |
| CTD and IaC, WS6/WS9 | HA resolver, catalog, peripheral pricing, Terraform adapter, and MigrationMgmtSvcs artifacts. [E9-E14] | Container-to-CTD support, AI composition/model/usage contracts, approved catalog and IaC modules, pricing support, and explicit unpriced/unsupported states. |
| Verification and operations, WS10/WS11/WS13/WS14 | Existing unit/golden/integration patterns; owning service's deployment and Geneva conventions. [E16] | Permission/consent/deletion tests, recommendation evaluation, cost reconciliation, no-AI cases, degradation, budget controls, observability, and regional release gates. |

WS1/WS3/WS4/WS12 remain providers of existing authorized discovery in the first pilot. Do not expand guest privileges or add business-content crawling merely to support this assessment. Richer code/API/data validation is a separately approved source of evidence. The host service can reuse its OneAKS/Geneva infrastructure; the customer's Foundry inference is not assumed to run inside Azure Migrate's cluster.

### 13.3 Minimum New Records

These logical names are illustrative, not approved API types:

| Record | Why it is needed |
| --- | --- |
| `ApplicationEvidenceProfile` | Stable resource/relationship/snapshot references, freshness and gaps; distinguishes observed facts from supplied descriptions. |
| `AiIntentBrief` | Theme, workflow, users, baseline/goal, constraints, scope, and confirming owner. |
| `AiOpportunityBrief` | Hypotheses, fit evidence, questions, alternatives, and proposed next meeting/action. |
| `AiFeasibilityResult` | Per-capability disposition, evidence, prerequisites, chosen alternatives, risk/complexity, and validation state. |
| `AiUsageAndCostEstimate` | Quantities, units, rates, source/date/region/currency, sensitivity, exclusions, shared-resource attribution, and reserve. |
| `AiDesignExtension` | Approved new components and data flows tied to the existing topology, with catalog/estimate versions. |
| `AiDeliveryHandoff` | Accepted recipient, PoC backlog, tests, approvals, artifact links, outcomes, and production decision. |

State transitions should distinguish **Draft -> NeedsEvidence -> Reviewable -> AcceptedForPoC -> InValidation -> Proceed/Revise/Stop**. These are proposed lifecycle states, not replacements for the existing assessment execution statuses. Report partial generation, stale evidence, and failed computation separately from a negative business recommendation.

### 13.4 Delivery Slices And Dependencies

1. **Report-first pilot:** evidence adapter, AMA-assisted intent capture, expert-reviewed briefs/assessments, deterministic spreadsheet-equivalent costing, and a manual architecture/handoff. This proves utility without claiming unsupported CTD automation.
2. **Connected product experience:** versioned persistence and tools, consent/owner tasks, catalog-backed AI design, supported container mapping, price integration, and export. Required before claiming the mixed application is fully represented automatically.
3. **Execution integration:** supported IaC modules, preflight/approval/deployment tasks, controlled ingestion, evaluation and outcome links. Required before offering a native "start PoC" execution action.

The dependency is evidence/intent contracts -> feasibility/policy and usage model -> AI CTD/catalog and price coverage -> reviewed artifacts -> explicit execution integration. Neither a new prompt nor a new catalog entry completes this chain on its own.

Measure expert preparation effort, time to customer-confirmed scope, handoff clarification cycles, material corrections, accepted PoCs, and later deployment/value outcomes. Do not count generated reports or automatically discovered groups as successful AI adoption.

## 14. A Stakeholder Demo Script

### 14.1 Lead With The Decision, Not The Inventory

The technical journey in Sections 4-13 stays in execution order. The **presentation order** starts with the customer's problem and returns to the evidence needed to make a decision. Do not make stakeholders watch server discovery complete or inspect all 15 machines before they understand why the application matters.

**Opening:** "Contoso's support lead wants employees to prepare accurate order-and-returns responses faster. An eight-minute task is our unvalidated starting estimate, not a measured result. Should Contoso invest in a ten-user AI experiment, which capability should it test first, and what must be true before spending more?"

There are two different asks: **the fictional customer** decides whether to authorize a scoped PoC; **Azure Migrate leadership** decides whether to validate this proposed product with FDEs and design partners. A customer approval is not product funding, an FDE assignment, or permission to deploy production resources.

The following is a **10-minute storyboard**, not implemented screens or a live assessment. Mark recorded source-backed surfaces as existing/snapshot-specific and proposed AMA/AI interactions as mockups. Use de-identified or fictional inputs. Do not portray generated artifacts, attractive diagrams, or a selected successful answer as proof of quality or value.

### 14.2 Eight Decision-Focused Scenes

| Scene and duration | Show and say | Decision or takeaway |
| --- | --- | --- |
| **1. Customer problem (45 seconds)** | Show one workflow: employee opens an order screen, finds guidance, reads a form, and drafts a response. State the internal-user scope, proposed time goal, and unchanged quality requirement. | "We are evaluating a specific workflow, not looking for somewhere to install a model." |
| **2. Reusable Migrate evidence (75 seconds)** | Show the reviewed application, one shared-cluster dependency, and an existing assessment result. Expand the provenance of one fact and one missing fact. Skip the full inventory tour. | "Migrate saves repeated technical discovery. It does not discover the business goal or prove an API is safe." |
| **3. Opportunity brief (60 seconds)** | Show candidate policy assistance, order lookup, and scanned-form extraction with supporting observations and questions. Contrast with an existing-product or non-AI option. No unsupported rankings or universal AI score. | "The brief prepares the FDE's conversation; it is not permission to build every candidate." |
| **4. Confirm intent through AMA (120 seconds)** | Demonstrate a short customer/FDE exchange that records baseline, target, metric, timeframe, and accountable owner. Add the use of recovered time, data/permission owners, and explicit prohibited actions. | "The customer supplies business meaning; AMA saves a reviewable agreement and routes unknowns to their owners." |
| **5. Make a scope decision (90 seconds)** | Show the feasibility comparison. The API is declared but case-level authorization is unverified; OCR sample accuracy is unknown. Keep both conditional. Show policy assistance as the first experiment only after content approval. | "Missing evidence changes the scope and validation backlog. A technical possibility is not implementation readiness." |
| **6. Explain the architecture (60 seconds)** | Reveal only the new components over the existing application. Explain Search for approved guidance, a Foundry model for drafting, and conditional extraction. Show the employee approval boundary. | "Every component has a workflow purpose. The model cannot approve a refund or grant itself data access." |
| **7. Review investment (60 seconds)** | Separate service cost, one-time engineering, and ongoing human work. Label the USD 874.56/month and USD 24,396.91 PoC figures as the full conditional demonstration scenarios from Section 10, not quotes for a narrower policy-only scope. | "A scope change requires a revised estimate. Time saved is not automatically cash saved, and no ROI is established." |
| **8. Decide and assign (90 seconds)** | Show the reviewed assessment, evidence tasks, critical-path dependencies, next gate, owners, and evaluation plan. Include a rehearsal-only 'quality below target' branch that pauses expansion even when the build is on schedule. | "Approve bounded validation, revise, or stop. Generating a plan does not deploy it or authorize scaling." |

The timing totals **600 seconds**. Keep source paths, complete inventory, rate worksheets, and catalog gaps in supporting views for questions. For an engineering review, spend the extra time on Sections 11-13; do not replace the business decision with a long service catalog tour.

### 14.3 Demonstrate A Meaningful Change In The Answer

Use the same three records throughout: **opportunity brief -> confirmed intent -> reviewed feasibility assessment**. Revisions retain evidence and show who changed the decision; they are not three independently generated essays.

> **FDE in AMA:** "Can order lookup be included in this PoC?"  
> **Proposed AMA behavior:** "The application owner says an API exists. Customer/case authorization has not been tested. I can record an integration validation task; I cannot mark lookup ready."  
> **Application owner:** "Keep it conditional until the access tests pass."  
> **Proposed result:** the assessment retains the declared API and its source, keeps the lookup capability conditional, and assigns an owner and test gate. It does not rewrite the declaration as a verified fact.

Then ask, "Can it automatically issue a refund?" The answer must explain that this is outside the confirmed scope, requires new decision authority and risk review, and cannot be enabled by a conversational request alone. This is the distinction between draft assistance and taking business actions. No actual customer-system call is needed for this proposal demo.

If a presenter selects a policy-only alternative, the architecture, quantities, and estimate must all change together; do not reuse the full conditional scenario's price as an approved policy-only quote. If a rate or input is unavailable, show **needs estimation**, not zero.

### 14.4 Executive Readout

Use one page for the decision and keep the detailed walkthrough behind it. The same versioned evidence should answer different stakeholder questions without generating conflicting claims. This adapts the materials' executive summary and initiative status formats. [T4, T5]

| Field | What the proposed Contoso readout says |
| --- | --- |
| Decision requested | Authorize the next bounded evidence/experiment step; no production rollout requested. |
| Business outcome and owner | Test a reduction in completed-task effort and use recovered capacity on aged cases. Head of Support is the proposed accountable role; identity and baseline require confirmation. |
| Selected scope | Policy assistance first, subject to content approval. Order lookup and OCR remain conditional; compare existing-product/non-AI alternatives. |
| Stage and evidence | Pre-validation. Migrate technical context is available; business metrics, data suitability, and API behavior are not yet validated. No actual AI outcome is reported. |
| Investment | Show the estimate for the selected revision. Section 10's full conditional-scenario figures are illustrative; implementation labor and ongoing human operations remain separate from Azure service charges. |
| Critical dependency and next gate | Content rights/access and available reviewers first; verified API authorization before live lookup. Set the gate date and evidence owners before starting. |
| Control and stop condition | Human review of responses, no transactional writes, and named stop authority. Pause expansion on failed quality/access/adoption gates or an unapproved material cost increase. |

### 14.5 Address The Room's Concerns

Adapt the stakeholder-response format to the proposal instead of reading a list of generic benefits. All evidence below is required or illustrative until actually collected. [T4, T5]

| Stakeholder and concern | Response and evidence to show | Accountable decision owner |
| --- | --- | --- |
| Business sponsor: "What will improve?" | Baseline, target, quality guardrails, and how recovered capacity will be used. Do not substitute a faster model response for an improved support task. | Customer business sponsor. |
| Finance: "Are the savings real?" | Separate time saved, productive capacity, and expenses actually removed; show full costs, assumptions, and downside. No ROI claim until benefits are supported. | Customer budget owner/finance approver. |
| FDE/app team: "Does this save engineering effort?" | Reusable scoped application evidence, remaining questions, dependency owners, and an accepted backlog. Measure preparation effort and clarification cycles. | Engagement lead with customer application owner. |
| Security/data owner: "Can this expose restricted data?" | Source-use approval, permission model, test evidence, retention, escalation and stop controls. A generated architecture is not security approval. | Customer data/security approval owners. |
| Employees: "How will my work change?" | Show the draft/review flow, training, issue reporting, and how users shape evaluation. Do not promise either headcount savings or no job impact. | Support business owner with participating users. |

### 14.6 Close With Two Clear Asks

**Customer decision:** "Authorize the agreed evidence collection and bounded experiment, name the business and technical owners, and approve the revised scope, estimate, and access controls before execution. Return at the next gate with measured quality, task effort, adoption, and cost."

**Azure Migrate leadership decision:** "Sponsor a small FDE/design-partner validation of this experience. Test whether reuse of Migrate context reduces preparation effort and time to an accepted scope, while preserving recommendation quality. Decide on product investment from that evidence."

**Closing sentence:** "Azure Migrate helps the FDE understand the application; AMA captures the customer's intended outcome; AI Feasibility turns both into a decision the customer can inspect, cost, test, and revise."

## 15. Source Register And Verification Limits

### 15.1 Research Coverage

The research inventoried **32 local repositories**, including this design repository, recording their tracked-file/source-tree layouts and local HEADs. It then followed the controlling discovery, Portal application, AMA, assessment, CTD, costing, IaC, and runbook paths cited below. It is **not a line-by-line audit of every repository**. Supporting repositories listed as surveyed were mapped from the repository index and source layout, not independently certified for all capabilities.

No sibling checkout, branch, package version, or Azure resource was changed. Source/tests were inspected; the large service test suites and a live customer discovery/assessment/deployment were not executed. The fictional application and all financial rates are teaching inputs. Source availability, supported contracts, feature gates, and deployment availability are separate facts.

The automatic grouping backend implementation was not located in the inspected backend checkouts; its Portal/DiscoveryService callers were verified and its documented behavior was sourced from Microsoft Learn. The empty nested `azure-migrate-container-discovery` checkout and the script-packaging repository do not establish a full production container-discovery implementation. The package-internal IaC generator and nonlocal reference repositories are outside this source trace. These gaps must be resolved with the owners before implementation estimates are committed.

### 15.2 Local Repository Inventory

All repositories below are siblings under `C:/Users/nigadh/source/repos/`. HEADs are local snapshots, not claims of latest upstream or deployed revisions. "Traced" means the specific paths in the evidence register were inspected, not every file in that repository.

| Repository | Local HEAD | Coverage in this walkthrough |
| --- | --- | --- |
| AzureMigrate-WebAppAgent | d3d2aad63076 | Traced web discovery workflow; pre-existing local source edits exist. |
| AzureMigrate-VMWareAgent | effcc692aa34 | Surveyed fabric-agent source/package layout. |
| AzureMigrate-HyperVAgent | 446eb56083a4 | Surveyed fabric-agent command layout. |
| AzureMigrate-ServerAgent | 2581845b0e2b | Surveyed physical-server discovery layout. |
| AzureMigrateAgents | ec2103cfcd33 | Traced shared dependency aggregation. |
| AzureMigrate-ServiceCommon | 067952c212ce | Traced dependency data contract; local branch may lag other consumers' package versions. |
| AzureMigrate-ApplianceComponents | c494e54a2631 | Surveyed appliance/deployment/test layout. |
| AzureMigrate-DiscoveryService | ff9c82302d22 | Traced dependency-map and post-import auto-application calls. |
| AzureMigrate-ApplicationMigration | 95acbc81e654 | Surveyed RP/API layout; no grouping algorithm found. |
| AzureMigrate-ResourceProvider | f081fc0e1460 | Surveyed RP/application layout. |
| AzureMigrate-AssessmentServiceV2 | 28f74cec59e3 | Traced partner entities, create/consume, manifest, container topology/plan relationships. |
| AzureMigrate-AssessmentFunctionApps | 42781da2594d | Traced container execution, shared orchestration, and golden-test structure. |
| AzureMigrate-Assessment-AKS-POS | eae51887de88 | Surveyed separate WebApp-to-AKS assessment surface. |
| AzureMigrate-Assessment-AKS-Java | 82186218e063 | Surveyed associated assessment worker layout. |
| AzureMigrate-AppCentricAssessments | b554c79e47ad | Traced application workflow, CTD mapper/resolution, peripheral cost, Terraform, and neighboring tests. |
| AzureMigrate-AssessmentService | 5121f56fb92d | Surveyed VM/SQL assessment and pricing layout. |
| AzureMigrate-WebAppCompoundAssessment | 073e7723e31c | Surveyed WebApp compound assessment layout. |
| AzureMigrate-Portal | ec255e9506e9 | Traced auto-application initiation, status, membership queries, and updates. |
| azure-migrate-ai-querynet-migrate-agent-tools | 89db87e8bc81 | Traced assessment scope, deployment, and result-tool surface. |
| azure-migrate-ai-agents | fd97c74e07e0 | Traced planner instructions and existing domains. |
| azure-migrate-ai-assistant-cortex | 3988aa459532 | Inspected control-plane/conversation/state architecture and source layout. |
| AzureMigrate-BusinessCaseService | 138e7235fc26 | Traced partner-assessment actions and dependency boundary. |
| AzureMigrate-Reporting | 9e53a41aa0dd | Surveyed reporting function/library layout. |
| AzureMigrate-MigrationMgmtSvcs | b3f4ab1fca1a | Traced runbook scope filtering, step generation, and approval insertion. |
| AzureMigrate-IntegrationTests | 7618dfda3dc4 | Surveyed integration-client/fixture layout; no live suite run. |
| AzureMigrate-RegionBuildout | 72cf1fafaea6 | Surveyed deployment/service configuration layout. |
| AzureMigrate-Geneva | 776b7e6d700b | Surveyed telemetry/release configuration layout. |
| AzureMigrate-ContainerDiscovery | 08286d3c5e1b | Inspected collector/aggregator packaging and documentation; not end-to-end service coverage. |
| AzureMigrate-ContainerDesign | 817401bcb744 | Repository index, related CTD review, proposal, and this new walkthrough. |
| CloudTopologyDesign-ArchitectureCatalog | 2b6874b82491 | Inspected catalog schema/release guidance and generated module/entry inventory. |
| Azure-AppModernizationService | e0168a218860 | Surveyed modernization/discovery/deployment layout as an adjacent implementation surface. |
| AzureMigrate-CodeScanningService | 86322ecd9707 | Surveyed optional code-insight workflow surface; not assumed to validate business APIs. |

### 15.3 Implementation Evidence

Paths below are relative to the named sibling repository. They are source evidence and candidate reuse locations, not approved edits. Earlier [Beyond_N_CTD_Review.md](Beyond_N_CTD_Review.md) is related context; this walkthrough rechecked the current owning paths rather than assuming its older snapshot still describes every behavior.

**E1. Web workload discovery:** `AzureMigrate-WebAppAgent/src/WebAppAgent/WebApp/WebAppEngine/Workflows/RefreshFabricLayout.cs`, `RefreshFabricLayout.AddNewFabricLayoutIntoMapAsync`. Reads target signatures, invokes discovery helpers, preserves results/errors, and supplies suitability-report context. Existing local edits were not changed by this task.

**E2. Connection processing:** `AzureMigrateAgents/src/DependencyMap/DataAggregrator.cs`, `RemoveDuplicateProcesses`, `FilteroutConnections`, and `GetConnectionKey`. Confirms process/connection aggregation rather than business API discovery.

**E3. Network evidence contract:** `AzureMigrate-ServiceCommon/src/ServiceContract/DiscoveryService/DiscoveryServiceContract/AgentDataContracts/DependencyMap/ConnectionInfo.cs`. Defines host/process/IP/port/count/timestamp evidence. The discovery-side map controller is `AzureMigrate-DiscoveryService/src/WebRole/Versioned/2020-01-01-preview/Controllers/VMWare/DependencyMapController.cs`.

**E4. Application creation and membership:** `AzureMigrate-Portal/src/ux/AzureMigrate.Extension/Client/React/Views/Applications/Helpers/AutoAppDiscoveryHelper.ts`, `startAutoDiscovery`, `triggerAutoAppDiscovery`, and `mapHubToInfo`; `Client/React/Views/Data/Applications/Data/ApplicationData.ts`, `getApplicationMembers` and `updateApplicationProperties`, under the same extension root. Backend caller: `AzureMigrate-DiscoveryService/src/VMwareTeeImplementation/TaskHandlers/MasterSiteTasks/PostHydrationUpdatesTask.cs` and `PartnerArmHelper/ApplicationMigrationArmResourceHelper.cs`. Caller and published behavior are verified; the backend algorithm is not.

**E5. AMA extension boundaries:** `azure-migrate-ai-agents/src/agents/planner/instructions/migrate_agent_planner.md` defines the current migration-domain routing. `azure-migrate-ai-querynet-migrate-agent-tools/src/querynet/app/services/assessment_service.py`, `AssessmentService.create_or_update_assessment`, resolves scope and creates assessment resources. `azure-migrate-ai-assistant-cortex/README.md` describes conversation/control-plane endpoints, the forwarding worker, and state surface. These are not existing AI-opportunity endpoints.

**E6. Container producer and consumer:** `AzureMigrate-AssessmentServiceV2/src/Workloads/Workflows/Assessment/CreateAssessment/Container/CreateContainerAssessmentHelper.cs`, `GetAdditionalArmResources`, `GetAssessmentMessageAsync`, and `GetMachineArmIdsOfAssessableInstances`; neighboring `ConsumeContainerAssessmentHelper.cs`, `BuildRecommendedPlans` and `RecommendedPlanArmId` assignment. Preserves workload-to-node/cluster/host and recommended-plan boundaries.

**E7. Container and generic computation:** `AzureMigrate-AssessmentFunctionApps/src/Container/Container.FunctionApp/ContainerWorkloadAssessmentClient.cs`, `DoValidation` and `DoExecution`; `src/AssessmentFunctions/AssessmentOrchestrator.cs`; Mongo's `src/Mongo/Mongo.FunctionApp/MongoAssessmentTriggerFunction.cs` provides the blob-to-orchestrator precedent. These establish asynchronous compute/validation patterns, not AI workflow feasibility.

**E8. Partner model/contract precedent:** `AzureMigrate-AssessmentServiceV2/src/Workloads/DataModel/Container/Entities/ContainerAssessmentEntity.cs`; `Mongo/Entities/MongoAssessmentEntity.cs`; `PGSQL/Entities/Assessed/PGSQLAssessmentEntity.cs`; `FileShare/Entities/Assessed/FileShareAssessmentEntity.cs`; `Oracle/Entities/OracleAssessmentEntity.cs`, all under the same `DataModel` root. Each uses the shared assessment base with partner-specific details. `src/Workloads/Workflows/ManifestStore/Container.json` validates output attributes. Mongo controller/create/consume patterns cited in the main proposal remain relevant. AI context and cost need their own contract, not container fields or infrastructure SKU attributes.

**E9. Application aggregation and CTD orchestration:** `AzureMigrate-AppCentricAssessments/src/ApplicationAssessments/ApplicationAssessments.Workflows/CreateAssessment/ComputeApplicationAssessmentWorkflow.cs`, `CatalogueWorkflow.cs`, and `ResolveArchitecturesWorkflow.cs`; `ApplicationAssessmentWorkflowModule.cs` at the workflow-project root. Establishes conditional CTD/network/peripheral orchestration, stateless resolver registration, vendored catalog loading, and optional IaC generation.

**E10. Mapping, defaults, and missing containers:** same repository, `src/ApplicationAssessments/ApplicationAssessments.Workflows/Resolver/CollectedDataResolverMapper.cs`; `src/Common/Ctd.Resolver/Services/ResolutionPipeline.cs`. Establishes supported member routing, explicit container exclusion, and N-tier/cloud-only defaults that must not masquerade as customer intent.

**E11. Supported pricing and repeat-merge behavior:** same repository, `src/ApplicationAssessments/ApplicationAssessments.Workflows/Resolver/PeripheralComponentDeriver.cs`; `src/Core/Common/Clients/PeripheralResource/Mapping/PeripheralServiceModuleMap.cs`; `src/ApplicationAssessments/ApplicationAssessments.Workflows/CreateAssessment/Helper/PeripheralCostMerger.cs`. Recognized types only, derived settings, and delta-based cost merge. Token/page/query pricing for the proposed AI solution is additional work.

**E12. Infrastructure generation boundary:** same repository, `src/ApplicationAssessments/ApplicationAssessments.Workflows/IaCGeneration/TerraformIaCGenerator.cs`; `src/Core/Runtime/Settings/FeatureFlags.cs`; `src/Core/Runtime/Settings/IaCGenerationSettings.cs`. Shows archive generation, init/validate, gap reporting, independently gated execution, and configurable real/static input. Does not perform application deployment or prove AI module support.

**E13. Catalog governance and coverage:** `CloudTopologyDesign-ArchitectureCatalog/README.md`; tracked entries in `catalogue/autogenerated-yaml/canonical/` and `catalogue/autogenerated-yaml/service-modules/`. Shows current N-tier entry coverage, parameter rules, and KG-driven contribution/review/release. No AI modules were present in the inspected generated inventory. Runtime adoption must be verified separately.

**E14. Runbook scope and approvals:** `AzureMigrate-MigrationMgmtSvcs/src/WorkflowEngine/Workflows/Workflows/Runbook/GenerateWaveRunbookExecutionPlanWorkflow.cs`. Validates target/tool selection, filters supported VMware rehost and file-share migrations, creates manifest-derived steps, and inserts approval gates. This is reuse precedent, not existing AI PoC execution.

**E15. Business-case integration:** `AzureMigrate-BusinessCaseService/src/BusinessCaseService/AppMod/Partners/MongoWorkload/MongoAssessmentPartnerActions.cs`, `IPartnerAssessmentActions`, `DependsOn`, and `CreateAssessmentAsync`. Demonstrates explicit dependencies and resource operations; proposed AI benefit/usage assumptions must not be folded blindly into migration TCO.

**E16. Neighboring validation patterns:** `AzureMigrate-AppCentricAssessments/test/ApplicationsAssessments.UnitTests/ApplicationsAssessments.UnitTests/Workflows.ApplicationAssessments/Resolver/MapperEdgeCaseTests.cs` pins host identity, engine detection, missing recommendations, and defaults. `AzureMigrate-AssessmentFunctionApps/test/IntegrationTests.Container/ContainerHappyPathIntegrationTests.cs` uses `GoldenFileAsserter` against the actual FunctionApp response. These tests were read, not executed for this documentation task.

### 15.4 Official Sources

- **S1:** [Explore application inventory](https://learn.microsoft.com/azure/migrate/define-manage-applications?view=migrate), accessed 27 September 2026. Automatic grouping signals, defaults, review/member changes, shared workloads, discovery-mode limits, and current one-time operation.
- **S2:** [Plan and manage Azure AI Search costs](https://learn.microsoft.com/azure/search/search-sku-manage-costs), accessed 27 September 2026. Dedicated search-unit billing, distinct serverless pricing, and separately charged features. Prices in this walkthrough are not taken from this page.
- **S3:** [Document Intelligence usage and cost estimation](https://learn.microsoft.com/azure/ai-services/document-intelligence/how-to-guides/estimate-cost?view=doc-intel-4.0.0), accessed 27 September 2026. Processed pages, model/feature breakdown, and region/payment-option estimation.
- **S4:** [Azure OpenAI cost management](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/manage-costs) and [Foundry RAG concepts](https://learn.microsoft.com/azure/foundry/concepts/retrieval-augmented-generation). Supports usage-based estimation, retrieval/embedding considerations, and access-control requirements; not a quote or a guarantee of quality.
- **S5:** [Microsoft Principal FDE role](https://apply.careers.microsoft.com/careers?query=Forward+Deployed&start=0&pid=1970393556939578&sort_by=relevance), inspected in the preceding proposal discussion on 24 September 2026; [ISE envisioning/problem formulation](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/envisioning-and-problem-formulation/) and [feasibility studies](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/feasibility-studies/). Supports customer problem framing, engineering validation, scope handoff, and production-oriented delivery. Actual program intake and capacity require owner confirmation.

### 15.5 Required Implementation Checks

Before calling the feature end-to-end, verify: correct application scope across shared hosts; supported container membership/CTD mapping; evidence and intent versioning; permission-preserving retrieval/API access; region and data-processing constraints; complete priced/unpriced service coverage; repeat-run cost reconciliation; current catalog and IaC module versions; real-input generation; safe reviewable deployment artifacts; separate execution approval; held-out evaluation; deletion/retention; and graceful failure without breaking the existing migration assessment.

Documentation verification for this walkthrough checks the 15-host inventory arithmetic, the example improvement target, all cost scenarios and totals, source-anchor existence, major source-backed boundary claims, Markdown structure, and the relationship between the brief, assessment, CTD, and PoC. It does not substitute for those future product and customer validation gates.

### 15.6 How The Supplied Materials Improve This Demo

Reviewed on **28 September 2026**: both supplied transcript-style PDFs and all three slide-deck PDFs, **98 PDF pages in total**. Text was extracted page by page; deck contact sheets and selected framework slides were inspected visually. References below use **PDF page numbers**, not timestamps or assumed slide numbers. These are user-supplied educational sources for communication/leadership practices, not Azure capability, pricing, or customer-outcome evidence. Original wording is synthesized rather than reproduced.

| Reference and local source | Relevant PDF pages | Adaptation in this walkthrough |
| --- | --- | --- |
| **T1:** [ai-project-startegy/AI Project Leadership.pdf](ai-project-startegy/AI%20Project%20Leadership.pdf), 6 pages | 2-3: business value, evaluation, data and people; 4-5: accountability and intervention; 6: ongoing review. | Outcome-to-capacity connection in Section 8; decision/stop authority in the charter; evidence-based review and revalidation in Section 12.6. |
| **T2:** [ai-project-startegy/leading-ai-projects-slides.pdf](ai-project-startegy/leading-ai-projects-slides.pdf), 37 pages | 11-22: five success factors; 23-28: accountability and decision authority; 30-34: oversight; 35-37: leadership questions. | Explicit response approval and stop controls; a failed-quality branch even when delivery is on schedule. Oversight is described by the actual action/approval boundary, not just a label. |
| **T3:** [ai-project-startegy/developing-a-scalable-generative-ai-strategy-slides.pdf](ai-project-startegy/developing-a-scalable-generative-ai-strategy-slides.pdf), 25 pages | 10-12: measurable objective and one-page vision; 14-19: value/readiness/feasibility/resources; 21-25: milestones, dependencies, and gates. | Confirmed decision charter, qualitative scope comparison, and a demo centered on decisions rather than a service inventory. |
| **T4:** [ai-project-startegy/Documenting and Communicating a Generative AI Strategy.pdf](ai-project-startegy/Documenting%20and%20Communicating%20a%20Generative%20AI%20Strategy.pdf), 11 pages | 1-4: outcome-first strategy and prioritization; 5-6: roadmap and critical path; 7-8: cost/value; 9-11: stakeholders, executive package, and governance. | Targeted AMA questions, why the first capability is selected, critical dependencies, audience-specific responses, and separate customer/product-leadership asks. |
| **T5:** [ai-project-startegy/presenting-and-sustaining-the-ai-strategy-slides.pdf](ai-project-startegy/presenting-and-sustaining-the-ai-strategy-slides.pdf), 19 pages | 3-9: time/capacity/cash, full costs, scenarios and funding gates; 14-15: users/stakeholder response; 17-19: executive summary and evidence-supported status. | Executive readout, stakeholder concern-to-evidence table, user adoption measures, and a review that separates delivery progress from value. |

**What we deliberately did not import:** the courses' sample ROI amounts, external adoption/productivity statistics, example sample sizes, dates, legal interpretations, or implied general permission for autonomous actions. Those need independent validation and customer-specific applicability. Transcript transcription artifacts must not become financial or technical claims. The existing cost worksheet is unchanged and remains demonstration arithmetic; the 87% review example is separately labeled rehearsal data.

**Scope of this revision:** narrative and proposed decision artifacts for the existing WS7/WS8/WS9 experience, plus ownership and evaluation criteria. It does not change any source-code findings, feature gates, container target phases, CTD coverage claims, ARM contracts, or deployment permissions. The materials help communicate and evaluate the proposal; they do not make the proposed AI feature implemented.