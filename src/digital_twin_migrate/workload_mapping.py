"""Azure service mapping for discovered workloads.

Maps on-premises databases, web apps, container runtimes, and orchestrators
to the most appropriate Azure PaaS / IaaS services with cost estimates,
migration approach, and step-by-step guidance.

Matching considers workload characteristics beyond just engine name:
- Database size, connection counts, edition, HA requirements
- Web app framework, process count, and runtime version
- Container count and resource requirements
- Orchestrator node/pod counts for proper sizing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .models_workload import (
    ContainerRuntimeType,
    DatabaseEngine,
    DiscoveredContainerRuntime,
    DiscoveredDatabase,
    DiscoveredOrchestrator,
    DiscoveredWebApp,
    OrchestratorType,
    VMWorkloads,
    WebAppRuntime,
    WorkloadDiscoveryResult,
    WorkloadRecommendation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Azure PaaS service catalog (representative pricing, East US PAYG)
# ---------------------------------------------------------------------------

@dataclass
class AzureServiceOption:
    name: str
    display: str
    category: str             # database / webapp / container
    sku_tier: str             # e.g. General Purpose, Standard S1
    estimated_monthly_usd: float
    migration_approach: str   # rehost / replatform / refactor
    complexity: str           # low / medium / high


# ------ Databases ----------------------------------------------------------

DB_SERVICE_MAP: dict[DatabaseEngine, list[AzureServiceOption]] = {
    DatabaseEngine.MSSQL: [
        AzureServiceOption(
            "Azure SQL Database", "Azure SQL Database (Gen Purpose 4 vCores)",
            "database", "GP_Gen5_4", 380.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure SQL Managed Instance", "Azure SQL MI (GP 4 vCores)",
            "database", "GP_Gen5_4", 640.0, "replatform", "medium"),
        AzureServiceOption(
            "SQL Server on Azure VM", "SQL Server on Azure VM (D4s v5)",
            "database", "Standard_D4s_v5", 500.0, "rehost", "low"),
    ],
    DatabaseEngine.MYSQL: [
        AzureServiceOption(
            "Azure Database for MySQL", "Azure MySQL Flexible (GP 4 vCores)",
            "database", "GP_Standard_D4ds_v4", 280.0, "replatform", "medium"),
        AzureServiceOption(
            "MySQL on Azure VM", "MySQL on Azure VM",
            "database", "Standard_D4s_v5", 200.0, "rehost", "low"),
    ],
    DatabaseEngine.MARIADB: [
        AzureServiceOption(
            "Azure Database for MySQL", "Azure MySQL Flexible (MariaDB-compat)",
            "database", "GP_Standard_D4ds_v4", 280.0, "replatform", "medium"),
        AzureServiceOption(
            "MariaDB on Azure VM", "MariaDB on Azure VM",
            "database", "Standard_D4s_v5", 200.0, "rehost", "low"),
    ],
    DatabaseEngine.POSTGRESQL: [
        AzureServiceOption(
            "Azure Database for PostgreSQL", "Azure PostgreSQL Flexible (GP 4 vCores)",
            "database", "GP_Standard_D4ds_v4", 290.0, "replatform", "medium"),
        AzureServiceOption(
            "PostgreSQL on Azure VM", "PostgreSQL on Azure VM",
            "database", "Standard_D4s_v5", 200.0, "rehost", "low"),
    ],
    DatabaseEngine.ORACLE: [
        AzureServiceOption(
            "Oracle on Azure VM", "Oracle DB on Azure VM (E8s v5)",
            "database", "Standard_E8s_v5", 750.0, "rehost", "low"),
        AzureServiceOption(
            "Azure SQL Database", "Migrate Oracle → Azure SQL DB",
            "database", "GP_Gen5_8", 760.0, "refactor", "high"),
        AzureServiceOption(
            "Azure Database for PostgreSQL", "Migrate Oracle → PostgreSQL Flex",
            "database", "GP_Standard_D8ds_v4", 580.0, "refactor", "high"),
    ],
    DatabaseEngine.MONGODB: [
        AzureServiceOption(
            "Azure Cosmos DB (MongoDB API)", "Cosmos DB for MongoDB (400 RU/s)",
            "database", "400_RUs", 24.0, "replatform", "medium"),
        AzureServiceOption(
            "MongoDB on Azure VM", "MongoDB on Azure VM",
            "database", "Standard_D4s_v5", 200.0, "rehost", "low"),
    ],
    DatabaseEngine.REDIS: [
        AzureServiceOption(
            "Azure Cache for Redis", "Azure Cache for Redis (Standard C2)",
            "database", "Standard_C2", 162.0, "replatform", "low"),
        AzureServiceOption(
            "Redis on Azure VM", "Redis on Azure VM",
            "database", "Standard_D2s_v5", 90.0, "rehost", "low"),
    ],
}

# ------ Web Apps / App Runtimes -------------------------------------------

WEBAPP_SERVICE_MAP: dict[WebAppRuntime, list[AzureServiceOption]] = {
    WebAppRuntime.DOTNET_FRAMEWORK: [
        AzureServiceOption(
            "Azure App Service (Windows)", "App Service P1v3 (Windows)",
            "webapp", "P1v3", 138.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure VM (IIS)", "IIS on Azure VM (D4s v5)",
            "webapp", "Standard_D4s_v5", 200.0, "rehost", "low"),
    ],
    WebAppRuntime.DOTNET_CORE: [
        AzureServiceOption(
            "Azure App Service", "App Service P1v3 (Linux)",
            "webapp", "P1v3", 108.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Container Apps", "Container Apps (1 vCPU, 2 GiB)",
            "webapp", "Consumption", 45.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Kubernetes Service", "AKS (D4s v5 node pool)",
            "webapp", "Standard_D4s_v5", 200.0, "refactor", "high"),
    ],
    WebAppRuntime.JAVA: [
        AzureServiceOption(
            "Azure App Service", "App Service P1v3 (Java)",
            "webapp", "P1v3", 108.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Spring Apps", "Azure Spring Apps (Standard)",
            "webapp", "Standard", 120.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Container Apps", "Container Apps (Java)",
            "webapp", "Consumption", 50.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure VM", "Java on Azure VM",
            "webapp", "Standard_D4s_v5", 200.0, "rehost", "low"),
    ],
    WebAppRuntime.NODEJS: [
        AzureServiceOption(
            "Azure App Service", "App Service P1v3 (Node.js)",
            "webapp", "P1v3", 108.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Container Apps", "Container Apps (Node.js)",
            "webapp", "Consumption", 40.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Static Web Apps", "Static Web Apps (Standard)",
            "webapp", "Standard", 9.0, "replatform", "low"),
    ],
    WebAppRuntime.PYTHON: [
        AzureServiceOption(
            "Azure App Service", "App Service P1v3 (Python)",
            "webapp", "P1v3", 108.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Container Apps", "Container Apps (Python)",
            "webapp", "Consumption", 40.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Functions", "Functions (Consumption plan)",
            "webapp", "Consumption", 15.0, "refactor", "medium"),
    ],
    WebAppRuntime.PHP: [
        AzureServiceOption(
            "Azure App Service", "App Service P1v3 (PHP)",
            "webapp", "P1v3", 108.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure VM", "PHP on Azure VM",
            "webapp", "Standard_D2s_v5", 90.0, "rehost", "low"),
    ],
    WebAppRuntime.RUBY: [
        AzureServiceOption(
            "Azure App Service", "App Service P1v3 (Ruby)",
            "webapp", "P1v3", 108.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Container Apps", "Container Apps (Ruby)",
            "webapp", "Consumption", 40.0, "replatform", "medium"),
    ],
    WebAppRuntime.GO: [
        AzureServiceOption(
            "Azure Container Apps", "Container Apps (Go)",
            "webapp", "Consumption", 40.0, "replatform", "low"),
        AzureServiceOption(
            "Azure App Service", "App Service P1v3 (Go)",
            "webapp", "P1v3", 108.0, "replatform", "medium"),
    ],
}

# ------ Containers / Orchestrators -----------------------------------------

CONTAINER_SERVICE_MAP: dict[ContainerRuntimeType, list[AzureServiceOption]] = {
    ContainerRuntimeType.DOCKER: [
        AzureServiceOption(
            "Azure Container Apps", "Container Apps (per-container)",
            "container", "Consumption", 45.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Container Instances", "ACI (1 vCPU, 1.5 GiB)",
            "container", "Standard", 35.0, "rehost", "low"),
        AzureServiceOption(
            "Azure Kubernetes Service", "AKS (D4s v5 node pool)",
            "container", "Standard_D4s_v5", 200.0, "replatform", "medium"),
    ],
    ContainerRuntimeType.PODMAN: [
        AzureServiceOption(
            "Azure Container Apps", "Container Apps",
            "container", "Consumption", 45.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Kubernetes Service", "AKS",
            "container", "Standard_D4s_v5", 200.0, "replatform", "medium"),
    ],
    ContainerRuntimeType.CONTAINERD: [
        AzureServiceOption(
            "Azure Kubernetes Service", "AKS (containerd runtime)",
            "container", "Standard_D4s_v5", 200.0, "replatform", "low"),
    ],
}

ORCHESTRATOR_SERVICE_MAP: dict[OrchestratorType, list[AzureServiceOption]] = {
    OrchestratorType.KUBERNETES: [
        AzureServiceOption(
            "Azure Kubernetes Service", "AKS (managed Kubernetes)",
            "orchestrator", "Standard_D4s_v5", 200.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Red Hat OpenShift", "ARO (if OpenShift compat needed)",
            "orchestrator", "Standard_D8s_v5", 600.0, "replatform", "medium"),
    ],
    OrchestratorType.DOCKER_SWARM: [
        AzureServiceOption(
            "Azure Kubernetes Service", "Migrate Swarm → AKS",
            "orchestrator", "Standard_D4s_v5", 200.0, "replatform", "high"),
        AzureServiceOption(
            "Azure Container Apps", "Migrate Swarm → Container Apps",
            "orchestrator", "Consumption", 80.0, "replatform", "medium"),
    ],
    OrchestratorType.OPENSHIFT: [
        AzureServiceOption(
            "Azure Red Hat OpenShift", "ARO",
            "orchestrator", "Standard_D8s_v5", 600.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Kubernetes Service", "Migrate OpenShift → AKS",
            "orchestrator", "Standard_D4s_v5", 200.0, "replatform", "high"),
    ],
}

# ------ Networks -----------------------------------------------------------

NETWORK_SERVICE_MAP: dict[str, list[AzureServiceOption]] = {
    "standard": [
        AzureServiceOption(
            "Azure Virtual Network", "Azure VNet + NSG",
            "network", "Standard", 35.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Virtual WAN", "Azure Virtual WAN (Standard)",
            "network", "Standard", 125.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Firewall", "Azure Firewall (Standard)",
            "network", "Standard", 912.50, "replatform", "medium"),
    ],
    "distributed": [
        AzureServiceOption(
            "Azure Virtual Network", "Azure VNet + NSG (dvSwitch replacement)",
            "network", "Standard", 35.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Virtual WAN", "Azure Virtual WAN (dvSwitch replacement)",
            "network", "Standard", 125.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure Firewall", "Azure Firewall (Premium, micro-segmentation)",
            "network", "Premium", 1825.0, "replatform", "high"),
    ],
}

# ------ File Shares / Storage ---------------------------------------------

FILESHARE_SERVICE_MAP: dict[str, list[AzureServiceOption]] = {
    "vmfs": [
        AzureServiceOption(
            "Azure Files", "Azure Files Premium (SMB/NFS)",
            "fileshare", "Premium_LRS", 120.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Managed Disks", "Azure Managed Disk (Premium SSD)",
            "fileshare", "Premium_LRS", 73.0, "rehost", "low"),
        AzureServiceOption(
            "Azure NetApp Files", "Azure NetApp Files (Standard)",
            "fileshare", "Standard", 180.0, "replatform", "medium"),
    ],
    "nfs": [
        AzureServiceOption(
            "Azure NetApp Files", "Azure NetApp Files (Premium)",
            "fileshare", "Premium", 270.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Files", "Azure Files Premium (NFS v4.1)",
            "fileshare", "Premium_LRS", 120.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Blob (NFS v3)", "Azure Blob Storage (NFS v3 protocol)",
            "fileshare", "Premium_LRS", 95.0, "replatform", "medium"),
    ],
    "vsan": [
        AzureServiceOption(
            "Azure VMware Solution", "AVS (vSAN → AVS)",
            "fileshare", "AV36", 450.0, "rehost", "low"),
        AzureServiceOption(
            "Azure Managed Disks", "Azure Managed Disk (Ultra SSD)",
            "fileshare", "UltraSSD_LRS", 150.0, "replatform", "medium"),
        AzureServiceOption(
            "Azure NetApp Files", "Azure NetApp Files (Ultra)",
            "fileshare", "Ultra", 360.0, "replatform", "medium"),
    ],
    "smb": [
        AzureServiceOption(
            "Azure Files", "Azure Files Standard (SMB)",
            "fileshare", "Standard_LRS", 55.0, "replatform", "low"),
        AzureServiceOption(
            "Azure Files", "Azure Files Premium (SMB)",
            "fileshare", "Premium_LRS", 120.0, "replatform", "low"),
        AzureServiceOption(
            "Azure NetApp Files", "Azure NetApp Files (Standard SMB)",
            "fileshare", "Standard", 180.0, "replatform", "medium"),
    ],
}


# ---------------------------------------------------------------------------
# Migration steps templates
# ---------------------------------------------------------------------------

_MIGRATION_STEPS: dict[str, list[str]] = {
    "Azure SQL Database": [
        "Assess schema compatibility with Data Migration Assistant (DMA)",
        "Choose Azure SQL Database service tier (DTU vs vCore)",
        "Use Azure Database Migration Service (DMS) for online migration",
        "Update application connection strings",
        "Validate data integrity and run functional tests",
        "Switch DNS / connection endpoints to Azure SQL",
    ],
    "Azure SQL Managed Instance": [
        "Run Azure SQL MI readiness assessment",
        "Set up VNet and subnet for Managed Instance",
        "Use Azure DMS for near-zero-downtime migration",
        "Reconfigure linked servers, SQL Agent jobs",
        "Update connection strings and test",
    ],
    "SQL Server on Azure VM": [
        "Create Azure VM with SQL Server image",
        "Backup and restore databases to Azure VM",
        "Reconfigure SQL Agent jobs, logins, linked servers",
        "Update connection strings and firewall rules",
    ],
    "Azure Database for MySQL": [
        "Assess compatibility using Azure DMS pre-migration assessment",
        "Use Azure DMS or mysqldump for migration",
        "Update connection strings (SSL required by default)",
        "Configure server parameters and firewall rules",
        "Validate data and test application",
    ],
    "Azure Database for PostgreSQL": [
        "Use pg_dump/pg_restore or Azure DMS for migration",
        "Configure extensions and server parameters",
        "Update connection strings (SSL required)",
        "Test application functionality and performance",
    ],
    "Oracle on Azure VM": [
        "Create Azure VM with Oracle-compatible image",
        "Use Oracle Data Guard or RMAN for migration",
        "Configure Oracle licensing (BYOL or pay-as-you-go)",
        "Reconfigure TNS listeners and connection strings",
    ],
    "Azure Cosmos DB (MongoDB API)": [
        "Assess document size and indexing compatibility",
        "Use Azure DMS or mongodump/mongorestore",
        "Configure partition key and RU throughput",
        "Update connection strings to Cosmos DB endpoint",
    ],
    "Azure Cache for Redis": [
        "Export RDB snapshot from source Redis",
        "Import into Azure Cache for Redis",
        "Update connection strings and enable SSL",
    ],
    "Azure App Service": [
        "Create App Service plan and web app",
        "Configure deployment (Git, CI/CD, ZIP deploy)",
        "Set up application settings and connection strings",
        "Configure custom domain and SSL certificate",
        "Test and validate application",
    ],
    "Azure App Service (Windows)": [
        "Create App Service plan (Windows) and web app",
        "Migrate IIS configuration to App Service",
        "Use App Service Migration Assistant tool",
        "Reconfigure authentication and connection strings",
        "Test with deployment slots before cutover",
    ],
    "Azure Container Apps": [
        "Build container image and push to Azure Container Registry",
        "Create Container Apps environment",
        "Deploy container app with Dapr/scaling configuration",
        "Set up ingress, secrets, and managed identity",
    ],
    "Azure Kubernetes Service": [
        "Create AKS cluster with appropriate node pool sizes",
        "Push container images to Azure Container Registry",
        "Convert Docker Compose / manifests to Kubernetes manifests",
        "Deploy workloads and configure Ingress controller",
        "Set up monitoring with Container Insights",
    ],
    "Azure Spring Apps": [
        "Create Azure Spring Apps instance",
        "Deploy Spring Boot JAR/WAR directly",
        "Configure service registry and config server",
        "Set up managed identity for Azure services",
    ],
    "Azure Functions": [
        "Choose hosting plan (Consumption, Premium, Dedicated)",
        "Refactor application into function triggers/bindings",
        "Deploy using Azure Functions Core Tools or CI/CD",
        "Configure application settings and managed identity",
    ],
    "Azure Virtual Network": [
        "Design Azure VNet address space and subnet layout",
        "Create Network Security Groups (NSGs) for micro-segmentation",
        "Configure VPN Gateway or ExpressRoute for hybrid connectivity",
        "Migrate firewall rules to NSG rules / Azure Firewall policies",
        "Set up DNS resolution (Azure DNS / Private DNS Zones)",
    ],
    "Azure Virtual WAN": [
        "Create Virtual WAN hub in target region",
        "Connect VNets via Virtual WAN hub",
        "Configure branch-to-Azure connectivity (VPN/ExpressRoute)",
        "Set up routing policies and security rules",
    ],
    "Azure Firewall": [
        "Create Azure Firewall in hub VNet",
        "Migrate on-premises firewall rules to Azure Firewall policies",
        "Configure DNAT/SNAT rules for inbound/outbound traffic",
        "Enable threat intelligence and IDPS (Premium tier)",
        "Set up diagnostic logging and monitoring",
    ],
    "Azure Files": [
        "Create Azure Storage Account with appropriate tier",
        "Create file share with required quota and protocol (SMB/NFS)",
        "Use Azure File Sync or AzCopy/Robocopy for data migration",
        "Configure private endpoints for secure access",
        "Update application mount points / UNC paths",
    ],
    "Azure Managed Disks": [
        "Create managed disk with appropriate tier (Standard/Premium/Ultra)",
        "Use Azure Migrate or disk snapshot for migration",
        "Attach managed disk to target Azure VM",
        "Validate disk performance and IOPS requirements",
    ],
    "Azure NetApp Files": [
        "Create Azure NetApp Files account and capacity pool",
        "Create NFS/SMB volume with required performance tier",
        "Use XCP, rsync, or Robocopy for data migration",
        "Configure Active Directory integration for SMB volumes",
        "Update client mount points and test connectivity",
    ],
    "Azure VMware Solution": [
        "Deploy Azure VMware Solution private cloud",
        "Connect to Azure VNet via ExpressRoute",
        "Use HCX for workload migration from on-premises vSAN",
        "Configure storage policies in AVS",
    ],
    "Azure Blob (NFS v3)": [
        "Create storage account with hierarchical namespace",
        "Enable NFS v3 protocol support",
        "Migrate data using AzCopy or rsync",
        "Configure private endpoints and network rules",
    ],
}


# ---------------------------------------------------------------------------
# Smart matching helpers — consider DB size, HA, connections, features
# ---------------------------------------------------------------------------

def _score_db_service(db: DiscoveredDatabase, svc: AzureServiceOption) -> tuple[float, str, list[str]]:
    """Score and adjust a database service option based on workload characteristics.

    Returns (adjusted_cost, adjusted_tier_display, issues).
    """
    cost = svc.estimated_monthly_usd
    issues: list[str] = []
    tier_info = svc.sku_tier

    size_gb = db.total_size_gb or (db.size_mb / 1024 if db.size_mb else 0)
    connections = db.active_connections or db.max_connections or 0
    edition = (db.edition or "").lower()

    # ---- Size-based tier scaling ----
    if "SQL Database" in svc.name or "Azure SQL MI" in svc.name or "SQL Managed Instance" in svc.name:
        if size_gb > 500:
            cost *= 2.5         # Business Critical 8 vCores range
            tier_info = "BC_Gen5_8"
            issues.append(f"Large DB ({size_gb:.0f} GB) — Business Critical tier recommended")
        elif size_gb > 100:
            cost *= 1.5
            tier_info = "GP_Gen5_8"
        # Connection-based scaling
        if connections > 200:
            cost *= 1.3
            issues.append(f"High connection count ({connections}) — larger compute tier needed")

    elif "MySQL" in svc.name or "PostgreSQL" in svc.name:
        if "Azure VM" not in svc.name:
            if size_gb > 500:
                cost *= 2.2
                tier_info = "GP_Standard_D8ds_v4"
                issues.append(f"Large DB ({size_gb:.0f} GB) — 8 vCore tier recommended")
            elif size_gb > 100:
                cost *= 1.4
                tier_info = "GP_Standard_D4ds_v4"
            if connections > 150:
                cost *= 1.2

    elif "Cosmos DB" in svc.name:
        # Scale RUs by size
        if size_gb > 50:
            cost = max(cost, 200.0)    # at least 1000 RU/s
            tier_info = "1000_RUs"
        if size_gb > 200:
            cost = max(cost, 800.0)    # autoscale
            tier_info = "4000_RUs_Autoscale"

    elif "Azure Cache for Redis" in svc.name:
        if size_gb > 13:
            cost *= 3.0
            tier_info = "Premium_P2"
        elif size_gb > 6:
            cost *= 2.0
            tier_info = "Premium_P1"

    # ---- Edition / feature compatibility ----
    if db.engine == DatabaseEngine.MSSQL:
        if "enterprise" in edition:
            if "SQL Database" in svc.name:
                issues.append("Enterprise edition features (CLR, Service Broker) may not be available in SQL Database — consider SQL MI")
            # Prefer SQL MI for enterprise edition
            if "SQL MI" in svc.name or "Managed Instance" in svc.name:
                cost *= 0.95  # slight preference
        if "express" in edition and "SQL Database" in svc.name:
            cost *= 0.5  # Express is tiny — small tier suffices
            tier_info = "GP_Gen5_2"

    if db.engine == DatabaseEngine.ORACLE:
        if "enterprise" in edition:
            issues.append("Oracle Enterprise Edition requires BYOL on Azure VMs")
            cost *= 1.2  # license premium

    return round(cost, 2), tier_info, issues


def _score_webapp_service(wa: DiscoveredWebApp, svc: AzureServiceOption) -> tuple[float, str, list[str]]:
    """Score a webapp service option based on runtime details.

    Returns (adjusted_cost, note, issues).
    """
    cost = svc.estimated_monthly_usd
    issues: list[str] = []
    note = ""

    framework = (wa.framework or "").lower()
    version = wa.runtime_version or ""

    # Framework-specific considerations
    if wa.runtime == WebAppRuntime.DOTNET_FRAMEWORK:
        if "Container Apps" in svc.name or "AKS" in svc.name:
            issues.append(".NET Framework apps require Windows containers — limited support on Container Apps/AKS")
            cost *= 1.3  # penalty for Windows container overhead
        if version and version.startswith("2."):
            issues.append(f".NET Framework {version} is very old — consider modernizing to .NET 8+")

    if wa.runtime == WebAppRuntime.JAVA:
        if "spring" in framework:
            # Azure Spring Apps is a natural fit
            if "Spring Apps" in svc.name:
                cost *= 0.9  # preference for Spring Apps
                note = "Spring Boot detected — Azure Spring Apps recommended"
        if "tomcat" in framework or "jboss" in framework:
            if "App Service" in svc.name:
                note = f"{framework.title()} detected — App Service with built-in server support"

    if wa.runtime == WebAppRuntime.NODEJS:
        if "static" in framework or "next" in framework or "react" in framework or "vue" in framework or "angular" in framework:
            if "Static Web Apps" in svc.name:
                cost *= 0.5  # SWA is ideal for static/SPA frameworks
                note = f"{framework.title()} SPA detected — Static Web Apps ideal"

    return round(cost, 2), note, issues


# ---------------------------------------------------------------------------
# Recommendation generator
# ---------------------------------------------------------------------------

def generate_workload_recommendations(
    discovery: WorkloadDiscoveryResult,
) -> list[WorkloadRecommendation]:
    """Generate Azure service recommendations for every discovered workload.

    Uses smart matching that considers:
    - Database: size, connections, edition, engine features
    - Web apps: framework, runtime version compatibility
    - Containers: running container count for cost scaling
    - Orchestrators: node/pod count for proper sizing
    """
    recs: list[WorkloadRecommendation] = []

    for vmw in discovery.vm_workloads:
        # Databases — smart matching by size, connections, edition
        for db in vmw.databases:
            options = DB_SERVICE_MAP.get(db.engine, [])
            if not options:
                continue

            # Score each option considering workload characteristics
            scored: list[tuple[float, AzureServiceOption, str, list[str]]] = []
            for opt in options:
                adj_cost, tier_info, opt_issues = _score_db_service(db, opt)
                scored.append((adj_cost, opt, tier_info, opt_issues))

            # Pick the best option: lowest complexity replatform first,
            # but prefer managed PaaS over IaaS when cost is similar
            best_cost, primary, best_tier, primary_issues = scored[0]
            alternatives = [o.name for o in options[1:]]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

            issues: list[str] = list(primary_issues)
            confidence = 70.0
            if db.version == "unknown":
                issues.append("Version not detected — verify compatibility manually")
                confidence -= 15
            if db.engine == DatabaseEngine.ORACLE:
                issues.append("Oracle licensing requires special consideration on Azure")
                confidence -= 10

            # Boost confidence when we have detailed discovery data
            size_gb = db.total_size_gb or (db.size_mb / 1024 if db.size_mb else 0)
            if size_gb > 0:
                confidence += 5   # size data available
            if db.active_connections > 0:
                confidence += 5   # connection data available
            if db.edition:
                confidence += 3   # edition detected
            if db.discovery_method == "direct_connect":
                confidence += 7   # deep probe has richer data

            confidence = min(confidence, 100.0)

            display = primary.display
            if best_tier != primary.sku_tier:
                # Tier was adjusted by smart matching — reflect in display
                display = f"{primary.name} ({best_tier})"

            recs.append(WorkloadRecommendation(
                vm_name=vmw.vm_name,
                workload_name=f"{db.engine.value}:{db.instance_name}",
                workload_type="database",
                source_engine=db.engine.value,
                source_version=db.version,
                recommended_azure_service=display,
                alternative_services=alternatives,
                estimated_monthly_cost_usd=best_cost,
                migration_approach=primary.migration_approach,
                migration_complexity=primary.complexity,
                migration_steps=steps,
                issues=issues,
                confidence=confidence,
            ))

        # Web apps — framework-aware matching
        for wa in vmw.web_apps:
            options = WEBAPP_SERVICE_MAP.get(wa.runtime, [])
            if not options:
                # Fallback for unknown runtimes
                options = [AzureServiceOption(
                    "Azure VM", "Rehost on Azure VM",
                    "webapp", "Standard_D2s_v5", 90.0, "rehost", "low")]

            # Score each option
            scored_wa: list[tuple[float, AzureServiceOption, str, list[str]]] = []
            for opt in options:
                adj_cost, note, opt_issues = _score_webapp_service(wa, opt)
                scored_wa.append((adj_cost, opt, note, opt_issues))

            best_cost, primary, best_note, primary_issues = scored_wa[0]
            alternatives = [o.name for o in options[1:]]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

            issues = list(primary_issues)
            confidence = 65.0
            if wa.runtime == WebAppRuntime.DOTNET_FRAMEWORK:
                issues.append(".NET Framework apps may need Windows App Service plan")
                confidence -= 5
            if wa.framework:
                confidence += 5  # framework detected
            if wa.runtime_version:
                confidence += 3  # version detected

            confidence = min(confidence, 100.0)

            recs.append(WorkloadRecommendation(
                vm_name=vmw.vm_name,
                workload_name=f"{wa.runtime.value}:{wa.framework}",
                workload_type="webapp",
                source_engine=wa.runtime.value,
                source_version=wa.runtime_version,
                recommended_azure_service=primary.display,
                alternative_services=alternatives,
                estimated_monthly_cost_usd=best_cost,
                migration_approach=primary.migration_approach,
                migration_complexity=primary.complexity,
                migration_steps=steps,
                issues=issues,
                confidence=confidence,
            ))

        # Container runtimes — scale by count
        for cr in vmw.container_runtimes:
            options = CONTAINER_SERVICE_MAP.get(cr.runtime, [])
            if not options:
                continue
            count = max(cr.running_containers, 1)
            primary = options[0]

            # If many containers, prefer AKS over individual Container Apps
            if count > 10 and len(options) > 1:
                aks_opts = [o for o in options if "Kubernetes" in o.name]
                if aks_opts:
                    primary = aks_opts[0]

            adjusted_cost = primary.estimated_monthly_usd * count
            alternatives = [o.name for o in options if o.name != primary.name]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

            issues = []
            confidence = 60.0
            if count > 20:
                issues.append(f"High container count ({count}) — dedicated AKS node pool recommended")
                confidence += 5  # we know more about capacity needs

            recs.append(WorkloadRecommendation(
                vm_name=vmw.vm_name,
                workload_name=f"{cr.runtime.value} ({cr.running_containers} containers)",
                workload_type="container",
                source_engine=cr.runtime.value,
                source_version=cr.version,
                recommended_azure_service=primary.display,
                alternative_services=alternatives,
                estimated_monthly_cost_usd=round(adjusted_cost, 2),
                migration_approach=primary.migration_approach,
                migration_complexity=primary.complexity,
                migration_steps=steps,
                issues=issues,
                confidence=confidence,
            ))

        # Orchestrators — scale by node count, consider pod density
        for orch in vmw.orchestrators:
            options = ORCHESTRATOR_SERVICE_MAP.get(orch.type, [])
            if not options:
                continue
            primary = options[0]
            node_mult = max(orch.node_count, 1)
            adjusted_cost = primary.estimated_monthly_usd * node_mult
            alternatives = [o.name for o in options[1:]]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

            issues = []
            confidence = 55.0

            # Pod density hints
            if orch.pod_count > 0 and orch.node_count > 0:
                pods_per_node = orch.pod_count / orch.node_count
                if pods_per_node > 50:
                    issues.append(f"High pod density ({pods_per_node:.0f} pods/node) — consider larger node SKU on AKS")
                confidence += 5

            if orch.node_count > 10:
                issues.append(f"Large cluster ({orch.node_count} nodes) — consider AKS autoscaler and spot node pools")
                confidence += 5

            recs.append(WorkloadRecommendation(
                vm_name=vmw.vm_name,
                workload_name=f"{orch.type.value} ({orch.role})",
                workload_type="orchestrator",
                source_engine=orch.type.value,
                source_version=orch.version,
                recommended_azure_service=primary.display,
                alternative_services=alternatives,
                estimated_monthly_cost_usd=round(adjusted_cost, 2),
                migration_approach=primary.migration_approach,
                migration_complexity=primary.complexity,
                migration_steps=steps,
                issues=issues,
                confidence=confidence,
            ))

    logger.info("Generated %d workload recommendations", len(recs))
    return recs
