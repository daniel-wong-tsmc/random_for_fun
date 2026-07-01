from __future__ import annotations
from pydantic import BaseModel, Field


class PromotionCandidate(BaseModel):
    pageId: str
    type: str                       # "entity" | "theme"
    title: str
    persistCycles: int
    distinctSources: int
    verdict: str


class PruneCandidate(BaseModel):
    pageId: str
    type: str
    reason: str


class QuarantineEntry(BaseModel):
    pageId: str
    status: str                     # always "provisional" here
    confidenceCapped: bool = True
    note: str = "not yet in coverage"


class LifecycleReport(BaseModel):
    asOf: str
    promotions: list[PromotionCandidate] = Field(default_factory=list)
    prunes: list[PruneCandidate] = Field(default_factory=list)
    quarantined: list[QuarantineEntry] = Field(default_factory=list)
    provisionalConsidered: int = 0


class AppliedSummary(BaseModel):
    promoted: int = 0
    pruned: int = 0


class LifecycleConfig(BaseModel):
    min_persist_cycles: int = 2     # distinct asOf cycles a provisional must be observed across
    min_sources: int = 2            # distinct evidence sources a provisional must cite
    stale_threshold: float = 0.1    # reuses 4-4b's stale definition (documented; prune reads the stale list)
    prune_salience_floor: float = 0.0


DEFAULT_LIFECYCLE_CONFIG = LifecycleConfig()
