---
feature: cli-interface
status: implemented
module: main.py, visualization.py
---

# CLI Interface

## Summary

Command-line entry point (`dt-migrate`) for automated discovery-to-digital-twin workflows. Provides non-interactive batch execution for CI/CD pipelines and scripting, with Rich-formatted console output.

## User Stories

- As a DevOps engineer, I want to run discovery from the command line so that I can automate it in a CI pipeline.
- As a developer, I want verbose logging so that I can debug connection issues.

## Functional Requirements

- **FR-1:** Discover vCenter environment using credentials from `.env` or environment variables.
- **FR-2:** Generate Azure SKU recommendations for all discovered VMs.
- **FR-3:** Optionally enrich with performance history from a JSON file.
- **FR-4:** Optionally provision Azure Digital Twins instance and create digital twins.
- **FR-5:** Export discovery report to JSON file.
- **FR-6:** Rich-formatted output: summary panel, topology tree, VM table, recommendations table, issues report.

## CLI Flags

| Flag | Description |
|------|-------------|
| `--discover-only` | Run vCenter discovery without creating Azure Digital Twins |
| `--skip-twin` | Skip Azure Digital Twins creation |
| `--skip-perf` | Skip performance counter collection |
| `--export <file>` | Export discovery data to JSON (default: `discovery_report.json`) |
| `--region <region>` | Target Azure region (default: `eastus`) |
| `--perf-history <file>` | Path to `perf_history.json` for enriched sizing |
| `-v, --verbose` | Enable verbose/debug logging |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/main.py](../src/digital_twin_migrate/main.py) — argument parsing, orchestration
- [src/digital_twin_migrate/visualization.py](../src/digital_twin_migrate/visualization.py) — Rich console output (tables, trees, panels)
- [src/digital_twin_migrate/twin_builder.py](../src/digital_twin_migrate/twin_builder.py) — Azure Digital Twins creation
- [src/digital_twin_migrate/azure_provisioning.py](../src/digital_twin_migrate/azure_provisioning.py) — ARM resource provisioning

### Key Classes / Functions

- `main()` — CLI entry point registered as `dt-migrate` console script
- `print_discovery_summary(env)` — Rich panel with VM/host/datastore counts
- `print_topology_tree(env)` — Rich tree showing DC → Cluster → Host → VM hierarchy
- `print_vm_table(env)` — Rich table of discovered VMs
- `print_recommendations_table(recs)` — Rich table of SKU recommendations
- `print_issues_report(recs)` — Rich panel of migration issues
- `export_report_json(env, recs, path)` — JSON export

## Test Coverage

- `tests/test_visualization.py` — validates Rich output formatting

## Acceptance Criteria

- [ ] `dt-migrate --discover-only --export report.json` discovers VMs and writes JSON without Azure provisioning.
- [ ] Auto-detects `data/perf_history.json` for enrichment when `--perf-history` is not specified.
- [ ] `--verbose` enables DEBUG-level logging.
- [ ] Exit code 1 when vCenter credentials are missing.
- [ ] Exported JSON is valid and contains VMs + recommendations.
