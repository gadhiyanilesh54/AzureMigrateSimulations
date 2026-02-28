"""Data models representing discovered on-premises infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GuestOSFamily(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    OTHER = "other"


class PowerState(str, Enum):
    POWERED_ON = "poweredOn"
    POWERED_OFF = "poweredOff"
    SUSPENDED = "suspended"


@dataclass
class DiskInfo:
    label: str = ""
    capacity_gb: float = 0.0
    thin_provisioned: bool = False
    datastore_name: str = ""


@dataclass
class NetworkInfo:
    name: str = ""
    mac_address: str = ""
    ip_addresses: list[str] = field(default_factory=list)
    network_name: str = ""
    connected: bool = True


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics (averages over collection period)."""
    cpu_usage_mhz: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    disk_read_kbps: float = 0.0
    disk_write_kbps: float = 0.0
    disk_iops_read: float = 0.0
    disk_iops_write: float = 0.0
    network_rx_kbps: float = 0.0
    network_tx_kbps: float = 0.0


@dataclass
class DiscoveredVM:
    """A virtual machine discovered from vCenter."""
    # Identity
    vcenter_id: str = ""          # MoRef ID
    name: str = ""
    instance_uuid: str = ""

    # Compute
    num_cpus: int = 0
    cpu_mhz_per_core: int = 0
    memory_mb: int = 0
    power_state: PowerState = PowerState.POWERED_OFF

    # Guest OS
    guest_os: str = ""
    guest_os_family: GuestOSFamily = GuestOSFamily.OTHER
    guest_hostname: str = ""

    # Storage
    disks: list[DiskInfo] = field(default_factory=list)
    total_disk_gb: float = 0.0

    # Network
    nics: list[NetworkInfo] = field(default_factory=list)

    # Location in vCenter hierarchy
    datacenter: str = ""
    cluster: str = ""
    host: str = ""
    folder: str = ""
    resource_pool: str = ""

    # VMware Tools
    tools_status: str = ""
    tools_version: str = ""

    # Performance
    perf: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    # Tags / annotations
    tags: dict[str, str] = field(default_factory=dict)
    annotation: str = ""


@dataclass
class DiscoveredHost:
    """An ESXi host discovered from vCenter."""
    name: str = ""
    vcenter_id: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    cpu_mhz: int = 0
    memory_mb: int = 0
    vendor: str = ""
    model: str = ""
    esxi_version: str = ""
    datacenter: str = ""
    cluster: str = ""
    vm_count: int = 0


@dataclass
class DiscoveredDatastore:
    """A datastore discovered from vCenter."""
    name: str = ""
    vcenter_id: str = ""
    type: str = ""               # VMFS, NFS, vSAN, etc.
    capacity_gb: float = 0.0
    free_space_gb: float = 0.0
    datacenter: str = ""


@dataclass
class DiscoveredNetwork:
    """A network (port group / dvSwitch) discovered from vCenter."""
    name: str = ""
    vcenter_id: str = ""
    vlan_id: int = 0
    network_type: str = ""       # Standard, Distributed
    datacenter: str = ""


@dataclass
class DiscoveredCluster:
    """A compute cluster discovered from vCenter."""
    name: str = ""
    vcenter_id: str = ""
    datacenter: str = ""
    total_cpu_mhz: int = 0
    total_memory_mb: int = 0
    host_count: int = 0
    ha_enabled: bool = False
    drs_enabled: bool = False


@dataclass
class DiscoveredDatacenter:
    """A vSphere datacenter discovered from vCenter."""
    name: str = ""
    vcenter_id: str = ""


@dataclass
class DiscoveredEnvironment:
    """Complete discovered on-premises environment."""
    vcenter_host: str = ""
    datacenters: list[DiscoveredDatacenter] = field(default_factory=list)
    clusters: list[DiscoveredCluster] = field(default_factory=list)
    hosts: list[DiscoveredHost] = field(default_factory=list)
    vms: list[DiscoveredVM] = field(default_factory=list)
    datastores: list[DiscoveredDatastore] = field(default_factory=list)
    networks: list[DiscoveredNetwork] = field(default_factory=list)
