"""Interactive pattern detector: tabs, modals, accordions, swipe actions."""

from __future__ import annotations

from .base import BaseDetector
from ..pen_parser import PenDocument
from ..state import make_feature

_TAB_PATTERNS = ["tab", "segment", "tab_bar", "segmented_control"]
_MODAL_PATTERNS = ["modal", "dialog", "sheet", "bottom_sheet", "overlay", "popup", "alert"]
_ACCORDION_PATTERNS = ["accordion", "expandable", "collapsible", "dropdown_section"]
_SWIPE_PATTERNS = ["swipe", "swipeable", "slide_action", "dismiss"]
_DRAG_PATTERNS = ["drag", "reorder", "sortable", "draggable"]


class InteractiveDetector(BaseDetector):
    """Identifies interactive UI patterns: tabs, modals, accordions, swipe, drag."""

    name = "interactive"
    description = "Identifies interactive patterns (tabs, modals, accordions, drag-and-drop)"

    def detect(self, doc: PenDocument) -> list[dict]:
        features = []

        for screen in doc.screens:
            patterns_found: dict[str, list[str]] = {}

            for node in screen.walk():
                if not node.name:
                    continue
                name_lower = node.name.lower().replace(" ", "_").replace("-", "_")

                if any(p in name_lower for p in _TAB_PATTERNS):
                    patterns_found.setdefault("tabs", []).append(node.name)
                if any(p in name_lower for p in _MODAL_PATTERNS):
                    patterns_found.setdefault("modals", []).append(node.name)
                if any(p in name_lower for p in _ACCORDION_PATTERNS):
                    patterns_found.setdefault("accordions", []).append(node.name)
                if any(p in name_lower for p in _SWIPE_PATTERNS):
                    patterns_found.setdefault("swipe", []).append(node.name)
                if any(p in name_lower for p in _DRAG_PATTERNS):
                    patterns_found.setdefault("drag_drop", []).append(node.name)

            tier_map = {
                "tabs": 2,
                "modals": 2,
                "accordions": 2,
                "swipe": 3,
                "drag_drop": 3,
            }

            for pattern_type, instances in patterns_found.items():
                features.append(make_feature(
                    detector="interactive",
                    screen_id=screen.id,
                    name=f"{screen.name}::{pattern_type}",
                    tier=tier_map.get(pattern_type, 2),
                    category="interactive",
                    summary=f"Interactive: {pattern_type} in {screen.name} ({len(instances)} elements)",
                    detail={
                        "pattern": pattern_type,
                        "instances": instances,
                        "screen_name": screen.name,
                    },
                ))

        return features
