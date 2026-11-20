"""Evidence-backed AI opportunity assessment for discovered applications.

The assessment is intentionally rules-first. Discovered application metadata is
used only to establish technical context; customer intent supplies business
meaning. Costs are deterministic planning estimates with explicit assumptions,
not Azure price quotes. A configured language model can improve the narrative,
but it does not select services, calculate costs, or override evidence gates.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import threading
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

AI_FEASIBILITY_SCHEMA_VERSION = "1.0"
AI_PATTERN_CATALOG_VERSION = "2026-10-02"
MAX_INTENT_CHARS = 12_000
MAX_INTENT_UPLOAD_BYTES = 1_000_000
MAX_DOCX_XML_BYTES = 5_000_000

_REGION_MULTIPLIERS = {
    "eastus": 1.0,
    "eastus2": 1.0,
    "centralus": 1.01,
    "westus2": 1.02,
    "westus3": 1.01,
    "canadacentral": 1.05,
    "northeurope": 1.12,
    "westeurope": 1.15,
    "uksouth": 1.14,
    "centralindia": 0.88,
    "southeastasia": 1.10,
    "australiaeast": 1.20,
    "japaneast": 1.18,
}

_COMMON_GAPS = [
    "Name the accountable business, application, data, and security owners.",
    "Validate data-use rights, retention, residency, identity, and permission boundaries.",
    "Measure representative quality, latency, adoption, and cost in a bounded proof of concept.",
    "Confirm fallback, monitoring, incident response, and production support ownership.",
]


def _usage_field(
    field_id: str,
    label: str,
    unit: str,
    default: float,
    minimum: float = 0,
) -> dict[str, Any]:
    return {
        "id": field_id,
        "label": label,
        "unit": unit,
        "default": default,
        "minimum": minimum,
    }


SOLUTION_CATEGORIES: dict[str, dict[str, Any]] = {
    "audio_processing": {
        "id": "audio_processing",
        "label": "Audio Processing",
        "icon": "bi-soundwave",
        "description": "Transcribe, summarize, classify, translate, or assist with recorded and live audio.",
        "keywords": [
            "audio", "speech", "voice", "call", "transcript", "transcription",
            "meeting", "conversation", "recording", "speaker", "translate",
        ],
        "examples": ["Call summarization", "Voice-of-customer insights", "Speech transcription"],
        "signal_types": ["webapp", "fileshare", "container"],
        "usage_fields": [
            _usage_field("audio_hours", "Audio processed monthly", "hours", 500),
            _usage_field("monthly_interactions", "Summaries or insights monthly", "requests", 10_000),
            _usage_field("storage_gb", "Retained approved audio", "GB", 100),
        ],
        "services": [
            ("speech", "Azure AI Speech", "Speech recognition, translation, and diarization", "ai-generic"),
            ("content-understanding", "Azure AI Content Understanding", "Structured audio insights when the scenario requires them", "ai-generic"),
            ("foundry", "Microsoft Foundry model", "Evidence-constrained summarization and reasoning", "ai-generic"),
            ("orchestration", "Azure Functions", "Event-driven ingestion and workflow orchestration", "function-apps.svg"),
            ("storage", "Azure Blob Storage", "Approved audio staging and lifecycle controls", "azure-fileshares.svg"),
            ("monitoring", "Application Insights", "Latency, failures, quality, and cost telemetry", "application-insights.svg"),
        ],
        "effort_weeks": [4, 7],
    },
    "video_image_processing": {
        "id": "video_image_processing",
        "label": "Video and Image Processing",
        "icon": "bi-camera-video",
        "description": "Classify, describe, moderate, search, or extract information from images and video.",
        "keywords": [
            "video", "image", "photo", "camera", "vision", "frame", "visual",
            "inspection", "object detection", "moderation", "multimodal",
        ],
        "examples": ["Visual inspection", "Media enrichment", "Image classification"],
        "signal_types": ["fileshare", "webapp", "container"],
        "usage_fields": [
            _usage_field("media_items", "Images or video segments monthly", "items", 20_000),
            _usage_field("monthly_interactions", "Human review or insight requests", "requests", 10_000),
            _usage_field("storage_gb", "Retained approved media", "GB", 250),
        ],
        "services": [
            ("content-understanding", "Azure AI Content Understanding", "Multimodal extraction and structured analysis", "ai-generic"),
            ("vision", "Azure AI Vision", "Image analysis and optical character recognition", "ai-generic"),
            ("foundry", "Microsoft Foundry model", "Reasoning over permitted visual findings", "ai-generic"),
            ("orchestration", "Azure Functions", "Asynchronous media-processing workflow", "function-apps.svg"),
            ("storage", "Azure Blob Storage", "Approved source and derived media", "azure-fileshares.svg"),
            ("monitoring", "Application Insights", "Quality, throughput, latency, and failure monitoring", "application-insights.svg"),
        ],
        "effort_weeks": [5, 9],
    },
    "predictive_analysis": {
        "id": "predictive_analysis",
        "label": "Predictive Analysis",
        "icon": "bi-graph-up-arrow",
        "description": "Forecast outcomes, detect anomalies, prioritize cases, or provide decision support.",
        "keywords": [
            "predict", "forecast", "anomaly", "risk", "propensity", "churn",
            "demand", "trend", "classification", "recommendation", "score",
        ],
        "examples": ["Demand forecasting", "Risk scoring", "Anomaly detection"],
        "signal_types": ["database", "fileshare"],
        "usage_fields": [
            _usage_field("training_hours", "Model training compute monthly", "hours", 80),
            _usage_field("endpoint_hours", "Managed endpoint runtime monthly", "hours", 730),
            _usage_field("monthly_predictions", "Predictions monthly", "predictions", 100_000),
        ],
        "services": [
            ("machine-learning", "Azure Machine Learning", "Data preparation, training, evaluation, and registry", "ai-generic"),
            ("managed-endpoint", "Managed online endpoint", "Controlled real-time or batch inference", "ai-generic"),
            ("data-pipeline", "Azure Data Factory", "Governed feature and training-data movement", "function-apps.svg"),
            ("storage", "Azure Data Lake Storage", "Versioned approved training and evaluation data", "azure-fileshares.svg"),
            ("monitoring", "Azure Monitor", "Drift, quality, latency, and cost monitoring", "application-insights.svg"),
        ],
        "effort_weeks": [6, 12],
    },
    "mlops": {
        "id": "mlops",
        "label": "MLOps",
        "icon": "bi-infinity",
        "description": "Create a governed lifecycle for training, evaluating, registering, deploying, and monitoring models.",
        "keywords": [
            "mlops", "machine learning operations", "model lifecycle", "retrain",
            "model registry", "pipeline", "feature store", "drift", "experiment",
        ],
        "examples": ["Model lifecycle automation", "Continuous evaluation", "Controlled deployment"],
        "signal_types": ["container", "orchestrator", "database"],
        "usage_fields": [
            _usage_field("training_hours", "Training and evaluation compute monthly", "hours", 100),
            _usage_field("endpoint_hours", "Managed endpoint runtime monthly", "hours", 730),
            _usage_field("pipeline_runs", "Pipeline runs monthly", "runs", 30),
        ],
        "services": [
            ("machine-learning", "Azure Machine Learning", "Experiments, pipelines, evaluation, and model registry", "ai-generic"),
            ("managed-endpoint", "Managed online endpoint", "Versioned model deployment", "ai-generic"),
            ("container-registry", "Azure Container Registry", "Controlled image and component storage", "container-apps-environments.svg"),
            ("key-vault", "Azure Key Vault", "Secrets, certificates, and managed-identity integration", "key-vault.svg"),
            ("monitoring", "Azure Monitor", "Model, data, endpoint, and pipeline monitoring", "application-insights.svg"),
        ],
        "effort_weeks": [6, 12],
    },
    "document_processing_enrichment": {
        "id": "document_processing_enrichment",
        "label": "Document Processing and Enrichment",
        "icon": "bi-file-earmark-text",
        "description": "Extract, classify, enrich, summarize, and route approved business documents.",
        "keywords": [
            "document", "pdf", "form", "invoice", "receipt", "contract", "ocr",
            "extract", "classification", "enrichment", "scan", "file", "email attachment",
        ],
        "examples": ["Invoice extraction", "Document classification", "Human-reviewed enrichment"],
        "signal_types": ["fileshare", "webapp", "database"],
        "usage_fields": [
            _usage_field("document_pages", "Document pages processed monthly", "pages", 6_000),
            _usage_field("monthly_interactions", "Review or enrichment requests", "requests", 20_000),
            _usage_field("search_units", "Dedicated search capacity", "search units", 1, 1),
        ],
        "services": [
            ("document-intelligence", "Azure AI Document Intelligence", "Optical character recognition, extraction, and classification", "ai-generic"),
            ("ai-search", "Azure AI Search", "Permission-aware retrieval and enrichment", "ai-generic"),
            ("foundry", "Microsoft Foundry model", "Summarization and grounded enrichment", "ai-generic"),
            ("orchestration", "Azure Functions or Logic Apps", "Ingestion, routing, and human-review workflow", "function-apps.svg"),
            ("storage", "Azure Blob Storage", "Approved source, staging, and lifecycle management", "azure-fileshares.svg"),
            ("monitoring", "Application Insights", "Extraction quality, latency, errors, and cost", "application-insights.svg"),
        ],
        "effort_weeks": [4, 8],
    },
    "workflow_automation": {
        "id": "workflow_automation",
        "label": "Workflow Automation",
        "icon": "bi-diagram-2",
        "description": "Assist or automate repetitive workflows with bounded actions and human approval.",
        "keywords": [
            "workflow", "automation", "automate", "agent", "approval", "routing",
            "triage", "task", "case", "process", "manual", "handoff",
        ],
        "examples": ["Case triage", "Draft-and-approve workflow", "Operational assistance"],
        "signal_types": ["webapp", "database", "container", "orchestrator"],
        "usage_fields": [
            _usage_field("workflow_executions", "Workflow executions monthly", "executions", 25_000),
            _usage_field("monthly_interactions", "AI-assisted steps monthly", "requests", 20_000),
            _usage_field("integration_count", "Business-system integrations", "integrations", 2, 1),
        ],
        "services": [
            ("workflow", "Azure Logic Apps", "Connector-based workflow and approval orchestration", "function-apps.svg"),
            ("functions", "Azure Functions", "Validated business rules and integration adapters", "function-apps.svg"),
            ("foundry", "Microsoft Foundry model", "Classification, drafting, and bounded reasoning", "ai-generic"),
            ("api-management", "Azure API Management", "Governed access to approved business APIs", "application-gateway.svg"),
            ("monitoring", "Application Insights", "Action, exception, approval, latency, and cost telemetry", "application-insights.svg"),
        ],
        "effort_weeks": [5, 10],
    },
    "chat_with_data": {
        "id": "chat_with_data",
        "label": "Chat with Data or Data Insights",
        "icon": "bi-chat-square-text",
        "description": "Answer questions and generate insights from authorized structured and unstructured data.",
        "keywords": [
            "chat with data", "data insights", "question answering", "knowledge",
            "search", "rag", "assistant", "copilot", "analytics", "query", "insight",
        ],
        "examples": ["Internal knowledge assistant", "Cited data insights", "Read-only operational assistant"],
        "signal_types": ["database", "fileshare", "webapp"],
        "usage_fields": [
            _usage_field("monthly_interactions", "Assisted interactions monthly", "requests", 40_000),
            _usage_field("search_units", "Dedicated search capacity", "search units", 2, 1),
            _usage_field("embedding_million_tokens", "Embedding volume monthly", "million tokens", 12),
        ],
        "services": [
            ("foundry", "Microsoft Foundry model", "Grounded answer generation and reasoning", "ai-generic"),
            ("ai-search", "Azure AI Search", "Permission-aware hybrid and vector retrieval", "ai-generic"),
            ("orchestration", "AI orchestration backend", "Authorization, retrieval, validation, and citations", "app-services.svg"),
            ("api-management", "Azure API Management", "Governed read-only access to approved APIs", "application-gateway.svg"),
            ("storage", "Azure Blob Storage", "Approved knowledge content and lifecycle metadata", "azure-fileshares.svg"),
            ("monitoring", "Application Insights", "Groundedness, quality, latency, failures, and cost", "application-insights.svg"),
        ],
        "effort_weeks": [4, 8],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalise_customer_text(value: str, *, limit: int = MAX_INTENT_CHARS) -> str:
    """Normalize customer-provided text while preserving readable paragraphs."""
    text = str(value or "").replace("\x00", " ")
    text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit]


def get_solution_categories() -> list[dict[str, Any]]:
    """Return the public, UI-safe solution-pattern catalog."""
    return [
        {
            key: deepcopy(value)
            for key, value in category.items()
            if key != "keywords"
        }
        for category in SOLUTION_CATEGORIES.values()
    ]


def infer_solution_category(text: str) -> dict[str, Any]:
    """Infer a broad solution category from untrusted customer text."""
    normalized = normalise_customer_text(text).casefold()
    scores: list[tuple[int, str, list[str]]] = []
    for category_id, category in SOLUTION_CATEGORIES.items():
        matched = sorted({
            keyword for keyword in category["keywords"] if keyword in normalized
        })
        scores.append((len(matched), category_id, matched))
    scores.sort(key=lambda item: (-item[0], item[1]))
    score, category_id, matched = scores[0]
    if score == 0:
        return {"category_id": "", "confidence": "low", "matched_terms": []}
    return {
        "category_id": category_id,
        "confidence": "high" if score >= 3 else "medium" if score >= 2 else "low",
        "matched_terms": matched,
    }


def _extract_docx_text(payload: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            try:
                document = archive.getinfo("word/document.xml")
            except KeyError as exc:
                raise ValueError("The DOCX file does not contain a Word document body.") from exc
            if document.file_size > MAX_DOCX_XML_BYTES:
                raise ValueError("The expanded DOCX document body is too large.")
            xml_bytes = archive.read(document)
    except zipfile.BadZipFile as exc:
        raise ValueError("The uploaded DOCX file is not a valid Office document.") from exc

    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        raise ValueError("The uploaded DOCX document XML is invalid.") from exc

    word_namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{word_namespace}p"):
        values = [node.text or "" for node in paragraph.iter(f"{word_namespace}t")]
        text = "".join(values).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_intent_document(filename: str, payload: bytes) -> dict[str, Any]:
    """Extract intent text from Markdown, plain text, or DOCX without execution."""
    safe_name = Path(filename or "").name
    suffix = Path(safe_name).suffix.casefold()
    if suffix not in {".md", ".markdown", ".txt", ".docx"}:
        raise ValueError("Upload a Markdown (.md), text (.txt), or Word (.docx) document.")
    if not payload:
        raise ValueError("The uploaded intent document is empty.")
    if len(payload) > MAX_INTENT_UPLOAD_BYTES:
        raise ValueError("Intent documents must be 1 MB or smaller.")

    if suffix == ".docx":
        extracted = _extract_docx_text(payload)
    else:
        try:
            extracted = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Markdown and text uploads must use UTF-8 encoding.") from exc

    normalized = normalise_customer_text(extracted)
    if not normalized:
        raise ValueError("No readable intent text was found in the uploaded document.")
    inference = infer_solution_category(normalized)
    return {
        "filename": safe_name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "text": normalized,
        "character_count": len(normalized),
        "truncated": len(extracted) > len(normalized),
        "inference": inference,
        "security_notice": (
            "Uploaded content is treated as untrusted customer-provided data, not as "
            "instructions or authorization. Review the extracted intent before assessment."
        ),
    }


def _safe_number(value: Any, default: float, minimum: float = 0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = float(default)
    return max(float(minimum), number)


def _application_signal_summary(application: dict[str, Any]) -> dict[str, Any]:
    members = application.get("members", [])
    counts: dict[str, int] = {}
    for member in members:
        member_type = str(member.get("type", "unknown"))
        counts[member_type] = counts.get(member_type, 0) + 1
    return {
        "member_count": len(members),
        "counts": counts,
        "member_types": sorted(counts),
        "candidate_data_sources": [
            {
                "name": member.get("name", "unknown"),
                "type": member.get("type", "unknown"),
                "observed_target": member.get("target_service", ""),
                "verification": "Access, contents, quality, and usage rights are not established by discovery.",
            }
            for member in members
            if member.get("type") in {"database", "fileshare"}
        ][:10],
    }


def _default_usage(
    application: dict[str, Any],
    category: dict[str, Any],
) -> dict[str, float]:
    member_count = max(int(application.get("member_count", 1) or 1), 1)
    defaults = {
        field["id"]: float(field["default"])
        for field in category["usage_fields"]
    }
    if "monthly_interactions" in defaults:
        defaults["monthly_interactions"] = max(defaults["monthly_interactions"], member_count * 1_000)
    if "document_pages" in defaults:
        fileshares = application.get("component_summary", {}).get("file_shares", 0) or 0
        defaults["document_pages"] = max(defaults["document_pages"], fileshares * 2_000)
    if "media_items" in defaults:
        fileshares = application.get("component_summary", {}).get("file_shares", 0) or 0
        defaults["media_items"] = max(defaults["media_items"], fileshares * 5_000)
    return defaults


def _normalise_usage(
    application: dict[str, Any],
    category: dict[str, Any],
    supplied: dict[str, Any] | None,
) -> tuple[dict[str, float], list[str]]:
    defaults = _default_usage(application, category)
    supplied = supplied or {}
    values: dict[str, float] = {}
    customer_provided: list[str] = []
    for field in category["usage_fields"]:
        field_id = field["id"]
        if field_id in supplied and supplied[field_id] not in (None, ""):
            values[field_id] = _safe_number(
                supplied[field_id],
                defaults[field_id],
                field.get("minimum", 0),
            )
            customer_provided.append(field_id)
        else:
            values[field_id] = defaults[field_id]
    return values, customer_provided


def _cost_line(
    service: str,
    description: str,
    quantity: float,
    unit: str,
    unit_rate: float,
    *,
    fixed: bool = False,
) -> dict[str, Any]:
    monthly_cost = quantity * unit_rate
    return {
        "service": service,
        "description": description,
        "quantity": round(quantity, 3),
        "unit": unit,
        "illustrative_unit_rate_usd": round(unit_rate, 6),
        "monthly_cost_usd": round(monthly_cost, 2),
        "cost_behavior": "fixed" if fixed else "usage",
        "rate_source": "Illustrative planning assumption — replace with current Azure pricing or agreement rates.",
    }


def _cost_lines(category_id: str, usage: dict[str, float]) -> list[dict[str, Any]]:
    interactions = usage.get("monthly_interactions", 0)
    if category_id == "audio_processing":
        return [
            _cost_line("Azure AI Speech", "Audio transcription/analysis", usage["audio_hours"], "audio hour", 1.25),
            _cost_line("Microsoft Foundry model", "Summarization and insight generation", interactions, "request", 0.004),
            _cost_line("Azure Functions", "Ingestion and orchestration allowance", 1, "monthly allowance", 80, fixed=True),
            _cost_line("Storage and monitoring", "Approved media lifecycle and telemetry allowance", 1, "monthly allowance", 45, fixed=True),
        ]
    if category_id == "video_image_processing":
        return [
            _cost_line("Azure AI visual services", "Image/video segment analysis", usage["media_items"], "media item", 0.003),
            _cost_line("Microsoft Foundry model", "Multimodal reasoning and enrichment", interactions, "request", 0.004),
            _cost_line("Processing compute", "Asynchronous orchestration allowance", 1, "monthly allowance", 100, fixed=True),
            _cost_line("Storage and monitoring", "Approved media lifecycle and telemetry allowance", 1, "monthly allowance", 60, fixed=True),
        ]
    if category_id == "predictive_analysis":
        return [
            _cost_line("Azure Machine Learning", "Training and evaluation compute", usage["training_hours"], "compute hour", 2.25),
            _cost_line("Managed online endpoint", "Inference endpoint runtime", usage["endpoint_hours"], "endpoint hour", 0.35),
            _cost_line("Data preparation", "Pipeline and governed data allowance", 1, "monthly allowance", 100, fixed=True),
            _cost_line("Monitoring", "Quality, drift, latency, and cost allowance", 1, "monthly allowance", 60, fixed=True),
        ]
    if category_id == "mlops":
        return [
            _cost_line("Azure Machine Learning", "Training and evaluation compute", usage["training_hours"], "compute hour", 2.25),
            _cost_line("Managed online endpoint", "Versioned endpoint runtime", usage["endpoint_hours"], "endpoint hour", 0.35),
            _cost_line("MLOps control plane", "Registry, pipelines, and artifact allowance", 1, "monthly allowance", 150, fixed=True),
            _cost_line("Security and monitoring", "Identity, secrets, quality, and drift allowance", 1, "monthly allowance", 80, fixed=True),
        ]
    if category_id == "document_processing_enrichment":
        return [
            _cost_line("Azure AI Document Intelligence", "Page extraction/classification", usage["document_pages"], "page", 0.012),
            _cost_line("Azure AI Search", "Dedicated retrieval capacity", usage["search_units"], "search unit-month", 220, fixed=True),
            _cost_line("Microsoft Foundry model", "Grounded enrichment and summarization", interactions, "request", 0.004),
            _cost_line("Backend and ingestion", "Orchestration and human-review integration allowance", 1, "monthly allowance", 120, fixed=True),
            _cost_line("Storage and monitoring", "Approved staging, lifecycle, and telemetry allowance", 1, "monthly allowance", 60, fixed=True),
        ]
    if category_id == "workflow_automation":
        return [
            _cost_line("Logic Apps and Functions", "Workflow executions", usage["workflow_executions"], "execution", 0.0002),
            _cost_line("Microsoft Foundry model", "AI-assisted workflow steps", interactions, "request", 0.004),
            _cost_line("Integration runtime", "Adapters and approval workflow allowance", 1, "monthly allowance", 100, fixed=True),
            _cost_line("API governance", "Approved API and messaging allowance", 1, "monthly allowance", 75, fixed=True),
            _cost_line("Monitoring", "Actions, exceptions, latency, and cost allowance", 1, "monthly allowance", 35, fixed=True),
        ]
    return [
        _cost_line("Azure AI Search", "Dedicated retrieval capacity", usage["search_units"], "search unit-month", 220, fixed=True),
        _cost_line("Microsoft Foundry model", "Grounded answer generation", interactions, "request", 0.004),
        _cost_line("Embeddings", "Knowledge indexing and query embeddings", usage["embedding_million_tokens"], "million tokens", 0.10),
        _cost_line("AI orchestration backend", "Authorization, retrieval, validation, and citations", 1, "monthly allowance", 120, fixed=True),
        _cost_line("Storage and monitoring", "Approved content lifecycle and telemetry allowance", 1, "monthly allowance", 60, fixed=True),
    ]


def _build_cost_estimate(
    category_id: str,
    usage: dict[str, float],
    region: str,
) -> dict[str, Any]:
    multiplier = _REGION_MULTIPLIERS.get(region, 1.0)
    lines = _cost_lines(category_id, usage)
    for line in lines:
        line["monthly_cost_usd"] = round(line["monthly_cost_usd"] * multiplier, 2)
    fixed = sum(line["monthly_cost_usd"] for line in lines if line["cost_behavior"] == "fixed")
    variable = sum(line["monthly_cost_usd"] for line in lines if line["cost_behavior"] == "usage")

    def scenario(name: str, variable_scale: float, fixed_scale: float) -> dict[str, Any]:
        subtotal = fixed * fixed_scale + variable * variable_scale
        reserve = subtotal * 0.20
        return {
            "name": name,
            "service_subtotal_usd": round(subtotal, 2),
            "planning_reserve_usd": round(reserve, 2),
            "budget_with_reserve_usd": round(subtotal + reserve, 2),
        }

    return {
        "currency": "USD",
        "region": region,
        "pricing_status": "illustrative_unquoted",
        "pricing_notice": (
            "Planning estimate only. Unit rates are explicit illustrative assumptions, not "
            "Azure price quotes. Resolve current meters, currency, region, and agreement rates before approval."
        ),
        "region_multiplier": multiplier,
        "line_items": lines,
        "scenarios": {
            "low": scenario("Low usage", 0.35, 1.0),
            "base": scenario("Base assumptions", 1.0, 1.0),
            "high": scenario("High demand", 3.0, 1.5),
        },
        "reserve_percent": 20,
    }


def _find_integration_point(application: dict[str, Any]) -> dict[str, Any]:
    members = application.get("members", [])
    for member_type in ("webapp", "container", "orchestrator", "vm"):
        member = next((item for item in members if item.get("type") == member_type), None)
        if member:
            return {
                "member_id": member.get("id", ""),
                "name": member.get("name", application.get("name", "Application")),
                "type": member_type,
                "assessed_target": member.get("target_service", ""),
                "provenance": "observed",
            }
    return {
        "member_id": "",
        "name": application.get("name", "Application"),
        "type": "application",
        "assessed_target": "",
        "provenance": "observed",
    }


def _architecture_extension(
    application: dict[str, Any],
    category: dict[str, Any],
    cost_estimate: dict[str, Any],
) -> dict[str, Any]:
    integration_point = _find_integration_point(application)
    costs = {
        line["service"]: line["monthly_cost_usd"]
        for line in cost_estimate["line_items"]
    }
    components = []
    for index, (component_id, service, role, icon) in enumerate(category["services"]):
        matched_cost = next(
            (value for key, value in costs.items() if key.casefold() in service.casefold() or service.casefold() in key.casefold()),
            0,
        )
        components.append({
            "id": component_id,
            "name": service,
            "role": role,
            "icon": icon,
            "provenance": "proposed",
            "order": index,
            "monthly_cost_usd": matched_cost,
        })

    data_sources = _application_signal_summary(application)["candidate_data_sources"]
    flows = [{
        "from": "existing-application",
        "to": components[0]["id"],
        "label": "Authorized request or event",
        "provenance": "proposed",
    }]
    for left, right in zip(components, components[1:]):
        flows.append({
            "from": left["id"],
            "to": right["id"],
            "label": "Controlled data or orchestration flow",
            "provenance": "proposed",
        })

    return {
        "title": f"{application.get('name')} AI-ready architecture",
        "pattern_id": category["id"],
        "pattern_label": category["label"],
        "integration_point": integration_point,
        "candidate_data_sources": data_sources,
        "components": components,
        "flows": flows,
        "trust_boundaries": [
            "Existing application authorization remains authoritative.",
            "AI services receive only the minimum permitted context.",
            "Customer data sources require owner approval and permission enforcement.",
            "Generated or extracted output is untrusted until validated; human approval remains required.",
        ],
        "fallback": "The existing application workflow remains available when the AI capability is unavailable or uncertain.",
    }


def _dimension_findings(
    application: dict[str, Any],
    category: dict[str, Any],
    intent: str,
    business_outcome: str,
    customer_usage_fields: list[str],
) -> list[dict[str, str]]:
    signals = _application_signal_summary(application)
    matching_types = sorted(set(signals["member_types"]) & set(category["signal_types"]))
    has_integration = any(
        member_type in signals["member_types"]
        for member_type in ("webapp", "container", "orchestrator", "vm")
    )
    return [
        {
            "id": "business_fit",
            "label": "Business fit",
            "status": "promising" if intent and business_outcome else "needs_evidence",
            "finding": (
                "A named intent and measurable business outcome were provided."
                if intent and business_outcome else
                "A workflow description and measurable business outcome are still required."
            ),
        },
        {
            "id": "data_readiness",
            "label": "Data readiness",
            "status": "conditional" if matching_types else "needs_evidence",
            "finding": (
                f"Discovery shows candidate {', '.join(matching_types)} components, but contents, quality, permissions, and suitability require validation."
                if matching_types else
                "Discovery does not establish a category-relevant data source; the data owner must identify and authorize one."
            ),
        },
        {
            "id": "integration_readiness",
            "label": "Integration readiness",
            "status": "conditional" if has_integration else "needs_evidence",
            "finding": (
                "An application integration boundary is visible, but API behavior, authentication, and change ownership are unverified."
                if has_integration else
                "No supported integration point has been validated for the proposed capability."
            ),
        },
        {
            "id": "security_governance",
            "label": "Security and governance",
            "status": "needs_evidence",
            "finding": "Identity, access, content safety, audit, retention, residency, and risk approvals require owner review.",
        },
        {
            "id": "delivery_operations",
            "label": "Delivery and operations",
            "status": "conditional" if has_integration else "needs_evidence",
            "finding": "A bounded PoC is technically plausible; delivery skills, monitoring, fallback, support, and adoption owners must be assigned.",
        },
        {
            "id": "economics",
            "label": "Economics",
            "status": "conditional" if customer_usage_fields else "needs_evidence",
            "finding": (
                "Customer-provided usage inputs improve the estimate, but current Azure rates and measured demand still require validation."
                if customer_usage_fields else
                "Costs use application-informed defaults; measured usage and current Azure rates are required before an investment decision."
            ),
        },
    ]


def generate_ai_feasibility_assessment(
    application: dict[str, Any],
    category_id: str,
    intent_text: str,
    business_outcome: str,
    *,
    usage_assumptions: dict[str, Any] | None = None,
    region: str = "eastus",
    consent_reference: str = "interactive-confirmation",
    input_source: dict[str, Any] | None = None,
    version: int = 1,
) -> dict[str, Any]:
    """Generate a structured, deterministic AI feasibility decision record."""
    if category_id not in SOLUTION_CATEGORIES:
        raise ValueError("Choose one of the supported AI solution categories.")
    intent = normalise_customer_text(intent_text)
    outcome = normalise_customer_text(business_outcome, limit=2_000)
    if len(intent) < 20:
        raise ValueError("Describe the business process or workload to improve in at least 20 characters.")
    if len(outcome) < 10:
        raise ValueError("Describe the expected business outcome in at least 10 characters.")

    category = SOLUTION_CATEGORIES[category_id]
    usage, customer_usage_fields = _normalise_usage(
        application,
        category,
        usage_assumptions,
    )
    costs = _build_cost_estimate(category_id, usage, region)
    signal_summary = _application_signal_summary(application)
    relevant_signals = sorted(set(signal_summary["member_types"]) & set(category["signal_types"]))
    dimensions = _dimension_findings(
        application,
        category,
        intent,
        outcome,
        customer_usage_fields,
    )
    disposition = "poc_candidate" if relevant_signals else "needs_evidence"
    disposition_label = "PoC candidate" if disposition == "poc_candidate" else "Needs evidence"

    gaps = list(_COMMON_GAPS)
    if not relevant_signals:
        gaps.insert(0, "Identify and validate a category-relevant data source or integration signal.")
    if not customer_usage_fields:
        gaps.insert(0, "Replace all application-informed usage defaults with measured or owner-approved volumes.")

    service_names = [service[1] for service in category["services"]]
    summary = (
        f"{application.get('name')} is a {disposition_label.lower()} for {category['label']}. "
        f"The proposed outcome is: {outcome}. Discovery supplies application context, not proof of "
        f"business-data suitability or production readiness. Start with a bounded, human-reviewed "
        f"PoC after the named evidence gaps are resolved. The base monthly planning range is "
        f"${costs['scenarios']['low']['budget_with_reserve_usd']:,.0f}–"
        f"${costs['scenarios']['high']['budget_with_reserve_usd']:,.0f}; this is not an Azure quote."
    )

    created_at = utc_now()
    assessment_id = f"aifa-{uuid4().hex}"
    return {
        "schema_version": AI_FEASIBILITY_SCHEMA_VERSION,
        "catalog_version": AI_PATTERN_CATALOG_VERSION,
        "id": assessment_id,
        "version": max(1, int(version)),
        "status": "reviewable" if disposition == "poc_candidate" else "needs_evidence",
        "created_at": created_at,
        "updated_at": created_at,
        "application": {
            "id": application.get("id", ""),
            "name": application.get("name", ""),
            "environment": application.get("environment", "Production"),
            "criticality": application.get("criticality", "Tier-2"),
            "component_summary": deepcopy(application.get("component_summary", {})),
            "member_count": application.get("member_count", 0),
            "target_monthly_cost_usd": application.get("target_monthly_cost", 0),
        },
        "solution_category": {
            "id": category_id,
            "label": category["label"],
            "description": category["description"],
        },
        "customer_intent": {
            "workflow": intent,
            "business_outcome": outcome,
            "input_source": deepcopy(input_source or {"type": "guided", "name": "Interactive assessment"}),
            "consent_reference": consent_reference,
        },
        "executive_decision": {
            "disposition": disposition,
            "disposition_label": disposition_label,
            "summary": summary,
            "decision_conditions": gaps[:5],
            "production_ready": False,
        },
        "evidence": [
            {
                "id": "application-boundary",
                "provenance": "observed",
                "source": "Application grouping and workload assessments",
                "detail": f"{signal_summary['member_count']} scoped members across {', '.join(signal_summary['member_types']) or 'unknown types'}.",
                "observed_at": created_at,
            },
            {
                "id": "customer-intent",
                "provenance": "customer-provided",
                "source": (input_source or {}).get("name", "Interactive assessment"),
                "detail": "Workflow intent and business outcome were supplied for this assessment.",
                "observed_at": created_at,
            },
            {
                "id": "usage-assumptions",
                "provenance": "customer-provided" if customer_usage_fields else "inferred",
                "source": "Assessment form" if customer_usage_fields else "AI pattern defaults and application size",
                "detail": f"Customer-provided fields: {', '.join(customer_usage_fields) if customer_usage_fields else 'none'}.",
                "observed_at": created_at,
            },
        ],
        "dimension_findings": dimensions,
        "recommended_services": [
            {
                "name": service,
                "role": role,
                "provenance": "proposed",
                "requires_validation": True,
            }
            for _, service, role, _ in category["services"]
        ],
        "service_summary": service_names,
        "usage_assumptions": {
            "values": usage,
            "customer_provided_fields": customer_usage_fields,
            "notice": "Unlisted fields use application-informed planning defaults and must be validated.",
        },
        "cost_estimate": costs,
        "architecture_extension": _architecture_extension(application, category, costs),
        "gaps": gaps,
        "poc_plan": {
            "recommended_duration_weeks": [4, 6],
            "estimated_effort_person_weeks": category["effort_weeks"],
            "scope": (
                "Use approved representative data, read-only integrations, a small user cohort, "
                "human review, and the existing workflow as fallback."
            ),
            "acceptance_tests": [
                "Agree a task-specific quality rubric and held-out evaluation set.",
                "Validate authorization, cross-user isolation, prompt-injection handling, and prohibited actions.",
                "Measure end-to-end task time, review effort, latency, failures, adoption, and actual cost.",
                "Demonstrate disablement and fallback without interrupting the existing application.",
            ],
            "production_gates": [
                "Application, data, security, and operations owners accept the measured results.",
                "Current service availability, quota, pricing, residency, and retention are validated.",
                "Monitoring, incident response, rollback, support, and user training are funded and owned.",
            ],
        },
        "generation": {
            "method": "deterministic-pattern-catalog",
            "narrative_provider": "local-grounded",
            "model_deployment": "",
        },
    }


class AIFeasibilityStore:
    """Thread-safe JSON persistence for versioned assessment records."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": AI_FEASIBILITY_SCHEMA_VERSION, "assessments": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": AI_FEASIBILITY_SCHEMA_VERSION, "assessments": []}
        if not isinstance(data, dict) or not isinstance(data.get("assessments"), list):
            return {"schema_version": AI_FEASIBILITY_SCHEMA_VERSION, "assessments": []}
        return data

    def _write(self, data: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def next_version(self, application_id: str) -> int:
        assessments = self.list_assessments(application_id=application_id)
        return max((int(item.get("version", 0)) for item in assessments), default=0) + 1

    def save(self, assessment: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            records = [
                item for item in data["assessments"]
                if item.get("id") != assessment.get("id")
            ]
            records.append(deepcopy(assessment))
            records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
            data["assessments"] = records
            data["updated_at"] = utc_now()
            self._write(data)
        return deepcopy(assessment)

    def get(self, assessment_id: str) -> dict[str, Any] | None:
        with self._lock:
            for assessment in self._read()["assessments"]:
                if assessment.get("id") == assessment_id:
                    return deepcopy(assessment)
        return None

    def list_assessments(self, application_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            records = deepcopy(self._read()["assessments"])
        if application_id:
            records = [
                item for item in records
                if item.get("application", {}).get("id") == application_id
            ]
        records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return records

    def latest_by_application(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for assessment in self.list_assessments():
            application_id = assessment.get("application", {}).get("id", "")
            current = latest.get(application_id)
            if application_id and (
                current is None
                or int(assessment.get("version", 0)) > int(current.get("version", 0))
                or (
                    int(assessment.get("version", 0)) == int(current.get("version", 0))
                    and assessment.get("created_at", "") > current.get("created_at", "")
                )
            ):
                latest[application_id] = assessment
        return latest

    def delete(self, assessment_id: str) -> bool:
        with self._lock:
            data = self._read()
            original_count = len(data["assessments"])
            data["assessments"] = [
                item for item in data["assessments"]
                if item.get("id") != assessment_id
            ]
            if len(data["assessments"]) == original_count:
                return False
            data["updated_at"] = utc_now()
            self._write(data)
        return True
