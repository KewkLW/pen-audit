"""Data display detector: identifies lists, cards, charts, and tables."""

from __future__ import annotations

from .base import BaseDetector
from ..pen_parser import PenDocument, PenNode
from ..state import make_feature

_LIST_PATTERNS = ["list", "row", "item", "cell", "feed", "timeline"]
_CARD_PATTERNS = ["card", "tile", "panel", "widget", "stat_card", "info_card"]
_CHART_PATTERNS = [
    "chart", "graph", "ring", "donut", "progress", "sparkline",
    "bar_chart", "line_chart", "pie", "gauge", "meter",
]
_TABLE_PATTERNS = ["table", "grid", "spreadsheet", "data_grid"]


class DataDisplayDetector(BaseDetector):
    """Identifies data display patterns: lists, cards, charts, tables."""

    name = "data_display"
    description = "Identifies data display patterns (lists, cards, charts, tables)"

    def detect(self, doc: PenDocument) -> list[dict]:
        features = []

        for screen in doc.screens:
            lists_found: list[str] = []
            cards_found: list[str] = []
            charts_found: list[str] = []
            tables_found: list[str] = []

            for node in screen.walk():
                if not node.name:
                    continue
                name_lower = node.name.lower().replace(" ", "_").replace("-", "_")

                if any(p in name_lower for p in _LIST_PATTERNS):
                    lists_found.append(node.name)
                if any(p in name_lower for p in _CARD_PATTERNS):
                    cards_found.append(node.name)
                if any(p in name_lower for p in _CHART_PATTERNS):
                    charts_found.append(node.name)
                if any(p in name_lower for p in _TABLE_PATTERNS):
                    tables_found.append(node.name)

            if lists_found:
                features.append(make_feature(
                    detector="data_display",
                    screen_id=screen.id,
                    name=f"{screen.name}::lists",
                    tier=2,
                    category="data_display",
                    summary=f"Lists: {len(lists_found)} in {screen.name}",
                    detail={"pattern": "list", "instances": lists_found, "screen_name": screen.name},
                ))

            if cards_found:
                features.append(make_feature(
                    detector="data_display",
                    screen_id=screen.id,
                    name=f"{screen.name}::cards",
                    tier=2,
                    category="data_display",
                    summary=f"Cards: {len(cards_found)} in {screen.name}",
                    detail={"pattern": "card", "instances": cards_found, "screen_name": screen.name},
                ))

            if charts_found:
                features.append(make_feature(
                    detector="data_display",
                    screen_id=screen.id,
                    name=f"{screen.name}::charts",
                    tier=3,
                    category="data_display",
                    summary=f"Charts: {len(charts_found)} in {screen.name}",
                    detail={"pattern": "chart", "instances": charts_found, "screen_name": screen.name},
                ))

            if tables_found:
                features.append(make_feature(
                    detector="data_display",
                    screen_id=screen.id,
                    name=f"{screen.name}::tables",
                    tier=3,
                    category="data_display",
                    summary=f"Tables: {len(tables_found)} in {screen.name}",
                    detail={"pattern": "table", "instances": tables_found, "screen_name": screen.name},
                ))

        return features
