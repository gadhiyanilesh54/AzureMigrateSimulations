"""Tests for the evidence-grounded migration chat engine and REST API."""

from __future__ import annotations

from typing import Any

import pytest

from azure_migrate_simulations.chat_store import ChatConversationStore
from azure_migrate_simulations.migration_chat import (
    FoundryGenerativeProvider,
    MAX_CHAT_MESSAGE_LENGTH,
    MigrationChatEngine,
)


def _sample_discovery() -> dict[str, Any]:
    return {
        "vcenter_host": "vc.example.test",
        "vms": [
            {
                "name": "shop-web-01",
                "num_cpus": 4,
                "memory_mb": 8192,
                "total_disk_gb": 128,
                "power_state": "poweredOn",
                "guest_os": "Ubuntu 22.04",
                "guest_os_family": "linux",
                "folder": "Production/Shop",
                "host": "esx-01",
                "disks": [{"datastore_name": "shared-data"}],
            },
            {
                "name": "shop-db-01",
                "num_cpus": 8,
                "memory_mb": 32768,
                "total_disk_gb": 512,
                "power_state": "poweredOn",
                "guest_os": "Windows Server 2012 R2",
                "guest_os_family": "windows",
                "folder": "Production/Shop",
                "host": "esx-01",
                "disks": [{"datastore_name": "shared-data"}],
            },
        ],
        "hosts": [{"name": "esx-01"}],
        "networks": [{"name": "VM Network", "network_type": "standard"}],
        "datastores": [
            {
                "name": "shared-data",
                "type": "VMFS",
                "capacity_gb": 1024,
                "free_space_gb": 512,
                "datacenter": "dc-01",
            }
        ],
        "recommendations": [
            {
                "vm_name": "shop-web-01",
                "recommended_vm_sku": "Standard_D4s_v5",
                "recommended_vm_family": "D",
                "estimated_monthly_cost_usd": 210,
                "migration_readiness": "Ready",
                "migration_issues": [],
                "confidence_score": 85,
                "target_region": "eastus",
                "pricing": {
                    "vm_payg_monthly": 150,
                    "disk_total_monthly": 25,
                    "os_license_monthly": 0,
                    "backup_monthly": 10,
                    "monitoring_monthly": 10,
                    "networking_monthly": 15,
                    "total_payg_monthly": 210,
                    "total_optimized_monthly": 145,
                },
            },
            {
                "vm_name": "shop-db-01",
                "recommended_vm_sku": "Standard_E8s_v6",
                "recommended_vm_family": "Esv6",
                "estimated_monthly_cost_usd": 500,
                "migration_readiness": "Ready with conditions",
                "migration_issues": ["Operating system is nearing end of support"],
                "confidence_score": 70,
                "target_region": "eastus",
                "pricing": {
                    "vm_payg_monthly": 390,
                    "disk_total_monthly": 55,
                    "os_license_monthly": 20,
                    "backup_monthly": 10,
                    "monitoring_monthly": 10,
                    "networking_monthly": 15,
                    "total_payg_monthly": 500,
                    "total_optimized_monthly": 330,
                },
            },
        ],
        "total_monthly_cost_usd": 710,
    }


def _sample_workloads() -> dict[str, Any]:
    return {
        "result": {
            "dependencies": [
                {
                    "source_vm": "shop-web-01",
                    "target_vm": "shop-db-01",
                    "target_port": 5432,
                    "protocol": "tcp",
                }
            ],
            "vm_workloads": [],
        },
        "recommendations": [
            {
                "vm_name": "shop-web-01",
                "workload_name": "Contoso Shop",
                "workload_type": "webapp",
                "source_engine": "dotnet_core",
                "source_version": "8.0",
                "recommended_azure_service": "Azure App Service",
                "alternative_services": ["Azure Container Apps", "Azure Kubernetes Service"],
                "estimated_monthly_cost_usd": 108,
                "migration_approach": "replatform",
                "migration_complexity": "low",
                "migration_steps": ["Create App Service plan", "Deploy the application"],
                "issues": [],
                "confidence": 90,
            },
            {
                "vm_name": "shop-db-01",
                "workload_name": "postgres:shop",
                "workload_type": "database",
                "source_engine": "postgresql",
                "source_version": "15",
                "recommended_azure_service": "Azure Database for PostgreSQL Flexible Server",
                "alternative_services": ["PostgreSQL on Azure VM"],
                "estimated_monthly_cost_usd": 290,
                "migration_approach": "replatform",
                "migration_complexity": "medium",
                "migration_steps": ["Use pg_dump or Azure DMS"],
                "issues": [],
                "confidence": 80,
            },
            {
                "vm_name": "dc-01",
                "workload_name": "File Share: shared-data",
                "workload_type": "fileshare",
                "source_engine": "vmfs",
                "recommended_azure_service": "Azure Files",
                "estimated_monthly_cost_usd": 120,
                "migration_approach": "replatform",
                "migration_complexity": "low",
                "confidence": 65,
            },
        ],
    }


def test_intent_classifier_covers_requested_experiences() -> None:
    engine = MigrationChatEngine()

    assert engine.classify_intent("How did this cost get calculated?") == "cost_explain"
    assert engine.classify_intent("Why was App Service selected?") == "service_explain"
    assert engine.classify_intent("Generate landing zones") == "landing_zone"
    assert engine.classify_intent("Build the business case and ROI") == "business_case"
    assert engine.classify_intent("What did discovery find?") == "inventory"
    assert engine.classify_intent("Summarize the assessment") == "summary"


def test_vm_cost_answer_has_exact_breakdown_and_evidence() -> None:
    result = MigrationChatEngine().answer(
        "How did the cost for shop-web-01 get calculated?",
        _sample_discovery(),
        _sample_workloads(),
    )

    assert result["intent"] == "cost_explain"
    assert "Standard_D4s_v5" in result["answer"]
    assert "VM compute: $150/month" in result["answer"]
    assert "Managed disks: $25/month" in result["answer"]
    assert "$210/month" in result["answer"]
    assert result["citations"][0]["entity"] == "shop-web-01"
    assert result["actions"][0]["target"] == "vm-whatif"


def test_follow_up_uses_vm_from_browser_history() -> None:
    result = MigrationChatEngine().answer(
        "How did this cost get calculated?",
        _sample_discovery(),
        _sample_workloads(),
        history=[{"role": "user", "content": "Tell me about shop-db-01"}],
    )

    assert "shop-db-01" in result["answer"]
    assert "Standard_E8s_v6" in result["answer"]


def test_app_service_answer_explains_source_target_and_alternatives() -> None:
    result = MigrationChatEngine().answer(
        "Why was App Service selected?",
        _sample_discovery(),
        _sample_workloads(),
    )

    assert result["intent"] == "service_explain"
    assert "dotnet_core" in result["answer"]
    assert "Azure App Service" in result["answer"]
    assert "Azure Container Apps" in result["answer"]
    assert "90% confidence" in result["answer"]


def test_landing_zone_answer_includes_ctd_evidence_and_action() -> None:
    result = MigrationChatEngine().answer(
        "Generate landing zones",
        _sample_discovery(),
        _sample_workloads(),
        landing_zones={
            "strategy_label": "PaaS Preferred",
            "region": "eastus",
            "applications": [
                {
                    "name": "Contoso Shop",
                    "architecture_entry_id": "n-tier-replatform-medium",
                    "source_member_count": 5,
                    "monthly_cost": 518,
                }
            ],
        },
    )

    assert "Generated 1 application landing-zone" in result["answer"]
    assert "n-tier-replatform-medium" in result["answer"]
    assert result["actions"][0]["target"] == "plan-landing-zone"
    assert any("CTD" in citation["title"] for citation in result["citations"])


def test_business_case_answer_preserves_modeled_values() -> None:
    result = MigrationChatEngine().answer(
        "Build the business case",
        _sample_discovery(),
        _sample_workloads(),
        business_case={
            "target_region": "eastus",
            "pricing_model": "3_year_ri",
            "analysis_years": 3,
            "onprem_monthly": 100_000,
            "azure_monthly": 50_000,
            "annual_savings": 600_000,
            "savings_pct": 50,
            "migration_one_time": 150_000,
            "payback_months": 3,
            "total_tco_savings": 1_650_000,
        },
    )

    assert "$100,000/month" in result["answer"]
    assert "$50,000/month" in result["answer"]
    assert "Payback: 3 months" in result["answer"]
    assert "not a billing quote" in result["answer"]


def test_no_data_response_directs_user_to_connect() -> None:
    result = MigrationChatEngine().answer("Summarize the assessment", {})

    assert result["intent"] == "no_data"
    assert result["actions"][0]["target"] == "connect"


def test_message_length_is_limited() -> None:
    with pytest.raises(ValueError, match="characters or fewer"):
        MigrationChatEngine().answer("x" * (MAX_CHAT_MESSAGE_LENGTH + 1), _sample_discovery())


def test_foundry_enhancer_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "AZURE_MIGRATE_CHAT_ENDPOINT",
        "AZURE_MIGRATE_CHAT_DEPLOYMENT",
        "AZURE_MIGRATE_CHAT_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    status = FoundryGenerativeProvider().status()

    assert status["mode"] == "local-grounded"
    assert status["configured"] is False
    assert "No migration data leaves" in status["cloud_data_notice"]


def test_foundry_enhancer_only_rewrites_grounded_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_MIGRATE_CHAT_ENDPOINT", "https://example.services.ai.azure.com")
    monkeypatch.setenv("AZURE_MIGRATE_CHAT_DEPLOYMENT", "gpt-test")
    monkeypatch.setenv("AZURE_MIGRATE_CHAT_API_KEY", "test-key")
    captured: dict[str, Any] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "Clear grounded response."}}]}

    def _post(url: str, **kwargs: Any) -> _Response:
        captured["url"] = url
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("azure_migrate_simulations.migration_chat.requests.post", _post)
    enhancer = FoundryGenerativeProvider()
    response = enhancer.enhance(
        "Explain cost",
        {
            "answer": "Grounded draft with $210.",
            "citations": [{"title": "VM cost", "source": "assessment", "route": "/api/vms"}],
            "provider": "local-grounded",
        },
    )

    assert response["answer"] == "Clear grounded response."
    assert response["provider"] == "foundry-generative"
    assert captured["headers"]["api-key"] == "test-key"
    prompt = captured["json"]["messages"][1]["content"]
    assert "Grounded draft with $210." in prompt
    assert "VM cost" in prompt


def test_foundry_enhancer_uses_gpt6_reasoning_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_MIGRATE_CHAT_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_MIGRATE_CHAT_DEPLOYMENT", "gpt-6.1-sol")
    monkeypatch.setenv("AZURE_MIGRATE_CHAT_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("AZURE_MIGRATE_CHAT_API_KEY", "test-key")
    captured: dict[str, Any] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "GPT-6 grounded response."}}]}

    def _post(url: str, **kwargs: Any) -> _Response:
        captured["url"] = url
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("azure_migrate_simulations.migration_chat.requests.post", _post)
    response = FoundryGenerativeProvider().enhance(
        "Explain cost",
        {"answer": "Grounded draft.", "citations": [], "provider": "local-grounded"},
    )

    payload = captured["json"]
    assert response["model_deployment"] == "gpt-6.1-sol"
    assert "gpt-6.1-sol" in captured["url"]
    assert "api-version=2024-12-01-preview" in captured["url"]
    assert payload["reasoning_effort"] == "low"
    assert payload["max_completion_tokens"] == 4_000
    assert "temperature" not in payload
    assert "max_tokens" not in payload


def test_chat_store_persists_conversations_across_instances(tmp_path) -> None:
    database = tmp_path / "chat.db"
    first_store = ChatConversationStore(database)
    conversation = first_store.create_conversation()
    first_store.append_message(conversation["id"], "user", "Explain the total Azure cost")
    first_store.append_message(
        conversation["id"],
        "assistant",
        "The assessed run rate is $710/month.",
        {"provider": "foundry-generative", "citations": [{"title": "Fleet cost"}]},
    )

    second_store = ChatConversationStore(database)
    restored = second_store.get_conversation(conversation["id"])

    assert restored is not None
    assert restored["title"] == "Explain the total Azure cost"
    assert restored["message_count"] == 2
    assert restored["messages"][1]["metadata"]["provider"] == "foundry-generative"
    assert second_store.list_conversations()[0]["id"] == conversation["id"]


def test_chat_store_delete_cascades_messages(tmp_path) -> None:
    store = ChatConversationStore(tmp_path / "chat.db")
    conversation = store.create_conversation("Delete me")
    store.append_message(conversation["id"], "user", "Hello")

    assert store.delete_conversation(conversation["id"]) is True
    assert store.get_conversation(conversation["id"]) is None
    assert store.delete_conversation(conversation["id"]) is False


def test_chat_rest_api_returns_grounded_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from azure_migrate_simulations.web import app as web_app

    monkeypatch.setattr(web_app, "_data", _sample_discovery())
    monkeypatch.setattr(web_app, "_workload_data", _sample_workloads())
    monkeypatch.setattr(web_app, "_enrichment_data", {})
    monkeypatch.setattr(web_app, "_perf_history", {})
    monkeypatch.setattr(web_app, "_whatif_overrides", {})
    monkeypatch.setattr(web_app, "_chat_store", ChatConversationStore(tmp_path / "chat.db"))
    monkeypatch.setattr(
        web_app._migration_chat_enhancer,
        "enhance",
        lambda question, response, history=None: response,
    )

    client = web_app.app.test_client()
    response = client.post("/api/chat", json={"message": "Explain the total Azure cost"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["provider"] == "local-grounded"
    assert payload["intent"] == "cost_explain"
    assert "$710/month" in payload["answer"]
    assert payload["citations"]
    assert payload["conversation_id"].startswith("conv-")

    restored = client.get(f"/api/chat/conversations/{payload['conversation_id']}")
    assert restored.status_code == 200
    conversation = restored.get_json()
    assert conversation["message_count"] == 2
    assert conversation["messages"][0]["role"] == "user"
    assert conversation["messages"][1]["role"] == "assistant"


def test_chat_rest_api_validates_request(monkeypatch: pytest.MonkeyPatch) -> None:
    from azure_migrate_simulations.web import app as web_app

    monkeypatch.setattr(web_app, "_data", _sample_discovery())
    client = web_app.app.test_client()

    assert client.post("/api/chat", json={}).status_code == 400
    assert client.post("/api/chat", json={"message": "hello", "history": {}}).status_code == 400
    assert client.post(
        "/api/chat",
        json={"message": "x" * (MAX_CHAT_MESSAGE_LENGTH + 1)},
    ).status_code == 400


def test_chat_status_reports_generative_ai_and_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    from azure_migrate_simulations.web import app as web_app

    monkeypatch.setattr(web_app, "_data", _sample_discovery())
    monkeypatch.setattr(
        web_app._migration_chat_enhancer,
        "status",
        lambda: {
            "mode": "foundry-generative",
            "configured": True,
            "generative_ai": True,
            "deployment": "gpt-6.1-sol",
            "cloud_data_notice": "Grounded context is sent to Foundry.",
        },
    )
    client = web_app.app.test_client()

    payload = client.get("/api/chat/status").get_json()

    assert payload["data_loaded"] is True
    assert payload["stateless"] is False
    assert payload["history_persisted"] is True
    assert payload["history_store"] == "SQLite"
    assert payload["mode"] == "foundry-generative"
    assert payload["generative_ai"] is True
