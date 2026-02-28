"""vCenter discovery module — connects to VMware vCenter and discovers the full environment."""

from __future__ import annotations

import atexit
import logging
import ssl
from typing import Any

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl

from .config import VCenterConfig
from .models import (
    DiscoveredCluster,
    DiscoveredDatacenter,
    DiscoveredDatastore,
    DiscoveredEnvironment,
    DiscoveredHost,
    DiscoveredNetwork,
    DiscoveredVM,
    DiskInfo,
    GuestOSFamily,
    NetworkInfo,
    PerformanceMetrics,
    PowerState,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _connect(cfg: VCenterConfig) -> vim.ServiceInstance:
    """Establish a connection to vCenter."""
    context = None
    if cfg.disable_ssl:
        context = ssl._create_unverified_context()

    logger.info("Connecting to vCenter %s:%s as %s …", cfg.host, cfg.port, cfg.username)
    si = SmartConnect(
        host=cfg.host,
        user=cfg.username,
        pwd=cfg.password,
        port=cfg.port,
        sslContext=context,
    )
    atexit.register(Disconnect, si)
    logger.info("Connected successfully. API version: %s", si.content.about.apiVersion)
    return si


# ---------------------------------------------------------------------------
# Helper: container view traversal
# ---------------------------------------------------------------------------

def _get_all_objects(content: vim.ServiceContent, obj_type: list, folder=None):
    """Return all managed objects of given type(s)."""
    container = content.viewManager.CreateContainerView(
        folder or content.rootFolder, obj_type, recursive=True
    )
    objects = list(container.view)
    container.Destroy()
    return objects


def _get_parent_name(obj, parent_type) -> str:
    """Walk up the parent chain to find the name of a given parent type."""
    current = getattr(obj, "parent", None)
    while current:
        if isinstance(current, parent_type):
            return current.name
        current = getattr(current, "parent", None)
    return ""


# ---------------------------------------------------------------------------
# Discover datacenters
# ---------------------------------------------------------------------------

def _discover_datacenters(content: vim.ServiceContent) -> list[DiscoveredDatacenter]:
    dcs = _get_all_objects(content, [vim.Datacenter])
    result = []
    for dc in dcs:
        result.append(DiscoveredDatacenter(
            name=dc.name,
            vcenter_id=str(dc._moId),
        ))
    logger.info("Discovered %d datacenter(s)", len(result))
    return result


# ---------------------------------------------------------------------------
# Discover clusters
# ---------------------------------------------------------------------------

def _discover_clusters(content: vim.ServiceContent) -> list[DiscoveredCluster]:
    clusters = _get_all_objects(content, [vim.ClusterComputeResource])
    result = []
    for cl in clusters:
        summary = cl.summary
        result.append(DiscoveredCluster(
            name=cl.name,
            vcenter_id=str(cl._moId),
            datacenter=_get_parent_name(cl, vim.Datacenter),
            total_cpu_mhz=int(summary.totalCpu) if summary.totalCpu else 0,
            total_memory_mb=int((summary.totalMemory or 0) / (1024 * 1024)),
            host_count=summary.numHosts or 0,
            ha_enabled=bool(cl.configuration.dasConfig.enabled) if cl.configuration and cl.configuration.dasConfig else False,
            drs_enabled=bool(cl.configuration.drsConfig.enabled) if cl.configuration and cl.configuration.drsConfig else False,
        ))
    logger.info("Discovered %d cluster(s)", len(result))
    return result


# ---------------------------------------------------------------------------
# Discover ESXi hosts
# ---------------------------------------------------------------------------

def _discover_hosts(content: vim.ServiceContent) -> list[DiscoveredHost]:
    hosts = _get_all_objects(content, [vim.HostSystem])
    result = []
    for h in hosts:
        hw = h.hardware
        summary = h.summary
        config = summary.config if summary else None
        # CPU model is in cpuPkg[0].description, not a top-level attribute
        cpu_model = ""
        if hw and hw.cpuPkg and len(hw.cpuPkg) > 0:
            cpu_model = hw.cpuPkg[0].description or ""

        result.append(DiscoveredHost(
            name=h.name,
            vcenter_id=str(h._moId),
            cpu_model=cpu_model,
            cpu_cores=hw.cpuInfo.numCpuCores if hw and hw.cpuInfo else 0,
            cpu_threads=hw.cpuInfo.numCpuThreads if hw and hw.cpuInfo else 0,
            cpu_mhz=int(hw.cpuInfo.hz / 1_000_000) if hw and hw.cpuInfo and hw.cpuInfo.hz else 0,
            memory_mb=int(hw.memorySize / (1024 * 1024)) if hw and hw.memorySize else 0,
            vendor=hw.systemInfo.vendor if hw and hw.systemInfo else "",
            model=hw.systemInfo.model if hw and hw.systemInfo else "",
            esxi_version=config.product.fullName if config and config.product else "",
            datacenter=_get_parent_name(h, vim.Datacenter),
            cluster=_get_parent_name(h, vim.ClusterComputeResource),
            vm_count=len(h.vm) if h.vm else 0,
        ))
    logger.info("Discovered %d host(s)", len(result))
    return result


# ---------------------------------------------------------------------------
# Discover datastores
# ---------------------------------------------------------------------------

def _discover_datastores(content: vim.ServiceContent) -> list[DiscoveredDatastore]:
    stores = _get_all_objects(content, [vim.Datastore])
    result = []
    for ds in stores:
        info = ds.info
        summary = ds.summary
        result.append(DiscoveredDatastore(
            name=ds.name,
            vcenter_id=str(ds._moId),
            type=summary.type if summary else "",
            capacity_gb=round((summary.capacity or 0) / (1024 ** 3), 2) if summary else 0,
            free_space_gb=round((summary.freeSpace or 0) / (1024 ** 3), 2) if summary else 0,
            datacenter=_get_parent_name(ds, vim.Datacenter),
        ))
    logger.info("Discovered %d datastore(s)", len(result))
    return result


# ---------------------------------------------------------------------------
# Discover networks
# ---------------------------------------------------------------------------

def _discover_networks(content: vim.ServiceContent) -> list[DiscoveredNetwork]:
    nets = _get_all_objects(content, [vim.Network])
    result = []
    for n in nets:
        vlan_id = 0
        net_type = "Standard"
        if isinstance(n, vim.dvs.DistributedVirtualPortgroup):
            net_type = "Distributed"
            cfg = n.config
            if cfg and hasattr(cfg, "defaultPortConfig"):
                dpc = cfg.defaultPortConfig
                if hasattr(dpc, "vlan") and hasattr(dpc.vlan, "vlanId"):
                    vlan_id = dpc.vlan.vlanId or 0
        result.append(DiscoveredNetwork(
            name=n.name,
            vcenter_id=str(n._moId),
            vlan_id=int(vlan_id) if isinstance(vlan_id, int) else 0,
            network_type=net_type,
            datacenter=_get_parent_name(n, vim.Datacenter),
        ))
    logger.info("Discovered %d network(s)", len(result))
    return result


# ---------------------------------------------------------------------------
# Discover VMs (the main workload inventory)
# ---------------------------------------------------------------------------

def _classify_os(guest_full_name: str) -> GuestOSFamily:
    lower = (guest_full_name or "").lower()
    if "windows" in lower:
        return GuestOSFamily.WINDOWS
    if any(k in lower for k in ("linux", "ubuntu", "centos", "rhel", "debian", "suse", "oracle", "photon", "fedora")):
        return GuestOSFamily.LINUX
    return GuestOSFamily.OTHER


def _extract_disks(vm: vim.VirtualMachine) -> list[DiskInfo]:
    disks: list[DiskInfo] = []
    if not vm.config or not vm.config.hardware:
        return disks
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk):
            backing = dev.backing
            ds_name = ""
            thin = False
            if hasattr(backing, "datastore") and backing.datastore:
                ds_name = backing.datastore.name
            if hasattr(backing, "thinProvisioned"):
                thin = bool(backing.thinProvisioned)
            disks.append(DiskInfo(
                label=dev.deviceInfo.label if dev.deviceInfo else "",
                capacity_gb=round(dev.capacityInKB / (1024 * 1024), 2) if dev.capacityInKB else 0,
                thin_provisioned=thin,
                datastore_name=ds_name,
            ))
    return disks


def _extract_nics(vm: vim.VirtualMachine) -> list[NetworkInfo]:
    nics: list[NetworkInfo] = []
    if not vm.config or not vm.config.hardware:
        return nics

    # Build IP map from guest info
    ip_map: dict[int, list[str]] = {}
    if vm.guest and vm.guest.net:
        for gn in vm.guest.net:
            key = gn.deviceConfigId
            ips = []
            if gn.ipConfig and gn.ipConfig.ipAddress:
                ips = [ip.ipAddress for ip in gn.ipConfig.ipAddress]
            elif gn.ipAddress:
                ips = gn.ipAddress if isinstance(gn.ipAddress, list) else [gn.ipAddress]
            ip_map[key] = ips

    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualEthernetCard):
            net_name = ""
            if hasattr(dev, "backing"):
                if hasattr(dev.backing, "network") and dev.backing.network:
                    net_name = dev.backing.network.name
                elif hasattr(dev.backing, "port"):
                    net_name = getattr(dev.backing.port, "portgroupKey", "")
            nics.append(NetworkInfo(
                name=dev.deviceInfo.label if dev.deviceInfo else "",
                mac_address=dev.macAddress or "",
                ip_addresses=ip_map.get(dev.key, []),
                network_name=net_name,
                connected=bool(dev.connectable and dev.connectable.connected) if dev.connectable else False,
            ))
    return nics


def _collect_perf_metrics(content: vim.ServiceContent, vm_obj: vim.VirtualMachine) -> PerformanceMetrics:
    """Collect real-time performance metrics for a VM using vSphere Performance Manager."""
    perf = PerformanceMetrics()
    try:
        perf_manager = content.perfManager

        # Counter name → counter ID mapping
        counter_map: dict[str, int] = {}
        for counter in perf_manager.perfCounter:
            full_name = f"{counter.groupInfo.key}.{counter.nameInfo.key}.{counter.rollupType}"
            counter_map[full_name] = counter.key

        # Metrics we want
        desired = {
            "cpu.usage.average": "cpu_usage_percent",
            "cpu.usagemhz.average": "cpu_usage_mhz",
            "mem.usage.average": "memory_usage_percent",
            "mem.active.average": "memory_usage_mb",
            "disk.read.average": "disk_read_kbps",
            "disk.write.average": "disk_write_kbps",
            "disk.numberRead.summation": "disk_iops_read",
            "disk.numberWrite.summation": "disk_iops_write",
            "net.received.average": "network_rx_kbps",
            "net.transmitted.average": "network_tx_kbps",
        }

        metric_ids = []
        metric_field_map: dict[int, str] = {}
        for counter_name, field_name in desired.items():
            cid = counter_map.get(counter_name)
            if cid is not None:
                metric_ids.append(vim.PerformanceManager.MetricId(counterId=cid, instance=""))
                metric_field_map[cid] = field_name

        if not metric_ids:
            return perf

        query_spec = vim.PerformanceManager.QuerySpec(
            entity=vm_obj,
            metricId=metric_ids,
            maxSample=1,
            intervalId=20,  # real-time 20-second interval
        )
        results = perf_manager.QueryPerf(querySpec=[query_spec])
        if results:
            for metric_series in results[0].value:
                field_name = metric_field_map.get(metric_series.id.counterId)
                if field_name and metric_series.value:
                    val = metric_series.value[-1]  # most recent sample
                    # vSphere returns percentages as hundredths (e.g., 5000 = 50%)
                    if "percent" in field_name or "usage" in field_name:
                        val = val / 100.0
                    setattr(perf, field_name, float(val))
    except Exception as e:
        logger.warning("Could not collect perf metrics for %s: %s", vm_obj.name, e)
    return perf


def _bulk_fetch_vm_properties(content: vim.ServiceContent) -> list[dict]:
    """Use PropertyCollector to fetch all VM properties in a single bulk call.

    This is dramatically faster than lazy per-VM property access (seconds vs minutes).
    """
    container_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], recursive=True
    )

    # Define the properties we need
    traversal_spec = vmodl.query.PropertyCollector.TraversalSpec(
        name="traverseEntities",
        path="view",
        skip=False,
        type=vim.view.ContainerView,
    )
    obj_spec = vmodl.query.PropertyCollector.ObjectSpec(
        obj=container_view,
        skip=True,
        selectSet=[traversal_spec],
    )
    prop_spec = vmodl.query.PropertyCollector.PropertySpec(
        type=vim.VirtualMachine,
        all=False,
        pathSet=[
            "name",
            "config.template",
            "config.instanceUuid",
            "config.guestFullName",
            "config.hardware.numCPU",
            "config.hardware.memoryMB",
            "config.hardware.device",
            "config.annotation",
            "summary.config.name",
            "runtime.powerState",
            "runtime.maxCpuUsage",
            "runtime.host",
            "guest.hostName",
            "guest.toolsRunningStatus",
            "guest.toolsVersion",
            "guest.net",
            "resourcePool",
            "parent",
        ],
    )
    filter_spec = vmodl.query.PropertyCollector.FilterSpec(
        objectSet=[obj_spec],
        propSet=[prop_spec],
    )

    props = content.propertyCollector.RetrieveContents([filter_spec])
    container_view.Destroy()

    vm_data_list: list[dict] = []
    for obj_content in props:
        vm_props: dict[str, Any] = {"_obj": obj_content.obj}
        for prop in obj_content.propSet:
            vm_props[prop.name] = prop.val
        vm_data_list.append(vm_props)

    logger.info("PropertyCollector fetched %d VM object(s)", len(vm_data_list))
    return vm_data_list


def _discover_vms(content: vim.ServiceContent, collect_perf: bool = True) -> list[DiscoveredVM]:
    # Use PropertyCollector for bulk fetch — much faster than lazy per-VM access
    vm_data_list = _bulk_fetch_vm_properties(content)
    result: list[DiscoveredVM] = []
    total = len(vm_data_list)
    skipped = 0
    errors = 0

    for idx, vm_props in enumerate(vm_data_list, 1):
        vm_obj = vm_props["_obj"]
        vm_name = vm_props.get("name", f"unknown-{idx}")

        try:
            # Skip templates
            is_template = vm_props.get("config.template", False)
            if is_template:
                skipped += 1
                continue

            if idx % 25 == 0 or idx == total:
                logger.info("Processing VM %d/%d (%s) ...", idx, total, vm_name)

            # Extract power state
            power = PowerState.POWERED_OFF
            ps_raw = vm_props.get("runtime.powerState")
            if ps_raw:
                ps = str(ps_raw)
                if ps == "poweredOn":
                    power = PowerState.POWERED_ON
                elif ps == "suspended":
                    power = PowerState.SUSPENDED

            guest_full = vm_props.get("config.guestFullName", "") or ""
            num_cpus = vm_props.get("config.hardware.numCPU", 0) or 0
            memory_mb = vm_props.get("config.hardware.memoryMB", 0) or 0
            max_cpu = vm_props.get("runtime.maxCpuUsage", 0) or 0

            # Extract disks from device list
            devices = vm_props.get("config.hardware.device", []) or []
            disks: list[DiskInfo] = []
            nics: list[NetworkInfo] = []

            # Build guest IP map FIRST so NIC construction can use it
            guest_nets = vm_props.get("guest.net") or []
            ip_map: dict[int, list[str]] = {}
            for gn in guest_nets:
                key = gn.deviceConfigId
                ips = []
                if gn.ipConfig and gn.ipConfig.ipAddress:
                    ips = [ip.ipAddress for ip in gn.ipConfig.ipAddress]
                elif gn.ipAddress:
                    ips = gn.ipAddress if isinstance(gn.ipAddress, list) else [gn.ipAddress]
                ip_map[key] = ips

            for dev in devices:
                if isinstance(dev, vim.vm.device.VirtualDisk):
                    backing = dev.backing
                    ds_name = ""
                    thin = False
                    if hasattr(backing, "datastore") and backing.datastore:
                        ds_name = backing.datastore.name
                    if hasattr(backing, "thinProvisioned"):
                        thin = bool(backing.thinProvisioned)
                    disks.append(DiskInfo(
                        label=dev.deviceInfo.label if dev.deviceInfo else "",
                        capacity_gb=round(dev.capacityInKB / (1024 * 1024), 2) if dev.capacityInKB else 0,
                        thin_provisioned=thin,
                        datastore_name=ds_name,
                    ))
                elif isinstance(dev, vim.vm.device.VirtualEthernetCard):
                    net_name = ""
                    try:
                        if hasattr(dev, "backing"):
                            if hasattr(dev.backing, "network") and dev.backing.network:
                                net_name = dev.backing.network.name
                            elif hasattr(dev.backing, "port"):
                                net_name = getattr(dev.backing.port, "portgroupKey", "")
                    except Exception:
                        pass  # network ref may be stale
                    nics.append(NetworkInfo(
                        name=dev.deviceInfo.label if dev.deviceInfo else "",
                        mac_address=dev.macAddress or "",
                        ip_addresses=ip_map.get(dev.key, []),
                        network_name=net_name,
                        connected=bool(dev.connectable and dev.connectable.connected) if dev.connectable else False,
                    ))

            # Host name from runtime.host
            host_obj = vm_props.get("runtime.host")
            host_name = host_obj.name if host_obj else ""

            # Resource pool
            rp = vm_props.get("resourcePool")
            rp_name = rp.name if rp else ""

            # Parent chain for datacenter/cluster/folder
            dc_name = _get_parent_name(vm_obj, vim.Datacenter)
            cluster_name = _get_parent_name(vm_obj, vim.ClusterComputeResource)
            folder_name = _get_parent_name(vm_obj, vim.Folder)

            # Performance (only if requested and VM is on)
            perf = PerformanceMetrics()
            if collect_perf and power == PowerState.POWERED_ON:
                perf = _collect_perf_metrics(content, vm_obj)

            discovered = DiscoveredVM(
                vcenter_id=str(vm_obj._moId),
                name=vm_name,
                instance_uuid=vm_props.get("config.instanceUuid", "") or "",
                num_cpus=num_cpus,
                cpu_mhz_per_core=int(max_cpu / (num_cpus or 1)) if max_cpu else 0,
                memory_mb=memory_mb,
                power_state=power,
                guest_os=guest_full,
                guest_os_family=_classify_os(guest_full),
                guest_hostname=vm_props.get("guest.hostName", "") or "",
                disks=disks,
                total_disk_gb=round(sum(d.capacity_gb for d in disks), 2),
                nics=nics,
                datacenter=dc_name,
                cluster=cluster_name,
                host=host_name,
                folder=folder_name,
                resource_pool=rp_name,
                tools_status=str(vm_props.get("guest.toolsRunningStatus", "")),
                tools_version=str(vm_props.get("guest.toolsVersion", "")),
                perf=perf,
                annotation=vm_props.get("config.annotation", "") or "",
            )
            result.append(discovered)
        except Exception as e:
            errors += 1
            logger.warning("Error processing VM %d/%d '%s': %s", idx, total, vm_name, e)

    logger.info(
        "Discovered %d VM(s) (excluded %d templates, %d errors) from %d objects",
        len(result), skipped, errors, total,
    )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_environment(cfg: VCenterConfig, collect_perf: bool = True) -> DiscoveredEnvironment:
    """
    Connect to vCenter and perform full discovery of the environment.
    Returns a DiscoveredEnvironment with all inventoried objects.
    """
    si = _connect(cfg)
    content = si.content

    env = DiscoveredEnvironment(
        vcenter_host=cfg.host,
        datacenters=_discover_datacenters(content),
        clusters=_discover_clusters(content),
        hosts=_discover_hosts(content),
        datastores=_discover_datastores(content),
        networks=_discover_networks(content),
        vms=_discover_vms(content, collect_perf=collect_perf),
    )
    return env
