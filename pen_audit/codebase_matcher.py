"""Codebase matcher: scans a Next.js codebase to detect implemented features.

Matches detected pen-audit features against actual page files, routes.json,
and component implementations to auto-resolve features.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def _normalize(s: str) -> str:
    """Normalize a string for fuzzy comparison."""
    return re.sub(r'[^a-z0-9]', '', s.lower())


def _find_page_files(app_dir: Path) -> dict[str, Path]:
    """Find all page.tsx files and map route paths to file paths."""
    pages: dict[str, Path] = {}
    for page_file in app_dir.rglob("page.tsx"):
        rel = page_file.parent.relative_to(app_dir)
        parts = [p for p in rel.parts if not p.startswith("(") and not p.startswith("[")]
        slug = "/".join(parts)
        if slug:
            pages[slug] = page_file
    return pages


def _find_routes_json(project_dir: Path) -> list[dict]:
    """Load routes from contracts/routes.json if it exists."""
    candidates = [
        project_dir / "contracts" / "routes.json",
        project_dir / "routes.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                data = json.loads(p.read_text())
                routes = data.get("routes", []) if isinstance(data, dict) else data
                if isinstance(routes, list):
                    return routes
            except (json.JSONDecodeError, OSError):
                pass
    return []


def _is_stub_page(page_path: Path) -> bool:
    """Check if a page file is just a stub (Coming Soon) or has real content."""
    try:
        content = page_path.read_text(errors="replace")
    except OSError:
        return True

    lines = content.strip().splitlines()
    if len(lines) < 10:
        return True

    content_lower = content.lower()
    if "coming soon" in content_lower and len(lines) < 30:
        return True

    return False


def _build_route_map(routes: list[dict]) -> dict[str, dict]:
    """Build a lookup from normalized screen name to route data."""
    result: dict[str, dict] = {}
    for route in routes:
        if not isinstance(route, dict):
            continue
        screen_name = route.get("screen_name", "")
        if screen_name:
            result[_normalize(screen_name)] = route
    return result


def match_codebase(
    state: dict,
    project_dir: str | Path,
    app_subdir: str = "",
    dry_run: bool = False,
) -> dict:
    """Match pen-audit features against the actual codebase.

    Uses three strategies:
    1. routes.json screen_name matching (most reliable)
    2. Page file path matching against slugified screen names
    3. Page file path last-segment matching

    Args:
        state: pen-audit state dict
        project_dir: path to the project root
        app_subdir: subdirectory containing the Next.js app (e.g., "apps/mobile-web")
        dry_run: if True, don't modify state, just return matches

    Returns:
        dict with matched/stub/missing counts and details
    """
    project = Path(project_dir)
    app_dir = project / app_subdir / "app" if app_subdir else project / "app"

    if not app_dir.exists():
        return {"error": f"App directory not found: {app_dir}", "matched": 0}

    # Find page files and routes
    pages = _find_page_files(app_dir)
    routes = _find_routes_json(project)
    route_map = _build_route_map(routes)

    # Also build a reverse map: route path -> page path
    route_path_to_page: dict[str, Path] = {}
    for route in routes:
        if not isinstance(route, dict):
            continue
        rpath = route.get("path", "").lstrip("/")
        for page_slug, page_path in pages.items():
            if rpath == page_slug or rpath.lstrip("app/") == page_slug.lstrip("app/"):
                route_path_to_page[rpath] = page_path
                break

    results = {
        "matched": [],
        "stub": [],
        "missing": [],
        "total_matched": 0,
        "total_stub": 0,
        "total_missing": 0,
    }

    features = state.get("features", {})
    for fid, f in features.items():
        if f["category"] != "screen":
            continue
        if f["status"] != "open":
            continue

        name = f["name"]
        slug = _slugify(name)
        norm_name = _normalize(name)

        page_path = None
        matched_via = None

        # Strategy 1: Match via routes.json screen_name
        if norm_name in route_map:
            route_data = route_map[norm_name]
            rpath = route_data.get("path", "").lstrip("/")
            matched_via = "routes.json"
            # Find the corresponding page file
            for page_slug, path in pages.items():
                if rpath == page_slug or rpath.endswith(page_slug) or page_slug.endswith(rpath.split("/")[-1]):
                    page_path = path
                    break

        # Strategy 2: Exact slug match in page files
        if not page_path:
            for page_slug, path in pages.items():
                if slug == page_slug or f"app/{slug}" == page_slug:
                    page_path = path
                    matched_via = "exact_slug"
                    break

        # Strategy 3: Last segment match
        if not page_path:
            for page_slug, path in pages.items():
                segments = page_slug.split("/")
                if segments and segments[-1] == slug:
                    page_path = path
                    matched_via = "last_segment"
                    break

        # Strategy 4: Normalized name match against page paths
        if not page_path:
            for page_slug, path in pages.items():
                norm_page = _normalize(page_slug)
                if norm_name == norm_page:
                    page_path = path
                    matched_via = "normalized"
                    break

        # Check routes.json for route entry
        has_route = norm_name in route_map

        if page_path and not _is_stub_page(page_path):
            results["matched"].append({
                "feature_id": fid,
                "screen_name": name,
                "page_path": str(page_path),
                "matched_via": matched_via,
                "has_route": has_route,
            })
            results["total_matched"] += 1
            if not dry_run:
                f["status"] = "implemented"
        elif page_path:
            results["stub"].append({
                "feature_id": fid,
                "screen_name": name,
                "page_path": str(page_path),
                "matched_via": matched_via,
            })
            results["total_stub"] += 1
        else:
            results["missing"].append({
                "feature_id": fid,
                "screen_name": name,
                "expected_slug": slug,
            })
            results["total_missing"] += 1

    return results
