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


# F31 identity moved to gpu_agent/publisher.py when F63 gave it three consumers;
# re-exported under the historical name so this module's callers (and thesis.py's
# defensive import of it) stay byte-compatible.
from gpu_agent.publisher import publisher_key as _publisher_key


def corroboration(store, page_id: str) -> int:
    """Distinct evidence PUBLISHERS (F31) across all findings observed on the page (Part 10
    corroboration) - two sources at the same publisher domain corroborate each other only once."""
    publishers: set[str] = set()
    for o in store.observations(page_id):
        if not store.findings.exists(o.findingId):
            continue
        f = store.findings.get(o.findingId)
        for e in f.evidence:
            publishers.add(_publisher_key(e))
    return len(publishers)


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


def prune_candidates(store, stale) -> list[PruneCandidate]:
    """Provisional pages that have gone stale (4-4b's stale signal) — the reverse of promotion.
    Registered pages are never pruned (established coverage). `stale` is a list of StaleEntry
    (pageId, effectiveSalience). Ordered by pageId."""
    idx = {e.id: e for e in store.index()}
    cands: list[PruneCandidate] = []
    for s in sorted(stale, key=lambda x: x.pageId):
        entry = idx.get(s.pageId)
        if entry is not None and entry.status == "provisional":
            cands.append(PruneCandidate(
                pageId=s.pageId, type=entry.type,
                reason=f"stale: eff_salience {s.effectiveSalience:.3g} below threshold"))
    return cands


def partition_canonical(index):
    """The quarantine filter seam: split a store index into (registered, provisional). Canonical
    projections (4-5, the layer rollup) include only `registered`; `provisional` are candidates."""
    registered = [e for e in index if e.status == "registered"]
    provisional = [e for e in index if e.status == "provisional"]
    return registered, provisional


def lifecycle(store, *, as_of, stale, config=DEFAULT_LIFECYCLE_CONFIG) -> LifecycleReport:
    """Propose the cycle's lifecycle actions (read-only). Every provisional page is examined and
    surfaced as a QuarantineEntry; promotions/prunes annotate subsets of them. Nothing is mutated."""
    _, provisional = partition_canonical(store.index())
    quarantined = [QuarantineEntry(pageId=e.id, status=e.status)
                   for e in sorted(provisional, key=lambda e: e.id)]
    return LifecycleReport(
        asOf=as_of,
        promotions=promotion_candidates(store, config),
        prunes=prune_candidates(store, stale),
        quarantined=quarantined,
        provisionalConsidered=len(provisional))


def apply_lifecycle(store, report, *, as_of, config=DEFAULT_LIFECYCLE_CONFIG) -> AppliedSummary:
    """The --apply path (the charter's 'reviewed -> promoted' step). Promote via update_header;
    prune via a non-destructive salience floor (record_state keeps state/trajectory). Idempotent:
    an already-registered page is not re-promoted; an already-floored page is not re-floored."""
    promoted = 0
    for pc in report.promotions:
        page = store.get_page(pc.pageId)
        if page.status != "registered":
            store.update_header(pc.pageId, as_of=as_of, status="registered")
            promoted += 1
    pruned = 0
    for pr in report.prunes:
        page = store.get_page(pr.pageId)
        if page.salience > config.prune_salience_floor:
            store.record_state(pr.pageId, as_of=as_of, state=page.state,
                               trajectory=page.trajectory, salience=config.prune_salience_floor)
            pruned += 1
    return AppliedSummary(promoted=promoted, pruned=pruned)
