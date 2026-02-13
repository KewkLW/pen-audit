"""Tests for the .pen file parser."""

from pen_audit.pen_parser import parse_pen_json, PenNode, PenDocument


def _sample_doc() -> dict:
    """A minimal .pen-like JSON structure for testing."""
    return {
        "id": "root",
        "type": "frame",
        "name": "Document",
        "children": [
            {
                "id": "screen1",
                "type": "frame",
                "name": "Food Log",
                "width": 390,
                "height": 844,
                "children": [
                    {
                        "id": "header1",
                        "type": "frame",
                        "name": "header",
                        "children": [
                            {"id": "title1", "type": "text", "name": "title", "content": "Food Log"},
                            {"id": "back1", "type": "frame", "name": "back_button"},
                        ],
                    },
                    {
                        "id": "search1",
                        "type": "ref",
                        "name": "searchBar",
                        "ref": "comp_search",
                    },
                    {
                        "id": "list1",
                        "type": "frame",
                        "name": "mealList",
                        "children": [
                            {"id": "item1", "type": "frame", "name": "breakfastRow"},
                            {"id": "item2", "type": "frame", "name": "lunchRow"},
                            {"id": "item3", "type": "frame", "name": "dinnerRow"},
                        ],
                    },
                    {
                        "id": "addBtn",
                        "type": "frame",
                        "name": "addFoodButton",
                        "children": [
                            {"id": "addText", "type": "text", "name": "label", "content": "Add Food"},
                        ],
                    },
                ],
            },
            {
                "id": "screen2",
                "type": "frame",
                "name": "Settings",
                "width": 390,
                "height": 844,
                "children": [
                    {"id": "s2header", "type": "frame", "name": "header"},
                    {"id": "s2title", "type": "text", "name": "title", "content": "Settings"},
                ],
            },
            {
                "id": "comp_search",
                "type": "frame",
                "name": "SearchBar",
                "reusable": True,
                "children": [
                    {"id": "searchInput", "type": "frame", "name": "input_field"},
                    {"id": "searchIcon", "type": "path", "name": "icon"},
                ],
            },
            {
                "id": "ds_container",
                "type": "frame",
                "name": "Design System",
                "children": [],
            },
        ],
    }


def test_parse_basic():
    doc = parse_pen_json(_sample_doc())
    assert isinstance(doc, PenDocument)
    assert doc.root.id == "root"
    assert doc.root.type == "frame"


def test_screens():
    doc = parse_pen_json(_sample_doc())
    screens = doc.screens
    # Should find Food Log and Settings (not the reusable component, not Design System)
    screen_names = [s.name for s in screens]
    assert "Food Log" in screen_names
    assert "Settings" in screen_names
    assert "SearchBar" not in screen_names  # reusable = excluded
    assert "Design System" in screen_names  # not reusable, so included as screen


def test_components():
    doc = parse_pen_json(_sample_doc())
    components = doc.components
    assert len(components) == 1
    assert components[0].name == "SearchBar"
    assert components[0].reusable is True


def test_instances():
    doc = parse_pen_json(_sample_doc())
    instances = doc.all_instances
    assert len(instances) == 1
    assert instances[0].type == "ref"
    assert instances[0].properties.get("ref") == "comp_search"


def test_walk():
    doc = parse_pen_json(_sample_doc())
    food_log = [s for s in doc.screens if s.name == "Food Log"][0]
    all_nodes = list(food_log.walk())
    assert len(all_nodes) > 5  # Food Log has multiple children


def test_find_text_content():
    doc = parse_pen_json(_sample_doc())
    food_log = [s for s in doc.screens if s.name == "Food Log"][0]
    texts = food_log.find_text_content()
    assert "Food Log" in texts
    assert "Add Food" in texts


def test_count_by_type():
    doc = parse_pen_json(_sample_doc())
    food_log = [s for s in doc.screens if s.name == "Food Log"][0]
    counts = food_log.count_by_type()
    assert counts["frame"] >= 3
    assert counts["text"] >= 1
    assert counts.get("ref", 0) >= 1


def test_depth():
    doc = parse_pen_json(_sample_doc())
    food_log = [s for s in doc.screens if s.name == "Food Log"][0]
    assert food_log.depth() >= 2  # header > title


def test_platform_detection():
    doc = parse_pen_json(_sample_doc())
    food_log = [s for s in doc.screens if s.name == "Food Log"][0]
    # 390px wide = mobile
    assert food_log.properties.get("width") == 390
