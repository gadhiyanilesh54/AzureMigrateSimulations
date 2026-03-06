---
feature: enrichment-data-loop
status: implemented
module: enrichment.py, web/app.py
---

# Enrichment Data Loop

## Summary

Ingest real-world monitoring telemetry from 8 APM/infrastructure tools to increase assessment accuracy and boost confidence scores. Supports Dynatrace, New Relic, Datadog, Splunk, Prometheus, AppDynamics, Zabbix, and a generic custom format.

## User Stories

- As a migration planner, I want to upload Dynatrace monitoring data so that my assessments are informed by real utilization metrics.
- As an analyst, I want to see which VMs have been enriched and by how much so that I can trust the confidence scores.
- As a user, I want to generate sample enrichment data to demo the feature without needing a real monitoring tool.

## Functional Requirements

- **FR-1:** Display 6 status cards: Total VMs, Enriched VMs, Coverage %, Avg Confidence Boost, Tools Integrated, Data Ingestions.
- **FR-2:** Support 8 monitoring tools with tool-specific JSON parsers:
  - Dynatrace (entities array with properties), New Relic (results array), Datadog (series array), Splunk, Prometheus (time-series), AppDynamics, Zabbix, Custom/Generic.
- **FR-3:** Fuzzy-match entity display names to discovered VM names using: exact match, case-insensitive, FQDN prefix, substring.
- **FR-4:** Produce normalised `EnrichmentTelemetry` records with: avg/P95 CPU, avg/P95 memory, IOPS, network kBps, response time, error rate, dependencies, monitoring period, sample count.
- **FR-5:** Calculate confidence boost (max +30) using weighted formula:
  - CPU metrics: +5, Memory: +5, CPU P95: +3, Memory P95: +3, IOPS: +2, Network: +2, Response time: +2, Error rate: +1, Dependencies: +2, Period: up to +3, Samples: up to +2.
- **FR-6:** Apply boost to both VM and workload assessment confidence scores (capped at 98).
- **FR-7:** Show enrichment telemetry table and before/after confidence chart.
- **FR-8:** Persist enrichment data to `data/enrichment_data.json`; auto-load on restart.
- **FR-9:** Provide sample data generation for demo purposes.
- **FR-10:** Ingestion history log tracking all uploads.

## Non-Functional Requirements

- **NFR-1:** Enrichment upload and matching must complete within 5 seconds for 500 entities.
- **NFR-2:** Partial matches are acceptable; unmatched entities are logged but do not cause errors.
- **NFR-3:** Multiple sequential uploads are additive (latest data per entity wins).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/enrichment/tools` | List supported monitoring tools |
| `POST` | `/api/enrichment/upload` | Upload monitoring JSON for enrichment |
| `POST` | `/api/enrichment/generate_sample` | Generate sample enrichment data |
| `GET` | `/api/enrichment/status` | Coverage and confidence boost stats |
| `GET` | `/api/enrichment/data` | Get all enrichment telemetry data |
| `GET` | `/api/enrichment/vm/<name>` | Get enrichment data for one VM |
| `GET` | `/api/enrichment/history` | Ingestion history log |
| `POST` | `/api/enrichment/clear` | Clear all enrichment data |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/enrichment.py](../src/digital_twin_migrate/enrichment.py) — parsers, matching, boost calculation (724 lines)
- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — enrichment REST endpoints
- [scripts/generate_dynatrace_enrichment.py](../scripts/generate_dynatrace_enrichment.py) — sample data generator

### Key Classes / Functions

- `MonitoringTool` enum — supported tool identifiers
- `EnrichmentMetrics` — normalised CPU/memory/IOPS/response-time percentile metrics
- `EnrichmentTelemetry` — per-entity record with source tool, matched VM, metrics, and `confidence_boost`
- `EnrichmentResult` — aggregated result with matched/unmatched counts
- `ingest_telemetry(data, tool, vm_names)` — main ingestion function
- `apply_enrichment_to_confidence(recommendations, enrichment)` — applies boost
- `generate_sample_enrichment(vm_names)` — creates realistic sample data

### Data Models

- Upload request: multipart form with `tool` field and `file` attachment
- Enrichment status response: `{ total_vms, enriched_vms, coverage_pct, avg_boost, tools_used, ingestion_count }`

## Dependencies

- No external dependencies beyond standard library and Flask.

## Test Coverage

- No dedicated enrichment tests yet; critical path for confidence scoring.

## Acceptance Criteria

- [ ] POST `/api/enrichment/upload` with Dynatrace JSON matches entities to VMs and applies confidence boost.
- [ ] Confidence scores increase by the expected weighted amount (verified via GET `/api/enrichment/status`).
- [ ] Unmatched entities do not cause errors; unmatched count is reported.
- [ ] GET `/api/enrichment/data` returns normalised telemetry for all enriched VMs.
- [ ] POST `/api/enrichment/generate_sample` creates data covering all discovered VMs.
- [ ] POST `/api/enrichment/clear` removes all enrichment data and resets confidence scores.
- [ ] Data persists across application restarts via `data/enrichment_data.json`.
