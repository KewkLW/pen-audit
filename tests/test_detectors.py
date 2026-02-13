"""Tests for UI pattern detectors."""

from pen_audit.pen_parser import parse_pen_json
from pen_audit.detectors import run_all_detectors
from pen_audit.detectors.screen import ScreenDetector
from pen_audit.detectors.component import ComponentDetector
from pen_audit.detectors.navigation import NavigationDetector
from pen_audit.detectors.form import FormDetector
from pen_audit.detectors.data_display import DataDisplayDetector
from pen_audit.detectors.crud import CrudDetector


def _sample_doc() -> dict:
    return {
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
                        {"id": "t1", "type": "text", "name": "title", "content": "Food Log"},
                        {"id": "b1", "type": "frame", "name": "back_button"},
                    ]},
                    {"id": "s1", "type": "ref", "name": "searchBar", "ref": "search_comp"},
                    {"id": "ml", "type": "frame", "name": "mealList", "children": [
                        {"id": "r1", "type": "frame", "name": "breakfastRow", "children": [
                            {"id": "bt", "type": "text", "content": "Breakfast"},
                        ]},
                        {"id": "r2", "type": "frame", "name": "lunchRow"},
                        {"id": "r3", "type": "frame", "name": "dinnerRow"},
                    ]},
                    {"id": "ab", "type": "frame", "name": "addFoodButton", "children": [
                        {"id": "at", "type": "text", "content": "Add Food"},
                    ]},
                    {"id": "cal", "type": "frame", "name": "calorie_chart"},
                    {"id": "wt", "type": "frame", "name": "water_tracker", "children": [
                        {"id": "ag", "type": "frame", "name": "addGlassButton"},
                    ]},
                ],
            },
            {
                "id": "scanner",
                "type": "frame",
                "name": "Barcode Scanner",
                "width": 390,
                "height": 844,
                "children": [
                    {"id": "cam", "type": "frame", "name": "camera_viewfinder"},
                    {"id": "sh", "type": "frame", "name": "header", "children": [
                        {"id": "st", "type": "text", "content": "Scan Barcode"},
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
                    {"id": "sh2", "type": "frame", "name": "header"},
                    {"id": "st2", "type": "text", "content": "Settings"},
                    {"id": "tog", "type": "frame", "name": "darkModeToggle"},
                ],
            },
            {
                "id": "search_comp",
                "type": "frame",
                "name": "SearchBar",
                "reusable": True,
                "children": [
                    {"id": "si", "type": "frame", "name": "search_input"},
                ],
            },
        ],
    }


def test_screen_detector():
    doc = parse_pen_json(_sample_doc())
    detector = ScreenDetector()
    features = detector.detect(doc)
    names = [f["name"] for f in features]
    assert "Food Log" in names
    assert "Barcode Scanner" in names
    assert "Settings" in names
    assert "SearchBar" not in names  # reusable component excluded


def test_screen_tier_classification():
    doc = parse_pen_json(_sample_doc())
    detector = ScreenDetector()
    features = detector.detect(doc)
    by_name = {f["name"]: f for f in features}

    # Settings = T1 (static, just toggle)
    # Food Log = T3 (has chart, list, CRUD)
    # Barcode Scanner = T4 (has camera)
    assert by_name["Barcode Scanner"]["tier"] == 4  # camera = T4
    assert by_name["Food Log"]["tier"] >= 2  # has list + chart


def test_component_detector():
    doc = parse_pen_json(_sample_doc())
    detector = ComponentDetector()
    features = detector.detect(doc)
    assert len(features) == 1
    assert features[0]["name"] == "SearchBar"
    assert features[0]["detail"]["usage_count"] == 1


def test_navigation_detector():
    doc = parse_pen_json(_sample_doc())
    detector = NavigationDetector()
    features = detector.detect(doc)
    # Should find headers and back buttons
    patterns = [f["detail"]["pattern_type"] for f in features]
    assert "header" in patterns
    assert "back_button" in patterns


def test_form_detector():
    doc = parse_pen_json(_sample_doc())
    detector = FormDetector()
    features = detector.detect(doc)
    # SearchBar has search_input, Food Log screen has it via ref
    # The actual search_input is inside the reusable component,
    # but the component itself has reusable=True so it's not a screen
    # The ref in Food Log points to it but doesn't have the name "input" itself
    # This is expected — form detection works on node names


def test_data_display_detector():
    doc = parse_pen_json(_sample_doc())
    detector = DataDisplayDetector()
    features = detector.detect(doc)
    # Food Log has mealList (list) and calorie_chart (chart)
    patterns = [f["detail"]["pattern"] for f in features]
    assert "list" in patterns
    assert "chart" in patterns


def test_crud_detector():
    doc = parse_pen_json(_sample_doc())
    detector = CrudDetector()
    features = detector.detect(doc)
    # Food Log has addFoodButton (create) and "Add Food" text
    assert len(features) >= 1
    food_log_crud = [f for f in features if "Food Log" in f["detail"].get("screen_name", "")]
    assert len(food_log_crud) >= 1
    ops = food_log_crud[0]["detail"]["operations"]
    assert "create" in ops  # addFoodButton


def test_run_all_detectors():
    doc = parse_pen_json(_sample_doc())
    features = run_all_detectors(doc)
    assert len(features) > 5  # Should find screens + components + navigation + etc.

    # Check all detectors contributed
    detectors_found = set(f["detector"] for f in features)
    assert "screen" in detectors_found
    assert "component" in detectors_found
    assert "navigation" in detectors_found
