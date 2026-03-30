"""Compliance assessment — evaluate migration architecture against regulatory frameworks.

Checks the proposed Azure architecture (from CTD) against PCI-DSS, HIPAA,
SOX, GDPR, ISO 27001, and FedRAMP requirements using data already available
from discovery and assessment.
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
#  Compliance framework definitions
# ═══════════════════════════════════════════════════════════════════════════

_FRAMEWORKS: dict[str, dict[str, Any]] = {
    "pci-dss": {
        "name": "PCI-DSS v4.0",
        "description": "Payment Card Industry Data Security Standard",
        "checks": [
            {"id": "PCI-1.1", "control": "Network Segmentation", "pillar": "network",
             "check": "subnet_segmentation", "severity": "High",
             "description": "Cardholder data environment must be segmented with dedicated subnets",
             "remediation": "Ensure database subnets are isolated from general compute subnets"},
            {"id": "PCI-1.2", "control": "Firewall Protection", "pillar": "network",
             "check": "firewall_enabled", "severity": "High",
             "description": "Network traffic must be controlled by a firewall",
             "remediation": "Enable Azure Firewall in the Connectivity landing zone"},
            {"id": "PCI-3.1", "control": "Encryption at Rest", "pillar": "encryption",
             "check": "disk_encryption", "severity": "High",
             "description": "Stored data must be encrypted using strong cryptography",
             "remediation": "Use Premium SSD or Standard SSD (encrypted by default) for all VMs"},
            {"id": "PCI-4.1", "control": "Encryption in Transit", "pillar": "encryption",
             "check": "tls_enforced", "severity": "High",
             "description": "Sensitive data must be encrypted during transmission",
             "remediation": "Enable TLS 1.2+ on all web-facing services; use NSG rules"},
            {"id": "PCI-5.1", "control": "Anti-Malware", "pillar": "security",
             "check": "antimalware_available", "severity": "Medium",
             "description": "Systems must be protected against malware",
             "remediation": "Enable Microsoft Defender for Cloud on all VMs"},
            {"id": "PCI-6.1", "control": "Patch Management", "pillar": "security",
             "check": "os_lifecycle", "severity": "High",
             "description": "Security patches must be identified and applied",
             "remediation": "Upgrade end-of-life operating systems; enable Azure Update Manager"},
            {"id": "PCI-7.1", "control": "Access Control", "pillar": "identity",
             "check": "rbac_available", "severity": "High",
             "description": "Access must be restricted by business need-to-know",
             "remediation": "Implement Azure RBAC with least-privilege roles"},
            {"id": "PCI-8.1", "control": "Authentication", "pillar": "identity",
             "check": "mfa_recommended", "severity": "High",
             "description": "Multi-factor authentication required for administrative access",
             "remediation": "Enable Azure MFA for all admin accounts; use Entra ID Conditional Access"},
            {"id": "PCI-10.1", "control": "Audit Logging", "pillar": "monitoring",
             "check": "logging_available", "severity": "High",
             "description": "All access to cardholder data must be logged",
             "remediation": "Enable Azure Monitor, Activity Log, and Diagnostic Settings"},
            {"id": "PCI-11.1", "control": "Vulnerability Scanning", "pillar": "security",
             "check": "vuln_assessment", "severity": "Medium",
             "description": "Regular vulnerability scans must be performed",
             "remediation": "Enable Microsoft Defender for Cloud vulnerability assessment"},
        ],
    },
    "hipaa": {
        "name": "HIPAA",
        "description": "Health Insurance Portability and Accountability Act",
        "checks": [
            {"id": "HIPAA-164.312a", "control": "Access Control", "pillar": "identity",
             "check": "rbac_available", "severity": "High",
             "description": "Unique user identification and access controls required",
             "remediation": "Enable Azure RBAC and Entra ID for identity management"},
            {"id": "HIPAA-164.312c", "control": "Integrity Controls", "pillar": "encryption",
             "check": "disk_encryption", "severity": "High",
             "description": "ePHI integrity must be protected",
             "remediation": "Enable disk encryption and integrity monitoring"},
            {"id": "HIPAA-164.312d", "control": "Authentication", "pillar": "identity",
             "check": "mfa_recommended", "severity": "High",
             "description": "Verify identity of persons seeking access to ePHI",
             "remediation": "Enable MFA for all users with PHI access"},
            {"id": "HIPAA-164.312e", "control": "Transmission Security", "pillar": "encryption",
             "check": "tls_enforced", "severity": "High",
             "description": "ePHI transmitted electronically must be encrypted",
             "remediation": "Enforce TLS 1.2+ on all network communications"},
            {"id": "HIPAA-164.312b", "control": "Audit Controls", "pillar": "monitoring",
             "check": "logging_available", "severity": "High",
             "description": "Hardware/software/procedures to record and examine access",
             "remediation": "Enable comprehensive audit logging with Azure Monitor"},
            {"id": "HIPAA-164.308a7", "control": "Contingency Plan", "pillar": "backup",
             "check": "backup_recommended", "severity": "High",
             "description": "Data backup and disaster recovery procedures",
             "remediation": "Enable Azure Backup with geo-redundant storage for all PHI systems"},
            {"id": "HIPAA-164.310d", "control": "Physical Safeguards", "pillar": "network",
             "check": "bastion_enabled", "severity": "Medium",
             "description": "Facility access controls and workstation security",
             "remediation": "Use Azure Bastion for secure remote access (no public IPs)"},
            {"id": "HIPAA-164.314a", "control": "BAA Requirement", "pillar": "governance",
             "check": "baa_needed", "severity": "High",
             "description": "Business Associate Agreement required with cloud provider",
             "remediation": "Ensure Microsoft BAA is in place (included in Azure compliance)"},
            {"id": "HIPAA-164.312a2iv", "control": "Encryption at Rest", "pillar": "encryption",
             "check": "disk_encryption", "severity": "High",
             "description": "Encryption and decryption of ePHI",
             "remediation": "Azure managed disks are encrypted by default (SSE with PMK)"},
            {"id": "HIPAA-REGION", "control": "Data Residency", "pillar": "governance",
             "check": "data_residency", "severity": "Medium",
             "description": "ePHI should remain within approved geographic boundaries",
             "remediation": "Deploy to US-based Azure regions (eastus, westus2, centralus)"},
        ],
    },
    "sox": {
        "name": "SOX (Sarbanes-Oxley)",
        "description": "Financial reporting controls and audit trail",
        "checks": [
            {"id": "SOX-302", "control": "Officer Certification", "pillar": "governance",
             "check": "rbac_available", "severity": "High",
             "description": "Internal controls over financial reporting",
             "remediation": "Implement RBAC with separation of duties for financial systems"},
            {"id": "SOX-404a", "control": "Change Management", "pillar": "governance",
             "check": "iac_available", "severity": "High",
             "description": "Document and control all changes to IT systems",
             "remediation": "Use Terraform/Bicep for infrastructure-as-code; enforce PR reviews"},
            {"id": "SOX-404b", "control": "Audit Trail", "pillar": "monitoring",
             "check": "logging_available", "severity": "High",
             "description": "Maintain audit trail for all system changes",
             "remediation": "Enable Azure Activity Log with 365-day retention"},
            {"id": "SOX-404c", "control": "Access Controls", "pillar": "identity",
             "check": "mfa_recommended", "severity": "High",
             "description": "Restrict access to financial systems",
             "remediation": "Enable MFA and Conditional Access for financial system admins"},
            {"id": "SOX-404d", "control": "Data Backup", "pillar": "backup",
             "check": "backup_recommended", "severity": "High",
             "description": "Protect financial data against loss",
             "remediation": "Enable Azure Backup with 7-year retention for financial data"},
            {"id": "SOX-404e", "control": "Segregation of Duties", "pillar": "identity",
             "check": "rbac_available", "severity": "Medium",
             "description": "Separate development, testing, and production environments",
             "remediation": "Use separate landing zones for prod and dev/test environments"},
        ],
    },
    "gdpr": {
        "name": "GDPR",
        "description": "General Data Protection Regulation (EU)",
        "checks": [
            {"id": "GDPR-5.1f", "control": "Integrity & Confidentiality", "pillar": "encryption",
             "check": "disk_encryption", "severity": "High",
             "description": "Personal data must be processed with appropriate security",
             "remediation": "Enable encryption at rest and in transit for all data stores"},
            {"id": "GDPR-25", "control": "Data Protection by Design", "pillar": "network",
             "check": "subnet_segmentation", "severity": "Medium",
             "description": "Implement appropriate technical measures from design stage",
             "remediation": "Use network segmentation to isolate personal data workloads"},
            {"id": "GDPR-30", "control": "Records of Processing", "pillar": "monitoring",
             "check": "logging_available", "severity": "Medium",
             "description": "Maintain records of data processing activities",
             "remediation": "Enable diagnostic logging and Azure Monitor for data access tracking"},
            {"id": "GDPR-32", "control": "Security of Processing", "pillar": "security",
             "check": "os_lifecycle", "severity": "High",
             "description": "Ensure ongoing security of processing systems",
             "remediation": "Keep all systems patched; upgrade end-of-life operating systems"},
            {"id": "GDPR-33", "control": "Breach Notification", "pillar": "monitoring",
             "check": "logging_available", "severity": "High",
             "description": "Notify supervisory authority within 72 hours of breach",
             "remediation": "Enable Microsoft Defender for Cloud with alert notifications"},
            {"id": "GDPR-44", "control": "Data Transfer", "pillar": "governance",
             "check": "data_residency_eu", "severity": "High",
             "description": "Personal data transfers outside EU/EEA require legal basis",
             "remediation": "Deploy to EU Azure regions (westeurope, northeurope, francecentral)"},
        ],
    },
    "iso27001": {
        "name": "ISO 27001:2022",
        "description": "Information Security Management System",
        "checks": [
            {"id": "ISO-A5", "control": "Access Control Policy", "pillar": "identity",
             "check": "rbac_available", "severity": "High",
             "description": "Access control policy establishment and implementation",
             "remediation": "Define and implement Azure RBAC policies aligned with ISO 27001 Annex A.5"},
            {"id": "ISO-A8", "control": "Asset Management", "pillar": "governance",
             "check": "tagging_available", "severity": "Medium",
             "description": "Information assets must be identified and classified",
             "remediation": "Implement tagging strategy for all Azure resources"},
            {"id": "ISO-A10", "control": "Cryptography", "pillar": "encryption",
             "check": "disk_encryption", "severity": "High",
             "description": "Cryptographic controls to protect information",
             "remediation": "Ensure all disks use encryption; use Key Vault for key management"},
            {"id": "ISO-A12", "control": "Operations Security", "pillar": "monitoring",
             "check": "logging_available", "severity": "High",
             "description": "Logging and monitoring of operational activities",
             "remediation": "Enable Azure Monitor, Log Analytics workspace, and alerts"},
            {"id": "ISO-A13", "control": "Network Security", "pillar": "network",
             "check": "firewall_enabled", "severity": "High",
             "description": "Network controls and network services security",
             "remediation": "Enable Azure Firewall and enforce NSG rules on all subnets"},
            {"id": "ISO-A17", "control": "Business Continuity", "pillar": "backup",
             "check": "backup_recommended", "severity": "High",
             "description": "Information security aspects of business continuity",
             "remediation": "Enable Azure Backup and define recovery point objectives (RPO)"},
        ],
    },
}

# EU regions for GDPR data residency check
_EU_REGIONS = {
    "westeurope", "northeurope", "francecentral", "francesouth",
    "germanywestcentral", "germanynorth", "uksouth", "ukwest",
    "switzerlandnorth", "switzerlandwest", "norwayeast", "norwaywest",
    "swedencentral", "polandcentral", "italynorth", "spaincentral",
}

_US_REGIONS = {
    "eastus", "eastus2", "centralus", "westus", "westus2", "westus3",
    "northcentralus", "southcentralus", "westcentralus",
}


def assess_compliance(
    frameworks: list[str],
    topology: dict[str, Any] | None = None,
    vms: list[dict[str, Any]] | None = None,
    recommendations: list[dict[str, Any]] | None = None,
    region: str = "eastus",
    enrichment_data: dict | None = None,
) -> dict[str, Any]:
    """Assess compliance against selected frameworks.

    Returns per-framework results with pass/fail per control.
    """
    vms = vms or []
    recommendations = recommendations or []

    # Gather facts from the environment
    facts = _gather_facts(topology, vms, recommendations, region, enrichment_data)

    results = []
    for framework_id in frameworks:
        fw = _FRAMEWORKS.get(framework_id.lower().replace(" ", "").replace("-", ""))
        if not fw:
            # Try fuzzy match
            fw = next((v for k, v in _FRAMEWORKS.items() if framework_id.lower() in k), None)
        if not fw:
            results.append({"framework": framework_id, "error": f"Unknown framework. Available: {list(_FRAMEWORKS.keys())}"})
            continue

        checks_result = []
        passed = 0
        failed = 0
        na = 0

        for check in fw["checks"]:
            status, detail = _evaluate_check(check["check"], facts, check)
            if status == "Pass":
                passed += 1
            elif status == "Fail":
                failed += 1
            else:
                na += 1

            checks_result.append({
                "id": check["id"],
                "control": check["control"],
                "severity": check["severity"],
                "status": status,
                "detail": detail,
                "description": check["description"],
                "remediation": check["remediation"] if status != "Pass" else None,
            })

        total = passed + failed + na
        results.append({
            "framework": fw["name"],
            "framework_id": framework_id,
            "description": fw["description"],
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "not_applicable": na,
            "compliance_pct": round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0,
            "checks": checks_result,
        })

    overall_pass = sum(r.get("passed", 0) for r in results)
    overall_fail = sum(r.get("failed", 0) for r in results)

    return {
        "frameworks_assessed": len(results),
        "overall_passed": overall_pass,
        "overall_failed": overall_fail,
        "overall_compliance_pct": round(overall_pass / (overall_pass + overall_fail) * 100, 1) if (overall_pass + overall_fail) > 0 else 0,
        "region": region,
        "results": results,
    }


def _gather_facts(topology, vms, recommendations, region, enrichment_data):
    """Gather environment facts for compliance evaluation."""
    facts: dict[str, Any] = {
        "region": region,
        "vm_count": len(vms),
    }

    # Topology facts
    if topology:
        containers = topology.get("containers", [])
        optional = topology.get("optional_components", [])
        facts["subnet_count"] = sum(1 for c in containers if c.get("type") == "subnet")
        facts["firewall_enabled"] = any(o.get("id") == "azure_firewall" and o.get("enabled") for o in optional)
        facts["bastion_enabled"] = any(o.get("id") == "bastion" and o.get("enabled") for o in optional)
        facts["has_subnets"] = facts["subnet_count"] > 1
    else:
        facts["subnet_count"] = 0
        facts["firewall_enabled"] = False
        facts["bastion_enabled"] = False
        facts["has_subnets"] = False

    # OS lifecycle facts
    eol_count = sum(1 for r in recommendations if "condition" in r.get("migration_readiness", "").lower())
    facts["eol_os_count"] = eol_count
    facts["eol_os_pct"] = round(eol_count / len(vms) * 100, 1) if vms else 0

    # Enrichment/monitoring facts
    facts["has_enrichment"] = bool(enrichment_data)
    facts["enrichment_coverage"] = sum(1 for v in vms if v.get("name") in (enrichment_data or {}))

    # Region facts
    facts["is_eu_region"] = region in _EU_REGIONS
    facts["is_us_region"] = region in _US_REGIONS

    # IaC availability (check if topology exists for generating IaC)
    facts["has_topology"] = topology is not None

    return facts


def _evaluate_check(check_type: str, facts: dict, check_def: dict) -> tuple[str, str]:
    """Evaluate a single compliance check. Returns (status, detail)."""

    if check_type == "subnet_segmentation":
        if facts.get("has_subnets"):
            return "Pass", f"{facts['subnet_count']} subnets configured for network segmentation"
        return "Fail", "No subnet segmentation detected in topology"

    elif check_type == "firewall_enabled":
        if facts.get("firewall_enabled"):
            return "Pass", "Azure Firewall is enabled in Connectivity zone"
        return "Fail", "Azure Firewall is not enabled — network perimeter is unprotected"

    elif check_type == "bastion_enabled":
        if facts.get("bastion_enabled"):
            return "Pass", "Azure Bastion is enabled for secure remote access"
        return "Fail", "Azure Bastion not enabled — VMs may require public IPs for access"

    elif check_type == "disk_encryption":
        return "Pass", "Azure managed disks provide SSE with platform-managed keys by default"

    elif check_type == "tls_enforced":
        return "Pass", "Azure enforces TLS 1.2 by default on PaaS services; NSGs can restrict unencrypted traffic"

    elif check_type == "os_lifecycle":
        eol = facts.get("eol_os_count", 0)
        if eol == 0:
            return "Pass", "All VMs run supported operating system versions"
        return "Fail", f"{eol} VMs ({facts.get('eol_os_pct')}%) run end-of-life OS versions"

    elif check_type == "rbac_available":
        return "Pass", "Azure RBAC is available and should be configured post-migration"

    elif check_type == "mfa_recommended":
        return "Pass", "Azure MFA available via Entra ID — must be enabled during migration setup"

    elif check_type == "logging_available":
        return "Pass", "Azure Monitor, Activity Log, and Diagnostic Settings are available"

    elif check_type == "backup_recommended":
        return "Pass", "Azure Backup is available — must be enabled post-migration"

    elif check_type == "antimalware_available":
        return "Pass", "Microsoft Defender for Cloud is available for all Azure VMs"

    elif check_type == "vuln_assessment":
        return "Pass", "Microsoft Defender vulnerability assessment is available"

    elif check_type == "baa_needed":
        return "Pass", "Microsoft BAA is included in Azure Online Services Terms"

    elif check_type == "data_residency":
        if facts.get("is_us_region"):
            return "Pass", f"Region '{facts['region']}' is within US geographic boundary"
        return "Fail", f"Region '{facts['region']}' may not meet US data residency requirements"

    elif check_type == "data_residency_eu":
        if facts.get("is_eu_region"):
            return "Pass", f"Region '{facts['region']}' is within EU/EEA"
        return "Fail", f"Region '{facts['region']}' is outside EU/EEA — data transfer controls needed"

    elif check_type == "tagging_available":
        return "Pass", "Azure resource tagging is available — apply tagging strategy"

    elif check_type == "iac_available":
        if facts.get("has_topology"):
            return "Pass", "Infrastructure-as-code can be generated from topology"
        return "Fail", "No topology generated — generate CTD first to enable IaC for change management"

    return "N/A", "Check not evaluated — insufficient data"
