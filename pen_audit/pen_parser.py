"""Parser for .pen file JSON node trees.

.pen files are encrypted at rest and must be read via Pencil MCP tools.
This module works on the deserialized JSON node tree (exported via batch_get).

The parser can accept:
1. A JSON file containing the full node tree (exported from Pencil MCP)
2. A dict already loaded into memory

Node types in .pen files:
- frame: containers, screens, cards, rows
- text: labels, headings, body text
- ellipse: rings, avatars, indicators
- rectangle: backgrounds, dividers
- ref: component instances (references reusable components)
- path: icons, custom shapes
- image: image fills on frames
- icon_font: icon font glyphs
- line: lines, dividers
- polygon: custom shapes
- connection: connectors between nodes
- note: annotation notes
- group: groups of nodes
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class PenNode:
    """Represents a node in the .pen file tree."""
    id: str
    type: str
    name: str = ""
    children: list["PenNode"] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    reusable: bool = False

    @property
    def is_screen(self) -> bool:
        """Top-level frames that look like screens (not components)."""
        return self.type == "frame" and not self.reusable

    @property
    def is_component(self) -> bool:
        """Reusable design system components."""
        return self.reusable

    @property
    def is_instance(self) -> bool:
        """Component instances (ref nodes)."""
        return self.type == "ref"

    def walk(self):
        """Yield all nodes in the subtree (DFS)."""
        yield self
        for child in self.children:
            yield from child.walk()

    def find_by_type(self, node_type: str) -> list["PenNode"]:
        """Find all descendant nodes of a given type."""
        return [n for n in self.walk() if n.type == node_type]

    def find_by_name(self, pattern: str) -> list["PenNode"]:
        """Find all descendant nodes whose name contains the pattern (case-insensitive)."""
        pattern_lower = pattern.lower()
        return [n for n in self.walk() if pattern_lower in n.name.lower()]

    def find_text_content(self) -> list[str]:
        """Extract all text content from descendant text nodes."""
        texts = []
        for n in self.walk():
            if n.type == "text":
                content = n.properties.get("content", "")
                if content:
                    texts.append(content)
        return texts

    def count_by_type(self) -> dict[str, int]:
        """Count all node types in the subtree."""
        counts: dict[str, int] = {}
        for n in self.walk():
            counts[n.type] = counts.get(n.type, 0) + 1
        return counts

    def depth(self) -> int:
        """Maximum depth of the subtree."""
        if not self.children:
            return 0
        return 1 + max(child.depth() for child in self.children)


@dataclass
class PenDocument:
    """Represents a parsed .pen document."""
    root: PenNode
    source_file: str = ""

    @property
    def screens(self) -> list[PenNode]:
        """Top-level frames (screens)."""
        return [c for c in self.root.children if c.is_screen]

    @property
    def components(self) -> list[PenNode]:
        """Reusable design system components."""
        components = []
        for node in self.root.walk():
            if node.is_component:
                components.append(node)
        return components

    @property
    def all_instances(self) -> list[PenNode]:
        """All component instances (ref nodes) across all screens."""
        return [n for n in self.root.walk() if n.is_instance]


def _parse_node(data: dict) -> PenNode:
    """Recursively parse a raw JSON node dict into a PenNode."""
    children = []
    raw_children = data.get("children", [])
    if isinstance(raw_children, list):
        for child_data in raw_children:
            if isinstance(child_data, dict):
                children.append(_parse_node(child_data))

    # Extract known properties, pass the rest through
    node_id = data.get("id", "")
    node_type = data.get("type", "frame")
    name = data.get("name", "")
    reusable = data.get("reusable", False)

    # Collect all other properties
    skip_keys = {"id", "type", "name", "children", "reusable"}
    properties = {k: v for k, v in data.items() if k not in skip_keys}

    return PenNode(
        id=node_id,
        type=node_type,
        name=name,
        children=children,
        properties=properties,
        reusable=reusable,
    )


def parse_pen_json(data: dict) -> PenDocument:
    """Parse a .pen JSON structure into a PenDocument."""
    root = _parse_node(data)
    return PenDocument(root=root)


def load_pen_file(path: str | Path) -> PenDocument:
    """Load and parse a .pen JSON export file.

    NOTE: Raw .pen files are encrypted. This expects a JSON export
    created by exporting via Pencil MCP's batch_get tool.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(p) as f:
        data = json.load(f)

    doc = parse_pen_json(data)
    doc.source_file = str(p)
    return doc
