---
feature: connect-data-ingestion
status: implemented
module: web/app.py, vcenter_discovery.py
---

# Connect & Data Ingestion

## Summary

Provides two entry points for loading VMware infrastructure data into the application: live vCenter connection via pyVmomi and offline JSON upload. Serves as the gateway to all downstream discovery, assessment, and simulation features.

## User Stories

- As an infrastructure engineer, I want to connect to my vCenter server with credentials so that my VMware environment is automatically discovered.
- As a consultant, I want to upload a previously exported discovery JSON so that I can analyse a client's environment offline.
- As a user, I want to see real-time discovery progress so that I know when data is ready.
- As a user, I want to disconnect and reset state so that I can start a fresh discovery.

## Functional Requirements

- **FR-1:** Accept vCenter host, username, and password via a POST request and initiate asynchronous discovery.
- **FR-2:** Support SSL-disabled connections for lab environments (`VCENTER_DISABLE_SSL`).
- **FR-3:** Poll discovery progress via a status endpoint returning percentage, phase, and discovered counts.
- **FR-4:** Accept a JSON file upload containing a previously exported discovery report.
- **FR-5:** Validate uploaded JSON structure before loading (must contain `vms` array at minimum).
- **FR-6:** Persist discovered data to `data/vcenter_discovery.json` on successful discovery.
- **FR-7:** Automatically trigger Azure SKU recommendation generation after discovery completes.
- **FR-8:** Provide a disconnect endpoint that clears all in-memory state.
- **FR-9:** Expose a status endpoint returning overall application state (connected, VM count, etc.).

## Non-Functional Requirements

- **NFR-1:** Discovery must run asynchronously and not block the web server.
- **NFR-2:** Connection timeout must be configurable (default: 30 s).
- **NFR-3:** Credentials must never be logged or returned in API responses.
- **NFR-4:** Uploaded files must be validated for size and format before processing.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/connect` | Connect to vCenter and start discovery |
| `GET` | `/api/discover/status` | Poll discovery progress |
| `POST` | `/api/disconnect` | Reset connection state |
| `POST` | `/api/upload` | Upload a saved discovery JSON |
| `GET` | `/api/status` | Overall app status |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — endpoint handlers
- [src/digital_twin_migrate/vcenter_discovery.py](../src/digital_twin_migrate/vcenter_discovery.py) — pyVmomi connection and discovery engine
- [src/digital_twin_migrate/config.py](../src/digital_twin_migrate/config.py) — `VCenterConfig` dataclass
- [src/digital_twin_migrate/web/validation.py](../src/digital_twin_migrate/web/validation.py) — `require_fields()` for input validation

### Key Classes / Functions

- `VCenterConfig` — holds host, port, user, password, SSL toggle
- `discover_environment(cfg, collect_perf)` — main discovery entry point returning `DiscoveredEnvironment`
- `_connect(host, port, user, pwd, disable_ssl)` — pyVmomi SmartConnect wrapper
- `require_fields(body, fields)` — request body validation helper

### Data Models

- `DiscoveredEnvironment` — top-level container (VMs, hosts, datastores, networks, clusters, datacenters)
- `DiscoveredVM`, `DiscoveredHost`, `DiscoveredDatastore`, `DiscoveredNetwork`

## Dependencies

- `pyVmomi` — VMware vSphere API bindings
- `Flask` — web framework
- `pydantic` — data validation (indirectly via models)

## Test Coverage

- `tests/test_config.py` — validates configuration loading and credential masking

## Acceptance Criteria

- [ ] POST `/api/connect` with valid credentials returns 200 and starts async discovery.
- [ ] GET `/api/discover/status` returns progress percentage during discovery.
- [ ] POST `/api/upload` with valid JSON loads VMs and triggers recommendation generation.
- [ ] POST `/api/upload` with malformed JSON returns 400 with descriptive error.
- [ ] POST `/api/disconnect` clears all in-memory data; subsequent GET `/api/status` reports disconnected.
- [ ] Credentials are never present in API responses or log output.
