<!--
  Sync Impact Report
  ─────────────────────────────────────────────────────────────
  Version change: N/A → 1.0.0 (initial ratification)
  Modified principles: N/A (first version)
  Added sections:
    - Core Principles (7 principles)
    - Technology Stack & Constraints
    - Development Workflow & Quality Gates
    - Governance
  Removed sections: N/A
  Templates requiring updates:
    - .specify/templates/plan-template.md        ✅ reviewed — compatible
    - .specify/templates/spec-template.md         ✅ reviewed — compatible
    - .specify/templates/tasks-template.md        ✅ reviewed — compatible
  Follow-up TODOs: None
-->

# Azure Migrate Simulations Constitution

## Core Principles

### I. Offline-First & Data Sovereignty

All discovery, assessment, simulation, and reporting MUST operate
without requiring an active Azure subscription or internet connection.
Zero telemetry or workload data leaves the user's machine unless they
explicitly invoke an Azure API (e.g., live pricing, Digital Twins
provisioning). JSON file I/O is the canonical data interchange format —
every stage of the pipeline MUST be round-trippable through
`data/*.json` files so consultants can carry results on portable media
into air-gapped environments.

**Rationale**: The primary differentiator versus Azure Migrate (SaaS) is
operating inside regulated, air-gapped data centres where data egress is
prohibited before migration approval.

### II. Src-Layout Python Package

All production source code lives under `src/azure_migrate_simulations/`
using the setuptools src-layout defined in `pyproject.toml`. Every new
module MUST be a single-file Python module placed directly in that
package directory unless a sub-package is structurally justified (e.g.,
`web/`). Imports MUST use the fully qualified package name
(`azure_migrate_simulations.*`) — never relative path hacks or
`sys.path` manipulation outside of test config.

**Rationale**: The src-layout prevents accidental imports of the
un-installed package and keeps `PYTHONPATH=src` as the sole environment
requirement for development.

### III. Dataclass Models as Contracts

Data flowing between modules MUST be represented as Python `dataclasses`
defined in `models.py` (infrastructure) or `models_workload.py`
(workloads). New entity types MUST follow the existing pattern: explicit
fields with sensible defaults, `str` Enum members for serialisation, and
no Pydantic or ORM coupling in the core models. JSON serialisation MUST
use `dataclasses.asdict()` or compatible conversion — custom
`__json__` methods are prohibited.

**Rationale**: Dataclass contracts keep the assessment engine, web API,
CLI, and MCP server in sync without schema drift. Pydantic is a
declared dependency but is reserved for external-facing validation (API
input), not internal domain models.

### IV. Dual Interface — CLI + Web (Flask)

Every major capability MUST be accessible both through the `dt-migrate`
CLI (argparse, stdout/stderr, exit codes) and the Flask REST API served
by `web/app.py`. The CLI is the automation-first interface; the web
dashboard is the human exploration interface. New features MUST NOT be
web-only — a programmatic path (CLI flag or API endpoint) is required.

**Rationale**: SI partners script assessments across hundreds of customer
environments; a web-only feature blocks automation pipelines.

### V. Test Discipline

- **Unit tests** (pytest, `tests/`) MUST cover models, mapping logic,
  and pure-function modules. Tests MUST run with `pytest` from the
  repo root with no external services.
- **End-to-end tests** (Playwright, `e2e/`) validate the Flask dashboard
  against a running server using data fixtures in `data/`.
- New modules MUST include at least smoke-level unit tests before merge.
- Tests MUST NOT depend on live vCenter, Azure, or external APIs;
  mock or fixture data is mandatory.

**Rationale**: The project runs in customer environments where
CI runners have no network access; tests must be self-contained.

### VI. Spec-Driven Features

Every non-trivial feature MUST have a specification under `specs/` with
a numeric prefix (e.g., `016-feature-name.spec.md`) before
implementation begins. Specs define user scenarios, acceptance criteria,
API contracts, and edge cases. Implementation without a merged spec is
permitted only for bug fixes and documentation.

**Rationale**: The spec directory is the single source of truth for what
the product does and why — it bridges product intent and engineering
execution.

### VII. Simplicity & YAGNI

Modules MUST be self-contained single files unless they genuinely need a
sub-package. Do not introduce ORMs, task queues, microservice splits, or
framework abstractions beyond Flask and argparse without a written spec
justifying the complexity. Hardcoded reference data (SKU catalogues,
region multipliers, compliance frameworks) is preferred over external
config files when the data changes infrequently.

**Rationale**: This is a simulation / assessment tool, not a production
SaaS platform. Operational complexity directly harms the air-gapped
deployment model.

## Technology Stack & Constraints

- **Language**: Python ≥ 3.10 (type hints, `match` statements allowed)
- **Package management**: `pyproject.toml` with setuptools; optional
  dependency groups (`web`, `mcp`, `guest`, `db`, `dev`, `all`)
- **Web framework**: Flask ≥ 3.0 (in `[web]` extras)
- **CLI framework**: argparse (stdlib) + Rich for console output
- **Data models**: stdlib `dataclasses` + `enum.Enum`
- **HTTP client**: `requests` for Azure Retail Pricing API
- **Testing**: pytest (unit), Playwright (e2e), pytest-cov for coverage
- **Containerisation**: Docker (single-stage `python:3.12-slim`),
  `docker-compose.yml` for web + MCP SSE services
- **Linting / Formatting**: follow PEP 8; no mandatory formatter
  configured yet — contributors MUST NOT introduce conflicting
  formatting tools without amending this constitution
- **Frontend**: Server-rendered HTML (Jinja2 templates) + vanilla JS +
  Bootstrap 5 + Chart.js + vis-network — no build step, no npm
  bundler for the dashboard itself
- **Node.js / npm**: Used exclusively for Playwright e2e tests
  (`package.json` at repo root)
- **MCP server**: Optional `mcp[server]` dependency for AI agent
  integration via stdin/stdout or SSE transport

### Dependency Rules

1. Core assessment logic (`models`, `azure_mapping`,
   `workload_mapping`, `cloud_topology`, `vulnerability_sla`) MUST NOT
   import Flask, Paramiko, or any optional-extras dependency.
2. `web/` may import any installed dependency.
3. New PyPI dependencies MUST be added to the correct extras group in
   `pyproject.toml` — never to the base `dependencies` list unless
   every user needs them.
4. Vendoring or pinning exact versions is discouraged; use minimum
   version constraints (e.g., `>=3.0.0`).

### API & Security Rules

1. All REST endpoints live under `/api/` and return JSON.
2. Optional API-key auth via `MIGRATE_API_KEY` env var — when set,
   `/api/*` routes require `X-API-Key` header.
3. User-supplied input (JSON bodies, query params, file uploads) MUST
   be validated using helpers in `web/validation.py` before use.
4. No secrets in source code — credentials come from env vars or `.env`
   (never committed).

## Development Workflow & Quality Gates

### Branching

- `main` is the stable trunk.
- Feature branches use the pattern `NNN-feature-name` matching the spec
  number (e.g., `001-cloud-topology-diagram`).
- PRs target `main` and require passing `pytest` + Playwright checks
  before merge.

### Data Directory Convention

- `data/` contains runtime fixtures and persisted state
  (`vcenter_discovery.json`, `workload_discovery.json`, etc.).
- `data/snapshots/` holds named checkpoint directories for
  rollback/comparison.
- `data/` files MUST NOT be imported as Python modules — load via
  `json.load()` at runtime only.

### Spec Workflow

1. Create `specs/NNN-feature-name.spec.md` from the spec template.
2. Review and approve the spec.
3. Create a feature branch `NNN-feature-name`.
4. Implement against the spec; update the spec if scope changes.
5. Add / update tests.
6. PR → review → merge to `main`.

### Quality Checklist (per PR)

- [ ] `pytest` passes with zero failures
- [ ] No new module imports a dependency outside its extras group
- [ ] New API endpoints are documented in the spec or README
- [ ] Air-gapped operation is preserved (no mandatory network calls)
- [ ] Sensitive data (passwords, API keys) never appear in source or
      committed data files

## Governance

This constitution is the highest-authority document for the
Azure Migrate Simulations project. All specs, plans, and code reviews
MUST verify compliance with the principles above.

### Amendment Procedure

1. Propose the change as a PR modifying this file.
2. Describe the rationale and impact in the PR description.
3. Update `CONSTITUTION_VERSION` using semantic versioning:
   - **MAJOR**: Principle removal or backward-incompatible redefinition.
   - **MINOR**: New principle added or material expansion.
   - **PATCH**: Clarification, typo fix, non-semantic wording change.
4. Update `LAST_AMENDED_DATE` to the merge date.
5. Propagate changes to affected templates under `.specify/templates/`.

### Compliance Review

Every spec and plan MUST include a "Constitution Check" section that
references the principles by number (e.g., "Principle I: confirmed —
no network calls required"). Reviewers MUST flag violations before
approving.

**Version**: 1.0.0 | **Ratified**: 2026-03-31 | **Last Amended**: 2026-03-31
