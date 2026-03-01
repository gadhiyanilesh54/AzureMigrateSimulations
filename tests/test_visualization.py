"""Tests for the visualization module, including the shared build_report helper."""

from digital_twin_migrate.visualization import build_report
from digital_twin_migrate.models import (
    DiscoveredEnvironment,
    DiscoveredVM,
    DiskInfo,
    GuestOSFamily,
    PowerState,
)
from digital_twin_migrate.azure_mapping import generate_recommendations


def _make_env(n_vms: int = 3) -> DiscoveredEnvironment:
    vms = [
        DiscoveredVM(
            name=f"vm-{i}",
            num_cpus=2,
            memory_mb=4096,
            power_state=PowerState.POWERED_ON,
            guest_os_family=GuestOSFamily.LINUX,
            disks=[DiskInfo(label="disk0", capacity_gb=50)],
            total_disk_gb=50,
        )
        for i in range(n_vms)
    ]
    return DiscoveredEnvironment(vcenter_host="test.local", vms=vms)


class TestBuildReport:
    def test_report_structure(self):
        env = _make_env()
        recs = generate_recommendations(env)
        report = build_report(env, recs)

        assert "vcenter_host" in report
        assert report["vcenter_host"] == "test.local"
        assert "summary" in report
        assert report["summary"]["vms"] == 3
        assert "vms" in report
        assert "recommendations" in report
        assert len(report["recommendations"]) == 3
        assert "total_monthly_cost_usd" in report
        assert report["total_monthly_cost_usd"] >= 0

    def test_report_with_empty_env(self):
        env = DiscoveredEnvironment(vcenter_host="empty.local")
        report = build_report(env, [])
        assert report["summary"]["vms"] == 0
        assert report["total_monthly_cost_usd"] == 0
        assert report["recommendations"] == []
