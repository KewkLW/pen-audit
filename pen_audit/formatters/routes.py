"""Routes formatter: generates routes.json entries from detected screens."""

from __future__ import annotations

import re


def _slugify(name: str) -> str:
    """Convert a screen name to a URL slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug


def generate_routes(state: dict) -> dict:
    """Generate a routes.json structure from detected screen features."""
    features = state.get("features", {})

    routes = []
    for fid, f in features.items():
        if f["category"] != "screen":
            continue

        name = f["name"]
        platform = f["detail"].get("platform", "unknown")
        slug = _slugify(name)

        # Determine platforms array
        if platform == "mobile":
            platforms = ["mobile", "web"]
        elif platform == "desktop":
            platforms = ["desktop", "web"]
        else:
            platforms = ["mobile", "desktop", "web"]

        routes.append({
            "id": f"app.{slug.replace('-', '_')}",
            "screen_name": name,
            "path": f"/app/{slug}",
            "platforms": platforms,
            "requires_auth": True,
            "tier": f["tier"],
            "status": f["status"],
            "pen_node_id": f["screen_id"],
        })

    return {
        "generated_by": "pen-audit",
        "source": state.get("source_file", "unknown"),
        "routes": sorted(routes, key=lambda r: r["path"]),
    }
