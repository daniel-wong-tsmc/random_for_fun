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


from gpu_agent.report import _momentum_word   # local, one-way; report never imports change

_ROUND = 3   # match report's %.3f index display so float noise never reads as a "change"


class ItemDelta(BaseModel):
    key: str                          # "dim:<d>", "index:demand|supply|gap", "thesis:<id>", "metric:<iid>", "price:<model>"
    changed: bool
    today: Optional[str] = None       # display token (renderer applies reader labels)
    prior: Optional[str] = None
    direction: str = "same"           # "up" | "down" | "same" | "new"
    unchangedSince: Optional[str] = None


class HorizonDiff(BaseModel):
    horizon: str                      # "yesterday" | "last week" | "last month"
    lookbackDays: int
    priorAsOf: Optional[str] = None   # nearest run's asOf; None when no run at/before the target
    items: list[ItemDelta] = Field(default_factory=list)


class ChangeReport(BaseModel):
    asOf: str
    horizons: list[HorizonDiff] = Field(default_factory=list)
    # AMENDED 2026-07-11: per-horizon prior StateVector (keyed by horizon name, None when no
    # run at/before that target) — the top band needs prior VALUES (bands.band_with_prior),
    # not display tokens; build_change_report already constructs these, now it keeps them.
    priors: dict[str, Optional[StateVector]] = Field(default_factory=dict)


def _index_token(value: float) -> str:
    return f"{_momentum_word(value)} {value:.3f}"


def _dir_of(today: float, prior: float) -> str:
    d = round(today, _ROUND) - round(prior, _ROUND)
    return "up" if d > 0 else "down" if d < 0 else "same"


def _metric_token(cell: "MetricCell") -> str:
    if cell.value is not None:
        return f"{cell.value:g}{(' ' + cell.unit) if cell.unit else ''}"
    return cell.statement


def _price_changed(a: float, b: float) -> tuple[bool, str]:
    tol = _PRICE_REL_TOL * max(abs(b), 1e-9)
    d = a - b
    if abs(d) <= tol:
        return False, "same"
    return True, ("up" if d > 0 else "down")


def diff_states(name: str, days: int, current: StateVector,
                prior: Optional[StateVector], prior_asof: Optional[str],
                book: Optional[ThesisBook]) -> HorizonDiff:
    """One horizon's point-in-time diff. Dimensions/indices/metrics/prices are two-snapshot
    diffs (current vs prior); theses read movement from the current book's lastChangedAsOf vs
    prior_asof (stored scorecards don't embed past book state — see the Task 3 assumption).
    prior=None (no run at/before this horizon) -> empty items list."""
    items: list[ItemDelta] = []
    if prior is None:
        return HorizonDiff(horizon=name, lookbackDays=days, priorAsOf=None, items=items)

    # dimensions
    for d, cell in current.dimensions.items():
        tok = f"{cell.rating}/{cell.direction}"
        pcell = prior.dimensions.get(d)
        if pcell is None:
            items.append(ItemDelta(key=f"dim:{d}", changed=True, today=tok, direction="new"))
        else:
            ptok = f"{pcell.rating}/{pcell.direction}"
            items.append(ItemDelta(key=f"dim:{d}", changed=(tok != ptok), today=tok, prior=ptok,
                                   direction=("same" if tok == ptok else "up")))  # dim direction refined in the renderer

    # indices: demand, supply, gap
    for key, cur_v, pri_v in (("index:demand", current.demand, prior.demand),
                              ("index:supply", current.supply, prior.supply),
                              ("index:gap", current.sdgi, prior.sdgi)):
        direction = _dir_of(cur_v, pri_v)
        items.append(ItemDelta(key=key, changed=(direction != "same"),
                               today=_index_token(cur_v), prior=_index_token(pri_v),
                               direction=direction))

    # headline metrics
    for iid, cell in current.metrics.items():
        tok = _metric_token(cell)
        pcell = prior.metrics.get(iid)
        if pcell is None:
            items.append(ItemDelta(key=f"metric:{iid}", changed=True, today=tok, direction="new"))
            continue
        ptok = _metric_token(pcell)
        direction = "same"
        if cell.value is not None and pcell.value is not None:
            direction = _dir_of(cell.value, pcell.value)
        items.append(ItemDelta(key=f"metric:{iid}", changed=(tok != ptok), today=tok, prior=ptok,
                               direction=direction))

    # prices
    pprice = {p.model: p for p in prior.prices}
    for p in current.prices:
        pp = pprice.get(p.model)
        if pp is None:
            items.append(ItemDelta(key=f"price:{p.model}", changed=True,
                                   today=f"${p.usdPerGpuHour:g}/GPU-hr", direction="new"))
            continue
        changed, direction = _price_changed(p.usdPerGpuHour, pp.usdPerGpuHour)
        items.append(ItemDelta(key=f"price:{p.model}", changed=changed,
                               today=f"${p.usdPerGpuHour:g}/GPU-hr",
                               prior=f"${pp.usdPerGpuHour:g}/GPU-hr", direction=direction))

    # binding constraint (AMENDED 2026-07-11 — feeds the exec top band + the alert ladder's
    # constraint-rotated trigger; None-safe: older scorecards may carry no categoryStatus)
    if current.constraintLabel is not None:
        if prior.constraintLabel is None:
            items.append(ItemDelta(key="status:constraint", changed=True,
                                   today=current.constraintLabel, direction="new"))
        else:
            items.append(ItemDelta(key="status:constraint",
                                   changed=(current.constraintLabel != prior.constraintLabel),
                                   today=current.constraintLabel, prior=prior.constraintLabel,
                                   direction=("same" if current.constraintLabel == prior.constraintLabel
                                              else "new")))

    # theses — movement from the current book's timestamps vs this horizon's prior asOf
    if book is not None and prior_asof is not None:
        _DIR = {1: "up", -1: "down", 0: "same"}
        for e in book.standing():
            moved = days_between(e.lastChangedAsOf, prior_asof) > 0
            items.append(ItemDelta(key=f"thesis:{e.id}", changed=moved,
                                   today=f"{e.conviction}/{e.lastVerdict}",
                                   direction=(_DIR.get(e.lastDirection, "same") if moved else "same")))

    return HorizonDiff(horizon=name, lookbackDays=days, priorAsOf=prior_asof, items=items)


def _annotate_unchanged_since(horizons: list[HorizonDiff]) -> None:
    """For every item key, set unchangedSince to the asOf of the FARTHEST-back sampled run
    that is unchanged contiguously from today outward (1d, then 7d, then 30d). A change at a
    nearer horizon stops the walk, so a value that reverted can never claim 'since <30d>'.
    Only horizons that actually have a prior run participate."""
    ordered = sorted(horizons, key=lambda h: h.lookbackDays)   # 1, 7, 30
    by_key: dict[str, list[tuple[HorizonDiff, ItemDelta]]] = {}
    for h in ordered:
        for it in h.items:
            by_key.setdefault(it.key, []).append((h, it))
    for key, pairs in by_key.items():
        since: Optional[str] = None
        for h, it in pairs:            # already 1 -> 7 -> 30
            if it.changed:
                break
            since = h.priorAsOf        # unchanged this far back
        if since is not None:
            for _h, it in pairs:
                if not it.changed:
                    it.unchangedSince = since


def build_change_report(store_dir, sc: Scorecard, book: Optional[ThesisBook] = None,
                        prices_by_days: Optional[dict[int, list[PriceCell]]] = None) -> ChangeReport:
    """Assemble the three-horizon change report. prices_by_days maps a lookback in days
    (0 = today, then each LOOKBACK) to that column's PriceCell list — the caller reads them
    from the Stage-5 feed (Task 4); omit for a price-free report. Pure projection over stored
    scorecards; the target dates are calendar-day offsets of period_end(sc.asOf), so skipped
    days resolve to the nearest run at/before (D3)."""
    prices_by_days = prices_by_days or {}
    current = build_state(sc, book, prices_by_days.get(0))
    target0 = period_end(sc.asOf)
    horizons: list[HorizonDiff] = []
    priors: dict[str, Optional[StateVector]] = {}   # AMENDED 2026-07-11: kept for the top band
    for name, days in LOOKBACKS:
        target = target0 - datetime.timedelta(days=days)
        prior_path = nearest_run_at_or_before(store_dir, sc.categoryId, target)
        prior_state = prior_asof = None
        if prior_path is not None:
            prior_sc = load_scorecard(prior_path)
            prior_asof = prior_sc.asOf
            prior_state = build_state(prior_sc, None, prices_by_days.get(days))
        priors[name] = prior_state
        horizons.append(diff_states(name, days, current, prior_state, prior_asof, book))
    _annotate_unchanged_since(horizons)
    return ChangeReport(asOf=sc.asOf, horizons=horizons, priors=priors)
