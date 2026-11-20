"""Generate neural narration and subtitle tracks for the product demo video."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "demo" / "video" / "audio"
MANIFEST_PATH = OUTPUT_DIR / "segments.json"
VOICE = "en-US-AvaMultilingualNeural"
RATE = "+3%"
PITCH = "+0Hz"

SEGMENTS: list[dict[str, str]] = [
    {
        "id": "slide_01",
        "kind": "slide",
        "visual": "1",
        "text": (
            "Azure Migrate helps customers understand and modernize their on-premises estate. "
            "In the AI era, we have an opportunity to extend that journey. Not only helping customers "
            "decide how to move an application to Azure, but also helping them identify where AI can "
            "create meaningful value, and what it would take to deliver that value responsibly."
        ),
    },
    {
        "id": "slide_02",
        "kind": "slide",
        "visual": "2",
        "text": (
            "Azure Migrate begins with discovery. It prepares an inventory of virtual machines, web "
            "applications, databases, file shares, containers, and supporting dependencies. Customers "
            "can then organize these components as a complete application, a unit that works and moves "
            "together. Assessment maps each component to an appropriate Azure target. A web application "
            "might map to Azure App Service. SQL Server might map to Azure SQL Managed Instance. A "
            "containerized workload might map to Azure Kubernetes Service. This gives us rich application "
            "intelligence: the application boundary, runtime, dependencies, assessed targets, readiness, "
            "and cost context."
        ),
    },
    {
        "id": "slide_03",
        "kind": "slide",
        "visual": "3",
        "text": (
            "That assessment is excellent at answering the cloud-era question: where and how should this "
            "application run in Azure? But customers increasingly ask a second question: how can I use AI "
            "in this existing application? And, if I already use AI on-premises, how should I modernize "
            "that capability in Azure? This leads to two strategic questions. How do we help customers find "
            "credible AI opportunities in the applications they already own? And what should the next "
            "generation of Azure Migrate look like in the AI era?"
        ),
    },
    {
        "id": "slide_04",
        "kind": "slide",
        "visual": "4",
        "text": (
            "The proposed idea is an AI Feasibility Assessment as a new step in the Azure Migrate journey. "
            "Discover. Assess. AI Feasibility Assessment. Design. Estimate. Modernize. It adds an AI "
            "modernization layer on top of existing application intelligence. The goal is not to turn "
            "every application into an AI project. The goal is to identify which application and workflow "
            "combinations justify a bounded experiment, which need remediation first, and which should not "
            "pursue AI."
        ),
    },
    {
        "id": "slide_05",
        "kind": "slide",
        "visual": "5",
        "text": (
            "For each selected application, the assessment should answer four practical questions. Where "
            "can AI create meaningful business or engineering value? Is the application and its data "
            "technically ready for that scenario? Which integrations, Azure services, and security or "
            "governance controls are required? And what is the pragmatic path from proof of concept, to "
            "pilot, to production? The output is a reviewable decision pack with explicit evidence gaps "
            "and production gates, not a generic list of AI ideas."
        ),
    },
    {
        "id": "slide_06",
        "kind": "slide",
        "visual": "6",
        "text": (
            "The experience combines two evidence streams. Azure Migrate contributes observed application "
            "facts: components, dependencies, runtime, assessed targets, and migration findings. The "
            "customer contributes the business meaning: the process to improve, users, desired outcome, "
            "data constraints, compliance needs, and expected usage. The assessment then produces a "
            "feasibility summary, data and integration readiness, governance considerations, recommended "
            "Azure AI services, indicative cost scenarios, an AI-ready architecture extension, and a proof "
            "of concept roadmap. The key design principle is explainability. Observed facts, customer-provided "
            "context, inferred assumptions, and missing evidence remain visibly separate. Rules and "
            "deterministic calculations control the decision pack. Generative AI can improve the narrative, "
            "but it does not silently invent readiness or cost."
        ),
    },
    {
        "id": "slide_07",
        "kind": "slide",
        "visual": "7",
        "text": (
            "Let’s see the proposed experience in the Azure Migrate simulator. Discovery and assessment "
            "are already complete. We will start with the B P T co application, inspect its current Azure "
            "architecture, capture a document-processing outcome, generate an AI Feasibility Assessment, "
            "and then see exactly where the proposed AI services fit in the application landing zone."
        ),
    },
    {
        "id": "live_02",
        "kind": "live",
        "visual": "application-groups",
        "text": (
            "Discovery and assessment are already complete, so we move directly to Plan. Under Plan, "
            "Application Groups brings related infrastructure and workloads together as one "
            "application. B P T co includes its virtual machines and the discovered web, database, container, "
            "orchestration, and file-share components that belong to the application boundary. This is the "
            "scope we carry forward. AI feasibility is not assessed against an isolated server. It is "
            "assessed against the complete application and a customer-confirmed workflow."
        ),
    },
    {
        "id": "live_03",
        "kind": "live",
        "visual": "base-architecture",
        "text": (
            "First, we look at the current proposed Azure architecture with AI turned off. This is the "
            "application landing-zone view produced from the migration assessment. It shows secure ingress, "
            "network boundaries, shared platform services, assessed application targets, and data or storage "
            "dependencies. At this point, the design answers where and how B P T co could run in Azure. It "
            "does not yet add an AI capability."
        ),
    },
    {
        "id": "live_04",
        "kind": "live",
        "visual": "start-assessment",
        "text": (
            "Now the customer wants to explore an AI opportunity for the same application. In Decide, the "
            "Assessment experience includes AI Feasibility Assessment. We select B P T co, then choose the "
            "broad solution idea: Document Processing and Enrichment. These categories guide the assessment; "
            "they do not predetermine a service purchase or claim that the scenario is feasible."
        ),
    },
    {
        "id": "live_05",
        "kind": "live",
        "visual": "intent-and-outcome",
        "text": (
            "The customer now supplies the context discovery cannot infer. Here the process is document "
            "intake and enrichment across invoices, contracts, and attachments. The intended capability is "
            "classification, field extraction, metadata enrichment, summarization, business-rule validation, "
            "and human review for exceptions. The business outcome is explicit: reduce manual data entry by "
            "sixty percent, reduce processing time by fifty percent, and target ninety-five percent accuracy "
            "for critical fields, while keeping controlled access, approval, and auditability."
        ),
    },
    {
        "id": "live_06",
        "kind": "live",
        "visual": "decision-pack",
        "text": (
            "The customer has confirmed the processing boundary. The entered intent, expected "
            "outcome, a deterministic local draft, and minimized evidence labels may be sent to the configured "
            "Foundry model. Uploaded content is treated as data, not as instructions. The result is a versioned "
            "decision pack. It separates business fit, data readiness, integration readiness, security and "
            "governance, delivery and operations, and economics. For this scenario, the proposed capability "
            "set includes Azure AI Document Intelligence for extraction and classification, Azure AI Search "
            "for permission-aware retrieval, a Microsoft Foundry model for grounded enrichment and summarization, "
            "workflow orchestration, approved storage, and monitoring. The estimate is shown as low, base, and "
            "high scenarios with explicit assumptions and a reserve. The output also identifies evidence gaps "
            "and defines the smallest bounded proof of concept "
            "and the tests required before any production decision. A proof of concept candidate means justified "
            "experimentation, not production readiness."
        ),
    },
    {
        "id": "live_07",
        "kind": "live",
        "visual": "ai-ready-architecture",
        "text": (
            "From the assessment we move directly into the AI-ready architecture. The original application "
            "design is preserved, but the diagram is replaced with a reviewed AI-ready variant for this "
            "application. The new capability extension shows where document intelligence, search, model access, "
            "orchestration, approved storage, and observability fit alongside the assessed application and data "
            "services. Every AI node is visibly marked as proposed. The diagram links back to the exact "
            "assessment revision, and base application cost remains separate from the incremental AI planning "
            "budget. If the checkbox is turned off, the architecture returns to the original migration design. "
            "AI is an explicit, assessed extension, not a silent default."
        ),
    },
    {
        "id": "slide_08",
        "kind": "slide",
        "visual": "8",
        "text": (
            "This demonstration connects four things that are usually separated. It reuses existing application "
            "intelligence. It captures the customer’s business intent and outcome. It produces an explainable, "
            "evidence-backed decision pack. And it carries the approved scenario into an AI-ready architecture "
            "without losing the base application design. The result is a qualified modernization conversation "
            "and a practical handoff, not a generic AI brainstorm."
        ),
    },
    {
        "id": "slide_09",
        "kind": "slide",
        "visual": "9",
        "text": (
            "The larger vision is simple. Azure Migrate has traditionally helped answer: how do I move this "
            "application to Azure? In the AI era, it can also help answer: how can I transform this application "
            "with AI, and what would it take to get there? Migration remains the foundation. AI Feasibility adds "
            "the next modernization decision at exactly the point where the customer already understands the "
            "application and is choosing its future."
        ),
    },
    {
        "id": "slide_10",
        "kind": "slide",
        "visual": "10",
        "text": (
            "Azure Migrate already works through a broad ecosystem, including C M F, S A Desk, cloud solution "
            "architects, systems integrators, and other delivery partners. AI Feasibility can extend those "
            "relationships with a better-qualified application opportunity and a versioned handoff. It can also "
            "create new collaboration paths with Microsoft Foundry, Azure Frontier, AI field engineers, and "
            "Forward Deployed Engineers. Azure Migrate owns the application-to-opportunity decision experience. "
            "Platform and delivery teams validate and build the solution. The customer retains ownership of "
            "business value, data authorization, and production acceptance. The next step is a bounded "
            "design-partner validation: human-reviewed recommendations, clear evidence gates, and measurable "
            "movement from qualified opportunity to customer-owned proof of concept. Azure Migrate helps us "
            "understand the application. AI Feasibility helps the customer decide how that application can create "
            "new value in the AI era."
        ),
    },
]


def spoken_text(text: str) -> str:
    """Make the initialism AI unambiguously letter-by-letter for neural TTS."""
    return re.sub(r"\bAI\b", "A I", text)


async def generate_segment(segment: dict[str, str]) -> dict[str, object]:
    segment_id = segment["id"]
    media_path = OUTPUT_DIR / f"{segment_id}.mp3"
    subtitle_path = OUTPUT_DIR / f"{segment_id}.vtt"
    communicate = edge_tts.Communicate(
        spoken_text(segment["text"]),
        VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(str(media_path), str(subtitle_path))
    duration = float(MP3(media_path).info.length)
    return {
        **segment,
        "media": media_path.name,
        "subtitles": subtitle_path.name,
        "duration_seconds": round(duration, 3),
    }


async def main_async() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for index, segment in enumerate(SEGMENTS, 1):
        print(f"[{index:02d}/{len(SEGMENTS):02d}] {segment['id']}")
        generated.append(await generate_segment(segment))
    total_duration = sum(float(item["duration_seconds"]) for item in generated)
    manifest = {
        "voice": VOICE,
        "rate": RATE,
        "pitch": PITCH,
        "total_duration_seconds": round(total_duration, 3),
        "segments": generated,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Narration duration: {total_duration / 60:.2f} minutes")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
