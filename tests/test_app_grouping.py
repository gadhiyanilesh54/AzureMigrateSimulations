"""Tests for heterogeneous application grouping."""

from azure_migrate_simulations.app_grouping import detect_application_groups


def _vm(name: str, datastore: str) -> dict:
    return {
        "name": name,
        "folder": "Production/ContosoShop",
        "guest_os": "Ubuntu 22.04",
        "guest_os_family": "linux",
        "disks": [{"datastore_name": datastore}],
    }


def _vm_recommendation(name: str, cost: float) -> dict:
    return {
        "vm_name": name,
        "recommended_vm_sku": "Standard_D2s_v5",
        "estimated_monthly_cost_usd": cost,
        "migration_readiness": "Ready",
        "confidence_score": 80,
    }


def _workload_recommendation(
    vm_name: str,
    name: str,
    workload_type: str,
    target: str,
    cost: float,
) -> dict:
    return {
        "vm_name": vm_name,
        "workload_name": name,
        "workload_type": workload_type,
        "source_engine": workload_type,
        "source_version": "1.0",
        "recommended_azure_service": target,
        "estimated_monthly_cost_usd": cost,
        "migration_approach": "replatform",
        "migration_complexity": "medium",
        "confidence": 75,
    }


def _sample_inputs() -> tuple[list[dict], list[dict], dict, list[dict]]:
    vms = [_vm("shop-web-01", "shared-data"), _vm("shop-db-01", "shared-data")]
    recommendations = [
        _vm_recommendation("shop-web-01", 100),
        _vm_recommendation("shop-db-01", 200),
    ]
    workload_data = {
        "result": {
            "dependencies": [{
                "source_vm": "shop-web-01",
                "target_vm": "shop-db-01",
                "target_port": 5432,
                "protocol": "tcp",
            }],
        },
        "recommendations": [
            _workload_recommendation(
                "shop-web-01", "Contoso Shop", "webapp", "Azure App Service", 80,
            ),
            _workload_recommendation(
                "shop-web-01", "shop-api", "container", "Azure Container Apps", 40,
            ),
            _workload_recommendation(
                "shop-db-01", "postgres:shop", "database",
                "Azure Database for PostgreSQL Flexible Server", 160,
            ),
            _workload_recommendation(
                "Production", "File Share: shared-data", "fileshare", "Azure Files", 60,
            ),
        ],
    }
    datastores = [{"name": "shared-data", "type": "VMFS", "capacity_gb": 500}]
    return vms, recommendations, workload_data, datastores


def test_group_contains_complete_heterogeneous_application() -> None:
    vms, recommendations, workload_data, datastores = _sample_inputs()

    groups = detect_application_groups(
        vms,
        recommendations,
        workload_data=workload_data,
        datastores=datastores,
    )

    assert len(groups) == 1
    application = groups[0]
    assert application["application_type"] == "Custom"
    assert application["architecture_pattern"] == "n-tier"
    assert application["component_summary"] == {
        "virtual_machines": 2,
        "web_apps": 1,
        "databases": 1,
        "containers": 1,
        "orchestrators": 0,
        "file_shares": 1,
    }
    assert {member["type"] for member in application["members"]} == {
        "vm", "webapp", "database", "container", "fileshare",
    }
    assert application["member_count"] == 6


def test_group_cost_uses_real_vm_field_and_assessed_targets() -> None:
    vms, recommendations, workload_data, datastores = _sample_inputs()

    application = detect_application_groups(
        vms,
        recommendations,
        workload_data=workload_data,
        datastores=datastores,
    )[0]

    assert application["total_monthly_cost"] == 300
    assert application["target_monthly_cost"] == 340
    fileshare = next(
        member for member in application["members"] if member["type"] == "fileshare"
    )
    assert fileshare["allocated_monthly_cost"] == 60
    assert fileshare["shared"] is False


def test_multiple_workload_types_are_preserved_on_one_vm() -> None:
    vms, recommendations, workload_data, datastores = _sample_inputs()

    application = detect_application_groups(
        vms,
        recommendations,
        workload_data=workload_data,
        datastores=datastores,
    )[0]
    web_vm = next(vm for vm in application["vms"] if vm["name"] == "shop-web-01")

    assert web_vm["workload_types"] == ["container", "webapp"]
