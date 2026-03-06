---
feature: core-data-models
status: implemented
module: models.py, models_workload.py, config.py
---

# Core Data Models

## Summary

Foundation data models for the entire application. Defines infrastructure entities (VMs, hosts, datastores, networks), workload entities (databases, web apps, containers), configuration management, and performance metrics.

## Modules

### Infrastructure Models (`models.py`)

Pydantic-style dataclass models for discovered VMware infrastructure:

- **Enums:** `GuestOSFamily` (Windows, Linux, Other), `PowerState` (poweredOn, poweredOff, suspended)
- **`DiskInfo`** — per-disk capacity, IOPS, latency
- **`NetworkInfo`** — NIC name, MAC, IPs, connected network
- **`PerformanceMetrics`** — avg, P50, P95, P99, max for CPU, memory, disk IOPS, throughput, network
- **`DiscoveredVM`** — name, OS, CPU, memory, disks, NICs, power state, perf metrics, tags, snapshots, NUMA, boot type, folder path, VMware tools status
- **`DiscoveredHost`** — name, CPU model/cores, memory, ESXi version, VMs
- **`DiscoveredDatastore`** — name, type, capacity, free space, VMs
- **`DiscoveredNetwork`** — name, type, VLAN, VMs
- **`DiscoveredCluster`** — name, hosts, HA/DRS status
- **`DiscoveredDatacenter`** — name, clusters
- **`DiscoveredEnvironment`** — top-level container holding all of the above

### Workload Models (`models_workload.py`)

Dataclass models for guest-discovered workloads:

- **Enums:** `DatabaseEngine` (7 engines), `WebAppRuntime` (8 runtimes), `ContainerRuntimeType` (4 types), `OrchestratorType`
- **`DiscoveredDatabase`** — engine, version, size, connections, port, auth
- **`DiscoveredWebApp`** — runtime, framework, port, sites/pools
- **`DiscoveredContainerRuntime`** — type, version, container count
- **`DiscoveredOrchestrator`** — type, version, node count, pod count
- **`ListeningPort`** — port, protocol, process, VM
- **`EstablishedConnection`** — source/dest VM, port, service
- **`WorkloadDependency`** — directed dependency edge
- **`VMWorkloads`** — per-VM roll-up of all discovered workloads
- **`WorkloadDiscoveryResult`** — scan-wide totals

### Configuration (`config.py`)

- **`VCenterConfig`** — host, port, user, password, disable_ssl (password masked in `__repr__`)
- **`AzureConfig`** — subscription_id, resource_group, location, dt_instance
- **`DiscoveryConfig`** — collect_perf toggle, interval
- **`AppConfig`** — aggregates VCenter + Azure + Discovery configs
- **`load_config()`** — reads from env vars and `.env` file

## Test Coverage

- `tests/test_models.py` — validates model construction and field defaults
- `tests/test_config.py` — validates config loading, env vars, credential masking

## Conventions

- All models use Python `@dataclass` with type annotations.
- Optional fields default to `None` or empty collections.
- Enums use `str` mixin for JSON serialisation compatibility.
- Credentials are never included in `__repr__` output.
