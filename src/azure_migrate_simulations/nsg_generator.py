"""NSG rule generator — auto-generate Azure Network Security Group rules from dependencies.

Uses discovered TCP connections to create least-privilege NSG allow rules,
plus standard Azure service rules and a default deny.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


# Common Azure service tag rules
_AZURE_SERVICE_RULES = [
    {
        "name": "AllowAzureLoadBalancerHealthProbe",
        "priority": 100,
        "direction": "Inbound",
        "access": "Allow",
        "protocol": "*",
        "source": "AzureLoadBalancer",
        "source_port": "*",
        "destination": "*",
        "destination_port": "*",
        "description": "Allow Azure Load Balancer health probes",
    },
    {
        "name": "AllowVNetInbound",
        "priority": 200,
        "direction": "Inbound",
        "access": "Allow",
        "protocol": "*",
        "source": "VirtualNetwork",
        "source_port": "*",
        "destination": "VirtualNetwork",
        "destination_port": "*",
        "description": "Allow intra-VNet traffic",
    },
]

_OUTBOUND_SERVICE_RULES = [
    {
        "name": "AllowMonitorOutbound",
        "priority": 100,
        "direction": "Outbound",
        "access": "Allow",
        "protocol": "Tcp",
        "source": "*",
        "source_port": "*",
        "destination": "AzureMonitor",
        "destination_port": "443",
        "description": "Allow outbound to Azure Monitor",
    },
    {
        "name": "AllowStorageOutbound",
        "priority": 110,
        "direction": "Outbound",
        "access": "Allow",
        "protocol": "Tcp",
        "source": "*",
        "source_port": "*",
        "destination": "Storage",
        "destination_port": "443",
        "description": "Allow outbound to Azure Storage",
    },
    {
        "name": "AllowKeyVaultOutbound",
        "priority": 120,
        "direction": "Outbound",
        "access": "Allow",
        "protocol": "Tcp",
        "source": "*",
        "source_port": "*",
        "destination": "AzureKeyVault",
        "destination_port": "443",
        "description": "Allow outbound to Key Vault",
    },
]


def generate_nsg_rules(
    topology: dict[str, Any],
    workload_data: dict[str, Any] | None = None,
    include_bastion: bool = False,
    include_service_rules: bool = True,
) -> dict[str, Any]:
    """Generate NSG rules from the cloud topology and dependencies.

    Returns per-subnet NSG rule sets.
    """
    containers = topology.get("containers", [])
    nodes = topology.get("nodes", [])

    subnets = [c for c in containers if c.get("type") == "subnet"]

    # Map VM → subnet
    vm_subnet: dict[str, str] = {}
    for node in nodes:
        if node.get("resource_type") in ("vm", "paas"):
            vm_subnet[node.get("source_vm", "")] = node.get("container", "")

    # Extract dependencies
    deps = []
    if workload_data:
        deps = workload_data.get("result", {}).get("dependencies", [])

    # Build per-subnet rules
    subnet_rules: dict[str, list[dict]] = defaultdict(list)
    seen_rules: dict[str, set[str]] = defaultdict(set)  # dedup key per subnet
    priority_counter: dict[str, int] = defaultdict(lambda: 300)

    for dep in deps:
        src_vm = dep.get("source_vm", "")
        tgt_vm = dep.get("target_vm", "")
        port = dep.get("port", "*")
        protocol = dep.get("protocol", "tcp").capitalize()
        if protocol not in ("Tcp", "Udp"):
            protocol = "Tcp"

        src_sn = vm_subnet.get(src_vm, "")
        tgt_sn = vm_subnet.get(tgt_vm, "")

        if not tgt_sn:
            continue

        # Dedup: one rule per (source_subnet, port) combination per dest subnet
        rule_key = f"{src_sn}:{port}:{protocol}"
        if rule_key in seen_rules[tgt_sn]:
            continue
        seen_rules[tgt_sn].add(rule_key)

        priority = priority_counter[tgt_sn]
        priority_counter[tgt_sn] += 10

        src_label = _subnet_label(src_sn, containers)
        tgt_label = _subnet_label(tgt_sn, containers)

        subnet_rules[tgt_sn].append({
            "name": f"Allow_{_sanitize(src_label)}_to_{port}",
            "priority": priority,
            "direction": "Inbound",
            "access": "Allow",
            "protocol": protocol,
            "source": _subnet_cidr(src_sn, containers) if src_sn else "*",
            "source_port": "*",
            "destination": _subnet_cidr(tgt_sn, containers),
            "destination_port": str(port) if port else "*",
            "description": f"Allow {src_vm} → {tgt_vm} on {protocol}/{port}",
            "source_vms": [src_vm],
            "target_vms": [tgt_vm],
        })

    # Add standard rules to each subnet
    nsg_output: list[dict[str, Any]] = []
    for sn in subnets:
        sn_id = sn["id"]
        sn_label = sn.get("label", sn_id)
        rules = []

        # Azure service rules
        if include_service_rules:
            rules.extend(_AZURE_SERVICE_RULES)

        # Bastion rule
        if include_bastion:
            rules.append({
                "name": "AllowBastionInbound",
                "priority": 150,
                "direction": "Inbound",
                "access": "Allow",
                "protocol": "Tcp",
                "source": "AzureBastion",  # Bastion subnet
                "source_port": "*",
                "destination": "*",
                "destination_port": "22,3389",
                "description": "Allow SSH/RDP from Azure Bastion",
            })

        # Dependency-derived rules
        rules.extend(subnet_rules.get(sn_id, []))

        # Default deny
        rules.append({
            "name": "DenyAllInbound",
            "priority": 4096,
            "direction": "Inbound",
            "access": "Deny",
            "protocol": "*",
            "source": "*",
            "source_port": "*",
            "destination": "*",
            "destination_port": "*",
            "description": "Deny all other inbound traffic",
        })

        # Outbound service rules
        if include_service_rules:
            rules.extend(_OUTBOUND_SERVICE_RULES)

        nsg_output.append({
            "subnet_id": sn_id,
            "subnet_label": sn_label,
            "nsg_name": f"nsg-{_sanitize(sn_label.split('(')[0].strip())}",
            "rule_count": len(rules),
            "rules": rules,
        })

    return {
        "subnet_count": len(nsg_output),
        "total_rules": sum(n["rule_count"] for n in nsg_output),
        "dependency_rules": sum(len(subnet_rules.get(sn["id"], [])) for sn in subnets),
        "nsgs": nsg_output,
    }


def _subnet_label(sn_id: str, containers: list[dict]) -> str:
    sn = next((c for c in containers if c["id"] == sn_id), None)
    return sn.get("label", sn_id).split("(")[0].strip() if sn else sn_id


def _subnet_cidr(sn_id: str, containers: list[dict]) -> str:
    sn = next((c for c in containers if c["id"] == sn_id), None)
    if sn:
        m = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)", sn.get("label", ""))
        if m:
            return m.group(1)
    return "*"


def _sanitize(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", name)[:40]
