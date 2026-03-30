"""Multi-project support — isolated data directories per migration project.

Each project gets its own data/ subdirectory with independent discovery,
assessment, wave plan, and enrichment data.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def list_projects(data_root: Path) -> list[dict[str, Any]]:
    """List all projects with metadata."""
    projects_dir = data_root / "projects"
    if not projects_dir.exists():
        # Backward compat: treat data_root as the "default" project
        return [_project_meta("default", data_root, is_active=True)]

    active = _get_active_project(data_root)
    projects = []
    for pdir in sorted(projects_dir.iterdir()):
        if pdir.is_dir():
            projects.append(_project_meta(pdir.name, pdir, is_active=(pdir.name == active)))

    if not projects:
        projects.append(_project_meta("default", data_root, is_active=True))

    return projects


def create_project(data_root: Path, name: str) -> dict[str, Any]:
    """Create a new project directory with empty data files."""
    safe_name = _sanitize_name(name)
    projects_dir = data_root / "projects"
    projects_dir.mkdir(exist_ok=True)

    project_dir = projects_dir / safe_name
    if project_dir.exists():
        return {"error": f"Project '{safe_name}' already exists."}

    project_dir.mkdir()

    # Create empty data files
    for fname in ["vcenter_discovery.json", "workload_discovery.json",
                   "whatif_overrides.json", "enrichment_data.json",
                   "perf_history.json"]:
        (project_dir / fname).write_text("{}", encoding="utf-8")

    # Write project metadata
    meta = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "",
    }
    (project_dir / "_project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {"created": safe_name, "path": str(project_dir), **meta}


def switch_project(data_root: Path, project_name: str) -> dict[str, Any]:
    """Switch the active project."""
    safe_name = _sanitize_name(project_name)
    project_dir = data_root / "projects" / safe_name

    if not project_dir.exists():
        return {"error": f"Project '{safe_name}' does not exist."}

    _set_active_project(data_root, safe_name)
    return {"active_project": safe_name, "path": str(project_dir)}


def archive_project(data_root: Path, project_name: str) -> dict[str, Any]:
    """Archive a project (move to archive/ directory)."""
    safe_name = _sanitize_name(project_name)
    project_dir = data_root / "projects" / safe_name

    if not project_dir.exists():
        return {"error": f"Project '{safe_name}' does not exist."}

    archive_dir = data_root / "archive"
    archive_dir.mkdir(exist_ok=True)

    dest = archive_dir / safe_name
    if dest.exists():
        # Add timestamp to avoid collision
        dest = archive_dir / f"{safe_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    shutil.move(str(project_dir), str(dest))

    # If archived project was active, clear active
    if _get_active_project(data_root) == safe_name:
        _set_active_project(data_root, "")

    return {"archived": safe_name, "archive_path": str(dest)}


def get_project_data_dir(data_root: Path) -> Path:
    """Get the data directory for the currently active project."""
    active = _get_active_project(data_root)
    if active:
        project_dir = data_root / "projects" / active
        if project_dir.exists():
            return project_dir
    return data_root  # Fallback to root (backward compat)


def migrate_to_default_project(data_root: Path) -> dict[str, Any]:
    """Migrate existing root-level data files into a 'default' project."""
    projects_dir = data_root / "projects"
    if projects_dir.exists() and list(projects_dir.iterdir()):
        return {"message": "Projects already exist. No migration needed."}

    default_dir = projects_dir / "default"
    default_dir.mkdir(parents=True, exist_ok=True)

    migrated_files = []
    for fname in ["vcenter_discovery.json", "workload_discovery.json",
                   "whatif_overrides.json", "enrichment_data.json",
                   "perf_history.json", "retail_price_cache.json",
                   "_wave_plan.json", "_last_topology.json"]:
        src = data_root / fname
        if src.exists():
            shutil.copy2(str(src), str(default_dir / fname))
            migrated_files.append(fname)

    # Set default as active
    _set_active_project(data_root, "default")

    meta = {
        "name": "Default Project",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "Migrated from root data directory",
    }
    (default_dir / "_project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {"migrated": True, "project": "default", "files": migrated_files}


# ═══════════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

def _project_meta(name: str, path: Path, is_active: bool = False) -> dict[str, Any]:
    meta_file = path / "_project.json"
    meta = {}
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Count VMs
    vm_count = 0
    disc_file = path / "vcenter_discovery.json"
    if disc_file.exists():
        try:
            data = json.loads(disc_file.read_text(encoding="utf-8"))
            vm_count = len(data.get("vms", []))
        except Exception:
            pass

    return {
        "name": meta.get("name", name),
        "id": name,
        "created_at": meta.get("created_at", ""),
        "description": meta.get("description", ""),
        "vm_count": vm_count,
        "is_active": is_active,
        "path": str(path),
    }


def _get_active_project(data_root: Path) -> str:
    active_file = data_root / "_active_project.json"
    if active_file.exists():
        try:
            data = json.loads(active_file.read_text(encoding="utf-8"))
            return data.get("active", "")
        except Exception:
            pass
    return ""


def _set_active_project(data_root: Path, project_name: str) -> None:
    active_file = data_root / "_active_project.json"
    active_file.write_text(json.dumps({"active": project_name}), encoding="utf-8")


def _sanitize_name(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")[:50]
