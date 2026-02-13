"""UI complexity tier scoring system.

Classifies detected features into implementation complexity tiers:
- T1: Static pages (about, terms, settings) — auto-scaffold
- T2: Standard CRUD screens (forms, lists, detail views)
- T3: Complex interactive (timers, charts, scanners, builders)
- T4: Advanced (real-time data, animations, camera, device APIs)
"""

from __future__ import annotations

TIER_NAMES = {
    1: "Static",
    2: "Standard",
    3: "Complex",
    4: "Advanced",
}

TIER_DESCRIPTIONS = {
    1: "Static pages — auto-scaffold",
    2: "Standard CRUD screens",
    3: "Complex interactive features",
    4: "Advanced (real-time, device APIs)",
}

# Effort weights: higher tiers take more effort to implement
TIER_WEIGHTS = {1: 1, 2: 2, 3: 4, 4: 8}


def classify_screen_tier(feature_counts: dict[str, int]) -> int:
    """Classify a screen's implementation tier based on detected features.

    Args:
        feature_counts: dict mapping feature types to counts, e.g.:
            {"forms": 2, "lists": 1, "charts": 1, "camera": 0, ...}

    Returns:
        Tier 1-4
    """
    # T4 indicators: device APIs, real-time, animations
    t4_indicators = ["camera", "scanner", "map", "video", "realtime", "animation", "device_api"]
    if any(feature_counts.get(ind, 0) > 0 for ind in t4_indicators):
        return 4

    # T3 indicators: complex interactivity
    t3_indicators = ["charts", "timers", "builders", "drag_drop", "swipe", "tabs_complex"]
    if any(feature_counts.get(ind, 0) > 0 for ind in t3_indicators):
        return 3

    # T2 indicators: CRUD, forms, data display
    t2_indicators = ["forms", "lists", "cards", "crud", "detail_view", "modals", "tabs"]
    if any(feature_counts.get(ind, 0) > 0 for ind in t2_indicators):
        return 2

    # T1: static content only
    return 1


def compute_completion(features: list[dict]) -> dict:
    """Compute completion metrics from a list of features.

    Returns:
        {
            "total": int,
            "implemented": int,
            "deferred": int,
            "out_of_scope": int,
            "open": int,
            "pct": float,
            "by_tier": {1: {"total": N, "done": N}, ...},
            "effort_score": float,  # weighted by tier effort
        }
    """
    by_tier: dict[int, dict[str, int]] = {}
    total = implemented = deferred = out_of_scope = 0

    for f in features:
        tier = f.get("tier", 2)
        status = f.get("status", "open")
        ts = by_tier.setdefault(tier, {"total": 0, "done": 0})
        ts["total"] += 1
        total += 1
        if status == "implemented":
            implemented += 1
            ts["done"] += 1
        elif status == "deferred":
            deferred += 1
        elif status == "out_of_scope":
            out_of_scope += 1

    open_count = total - implemented - deferred - out_of_scope
    pct = round((implemented / total) * 100, 1) if total > 0 else 0.0

    # Effort-weighted completion
    total_effort = sum(
        TIER_WEIGHTS.get(tier, 2) * ts["total"]
        for tier, ts in by_tier.items()
    )
    done_effort = sum(
        TIER_WEIGHTS.get(tier, 2) * ts["done"]
        for tier, ts in by_tier.items()
    )
    effort_score = round((done_effort / total_effort) * 100, 1) if total_effort > 0 else 0.0

    return {
        "total": total,
        "implemented": implemented,
        "deferred": deferred,
        "out_of_scope": out_of_scope,
        "open": open_count,
        "pct": pct,
        "by_tier": by_tier,
        "effort_score": effort_score,
    }
