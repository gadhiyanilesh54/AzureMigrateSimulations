"""Create digital twins and relationships in Azure Digital Twins from discovered vCenter data."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from azure.digitaltwins.core import DigitalTwinsClient
from azure.identity import DefaultAzureCredential

from .models import (
    DiscoveredCluster,
    DiscoveredDatacenter,
    DiscoveredDatastore,
    DiscoveredEnvironment,
    DiscoveredHost,
    DiscoveredNetwork,
    DiscoveredVM,
)

logger = logging.getLogger(__name__)

DTDL_MODELS_PATH = Path(__file__).parent / "dtdl_models.json"


def _sanitize_id(name: str) -> str:
    """Convert a name into a valid Digital Twin ID (alphanumeric + hyphens)."""
    s = re.sub(r"[^a-zA-Z0-9_-]", "-", name)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unknown"


def _build_dt_client(endpoint: str) -> DigitalTwinsClient:
    credential = DefaultAzureCredential()
    return DigitalTwinsClient(endpoint, credential)


# ---------------------------------------------------------------------------
# Upload DTDL models
# ---------------------------------------------------------------------------

def upload_models(client: DigitalTwinsClient) -> None:
    """Upload DTDL models to the Azure Digital Twins instance."""
    models_json = json.loads(DTDL_MODELS_PATH.read_text(encoding="utf-8"))
    try:
        client.create_models(models_json)
        logger.info("Uploaded %d DTDL model(s).", len(models_json))
    except Exception as e:
        if "ModelAlreadyExists" in str(e) or "409" in str(e):
            logger.info("DTDL models already exist — skipping upload.")
        else:
            raise


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def _upsert_twin(client: DigitalTwinsClient, twin_id: str, model_id: str, properties: dict) -> None:
    """Create or update a digital twin."""
    twin = {
        "$metadata": {"$model": model_id},
        **properties,
    }
    try:
        client.upsert_digital_twin(twin_id, twin)
        logger.debug("Upserted twin: %s", twin_id)
    except Exception as e:
        logger.error("Failed to upsert twin %s: %s", twin_id, e)


def _upsert_relationship(
    client: DigitalTwinsClient,
    source_id: str,
    target_id: str,
    rel_name: str,
    rel_id: str | None = None,
) -> None:
    """Create or update a relationship between twins."""
    rid = rel_id or f"{source_id}-{rel_name}-{target_id}"
    relationship = {
        "$relationshipId": rid,
        "$sourceId": source_id,
        "$targetId": target_id,
        "$relationshipName": rel_name,
    }
    try:
        client.upsert_relationship(source_id, rid, relationship)
        logger.debug("Upserted relationship: %s -> %s [%s]", source_id, target_id, rel_name)
    except Exception as e:
        logger.error("Failed to upsert relationship %s: %s", rid, e)


# ---------------------------------------------------------------------------
# Create twins for each entity type
# ---------------------------------------------------------------------------

def _create_datacenter_twins(client: DigitalTwinsClient, env: DiscoveredEnvironment) -> None:
    for dc in env.datacenters:
        tid = _sanitize_id(f"dc-{dc.name}")
        _upsert_twin(client, tid, "dtmi:com:microsoft:migrate:Datacenter;1", {
            "vcenter_id": dc.vcenter_id,
            "vcenter_host": env.vcenter_host,
        })


def _create_cluster_twins(client: DigitalTwinsClient, env: DiscoveredEnvironment) -> None:
    for cl in env.clusters:
        tid = _sanitize_id(f"cluster-{cl.name}")
        _upsert_twin(client, tid, "dtmi:com:microsoft:migrate:Cluster;1", {
            "vcenter_id": cl.vcenter_id,
            "datacenter": cl.datacenter,
            "total_cpu_mhz": cl.total_cpu_mhz,
            "total_memory_mb": cl.total_memory_mb,
            "host_count": cl.host_count,
            "ha_enabled": cl.ha_enabled,
            "drs_enabled": cl.drs_enabled,
        })
        # Relationship: datacenter → cluster
        if cl.datacenter:
            dc_tid = _sanitize_id(f"dc-{cl.datacenter}")
            _upsert_relationship(client, dc_tid, tid, "contains_cluster")


def _create_host_twins(client: DigitalTwinsClient, env: DiscoveredEnvironment) -> None:
    for h in env.hosts:
        tid = _sanitize_id(f"host-{h.name}")
        _upsert_twin(client, tid, "dtmi:com:microsoft:migrate:Host;1", {
            "vcenter_id": h.vcenter_id,
            "cpu_model": h.cpu_model,
            "cpu_cores": h.cpu_cores,
            "cpu_threads": h.cpu_threads,
            "cpu_mhz": h.cpu_mhz,
            "memory_mb": h.memory_mb,
            "vendor": h.vendor,
            "model": h.model,
            "esxi_version": h.esxi_version,
            "datacenter": h.datacenter,
            "cluster": h.cluster,
            "vm_count": h.vm_count,
        })
        # Relationship: cluster → host
        if h.cluster:
            cl_tid = _sanitize_id(f"cluster-{h.cluster}")
            _upsert_relationship(client, cl_tid, tid, "contains_host")


def _create_datastore_twins(client: DigitalTwinsClient, env: DiscoveredEnvironment) -> None:
    for ds in env.datastores:
        tid = _sanitize_id(f"ds-{ds.name}")
        _upsert_twin(client, tid, "dtmi:com:microsoft:migrate:Datastore;1", {
            "vcenter_id": ds.vcenter_id,
            "ds_type": ds.type,
            "capacity_gb": ds.capacity_gb,
            "free_space_gb": ds.free_space_gb,
            "datacenter": ds.datacenter,
        })
        if ds.datacenter:
            dc_tid = _sanitize_id(f"dc-{ds.datacenter}")
            _upsert_relationship(client, dc_tid, tid, "contains_datastore")


def _create_network_twins(client: DigitalTwinsClient, env: DiscoveredEnvironment) -> None:
    for net in env.networks:
        tid = _sanitize_id(f"net-{net.name}")
        _upsert_twin(client, tid, "dtmi:com:microsoft:migrate:Network;1", {
            "vcenter_id": net.vcenter_id,
            "vlan_id": net.vlan_id,
            "network_type": net.network_type,
            "datacenter": net.datacenter,
        })
        if net.datacenter:
            dc_tid = _sanitize_id(f"dc-{net.datacenter}")
            _upsert_relationship(client, dc_tid, tid, "contains_network")


def _create_vm_twins(client: DigitalTwinsClient, env: DiscoveredEnvironment) -> None:
    """Create twins for all VMs, including performance and Azure recommendation components."""
    # Build lookup for datastore names → twin IDs
    ds_lookup = {ds.name: _sanitize_id(f"ds-{ds.name}") for ds in env.datastores}
    net_lookup = {n.name: _sanitize_id(f"net-{n.name}") for n in env.networks}

    for vm in env.vms:
        tid = _sanitize_id(f"vm-{vm.name}")
        _upsert_twin(client, tid, "dtmi:com:microsoft:migrate:VirtualMachine;1", {
            "vcenter_id": vm.vcenter_id,
            "instance_uuid": vm.instance_uuid,
            "num_cpus": vm.num_cpus,
            "cpu_mhz_per_core": vm.cpu_mhz_per_core,
            "memory_mb": vm.memory_mb,
            "power_state": vm.power_state.value,
            "guest_os": vm.guest_os,
            "guest_os_family": vm.guest_os_family.value,
            "guest_hostname": vm.guest_hostname,
            "total_disk_gb": vm.total_disk_gb,
            "datacenter": vm.datacenter,
            "cluster": vm.cluster,
            "host": vm.host,
            "folder": vm.folder,
            "resource_pool": vm.resource_pool,
            "tools_status": vm.tools_status,
            "annotation": vm.annotation,
            "performance": {
                "$metadata": {},
                "cpu_usage_mhz": vm.perf.cpu_usage_mhz,
                "cpu_usage_percent": vm.perf.cpu_usage_percent,
                "memory_usage_mb": vm.perf.memory_usage_mb,
                "memory_usage_percent": vm.perf.memory_usage_percent,
                "disk_read_kbps": vm.perf.disk_read_kbps,
                "disk_write_kbps": vm.perf.disk_write_kbps,
                "disk_iops_read": vm.perf.disk_iops_read,
                "disk_iops_write": vm.perf.disk_iops_write,
                "network_rx_kbps": vm.perf.network_rx_kbps,
                "network_tx_kbps": vm.perf.network_tx_kbps,
            },
            "azure_recommendation": {
                "$metadata": {},
                "recommended_vm_sku": "",
                "recommended_vm_family": "",
                "recommended_disk_type": "",
                "recommended_disk_size_gb": 0,
                "estimated_monthly_cost_usd": 0.0,
                "migration_readiness": "Unknown",
                "migration_issues": "",
                "target_region": "",
            },
        })

        # Relationship: host → VM
        if vm.host:
            host_tid = _sanitize_id(f"host-{vm.host}")
            _upsert_relationship(client, host_tid, tid, "runs_vm")

        # Relationship: VM → datastores
        seen_ds = set()
        for disk in vm.disks:
            if disk.datastore_name and disk.datastore_name not in seen_ds:
                seen_ds.add(disk.datastore_name)
                ds_tid = ds_lookup.get(disk.datastore_name)
                if ds_tid:
                    _upsert_relationship(client, tid, ds_tid, "uses_datastore")

        # Relationship: VM → networks
        seen_nets = set()
        for nic in vm.nics:
            if nic.network_name and nic.network_name not in seen_nets:
                seen_nets.add(nic.network_name)
                net_tid = net_lookup.get(nic.network_name)
                if net_tid:
                    _upsert_relationship(client, tid, net_tid, "connected_to_network")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_digital_twin(endpoint: str, env: DiscoveredEnvironment) -> None:
    """
    Upload DTDL models and create all twins + relationships for the discovered environment.
    """
    client = _build_dt_client(endpoint)

    logger.info("Uploading DTDL models …")
    upload_models(client)

    logger.info("Creating digital twins for %d datacenters …", len(env.datacenters))
    _create_datacenter_twins(client, env)

    logger.info("Creating digital twins for %d clusters …", len(env.clusters))
    _create_cluster_twins(client, env)

    logger.info("Creating digital twins for %d hosts …", len(env.hosts))
    _create_host_twins(client, env)

    logger.info("Creating digital twins for %d datastores …", len(env.datastores))
    _create_datastore_twins(client, env)

    logger.info("Creating digital twins for %d networks …", len(env.networks))
    _create_network_twins(client, env)

    logger.info("Creating digital twins for %d VMs …", len(env.vms))
    _create_vm_twins(client, env)

    total = (
        len(env.datacenters) + len(env.clusters) + len(env.hosts)
        + len(env.datastores) + len(env.networks) + len(env.vms)
    )
    logger.info("Digital twin creation complete. Total twins: %d", total)
