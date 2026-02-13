"""Tests for output formatters."""

from pen_audit.pen_parser import parse_pen_json
from pen_audit.detectors import run_all_detectors
from pen_audit.state import _empty_state, merge_scan
from pen_audit.formatters.markdown import generate_markdown
from pen_audit.formatters.routes import generate_routes
from pen_audit.formatters.jira import generate_jira_tasks
from pen_audit.formatters.stubs import generate_stubs, _component_name
from pen_audit.formatters.tests import generate_test_skeletons


def _make_state() -> dict:
    """Create a state with sample scan data."""
    doc = parse_pen_json({
        "id": "root",
        "type": "frame",
        "name": "Document",
        "children": [
            {
                "id": "food_log",
                "type": "frame",
                "name": "Food Log",
                "width": 390,
                "height": 844,
                "children": [
                    {"id": "h1", "type": "frame", "name": "header", "children": [
                        {"id": "t1", "type": "text", "content": "Food Log"},
                        {"id": "b1", "type": "frame", "name": "back_button"},
                    ]},
                    {"id": "ml", "type": "frame", "name": "mealList", "children": [
                        {"id": "r1", "type": "frame", "name": "breakfastRow"},
                        {"id": "r2", "type": "frame", "name": "lunchRow"},
                    ]},
                    {"id": "ab", "type": "frame", "name": "addFoodButton", "children": [
                        {"id": "at", "type": "text", "content": "Add Food"},
                    ]},
                ],
            },
            {
                "id": "settings",
                "type": "frame",
                "name": "Settings",
                "width": 390,
                "height": 844,
                "children": [
                    {"id": "sh", "type": "frame", "name": "header"},
                    {"id": "tog", "type": "frame", "name": "darkModeToggle"},
                ],
            },
        ],
    })

    features = run_all_detectors(doc)
    state = _empty_state()
    merge_scan(state, features, source_file="test.json")
    return state


def test_markdown_formatter():
    state = _make_state()
    md = generate_markdown(state)
    assert "# Feature Inventory" in md
    assert "Food Log" in md
    assert "Settings" in md
    assert "| Tier |" in md


def test_routes_formatter():
    state = _make_state()
    routes = generate_routes(state)
    assert routes["generated_by"] == "pen-audit"
    assert len(routes["routes"]) >= 2
    paths = [r["path"] for r in routes["routes"]]
    assert "/app/food-log" in paths
    assert "/app/settings" in paths


def test_routes_have_platforms():
    state = _make_state()
    routes = generate_routes(state)
    for route in routes["routes"]:
        assert "platforms" in route
        assert isinstance(route["platforms"], list)
        assert len(route["platforms"]) > 0


def test_jira_formatter():
    state = _make_state()
    tasks = generate_jira_tasks(state)
    assert len(tasks) >= 2
    summaries = [t["summary"] for t in tasks]
    assert any("Food Log" in s for s in summaries)
    assert any("Settings" in s for s in summaries)

    # Check ADF structure
    for task in tasks:
        desc = task["description"]
        assert desc["version"] == 1
        assert desc["type"] == "doc"
        assert len(desc["content"]) > 0


def test_jira_tasks_have_labels():
    state = _make_state()
    tasks = generate_jira_tasks(state)
    for task in tasks:
        assert "pen-audit" in task["labels"]
        assert any(l.startswith("tier-") for l in task["labels"])


def test_stubs_formatter():
    state = _make_state()
    stubs = generate_stubs(state)
    assert len(stubs) >= 2
    paths = [s["path"] for s in stubs]
    assert any("food-log" in p for p in paths)
    assert any("settings" in p for p in paths)

    # Check content is valid-ish TSX
    for stub in stubs:
        assert '"use client";' in stub["content"]
        assert "ScreenHeader" in stub["content"]
        assert "export default function" in stub["content"]


def test_stubs_component_name_numeric_prefix():
    assert _component_name("1RM Calculator") == "X1rmCalculator"
    assert _component_name("Food Log") == "FoodLog"
    assert _component_name("Settings") == "Settings"


def test_test_skeletons():
    state = _make_state()
    tests = generate_test_skeletons(state)
    assert len(tests) >= 2

    for tf in tests:
        assert tf["path"].endswith(".spec.ts")
        assert "test.describe" in tf["content"]
        assert "renders screen header" in tf["content"]


def test_test_skeletons_have_crud_tests():
    state = _make_state()
    tests = generate_test_skeletons(state)
    food_log_tests = [t for t in tests if t["screen_name"] == "Food Log"]
    assert len(food_log_tests) == 1
    content = food_log_tests[0]["content"]
    # Food Log has CRUD (addFoodButton), so should have CRUD test stub
    assert "create" in content.lower()
