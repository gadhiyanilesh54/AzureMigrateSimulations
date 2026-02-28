"""Rich console visualization and reporting for the discovered environment and recommendations."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .azure_mapping import AzureRecommendation
from .models import DiscoveredEnvironment, PowerState

logger = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Summary banner
# ---------------------------------------------------------------------------

def print_discovery_summary(env: DiscoveredEnvironment) -> None:
    """Print a high-level summary of what was discovered."""
    powered_on = sum(1 for vm in env.vms if vm.power_state == PowerState.POWERED_ON)
    total_vcpus = sum(vm.num_cpus for vm in env.vms)
    total_memory_gb = sum(vm.memory_mb for vm in env.vms) / 1024
    total_disk_tb = sum(vm.total_disk_gb for vm in env.vms) / 1024

    summary = (
        f"[bold cyan]vCenter:[/] {env.vcenter_host}\n"
        f"[bold]Datacenters:[/]  {len(env.datacenters)}    "
        f"[bold]Clusters:[/] {len(env.clusters)}    "
        f"[bold]Hosts:[/] {len(env.hosts)}\n"
        f"[bold]VMs:[/] {len(env.vms)} ({powered_on} powered on)    "
        f"[bold]Datastores:[/] {len(env.datastores)}    "
        f"[bold]Networks:[/] {len(env.networks)}\n"
        f"\n"
        f"[bold]Total vCPUs:[/] {total_vcpus}    "
        f"[bold]Total Memory:[/] {total_memory_gb:,.0f} GB    "
        f"[bold]Total Disk:[/] {total_disk_tb:,.1f} TB"
    )
    console.print(Panel(summary, title="[bold green]Discovery Summary", border_style="green"))


# ---------------------------------------------------------------------------
# Environment topology tree
# ---------------------------------------------------------------------------

def print_topology_tree(env: DiscoveredEnvironment) -> None:
    """Print the environment as a hierarchical tree."""
    tree = Tree(f"[bold blue]vCenter: {env.vcenter_host}")

    for dc in env.datacenters:
        dc_node = tree.add(f"[bold yellow]📁 Datacenter: {dc.name}")

        # Clusters & hosts
        dc_clusters = [c for c in env.clusters if c.datacenter == dc.name]
        for cl in dc_clusters:
            cl_node = dc_node.add(
                f"[bold cyan]⚙ Cluster: {cl.name}  "
                f"(HA={'✓' if cl.ha_enabled else '✗'} DRS={'✓' if cl.drs_enabled else '✗'})"
            )
            cl_hosts = [h for h in env.hosts if h.cluster == cl.name]
            for h in cl_hosts:
                h_node = cl_node.add(
                    f"[white]🖥 Host: {h.name}  "
                    f"({h.cpu_cores}c/{h.memory_mb // 1024}GB, {h.esxi_version})"
                )
                host_vms = [vm for vm in env.vms if vm.host == h.name]
                for vm in host_vms:
                    power_icon = "🟢" if vm.power_state == PowerState.POWERED_ON else "🔴"
                    h_node.add(
                        f"{power_icon} [white]{vm.name}  "
                        f"({vm.num_cpus}vCPU, {vm.memory_mb // 1024}GB, "
                        f"{vm.total_disk_gb:.0f}GB disk, {vm.guest_os_family.value})"
                    )

        # Datastores
        dc_datastores = [ds for ds in env.datastores if ds.datacenter == dc.name]
        if dc_datastores:
            ds_folder = dc_node.add("[bold magenta]💾 Datastores")
            for ds in dc_datastores:
                used = ds.capacity_gb - ds.free_space_gb
                pct = (used / ds.capacity_gb * 100) if ds.capacity_gb > 0 else 0
                ds_folder.add(
                    f"[white]{ds.name}  ({ds.type}, "
                    f"{used:,.0f}/{ds.capacity_gb:,.0f} GB used, {pct:.0f}%)"
                )

        # Networks
        dc_networks = [n for n in env.networks if n.datacenter == dc.name]
        if dc_networks:
            net_folder = dc_node.add("[bold green]🌐 Networks")
            for n in dc_networks:
                vlan = f"VLAN {n.vlan_id}" if n.vlan_id else "No VLAN"
                net_folder.add(f"[white]{n.name}  ({n.network_type}, {vlan})")

    console.print(tree)


# ---------------------------------------------------------------------------
# VM Inventory table
# ---------------------------------------------------------------------------

def print_vm_table(env: DiscoveredEnvironment) -> None:
    """Print a detailed table of all discovered VMs."""
    table = Table(title="Discovered Virtual Machines", show_lines=True)
    table.add_column("Name", style="bold", max_width=25)
    table.add_column("State", justify="center")
    table.add_column("vCPUs", justify="right")
    table.add_column("RAM (GB)", justify="right")
    table.add_column("Disk (GB)", justify="right")
    table.add_column("OS", max_width=30)
    table.add_column("Host", max_width=20)
    table.add_column("CPU %", justify="right")
    table.add_column("Mem %", justify="right")
    table.add_column("IPs", max_width=25)

    for vm in sorted(env.vms, key=lambda v: v.name):
        state = "[green]ON[/]" if vm.power_state == PowerState.POWERED_ON else "[red]OFF[/]"
        ips = ", ".join(ip for nic in vm.nics for ip in nic.ip_addresses[:2])
        cpu_pct = f"{vm.perf.cpu_usage_percent:.0f}" if vm.perf.cpu_usage_percent > 0 else "—"
        mem_pct = f"{vm.perf.memory_usage_percent:.0f}" if vm.perf.memory_usage_percent > 0 else "—"
        table.add_row(
            vm.name, state, str(vm.num_cpus), str(vm.memory_mb // 1024),
            f"{vm.total_disk_gb:.0f}", vm.guest_os[:30], vm.host[:20],
            cpu_pct, mem_pct, ips or "—",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Azure recommendations table
# ---------------------------------------------------------------------------

def print_recommendations_table(recommendations: list[AzureRecommendation]) -> None:
    """Print Azure migration recommendations for each VM."""
    table = Table(title="Azure Migration Recommendations", show_lines=True)
    table.add_column("VM Name", style="bold", max_width=25)
    table.add_column("Azure VM SKU", style="cyan")
    table.add_column("Family")
    table.add_column("Disk Type")
    table.add_column("Disk GB", justify="right")
    table.add_column("Monthly $", justify="right", style="green")
    table.add_column("Readiness", justify="center")
    table.add_column("Confidence", justify="right")
    table.add_column("Right-Sizing Note", max_width=40)

    total_cost = 0.0
    for rec in sorted(recommendations, key=lambda r: r.vm_name):
        readiness_style = {
            "Ready": "[green]Ready[/]",
            "Ready with conditions": "[yellow]Conditional[/]",
            "Not Ready": "[red]Not Ready[/]",
        }.get(rec.migration_readiness, rec.migration_readiness)

        conf_style = (
            f"[green]{rec.confidence_score:.0f}%[/]" if rec.confidence_score >= 80
            else f"[yellow]{rec.confidence_score:.0f}%[/]" if rec.confidence_score >= 50
            else f"[red]{rec.confidence_score:.0f}%[/]"
        )

        table.add_row(
            rec.vm_name,
            rec.recommended_vm_sku,
            rec.recommended_vm_family,
            rec.recommended_disk_type,
            str(rec.recommended_disk_size_gb),
            f"${rec.estimated_monthly_cost_usd:,.2f}",
            readiness_style,
            conf_style,
            rec.right_sizing_note[:40] if rec.right_sizing_note else "—",
        )
        total_cost += rec.estimated_monthly_cost_usd

    console.print(table)
    console.print(
        Panel(
            f"[bold green]Estimated total monthly Azure cost: ${total_cost:,.2f}[/]\n"
            f"[dim]Estimated annual cost: ${total_cost * 12:,.2f}[/]",
            title="Cost Summary",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# Issues / blockers report
# ---------------------------------------------------------------------------

def print_issues_report(recommendations: list[AzureRecommendation]) -> None:
    """Print migration issues and blockers."""
    issues_found = [r for r in recommendations if r.migration_issues]
    if not issues_found:
        console.print("[bold green]✓ No migration issues detected.[/]\n")
        return

    table = Table(title="Migration Issues & Blockers", show_lines=True)
    table.add_column("VM Name", style="bold")
    table.add_column("Readiness")
    table.add_column("Issues", style="yellow")

    for rec in issues_found:
        readiness_style = "[red]" if rec.migration_readiness == "Not Ready" else "[yellow]"
        table.add_row(
            rec.vm_name,
            f"{readiness_style}{rec.migration_readiness}[/]",
            "\n".join(f"• {i}" for i in rec.migration_issues),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Export to JSON
# ---------------------------------------------------------------------------

def export_report_json(
    env: DiscoveredEnvironment,
    recommendations: list[AzureRecommendation],
    output_path: Path,
) -> None:
    """Export the full discovery + recommendations to a JSON file."""
    from dataclasses import asdict

    report = {
        "vcenter_host": env.vcenter_host,
        "summary": {
            "datacenters": len(env.datacenters),
            "clusters": len(env.clusters),
            "hosts": len(env.hosts),
            "vms": len(env.vms),
            "datastores": len(env.datastores),
            "networks": len(env.networks),
        },
        "vms": [asdict(vm) for vm in env.vms],
        "hosts": [asdict(h) for h in env.hosts],
        "clusters": [asdict(c) for c in env.clusters],
        "datastores": [asdict(ds) for ds in env.datastores],
        "networks": [asdict(n) for n in env.networks],
        "recommendations": [asdict(r) for r in recommendations],
        "total_monthly_cost_usd": round(sum(r.estimated_monthly_cost_usd for r in recommendations), 2),
    }

    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Report exported to %s", output_path)
    console.print(f"\n[bold]Report exported to:[/] {output_path}")
