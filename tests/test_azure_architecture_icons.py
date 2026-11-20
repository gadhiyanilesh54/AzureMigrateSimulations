"""Regression checks for official Azure icons used by architecture diagrams."""

from pathlib import Path
from xml.etree import ElementTree


ICON_DIRECTORY = (
    Path(__file__).parents[1]
    / "src"
    / "azure_migrate_simulations"
    / "web"
    / "static"
    / "icons"
    / "azure"
)

EXPECTED_ICONS = {
    "app-services.svg",
    "application-gateway.svg",
    "application-insights.svg",
    "azure-cosmos-db.svg",
    "azure-database-mysql-server.svg",
    "azure-database-postgresql-server.svg",
    "azure-fileshares.svg",
    "container-apps-environments.svg",
    "function-apps.svg",
    "key-vault.svg",
    "kubernetes-services.svg",
    "managed-identities.svg",
    "private-endpoints.svg",
    "recovery-services-vaults.svg",
    "sql-database.svg",
    "virtual-machine.svg",
    "virtual-network.svg",
}


def test_official_azure_icon_bundle_is_complete() -> None:
    actual_icons = {path.name for path in ICON_DIRECTORY.glob("*.svg")}

    assert actual_icons == EXPECTED_ICONS
    assert (ICON_DIRECTORY / "NOTICE.md").is_file()


def test_all_azure_icons_are_valid_scalable_svg() -> None:
    for icon_name in sorted(EXPECTED_ICONS):
        root = ElementTree.parse(ICON_DIRECTORY / icon_name).getroot()

        assert root.tag.endswith("svg"), icon_name
        assert root.attrib.get("viewBox"), icon_name