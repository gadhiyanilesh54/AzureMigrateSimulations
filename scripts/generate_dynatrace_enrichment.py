"""Generate realistic Dynatrace enrichment data for all discovered VMs and workloads.

Produces a ``data/dynatrace_enrichment_export.json`` file that mimics a real
Dynatrace Environment API v2 entities+metrics export.  The file can be uploaded
via the dashboard's Enrichment Data tab to boost confidence scores.

Usage:
    python scripts/generate_dynatrace_enrichment.py
"""

import json
import random
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

_PROJECT = Path(__file__).resolve().parent.parent
_DATA = _PROJECT / "data"

# ---------------------------------------------------------------------------
# Load current discovery data
# ---------------------------------------------------------------------------
with open(_DATA / "vcenter_discovery.json", encoding="utf-8") as f:
    _vcenter = json.load(f)

_vms = _vcenter.get("vms", [])
_vm_names = [v["name"] for v in _vms]

# Workload data (optional)
try:
    with open(_DATA / "workload_discovery.json", encoding="utf-8") as f:
        _workload = json.load(f)
    _workload_recs = _workload.get("recommendations", [])
except FileNotFoundError:
    _workload_recs = []

# Build VM→workload map
_vm_workloads: dict[str, list[dict]] = {}
for wr in _workload_recs:
    vn = wr.get("vm_name", "")
    _vm_workloads.setdefault(vn, []).append(wr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _entity_id(prefix: str, name: str) -> str:
    """Dynatrace-style entity ID: HOST-<hex>"""
    h = hashlib.md5(name.encode()).hexdigest()[:16].upper()
    return f"{prefix}-{h}"


def _ts_iso(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


# Tier profiles – different workload tiers get different metric ranges
_TIER_PROFILES = {
    "database": {
        "cpu": (25, 75), "cpu_p95": (50, 92), "mem": (40, 90), "mem_p95": (60, 96),
        "iops": (200, 8000), "iops_p95": (500, 15000), "net": (500, 10000),
        "resp": (1, 50), "err": (0, 1.5), "conn": (10, 500),
        "txn": (100, 50000), "dep": 2,
    },
    "webapp": {
        "cpu": (10, 60), "cpu_p95": (30, 85), "mem": (20, 70), "mem_p95": (35, 85),
        "iops": (20, 500), "iops_p95": (50, 1200), "net": (200, 8000),
        "resp": (5, 800), "err": (0, 5), "conn": (5, 300),
        "txn": (50, 20000), "dep": 4,
    },
    "container": {
        "cpu": (5, 50), "cpu_p95": (15, 70), "mem": (10, 65), "mem_p95": (20, 80),
        "iops": (10, 300), "iops_p95": (30, 800), "net": (100, 5000),
        "resp": (2, 200), "err": (0, 3), "conn": (3, 150),
        "txn": (20, 10000), "dep": 3,
    },
    "orchestrator": {
        "cpu": (5, 40), "cpu_p95": (15, 60), "mem": (15, 55), "mem_p95": (25, 70),
        "iops": (30, 400), "iops_p95": (80, 900), "net": (200, 6000),
        "resp": (1, 100), "err": (0, 2), "conn": (5, 100),
        "txn": (50, 8000), "dep": 5,
    },
    "general_windows": {
        "cpu": (5, 65), "cpu_p95": (20, 80), "mem": (30, 85), "mem_p95": (45, 92),
        "iops": (20, 600), "iops_p95": (50, 1500), "net": (50, 3000),
        "resp": (5, 300), "err": (0, 4), "conn": (1, 100),
        "txn": (10, 5000), "dep": 2,
    },
    "general_linux": {
        "cpu": (3, 55), "cpu_p95": (15, 75), "mem": (15, 70), "mem_p95": (25, 85),
        "iops": (10, 400), "iops_p95": (30, 1000), "net": (30, 4000),
        "resp": (2, 250), "err": (0, 3), "conn": (1, 80),
        "txn": (5, 4000), "dep": 2,
    },
}

# Software packages Dynatrace would detect per tier
_DETECTED_SOFTWARE: dict[str, list[dict]] = {
    "database": [
        {"type": "SQL_SERVER", "version": "2019.150.4415.2", "edition": "Standard"},
        {"type": "MYSQL", "version": "8.0.36"},
        {"type": "POSTGRESQL", "version": "16.2"},
        {"type": "MARIADB", "version": "10.11.7"},
        {"type": "MONGODB", "version": "7.0.5"},
        {"type": "ORACLE_DB", "version": "19.22.0"},
    ],
    "webapp": [
        {"type": "IIS", "version": "10.0.20348.1"},
        {"type": "APACHE_HTTP_SERVER", "version": "2.4.58"},
        {"type": "NGINX", "version": "1.24.0"},
        {"type": "TOMCAT", "version": "10.1.18"},
        {"type": "DOTNET_RUNTIME", "version": "8.0.2"},
        {"type": "NODEJS", "version": "20.11.1"},
    ],
    "container": [
        {"type": "DOCKER", "version": "25.0.3"},
        {"type": "CONTAINERD", "version": "1.7.13"},
        {"type": "PODMAN", "version": "5.0.0"},
    ],
    "orchestrator": [
        {"type": "KUBERNETES", "version": "1.29.2"},
        {"type": "OPENSHIFT", "version": "4.15.0"},
    ],
}

# Environment tags for realism
_ENVS = ["production", "staging", "development", "qa", "dr"]
_TIERS = ["web-tier", "app-tier", "data-tier", "infra-tier", "middleware-tier"]
_OWNERS = ["platform-team", "app-dev", "dba-team", "devops", "sre-team", "cloud-migration"]
_REGIONS = ["us-east-dc1", "us-west-dc2", "eu-central-dc3"]

_DYNATRACE_HOST_GROUP_IDS = [
    "HOST_GROUP-A1B2C3D4E5F60001",
    "HOST_GROUP-A1B2C3D4E5F60002",
    "HOST_GROUP-A1B2C3D4E5F60003",
    "HOST_GROUP-A1B2C3D4E5F60004",
]


# ---------------------------------------------------------------------------
# Build Dynatrace export
# ---------------------------------------------------------------------------
def _build_host_entity(vm: dict, workloads: list[dict]) -> dict:
    """Build a Dynatrace host entity with full metrics & metadata."""
    name = vm["name"]
    os_fam = vm.get("guest_os_family", "linux")
    guest_os = vm.get("guest_os", "")
    cpus = vm.get("num_cpus", 2)
    mem_mb = vm.get("memory_mb", 4096)
    power = vm.get("power_state", "poweredOn")

    # Determine tier profile
    wl_types = [w.get("workload_type", "") for w in workloads]
    if "database" in wl_types:
        tier = "database"
    elif "webapp" in wl_types:
        tier = "webapp"
    elif "container" in wl_types:
        tier = "container"
    elif "orchestrator" in wl_types:
        tier = "orchestrator"
    elif os_fam == "windows":
        tier = "general_windows"
    else:
        tier = "general_linux"

    profile = _TIER_PROFILES[tier]

    # Scale metrics based on VM size
    cpu_scale = min(cpus / 4.0, 3.0)
    mem_scale = min(mem_mb / 8192.0, 3.0)

    # If powered off, metrics should be minimal
    if power != "poweredOn":
        avg_cpu = round(random.uniform(0, 2), 1)
        p95_cpu = round(random.uniform(0, 5), 1)
        avg_mem = round(random.uniform(0, 5), 1)
        p95_mem = round(random.uniform(0, 8), 1)
        iops = 0.0
        iops_p95 = 0.0
        net_kbps = 0.0
        resp_ms = None
        err_rate = None
        connections = 0
        transactions = 0
    else:
        avg_cpu = round(random.uniform(*profile["cpu"]), 1)
        p95_cpu = round(min(random.uniform(*profile["cpu_p95"]), 100), 1)
        if p95_cpu < avg_cpu:
            p95_cpu = round(avg_cpu + random.uniform(5, 20), 1)
        max_cpu = round(min(p95_cpu + random.uniform(2, 10), 100), 1)

        avg_mem = round(random.uniform(*profile["mem"]), 1)
        p95_mem = round(min(random.uniform(*profile["mem_p95"]), 100), 1)
        if p95_mem < avg_mem:
            p95_mem = round(avg_mem + random.uniform(3, 15), 1)
        max_mem = round(min(p95_mem + random.uniform(1, 8), 100), 1)

        iops = round(random.uniform(*profile["iops"]) * cpu_scale, 0)
        iops_p95 = round(random.uniform(*profile["iops_p95"]) * cpu_scale, 0)
        if iops_p95 < iops:
            iops_p95 = round(iops * 1.5, 0)

        net_kbps = round(random.uniform(*profile["net"]) * mem_scale, 0)
        resp_ms = round(random.uniform(*profile["resp"]), 1) if tier in ("webapp", "database", "container") else None
        err_rate = round(random.uniform(*profile["err"]), 2)
        connections = random.randint(*profile["conn"])
        transactions = random.randint(*profile["txn"])

    entity_id = _entity_id("HOST", name)
    monitoring_days = random.choice([7, 14, 30, 30, 30, 60, 90])
    sample_count = monitoring_days * random.randint(144, 288)  # 5-10min intervals

    # Detected processes (Dynatrace process groups)
    processes = []
    if workloads:
        for w in workloads:
            eng = w.get("source_engine", "unknown")
            ver = w.get("source_version", "")
            processes.append({
                "entityId": _entity_id("PROCESS_GROUP_INSTANCE", f"{name}-{eng}"),
                "displayName": eng.replace("_", " ").title(),
                "softwareTechnologyType": eng.upper(),
                "softwareTechnologyVersion": ver or "unknown",
                "listeningPorts": [random.choice([80, 443, 3306, 5432, 1433, 8080, 8443, 27017, 6379, 9090])],
            })

    # Dynatrace-detected software for that tier
    detected_sw = []
    if tier in _DETECTED_SOFTWARE:
        n_sw = random.randint(1, min(3, len(_DETECTED_SOFTWARE[tier])))
        detected_sw = random.sample(_DETECTED_SOFTWARE[tier], n_sw)

    # Dependencies (Dynatrace SmartScape relationships)
    dep_names = []
    dep_count = random.randint(0, profile["dep"])
    if dep_count > 0:
        other_vms = [v for v in _vm_names if v != name]
        dep_names = random.sample(other_vms, min(dep_count, len(other_vms)))

    # Tags in Dynatrace format
    env_tag = random.choice(_ENVS)
    tier_tag = random.choice(_TIERS)
    owner_tag = random.choice(_OWNERS)

    entity = {
        "entityId": entity_id,
        "displayName": name,
        "entityName": name,
        "firstSeenTimestamp": _ts_iso(monitoring_days + random.randint(0, 60)),
        "lastSeenTimestamp": _ts_iso(0),
        "monitoringMode": "FULL_STACK",
        "state": "RUNNING" if power == "poweredOn" else "SHUTDOWN",
        "osType": "WINDOWS" if os_fam == "windows" else "LINUX",
        "osVersion": guest_os or ("Windows Server 2019" if os_fam == "windows" else "Ubuntu 22.04"),
        "hypervisorType": "VMWARE",
        "ipAddresses": vm.get("ip_addresses", []) or [f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"],
        "cpuCores": cpus,
        "physicalMemoryMB": mem_mb,
        "hostGroup": {
            "meId": random.choice(_DYNATRACE_HOST_GROUP_IDS),
            "name": f"vSphere-{random.choice(_REGIONS)}",
        },
        "properties": {
            # ── CPU metrics ──
            "cpuUsage": avg_cpu,
            "cpuUsage95th": p95_cpu if power == "poweredOn" else 0,
            "cpuUsageMax": max_cpu if power == "poweredOn" else 0,
            # ── Memory metrics ──
            "memoryUsage": avg_mem,
            "memoryUsage95th": p95_mem if power == "poweredOn" else 0,
            "memoryUsageMax": max_mem if power == "poweredOn" else 0,
            # ── Disk metrics ──
            "diskIOPS": iops,
            "diskIOPS95th": iops_p95 if power == "poweredOn" else 0,
            "diskReadBytesPerSec": round(iops * random.uniform(4, 16) * 1024, 0) if iops else 0,
            "diskWriteBytesPerSec": round(iops * random.uniform(2, 8) * 1024, 0) if iops else 0,
            "diskLatencyMs": round(random.uniform(0.5, 15), 2) if power == "poweredOn" else 0,
            # ── Network metrics ──
            "networkBandwidth": net_kbps,
            "networkBytesReceivedPerSec": round(net_kbps * 128, 0) if net_kbps else 0,
            "networkBytesSentPerSec": round(net_kbps * 64, 0) if net_kbps else 0,
            "networkRetransmissionRate": round(random.uniform(0, 2), 3) if power == "poweredOn" else 0,
            # ── Application-level metrics ──
            "responseTime": resp_ms,
            "responseTime95th": round(resp_ms * random.uniform(1.5, 3.0), 1) if resp_ms else None,
            "errorRate": err_rate,
            "activeConnections": connections,
            "transactionCount": transactions,
            "requestCount": transactions * random.randint(1, 5) if transactions else 0,
            # ── Observation metadata ──
            "monitoringDays": monitoring_days,
            "sampleCount": sample_count,
            "dataPointInterval": "5m",
            "collectionStart": _ts_iso(monitoring_days),
            "collectionEnd": _ts_iso(0),
            # ── OneAgent info ──
            "oneAgentVersion": f"1.{random.randint(280, 300)}.{random.randint(0, 50)}.{random.randint(10000000, 99999999)}",
            "oneAgentActive": power == "poweredOn",
        },
        "tags": [
            {"context": "CONTEXTLESS", "key": "Environment", "value": env_tag},
            {"context": "CONTEXTLESS", "key": "Tier", "value": tier_tag},
            {"context": "CONTEXTLESS", "key": "Owner", "value": owner_tag},
            {"context": "CONTEXTLESS", "key": "CostCenter", "value": f"CC-{random.randint(1000,9999)}"},
            {"context": "CONTEXTLESS", "key": "MigrationWave", "value": f"wave-{random.randint(1,5)}"},
            {"context": "CONTEXTLESS", "key": "Criticality", "value": random.choice(["high", "medium", "low", "critical"])},
        ],
        "managementZones": [
            {"id": f"MZ-{random.randint(100000, 999999)}", "name": f"{env_tag.title()} {tier_tag.replace('-', ' ').title()}"},
        ],
        "fromRelationships": {},
        "toRelationships": {},
        "detectedSoftware": detected_sw,
        "processes": processes,
    }

    # SmartScape relationships
    if dep_names:
        entity["fromRelationships"]["isNetworkClientOf"] = [
            {"id": _entity_id("HOST", dep), "type": "HOST", "name": dep}
            for dep in dep_names
        ]
    if processes:
        entity["fromRelationships"]["runs"] = [
            {"id": p["entityId"], "type": "PROCESS_GROUP_INSTANCE", "name": p["displayName"]}
            for p in processes
        ]

    # Service-level entities for workloads with application metrics
    services = []
    if workloads and power == "poweredOn":
        for w in workloads:
            wl_type = w.get("workload_type", "")
            eng = w.get("source_engine", "unknown")
            svc_name = f"{name}:{eng}"
            svc_profile = _TIER_PROFILES.get(wl_type, _TIER_PROFILES["general_linux"])
            services.append({
                "entityId": _entity_id("SERVICE", svc_name),
                "displayName": f"{eng.replace('_', ' ').title()} on {name}",
                "discoveredName": eng,
                "hostEntityId": entity_id,
                "hostName": name,
                "serviceType": wl_type.upper(),
                "softwareTechnology": eng.upper(),
                "metrics": {
                    "responseTimeAvg": round(random.uniform(*svc_profile["resp"]), 1),
                    "responseTime95th": round(random.uniform(*svc_profile["resp"]) * 2, 1),
                    "errorRate": round(random.uniform(*svc_profile["err"]), 2),
                    "throughputPerMin": random.randint(10, 5000),
                    "activeConnections": random.randint(*svc_profile["conn"]),
                    "transactionsPerDay": random.randint(1000, 500000),
                    "failedTransactionsPct": round(random.uniform(0, 3), 2),
                },
                "tags": [
                    {"key": "ServiceType", "value": wl_type},
                    {"key": "Engine", "value": eng},
                ],
            })
        entity["services"] = services
        entity["toRelationships"]["runsOn"] = [
            {"id": s["entityId"], "type": "SERVICE", "name": s["displayName"]}
            for s in services
        ]

    return entity


def main():
    random.seed(42)  # reproducible output

    print(f"Generating Dynatrace enrichment data for {len(_vms)} VMs...")

    entities = []
    for vm in _vms:
        workloads = _vm_workloads.get(vm["name"], [])
        entity = _build_host_entity(vm, workloads)
        entities.append(entity)

    # Assemble Dynatrace Environment API v2 export structure
    export = {
        "exportMetadata": {
            "exportedBy": "Dynatrace Environment API v2",
            "exportVersion": "2.0",
            "environmentId": "abc12345",
            "environmentUrl": "https://abc12345.live.dynatrace.com",
            "exportTimestamp": _ts_iso(0),
            "entityCount": len(entities),
            "metricsResolution": "5m",
            "collectionPeriodDays": 30,
            "oneAgentVersion": "1.291.43.20260215-103012",
        },
        "entities": entities,
        "summary": {
            "totalHosts": len(entities),
            "runningHosts": sum(1 for e in entities if e["state"] == "RUNNING"),
            "shutdownHosts": sum(1 for e in entities if e["state"] == "SHUTDOWN"),
            "hostsWithProcesses": sum(1 for e in entities if e.get("processes")),
            "hostsWithServices": sum(1 for e in entities if e.get("services")),
            "totalProcesses": sum(len(e.get("processes", [])) for e in entities),
            "totalServices": sum(len(e.get("services", [])) for e in entities),
            "totalDetectedSoftware": sum(len(e.get("detectedSoftware", [])) for e in entities),
            "monitoringCoverage": {
                "fullStack": sum(1 for e in entities if e["monitoringMode"] == "FULL_STACK"),
                "infrastructureOnly": 0,
            },
        },
    }

    out_path = _DATA / "dynatrace_enrichment_export.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2, default=str)

    print(f"  Written to {out_path}")
    print(f"  Total entities: {export['summary']['totalHosts']}")
    print(f"  Running hosts:  {export['summary']['runningHosts']}")
    print(f"  With processes: {export['summary']['hostsWithProcesses']}")
    print(f"  With services:  {export['summary']['hostsWithServices']}")
    print(f"  Total services: {export['summary']['totalServices']}")
    print()
    print("To use this file:")
    print("  1. Open the dashboard → Enrichment Data tab")
    print("  2. Select 'Dynatrace' as tool")
    print("  3. Upload data/dynatrace_enrichment_export.json")
    print("  4. Confidence scores will increase across all VMs")


if __name__ == "__main__":
    main()
