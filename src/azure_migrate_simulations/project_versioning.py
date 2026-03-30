"""Project versioning — save, restore, and compare project snapshots.

Allows customers to save point-in-time snapshots of their migration planning
state, restore previous versions, and compare iterations.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SNAPSHOT_FILES = [
    "vcenter_discovery.json", "workload_discovery.json",
    "whatif_overrides.json", "enrichment_data.json",
    "perf_history.json", "_wave_plan.json", "_last_topology.json",
    "migration_status.json", "application_groups.json",
]


def save_snapshot(data_dir: Path, name: str, description: str = "") -> dict[str, Any]:
    """Save a snapshot of the current project state."""
    snapshots_dir = data_dir / "snapshots"
    snapshots_dir.mkdir(exist_ok=True)

    safe_name = _sanitize(name)
    snap_dir = snapshots_dir / safe_name
    if snap_dir.exists():
        return {"error": f"Snapshot '{safe_name}' already exists. Choose a different name."}

    snap_dir.mkdir()

    copied = []
    for fname in _SNAPSHOT_FILES:
        src = data_dir / fname
        if src.exists():
            shutil.copy2(str(src), str(snap_dir / fname))
            copied.append(fname)

    # Save snapshot metadata
    meta = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": description,
        "files": copied,
        "vm_count": _count_vms(snap_dir),
    }
    (snap_dir / "_snapshot.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {"saved": safe_name, **meta}


def list_snapshots(data_dir: Path) -> list[dict[str, Any]]:
    """List all snapshots with metadata."""
    snapshots_dir = data_dir / "snapshots"
    if not snapshots_dir.exists():
        return []

    snapshots = []
    for snap_dir in sorted(snapshots_dir.iterdir()):
        if not snap_dir.is_dir():
            continue
        meta_file = snap_dir / "_snapshot.json"
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        snapshots.append({
            "id": snap_dir.name,
            "name": meta.get("name", snap_dir.name),
            "created_at": meta.get("created_at", ""),
            "description": meta.get("description", ""),
            "vm_count": meta.get("vm_count", _count_vms(snap_dir)),
            "file_count": len(meta.get("files", [])),
        })

    return snapshots


def restore_snapshot(data_dir: Path, snapshot_name: str) -> dict[str, Any]:
    """Restore a snapshot, auto-saving current state first."""
    safe_name = _sanitize(snapshot_name)
    snap_dir = data_dir / "snapshots" / safe_name

    if not snap_dir.exists():
        return {"error": f"Snapshot '{safe_name}' not found."}

    # Auto-save current state
    auto_name = f"pre-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    auto_result = save_snapshot(data_dir, auto_name, description=f"Auto-saved before restoring '{snapshot_name}'")

    # Restore files from snapshot
    restored = []
    for fname in _SNAPSHOT_FILES:
        src = snap_dir / fname
        if src.exists():
            dest = data_dir / fname
            shutil.copy2(str(src), str(dest))
            restored.append(fname)

    return {
        "restored": safe_name,
        "auto_saved_as": auto_name,
        "files_restored": restored,
        "file_count": len(restored),
    }


def compare_snapshots(data_dir: Path, snapshot_a: str, snapshot_b: str) -> dict[str, Any]:
    """Compare two snapshots and show deltas."""
    dir_a = data_dir / "snapshots" / _sanitize(snapshot_a)
    dir_b = data_dir / "snapshots" / _sanitize(snapshot_b)

    if not dir_a.exists():
        return {"error": f"Snapshot '{snapshot_a}' not found."}
    if not dir_b.exists():
        return {"error": f"Snapshot '{snapshot_b}' not found."}

    # Load discovery data from both
    disc_a = _load(dir_a / "vcenter_discovery.json")
    disc_b = _load(dir_b / "vcenter_discovery.json")

    vms_a = {v.get("name") for v in disc_a.get("vms", [])}
    vms_b = {v.get("name") for v in disc_b.get("vms", [])}

    recs_a = {r.get("vm_name"): r for r in disc_a.get("recommendations", [])}
    recs_b = {r.get("vm_name"): r for r in disc_b.get("recommendations", [])}

    # VM changes
    added = sorted(vms_b - vms_a)
    removed = sorted(vms_a - vms_b)
    common = vms_a & vms_b

    # SKU changes
    sku_changes = []
    cost_delta = 0.0
    for vm in sorted(common):
        sku_a = recs_a.get(vm, {}).get("recommended_vm_sku", "")
        sku_b = recs_b.get(vm, {}).get("recommended_vm_sku", "")
        cost_a = recs_a.get(vm, {}).get("estimated_monthly_cost", 0)
        cost_b = recs_b.get(vm, {}).get("estimated_monthly_cost", 0)
        if sku_a != sku_b:
            sku_changes.append({"vm": vm, "from_sku": sku_a, "to_sku": sku_b, "cost_delta": round(cost_b - cost_a, 2)})
        cost_delta += cost_b - cost_a

    # Wave plan changes
    wave_a = _load(dir_a / "_wave_plan.json")
    wave_b = _load(dir_b / "_wave_plan.json")
    wave_count_a = len(wave_a.get("waves", []))
    wave_count_b = len(wave_b.get("waves", []))

    return {
        "snapshot_a": snapshot_a,
        "snapshot_b": snapshot_b,
        "vm_count_a": len(vms_a),
        "vm_count_b": len(vms_b),
        "vms_added": added[:20],
        "vms_removed": removed[:20],
        "vms_added_count": len(added),
        "vms_removed_count": len(removed),
        "sku_changes": sku_changes[:20],
        "sku_change_count": len(sku_changes),
        "total_cost_delta": round(cost_delta, 2),
        "wave_count_a": wave_count_a,
        "wave_count_b": wave_count_b,
    }


def delete_snapshot(data_dir: Path, snapshot_name: str) -> dict[str, Any]:
    """Delete a snapshot."""
    safe_name = _sanitize(snapshot_name)
    snap_dir = data_dir / "snapshots" / safe_name
    if not snap_dir.exists():
        return {"error": f"Snapshot '{safe_name}' not found."}
    shutil.rmtree(str(snap_dir))
    return {"deleted": safe_name}


# ═══════════════════════════════════════════════════════════════════════════

def _sanitize(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")[:60]

def _count_vms(directory: Path) -> int:
    disc_file = directory / "vcenter_discovery.json"
    if disc_file.exists():
        try:
            data = json.loads(disc_file.read_text(encoding="utf-8"))
            return len(data.get("vms", []))
        except Exception:
            pass
    return 0

def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}
