"""Azure target mapping engine — recommends Azure VM SKUs, disks, and cost estimates."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from .models import DiscoveredEnvironment, DiscoveredVM, GuestOSFamily, PowerState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Azure VM SKU catalog (subset of common SKUs for recommendation)
# ---------------------------------------------------------------------------

@dataclass
class AzureVMSku:
    name: str
    family: str
    vcpus: int
    memory_gb: float
    max_data_disks: int
    max_iops: int
    monthly_cost_usd: float   # Pay-as-you-go East US pricing (approximate)
    gpu: bool = False


# Representative SKU catalog — in production, fetch from Azure Retail Prices API
VM_CATALOG: list[AzureVMSku] = [
    # B-series (burstable)
    AzureVMSku("Standard_B1s",  "B", 1,  1,    2,   320,    7.59),
    AzureVMSku("Standard_B2s",  "B", 2,  4,    4,  1280,   30.37),
    AzureVMSku("Standard_B2ms", "B", 2,  8,    4,  2880,   60.74),
    AzureVMSku("Standard_B4ms", "B", 4, 16,    8,  5760,  121.47),
    AzureVMSku("Standard_B8ms", "B", 8, 32,   16, 11520,  242.94),
    # D-series v5 (general purpose)
    AzureVMSku("Standard_D2s_v5",  "Dsv5",  2,   8,   4,  3750,   70.08),
    AzureVMSku("Standard_D4s_v5",  "Dsv5",  4,  16,   8,  6400,  140.16),
    AzureVMSku("Standard_D8s_v5",  "Dsv5",  8,  32,  16, 12800,  280.32),
    AzureVMSku("Standard_D16s_v5", "Dsv5", 16,  64,  32, 25600,  560.64),
    AzureVMSku("Standard_D32s_v5", "Dsv5", 32, 128,  32, 51200, 1121.28),
    # E-series v5 (memory optimized)
    AzureVMSku("Standard_E2s_v5",  "Esv5",  2,  16,   4,  3750,   91.98),
    AzureVMSku("Standard_E4s_v5",  "Esv5",  4,  32,   8,  6400,  183.96),
    AzureVMSku("Standard_E8s_v5",  "Esv5",  8,  64,  16, 12800,  367.92),
    AzureVMSku("Standard_E16s_v5", "Esv5", 16, 128,  32, 25600,  735.84),
    AzureVMSku("Standard_E32s_v5", "Esv5", 32, 256,  32, 51200, 1471.68),
    # F-series v2 (compute optimized)
    AzureVMSku("Standard_F2s_v2",  "Fsv2",  2,   4,   4,  3200,   61.32),
    AzureVMSku("Standard_F4s_v2",  "Fsv2",  4,   8,   8,  6400,  122.64),
    AzureVMSku("Standard_F8s_v2",  "Fsv2",  8,  16,  16, 12800,  245.28),
    AzureVMSku("Standard_F16s_v2", "Fsv2", 16,  32,  32, 25600,  490.56),
]


# ---------------------------------------------------------------------------
# Azure Disk catalog
# ---------------------------------------------------------------------------

@dataclass
class AzureDiskOption:
    type_name: str       # StandardSSD_LRS, Premium_SSD, etc.
    display: str
    sizes_gb: list[int]  # available sizes
    max_iops: int
    monthly_per_gb: float


DISK_OPTIONS = [
    AzureDiskOption("StandardSSD_LRS", "Standard SSD",  [32, 64, 128, 256, 512, 1024, 2048, 4096], 500,  0.04),
    AzureDiskOption("Premium_SSD_LRS", "Premium SSD",   [32, 64, 128, 256, 512, 1024, 2048, 4096], 7500, 0.10),
    AzureDiskOption("StandardHDD_LRS", "Standard HDD",  [32, 64, 128, 256, 512, 1024, 2048, 4096], 500,  0.02),
]


# ---------------------------------------------------------------------------
# Recommendation result
# ---------------------------------------------------------------------------

@dataclass
class AzureRecommendation:
    vm_name: str = ""
    recommended_vm_sku: str = ""
    recommended_vm_family: str = ""
    recommended_disk_type: str = ""
    recommended_disk_size_gb: int = 0
    estimated_monthly_cost_usd: float = 0.0
    migration_readiness: str = "Unknown"
    migration_issues: list[str] = field(default_factory=list)
    target_region: str = "eastus"
    confidence_score: float = 0.0         # 0–100
    right_sizing_note: str = ""
    on_prem_cpu_usage_percent: float = 0.0
    on_prem_memory_usage_percent: float = 0.0


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------

def _recommend_vm_sku(vm: DiscoveredVM) -> tuple[AzureVMSku | None, str]:
    """Find the smallest Azure VM SKU that fits the VM's requirements."""
    required_cpus = vm.num_cpus
    required_memory_gb = vm.memory_mb / 1024
    required_disks = len(vm.disks)

    # Right-sizing: if perf data shows low utilization, consider downsizing
    note = ""
    if vm.perf.cpu_usage_percent > 0 and vm.perf.cpu_usage_percent < 30:
        # VM is underutilized — recommend fewer vCPUs
        effective_cpus = max(1, math.ceil(required_cpus * (vm.perf.cpu_usage_percent / 100) * 2))
        if effective_cpus < required_cpus:
            note = f"Right-sized from {required_cpus} → {effective_cpus} vCPUs (avg usage {vm.perf.cpu_usage_percent:.0f}%)"
            required_cpus = effective_cpus

    if vm.perf.memory_usage_percent > 0 and vm.perf.memory_usage_percent < 30:
        effective_mem = max(1, math.ceil(required_memory_gb * (vm.perf.memory_usage_percent / 100) * 2))
        if effective_mem < required_memory_gb:
            note += f" | Memory right-sized from {required_memory_gb:.0f} → {effective_mem} GB (avg usage {vm.perf.memory_usage_percent:.0f}%)"
            required_memory_gb = effective_mem

    # Determine preferred family based on workload characteristics
    memory_ratio = required_memory_gb / max(required_cpus, 1)

    # Filter and sort candidates
    candidates = [
        sku for sku in VM_CATALOG
        if sku.vcpus >= required_cpus
        and sku.memory_gb >= required_memory_gb
        and sku.max_data_disks >= required_disks
    ]

    if not candidates:
        return None, note

    # Prefer memory-optimized if high memory ratio, compute-optimized if low
    def score(sku: AzureVMSku) -> float:
        # Prefer smallest adequate SKU by cost
        cost_weight = sku.monthly_cost_usd
        # Penalize over-provisioning
        cpu_waste = (sku.vcpus - required_cpus) * 10
        mem_waste = (sku.memory_gb - required_memory_gb) * 5
        return cost_weight + cpu_waste + mem_waste

    candidates.sort(key=score)
    return candidates[0], note


def _recommend_disk(vm: DiscoveredVM) -> tuple[str, int, float]:
    """Recommend disk type and size for the VM."""
    total_gb = max(vm.total_disk_gb, 32)  # minimum 32 GB

    # Choose disk type based on IOPS needs
    total_iops = vm.perf.disk_iops_read + vm.perf.disk_iops_write
    if total_iops > 500:
        disk_opt = DISK_OPTIONS[1]  # Premium SSD
    else:
        disk_opt = DISK_OPTIONS[0]  # Standard SSD

    # Find smallest disk size that fits
    disk_size = 32
    for size in disk_opt.sizes_gb:
        if size >= total_gb:
            disk_size = size
            break
    else:
        disk_size = disk_opt.sizes_gb[-1]

    monthly_cost = disk_size * disk_opt.monthly_per_gb
    return disk_opt.display, disk_size, monthly_cost


def _assess_readiness(vm: DiscoveredVM) -> tuple[str, list[str]]:
    """Assess migration readiness and identify potential issues."""
    issues: list[str] = []

    # Check power state
    if vm.power_state != PowerState.POWERED_ON:
        issues.append(f"VM is {vm.power_state.value} — cannot assess running workload")

    # Check VMware Tools
    if vm.tools_status and "notRunning" in vm.tools_status:
        issues.append("VMware Tools not running — guest OS details may be incomplete")

    # Check for unsupported OS
    guest_lower = vm.guest_os.lower()
    if any(term in guest_lower for term in ["solaris", "freebsd", "aix", "hp-ux"]):
        issues.append(f"OS '{vm.guest_os}' is not natively supported on Azure")
        return "Not Ready", issues

    # Check disk count
    if len(vm.disks) > 32:
        issues.append(f"VM has {len(vm.disks)} disks — exceeds Azure max data disks for most SKUs")

    # Check memory size
    if vm.memory_mb > 256 * 1024:
        issues.append(f"VM has {vm.memory_mb / 1024:.0f} GB RAM — may need M-series constrained SKU")

    # Check for very large disks
    for disk in vm.disks:
        if disk.capacity_gb > 4096:
            issues.append(f"Disk '{disk.label}' is {disk.capacity_gb:.0f} GB — exceeds max managed disk size")

    if not issues:
        return "Ready", []
    elif any("Not Ready" in i or "not natively supported" in i or "exceeds" in i for i in issues):
        return "Ready with conditions", issues
    else:
        return "Ready with conditions", issues


def generate_recommendations(env: DiscoveredEnvironment, target_region: str = "eastus") -> list[AzureRecommendation]:
    """Generate Azure migration recommendations for all discovered VMs."""
    recommendations: list[AzureRecommendation] = []

    for vm in env.vms:
        sku, right_size_note = _recommend_vm_sku(vm)
        disk_type, disk_size, disk_cost = _recommend_disk(vm)
        readiness, issues = _assess_readiness(vm)

        vm_cost = sku.monthly_cost_usd if sku else 0.0
        total_cost = vm_cost + disk_cost

        # Confidence score based on data quality
        confidence = 50.0  # base
        if vm.power_state == PowerState.POWERED_ON:
            confidence += 20
        if vm.perf.cpu_usage_percent > 0:
            confidence += 15
        if vm.perf.memory_usage_percent > 0:
            confidence += 15

        rec = AzureRecommendation(
            vm_name=vm.name,
            recommended_vm_sku=sku.name if sku else "Manual assessment needed",
            recommended_vm_family=sku.family if sku else "",
            recommended_disk_type=disk_type,
            recommended_disk_size_gb=disk_size,
            estimated_monthly_cost_usd=round(total_cost, 2),
            migration_readiness=readiness,
            migration_issues=issues,
            target_region=target_region,
            confidence_score=confidence,
            right_sizing_note=right_size_note,
            on_prem_cpu_usage_percent=vm.perf.cpu_usage_percent,
            on_prem_memory_usage_percent=vm.perf.memory_usage_percent,
        )
        recommendations.append(rec)

    logger.info("Generated recommendations for %d VM(s)", len(recommendations))
    return recommendations
