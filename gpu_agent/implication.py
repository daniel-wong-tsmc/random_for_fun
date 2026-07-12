"""gpu_agent/implication.py — the F65 "so what for TSMC" implication brain.

Mirrors the thesis seam (gpu_agent/thesis.py): a category-agnostic prompt template
(the SYSTEM template carries zero merchant-gpu idioms — the per-category DECISION
VARIABLES live in registry/implications.json as DATA), a pure deterministic gate, and
a storage carve-out. ONE author, no sampling. The scorecard is untouched — the
implication artifact is a separate carve-out under store/implications/.

Implications are WATCH-ITEMS / EXPOSURE statements, NEVER recommendations or actions
(charter Parts 10-11/21). The gate enforces that deterministically.
"""
from __future__ import annotations
import json
import pathlib
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ImplicationError(Exception):
    """Raised for an unknown category, or an untrusted / missing on-disk implication artifact."""


# --- registry (per-category decision variables — DATA) -------------------------

class DecisionVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    description: str


class ImplicationRegistry:
    """registry/implications.json -> per-category decision-variable lists. Adding a variable
    or a new category is a pure data edit (registry-driven; F26/F27)."""

    def __init__(self, by_category: dict[str, list[DecisionVariable]]):
        self._by_category = by_category

    @classmethod
    def load(cls, path) -> "ImplicationRegistry":
        raw = json.loads(pathlib.Path(path).read_text("utf-8"))
        by_cat = {
            category: [DecisionVariable(**v) for v in entry["variables"]]
            for category, entry in raw.items()
        }
        return cls(by_cat)

    def variables_for(self, category: str) -> list[DecisionVariable]:
        if category not in self._by_category:
            raise ImplicationError(
                f"no implication decision variables registered for category {category!r}")
        return self._by_category[category]
