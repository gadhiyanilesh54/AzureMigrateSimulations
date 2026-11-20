"""Tests for application-scoped AI Feasibility Assessment."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import pytest

from azure_migrate_simulations.ai_feasibility import (
    AIFeasibilityStore,
    extract_intent_document,
    generate_ai_feasibility_assessment,
    get_solution_categories,
    infer_solution_category,
)
from azure_migrate_simulations.application_landing_zone import (
    generate_application_landing_zones,
)
from azure_migrate_simulations.migration_chat import MigrationChatEngine


def _application() -> dict[str, Any]:
    members = [
        {
            "id": "vm:orders-web-01",
            "type": "vm",
            "name": "orders-web-01",
            "source_vm": "orders-web-01",
            "target_service": "Azure Virtual Machine",
            "target_sku": "Standard_D4s_v5",
            "monthly_cost": 210,
        },
        {
            "id": "webapp:orders-web-01:orders",
            "type": "webapp",
            "name": "Contoso Orders",
            "source_vm": "orders-web-01",
            "source_engine": "dotnet_core",
            "target_service": "Azure App Service",
            "target_sku": "P1v3",
            "monthly_cost": 108,
        },
        {
            "id": "database:orders-db-01:orders",
            "type": "database",
            "name": "orders-db",
            "source_vm": "orders-db-01",
            "source_engine": "postgresql",
            "target_service": "Azure Database for PostgreSQL Flexible Server",
            "monthly_cost": 290,
        },
        {
            "id": "fileshare:return-forms",
            "type": "fileshare",
            "name": "return-forms",
            "target_service": "Azure Files",
            "monthly_cost": 90,
            "allocated_monthly_cost": 90,
        },
    ]
    return {
        "id": "app-001-orders",
        "name": "Contoso Orders",
        "application_type": "Custom",
        "environment": "Production",
        "criticality": "Tier-2",
        "complexity_score": 6,
        "member_count": len(members),
        "members": members,
        "component_summary": {
            "virtual_machines": 1,
            "web_apps": 1,
            "databases": 1,
            "containers": 0,
            "orchestrators": 0,
            "file_shares": 1,
        },
        "dependencies": [],
        "dependency_count": 0,
        "target_monthly_cost": 488,
    }


def _assessment(version: int = 1) -> dict[str, Any]:
    return generate_ai_feasibility_assessment(
        _application(),
        "document_processing_enrichment",
        (
            "Support employees manually read return forms, search approved policy files, "
            "and draft a response for an internal reviewer."
        ),
        "Reduce median handling time while maintaining quality and mandatory employee approval.",
        usage_assumptions={"document_pages": 8000, "monthly_interactions": 12000},
        region="eastus",
        version=version,
    )


def _docx_bytes(text: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return stream.getvalue()


def test_solution_catalog_exposes_all_requested_categories() -> None:
    categories = get_solution_categories()

    assert [item["id"] for item in categories] == [
        "audio_processing",
        "video_image_processing",
        "predictive_analysis",
        "mlops",
        "document_processing_enrichment",
        "workflow_automation",
        "chat_with_data",
    ]
    assert all(item["usage_fields"] for item in categories)
    assert all("keywords" not in item for item in categories)


def test_intent_inference_and_safe_document_extraction() -> None:
    markdown = b"# Returns automation\nExtract fields from scanned PDF forms using OCR and route them for review."
    extracted = extract_intent_document("intent.md", markdown)

    assert extracted["inference"]["category_id"] == "document_processing_enrichment"
    assert extracted["sha256"]
    assert "untrusted" in extracted["security_notice"]

    docx = extract_intent_document(
        "intent.docx",
        _docx_bytes("Build a knowledge assistant that can chat with approved policy data."),
    )
    assert "knowledge assistant" in docx["text"]
    assert docx["inference"]["category_id"] == "chat_with_data"

    with pytest.raises(ValueError, match="Markdown"):
        extract_intent_document("intent.pdf", b"not allowed")


def test_assessment_separates_evidence_cost_and_production_readiness() -> None:
    assessment = _assessment()

    assert assessment["executive_decision"]["disposition"] == "poc_candidate"
    assert assessment["executive_decision"]["production_ready"] is False
    assert assessment["status"] == "reviewable"
    assert {item["provenance"] for item in assessment["evidence"]} >= {
        "observed",
        "customer-provided",
    }
    assert {item["id"] for item in assessment["dimension_findings"]} == {
        "business_fit",
        "data_readiness",
        "integration_readiness",
        "security_governance",
        "delivery_operations",
        "economics",
    }
    assert assessment["cost_estimate"]["pricing_status"] == "illustrative_unquoted"
    assert assessment["cost_estimate"]["scenarios"]["low"]["budget_with_reserve_usd"] < assessment["cost_estimate"]["scenarios"]["base"]["budget_with_reserve_usd"]
    assert assessment["cost_estimate"]["scenarios"]["base"]["budget_with_reserve_usd"] < assessment["cost_estimate"]["scenarios"]["high"]["budget_with_reserve_usd"]
    assert "Azure AI Document Intelligence" in assessment["service_summary"]
    assert assessment["architecture_extension"]["integration_point"]["name"] == "Contoso Orders"
    assert "feasibility_score" not in assessment


def test_store_persists_versions_and_deletes(tmp_path: Path) -> None:
    store = AIFeasibilityStore(tmp_path / "assessments.json")
    first = _assessment(1)
    second = _assessment(2)
    store.save(first)
    store.save(second)

    assert store.next_version(_application()["id"]) == 3
    assert store.get(first["id"])["application"]["name"] == "Contoso Orders"
    assert store.latest_by_application()[_application()["id"]]["id"] == second["id"]
    assert store.delete(first["id"]) is True
    assert store.get(first["id"]) is None


def test_ai_assessment_replaces_only_matching_landing_zone_variant() -> None:
    application = _application()
    other = dict(application)
    other["id"] = "app-002-other"
    other["name"] = "Other App"

    result = generate_application_landing_zones(
        [application, other],
        ai_assessments=[_assessment()],
    )
    ai_ready = next(item for item in result["applications"] if item["id"] == application["id"])
    base = next(item for item in result["applications"] if item["id"] == other["id"])

    assert ai_ready["ai_ready"] is True
    assert ai_ready["architecture_entry_id"].endswith("+ai-ready")
    assert ai_ready["monthly_cost"] == pytest.approx(
        ai_ready["base_monthly_cost"] + ai_ready["ai_monthly_cost"]
    )
    assert any(slot["origin"] == "proposed-ai" for slot in ai_ready["slots"])
    assert any(subnet["name"] == "snet-ai" for subnet in ai_ready["landing_zone"]["vnet"]["subnets"])
    assert "ai_ready" not in base
    assert result["summary"]["ai_ready_application_count"] == 1


def test_chat_guides_application_category_and_intent_selection() -> None:
    engine = MigrationChatEngine()
    discovery = {"vms": [{"name": "orders-web-01"}]}
    categories = get_solution_categories()

    choose_app = engine.answer(
        "Start an AI feasibility assessment",
        discovery,
        ai_feasibility_context={"applications": [_application()], "categories": categories},
    )
    assert choose_app["ai_feasibility_stage"] == "select_application"
    assert choose_app["actions"][0]["type"] == "chat_prompt"

    choose_category = engine.answer(
        "Assess AI feasibility for application Contoso Orders",
        discovery,
        ai_feasibility_context={"applications": [_application()], "categories": categories},
    )
    assert choose_category["ai_feasibility_stage"] == "select_category"
    assert len(choose_category["actions"]) == 7

    describe = engine.answer(
        "Use Document Processing and Enrichment for application Contoso Orders",
        discovery,
        ai_feasibility_context={
            "applications": [_application()],
            "categories": categories,
            "stage": "select_category",
            "selected_application_id": _application()["id"],
        },
    )
    assert describe["ai_feasibility_stage"] == "describe_intent"

    captured = engine.answer(
        "Support employees manually read scanned forms and want faster reviewed responses.",
        discovery,
        ai_feasibility_context={
            "applications": [_application()],
            "categories": categories,
            "stage": "describe_intent",
            "selected_application_id": _application()["id"],
            "selected_category_id": "document_processing_enrichment",
        },
    )
    assert captured["ai_feasibility_stage"] == "intent_captured"
    assert captured["actions"][0]["type"] == "ai_feasibility_start"
    assert captured["actions"][0]["intent"].startswith("Support employees")


def test_ai_feasibility_rest_lifecycle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from azure_migrate_simulations.web import app as web_app

    discovery = {
        "vms": [
            {
                "name": "orders-web-01",
                "folder": "Production/Orders",
                "guest_os_family": "linux",
                "guest_os": "Ubuntu 24.04",
                "disks": [{"datastore_name": "return-forms"}],
            }
        ],
        "recommendations": [
            {
                "vm_name": "orders-web-01",
                "recommended_vm_sku": "Standard_D4s_v5",
                "estimated_monthly_cost_usd": 210,
                "migration_readiness": "Ready",
                "confidence_score": 85,
            }
        ],
        "datastores": [{"name": "return-forms", "capacity_gb": 500, "type": "VMFS"}],
    }
    workloads = {
        "recommendations": [
            {
                "vm_name": "orders-web-01",
                "workload_name": "Contoso Orders",
                "workload_type": "webapp",
                "source_engine": "dotnet_core",
                "recommended_azure_service": "Azure App Service",
                "estimated_monthly_cost_usd": 108,
                "confidence": 90,
            },
            {
                "vm_name": "dc-01",
                "workload_name": "File Share: return-forms",
                "workload_type": "fileshare",
                "recommended_azure_service": "Azure Files",
                "estimated_monthly_cost_usd": 90,
            },
        ],
        "result": {"dependencies": []},
    }
    monkeypatch.setattr(web_app, "_data", discovery)
    monkeypatch.setattr(web_app, "_workload_data", workloads)
    monkeypatch.setattr(
        web_app,
        "_ai_feasibility_store",
        AIFeasibilityStore(tmp_path / "assessments.json"),
    )
    monkeypatch.setattr(
        web_app._migration_chat_enhancer,
        "enhance",
        lambda question, response, history=None: response,
    )
    client = web_app.app.test_client()

    applications = client.get("/api/applications").get_json()["applications"]
    application_id = applications[0]["id"]
    payload = {
        "application_id": application_id,
        "category_id": "document_processing_enrichment",
        "intent": "Support employees manually review scanned return forms and search policies before drafting a response.",
        "business_outcome": "Reduce median handling time while keeping every response under employee review.",
        "region": "eastus",
        "usage_assumptions": {"document_pages": 8000},
        "consent_confirmed": True,
    }

    assert client.post("/api/ai-feasibility/assessments", json={**payload, "consent_confirmed": False}).status_code == 400
    created_response = client.post("/api/ai-feasibility/assessments", json=payload)
    assert created_response.status_code == 201
    created = created_response.get_json()
    assert created["generation"]["narrative_provider"] == "local-grounded"

    listed = client.get("/api/ai-feasibility/assessments").get_json()
    assert listed["assessment_count"] == 1
    assert client.get(f"/api/ai-feasibility/assessments/{created['id']}").status_code == 200

    landing = client.get(
        f"/api/landing-zones?include_ai=true&ai_assessment_id={created['id']}"
    ).get_json()
    assert landing["summary"]["ai_ready_application_count"] == 1
    assert landing["applications"][0]["ai_feasibility"]["assessment_id"] == created["id"]

    upload = client.post(
        "/api/ai-feasibility/intent-upload",
        data={"file": (io.BytesIO(b"Extract fields from scanned invoices and route for approval."), "intent.md")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    assert upload.get_json()["inference"]["category_id"] == "document_processing_enrichment"

    assert client.delete(f"/api/ai-feasibility/assessments/{created['id']}").status_code == 200
    assert client.get("/api/ai-feasibility/assessments").get_json()["assessment_count"] == 0


def test_chat_rest_preserves_ai_feasibility_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from azure_migrate_simulations.chat_store import ChatConversationStore
    from azure_migrate_simulations.web import app as web_app

    monkeypatch.setattr(
        web_app,
        "_data",
        {
            "vms": [{"name": "orders-web-01", "folder": "Production/Orders", "disks": []}],
            "recommendations": [{"vm_name": "orders-web-01", "migration_readiness": "Ready"}],
            "datastores": [],
        },
    )
    monkeypatch.setattr(web_app, "_workload_data", {"recommendations": [], "result": {"dependencies": []}})
    monkeypatch.setattr(web_app, "_chat_store", ChatConversationStore(tmp_path / "chat.db"))
    monkeypatch.setattr(
        web_app._migration_chat_enhancer,
        "enhance",
        lambda question, response, history=None: response,
    )
    client = web_app.app.test_client()

    first = client.post("/api/chat", json={"message": "Start an AI feasibility assessment"}).get_json()
    second = client.post(
        "/api/chat",
        json={
            "conversation_id": first["conversation_id"],
            "message": "Assess AI feasibility for application orders-web-01",
        },
    ).get_json()
    third = client.post(
        "/api/chat",
        json={
            "conversation_id": first["conversation_id"],
            "message": "Use Document Processing and Enrichment for application orders-web-01",
        },
    ).get_json()
    fourth = client.post(
        "/api/chat",
        json={
            "conversation_id": first["conversation_id"],
            "message": "Support employees read scanned forms and want faster reviewed responses.",
        },
    ).get_json()

    assert first["ai_feasibility_stage"] == "select_application"
    assert second["ai_feasibility_stage"] == "select_category"
    assert third["ai_feasibility_stage"] == "describe_intent"
    assert third["intent"] == "ai_feasibility"
    assert fourth["ai_feasibility_stage"] == "intent_captured"
    assert fourth["actions"][0]["type"] == "ai_feasibility_start"
