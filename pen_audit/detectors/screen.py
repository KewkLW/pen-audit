"""Screen detector: identifies top-level frames as screens."""

from __future__ import annotations

from .base import BaseDetector
from ..pen_parser import PenDocument, PenNode
from ..state import make_feature
from ..scoring import classify_screen_tier


# Names that indicate design system containers, not screens
_SYSTEM_NAMES = {
    "design system", "components", "symbols", "tokens", "colors",
    "typography", "icons", "library", "assets", "styles",
}

# Common dimension patterns for mobile/desktop/tablet
_MOBILE_WIDTHS = range(320, 430)
_TABLET_WIDTHS = range(700, 850)
_DESKTOP_WIDTHS = range(1200, 1600)


def _detect_platform(node: PenNode) -> str:
    """Detect target platform from frame dimensions."""
    w = node.properties.get("width", 0)
    if isinstance(w, (int, float)):
        if w in _MOBILE_WIDTHS or (360 <= w <= 414):
            return "mobile"
        if w in _TABLET_WIDTHS or (768 <= w <= 834):
            return "tablet"
        if w >= 1200:
            return "desktop"
    return "unknown"


def _count_features(node: PenNode) -> dict[str, int]:
    """Count feature types in a screen's subtree for tier classification."""
    counts: dict[str, int] = {}
    type_counts = node.count_by_type()

    # Text nodes suggest static content
    counts["text_nodes"] = type_counts.get("text", 0)

    # Ref nodes suggest component usage
    counts["ref_nodes"] = type_counts.get("ref", 0)

    # Look for specific patterns in descendant names and content
    for n in node.walk():
        name_lower = n.name.lower() if n.name else ""
        texts = " ".join(n.find_text_content()).lower() if n.type == "frame" else ""
        combined = name_lower + " " + texts

        # Forms
        if any(k in name_lower for k in ["input", "field", "text_field", "search", "form"]):
            counts["forms"] = counts.get("forms", 0) + 1

        # Lists
        if any(k in name_lower for k in ["list", "row", "item", "cell"]):
            counts["lists"] = counts.get("lists", 0) + 1

        # Cards
        if "card" in name_lower:
            counts["cards"] = counts.get("cards", 0) + 1

        # Charts/visualizations
        if any(k in name_lower for k in ["chart", "graph", "ring", "progress", "donut"]):
            counts["charts"] = counts.get("charts", 0) + 1

        # Tabs
        if any(k in name_lower for k in ["tab", "segment"]):
            counts["tabs"] = counts.get("tabs", 0) + 1

        # Modals/sheets
        if any(k in name_lower for k in ["modal", "sheet", "dialog", "overlay", "popup"]):
            counts["modals"] = counts.get("modals", 0) + 1

        # Camera/scanner
        if any(k in name_lower for k in ["camera", "scanner", "barcode", "qr"]):
            counts["camera"] = counts.get("camera", 0) + 1
            counts["scanner"] = counts.get("scanner", 0) + 1

        # Timer/stopwatch
        if any(k in name_lower for k in ["timer", "stopwatch", "countdown"]):
            counts["timers"] = counts.get("timers", 0) + 1

        # Map
        if "map" in name_lower:
            counts["map"] = counts.get("map", 0) + 1

        # CRUD buttons
        if any(k in combined for k in ["add", "create", "new", "edit", "delete", "remove"]):
            counts["crud"] = counts.get("crud", 0) + 1

        # Drag/reorder
        if any(k in name_lower for k in ["drag", "reorder", "sortable"]):
            counts["drag_drop"] = counts.get("drag_drop", 0) + 1

        # Builder pattern
        if "builder" in name_lower:
            counts["builders"] = counts.get("builders", 0) + 1

    return counts


class ScreenDetector(BaseDetector):
    """Identifies top-level frames as screens and classifies their complexity."""

    name = "screen"
    description = "Identifies screens (top-level frames) and their complexity tier"

    def detect(self, doc: PenDocument) -> list[dict]:
        features = []

        for screen in doc.root.children:
            if screen.type != "frame":
                continue

            # Skip design system containers
            if screen.name and screen.name.lower() in _SYSTEM_NAMES:
                continue
            if screen.reusable:
                continue

            # Detect platform and features
            platform = _detect_platform(screen)
            feature_counts = _count_features(screen)
            tier = classify_screen_tier(feature_counts)

            # Extract text content for description
            texts = screen.find_text_content()
            heading = texts[0] if texts else screen.name

            # Count child elements
            child_count = sum(1 for _ in screen.walk()) - 1  # exclude self
            depth = screen.depth()

            features.append(make_feature(
                detector="screen",
                screen_id=screen.id,
                name=screen.name or screen.id,
                tier=tier,
                category="screen",
                summary=f"Screen: {screen.name or screen.id} ({platform}, T{tier})",
                detail={
                    "platform": platform,
                    "width": screen.properties.get("width"),
                    "height": screen.properties.get("height"),
                    "heading": heading,
                    "child_count": child_count,
                    "depth": depth,
                    "feature_counts": feature_counts,
                    "node_types": screen.count_by_type(),
                },
            ))

        return features
