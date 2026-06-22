from __future__ import annotations
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel

class Kind(str, Enum):
    measured = "measured"
    observed = "observed"
    hypothesis = "hypothesis"

class Value(BaseModel):
    number: float
    unit: str

class Impact(BaseModel):
    targets: list[str]
    direction: Literal["positive", "negative", "mixed"]
    mechanism: str

class Evidence(BaseModel):
    source: str
    url: str
    date: str
    excerpt: str
    tier: Literal["primary", "secondary"]

class Confidence(BaseModel):
    level: Literal["low", "medium", "high"]
    basis: str

class Finding(BaseModel):
    id: str
    statement: str
    kind: Kind
    value: Optional[Value] = None
    trend: Literal["rising", "falling", "flat", "unknown"]
    why: str
    impact: Impact
    evidence: list[Evidence] = []
    reasoning: Optional[str] = None
    confidence: Confidence
    dispersion: Optional[str] = None
    asOf: str
    indicatorId: str
    side: Literal["demand", "supply", "price", "structural"]
    polarityDemand: Literal[-1, 0, 1]
    polaritySupply: Literal[-1, 0, 1]
    magnitude: Literal[1, 2, 3]
    entity: str
    observedAt: str
    capturedAt: str
    extractionModel: Optional[str] = None
    schemaVersion: str = "1.0"
