from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons


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

_CADENCE_HL = {"daily": "h_short", "weekly": "h_med", "quarterly": "h_long"}


def _findings_for(store, page_id, observations):
    """Resolve observation finding ids to Findings, skipping any not in the FindingStore."""
    out = []
    for o in observations:
        try:
            out.append(store.findings.get(o.findingId))
        except Exception:
            continue
    return out


def half_life(findings, horizons, config=DEFAULT_LINT_CONFIG):
    """Longest-persistence half-life (in cycles) among the findings' cadence-horizon tags.
    cadence drives persistence (daily->short, weekly->med, quarterly->long); a leading-horizon
    finding is floored at H_med. Untagged indicator ids fall back to H_med and are RETURNED
    (the caller logs them — nothing silent). No findings -> H_med (neutral)."""
    untagged: list[str] = []
    classes: list[int] = []
    for f in findings:
        tag = horizons.get(f.indicatorId)
        if tag is None or tag.get("cadence") not in _CADENCE_HL:
            untagged.append(f.indicatorId)
            classes.append(config.h_med)
            continue
        hl = getattr(config, _CADENCE_HL[tag["cadence"]])
        if tag.get("horizon") == "leading":
            hl = max(hl, config.h_med)
        classes.append(hl)
    return (max(classes) if classes else config.h_med), untagged


def quiet_age(store, page_id, as_of) -> int:
    """Number of distinct asOf cycles in the log strictly after the page's last MATERIAL event
    (append-observation or state-change), up to as_of. A body-only edit is not material. A page
    with no material events decays from its createdAsOf."""
    events = [e for e in store.log.read() if e.asOf <= as_of]
    cycles = sorted({e.asOf for e in events})
    materials = [e.asOf for e in events
                 if e.pageId == page_id and e.kind in ("append-observation", "state-change")]
    baseline = max(materials) if materials else store.get_page(page_id).createdAsOf
    return sum(1 for c in cycles if c > baseline)


def decay(quiet_age: int, half_life: int) -> float:
    return 0.5 ** (quiet_age / half_life)


def effective_salience(intrinsic: float, quiet_age: int, half_life: int) -> float:
    return intrinsic * decay(quiet_age, half_life)
