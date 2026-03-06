"""Tests for azure_mapping.py recommendation engine."""

from azure_migrate_simulations.azure_mapping import (
    VM_CATALOG,
    generate_recommendations,
    _check_os_eol,
    _detect_workload_type,
    _calculate_confidence,
    _recommend_disk_per_disk,
    _assess_readiness,
)
from azure_migrate_simulations.models import (
    DiscoveredEnvironment,
    DiscoveredVM,
    DiskInfo,
    GuestOSFamily,
    PerformanceMetrics,
    PowerState,
)


def _make_vm(name: str, cpus: int = 4, mem_mb: int = 8192, disk_gb: float = 100.0,
              power: PowerState = PowerState.POWERED_ON,
              os_family: GuestOSFamily = GuestOSFamily.LINUX,
              guest_os: str = "Ubuntu 22.04",
              perf: PerformanceMetrics | None = None) -> DiscoveredVM:
    return DiscoveredVM(
        name=name,
        num_cpus=cpus,
        memory_mb=mem_mb,
        power_state=power,
        guest_os=guest_os,
        guest_os_family=os_family,
        disks=[DiskInfo(label="Hard disk 1", capacity_gb=disk_gb, is_boot_disk=True)],
        total_disk_gb=disk_gb,
        perf=perf or PerformanceMetrics(),
    )


class TestVMCatalog:
    def test_catalog_is_non_empty(self):
        assert len(VM_CATALOG) > 0

    def test_catalog_entries_have_required_fields(self):
        for sku in VM_CATALOG:
            assert sku.name, "SKU name must not be empty"
            assert sku.vcpus > 0
            assert sku.memory_gb > 0
            assert sku.monthly_cost_usd >= 0


class TestGenerateRecommendations:
    def test_basic_recommendation(self):
        vm = _make_vm("web-01")
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert len(recs) == 1
        assert recs[0].vm_name == "web-01"
        assert recs[0].recommended_vm_sku != ""
        assert recs[0].estimated_monthly_cost_usd > 0

    def test_powered_off_vm_gets_recommendation(self):
        vm = _make_vm("dev-01", power=PowerState.POWERED_OFF)
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert len(recs) == 1

    def test_multiple_vms(self):
        vms = [_make_vm(f"vm-{i}", cpus=2 * (i + 1), mem_mb=4096 * (i + 1)) for i in range(5)]
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=vms)
        recs = generate_recommendations(env)
        assert len(recs) == 5
        names = {r.vm_name for r in recs}
        assert len(names) == 5

    def test_large_vm_recommendation(self):
        """A VM with many CPUs and large memory should get a large SKU."""
        vm = _make_vm("big-01", cpus=64, mem_mb=256 * 1024, disk_gb=2000)
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert len(recs) == 1
        assert recs[0].estimated_monthly_cost_usd > 100

    def test_windows_vm_gets_os_license_cost(self):
        """Windows VMs should include OS license cost in pricing."""
        vm = _make_vm("win-01", os_family=GuestOSFamily.WINDOWS, guest_os="Windows Server 2022")
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert recs[0].os_type == "windows"
        assert recs[0].azure_hybrid_benefit_eligible is True
        assert recs[0].pricing.os_license_monthly > 0

    def test_linux_vm_no_license_cost(self):
        """Linux VMs should have zero OS license cost."""
        vm = _make_vm("linux-01", os_family=GuestOSFamily.LINUX, guest_os="Ubuntu 22.04")
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert recs[0].os_type == "linux"
        assert recs[0].pricing.os_license_monthly == 0.0

    def test_per_disk_recommendations(self):
        """Each disk should get its own recommendation."""
        disks = [
            DiskInfo(label="Hard disk 1", capacity_gb=100, is_boot_disk=True),
            DiskInfo(label="Hard disk 2", capacity_gb=500, is_boot_disk=False),
            DiskInfo(label="Hard disk 3", capacity_gb=1000, is_boot_disk=False),
        ]
        vm = DiscoveredVM(
            name="multi-disk-vm", num_cpus=4, memory_mb=8192,
            power_state=PowerState.POWERED_ON, guest_os="Ubuntu 22.04",
            guest_os_family=GuestOSFamily.LINUX,
            disks=disks, total_disk_gb=1600,
        )
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert len(recs[0].disk_recommendations) == 3
        assert recs[0].disk_recommendations[0].is_os_disk is True

    def test_pricing_breakdown_populated(self):
        """Recommendation should include full pricing breakdown."""
        vm = _make_vm("pricing-test")
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        p = recs[0].pricing
        assert p.vm_payg_monthly > 0
        assert p.vm_1yr_ri_monthly > 0
        assert p.vm_3yr_ri_monthly > 0
        assert p.disk_total_monthly >= 0
        assert p.total_payg_monthly > 0
        assert p.total_optimized_monthly > 0
        assert p.total_optimized_monthly <= p.total_payg_monthly

    def test_optimized_cost_less_than_payg(self):
        """Optimized cost (3yr RI) should always be less than PAYG."""
        vm = _make_vm("cost-test")
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert recs[0].total_tco_optimized_monthly <= recs[0].total_tco_monthly


class TestPercentileBasedSizing:
    def test_perf_based_downsizing(self):
        """VM with low CPU P95 should be downsized."""
        perf = PerformanceMetrics(
            cpu_usage_percent=15.0,
            cpu_p95_percent=20.0,
            memory_usage_percent=30.0,
            memory_p95_percent=35.0,
            perf_data_source="perf_history",
            sample_count=100,
        )
        vm = _make_vm("low-util", cpus=16, mem_mb=64 * 1024, perf=perf)
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        # Should downsize from 16 vCPUs
        assert "downsized" in recs[0].right_sizing_note.lower()

    def test_as_is_sizing_when_no_perf(self):
        """VM with no perf data should use as-is sizing."""
        vm = _make_vm("no-perf")
        env = DiscoveredEnvironment(vcenter_host="test.local", vms=[vm])
        recs = generate_recommendations(env)
        assert recs[0].sizing_approach == "as_is"


class TestOSEOL:
    def test_centos_7_eol(self):
        vm = _make_vm("centos-vm", guest_os="CentOS 7.9")
        eol_status, detail, os_type = _check_os_eol(vm)
        assert eol_status == "eol"
        assert "2024" in detail
        assert os_type == "linux"

    def test_windows_2012_eol_esu(self):
        vm = _make_vm("old-win", os_family=GuestOSFamily.WINDOWS,
                       guest_os="Windows Server 2012 R2")
        eol_status, detail, os_type = _check_os_eol(vm)
        assert eol_status == "eol_esu_eligible"
        assert os_type == "windows"

    def test_ubuntu_2204_supported(self):
        vm = _make_vm("ubuntu-vm", guest_os="Ubuntu 22.04")
        eol_status, detail, os_type = _check_os_eol(vm)
        assert eol_status == "supported"


class TestWorkloadDetection:
    def test_detects_database(self):
        vm = _make_vm("sql-prod-01")
        assert _detect_workload_type(vm) == "database"

    def test_detects_web_server(self):
        vm = _make_vm("web-frontend-01")
        assert _detect_workload_type(vm) == "web_server"

    def test_detects_dev_test(self):
        vm = _make_vm("dev-sandbox-01")
        assert _detect_workload_type(vm) == "dev_test"

    def test_general_fallback(self):
        vm = _make_vm("app-server-01")
        assert _detect_workload_type(vm) == "general"


class TestConfidenceScoring:
    def test_high_confidence_with_full_data(self):
        perf = PerformanceMetrics(
            cpu_usage_percent=50.0, memory_usage_percent=60.0,
            cpu_p95_percent=70.0, memory_p95_percent=75.0,
            disk_iops_read=500, disk_iops_write=200,
            perf_data_source="vcenter_historical",
            sample_count=500, collection_period_days=30,
        )
        vm = _make_vm("high-conf", perf=perf)
        vm.tools_status = "guestToolsRunning"
        score = _calculate_confidence(vm, "performance_based_p95")
        assert score >= 85.0

    def test_low_confidence_without_perf(self):
        vm = _make_vm("low-conf", power=PowerState.POWERED_OFF)
        score = _calculate_confidence(vm, "as_is")
        assert score < 30.0


class TestReadinessAssessment:
    def test_ready_vm(self):
        vm = _make_vm("healthy-vm")
        readiness, issues = _assess_readiness(vm)
        assert readiness == "Ready"
        assert len(issues) == 0

    def test_snapshot_warning(self):
        vm = _make_vm("snap-vm")
        vm.has_snapshots = True
        vm.snapshot_count = 3
        vm.snapshot_size_gb = 50.0
        readiness, issues = _assess_readiness(vm)
        assert readiness == "Ready with conditions"
        assert any("snapshot" in i.lower() for i in issues)

    def test_unsupported_os(self):
        vm = _make_vm("solaris-vm", guest_os="Solaris 11")
        readiness, issues = _assess_readiness(vm)
        assert any("not natively supported" in i for i in issues)

    def test_eol_os_detection(self):
        vm = _make_vm("centos7-vm", guest_os="CentOS 7.5")
        readiness, issues = _assess_readiness(vm)
        assert any("end of life" in i.lower() for i in issues)


class TestPerDiskRecommendation:
    def test_os_disk_gets_premium(self):
        """OS disk should always get Premium SSD."""
        disks = [DiskInfo(label="OS Disk", capacity_gb=64, is_boot_disk=True)]
        vm = DiscoveredVM(
            name="os-disk-test", num_cpus=2, memory_mb=4096,
            power_state=PowerState.POWERED_ON,
            guest_os_family=GuestOSFamily.LINUX,
            disks=disks, total_disk_gb=64,
        )
        recs = _recommend_disk_per_disk(vm)
        assert len(recs) == 1
        assert "Premium" in recs[0].recommended_type
        assert recs[0].is_os_disk is True

    def test_high_iops_data_disk(self):
        """High-IOPS data disk should get Premium SSD v2 or Ultra."""
        disks = [
            DiskInfo(label="OS", capacity_gb=64, is_boot_disk=True),
            DiskInfo(label="Data", capacity_gb=500, is_boot_disk=False,
                     iops_read=15000, iops_write=10000),
        ]
        vm = DiscoveredVM(
            name="iops-test", num_cpus=8, memory_mb=32768,
            power_state=PowerState.POWERED_ON,
            guest_os_family=GuestOSFamily.LINUX,
            disks=disks, total_disk_gb=564,
        )
        recs = _recommend_disk_per_disk(vm)
        assert len(recs) == 2
        data_rec = [r for r in recs if not r.is_os_disk][0]
        assert "Ultra" in data_rec.recommended_type or "v2" in data_rec.recommended_type
