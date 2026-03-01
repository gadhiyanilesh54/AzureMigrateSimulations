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


# Representative SKU catalog — covers all major families
# Prices are approximate East US PAYG; live pricing via Azure Retail Prices API
# is attempted at both initial assessment and simulation time.
VM_CATALOG: list[AzureVMSku] = [
    # ── B-series (burstable, dev/test, low-traffic workloads) ──
    AzureVMSku("Standard_B1s",   "B", 1,   1,    2,    320,     7.59),
    AzureVMSku("Standard_B1ms",  "B", 1,   2,    2,    640,    15.18),
    AzureVMSku("Standard_B2s",   "B", 2,   4,    4,   1280,    30.37),
    AzureVMSku("Standard_B2ms",  "B", 2,   8,    4,   2880,    60.74),
    AzureVMSku("Standard_B4ms",  "B", 4,  16,    8,   5760,   121.47),
    AzureVMSku("Standard_B8ms",  "B", 8,  32,   16,  11520,   242.94),
    AzureVMSku("Standard_B12ms", "B", 12, 48,   16,  17280,   364.42),
    AzureVMSku("Standard_B16ms", "B", 16, 64,   32,  23040,   485.89),
    AzureVMSku("Standard_B20ms", "B", 20, 80,   32,  28800,   607.36),

    # ── D-series v5 (general purpose) ──
    AzureVMSku("Standard_D2s_v5",  "Dsv5",  2,    8,   4,   3750,    70.08),
    AzureVMSku("Standard_D4s_v5",  "Dsv5",  4,   16,   8,   6400,   140.16),
    AzureVMSku("Standard_D8s_v5",  "Dsv5",  8,   32,  16,  12800,   280.32),
    AzureVMSku("Standard_D16s_v5", "Dsv5", 16,   64,  32,  25600,   560.64),
    AzureVMSku("Standard_D32s_v5", "Dsv5", 32,  128,  32,  51200,  1121.28),
    AzureVMSku("Standard_D48s_v5", "Dsv5", 48,  192,  32,  76800,  1681.92),
    AzureVMSku("Standard_D64s_v5", "Dsv5", 64,  256,  32, 102400,  2242.56),
    AzureVMSku("Standard_D96s_v5", "Dsv5", 96,  384,  32, 153600,  3363.84),

    # ── D-series v6 (latest gen general purpose) ──
    AzureVMSku("Standard_D2s_v6",  "Dsv6",  2,    8,   4,   3750,    66.58),
    AzureVMSku("Standard_D4s_v6",  "Dsv6",  4,   16,   8,   6400,   133.15),
    AzureVMSku("Standard_D8s_v6",  "Dsv6",  8,   32,  16,  12800,   266.30),
    AzureVMSku("Standard_D16s_v6", "Dsv6", 16,   64,  32,  25600,   532.61),
    AzureVMSku("Standard_D32s_v6", "Dsv6", 32,  128,  32,  51200,  1065.22),
    AzureVMSku("Standard_D48s_v6", "Dsv6", 48,  192,  32,  76800,  1597.82),
    AzureVMSku("Standard_D64s_v6", "Dsv6", 64,  256,  32, 102400,  2130.43),
    AzureVMSku("Standard_D96s_v6", "Dsv6", 96,  384,  32, 153600,  3195.65),

    # ── E-series v5 (memory optimized) ──
    AzureVMSku("Standard_E2s_v5",   "Esv5",   2,   16,   4,   3750,    91.98),
    AzureVMSku("Standard_E4s_v5",   "Esv5",   4,   32,   8,   6400,   183.96),
    AzureVMSku("Standard_E8s_v5",   "Esv5",   8,   64,  16,  12800,   367.92),
    AzureVMSku("Standard_E16s_v5",  "Esv5",  16,  128,  32,  25600,   735.84),
    AzureVMSku("Standard_E32s_v5",  "Esv5",  32,  256,  32,  51200,  1471.68),
    AzureVMSku("Standard_E48s_v5",  "Esv5",  48,  384,  32,  76800,  2207.52),
    AzureVMSku("Standard_E64s_v5",  "Esv5",  64,  512,  32, 102400,  2943.36),
    AzureVMSku("Standard_E96s_v5",  "Esv5",  96,  672,  32, 153600,  4415.04),
    AzureVMSku("Standard_E104is_v5","Esv5", 104,  672,  64, 160000,  5379.60),

    # ── E-series v6 (latest gen memory optimized) ──
    AzureVMSku("Standard_E2s_v6",  "Esv6",  2,   16,   4,   3750,    87.38),
    AzureVMSku("Standard_E4s_v6",  "Esv6",  4,   32,   8,   6400,   174.76),
    AzureVMSku("Standard_E8s_v6",  "Esv6",  8,   64,  16,  12800,   349.52),
    AzureVMSku("Standard_E16s_v6", "Esv6", 16,  128,  32,  25600,   699.05),
    AzureVMSku("Standard_E32s_v6", "Esv6", 32,  256,  32,  51200,  1398.10),
    AzureVMSku("Standard_E64s_v6", "Esv6", 64,  512,  32, 102400,  2796.19),
    AzureVMSku("Standard_E96s_v6", "Esv6", 96,  672,  32, 153600,  4194.29),

    # ── F-series v2 (compute optimized) ──
    AzureVMSku("Standard_F2s_v2",  "Fsv2",  2,   4,   4,   3200,    61.32),
    AzureVMSku("Standard_F4s_v2",  "Fsv2",  4,   8,   8,   6400,   122.64),
    AzureVMSku("Standard_F8s_v2",  "Fsv2",  8,  16,  16,  12800,   245.28),
    AzureVMSku("Standard_F16s_v2", "Fsv2", 16,  32,  32,  25600,   490.56),
    AzureVMSku("Standard_F32s_v2", "Fsv2", 32,  64,  32,  51200,   981.12),
    AzureVMSku("Standard_F48s_v2", "Fsv2", 48,  96,  32,  76800,  1471.68),
    AzureVMSku("Standard_F64s_v2", "Fsv2", 64, 128,  32, 102400,  1962.24),
    AzureVMSku("Standard_F72s_v2", "Fsv2", 72, 144,  32, 115200,  2207.52),

    # ── M-series (memory-intensive: SAP HANA, large databases) ──
    AzureVMSku("Standard_M8ms",    "Msv2",   8,  218.75, 8,   10000,   1313.47),
    AzureVMSku("Standard_M16ms",   "Msv2",  16,  437.5, 16,   20000,   2626.94),
    AzureVMSku("Standard_M32ms",   "Msv2",  32,  875,   32,   40000,   5253.89),
    AzureVMSku("Standard_M32ts",   "Msv2",  32,  192,   32,   40000,   2482.56),
    AzureVMSku("Standard_M64s",    "Msv2",  64, 1024,   64,   80000,   5472.48),
    AzureVMSku("Standard_M64ms",   "Msv2",  64, 1792,   64,   80000,  10507.78),
    AzureVMSku("Standard_M128s",   "Msv2", 128, 2048,   64,  160000,  10944.96),
    AzureVMSku("Standard_M128ms",  "Msv2", 128, 3892,   64,  160000,  21015.55),

    # ── L-series v3 (storage optimized: big data, data warehouses) ──
    AzureVMSku("Standard_L8s_v3",  "Lsv3",  8,   64,  16,   25600,   500.04),
    AzureVMSku("Standard_L16s_v3", "Lsv3", 16,  128,  32,   51200,  1000.08),
    AzureVMSku("Standard_L32s_v3", "Lsv3", 32,  256,  32,  102400,  2000.16),
    AzureVMSku("Standard_L48s_v3", "Lsv3", 48,  384,  32,  153600,  3000.24),
    AzureVMSku("Standard_L64s_v3", "Lsv3", 64,  512,  32,  204800,  4000.32),
    AzureVMSku("Standard_L80s_v3", "Lsv3", 80,  640,  32,  256000,  5000.40),

    # ── N-series (GPU: AI/ML, rendering, HPC) ──
    AzureVMSku("Standard_NC4as_T4_v3",  "NCasT4v3",  4,   28,   8,   6400,   394.47, gpu=True),
    AzureVMSku("Standard_NC8as_T4_v3",  "NCasT4v3",  8,   56,  16,  12800,   788.94, gpu=True),
    AzureVMSku("Standard_NC16as_T4_v3", "NCasT4v3", 16,  110,  32,  25600,  1177.42, gpu=True),
    AzureVMSku("Standard_NC64as_T4_v3", "NCasT4v3", 64,  440,  32, 102400,  3149.76, gpu=True),
    AzureVMSku("Standard_NC6s_v3",      "NCsv3",     6,  112,  12,  20000,  2190.24, gpu=True),
    AzureVMSku("Standard_NC12s_v3",     "NCsv3",    12,  224,  24,  40000,  4380.48, gpu=True),
    AzureVMSku("Standard_NC24s_v3",     "NCsv3",    24,  448,  32,  80000,  8760.96, gpu=True),
    AzureVMSku("Standard_NV6ads_A10_v5","NVadsA10v5", 6,   55,   4,   6000,   408.80, gpu=True),
    AzureVMSku("Standard_NV12ads_A10_v5","NVadsA10v5",12, 110,   4,  12000,   817.60, gpu=True),
    AzureVMSku("Standard_NV36ads_A10_v5","NVadsA10v5",36, 440,  32,  80000,  2860.80, gpu=True),

    # ── A-series v2 (economical general purpose) ──
    AzureVMSku("Standard_A2_v2",  "Av2",  2,   4,  4,   3200,    60.59),
    AzureVMSku("Standard_A4_v2",  "Av2",  4,   8,  8,   6400,   127.02),
    AzureVMSku("Standard_A8_v2",  "Av2",  8,  16, 16,  12800,   266.45),

    # ── A-series v2 memory-optimized ──
    AzureVMSku("Standard_A2m_v2", "Av2",  2,  16,  4,   3200,    88.33),
    AzureVMSku("Standard_A4m_v2", "Av2",  4,  32,  8,   6400,   185.06),
    AzureVMSku("Standard_A8m_v2", "Av2",  8,  64, 16,  12800,   388.26),

    # ── HB/HC-series (HPC) ──
    AzureVMSku("Standard_HB120rs_v3", "HBv3", 120, 448, 32, 350000, 2628.00),

    # ── DC-series v2 (confidential computing) ──
    AzureVMSku("Standard_DC2s_v2",  "DCsv2",  2,   8,  4,   3200,   146.00),
    AzureVMSku("Standard_DC4s_v2",  "DCsv2",  4,  16,  8,   6400,   292.00),
    AzureVMSku("Standard_DC8s_v2",  "DCsv2",  8,  32, 16,  12800,   584.00),
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
    AzureDiskOption("StandardHDD_LRS", "Standard HDD",  [32, 64, 128, 256, 512, 1024, 2048, 4096],    500, 0.02),
    AzureDiskOption("StandardSSD_LRS", "Standard SSD",  [32, 64, 128, 256, 512, 1024, 2048, 4096],   6000, 0.04),
    AzureDiskOption("Premium_SSD_LRS", "Premium SSD",   [32, 64, 128, 256, 512, 1024, 2048, 4096],  20000, 0.10),
    AzureDiskOption("PremiumV2_LRS",   "Premium SSD v2", [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768], 80000, 0.12),
    AzureDiskOption("UltraSSD_LRS",    "Ultra SSD",      [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536], 160000, 0.15),
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
# Right-sizing configuration (can be tuned via config or whatif overrides)
# ---------------------------------------------------------------------------

RIGHT_SIZING_CONFIG = {
    "downsize_cpu_threshold": 40,       # % — downsize if avg CPU below this
    "downsize_mem_threshold": 40,       # % — downsize if avg memory below this
    "upsize_cpu_threshold": 80,         # % — upsize if avg CPU above this
    "upsize_mem_threshold": 85,         # % — upsize if avg memory above this
    "downsize_headroom_factor": 1.5,    # keep 1.5× observed peak after downsize
    "upsize_headroom_factor": 1.3,      # add 30% headroom above observed peak
    "min_vcpus": 1,
    "min_memory_gb": 1,
}


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------

def _recommend_vm_sku(vm: DiscoveredVM) -> tuple[AzureVMSku | None, str]:
    """Find the smallest Azure VM SKU that fits the VM's requirements.

    Performs bidirectional right-sizing:
    - Downsize when utilization is consistently LOW (below downsize threshold)
    - Upsize when utilization is consistently HIGH (above upsize threshold)
    This avoids both over- and under-provisioning.
    """
    cfg = RIGHT_SIZING_CONFIG
    required_cpus = vm.num_cpus
    required_memory_gb = vm.memory_mb / 1024
    required_disks = len(vm.disks)

    note = ""

    # ---- Right-sizing: CPU --------------------------------------------------
    cpu_pct = vm.perf.cpu_usage_percent
    if cpu_pct > 0:
        if cpu_pct < cfg["downsize_cpu_threshold"]:
            # Under-utilised → downsize with headroom
            effective_cpus = max(
                cfg["min_vcpus"],
                math.ceil(required_cpus * (cpu_pct / 100) * cfg["downsize_headroom_factor"]),
            )
            if effective_cpus < required_cpus:
                note = (f"CPU downsized {required_cpus} → {effective_cpus} vCPUs "
                        f"(avg {cpu_pct:.0f}%, threshold <{cfg['downsize_cpu_threshold']}%)")
                required_cpus = effective_cpus
        elif cpu_pct > cfg["upsize_cpu_threshold"]:
            # Saturated → upsize with headroom
            effective_cpus = math.ceil(required_cpus * (cpu_pct / 100) * cfg["upsize_headroom_factor"])
            if effective_cpus > required_cpus:
                note = (f"CPU upsized {required_cpus} → {effective_cpus} vCPUs "
                        f"(avg {cpu_pct:.0f}%, threshold >{cfg['upsize_cpu_threshold']}%)")
                required_cpus = effective_cpus

    # ---- Right-sizing: Memory -----------------------------------------------
    mem_pct = vm.perf.memory_usage_percent
    if mem_pct > 0:
        if mem_pct < cfg["downsize_mem_threshold"]:
            effective_mem = max(
                cfg["min_memory_gb"],
                math.ceil(required_memory_gb * (mem_pct / 100) * cfg["downsize_headroom_factor"]),
            )
            if effective_mem < required_memory_gb:
                sep = " | " if note else ""
                note += (f"{sep}Memory downsized {required_memory_gb:.0f} → {effective_mem} GB "
                         f"(avg {mem_pct:.0f}%, threshold <{cfg['downsize_mem_threshold']}%)")
                required_memory_gb = effective_mem
        elif mem_pct > cfg["upsize_mem_threshold"]:
            effective_mem = math.ceil(required_memory_gb * (mem_pct / 100) * cfg["upsize_headroom_factor"])
            if effective_mem > required_memory_gb:
                sep = " | " if note else ""
                note += (f"{sep}Memory upsized {required_memory_gb:.0f} → {effective_mem} GB "
                         f"(avg {mem_pct:.0f}%, threshold >{cfg['upsize_mem_threshold']}%)")
                required_memory_gb = effective_mem

    # ---- Determine preferred family based on workload characteristics -------
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
    """Recommend disk type and size for the VM based on IOPS and throughput."""
    total_gb = max(vm.total_disk_gb, 32)  # minimum 32 GB

    # Choose disk type based on IOPS needs (ordered by capability)
    total_iops = vm.perf.disk_iops_read + vm.perf.disk_iops_write
    total_throughput = vm.perf.disk_read_kbps + vm.perf.disk_write_kbps  # KB/s

    if total_iops > 20000 or total_throughput > 500000:
        disk_opt = DISK_OPTIONS[4]  # Ultra SSD
    elif total_iops > 6000 or total_throughput > 200000:
        disk_opt = DISK_OPTIONS[3]  # Premium SSD v2
    elif total_iops > 500 or total_throughput > 60000:
        disk_opt = DISK_OPTIONS[2]  # Premium SSD
    elif total_iops > 100:
        disk_opt = DISK_OPTIONS[1]  # Standard SSD
    else:
        disk_opt = DISK_OPTIONS[0]  # Standard HDD (for very low IOPS, e.g. archive)

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
    if len(vm.disks) > 64:
        issues.append(f"VM has {len(vm.disks)} disks — exceeds Azure max data disks (64 on largest SKUs)")
    elif len(vm.disks) > 32:
        issues.append(f"VM has {len(vm.disks)} disks — requires a large SKU with 64 data disk support (E104is, M-series)")

    # Check memory size
    if vm.memory_mb > 3892 * 1024:
        issues.append(f"VM has {vm.memory_mb / 1024:.0f} GB RAM — exceeds largest Azure VM SKU (M128ms: 3892 GB)")
    elif vm.memory_mb > 672 * 1024:
        issues.append(f"VM has {vm.memory_mb / 1024:.0f} GB RAM — requires M-series constrained memory SKU")

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
    """Generate Azure migration recommendations for all discovered VMs.

    Attempts to fetch live pricing from Azure Retail Prices API for the
    target region.  Falls back to hardcoded catalog prices when unavailable.
    """
    recommendations: list[AzureRecommendation] = []

    # --- Try to get live pricing for the target region --------------------
    live_prices: dict[str, float] = {}
    pricing_source = "hardcoded"
    try:
        from .azure_pricing import get_default_client
        client = get_default_client()
        if client is not None:
            all_sku_names = [sku.name for sku in VM_CATALOG]
            bulk_prices = client.get_vm_prices(all_sku_names, target_region)
            for sku_name, price_dict in bulk_prices.items():
                payg = price_dict.get("pay_as_you_go")
                if payg:
                    live_prices[sku_name] = payg
            if live_prices:
                pricing_source = "azure_retail_api"
                logger.info("Live pricing fetched for %d SKUs in %s", len(live_prices), target_region)
    except Exception as exc:
        logger.warning("Could not fetch live pricing for initial assessment: %s", exc)

    for vm in env.vms:
        sku, right_size_note = _recommend_vm_sku(vm)
        disk_type, disk_size, disk_cost = _recommend_disk(vm)
        readiness, issues = _assess_readiness(vm)

        # Use live price if available, else catalog price
        if sku:
            vm_cost = live_prices.get(sku.name, sku.monthly_cost_usd)
        else:
            vm_cost = 0.0
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
