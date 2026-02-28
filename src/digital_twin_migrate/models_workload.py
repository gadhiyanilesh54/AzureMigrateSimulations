"""Data models for guest-level workload discovery (databases, webapps,
containers, orchestrators, and cross-VM dependency topology)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WorkloadType(str, Enum):
    DATABASE = "database"
    WEBAPP = "webapp"
    CONTAINER_RUNTIME = "container_runtime"
    ORCHESTRATOR = "orchestrator"


class DatabaseEngine(str, Enum):
    MSSQL = "mssql"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    MONGODB = "mongodb"
    REDIS = "redis"
    MARIADB = "mariadb"
    UNKNOWN = "unknown"


class WebAppRuntime(str, Enum):
    DOTNET_FRAMEWORK = "dotnet_framework"
    DOTNET_CORE = "dotnet_core"
    JAVA = "java"
    PHP = "php"
    PYTHON = "python"
    NODEJS = "nodejs"
    RUBY = "ruby"
    GO = "go"
    UNKNOWN = "unknown"


class ContainerRuntimeType(str, Enum):
    DOCKER = "docker"
    CONTAINERD = "containerd"
    PODMAN = "podman"
    CRIO = "cri-o"
    UNKNOWN = "unknown"


class OrchestratorType(str, Enum):
    KUBERNETES = "kubernetes"
    DOCKER_SWARM = "docker_swarm"
    OPENSHIFT = "openshift"
    NOMAD = "nomad"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Discovered workloads
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredDatabase:
    vm_name: str = ""
    engine: DatabaseEngine = DatabaseEngine.UNKNOWN
    version: str = ""
    instance_name: str = ""
    port: int = 0
    databases: list[str] = field(default_factory=list)
    size_mb: float = 0.0
    status: str = "running"
    edition: str = ""          # e.g. Enterprise, Standard, Community


@dataclass
class DiscoveredWebApp:
    vm_name: str = ""
    runtime: WebAppRuntime = WebAppRuntime.UNKNOWN
    runtime_version: str = ""
    framework: str = ""        # ASP.NET, Spring Boot, Django, Express …
    app_name: str = ""
    port: int = 0
    binding: str = ""          # e.g. http://localhost:8080, IIS site binding
    app_pool: str = ""         # IIS application pool name
    status: str = "running"
    process_name: str = ""
    pid: int = 0


@dataclass
class ContainerInfo:
    container_id: str = ""
    name: str = ""
    image: str = ""
    status: str = ""
    ports: list[str] = field(default_factory=list)


@dataclass
class DiscoveredContainerRuntime:
    vm_name: str = ""
    runtime: ContainerRuntimeType = ContainerRuntimeType.UNKNOWN
    version: str = ""
    containers: list[ContainerInfo] = field(default_factory=list)
    total_containers: int = 0
    running_containers: int = 0


@dataclass
class DiscoveredOrchestrator:
    vm_name: str = ""
    type: OrchestratorType = OrchestratorType.UNKNOWN
    version: str = ""
    role: str = ""             # control-plane, worker
    cluster_name: str = ""
    node_count: int = 0
    pod_count: int = 0
    namespace_count: int = 0


@dataclass
class ListeningPort:
    port: int = 0
    protocol: str = "tcp"
    process: str = ""
    pid: int = 0
    address: str = "0.0.0.0"


@dataclass
class EstablishedConnection:
    """An outbound established connection from this VM."""
    local_port: int = 0
    remote_ip: str = ""
    remote_port: int = 0
    process: str = ""
    pid: int = 0


@dataclass
class WorkloadDependency:
    """Directed edge: source_vm/workload depends on target_vm/workload."""
    source_vm: str = ""
    source_workload: str = ""
    target_vm: str = ""
    target_workload: str = ""
    target_port: int = 0
    protocol: str = "tcp"
    connection_count: int = 1


# ---------------------------------------------------------------------------
# Per-VM workload summary
# ---------------------------------------------------------------------------

@dataclass
class VMWorkloads:
    vm_name: str = ""
    ip_addresses: list[str] = field(default_factory=list)
    os_family: str = ""
    scan_status: str = "pending"   # pending | scanning | complete | error | skipped
    scan_error: str = ""
    databases: list[DiscoveredDatabase] = field(default_factory=list)
    web_apps: list[DiscoveredWebApp] = field(default_factory=list)
    container_runtimes: list[DiscoveredContainerRuntime] = field(default_factory=list)
    orchestrators: list[DiscoveredOrchestrator] = field(default_factory=list)
    listening_ports: list[ListeningPort] = field(default_factory=list)
    established_connections: list[EstablishedConnection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Full workload discovery result
# ---------------------------------------------------------------------------

@dataclass
class WorkloadDiscoveryResult:
    """Complete result of a guest-level workload scan across VMs."""
    vm_workloads: list[VMWorkloads] = field(default_factory=list)
    dependencies: list[WorkloadDependency] = field(default_factory=list)
    total_databases: int = 0
    total_webapps: int = 0
    total_containers: int = 0
    total_orchestrators: int = 0
    scanned_count: int = 0
    error_count: int = 0
    skipped_count: int = 0


# ---------------------------------------------------------------------------
# Azure workload recommendation
# ---------------------------------------------------------------------------

@dataclass
class WorkloadRecommendation:
    vm_name: str = ""
    workload_name: str = ""
    workload_type: str = ""                   # database / webapp / container
    source_engine: str = ""                   # mssql / mysql / dotnet_core / docker …
    source_version: str = ""
    recommended_azure_service: str = ""       # e.g. Azure SQL Database
    alternative_services: list[str] = field(default_factory=list)
    estimated_monthly_cost_usd: float = 0.0
    migration_approach: str = ""              # rehost / replatform / refactor
    migration_complexity: str = ""            # low / medium / high
    migration_steps: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    confidence: float = 50.0
