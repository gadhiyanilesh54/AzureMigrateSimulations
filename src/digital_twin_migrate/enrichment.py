"""Enrichment Data Loop – ingest monitoring telemetry from external APM tools
(Dynatrace, New Relic, Datadog, Splunk, etc.) to boost assessment confidence.

The enrichment engine normalises heterogeneous monitoring exports into a
unified ``EnrichmentTelemetry`` for every VM / workload, then produces a
per-entity confidence delta that can be merged with the base assessment.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Supported monitoring tools
# ---------------------------------------------------------------------------


class MonitoringTool(str, Enum):
    DYNATRACE = "dynatrace"
    NEW_RELIC = "new_relic"
    DATADOG = "datadog"
    SPLUNK = "splunk"
    PROMETHEUS = "prometheus"
    ZABBIX = "zabbix"
    APP_DYNAMICS = "app_dynamics"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Normalised telemetry model
# ---------------------------------------------------------------------------


@dataclass
class EnrichmentMetrics:
    """Normalised metrics extracted from any monitoring tool export."""
    avg_cpu_pct: float | None = None
    p95_cpu_pct: float | None = None
    max_cpu_pct: float | None = None
    avg_memory_pct: float | None = None
    p95_memory_pct: float | None = None
    max_memory_pct: float | None = None
    avg_disk_iops: float | None = None
    p95_disk_iops: float | None = None
    avg_network_kbps: float | None = None
    p95_network_kbps: float | None = None
    avg_response_time_ms: float | None = None
    p95_response_time_ms: float | None = None
    error_rate_pct: float | None = None
    request_rate_rpm: float | None = None
    active_connections: int | None = None
    dependency_count: int | None = None
    transaction_count: int | None = None


@dataclass
class EnrichmentTelemetry:
    """Enrichment record for a single VM or workload entity."""
    entity_name: str = ""                       # vm_name or workload key
    entity_type: str = "vm"                     # vm | workload
    monitoring_tool: str = ""                   # dynatrace, new_relic, …
    collection_period_days: int = 0             # how many days of data
    sample_count: int = 0                       # number of data points
    metrics: EnrichmentMetrics = field(default_factory=EnrichmentMetrics)
    dependencies: list[str] = field(default_factory=list)       # discovered app deps
    tags: dict[str, str] = field(default_factory=dict)
    raw_data_snippet: str = ""                  # first 500 chars of raw payload
    ingested_at: str = ""                       # ISO timestamp
    confidence_boost: float = 0.0               # calculated boost

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Enrichment result container
# ---------------------------------------------------------------------------


@dataclass
class EnrichmentResult:
    """Overall result from an enrichment ingestion."""
    tool: str = ""
    entities_matched: int = 0
    entities_unmatched: int = 0
    total_records: int = 0
    ingested_at: str = ""
    telemetry: list[EnrichmentTelemetry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "entities_matched": self.entities_matched,
            "entities_unmatched": self.entities_unmatched,
            "total_records": self.total_records,
            "ingested_at": self.ingested_at,
            "telemetry": [t.to_dict() for t in self.telemetry],
        }


# ---------------------------------------------------------------------------
# Parser registry – one parser per monitoring tool
# ---------------------------------------------------------------------------


def _parse_dynatrace(raw: dict, vm_names: set[str]) -> list[EnrichmentTelemetry]:
    """Parse Dynatrace export JSON (entities / metrics / smartscape)."""
    records: list[EnrichmentTelemetry] = []
    entities = raw.get("result", raw.get("entities", raw.get("hosts", [])))
    if isinstance(entities, dict):
        entities = list(entities.values()) if not isinstance(list(entities.values())[0] if entities else "", dict) else list(entities.values())
        if not entities:
            entities = [raw]

    for ent in (entities if isinstance(entities, list) else [entities]):
        name = (
            ent.get("displayName")
            or ent.get("entityName")
            or ent.get("host_name")
            or ent.get("name", "")
        )
        matched_name = _fuzzy_match(name, vm_names)
        if not matched_name:
            continue

        props = ent.get("properties", ent)
        metrics = EnrichmentMetrics(
            avg_cpu_pct=_float(props, "cpuUsage", "cpu.usage.average", "cpuUsagePercent"),
            p95_cpu_pct=_float(props, "cpuUsage95th"),
            avg_memory_pct=_float(props, "memoryUsage", "memory.usage.average", "memoryUsagePercent"),
            p95_memory_pct=_float(props, "memoryUsage95th"),
            avg_disk_iops=_float(props, "diskIOPS", "disk.iops"),
            avg_network_kbps=_float(props, "networkBandwidth", "network.kbps"),
            avg_response_time_ms=_float(props, "responseTime", "response_time_ms"),
            error_rate_pct=_float(props, "errorRate", "error_rate"),
            active_connections=_int(props, "activeConnections", "connections"),
        )
        deps = ent.get("fromRelationships", ent.get("dependencies", []))
        dep_names = []
        if isinstance(deps, dict):
            for rel_list in deps.values():
                if isinstance(rel_list, list):
                    dep_names.extend([d.get("name", str(d)) for d in rel_list if isinstance(d, dict)])
        elif isinstance(deps, list):
            dep_names = [d.get("name", str(d)) if isinstance(d, dict) else str(d) for d in deps]

        period = _int(props, "monitoringDays", "period_days") or 30
        samples = _int(props, "sampleCount", "dataPoints") or 0

        records.append(EnrichmentTelemetry(
            entity_name=matched_name,
            entity_type="vm",
            monitoring_tool=MonitoringTool.DYNATRACE.value,
            collection_period_days=period,
            sample_count=samples,
            metrics=metrics,
            dependencies=dep_names[:20],
            tags=_extract_tags(ent),
            raw_data_snippet=json.dumps(ent, default=str)[:500],
            ingested_at=datetime.now(timezone.utc).isoformat(),
        ))

    return records


def _parse_new_relic(raw: dict, vm_names: set[str]) -> list[EnrichmentTelemetry]:
    """Parse New Relic NRQL / Insights / Infrastructure export."""
    records: list[EnrichmentTelemetry] = []
    results = raw.get("results", raw.get("data", raw.get("facets", [])))
    if isinstance(results, dict):
        results = results.get("results", [results])

    for item in (results if isinstance(results, list) else [results]):
        name = (
            item.get("facet", [None])[0] if isinstance(item.get("facet"), list) else
            item.get("hostname") or item.get("host") or item.get("name", "")
        )
        if isinstance(name, list):
            name = name[0] if name else ""
        matched_name = _fuzzy_match(str(name), vm_names)
        if not matched_name:
            continue

        metrics = EnrichmentMetrics(
            avg_cpu_pct=_float(item, "average.cpuPercent", "cpuPercent", "avgCpu"),
            p95_cpu_pct=_float(item, "percentile.cpuPercent.95", "cpuP95"),
            avg_memory_pct=_float(item, "average.memoryUsedPercent", "memoryPercent", "avgMemory"),
            p95_memory_pct=_float(item, "percentile.memoryUsedPercent.95", "memP95"),
            avg_disk_iops=_float(item, "average.diskIOPS", "diskIops"),
            avg_network_kbps=_float(item, "average.networkKbps", "netKbps"),
            avg_response_time_ms=_float(item, "average.duration", "responseTime"),
            error_rate_pct=_float(item, "percentage.error", "errorRate"),
            request_rate_rpm=_float(item, "rate.count", "requestsPerMinute"),
        )

        records.append(EnrichmentTelemetry(
            entity_name=matched_name,
            entity_type="vm",
            monitoring_tool=MonitoringTool.NEW_RELIC.value,
            collection_period_days=_int(item, "periodDays") or 30,
            sample_count=_int(item, "count", "sampleCount") or 0,
            metrics=metrics,
            dependencies=_list_str(item, "dependencies", "relatedEntities"),
            tags=_extract_tags(item),
            raw_data_snippet=json.dumps(item, default=str)[:500],
            ingested_at=datetime.now(timezone.utc).isoformat(),
        ))

    return records


def _parse_datadog(raw: dict, vm_names: set[str]) -> list[EnrichmentTelemetry]:
    """Parse Datadog metrics / host map export."""
    records: list[EnrichmentTelemetry] = []
    series = raw.get("series", raw.get("host_list", raw.get("data", [])))
    if isinstance(series, dict):
        series = list(series.values())

    for item in (series if isinstance(series, list) else [series]):
        name = (
            item.get("host_name")
            or item.get("hostname")
            or item.get("scope", "").replace("host:", "")
            or item.get("display_name", "")
        )
        matched_name = _fuzzy_match(name, vm_names)
        if not matched_name:
            continue

        meta = item.get("metrics", item.get("meta", item))
        metrics = EnrichmentMetrics(
            avg_cpu_pct=_float(meta, "system.cpu.user", "cpu_user", "avg_cpu"),
            p95_cpu_pct=_float(meta, "system.cpu.user.p95", "cpu_p95"),
            avg_memory_pct=_float(meta, "system.mem.pct_usable", "mem_pct", "avg_memory"),
            p95_memory_pct=_float(meta, "system.mem.pct_usable.p95", "mem_p95"),
            avg_disk_iops=_float(meta, "system.io.r_s", "disk_iops"),
            avg_network_kbps=_float(meta, "system.net.bytes_rcvd", "net_kbps"),
            avg_response_time_ms=_float(meta, "trace.http.request.duration", "response_time"),
            error_rate_pct=_float(meta, "trace.http.request.errors.pct", "error_rate"),
        )

        tags = {}
        for t in item.get("tags_by_source", item.get("tags", [])):
            if isinstance(t, str) and ":" in t:
                k, v = t.split(":", 1)
                tags[k] = v

        records.append(EnrichmentTelemetry(
            entity_name=matched_name,
            entity_type="vm",
            monitoring_tool=MonitoringTool.DATADOG.value,
            collection_period_days=_int(meta, "period_days") or 30,
            sample_count=_int(meta, "pointcount", "count") or 0,
            metrics=metrics,
            tags=tags,
            raw_data_snippet=json.dumps(item, default=str)[:500],
            ingested_at=datetime.now(timezone.utc).isoformat(),
        ))

    return records


def _parse_splunk(raw: dict, vm_names: set[str]) -> list[EnrichmentTelemetry]:
    """Parse Splunk search results (JSON export)."""
    records: list[EnrichmentTelemetry] = []
    results = raw.get("results", raw.get("rows", raw.get("data", [])))
    if isinstance(results, dict):
        results = [results]

    for item in (results if isinstance(results, list) else [results]):
        name = item.get("host") or item.get("hostname") or item.get("src", "")
        matched_name = _fuzzy_match(name, vm_names)
        if not matched_name:
            continue

        metrics = EnrichmentMetrics(
            avg_cpu_pct=_float(item, "avg_cpu", "cpu_pct", "CPU_Percent"),
            p95_cpu_pct=_float(item, "p95_cpu", "perc95_cpu"),
            avg_memory_pct=_float(item, "avg_mem", "mem_pct", "Memory_Percent"),
            p95_memory_pct=_float(item, "p95_mem", "perc95_mem"),
            avg_disk_iops=_float(item, "avg_disk_iops", "IOPS"),
            avg_network_kbps=_float(item, "avg_net_kbps", "Network_KBps"),
            avg_response_time_ms=_float(item, "avg_response_time", "ResponseTime"),
            error_rate_pct=_float(item, "error_rate", "ErrorPercent"),
        )

        records.append(EnrichmentTelemetry(
            entity_name=matched_name,
            entity_type="vm",
            monitoring_tool=MonitoringTool.SPLUNK.value,
            collection_period_days=_int(item, "span_days", "period_days") or 30,
            sample_count=_int(item, "count", "eventcount") or 0,
            metrics=metrics,
            tags=_extract_tags(item),
            raw_data_snippet=json.dumps(item, default=str)[:500],
            ingested_at=datetime.now(timezone.utc).isoformat(),
        ))

    return records


def _parse_prometheus(raw: dict, vm_names: set[str]) -> list[EnrichmentTelemetry]:
    """Parse Prometheus / Thanos query result JSON."""
    records: list[EnrichmentTelemetry] = []
    data = raw.get("data", raw)
    results = data.get("result", data.get("results", []))
    if isinstance(results, dict):
        results = [results]

    for item in (results if isinstance(results, list) else [results]):
        metric = item.get("metric", item)
        name = metric.get("instance", metric.get("node", metric.get("hostname", "")))
        # strip port from instance
        if ":" in name:
            name = name.split(":")[0]
        matched_name = _fuzzy_match(name, vm_names)
        if not matched_name:
            continue

        values = item.get("values", item.get("value", []))
        avg_val = 0.0
        if isinstance(values, list) and values:
            nums = [float(v[1]) if isinstance(v, list) and len(v) > 1 else float(v) for v in values if _is_numeric(v)]
            avg_val = sum(nums) / len(nums) if nums else 0.0

        metrics = EnrichmentMetrics(
            avg_cpu_pct=avg_val if "cpu" in str(metric.get("__name__", "")).lower() else _float(metric, "cpu"),
            avg_memory_pct=avg_val if "mem" in str(metric.get("__name__", "")).lower() else _float(metric, "memory"),
        )

        records.append(EnrichmentTelemetry(
            entity_name=matched_name,
            entity_type="vm",
            monitoring_tool=MonitoringTool.PROMETHEUS.value,
            collection_period_days=_int(metric, "period_days") or 7,
            sample_count=len(values) if isinstance(values, list) else 0,
            metrics=metrics,
            tags={k: v for k, v in metric.items() if k != "__name__" and isinstance(v, str)},
            raw_data_snippet=json.dumps(item, default=str)[:500],
            ingested_at=datetime.now(timezone.utc).isoformat(),
        ))

    return records


def _parse_generic(raw: dict, vm_names: set[str]) -> list[EnrichmentTelemetry]:
    """Parse generic / custom monitoring export — expects a simple list of
    objects with 'hostname' (or 'vm_name'/'host'/'name') plus metric fields."""
    records: list[EnrichmentTelemetry] = []
    items = raw if isinstance(raw, list) else raw.get("data", raw.get("results", raw.get("hosts", [raw])))
    if isinstance(items, dict):
        items = [items]

    for item in items:
        name = (
            item.get("hostname")
            or item.get("vm_name")
            or item.get("host")
            or item.get("name")
            or item.get("server", "")
        )
        matched_name = _fuzzy_match(str(name), vm_names)
        if not matched_name:
            continue

        metrics = EnrichmentMetrics(
            avg_cpu_pct=_float(item, "avg_cpu", "cpu_pct", "cpu_percent", "cpu_usage", "cpu"),
            p95_cpu_pct=_float(item, "p95_cpu", "cpu_p95"),
            max_cpu_pct=_float(item, "max_cpu", "cpu_max"),
            avg_memory_pct=_float(item, "avg_memory", "mem_pct", "memory_percent", "memory_usage", "memory"),
            p95_memory_pct=_float(item, "p95_memory", "mem_p95"),
            max_memory_pct=_float(item, "max_memory", "mem_max"),
            avg_disk_iops=_float(item, "disk_iops", "iops"),
            p95_disk_iops=_float(item, "disk_iops_p95"),
            avg_network_kbps=_float(item, "network_kbps", "net_kbps"),
            p95_network_kbps=_float(item, "network_kbps_p95"),
            avg_response_time_ms=_float(item, "response_time", "latency"),
            p95_response_time_ms=_float(item, "response_time_p95", "latency_p95"),
            error_rate_pct=_float(item, "error_rate", "errors"),
            request_rate_rpm=_float(item, "request_rate", "rpm", "throughput"),
            active_connections=_int(item, "connections", "active_connections"),
            dependency_count=_int(item, "dependency_count", "deps"),
        )

        records.append(EnrichmentTelemetry(
            entity_name=matched_name,
            entity_type="vm",
            monitoring_tool="custom",
            collection_period_days=_int(item, "period_days", "days") or 30,
            sample_count=_int(item, "sample_count", "count") or 0,
            metrics=metrics,
            dependencies=_list_str(item, "dependencies"),
            tags=_extract_tags(item),
            raw_data_snippet=json.dumps(item, default=str)[:500],
            ingested_at=datetime.now(timezone.utc).isoformat(),
        ))

    return records


# Parser dispatch table
_PARSERS: dict[str, Any] = {
    MonitoringTool.DYNATRACE.value: _parse_dynatrace,
    MonitoringTool.NEW_RELIC.value: _parse_new_relic,
    MonitoringTool.DATADOG.value: _parse_datadog,
    MonitoringTool.SPLUNK.value: _parse_splunk,
    MonitoringTool.PROMETHEUS.value: _parse_prometheus,
    MonitoringTool.ZABBIX.value: _parse_generic,
    MonitoringTool.APP_DYNAMICS.value: _parse_generic,
    MonitoringTool.CUSTOM.value: _parse_generic,
}


# ---------------------------------------------------------------------------
# Main ingestion API
# ---------------------------------------------------------------------------


def ingest_telemetry(
    raw_data: dict | list,
    tool: str,
    vm_names: list[str],
) -> EnrichmentResult:
    """Ingest monitoring export and return normalised enrichment records.

    Parameters
    ----------
    raw_data : dict | list
        Parsed JSON from the monitoring tool export.
    tool : str
        One of the ``MonitoringTool`` values, or 'custom'.
    vm_names : list[str]
        All known VM names from the current vCenter discovery, used for
        fuzzy matching monitoring entity names → VM names.

    Returns
    -------
    EnrichmentResult
        Contains matched records, counts, and per-entity confidence boosts.
    """
    tool_key = tool.lower().replace(" ", "_").replace("-", "_")
    parser = _PARSERS.get(tool_key, _parse_generic)

    name_set = set(vm_names)
    now = datetime.now(timezone.utc).isoformat()

    try:
        if isinstance(raw_data, list):
            records = _parse_generic({"data": raw_data}, name_set)
        else:
            records = parser(raw_data, name_set)
    except Exception as exc:
        logger.error("Error parsing %s data: %s", tool, exc)
        records = []

    # Calculate confidence boost for each record
    for rec in records:
        rec.confidence_boost = _calculate_confidence_boost(rec)

    matched = len(records)
    # Estimate total records in the raw data
    total = _estimate_total_records(raw_data)

    result = EnrichmentResult(
        tool=tool_key,
        entities_matched=matched,
        entities_unmatched=max(0, total - matched),
        total_records=total,
        ingested_at=now,
        telemetry=records,
    )
    logger.info(
        "Enrichment ingestion complete: tool=%s, matched=%d/%d",
        tool, matched, total,
    )
    return result


# ---------------------------------------------------------------------------
# Confidence boost calculation
# ---------------------------------------------------------------------------

# Weights for different metric categories — how much each contributes to boost
_METRIC_WEIGHTS = {
    "cpu":          5.0,   # avg CPU → +5
    "cpu_p95":      3.0,   # p95 CPU → +3
    "memory":       5.0,   # avg memory → +5
    "memory_p95":   3.0,   # p95 memory → +3
    "disk_iops":    2.0,   # disk IOPS → +2
    "network":      2.0,   # network throughput → +2
    "response_time": 2.0,  # app response time → +2
    "error_rate":   1.0,   # error rate → +1
    "dependencies": 2.0,   # discovered dependencies → +2
    "period":       3.0,   # long observation period → up to +3
    "samples":      2.0,   # high sample count → up to +2
}

MAX_CONFIDENCE_BOOST = 30.0  # cap at +30%


def _calculate_confidence_boost(rec: EnrichmentTelemetry) -> float:
    """Calculate how much this enrichment record should boost confidence.

    Each non-null metric contributes its weight.  Longer observation
    periods and higher sample counts add extra credit.
    """
    boost = 0.0
    m = rec.metrics

    if m.avg_cpu_pct is not None:
        boost += _METRIC_WEIGHTS["cpu"]
    if m.p95_cpu_pct is not None:
        boost += _METRIC_WEIGHTS["cpu_p95"]
    if m.avg_memory_pct is not None:
        boost += _METRIC_WEIGHTS["memory"]
    if m.p95_memory_pct is not None:
        boost += _METRIC_WEIGHTS["memory_p95"]
    if m.avg_disk_iops is not None:
        boost += _METRIC_WEIGHTS["disk_iops"]
    if m.avg_network_kbps is not None:
        boost += _METRIC_WEIGHTS["network"]
    if m.avg_response_time_ms is not None:
        boost += _METRIC_WEIGHTS["response_time"]
    if m.error_rate_pct is not None:
        boost += _METRIC_WEIGHTS["error_rate"]
    if rec.dependencies:
        boost += _METRIC_WEIGHTS["dependencies"]

    # Period bonus: +1 per 10 days up to +3
    if rec.collection_period_days > 0:
        period_bonus = min(rec.collection_period_days / 10.0, 3.0)
        boost += period_bonus

    # Sample bonus: +1 per 1000 samples up to +2
    if rec.sample_count > 0:
        sample_bonus = min(rec.sample_count / 1000.0, 2.0)
        boost += sample_bonus

    return round(min(boost, MAX_CONFIDENCE_BOOST), 1)


def apply_enrichment_to_confidence(
    base_confidence: float,
    enrichment_boost: float,
    cap: float = 98.0,
) -> float:
    """Apply enrichment boost to a base confidence, capped at ``cap``."""
    return min(round(base_confidence + enrichment_boost, 1), cap)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fuzzy_match(name: str, vm_names: set[str]) -> str | None:
    """Try to match a monitoring entity name to a known VM name.

    Supports exact match, case-insensitive, FQDN prefix, and substring.
    """
    if not name:
        return None

    name_stripped = name.strip()

    # Exact match
    if name_stripped in vm_names:
        return name_stripped

    # Case-insensitive
    lower = name_stripped.lower()
    for vn in vm_names:
        if vn.lower() == lower:
            return vn

    # FQDN: monitoring tool may report 'web-01.corp.local', VM is 'web-01'
    short = name_stripped.split(".")[0]
    for vn in vm_names:
        if vn.lower() == short.lower():
            return vn

    # Substring match: VM name contained in monitoring name or vice-versa
    for vn in vm_names:
        if vn.lower() in lower or lower in vn.lower():
            return vn

    return None


def _float(obj: dict, *keys: str) -> float | None:
    """Return the first key that maps to a numeric value."""
    for k in keys:
        # Support nested dot keys
        parts = k.split(".")
        cur: Any = obj
        for p in parts:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                cur = None
                break
        if cur is not None:
            try:
                return float(cur)
            except (ValueError, TypeError):
                continue
    return None


def _int(obj: dict, *keys: str) -> int | None:
    """Return the first key that maps to an integer value."""
    for k in keys:
        v = obj.get(k)
        if v is not None:
            try:
                return int(v)
            except (ValueError, TypeError):
                continue
    return None


def _list_str(obj: dict, *keys: str) -> list[str]:
    """Return the first key whose value is a list of strings."""
    for k in keys:
        v = obj.get(k)
        if isinstance(v, list):
            return [str(x) for x in v[:20]]
    return []


def _extract_tags(obj: dict) -> dict[str, str]:
    """Pull out common tag-like fields from a monitoring entity."""
    tags: dict[str, str] = {}
    for k in ("tags", "labels", "metadata", "customProperties"):
        v = obj.get(k)
        if isinstance(v, dict):
            for tk, tv in v.items():
                tags[str(tk)] = str(tv)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and ":" in item:
                    tk, tv = item.split(":", 1)
                    tags[tk] = tv
    return dict(list(tags.items())[:20])


def _estimate_total_records(raw: Any) -> int:
    """Estimate the number of entity records in the raw data."""
    if isinstance(raw, list):
        return len(raw)
    if isinstance(raw, dict):
        for k in ("result", "entities", "hosts", "results", "data", "series",
                   "host_list", "facets", "rows"):
            v = raw.get(k)
            if isinstance(v, list):
                return len(v)
            if isinstance(v, dict):
                return len(v)
    return 1


def _is_numeric(v: Any) -> bool:
    """Check if a value (or a list element) is numeric."""
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, list) and len(v) > 1:
        try:
            float(v[1])
            return True
        except (ValueError, TypeError):
            return False
    if isinstance(v, str):
        try:
            float(v)
            return True
        except ValueError:
            return False
    return False


# ---------------------------------------------------------------------------
# Utility: generate sample enrichment data for demos
# ---------------------------------------------------------------------------

def generate_sample_enrichment(
    vm_names: list[str],
    tool: str = "dynatrace",
) -> dict:
    """Generate realistic sample monitoring export JSON for demo purposes."""
    import random as _rand

    records = []
    for name in vm_names:
        records.append({
            "displayName": name,
            "entityName": name,
            "properties": {
                "cpuUsage": round(_rand.uniform(5, 85), 1),
                "cpuUsage95th": round(_rand.uniform(30, 95), 1),
                "memoryUsage": round(_rand.uniform(20, 90), 1),
                "memoryUsage95th": round(_rand.uniform(40, 95), 1),
                "diskIOPS": round(_rand.uniform(10, 500), 0),
                "networkBandwidth": round(_rand.uniform(50, 5000), 0),
                "responseTime": round(_rand.uniform(5, 500), 1),
                "errorRate": round(_rand.uniform(0, 5), 2),
                "activeConnections": _rand.randint(1, 200),
                "monitoringDays": 30,
                "sampleCount": _rand.randint(500, 5000),
            },
            "tags": {"env": _rand.choice(["prod", "staging", "dev"]), "tier": _rand.choice(["web", "app", "db"])},
            "dependencies": [f"dep-{_rand.randint(1,50)}" for _ in range(_rand.randint(0, 5))],
        })

    return {"entities": records}
