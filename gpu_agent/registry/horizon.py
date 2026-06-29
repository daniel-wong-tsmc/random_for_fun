from __future__ import annotations
import json
import pathlib
from typing import Optional

CADENCES = {"daily", "weekly", "quarterly"}
HORIZONS = {"leading", "coincident", "lagging"}


class HorizonError(Exception):
    """Raised when a cadence/horizon tag is missing, invalid, or orphaned (fail loud)."""


class IndicatorHorizons:
    """Read accessor for the top-level `cadenceHorizon` map in indicators.json.

    The frozen IndicatorRegistry.load() ignores this top-level key; this class is
    the seam 4-3 reads to bucket Momentum (lagging+coincident) vs Outlook (leading).
    """

    def __init__(self, mapping: dict[str, dict]):
        self.mapping = mapping

    @classmethod
    def load(cls, path) -> "IndicatorHorizons":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(data.get("cadenceHorizon", {}))

    def get(self, indicator_id: str) -> Optional[dict]:
        return self.mapping.get(indicator_id)

    def _valid_tag(self, indicator_id: str) -> dict:
        tag = self.mapping.get(indicator_id)
        if tag is None:
            raise HorizonError(f"indicator '{indicator_id}' has no cadenceHorizon tag")
        if tag.get("cadence") not in CADENCES:
            raise HorizonError(
                f"indicator '{indicator_id}' has invalid cadence: {tag.get('cadence')!r}")
        if tag.get("horizon") not in HORIZONS:
            raise HorizonError(
                f"indicator '{indicator_id}' has invalid horizon: {tag.get('horizon')!r}")
        return tag

    def cadence(self, indicator_id: str) -> str:
        return self._valid_tag(indicator_id)["cadence"]

    def horizon(self, indicator_id: str) -> str:
        return self._valid_tag(indicator_id)["horizon"]

    def validate_coverage(self, registry) -> None:
        """Fail loud unless every SCORING indicator is tagged with valid values and
        every tag refers to a registered indicator (no orphans)."""
        violations: list[str] = []
        for ind_id in self.mapping:
            if ind_id not in registry.indicators:
                violations.append(f"cadenceHorizon tags unregistered indicator '{ind_id}'")
        for ind_id in registry.indicators:
            spec = registry.resolve(ind_id)
            if not spec.scoring:
                continue
            tag = self.mapping.get(ind_id)
            if tag is None:
                violations.append(f"scoring indicator '{ind_id}' is untagged")
                continue
            if tag.get("cadence") not in CADENCES:
                violations.append(
                    f"scoring indicator '{ind_id}' has invalid cadence: {tag.get('cadence')!r}")
            if tag.get("horizon") not in HORIZONS:
                violations.append(
                    f"scoring indicator '{ind_id}' has invalid horizon: {tag.get('horizon')!r}")
        if violations:
            raise HorizonError("; ".join(violations))
