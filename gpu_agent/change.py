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
from gpu_agent import bands

# Headline-metric selectors (registry indicator ids). Tier 2 rental price comes from the
# price feed (PriceCell), not a finding, so it is not in SCARCITY_INDICATORS.
SCARCITY_INDICATORS = ("leadTimes", "S10")   # lead times + whole-chain packaging/HBM inventory
MONEY_INDICATORS = ("vendorRevenueGuidance", "rpoBacklog", "grossMargin")
# (name, calendar-day lookback) — the three horizons of the change-first lead (D3).
LOOKBACKS = (("yesterday", 1), ("last week", 7), ("last month", 30))
_PRICE_REL_TOL = 0.01   # mirrors price_track.REL_TOL — "flat" band for a rental price move
# Verdicts that count as a real thesis MOVE. "reaffirmed" re-stamps lastChangedAsOf without a
# real move (thesis.py applies every non-reversal judgment), so a timestamp-only predicate
# degenerates under daily cadence; spec 2026-07-11 §4 counts strengthened/weakened/challenged
# only. Known accepted gap (user-accepted): a conviction promotion carried by a reaffirmed
# verdict won't read as a move until per-run book state exists (F79).
_MOVED_VERDICTS = frozenset({"strengthened", "weakened", "broken"})


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
    prior_asof (stored scorecards don't embed past book state — see the Task 3 assumption),
    AND the verdict must be in _MOVED_VERDICTS — "reaffirmed" re-stamps the timestamp without
    a real move (spec 2026-07-11 §4). prior=None (no run at/before this horizon) -> empty
    items list."""
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

    # theses — movement from the current book's timestamps vs this horizon's prior asOf,
    # gated on _MOVED_VERDICTS: a plain reaffirmation re-stamps the timestamp but is not a move
    if book is not None and prior_asof is not None:
        _DIR = {1: "up", -1: "down", 0: "same"}
        for e in book.standing():
            moved = (days_between(e.lastChangedAsOf, prior_asof) > 0
                     and e.lastVerdict in _MOVED_VERDICTS)
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


# ---------------------------------------------------------------------------
# AMENDED 2026-07-11 — executive alert ladder (spec 2026-07-11 §4). Rule-based v1;
# F79 swaps the trigger definitions for sigma-bands, keeping AlertState/fold intact.

_ALERT_RANK = {"green": 0, "yellow": 1, "orange": 2, "red": 3}
_BAND_RANK = ["contracting"] + [w for _, w in reversed(bands.BANDS)]  # mirrors bands._WORD_RANK
_YELLOW_RULES = ("gap-band-changed", "high-call-moved", "constraint-rotated", "calls-co-move")


class AlertState(BaseModel):
    color: str                        # displayed color after anti-flapping
    priorColor: Optional[str] = None  # prior run's displayed color; None on the first run
    rawColor: str = "green"           # today's raw ladder evaluation (pre-fold)
    triggers: list[str] = Field(default_factory=list)   # today's fired rule ids


def _band_rank(word: str) -> int:
    return _BAND_RANK.index(word)


def _thesis_moves_between(book: ThesisBook, after_asof: str, at_or_before_asof: str):
    """Standing theses whose lastChangedAsOf lies in (after_asof, at_or_before_asof] AND whose
    lastVerdict is in _MOVED_VERDICTS — a plain reaffirmation re-stamps the timestamp without
    a real move (spec 2026-07-11 §4). Current-book timestamps (see the Task 5b assumption
    note)."""
    _DIR = {1: "up", -1: "down", 0: "same"}
    out = []
    for e in book.standing():
        if (days_between(e.lastChangedAsOf, after_asof) > 0
                and days_between(at_or_before_asof, e.lastChangedAsOf) >= 0
                and e.lastVerdict in _MOVED_VERDICTS):
            out.append((e, _DIR.get(e.lastDirection, "same")))
    return out


def _high_break_between(book: ThesisBook, after_asof: str, at_or_before_asof: str) -> bool:
    """A high-conviction call that broke/retired inside the window. Iterates ALL entries —
    standing() excludes retired, which is exactly what a break produces."""
    for e in book.entries:
        if e.conviction != "high":
            continue
        if not (e.status == "retired" or e.lastVerdict == "broken"):
            continue
        if (days_between(e.lastChangedAsOf, after_asof) > 0
                and days_between(at_or_before_asof, e.lastChangedAsOf) >= 0):
            return True
    return False


def _raw_alert(cur: StateVector, prior7: Optional[StateVector], prior7_asof: Optional[str],
               book: Optional[ThesisBook]) -> tuple[str, list[str]]:
    """One run's raw ladder color. First match from the top wins; co-occurrence is counted at
    the RULE level (two rules fed by one event still count as two — spec §4)."""
    triggers: list[str] = []
    if prior7 is not None:
        if bands.band_word(cur.sdgi) != bands.band_word(prior7.sdgi):
            triggers.append("gap-band-changed")
        if (cur.constraintLabel and prior7.constraintLabel
                and cur.constraintLabel != prior7.constraintLabel):
            triggers.append("constraint-rotated")
    if book is not None and prior7_asof is not None:
        moves = _thesis_moves_between(book, prior7_asof, cur.asOf)
        if any(e.conviction == "high" for e, _d in moves):
            triggers.append("high-call-moved")
        for d in ("up", "down"):
            if sum(1 for _e, dd in moves if dd == d) >= 2:
                triggers.append("calls-co-move")
                break
        if _high_break_between(book, prior7_asof, cur.asOf):
            triggers.append("high-call-broke")
    if prior7 is not None:
        demand_worsened = _band_rank(bands.band_word(cur.demand)) < _band_rank(
            bands.band_word(prior7.demand))
        gap_toward_glut = round(cur.sdgi, _ROUND) < round(prior7.sdgi, _ROUND)
        if demand_worsened and gap_toward_glut:
            triggers.append("demand-reversal")   # asymmetric: this pair ALONE escalates

    y_hits = [t for t in triggers if t in _YELLOW_RULES]
    if "high-call-broke" in triggers and "gap-band-changed" in triggers:
        return "red", triggers
    if "high-call-broke" in triggers or "demand-reversal" in triggers or len(y_hits) >= 2:
        return "orange", triggers
    if y_hits:
        return "yellow", triggers
    return "green", triggers


def _raw_alert_for(store_dir, sc_run: Scorecard, book: Optional[ThesisBook]) -> tuple[str, list[str]]:
    cur = build_state(sc_run)
    target = period_end(sc_run.asOf) - datetime.timedelta(days=7)
    prior_path = nearest_run_at_or_before(store_dir, sc_run.categoryId, target)
    prior7 = prior7_asof = None
    if prior_path is not None:
        prior_sc = load_scorecard(prior_path)
        prior7, prior7_asof = build_state(prior_sc), prior_sc.asOf
    return _raw_alert(cur, prior7, prior7_asof, book)


def _fold_displayed(raws: list[str]) -> list[str]:
    """Anti-flapping: escalation is immediate; a color steps DOWN only after 2 consecutive
    runs whose raw evaluation sits below the held color (spec §4). displayed[i] is:
    raw[i] when raw[i] >= displayed[i-1]; the held color when this is the FIRST calm run
    (raw[i-1] had earned the held color); otherwise the higher of the last two raws."""
    disp: list[str] = []
    for i, raw in enumerate(raws):
        if i == 0:
            disp.append(raw)
            continue
        held = disp[i - 1]
        if _ALERT_RANK[raw] >= _ALERT_RANK[held]:
            disp.append(raw)
        elif _ALERT_RANK[raws[i - 1]] >= _ALERT_RANK[held]:
            disp.append(held)
        else:
            disp.append(max(raw, raws[i - 1], key=lambda c: _ALERT_RANK[c]))
    return disp


def alert_state(store_dir, sc: Scorecard, book: Optional[ThesisBook] = None) -> AlertState:
    """Today's displayed alert. Recomputes every stored run's raw color chronologically and
    folds the de-escalation memory — pure projection, no stored field, replayable."""
    cat_dir = Path(store_dir) / sc.categoryId
    runs: dict[str, tuple[int, Path]] = {}
    if cat_dir.is_dir():
        for p in sorted(cat_dir.iterdir()):
            m = _VERSION_RE.match(p.name)
            if not m:
                continue
            as_of, ver = m.group(1), int(m.group(2))
            if as_of == sc.asOf:
                continue          # today is evaluated from `sc`, not the store copy
            if as_of not in runs or ver > runs[as_of][0]:
                runs[as_of] = (ver, p)
    ordered = sorted(runs, key=period_end)
    raws = [_raw_alert_for(store_dir, load_scorecard(runs[a][1]), book)[0] for a in ordered]
    raw_today, triggers = _raw_alert_for(store_dir, sc, book)
    raws.append(raw_today)
    disp = _fold_displayed(raws)
    return AlertState(color=disp[-1], priorColor=(disp[-2] if len(disp) > 1 else None),
                      rawColor=raw_today, triggers=triggers)


# --- Stage-5 price-feed adapter (the assumption seam) ---------------------------------
#
# DEVIATION (plan-sanctioned seam): Stage 5 shipped headline_prices(as_of, data_dir)
# -> dict[model, usd] + PricePoint.usd_per_gpu_hour/gpu_class instead of the assumed
# read_prices/PricePoint.usdPerGpuHour/.column/.custom; adapter consumes headline_prices
# (custom silicon excluded upstream); asOfColumn carries the requested label (no single
# column exists after median-of-medians). See tests/test_change_pricefeed.py.

def price_cells_from_feed(as_of: str, *, read=None, scrape_dir=None) -> list[PriceCell]:
    """Read the Stage-5 headline price feed for `as_of` and map it to PriceCell, sorted by
    model for determinism. `read` defaults to gpu_agent.pricefeed.headline_prices, which
    already excludes custom silicon (it filters gpu_class == "gpu") and already collapses
    each headline model to one representative $/GPU-hr (median of per-provider medians) —
    this adapter does not re-implement that logic, only maps its dict result. `scrape_dir`
    keeps the plan's public kwarg name but maps to the feed's `data_dir=` kwarg. asOfColumn
    carries the REQUESTED label: after cross-provider aggregation there is no single
    underlying scrape column, so the requested label is the honest, deterministic
    provenance."""
    if read is None:
        from gpu_agent.pricefeed import headline_prices as read   # local import: sole pricefeed seam
    kw = {"data_dir": scrape_dir} if scrape_dir is not None else {}
    prices = read(as_of, **kw)
    return [PriceCell(model=m, usdPerGpuHour=v, asOfColumn=as_of, custom=False)
            for m, v in sorted(prices.items())]


def prices_by_lookback(as_of: str, *, read=None, scrape_dir=None) -> dict[int, list[PriceCell]]:
    """PriceCell lists keyed by lookback-in-days (0 = today, then each LOOKBACK), each read
    from the feed's nearest-at/before selection for that date — the dict build_change_report's
    `prices_by_days` expects. Deterministic: labels derive from period_end(as_of), never the
    clock."""
    end = period_end(as_of)
    out = {0: price_cells_from_feed(as_of, read=read, scrape_dir=scrape_dir)}
    for _name, days in LOOKBACKS:
        label = (end - datetime.timedelta(days=days)).isoformat()
        out[days] = price_cells_from_feed(label, read=read, scrape_dir=scrape_dir)
    return out
