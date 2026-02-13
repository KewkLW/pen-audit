"""Base class for .pen file UI pattern detectors."""

from __future__ import annotations
from abc import ABC, abstractmethod

from ..pen_parser import PenDocument


class BaseDetector(ABC):
    """Base class for all UI pattern detectors.

    Each detector walks the .pen node tree and identifies specific UI patterns,
    returning a list of feature dicts.
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    def detect(self, doc: PenDocument) -> list[dict]:
        """Run detection against the document. Returns list of feature dicts."""
        ...
