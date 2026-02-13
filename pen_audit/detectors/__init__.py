"""UI pattern detectors for .pen files."""

from .screen import ScreenDetector
from .component import ComponentDetector
from .navigation import NavigationDetector
from .form import FormDetector
from .data_display import DataDisplayDetector
from .interactive import InteractiveDetector
from .crud import CrudDetector

ALL_DETECTORS = [
    ScreenDetector,
    ComponentDetector,
    NavigationDetector,
    FormDetector,
    DataDisplayDetector,
    InteractiveDetector,
    CrudDetector,
]


def run_all_detectors(doc) -> list[dict]:
    """Run all detectors against a PenDocument and return combined features."""
    features = []
    for detector_cls in ALL_DETECTORS:
        detector = detector_cls()
        features.extend(detector.detect(doc))
    return features
