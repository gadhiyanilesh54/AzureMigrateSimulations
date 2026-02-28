"""Main orchestrator — ties discovery, twin creation, mapping, and visualization together."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

from .azure_mapping import generate_recommendations
from .azure_provisioning import provision_digital_twins
from .config import load_config
from .twin_builder import create_digital_twin
from .vcenter_discovery import discover_environment
from .visualization import (
    console,
    export_report_json,
    print_discovery_summary,
    print_issues_report,
    print_recommendations_table,
    print_topology_tree,
    print_vm_table,
)

logger = logging.getLogger("digital_twin_migrate")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, markup=True)],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dt-migrate",
        description="Create a digital twin of on-premises VMware vCenter workloads in Azure.",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only discover the vCenter environment (skip Azure Digital Twins creation).",
    )
    parser.add_argument(
        "--skip-twin",
        action="store_true",
        help="Skip Azure Digital Twins provisioning and twin creation.",
    )
    parser.add_argument(
        "--skip-perf",
        action="store_true",
        help="Skip performance data collection (faster discovery).",
    )
    parser.add_argument(
        "--export",
        type=str,
        default="discovery_report.json",
        help="Path to export the JSON report (default: discovery_report.json).",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="eastus",
        help="Target Azure region for recommendations (default: eastus).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    _setup_logging(args.verbose)

    console.print(Panel(
        "[bold blue]Azure Migrate — Digital Twin Creator[/]\n"
        "Discover on-prem VMware workloads and create a digital twin in Azure",
        border_style="blue",
    ))

    # ── Load configuration ──────────────────────────────────────────────
    cfg = load_config()
    if not cfg.vcenter.host or not cfg.vcenter.username:
        console.print("[bold red]Error:[/] vCenter connection details not configured. Check .env file.")
        sys.exit(1)

    # ── Step 1: Discover vCenter environment ────────────────────────────
    console.print("\n[bold]Step 1:[/] Discovering vCenter environment …\n")
    try:
        env = discover_environment(cfg.vcenter, collect_perf=not args.skip_perf)
    except Exception as e:
        console.print(f"[bold red]Discovery failed:[/] {e}")
        logger.exception("Discovery error")
        sys.exit(1)

    # ── Print discovery results ─────────────────────────────────────────
    print_discovery_summary(env)
    console.print()
    print_topology_tree(env)
    console.print()
    print_vm_table(env)

    if not env.vms:
        console.print("[yellow]No VMs discovered. Nothing to do.[/]")
        sys.exit(0)

    # ── Step 2: Generate Azure recommendations ──────────────────────────
    console.print("\n[bold]Step 2:[/] Generating Azure migration recommendations …\n")
    recommendations = generate_recommendations(env, target_region=args.region)
    print_recommendations_table(recommendations)
    console.print()
    print_issues_report(recommendations)

    # ── Step 3: Export report ───────────────────────────────────────────
    export_path = Path(args.export)
    export_report_json(env, recommendations, export_path)

    if args.discover_only:
        console.print("\n[dim]--discover-only specified. Skipping Azure Digital Twins creation.[/]")
        return

    # ── Step 4: Provision Azure Digital Twins ───────────────────────────
    if not args.skip_twin:
        if not cfg.azure.subscription_id:
            console.print("[bold red]Error:[/] Azure subscription ID not configured. Check .env file.")
            sys.exit(1)

        console.print("\n[bold]Step 3:[/] Provisioning Azure Digital Twins instance …\n")
        try:
            endpoint = provision_digital_twins(cfg.azure)
        except Exception as e:
            console.print(f"[bold red]Azure provisioning failed:[/] {e}")
            logger.exception("Provisioning error")
            sys.exit(1)

        # ── Step 5: Create digital twins ────────────────────────────────
        console.print("\n[bold]Step 4:[/] Creating digital twin of on-prem environment …\n")
        try:
            create_digital_twin(endpoint, env)
        except Exception as e:
            console.print(f"[bold red]Twin creation failed:[/] {e}")
            logger.exception("Twin creation error")
            sys.exit(1)

        console.print(Panel(
            f"[bold green]✓ Digital twin created successfully![/]\n\n"
            f"[bold]ADT Endpoint:[/] {endpoint}\n"
            f"[bold]Twins created:[/] {len(env.datacenters) + len(env.clusters) + len(env.hosts) + len(env.datastores) + len(env.networks) + len(env.vms)}\n"
            f"[bold]Report:[/] {export_path.absolute()}\n\n"
            f"[dim]View your digital twin in Azure Portal → Digital Twins Explorer[/]",
            title="Complete",
            border_style="green",
        ))
    else:
        console.print("\n[dim]--skip-twin specified. Skipping Azure Digital Twins creation.[/]")

    console.print("\n[bold green]Done![/]")


if __name__ == "__main__":
    main()
