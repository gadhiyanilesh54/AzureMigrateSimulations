"""Flask web dashboard for Azure Migrate Simulations – serves the discovery report
as an interactive UI with topology, assessment engine, and simulation engine.

Supports both live vCenter discovery and loading from a saved report file."""

from __future__ import annotations

import json
import logging
import math
import random
import re as _re
import sys
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# Ensure the src package is importable
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))

from digital_twin_migrate.vcenter_discovery import discover_environment  # noqa: E402
from digital_twin_migrate.azure_mapping import generate_recommendations  # noqa: E402
from digital_twin_migrate.config import VCenterConfig  # noqa: E402
from digital_twin_migrate.guest_discovery import GuestDiscoverer, Credential, DatabaseCredential, deep_probe_databases  # noqa: E402
from digital_twin_migrate.workload_mapping import generate_workload_recommendations  # noqa: E402
from digital_twin_migrate.enrichment import (  # noqa: E402
    ingest_telemetry,
    MonitoringTool,
    EnrichmentResult,
    apply_enrichment_to_confidence,
    generate_sample_enrichment,
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data persistence directory
# ---------------------------------------------------------------------------

DATA_DIR = _project_root / "data"
DATA_DIR.mkdir(exist_ok=True)

_VCENTER_DATA_FILE = DATA_DIR / "vcenter_discovery.json"
_WORKLOAD_DATA_FILE = DATA_DIR / "workload_discovery.json"
_WHATIF_OVERRIDES_FILE = DATA_DIR / "whatif_overrides.json"
_WL_WHATIF_OVERRIDES_FILE = DATA_DIR / "workload_whatif_overrides.json"
_PERF_HISTORY_FILE = DATA_DIR / "perf_history.json"
_ENRICHMENT_DATA_FILE = DATA_DIR / "enrichment_data.json"


def _save_json(path: Path, obj: dict) -> None:
    """Persist a dict to a JSON file in the data/ folder."""
    try:
        path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
        logger.info("Saved %s", path.name)
    except Exception as exc:
        logger.warning("Failed to save %s: %s", path.name, exc)


def _load_json(path: Path) -> dict:
    """Load a JSON file, returning empty dict on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load %s: %s", path.name, exc)
    return {}


# ---------------------------------------------------------------------------
# Global data store & discovery state
# ---------------------------------------------------------------------------

_data: dict = {}

_discovery_state: dict = {
    "status": "idle",       # idle | connecting | discovering | mapping | complete | error
    "message": "",
    "progress": 0,
    "vcenter_host": "",
}

# Workload discovery state
_workload_data: dict = {}            # stores discovered workloads + recommendations
_workload_discoverer: GuestDiscoverer | None = None

# What-If overrides: { vm_name: { sku, region, pricing } }
_whatif_overrides: dict[str, dict] = {}

# Workload What-If overrides: { workload_key: { service, region, pricing } }
_workload_whatif_overrides: dict[str, dict] = {}

# Enrichment data store: { vm_name: EnrichmentTelemetry.to_dict() }
_enrichment_data: dict[str, dict] = {}
_enrichment_history: list[dict] = []  # list of ingestion results

# ---------------------------------------------------------------------------
# Performance Collector – collects VM & workload perf every 15 minutes
# ---------------------------------------------------------------------------

PERF_INTERVAL_SECONDS = 900          # 15 minutes
PERF_HISTORY_MAX_HOURS = 7 * 24      # default: 7 days rolling window
PERF_HISTORY_MAX_SAMPLES = int(PERF_HISTORY_MAX_HOURS * 3600 / PERF_INTERVAL_SECONDS)

# Perf data store: { vm_name: [ { ts, cpu_pct, mem_pct, disk_iops, net_kbps } ] }
_perf_history: dict[str, list[dict]] = {}
# Workload perf store: { "vm_name::workload_name": [ { ts, cpu_pct, mem_mb, connections } ] }
_workload_perf_history: dict[str, list[dict]] = {}

_perf_collector_state: dict = {
    "running": False,
    "last_collection": None,       # ISO timestamp
    "next_collection": None,       # ISO timestamp
    "samples_collected": 0,
    "interval_seconds": PERF_INTERVAL_SECONDS,
    "vms_monitored": 0,
    "workloads_monitored": 0,
    "duration_days": 7,
}

_perf_collector_stop = threading.Event()


def _collect_perf_sample() -> None:
    """Collect one perf sample for all powered-on VMs and their workloads.

    When running from saved data (no live vCenter connection), we simulate
    realistic perf readings based on the initial snapshot data with random
    jitter so that assessment can use avg/p95 statistics for right-sizing.
    """
    global _perf_history, _workload_perf_history

    if not _data or not _data.get("vms"):
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    vms = _data["vms"]
    powered_on = [v for v in vms if v.get("power_state") == "poweredOn"]

    vm_count = 0
    for vm in powered_on:
        name = vm["name"]
        perf = vm.get("perf", {})

        # Base values from the discovery snapshot
        base_cpu = perf.get("cpu_usage_percent", 0) or random.uniform(5, 45)
        base_mem = perf.get("memory_usage_percent", 0) or random.uniform(20, 60)
        base_iops_r = perf.get("disk_iops_read", 0) or random.uniform(0, 50)
        base_iops_w = perf.get("disk_iops_write", 0) or random.uniform(0, 30)
        base_net_rx = perf.get("network_rx_kbps", 0) or random.uniform(0, 500)
        base_net_tx = perf.get("network_tx_kbps", 0) or random.uniform(0, 200)
        base_disk_r = perf.get("disk_read_kbps", 0) or random.uniform(0, 1000)
        base_disk_w = perf.get("disk_write_kbps", 0) or random.uniform(0, 500)

        # Add realistic jitter (±30%)
        def _jitter(val: float, pct: float = 0.30) -> float:
            return max(0, val * random.uniform(1 - pct, 1 + pct))

        sample = {
            "ts": now_iso,
            "cpu_pct": round(min(100, _jitter(base_cpu)), 2),
            "mem_pct": round(min(100, _jitter(base_mem)), 2),
            "disk_iops": round(_jitter(base_iops_r + base_iops_w), 1),
            "disk_read_kbps": round(_jitter(base_disk_r), 1),
            "disk_write_kbps": round(_jitter(base_disk_w), 1),
            "net_rx_kbps": round(_jitter(base_net_rx), 1),
            "net_tx_kbps": round(_jitter(base_net_tx), 1),
        }

        if name not in _perf_history:
            _perf_history[name] = []
        _perf_history[name].append(sample)
        # Trim to max window
        if len(_perf_history[name]) > PERF_HISTORY_MAX_SAMPLES:
            _perf_history[name] = _perf_history[name][-PERF_HISTORY_MAX_SAMPLES:]
        vm_count += 1

    # ----- Workload-level perf -----
    wl_count = 0
    recs = (_workload_data or {}).get("recommendations", [])
    for rec in recs:
        wl_type = rec.get("workload_type", "")
        if wl_type in ("network", "fileshare"):
            continue  # infra items — no per-process perf
        vm_name = rec.get("vm_name", "")
        wl_name = rec.get("workload_name", "")
        key = f"{vm_name}::{wl_name}"

        # Find parent VM perf as basis
        vm_perf = _perf_history.get(vm_name, [{}])
        latest_vm = vm_perf[-1] if vm_perf else {}

        # Estimate workload share of VM resources based on type
        if wl_type == "database":
            cpu_share = random.uniform(0.3, 0.7)
            mem_share = random.uniform(0.4, 0.8)
            conn_base = random.randint(5, 80)
        elif wl_type == "webapp":
            cpu_share = random.uniform(0.1, 0.4)
            mem_share = random.uniform(0.1, 0.35)
            conn_base = random.randint(2, 40)
        elif wl_type in ("container", "orchestrator"):
            cpu_share = random.uniform(0.2, 0.6)
            mem_share = random.uniform(0.2, 0.5)
            conn_base = random.randint(1, 20)
        else:
            cpu_share = random.uniform(0.1, 0.3)
            mem_share = random.uniform(0.1, 0.3)
            conn_base = random.randint(1, 10)

        vm_cpu = latest_vm.get("cpu_pct", random.uniform(10, 40))
        vm_mem = latest_vm.get("mem_pct", random.uniform(20, 50))

        # Find VM's memory_mb for absolute calculation
        vm_data = next((v for v in vms if v["name"] == vm_name), None)
        vm_mem_mb = (vm_data.get("memory_mb", 4096) if vm_data else 4096)

        wl_sample = {
            "ts": now_iso,
            "cpu_pct": round(min(100, vm_cpu * cpu_share * random.uniform(0.8, 1.2)), 2),
            "mem_mb": round(vm_mem_mb * (vm_mem / 100) * mem_share * random.uniform(0.8, 1.2), 1),
            "connections": max(0, int(conn_base * random.uniform(0.5, 1.5))),
        }

        if key not in _workload_perf_history:
            _workload_perf_history[key] = []
        _workload_perf_history[key].append(wl_sample)
        if len(_workload_perf_history[key]) > PERF_HISTORY_MAX_SAMPLES:
            _workload_perf_history[key] = _workload_perf_history[key][-PERF_HISTORY_MAX_SAMPLES:]
        wl_count += 1

    _perf_collector_state["last_collection"] = now_iso
    _perf_collector_state["samples_collected"] += 1
    _perf_collector_state["vms_monitored"] = vm_count
    _perf_collector_state["workloads_monitored"] = wl_count
    logger.info("Perf sample #%d: %d VMs, %d workloads",
                _perf_collector_state["samples_collected"], vm_count, wl_count)


def _perf_collector_loop() -> None:
    """Background thread that collects perf samples every PERF_INTERVAL_SECONDS."""
    _perf_collector_state["running"] = True
    logger.info("Perf collector started (interval=%ds)", PERF_INTERVAL_SECONDS)

    # Collect an initial sample immediately
    try:
        _collect_perf_sample()
        _save_perf_history()
    except Exception as e:
        logger.warning("Initial perf collection failed: %s", e)

    while not _perf_collector_stop.is_set():
        next_ts = datetime.now(timezone.utc).timestamp() + PERF_INTERVAL_SECONDS
        _perf_collector_state["next_collection"] = datetime.fromtimestamp(
            next_ts, tz=timezone.utc
        ).isoformat()

        # Wait for interval or stop signal
        if _perf_collector_stop.wait(timeout=PERF_INTERVAL_SECONDS):
            break

        try:
            _collect_perf_sample()
            _save_perf_history()
        except Exception as e:
            logger.warning("Perf collection failed: %s", e)

    _perf_collector_state["running"] = False
    logger.info("Perf collector stopped")


def _save_perf_history() -> None:
    """Persist perf history to disk."""
    _save_json(_PERF_HISTORY_FILE, {
        "vm_perf": _perf_history,
        "workload_perf": _workload_perf_history,
        "state": _perf_collector_state,
    })


def _load_perf_history() -> None:
    """Load perf history from disk."""
    global _perf_history, _workload_perf_history
    data = _load_json(_PERF_HISTORY_FILE)
    if data:
        _perf_history = data.get("vm_perf", {})
        _workload_perf_history = data.get("workload_perf", {})
        saved_state = data.get("state", {})
        _perf_collector_state["samples_collected"] = saved_state.get("samples_collected", 0)
        _perf_collector_state["last_collection"] = saved_state.get("last_collection")
        total_samples = sum(len(v) for v in _perf_history.values())
        logger.info("Loaded perf history: %d VMs, %d total samples",
                    len(_perf_history), total_samples)


def _set_perf_duration(days: int) -> None:
    """Update the perf collection rolling window duration."""
    global PERF_HISTORY_MAX_HOURS, PERF_HISTORY_MAX_SAMPLES
    days = max(1, min(30, days))  # clamp to 1-30
    PERF_HISTORY_MAX_HOURS = days * 24
    PERF_HISTORY_MAX_SAMPLES = int(PERF_HISTORY_MAX_HOURS * 3600 / PERF_INTERVAL_SECONDS)
    _perf_collector_state["duration_days"] = days
    logger.info("Perf duration set to %d day(s) (%d hours, max %d samples)",
                days, PERF_HISTORY_MAX_HOURS, PERF_HISTORY_MAX_SAMPLES)


def _start_perf_collector() -> None:
    """Start the perf collector background thread if data is available."""
    if _perf_collector_state["running"]:
        return
    if not _data or not _data.get("vms"):
        return
    _perf_collector_stop.clear()
    threading.Thread(target=_perf_collector_loop, daemon=True).start()


def _compute_perf_stats(samples: list[dict], field: str) -> dict:
    """Compute avg, min, max, p95 for a given field over samples."""
    values = [s.get(field, 0) for s in samples if s.get(field) is not None]
    if not values:
        return {"avg": 0, "min": 0, "max": 0, "p95": 0, "latest": 0, "count": 0}
    values_sorted = sorted(values)
    n = len(values_sorted)
    p95_idx = min(int(n * 0.95), n - 1)
    return {
        "avg": round(sum(values) / n, 2),
        "min": round(values_sorted[0], 2),
        "max": round(values_sorted[-1], 2),
        "p95": round(values_sorted[p95_idx], 2),
        "latest": round(values[-1], 2),
        "count": n,
    }


def _auto_load_from_data_dir() -> None:
    """Auto-load persisted data from data/ folder on startup."""
    global _data, _discovery_state, _workload_data, _whatif_overrides, _workload_whatif_overrides, _enrichment_data, _enrichment_history

    # Load vCenter discovery
    vc = _load_json(_VCENTER_DATA_FILE)
    if vc and "vms" in vc:
        _data = vc
        _discovery_state.update(
            status="complete",
            message=f"Loaded from data/: {len(vc['vms'])} VMs",
            progress=100,
            vcenter_host=vc.get("vcenter_host", ""),
        )
        logger.info("Auto-loaded vCenter data: %d VMs", len(vc["vms"]))

    # Load workload discovery
    wl = _load_json(_WORKLOAD_DATA_FILE)
    if wl and "recommendations" in wl:
        _workload_data = wl
        logger.info("Auto-loaded workload data: %d recommendations",
                    len(wl["recommendations"]))

    # Generate infrastructure-level recommendations (networks + file shares)
    if _workload_data and _data:
        _merge_infra_recommendations()

    # Load what-if overrides
    ov = _load_json(_WHATIF_OVERRIDES_FILE)
    if ov:
        _whatif_overrides.update(ov)
        logger.info("Auto-loaded %d VM what-if overrides", len(ov))

    wov = _load_json(_WL_WHATIF_OVERRIDES_FILE)
    if wov:
        _workload_whatif_overrides.update(wov)
        logger.info("Auto-loaded %d workload what-if overrides", len(wov))

    # Load perf history and start collector
    _load_perf_history()
    _start_perf_collector()

    # Load enrichment data
    enr = _load_json(_ENRICHMENT_DATA_FILE)
    if enr:
        _enrichment_data.update(enr.get("telemetry", {}))
        _enrichment_history = enr.get("history", [])
        logger.info("Auto-loaded enrichment data for %d entities", len(_enrichment_data))


def _load_data() -> dict:
    """Return the current in-memory data.  Returns empty dict when nothing loaded."""
    return _data


def _merge_infra_recommendations() -> None:
    """Generate network & file-share recommendations from vCenter data and merge
    them into the workload recommendation list.  Idempotent – removes previous
    infra recs before adding new ones."""
    global _workload_data
    if not _workload_data or not _data:
        return
    recs: list[dict] = _workload_data.get("recommendations", [])
    # Remove stale infra recs
    recs = [r for r in recs if r.get("workload_type") not in ("network", "fileshare")]

    # ----- Networks -----
    for net in _data.get("networks", []):
        net_type = (net.get("network_type", "standard") or "standard").lower()
        options = NETWORK_SERVICE_MAP.get(net_type, NETWORK_SERVICE_MAP.get("standard", []))
        if not options:
            continue
        primary = options[0]
        recs.append({
            "vm_name": net.get("datacenter", "Infra"),
            "workload_name": f"Network: {net['name']}",
            "workload_type": "network",
            "source_engine": net_type,
            "source_version": f"VLAN {net.get('vlan_id', 0)}",
            "recommended_azure_service": primary.display,
            "alternative_services": [o.name for o in options[1:]],
            "estimated_monthly_cost_usd": primary.estimated_monthly_usd,
            "migration_approach": primary.migration_approach,
            "migration_complexity": primary.complexity,
            "migration_steps": [
                "Design Azure VNet address space and subnet layout",
                "Create Network Security Groups (NSGs) for micro-segmentation",
                "Configure VPN Gateway or ExpressRoute for hybrid connectivity",
                "Migrate firewall rules to NSG rules / Azure Firewall policies",
                "Set up DNS resolution (Azure DNS / Private DNS Zones)",
            ],
            "issues": [],
            "confidence": 70.0,
        })

    # ----- File Shares (from datastores) -----
    for ds in _data.get("datastores", []):
        ds_type = (ds.get("type", "vmfs") or "vmfs").lower()
        options = FILESHARE_SERVICE_MAP.get(ds_type, FILESHARE_SERVICE_MAP.get("vmfs", []))
        if not options:
            continue
        primary = options[0]
        # Scale cost by capacity (per 100 GB)
        cap = ds.get("capacity_gb", 0) or 0
        cost_mult = max(cap / 100.0, 1.0)
        adjusted_cost = round(primary.estimated_monthly_usd * cost_mult, 2)
        recs.append({
            "vm_name": ds.get("datacenter", "Infra"),
            "workload_name": f"File Share: {ds['name']}",
            "workload_type": "fileshare",
            "source_engine": ds_type,
            "source_version": f"{round(cap)} GB",
            "recommended_azure_service": primary.display,
            "alternative_services": [o.name for o in options[1:]],
            "estimated_monthly_cost_usd": adjusted_cost,
            "migration_approach": primary.migration_approach,
            "migration_complexity": primary.complexity,
            "migration_steps": [
                "Create Azure Storage Account with appropriate tier",
                "Create file share with required quota and protocol (SMB/NFS)",
                "Use Azure File Sync or AzCopy/Robocopy for data migration",
                "Configure private endpoints for secure access",
                "Update application mount points / UNC paths",
            ],
            "issues": [],
            "confidence": 65.0,
        })

    _workload_data["recommendations"] = recs
    # Update total cost
    _workload_data["total_workload_cost"] = round(
        sum(r.get("estimated_monthly_cost_usd", 0) for r in recs), 2
    )
    logger.info("Merged infra recommendations: total %d recs", len(recs))


# ---------------------------------------------------------------------------
# Discovery progress logging interceptor
# ---------------------------------------------------------------------------

class _DiscoveryProgressHandler(logging.Handler):
    """Captures log messages from the discovery module to update progress."""

    def emit(self, record):
        msg = record.getMessage()
        try:
            if "Connecting to vCenter" in msg:
                _discovery_state.update(message="Connecting to vCenter…", progress=5)
            elif "Connected successfully" in msg:
                _discovery_state.update(message="Connected! Starting discovery…", progress=10)
            elif "datacenter" in msg.lower() and "Discovered" in msg:
                _discovery_state.update(message=msg, progress=15)
            elif "cluster" in msg.lower() and "Discovered" in msg:
                _discovery_state.update(message=msg, progress=18)
            elif "host" in msg.lower() and "Discovered" in msg:
                _discovery_state.update(message=msg, progress=22)
            elif "datastore" in msg.lower() and "Discovered" in msg:
                _discovery_state.update(message=msg, progress=26)
            elif "network" in msg.lower() and "Discovered" in msg:
                _discovery_state.update(message=msg, progress=30)
            elif "PropertyCollector fetched" in msg:
                _discovery_state.update(message=msg, progress=35)
            elif "Processing VM" in msg:
                m = _re.search(r"Processing VM (\d+)/(\d+)", msg)
                if m:
                    cur, tot = int(m.group(1)), int(m.group(2))
                    pct = 35 + int(45 * cur / tot)
                    _discovery_state.update(
                        message=f"Discovering VMs… {cur}/{tot}",
                        progress=min(pct, 80),
                    )
            elif "VM" in msg and "Discovered" in msg and "template" not in msg.lower():
                _discovery_state.update(message=msg, progress=80)
            elif "Generated recommendations" in msg:
                _discovery_state.update(message=msg, progress=95)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Background discovery runner
# ---------------------------------------------------------------------------

def _run_discovery(host: str, username: str, password: str,
                   port: int = 443, disable_ssl: bool = True,
                   collect_perf: bool = True) -> None:
    """Execute vCenter discovery + Azure mapping in a background thread."""
    global _data, _discovery_state

    progress_handler = _DiscoveryProgressHandler()
    disc_logger = logging.getLogger("digital_twin_migrate")
    disc_logger.addHandler(progress_handler)
    disc_logger.setLevel(logging.INFO)

    try:
        _discovery_state.update(
            status="connecting", message="Connecting to vCenter…",
            progress=5, vcenter_host=host,
        )

        cfg = VCenterConfig(
            host=host, port=port, username=username,
            password=password, disable_ssl=disable_ssl,
        )

        _discovery_state.update(
            status="discovering",
            message="Starting environment discovery…", progress=10,
        )
        env = discover_environment(cfg, collect_perf=collect_perf)

        _discovery_state.update(
            status="mapping",
            message="Generating Azure migration recommendations…", progress=85,
        )
        recs = generate_recommendations(env)

        _discovery_state.update(
            status="building", message="Building report…", progress=92,
        )

        report = {
            "vcenter_host": env.vcenter_host,
            "summary": {
                "datacenters": len(env.datacenters),
                "clusters": len(env.clusters),
                "hosts": len(env.hosts),
                "vms": len(env.vms),
                "datastores": len(env.datastores),
                "networks": len(env.networks),
            },
            "vms": [asdict(vm) for vm in env.vms],
            "hosts": [asdict(h) for h in env.hosts],
            "clusters": [asdict(c) for c in env.clusters],
            "datastores": [asdict(ds) for ds in env.datastores],
            "networks": [asdict(n) for n in env.networks],
            "recommendations": [asdict(r) for r in recs],
            "total_monthly_cost_usd": round(
                sum(r.estimated_monthly_cost_usd for r in recs), 2
            ),
        }

        # Normalise via JSON round-trip (handles enums, datetimes, etc.)
        _data = json.loads(json.dumps(report, default=str))

        # Persist for future reloads
        save_path = _project_root / "discovery_report.json"
        save_path.write_text(json.dumps(_data, indent=2), encoding="utf-8")

        # Also save to data/ folder
        _save_json(_VCENTER_DATA_FILE, _data)

        _discovery_state.update(
            status="complete",
            message=(
                f"Discovery complete! Found {len(env.vms)} VMs, "
                f"{len(env.hosts)} hosts, {len(env.datastores)} datastores."
            ),
            progress=100,
        )

        # Start perf collector after successful discovery
        _start_perf_collector()
    except Exception as exc:
        logger.exception("Discovery failed")
        _discovery_state.update(
            status="error", message=str(exc), progress=0,
        )
    finally:
        disc_logger.removeHandler(progress_handler)


# ---------------------------------------------------------------------------
# Connection / status endpoints
# ---------------------------------------------------------------------------

@app.route("/api/connect", methods=["POST"])
def api_connect():
    """Start live vCenter discovery from user-provided credentials."""
    busy = _discovery_state["status"] in (
        "connecting", "discovering", "mapping", "building",
    )
    if busy:
        return jsonify({"error": "Discovery already in progress"}), 409

    body = request.get_json(force=True)
    host = body.get("vcenter_url", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    port = int(body.get("port", 443))
    disable_ssl = body.get("disable_ssl", True)
    collect_perf = body.get("collect_perf", True)
    perf_duration_days = int(body.get("perf_duration_days", 7))

    # Update perf collection window based on user selection
    _set_perf_duration(perf_duration_days)

    if not host or not username or not password:
        return jsonify({"error": "vCenter URL, username, and password are required"}), 400

    threading.Thread(
        target=_run_discovery,
        args=(host, username, password, port, disable_ssl, collect_perf),
        daemon=True,
    ).start()

    return jsonify({"status": "started", "message": "Discovery started"})


@app.route("/api/discover/status")
def api_discover_status():
    """Poll discovery progress."""
    return jsonify(_discovery_state)


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    """Clear loaded data and return to the connection screen."""
    global _data, _discovery_state
    _data = {}
    _discovery_state = {
        "status": "idle", "message": "", "progress": 0, "vcenter_host": "",
    }
    return jsonify({"status": "disconnected"})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Load data from an uploaded discovery_report.json file."""
    global _data, _discovery_state
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    try:
        content = f.read().decode("utf-8")
        data = json.loads(content)
        required = ["vcenter_host", "vms", "recommendations"]
        missing = [k for k in required if k not in data]
        if missing:
            return jsonify({
                "error": f"Invalid report file. Missing keys: {', '.join(missing)}"
            }), 400

        _data = data
        _discovery_state.update(
            status="complete",
            message=f"Loaded from file: {len(data['vms'])} VMs",
            progress=100,
            vcenter_host=data.get("vcenter_host", ""),
        )
        # Persist to data/
        _save_json(_VCENTER_DATA_FILE, _data)
        return jsonify({"status": "loaded", "vms": len(data["vms"])})
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON file"}), 400


@app.route("/api/status")
def api_status():
    """Return whether data is loaded and the current connection state."""
    return jsonify({
        "data_loaded": bool(_data),
        "vcenter_host": _data.get("vcenter_host", ""),
        "vm_count": len(_data.get("vms", [])),
        "discovery_state": _discovery_state,
    })


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API endpoints (consumed by JS on the page)
# ---------------------------------------------------------------------------

@app.route("/api/summary")
def api_summary():
    d = _load_data()
    vms = d["vms"]
    recs = d["recommendations"]

    powered_on = sum(1 for v in vms if v["power_state"] == "poweredOn")
    powered_off = len(vms) - powered_on
    windows = sum(1 for v in vms if v["guest_os_family"] == "windows")
    linux = sum(1 for v in vms if v["guest_os_family"] == "linux")
    other_os = len(vms) - windows - linux

    ready = sum(1 for r in recs if r["migration_readiness"] == "Ready")
    conditional = sum(1 for r in recs if r["migration_readiness"] == "Ready with conditions")
    not_ready = sum(1 for r in recs if r["migration_readiness"] == "Not Ready")

    total_vcpus = sum(v["num_cpus"] for v in vms)
    total_memory_gb = sum(v["memory_mb"] for v in vms) / 1024
    total_disk_tb = sum(v["total_disk_gb"] for v in vms) / 1024

    # SKU distribution
    sku_dist: dict[str, int] = {}
    for r in recs:
        sku = r["recommended_vm_sku"]
        sku_dist[sku] = sku_dist.get(sku, 0) + 1

    # Family distribution
    family_dist: dict[str, int] = {}
    for r in recs:
        fam = r["recommended_vm_family"] or "Unknown"
        family_dist[fam] = family_dist.get(fam, 0) + 1

    # Cost by family
    cost_by_family: dict[str, float] = {}
    for r in recs:
        fam = r["recommended_vm_family"] or "Unknown"
        cost_by_family[fam] = cost_by_family.get(fam, 0) + r["estimated_monthly_cost_usd"]

    # Folder distribution
    folder_dist: dict[str, int] = {}
    for v in vms:
        f = v.get("folder", "Unknown") or "Unknown"
        folder_dist[f] = folder_dist.get(f, 0) + 1

    return jsonify({
        "total_vms": len(vms),
        "powered_on": powered_on,
        "powered_off": powered_off,
        "windows": windows,
        "linux": linux,
        "other_os": other_os,
        "ready": ready,
        "conditional": conditional,
        "not_ready": not_ready,
        "total_vcpus": total_vcpus,
        "total_memory_gb": round(total_memory_gb, 1),
        "total_disk_tb": round(total_disk_tb, 2),
        "total_monthly_cost": d["total_monthly_cost_usd"],
        "total_annual_cost": round(d["total_monthly_cost_usd"] * 12, 2),
        "hosts": len(d["hosts"]),
        "file_shares": len(d["datastores"]),
        "networks": len(d["networks"]),
        "sku_distribution": sku_dist,
        "family_distribution": family_dist,
        "cost_by_family": {k: round(v, 2) for k, v in cost_by_family.items()},
        "folder_distribution": folder_dist,
    })


@app.route("/api/topology")
def api_topology():
    """Return nodes and edges for the interactive topology graph."""
    d = _load_data()
    nodes = []
    edges = []
    node_id = 0

    # vCenter root
    vc_id = node_id
    nodes.append({"id": vc_id, "label": d["vcenter_host"].split(".")[0], "group": "vcenter",
                   "title": f"vCenter: {d['vcenter_host']}"})
    node_id += 1

    # Datacenter (only 1 in this lab)
    dc_name = d["hosts"][0]["datacenter"] if d["hosts"] else "DC"
    dc_id = node_id
    nodes.append({"id": dc_id, "label": dc_name, "group": "datacenter",
                   "title": f"Datacenter: {dc_name}"})
    edges.append({"from": vc_id, "to": dc_id})
    node_id += 1

    # Hosts
    host_ids: dict[str, int] = {}
    for h in d["hosts"]:
        hid = node_id
        host_ids[h["name"]] = hid
        mem_gb = h["memory_mb"] // 1024
        nodes.append({
            "id": hid, "label": h["name"], "group": "host",
            "title": (f"Host: {h['name']}\n{h['vendor']} {h['model']}\n"
                      f"CPU: {h['cpu_cores']}c — {h['cpu_model']}\n"
                      f"RAM: {mem_gb} GB\nESXi: {h['esxi_version']}\nVMs: {h['vm_count']}")
        })
        edges.append({"from": dc_id, "to": hid})
        node_id += 1

    # File Shares (from vCenter datastores)
    fs_folder_id = node_id
    nodes.append({"id": fs_folder_id, "label": "File Shares", "group": "fileshare_folder",
                   "title": f"{len(d['datastores'])} file shares"})
    edges.append({"from": dc_id, "to": fs_folder_id})
    node_id += 1

    for ds in d["datastores"]:
        did = node_id
        used = ds["capacity_gb"] - ds["free_space_gb"]
        pct = (used / ds["capacity_gb"] * 100) if ds["capacity_gb"] > 0 else 0
        nodes.append({
            "id": did, "label": ds["name"], "group": "fileshare",
            "title": f"File Share: {ds['name']}\nType: {ds['type']}\n"
                     f"Used: {used:,.0f}/{ds['capacity_gb']:,.0f} GB ({pct:.0f}%)"
        })
        edges.append({"from": fs_folder_id, "to": did})
        node_id += 1

    # Networks
    net_folder_id = node_id
    nodes.append({"id": net_folder_id, "label": "Networks", "group": "network_folder",
                   "title": f"{len(d['networks'])} networks"})
    edges.append({"from": dc_id, "to": net_folder_id})
    node_id += 1

    for net in d["networks"]:
        nid = node_id
        nodes.append({
            "id": nid, "label": net["name"], "group": "network",
            "title": f"Network: {net['name']}\nType: {net['network_type']}\nVLAN: {net['vlan_id']}"
        })
        edges.append({"from": net_folder_id, "to": nid})
        node_id += 1

    # VMs (grouped by host)
    for vm in d["vms"]:
        vid = node_id
        state = "vm_on" if vm["power_state"] == "poweredOn" else "vm_off"
        disk_gb = vm["total_disk_gb"]
        ips = ", ".join(ip for nic in vm["nics"] for ip in nic.get("ip_addresses", [])[:2])
        nodes.append({
            "id": vid, "label": vm["name"][:20], "group": state,
            "title": (f"VM: {vm['name']}\nState: {vm['power_state']}\n"
                      f"vCPU: {vm['num_cpus']} | RAM: {vm['memory_mb'] // 1024} GB\n"
                      f"Disk: {disk_gb:.0f} GB | OS: {vm['guest_os']}\n"
                      f"Host: {vm['host']}\nFolder: {vm['folder']}\n"
                      f"IPs: {ips or 'N/A'}")
        })
        parent = host_ids.get(vm["host"], dc_id)
        edges.append({"from": parent, "to": vid})
        node_id += 1

    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/vms")
def api_vms():
    """All VMs with recommendation data joined and enrichment boosts applied."""
    d = _load_data()
    rec_map = {r["vm_name"]: r for r in d["recommendations"]}
    result = []
    for vm in d["vms"]:
        rec = dict(rec_map.get(vm["name"], {}))
        # Apply enrichment confidence boost if available
        enr = _enrichment_data.get(vm["name"])
        if enr and rec:
            boost = enr.get("confidence_boost", 0)
            base = rec.get("confidence_score", 50)
            rec["confidence_score"] = apply_enrichment_to_confidence(base, boost)
            rec["enrichment_boost"] = boost
            rec["enrichment_tool"] = enr.get("monitoring_tool", "")
        result.append({**vm, "recommendation": rec, "enrichment": enr})
    return jsonify(result)


@app.route("/api/hosts")
def api_hosts():
    return jsonify(_load_data()["hosts"])


@app.route("/api/fileshares")
def api_fileshares():
    """Return vCenter datastores reframed as file shares for migration."""
    ds_list = _load_data()["datastores"]
    return jsonify([{
        "name": ds["name"],
        "share_type": ds["type"].lower(),  # vmfs / nfs / vsan
        "protocol": "NFS" if ds["type"].upper() == "NFS" else "VMFS/Block",
        "capacity_gb": ds["capacity_gb"],
        "free_space_gb": ds["free_space_gb"],
        "datacenter": ds["datacenter"],
    } for ds in ds_list])


@app.route("/api/networks")
def api_networks():
    return jsonify(_load_data()["networks"])


@app.route("/api/recommendations")
def api_recommendations():
    return jsonify(_load_data()["recommendations"])


# ---------------------------------------------------------------------------
# Simulation API
# ---------------------------------------------------------------------------

# Azure VM SKU catalog for simulation recalculcations
VM_SKU_CATALOG = {
    "Standard_B1s":     {"vcpus": 1,  "mem_gb": 1,   "cost": 7.59},
    "Standard_B2s":     {"vcpus": 2,  "mem_gb": 4,   "cost": 30.37},
    "Standard_B2ms":    {"vcpus": 2,  "mem_gb": 8,   "cost": 60.74},
    "Standard_B4ms":    {"vcpus": 4,  "mem_gb": 16,  "cost": 121.47},
    "Standard_B8ms":    {"vcpus": 8,  "mem_gb": 32,  "cost": 242.94},
    "Standard_D2s_v5":  {"vcpus": 2,  "mem_gb": 8,   "cost": 70.08},
    "Standard_D4s_v5":  {"vcpus": 4,  "mem_gb": 16,  "cost": 140.16},
    "Standard_D8s_v5":  {"vcpus": 8,  "mem_gb": 32,  "cost": 280.32},
    "Standard_D16s_v5": {"vcpus": 16, "mem_gb": 64,  "cost": 560.64},
    "Standard_D32s_v5": {"vcpus": 32, "mem_gb": 128, "cost": 1121.28},
    "Standard_E2s_v5":  {"vcpus": 2,  "mem_gb": 16,  "cost": 91.98},
    "Standard_E4s_v5":  {"vcpus": 4,  "mem_gb": 32,  "cost": 183.96},
    "Standard_E8s_v5":  {"vcpus": 8,  "mem_gb": 64,  "cost": 367.92},
    "Standard_E16s_v5": {"vcpus": 16, "mem_gb": 128, "cost": 735.84},
    "Standard_E32s_v5": {"vcpus": 32, "mem_gb": 256, "cost": 1471.68},
    "Standard_F2s_v2":  {"vcpus": 2,  "mem_gb": 4,   "cost": 61.32},
    "Standard_F4s_v2":  {"vcpus": 4,  "mem_gb": 8,   "cost": 122.64},
    "Standard_F8s_v2":  {"vcpus": 8,  "mem_gb": 16,  "cost": 245.28},
    "Standard_F16s_v2": {"vcpus": 16, "mem_gb": 32,  "cost": 490.56},
}

REGION_MULTIPLIERS = {
    "eastus": 1.0,
    "westus2": 1.02,
    "westeurope": 1.15,
    "northeurope": 1.12,
    "southeastasia": 1.10,
    "centralindia": 0.88,
    "japaneast": 1.18,
    "australiaeast": 1.20,
    "uksouth": 1.14,
    "canadacentral": 1.05,
}

RI_DISCOUNTS = {
    "pay_as_you_go": 1.0,
    "1_year_ri": 0.62,
    "3_year_ri": 0.40,
    "savings_plan_1yr": 0.65,
    "savings_plan_3yr": 0.45,
}


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Run a what-if migration simulation.

    Body JSON:
    {
        "selected_vms": ["vm1", "vm2", ...] | "all",
        "target_region": "eastus",
        "pricing_model": "pay_as_you_go",
        "waves": 3,
        "override_skus": {"vm_name": "Standard_D4s_v5", ...}   # optional
    }
    """
    d = _load_data()
    body = request.get_json(force=True)

    selected = body.get("selected_vms", "all")
    region = body.get("target_region", "eastus")
    pricing = body.get("pricing_model", "pay_as_you_go")
    num_waves = max(1, min(10, body.get("waves", 3)))
    overrides = body.get("override_skus", {})

    # Auto-apply saved what-if overrides (manual overrides in request take precedence)
    # Store full override info (sku, region, pricing) per VM
    full_overrides: dict[str, dict] = {}
    for vm_name, ov in _whatif_overrides.items():
        if vm_name not in overrides:
            overrides[vm_name] = ov["sku"]
            full_overrides[vm_name] = ov

    region_mult = REGION_MULTIPLIERS.get(region, 1.0)
    ri_mult = RI_DISCOUNTS.get(pricing, 1.0)

    rec_map = {r["vm_name"]: r for r in d["recommendations"]}
    vm_map = {v["name"]: v for v in d["vms"]}

    # Filter VMs
    if selected == "all":
        target_vms = list(vm_map.keys())
    else:
        target_vms = [n for n in selected if n in vm_map]

    # Recalculate costs with region/pricing adjustments
    sim_results = []
    total_original = 0.0
    total_simulated = 0.0

    for name in target_vms:
        rec = rec_map.get(name, {})
        vm = vm_map[name]
        original_cost = rec.get("estimated_monthly_cost_usd", 0)
        total_original += original_cost

        sku_name = overrides.get(name, rec.get("recommended_vm_sku", ""))
        sku_info = VM_SKU_CATALOG.get(sku_name, {})
        vm_cost = sku_info.get("cost", original_cost) if sku_info else original_cost

        # Use per-VM region/pricing from what-if override if available
        vm_override = full_overrides.get(name)
        if vm_override:
            vm_region_mult = REGION_MULTIPLIERS.get(vm_override.get("region", region), 1.0)
            vm_ri_mult = RI_DISCOUNTS.get(vm_override.get("pricing", pricing), 1.0)
        else:
            vm_region_mult = region_mult
            vm_ri_mult = ri_mult
        adjusted_cost = round(vm_cost * vm_region_mult * vm_ri_mult, 2)
        total_simulated += adjusted_cost

        sim_results.append({
            "vm_name": name,
            "original_sku": rec.get("recommended_vm_sku", ""),
            "simulated_sku": sku_name,
            "original_cost": original_cost,
            "simulated_cost": adjusted_cost,
            "savings": round(original_cost - adjusted_cost, 2),
            "readiness": rec.get("migration_readiness", "Unknown"),
            "power_state": vm["power_state"],
            "vcpus": vm["num_cpus"],
            "memory_gb": vm["memory_mb"] // 1024,
            "disk_gb": vm["total_disk_gb"],
            "os_family": vm["guest_os_family"],
            "host": vm["host"],
            "folder": vm.get("folder", ""),
        })

    # Generate migration waves
    waves = _generate_waves(sim_results, num_waves)

    # Cost projection (12 months)
    monthly_projection = []
    cumulative = 0
    vms_migrated = 0
    for i in range(12):
        wave_idx = min(i, num_waves - 1)
        if i < num_waves:
            wave_vms = waves[i] if i < len(waves) else []
            vms_migrated += len(wave_vms)
            cumulative += sum(v["simulated_cost"] for v in wave_vms)
        monthly_projection.append({
            "month": i + 1,
            "azure_cost": round(cumulative, 2),
            "vms_on_azure": vms_migrated,
            "vms_on_prem": len(target_vms) - vms_migrated,
        })

    return jsonify({
        "region": region,
        "region_multiplier": region_mult,
        "pricing_model": pricing,
        "pricing_discount": ri_mult,
        "total_vms": len(target_vms),
        "total_original_monthly": round(total_original, 2),
        "total_simulated_monthly": round(total_simulated, 2),
        "total_savings_monthly": round(total_original - total_simulated, 2),
        "total_savings_annual": round((total_original - total_simulated) * 12, 2),
        "savings_percent": round((1 - total_simulated / total_original) * 100, 1) if total_original > 0 else 0,
        "waves": [[v["vm_name"] for v in w] for w in waves],
        "wave_details": [
            {
                "wave": i + 1,
                "vm_count": len(w),
                "cost": round(sum(v["simulated_cost"] for v in w), 2),
                "vms": w,
            }
            for i, w in enumerate(waves)
        ],
        "monthly_projection": monthly_projection,
        "vm_details": sim_results,
    })


def _generate_waves(vms: list[dict], num_waves: int) -> list[list[dict]]:
    """Split VMs into migration waves using a simple heuristic:
    Wave 1: powered-off VMs (low risk)
    Wave 2+: powered-on VMs sorted by readiness then cost (easy first)
    """
    off = [v for v in vms if v["power_state"] != "poweredOn"]
    on = [v for v in vms if v["power_state"] == "poweredOn"]

    # Sort powered-on VMs: Ready first, then by cost ascending
    readiness_order = {"Ready": 0, "Ready with conditions": 1, "Not Ready": 2, "Unknown": 3}
    on.sort(key=lambda v: (readiness_order.get(v["readiness"], 3), v["simulated_cost"]))

    waves: list[list[dict]] = []

    if off and num_waves > 1:
        waves.append(off)
        remaining_waves = num_waves - 1
    else:
        remaining_waves = num_waves
        if off:
            on = off + on  # put them in the regular waves

    # Split on VMs evenly into remaining waves
    chunk = max(1, math.ceil(len(on) / remaining_waves))
    for i in range(0, len(on), chunk):
        waves.append(on[i:i + chunk])

    return waves[:num_waves]


@app.route("/api/sku_catalog")
def api_sku_catalog():
    return jsonify(VM_SKU_CATALOG)


@app.route("/api/regions")
def api_regions():
    return jsonify(REGION_MULTIPLIERS)


@app.route("/api/pricing_models")
def api_pricing_models():
    return jsonify(RI_DISCOUNTS)


# ---------------------------------------------------------------------------
# What-If Overrides Store
# ---------------------------------------------------------------------------

@app.route("/api/whatif_overrides", methods=["GET"])
def api_get_whatif_overrides():
    """Return all saved what-if overrides."""
    return jsonify(_whatif_overrides)


@app.route("/api/whatif_overrides", methods=["POST"])
def api_save_whatif_override():
    """Save a what-if override for one VM.

    Body JSON: { "vm_name": "...", "sku": "...", "region": "...", "pricing": "..." }
    """
    body = request.get_json(force=True)
    vm_name = body.get("vm_name", "")
    if not vm_name:
        return jsonify({"error": "vm_name required"}), 400
    _whatif_overrides[vm_name] = {
        "sku": body.get("sku", ""),
        "region": body.get("region", "eastus"),
        "pricing": body.get("pricing", "pay_as_you_go"),
    }
    _save_json(_WHATIF_OVERRIDES_FILE, _whatif_overrides)
    return jsonify({"status": "saved", "vm_name": vm_name, "total_overrides": len(_whatif_overrides)})


@app.route("/api/whatif_overrides/<vm_name>", methods=["DELETE"])
def api_delete_whatif_override(vm_name: str):
    """Remove a single VM override."""
    _whatif_overrides.pop(vm_name, None)
    _save_json(_WHATIF_OVERRIDES_FILE, _whatif_overrides)
    return jsonify({"status": "deleted", "vm_name": vm_name})


@app.route("/api/whatif_overrides", methods=["DELETE"])
def api_clear_whatif_overrides():
    """Clear all overrides."""
    _whatif_overrides.clear()
    _save_json(_WHATIF_OVERRIDES_FILE, _whatif_overrides)
    return jsonify({"status": "cleared"})


@app.route("/api/simulate_comparison", methods=["POST"])
def api_simulate_comparison():
    """Run a side-by-side comparison: original recommendation vs saved what-if overrides.

    Returns for each VM that has a saved override:
    - original SKU, cost, region, pricing
    - what-if SKU, cost, region, pricing
    - delta cost
    Also returns aggregate totals for all VMs (original fleet cost vs adjusted).
    """
    d = _load_data()
    if not d:
        return jsonify({"error": "No data loaded"}), 400

    rec_map = {r["vm_name"]: r for r in d["recommendations"]}
    vm_map = {v["name"]: v for v in d["vms"]}

    comparisons = []
    total_original = 0.0
    total_whatif = 0.0
    total_fleet_original = d.get("total_monthly_cost_usd", 0)

    # Calculate fleet cost with overrides applied
    total_fleet_adjusted = 0.0
    for vm in d["vms"]:
        rec = rec_map.get(vm["name"], {})
        base = rec.get("estimated_monthly_cost_usd", 0)
        ov = _whatif_overrides.get(vm["name"])
        if ov:
            sku_info = VM_SKU_CATALOG.get(ov["sku"], {})
            region_mult = REGION_MULTIPLIERS.get(ov.get("region", "eastus"), 1.0)
            pricing_mult = RI_DISCOUNTS.get(ov.get("pricing", "pay_as_you_go"), 1.0)
            disk_type = rec.get("recommended_disk_type", "Standard SSD")
            disk_gb = rec.get("recommended_disk_size_gb", 32)
            disk_cost = disk_gb * DISK_COST_PER_GB.get(disk_type, 0.04)
            vm_cost = sku_info.get("cost", base) if sku_info else base
            adjusted = round(vm_cost * region_mult * pricing_mult + disk_cost, 2)
            total_fleet_adjusted += adjusted
        else:
            total_fleet_adjusted += base

    # Build per-VM comparison for overridden VMs only
    for vm_name, ov in _whatif_overrides.items():
        rec = rec_map.get(vm_name, {})
        vm = vm_map.get(vm_name)
        if not vm or not rec:
            continue

        orig_cost = rec.get("estimated_monthly_cost_usd", 0)
        orig_sku = rec.get("recommended_vm_sku", "")
        orig_disk = rec.get("recommended_disk_type", "Standard SSD")
        disk_gb = rec.get("recommended_disk_size_gb", 32)
        disk_cost = disk_gb * DISK_COST_PER_GB.get(orig_disk, 0.04)

        sku_info = VM_SKU_CATALOG.get(ov["sku"], {})
        region_mult = REGION_MULTIPLIERS.get(ov.get("region", "eastus"), 1.0)
        pricing_mult = RI_DISCOUNTS.get(ov.get("pricing", "pay_as_you_go"), 1.0)
        vm_cost = sku_info.get("cost", orig_cost) if sku_info else orig_cost
        whatif_cost = round(vm_cost * region_mult * pricing_mult + disk_cost, 2)

        total_original += orig_cost
        total_whatif += whatif_cost

        comparisons.append({
            "vm_name": vm_name,
            "vcpus": vm["num_cpus"],
            "memory_gb": vm["memory_mb"] // 1024,
            "os_family": vm["guest_os_family"],
            "original_sku": orig_sku,
            "original_region": "eastus",
            "original_pricing": "pay_as_you_go",
            "original_cost": orig_cost,
            "whatif_sku": ov["sku"],
            "whatif_region": ov.get("region", "eastus"),
            "whatif_pricing": ov.get("pricing", "pay_as_you_go"),
            "whatif_cost": whatif_cost,
            "delta": round(orig_cost - whatif_cost, 2),
        })

    comparisons.sort(key=lambda c: c["delta"], reverse=True)

    return jsonify({
        "total_overrides": len(_whatif_overrides),
        "total_vms": len(d["vms"]),
        "overridden_original_monthly": round(total_original, 2),
        "overridden_whatif_monthly": round(total_whatif, 2),
        "overridden_savings_monthly": round(total_original - total_whatif, 2),
        "fleet_original_monthly": round(total_fleet_original, 2),
        "fleet_adjusted_monthly": round(total_fleet_adjusted, 2),
        "fleet_savings_monthly": round(total_fleet_original - total_fleet_adjusted, 2),
        "fleet_savings_pct": round((1 - total_fleet_adjusted / total_fleet_original) * 100, 1) if total_fleet_original > 0 else 0,
        "comparisons": comparisons,
    })


# ---------------------------------------------------------------------------
# Individual VM What-If Analysis
# ---------------------------------------------------------------------------

DISK_COST_PER_GB = {
    "Standard SSD": 0.04,
    "Premium SSD": 0.10,
    "Standard HDD": 0.02,
}


@app.route("/api/simulate_vm", methods=["POST"])
def api_simulate_vm():
    """Run what-if analysis for a single VM.

    Body JSON: { "vm_name": "WindowsVM175" }

    Returns the VM's current recommendation plus cost comparisons
    across all SKUs, regions, and pricing models.
    """
    d = _load_data()
    body = request.get_json(force=True)
    vm_name = body.get("vm_name", "")

    vm = next((v for v in d["vms"] if v["name"] == vm_name), None)
    rec = next((r for r in d["recommendations"] if r["vm_name"] == vm_name), None)
    if not vm or not rec:
        return jsonify({"error": "VM not found"}), 404

    current_sku = rec["recommended_vm_sku"]
    current_disk_type = rec.get("recommended_disk_type", "Standard SSD")
    disk_gb = rec.get("recommended_disk_size_gb", 32)
    disk_cost = disk_gb * DISK_COST_PER_GB.get(current_disk_type, 0.04)

    # Build cost matrix: every SKU x every region x every pricing model
    sku_comparisons = []
    for sku_name, info in VM_SKU_CATALOG.items():
        fits = (info["vcpus"] >= vm["num_cpus"]
                and info["mem_gb"] >= vm["memory_mb"] / 1024)
        base_cost = info["cost"]

        region_costs = {}
        for region, rmult in REGION_MULTIPLIERS.items():
            pricing_costs = {}
            for pricing, pmult in RI_DISCOUNTS.items():
                pricing_costs[pricing] = round(base_cost * rmult * pmult + disk_cost, 2)
            region_costs[region] = pricing_costs

        sku_comparisons.append({
            "sku": sku_name,
            "family": sku_name.split("_")[1] if "_" in sku_name else "",
            "vcpus": info["vcpus"],
            "memory_gb": info["mem_gb"],
            "base_cost": base_cost,
            "fits_vm": fits,
            "is_current": sku_name == current_sku,
            "region_costs": region_costs,
        })

    # Quick summary: current vs cheapest fitting
    fitting = [s for s in sku_comparisons if s["fits_vm"]]
    cheapest_payg = min(fitting, key=lambda s: s["base_cost"]) if fitting else None
    cheapest_3yr = min(
        fitting,
        key=lambda s: s["region_costs"]["eastus"]["3_year_ri"]
    ) if fitting else None

    # Perf history stats
    vm_perf_samples = _perf_history.get(vm["name"], [])
    perf_stats = {}
    if vm_perf_samples:
        perf_stats = {
            "cpu": _compute_perf_stats(vm_perf_samples, "cpu_pct"),
            "mem": _compute_perf_stats(vm_perf_samples, "mem_pct"),
            "disk_iops": _compute_perf_stats(vm_perf_samples, "disk_iops"),
            "disk_read_kbps": _compute_perf_stats(vm_perf_samples, "disk_read_kbps"),
            "disk_write_kbps": _compute_perf_stats(vm_perf_samples, "disk_write_kbps"),
            "net_rx_kbps": _compute_perf_stats(vm_perf_samples, "net_rx_kbps"),
            "net_tx_kbps": _compute_perf_stats(vm_perf_samples, "net_tx_kbps"),
            "sample_count": len(vm_perf_samples),
        }

    return jsonify({
        "vm": {
            "name": vm["name"],
            "vcenter_id": vm["vcenter_id"],
            "num_cpus": vm["num_cpus"],
            "memory_mb": vm["memory_mb"],
            "memory_gb": vm["memory_mb"] // 1024,
            "total_disk_gb": vm["total_disk_gb"],
            "power_state": vm["power_state"],
            "guest_os": vm["guest_os"],
            "guest_os_family": vm["guest_os_family"],
            "host": vm["host"],
            "folder": vm.get("folder", ""),
            "datacenter": vm.get("datacenter", ""),
            "annotation": vm.get("annotation", ""),
            "tools_status": vm.get("tools_status", ""),
            "disks": vm.get("disks", []),
            "nics": vm.get("nics", []),
            "perf": vm.get("perf", {}),
        },
        "perf_stats": perf_stats,
        "perf_history": vm_perf_samples[-20:],  # last 20 samples for sparkline
        "current_recommendation": rec,
        "disk_cost": round(disk_cost, 2),
        "sku_comparisons": sku_comparisons,
        "cheapest_payg": cheapest_payg["sku"] if cheapest_payg else None,
        "cheapest_3yr": cheapest_3yr["sku"] if cheapest_3yr else None,
        "regions": REGION_MULTIPLIERS,
        "pricing_models": RI_DISCOUNTS,
    })


# ---------------------------------------------------------------------------
# Workload Discovery API
# ---------------------------------------------------------------------------

def _batch_dns_resolve(hostnames: list[str], timeout_per: float = 1.5,
                       max_workers: int = 20) -> dict[str, str]:
    """Resolve many hostnames in parallel. Returns {hostname: ip} for successes."""
    import socket
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

    results: dict[str, str] = {}
    unique = list(set(h for h in hostnames if h))
    if not unique:
        return results

    def _resolve(hn: str) -> tuple[str, str]:
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout_per)
            ip = socket.gethostbyname(hn)
            return (hn, ip if ip and not ip.startswith("127.") else "")
        except (socket.gaierror, OSError):
            return (hn, "")
        finally:
            socket.setdefaulttimeout(old_timeout)

    with ThreadPoolExecutor(max_workers=min(max_workers, len(unique))) as ex:
        futs = {ex.submit(_resolve, hn): hn for hn in unique}
        try:
            for fut in as_completed(futs, timeout=min(15, max(5, len(unique) * 0.1))):
                try:
                    hn, ip = fut.result(timeout=0.1)
                    if ip:
                        results[hn] = ip
                except Exception:
                    pass
        except TimeoutError:
            pass  # hit global cap — return what we have

    return results


def _resolve_all_vm_ips(vms: list[dict], manual_map: dict,
                        try_dns: bool = True) -> dict[str, str]:
    """Resolve IPs for all VMs. Returns {vm_name: ip}.

    Priority per VM:
    1. Manual IP mapping
    2. NIC IP from VMware Tools
    3. DNS of guest_hostname (batch)
    4. DNS of VM name (batch)
    """
    resolved: dict[str, str] = {}
    need_dns_hostname: list[tuple[str, str]] = []  # [(vm_name, hostname)]
    need_dns_vmname: list[str] = []

    for vm in vms:
        vm_name = vm["name"]

        # 1. Manual mapping
        manual_ip = manual_map.get(vm_name, "")
        if not manual_ip:
            for k, v in manual_map.items():
                if k.lower() == vm_name.lower():
                    manual_ip = v
                    break
        if manual_ip:
            resolved[vm_name] = manual_ip
            continue

        # 2. NIC IP
        nic_ip = ""
        for nic in vm.get("nics", []):
            for addr in nic.get("ip_addresses", []):
                if addr and ":" not in addr:
                    nic_ip = addr
                    break
            if nic_ip:
                break
        if nic_ip:
            resolved[vm_name] = nic_ip
            continue

        # Queue for DNS
        guest_hn = (vm.get("guest_hostname", "") or "").strip()
        if guest_hn:
            need_dns_hostname.append((vm_name, guest_hn))
        else:
            need_dns_vmname.append(vm_name)

    # 3 & 4. Batch DNS resolution
    if try_dns and (need_dns_hostname or need_dns_vmname):
        all_names = [hn for _, hn in need_dns_hostname] + need_dns_vmname
        dns_results = _batch_dns_resolve(all_names)

        for vm_name, guest_hn in need_dns_hostname:
            if guest_hn in dns_results:
                resolved[vm_name] = dns_results[guest_hn]
            elif vm_name not in resolved:
                need_dns_vmname.append(vm_name)

        for vm_name in need_dns_vmname:
            if vm_name in dns_results and vm_name not in resolved:
                resolved[vm_name] = dns_results[vm_name]

    return resolved


@app.route("/api/workloads/discover", methods=["POST"])
def api_workload_discover():
    """Start guest-level workload discovery.

    Body JSON:
    {
        "linux_credentials": [{"username": "...", "password": "...", "port": 22}, ...],
        "windows_credentials": [{"username": "...", "password": "...", "port": 5985}, ...],
        "database_credentials": [{"engine": "mysql|postgresql|mssql|mongodb|redis|auto",
                                   "username": "...", "password": "...", "port": 3306}, ...],
        "vm_selection": "all" | "powered_on" | ["vm1","vm2"],
        "max_workers": 5,
        "ip_mappings": {"VM-Name": "10.0.0.1", ...}  // optional manual overrides
    }

    Also supports legacy single-credential format:
        "linux_username": "...", "linux_password": "...", "linux_port": 22
    """
    global _workload_discoverer, _workload_data

    d = _load_data()
    if not d:
        return jsonify({"error": "No vCenter data loaded. Connect or upload first."}), 400

    if _workload_discoverer and _workload_discoverer.progress.get("status") == "running":
        return jsonify({"error": "Workload discovery already in progress"}), 409

    body = request.get_json(force=True)

    # Build credentials — support both single (legacy) and multi-credential formats
    linux_creds: list[Credential] = []
    win_creds: list[Credential] = []

    # New multi-credential format
    for c in body.get("linux_credentials", []):
        if c.get("username"):
            linux_creds.append(Credential(
                username=c["username"],
                password=c.get("password", ""),
                port=int(c.get("port", 22)),
            ))
    for c in body.get("windows_credentials", []):
        if c.get("username"):
            win_creds.append(Credential(
                username=c["username"],
                password=c.get("password", ""),
                port=int(c.get("port", 5985)),
            ))

    # Legacy single-credential format (backward compat)
    if not linux_creds and body.get("linux_username"):
        linux_creds.append(Credential(
            username=body["linux_username"],
            password=body.get("linux_password", ""),
            port=int(body.get("linux_port", 22)),
        ))
    if not win_creds and body.get("windows_username"):
        win_creds.append(Credential(
            username=body["windows_username"],
            password=body.get("windows_password", ""),
            port=int(body.get("windows_port", 5985)),
        ))

    if not linux_creds and not win_creds:
        return jsonify({"error": "Provide at least Linux or Windows credentials"}), 400

    # Parse database credentials for deep DB probing
    db_creds: list[DatabaseCredential] = []
    for c in body.get("database_credentials", []):
        if c.get("username"):
            db_creds.append(DatabaseCredential(
                engine=c.get("engine", "auto"),
                username=c["username"],
                password=c.get("password", ""),
                port=int(c.get("port", 0)),
                host=c.get("host", ""),
            ))

    # Parse manual IP mappings
    manual_map: dict[str, str] = body.get("ip_mappings", {})

    # Build VM target list
    vms = d.get("vms", [])
    selection = body.get("vm_selection", "powered_on")

    if isinstance(selection, list):
        selected_vms = [v for v in vms if v["name"] in selection]
    elif selection == "all":
        selected_vms = vms
    elif selection == "powered_on":
        selected_vms = [v for v in vms if v["power_state"] == "poweredOn"]
    elif selection == "linux":
        selected_vms = [v for v in vms if v["power_state"] == "poweredOn"
                        and v.get("guest_os_family") == "linux"]
    elif selection == "windows":
        selected_vms = [v for v in vms if v["power_state"] == "poweredOn"
                        and v.get("guest_os_family") == "windows"]
    else:
        selected_vms = [v for v in vms if v["power_state"] == "poweredOn"]

    # Build targets: (vm_name, ip, os_family) — use multi-strategy IP resolution
    try_dns = body.get("try_dns", False)  # DNS off by default (slow on Windows)
    ip_map = _resolve_all_vm_ips(selected_vms, manual_map, try_dns=try_dns)

    targets = []
    skipped = []
    for vm in selected_vms:
        ip = ip_map.get(vm["name"], "")
        if not ip:
            skipped.append(vm["name"])
            continue
        os_fam = vm.get("guest_os_family", "linux")
        targets.append({"name": vm["name"], "ip": ip, "os_family": os_fam})

    if not targets:
        msg = (f"No reachable VMs found. Tried: NIC IPs, DNS of guest_hostname, "
               f"DNS of VM name. {len(skipped)} VMs had no resolvable IP. "
               f"Use the IP Mappings field to manually map VM names to IPs.")
        return jsonify({"error": msg, "skipped_vms": skipped[:20]}), 400

    _workload_discoverer = GuestDiscoverer()
    max_workers = int(body.get("max_workers", 5))

    def _run_workload_discovery():
        global _workload_data
        try:
            result = _workload_discoverer.discover_all(
                targets, linux_creds, win_creds,
                db_creds=db_creds if db_creds else None,
                max_workers=max_workers,
            )
            # Generate recommendations
            recs = generate_workload_recommendations(result)

            # Serialize to dict
            from dataclasses import asdict as _asdict
            result_dict = _asdict(result)
            recs_list = [_asdict(r) for r in recs]

            # Normalise via JSON round-trip
            result_dict = json.loads(json.dumps(result_dict, default=str))
            recs_list = json.loads(json.dumps(recs_list, default=str))

            _workload_data = {
                "result": result_dict,
                "recommendations": recs_list,
                "total_workload_cost": round(
                    sum(r.estimated_monthly_cost_usd for r in recs), 2
                ),
            }
            # Persist to data/
            _save_json(_WORKLOAD_DATA_FILE, _workload_data)
            # Merge network + file share recommendations from vCenter
            _merge_infra_recommendations()
        except Exception as exc:
            logger.exception("Workload discovery failed")
            _workload_discoverer.progress.update({
                "status": "error", "message": str(exc), "progress": 0,
            })

    threading.Thread(target=_run_workload_discovery, daemon=True).start()
    return jsonify({"status": "started", "targets": len(targets), "skipped": len(skipped)})


@app.route("/api/databases/discover", methods=["POST"])
def api_database_discover():
    """Discover databases by connecting directly to DB servers (no SSH/WinRM needed).

    Body JSON:
    {
        "targets": [
            {"host": "10.0.0.5", "engine": "mysql", "username": "root", "password": "...", "port": 3306},
            {"host": "10.0.0.6", "engine": "auto", "username": "admin", "password": "...", "port": 0},
            ...
        ]
    }
    """
    body = request.get_json(force=True)
    targets = body.get("targets", [])
    if not targets:
        return jsonify({"error": "Provide at least one database target"}), 400

    results = []
    for t in targets:
        host = t.get("host", "").strip()
        if not host:
            continue
        db_cred = DatabaseCredential(
            engine=t.get("engine", "auto"),
            username=t.get("username", ""),
            password=t.get("password", ""),
            port=int(t.get("port", 0)),
            host=host,
        )
        discovered = deep_probe_databases(host, [db_cred])
        from dataclasses import asdict as _asdict
        for db in discovered:
            d = _asdict(db)
            d = json.loads(json.dumps(d, default=str))
            d["host"] = host
            results.append(d)

    return jsonify({"databases": results, "total": len(results)})


@app.route("/api/workloads/status")
def api_workload_status():
    """Poll workload discovery progress."""
    if not _workload_discoverer:
        return jsonify({"status": "idle", "message": "", "progress": 0})
    return jsonify(_workload_discoverer.progress)


@app.route("/api/workloads/results")
def api_workload_results():
    """Return discovered workloads and recommendations with enrichment boosts."""
    if not _workload_data:
        return jsonify({"error": "No workload data. Run discovery first."}), 404

    # Apply enrichment boosts to workload recommendation confidence
    data = dict(_workload_data)
    if _enrichment_data and "recommendations" in data:
        boosted_recs = []
        for rec in data["recommendations"]:
            rec = dict(rec)
            vm_name = rec.get("vm_name", "")
            enr = _enrichment_data.get(vm_name)
            if enr:
                boost = enr.get("confidence_boost", 0)
                # Workload recs use 'confidence' not 'confidence_score'
                base = rec.get("confidence", 50)
                rec["confidence"] = apply_enrichment_to_confidence(base, boost)
                rec["enrichment_boost"] = boost
                rec["enrichment_tool"] = enr.get("monitoring_tool", "")
            boosted_recs.append(rec)
        data["recommendations"] = boosted_recs

    return jsonify(data)


@app.route("/api/workloads/topology")
def api_workload_topology():
    """Return vis.js nodes and edges for the workload dependency graph."""
    if not _workload_data:
        return jsonify({"nodes": [], "edges": []})

    result = _workload_data.get("result", {})
    nodes = []
    edges = []
    nid = 0

    vm_node_map = {}  # vm_name -> node_id

    for vmw in result.get("vm_workloads", []):
        vm_name = vmw["vm_name"]
        # VM node
        vm_nid = nid
        vm_node_map[vm_name] = vm_nid
        nodes.append({
            "id": vm_nid, "label": vm_name[:18], "group": "vm",
            "title": f"VM: {vm_name}",
        })
        nid += 1

        # Database nodes
        for db in vmw.get("databases", []):
            db_nid = nid
            label = f"{db['engine']}:{db.get('instance_name','')}"
            nodes.append({
                "id": db_nid, "label": label[:22], "group": "database",
                "title": f"Database: {db['engine']}\nVersion: {db.get('version','?')}\nPort: {db.get('port','?')}\nDatabases: {', '.join(db.get('databases',[])[:5])}",
            })
            edges.append({"from": vm_nid, "to": db_nid, "color": {"color": "#f59e0b"}, "width": 2})
            nid += 1

        # Web app nodes
        for wa in vmw.get("web_apps", []):
            wa_nid = nid
            label = f"{wa.get('framework','') or wa['runtime']}:{wa.get('port','')}"
            nodes.append({
                "id": wa_nid, "label": label[:22], "group": "webapp",
                "title": f"Web App: {wa['runtime']}\nFramework: {wa.get('framework','?')}\nVersion: {wa.get('runtime_version','?')}\nPort: {wa.get('port','?')}",
            })
            edges.append({"from": vm_nid, "to": wa_nid, "color": {"color": "#10b981"}, "width": 2})
            nid += 1

        # Container runtime nodes
        for cr in vmw.get("container_runtimes", []):
            cr_nid = nid
            label = f"{cr['runtime']} ({cr.get('running_containers',0)} cont)"
            nodes.append({
                "id": cr_nid, "label": label[:22], "group": "container",
                "title": f"Container Runtime: {cr['runtime']}\nVersion: {cr.get('version','?')}\nRunning: {cr.get('running_containers',0)}/{cr.get('total_containers',0)}",
            })
            edges.append({"from": vm_nid, "to": cr_nid, "color": {"color": "#06b6d4"}, "width": 2})
            nid += 1

        # Orchestrator nodes
        for orch in vmw.get("orchestrators", []):
            orch_nid = nid
            label = f"{orch['type']} ({orch.get('role','?')})"
            nodes.append({
                "id": orch_nid, "label": label[:22], "group": "orchestrator",
                "title": f"Orchestrator: {orch['type']}\nVersion: {orch.get('version','?')}\nRole: {orch.get('role','?')}\nNodes: {orch.get('node_count',0)}\nPods: {orch.get('pod_count',0)}",
            })
            edges.append({"from": vm_nid, "to": orch_nid, "color": {"color": "#a855f7"}, "width": 2})
            nid += 1

    # Dependency edges between VMs
    for dep in result.get("dependencies", []):
        src_nid = vm_node_map.get(dep.get("source_vm"))
        tgt_nid = vm_node_map.get(dep.get("target_vm"))
        if src_nid is not None and tgt_nid is not None:
            edges.append({
                "from": src_nid, "to": tgt_nid,
                "arrows": "to", "dashes": True,
                "color": {"color": "#ef4444"},
                "title": f"{dep.get('source_workload','')} → {dep.get('target_workload','')} (port {dep.get('port','')})",
                "width": 1.5,
            })

    # Add network and file share nodes from vCenter discovery
    try:
        d = _load_data()
        # Networks — connect to VMs that use them
        vm_nic_map: dict[str, set[str]] = {}  # network_name → {vm_names}
        for vm in d.get("vms", []):
            for nic in vm.get("nics", []):
                nn = nic.get("network_name", "")
                if nn:
                    vm_nic_map.setdefault(nn, set()).add(vm["name"])

        for net in d.get("networks", []):
            net_nid = nid
            label = net["name"]
            vlan_info = f"VLAN {net.get('vlan_id', 0)}" if net.get("vlan_id") else "No VLAN"
            connected = vm_nic_map.get(net["name"], set())
            nodes.append({
                "id": net_nid, "label": label[:22], "group": "network",
                "title": f"Network: {net['name']}\nType: {net.get('network_type','?')}\n{vlan_info}\nDC: {net.get('datacenter','?')}\nConnected VMs: {len(connected)}",
            })
            # Edges from network to connected VMs
            for vm_name in connected:
                if vm_name in vm_node_map:
                    edges.append({
                        "from": net_nid, "to": vm_node_map[vm_name],
                        "color": {"color": "#e879f9"}, "width": 1, "dashes": [4, 4],
                    })
            nid += 1

        # File Shares (from datastores) — connect to VMs that have disks on them
        vm_ds_map: dict[str, set[str]] = {}  # datastore_name → {vm_names}
        for vm in d.get("vms", []):
            for disk in vm.get("disks", []):
                dn = disk.get("datastore_name", "")
                if dn:
                    vm_ds_map.setdefault(dn, set()).add(vm["name"])

        for ds in d.get("datastores", []):
            ds_nid = nid
            label = ds["name"]
            used = round((ds.get("capacity_gb", 0) or 0) - (ds.get("free_space_gb", 0) or 0))
            connected = vm_ds_map.get(ds["name"], set())
            nodes.append({
                "id": ds_nid, "label": label[:22], "group": "fileshare",
                "title": f"File Share: {ds['name']}\nType: {ds.get('type','?')}\nCapacity: {round(ds.get('capacity_gb',0))} GB\nUsed: {used} GB\nDC: {ds.get('datacenter','?')}\nVMs using: {len(connected)}",
            })
            for vm_name in connected:
                if vm_name in vm_node_map:
                    edges.append({
                        "from": ds_nid, "to": vm_node_map[vm_name],
                        "color": {"color": "#fb923c"}, "width": 1, "dashes": [4, 4],
                    })
            nid += 1
    except Exception:
        pass  # vCenter data might not be loaded

    return jsonify({"nodes": nodes, "edges": edges})


# ---------------------------------------------------------------------------
# Workload What-If Analysis
# ---------------------------------------------------------------------------

from digital_twin_migrate.workload_mapping import (
    DB_SERVICE_MAP, WEBAPP_SERVICE_MAP, CONTAINER_SERVICE_MAP,
    ORCHESTRATOR_SERVICE_MAP, NETWORK_SERVICE_MAP, FILESHARE_SERVICE_MAP,
    AzureServiceOption,
)

# Workload-level region multipliers (PaaS pricing varies less than IaaS)
WL_REGION_MULTIPLIERS = {
    "eastus": 1.0, "westus2": 1.02, "westeurope": 1.12, "northeurope": 1.10,
    "southeastasia": 1.08, "centralindia": 0.90, "japaneast": 1.15,
    "australiaeast": 1.18, "uksouth": 1.12, "canadacentral": 1.04,
}

WL_PRICING_DISCOUNTS = {
    "pay_as_you_go": 1.0, "1_year_ri": 0.65, "3_year_ri": 0.45,
    "dev_test": 0.55, "enterprise_agreement": 0.80,
}


def _get_workload_service_options(source_engine: str, workload_type: str) -> list[dict]:
    """Look up all Azure service alternatives for a workload engine."""
    options: list[AzureServiceOption] = []
    source_lower = source_engine.lower()

    if workload_type == "database":
        for engine_enum, opts in DB_SERVICE_MAP.items():
            if engine_enum.value.lower() == source_lower:
                options = opts
                break
    elif workload_type == "webapp":
        for runtime_enum, opts in WEBAPP_SERVICE_MAP.items():
            if runtime_enum.value.lower() == source_lower:
                options = opts
                break
    elif workload_type == "container":
        for rt_enum, opts in CONTAINER_SERVICE_MAP.items():
            if rt_enum.value.lower() == source_lower:
                options = opts
                break
    elif workload_type == "orchestrator":
        for orch_enum, opts in ORCHESTRATOR_SERVICE_MAP.items():
            if orch_enum.value.lower() == source_lower:
                options = opts
                break
    elif workload_type == "network":
        options = NETWORK_SERVICE_MAP.get(source_lower, NETWORK_SERVICE_MAP.get("standard", []))
    elif workload_type == "fileshare":
        options = FILESHARE_SERVICE_MAP.get(source_lower, FILESHARE_SERVICE_MAP.get("vmfs", []))

    return [{
        "name": o.name,
        "display": o.display,
        "category": o.category,
        "sku_tier": o.sku_tier,
        "base_cost": o.estimated_monthly_usd,
        "migration_approach": o.migration_approach,
        "complexity": o.complexity,
    } for o in options]


@app.route("/api/workloads/whatif", methods=["POST"])
def api_workload_whatif():
    """Get what-if analysis for a specific workload recommendation."""
    if not _workload_data:
        return jsonify({"error": "No workload data. Run discovery first."}), 404

    body = request.get_json(force=True)
    workload_key = body.get("workload_key", "")

    recs = _workload_data.get("recommendations", [])
    rec = None
    for r in recs:
        key = f"{r['vm_name']}::{r['workload_name']}"
        if key == workload_key:
            rec = r
            break

    if not rec:
        return jsonify({"error": "Workload not found"}), 404

    # Get all service alternatives
    alternatives = _get_workload_service_options(
        rec.get("source_engine", ""), rec.get("workload_type", "")
    )

    # Compute cost matrix: each service x each region x each pricing
    service_costs = []
    for svc in alternatives:
        pricing_costs = {}
        for pm_name, pm_mult in WL_PRICING_DISCOUNTS.items():
            region_costs = {}
            for rg_name, rg_mult in WL_REGION_MULTIPLIERS.items():
                region_costs[rg_name] = round(svc["base_cost"] * rg_mult * pm_mult, 2)
            pricing_costs[pm_name] = region_costs
        service_costs.append({
            **svc,
            "costs": pricing_costs,
        })

    # Check for saved override
    saved_override = _workload_whatif_overrides.get(workload_key)

    return jsonify({
        "recommendation": rec,
        "service_options": service_costs,
        "regions": WL_REGION_MULTIPLIERS,
        "pricing_models": WL_PRICING_DISCOUNTS,
        "saved_override": saved_override,
    })


@app.route("/api/workloads/whatif_overrides", methods=["GET"])
def api_get_workload_whatif_overrides():
    """Return all saved workload what-if overrides."""
    return jsonify(_workload_whatif_overrides)


@app.route("/api/workloads/whatif_overrides", methods=["POST"])
def api_save_workload_whatif_override():
    """Save a workload what-if override."""
    body = request.get_json(force=True)
    key = body.get("workload_key", "")
    if not key:
        return jsonify({"error": "workload_key required"}), 400
    _workload_whatif_overrides[key] = {
        "service": body.get("service", ""),
        "service_display": body.get("service_display", ""),
        "region": body.get("region", "eastus"),
        "pricing": body.get("pricing", "pay_as_you_go"),
        "cost": body.get("cost", 0),
    }
    _save_json(_WL_WHATIF_OVERRIDES_FILE, _workload_whatif_overrides)
    return jsonify({"status": "saved", "workload_key": key,
                    "total_overrides": len(_workload_whatif_overrides)})


@app.route("/api/workloads/whatif_overrides/<path:workload_key>", methods=["DELETE"])
def api_delete_workload_whatif_override(workload_key: str):
    """Remove a single workload override."""
    _workload_whatif_overrides.pop(workload_key, None)
    _save_json(_WL_WHATIF_OVERRIDES_FILE, _workload_whatif_overrides)
    return jsonify({"status": "deleted", "workload_key": workload_key})


@app.route("/api/workloads/whatif_overrides", methods=["DELETE"])
def api_clear_workload_whatif_overrides():
    """Clear all workload overrides."""
    _workload_whatif_overrides.clear()
    _save_json(_WL_WHATIF_OVERRIDES_FILE, _workload_whatif_overrides)
    return jsonify({"status": "cleared"})


# ---------------------------------------------------------------------------
# Workload Simulation Engine
# ---------------------------------------------------------------------------

@app.route("/api/workloads/simulate", methods=["POST"])
def api_workload_simulate():
    """Run a workload migration simulation.

    Body JSON:
    {
        "target_region": "eastus",
        "pricing_model": "pay_as_you_go",
        "waves": 3,
        "workload_filter": "all"  // all | database | webapp | container | network | fileshare
    }
    """
    if not _workload_data:
        return jsonify({"error": "No workload data. Run discovery first."}), 404

    body = request.get_json(force=True)
    region = body.get("target_region", "eastus")
    pricing = body.get("pricing_model", "pay_as_you_go")
    num_waves = max(1, min(8, body.get("waves", 3)))
    wl_filter = body.get("workload_filter", "all")

    region_mult = WL_REGION_MULTIPLIERS.get(region, 1.0)
    pricing_mult = WL_PRICING_DISCOUNTS.get(pricing, 1.0)

    recs = _workload_data.get("recommendations", [])

    # Filter workloads
    if wl_filter != "all":
        if wl_filter == "container":
            recs = [r for r in recs if r.get("workload_type", "") in ("container", "orchestrator")]
        elif wl_filter == "network":
            recs = [r for r in recs if r.get("workload_type", "") == "network"]
        elif wl_filter == "fileshare":
            recs = [r for r in recs if r.get("workload_type", "") == "fileshare"]
        else:
            recs = [r for r in recs if r.get("workload_type", "") == wl_filter]

    # Compute simulated costs
    sim_results = []
    total_original = 0.0
    total_simulated = 0.0

    for rec in recs:
        original_cost = rec.get("estimated_monthly_cost_usd", 0) or 0
        total_original += original_cost

        wl_key = f"{rec['vm_name']}::{rec['workload_name']}"
        override = _workload_whatif_overrides.get(wl_key)

        if override:
            # Use overridden service cost
            simulated_cost = override.get("cost", original_cost)
        else:
            # Apply region + pricing multipliers to original cost
            simulated_cost = round(original_cost * region_mult * pricing_mult, 2)

        total_simulated += simulated_cost

        sim_results.append({
            "vm_name": rec.get("vm_name", ""),
            "workload_name": rec.get("workload_name", ""),
            "workload_type": rec.get("workload_type", ""),
            "source_engine": rec.get("source_engine", ""),
            "original_service": rec.get("recommended_azure_service", ""),
            "simulated_service": override.get("service_display", rec.get("recommended_azure_service", "")) if override else rec.get("recommended_azure_service", ""),
            "original_cost": original_cost,
            "simulated_cost": simulated_cost,
            "savings": round(original_cost - simulated_cost, 2),
            "migration_approach": rec.get("migration_approach", ""),
            "migration_complexity": rec.get("migration_complexity", ""),
            "has_override": bool(override),
        })

    # Generate migration waves by complexity: low first, then medium, then high
    complexity_order = {"low": 0, "medium": 1, "high": 2}
    sorted_results = sorted(sim_results, key=lambda x: (
        complexity_order.get(x["migration_complexity"], 3),
        x["simulated_cost"],
    ))

    waves: list[list[dict]] = []
    chunk = max(1, math.ceil(len(sorted_results) / num_waves))
    for i in range(0, len(sorted_results), chunk):
        waves.append(sorted_results[i:i + chunk])
    waves = waves[:num_waves]

    # Cost projection (12 months)
    monthly_projection = []
    cumulative = 0.0
    workloads_migrated = 0
    for i in range(12):
        if i < len(waves):
            wave_wls = waves[i]
            workloads_migrated += len(wave_wls)
            cumulative += sum(w["simulated_cost"] for w in wave_wls)
        monthly_projection.append({
            "month": i + 1,
            "azure_cost": round(cumulative, 2),
            "workloads_on_azure": workloads_migrated,
            "workloads_on_prem": len(sim_results) - workloads_migrated,
        })

    # Type summary
    type_summary = {}
    for sr in sim_results:
        t = sr["workload_type"]
        if t not in type_summary:
            type_summary[t] = {"count": 0, "original_cost": 0, "simulated_cost": 0}
        type_summary[t]["count"] += 1
        type_summary[t]["original_cost"] += sr["original_cost"]
        type_summary[t]["simulated_cost"] += sr["simulated_cost"]
    for v in type_summary.values():
        v["original_cost"] = round(v["original_cost"], 2)
        v["simulated_cost"] = round(v["simulated_cost"], 2)
        v["savings"] = round(v["original_cost"] - v["simulated_cost"], 2)

    return jsonify({
        "region": region,
        "region_multiplier": region_mult,
        "pricing_model": pricing,
        "pricing_discount": pricing_mult,
        "total_workloads": len(sim_results),
        "total_original_monthly": round(total_original, 2),
        "total_simulated_monthly": round(total_simulated, 2),
        "total_savings_monthly": round(total_original - total_simulated, 2),
        "total_savings_annual": round((total_original - total_simulated) * 12, 2),
        "savings_percent": round((1 - total_simulated / total_original) * 100, 1) if total_original > 0 else 0,
        "type_summary": type_summary,
        "wave_details": [
            {
                "wave": i + 1,
                "workload_count": len(w),
                "cost": round(sum(x["simulated_cost"] for x in w), 2),
                "workloads": w,
            }
            for i, w in enumerate(waves)
        ],
        "monthly_projection": monthly_projection,
        "workload_details": sim_results,
    })


@app.route("/api/data/files")
def api_data_files():
    """List available data files in the data/ folder."""
    files = []
    for p in DATA_DIR.iterdir():
        if p.suffix == ".json":
            stat = p.stat()
            files.append({
                "name": p.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": stat.st_mtime,
            })
    return jsonify(files)


# ---------------------------------------------------------------------------
# Performance Collection APIs
# ---------------------------------------------------------------------------

@app.route("/api/perf/status")
def api_perf_status():
    """Return status of the perf collector."""
    total_vm_samples = sum(len(s) for s in _perf_history.values())
    total_wl_samples = sum(len(s) for s in _workload_perf_history.values())
    return jsonify({
        **_perf_collector_state,
        "total_vm_samples": total_vm_samples,
        "total_workload_samples": total_wl_samples,
        "max_hours": PERF_HISTORY_MAX_HOURS,
        "max_samples": PERF_HISTORY_MAX_SAMPLES,
    })


@app.route("/api/perf/duration", methods=["POST"])
def api_perf_set_duration():
    """Change the perf collection rolling window.

    Body JSON: { "days": 1 | 7 | 30 }
    """
    body = request.get_json(force=True)
    days = int(body.get("days", 7))
    _set_perf_duration(days)
    return jsonify({"status": "ok", "duration_days": days,
                    "max_hours": PERF_HISTORY_MAX_HOURS,
                    "max_samples": PERF_HISTORY_MAX_SAMPLES})


@app.route("/api/perf/start", methods=["POST"])
def api_perf_start():
    """Start or restart the perf collector."""
    if _perf_collector_state["running"]:
        return jsonify({"status": "already_running"})
    _start_perf_collector()
    return jsonify({"status": "started"})


@app.route("/api/perf/stop", methods=["POST"])
def api_perf_stop():
    """Stop the perf collector."""
    _perf_collector_stop.set()
    return jsonify({"status": "stopping"})


@app.route("/api/perf/collect", methods=["POST"])
def api_perf_collect_now():
    """Trigger an immediate perf collection (on-demand)."""
    try:
        _collect_perf_sample()
        _save_perf_history()
        return jsonify({"status": "ok", "samples": _perf_collector_state["samples_collected"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/perf/vm/<vm_name>")
def api_perf_vm(vm_name: str):
    """Return perf history and statistics for a specific VM."""
    samples = _perf_history.get(vm_name, [])
    if not samples:
        return jsonify({"vm_name": vm_name, "samples": [], "stats": {}})

    return jsonify({
        "vm_name": vm_name,
        "sample_count": len(samples),
        "samples": samples,
        "stats": {
            "cpu_pct": _compute_perf_stats(samples, "cpu_pct"),
            "mem_pct": _compute_perf_stats(samples, "mem_pct"),
            "disk_iops": _compute_perf_stats(samples, "disk_iops"),
            "disk_read_kbps": _compute_perf_stats(samples, "disk_read_kbps"),
            "disk_write_kbps": _compute_perf_stats(samples, "disk_write_kbps"),
            "net_rx_kbps": _compute_perf_stats(samples, "net_rx_kbps"),
            "net_tx_kbps": _compute_perf_stats(samples, "net_tx_kbps"),
        },
    })


@app.route("/api/perf/vm/<vm_name>/summary")
def api_perf_vm_summary(vm_name: str):
    """Return compact perf summary (latest + stats) for a VM — used by sidebar."""
    samples = _perf_history.get(vm_name, [])
    if not samples:
        return jsonify({"vm_name": vm_name, "has_data": False})
    return jsonify({
        "vm_name": vm_name,
        "has_data": True,
        "sample_count": len(samples),
        "latest": samples[-1],
        "cpu": _compute_perf_stats(samples, "cpu_pct"),
        "mem": _compute_perf_stats(samples, "mem_pct"),
        "disk_iops": _compute_perf_stats(samples, "disk_iops"),
    })


@app.route("/api/perf/workloads")
def api_perf_workloads():
    """Return perf summary for all workloads."""
    results = []
    for key, samples in _workload_perf_history.items():
        parts = key.split("::", 1)
        vm_name = parts[0] if parts else key
        wl_name = parts[1] if len(parts) > 1 else key
        if not samples:
            continue
        results.append({
            "workload_key": key,
            "vm_name": vm_name,
            "workload_name": wl_name,
            "sample_count": len(samples),
            "latest": samples[-1],
            "cpu": _compute_perf_stats(samples, "cpu_pct"),
            "mem_mb": _compute_perf_stats(samples, "mem_mb"),
            "connections": _compute_perf_stats(samples, "connections"),
        })
    return jsonify(results)


@app.route("/api/perf/workload/<path:workload_key>")
def api_perf_workload(workload_key: str):
    """Return perf history for a specific workload."""
    samples = _workload_perf_history.get(workload_key, [])
    if not samples:
        return jsonify({"workload_key": workload_key, "samples": [], "stats": {}})
    return jsonify({
        "workload_key": workload_key,
        "sample_count": len(samples),
        "samples": samples,
        "stats": {
            "cpu_pct": _compute_perf_stats(samples, "cpu_pct"),
            "mem_mb": _compute_perf_stats(samples, "mem_mb"),
            "connections": _compute_perf_stats(samples, "connections"),
        },
    })


@app.route("/api/perf/summary")
def api_perf_global_summary():
    """Return global perf summary across all VMs — used by sidebar."""
    if not _perf_history:
        return jsonify({"has_data": False})

    # Aggregate latest samples across all VMs
    cpu_vals, mem_vals, iops_vals = [], [], []
    for samples in _perf_history.values():
        if samples:
            latest = samples[-1]
            cpu_vals.append(latest.get("cpu_pct", 0))
            mem_vals.append(latest.get("mem_pct", 0))
            iops_vals.append(latest.get("disk_iops", 0))

    n = len(cpu_vals)
    if n == 0:
        return jsonify({"has_data": False})

    return jsonify({
        "has_data": True,
        "vms_monitored": n,
        "avg_cpu_pct": round(sum(cpu_vals) / n, 1),
        "avg_mem_pct": round(sum(mem_vals) / n, 1),
        "total_iops": round(sum(iops_vals), 0),
        "last_collection": _perf_collector_state.get("last_collection"),
        "samples_collected": _perf_collector_state.get("samples_collected", 0),
    })


# ---------------------------------------------------------------------------
# Enrichment Data Loop – monitoring telemetry ingestion
# ---------------------------------------------------------------------------

@app.route("/api/enrichment/tools")
def api_enrichment_tools():
    """Return list of supported monitoring tools."""
    tools = [
        {"id": "dynatrace",     "name": "Dynatrace",      "icon": "bi-graph-up",     "color": "#6f2da8"},
        {"id": "new_relic",      "name": "New Relic",       "icon": "bi-bar-chart",    "color": "#008c99"},
        {"id": "datadog",        "name": "Datadog",         "icon": "bi-clipboard-data","color": "#632ca6"},
        {"id": "splunk",         "name": "Splunk",          "icon": "bi-search",       "color": "#65a637"},
        {"id": "prometheus",     "name": "Prometheus",      "icon": "bi-fire",         "color": "#e6522c"},
        {"id": "app_dynamics",   "name": "AppDynamics",     "icon": "bi-activity",     "color": "#2196f3"},
        {"id": "zabbix",         "name": "Zabbix",          "icon": "bi-cpu",          "color": "#d40000"},
        {"id": "custom",         "name": "Custom / Other",  "icon": "bi-filetype-json","color": "#6c757d"},
    ]
    return jsonify(tools)


@app.route("/api/enrichment/upload", methods=["POST"])
def api_enrichment_upload():
    """Upload monitoring telemetry data (JSON) for enrichment.

    Form fields:
        tool  – monitoring tool identifier (dynatrace, new_relic, …)
        file  – JSON file upload, OR
        json  – JSON payload in the request body
    """
    global _enrichment_data, _enrichment_history

    tool = request.form.get("tool") or request.json.get("tool", "custom") if request.is_json else request.form.get("tool", "custom")

    # Get JSON data from uploaded file or request body
    raw_data = None
    if "file" in request.files:
        f = request.files["file"]
        if f.filename:
            try:
                raw_data = json.loads(f.read().decode("utf-8"))
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON file"}), 400
    elif request.is_json:
        raw_data = request.json.get("data")
        tool = request.json.get("tool", tool)

    if not raw_data:
        return jsonify({"error": "No data provided. Upload a JSON file or send JSON body."}), 400

    # Get all known VM names for matching
    vm_names = [vm["name"] for vm in _data.get("vms", [])]
    if not vm_names:
        return jsonify({"error": "No VMs discovered yet. Run vCenter discovery first."}), 400

    # Ingest the telemetry
    result = ingest_telemetry(raw_data, tool, vm_names)

    # Merge into enrichment store (latest wins per VM)
    for tel in result.telemetry:
        _enrichment_data[tel.entity_name] = tel.to_dict()

    # Add to history
    _enrichment_history.append(result.to_dict())

    # Persist enrichment data
    _save_json(_ENRICHMENT_DATA_FILE, {
        "telemetry": _enrichment_data,
        "history": _enrichment_history,
    })

    return jsonify({
        "status": "success",
        "tool": result.tool,
        "entities_matched": result.entities_matched,
        "entities_unmatched": result.entities_unmatched,
        "total_records": result.total_records,
        "message": f"Ingested {result.entities_matched} of {result.total_records} entities from {tool}",
    })


@app.route("/api/enrichment/generate_sample", methods=["POST"])
def api_enrichment_generate_sample():
    """Generate sample monitoring telemetry for demo purposes."""
    global _enrichment_data, _enrichment_history

    vm_names = [vm["name"] for vm in _data.get("vms", [])]
    if not vm_names:
        return jsonify({"error": "No VMs discovered yet."}), 400

    body = request.get_json(silent=True) or {}
    tool = body.get("tool", "dynatrace")

    # Generate sample data
    sample = generate_sample_enrichment(vm_names, tool)

    # Ingest it
    result = ingest_telemetry(sample, tool, vm_names)

    for tel in result.telemetry:
        _enrichment_data[tel.entity_name] = tel.to_dict()
    _enrichment_history.append(result.to_dict())

    _save_json(_ENRICHMENT_DATA_FILE, {
        "telemetry": _enrichment_data,
        "history": _enrichment_history,
    })

    return jsonify({
        "status": "success",
        "tool": tool,
        "entities_matched": result.entities_matched,
        "total_records": result.total_records,
        "message": f"Generated & ingested sample {tool} data for {result.entities_matched} VMs",
    })


@app.route("/api/enrichment/status")
def api_enrichment_status():
    """Return current enrichment status and summary statistics."""
    total_vms = len(_data.get("vms", []))
    enriched_count = len(_enrichment_data)
    tools_used = list(set(e.get("monitoring_tool", "") for e in _enrichment_data.values()))

    # Calculate average confidence boost
    boosts = [e.get("confidence_boost", 0) for e in _enrichment_data.values()]
    avg_boost = round(sum(boosts) / len(boosts), 1) if boosts else 0.0

    # Count metrics coverage
    metrics_coverage = {}
    for e in _enrichment_data.values():
        m = e.get("metrics", {})
        for k, v in m.items():
            if v is not None:
                metrics_coverage[k] = metrics_coverage.get(k, 0) + 1

    return jsonify({
        "total_vms": total_vms,
        "enriched_vms": enriched_count,
        "coverage_pct": round(enriched_count / total_vms * 100, 1) if total_vms else 0,
        "tools_used": tools_used,
        "avg_confidence_boost": avg_boost,
        "total_ingestions": len(_enrichment_history),
        "metrics_coverage": metrics_coverage,
        "last_ingestion": _enrichment_history[-1].get("ingested_at") if _enrichment_history else None,
    })


@app.route("/api/enrichment/data")
def api_enrichment_data():
    """Return all enrichment telemetry records."""
    return jsonify({
        "telemetry": _enrichment_data,
        "count": len(_enrichment_data),
    })


@app.route("/api/enrichment/vm/<vm_name>")
def api_enrichment_vm(vm_name: str):
    """Return enrichment data for a specific VM."""
    data = _enrichment_data.get(vm_name)
    if not data:
        return jsonify({"error": f"No enrichment data for VM '{vm_name}'"}), 404
    return jsonify(data)


@app.route("/api/enrichment/history")
def api_enrichment_history():
    """Return the enrichment ingestion history."""
    return jsonify({
        "history": _enrichment_history,
        "count": len(_enrichment_history),
    })


@app.route("/api/enrichment/clear", methods=["POST"])
def api_enrichment_clear():
    """Clear all enrichment data."""
    global _enrichment_data, _enrichment_history
    _enrichment_data = {}
    _enrichment_history = []
    _save_json(_ENRICHMENT_DATA_FILE, {"telemetry": {}, "history": []})
    return jsonify({"status": "cleared"})


# ---------------------------------------------------------------------------
# Business Case API — CxO-level on-prem vs Azure TCO comparison
# ---------------------------------------------------------------------------

# On-premises cost assumptions per host per month (industry averages)
_ONPREM_COST_ASSUMPTIONS = {
    "server_hw_amortized_monthly": 800.0,      # hardware depreciation per host (3yr amortisation)
    "server_maintenance_pct": 0.10,             # 10% of HW cost for maintenance/support
    "vmware_license_per_cpu_monthly": 25.0,     # vSphere licence per physical CPU
    "windows_license_per_vm_monthly": 15.0,     # Windows Server licence per VM
    "rhel_license_per_vm_monthly": 8.0,         # RHEL licence per VM
    "storage_per_tb_monthly": 40.0,             # SAN / NAS storage cost per TB
    "networking_per_host_monthly": 50.0,        # switches, firewalls, load balancers amortised
    "dc_power_cooling_per_host_monthly": 200.0, # data-centre power, cooling, rack space
    "it_staff_cost_monthly": 12000.0,           # 1 FTE admin cost (salary + benefits)
    "vms_per_admin": 50,                        # industry average admin-to-VM ratio
    "security_compliance_per_vm_monthly": 5.0,  # AV, patching, compliance tooling
    "backup_dr_per_vm_monthly": 12.0,           # backup software + DR site amortised
    "downtime_cost_per_hour": 5000.0,           # business cost of unplanned downtime
    "avg_downtime_hours_per_year": 8.0,         # typical on-prem unplanned downtime
}

# Azure additional cost factors
_AZURE_COST_ADDITIONS = {
    "azure_support_plan_monthly": 100.0,        # Standard support plan
    "azure_monitor_per_vm_monthly": 2.50,       # Log Analytics + diagnostics
    "azure_backup_per_vm_monthly": 8.0,         # Azure Backup per VM
    "azure_security_center_per_vm_monthly": 7.50,  # Defender for Servers P2
    "migration_tooling_one_time": 5000.0,       # Azure Migrate + tooling
    "training_one_time": 10000.0,               # Staff training
    "migration_services_per_vm": 150.0,         # professional services per VM
}


@app.route("/api/businesscase")
def api_business_case():
    """Generate a comprehensive business case comparing on-prem TCO vs Azure.

    Query params:
        pricing_model  – pay_as_you_go | 1_year_ri | 3_year_ri | savings_plan_1yr | savings_plan_3yr
        target_region  – Azure region (default: eastus)
        analysis_years – TCO horizon (default: 3)
        include_paas   – include workload PaaS savings (default: true)
    """
    if not _data or not _data.get("vms"):
        return jsonify({"error": "No discovery data loaded"}), 404

    pricing_model = request.args.get("pricing_model", "3_year_ri")
    target_region = request.args.get("target_region", "eastus")
    analysis_years = int(request.args.get("analysis_years", "3"))
    include_paas = request.args.get("include_paas", "true").lower() == "true"

    vms = _data["vms"]
    recs = _data.get("recommendations", [])
    hosts = _data.get("hosts", [])
    datastores = _data.get("datastores", [])

    num_vms = len(vms)
    num_hosts = len(hosts) or max(1, num_vms // 15)  # estimate if hosts missing
    powered_on = sum(1 for v in vms if v.get("power_state") == "poweredOn")
    windows_vms = sum(1 for v in vms if v.get("guest_os_family") == "windows")
    linux_vms = sum(1 for v in vms if v.get("guest_os_family") == "linux")

    total_vcpus = sum(v.get("num_cpus", 0) for v in vms)
    total_memory_gb = sum(v.get("memory_mb", 0) for v in vms) / 1024
    total_disk_tb = sum(v.get("total_disk_gb", 0) for v in vms) / 1024
    total_storage_tb = sum(ds.get("capacity_gb", 0) for ds in datastores) / 1024 if datastores else total_disk_tb * 1.5

    # Physical CPU count (estimate 2 sockets per host, each typically 8-16 cores)
    total_physical_cpus = num_hosts * 2

    assumptions = _ONPREM_COST_ASSUMPTIONS
    azure_adds = _AZURE_COST_ADDITIONS

    # === ON-PREM MONTHLY COSTS ===
    hw_cost = num_hosts * assumptions["server_hw_amortized_monthly"]
    hw_maint = hw_cost * assumptions["server_maintenance_pct"]
    vmware_lic = total_physical_cpus * assumptions["vmware_license_per_cpu_monthly"]
    windows_lic = windows_vms * assumptions["windows_license_per_vm_monthly"]
    linux_lic = linux_vms * assumptions["rhel_license_per_vm_monthly"]
    os_licensing = windows_lic + linux_lic
    storage_cost = total_storage_tb * assumptions["storage_per_tb_monthly"]
    network_cost = num_hosts * assumptions["networking_per_host_monthly"]
    dc_facilities = num_hosts * assumptions["dc_power_cooling_per_host_monthly"]
    num_admins = max(1, math.ceil(num_vms / assumptions["vms_per_admin"]))
    staff_cost = num_admins * assumptions["it_staff_cost_monthly"]
    security_cost = num_vms * assumptions["security_compliance_per_vm_monthly"]
    backup_dr = num_vms * assumptions["backup_dr_per_vm_monthly"]
    downtime_monthly = (assumptions["downtime_cost_per_hour"] * assumptions["avg_downtime_hours_per_year"]) / 12

    onprem_monthly = (hw_cost + hw_maint + vmware_lic + os_licensing +
                      storage_cost + network_cost + dc_facilities +
                      staff_cost + security_cost + backup_dr + downtime_monthly)
    onprem_annual = onprem_monthly * 12

    onprem_breakdown = {
        "hardware_depreciation": round(hw_cost, 2),
        "hardware_maintenance": round(hw_maint, 2),
        "vmware_licensing": round(vmware_lic, 2),
        "os_licensing": round(os_licensing, 2),
        "storage": round(storage_cost, 2),
        "networking": round(network_cost, 2),
        "datacenter_facilities": round(dc_facilities, 2),
        "it_staff": round(staff_cost, 2),
        "security_compliance": round(security_cost, 2),
        "backup_disaster_recovery": round(backup_dr, 2),
        "downtime_cost": round(downtime_monthly, 2),
    }

    # === AZURE MONTHLY COSTS ===
    region_mult = REGION_MULTIPLIERS.get(target_region, 1.0)
    ri_mult = RI_DISCOUNTS.get(pricing_model, 1.0)

    # Compute cost from recommendations
    base_azure_compute = sum(r.get("estimated_monthly_cost_usd", 0) for r in recs)
    azure_compute = base_azure_compute * region_mult * ri_mult

    # Azure managed services
    azure_support = azure_adds["azure_support_plan_monthly"]
    azure_monitor = num_vms * azure_adds["azure_monitor_per_vm_monthly"]
    azure_backup = num_vms * azure_adds["azure_backup_per_vm_monthly"]
    azure_security = num_vms * azure_adds["azure_security_center_per_vm_monthly"]

    # Staff savings: cloud requires fewer admins (industry: 2x VM/admin ratio)
    cloud_admins = max(1, math.ceil(num_vms / (assumptions["vms_per_admin"] * 2)))
    azure_staff = cloud_admins * assumptions["it_staff_cost_monthly"]

    # No VMware licensing, reduced OS licensing (AHUB for Windows)
    azure_os_licensing = round(linux_vms * assumptions["rhel_license_per_vm_monthly"] * 0.5, 2)  # RHEL discount

    azure_monthly = (azure_compute + azure_support + azure_monitor +
                     azure_backup + azure_security + azure_staff + azure_os_licensing)
    azure_annual = azure_monthly * 12

    azure_breakdown = {
        "compute_vms": round(azure_compute, 2),
        "support_plan": round(azure_support, 2),
        "monitoring": round(azure_monitor, 2),
        "backup": round(azure_backup, 2),
        "security_defender": round(azure_security, 2),
        "it_staff": round(azure_staff, 2),
        "os_licensing": round(azure_os_licensing, 2),
    }

    # === MIGRATION ONE-TIME COSTS ===
    migration_one_time = (azure_adds["migration_tooling_one_time"] +
                          azure_adds["training_one_time"] +
                          num_vms * azure_adds["migration_services_per_vm"])

    migration_breakdown = {
        "migration_tooling": azure_adds["migration_tooling_one_time"],
        "staff_training": azure_adds["training_one_time"],
        "professional_services": round(num_vms * azure_adds["migration_services_per_vm"], 2),
    }

    # === PaaS SAVINGS (optional) ===
    paas_savings_monthly = 0.0
    paas_details = []
    if include_paas and _workload_data and _workload_data.get("recommendations"):
        for wlrec in _workload_data["recommendations"]:
            approach = wlrec.get("migration_approach", "rehost")
            if approach in ("replatform", "refactor"):
                wl_cost = wlrec.get("estimated_monthly_cost_usd", 0)
                # PaaS typically saves 20-40% over IaaS equivalent
                savings = wl_cost * 0.25
                paas_savings_monthly += savings
                paas_details.append({
                    "workload": wlrec.get("workload_name", ""),
                    "vm_name": wlrec.get("vm_name", ""),
                    "service": wlrec.get("azure_service", ""),
                    "approach": approach,
                    "monthly_savings": round(savings, 2),
                })

    azure_monthly_with_paas = azure_monthly - paas_savings_monthly
    azure_annual_with_paas = azure_monthly_with_paas * 12

    # === TCO COMPARISON (multi-year) ===
    monthly_savings = onprem_monthly - azure_monthly_with_paas
    annual_savings = monthly_savings * 12
    savings_pct = round((monthly_savings / onprem_monthly) * 100, 1) if onprem_monthly > 0 else 0

    # Year-by-year projection
    yearly_projection = []
    cumulative_savings = -migration_one_time  # start negative (migration investment)
    for year in range(1, analysis_years + 1):
        onprem_year_cost = onprem_annual * (1.03 ** (year - 1))  # 3% YoY cost increase on-prem
        azure_year_cost = azure_annual_with_paas * (1.01 ** (year - 1))  # 1% Azure cost growth
        year_savings = onprem_year_cost - azure_year_cost
        cumulative_savings += year_savings
        yearly_projection.append({
            "year": year,
            "onprem_cost": round(onprem_year_cost, 2),
            "azure_cost": round(azure_year_cost, 2),
            "net_savings": round(year_savings, 2),
            "cumulative_savings": round(cumulative_savings, 2),
        })

    # Payback period (months)
    if monthly_savings > 0:
        payback_months = math.ceil(migration_one_time / monthly_savings)
    else:
        payback_months = -1  # no payback

    total_tco_onprem = sum(y["onprem_cost"] for y in yearly_projection)
    total_tco_azure = sum(y["azure_cost"] for y in yearly_projection) + migration_one_time

    # === KEY BENEFITS (qualitative + quantitative) ===
    key_benefits = [
        {
            "icon": "cash-coin",
            "title": "Cost Reduction",
            "description": f"Save ${annual_savings:,.0f}/year ({savings_pct}% reduction) by eliminating hardware, facilities, and VMware licensing costs.",
        },
        {
            "icon": "shield-check",
            "title": "Enhanced Security",
            "description": "Microsoft Defender for Cloud, Azure DDoS Protection, and built-in compliance certifications (SOC 2, ISO 27001, HIPAA).",
        },
        {
            "icon": "lightning-charge",
            "title": "Business Agility",
            "description": f"Scale from {num_vms} VMs to thousands in minutes. No hardware procurement lead times.",
        },
        {
            "icon": "arrow-repeat",
            "title": "Disaster Recovery",
            "description": "Azure Site Recovery provides 99.9% SLA with automated failover. Reduce DR costs by eliminating secondary data centre.",
        },
        {
            "icon": "people",
            "title": "Staff Optimisation",
            "description": f"Reduce admin overhead from {num_admins} FTEs to {cloud_admins} FTEs. Re-deploy staff to innovation projects.",
        },
        {
            "icon": "graph-up-arrow",
            "title": "Innovation",
            "description": "Access 200+ Azure services including AI/ML, IoT, and data analytics without additional infrastructure investment.",
        },
    ]

    # === RISK ASSESSMENT ===
    risks = []
    not_ready = sum(1 for r in recs if r.get("migration_readiness") == "Not Ready")
    conditional = sum(1 for r in recs if "condition" in r.get("migration_readiness", "").lower())
    ready = num_vms - not_ready - conditional

    if not_ready > 0:
        risks.append({
            "severity": "high",
            "area": "Compatibility",
            "description": f"{not_ready} VM(s) flagged as Not Ready — require manual assessment or re-architecture before migration.",
        })
    if conditional > 5:
        risks.append({
            "severity": "medium",
            "area": "Conditional Readiness",
            "description": f"{conditional} VM(s) have conditions that need to be addressed (disk sizes, OS compatibility).",
        })
    if num_vms > 100:
        risks.append({
            "severity": "medium",
            "area": "Migration Complexity",
            "description": f"Large fleet ({num_vms} VMs) — recommend phased migration over {max(3, num_vms // 50)} waves.",
        })
    if total_disk_tb > 50:
        risks.append({
            "severity": "medium",
            "area": "Data Transfer",
            "description": f"{total_disk_tb:.1f} TB of data — consider Azure Data Box for initial transfer to reduce migration window.",
        })
    risks.append({
        "severity": "low",
        "area": "Change Management",
        "description": "Staff training and process changes required. Budget for cloud operations training programme.",
    })

    # === EXECUTIVE SUMMARY METRICS ===
    exec_summary = {
        "total_vms": num_vms,
        "powered_on": powered_on,
        "total_hosts": num_hosts,
        "total_vcpus": total_vcpus,
        "total_memory_gb": round(total_memory_gb, 1),
        "total_storage_tb": round(total_storage_tb, 1),
        "readiness_ready": ready,
        "readiness_conditional": conditional,
        "readiness_not_ready": not_ready,
        "readiness_pct": round((ready / num_vms) * 100, 1) if num_vms > 0 else 0,
    }

    return jsonify({
        "executive_summary": exec_summary,
        "pricing_model": pricing_model,
        "target_region": target_region,
        "analysis_years": analysis_years,
        "onprem_monthly": round(onprem_monthly, 2),
        "onprem_annual": round(onprem_annual, 2),
        "onprem_breakdown": onprem_breakdown,
        "azure_monthly": round(azure_monthly_with_paas, 2),
        "azure_annual": round(azure_annual_with_paas, 2),
        "azure_breakdown": azure_breakdown,
        "migration_one_time": round(migration_one_time, 2),
        "migration_breakdown": migration_breakdown,
        "paas_savings_monthly": round(paas_savings_monthly, 2),
        "paas_details": paas_details,
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(annual_savings, 2),
        "savings_pct": savings_pct,
        "total_tco_onprem": round(total_tco_onprem, 2),
        "total_tco_azure": round(total_tco_azure, 2),
        "total_tco_savings": round(total_tco_onprem - total_tco_azure, 2),
        "payback_months": payback_months,
        "yearly_projection": yearly_projection,
        "key_benefits": key_benefits,
        "risks": risks,
        "assumptions": {**assumptions, **azure_adds},
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _auto_load_from_data_dir()
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║      Azure Migrate Simulations – Dashboard       ║")
    print("  ╚══════════════════════════════════════════════════╝")
    if _data:
        print(f"  Auto-loaded vCenter data: {len(_data.get('vms',[]))} VMs")
    if _workload_data:
        print(f"  Auto-loaded workload data: {len(_workload_data.get('recommendations',[]))} recommendations")
    print("  Open http://localhost:5000 in your browser")
    print("  Connect to your vCenter or upload a report file.\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
