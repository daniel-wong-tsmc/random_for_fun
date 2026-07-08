# F78 Stage 6 — Change engine + change-first renderer + quick-glance tiers (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the two coupled pieces that turn the daily brief change-first: (A) a **change engine** (`gpu_agent/change.py`) that builds today's STATE VECTOR and diffs it POINT-IN-TIME against the nearest stored run at/before `asOf−1d / −7d / −30d`, emitting per-item deltas and explicit "unchanged since <date>" states; and (B) a **change-first renderer** in `gpu_agent/report.py` that leads with the three horizon change lines and the three quick-glance TIERS, then the ranked calls (highest-conviction / most-moved first), with real-age tags on carried facts and a length budget above the appendix. **Delivers F64** (the change lines are the trigger-first daily lead) **and F77** (importance-ordered, consolidated, length-capped). Share price is EXCLUDED.

**Architecture:** The renderer and the change engine are **pure projections** of stored scorecards + the price feed — replayable for `$0`, no wall-clock (all day math via `gpu_agent/asof.py`). `report.find_prior` already does a single "vs prior" pick by `(asOf, version)`; Task 2 generalizes it to a calendar-day "nearest stored run at/before a target date" used at three lookbacks. The state vector holds the six dimension ratings, the demand/supply momentum + gap, the standing theses (conviction / verdict / streak / challenged), the headline scarcity + money metrics, and the price-feed rental snapshot. `change.py` imports one-way from `report.py`/`asof.py`/`schema` (no cycle — `report.py` never imports `change.py`; the renderer receives the `ChangeReport` as data via a new optional `change=` kwarg, so its existing behavior is byte-identical when `change is None`).

**Tech Stack:** Python 3.11, pydantic v2, pytest. Run Python as `.venv/Scripts/python` from repo root (from a worktree: `../../.venv/Scripts/python`; one shared root venv — never create a per-worktree venv).

**Spec:** `docs/superpowers/specs/2026-07-08-f78-daily-change-first-brief-design.md` §5.5 (change engine, D3), §5.6 (quick-glance tiers, D8), §5.8 (renderer, D7 — delivers F64 + F77), decisions D3/D7/D8 in §4, §6 (data flow). This is **F78 Stage 6 of 6** — built **LAST**.

## Dependencies (this stage is built last)

This plan assumes the earlier stages have landed on the branch base. Confirm before starting:

- **Stage 1** — `gpu_agent/asof.py` exists exposing `period_end(label) -> date`, `days_between(later, earlier) -> int`, `class AsOfError(ValueError)`; wiki decay is calendar-day. **On the current root checkout `asof.py` does NOT yet exist** — the executing agent MUST branch off a base where Stages 1–5 are merged, and first run `.venv/Scripts/python -c "import gpu_agent.asof, gpu_agent.pricefeed"` to confirm. If either import fails, stop: the base is wrong.
- **Stage 2** — thesis pacing on calendar days (`gpu_agent/thesis.py`); no interface consumed here beyond the existing `ThesisBook`/`ThesisEntry` fields (`conviction`, `lastVerdict`, `lastDirection`, `streak`, `pendingChallenge`, `lastChangedAsOf`, `falsifiableTrigger`, `title`, `id`, `.standing()`).
- **Stage 3** — aged corpus; no direct interface consumed here (the change engine reads finished scorecards, not the corpus).
- **Stage 5** — `gpu_agent/pricefeed.py` price feed. **Interface ASSUMED** (isolated to Task 4, the only seam that imports it): a callable `read_prices(as_of: str, *, scrape_dir: Path = Path("gpu_agent/scrape_data")) -> list[PricePoint]` returning **on-demand, USA-region, `$/GPU-hour`** representative prices for the column **nearest at/before** `as_of`, where each `PricePoint` exposes `.model` (GPU model string, e.g. `"H100"`/`"B200"`), `.usdPerGpuHour` (float), `.column` (the `YYYY-MM-DD` column actually read), and `.custom` (bool — `True` for custom silicon like Trainium/TPU, which is NOT a GPU and is excluded from the rental tier). **If the real Stage-5 names differ, only Task 4's adapter (`change.price_cells_from_feed`) changes** — the engine and renderer consume the engine-local `PriceCell`, never `pricefeed` directly. State any deviation in the Task 4 commit body.

## Global Constraints (copy verbatim into every commit's reasoning)

- **Pure projection / determinism:** the renderer and change engine are pure projections of stored scorecards + the price feed — replayable for `$0`, no wall-clock (day math via `asof`). No `datetime.now()`, `Date.now()`, `Math.random()`. Same inputs → byte-identical output.
- **Frozen core untouched:** do NOT modify `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`. `report.py`, `reader.py`, `brief.py` are NOT frozen core and may be edited; `change.py` is new.
- **Reader contract:** output prose above the appendix is read by a non-technical TSMC executive — no AI/doctrine/internal jargon; reuse `reader.py`'s label maps + acronym allowlist. Every above-`reader.APPENDIX_DIVIDER` line must pass `reader.lint_acronyms`.
- **No brain-prompt changes → `tests/test_evals_baseline_pin.py` stays green.** If that pin goes red you touched a prompt file — stop and re-scope. This feature is code + a DATA edit to `registry/acronyms.json`, not prompt text.
- **Execution happens in a git worktree** per repo discipline: feature work in `.worktrees/<name>` on a claimed branch, never the root checkout's main. `git log --oneline -1` immediately before every commit (concurrent-instance guard).
- **Suite green at every commit.** Baseline on this root checkout (pre-Stage-1): `1153 passed, 5 skipped`. Re-baseline on the actual Stage-5 branch base before starting and record the number.
- **Windows:** use the Bash tool for `>` redirects / heredocs; no double quotes inside `git commit -m` under PowerShell (use a bash heredoc). Commit trailer names the ACTUAL implementer model.

---

### Task 1: `change.py` — state-vector models + `build_state`

Build today's STATE VECTOR from a finished scorecard (+ optional thesis book + optional price snapshot). Pure; no I/O.

**Files:**
- Create: `gpu_agent/change.py`
- Create: `tests/test_change_state.py`

**Interfaces:**
- Consumes: `gpu_agent.report.compute_sdgi`; `gpu_agent.schema.scorecard.{Scorecard, DIMENSIONS}`; `gpu_agent.thesis.ThesisBook`.
- Produces: pydantic models `DimCell`, `ThesisCell`, `MetricCell`, `PriceCell`, `StateVector`; `SCARCITY_INDICATORS`, `MONEY_INDICATORS`, `LOOKBACKS` constants; `build_state(sc, book=None, prices=None) -> StateVector`; `_latest_metric(sc, indicator_id)` helper.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_change_state.py
from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, DimensionRating
from gpu_agent.schema.finding import Finding, Kind, Value, Impact, Evidence, Confidence
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import build_state, PriceCell, SCARCITY_INDICATORS, MONEY_INDICATORS


def _conf():
    return Confidence(level="medium", basis="b")


def _dim(rating, direction="steady"):
    return DimensionRating(rating=rating, direction=direction, confidence=_conf(),
                           findingIds=[], rationale="r")


def _finding(iid, *, number=None, unit=None, statement="s", date="2026-05-05",
             captured="2026-07-08T00:00:00Z", observed="2026-05-05", mag=2, fid=None):
    return Finding(
        id=fid or f"{iid}-x-1", statement=statement, kind=Kind.measured,
        value=(Value(number=number, unit=unit) if number is not None else None),
        trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=date,
                           excerpt="e", tier="primary")],
        confidence=_conf(), asOf="2026-07-08", indicatorId=iid, side="demand",
        polarityDemand=1, polaritySupply=0, magnitude=mag, entity="nvidia",
        observedAt=observed, capturedAt=captured)


def _sc(as_of="2026-07-08", dmi=0.57, smi=0.29, dims=None, findings=None):
    return Scorecard(
        categoryId="chips.merchant-gpu", asOf=as_of,
        findings=findings or [],
        dimensionRatings=dims or {},
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
        narrative="n", confidence=_conf())


def _entry(eid="demand-durability", **kw):
    f = dict(id=eid, title="Demand outruns capacity",
             statement="Demand keeps outrunning capacity.", lens="demand",
             status="registered", conviction="high", lastVerdict="reaffirmed",
             lastDirection=0, streak=3, mechanism="m",
             falsifiableTrigger="Backlog growth falls below shipment growth.",
             sensitivity="capex", createdAsOf="2026-06", lastChangedAsOf="2026-07-05",
             lastJudgedAsOf="2026-07-05")
    f.update(kw)
    return ThesisEntry(**f)


def test_dimensions_and_indices_captured():
    sc = _sc(dmi=0.57, smi=0.29,
             dims={"momentum": _dim("Very strong", "improving"),
                   "moat": _dim("Mixed", "improving")})
    st = build_state(sc)
    assert st.asOf == "2026-07-08"
    assert st.dimensions["momentum"].rating == "Very strong"
    assert st.dimensions["momentum"].direction == "improving"
    assert st.demand == 0.57 and st.supply == 0.29
    # sdgi = dmi - smi when not stored
    assert abs(st.sdgi - 0.28) < 1e-9


def test_standing_theses_captured_retired_excluded():
    book = ThesisBook(categoryId="chips.merchant-gpu",
                      entries=[_entry(), _entry(eid="gone", status="retired")])
    st = build_state(_sc(), book=book)
    assert set(st.theses) == {"demand-durability"}
    cell = st.theses["demand-durability"]
    assert cell.conviction == "high" and cell.streak == 3 and cell.challenged is False


def test_headline_metrics_latest_vintage_and_age_source():
    old = _finding("grossMargin", number=53.0, unit="pct", date="2026-05-05",
                   captured="2026-07-04T00:00:00Z", fid="gm-old")
    new = _finding("grossMargin", number=55.0, unit="pct", date="2026-05-20",
                   captured="2026-07-08T00:00:00Z", fid="gm-new")
    lead = _finding("leadTimes", statement="lead times ~40 weeks", date="2026-06-30",
                    captured="2026-07-08T00:00:00Z", fid="lt-1")
    st = build_state(_sc(findings=[old, new, lead]))
    # latest vintage wins (captured 07-08 > 07-04)
    assert st.metrics["grossMargin"].value == 55.0
    assert st.metrics["grossMargin"].observedAt == "2026-05-20"   # newest evidence date -> age source
    assert st.metrics["grossMargin"].tier == "money"
    assert st.metrics["leadTimes"].tier == "scarcity"
    assert "grossMargin" in MONEY_INDICATORS and "leadTimes" in SCARCITY_INDICATORS


def test_prices_passed_through():
    prices = [PriceCell(model="B200", usdPerGpuHour=3.99, asOfColumn="2026-07-08")]
    st = build_state(_sc(), prices=prices)
    assert st.prices[0].model == "B200" and st.prices[0].usdPerGpuHour == 3.99
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_change_state.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.change'`.

- [ ] **Step 3: Write the implementation**

```python
# gpu_agent/change.py
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

    return StateVector(
        asOf=sc.asOf, dimensions=dims,
        demand=sc.demandSupply.dmiContribution, supply=sc.demandSupply.smiContribution,
        sdgi=compute_sdgi(sc), theses=theses, metrics=metrics,
        prices=list(prices or []))
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_change_state.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/change.py tests/test_change_state.py
git commit -m "$(cat <<'EOF'
feat(F78-6): change engine state vector — build_state over scorecard + book + price snapshot

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `change.py` — nearest stored run at/before a calendar-day target

Generalize `report.find_prior` (which picks one "prior" by `(asOf, version)`) to "the nearest stored run whose asOf period-end is `<=` a target date" — the D3 "nearest at/before" rule that makes the three lookbacks robust to skipped days.

**Files:**
- Modify: `gpu_agent/change.py`
- Create: `tests/test_change_nearest.py`

**Interfaces:**
- Consumes: `gpu_agent.asof.{period_end, AsOfError}`; `gpu_agent.report._VERSION_RE`.
- Produces: `nearest_run_at_or_before(store_dir, category_id, target, *, before=None) -> Optional[Path]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_change_nearest.py
from __future__ import annotations
import datetime
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence
from gpu_agent.change import nearest_run_at_or_before


def _write(store, as_of, version, dmi=0.5, smi=0.3):
    cat = store / "chips.merchant-gpu"
    cat.mkdir(parents=True, exist_ok=True)
    sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                   demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
                   narrative="n", confidence=Confidence(level="medium", basis="b"))
    (cat / f"{as_of}-v{version}.json").write_text(sc.model_dump_json(), "utf-8")


def test_exact_day_hit(tmp_path):
    _write(tmp_path, "2026-07-01", 1)
    _write(tmp_path, "2026-07-07", 1)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 7))
    assert got.name == "2026-07-07-v1.json"


def test_skipped_day_falls_back_to_nearest_before(tmp_path):
    # target is 07-07 but only 07-05 exists at/before it -> nearest at/before wins.
    _write(tmp_path, "2026-07-01", 1)
    _write(tmp_path, "2026-07-05", 1)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 7))
    assert got.name == "2026-07-05-v1.json"


def test_highest_version_same_day(tmp_path):
    _write(tmp_path, "2026-07-05", 1)
    _write(tmp_path, "2026-07-05", 2)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 6))
    assert got.name == "2026-07-05-v2.json"


def test_month_grain_period_end(tmp_path):
    # month-grain 2026-06 has period-end 2026-06-30 -> counts as at/before a July target.
    _write(tmp_path, "2026-06", 12)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 1))
    assert got.name == "2026-06-v12.json"


def test_nothing_at_or_before_returns_none(tmp_path):
    _write(tmp_path, "2026-07-10", 1)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 1))
    assert got is None


def test_before_excludes_current_run(tmp_path):
    _write(tmp_path, "2026-07-08", 1)
    _write(tmp_path, "2026-07-08", 2)
    # exclude the current (2026-07-08, v2); nearest strictly-below is v1 same day.
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu",
                                   datetime.date(2026, 7, 8), before=("2026-07-08", 2))
    assert got.name == "2026-07-08-v1.json"


def test_missing_category_dir_returns_none(tmp_path):
    assert nearest_run_at_or_before(tmp_path, "nope", datetime.date(2026, 7, 1)) is None
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_change_nearest.py -q`
Expected: FAIL with `ImportError: cannot import name 'nearest_run_at_or_before'`.

- [ ] **Step 3: Add the implementation to `gpu_agent/change.py`**

Append below `build_state`:

```python
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
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_change_nearest.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/change.py tests/test_change_nearest.py
git commit -m "$(cat <<'EOF'
feat(F78-6): nearest-run-at/before selector (generalizes find_prior to a calendar-day target)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `change.py` — diff engine, thesis movement, unchanged-since, `build_change_report`

Diff today's state against each horizon's nearest prior state (dimensions / indices / metrics / prices are two-snapshot point-in-time diffs); thesis movement is derived from the CURRENT book's `lastChangedAsOf` vs the horizon's prior asOf (see the assumption note below). Then annotate the consolidated "unchanged since <date>".

**Assumption (state explicitly, spec §5.5):** stored scorecards do NOT embed the thesis book's per-run state, so a two-snapshot thesis diff is not available from the store. The engine therefore reads thesis movement from the *current* book's timestamps: a standing thesis "moved" within a horizon iff its `lastChangedAsOf` is strictly after that horizon's prior-run asOf (`asof.days_between(entry.lastChangedAsOf, prior_asof) > 0`). This uses only stored artifacts and stays deterministic. Dimensions, demand/supply/gap, headline metrics, and prices are true two-snapshot diffs.

**Files:**
- Modify: `gpu_agent/change.py`
- Create: `tests/test_change_diff.py`

**Interfaces:**
- Consumes: Task 1/2 above; `gpu_agent.report.load_scorecard`; `gpu_agent.asof.{period_end, days_between}`.
- Produces: models `ItemDelta`, `HorizonDiff`, `ChangeReport`; `diff_states(name, days, current, prior, prior_asof, book) -> HorizonDiff`; `build_change_report(store_dir, sc, book=None, prices_by_days=None) -> ChangeReport`; internal `_index_token`, `_dir_of`, `_metric_token`, `_price_changed`, `_annotate_unchanged_since`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_change_diff.py
from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, DimensionRating
from gpu_agent.schema.finding import Confidence
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import build_state, build_change_report, diff_states, PriceCell


def _conf():
    return Confidence(level="medium", basis="b")


def _dim(rating, direction="steady"):
    return DimensionRating(rating=rating, direction=direction, confidence=_conf(),
                           findingIds=[], rationale="r")


def _sc(store, as_of, version, dmi, smi, dims):
    cat = store / "chips.merchant-gpu"
    cat.mkdir(parents=True, exist_ok=True)
    sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                   dimensionRatings=dims,
                   demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
                   narrative="n", confidence=_conf())
    (cat / f"{as_of}-v{version}.json").write_text(sc.model_dump_json(), "utf-8")
    return sc


def _entry(**kw):
    f = dict(id="demand-durability", title="Demand outruns capacity",
             statement="s", lens="demand", status="registered", conviction="high",
             lastVerdict="strengthened", lastDirection=1, streak=3, mechanism="m",
             falsifiableTrigger="t", sensitivity="s", createdAsOf="2026-06",
             lastChangedAsOf="2026-07-08", lastJudgedAsOf="2026-07-08")
    f.update(kw)
    return ThesisEntry(**f)


def test_dimension_change_and_direction():
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      dimensionRatings={"momentum": _dim("Very strong", "improving")},
                      demandSupply=DemandSupply(dmiContribution=0.6, smiContribution=0.3),
                      narrative="n", confidence=_conf()))
    prior = build_state(Scorecard(categoryId="c", asOf="2026-07-01", findings=[],
                        dimensionRatings={"momentum": _dim("Strong", "steady")},
                        demandSupply=DemandSupply(dmiContribution=0.4, smiContribution=0.3),
                        narrative="n", confidence=_conf()))
    hd = diff_states("last week", 7, cur, prior, "2026-07-01", None)
    dim = next(i for i in hd.items if i.key == "dim:momentum")
    assert dim.changed and dim.today.startswith("Very strong") and dim.prior.startswith("Strong")
    dem = next(i for i in hd.items if i.key == "index:demand")
    assert dem.changed and dem.direction == "up"
    sup = next(i for i in hd.items if i.key == "index:supply")
    assert not sup.changed and sup.direction == "same"


def test_thesis_moved_when_changed_after_prior_asof():
    book = ThesisBook(categoryId="c", entries=[_entry(lastChangedAsOf="2026-07-08")])
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf()), book=book)
    prior = build_state(Scorecard(categoryId="c", asOf="2026-07-01", findings=[],
                        demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                        narrative="n", confidence=_conf()))
    hd = diff_states("last week", 7, cur, prior, "2026-07-01", book)
    th = next(i for i in hd.items if i.key == "thesis:demand-durability")
    assert th.changed and th.direction == "up"   # lastDirection 1 -> up


def test_thesis_not_moved_when_change_precedes_prior_asof():
    book = ThesisBook(categoryId="c", entries=[_entry(lastChangedAsOf="2026-06-20")])
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf()), book=book)
    hd = diff_states("last week", 7, cur, cur, "2026-07-01", book)
    th = next(i for i in hd.items if i.key == "thesis:demand-durability")
    assert not th.changed


def test_price_change_uses_rel_tol():
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf()),
                      prices=[PriceCell(model="B200", usdPerGpuHour=3.75, asOfColumn="2026-07-08")])
    prior = build_state(Scorecard(categoryId="c", asOf="2026-07-01", findings=[],
                        demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                        narrative="n", confidence=_conf()),
                        prices=[PriceCell(model="B200", usdPerGpuHour=3.99, asOfColumn="2026-07-01")])
    hd = diff_states("last week", 7, cur, prior, "2026-07-01", None)
    price = next(i for i in hd.items if i.key == "price:B200")
    assert price.changed and price.direction == "down"


def test_build_change_report_three_horizons_and_unchanged_since(tmp_path):
    # Runs at -30d, -7d, -1d relative to 2026-07-08 (period-end math): 06-08, 07-01, 07-07.
    steady = {"moat": _dim("Mixed", "improving")}
    _sc(tmp_path, "2026-06-08", 1, 0.5, 0.3, steady)
    _sc(tmp_path, "2026-07-01", 1, 0.5, 0.3, steady)
    _sc(tmp_path, "2026-07-07", 1, 0.5, 0.3, steady)
    today = Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                      dimensionRatings=steady,
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf())
    rpt = build_change_report(tmp_path, today)
    assert [h.horizon for h in rpt.horizons] == ["yesterday", "last week", "last month"]
    assert [h.priorAsOf for h in rpt.horizons] == ["2026-07-07", "2026-07-01", "2026-06-08"]
    # moat never moved across all three sampled runs -> unchanged since the oldest (06-08).
    moat = next(i for i in rpt.horizons[0].items if i.key == "dim:moat")
    assert moat.changed is False
    assert moat.unchangedSince == "2026-06-08"


def test_build_change_report_no_run_at_horizon(tmp_path):
    _sc(tmp_path, "2026-07-07", 1, 0.5, 0.3, {})
    today = Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf())
    rpt = build_change_report(tmp_path, today)
    last_month = next(h for h in rpt.horizons if h.horizon == "last month")
    assert last_month.priorAsOf is None and last_month.items == []
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_change_diff.py -q`
Expected: FAIL (`ImportError: cannot import name 'build_change_report'`).

- [ ] **Step 3: Add the implementation to `gpu_agent/change.py`**

Append below `nearest_run_at_or_before`:

```python
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
    for name, days in LOOKBACKS:
        target = target0 - datetime.timedelta(days=days)
        prior_path = nearest_run_at_or_before(store_dir, sc.categoryId, target)
        prior_state = prior_asof = None
        if prior_path is not None:
            prior_sc = load_scorecard(prior_path)
            prior_asof = prior_sc.asOf
            prior_state = build_state(prior_sc, None, prices_by_days.get(days))
        horizons.append(diff_states(name, days, current, prior_state, prior_asof, book))
    _annotate_unchanged_since(horizons)
    return ChangeReport(asOf=sc.asOf, horizons=horizons)
```

Note: `dim:` direction is coarse here ("up" when the token differs); the renderer (Task 5) refines the dimension arrow from the rating rank (`report.RATING_SCALE`) so the change lines show a true ↑/↓. The engine keeps the raw tokens; ranking lives in the renderer.

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_change_diff.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/change.py tests/test_change_diff.py
git commit -m "$(cat <<'EOF'
feat(F78-6): change-report diff — point-in-time deltas, thesis movement, unchanged-since

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `change.py` — Stage-5 price-feed adapter (the assumption seam)

The single place `pricefeed` is imported. Maps the Stage-5 `PricePoint`s at each lookback column into the engine-local `PriceCell` dict `build_change_report` expects, dropping custom silicon from the rental tier.

**Files:**
- Modify: `gpu_agent/change.py`
- Create: `tests/test_change_pricefeed.py`

**Interfaces:**
- Consumes (ASSUMED, see Dependencies): `gpu_agent.pricefeed.read_prices(as_of, *, scrape_dir=...) -> list[PricePoint]` with `.model`, `.usdPerGpuHour`, `.column`, `.custom`.
- Produces: `price_cells_from_feed(as_of, *, read=None, scrape_dir=None) -> list[PriceCell]`; `prices_by_lookback(as_of, *, read=None) -> dict[int, list[PriceCell]]` (keys `0` + each `LOOKBACKS` day). `read` is injectable so the test stubs the feed and Stage-5's real signature is never hard-wired.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_change_pricefeed.py
from __future__ import annotations
from types import SimpleNamespace
from gpu_agent.change import price_cells_from_feed, prices_by_lookback


def _stub_point(model, price, column, custom=False):
    return SimpleNamespace(model=model, usdPerGpuHour=price, column=column, custom=custom)


def test_maps_points_and_drops_custom_silicon():
    def read(as_of, **kw):
        return [_stub_point("B200", 3.99, as_of),
                _stub_point("Trainium3", 1.20, as_of, custom=True)]
    cells = price_cells_from_feed("2026-07-08", read=read)
    assert [c.model for c in cells] == ["B200"]           # Trainium (custom) excluded
    assert cells[0].usdPerGpuHour == 3.99 and cells[0].asOfColumn == "2026-07-08"


def test_prices_by_lookback_reads_all_four_columns():
    seen = []

    def read(as_of, **kw):
        seen.append(as_of)
        return [_stub_point("B200", 4.0, as_of)]

    got = prices_by_lookback("2026-07-08", read=read)
    # today (0) + 1 + 7 + 30 day offsets of period_end(2026-07-08)
    assert set(got) == {0, 1, 7, 30}
    assert seen == ["2026-07-08", "2026-07-07", "2026-07-01", "2026-06-08"]
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_change_pricefeed.py -q`
Expected: FAIL (`ImportError: cannot import name 'price_cells_from_feed'`).

- [ ] **Step 3: Add the implementation to `gpu_agent/change.py`**

Append below `build_change_report`:

```python
def price_cells_from_feed(as_of: str, *, read=None, scrape_dir=None) -> list[PriceCell]:
    """Read the Stage-5 price feed for `as_of` and map GPU rows to PriceCell (custom silicon
    excluded — it isn't a GPU rental). `read` defaults to gpu_agent.pricefeed.read_prices;
    injectable so tests stub it and the real Stage-5 signature is isolated here. If the real
    PricePoint field names differ from (.model/.usdPerGpuHour/.column/.custom), adjust ONLY
    this mapping."""
    if read is None:
        from gpu_agent.pricefeed import read_prices as read   # local import: sole pricefeed seam
    kw = {"scrape_dir": scrape_dir} if scrape_dir is not None else {}
    points = read(as_of, **kw)
    return [PriceCell(model=p.model, usdPerGpuHour=p.usdPerGpuHour,
                      asOfColumn=p.column, custom=getattr(p, "custom", False))
            for p in points if not getattr(p, "custom", False)]


def prices_by_lookback(as_of: str, *, read=None, scrape_dir=None) -> dict[int, list[PriceCell]]:
    """PriceCell lists keyed by lookback-in-days (0 = today, then each LOOKBACK), each read
    from the feed's nearest-at/before column for that date — the dict build_change_report's
    `prices_by_days` expects. Deterministic: columns derive from period_end(as_of), never the
    clock."""
    end = period_end(as_of)
    out = {0: price_cells_from_feed(as_of, read=read, scrape_dir=scrape_dir)}
    for _name, days in LOOKBACKS:
        label = (end - datetime.timedelta(days=days)).isoformat()
        out[days] = price_cells_from_feed(label, read=read, scrape_dir=scrape_dir)
    return out
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_change_pricefeed.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Confirm the assumed feed actually exists on the branch base**

Run: `.venv/Scripts/python -c "from gpu_agent.pricefeed import read_prices; print('ok')"`
Expected: `ok`. If this fails, Stage 5 has not landed — STOP and reconcile the branch base (see Dependencies). If it imports but the attribute names differ, adjust only `price_cells_from_feed` and record the deviation in the commit body.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/change.py tests/test_change_pricefeed.py
git commit -m "$(cat <<'EOF'
feat(F78-6): price-feed adapter (Stage-5 seam) — PricePoint -> PriceCell, custom silicon dropped

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `report.py` — the three horizon change lines (+ `reader.DIM_LABEL`)

Render `WHAT CHANGED` — the trigger-first daily lead (F64): one line per horizon (since yesterday / last week / last month) summarizing the moved items, with explicit "unchanged since <date>" when nothing moved. Above the fold, so exec-plain: dimension ids map through a new `reader.DIM_LABEL`, and the block must pass `reader.lint_acronyms`.

**Files:**
- Modify: `gpu_agent/reader.py` (add `DIM_LABEL`)
- Modify: `gpu_agent/report.py` (add `render_change_lines`)
- Create: `tests/test_report_change_lines.py`

**Interfaces:**
- Consumes: `change.ChangeReport`; `reader.DIM_LABEL`, `reader.indicator_label`; `report.RATING_SCALE`, `report.DIRECTION_ARROW`.
- Produces: `reader.DIM_LABEL: dict[str,str]`; `report.render_change_lines(change, registry) -> str`.

- [ ] **Step 1: Add `DIM_LABEL` to `gpu_agent/reader.py`**

After `STATUS_LABEL` (line ~23):

```python
# Six scorecard dimension ids -> exec-plain labels for above-the-fold change/quick-glance
# lines (the DIMENSION RATINGS appendix section keeps the raw ids). All pass lint_acronyms.
DIM_LABEL = {
    "momentum": "Demand momentum",
    "unitEconomics": "Unit economics",
    "competitiveStructure": "Competitive structure",
    "moat": "Moat",
    "bottleneck": "Supply bottleneck",
    "strategicRisk": "Strategic risk",
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_report_change_lines.py
from __future__ import annotations
from gpu_agent.change import ChangeReport, HorizonDiff, ItemDelta
from gpu_agent.report import render_change_lines
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent import reader


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def test_horizon_lines_lead_and_name_moves():
    cr = ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="dim:momentum", changed=True, today="Very strong/improving",
                      prior="Strong/steady", direction="up"),
            ItemDelta(key="price:B200", changed=True, today="$3.75/GPU-hr",
                      prior="$3.99/GPU-hr", direction="down")]),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[
            ItemDelta(key="dim:moat", changed=False, today="Mixed/improving",
                      unchangedSince="2026-06-08")]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf=None, items=[]),
    ])
    out = render_change_lines(cr, _reg())
    lines = out.splitlines()
    assert lines[0] == "WHAT CHANGED"
    assert "Since yesterday" in out and "(vs 2026-07-07)" in out
    assert "Demand momentum" in out            # DIM_LABEL, not the raw id
    assert "GPU rental price" not in out       # price line uses the model token, not a registry label
    # unchanged horizon states the anchor date
    assert "unchanged since 2026-06-08" in out
    # no-run horizon is explicit, not blank
    assert "no run yet at/before" in out


def test_change_lines_pass_acronym_lint():
    cr = ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="metric:vendorRevenueGuidance", changed=True,
                      today="11.2 USD_B", prior="10.0 USD_B", direction="up")]),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf="2026-06-08", items=[]),
    ])
    out = render_change_lines(cr, _reg())
    assert reader.lint_acronyms(out) == []
```

Note: `USD_B` is an all-caps token. If `test_change_lines_pass_acronym_lint` reports `['USD_B']`, the renderer must NOT print raw units above the fold — the metric-token renderer strips/relabels the `USD_B` unit to plain `$…B` (handled in Task 6's `_metric_display`). For the change lines specifically, prefer the reader label + arrow over the raw token; keep the numeric token minimal. Adjust the metric-token formatting until the lint is clean (this is the reader contract doing its job, not a test to weaken).

- [ ] **Step 3: Implement `render_change_lines` in `gpu_agent/report.py`**

Add near the other section renderers (after `render_dmi_smi_sdgi`):

```python
_CHANGE_ARROW = {"up": "↑", "down": "↓", "same": "→", "new": "＋"}
_HORIZON_PHRASE = {"yesterday": "Since yesterday", "last week": "Since last week",
                   "last month": "Since last month"}


def _change_item_label(item, registry) -> str:
    """Exec-plain label for a change item key. dim:/metric: map through reader; index:/price:/
    thesis: get plain words. Never leaks a raw id above the fold."""
    kind, _, rest = item.key.partition(":")
    if kind == "dim":
        return reader.DIM_LABEL.get(rest, rest)
    if kind == "index":
        return {"demand": "Demand momentum", "supply": "Supply momentum",
                "gap": "Demand-supply gap"}.get(rest, rest)
    if kind == "metric":
        return reader.indicator_label(rest, registry)
    if kind == "price":
        return f"{rest} rental"
    if kind == "thesis":
        return "a standing call"     # the ranked-calls section names it; the lead just counts
    return rest


def _dim_arrow(item) -> str:
    """Refine a dim item's arrow from the rating rank (the engine only knows tokens differ)."""
    if not item.changed or item.today is None or item.prior is None:
        return _CHANGE_ARROW["same"]
    cur = RATING_SCALE.get(item.today.split("/")[0], 0)
    pri = RATING_SCALE.get(item.prior.split("/")[0], 0)
    return _CHANGE_ARROW["up"] if cur > pri else _CHANGE_ARROW["down"] if cur < pri else _CHANGE_ARROW["same"]


def render_change_lines(change, registry=None) -> str:
    """WHAT CHANGED (F64 lead): one line per horizon naming the moved items with arrows, or an
    explicit unchanged/no-run state. Above the fold — every token is exec-plain (reader.DIM_LABEL
    / registry labels / plain words) and passes reader.lint_acronyms. change=None -> honest
    empty-state header (a caller with no store yet)."""
    lines = ["WHAT CHANGED"]
    if change is None:
        lines.append("  (no store history yet — needs a prior daily run to compare)")
        return "\n".join(lines)
    for h in change.horizons:
        phrase = _HORIZON_PHRASE.get(h.horizon, f"Since {h.horizon}")
        if h.priorAsOf is None:
            lines.append(f"  {phrase}: no run yet at/before this horizon — first tracked {h.horizon}")
            continue
        moved = [it for it in h.items if it.changed]
        if not moved:
            since = next((it.unchangedSince for it in h.items if it.unchangedSince), h.priorAsOf)
            lines.append(f"  {phrase} (vs {h.priorAsOf}): no change — unchanged since {since}")
            continue
        parts = []
        for it in moved[:_CHANGE_LINE_CAP]:
            arrow = _dim_arrow(it) if it.key.startswith("dim:") else _CHANGE_ARROW.get(it.direction, "→")
            label = _change_item_label(it, registry)
            parts.append(f"{label} {arrow}")
        extra = len(moved) - len(parts)
        tail = f"; +{extra} more moved" if extra > 0 else ""
        lines.append(f"  {phrase} (vs {h.priorAsOf}): " + "; ".join(parts) + tail)
    return "\n".join(lines)
```

Add the module constant near the top of `report.py` (by the other caps):

```python
_CHANGE_LINE_CAP = 4   # F77: bound per-horizon lead width; overflow folds to "+N more moved"
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_report_change_lines.py -q`
Expected: PASS. If the acronym-lint test fails on a unit token, fix the metric-token formatting (Task 6 `_metric_display`) — do not weaken the assertion.

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/reader.py gpu_agent/report.py tests/test_report_change_lines.py
git commit -m "$(cat <<'EOF'
feat(F78-6): change-first lead lines (three horizons) + reader DIM_LABEL; exec-plain, lint-clean

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `report.py` — the three quick-glance tiers (move + age)

Render `QUICK GLANCE` — Tier 1 verdict (six ratings + demand/supply direction), Tier 2 scarcity (rental price from the feed + lead times + packaging/HBM), Tier 3 money (revenue guidance + backlog + gross margin, age-tagged). Each row shows its move arrow across the horizons and, for carried facts, a real age tag via `asof.days_between`.

**Files:**
- Modify: `gpu_agent/report.py` (add `render_quick_glance`, `_metric_display`, `_age_tag`)
- Create: `tests/test_report_quick_glance.py`

**Interfaces:**
- Consumes: `change.{StateVector, ChangeReport}`; `asof.days_between`; `reader.{DIM_LABEL, indicator_label, lint_acronyms}`; `report.DIRECTION_ARROW`, `_CHANGE_ARROW`.
- Produces: `render_quick_glance(state, change, registry) -> str`; helpers `_metric_display(cell)`, `_age_tag(as_of, observed)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report_quick_glance.py
from __future__ import annotations
from gpu_agent.change import StateVector, DimCell, MetricCell, PriceCell, ChangeReport, HorizonDiff, ItemDelta
from gpu_agent.report import render_quick_glance
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent import reader


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def _state():
    return StateVector(
        asOf="2026-07-08",
        dimensions={"momentum": DimCell(rating="Very strong", direction="improving"),
                    "moat": DimCell(rating="Mixed", direction="improving")},
        demand=0.57, supply=0.29, sdgi=0.28,
        metrics={
            "leadTimes": MetricCell(indicatorId="leadTimes", statement="lead times ~40 weeks",
                                    observedAt="2026-06-30", tier="scarcity"),
            "grossMargin": MetricCell(indicatorId="grossMargin", value=75.0, unit="pct",
                                      statement="gm 75%", observedAt="2026-05-20", tier="money"),
        },
        prices=[PriceCell(model="B200", usdPerGpuHour=3.99, asOfColumn="2026-07-08")])


def _change():
    return ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="index:demand", changed=False, direction="same", unchangedSince="2026-06-08"),
            ItemDelta(key="metric:grossMargin", changed=False, direction="same"),
            ItemDelta(key="price:B200", changed=True, direction="down")])])


def test_three_tiers_present_with_arrows_and_age():
    out = render_quick_glance(_state(), _change(), _reg())
    assert "QUICK GLANCE" in out
    assert "Verdict" in out and "Scarcity" in out and "Money" in out
    assert "Demand momentum" in out            # Tier 1 uses DIM_LABEL
    assert "B200 rental" in out and "$3.99" in out
    # Tier 3 money row carries an age tag (asOf 2026-07-08 vs observed 2026-05-20 = 49 days)
    assert "49 days old" in out


def test_quick_glance_passes_acronym_lint():
    out = render_quick_glance(_state(), _change(), _reg())
    assert reader.lint_acronyms(out) == []
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_report_quick_glance.py -q`
Expected: FAIL (`ImportError: cannot import name 'render_quick_glance'`).

- [ ] **Step 3: Implement in `gpu_agent/report.py`**

```python
from gpu_agent.asof import days_between   # add to the imports block at the top of report.py

_UNIT_DISPLAY = {"pct": "%", "USD_B": " billion USD", "USD_per_gpu_hr": "/GPU-hr",
                 "USD_per_gpu": " USD", "USD_per_card": " USD"}


def _metric_display(cell) -> str:
    """Exec-plain value token for a metric cell — raw units (USD_B, pct) relabeled so nothing
    off the acronym allowlist reaches above the fold; qualitative metrics show their statement."""
    if cell.value is None:
        return cell.statement
    unit = _UNIT_DISPLAY.get(cell.unit, "")
    prefix = "$" if cell.unit and cell.unit.startswith("USD_per") else ""
    return f"{prefix}{cell.value:g}{unit}"


def _age_tag(as_of: str, observed) -> str:
    """'N days old' from the run date to a fact's newest evidence date (asof day-math, never
    the clock). Empty when the date is missing or in the future (no negative ages)."""
    if not observed:
        return ""
    try:
        n = days_between(as_of, observed)
    except Exception:   # noqa: BLE001 — a malformed date must not crash the brief
        return ""
    return f"{n} days old" if n > 0 else ""


def _glance_arrow(change, key) -> str:
    """Nearest-horizon arrow for a glance row (yesterday first); '→' when it didn't move."""
    if change is None:
        return _CHANGE_ARROW["same"]
    for h in sorted(change.horizons, key=lambda h: h.lookbackDays):
        for it in h.items:
            if it.key == key:
                return _CHANGE_ARROW.get(it.direction, "→")
    return _CHANGE_ARROW["same"]


def render_quick_glance(state, change=None, registry=None) -> str:
    """QUICK GLANCE (D8) — three tiers, each row its move arrow + (money) an age tag. Tier 1
    verdict: the six ratings + demand/supply momentum. Tier 2 scarcity: rental price (feed) +
    lead times + packaging/HBM. Tier 3 money: revenue guidance + backlog + gross margin,
    age-tagged (they move on earnings). Above the fold — passes reader.lint_acronyms. Share
    price is excluded (spec §5.6)."""
    lines = ["QUICK GLANCE"]

    lines.append("  Tier 1 — Verdict")
    d_arrow = _glance_arrow(change, "index:demand")
    s_arrow = _glance_arrow(change, "index:supply")
    lines.append(f"    Demand momentum {_momentum_word(state.demand)} {d_arrow}"
                 f"    Supply momentum {_momentum_word(state.supply)} {s_arrow}")
    for dim, cell in state.dimensions.items():
        arrow = _glance_arrow(change, f"dim:{dim}")
        label = reader.DIM_LABEL.get(dim, dim)
        lines.append(f"    {label:<24} {cell.rating} {arrow}")

    lines.append("  Tier 2 — Scarcity")
    for p in state.prices:
        arrow = _glance_arrow(change, f"price:{p.model}")
        lines.append(f"    {p.model + ' rental':<24} ${p.usdPerGpuHour:g}/GPU-hr {arrow}")
    for iid, cell in state.metrics.items():
        if cell.tier != "scarcity":
            continue
        arrow = _glance_arrow(change, f"metric:{iid}")
        lines.append(f"    {reader.indicator_label(iid, registry):<24} {_metric_display(cell)} {arrow}")

    lines.append("  Tier 3 — Money")
    for iid, cell in state.metrics.items():
        if cell.tier != "money":
            continue
        arrow = _glance_arrow(change, f"metric:{iid}")
        age = _age_tag(state.asOf, cell.observedAt)
        age_str = f"  ({age})" if age else ""
        lines.append(f"    {reader.indicator_label(iid, registry):<24} "
                     f"{_metric_display(cell)} {arrow}{age_str}")

    return "\n".join(lines)
```

Note the reader labels used here (`Merchant-GPU product lead times`, `Whole-chain inventory`, `Vendor DC-GPU revenue guidance`, `Backlog / purchase commitments`, `Gross margin`) contain only tokens already on the allowlist (`GPU`, `DC-GPU`). If a future registry label introduces an off-list acronym, add it to `registry/acronyms.json` — the lint test in Step 1 is the guard.

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_report_quick_glance.py -q`
Expected: PASS (2 passed). If the acronym-lint test flags a token, extend `_UNIT_DISPLAY` or add the token to `registry/acronyms.json`; never weaken the assertion.

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/report.py tests/test_report_quick_glance.py
git commit -m "$(cat <<'EOF'
feat(F78-6): quick-glance three tiers (verdict/scarcity/money) with move arrows + age tags

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `report.py` — ranked, length-capped calls (F77)

The calls section ordered highest-conviction / most-moved first, top-K rendered as the existing three-line block, the remainder compressed to one line each with an explicit fold count — the F77 volume cap. Builds on `brief.render_the_calls`' helpers; leaves `brief.render_the_calls` (the non-change-first path) untouched.

**Files:**
- Modify: `gpu_agent/report.py` (add `render_ranked_calls`)
- Create: `tests/test_report_ranked_calls.py`

**Interfaces:**
- Consumes: `gpu_agent.thesis.{ThesisBook, CONVICTION_RANK}`; `change.ChangeReport`; `brief._calls_headline_line`, `brief._calls_evidence_line`; `reader.label_ids_in_text`.
- Produces: `report.render_ranked_calls(book, sc, change, last_findings=None, registry=None, top_k=5) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report_ranked_calls.py
from __future__ import annotations
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import ChangeReport, HorizonDiff, ItemDelta
from gpu_agent.report import render_ranked_calls
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def _sc():
    return Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                     demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                     narrative="n", confidence=Confidence(level="medium", basis="b"))


def _entry(eid, conviction, moved_dir=None, **kw):
    f = dict(id=eid, title=f"call {eid}", statement="s", lens="demand",
             status="registered", conviction=conviction, lastVerdict="reaffirmed",
             lastDirection=0, streak=2, mechanism="m", falsifiableTrigger="t",
             sensitivity="s", createdAsOf="2026-06", lastChangedAsOf="2026-07-08",
             lastJudgedAsOf="2026-07-08")
    f.update(kw)
    return ThesisEntry(**f)


def _change(moved_ids):
    return ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07",
                    items=[ItemDelta(key=f"thesis:{i}", changed=True, direction="up") for i in moved_ids])])


def test_moved_high_conviction_leads_and_tail_folds():
    book = ThesisBook(categoryId="c", entries=[
        _entry("a", "low"), _entry("b", "high"), _entry("c", "medium"),
        _entry("d", "low"), _entry("e", "medium"), _entry("f", "low")])
    out = render_ranked_calls(book, _sc(), _change(moved_ids=["d"]), registry=_reg(), top_k=3)
    # moved 'd' (even at low conviction) ranks into the detailed top; 'b' (high) too.
    assert out.index("call d") < out.index("call f")
    assert out.index("call b") < out.index("call f")
    # tail compressed to one line each + explicit fold count
    assert "more calls folded" in out


def test_all_within_top_k_no_fold_line():
    book = ThesisBook(categoryId="c", entries=[_entry("a", "high"), _entry("b", "medium")])
    out = render_ranked_calls(book, _sc(), None, registry=_reg(), top_k=5)
    assert "folded" not in out


def test_book_none_empty_state():
    out = render_ranked_calls(None, _sc(), None, registry=_reg())
    assert "THE CALLS" in out and "no thesis book yet" in out
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_report_ranked_calls.py -q`
Expected: FAIL (`ImportError: cannot import name 'render_ranked_calls'`).

- [ ] **Step 3: Implement in `gpu_agent/report.py`**

```python
from gpu_agent.thesis import CONVICTION_RANK   # add to report.py imports


def _moved_thesis_ids(change) -> set[str]:
    if change is None:
        return set()
    out = set()
    for h in change.horizons:
        for it in h.items:
            if it.key.startswith("thesis:") and it.changed:
                out.add(it.key.split(":", 1)[1])
    return out


def render_ranked_calls(book, sc, change=None, last_findings=None, registry=None, top_k=5) -> str:
    """THE CALLS ranked by (moved-this-cycle, conviction) desc — the F77 importance order and
    volume cap. Top-K get the full three-line block (headline / statement+source-count / breaks-if,
    reusing brief's helpers); the remainder compress to one headline line each with an explicit
    fold count. book=None -> the same honest empty-state brief.render_the_calls emits, so the
    change-first and legacy paths degrade identically."""
    if book is None:
        return "THE CALLS\n  (no thesis book yet - runs after the first thesis cycle)"

    moved = _moved_thesis_ids(change)
    findings_by_id = {f.id: f for f in sc.findings}
    standing = sorted(
        book.standing(),
        key=lambda e: (e.id not in moved, -CONVICTION_RANK[e.conviction], e.id),
    )

    lines = ["THE CALLS  (most-moved / highest-conviction first)"]
    detailed, tail = standing[:top_k], standing[top_k:]
    for entry in detailed:
        finding_ids = (last_findings or {}).get(entry.id)
        lines.append(brief._calls_headline_line(entry))
        lines.append(brief._calls_evidence_line(entry, finding_ids, findings_by_id))
        lines.append(f"      breaks if: {reader.label_ids_in_text(entry.falsifiableTrigger, registry)}")
    for entry in tail:
        lines.append(brief._calls_headline_line(entry))
    if tail:
        lines.append(f"  (+{len(tail)} more calls folded to one line each — full detail in THE CALLS appendix)")
    return "\n".join(lines)
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_report_ranked_calls.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/report.py tests/test_report_ranked_calls.py
git commit -m "$(cat <<'EOF'
feat(F78-6): ranked, length-capped calls (moved+conviction first, tail folded) — F77 hierarchy

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: `report.py` — wire the change-first mode into `render_report` (+ length budget, lint, determinism)

When a `ChangeReport` is supplied, `render_report` leads with `WHAT CHANGED` → `QUICK GLANCE` → ranked calls, applies a length budget above the appendix, and keeps everything else (and the whole appendix) as today. When `change is None`, output is byte-identical to today so every existing report/brief test stays green.

**Files:**
- Modify: `gpu_agent/report.py` (`render_report` signature + body; add `_ABOVE_FOLD_BUDGET`)
- Create: `tests/test_report_change_first.py`

**Interfaces:**
- Produces: `render_report(..., change=None, state=None, top_k=5)` — three additive keyword-only params; default `None`/`None`/`5` reproduces today's behavior.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report_change_first.py
from __future__ import annotations
from gpu_agent.report import render_report, render_change_lines
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.scorecard import (Scorecard, DemandSupply, DimensionRating,
                                        CategoryStatus)
from gpu_agent.schema.finding import Confidence
from gpu_agent.change import build_state, StateVector, ChangeReport, HorizonDiff, ItemDelta
from gpu_agent import reader


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def _conf():
    return Confidence(level="medium", basis="b")


def _sc():
    return Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                     dimensionRatings={"momentum": DimensionRating(
                         rating="Very strong", direction="improving", confidence=_conf(),
                         findingIds=[], rationale="r")},
                     demandSupply=DemandSupply(dmiContribution=0.57, smiContribution=0.29),
                     narrative="n", confidence=_conf(),
                     categoryStatus=CategoryStatus(rating="Strong", direction="improving",
                                                   bottleneck="packaging", reason="demand outruns ramp"))


def _change():
    return ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="dim:momentum", changed=True, today="Very strong/improving",
                      prior="Strong/steady", direction="up")]),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf="2026-06-08", items=[])])


def test_change_none_is_unchanged_behavior():
    # A caller that passes no change report gets exactly today's report (no WHAT CHANGED lead).
    out = render_report(_sc(), None, _reg(), render_ts="fixed")
    assert "WHAT CHANGED" not in out
    assert "STATE OF THE MARKET" in out


def test_change_first_leads_with_what_changed_then_glance():
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    assert out.index("WHAT CHANGED") < out.index("QUICK GLANCE") < out.index(reader.APPENDIX_DIVIDER)
    # change-first lead sits above STATE OF THE MARKET
    assert out.index("WHAT CHANGED") < out.index("STATE OF THE MARKET")


def test_above_fold_passes_acronym_lint():
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    above = out.split(reader.APPENDIX_DIVIDER)[0]
    assert reader.lint_acronyms(above) == []


def test_above_fold_within_length_budget():
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    above = out.split(reader.APPENDIX_DIVIDER)[0]
    from gpu_agent.report import _ABOVE_FOLD_BUDGET
    assert len(above.splitlines()) <= _ABOVE_FOLD_BUDGET


def test_change_first_is_byte_deterministic():
    st = build_state(_sc())
    a = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    b = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    assert a == b
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_report_change_first.py -q`
Expected: FAIL (`render_report() got an unexpected keyword argument 'change'`).

- [ ] **Step 3: Modify `render_report` in `gpu_agent/report.py`**

Add the module constant near the other caps:

```python
_ABOVE_FOLD_BUDGET = 80   # F77: hard line budget for everything above reader.APPENDIX_DIVIDER
```

Extend the signature (keyword-only, all defaulting to today's behavior):

```python
def render_report(
    sc: Scorecard,
    prior: Optional[Scorecard],
    registry: IndicatorRegistry,
    *,
    render_ts: Optional[str] = None,
    horizons=None,
    movement=None,
    thesis_book=None,
    thesis_last_findings=None,
    daily: bool = False,
    gate_waivers=None,
    change=None,          # F78 Stage 6: a change.ChangeReport -> lead change-first
    state=None,           # F78 Stage 6: a change.StateVector for the quick-glance tiers
    top_k: int = 5,       # F78 Stage 6: ranked-calls detail cap (F77)
) -> str:
```

Replace the `top = [...]` / `if daily:` / `appendix = [...]` / `return` block with:

```python
    if render_ts is None:
        render_ts = datetime.now(timezone.utc).isoformat()

    track = compute_price_track(sc, prior)   # F49 — computed once, shared by brief + report

    if change is not None:
        # F78 Stage 6 change-first lead (F64 + F77): WHAT CHANGED -> QUICK GLANCE -> ranked calls,
        # then the rest of the above-the-fold sections, then the untouched appendix.
        top = [
            render_header(sc, render_ts),
            render_change_lines(change, registry),
            render_quick_glance(state, change, registry) if state is not None else "",
            render_ranked_calls(thesis_book, sc, change, thesis_last_findings,
                                registry=registry, top_k=top_k),
            brief.render_state_of_market(sc, prior, track),
            brief.render_why(thesis_book, thesis_last_findings),
            brief.render_demand_supply_board(sc, horizons, registry=registry),
            brief.render_storylines(movement),
            render_trust_footer(sc, gate_waivers=gate_waivers),
        ]
    else:
        top = [
            render_header(sc, render_ts),
            brief.render_state_of_market(sc, prior, track),       # words-first BLUF
            brief.render_what_moved(movement),
            brief.render_the_calls(thesis_book, sc, thesis_last_findings, registry=registry),
            brief.render_why(thesis_book, thesis_last_findings),  # drivers -> constraints
            brief.render_demand_supply_board(sc, horizons, registry=registry),
            brief.render_storylines(movement),
            render_trust_footer(sc, gate_waivers=gate_waivers),   # the one honest caveat (+F75 waivers)
        ]
        if daily:   # F67 §4: the daily's headline is the diff
            top[1], top[2] = top[2], top[1]

    appendix = [
        reader.APPENDIX_DIVIDER,
        render_overall_status(sc),
        render_dimensions(sc, prior),
        render_raw_indices(sc, prior),
        render_price_track(track),
        render_entity_panel(sc),
        render_evidence_quality(sc, registry),
        render_sources(sc),
        render_coverage_gaps(sc),
        render_citation_map(sc),
    ]
    body = "\n\n".join(s for s in top + appendix if s)

    # F77 length budget: if the above-the-fold half overshoots, tighten the ranked-calls cap
    # (the one section that grows with book size) until it fits or top_k hits 1 — deterministic.
    if change is not None:
        k = top_k
        while len(body.split(reader.APPENDIX_DIVIDER)[0].splitlines()) > _ABOVE_FOLD_BUDGET and k > 1:
            k -= 1
            top[3] = render_ranked_calls(thesis_book, sc, change, thesis_last_findings,
                                         registry=registry, top_k=k)
            body = "\n\n".join(s for s in top + appendix if s)
    return body
```

Update the `render_report` docstring's page-order paragraph to note the change-first lead (a prose-only edit; keep the existing F67 order description for the `change is None` path).

- [ ] **Step 4: Run it — verify it passes, and confirm no regressions**

Run: `.venv/Scripts/python -m pytest tests/test_report_change_first.py -q`
Expected: PASS (5 passed).
Run: `.venv/Scripts/python -m pytest tests/test_report.py tests/test_report_surgery.py tests/test_report_contract.py tests/test_report_no_duplicate.py tests/test_brief_report.py -q`
Expected: PASS (unchanged — every existing caller passes `change=None`).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/report.py tests/test_report_change_first.py
git commit -m "$(cat <<'EOF'
feat(F78-6): change-first render_report mode (change=/state=) with above-fold length budget

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: `cli.py` — wire the change engine into `gpu-agent report`

Assemble the `ChangeReport` + `StateVector` (+ price feed) in `_report` and pass them to `render_report` under a `--change-first` flag, so the live daily run emits the change-first brief. Additive: without the flag, behavior is exactly today's.

**Files:**
- Modify: `gpu_agent/cli.py` (`_report` handler + the `report` subparser)
- Create: `tests/test_cli_report_change_first.py`

**Interfaces:**
- Consumes: `change.{build_change_report, build_state, prices_by_lookback}`.
- Produces: a `--change-first` CLI flag; when set, `_report` builds the change report from `args.store` and renders change-first.

- [ ] **Step 1: Write the failing test** (CLI end-to-end over a tiny two-run store)

```python
# tests/test_cli_report_change_first.py
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, DimensionRating
from gpu_agent.schema.finding import Confidence

PY = sys.executable


def _conf():
    return Confidence(level="medium", basis="b")


def _dim(r, d="steady"):
    return DimensionRating(rating=r, direction=d, confidence=_conf(), findingIds=[], rationale="x")


def _write(store, as_of, version, momentum_rating):
    cat = store / "chips.merchant-gpu"
    cat.mkdir(parents=True, exist_ok=True)
    sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                   dimensionRatings={"momentum": _dim(momentum_rating, "improving")},
                   demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                   narrative="n", confidence=_conf())
    p = cat / f"{as_of}-v{version}.json"
    p.write_text(sc.model_dump_json(), "utf-8")
    return p


def _run(*args):
    env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True,
                          text=True, encoding="utf-8", env=env)


def test_cli_change_first_emits_what_changed(tmp_path):
    store = tmp_path / "store"
    _write(store, "2026-07-07", 1, "Strong")
    cur = _write(store, "2026-07-08", 1, "Very strong")
    r = _run("report", "--scorecard", str(cur), "--store", str(store),
             "--change-first", "--render-ts", "fixed")
    assert r.returncode == 0, r.stderr
    assert "WHAT CHANGED" in r.stdout
    assert "QUICK GLANCE" in r.stdout
    assert "Since yesterday" in r.stdout


def test_cli_without_flag_is_legacy(tmp_path):
    store = tmp_path / "store"
    cur = _write(store, "2026-07-08", 1, "Very strong")
    r = _run("report", "--scorecard", str(cur), "--store", str(store),
             "--no-prior", "--render-ts", "fixed")
    assert r.returncode == 0, r.stderr
    assert "WHAT CHANGED" not in r.stdout
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_cli_report_change_first.py -q`
Expected: FAIL (`--change-first` is not a recognized argument → non-zero exit / assertion fail).

- [ ] **Step 3: Add the flag to the `report` subparser** (near the `--daily` arg, line ~1170)

```python
    rp.add_argument("--change-first", action="store_true",
                    help="F78 daily: lead with the three-horizon change lines + quick-glance "
                         "tiers (reads the store at asOf-1/7/30 days). Overrides --daily's order.")
```

- [ ] **Step 4: Build the change report in `_report`** — insert just before the `text = render_report(...)` call (line ~987):

```python
    change = None
    state = None
    if getattr(args, "change_first", False):
        from gpu_agent import change as change_mod
        prices_by_days = None
        try:
            prices_by_days = change_mod.prices_by_lookback(sc.asOf)
        except Exception as e:   # noqa: BLE001 — a missing/партial feed must not sink the brief
            print(f"gpu-agent report: note: price feed unavailable ({e}); "
                  f"rendering change-first without the rental tier", file=sys.stderr)
        change = change_mod.build_change_report(
            pathlib.Path(args.store), sc, book=thesis_book, prices_by_days=prices_by_days)
        state = change_mod.build_state(
            sc, thesis_book, (prices_by_days or {}).get(0))
```

Then pass them through:

```python
    text = render_report(sc, prior, registry,
                         render_ts=getattr(args, "render_ts", None),
                         horizons=horizons, movement=movement,
                         thesis_book=thesis_book, thesis_last_findings=thesis_last_findings,
                         daily=getattr(args, "daily", False), gate_waivers=gate_waivers,
                         change=change, state=state)
```

(Fix the accidental non-ASCII in the `except` comment above — write it as plain ASCII "partial".)

- [ ] **Step 5: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_cli_report_change_first.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/cli.py tests/test_cli_report_change_first.py
git commit -m "$(cat <<'EOF'
feat(F78-6): gpu-agent report --change-first wires the change engine into the daily brief

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Full-suite reconciliation, live shadow-check, eval pin

Confirm the whole suite is green, the eval pin is untouched, and — as evidence, not just green tests — the change-first brief renders cleanly over the LIVE store's day-grain runs.

- [ ] **Step 1: Run the full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: green (baseline pass count + the ~28 new tests from Tasks 1–9; expect the same 5 skips). Any pre-existing report/brief test that fails means the `change is None` path drifted — restore byte-identical legacy output rather than editing the test.

- [ ] **Step 2: Confirm the eval pin is green**

Run: `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q`
Expected: PASS. This stage changed no emitted brain-prompt bytes (only `report.py`/`reader.py`/`change.py`/`cli.py` + a DATA edit to `registry/acronyms.json` if one was needed). If it is red, a prompt file was touched — stop and re-scope.

- [ ] **Step 3: Live shadow-check (evidence)** — render the real store's newest day-grain run change-first and eyeball the lead + tiers, then assert the above-the-fold half is lint-clean and within budget. Reconfigure stdout to UTF-8 first (Windows note):

```bash
.venv/Scripts/python - <<'PY'
import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pathlib
from gpu_agent.report import load_scorecard, render_report, _ABOVE_FOLD_BUDGET
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent import change as ch, reader
store = pathlib.Path("store")
sc = load_scorecard(store / "chips.merchant-gpu" / "2026-07-06-v1.json")
reg = IndicatorRegistry.load("registry/indicators.json")
try:
    pbd = ch.prices_by_lookback(sc.asOf)
except Exception as e:
    print("price feed unavailable:", e); pbd = None
report = ch.build_change_report(store, sc, prices_by_days=pbd)
state = ch.build_state(sc, None, (pbd or {}).get(0))
out = render_report(sc, None, reg, render_ts="shadow", change=report, state=state)
above = out.split(reader.APPENDIX_DIVIDER)[0]
print(above)
print("---")
print("above-fold lines:", len(above.splitlines()), "budget:", _ABOVE_FOLD_BUDGET)
print("acronym lint (must be []):", reader.lint_acronyms(above))
for h in report.horizons:
    print(h.horizon, "-> prior", h.priorAsOf, "moved", sum(1 for i in h.items if i.changed))
PY
```
Expected: `WHAT CHANGED` leads with three horizon lines resolving to the nearest day-grain run at/before each target (07-05 / 07-… / 06-…), `QUICK GLANCE` shows the three tiers with arrows and age tags, the acronym lint is `[]`, and the above-fold line count is `<= _ABOVE_FOLD_BUDGET`. This is the Stage-6 slice of the spec's shadow-check (§7) — no stored scorecard is edited.

- [ ] **Step 4: Determinism replay**

```bash
.venv/Scripts/python - <<'PY'
import pathlib
from gpu_agent.report import load_scorecard, render_report
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent import change as ch
store = pathlib.Path("store")
sc = load_scorecard(store / "chips.merchant-gpu" / "2026-07-06-v1.json")
reg = IndicatorRegistry.load("registry/indicators.json")
r = ch.build_change_report(store, sc)
s = ch.build_state(sc)
a = render_report(sc, None, reg, render_ts="fixed", change=r, state=s)
b = render_report(sc, None, reg, render_ts="fixed", change=r, state=s)
print("byte-identical:", a == b)
PY
```
Expected: `byte-identical: True`.

- [ ] **Step 5: Commit any reconciliation**

```bash
git add -A
git commit -m "$(cat <<'EOF'
test(F78-6): full-suite green + live change-first shadow-check; eval pin untouched

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

- **Spec coverage.** §5.5 change engine: `build_state` (state vector = 6 ratings + demand/supply/gap + standing theses + scarcity/money metrics + price snapshot), `nearest_run_at_or_before` (D3 "nearest at/before" at −1/−7/−30d via `asof`), `diff_states` + `_annotate_unchanged_since` (per-item deltas + explicit "unchanged since <date>"). §5.6 quick-glance: `render_quick_glance` Tier 1 verdict / Tier 2 scarcity (feed rental + lead times + packaging/HBM) / Tier 3 money (age-tagged), each with a move arrow; share price excluded. §5.8 renderer / D7: `render_change_lines` lead + `render_ranked_calls` (importance order, one-line tail, fold count) + `_ABOVE_FOLD_BUDGET` length budget. Delivers F64 (change-lines lead) and F77 (ranked, consolidated, capped).
- **Change engine / diff shape.** State vector items carry raw registry ids/tokens (labels applied only in the renderer, per the reader contract). Dimensions / demand-supply / metrics / prices are true two-snapshot point-in-time diffs; **thesis movement is derived from the current book's `lastChangedAsOf` vs each horizon's prior asOf** because stored scorecards don't embed past book state — the one interface-shaped assumption, stated in Task 3. "unchanged since" walks 1→7→30 outward and stops at the first sampled change, so a reverted value can't claim the farthest date.
- **Assumed earlier-stage interfaces.** `asof.period_end/days_between/AsOfError` (Stage 1); `ThesisEntry.lastChangedAsOf/lastDirection/conviction/streak/pendingChallenge` (Stages 1/2, already present today); and — the only genuinely uncertain one — `pricefeed.read_prices(as_of) -> [PricePoint{.model,.usdPerGpuHour,.column,.custom}]` (Stage 5), isolated to Task 4's injectable adapter so a signature mismatch touches one function. Stage 3 (aged corpus) is consumed indirectly (finished scorecards), no interface.
- **Frozen core / eval pin / reader contract.** Only `report.py`, `reader.py`, `cli.py`, new `change.py`, and (if needed) the `registry/acronyms.json` DATA file are touched; `gate.py`/`scoring.py`/`pipeline.py`/`schema/*`/`judgment/*` untouched; eval pin re-checked in Task 10; every above-fold block pinned lint-clean (Tasks 5, 6, 8) with `_metric_display`/`DIM_LABEL` keeping units and dimension ids exec-plain.
- **Determinism.** No wall-clock anywhere: all lookback targets are `period_end(asOf) − Nd`; the price feed is `asOf`-column-keyed; byte-determinism pinned in Tasks 8 and 10.
- **Legacy safety.** `render_report(change=None)` reproduces today's output exactly (Task 8 `test_change_none_is_unchanged_behavior` + the existing report/brief suites in Task 8 Step 4), so no existing caller/test regresses.
- **Risks / open questions.** (1) The exact `pricefeed` signature — if Stage 5 shipped a class/dataclass instead of the assumed `PricePoint`, adjust `price_cells_from_feed` only. (2) `SCARCITY_INDICATORS = ("leadTimes","S10")` and `MONEY_INDICATORS` are pinned from the live registry (`leadTimes`, `S10`=whole-chain inventory, `vendorRevenueGuidance`, `rpoBacklog`, `grossMargin`) — if the category's indicator set differs, extend the constants. (3) `_ABOVE_FOLD_BUDGET = 80` is a provisional cap (tune during the live shadow-check). (4) Thesis point-in-time state is approximated from book timestamps (see above) — a full per-run thesis snapshot would need a schema/store change, deferred (Part 33). (5) The DIM_LABEL/`_UNIT_DISPLAY` maps assume the six canonical dimensions and the units seen in the live store; a new unit needs one `_UNIT_DISPLAY` entry, guarded by the lint tests.
- **Placeholders:** none — every code step is real code against the actual `report.py`/`reader.py`/`brief.py`/`change` surfaces and the real scorecard/thesis/finding shapes; each task names exact files and pytest commands and uses small on-disk/in-memory scorecard fixtures for the delta tests.
