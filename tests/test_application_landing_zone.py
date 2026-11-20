"""Tests for application-centric CTD landing-zone resolution."""

import pytest

from azure_migrate_simulations.application_landing_zone import (
    CATALOGUE_COMMIT,
    CATALOGUE_VERSION,
    generate_application_landing_zones,
)


def _application() -> dict:
    members = [
        {
            "id": "vm:shop-web-01",
            "type": "vm",
            "name": "shop-web-01",
            "source_vm": "shop-web-01",
            "target_service": "Azure Virtual Machine",
            "target_sku": "Standard_D2s_v5",
            "monthly_cost": 100,
        },
        {
            "id": "webapp:shop-web-01:shop",
            "type": "webapp",
            "name": "Contoso Shop",
            "source_vm": "shop-web-01",
            "target_service": "Azure App Service",
            "target_sku": "P1v3",
            "monthly_cost": 80,
        },
        {
            "id": "database:shop-db-01:postgres",
            "type": "database",
            "name": "postgres:shop",
            "source_vm": "shop-db-01",
            "target_service": "Azure Database for PostgreSQL Flexible Server",
            "target_sku": "GP_Standard_D4ds_v4",
            "monthly_cost": 160,
        },
        {
            "id": "fileshare:shared-data",
            "type": "fileshare",
            "name": "shared-data",
            "source_vm": "",
            "target_service": "Azure Files",
            "target_sku": "Premium_LRS",
            "monthly_cost": 60,
            "allocated_monthly_cost": 30,
        },
    ]
    return {
        "id": "app-001-contoso-shop",
        "name": "Contoso Shop",
        "application_type": "Custom",
        "criticality": "Tier-2",
        "environment": "Production",
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
    }


def test_paas_preferred_resolves_catalogue_architecture() -> None:
    result = generate_application_landing_zones([_application()])

    assert result["schema_version"] == "1.0"
    assert result["catalogue"]["version"] == CATALOGUE_VERSION
    assert result["catalogue"]["commit"] == CATALOGUE_COMMIT
    assert result["application_count"] == 1

    architecture = result["applications"][0]
    assert architecture["architecture_entry_id"] == "n-tier-replatform-medium"
    assert architecture["strategy"] == "PaaSPreferred"
    assert architecture["tags"] == {
        "architecture_pattern": "n-tier",
        "migration_intent": "replatform",
        "criticality": "medium",
        "environment": "production",
        "hybrid_multicloud": "cloud-only",
    }
    assert architecture["source_member_count"] == 4
    assert architecture["landing_zone"]["type"] == "application"


def test_paas_architecture_uses_assessed_compute_data_and_storage_targets() -> None:
    architecture = generate_application_landing_zones([_application()])["applications"][0]
    migrated_slots = [slot for slot in architecture["slots"] if slot["origin"] == "migrated"]

    assert {slot["domain"] for slot in migrated_slots} == {"compute", "data", "storage"}
    assert {slot["resolved_target"] for slot in migrated_slots} == {
        "Azure App Service",
        "Azure Database for PostgreSQL Flexible Server",
        "Azure Files",
    }
    assert architecture["monthly_cost"] == 270
    assert any(node["group"] == "application" for node in architecture["nodes"])
    assert architecture["edges"]


def test_lift_and_shift_selects_rehost_entry_and_vm_target() -> None:
    architecture = generate_application_landing_zones(
        [_application()],
        strategy="lift_and_shift",
    )["applications"][0]

    assert architecture["architecture_entry_id"] == "n-tier-rehost-medium"
    assert architecture["strategy"] == "LiftAndShift"
    migrated_targets = {
        slot["resolved_target"]
        for slot in architecture["slots"]
        if slot["origin"] == "migrated"
    }
    assert migrated_targets == {"Azure Virtual Machine", "Azure Files"}


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown landing-zone strategy"):
        generate_application_landing_zones([_application()], strategy="unknown")