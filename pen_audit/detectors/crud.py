"""CRUD detector: identifies create/read/update/delete patterns."""

from __future__ import annotations

from .base import BaseDetector
from ..pen_parser import PenDocument
from ..state import make_feature

_CREATE_PATTERNS = ["add", "create", "new", "plus", "compose"]
_EDIT_PATTERNS = ["edit", "modify", "update", "pencil", "pen"]
_DELETE_PATTERNS = ["delete", "remove", "trash", "bin", "discard"]
_DETAIL_PATTERNS = ["detail", "view", "info", "profile", "preview"]
_EMPTY_STATE_PATTERNS = ["empty", "no_data", "no_items", "placeholder", "zero_state", "blank"]


class CrudDetector(BaseDetector):
    """Identifies CRUD patterns: add/create buttons, edit/delete affordances, detail views, empty states."""

    name = "crud"
    description = "Identifies CRUD patterns (create, read, update, delete)"

    def detect(self, doc: PenDocument) -> list[dict]:
        features = []

        for screen in doc.screens:
            crud_ops: dict[str, list[str]] = {}

            for node in screen.walk():
                if not node.name:
                    continue
                name_lower = node.name.lower().replace(" ", "_").replace("-", "_")

                if any(p in name_lower for p in _CREATE_PATTERNS):
                    crud_ops.setdefault("create", []).append(node.name)
                if any(p in name_lower for p in _EDIT_PATTERNS):
                    crud_ops.setdefault("edit", []).append(node.name)
                if any(p in name_lower for p in _DELETE_PATTERNS):
                    crud_ops.setdefault("delete", []).append(node.name)
                if any(p in name_lower for p in _DETAIL_PATTERNS):
                    crud_ops.setdefault("detail", []).append(node.name)
                if any(p in name_lower for p in _EMPTY_STATE_PATTERNS):
                    crud_ops.setdefault("empty_state", []).append(node.name)

            # Also scan text content
            texts = screen.find_text_content()
            for text in texts:
                text_lower = text.lower()
                if any(p in text_lower for p in ["add ", "create ", "new "]):
                    crud_ops.setdefault("create", []).append(f"text: {text[:30]}")
                if any(p in text_lower for p in ["no items", "nothing here", "get started", "empty"]):
                    crud_ops.setdefault("empty_state", []).append(f"text: {text[:30]}")

            if crud_ops:
                ops_summary = ", ".join(f"{k}({len(v)})" for k, v in crud_ops.items())
                features.append(make_feature(
                    detector="crud",
                    screen_id=screen.id,
                    name=f"{screen.name}::crud",
                    tier=2,
                    category="crud",
                    summary=f"CRUD: {ops_summary} in {screen.name}",
                    detail={
                        "operations": crud_ops,
                        "screen_name": screen.name,
                    },
                ))

        return features
