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


def _get_controller_type(vm: vim.VirtualMachine, controller_key: int) -> str:
    """Look up the controller type for a given controller key."""
    if not vm.config or not vm.config.hardware:
        return ""
    for dev in vm.config.hardware.device:
        if hasattr(dev, 'key') and dev.key == controller_key:
            if isinstance(dev, vim.vm.device.ParaVirtualSCSIController):
                return "pvscsi"
            elif isinstance(dev, vim.vm.device.VirtualLsiLogicSASController):
                return "lsilogicsas"
            elif isinstance(dev, vim.vm.device.VirtualLsiLogicController):
                return "lsilogic"
            elif isinstance(dev, vim.vm.device.VirtualBusLogicController):
                return "buslogic"
            elif isinstance(dev, vim.vm.device.VirtualNVMEController):
                return "nvme"
            elif isinstance(dev, vim.vm.device.VirtualIDEController):
                return "ide"
            elif isinstance(dev, vim.vm.device.VirtualAHCIController):
                return "ahci"
            elif isinstance(dev, vim.vm.device.VirtualSCSIController):
                return "scsi"
            return type(dev).__name__
    return ""


def _extract_disks(vm: vim.VirtualMachine) -> list[DiskInfo]:
    disks: list[DiskInfo] = []
    if not vm.config or not vm.config.hardware:
        return disks
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk):
            backing = dev.backing
            ds_name = ""
            thin = False
            disk_mode = ""
            if hasattr(backing, "datastore") and backing.datastore:
                ds_name = backing.datastore.name
            if hasattr(backing, "thinProvisioned"):
                thin = bool(backing.thinProvisioned)
            if hasattr(backing, "diskMode"):
                disk_mode = str(backing.diskMode or "")
            controller_type = _get_controller_type(vm, dev.controllerKey)
            # Boot disk heuristic: unit 0 on controller key 1000 (first SCSI controller)
            is_boot = (dev.controllerKey == 1000 and dev.unitNumber == 0)
            disks.append(DiskInfo(
                label=dev.deviceInfo.label if dev.deviceInfo else "",
                capacity_gb=round(dev.capacityInKB / (1024 * 1024), 2) if dev.capacityInKB else 0,
                thin_provisioned=thin,
                datastore_name=ds_name,
                is_boot_disk=is_boot,
                controller_type=controller_type,
                controller_key=dev.controllerKey,
                unit_number=dev.unitNumber,
                disk_mode=disk_mode,
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


def _get_controller_type_from_devices(devices: list, controller_key: int) -> str:
    """Look up controller type from a flat device list."""
    for dev in devices:
        if hasattr(dev, 'key') and dev.key == controller_key:
            if isinstance(dev, vim.vm.device.ParaVirtualSCSIController):
                return "pvscsi"
            elif isinstance(dev, vim.vm.device.VirtualLsiLogicSASController):
                return "lsilogicsas"
            elif isinstance(dev, vim.vm.device.VirtualLsiLogicController):
                return "lsilogic"
            elif isinstance(dev, vim.vm.device.VirtualBusLogicController):
                return "buslogic"
            elif isinstance(dev, vim.vm.device.VirtualNVMEController):
                return "nvme"
            elif isinstance(dev, vim.vm.device.VirtualIDEController):
                return "ide"
            elif isinstance(dev, vim.vm.device.VirtualAHCIController):
                return "ahci"
            elif isinstance(dev, vim.vm.device.VirtualSCSIController):
                return "scsi"
            return type(dev).__name__
    return ""


def _extract_disks_from_devices(devices: list, **_kw) -> list[DiskInfo]:
    """Extract disk info from a pre-fetched device list (PropertyCollector path)."""
    disks: list[DiskInfo] = []
    for dev in devices:
        if isinstance(dev, vim.vm.device.VirtualDisk):
            backing = dev.backing
            ds_name = ""
            thin = False
            disk_mode = ""
            if hasattr(backing, "datastore") and backing.datastore:
                ds_name = backing.datastore.name
            if hasattr(backing, "thinProvisioned"):
                thin = bool(backing.thinProvisioned)
            if hasattr(backing, "diskMode"):
                disk_mode = str(backing.diskMode or "")
            controller_type = _get_controller_type_from_devices(devices, dev.controllerKey)
            is_boot = (dev.controllerKey == 1000 and dev.unitNumber == 0)
            disks.append(DiskInfo(
                label=dev.deviceInfo.label if dev.deviceInfo else "",
                capacity_gb=round(dev.capacityInKB / (1024 * 1024), 2) if dev.capacityInKB else 0,
                thin_provisioned=thin,
                datastore_name=ds_name,
                is_boot_disk=is_boot,
                controller_type=controller_type,
                controller_key=dev.controllerKey,
                unit_number=dev.unitNumber,
                disk_mode=disk_mode,
            ))
    return disks


def _extract_nics_from_devices(devices: list, ip_map: dict[int, list[str]]) -> list[NetworkInfo]:
    """Extract NIC info from a pre-fetched device list and guest IP map."""
    nics: list[NetworkInfo] = []
    for dev in devices:
        if isinstance(dev, vim.vm.device.VirtualEthernetCard):
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
    return nics


def _build_ip_map(guest_nets) -> dict[int, list[str]]:
    """Build a device-key → IP-addresses map from guest network info."""
    ip_map: dict[int, list[str]] = {}
    for gn in guest_nets:
        key = gn.deviceConfigId
        ips = []
        if gn.ipConfig and gn.ipConfig.ipAddress:
            ips = [ip.ipAddress for ip in gn.ipConfig.ipAddress]
        elif gn.ipAddress:
            ips = gn.ipAddress if isinstance(gn.ipAddress, list) else [gn.ipAddress]
        ip_map[key] = ips
    return ip_map


def _collect_perf_metrics(content: vim.ServiceContent, vm_obj: vim.VirtualMachine,
                          historical: bool = True) -> PerformanceMetrics:
    """Collect performance metrics for a VM using vSphere Performance Manager.

    When *historical* is True, fetches up to 7 days of 5-minute rollup data
    (intervalId=300) and computes avg / P50 / P95 / P99 / max.  Falls back to
    real-time 20-second samples when historical stats are unavailable.
    """
    import statistics
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

        # --- Try historical (5-min rollup, up to 7 days) first ----------------
        used_historical = False
        if historical:
            try:
                hist_spec = vim.PerformanceManager.QuerySpec(
                    entity=vm_obj,
                    metricId=metric_ids,
                    maxSample=2016,  # 7 days × 24h × 60min / 5min = 2016
                    intervalId=300,  # 5-minute rollup
                )
                hist_results = perf_manager.QueryPerf(querySpec=[hist_spec])
                if hist_results and hist_results[0].value:
                    series_data: dict[str, list[float]] = {}
                    for metric_series in hist_results[0].value:
                        field_name = metric_field_map.get(metric_series.id.counterId)
                        if field_name and metric_series.value:
                            vals = [float(v) for v in metric_series.value if v >= 0]
                            if "percent" in field_name or "usage" in field_name:
                                vals = [v / 100.0 for v in vals]
                            series_data[field_name] = vals

                    if series_data:
                        used_historical = True
                        sample_counts = [len(v) for v in series_data.values()]
                        perf.sample_count = max(sample_counts) if sample_counts else 0
                        perf.collection_period_days = min(7, perf.sample_count * 5 // (60 * 24) + 1)
                        perf.perf_data_source = "vcenter_historical"

                        for field_name, vals in series_data.items():
                            if not vals:
                                continue
                            avg_val = statistics.mean(vals)
                            setattr(perf, field_name, avg_val)

                            sorted_vals = sorted(vals)
                            n = len(sorted_vals)
                            # Compute percentiles for CPU and memory
                            if field_name == "cpu_usage_percent":
                                perf.cpu_p50_percent = sorted_vals[int(n * 0.50)] if n > 0 else 0
                                perf.cpu_p95_percent = sorted_vals[min(int(n * 0.95), n - 1)] if n > 0 else 0
                                perf.cpu_p99_percent = sorted_vals[min(int(n * 0.99), n - 1)] if n > 0 else 0
                                perf.cpu_max_percent = sorted_vals[-1] if n > 0 else 0
                            elif field_name == "memory_usage_percent":
                                perf.memory_p50_percent = sorted_vals[int(n * 0.50)] if n > 0 else 0
                                perf.memory_p95_percent = sorted_vals[min(int(n * 0.95), n - 1)] if n > 0 else 0
                                perf.memory_p99_percent = sorted_vals[min(int(n * 0.99), n - 1)] if n > 0 else 0
                                perf.memory_max_percent = sorted_vals[-1] if n > 0 else 0
                            elif field_name in ("disk_iops_read", "disk_iops_write"):
                                # Accumulate total IOPS P95 from both read+write
                                p95_val = sorted_vals[min(int(n * 0.95), n - 1)] if n > 0 else 0
                                perf.disk_iops_p95 += p95_val
                            elif field_name in ("disk_read_kbps", "disk_write_kbps"):
                                p95_val = sorted_vals[min(int(n * 0.95), n - 1)] if n > 0 else 0
                                perf.disk_throughput_p95_kbps += p95_val
                            elif field_name in ("network_rx_kbps", "network_tx_kbps"):
                                p95_val = sorted_vals[min(int(n * 0.95), n - 1)] if n > 0 else 0
                                perf.network_p95_kbps += p95_val
            except Exception as e:
                logger.debug("Historical stats not available for %s: %s", vm_obj.name, e)

        # --- Fallback to real-time single sample ------------------------------
        if not used_historical:
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
                        if "percent" in field_name or "usage" in field_name:
                            val = val / 100.0
                        setattr(perf, field_name, float(val))
                perf.sample_count = 1
                perf.perf_data_source = "vcenter_realtime"

    except Exception as e:
        logger.warning("Could not collect perf metrics for %s: %s", vm_obj.name, e)
    return perf


def _collect_per_disk_perf(content: vim.ServiceContent, vm_obj: vim.VirtualMachine,
                           disks: list[DiskInfo]) -> None:
    """Collect per-disk IOPS and throughput metrics and update DiskInfo in-place."""
    try:
        perf_manager = content.perfManager
        counter_map: dict[str, int] = {}
        for counter in perf_manager.perfCounter:
            full_name = f"{counter.groupInfo.key}.{counter.nameInfo.key}.{counter.rollupType}"
            counter_map[full_name] = counter.key

        # Per-disk counters use instance = "scsiX:Y" format
        disk_counters = {
            "virtualDisk.numberReadAveraged.average": "iops_read",
            "virtualDisk.numberWriteAveraged.average": "iops_write",
            "virtualDisk.read.average": "throughput_read_kbps",
            "virtualDisk.write.average": "throughput_write_kbps",
            "virtualDisk.totalReadLatency.average": "latency_read_ms",
            "virtualDisk.totalWriteLatency.average": "latency_write_ms",
        }

        metric_ids = []
        metric_field_map: dict[int, str] = {}
        for counter_name, field_name in disk_counters.items():
            cid = counter_map.get(counter_name)
            if cid is not None:
                # Use "*" to get all disk instances
                metric_ids.append(vim.PerformanceManager.MetricId(counterId=cid, instance="*"))
                metric_field_map[cid] = field_name

        if not metric_ids:
            return

        query_spec = vim.PerformanceManager.QuerySpec(
            entity=vm_obj,
            metricId=metric_ids,
            maxSample=12,  # last hour of 5-min samples
            intervalId=300,
        )
        results = perf_manager.QueryPerf(querySpec=[query_spec])
        if not results:
            return

        # Map instance IDs ("scsi0:0") to disk index
        for metric_series in results[0].value:
            field_name = metric_field_map.get(metric_series.id.counterId)
            instance = metric_series.id.instance  # e.g. "scsi0:0"
            if not field_name or not instance or not metric_series.value:
                continue
            avg_val = sum(float(v) for v in metric_series.value if v >= 0) / max(len(metric_series.value), 1)

            # Match instance to disk by controller:unit pattern
            for disk in disks:
                disk_instance = f"scsi{disk.controller_key - 1000}:{disk.unit_number}"
                if instance == disk_instance:
                    setattr(disk, field_name, round(avg_val, 2))
                    break
    except Exception as e:
        logger.debug("Could not collect per-disk perf for %s: %s", vm_obj.name, e)


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
            "config.version",                 # hardware version e.g. "vmx-19"
            "config.firmware",                # "bios" or "efi"
            "config.cpuHotAddEnabled",
            "config.memoryHotAddEnabled",
            "config.guestId",
            "summary.config.name",
            "runtime.powerState",
            "runtime.maxCpuUsage",
            "runtime.host",
            "guest.hostName",
            "guest.toolsRunningStatus",
            "guest.toolsVersion",
            "guest.net",
            "guest.guestFullName",            # detailed OS from tools
            "resourceConfig",                 # CPU/memory reservations, limits, shares
            "resourcePool",
            "parent",
            "snapshot",                       # snapshot tree
            "layoutEx",                       # for snapshot/clone size
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

            # Build guest IP map FIRST so NIC construction can use it
            guest_nets = vm_props.get("guest.net") or []
            ip_map = _build_ip_map(guest_nets)

            disks = _extract_disks_from_devices(devices)
            nics = _extract_nics_from_devices(devices, ip_map)

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
                perf = _collect_perf_metrics(content, vm_obj, historical=True)
                # Collect per-disk performance
                if disks:
                    _collect_per_disk_perf(content, vm_obj, disks)

            # --- Snapshots ---------------------------------------------------
            has_snapshots = False
            snapshot_count = 0
            snapshot_size_gb = 0.0
            has_linked_clones = False
            snapshot_tree = vm_props.get("snapshot")
            if snapshot_tree and hasattr(snapshot_tree, "rootSnapshotList"):
                has_snapshots = True
                def _count_snapshots(snap_list):
                    count = 0
                    for s in snap_list:
                        count += 1
                        if s.childSnapshotList:
                            count += _count_snapshots(s.childSnapshotList)
                    return count
                snapshot_count = _count_snapshots(snapshot_tree.rootSnapshotList)

            # Snapshot size from layoutEx
            layout_ex = vm_props.get("layoutEx")
            if layout_ex and hasattr(layout_ex, "file"):
                for f in layout_ex.file:
                    fname = f.name.lower() if f.name else ""
                    if "delta" in fname or "sesparse" in fname:
                        has_linked_clones = True
                    if any(ext in fname for ext in ("-delta.vmdk", "-sesparse.vmdk", ".vmsn")):
                        snapshot_size_gb += (f.size or 0) / (1024 ** 3)

            # --- Resource config (CPU/memory reservations, limits, shares) ----
            cpu_reservation = 0
            cpu_limit = -1
            mem_reservation = 0
            mem_limit = -1
            cpu_shares_str = ""
            mem_shares_str = ""
            res_config = vm_props.get("resourceConfig")
            if res_config:
                if hasattr(res_config, "cpuAllocation"):
                    cpu_alloc = res_config.cpuAllocation
                    cpu_reservation = cpu_alloc.reservation or 0
                    cpu_limit = cpu_alloc.limit if cpu_alloc.limit is not None else -1
                    if cpu_alloc.shares:
                        cpu_shares_str = str(cpu_alloc.shares.level) if cpu_alloc.shares.level else str(cpu_alloc.shares.shares)
                if hasattr(res_config, "memoryAllocation"):
                    mem_alloc = res_config.memoryAllocation
                    mem_reservation = mem_alloc.reservation or 0
                    mem_limit = mem_alloc.limit if mem_alloc.limit is not None else -1
                    if mem_alloc.shares:
                        mem_shares_str = str(mem_alloc.shares.level) if mem_alloc.shares.level else str(mem_alloc.shares.shares)

            # --- Hardware version & firmware ---------------------------------
            hw_version = vm_props.get("config.version", "") or ""
            firmware = vm_props.get("config.firmware", "") or ""
            boot_type = "efi" if firmware.lower() == "efi" else "bios"
            cpu_hot_add = bool(vm_props.get("config.cpuHotAddEnabled", False))
            mem_hot_add = bool(vm_props.get("config.memoryHotAddEnabled", False))
            guest_os_detailed = vm_props.get("guest.guestFullName", "") or ""

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
                # New fields
                hardware_version=hw_version,
                boot_type=boot_type,
                cpu_reservation_mhz=cpu_reservation,
                cpu_limit_mhz=cpu_limit,
                memory_reservation_mb=mem_reservation,
                memory_limit_mb=mem_limit,
                cpu_shares=cpu_shares_str,
                memory_shares=mem_shares_str,
                has_snapshots=has_snapshots,
                snapshot_count=snapshot_count,
                snapshot_size_gb=round(snapshot_size_gb, 2),
                has_linked_clones=has_linked_clones,
                cpu_hot_add_enabled=cpu_hot_add,
                memory_hot_add_enabled=mem_hot_add,
                guest_os_detailed=guest_os_detailed,
                firmware=firmware,
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
