"""Test skeleton generator: creates Playwright E2E test stubs from detected screens."""

from __future__ import annotations

import re


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def _test_id(name: str) -> str:
    """Generate a test-friendly identifier."""
    return re.sub(r'[^a-zA-Z0-9]', '_', name).strip('_').lower()


def generate_test_skeletons(state: dict) -> list[dict]:
    """Generate Playwright E2E test skeletons from detected screens.

    Returns list of dicts with:
    - path: str (file path for the test)
    - content: str (test file content)
    - screen_name: str
    - tier: int
    """
    features = list(state.get("features", {}).values())
    tests = []

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
        tid = _test_id(name)
        tier = screen_f["tier"]
        sub_features = data["sub_features"]

        lines = [
            f'import {{ test, expect }} from "@playwright/test";',
            f'import {{ auth }} from "./helpers/auth";',
            '',
            f'test.describe("{name}", () => {{',
            f'  test.beforeEach(async ({{ page }}) => {{',
            f'    await auth(page);',
            f'    await page.goto("/app/{slug}");',
            f'  }});',
            '',
            f'  test("renders screen header", async ({{ page }}) => {{',
            f'    await expect(page.getByRole("heading", {{ name: "{name}" }})).toBeVisible();',
            f'  }});',
            '',
        ]

        # Generate test stubs for each sub-feature
        for sf in sub_features:
            det = sf["detector"]
            if det == "navigation":
                pattern = sf["detail"].get("pattern_type", "nav")
                lines.extend([
                    f'  test("has {pattern} navigation", async ({{ page }}) => {{',
                    f'    // TODO: verify {pattern} elements',
                    f'    test.skip(); // stub',
                    f'  }});',
                    '',
                ])
            elif det == "form":
                count = sf["detail"].get("input_count", 0)
                input_types = sf["detail"].get("input_types", [])
                lines.extend([
                    f'  test("renders form with {count} inputs", async ({{ page }}) => {{',
                    f'    // Input types: {", ".join(input_types)}',
                    f'    // TODO: verify form inputs render',
                    f'    test.skip(); // stub',
                    f'  }});',
                    '',
                    f'  test("validates form inputs", async ({{ page }}) => {{',
                    f'    // TODO: test validation rules',
                    f'    test.skip(); // stub',
                    f'  }});',
                    '',
                ])
            elif det == "data_display":
                pattern = sf["detail"].get("pattern", "data")
                lines.extend([
                    f'  test("displays {pattern} data", async ({{ page }}) => {{',
                    f'    // TODO: verify {pattern} renders with data',
                    f'    test.skip(); // stub',
                    f'  }});',
                    '',
                ])
            elif det == "crud":
                ops = sf["detail"].get("operations", {})
                for op in ops:
                    lines.extend([
                        f'  test("supports {op} operation", async ({{ page }}) => {{',
                        f'    // TODO: test {op} flow',
                        f'    test.skip(); // stub',
                        f'  }});',
                        '',
                    ])
            elif det == "interactive":
                pattern = sf["detail"].get("pattern", "interactive")
                lines.extend([
                    f'  test("{pattern} interaction works", async ({{ page }}) => {{',
                    f'    // TODO: test {pattern} behavior',
                    f'    test.skip(); // stub',
                    f'  }});',
                    '',
                ])

        lines.append('});')
        lines.append('')

        test_path = f"e2e/{tid}.spec.ts"

        tests.append({
            "path": test_path,
            "content": '\n'.join(lines),
            "screen_name": name,
            "tier": tier,
        })

    return sorted(tests, key=lambda t: t["path"])
