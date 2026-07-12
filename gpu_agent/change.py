"""F78 Stage 6 — the change engine.

Pure projection over stored scorecards + an injected price snapshot. Builds today's
STATE VECTOR and diffs it POINT-IN-TIME against the nearest stored run at/before
asOf-1d / asOf-7d / asOf-30d. No wall-clock: all day math via gpu_agent.asof, so a
replay of the same day is byte-identical. Reader labels are applied in the renderer,
never here — the engine keeps registry ids for stable diffing.
"""
from __future__ import annotations
import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from gpu_agent.asof import period_end, days_between, AsOfError
from gpu_agent.schema.scorecard import Scorecard, DIMENSIONS
from gpu_agent.thesis import ThesisBook
from gpu_agent.report import _VERSION_RE, compute_sdgi, load_scorecard

# Headline-metric selectors (registry indicator ids). Tier 2 rental price comes from the
# price feed (PriceCell), not a finding, so it is not in SCARCITY_INDICATORS.
SCARCITY_INDICATORS = ("leadTimes", "S10")   # lead times + whole-chain packaging/HBM inventory
MONEY_INDICATORS = ("vendorRevenueGuidance", "rpoBacklog", "grossMargin")
# (name, calendar-day lookback) — the three horizons of the change-first lead (D3).
LOOKBACKS = (("yesterday", 1), ("last week", 7), ("last month", 30))
_PRICE_REL_TOL = 0.01   # mirrors price_track.REL_TOL — "flat" band for a rental price move


class DimCell(BaseModel):
    rating: str
    direction: str


class ThesisCell(BaseModel):
    conviction: str
    lastVerdict: Optional[str] = None
    streak: int = 0
    challenged: bool = False
    title: str = ""
    lastChangedAsOf: str = ""


class MetricCell(BaseModel):
    indicatorId: str
    value: Optional[float] = None
    unit: Optional[str] = None
    statement: str = ""
    observedAt: Optional[str] = None   # newest evidence date — the age tag is measured from here
    tier: str = ""                     # "scarcity" (Tier 2) or "money" (Tier 3)


class PriceCell(BaseModel):
    model: str                # GPU model, e.g. "B200"
    usdPerGpuHour: float
    asOfColumn: str           # the date column actually read (nearest at/before)
    custom: bool = False      # True = custom silicon (Trainium/TPU); excluded from the rental tier


class StateVector(BaseModel):
    asOf: str
    dimensions: dict[str, DimCell] = Field(default_factory=dict)
    demand: float = 0.0       # demandSupply.dmiContribution
    supply: float = 0.0       # demandSupply.smiContribution
    sdgi: float = 0.0         # demand - supply gap
    theses: dict[str, ThesisCell] = Field(default_factory=dict)
    metrics: dict[str, MetricCell] = Field(default_factory=dict)   # keyed by indicatorId
    prices: list[PriceCell] = Field(default_factory=list)
    # AMENDED 2026-07-11 (exec top band + alert ladder): categoryStatus projection.
    statusRating: Optional[str] = None       # categoryStatus.rating   (e.g. "Strong")
    statusDirection: Optional[str] = None    # categoryStatus.direction (e.g. "worsening")
    constraintLabel: Optional[str] = None    # categoryStatus.constraintLabel — the binding constraint


def _latest_metric(sc: Scorecard, indicator_id: str):
    """The latest-vintage finding for an indicator id by (capturedAt, observedAt, magnitude)
    — the same collapse brief._collapse_latest / price_track._latest_by_series use — or None."""
    best = None
    for f in sc.findings:
        if f.indicatorId != indicator_id:
            continue
        key = (f.capturedAt, f.observedAt, f.magnitude)
        if best is None or key > (best.capturedAt, best.observedAt, best.magnitude):
            best = f
    return best


def build_state(sc: Scorecard, book: Optional[ThesisBook] = None,
                prices: Optional[list[PriceCell]] = None) -> StateVector:
    """Project a finished scorecard (+ optional standing thesis book + price snapshot) into
    the STATE VECTOR the diff engine compares point-in-time. Retired theses are dropped
    (book.standing()); a metric with no finding this cycle is simply absent (honest gap)."""
    dims = {d: DimCell(rating=dr.rating, direction=dr.direction)
            for d in DIMENSIONS
            if (dr := sc.dimensionRatings.get(d)) is not None}

    theses: dict[str, ThesisCell] = {}
    if book is not None:
        for e in book.standing():
            theses[e.id] = ThesisCell(
                conviction=e.conviction, lastVerdict=e.lastVerdict, streak=e.streak,
                challenged=e.pendingChallenge is not None, title=e.title,
                lastChangedAsOf=e.lastChangedAsOf)

    metrics: dict[str, MetricCell] = {}
    for iid in SCARCITY_INDICATORS + MONEY_INDICATORS:
        f = _latest_metric(sc, iid)
        if f is None:
            continue
        ev_dates = [ev.date for ev in f.evidence if ev.date]
        metrics[iid] = MetricCell(
            indicatorId=iid,
            value=(f.value.number if f.value is not None else None),
            unit=(f.value.unit if f.value is not None else None),
            statement=f.statement,
            observedAt=(max(ev_dates) if ev_dates else f.observedAt),
            tier=("money" if iid in MONEY_INDICATORS else "scarcity"))

    cs = sc.categoryStatus   # AMENDED 2026-07-11: Optional on older scorecards — None-safe
    return StateVector(
        asOf=sc.asOf, dimensions=dims,
        demand=sc.demandSupply.dmiContribution, supply=sc.demandSupply.smiContribution,
        sdgi=compute_sdgi(sc), theses=theses, metrics=metrics,
        prices=list(prices or []),
        statusRating=(cs.rating if cs is not None else None),
        statusDirection=(cs.direction if cs is not None else None),
        constraintLabel=(getattr(cs, "constraintLabel", None) if cs is not None else None))


def nearest_run_at_or_before(store_dir, category_id: str, target: datetime.date,
                             *, before: Optional[tuple[str, int]] = None):
    """The stored scorecard whose asOf period-end is the GREATEST that is <= `target`
    (nearest at/before — robust to skipped days). Generalizes report.find_prior from a
    single 'prior' to an arbitrary calendar-day target. `before`, when given as the current
    run's (asOf, version), excludes that run and anything at/after it so a run never diffs
    against itself (tuple compare, exactly as find_prior's `(asof, v) < cur_key`). Files
    that don't match <asOf>-v<N>.json, or carry an unparseable asOf, are skipped silently
    (they're not scorecards). Returns a Path or None."""
    cat_dir = Path(store_dir) / category_id
    if not cat_dir.is_dir():
        return None
    cands: list[tuple[datetime.date, str, int, Path]] = []
    for p in cat_dir.glob("*.json"):
        m = _VERSION_RE.match(p.name)
        if not m:
            continue
        asof, v = m.group(1), int(m.group(2))
        try:
            pe = period_end(asof)
        except AsOfError:
            continue
        if pe > target:
            continue
        if before is not None and (asof, v) >= before:
            continue
        cands.append((pe, asof, v, p))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[2]))   # period-end asc, then version asc
    return cands[-1][3]
