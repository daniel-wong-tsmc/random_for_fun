"""F79 — the series-indicator registry (registry/series-indicators.json).

NON-prompt-affecting metadata for the six SDEWS series (side, weight, decay, dual
polarity, lifecycle). Read by the series engine / backtest / shadow only. The F6 prompt
pin reads registry/indicators.json (config.REGISTRY_PATH), NOT this file, so the six
series stay out of the emitted extract prompt until they are PROMOTED into
registry/indicators.json at the G3 stage. See plan DP-3.
"""
from __future__ import annotations
import json
import pathlib
from typing import Literal
from pydantic import BaseModel, ConfigDict


class SeriesIndicatorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    sdews: str = ""
    side: Literal["demand", "supply"]
    weight: float
    decayLambda: float = 0.0
    polarityDemand: int = 0
    polaritySupply: int = 0
    lifecycle: Literal["active", "degraded", "retired"] = "active"
    leadMonths: str = ""
    estimateGrade: bool = False
    unit: str = ""


class SeriesRegistry:
    def __init__(self, specs: dict[str, SeriesIndicatorSpec]):
        self.specs = specs

    @classmethod
    def load(cls, path) -> "SeriesRegistry":
        raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("seriesIndicators", {})
        return cls({k: SeriesIndicatorSpec(id=k, **v) for k, v in raw.items()})

    def resolve(self, indicator_id: str) -> SeriesIndicatorSpec:
        if indicator_id not in self.specs:
            raise KeyError(f"unregistered series indicator: {indicator_id}")
        return self.specs[indicator_id]
