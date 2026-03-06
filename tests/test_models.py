"""Tests for data models (models.py)."""

from azure_migrate_simulations.models import (
    DiskInfo,
    DiscoveredVM,
    DiscoveredHost,
    DiscoveredEnvironment,
    GuestOSFamily,
    NetworkInfo,
    PerformanceMetrics,
    PowerState,
)


class TestPowerState:
    def test_enum_values(self):
        assert PowerState.POWERED_ON.value == "poweredOn"
        assert PowerState.POWERED_OFF.value == "poweredOff"
        assert PowerState.SUSPENDED.value == "suspended"


class TestGuestOSFamily:
    def test_enum_values(self):
        assert GuestOSFamily.WINDOWS.value == "windows"
        assert GuestOSFamily.LINUX.value == "linux"
        assert GuestOSFamily.OTHER.value == "other"


class TestDiskInfo:
    def test_defaults(self):
        d = DiskInfo()
        assert d.label == ""
        assert d.capacity_gb == 0.0
        assert d.thin_provisioned is False

    def test_with_values(self):
        d = DiskInfo(label="Hard disk 1", capacity_gb=100.0, thin_provisioned=True, datastore_name="ds1")
        assert d.capacity_gb == 100.0
        assert d.datastore_name == "ds1"

    def test_new_disk_fields(self):
        d = DiskInfo(
            label="Hard disk 1", capacity_gb=200.0,
            is_boot_disk=True, controller_type="paravirtual",
            controller_key=1000, unit_number=0, disk_mode="persistent",
        )
        assert d.is_boot_disk is True
        assert d.controller_type == "paravirtual"
        assert d.controller_key == 1000
        assert d.unit_number == 0
        assert d.disk_mode == "persistent"

    def test_per_disk_perf_fields(self):
        d = DiskInfo(
            label="Data disk", capacity_gb=500.0,
            iops_read=1500.0, iops_write=800.0,
            throughput_read_kbps=50000.0, throughput_write_kbps=25000.0,
            latency_read_ms=1.2, latency_write_ms=2.5,
        )
        assert d.iops_read == 1500.0
        assert d.iops_write == 800.0
        assert d.throughput_read_kbps == 50000.0
        assert d.latency_write_ms == 2.5


class TestNetworkInfo:
    def test_defaults(self):
        n = NetworkInfo()
        assert n.ip_addresses == []
        assert n.connected is True


class TestPerformanceMetrics:
    def test_defaults_are_zero(self):
        p = PerformanceMetrics()
        assert p.cpu_usage_mhz == 0.0
        assert p.memory_usage_percent == 0.0

    def test_percentile_fields(self):
        p = PerformanceMetrics(
            cpu_p50_percent=30.0, cpu_p95_percent=70.0,
            cpu_p99_percent=85.0, cpu_max_percent=95.0,
            memory_p50_percent=40.0, memory_p95_percent=65.0,
            memory_p99_percent=80.0, memory_max_percent=90.0,
            perf_data_source="vcenter_historical",
            sample_count=500, collection_period_days=7,
        )
        assert p.cpu_p95_percent == 70.0
        assert p.memory_p95_percent == 65.0
        assert p.perf_data_source == "vcenter_historical"
        assert p.sample_count == 500
        assert p.collection_period_days == 7


class TestDiscoveredVM:
    def test_default_vm(self):
        vm = DiscoveredVM(name="test-vm", num_cpus=4, memory_mb=8192)
        assert vm.name == "test-vm"
        assert vm.num_cpus == 4
        assert vm.memory_mb == 8192
        assert vm.power_state == PowerState.POWERED_OFF
        assert vm.guest_os_family == GuestOSFamily.OTHER
        assert vm.disks == []
        assert vm.total_disk_gb == 0.0

    def test_new_vm_fields(self):
        vm = DiscoveredVM(
            name="new-fields-vm", num_cpus=8, memory_mb=16384,
            hardware_version="vmx-19", boot_type="efi",
            cpu_reservation_mhz=2000, cpu_limit_mhz=8000,
            memory_reservation_mb=4096, memory_limit_mb=16384,
            has_snapshots=True, snapshot_count=2, snapshot_size_gb=15.5,
            has_linked_clones=False, numa_nodes=2,
            cpu_hot_add_enabled=True, memory_hot_add_enabled=False,
            firmware="efi",
        )
        assert vm.hardware_version == "vmx-19"
        assert vm.boot_type == "efi"
        assert vm.cpu_reservation_mhz == 2000
        assert vm.has_snapshots is True
        assert vm.snapshot_count == 2
        assert vm.snapshot_size_gb == 15.5
        assert vm.cpu_hot_add_enabled is True
        assert vm.firmware == "efi"


class TestDiscoveredEnvironment:
    def test_empty_environment(self):
        env = DiscoveredEnvironment(vcenter_host="test.local")
        assert env.vcenter_host == "test.local"
        assert env.vms == []
        assert env.hosts == []
        assert env.datacenters == []
