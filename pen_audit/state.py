"""Persistent state management for pen-audit (.pen-audit/state.json).

Tracks detected features and their implementation status across scans.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .scoring import compute_completion

CURRENT_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable: {obj!r}")


def _empty_state() -> dict:
    return {
        "version": CURRENT_VERSION,
        "created": _now(),
        "last_scan": None,
        "scan_count": 0,
        "source_file": None,
        "features": {},
        "components": {},
        "stats": {},
    }


def get_state_path(project_dir: Path | None = None) -> Path:
    """Get the state file path for a project directory."""
    base = project_dir or Path.cwd()
    return base / ".pen-audit" / "state.json"


def load_state(path: Path | None = None) -> dict:
    """Load state from disk, or return empty state."""
    p = path or get_state_path()
    if not p.exists():
        return _empty_state()

    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        backup = p.with_suffix(".json.bak")
        if backup.exists():
            try:
                return json.loads(backup.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        print(f"  State file corrupted ({e}). Starting fresh.", file=sys.stderr)
        return _empty_state()

    return data


def save_state(state: dict, path: Path | None = None):
    """Recompute stats and save to disk atomically."""
    _recompute_stats(state)
    p = path or get_state_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(state, indent=2, default=_json_default) + "\n"

    try:
        fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
        try:
            os.write(fd, content.encode())
            os.fsync(fd)
        finally:
            os.close(fd)

        if p.exists():
            backup = p.with_suffix(".json.bak")
            try:
                import shutil
                shutil.copy2(str(p), str(backup))
            except OSError:
                pass

        os.replace(tmp_path, str(p))
    except OSError:
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass
        p.write_text(content)


def _recompute_stats(state: dict):
    """Recompute stats from features."""
    features = list(state.get("features", {}).values())
    state["stats"] = compute_completion(features)


def make_feature(
    detector: str,
    screen_id: str,
    name: str,
    *,
    tier: int,
    category: str,
    summary: str,
    detail: dict | None = None,
) -> dict:
    """Create a normalized feature dict with a stable ID."""
    fid = f"{detector}::{screen_id}::{name}" if name else f"{detector}::{screen_id}"
    now = _now()
    return {
        "id": fid,
        "detector": detector,
        "screen_id": screen_id,
        "name": name,
        "tier": tier,
        "category": category,
        "summary": summary,
        "detail": detail or {},
        "status": "open",
        "first_seen": now,
        "last_seen": now,
    }


def merge_scan(state: dict, features: list[dict], source_file: str = "") -> dict:
    """Merge a fresh scan into existing state. Returns diff summary."""
    now = _now()
    state["last_scan"] = now
    state["scan_count"] = state.get("scan_count", 0) + 1
    if source_file:
        state["source_file"] = source_file

    existing = state["features"]
    current_ids: set[str] = set()
    new_count = 0

    for f in features:
        fid = f["id"]
        current_ids.add(fid)

        if fid in existing:
            old = existing[fid]
            old["last_seen"] = now
            old["tier"] = f["tier"]
            old["summary"] = f["summary"]
            old["detail"] = f.get("detail", {})
            # Don't overwrite status if already resolved
        else:
            existing[fid] = f
            new_count += 1

    # Auto-resolve features that disappeared from the design
    removed = 0
    for fid, old in existing.items():
        if fid not in current_ids and old["status"] == "open":
            old["status"] = "removed_from_design"
            removed += 1

    _recompute_stats(state)

    return {
        "new": new_count,
        "removed": removed,
        "total": len(current_ids),
    }


def resolve_feature(state: dict, pattern: str, status: str) -> list[str]:
    """Resolve features matching pattern. Returns list of resolved IDs.

    Valid statuses: implemented, deferred, out_of_scope
    """
    resolved = []
    for fid, f in state["features"].items():
        if f["status"] != "open":
            continue
        if fid == pattern or f["screen_id"] == pattern or pattern in fid:
            f["status"] = status
            resolved.append(fid)
    _recompute_stats(state)
    return resolved
