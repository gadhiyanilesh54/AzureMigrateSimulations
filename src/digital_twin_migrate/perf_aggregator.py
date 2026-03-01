"""Performance history aggregator — converts raw time-series perf data into
percentile-based metrics suitable for accurate VM right-sizing.

Feeds ``perf_history.json`` (collected over time from multi-sample runs) into
the PerformanceMetrics model used by the assessment engine, computing avg,
P50, P95, P99, and max for each metric.

Usage
-----
    from .perf_aggregator import apply_perf_history
    apply_perf_history(env, Path("data/perf_history.json"))
"""

from __future__ import annotations

import json
import logging
import statistics
from pathlib import Path
from typing import Any

from .models import DiscoveredEnvironment, PerformanceMetrics

logger = logging.getLogger(__name__)


def _percentile(sorted_data: list[float], pct: float) -> float:
    """Return the *pct*-th percentile from pre-sorted data (0–100 scale)."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    idx = min(int(n * pct / 100.0), n - 1)
    return sorted_data[idx]


def _aggregate_samples(samples: list[dict]) -> PerformanceMetrics:
    """Aggregate a list of raw perf samples into a PerformanceMetrics."""
    if not samples:
        return PerformanceMetrics()

    cpu_vals = [s["cpu_pct"] for s in samples if "cpu_pct" in s and s["cpu_pct"] is not None]
    mem_vals = [s["mem_pct"] for s in samples if "mem_pct" in s and s["mem_pct"] is not None]
    iops_vals = [s.get("disk_iops", 0) or 0 for s in samples]
    disk_read_vals = [s.get("disk_read_kbps", 0) or 0 for s in samples]
    disk_write_vals = [s.get("disk_write_kbps", 0) or 0 for s in samples]
    net_rx_vals = [s.get("net_rx_kbps", 0) or 0 for s in samples]
    net_tx_vals = [s.get("net_tx_kbps", 0) or 0 for s in samples]

    # Sort for percentile computation
    cpu_sorted = sorted(cpu_vals) if cpu_vals else []
    mem_sorted = sorted(mem_vals) if mem_vals else []
    iops_sorted = sorted(iops_vals) if iops_vals else []
    disk_r_sorted = sorted(disk_read_vals) if disk_read_vals else []
    disk_w_sorted = sorted(disk_write_vals) if disk_write_vals else []
    net_sorted = sorted(rx + tx for rx, tx in zip(net_rx_vals, net_tx_vals)) if net_rx_vals else []

    # Combine disk throughput for P95
    disk_tp_sorted = sorted(r + w for r, w in zip(disk_read_vals, disk_write_vals)) if disk_read_vals else []

    perf = PerformanceMetrics(
        cpu_usage_percent=statistics.mean(cpu_vals) if cpu_vals else 0,
        memory_usage_percent=statistics.mean(mem_vals) if mem_vals else 0,
        disk_read_kbps=statistics.mean(disk_read_vals) if disk_read_vals else 0,
        disk_write_kbps=statistics.mean(disk_write_vals) if disk_write_vals else 0,
        disk_iops_read=statistics.mean(iops_vals) / 2 if iops_vals else 0,  # rough split
        disk_iops_write=statistics.mean(iops_vals) / 2 if iops_vals else 0,
        network_rx_kbps=statistics.mean(net_rx_vals) if net_rx_vals else 0,
        network_tx_kbps=statistics.mean(net_tx_vals) if net_tx_vals else 0,
        # Percentiles
        cpu_p50_percent=_percentile(cpu_sorted, 50),
        cpu_p95_percent=_percentile(cpu_sorted, 95),
        cpu_p99_percent=_percentile(cpu_sorted, 99),
        cpu_max_percent=cpu_sorted[-1] if cpu_sorted else 0,
        memory_p50_percent=_percentile(mem_sorted, 50),
        memory_p95_percent=_percentile(mem_sorted, 95),
        memory_p99_percent=_percentile(mem_sorted, 99),
        memory_max_percent=mem_sorted[-1] if mem_sorted else 0,
        disk_iops_p95=_percentile(iops_sorted, 95),
        disk_throughput_p95_kbps=_percentile(disk_tp_sorted, 95),
        network_p95_kbps=_percentile(net_sorted, 95),
        # Data quality
        sample_count=len(samples),
        collection_period_days=_estimate_days(samples),
        perf_data_source="perf_history",
    )
    return perf


def _estimate_days(samples: list[dict]) -> int:
    """Estimate the time span of samples in days from timestamps."""
    timestamps = [s.get("ts", "") for s in samples if s.get("ts")]
    if len(timestamps) < 2:
        return 1
    try:
        from datetime import datetime, timezone

        def _parse(ts: str) -> datetime:
            # Handle ISO 8601 with timezone
            if "+" in ts or ts.endswith("Z"):
                ts = ts.replace("Z", "+00:00")
            return datetime.fromisoformat(ts)

        times = sorted(_parse(t) for t in timestamps)
        span = (times[-1] - times[0]).days
        return max(span, 1)
    except Exception:
        return 1


def apply_perf_history(
    env: DiscoveredEnvironment,
    perf_history_path: Path,
    *,
    prefer_over_vcenter: bool = True,
) -> int:
    """Load perf_history.json and merge percentile-aggregated data into the
    environment's VMs.

    Args:
        env: The discovered environment (VMs are updated in-place).
        perf_history_path: Path to the perf_history.json file.
        prefer_over_vcenter: If True, perf_history data replaces vcenter
            real-time data (but not vcenter historical data with more samples).

    Returns:
        Number of VMs enriched.
    """
    if not perf_history_path.exists():
        logger.info("No perf_history file at %s — skipping", perf_history_path)
        return 0

    try:
        raw = json.loads(perf_history_path.read_text("utf-8"))
    except Exception as exc:
        logger.warning("Failed to load perf_history: %s", exc)
        return 0

    vm_perf: dict[str, list[dict]] = raw.get("vm_perf", {})
    if not vm_perf:
        logger.info("perf_history.json has no vm_perf data")
        return 0

    # Build a name → VM lookup
    vm_by_name = {vm.name: vm for vm in env.vms}
    enriched = 0

    for vm_name, samples in vm_perf.items():
        vm = vm_by_name.get(vm_name)
        if vm is None:
            continue

        if not samples:
            continue

        aggregated = _aggregate_samples(samples)

        # Decide whether to use this data
        existing = vm.perf
        should_apply = False

        if existing.sample_count == 0 or existing.cpu_usage_percent == 0:
            # No existing data at all
            should_apply = True
        elif prefer_over_vcenter and existing.perf_data_source == "vcenter_realtime":
            # Perf history is richer than a single real-time sample
            should_apply = True
        elif aggregated.sample_count > existing.sample_count:
            # More samples = more accurate
            should_apply = True

        if should_apply:
            vm.perf = aggregated
            enriched += 1
            logger.debug("Applied perf_history for %s (%d samples, P95 CPU=%.1f%%)",
                         vm_name, aggregated.sample_count, aggregated.cpu_p95_percent)

    logger.info("Enriched %d/%d VMs with perf_history data", enriched, len(env.vms))
    return enriched
