# Azure Migrate AI Feasibility Assessment — Product Demo Script

**Target runtime:** 8–9 minutes  
**Format:** 16:9, 1080p, narrated product demo  
**Audience:** Azure Migrate leadership, product engineering, field, partner, and AI platform stakeholders  
**Tone:** Visionary but credible; customer-outcome first; evidence-based; no production-readiness or pricing claims  
**Demo application:** `BPTco` (use this exact spelling because it matches the simulator UI)  
**Feature status:** Proposed Azure Migrate concept demonstrated through a bounded simulator prototype

## Core message

Azure Migrate already understands enough about an application to create a strong technical starting point. AI Feasibility Assessment combines that application intelligence with customer-confirmed business intent to answer a new question:

> Given what we know about this application, where can AI create meaningful value, and what would it take to make it real?

The differentiator is not an opaque LLM score. It is a reviewable decision pack grounded in observed application evidence, customer-provided context, explicit assumptions, deterministic cost arithmetic, and visible gaps.

---

# Run of show

| Time | Visual | Purpose |
|---:|---|---|
| 00:00–00:20 | Slide 1 | Set the AI-era ambition |
| 00:20–01:00 | Slide 2 | Establish Azure Migrate's existing application intelligence |
| 01:00–01:45 | Slide 3 | Explain the cloud-era gap and the two strategic questions |
| 01:45–02:15 | Slide 4 | Introduce the extended journey |
| 02:15–02:55 | Slide 5 | Define the four decisions the assessment must support |
| 02:55–03:30 | Slide 6 | Explain inputs, outputs, and evidence principle |
| 03:30–03:45 | Slide 7 | Introduce the BPTco demo scenario |
| 03:45–07:15 | Live product | Show base application → assessment → AI-ready architecture |
| 07:15–07:45 | Slide 8 | Summarize what the demo proves |
| 07:45–08:15 | Slide 9 | State the larger product vision |
| 08:15–08:50 | Slide 10 | Close with ecosystem and validation path |

---

# Slide narration

## Slide 1 — Azure Migrate in the AI era

**On-screen title:** `Azure Migrate in the AI era`  
**Subtitle:** `AI Feasibility Assessment — from application intelligence to an actionable AI modernization decision`

**Narration:**

> Azure Migrate helps customers understand and modernize their on-premises estate. In the AI era, we have an opportunity to extend that journey. Not only helping customers decide how to move an application to Azure, but also helping them identify where AI can create meaningful value—and what it would take to deliver that value responsibly.

**Presenter cue:** Pause briefly on the subtitle. Do not call this a shipping production feature; describe it as the proposed experience demonstrated by the simulator prototype.

---

## Slide 2 — Azure Migrate already builds application intelligence

**Narration:**

> Azure Migrate begins with discovery. It prepares an inventory of virtual machines, web applications, databases, file shares, containers, and supporting dependencies.
>
> Customers can then organize these components as a complete application—a unit that works and moves together. Assessment maps each component to an appropriate Azure target. A web application might map to Azure App Service. SQL Server might map to Azure SQL Managed Instance. A containerized workload might map to Azure Kubernetes Service.
>
> This gives us rich application intelligence: the application boundary, the current technology, assessed Azure targets, dependencies, readiness, and cost context.

**Emphasis:** Say **application intelligence**, not just infrastructure inventory.

---

## Slide 3 — Cloud-era answer. AI-era opportunity.

**Narration:**

> That assessment is excellent at answering the cloud-era question: where and how should this application run in Azure?
>
> But customers increasingly ask a second question: how can I use AI in this existing application? And, if I already use AI on-premises, how should I modernize that capability in Azure?
>
> This leads to two strategic questions for us. First: how do we help customers find credible AI opportunities in the applications they already own? Second: what should the next generation of Azure Migrate look like in the AI era?

**Presenter cue:** Pause after each question.

---

## Slide 4 — Extend the migration journey

**Narration:**

> The proposed idea is an AI Feasibility Assessment as a new step in the Azure Migrate journey.
>
> Discover. Assess. AI Feasibility Assessment. Design. Estimate. Modernize.
>
> It adds an AI modernization layer on top of existing application intelligence. The goal is not to turn every application into an AI project. The goal is to identify which application-and-workflow combinations justify a bounded experiment, which need remediation first, and which should not pursue AI.

**Emphasis:** The unit is **application plus business workflow**.

---

## Slide 5 — Four decisions the assessment must support

**Narration:**

> For each selected application, the assessment should answer four practical questions.
>
> Where can AI create meaningful business or engineering value?
>
> Is the application and its data technically ready for that scenario?
>
> Which integrations, Azure services, and security or governance controls are required?
>
> And what is the pragmatic path from proof of concept, to pilot, to production?
>
> The output is a reviewable decision pack with explicit evidence gaps and production gates—not a generic list of AI ideas.

---

## Slide 6 — Evidence in. Decision pack out.

**Narration:**

> The experience combines two evidence streams. Azure Migrate contributes observed application facts: components, dependencies, runtime, assessed targets, and migration findings. The customer contributes the business meaning: the process to improve, users, desired outcome, data constraints, compliance needs, and expected usage.
>
> The assessment then produces a feasibility summary, data and integration readiness, governance considerations, evidence-backed opportunities, recommended Azure AI services, indicative cost scenarios, an AI-ready architecture extension, and a PoC roadmap.
>
> The key design principle is explainability. Observed facts, customer-provided context, inferred assumptions, and missing evidence remain visibly separate. Rules and deterministic calculations control the decision pack. Generative AI can improve the narrative, but it does not silently invent readiness or cost.

**Presenter cue:** Point to the evidence labels and the `Not an opaque LLM score` statement.

---

## Slide 7 — Live demo: BPTco document processing

**Narration:**

> Let’s see the proposed experience in the Azure Migrate simulator. Discovery and assessment are already complete. We will start with the BPTco application, inspect its current Azure architecture, capture a document-processing outcome, generate an AI Feasibility Assessment, and then see exactly where the proposed AI services fit in the application landing zone.

**Transition:** Switch from PowerPoint to the browser without narration overlap.

---

# Live product demo

## Scene 1 — Application Groups: select BPTco

**Action:**
1. Select **Plan**.
2. Select **Application Groups**.
3. If needed, select **Detect Groups**.
4. Focus on the `BPTco` card.

**Narration:**

> Discovery and assessment are already complete, so we move directly to Plan. Application Groups brings related infrastructure and workloads together as one application. BPTco includes its virtual machines and the discovered web, database, container, orchestration, and file-share components that belong to the application boundary.
>
> This is the scope we carry forward. AI feasibility is not assessed against an isolated server. It is assessed against the complete application and a customer-confirmed workflow.

**Duration:** 25–30 seconds.

---

## Scene 2 — Current landing-zone architecture, AI off

**Action:**
1. Select **Landing Zone**.
2. Confirm **AI-ready architecture** is **off**.
3. Keep **PaaS Preferred** and **East US**.
4. Select **Generate Architecture**.
5. Select **View Architecture** on `BPTco`.
6. Pan only enough to show the title, Azure boundary, workload tier, and data/storage tier.

**Narration:**

> First, we look at the current proposed Azure architecture with AI turned off.
>
> This is the application landing-zone view produced from the migration assessment. It shows secure ingress, network boundaries, shared platform services, assessed application targets, and data or storage dependencies. At this point, the design answers where and how BPTco could run in Azure. It does not yet add an AI capability.

**Duration:** 35–40 seconds.

---

## Scene 3 — Start AI Feasibility Assessment

**Action:**
1. Select **Decide**.
2. Open **Discovery & Assessment**.
3. Select the inner **Assessment** tab.
4. Select **Start assessment** in the AI Feasibility banner.
5. Select application `BPTco`.
6. Select **Document Processing and Enrichment**.

**Narration:**

> Now the customer wants to explore an AI opportunity for the same application.
>
> In Decide, the Assessment experience includes AI Feasibility Assessment. We select BPTco, then choose the broad solution idea: Document Processing and Enrichment.
>
> These categories guide the assessment; they do not predetermine a service purchase or claim that the scenario is feasible.

**Duration:** 30–35 seconds.

---

## Scene 4 — Capture customer intent and outcome

**Action:** Paste the following into **Describe the process or workload to improve**:

> Use AI in BPTco to streamline the processing and enrichment of business documents, such as invoices, contracts, and supporting attachments. Automatically classify documents, extract key information—including names, reference numbers, dates, and amounts—and enrich them with standardized metadata and concise summaries. Validate extracted information against business rules and route exceptions or low-confidence results for human review.

Paste the following into **Expected business outcome**:

> Reduce manual data-entry effort by 60% and document-processing time by 50%, while targeting 95% accuracy for critical fields across supported document types. Improve document searchability, data consistency, and downstream reporting so employees can spend less time reviewing documents and more time resolving exceptions. Maintain controlled access, human approval for critical updates, and an audit trail.

**Narration while pasting:**

> The customer now supplies the context discovery cannot infer. Here the process is document intake and enrichment across invoices, contracts, and attachments. The intended capability is classification, field extraction, metadata enrichment, summarization, business-rule validation, and human review for exceptions.
>
> The business outcome is explicit: reduce manual data entry by sixty percent, reduce processing time by fifty percent, and target ninety-five percent accuracy for critical fields—while keeping controlled access, approval, and auditability.

**Optional alternative:** Use the prepared file [BPTco_Document_Processing_Intent.md](BPTco_Document_Processing_Intent.md) through **Upload intent**. The product treats the document as untrusted customer-provided data and infers the broad category for review.

**Duration:** 45–55 seconds.

---

## Scene 5 — Generate and review the decision pack

**Action:**
1. Keep **East US**.
2. Leave usage assumptions blank for the standard demo, so the UI clearly labels application-informed defaults.
3. Check the explicit Foundry consent box.
4. Select **Generate AI Feasibility Assessment**.
5. While it runs, keep the loading message visible.
6. On completion, pause on the executive decision and six dimension cards.
7. Scroll to the proposed Azure capability set and cost scenarios.
8. Pause on the **Not an Azure quote** label and PoC acceptance plan.

**Narration:**

> The customer has confirmed the processing boundary. The entered intent, expected outcome, a deterministic local draft, and minimized evidence labels may be sent to the configured Foundry model. Uploaded content is treated as data, not as instructions.
>
> The result is a versioned decision pack. It separates business fit, data readiness, integration readiness, security and governance, delivery and operations, and economics.
>
> For this scenario, the proposed capability set includes Azure AI Document Intelligence for extraction and classification, Azure AI Search for permission-aware retrieval, a Microsoft Foundry model for grounded enrichment and summarization, workflow orchestration, approved storage, and monitoring.
>
> The estimate is shown as low, base, and high scenarios with explicit assumptions and a reserve. The output also identifies evidence gaps and defines the smallest bounded PoC and the tests required before any production decision.

**Presenter cue:** If the disposition is `PoC candidate`, say: “PoC candidate means justified experimentation—not production-ready.”

**Duration:** 65–75 seconds.

---

## Scene 6 — Replace the base diagram with the AI-ready architecture

**Action:**
1. Select **View AI-ready architecture**.
2. Confirm the browser navigates to **Plan → Landing Zone** and the checkbox is on.
3. Show the `AI capability extension · Document Processing and Enrichment` section.
4. Point out the purple proposed-flow connectors and the linked assessment revision in the metadata.
5. Briefly show base cost versus incremental AI planning budget.

**Narration:**

> From the assessment we move directly into the AI-ready architecture.
>
> The original application design is preserved, but the diagram is replaced with a reviewed AI-ready variant for this application. The new capability extension shows where document intelligence, search, model access, orchestration, approved storage, and observability fit alongside the assessed application and data services.
>
> Every AI node is visibly marked as proposed. The diagram links back to the exact assessment revision, and base application cost remains separate from the incremental AI planning budget.
>
> If the checkbox is turned off, the architecture returns to the original migration design. AI is an explicit, assessed extension—not a silent default.

**Duration:** 45–55 seconds.

**Transition:** Return to PowerPoint slide 8.

---

## Slide 8 — What the demo demonstrates

**Narration:**

> This demonstration connects four things that are usually separated.
>
> It reuses existing application intelligence. It captures the customer's business intent and outcome. It produces an explainable, evidence-backed decision pack. And it carries the approved scenario into an AI-ready architecture without losing the base application design.
>
> The result is a qualified modernization conversation and a practical handoff—not a generic AI brainstorm.

---

## Slide 9 — The larger vision

**Narration:**

> The larger vision is simple.
>
> Azure Migrate has traditionally helped answer: how do I move this application to Azure?
>
> In the AI era, it can also help answer: how can I transform this application with AI, and what would it take to get there?
>
> Migration remains the foundation. AI Feasibility adds the next modernization decision at exactly the point where the customer already understands the application and is choosing its future.

---

## Slide 10 — Scale through the ecosystem

**Narration:**

> Azure Migrate already works through a broad ecosystem—including CMF, SA Desk, cloud solution architects, systems integrators, and other delivery partners.
>
> AI Feasibility can extend those relationships with a better-qualified application opportunity and a versioned handoff. It can also create new collaboration paths with Microsoft Foundry, Azure Frontier, AI field engineers, and Forward Deployed Engineers.
>
> Azure Migrate owns the application-to-opportunity decision experience. Platform and delivery teams validate and build the solution. The customer retains ownership of business value, data authorization, and production acceptance.
>
> The next step is a bounded design-partner validation: human-reviewed recommendations, clear evidence gates, and measurable movement from qualified opportunity to customer-owned PoC.

**Closing line:**

> Azure Migrate helps us understand the application. AI Feasibility helps the customer decide how that application can create new value in the AI era.

---

# Recording preparation checklist

## PowerPoint

- Open [Azure_Migrate_AI_Feasibility_Product_Demo.pptx](Azure_Migrate_AI_Feasibility_Product_Demo.pptx).
- Use Presenter View only if the recording captures the slide-show window, not speaker notes.
- Set slide show to 16:9 and advance manually.
- Record slides 1–7 as the opening segment and slides 8–10 as the closing segment.
- Use short crossfades in the editor rather than PowerPoint animations.

## Browser

- Resolution: 1920×1080.
- Browser zoom: 100%.
- Hide bookmarks bar, downloads shelf, and unrelated tabs.
- Confirm the connection overlay is hidden and `BPTco` is visible.
- Check for saved AI assessment revisions before the take. Either use the approved existing BPTco revision or explicitly delete only a known demo record; never remove a user-owned assessment automatically. Generating again creates the next revision.
- Keep AI-ready architecture **off** at the beginning.
- Use `PaaS Preferred` and `East US` for both base and AI-ready architecture.
- Keep the pointer slow and intentional. Pause after every navigation and before each click.
- Do not show environment files, terminal output, subscriptions, tokens, or credentials.

## Audio

- Delivery: calm, confident, conversational; 135–145 words per minute.
- Record in short sections: slides 1–7, each live-demo scene, then slides 8–10.
- Leave one second of room tone before and after each section.
- Pronunciation: say `B-P-T-co`; say `C-T-D` if the acronym is used; say `P-O-C` or “proof of concept” consistently.

## Editing

- Use 1080p, 30 fps.
- Add subtle cursor emphasis; avoid large click ripples.
- Add captions from the narration script and correct product/service capitalization.
- Keep music optional and very low under narration; remove it during detailed product interaction if it competes with speech.
- Add a persistent lower-corner label during live product footage: `Simulator prototype · Proposed Azure Migrate experience`.
- End on slide 10 for three seconds after the closing line.

# Accuracy guardrails for the recording

- Say **proposed concept**, **simulator prototype**, or **could** when describing future Azure Migrate product behavior.
- Say **indicative planning estimate**, not price quote.
- Say **PoC candidate**, not production ready.
- Do not claim that discovery proves business purpose, document contents, data quality, access rights, or API safety.
- Do not imply Microsoft field, Azure Frontier, FDE, or partner capacity is committed; describe these as proposed collaboration paths.
- Distinguish observed application facts, customer-provided intent, inferred assumptions, and missing evidence.
