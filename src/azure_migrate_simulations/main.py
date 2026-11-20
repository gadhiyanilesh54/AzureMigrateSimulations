"""Main orchestrator — ties discovery, twin creation, mapping, and visualization together."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from .azure_mapping import generate_recommendations
from .azure_provisioning import provision_digital_twins
from .config import load_config
from .perf_aggregator import apply_perf_history
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

logger = logging.getLogger("azure_migrate_simulations")


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
        "--perf-history",
        type=str,
        default=None,
        help="Path to perf_history.json for enriched percentile-based sizing.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    return parser.parse_args()


def main() -> None:
    # Check for 'risk' subcommand first
    if len(sys.argv) >= 2 and sys.argv[1] == "risk":
        _handle_risk_cli()
        return

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

    # ── Step 1b: Enrich with perf history (if provided) ─────────────────
    perf_path = args.perf_history
    if perf_path is None:
        # Auto-detect data/perf_history.json relative to project root
        auto_path = Path(__file__).resolve().parents[2] / "data" / "perf_history.json"
        if auto_path.exists():
            perf_path = str(auto_path)

    if perf_path:
        console.print(f"\n[bold]Step 1b:[/] Enriching VMs with perf history from {perf_path} …\n")
        try:
            matched = apply_perf_history(env, perf_path)
            console.print(f"  [green]✓ Perf history applied to {matched} / {len(env.vms)} VMs[/]")
        except Exception as e:
            console.print(f"  [yellow]⚠ Could not load perf history:[/] {e}")
            logger.warning("Perf history enrichment failed: %s", e)

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


# ---------------------------------------------------------------------------
# Risk Heatmap CLI
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_data_file(name: str) -> dict:
    path = _DATA_DIR / name
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _band_style(band: str) -> str:
    if band == "green":
        return "green"
    if band == "yellow":
        return "yellow"
    return "red"


def _handle_risk_cli() -> None:
    parser = argparse.ArgumentParser(prog="dt-migrate risk")
    sub = parser.add_subparsers(dest="subcmd")

    hm_parser = sub.add_parser("heatmap", help="Compute fleet-wide risk heatmap")
    hm_parser.add_argument("--top", type=int, default=10, help="Top-N riskiest VMs (default: 10)")
    hm_parser.add_argument("--format", dest="fmt", choices=["json", "table"], default="table")
    hm_parser.add_argument("--band", choices=["green", "yellow", "red"], default=None)

    sc_parser = sub.add_parser("score", help="Compute risk score for a single VM")
    sc_parser.add_argument("vm_name", help="VM name to score")
    sc_parser.add_argument("--format", dest="fmt", choices=["json", "table"], default="table")

    args = parser.parse_args(sys.argv[2:])

    if args.subcmd is None:
        parser.print_help()
        sys.exit(2)

    disc = _load_data_file("vcenter_discovery.json")
    vms = disc.get("vms", [])
    if not vms:
        console.print("[bold red]Error:[/] No discovery data found. Run discovery first or place vcenter_discovery.json in data/.")
        sys.exit(1)

    wl = _load_data_file("workload_discovery.json")
    enr = _load_data_file("enrichment_data.json")

    from .risk_heatmap import compute_heatmap, compute_risk_score, _compute_fleet_stats

    if args.subcmd == "heatmap":
        _cmd_risk_heatmap(vms, wl, enr, args)
    elif args.subcmd == "score":
        _cmd_risk_score(vms, wl, enr, args)


def _cmd_risk_heatmap(vms: list, wl: dict, enr: dict, args) -> None:
    from .risk_heatmap import compute_heatmap

    heatmap = compute_heatmap(vms, wl, enr, top_n=args.top)
    result = asdict(heatmap)

    if args.band:
        result["vm_scores"] = [s for s in result["vm_scores"] if s["composite_band"] == args.band]

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    # Rich table output
    table = Table(title=f"Migration Risk Heatmap ({heatmap.total_vms} VMs)")
    table.add_column("VM Name", style="bold", max_width=30)
    table.add_column("Deps", justify="center")
    table.add_column("OS EOL", justify="center")
    table.add_column("Wkload", justify="center")
    table.add_column("Perf", justify="center")
    table.add_column("Comp", justify="center")
    table.add_column("Data", justify="center")
    table.add_column("Composite", justify="center", style="bold")

    for s in result["vm_scores"][:args.top]:
        factors = {f["name"]: f for f in s.get("factors", [])}
        row = [s["vm_name"]]
        for fname in ["dependency_count", "os_eol", "workload_complexity",
                       "performance_sensitivity", "compliance_scope", "data_volume"]:
            f = factors.get(fname, {})
            score = f.get("score", 0)
            band = f.get("band", "green")
            row.append(f"[{_band_style(band)}]{score}[/]")
        comp_band = s.get("composite_band", "green")
        row.append(f"[{_band_style(comp_band)}]{s['composite_score']}[/]")
        table.add_row(*row)

    console.print(table)
    dist = heatmap.band_distribution
    console.print(f"\n  [green]● {dist.get('green', 0)} Low[/]  [yellow]● {dist.get('yellow', 0)} Medium[/]  [red]● {dist.get('red', 0)} High[/]")


def _cmd_risk_score(vms: list, wl: dict, enr: dict, args) -> None:
    from .risk_heatmap import compute_risk_score, _compute_fleet_stats

    vm = None
    for v in vms:
        if v.get("name") == args.vm_name:
            vm = v
            break

    if vm is None:
        console.print(f"[bold red]Error:[/] VM '{args.vm_name}' not found in discovery data.")
        sys.exit(1)

    max_deps, iops_p75, max_disk = _compute_fleet_stats(vms, wl, enr)
    score = compute_risk_score(vm, wl, enr, max_deps, iops_p75, max_disk)
    result = asdict(score)

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    # Rich panel output
    table = Table(show_header=True, header_style="bold")
    table.add_column("Factor")
    table.add_column("Raw Value")
    table.add_column("Score", justify="center")
    table.add_column("Weight", justify="center")
    table.add_column("Weighted", justify="center")
    table.add_column("Band", justify="center")

    for f in score.factors:
        band_style = _band_style(f.band)
        avail = "" if f.data_available else " ⚠"
        table.add_row(
            f.name.replace("_", " ").title() + avail,
            f.raw_value,
            f"[{band_style}]{f.score}[/]",
            f"{f.weight:.0%}",
            f"{f.weighted_score:.1f}",
            f"[{band_style}]{f.band.upper()}[/]",
        )

    comp_style = _band_style(score.composite_band)
    panel_title = f"Risk Score: {score.vm_name} — Composite: [{comp_style}]{score.composite_score} ({score.composite_band.upper()})[/]"
    console.print(Panel(table, title=panel_title, border_style=comp_style))

    if score.mitigations:
        console.print("\n[bold]Mitigation Suggestions:[/]")
        for m in score.mitigations:
            console.print(f"  [{_band_style(m.severity)}]●[/] [{m.factor.replace('_', ' ').title()}] {m.action}")


if __name__ == "__main__":
    main()
