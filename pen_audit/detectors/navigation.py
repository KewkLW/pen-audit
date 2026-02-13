"""Navigation detector: identifies navigation patterns in screens."""

from __future__ import annotations

from .base import BaseDetector
from ..pen_parser import PenDocument, PenNode
from ..state import make_feature

# Common navigation element names
_NAV_PATTERNS = {
    "tab_bar": ["tabbar", "tab_bar", "bottom_nav", "bottomnav", "navigation_bar", "navbar"],
    "sidebar": ["sidebar", "side_nav", "sidenav", "drawer", "nav_drawer"],
    "back_button": ["back", "back_button", "back_arrow", "chevron_left", "arrow_left"],
    "header": ["header", "topbar", "top_bar", "app_bar", "appbar", "screen_header"],
    "breadcrumb": ["breadcrumb", "bread_crumb"],
}


def _match_nav_pattern(name: str) -> str | None:
    """Check if a node name matches any navigation pattern."""
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    for pattern_type, keywords in _NAV_PATTERNS.items():
        if any(kw in name_lower for kw in keywords):
            return pattern_type
    return None


class NavigationDetector(BaseDetector):
    """Identifies navigation patterns (tab bars, sidebars, back buttons, headers)."""

    name = "navigation"
    description = "Identifies navigation UI patterns"

    def detect(self, doc: PenDocument) -> list[dict]:
        features = []

        for screen in doc.screens:
            nav_found: dict[str, list[str]] = {}  # pattern_type -> [node_names]

            for node in screen.walk():
                if not node.name:
                    continue
                pattern = _match_nav_pattern(node.name)
                if pattern:
                    nav_found.setdefault(pattern, []).append(node.name)

            # Also check text content for navigation-like elements
            texts = screen.find_text_content()
            tab_labels = [t for t in texts if len(t) < 20]  # Short labels are likely nav items

            for pattern_type, instances in nav_found.items():
                features.append(make_feature(
                    detector="navigation",
                    screen_id=screen.id,
                    name=f"{screen.name}::{pattern_type}",
                    tier=1 if pattern_type in ("header", "back_button") else 2,
                    category="navigation",
                    summary=f"Nav: {pattern_type} in {screen.name} ({len(instances)} elements)",
                    detail={
                        "pattern_type": pattern_type,
                        "instances": instances,
                        "screen_name": screen.name,
                    },
                ))

        return features
