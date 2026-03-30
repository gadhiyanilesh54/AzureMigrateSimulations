"""Migration status tracker — per-VM state machine through the migration lifecycle.

Tracks each VM from Not Started → Planned → Replicating → Test Failover →
Migrated → Validated → Decommissioned, with timestamps, notes, and blockers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Valid state transitions
VALID_STATES = [
    "Not Started", "Planned", "Replicating",
    "Test Failover", "Migrated", "Validated", "Decommissioned",
]

_TRANSITIONS: dict[str, list[str]] = {
    "Not Started": ["Planned"],
    "Planned": ["Replicating", "Not Started"],
    "Replicating": ["Test Failover", "Planned"],
    "Test Failover": ["Migrated", "Replicating"],
    "Migrated": ["Validated", "Test Failover"],
    "Validated": ["Decommissioned"],
    "Decommissioned": [],
}


def get_migration_progress(
    status_data: dict[str, Any],
    wave_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get migration progress summary with per-wave breakdown."""
    statuses = status_data.get("statuses", {})

    # Global counts
    state_counts: dict[str, int] = {s: 0 for s in VALID_STATES}
    for vm_status in statuses.values():
        state = vm_status.get("state", "Not Started")
        state_counts[state] = state_counts.get(state, 0) + 1

    total = sum(state_counts.values())
    migrated = state_counts.get("Migrated", 0) + state_counts.get("Validated", 0) + state_counts.get("Decommissioned", 0)

    # Per-wave breakdown
    wave_progress = []
    if wave_plan and wave_plan.get("waves"):
        for wave in wave_plan["waves"]:
            wave_num = wave.get("wave", 0)
            wave_vms = wave.get("vms", [])
            wave_states: dict[str, int] = {s: 0 for s in VALID_STATES}
            for vm_name in wave_vms:
                state = statuses.get(vm_name, {}).get("state", "Not Started")
                wave_states[state] = wave_states.get(state, 0) + 1
            wave_migrated = wave_states.get("Migrated", 0) + wave_states.get("Validated", 0) + wave_states.get("Decommissioned", 0)
            wave_progress.append({
                "wave": wave_num,
                "vm_count": len(wave_vms),
                "migrated": wave_migrated,
                "progress_pct": round(wave_migrated / len(wave_vms) * 100, 1) if wave_vms else 0,
                "state_breakdown": wave_states,
            })

    # Blockers
    blockers = []
    for vm_name, vm_status in statuses.items():
        if vm_status.get("blocker"):
            blockers.append({
                "vm_name": vm_name,
                "state": vm_status.get("state"),
                "blocker": vm_status["blocker"],
            })

    return {
        "total_vms": total,
        "migrated": migrated,
        "progress_pct": round(migrated / total * 100, 1) if total else 0,
        "state_counts": state_counts,
        "wave_progress": wave_progress,
        "blockers": blockers,
        "blocker_count": len(blockers),
    }


def set_vm_status(
    status_data: dict[str, Any],
    vm_name: str,
    new_state: str,
    note: str | None = None,
    blocker: str | None = None,
) -> dict[str, Any]:
    """Update a VM's migration status with validation."""
    if new_state not in VALID_STATES:
        return {"error": f"Invalid state '{new_state}'. Valid: {VALID_STATES}"}

    statuses = status_data.setdefault("statuses", {})
    current = statuses.get(vm_name, {"state": "Not Started", "history": []})
    current_state = current.get("state", "Not Started")

    # Validate transition
    allowed = _TRANSITIONS.get(current_state, [])
    if new_state != current_state and new_state not in allowed:
        return {
            "error": f"Cannot transition from '{current_state}' to '{new_state}'. Allowed: {allowed}",
            "vm_name": vm_name,
            "current_state": current_state,
        }

    # Record transition
    now = datetime.now(timezone.utc).isoformat()
    current.setdefault("history", []).append({
        "from": current_state,
        "to": new_state,
        "timestamp": now,
        "note": note,
    })
    current["state"] = new_state
    current["updated_at"] = now
    if blocker is not None:
        current["blocker"] = blocker if blocker else None
    if note:
        current["last_note"] = note

    statuses[vm_name] = current

    return {
        "vm_name": vm_name,
        "state": new_state,
        "previous_state": current_state,
        "updated_at": now,
        "blocker": current.get("blocker"),
    }


def log_blocker(
    status_data: dict[str, Any],
    vm_name: str,
    blocker: str,
) -> dict[str, Any]:
    """Log or clear a blocker on a VM."""
    statuses = status_data.setdefault("statuses", {})
    current = statuses.get(vm_name, {"state": "Not Started", "history": []})
    current["blocker"] = blocker if blocker else None
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    statuses[vm_name] = current
    return {"vm_name": vm_name, "blocker": current["blocker"], "state": current["state"]}
