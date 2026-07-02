# Per-category brief — store-fed sections (sub-project 4-5b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two 4-5 stub lines with real renders — **WHAT MOVED SINCE LAST RUN** (the materiality-ranked daily diff) and **STORYLINES** (page state/trajectory over time) — read from the wiki store as a pure, deterministic projection, so the default `report` leads with the market picture *and* the day's changes.

**Architecture:** A new read-only collector `gpu_agent/wiki/movement.py` reads the store (`diff` + 4-4b `score_moves`, `index` + 4-4c `partition_canonical`) and returns a plain `MarketMovement` value — **no store write** (never `lint()`). Two new pure renderers in `gpu_agent/brief.py` (`render_what_moved`, `render_storylines`) project `MarketMovement` to text (`None` → an honest empty-state note). `report.py`'s `render_report` gains `*, movement=None` and swaps the single `render_deferred_stubs()` call for the two renderers; the CLI `_report` builds the store from the existing `--store` root, calls the collector, and threads `movement=`.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset on Windows — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`/`validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the `Scorecard` schema (`gpu_agent/schema/scorecard.py` — reads existing fields only, adds none), the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, `store.py`, and **every *existing* module under `gpu_agent/wiki/`** (`lint.py`, `lifecycle.py`, `page.py`, `log.py`, `ingest.py`, `dedup.py`), `gpu_agent/gathering/`. 4-5b only *reads* the wiki store and *reuses* `report.py`/`registry`; it never edits the frozen set.
- **Additive only** (Part 33): the new module `gpu_agent/wiki/movement.py`; two new renderers in `gpu_agent/brief.py`; the retirement of `brief.render_deferred_stubs` (superseded — its call site is replaced, and its stub test updated); a minimal additive edit to `render_report` in `gpu_agent/report.py` (the `*, movement=None` kwarg + the two renderer calls in the two stub positions — the eight detailed sections + `render_market_caveat` + their order unchanged); the `_report` handler edit in `cli.py`. Do NOT edit any committed fixture under `fixtures/`. **No new `Scorecard` field.**
- **Read-only (Part 35):** the collector and renderers write **no store event and no number**. WHAT MOVED ranks via the read-only `score_moves(...)`, **never** `lint(...)` (which appends a log event). A collector test asserts the log length is unchanged.
- **Honesty (Part 17/29):** every WHAT MOVED row is cited (`[f-###]`) and tiered (primary/secondary); provisional moves + storylines are marked confidence-capped; the folded below-threshold count is always shown; every degradation is an honest one-line note, never a silent omission or a crash.
- **Determinism (Part 20):** no wall-clock anywhere in `wiki/movement.py` or `brief.py`; recency is data-derived (`prevAsOf`, `lastUpdatedAsOf`), never "now". Every ordering has an explicit tiebreak: `moved` by `score` desc then `pageId`; `storylines` by `salience` desc then `title`. Section order fixed.
- **Every test builds its inputs in-code** — the collector tests build a `WikiStore` in `tmp_path` via the wiki-test convention (`route_findings`/`record_state`/`update_header`); the renderer tests build `MarketMovement` in-code. **No committed `fixtures/wiki`**, so the frozen-fixtures guard stays empty.
- **The full suite stays green after every task.** Baseline: **399 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file guard** (Task 4 Step 9): the only `gpu_agent/` changes are the new `wiki/movement.py` and the additive `brief.py`/`report.py`/`cli.py` edits; every frozen file byte-unchanged; no `fixtures/` file changes.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gpu_agent/wiki/movement.py` | the read-only collector `collect_movement` + the `MarketMovement`/`MovedRow`/`StorylineRow` models | Create |
| `gpu_agent/brief.py` | add `render_what_moved` + `render_storylines` (pure); **retire** `render_deferred_stubs` | Modify |
| `gpu_agent/report.py` | `render_report` gains `*, movement=None`; the two stub calls become `render_what_moved`/`render_storylines` | Modify: `render_report` only |
| `gpu_agent/cli.py` | `_report` builds the store from `--store`, calls `collect_movement`, threads `movement=` | Modify: `_report` + one import |
| `tests/test_brief_movement.py` | `collect_movement` (against an in-code 2-cycle store) | Create |
| `tests/test_brief_moved.py` | `render_what_moved` (in-code `MarketMovement`) | Create |
| `tests/test_brief_storylines.py` | `render_storylines` (in-code `MarketMovement`) | Create |
| `tests/test_brief_stubs.py` | remove `test_deferred_stubs_name_4_5b` (renderer retired); keep `test_market_caveat` | Modify |
| `tests/test_brief_report.py` | extend: brief-first composition with `movement`, `movement=None`, byte-stable, CLI e2e | Modify |

**Shared test helpers for the collector tests (Task 1) — the exact wiki-store idiom used by `tests/test_wiki_lint_materiality.py`:**

```python
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _reg_hz():
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def _f(fid, entity, indicatorId, *, as_of, magnitude=2, tier="secondary"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=[Evidence(source="src", url="u", date=as_of, excerpt="e", tier=tier)],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt=as_of, capturedAt=as_of + "-12")
```

**Shared test helpers for the renderer tests (Tasks 2 & 3) — build `MarketMovement` directly:**

```python
from gpu_agent.wiki.movement import MarketMovement, MovedRow, StorylineRow


def _moved(**kw):
    base = dict(title="NVDA — hot (rising)", findingIds=["f-1"], tier="primary",
                provisional=False, newThread=False, contradiction=False,
                contradictionNote="", stateFrom=None, stateTo=None, score=1.0)
    base.update(kw)
    return MovedRow(**base)


def _story(**kw):
    base = dict(title="AMD", state="on-track", trajectory="accelerating",
                lastUpdatedAsOf="2026-07", salience=0.8, provisional=False)
    base.update(kw)
    return StorylineRow(**base)


def _mv(**kw):
    base = dict(prevAsOf="2026-06", moved=[], foldedCount=0, storylines=[])
    base.update(kw)
    return MarketMovement(**base)
```

---

### Task 1: `wiki/movement.py` — the `MarketMovement` models + `collect_movement` collector

**Files:**
- Create: `gpu_agent/wiki/movement.py`
- Test: `tests/test_brief_movement.py`

**Interfaces:**
- Consumes: `WikiStore.diff`/`index`, `gpu_agent.wiki.lint.score_moves`/`_contradictions_for`/`DEFAULT_LINT_CONFIG`, `gpu_agent.wiki.lifecycle.partition_canonical`, `IndicatorRegistry`, `IndicatorHorizons`.
- Produces (used by Tasks 2–4): `MovedRow`, `StorylineRow`, `MarketMovement`, `collect_movement(store, *, as_of, prev_as_of, registry, horizons, config=DEFAULT_LINT_CONFIG) -> MarketMovement`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_brief_movement.py` (include the Task-1 shared helpers `_store`/`_reg_hz`/`_f` from the File Structure section above), then:

```python
from gpu_agent.wiki.movement import collect_movement


def test_collect_ranks_moves_splits_storylines_and_never_writes(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # cycle 1 (2026-05): NVDA — a scoring, leading, magnitude-3, primary finding; promote it to REGISTERED.
    route_findings(ws, [_f("f-nv1", "NVDA", "rpoBacklog", as_of="2026-05", magnitude=3, tier="primary")],
                   as_of="2026-05")
    ws.update_header("entity:nvda", as_of="2026-05", status="registered")
    ws.record_state("entity:nvda", as_of="2026-05", state="on-track", trajectory="accelerating", salience=0.9)
    # cycle 2 (2026-06): NVDA gets a new material finding; AMD is a NEW provisional overlay (low materiality).
    route_findings(ws, [_f("f-nv2", "NVDA", "rpoBacklog", as_of="2026-06", magnitude=3, tier="primary"),
                        _f("f-amd", "AMD", "gpuSpotPrice", as_of="2026-06")], as_of="2026-06")
    ws.record_state("entity:amd", as_of="2026-06", state="watch", trajectory="softening", salience=0.4)

    before = len(ws.log.read())
    mv = collect_movement(ws, as_of="2026-06", prev_as_of="2026-05", registry=reg, horizons=hz)
    assert len(ws.log.read()) == before                      # READ-ONLY: no lint/log write

    assert mv.prevAsOf == "2026-05"                           # carries the diff's prev cycle
    # NVDA is material (scoring/leading/primary); AMD (overlay) falls below threshold -> folded.
    assert mv.moved, "expected at least one material move"
    top = mv.moved[0]
    assert top.findingIds == ["f-nv2"]           # NVDA's this-cycle finding is the citation
    assert top.tier == "primary"                 # derived from tierMult
    assert top.provisional is False              # entity:nvda was promoted to registered
    assert mv.foldedCount >= 1                    # AMD overlay dropped below threshold

    # STORYLINES: entity:nvda registered (canonical), entity:amd provisional (confidence-capped).
    reg_titles = [s.title for s in mv.storylines if not s.provisional]
    prov_titles = [s.title for s in mv.storylines if s.provisional]
    assert "NVDA" in reg_titles and "AMD" in prov_titles


def test_collect_no_prior_still_lists_storylines(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-nv", "NVDA", "rpoBacklog", as_of="2026-06", magnitude=3, tier="primary")],
                   as_of="2026-06")
    ws.record_state("entity:nvda", as_of="2026-06", state="hot", trajectory="rising", salience=0.8)
    mv = collect_movement(ws, as_of="2026-06", prev_as_of=None, registry=reg, horizons=hz)
    assert mv.prevAsOf is None
    assert mv.moved == [] and mv.foldedCount == 0     # no diff without a prior cycle
    assert any(s.title == "NVDA" for s in mv.storylines)   # storylines still render


def test_collect_empty_store_is_empty(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    mv = collect_movement(ws, as_of="2026-06", prev_as_of="2026-05", registry=reg, horizons=hz)
    assert mv.moved == [] and mv.storylines == [] and mv.foldedCount == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_movement.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.wiki.movement'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/wiki/movement.py`:

```python
"""gpu_agent/wiki/movement.py — read-only collector for the brief's store-fed sections
(sub-project 4-5b). Assembles WHAT MOVED (ranked material moves) + STORYLINES (page
state/trajectory) from the wiki store as a plain MarketMovement value. No LLM, no store
write (never calls lint())."""
from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field
from gpu_agent.wiki.lint import score_moves, _contradictions_for, DEFAULT_LINT_CONFIG
from gpu_agent.wiki.lifecycle import partition_canonical


class MovedRow(BaseModel):
    title: str
    findingIds: list[str] = Field(default_factory=list)
    tier: Literal["primary", "secondary"]
    provisional: bool
    newThread: bool
    contradiction: bool
    contradictionNote: str = ""
    stateFrom: Optional[str] = None
    stateTo: Optional[str] = None
    score: float


class StorylineRow(BaseModel):
    title: str
    state: str
    trajectory: str
    lastUpdatedAsOf: str
    salience: float
    provisional: bool


class MarketMovement(BaseModel):
    prevAsOf: Optional[str] = None
    moved: list[MovedRow] = Field(default_factory=list)
    foldedCount: int = 0
    storylines: list[StorylineRow] = Field(default_factory=list)


def _moved_row(m, one_by_id) -> MovedRow:
    st = m.factors.stateTransition or {}
    return MovedRow(
        title=one_by_id.get(m.pageId, m.title),
        findingIds=list(m.contributingFindingIds),
        tier="primary" if m.tierMult >= 0.8 else "secondary",
        provisional=(m.status != "registered"),
        newThread=m.factors.newThread,
        contradiction=m.factors.contradiction,
        contradictionNote=m.factors.contradictionNote,
        stateFrom=st.get("from"),
        stateTo=st.get("to"),
        score=m.score)


def _storyline_rows(entries, *, provisional) -> list[StorylineRow]:
    # Row order is a display concern owned by render_storylines (which sorts each group);
    # the collector returns index order (sorted by category, id).
    return [StorylineRow(title=e.title, state=e.state, trajectory=e.trajectory,
                         lastUpdatedAsOf=e.lastUpdatedAsOf, salience=e.salience,
                         provisional=provisional) for e in entries]


def collect_movement(store, *, as_of, prev_as_of, registry, horizons,
                     config=DEFAULT_LINT_CONFIG) -> MarketMovement:
    """Read-only. WHAT MOVED via diff + score_moves (only when a prior cycle exists);
    STORYLINES via index + partition_canonical. Never writes (never calls lint())."""
    index = store.index()
    one_by_id = {e.id: e.oneLine for e in index}
    moved: list[MovedRow] = []
    folded = 0
    if prev_as_of is not None:
        diff = store.diff(as_of, prev_as_of)
        contradictions = _contradictions_for(store, as_of)
        material, dropped = score_moves(store, diff, contradictions, as_of=as_of,
                                        prev_as_of=prev_as_of, registry=registry,
                                        horizons=horizons, config=config)
        material.sort(key=lambda m: (-m.score, m.pageId))   # byte-stable tiebreak
        moved = [_moved_row(m, one_by_id) for m in material]
        folded = len(dropped)
    registered, provisional = partition_canonical(index)
    storylines = (_storyline_rows(registered, provisional=False)
                  + _storyline_rows(provisional, provisional=True))
    return MarketMovement(prevAsOf=prev_as_of, moved=moved, foldedCount=folded,
                          storylines=storylines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_movement.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 402 passed, 3 skipped (399 baseline + 3 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/movement.py tests/test_brief_movement.py && git commit -m "feat(4-5b): wiki/movement.py — read-only MarketMovement collector

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `brief.py` — `render_what_moved` (pure renderer)

**Files:**
- Modify: `gpu_agent/brief.py` (add the renderer + the shared trend-keyword map)
- Test: `tests/test_brief_moved.py`

**Interfaces:**
- Consumes: `MovedRow`/`MarketMovement` (Task 1).
- Produces (used by Task 4): `render_what_moved(movement) -> str`; the module-private `_traj_arrow(text) -> str` (reused by Task 3).

- [ ] **Step 1: Write the failing test**

Create `tests/test_brief_moved.py` (include the Tasks 2&3 shared helpers `_moved`/`_story`/`_mv` from the File Structure section above), then:

```python
from gpu_agent.brief import render_what_moved


def test_moved_tags_and_arrows():
    mv = _mv(prevAsOf="2026-06", moved=[
        _moved(title="AMD", newThread=True, findingIds=["f-217"], tier="primary"),
        _moved(title="Capex", contradiction=True, contradictionNote="guidance cut",
               findingIds=["f-241"], tier="secondary"),
        _moved(title="RPO", stateFrom="steady", stateTo="accelerating", findingIds=["f-203"]),
        _moved(title="Moat", stateFrom="intact", stateTo="eroding", findingIds=["f-198"]),
        _moved(title="Spot", stateFrom="firm", stateTo="firm", findingIds=["f-9"]),   # neutral kw
        _moved(title="Lead", findingIds=["f-5"]),                                     # indicator-only
    ])
    out = render_what_moved(mv)
    assert "WHAT MOVED SINCE LAST RUN  (vs 2026-06)" in out
    assert "▲ NEW    AMD" in out
    assert "▼ WATCH  Capex" in out and "(guidance cut)" in out
    assert "▲ UP     RPO" in out
    assert "▼ DOWN   Moat" in out
    assert "= CHANGED Spot" in out
    assert "= MOVED  Lead" in out


def test_moved_citation_tier_and_provisional():
    mv = _mv(moved=[_moved(title="AMD", findingIds=["f-1", "f-2"], tier="secondary",
                           newThread=True, provisional=True)])
    out = render_what_moved(mv)
    assert "[f-1, f-2] secondary" in out
    assert "(provisional)" in out


def test_moved_folded_footer():
    mv = _mv(moved=[_moved(newThread=True)], foldedCount=3)
    out = render_what_moved(mv)
    assert "(3 lower-materiality items folded — see wiki-lint)" in out


def test_moved_none_is_empty_state():
    out = render_what_moved(None)
    assert "WHAT MOVED SINCE LAST RUN" in out
    assert "no wiki store yet" in out


def test_moved_no_prior_note():
    out = render_what_moved(_mv(prevAsOf=None))
    assert "no prior cycle to compare" in out
    assert "(vs " not in out


def test_moved_empty_when_no_moves():
    out = render_what_moved(_mv(prevAsOf="2026-06", moved=[], foldedCount=0))
    assert "(no material moves this cycle)" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_moved.py -q`
Expected: FAIL with `ImportError: cannot import name 'render_what_moved'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/brief.py`, add at the end of the module:

```python
# ── store-fed sections (4-5b) ────────────────────────────────────────────────
_TRAJ_UP = {"accelerating", "improving", "rising", "up", "expanding", "strengthening", "hot"}
_TRAJ_DOWN = {"eroding", "worsening", "decelerating", "falling", "down", "slipping",
              "softening", "weakening", "contracting"}
_TRAJ_FLAT = {"steady", "flat", "stable", "unchanged", "tight", "intact", "firm", "on-track"}


def _traj_arrow(text) -> str:
    """Best-effort ▲/▼/=/· from brain-authored free-text state/trajectory (shared by the
    WHAT MOVED UP/DOWN tag and the STORYLINES arrow). Falls back to · on no keyword match."""
    t = (text or "").lower()
    if any(w in t for w in _TRAJ_UP):
        return "▲"
    if any(w in t for w in _TRAJ_DOWN):
        return "▼"
    if any(w in t for w in _TRAJ_FLAT):
        return "="
    return "·"


def _moved_tag(row):
    if row.newThread:
        return "NEW", "▲"
    if row.contradiction:
        return "WATCH", "▼"
    if row.stateTo:
        arrow = _traj_arrow(row.stateTo)
        if arrow == "▲":
            return "UP", "▲"
        if arrow == "▼":
            return "DOWN", "▼"
        return "CHANGED", "="
    return "MOVED", "="


def render_what_moved(movement) -> str:
    """WHAT MOVED SINCE LAST RUN: the materiality-ranked daily diff (4-4b score_moves),
    each row tagged NEW/WATCH/UP/DOWN/CHANGED/MOVED, cited + tiered, provisional marked;
    the folded below-threshold count shown. Pure; movement=None → honest empty-state."""
    lines = ["WHAT MOVED SINCE LAST RUN"]
    if movement is None:
        lines.append("  (no wiki store yet — needs a multi-cycle store from daily cycles)")
        return "\n".join(lines)
    if movement.prevAsOf is None:
        lines.append("  (no prior cycle to compare — first tracked cycle)")
        return "\n".join(lines)
    lines[0] += f"  (vs {movement.prevAsOf})"
    for row in movement.moved:
        tag, arrow = _moved_tag(row)
        cite = f"[{', '.join(row.findingIds)}]" if row.findingIds else "[—]"
        prov = "  (provisional)" if row.provisional else ""
        contra = f"  ({row.contradictionNote})" if row.contradiction and row.contradictionNote else ""
        lines.append(f"  {arrow} {tag:<6} {row.title}  {cite} {row.tier}{prov}{contra}")
    if not movement.moved:
        lines.append("  (no material moves this cycle)")
    if movement.foldedCount:
        lines.append(f"  ({movement.foldedCount} lower-materiality items folded — see wiki-lint)")
    return "\n".join(lines)
```

Note on the `{tag:<6}` padding: `NEW`/`UP`/`DOWN`/`WATCH`/`MOVED` pad to 6 so `test_moved_tags_and_arrows`'s literals (`"▲ NEW    AMD"` = `NEW` + 3 trailing spaces before the single row-separator space, etc.) match. If a literal spacing assertion mismatches in Step 4, adjust the assertion's spaces to the actual `f"  {arrow} {tag:<6} {title}…"` output (the tag column is `<6`, then one space) — do NOT change the format string.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_moved.py -q`
Expected: PASS (6 passed). If a spacing literal in `test_moved_tags_and_arrows` mismatches, correct that assertion's spaces to the real output and re-run (the format string is authoritative).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 408 passed, 3 skipped (402 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/brief.py tests/test_brief_moved.py && git commit -m "feat(4-5b): render_what_moved (ranked diff, tags/arrows, cited, folded)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `brief.py` — `render_storylines` (pure renderer)

**Files:**
- Modify: `gpu_agent/brief.py` (add the renderer; reuses `_traj_arrow` from Task 2)
- Test: `tests/test_brief_storylines.py`

**Interfaces:**
- Consumes: `StorylineRow`/`MarketMovement` (Task 1); `_traj_arrow` (Task 2).
- Produces (used by Task 4): `render_storylines(movement) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_brief_storylines.py` (include the Tasks 2&3 shared helpers `_moved`/`_story`/`_mv`), then:

```python
from gpu_agent.brief import render_storylines


def test_storylines_two_groups_arrows_and_order():
    mv = _mv(storylines=[
        _story(title="AMD", state="on-track", trajectory="accelerating", salience=0.5),
        _story(title="NVIDIA moat", state="intact", trajectory="eroding", salience=0.9),
        _story(title="Export controls", state="quiet", trajectory="quiet",
               salience=0.3, provisional=True),
    ])
    out = render_storylines(mv)
    assert "REGISTERED (canonical)" in out
    assert "PROVISIONAL (confidence-capped)" in out
    lines = out.splitlines()
    # registered ordered by salience desc: NVIDIA moat (0.9) before AMD (0.5)
    assert lines.index("    • NVIDIA moat  intact → eroding  (last updated 2026-07)  ▼") \
        < lines.index("    • AMD  on-track → accelerating  (last updated 2026-07)  ▲")
    # provisional group carries the quiet storyline with a · arrow
    assert "    • Export controls  quiet → quiet  (last updated 2026-07)  ·" in out


def test_storylines_none_is_empty_state():
    out = render_storylines(None)
    assert "STORYLINES (tracked over time)" in out
    assert "no wiki store yet" in out


def test_storylines_empty_index_note():
    out = render_storylines(_mv(storylines=[]))
    assert "(no tracked storylines yet)" in out


def test_storylines_one_group_empty_note():
    out = render_storylines(_mv(storylines=[_story(title="AMD")]))  # only registered
    assert "REGISTERED (canonical)" in out and "• AMD" in out
    assert "PROVISIONAL (confidence-capped)" in out
    assert "(none)" in out   # empty provisional group
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_storylines.py -q`
Expected: FAIL with `ImportError: cannot import name 'render_storylines'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/brief.py`, add at the end of the module:

```python
def _storyline_line(s) -> str:
    return (f"    • {s.title}  {s.state} → {s.trajectory}  "
            f"(last updated {s.lastUpdatedAsOf})  {_traj_arrow(s.trajectory)}")


def render_storylines(movement) -> str:
    """STORYLINES: the tracked threads' state → trajectory + last-change, split by
    partition_canonical into REGISTERED (canonical) and PROVISIONAL (confidence-capped),
    each ordered by salience desc. Pure; movement=None → honest empty-state."""
    lines = ["STORYLINES (tracked over time)"]
    if movement is None:
        lines.append("  (no wiki store yet — needs a multi-cycle store from daily cycles)")
        return "\n".join(lines)
    if not movement.storylines:
        lines.append("  (no tracked storylines yet)")
        return "\n".join(lines)
    _key = lambda s: (-s.salience, s.title)   # deterministic display order: salience desc, then title
    registered = sorted((s for s in movement.storylines if not s.provisional), key=_key)
    provisional = sorted((s for s in movement.storylines if s.provisional), key=_key)
    lines.append("  REGISTERED (canonical)")
    lines.extend(_storyline_line(s) for s in registered) if registered else lines.append("    (none)")
    lines.append("  PROVISIONAL (confidence-capped)")
    lines.extend(_storyline_line(s) for s in provisional) if provisional else lines.append("    (none)")
    return "\n".join(lines)
```

Note: `list.extend(...)` returns `None`, so the `A if cond else B` one-liners evaluate for their side effect only (both branches mutate `lines`); this is intentional and keeps the two groups symmetric. If that idiom reads poorly to you, replace each with a plain `if registered: lines.extend(...)` / `else: lines.append("    (none)")` block — behaviour identical.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_storylines.py -q`
Expected: PASS (4 passed). If a row literal mismatches on spacing, correct the assertion to the real `_storyline_line` output (the format string is authoritative).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 412 passed, 3 skipped (408 + 4 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/brief.py tests/test_brief_storylines.py && git commit -m "feat(4-5b): render_storylines (registered/provisional groups, arrows, ordered)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: compose into `render_report` + retire the stub + CLI `_report` wiring + guards

**Files:**
- Modify: `gpu_agent/brief.py` (retire `render_deferred_stubs`)
- Modify: `gpu_agent/report.py` (`render_report` only)
- Modify: `gpu_agent/cli.py` (`_report` handler + one import)
- Modify: `tests/test_brief_stubs.py` (remove the retired-renderer test)
- Test: `tests/test_brief_report.py` (extend)

**Interfaces:**
- Consumes: Task 1 `collect_movement`/`MarketMovement`; Task 2 `render_what_moved`; Task 3 `render_storylines`; the existing `render_report`, `load_scorecard`, `main`; `WikiStore`/`FindingStore`/`IndicatorHorizons` (already imported in `cli.py`).
- Produces: a brief-first `render_report(sc, prior, registry, render_ts=None, *, horizons=None, movement=None)`; the `report` CLI reads `<store>/wiki` and renders the two store-fed sections.

- [ ] **Step 1: Write the failing test**

Extend `tests/test_brief_report.py`. It already has the 4-5 `_sc`/`_ds`/`_f`/`_reg`/`_rich_sc` helpers — reuse them. Add the Task-1 wiki helpers it will need (`FindingStore`, `WikiStore`, `route_findings`, `IndicatorRegistry`, `IndicatorHorizons` are importable at module top; add them if absent), then append:

```python
import pathlib
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence
from gpu_agent.wiki.movement import MarketMovement, StorylineRow


def _story_movement():
    return MarketMovement(prevAsOf=None, moved=[], foldedCount=0, storylines=[
        StorylineRow(title="AMD", state="on-track", trajectory="accelerating",
                     lastUpdatedAsOf="2026-07", salience=0.8, provisional=False)])


def test_render_report_composes_store_sections_brief_first():
    out = render_report(_rich_sc(), None, _reg(), render_ts="t", movement=_story_movement())
    i_state = out.index("STATE OF THE MARKET")
    i_board = out.index("DEMAND | SUPPLY")
    i_moved = out.index("WHAT MOVED SINCE LAST RUN")
    i_story = out.index("STORYLINES (tracked over time)")
    i_detail = out.index("ENTITY PANEL")
    i_caveat = out.index("read DIRECTION, not level")
    assert i_state < i_board < i_moved < i_story < i_detail < i_caveat
    assert "• AMD  on-track → accelerating" in out   # real storyline, not the stub


def test_render_report_movement_none_is_empty_state():
    out = render_report(_rich_sc(), None, _reg(), render_ts="t", movement=None)
    assert "WHAT MOVED SINCE LAST RUN" in out and "STORYLINES (tracked over time)" in out
    assert "no wiki store yet" in out
    assert "rendered in 4-5b" not in out             # the promissory stub is retired


def test_render_report_byte_stable_with_movement():
    a = render_report(_rich_sc(), None, _reg(), render_ts="fixed", movement=_story_movement())
    b = render_report(_rich_sc(), None, _reg(), render_ts="fixed", movement=_story_movement())
    assert a == b


def _seed_store(root: pathlib.Path):
    ws = WikiStore(root / "wiki", FindingStore(root / "findings"))
    f = Finding(id="f-nv", statement="s", kind=Kind.observed, trend="flat", why="w",
                impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                evidence=[Evidence(source="src", url="u", date="2026-07", excerpt="e", tier="primary")],
                confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
                indicatorId="rpoBacklog", side="demand", polarityDemand=1, polaritySupply=0,
                magnitude=3, entity="NVDA", observedAt="2026-07", capturedAt="2026-07-12")
    route_findings(ws, [f], as_of="2026-07")
    ws.update_header("entity:nvda", as_of="2026-07", status="registered")
    ws.record_state("entity:nvda", as_of="2026-07", state="hot", trajectory="rising", salience=0.9)


def test_cli_report_renders_storylines_from_store(tmp_path, capsys):
    _seed_store(tmp_path)
    p = tmp_path / "sc.json"
    p.write_text(_rich_sc().model_dump_json(), encoding="utf-8")
    rc = main(["report", "--scorecard", str(p), "--store", str(tmp_path), "--no-prior",
               "--render-ts", "2026-07-02T00:00:00+00:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STORYLINES (tracked over time)" in out
    assert "• NVDA  hot → rising" in out                       # real storyline from the store
    assert "no prior cycle to compare" in out                 # --no-prior → WHAT MOVED note


def test_cli_report_no_wiki_store_is_empty_state(tmp_path, capsys):
    p = tmp_path / "sc.json"
    p.write_text(_rich_sc().model_dump_json(), encoding="utf-8")
    rc = main(["report", "--scorecard", str(p), "--store", str(tmp_path), "--no-prior",
               "--render-ts", "t"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no wiki store yet" in out                          # <store>/wiki absent → empty-state
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_report.py -q`
Expected: FAIL — `test_render_report_composes_store_sections_brief_first` raises `TypeError` (`render_report` has no `movement` kwarg) or `ValueError: substring not found` (the store sections aren't composed yet).

- [ ] **Step 3: Retire `render_deferred_stubs` in `gpu_agent/brief.py`**

Delete the `render_deferred_stubs` function from `brief.py` (added in 4-5). Leave `render_market_caveat` unchanged. (The two new renderers now cover the `movement=None` empty-state.)

- [ ] **Step 4: Edit `render_report` in `gpu_agent/report.py`**

Change the signature to add `*, movement=None` (after the existing `*, horizons=None` from 4-5) and replace the single `brief.render_deferred_stubs()` entry in the `sections` list with the two new renderers:

```python
def render_report(
    sc: Scorecard,
    prior: Optional[Scorecard],
    registry: IndicatorRegistry,
    render_ts: Optional[str] = None,
    *,
    horizons=None,
    movement=None,
) -> str:
    if render_ts is None:
        render_ts = datetime.now(timezone.utc).isoformat()

    sections = [
        render_header(sc, render_ts),
        brief.render_state_of_market(sc, prior),
        brief.render_demand_supply_board(sc, horizons),
        brief.render_what_moved(movement),        # was render_deferred_stubs (part 1)
        brief.render_storylines(movement),        # was render_deferred_stubs (part 2)
        render_overall_status(sc),
        render_dimensions(sc, prior),
        render_dmi_smi_sdgi(sc, prior),
        render_entity_panel(sc),
        render_evidence_quality(sc, registry),
        render_sources(sc),
        render_coverage_gaps(sc),
        brief.render_market_caveat(sc),
    ]
    return "\n\n".join(sections)
```

(Append one line to the docstring noting `movement`. Everything else in `report.py` is unchanged.)

- [ ] **Step 5: Edit the `_report` handler in `gpu_agent/cli.py`**

Add the import near the other `gpu_agent.wiki` imports at the top (cli.py:16–19):

```python
from gpu_agent.wiki.movement import collect_movement
```

The live handler (cli.py ~343–344) is exactly:

```python
    registry = IndicatorRegistry.load(args.registry)
    horizons = IndicatorHorizons.load(args.registry)   # (4-5)
    text = render_report(sc, prior, registry,
                         render_ts=getattr(args, "render_ts", None), horizons=horizons)
```

Replace those with a store-guarded movement load threaded into the existing call (reuse the already-imported `pathlib`/`WikiStore`/`FindingStore`):

```python
    registry = IndicatorRegistry.load(args.registry)
    horizons = IndicatorHorizons.load(args.registry)
    wiki_dir = pathlib.Path(args.store) / "wiki"
    movement = None
    if wiki_dir.exists():
        store = WikiStore(wiki_dir, FindingStore(pathlib.Path(args.store) / "findings"))
        prev_as_of = prior.asOf if prior is not None else None
        movement = collect_movement(store, as_of=sc.asOf, prev_as_of=prev_as_of,
                                    registry=registry, horizons=horizons)
    text = render_report(sc, prior, registry,
                         render_ts=getattr(args, "render_ts", None),
                         horizons=horizons, movement=movement)
```

Do NOT add a CLI flag and do NOT change any other line of `_report` (the variable is `text`, printed by the existing code below).

- [ ] **Step 6: Update `tests/test_brief_stubs.py`**

`render_deferred_stubs` no longer exists. Remove `test_deferred_stubs_name_4_5b` and its `render_deferred_stubs` import; keep `test_market_caveat` (and its `render_market_caveat` import). The file now has one test.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_brief_report.py tests/test_brief_stubs.py -q`
Expected: PASS (test_brief_report.py: 4 pre-existing 4-5 tests + 5 new = 9; test_brief_stubs.py: 1). If a store-fed row literal mismatches on spacing, correct the assertion to the real render output (the format strings are authoritative).

- [ ] **Step 8: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 416 passed, 3 skipped (412 + 5 new in test_brief_report.py − 1 removed from test_brief_stubs.py = 416). The existing `tests/test_report*.py` and the 4-5 `test_brief_report.py` order tests still pass (the two real sections occupy the stubs' positions; headers preserved).

- [ ] **Step 9: Run the frozen guards**

Run: `cd /c/Users/danie/random_for_fun && git diff --stat main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/schema/scorecard.py gpu_agent/pipeline.py gpu_agent/store.py gpu_agent/wiki/lint.py gpu_agent/wiki/lifecycle.py gpu_agent/wiki/page.py gpu_agent/wiki/log.py gpu_agent/wiki/ingest.py gpu_agent/wiki/dedup.py gpu_agent/gathering/`
Expected: **no output** (every frozen file byte-unchanged; the only `gpu_agent/` changes are the new `wiki/movement.py` and the additive `brief.py`/`report.py`/`cli.py` edits).

Run: `cd /c/Users/danie/random_for_fun && git diff main -- fixtures/`
Expected: **no output** (no committed fixture changed).

- [ ] **Step 10: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/brief.py gpu_agent/report.py gpu_agent/cli.py tests/test_brief_report.py tests/test_brief_stubs.py && git commit -m "feat(4-5b): compose store-fed sections into render_report + CLI wiring; retire stub

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-07-02-brief-store-fed-sections-design.md`):
- §0(a) scope = the two store-fed sections, WHY deferred → Tasks 1–4 (no WHY tree). ✓
- §0(b) precompute-and-pass; renderer pure; `movement=None` → empty-state → Task 1 (collector) + Tasks 2/3 (pure renderers, `None` branch) + Task 4 (CLI passes `movement`). ✓
- §0(c) collector is `wiki/movement.py`, reuses `score_moves`/`_contradictions_for`/`partition_canonical`, `brief.py` imports only the data type → Task 1. ✓
- §0(d) read-only, never `lint()` → Task 1 (uses `score_moves`) + the no-write assertion in `test_collect_ranks_moves_splits_storylines_and_never_writes`. ✓
- §0(e) store from the existing `--store` root, absent `<store>/wiki` → `movement=None` → stubs → Task 4 Step 5 (`wiki_dir.exists()` guard) + `test_cli_report_no_wiki_store_is_empty_state`. ✓
- §1 architecture (3 units + `MarketMovement` model + `render_report` `*, movement=None` + CLI wiring) → Tasks 1 (units+model) + 4 (compose+CLI). ✓
- §2① WHAT MOVED (ranked, tag/arrow precedence, citation+tier, provisional, folded footer, 3 degradations) → Task 2. ✓
- §2② STORYLINES (registered/provisional groups, trajectory→arrow, last-updated, salience order, empty notes) → Task 3. ✓
- §3 determinism (no wall-clock; data-derived recency; tiebreaks) → Task 1 moved `(-score, pageId)` + Task 3 storylines `(-salience, title)` (display order owned by the renderer) + Task 4 byte-stable test. ✓
- §4 frozen/additive boundary (new `wiki/movement.py`; retire `render_deferred_stubs`; `render_report`/`_report` edits; existing wiki modules byte-unchanged) → Task 4 Steps 3–5 + Step 9 guards. ✓
- §5 doctrine (pure/read-only/honest/replayable; `movement=None` accurate empty-state, no promissory "4-5b" text) → `test_render_report_movement_none_is_empty_state` asserts `"rendered in 4-5b" not in out`. ✓
- §7 test strategy (in-code 2-cycle store; renderer in-code data; composition; CLI e2e; guards) → every task. ✓
- §9 acceptance items 1–6 all map to tasks above. ✓

**Placeholder scan:** none — every code step has complete code; every test step has complete assertions. Two steps (Task 2 Step 3 padding note, Task 3 Step 3 `extend`-idiom note) point the implementer at the authoritative format string for spacing literals; these are grounding notes, not placeholders.

**Type consistency:** `collect_movement(store, *, as_of, prev_as_of, registry, horizons, config=DEFAULT_LINT_CONFIG) -> MarketMovement` (Task 1) is called with exactly those kwargs by `_report` (Task 4). `render_what_moved(movement)` (Task 2), `render_storylines(movement)` (Task 3) are called by `render_report` (Task 4) with the `MarketMovement | None` value. `MarketMovement`/`MovedRow`/`StorylineRow` field names (`prevAsOf`, `moved`, `foldedCount`, `storylines`; `title`, `findingIds`, `tier`, `provisional`, `newThread`, `contradiction`, `contradictionNote`, `stateFrom`, `stateTo`, `score`; `state`, `trajectory`, `lastUpdatedAsOf`, `salience`) are used identically in the collector (Task 1), the renderers (Tasks 2/3), and the test helpers. `render_report` gains `*, horizons=None, movement=None` (backward-compatible; 4-5 callers unaffected). `_traj_arrow` defined in Task 2 is reused by Task 3.

**Controller-confirmed (against live code at plan time):** `score_moves(store, diff, contradictions, *, as_of, prev_as_of, registry, horizons, config)` returns `(material, dropped)` and is **read-only** (only `lint()` appends the log event) — verified at `wiki/lint.py:250` + `:307`; `MaterialMove` carries `pageId`/`title`/`type`/`status`/`score`/`factors`(`newThread`/`contradiction`/`contradictionNote`/`stateTransition`)/`contributingFindingIds`/`tierMult` (`wiki/lint.py:24`); `partition_canonical(index) -> (registered, provisional)` (`wiki/lifecycle.py:100`); `IndexEntry` carries `id`/`title`/`status`/`state`/`trajectory`/`salience`/`lastUpdatedAsOf`/`oneLine` with `oneLine = "<title> — <state> (<trajectory>)"` (`wiki/store.py:182`); `WikiStore.diff(as_of, prev_as_of)` + `index()` exist; `route_findings`/`record_state`/`update_header` are the store-seeding idiom (`tests/test_wiki_lint_materiality.py`); `cli.py` already imports `pathlib`/`WikiStore`/`FindingStore`/`IndicatorHorizons`/`render_report` (cli.py:2/15/16/28/32) and the `_report` handler loads `registry`+`horizons` and supports `--store`/`--no-prior`/`--render-ts`; `report.py`'s `render_report` composes the 4-5 brief-first sections incl. `brief.render_deferred_stubs()` in the WHAT-MOVED/STORYLINES position; `brief.py` has `render_deferred_stubs`/`render_market_caveat` (4-5).

**Test-count math:** baseline 399 → +3 (T1) → +6 (T2) → +4 (T3) → +5 −1 (T4: 5 new in test_brief_report.py, 1 removed from test_brief_stubs.py) = **416 passed, 3 skipped** at the end.
