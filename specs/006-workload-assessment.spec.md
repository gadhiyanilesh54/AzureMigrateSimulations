---
feature: workload-assessment
status: implemented
module: guest_discovery.py, workload_mapping.py, web/app.py
---

# Workload Assessment

## Summary

Guest-level workload discovery via SSH (Linux) and WinRM (Windows) identifies databases, web applications, container runtimes, and orchestrators running on discovered VMs. Each workload is mapped to an Azure PaaS service with a migration playbook.

## User Stories

- As a migration planner, I want to discover databases and web apps inside VMs so that I can recommend PaaS alternatives.
- As an architect, I want each workload mapped to an Azure service with a migration approach (rehost, replatform, refactor) so that I can plan the right strategy.
- As an engineer, I want step-by-step migration playbooks so that I know exactly how to migrate each workload.
- As a user, I want to provide SSH and WinRM credentials through the UI so that guest discovery can connect.

## Functional Requirements

- **FR-1:** Accept multiple SSH and WinRM credential sets via the sidebar drawer.
- **FR-2:** Discover 7 database engines: SQL Server, MySQL, PostgreSQL, MariaDB, MongoDB, Oracle, Redis.
- **FR-3:** Discover 8 web runtimes: IIS, Apache, Nginx, Tomcat, Node.js, .NET Core/Kestrel, Python (Flask/Django/Gunicorn), PHP-FPM.
- **FR-4:** Discover 4 container runtimes: Docker, containerd, Podman, CRI-O.
- **FR-5:** Discover orchestrators: Kubernetes (kubelet/kube-apiserver).
- **FR-6:** Map each workload to Azure PaaS services using 24 migration playbooks.
- **FR-7:** Each mapping includes: Azure service, tier, cost estimate, migration approach, complexity, and step-by-step playbook.
- **FR-8:** Support deep database discovery with optional database credentials for schema/size enumeration.
- **FR-9:** Display results in a table with columns: Workload Name, Source VM, Type, Version, Azure Service, Migration Approach, Complexity, CPU %, Memory (MB), Connections, Monthly Cost ($), Confidence.
- **FR-10:** Workload discovery runs asynchronously with progress polling.

## Non-Functional Requirements

- **NFR-1:** Guest probing uses configurable parallelism (1–20 workers).
- **NFR-2:** SSH/WinRM connection timeout must not exceed 30 seconds per VM.
- **NFR-3:** Credentials must be held in memory only and never persisted to disk.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/workloads/discover` | Trigger guest-level workload discovery |
| `GET` | `/api/workloads/status` | Poll workload discovery progress |
| `GET` | `/api/workloads/results` | Get workload recommendations |
| `POST` | `/api/databases/discover` | Trigger deep database discovery |

## Implementation Details

### Source Files

- [src/digital_twin_migrate/guest_discovery.py](../src/digital_twin_migrate/guest_discovery.py) — SSH/WinRM probing, process scanning (1553 lines)
- [src/digital_twin_migrate/workload_mapping.py](../src/digital_twin_migrate/workload_mapping.py) — PaaS service mapping, playbooks (813 lines)
- [src/digital_twin_migrate/models_workload.py](../src/digital_twin_migrate/models_workload.py) — workload data models
- [src/digital_twin_migrate/web/app.py](../src/digital_twin_migrate/web/app.py) — REST endpoints

### Key Classes / Functions

- `GuestDiscoverer` — orchestrates concurrent multi-VM scanning
- `Credential` / `DatabaseCredential` — credential dataclasses
- `generate_workload_recommendations()` — maps discovered workloads to Azure PaaS options
- `AzureServiceOption` — recommended Azure service with cost, complexity, playbook
- `DB_SERVICE_MAP`, `WEBAPP_SERVICE_MAP`, `CONTAINER_SERVICE_MAP` — per-type catalogs

### Data Models

- `DiscoveredDatabase`, `DiscoveredWebApp`, `DiscoveredContainerRuntime`, `DiscoveredOrchestrator`
- `VMWorkloads` — per-VM workload roll-up
- `WorkloadDiscoveryResult` — scan-wide totals and per-VM results
- `ListeningPort`, `EstablishedConnection`, `WorkloadDependency`

## Dependencies

- `paramiko` — SSH client for Linux guest probing
- `pywinrm` — WinRM client for Windows guest probing
- `pymssql`, `psycopg2`, `pymongo` — optional for deep database discovery

## Test Coverage

- No dedicated workload assessment tests yet.

## Acceptance Criteria

- [ ] POST `/api/workloads/discover` with valid credentials starts async discovery and returns 202.
- [ ] GET `/api/workloads/status` returns progress (VMs scanned, workloads found).
- [ ] GET `/api/workloads/results` returns per-workload Azure PaaS recommendations with playbooks.
- [ ] SQL Server is mapped to Azure SQL Database / MI / VM options.
- [ ] Docker containers are mapped to ACI / ACA options.
- [ ] Each recommendation includes migration steps, complexity, and cost estimate.
- [ ] Deep database discovery returns schema and size details.
