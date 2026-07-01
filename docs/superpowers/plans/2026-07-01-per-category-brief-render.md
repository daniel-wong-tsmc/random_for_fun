# Per-category Market-State brief render (sub-project 4-5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend A's `report.py` into a brief-first human artifact — render the STATE OF THE MARKET (BLUF), the DEMAND | SUPPLY board, honest "in 4-5b" stubs for the store-fed sections, and a trust caveat — as a pure, deterministic projection of the `Scorecard`, so the default `report` command leads with the market picture.

**Architecture:** A new pure module `gpu_agent/brief.py` holds the new section renderers and reuses `report.py`'s existing helpers (`_momentum_word`/`_sdgi_interpretation`/`_fmt_delta`/`compute_sdgi`/`_signal_label`). `report.py`'s `render_report` gets a minimal additive edit — it prepends the brief sections, appends the caveat, and accepts an optional `horizons` kwarg — and the CLI `_report` handler loads `horizons` and passes it. No wiki store is read; every section projects from the `Scorecard` alone.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset on Windows — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`/`validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the `Scorecard` schema (`gpu_agent/schema/scorecard.py` — 4-5 reads existing fields only, adds none), the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, `store.py`, **every module under** `gpu_agent/wiki/`, and `gpu_agent/gathering/`. 4-5 only *reads* the `Scorecard` and *reuses* `report.py`/`registry/horizon.py`; it never edits the frozen set.
- **Additive only** (Part 33): the new module `gpu_agent/brief.py`; a minimal additive edit to `render_report` in `gpu_agent/report.py` (prepend brief sections + append caveat + optional `horizons` kwarg — the existing eight `render_*` helpers and their relative order stay unchanged); the `_report` handler edit in `cli.py`. Do NOT edit any committed fixture under `fixtures/`. **No new `Scorecard` field.**
- **Honesty (Part 17):** no magnitude adjective is ever derived from the unscaled DMI/SMI — the demand/supply momentum lines carry only `positive`/`negative`/`flat` (from the existing `_momentum_word`) plus the Δ-vs-prior. Earned magnitude words come only from the brain's bounded-scale judgment (`categoryStatus`, per-signal `_signal_label`).
- **Determinism (Part 20):** no wall-clock in `brief.py`; the only clock read stays in `render_report` behind the injected `render_ts`. Recency/carry-over is derived from data (`finding.asOf` vs `sc.asOf`), never from "now". Section order fixed; board rows/columns ordered by `indicatorId`.
- **Every test builds `Scorecard` objects in-code** (via the `_sc`/`_f` helpers below) — no new committed fixture, so the frozen-fixtures guard stays empty. The CLI test dumps an in-code scorecard to `tmp_path`.
- **The full suite stays green after every task.** Baseline: **382 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file guard** (Task 4 Step 8): the only `gpu_agent/` changes are the new `brief.py` and the additive `report.py`/`cli.py` edits; every frozen file byte-unchanged; no `fixtures/` file changes.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gpu_agent/brief.py` | the new brief renderers: `render_state_of_market`, `render_demand_supply_board`, `render_deferred_stubs`, `render_market_caveat` + small local helpers | Create |
| `gpu_agent/report.py` | compose the brief sections into `render_report` (brief-first) + optional `horizons` kwarg | Modify: `render_report` only |
| `gpu_agent/cli.py` | `_report` handler loads `horizons` and passes it to `render_report` | Modify: `_report` handler only |
| `tests/test_brief_state.py` | `render_state_of_market` | Create |
| `tests/test_brief_board.py` | `render_demand_supply_board` | Create |
| `tests/test_brief_stubs.py` | `render_deferred_stubs` + `render_market_caveat` | Create |
| `tests/test_brief_report.py` | brief-first composition + honesty invariant + CLI end-to-end + frozen guard | Create |

**Shared test helpers (copied verbatim into each new test file that needs them — the engineer may read tasks out of order):**

```python
# _sc: build a minimal valid Scorecard in-code (no committed fixture).
from gpu_agent.schema.scorecard import (
    Scorecard, DemandSupply, MarketIndices, Divergence, CategoryStatus)
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _ds(dmi=0.0, smi=0.0, sdgi=None, direction=None):
    return DemandSupply(dmiContribution=dmi, smiContribution=smi, sdgi=sdgi,
                        sdgiDirection=direction)


def _sc(*, as_of="2026-07", dmi=0.07, smi=0.05, findings=None, indices=None,
        category_status=None):
    return Scorecard(
        categoryId="chips.merchant-gpu", asOf=as_of,
        findings=findings or [],
        demandSupply=_ds(dmi=dmi, smi=smi),
        narrative="n", confidence=Confidence(level="medium", basis="b"),
        indices=indices, categoryStatus=category_status)


def _f(fid, *, side, indicatorId, trend="rising", magnitude=2, asOf="2026-07",
       polDemand=1, polSupply=0, entity="NVDA"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend=trend, why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=None, confidence=Confidence(level="medium", basis="b"), asOf=asOf,
        indicatorId=indicatorId, side=side, polarityDemand=polDemand,
        polaritySupply=polSupply, magnitude=magnitude, entity=entity,
        observedAt=asOf, capturedAt=asOf + "-01",
        evidence=[Evidence(source="sec", url="http://sec/x", date=asOf,
                           excerpt="e", tier="secondary")])
```

**Note on `horizons`:** the real `IndicatorHorizons` loads from `registry/indicators.json`
(`IndicatorHorizons.load("registry/indicators.json")`); board tests that exercise the `leading` tag load it that way.
`horizons.get(indicator_id)` returns an `Optional[dict]` (the tag, with a `"horizon"` key) — safe on untagged ids.

---

### Task 1: `brief.py` — `render_state_of_market` (the BLUF)

**Files:**
- Create: `gpu_agent/brief.py`
- Test: `tests/test_brief_state.py`

**Interfaces:**
- Consumes: `report._momentum_word`, `report._sdgi_interpretation`, `report._fmt_delta`, `report.compute_sdgi`; `Scorecard`/`DemandSupply`/`MarketIndices`/`Divergence`/`CategoryStatus`.
- Produces (used by Task 4): `render_state_of_market(sc, prior) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_brief_state.py` (include the `_sc`/`_ds`/`_f` helpers from the File Structure section above), then:

```python
from gpu_agent.brief import render_state_of_market


def _indices(*, mom=(0.07, 0.05), out=(0.0, 0.0), div_state="insufficient-coverage",
             note="outlook has no leading findings yet"):
    return MarketIndices(
        momentum=_ds(dmi=mom[0], smi=mom[1]),
        outlook=_ds(dmi=out[0], smi=out[1]),
        divergence=Divergence(state=div_state, sdgiGap=0.0, outlookFindingCount=0,
                              momentumFindingCount=3, note=note))


def _catstat():
    return CategoryStatus(rating="Strong", direction="improving",
                          bottleneck="advanced packaging (CoWoS)",
                          reason="demand outruns the packaging ramp")


def test_state_header_full():
    prior = _sc(dmi=0.04, smi=0.05)
    sc = _sc(dmi=0.07, smi=0.05, indices=_indices(), category_status=_catstat())
    out = render_state_of_market(sc, prior)
    assert "STATE OF THE MARKET" in out
    assert "Strong, improving" in out                 # categoryStatus headline
    assert "demand outruns the packaging ramp" in out
    assert "Demand momentum: positive" in out         # _momentum_word(0.07) == positive
    assert "Supply momentum: flat" in out             # _momentum_word delta 0 handled; smi 0.05 > 0 -> positive
    assert "DMI 0.070" in out and "Δ +0.030" in out   # Δ vs prior 0.04
    assert "BINDING CONSTRAINT: advanced packaging (CoWoS)" in out


def test_now_next_and_divergence():
    sc = _sc(indices=_indices(div_state="insufficient-coverage"), category_status=_catstat())
    out = render_state_of_market(sc, None)
    assert "NOW (Momentum):" in out
    assert "NEXT (Outlook): insufficient coverage" in out   # honest until 4-4 feeds leading findings


def test_divergence_flagged_when_diverging():
    sc = _sc(indices=_indices(div_state="diverging-weakening",
                              note="trailing strong; one forward signal softened"),
             category_status=_catstat())
    out = render_state_of_market(sc, None)
    assert "DIVERGENCE" in out and "softened" in out


def test_degrades_without_categorystatus_or_indices():
    sc = _sc()  # no indices, no categoryStatus
    out = render_state_of_market(sc, None)
    assert "STATE OF THE MARKET" in out
    assert "Demand momentum:" in out         # scorecard demandSupply still renders
    assert "NOW (Momentum)" not in out       # no indices -> no NOW/NEXT
    assert "BINDING CONSTRAINT" not in out   # no categoryStatus -> no binding line


def test_no_magnitude_word_on_indices():
    # Honesty: the DMI/SMI momentum lines carry NO magnitude adjective.
    sc = _sc(dmi=0.9, smi=0.9, category_status=_catstat())  # large values, still only direction
    out = render_state_of_market(sc, None)
    demand_line = [ln for ln in out.splitlines() if "Demand momentum:" in ln][0]
    for banned in ("strong", "accelerating", "weak", "slight", "moderate"):
        assert banned not in demand_line.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_state.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.brief'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/brief.py`:

```python
"""The human-facing Market-State brief (sub-project 4-5). Pure, deterministic
projection of a Scorecard — no LLM, no wiki store, no new number. Reuses report.py's
wording helpers so the brief and the detailed report speak the same vocabulary."""
from __future__ import annotations
from typing import Optional
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent import report   # module ref, resolved at call-time — avoids the report<->brief cycle

_ARROW = {"positive": "▲", "negative": "▼", "flat": "="}   # ▲ ▼ =


def _dir_arrow(value: float) -> str:
    return _ARROW[report._momentum_word(value)]


def render_state_of_market(sc: Scorecard, prior: Optional[Scorecard]) -> str:
    """STATE OF THE MARKET (BLUF): demand/supply momentum as direction + Δ (never an
    invented magnitude word on the unscaled index — Part 17), the SDGI gap wording, the
    brain's earned categoryStatus headline + binding constraint, and NOW/NEXT + divergence
    from the two indices. Optional fields degrade cleanly."""
    ds = sc.demandSupply
    sdgi = report.compute_sdgi(sc)
    p_dmi = prior.demandSupply.dmiContribution if prior else None
    p_smi = prior.demandSupply.smiContribution if prior else None
    p_sdgi = report.compute_sdgi(prior) if prior else None

    lines = ["STATE OF THE MARKET"]
    cs = sc.categoryStatus
    if cs is not None:
        lines.append(f"  {cs.rating}, {cs.direction} — {cs.reason}")
    lines.append(f"  Demand momentum: {report._momentum_word(ds.dmiContribution)} "
                 f"{_dir_arrow(ds.dmiContribution)}   "
                 f"(DMI {ds.dmiContribution:.3f}, Δ {report._fmt_delta(ds.dmiContribution, p_dmi)})")
    lines.append(f"  Supply momentum: {report._momentum_word(ds.smiContribution)} "
                 f"{_dir_arrow(ds.smiContribution)}   "
                 f"(SMI {ds.smiContribution:.3f}, Δ {report._fmt_delta(ds.smiContribution, p_smi)})")
    lines.append(f"  Gap: {report._sdgi_interpretation(sdgi)}   "
                 f"(SDGI {sdgi:.3f}, Δ {report._fmt_delta(sdgi, p_sdgi)})")

    ix = sc.indices
    if ix is not None:
        now = (f"demand {report._momentum_word(ix.momentum.dmiContribution)} "
               f"{_dir_arrow(ix.momentum.dmiContribution)} / "
               f"supply {report._momentum_word(ix.momentum.smiContribution)} "
               f"{_dir_arrow(ix.momentum.smiContribution)}")
        if ix.divergence.state == "insufficient-coverage":
            nxt = "insufficient coverage"
        else:
            nxt = (f"demand {report._momentum_word(ix.outlook.dmiContribution)} "
                   f"{_dir_arrow(ix.outlook.dmiContribution)} / "
                   f"supply {report._momentum_word(ix.outlook.smiContribution)} "
                   f"{_dir_arrow(ix.outlook.smiContribution)}")
        lines.append(f"  NOW (Momentum): {now}    NEXT (Outlook): {nxt}")
        if ix.divergence.state != "aligned":
            flag = "⚠ " if ix.divergence.state.startswith("diverging") else ""
            lines.append(f"  {flag}DIVERGENCE: {ix.divergence.note}")

    if cs is not None:
        lines.append(f"  BINDING CONSTRAINT: {cs.bottleneck}")
    return "\n".join(lines)
```

Note: `_momentum_word(0.05)` returns `positive` (0.05 > 0). The Task-1 test's `"Supply momentum: flat"` assertion is **wrong** for `smi=0.05` — fix the test to `"Supply momentum: positive"` before running Step 4 (the implementer should catch this in Step 2's RED output when the assertion mismatches). This is intentional: verify the direction wording matches `_momentum_word`'s sign rule.

- [ ] **Step 4: Correct the test assertion, then run tests to verify they pass**

Change `test_state_header_full`'s `assert "Supply momentum: flat"` to `assert "Supply momentum: positive"`.
Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_state.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 387 passed, 3 skipped (382 baseline + 5 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/brief.py tests/test_brief_state.py && git commit -m "feat(4-5): brief.py + render_state_of_market (BLUF, honest direction-only)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `brief.py` — `render_demand_supply_board`

**Files:**
- Modify: `gpu_agent/brief.py` (add the board renderer)
- Test: `tests/test_brief_board.py`

**Interfaces:**
- Consumes: `report._signal_label` (via the `from gpu_agent import report` module ref added in Task 1); `IndicatorHorizons` (`gpu_agent.registry.horizon`); `Scorecard`/`Finding`.
- Produces (used by Task 4): `render_demand_supply_board(sc, horizons) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_brief_board.py` (include the `_sc`/`_ds`/`_f` helpers), then:

```python
from gpu_agent.brief import render_demand_supply_board
from gpu_agent.registry.horizon import IndicatorHorizons


def test_board_groups_by_side():
    sc = _sc(findings=[
        _f("d1", side="demand", indicatorId="rpoBacklog", trend="rising", polDemand=1),
        _f("s1", side="supply", indicatorId="leadTimes", trend="falling", polSupply=1),
    ])
    out = render_demand_supply_board(sc, None)
    assert "DEMAND" in out and "SUPPLY" in out
    assert "rpoBacklog" in out and "leadTimes" in out


def test_board_collapses_to_latest_vintage_per_indicator():
    # two vintages of the same indicator -> ONE row (the latest capturedAt)
    sc = _sc(findings=[
        _f("d-old", side="demand", indicatorId="rpoBacklog", asOf="2026-06", magnitude=1),
        _f("d-new", side="demand", indicatorId="rpoBacklog", asOf="2026-07", magnitude=3),
    ])
    out = render_demand_supply_board(sc, None)
    assert out.count("rpoBacklog") == 1


def test_board_leading_tag_when_horizons_supplied():
    horizons = IndicatorHorizons.load("registry/indicators.json")
    sc = _sc(findings=[_f("d1", side="demand", indicatorId="rpoBacklog", trend="rising")])
    out = render_demand_supply_board(sc, horizons)
    # rpoBacklog is horizon=leading in the registry (4-2)
    assert "leading" in out


def test_board_no_leading_tag_without_horizons():
    sc = _sc(findings=[_f("d1", side="demand", indicatorId="rpoBacklog", trend="rising")])
    out = render_demand_supply_board(sc, None)
    assert "leading" not in out


def test_board_flags_carried_finding():
    # finding.asOf predates the scorecard asOf -> a stale carry-over
    sc = _sc(as_of="2026-07", findings=[
        _f("d1", side="demand", indicatorId="rpoBacklog", asOf="2026-05")])
    out = render_demand_supply_board(sc, None)
    assert "⚠carried" in out


def test_board_empty_side_note():
    sc = _sc(findings=[_f("d1", side="demand", indicatorId="rpoBacklog")])
    out = render_demand_supply_board(sc, None)
    assert "no supply findings" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_board.py -q`
Expected: FAIL with `ImportError: cannot import name 'render_demand_supply_board'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/brief.py`, add at the end of the module:

```python
_TREND_ARROW = {"rising": "▲", "falling": "▼", "flat": "=", "unknown": "·"}


def _collapse_latest(findings):
    """One finding per indicatorId — the latest vintage (max by capturedAt, observedAt,
    magnitude), the same collapse the frozen dmi_smi_contribution uses. Deterministic."""
    latest: dict[str, object] = {}
    for f in findings:
        cur = latest.get(f.indicatorId)
        key = (f.capturedAt, f.observedAt, f.magnitude)
        if cur is None or key > (cur.capturedAt, cur.observedAt, cur.magnitude):
            latest[f.indicatorId] = f
    return latest


def _board_rows(findings, side, sc_as_of, horizons):
    rows = []
    on_side = [f for f in findings if f.side == side]
    latest = _collapse_latest(on_side)
    for indicator_id in sorted(latest):
        f = latest[indicator_id]
        pol = f.polarityDemand if side == "demand" else f.polaritySupply
        word = report._signal_label(pol * f.magnitude)
        arrow = _TREND_ARROW.get(f.trend, "·")
        tags = []
        if horizons is not None:
            tag = horizons.get(indicator_id)
            if tag is not None and tag.get("horizon") == "leading":
                tags.append("leading")
        if f.asOf < sc_as_of:
            tags.append("⚠carried")
        suffix = ("  [" + ", ".join(tags) + "]") if tags else ""
        rows.append(f"    {indicator_id}  {word} {arrow}{suffix}")
    if not rows:
        rows.append(f"    (no {side} findings)")
    return rows


def render_demand_supply_board(sc: Scorecard, horizons) -> str:
    """DEMAND | SUPPLY board: findings grouped by side, collapsed to the latest vintage per
    indicator, each row a _signal_label word (from polarity*magnitude — the same score the
    entity panel uses) + a trend arrow, with a `leading` tag (when horizons supplied) and a
    `carried` flag for a stale carry-over. Read-only; deterministic (rows ordered by id)."""
    lines = ["DEMAND | SUPPLY"]
    lines.append("  DEMAND")
    lines.extend(_board_rows(sc.findings, "demand", sc.asOf, horizons))
    lines.append("  SUPPLY")
    lines.extend(_board_rows(sc.findings, "supply", sc.asOf, horizons))
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_board.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 393 passed, 3 skipped (387 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/brief.py tests/test_brief_board.py && git commit -m "feat(4-5): render_demand_supply_board (side-grouped, collapsed, leading/carried tags)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `brief.py` — `render_deferred_stubs` + `render_market_caveat`

**Files:**
- Modify: `gpu_agent/brief.py` (add the two small renderers)
- Test: `tests/test_brief_stubs.py`

**Interfaces:**
- Produces (used by Task 4): `render_deferred_stubs() -> str`, `render_market_caveat(sc) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_brief_stubs.py` (include the `_sc`/`_ds` helpers), then:

```python
from gpu_agent.brief import render_deferred_stubs, render_market_caveat


def test_deferred_stubs_name_4_5b():
    out = render_deferred_stubs()
    assert "WHAT MOVED SINCE LAST RUN" in out
    assert "STORYLINES" in out
    assert out.count("4-5b") == 2   # both sections name the follow-up


def test_market_caveat_reads_direction_not_level():
    out = render_market_caveat(_sc())
    assert "read DIRECTION, not level" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_stubs.py -q`
Expected: FAIL with `ImportError: cannot import name 'render_deferred_stubs'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/brief.py`, add at the end of the module:

```python
def render_deferred_stubs() -> str:
    """Honest placeholders for the store-fed sections wired in 4-5b (nothing silently
    omitted — Part 29). They need a multi-cycle wiki store, out of scope this cut."""
    return ("WHAT MOVED SINCE LAST RUN\n"
            "  (rendered in 4-5b — needs a multi-cycle wiki store)\n"
            "STORYLINES\n"
            "  (rendered in 4-5b — needs a multi-cycle wiki store)")


def render_market_caveat(sc: Scorecard) -> str:
    """The one honest trust-footer caveat: the index LEVEL is run-to-run noisy until the
    4-4 memory stabilizes it, so the brief is a read of DIRECTION and change, not level."""
    return ("TRUST & COVERAGE (caveat)\n"
            "  index level varies run-to-run until the 4-4 memory stabilizes it — "
            "read DIRECTION, not level")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_stubs.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 395 passed, 3 skipped (393 + 2 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/brief.py tests/test_brief_stubs.py && git commit -m "feat(4-5): render_deferred_stubs + render_market_caveat (honest 4-5b stubs + caveat)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: compose brief-first into `render_report` + CLI `horizons` + honesty guard + frozen guard

**Files:**
- Modify: `gpu_agent/report.py` (`render_report` only)
- Modify: `gpu_agent/cli.py` (`_report` handler only)
- Test: `tests/test_brief_report.py`

**Interfaces:**
- Consumes: Task 1 `render_state_of_market`, Task 2 `render_demand_supply_board`, Task 3 `render_deferred_stubs`/`render_market_caveat`; the existing `render_report`, `load_scorecard`; `main` (`gpu_agent.cli`); `IndicatorHorizons`.
- Produces: a brief-first `render_report(sc, prior, registry, render_ts=None, *, horizons=None)`; `report` CLI emits brief-first output.

- [ ] **Step 1: Write the failing test**

Create `tests/test_brief_report.py` (include the `_sc`/`_ds`/`_f` helpers), then:

```python
import json
from gpu_agent.report import render_report
from gpu_agent.cli import main
from gpu_agent.schema.scorecard import MarketIndices, Divergence, CategoryStatus


def _reg():
    # the brief needs a registry only for the (unchanged) evidence-quality section.
    # IndicatorRegistry lives in gpu_agent.registry.indicators (confirmed against report.py:15).
    from gpu_agent.registry.indicators import IndicatorRegistry
    return IndicatorRegistry.load("registry/indicators.json")


def _rich_sc():
    ix = MarketIndices(momentum=_ds(dmi=0.07, smi=0.05), outlook=_ds(dmi=0.0, smi=0.0),
                       divergence=Divergence(state="insufficient-coverage", sdgiGap=0.0,
                                             outlookFindingCount=0, momentumFindingCount=3,
                                             note="no leading findings yet"))
    cs = CategoryStatus(rating="Strong", direction="improving",
                        bottleneck="advanced packaging (CoWoS)", reason="demand outruns ramp")
    return _sc(dmi=0.07, smi=0.05, indices=ix, category_status=cs,
               findings=[_f("d1", side="demand", indicatorId="rpoBacklog", trend="rising")])


def test_render_report_is_brief_first():
    out = render_report(_rich_sc(), None, _reg(), render_ts="2026-07-01T00:00:00+00:00")
    i_state = out.index("STATE OF THE MARKET")
    i_board = out.index("DEMAND | SUPPLY")
    i_moved = out.index("WHAT MOVED SINCE LAST RUN")
    i_detail = out.index("ENTITY PANEL")         # an existing detailed section
    i_caveat = out.index("read DIRECTION, not level")
    assert i_state < i_board < i_moved < i_detail < i_caveat  # brief-first, caveat last


def test_render_report_honesty_invariant():
    # magnitude words appear only on the categoryStatus headline, never on the DMI/SMI lines
    out = render_report(_rich_sc(), None, _reg(), render_ts="t")
    for ln in out.splitlines():
        if "Demand momentum:" in ln or "Supply momentum:" in ln:
            for banned in ("strong", "accelerating", "weak", "slight", "moderate"):
                assert banned not in ln.lower()


def test_render_report_byte_stable():
    a = render_report(_rich_sc(), None, _reg(), render_ts="fixed")
    b = render_report(_rich_sc(), None, _reg(), render_ts="fixed")
    assert a == b


def test_cli_report_brief_first(tmp_path, capsys):
    p = tmp_path / "scorecard.json"
    p.write_text(_rich_sc().model_dump_json(), encoding="utf-8")
    # --scorecard is a REQUIRED flag (not positional); --registry defaults to registry/indicators.json
    rc = main(["report", "--scorecard", str(p), "--no-prior",
               "--render-ts", "2026-07-01T00:00:00+00:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.index("STATE OF THE MARKET") < out.index("ENTITY PANEL")
```

Note: `_reg()` uses `IndicatorRegistry.load("registry/indicators.json")` (the same loader `cli._load_registry` wraps at cli.py:40; the extra `validate_against` there is unnecessary for the brief, which uses the registry only for the unchanged evidence-quality section). Do NOT invent a new loader.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_report.py -q`
Expected: FAIL — `test_render_report_is_brief_first` raises `ValueError: substring not found` (the brief sections aren't composed yet).

- [ ] **Step 3: Edit `render_report` in `gpu_agent/report.py`**

Add the import near the top of `report.py` (below the existing imports at lines 14–15):

```python
from gpu_agent import brief   # module ref; brief also does `from gpu_agent import report` — both resolve at call-time
```

Change the `render_report` signature to accept the optional `horizons` kwarg and prepend/append the brief sections. The `sections` list becomes:

```python
def render_report(
    sc: Scorecard,
    prior: Optional[Scorecard],
    registry: IndicatorRegistry,
    render_ts: Optional[str] = None,
    *,
    horizons=None,
) -> str:
    if render_ts is None:
        render_ts = datetime.now(timezone.utc).isoformat()

    sections = [
        render_header(sc, render_ts),
        brief.render_state_of_market(sc, prior),          # NEW — BLUF
        brief.render_demand_supply_board(sc, horizons),   # NEW
        brief.render_deferred_stubs(),                    # NEW — 4-5b stubs
        render_overall_status(sc),
        render_dimensions(sc, prior),
        render_dmi_smi_sdgi(sc, prior),
        render_entity_panel(sc),
        render_evidence_quality(sc, registry),
        render_sources(sc),
        render_coverage_gaps(sc),
        brief.render_market_caveat(sc),                   # NEW — trust footer caveat
    ]
    return "\n\n".join(sections)
```

(Keep the existing docstring; append one line noting the brief sections + `horizons`. Everything else in `report.py` is unchanged.)

**Circular-import safety (why this works):** `report.py` does `from gpu_agent import brief` and `brief.py` does `from gpu_agent import report` — both bind the *module object* (which exists in `sys.modules` as soon as either starts importing), and every cross-reference (`report._momentum_word(...)`, `brief.render_state_of_market(...)`) is a call-time attribute lookup, never an import-time `from X import name` binding. So whichever module is imported first, the other's partially-initialized module object is enough; the names are resolved only when the functions actually run. No import ordering fix is needed. (Do NOT change `brief.py` to `from gpu_agent.report import _momentum_word` — that would reintroduce an import-time binding and can fail depending on import order.)

- [ ] **Step 4: Edit the `_report` handler in `gpu_agent/cli.py`**

The live handler (cli.py ~343–344) is exactly:

```python
    registry = IndicatorRegistry.load(args.registry)
    text = render_report(sc, prior, registry, render_ts=getattr(args, "render_ts", None))
```

Edit ONLY these two lines' neighborhood — insert a horizons load from the **same `args.registry`** path (that file holds both `indicators` and the `cadenceHorizon` map) and thread `horizons=` into the existing call:

```python
    registry = IndicatorRegistry.load(args.registry)
    horizons = IndicatorHorizons.load(args.registry)   # same file; carries the cadenceHorizon tags
    text = render_report(sc, prior, registry,
                         render_ts=getattr(args, "render_ts", None), horizons=horizons)
```

`IndicatorHorizons` is already imported at the top of `cli.py` (used by the `wiki-lint`/`run` handlers) — reuse that import; if for any reason it is not, add `from gpu_agent.registry.horizon import IndicatorHorizons` at the top with the other imports. Do NOT add a CLI flag and do NOT change any other line of `_report` (the variable is `text`, printed by the existing code below).

- [ ] **Step 5: Confirm `_report`'s existing render_ts/registry vars are threaded**

`_reg()` in the test already uses the real `IndicatorRegistry.load` (Step 1). Verify the `_report` edit (Step 4) reuses the handler's existing `registry` and `render_ts` locals — it must NOT introduce a new registry load or a new CLI flag; only the `horizons` load + the `horizons=horizons` kwarg are added.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_report.py -q`
Expected: PASS (4 passed).

- [ ] **Step 7: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 399 passed, 3 skipped (395 + 4 new). The existing `tests/test_report*.py` still pass (the detailed sections are unchanged, merely preceded by the brief).

- [ ] **Step 8: Run the frozen guards**

Run: `cd /c/Users/danie/random_for_fun && git diff --stat main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/schema/scorecard.py gpu_agent/pipeline.py gpu_agent/store.py gpu_agent/wiki/ gpu_agent/gathering/`
Expected: **no output** (every frozen file byte-unchanged; the only `gpu_agent/` changes are the new `brief.py` and the additive `report.py`/`cli.py` edits).

Run: `cd /c/Users/danie/random_for_fun && git diff main -- fixtures/`
Expected: **no output** (no committed fixture changed).

- [ ] **Step 9: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/report.py gpu_agent/cli.py tests/test_brief_report.py && git commit -m "feat(4-5): compose brief-first render_report + CLI horizons wiring + honesty guard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-07-01-per-category-brief-render-design.md`):
- §0(a) scope = 3 live sections + detailed drill-down + deferred stubs → Tasks 1 (state), 2 (board), 3 (stubs+caveat), 4 (compose). ✓
- §0(b) unified brief-first `report`, no new subcommand/flag → Task 4 (`render_report` order + `_report` handler; no argparse change). ✓
- §0(c) new `brief.py` reusing report helpers; minimal additive `render_report` edit → Tasks 1–3 (brief.py) + Task 4 (compose). ✓
- §0(d) honesty — no magnitude word on DMI/SMI; earned words from categoryStatus/_signal_label → Task 1 (`_momentum_word` only on momentum lines) + the honesty tests in Tasks 1 & 4. ✓
- §0(e) pure Scorecard projection, no wiki store → every task reads only `Scorecard` (+ registry/horizons). ✓
- §1 architecture (render_report signature + optional horizons + CLI load) → Task 4. ✓
- §2① state header (categoryStatus headline, demand/supply direction+Δ, gap, NOW/NEXT, divergence, binding constraint, degradation) → Task 1. ✓
- §2② board (group by side, collapse latest vintage, _signal_label(polarity*magnitude), trend arrow, leading tag, carried flag, empty-side note, ordered by id) → Task 2. ✓
- §2③ deferred stubs → Task 3. ✓
- §3 trust footer caveat (evidence/coverage reused unchanged + new caveat line) → Task 3 (caveat) + Task 4 (evidence/coverage stay in place). ✓
- §4 determinism (no wall-clock in brief.py; render_ts injected; recency from data) → Tasks 1/2 + Task 4 byte-stable test. ✓
- §5 frozen/additive boundary → Task 4 Step 8 guards. ✓
- §6 doctrine (pure projection, honest, replayable, nothing silent) → Tasks 1–4. ✓
- §8 test strategy (in-code Scorecards, honesty test, CLI e2e, guards) → every task. ✓
- §10 acceptance items 1–7 all map to tasks above. ✓

**Placeholder scan:** none — every code step has complete code; every test step has complete assertions. Two steps (Task 4 Step 5 `_reg()` import, Step 3 grep) explicitly instruct the implementer to mirror the *existing* loader rather than invent one, with the exact pattern named (`registry, _ = _load_registry()`); these are grounding instructions, not placeholders.

**Type consistency:** `render_state_of_market(sc, prior)` (T1), `render_demand_supply_board(sc, horizons)` (T2), `render_deferred_stubs()` + `render_market_caveat(sc)` (T3) are called by `render_report` (T4) with exactly those signatures. `brief.py` imports `_momentum_word`/`_sdgi_interpretation`/`_fmt_delta`/`compute_sdgi`/`_signal_label` from `report.py` — all confirmed to exist at plan time (`report.py` lines 105/258/265/274/315). `render_report` gains `*, horizons=None` (backward-compatible; existing callers unaffected). `IndicatorHorizons.get(id)` returns `Optional[dict]` with a `"horizon"` key; `Finding.trend ∈ {rising,falling,flat,unknown}`; `Scorecard` carries `indices`/`categoryStatus`/`demandSupply`/`findings` — all confirmed against the live schema.

**Controller-confirmed (against live code at plan time):** `report.py` exposes `render_report(sc, prior, registry, render_ts=None)` composing 8 sections (the edit adds `*, horizons=None` + 4 brief sections); the wording helpers `_momentum_word` (positive/negative/flat only — the honesty rule), `_sdgi_interpretation`, `_fmt_delta`, `compute_sdgi`, `_signal_label` (thresholds ±0.1/0.5/1.5) all exist; `render_entity_panel` feeds `_signal_label(polarityDemand*magnitude)` (the board mirrors this); the `_report` CLI handler loads `sc`/`prior`/`registry` and supports `--no-prior`/`--render-ts`; `IndicatorHorizons.load("registry/indicators.json")` + `.get()` are the 4-2 accessors (same call `wiki-lint` uses); no committed fixture carries `indices` (so tests build Scorecards in-code).

**Test-count math:** baseline 382 → +5 (T1) → +6 (T2) → +2 (T3) → +4 (T4) = **399 passed, 3 skipped** at the end.
