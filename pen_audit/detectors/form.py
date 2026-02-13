"""Form detector: identifies input fields and form patterns."""

from __future__ import annotations

from .base import BaseDetector
from ..pen_parser import PenDocument, PenNode
from ..state import make_feature

_INPUT_PATTERNS = [
    "input", "field", "text_field", "textfield", "textarea",
    "search", "searchbar", "search_bar",
    "select", "dropdown", "picker", "combo",
    "toggle", "switch", "checkbox", "check_box",
    "slider", "range",
    "radio", "radio_button",
    "date", "datepicker", "date_picker", "time_picker",
    "stepper", "number_input",
    "password", "email",
]

_BUTTON_PATTERNS = [
    "button", "btn", "cta", "submit", "save", "cancel", "confirm",
    "action", "primary_button", "secondary_button",
]


def _classify_input(name: str) -> str:
    """Classify an input type from its name."""
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    if any(k in name_lower for k in ["toggle", "switch"]):
        return "toggle"
    if any(k in name_lower for k in ["slider", "range"]):
        return "slider"
    if any(k in name_lower for k in ["select", "dropdown", "picker", "combo"]):
        return "select"
    if any(k in name_lower for k in ["checkbox", "check_box", "radio"]):
        return "checkbox"
    if any(k in name_lower for k in ["search"]):
        return "search"
    if any(k in name_lower for k in ["date", "time"]):
        return "date"
    if any(k in name_lower for k in ["textarea"]):
        return "textarea"
    if any(k in name_lower for k in ["stepper", "number"]):
        return "number"
    return "text"


class FormDetector(BaseDetector):
    """Identifies form inputs, buttons, and groups them into logical forms."""

    name = "form"
    description = "Identifies form elements (inputs, buttons, validation)"

    def detect(self, doc: PenDocument) -> list[dict]:
        features = []

        for screen in doc.screens:
            inputs: list[dict] = []
            buttons: list[str] = []

            for node in screen.walk():
                if not node.name:
                    continue
                name_lower = node.name.lower().replace(" ", "_").replace("-", "_")

                # Check for input fields
                if any(p in name_lower for p in _INPUT_PATTERNS):
                    input_type = _classify_input(node.name)
                    inputs.append({
                        "name": node.name,
                        "type": input_type,
                        "node_id": node.id,
                    })

                # Check for buttons
                if any(p in name_lower for p in _BUTTON_PATTERNS):
                    buttons.append(node.name)

            if inputs:
                # Group inputs = a form
                tier = 2 if len(inputs) <= 5 else 3
                features.append(make_feature(
                    detector="form",
                    screen_id=screen.id,
                    name=f"{screen.name}::form",
                    tier=tier,
                    category="form",
                    summary=f"Form: {len(inputs)} inputs in {screen.name} ({', '.join(i['type'] for i in inputs[:5])})",
                    detail={
                        "inputs": inputs,
                        "buttons": buttons,
                        "screen_name": screen.name,
                        "input_count": len(inputs),
                        "input_types": list(set(i["type"] for i in inputs)),
                    },
                ))

        return features
