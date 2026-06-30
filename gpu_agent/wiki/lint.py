from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class IndicatorMove(BaseModel):
    indicatorId: str
    magnitude: int
    scoring: bool


class MoveFactors(BaseModel):
    newThread: bool = False
    stateTransition: Optional[dict] = None
    contradiction: bool = False
    contradictionNote: str = ""
    indicatorMoves: list[IndicatorMove] = Field(default_factory=list)


class MaterialMove(BaseModel):
    pageId: str
    title: str
    type: str
    status: str
    score: float
    factors: MoveFactors
    contributingFindingIds: list[str] = Field(default_factory=list)
    tierMult: float
    recencyMult: float
    effectiveSalience: float


class CrossRefGap(BaseModel):
    source: str
    target: str
    reason: str


class ContradictionEntry(BaseModel):
    pageId: str
    note: str
    asOf: str


class StaleEntry(BaseModel):
    pageId: str
    effectiveSalience: float


class HealthReport(BaseModel):
    orphans: list[str] = Field(default_factory=list)
    stale: list[StaleEntry] = Field(default_factory=list)
    crossRefGaps: list[CrossRefGap] = Field(default_factory=list)
    contradictions: list[ContradictionEntry] = Field(default_factory=list)


class LintReport(BaseModel):
    asOf: str
    prevAsOf: Optional[str] = None
    material: list[MaterialMove] = Field(default_factory=list)
    dropped: list[MaterialMove] = Field(default_factory=list)
    health: HealthReport


class LintConfig(BaseModel):
    w_contra: float = 1.0
    w_state: float = 0.6
    w_new: float = 0.5
    w_ind: float = 0.3
    tier_primary: float = 1.0
    tier_secondary: float = 0.6
    recency_full: float = 1.0
    recency_decayed: float = 0.7
    horizon_boost_leading: float = 0.5
    salience_floor: float = 0.5
    material_threshold: float = 0.3
    h_short: int = 1
    h_med: int = 3
    h_long: int = 6
    stale_threshold: float = 0.1


DEFAULT_LINT_CONFIG = LintConfig()
