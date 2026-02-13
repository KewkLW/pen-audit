"""Jira formatter: generates Jira ADF task descriptions from detected features."""

from __future__ import annotations

from ..scoring import TIER_NAMES, TIER_DESCRIPTIONS


def _adf_paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _adf_heading(text: str, level: int = 3) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}


def _adf_bullet_list(items: list[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [_adf_paragraph(item)],
            }
            for item in items
        ],
    }


def _adf_status(text: str, color: str = "neutral") -> dict:
    """Inline status lozenge."""
    return {
        "type": "status",
        "attrs": {"text": text, "color": color},
    }


def generate_jira_tasks(state: dict) -> list[dict]:
    """Generate Jira-ready task payloads from state.

    Returns a list of dicts, each with:
    - summary: str (Jira issue title)
    - description: dict (ADF document)
    - labels: list[str]
    - tier: int
    - screen_name: str
    - pen_node_id: str
    """
    features = list(state.get("features", {}).values())
    tasks = []

    # Group features by screen
    screens: dict[str, dict] = {}
    for f in features:
        if f["category"] == "screen":
            screens[f["name"]] = {"screen": f, "sub_features": []}

    for f in features:
        if f["category"] != "screen":
            screen_name = f["detail"].get("screen_name", "Unknown")
            if screen_name in screens:
                screens[screen_name]["sub_features"].append(f)

    for name, data in screens.items():
        screen_f = data["screen"]
        if screen_f["status"] != "open":
            continue

        tier = screen_f["tier"]
        platform = screen_f["detail"].get("platform", "unknown")
        node_id = screen_f["screen_id"]
        sub_features = data["sub_features"]

        # Build ADF description
        adf_content = []

        # Overview
        adf_content.append(_adf_heading(f"Screen: {name}", 2))
        adf_content.append(_adf_paragraph(
            f"Tier {tier} ({TIER_DESCRIPTIONS.get(tier, '?')}) — {platform} platform"
        ))

        # Dimensions and stats
        detail = screen_f.get("detail", {})
        adf_content.append(_adf_heading("Specifications", 3))
        specs = [
            f"Dimensions: {detail.get('width', '?')} x {detail.get('height', '?')}",
            f"Elements: {detail.get('child_count', 0)} nodes",
            f"Tree depth: {detail.get('depth', 0)}",
            f"Pen node ID: {node_id}",
        ]
        adf_content.append(_adf_bullet_list(specs))

        # Sub-features as acceptance criteria
        if sub_features:
            adf_content.append(_adf_heading("Acceptance Criteria", 3))
            criteria = []
            for sf in sub_features:
                criteria.append(f"[{sf['detector']}] {sf['summary']}")
            adf_content.append(_adf_bullet_list(criteria))

        # Feature counts
        fc = detail.get("feature_counts", {})
        if fc:
            adf_content.append(_adf_heading("Detected Patterns", 3))
            patterns = [f"{k}: {v}" for k, v in sorted(fc.items()) if v > 0]
            if patterns:
                adf_content.append(_adf_bullet_list(patterns))

        # Labels
        labels = [f"tier-{tier}", f"platform-{platform}", "pen-audit"]
        for sf in sub_features:
            labels.append(f"has-{sf['detector']}")
        labels = sorted(set(labels))

        tasks.append({
            "summary": f"[T{tier}] Implement {name} screen ({platform})",
            "description": {"version": 1, "type": "doc", "content": adf_content},
            "labels": labels,
            "tier": tier,
            "screen_name": name,
            "pen_node_id": node_id,
            "sub_feature_count": len(sub_features),
        })

    return sorted(tasks, key=lambda t: (t["tier"], t["screen_name"]))
