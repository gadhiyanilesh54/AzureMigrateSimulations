"""Provision and manage Azure Digital Twins instance."""

from __future__ import annotations

import logging
import time

from azure.identity import DefaultAzureCredential
from azure.mgmt.digitaltwins import AzureDigitalTwinsManagementClient
from azure.mgmt.digitaltwins.models import (
    DigitalTwinsDescription,
    DigitalTwinsIdentity,
    DigitalTwinsIdentityType,
)
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import ResourceGroup

from .config import AzureConfig

logger = logging.getLogger(__name__)


def _ensure_resource_group(cfg: AzureConfig, credential) -> None:
    """Create the resource group if it doesn't exist."""
    client = ResourceManagementClient(credential, cfg.subscription_id)
    if not client.resource_groups.check_existence(cfg.resource_group):
        logger.info("Creating resource group %s in %s …", cfg.resource_group, cfg.location)
        client.resource_groups.create_or_update(
            cfg.resource_group,
            ResourceGroup(location=cfg.location, tags={"purpose": "azure-migrate-simulations"}),
        )
    else:
        logger.info("Resource group %s already exists.", cfg.resource_group)


def _ensure_dt_instance(cfg: AzureConfig, credential) -> str:
    """Create the Azure Digital Twins instance if it doesn't exist. Returns the host name."""
    dt_client = AzureDigitalTwinsManagementClient(credential, cfg.subscription_id)

    try:
        existing = dt_client.digital_twins.get(cfg.resource_group, cfg.dt_instance_name)
        host = existing.host_name
        logger.info("Digital Twins instance %s already exists at %s", cfg.dt_instance_name, host)
        return host
    except Exception:
        pass  # instance doesn't exist yet

    logger.info("Creating Azure Digital Twins instance %s …", cfg.dt_instance_name)
    dt_description = DigitalTwinsDescription(
        location=cfg.location,
        identity=DigitalTwinsIdentity(type=DigitalTwinsIdentityType.SYSTEM_ASSIGNED),
        tags={"purpose": "azure-migrate-simulations"},
    )
    poller = dt_client.digital_twins.begin_create_or_update(
        cfg.resource_group, cfg.dt_instance_name, dt_description
    )
    result = poller.result()
    logger.info("Digital Twins instance created. Host: %s", result.host_name)
    return result.host_name


def provision_digital_twins(cfg: AzureConfig) -> str:
    """
    Ensure the Azure Digital Twins instance is provisioned.
    Returns the ADT endpoint URL (https://<hostname>).
    """
    credential = DefaultAzureCredential()
    _ensure_resource_group(cfg, credential)
    hostname = _ensure_dt_instance(cfg, credential)
    return f"https://{hostname}"
