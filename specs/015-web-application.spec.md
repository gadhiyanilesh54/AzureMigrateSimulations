---
feature: web-application
status: implemented
module: web/app.py, web/templates/index.html, web/validation.py
---

# Web Application (Flask Dashboard)

## Summary

Single-page Flask web dashboard serving as the primary user interface. Hosts 57 REST API endpoints, renders an interactive Bootstrap 5 dark-theme UI with tabs for Dashboard, Discovery & Assessment, Business Case, and Enrichment. Includes optional API key authentication.

## Functional Requirements

- **FR-1:** Serve a single-page HTML application at `/` with tabbed navigation.
- **FR-2:** Expose 57 REST API endpoints across 9 categories (see API Reference in README).
- **FR-3:** Optional API key authentication: when `MIGRATE_API_KEY` env var is set, all `/api/*` routes require `X-API-Key` header.
- **FR-4:** Auto-load sample data from `data/` directory on startup (vcenter_discovery, workload_discovery, enrichment, perf history, what-if overrides).
- **FR-5:** Persist state to JSON files in `data/` directory.
- **FR-6:** Request validation via `validation.py` helpers (`require_fields`, `validate_int`, `validate_choice`).
- **FR-7:** CORS support for API consumers.
- **FR-8:** Error responses use consistent JSON format: `{ "error": "message" }`.

## Non-Functional Requirements

- **NFR-1:** Single-file SPA — no build step required for frontend.
- **NFR-2:** All frontend assets loaded from CDN (Bootstrap, Chart.js, vis-network, Bootstrap Icons).
- **NFR-3:** Dark theme using Bootstrap 5.3.3 `data-bs-theme="dark"`.
- **NFR-4:** Application must start within 5 seconds.
- **NFR-5:** No external database — JSON file persistence only.

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Flask | ≥ 3.0.0 |
| Frontend CSS | Bootstrap | 5.3.3 |
| Icons | Bootstrap Icons | 1.11.3 |
| Charts | Chart.js | 4.4.1 |
| Network graphs | vis-network | 9.1.6 |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — Flask app factory, all 57 endpoints (3328 lines)
- [src/digital_twin_migrate/web/templates/index.html](../src/digital_twin_migrate/web/templates/index.html) — SPA template (5560 lines)
- [src/digital_twin_migrate/web/validation.py](../src/digital_twin_migrate/web/validation.py) — request validation helpers (74 lines)

### Key Classes / Functions

- `create_app()` or module-level Flask app — app factory
- `@app.before_request` — API key enforcement
- `main()` — entry point registered as `dt-migrate-web`
- `require_fields(body, fields)` — validates required JSON fields
- `validate_int(body, key, default, lo, hi)` — integer parameter validation
- `validate_choice(body, key, choices, default)` — enum parameter validation

## Acceptance Criteria

- [ ] `python -m digital_twin_migrate.web.app` starts the server on port 5000.
- [ ] GET `/` returns the HTML dashboard.
- [ ] All 57 API endpoints respond with correct status codes.
- [ ] Setting `MIGRATE_API_KEY` env var enforces authentication on API routes.
- [ ] Sample data auto-loads from `data/` on startup.
- [ ] Invalid requests return 400 with descriptive JSON error messages.
