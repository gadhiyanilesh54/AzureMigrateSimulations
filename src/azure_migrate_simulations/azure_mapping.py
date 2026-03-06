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
# Per-disk recommendation
# ---------------------------------------------------------------------------

@dataclass
class DiskRecommendation:
    """Recommendation for a single disk."""
    source_label: str = ""
    is_os_disk: bool = False
    source_capacity_gb: float = 0.0
    recommended_type: str = ""           # Premium SSD, Standard SSD, etc.
    recommended_type_name: str = ""      # Premium_SSD_LRS, etc.
    recommended_size_gb: int = 0
    estimated_monthly_cost_usd: float = 0.0
    source_iops: float = 0.0
    source_throughput_kbps: float = 0.0


# ---------------------------------------------------------------------------
# Pricing breakdown
# ---------------------------------------------------------------------------

@dataclass
class PricingBreakdown:
    """Multi-model pricing for a VM recommendation."""
    vm_payg_monthly: float = 0.0
    vm_1yr_ri_monthly: float = 0.0
    vm_3yr_ri_monthly: float = 0.0
    vm_savings_plan_1yr_monthly: float = 0.0
    vm_savings_plan_3yr_monthly: float = 0.0
    vm_ahub_monthly: float = 0.0             # Azure Hybrid Benefit
    vm_dev_test_monthly: float = 0.0
    disk_total_monthly: float = 0.0
    os_license_monthly: float = 0.0          # Windows license if not AHUB
    backup_monthly: float = 0.0
    monitoring_monthly: float = 0.0          # Defender for Cloud + diagnostics
    networking_monthly: float = 0.0          # estimated bandwidth
    total_payg_monthly: float = 0.0
    total_optimized_monthly: float = 0.0     # best RI/SP + AHUB


# ---------------------------------------------------------------------------
# Recommendation result
# ---------------------------------------------------------------------------

@dataclass
class AzureRecommendation:
    vm_name: str = ""
    recommended_vm_sku: str = ""
    recommended_vm_family: str = ""
    # Legacy single-disk fields (kept for backward compatibility)
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
    # --- New fields ---
    # Per-disk recommendations
    disk_recommendations: list[DiskRecommendation] = field(default_factory=list)
    # Pricing breakdown with RI/SP/AHUB
    pricing: PricingBreakdown = field(default_factory=PricingBreakdown)
    # OS details
    os_type: str = ""                     # "windows" or "linux"
    os_eol_status: str = ""               # "supported", "eol", "eol_esu_eligible"
    os_eol_detail: str = ""               # human-readable detail
    azure_hybrid_benefit_eligible: bool = False
    # Sizing details
    sizing_approach: str = ""             # "as_is", "performance_based_avg", "performance_based_p95"
    perf_data_source: str = ""            # "vcenter_realtime", "vcenter_historical", "perf_history", etc.
    perf_sample_count: int = 0
    on_prem_cpu_p95_percent: float = 0.0
    on_prem_memory_p95_percent: float = 0.0
    # TCO
    total_tco_monthly: float = 0.0
    total_tco_optimized_monthly: float = 0.0


# ---------------------------------------------------------------------------
# OS End-of-Life / Extended Security Updates database
# ---------------------------------------------------------------------------

OS_EOL_DATABASE: dict[str, dict] = {
    # Windows Server
    "windows server 2003":  {"eol": True, "esu_eligible": False, "detail": "Windows Server 2003 — End of Life (Jul 2015), not supported on Azure"},
    "windows server 2008":  {"eol": True, "esu_eligible": True,  "detail": "Windows Server 2008 — End of Life (Jan 2020), free ESUs on Azure for 3 years"},
    "windows server 2008 r2": {"eol": True, "esu_eligible": True, "detail": "Windows Server 2008 R2 — End of Life (Jan 2020), free ESUs on Azure for 3 years"},
    "windows server 2012":  {"eol": True, "esu_eligible": True,  "detail": "Windows Server 2012 — End of Life (Oct 2023), free ESUs on Azure for 3 years"},
    "windows server 2012 r2": {"eol": True, "esu_eligible": True, "detail": "Windows Server 2012 R2 — End of Life (Oct 2023), free ESUs on Azure for 3 years"},
    "windows server 2016":  {"eol": False, "esu_eligible": False, "detail": "Windows Server 2016 — Mainstream support (EOS Jan 2027)"},
    "windows server 2019":  {"eol": False, "esu_eligible": False, "detail": "Windows Server 2019 — Mainstream support"},
    "windows server 2022":  {"eol": False, "esu_eligible": False, "detail": "Windows Server 2022 — Current"},
    "windows server 2025":  {"eol": False, "esu_eligible": False, "detail": "Windows Server 2025 — Current"},
    # Linux
    "centos 6":             {"eol": True, "esu_eligible": False, "detail": "CentOS 6 — End of Life (Nov 2020)"},
    "centos 7":             {"eol": True, "esu_eligible": False, "detail": "CentOS 7 — End of Life (Jun 2024)"},
    "centos 8":             {"eol": True, "esu_eligible": False, "detail": "CentOS 8 — End of Life (Dec 2021), consider migrating to RHEL/AlmaLinux/Rocky"},
    "centos stream 8":      {"eol": True, "esu_eligible": False, "detail": "CentOS Stream 8 — End of Life (May 2024)"},
    "rhel 6":               {"eol": True, "esu_eligible": False, "detail": "RHEL 6 — End of Life (Nov 2020)"},
    "rhel 7":               {"eol": True, "esu_eligible": False, "detail": "RHEL 7 — End of Maintenance (Jun 2024)"},
    "ubuntu 14.04":         {"eol": True, "esu_eligible": False, "detail": "Ubuntu 14.04 — End of Life (Apr 2024 ESM)"},
    "ubuntu 16.04":         {"eol": True, "esu_eligible": False, "detail": "Ubuntu 16.04 — End of Life (Apr 2026 ESM)"},
    "ubuntu 18.04":         {"eol": True, "esu_eligible": False, "detail": "Ubuntu 18.04 — End of Standard Support (Jun 2023), ESM until 2028"},
    "suse 11":              {"eol": True, "esu_eligible": False, "detail": "SLES 11 — End of Life"},
    "suse 12":              {"eol": False, "esu_eligible": False, "detail": "SLES 12 — LTSS available"},
    "debian 9":             {"eol": True, "esu_eligible": False, "detail": "Debian 9 (Stretch) — End of Life (Jun 2022)"},
    "debian 10":            {"eol": True, "esu_eligible": False, "detail": "Debian 10 (Buster) — End of Life (Jun 2024)"},
}


# ---------------------------------------------------------------------------
# Azure region SKU availability (representative subset)
# ---------------------------------------------------------------------------

# SKU families NOT available in certain regions
REGION_SKU_RESTRICTIONS: dict[str, set[str]] = {
    "brazilsouth":   {"Msv2", "NCsv3", "NVadsA10v5", "HBv3", "DCsv2", "Lsv3"},
    "southafricanorth": {"Msv2", "NCsv3", "NVadsA10v5", "HBv3", "DCsv2"},
    "uaenorth":      {"NCsv3", "NVadsA10v5", "HBv3", "DCsv2"},
    "centralindia":  {"Msv2", "HBv3", "DCsv2"},
    "koreacentral":  {"HBv3", "DCsv2"},
    "japanwest":     {"Msv2", "NCsv3", "HBv3", "DCsv2", "Lsv3"},
    "westus":        {"HBv3"},
    "northeurope":   set(),
    "westeurope":    set(),
    "eastus":        set(),
    "eastus2":       set(),
    "westus2":       set(),
    "westus3":       set(),
}


# ---------------------------------------------------------------------------
# Approximate Windows license cost per-vCPU per month (for non-AHUB)
# ---------------------------------------------------------------------------

WINDOWS_LICENSE_COST_PER_VCPU_MONTHLY = 6.50   # ~$0.009/hr per vCPU


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
    # Percentile to use for sizing when historical data is available
    "sizing_percentile": "p95",         # "avg", "p50", "p95", "p99", "max"
}

# Workload-specific overrides: certain workload patterns deserve different thresholds
WORKLOAD_RIGHT_SIZING_OVERRIDES: dict[str, dict] = {
    "database": {
        "downsize_cpu_threshold": 25,   # databases need more headroom
        "downsize_mem_threshold": 20,   # memory is critical for DB caching
        "upsize_headroom_factor": 1.5,
    },
    "web_server": {
        "downsize_cpu_threshold": 50,   # web servers can be more aggressively downsized
        "downsize_mem_threshold": 50,
    },
    "dev_test": {
        "downsize_cpu_threshold": 60,   # dev/test can be very aggressively downsized
        "downsize_mem_threshold": 60,
        "downsize_headroom_factor": 1.2,
    },
}


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Workload detection from VM metadata
# ---------------------------------------------------------------------------

def _detect_workload_type(vm: DiscoveredVM) -> str:
    """Heuristic to detect workload type from VM name, annotation, folder, OS."""
    name_lower = vm.name.lower()
    annotation_lower = (vm.annotation or "").lower()
    folder_lower = (vm.folder or "").lower()
    combined = f"{name_lower} {annotation_lower} {folder_lower}"

    # Database indicators
    if any(kw in combined for kw in ("sql", "mysql", "postgres", "oracle", "mongo", "redis",
                                      "mariadb", "database", "db-", "-db", "cassandra")):
        return "database"

    # Web/app server indicators
    if any(kw in combined for kw in ("web", "iis", "apache", "nginx", "tomcat", "httpd",
                                      "webapp", "frontend", "api-", "-api")):
        return "web_server"

    # Dev/test indicators
    if any(kw in combined for kw in ("dev", "test", "staging", "qa", "sandbox",
                                      "lab", "demo", "temp")):
        return "dev_test"

    return "general"


def _get_right_sizing_config(workload_type: str) -> dict:
    """Get right-sizing config with workload-specific overrides applied."""
    cfg = dict(RIGHT_SIZING_CONFIG)
    overrides = WORKLOAD_RIGHT_SIZING_OVERRIDES.get(workload_type)
    if overrides:
        cfg.update(overrides)
    return cfg


# ---------------------------------------------------------------------------
# OS EOL detection
# ---------------------------------------------------------------------------

def _check_os_eol(vm: DiscoveredVM) -> tuple[str, str, str]:
    """Check if the VM's OS is end-of-life.

    Returns:
        (eol_status, eol_detail, os_type)
        eol_status: "supported", "eol", "eol_esu_eligible"
    """
    guest_os = (vm.guest_os or vm.guest_os_detailed or "").lower()
    os_type = "linux" if vm.guest_os_family == GuestOSFamily.LINUX else \
              "windows" if vm.guest_os_family == GuestOSFamily.WINDOWS else "other"

    for pattern, info in OS_EOL_DATABASE.items():
        if pattern in guest_os:
            if info["eol"]:
                status = "eol_esu_eligible" if info["esu_eligible"] else "eol"
            else:
                status = "supported"
            return status, info["detail"], os_type

    return "supported", "", os_type


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------

def _recommend_vm_sku(vm: DiscoveredVM, target_region: str = "eastus") -> tuple[AzureVMSku | None, str, str]:
    """Find the smallest Azure VM SKU that fits the VM's requirements.

    Uses percentile-based sizing (P95 by default) when historical data is
    available, otherwise falls back to average-based or as-is sizing.

    Returns:
        (best_sku, right_sizing_note, sizing_approach)
    """
    workload_type = _detect_workload_type(vm)
    cfg = _get_right_sizing_config(workload_type)

    required_cpus = vm.num_cpus
    required_memory_gb = vm.memory_mb / 1024
    required_disks = len(vm.disks)

    note = ""
    sizing_approach = "as_is"

    # Determine which CPU/memory metric to use for right-sizing
    perf = vm.perf
    has_percentile_data = perf.cpu_p95_percent > 0 or perf.memory_p95_percent > 0

    if has_percentile_data:
        sizing_pctl = cfg.get("sizing_percentile", "p95")
        if sizing_pctl == "p95":
            cpu_pct = perf.cpu_p95_percent
            mem_pct = perf.memory_p95_percent
        elif sizing_pctl == "p99":
            cpu_pct = perf.cpu_p99_percent
            mem_pct = perf.memory_p99_percent
        elif sizing_pctl == "p50":
            cpu_pct = perf.cpu_p50_percent
            mem_pct = perf.memory_p50_percent
        elif sizing_pctl == "max":
            cpu_pct = perf.cpu_max_percent
            mem_pct = perf.memory_max_percent
        else:
            cpu_pct = perf.cpu_usage_percent
            mem_pct = perf.memory_usage_percent
        sizing_approach = f"performance_based_{sizing_pctl}"
    elif perf.cpu_usage_percent > 0:
        cpu_pct = perf.cpu_usage_percent
        mem_pct = perf.memory_usage_percent
        sizing_approach = "performance_based_avg"
    else:
        cpu_pct = 0
        mem_pct = 0

    # ---- Right-sizing: CPU --------------------------------------------------
    if cpu_pct > 0:
        if cpu_pct < cfg["downsize_cpu_threshold"]:
            effective_cpus = max(
                cfg["min_vcpus"],
                math.ceil(required_cpus * (cpu_pct / 100) * cfg["downsize_headroom_factor"]),
            )
            if effective_cpus < required_cpus:
                note = (f"CPU downsized {required_cpus} → {effective_cpus} vCPUs "
                        f"({sizing_approach}: {cpu_pct:.0f}%, threshold <{cfg['downsize_cpu_threshold']}%)")
                required_cpus = effective_cpus
        elif cpu_pct > cfg["upsize_cpu_threshold"]:
            effective_cpus = math.ceil(required_cpus * (cpu_pct / 100) * cfg["upsize_headroom_factor"])
            if effective_cpus > required_cpus:
                note = (f"CPU upsized {required_cpus} → {effective_cpus} vCPUs "
                        f"({sizing_approach}: {cpu_pct:.0f}%, threshold >{cfg['upsize_cpu_threshold']}%)")
                required_cpus = effective_cpus

    # ---- Right-sizing: Memory -----------------------------------------------
    if mem_pct > 0:
        if mem_pct < cfg["downsize_mem_threshold"]:
            effective_mem = max(
                cfg["min_memory_gb"],
                math.ceil(required_memory_gb * (mem_pct / 100) * cfg["downsize_headroom_factor"]),
            )
            if effective_mem < required_memory_gb:
                sep = " | " if note else ""
                note += (f"{sep}Memory downsized {required_memory_gb:.0f} → {effective_mem} GB "
                         f"({sizing_approach}: {mem_pct:.0f}%, threshold <{cfg['downsize_mem_threshold']}%)")
                required_memory_gb = effective_mem
        elif mem_pct > cfg["upsize_mem_threshold"]:
            effective_mem = math.ceil(required_memory_gb * (mem_pct / 100) * cfg["upsize_headroom_factor"])
            if effective_mem > required_memory_gb:
                sep = " | " if note else ""
                note += (f"{sep}Memory upsized {required_memory_gb:.0f} → {effective_mem} GB "
                         f"({sizing_approach}: {mem_pct:.0f}%, threshold >{cfg['upsize_mem_threshold']}%)")
                required_memory_gb = effective_mem

    # ---- Determine preferred family based on workload characteristics -------
    memory_ratio = required_memory_gb / max(required_cpus, 1)

    # ---- Region SKU availability filter -------------------------------------
    restricted_families = REGION_SKU_RESTRICTIONS.get(target_region, set())

    # Filter and sort candidates
    candidates = [
        sku for sku in VM_CATALOG
        if sku.vcpus >= required_cpus
        and sku.memory_gb >= required_memory_gb
        and sku.max_data_disks >= required_disks
        and sku.family not in restricted_families
    ]

    if not candidates:
        return None, note, sizing_approach

    # Prefer smallest adequate SKU by cost
    def score(sku: AzureVMSku) -> float:
        cost_weight = sku.monthly_cost_usd
        cpu_waste = (sku.vcpus - required_cpus) * 10
        mem_waste = (sku.memory_gb - required_memory_gb) * 5
        return cost_weight + cpu_waste + mem_waste

    candidates.sort(key=score)
    return candidates[0], note, sizing_approach


def _recommend_disk_per_disk(vm: DiscoveredVM) -> list[DiskRecommendation]:
    """Generate per-disk Azure disk recommendations."""
    recs: list[DiskRecommendation] = []

    if not vm.disks:
        # Fallback: create a single minimal recommendation
        recs.append(DiskRecommendation(
            source_label="(no disks)",
            is_os_disk=True,
            source_capacity_gb=32,
            recommended_type="Premium SSD",
            recommended_type_name="Premium_SSD_LRS",
            recommended_size_gb=32,
            estimated_monthly_cost_usd=32 * 0.10,
        ))
        return recs

    for disk in vm.disks:
        capacity_gb = max(disk.capacity_gb, 32)  # Azure minimum 32 GB

        # Determine disk IOPS needs
        disk_iops = disk.iops_read + disk.iops_write
        disk_throughput = disk.throughput_read_kbps + disk.throughput_write_kbps

        # If per-disk perf is zero, distribute VM-level IOPS across disks
        if disk_iops == 0 and len(vm.disks) > 0:
            total_iops = vm.perf.disk_iops_read + vm.perf.disk_iops_write
            # Weight by capacity
            total_capacity = sum(d.capacity_gb for d in vm.disks) or 1
            weight = disk.capacity_gb / total_capacity
            disk_iops = total_iops * weight
            disk_throughput = (vm.perf.disk_read_kbps + vm.perf.disk_write_kbps) * weight

        # OS disk should generally be Premium SSD for consistent performance
        if disk.is_boot_disk:
            if disk_iops > 20000:
                disk_opt = DISK_OPTIONS[3]  # Premium SSD v2
            elif disk_iops > 500 or disk.is_boot_disk:
                disk_opt = DISK_OPTIONS[2]  # Premium SSD (recommended for OS)
            else:
                disk_opt = DISK_OPTIONS[2]  # Still Premium SSD for OS
        else:
            # Data disks — match to actual IOPS needs
            if disk_iops > 20000 or disk_throughput > 500000:
                disk_opt = DISK_OPTIONS[4]  # Ultra SSD
            elif disk_iops > 6000 or disk_throughput > 200000:
                disk_opt = DISK_OPTIONS[3]  # Premium SSD v2
            elif disk_iops > 500 or disk_throughput > 60000:
                disk_opt = DISK_OPTIONS[2]  # Premium SSD
            elif disk_iops > 100:
                disk_opt = DISK_OPTIONS[1]  # Standard SSD
            else:
                disk_opt = DISK_OPTIONS[1]  # Standard SSD (avoid HDD for most workloads)

        # Find smallest disk size that fits
        disk_size = 32
        for size in disk_opt.sizes_gb:
            if size >= capacity_gb:
                disk_size = size
                break
        else:
            disk_size = disk_opt.sizes_gb[-1]

        monthly_cost = disk_size * disk_opt.monthly_per_gb

        recs.append(DiskRecommendation(
            source_label=disk.label,
            is_os_disk=disk.is_boot_disk,
            source_capacity_gb=disk.capacity_gb,
            recommended_type=disk_opt.display,
            recommended_type_name=disk_opt.type_name,
            recommended_size_gb=disk_size,
            estimated_monthly_cost_usd=round(monthly_cost, 2),
            source_iops=round(disk_iops, 1),
            source_throughput_kbps=round(disk_throughput, 1),
        ))

    return recs


def _recommend_disk(vm: DiscoveredVM) -> tuple[str, int, float]:
    """Legacy: recommend single disk type and size for backward compatibility."""
    disk_recs = _recommend_disk_per_disk(vm)
    if not disk_recs:
        return "Standard SSD", 32, 32 * 0.04
    # Use the "most performant" recommendation as the summary
    best = max(disk_recs, key=lambda d: d.estimated_monthly_cost_usd)
    total_cost = sum(d.estimated_monthly_cost_usd for d in disk_recs)
    total_size = sum(d.recommended_size_gb for d in disk_recs)
    return best.recommended_type, total_size, total_cost


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

    # Check for snapshots (must consolidate before migration)
    if vm.has_snapshots:
        issues.append(f"VM has {vm.snapshot_count} snapshot(s) ({vm.snapshot_size_gb:.1f} GB) — consolidate before migration")

    # Check for linked clones
    if vm.has_linked_clones:
        issues.append("VM uses linked clones — must be consolidated to a full disk before migration")

    # Check disk controller type (IDE may need attention)
    ide_disks = [d for d in vm.disks if d.controller_type == "ide"]
    if ide_disks:
        issues.append(f"{len(ide_disks)} disk(s) on IDE controller — may need conversion to SCSI for Azure")

    # Check boot type for Gen2 compatibility
    if vm.boot_type == "bios":
        issues.append("VM uses BIOS boot — Azure Gen2 VMs require UEFI. Consider Gen1 VM or BIOS→UEFI conversion")

    # Check hardware version
    if vm.hardware_version:
        try:
            version_num = int(vm.hardware_version.replace("vmx-", ""))
            if version_num < 9:
                issues.append(f"Hardware version {vm.hardware_version} is very old — upgrade before migration")
        except (ValueError, AttributeError):
            pass

    # Check OS end-of-life
    eol_status, eol_detail, _ = _check_os_eol(vm)
    if eol_status == "eol":
        issues.append(f"OS is End of Life: {eol_detail}")
    elif eol_status == "eol_esu_eligible":
        issues.append(f"OS is End of Life but eligible for free ESUs on Azure: {eol_detail}")

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
        if disk.capacity_gb > 32767:
            issues.append(f"Disk '{disk.label}' is {disk.capacity_gb:.0f} GB — exceeds max managed disk size (32 TiB)")
        elif disk.capacity_gb > 4096 and disk.is_boot_disk:
            issues.append(f"OS disk '{disk.label}' is {disk.capacity_gb:.0f} GB — OS disk max is 4 TiB")

    # Check independent persistent disks (can't be migrated with VM)
    independent_disks = [d for d in vm.disks if "independent" in (d.disk_mode or "").lower()]
    if independent_disks:
        issues.append(f"{len(independent_disks)} disk(s) in independent mode — require separate migration handling")

    # CPU reservation/limit warnings
    if vm.cpu_reservation_mhz > 0:
        issues.append(f"CPU reservation of {vm.cpu_reservation_mhz} MHz — Azure doesn't support CPU reservations, ensure SKU provides adequate compute")
    if vm.cpu_limit_mhz > 0 and vm.cpu_limit_mhz != -1:
        issues.append(f"CPU limit of {vm.cpu_limit_mhz} MHz — Azure doesn't support CPU limits")

    if not issues:
        return "Ready", []
    elif any("Not Ready" in i or "not natively supported" in i or "exceeds" in i for i in issues):
        return "Ready with conditions", issues
    else:
        return "Ready with conditions", issues


def _calculate_confidence(vm: DiscoveredVM, sizing_approach: str) -> float:
    """Calculate confidence score based on data quality and completeness."""
    score = 0.0

    # Power state (20 pts)
    if vm.power_state == PowerState.POWERED_ON:
        score += 20.0

    # Performance data quality (40 pts)
    perf = vm.perf
    if perf.perf_data_source == "vcenter_historical" and perf.sample_count > 100:
        score += 40.0  # Full historical data
    elif perf.perf_data_source == "perf_history" and perf.sample_count > 50:
        score += 35.0  # Perf history file data
    elif perf.perf_data_source == "enrichment":
        score += 30.0  # Enrichment data
    elif perf.cpu_usage_percent > 0 and perf.memory_usage_percent > 0:
        score += 15.0  # Basic real-time data
    elif perf.cpu_usage_percent > 0 or perf.memory_usage_percent > 0:
        score += 8.0   # Partial data

    # Collection duration (15 pts)
    if perf.collection_period_days >= 30:
        score += 15.0
    elif perf.collection_period_days >= 7:
        score += 10.0
    elif perf.collection_period_days >= 1:
        score += 5.0

    # Percentile data available (10 pts)
    if perf.cpu_p95_percent > 0 and perf.memory_p95_percent > 0:
        score += 10.0
    elif perf.cpu_p95_percent > 0 or perf.memory_p95_percent > 0:
        score += 5.0

    # Disk IOPS data (5 pts)
    if perf.disk_iops_read > 0 or perf.disk_iops_write > 0:
        score += 5.0

    # VMware Tools running (5 pts)
    if vm.tools_status and "Running" in vm.tools_status:
        score += 5.0

    # Guest OS identified (5 pts)
    if vm.guest_os and vm.guest_os_family != GuestOSFamily.OTHER:
        score += 5.0

    return min(score, 100.0)


def generate_recommendations(env: DiscoveredEnvironment, target_region: str = "eastus") -> list[AzureRecommendation]:
    """Generate Azure migration recommendations for all discovered VMs.

    Includes:
    - Percentile-based right-sizing (P95 when available)
    - Per-disk recommendations
    - Windows vs Linux pricing with Azure Hybrid Benefit
    - RI / Savings Plan / Dev-Test pricing models
    - OS end-of-life detection
    - Workload-aware right-sizing thresholds
    - Enhanced confidence scoring
    - Region SKU availability validation
    - TCO cost components (backup, monitoring, networking)
    """
    recommendations: list[AzureRecommendation] = []

    # --- Try to get live pricing for the target region --------------------
    live_prices: dict[str, dict[str, float]] = {}
    pricing_source = "hardcoded"
    try:
        from .azure_pricing import get_default_client
        client = get_default_client()
        if client is not None:
            all_sku_names = [sku.name for sku in VM_CATALOG]
            bulk_prices = client.get_vm_prices(all_sku_names, target_region)
            for sku_name, price_dict in bulk_prices.items():
                if price_dict:
                    live_prices[sku_name] = price_dict
            if live_prices:
                pricing_source = "azure_retail_api"
                logger.info("Live pricing fetched for %d SKUs in %s", len(live_prices), target_region)
    except Exception as exc:
        logger.warning("Could not fetch live pricing for initial assessment: %s", exc)

    for vm in env.vms:
        sku, right_size_note, sizing_approach = _recommend_vm_sku(vm, target_region)
        disk_recs = _recommend_disk_per_disk(vm)
        readiness, issues = _assess_readiness(vm)
        eol_status, eol_detail, os_type = _check_os_eol(vm)

        # --- Pricing breakdown -------------------------------------------
        pricing = PricingBreakdown()

        # VM compute cost
        if sku:
            sku_prices = live_prices.get(sku.name, {})
            pricing.vm_payg_monthly = sku_prices.get("pay_as_you_go", sku.monthly_cost_usd)
            pricing.vm_1yr_ri_monthly = sku_prices.get("1_year_ri", pricing.vm_payg_monthly * 0.63)
            pricing.vm_3yr_ri_monthly = sku_prices.get("3_year_ri", pricing.vm_payg_monthly * 0.40)
            pricing.vm_savings_plan_1yr_monthly = sku_prices.get("savings_plan_1yr", pricing.vm_1yr_ri_monthly * 1.05)
            pricing.vm_savings_plan_3yr_monthly = sku_prices.get("savings_plan_3yr", pricing.vm_3yr_ri_monthly * 1.12)
            pricing.vm_dev_test_monthly = sku_prices.get("dev_test", pricing.vm_payg_monthly * 0.55)

        # Disk costs (sum of all per-disk recommendations)
        pricing.disk_total_monthly = round(sum(d.estimated_monthly_cost_usd for d in disk_recs), 2)

        # Windows licensing
        is_windows = (os_type == "windows" or vm.guest_os_family == GuestOSFamily.WINDOWS)
        ahub_eligible = is_windows  # Customers with Software Assurance
        if is_windows and sku:
            pricing.os_license_monthly = round(sku.vcpus * WINDOWS_LICENSE_COST_PER_VCPU_MONTHLY, 2)
            pricing.vm_ahub_monthly = pricing.vm_payg_monthly  # AHUB = no Windows surcharge
        else:
            pricing.vm_ahub_monthly = pricing.vm_payg_monthly

        # TCO components
        if sku:
            # Azure Backup (estimated: ~$5/instance + $0.01/GB/month for data)
            total_disk_gb = sum(d.recommended_size_gb for d in disk_recs)
            pricing.backup_monthly = round(5.0 + total_disk_gb * 0.01, 2)
            # Azure Monitor / Defender for Cloud basic (~$5/server/month)
            pricing.monitoring_monthly = 5.0
            # Networking (~$0.087/GB egress, estimate 50GB/month for avg VM)
            pricing.networking_monthly = round(50 * 0.087, 2)

        # Total PAYG (compute + Windows license if applicable + disks + TCO)
        vm_base_payg = pricing.vm_payg_monthly
        if is_windows:
            vm_base_payg += pricing.os_license_monthly
        pricing.total_payg_monthly = round(
            vm_base_payg + pricing.disk_total_monthly +
            pricing.backup_monthly + pricing.monitoring_monthly + pricing.networking_monthly,
            2
        )

        # Total optimized: best of RI/SP + AHUB (no Windows surcharge) + disks + TCO
        best_compute = min(
            pricing.vm_3yr_ri_monthly,
            pricing.vm_savings_plan_3yr_monthly,
        ) if sku else 0
        pricing.total_optimized_monthly = round(
            best_compute + pricing.disk_total_monthly +
            pricing.backup_monthly + pricing.monitoring_monthly + pricing.networking_monthly,
            2
        )

        # Legacy single-disk summary
        if disk_recs:
            legacy_disk_type = max(disk_recs, key=lambda d: d.estimated_monthly_cost_usd).recommended_type
            legacy_disk_size = sum(d.recommended_size_gb for d in disk_recs)
        else:
            legacy_disk_type = "Standard SSD"
            legacy_disk_size = 32

        # Confidence score
        confidence = _calculate_confidence(vm, sizing_approach)

        rec = AzureRecommendation(
            vm_name=vm.name,
            recommended_vm_sku=sku.name if sku else "Manual assessment needed",
            recommended_vm_family=sku.family if sku else "",
            recommended_disk_type=legacy_disk_type,
            recommended_disk_size_gb=legacy_disk_size,
            estimated_monthly_cost_usd=round(pricing.total_payg_monthly, 2),
            migration_readiness=readiness,
            migration_issues=issues,
            target_region=target_region,
            confidence_score=confidence,
            right_sizing_note=right_size_note,
            on_prem_cpu_usage_percent=vm.perf.cpu_usage_percent,
            on_prem_memory_usage_percent=vm.perf.memory_usage_percent,
            # New fields
            disk_recommendations=disk_recs,
            pricing=pricing,
            os_type=os_type,
            os_eol_status=eol_status,
            os_eol_detail=eol_detail,
            azure_hybrid_benefit_eligible=ahub_eligible,
            sizing_approach=sizing_approach,
            perf_data_source=vm.perf.perf_data_source,
            perf_sample_count=vm.perf.sample_count,
            on_prem_cpu_p95_percent=vm.perf.cpu_p95_percent,
            on_prem_memory_p95_percent=vm.perf.memory_p95_percent,
            total_tco_monthly=pricing.total_payg_monthly,
            total_tco_optimized_monthly=pricing.total_optimized_monthly,
        )
        recommendations.append(rec)

    logger.info("Generated recommendations for %d VM(s)", len(recommendations))
    return recommendations
