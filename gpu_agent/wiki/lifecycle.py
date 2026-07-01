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


def persistence(store, page_id: str) -> int:
    """Distinct asOf cycles the page has been observed across (post-4-4d, each new-cycle
    observation is a genuinely NEW/UPDATE fact — DUPLICATE re-reports never create observations)."""
    return len({o.asOf for o in store.observations(page_id)})


def corroboration(store, page_id: str) -> int:
    """Distinct evidence sources across all findings observed on the page (Part 10 corroboration)."""
    sources: set[str] = set()
    for o in store.observations(page_id):
        if not store.findings.exists(o.findingId):
            continue
        f = store.findings.get(o.findingId)
        for e in f.evidence:
            sources.add(e.source)
    return len(sources)


def promotion_candidates(store, config=DEFAULT_LIFECYCLE_CONFIG) -> list[PromotionCandidate]:
    """Provisional pages (any type) that meet BOTH the persist and corroborate bars. Read-only;
    ordered by pageId. Registered pages are already canonical and are skipped."""
    cands: list[PromotionCandidate] = []
    for entry in sorted(store.index(), key=lambda e: e.id):
        if entry.status != "provisional":
            continue
        pc = persistence(store, entry.id)
        src = corroboration(store, entry.id)
        if pc >= config.min_persist_cycles and src >= config.min_sources:
            cands.append(PromotionCandidate(
                pageId=entry.id, type=entry.type, title=entry.title,
                persistCycles=pc, distinctSources=src,
                verdict=f"persisted {pc} cycles, {src} sources -> promote"))
    return cands
