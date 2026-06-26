from __future__ import annotations
import json, pathlib
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

class RegistryError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))

class IndicatorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str = ""
    dimension: Optional[str] = None
    polarityTrack: Optional[Literal["demand", "supply"]] = None
    side: Optional[Literal["demand", "supply", "price", "structural"]] = None
    weight: float = 0.0
    unit: str = ""
    kind: Literal["measured", "qualitative"] = "measured"
    comparability: str = ""
    scoring: bool = True
    readsLevelOrSlope: Optional[Literal["level", "slope"]] = None
    decayLambda: float = 0.0
    leadMonths: str = ""

class IndicatorRegistry:
    def __init__(self, indicators: dict[str, dict], overrides: dict[str, dict] | None = None):
        self.indicators = indicators
        self.overrides = overrides or {}

    @classmethod
    def load(cls, path) -> "IndicatorRegistry":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(data.get("indicators", {}), data.get("overrides", {}))

    def resolve(self, indicator_id: str, category_id: str | None = None) -> IndicatorSpec:
        if indicator_id not in self.indicators:
            raise RegistryError([f"unregistered indicator: {indicator_id}"])
        merged = dict(self.indicators[indicator_id])
        if category_id and indicator_id in self.overrides.get(category_id, {}):
            merged.update(self.overrides[category_id][indicator_id])
        return IndicatorSpec(id=indicator_id, **merged)

    def validate_against(self, taxonomy) -> None:
        violations: list[str] = []
        for ind_id, raw in self.indicators.items():
            spec = IndicatorSpec(id=ind_id, **raw)
            if not spec.scoring:
                continue
            if spec.dimension not in taxonomy.dimensions:
                violations.append(f"{ind_id}: dimension '{spec.dimension}' not in taxonomy")
            if spec.weight == 0.0:
                violations.append(f"{ind_id}: scoring indicator has zero weight")
        for cat, inds in self.overrides.items():
            if cat not in taxonomy.categories:
                violations.append(f"override category '{cat}' not in taxonomy")
            for ind_id in inds:
                if ind_id not in self.indicators:
                    violations.append(f"override for unregistered indicator '{ind_id}'")
        if violations:
            raise RegistryError(violations)
