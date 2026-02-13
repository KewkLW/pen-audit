"""Markdown formatter: generates human-readable feature inventory."""

from __future__ import annotations

from ..scoring import TIER_NAMES, TIER_DESCRIPTIONS


def generate_markdown(state: dict) -> str:
    """Generate a markdown feature inventory from state."""
    features = list(state.get("features", {}).values())
    stats = state.get("stats", {})
    source = state.get("source_file", "unknown")

    lines = [
        "# Feature Inventory",
        "",
        f"**Source**: `{source}`",
        f"**Total features**: {stats.get('total', 0)}",
        f"**Completion**: {stats.get('pct', 0)}%",
        "",
        "## Summary",
        "",
    ]

    # Tier summary
    by_tier = stats.get("by_tier", {})
    lines.append("| Tier | Type | Total | Done | Open |")
    lines.append("|------|------|-------|------|------|")
    for tier in sorted(by_tier.keys(), key=int):
        ts = by_tier[tier]
        tier_int = int(tier)
        open_count = ts["total"] - ts["done"]
        lines.append(
            f"| T{tier} | {TIER_NAMES.get(tier_int, '?')} | {ts['total']} | {ts['done']} | {open_count} |"
        )
    lines.append("")

    # Group by screen
    screens: dict[str, list[dict]] = {}
    components: list[dict] = []

    for f in features:
        if f["category"] == "component":
            components.append(f)
        elif f["category"] == "screen":
            screens.setdefault(f["name"], {"screen": f, "features": []})
        else:
            screen_name = f["detail"].get("screen_name", "Unknown")
            if screen_name not in screens:
                screens[screen_name] = {"screen": None, "features": []}
            screens[screen_name]["features"].append(f)

    # Screens section
    lines.append("## Screens")
    lines.append("")

    for name, data in sorted(screens.items()):
        screen_f = data.get("screen")
        tier = screen_f["tier"] if screen_f else 2
        platform = screen_f["detail"].get("platform", "unknown") if screen_f else ""
        status = screen_f["status"] if screen_f else "open"
        icon = "x" if status == "implemented" else " "

        lines.append(f"### [{icon}] {name} (T{tier}, {platform})")
        lines.append("")

        if screen_f:
            detail = screen_f.get("detail", {})
            lines.append(f"- **Dimensions**: {detail.get('width', '?')} x {detail.get('height', '?')}")
            lines.append(f"- **Elements**: {detail.get('child_count', 0)} nodes, depth {detail.get('depth', 0)}")

        screen_features = data.get("features", [])
        if screen_features:
            lines.append(f"- **Sub-features**: {len(screen_features)}")
            for sf in screen_features:
                sf_icon = "x" if sf["status"] == "implemented" else " "
                lines.append(f"  - [{sf_icon}] {sf['summary']}")

        lines.append("")

    # Components section
    if components:
        lines.append("## Design System Components")
        lines.append("")
        lines.append("| Component | Usage | Screens |")
        lines.append("|-----------|-------|---------|")
        for comp in sorted(components, key=lambda x: x["detail"].get("usage_count", 0), reverse=True):
            usage = comp["detail"].get("usage_count", 0)
            screen_list = ", ".join(comp["detail"].get("screens_used", [])[:3])
            if len(comp["detail"].get("screens_used", [])) > 3:
                screen_list += "..."
            lines.append(f"| {comp['name']} | {usage}x | {screen_list} |")
        lines.append("")

    return "\n".join(lines)
