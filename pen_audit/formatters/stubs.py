"""Stub generator: creates Next.js App Router page stubs from detected screens."""

from __future__ import annotations

import re


def _slugify(name: str) -> str:
    """Convert screen name to URL path segment."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def _component_name(name: str) -> str:
    """Convert screen name to PascalCase component name."""
    parts = re.sub(r'[^a-zA-Z0-9\s]', '', name).split()
    result = ''.join(p.capitalize() for p in parts) or 'Page'
    # Ensure it doesn't start with a digit
    if result[0].isdigit():
        result = 'X' + result
    return result


def generate_stubs(state: dict, app_dir: str = "app") -> list[dict]:
    """Generate Next.js App Router page stubs from detected screens.

    Returns list of dicts with:
    - path: str (file path relative to app dir)
    - content: str (page.tsx content)
    - screen_name: str
    - tier: int
    """
    features = list(state.get("features", {}).values())
    stubs = []

    # Collect screen features with their sub-features
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

        slug = _slugify(name)
        comp = _component_name(name)
        tier = screen_f["tier"]
        platform = screen_f["detail"].get("platform", "unknown")
        sub_features = data["sub_features"]

        # Build the page content
        imports = ['"use client";', '', 'import { ScreenHeader } from "@/components/screen-header";']

        # Detect what imports might be needed
        detectors_used = set(sf["detector"] for sf in sub_features)
        if "form" in detectors_used:
            imports.append('// TODO: import form components')
        if "data_display" in detectors_used:
            imports.append('// TODO: import data display components')
        if "interactive" in detectors_used:
            imports.append('// TODO: import interactive components')

        # Build component body
        body_parts = []
        body_parts.append(f'  // Tier {tier} screen — {platform}')
        body_parts.append(f'  // Pen node ID: {screen_f["screen_id"]}')

        # Add TODO comments for each sub-feature
        if sub_features:
            body_parts.append('')
            body_parts.append('  // Detected features:')
            for sf in sub_features:
                body_parts.append(f'  // - [{sf["detector"]}] {sf["summary"]}')

        # Build JSX
        jsx_parts = ['    <div className="flex flex-col min-h-screen">']
        jsx_parts.append(f'      <ScreenHeader title="{name}" />')
        jsx_parts.append(f'      <main className="flex-1 p-4">')

        # Add placeholder sections based on sub-features
        for sf in sub_features:
            det = sf["detector"]
            if det == "navigation":
                pattern = sf["detail"].get("pattern_type", "nav")
                jsx_parts.append(f'        {{/* TODO: {pattern} navigation */}}')
            elif det == "form":
                count = sf["detail"].get("input_count", 0)
                jsx_parts.append(f'        {{/* TODO: form with {count} inputs */}}')
            elif det == "data_display":
                pattern = sf["detail"].get("pattern", "data")
                instances = sf["detail"].get("instances", [])
                jsx_parts.append(f'        {{/* TODO: {pattern} display ({len(instances)} items) */}}')
            elif det == "crud":
                ops = sf["detail"].get("operations", {})
                jsx_parts.append(f'        {{/* TODO: CRUD operations: {", ".join(ops.keys())} */}}')
            elif det == "interactive":
                pattern = sf["detail"].get("pattern", "interactive")
                jsx_parts.append(f'        {{/* TODO: {pattern} interaction */}}')

        if not sub_features:
            jsx_parts.append(f'        <p className="text-muted-foreground">Coming Soon</p>')

        jsx_parts.append(f'      </main>')
        jsx_parts.append(f'    </div>')

        # Assemble
        content_lines = imports + ['', '', f'export default function {comp}Page() {{']
        content_lines.extend(body_parts)
        content_lines.append('')
        content_lines.append('  return (')
        content_lines.extend(jsx_parts)
        content_lines.append('  );')
        content_lines.append('}')
        content_lines.append('')

        file_path = f"{app_dir}/app/{slug}/page.tsx"

        stubs.append({
            "path": file_path,
            "content": '\n'.join(content_lines),
            "screen_name": name,
            "tier": tier,
        })

    return sorted(stubs, key=lambda s: s["path"])
