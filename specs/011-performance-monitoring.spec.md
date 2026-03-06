---
feature: performance-monitoring
status: implemented
module: perf_aggregator.py, web/app.py
---

# Performance Monitoring

## Summary

Background performance data collector that captures real-time CPU, memory, IOPS, and network I/O metrics from the vCenter API every 15 minutes. Supports per-VM sparkline charts and fleet-wide performance summaries for right-sizing validation.

## User Stories

- As an engineer, I want to collect real performance data over time so that right-sizing recommendations are based on actual usage rather than allocated capacity.
- As a user, I want to start/stop the collector and trigger an immediate collection from the UI.
- As an analyst, I want per-VM performance sparklines with P95 stats in the What-If modal so that I can validate SKU choices against usage patterns.

## Functional Requirements

- **FR-1:** Collect 4 metrics per VM every 15 minutes: CPU utilisation (%), memory usage (%), disk IOPS, network I/O (kBps).
- **FR-2:** Provide start, stop, and collect-now controls.
- **FR-3:** Configurable collection interval via API.
- **FR-4:** Per-VM time-series endpoint returning historical samples.
- **FR-5:** Per-VM summary endpoint returning avg, min, max, P95 for each metric.
- **FR-6:** Fleet-wide summary endpoint returning aggregate averages.
- **FR-7:** Workload-scoped performance data endpoint.
- **FR-8:** Persist data to `data/perf_history.json`.
- **FR-9:** Dashboard sidebar shows live status indicator, averages, sample count.
- **FR-10:** Per-VM sparklines in the What-If modal.

## Non-Functional Requirements

- **NFR-1:** Collector runs in a background thread; must not block the web server.
- **NFR-2:** Data file must not grow unboundedly; cap at configurable max samples.
- **NFR-3:** Collection must gracefully handle VMs that are powered off or unreachable.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/perf/status` | Collector status (running, samples, interval) |
| `POST` | `/api/perf/start` | Start background collector |
| `POST` | `/api/perf/stop` | Stop collector |
| `POST` | `/api/perf/collect` | Collect a sample immediately |
| `POST` | `/api/perf/duration` | Set collection interval |
| `GET` | `/api/perf/vm/<name>` | VM time-series perf data |
| `GET` | `/api/perf/vm/<name>/summary` | VM perf stats (avg/min/max/P95) |
| `GET` | `/api/perf/workloads` | Monitored workloads with perf summaries |
| `GET` | `/api/perf/workload/<key>` | Workload time-series perf data |
| `GET` | `/api/perf/summary` | Fleet-wide perf summary |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/perf_aggregator.py](../src/digital_twin_migrate/perf_aggregator.py) — percentile aggregation from raw time-series (179 lines)
- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — collector thread, perf endpoints
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — sidebar perf status, sparkline charts

### Key Classes / Functions

- `_percentile(sorted_data, pct)` — percentile calculation
- `_aggregate_samples(samples)` — computes avg, P50, P95, P99, max for each metric
- `_estimate_days(samples)` — calculates monitoring duration from timestamps
- `apply_perf_history(env, path)` — enriches VMs with percentile-based `PerformanceMetrics`
- Background collector thread in `app.py` using `threading.Timer`

### Data Models

- `PerformanceMetrics` — avg, P50, P95, P99, max for CPU, memory, disk IOPS, throughput, network
- Perf history JSON: `{ samples: [{ timestamp, vm_name, cpu_pct, memory_pct, iops, network_kbps }] }`

## Dependencies

- `pyVmomi` — for real-time vCenter performance counter queries
- Standard library `threading` — background collector

## Test Coverage

- No dedicated perf monitoring tests yet.

## Acceptance Criteria

- [ ] POST `/api/perf/start` starts background collection; GET `/api/perf/status` shows running.
- [ ] POST `/api/perf/collect` captures an immediate sample for all powered-on VMs.
- [ ] GET `/api/perf/vm/<name>` returns time-series data with timestamps.
- [ ] GET `/api/perf/vm/<name>/summary` returns avg, min, max, P95 for all 4 metrics.
- [ ] POST `/api/perf/stop` stops collection; status shows stopped.
- [ ] Data persists to `data/perf_history.json` and is loaded on restart.
- [ ] Sparklines render in the What-If modal when perf data is available.
