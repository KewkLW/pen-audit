"""Component detector: identifies design system components and their usage."""

from __future__ import annotations
from collections import Counter

from .base import BaseDetector
from ..pen_parser import PenDocument, PenNode
from ..state import make_feature


class ComponentDetector(BaseDetector):
    """Identifies reusable components and maps their usage across screens."""

    name = "component"
    description = "Identifies design system components and tracks instance usage"

    def detect(self, doc: PenDocument) -> list[dict]:
        features = []

        # Find all reusable components (design system)
        components = doc.components
        component_ids = {c.id for c in components}

        # Find all instances (ref nodes) and count usage
        usage_counter: Counter[str] = Counter()
        instance_locations: dict[str, list[str]] = {}  # ref_id -> [screen_names]

        for screen in doc.screens:
            for node in screen.walk():
                if node.type == "ref":
                    ref_id = node.properties.get("ref", "")
                    if ref_id:
                        usage_counter[ref_id] += 1
                        locs = instance_locations.setdefault(ref_id, [])
                        if screen.name and screen.name not in locs:
                            locs.append(screen.name)

        # Report each component with usage stats
        for comp in components:
            usage = usage_counter.get(comp.id, 0)
            screens_used = instance_locations.get(comp.id, [])

            features.append(make_feature(
                detector="component",
                screen_id=comp.id,
                name=comp.name or comp.id,
                tier=1,  # Components themselves are T1 (they exist already)
                category="component",
                summary=f"Component: {comp.name or comp.id} (used {usage}x across {len(screens_used)} screens)",
                detail={
                    "usage_count": usage,
                    "screens_used": screens_used,
                    "child_count": sum(1 for _ in comp.walk()) - 1,
                    "node_types": comp.count_by_type(),
                },
            ))

        return features
