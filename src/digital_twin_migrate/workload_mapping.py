"""Azure service mapping for discovered workloads.

Maps on-premises databases, web apps, container runtimes, and orchestrators
to the most appropriate Azure PaaS / IaaS services with cost estimates,
migration approach, and step-by-step guidance.
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
# Recommendation generator
# ---------------------------------------------------------------------------

def generate_workload_recommendations(
    discovery: WorkloadDiscoveryResult,
) -> list[WorkloadRecommendation]:
    """Generate Azure service recommendations for every discovered workload."""
    recs: list[WorkloadRecommendation] = []

    for vmw in discovery.vm_workloads:
        # Databases
        for db in vmw.databases:
            options = DB_SERVICE_MAP.get(db.engine, [])
            if not options:
                continue
            primary = options[0]
            alternatives = [o.name for o in options[1:]]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

            issues: list[str] = []
            confidence = 70.0
            if db.version == "unknown":
                issues.append("Version not detected — verify compatibility manually")
                confidence -= 15
            if db.engine == DatabaseEngine.ORACLE:
                issues.append("Oracle licensing requires special consideration on Azure")
                confidence -= 10

            recs.append(WorkloadRecommendation(
                vm_name=vmw.vm_name,
                workload_name=f"{db.engine.value}:{db.instance_name}",
                workload_type="database",
                source_engine=db.engine.value,
                source_version=db.version,
                recommended_azure_service=primary.display,
                alternative_services=alternatives,
                estimated_monthly_cost_usd=primary.estimated_monthly_usd,
                migration_approach=primary.migration_approach,
                migration_complexity=primary.complexity,
                migration_steps=steps,
                issues=issues,
                confidence=confidence,
            ))

        # Web apps
        for wa in vmw.web_apps:
            options = WEBAPP_SERVICE_MAP.get(wa.runtime, [])
            if not options:
                # Fallback for unknown runtimes
                options = [AzureServiceOption(
                    "Azure VM", "Rehost on Azure VM",
                    "webapp", "Standard_D2s_v5", 90.0, "rehost", "low")]
            primary = options[0]
            alternatives = [o.name for o in options[1:]]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

            issues = []
            confidence = 65.0
            if wa.runtime == WebAppRuntime.DOTNET_FRAMEWORK:
                issues.append(".NET Framework apps may need Windows App Service plan")
                confidence -= 5

            recs.append(WorkloadRecommendation(
                vm_name=vmw.vm_name,
                workload_name=f"{wa.runtime.value}:{wa.framework}",
                workload_type="webapp",
                source_engine=wa.runtime.value,
                source_version=wa.runtime_version,
                recommended_azure_service=primary.display,
                alternative_services=alternatives,
                estimated_monthly_cost_usd=primary.estimated_monthly_usd,
                migration_approach=primary.migration_approach,
                migration_complexity=primary.complexity,
                migration_steps=steps,
                issues=issues,
                confidence=confidence,
            ))

        # Container runtimes
        for cr in vmw.container_runtimes:
            options = CONTAINER_SERVICE_MAP.get(cr.runtime, [])
            if not options:
                continue
            # Scale cost by number of running containers
            count = max(cr.running_containers, 1)
            primary = options[0]
            adjusted_cost = primary.estimated_monthly_usd * count
            alternatives = [o.name for o in options[1:]]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

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
                confidence=60.0,
            ))

        # Orchestrators
        for orch in vmw.orchestrators:
            options = ORCHESTRATOR_SERVICE_MAP.get(orch.type, [])
            if not options:
                continue
            primary = options[0]
            # Scale cost by node count
            node_mult = max(orch.node_count, 1)
            adjusted_cost = primary.estimated_monthly_usd * node_mult
            alternatives = [o.name for o in options[1:]]
            steps = _MIGRATION_STEPS.get(primary.name, ["Consult Azure migration documentation"])

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
                confidence=55.0,
            ))

    logger.info("Generated %d workload recommendations", len(recs))
    return recs
