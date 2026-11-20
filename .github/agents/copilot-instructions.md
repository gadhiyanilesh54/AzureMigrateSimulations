# AzureMigrateSimulations Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-04

## Active Technologies
- Python ≥ 3.10 (type hints, dataclasses, match statements) + Flask ≥ 3.0 (web), argparse + Rich (CLI), mcp[server] (MCP), no new PyPI deps required (002-migration-risk-heatmap)
- JSON persistence (`data/*.json`) — no database; risk scores computed on-demand from existing discovery data (002-migration-risk-heatmap)

- Python 3.10+ (backend), vanilla JavaScript ES2020+ (frontend) + Flask (backend), vis-network 9.1.6, Chart.js 4.4.1, Bootstrap 5.3.3 (all existing CDN deps — zero new dependencies) (001-cloud-topology-diagram)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.10+ (backend), vanilla JavaScript ES2020+ (frontend): Follow standard conventions

## Recent Changes
- 002-migration-risk-heatmap: Added Python ≥ 3.10 (type hints, dataclasses, match statements) + Flask ≥ 3.0 (web), argparse + Rich (CLI), mcp[server] (MCP), no new PyPI deps required

- 001-cloud-topology-diagram: Added Python 3.10+ (backend), vanilla JavaScript ES2020+ (frontend) + Flask (backend), vis-network 9.1.6, Chart.js 4.4.1, Bootstrap 5.3.3 (all existing CDN deps — zero new dependencies)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
