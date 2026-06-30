# Relevance engine — the wiki lint pass (sub-project 4-4b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the wiki **lint / early-warning pass** — a pure-code, deterministic `LintReport` over the store that ranks the day's material moves (the 4 factors, hybrid weighting), decays quiet threads (tag-derived half-life), and surfaces structural health (orphans / stale / cross-ref gaps / contradictions) — all additive, with the frozen contract byte-unchanged and no new brain step.

**Architecture:** A new pure module `gpu_agent/wiki/lint.py` reads the store (`diff`/`index`/`observations`/`log`), the `FindingStore`, and the registry (`IndicatorRegistry` scoring split + `IndicatorHorizons` cadence/horizon tags) and returns a structured `LintReport`. Relevance = the brain's intrinsic `salience` (4-4a) × code-derived factor/tier/recency weights; persistence (decay half-life) = input-derived from 4-2's `cadence × horizon` tags. A shared contradiction format/parse helper in our own `ingest.py` lets the lint pass read 4-4a's brain-flagged contradiction without scraping fragile free text. A `wiki-lint` CLI subcommand mirrors `wiki-ingest` (no brain seam) and emits one idempotent `lint` log event per cycle.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), stdlib `re`/`json`/`pathlib`, pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset on Windows — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`/`validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, the existing `JsonStore`/`FindingStore` (`gpu_agent/store.py`), **every member of `gpu_agent/wiki/store.py`** (incl. 4-4a's `set_body`), `gpu_agent/wiki/log.py`, and `gpu_agent/wiki/page.py`.
- **Modified additively (behavior-preserving) in `gpu_agent/wiki/ingest.py`:** add `format_contradiction_detail`/`parse_contradiction_detail`; refactor `apply_enrichment` to build its `detail` via the formatter (output string unchanged — existing 4-4a tests stay green); add the `PageEnrichment.salience` range bound. 4-4a's `slug`/`route_findings`/`build_bundle`/`IngestResult`/`INGEST_SYSTEM` are otherwise untouched.
- **Additive only** (Part 33): the new module `gpu_agent/wiki/lint.py`; the `wiki-lint` CLI subcommand in `cli.py`. Do NOT edit any committed fixture under `fixtures/`.
- **Doctrine:** numbers only from gated findings (Part 17 — the scorer reads structured `Finding`/diff/registry values, writes none); nothing silent (Part 29 — dropped moves are reported + counted; an untagged indicator's half-life fallback is logged); replayable (Part 20 — non-destructive read-time computation + one idempotent `lint` event); 4-4b **mutates no page lifecycle** (no promote/prune/`record_state`).
- **Determinism:** no wall-clock; `as_of` is always passed in; re-running a cycle is a no-op (the `lint` event is idempotent per `asOf`).
- **The full suite stays green after every task.** Baseline: **300 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file guard** (Task 6 Step 5): the only `gpu_agent/` changes are the new `wiki/lint.py`, the additive `ingest.py` edits, and the additive `cli.py` edits — every frozen file above stays byte-unchanged and no `fixtures/` file changes.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gpu_agent/wiki/ingest.py` | the ingest writer | Modify: add contradiction format/parse helpers; `apply_enrichment` uses the formatter; `PageEnrichment.salience` bound |
| `gpu_agent/wiki/lint.py` | the lint pass: models, `LintConfig`, decay, materiality scorer, health, `lint()` | Create |
| `gpu_agent/cli.py` | CLI entry points | Modify: add `wiki-lint` subparser + `_wiki_lint` handler + dispatch |
| `tests/test_wiki_ingest_seam.py` | contradiction round-trip + salience bound | Create |
| `tests/test_wiki_lint_models.py` | data models + `LintConfig` defaults | Create |
| `tests/test_wiki_lint_decay.py` | half-life + quiet-age + decay | Create |
| `tests/test_wiki_lint_materiality.py` | the materiality scorer | Create |
| `tests/test_wiki_lint_health.py` | structural health checks | Create |
| `tests/test_wiki_lint_cli.py` | `lint()` assembly end-to-end + CLI | Create |

**Note on `CrossRefGap` field naming:** the spec §8 writes the gap as `{from, to, reason}`. `from` is a Python keyword, so the model uses **`source`/`target`/`reason`** — the keyword-safe realization of the spec's intent.

---

### Task 1: `ingest.py` — contradiction seam + salience bound

**Files:**
- Modify: `gpu_agent/wiki/ingest.py`
- Test: `tests/test_wiki_ingest_seam.py`

**Interfaces:**
- Consumes: existing `apply_enrichment`, `PageEnrichment`, `IngestResult`.
- Produces:
  - `format_contradiction_detail(enriched_count: int, contradictions: list[tuple[str, str]]) -> str`
  - `parse_contradiction_detail(detail: str) -> dict` (`{"count": int, "contradictions": [{"pageId","note"}]}`)
  - `PageEnrichment.salience` now bounded `[0.0, 1.0]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_ingest_seam.py`:

```python
import pytest
from pydantic import ValidationError
from gpu_agent.wiki.ingest import (
    format_contradiction_detail, parse_contradiction_detail, PageEnrichment)


def test_format_parse_roundtrip():
    detail = format_contradiction_detail(2, [("entity:nvda", "guidance cut"),
                                             ("entity:amd", "share loss")])
    assert detail == ("enriched 2 page(s); contradictions: "
                      "entity:nvda: guidance cut | entity:amd: share loss")
    parsed = parse_contradiction_detail(detail)
    assert parsed["count"] == 2
    assert parsed["contradictions"] == [
        {"pageId": "entity:nvda", "note": "guidance cut"},
        {"pageId": "entity:amd", "note": "share loss"}]


def test_format_parse_no_contradictions():
    detail = format_contradiction_detail(1, [])
    assert detail == "enriched 1 page(s)"
    parsed = parse_contradiction_detail(detail)
    assert parsed == {"count": 1, "contradictions": []}


def test_parse_keeps_entity_colon_and_note_colon():
    # pageId contains ':' (no space); a note may contain ': ' — the FIRST ': ' splits id from note.
    detail = format_contradiction_detail(1, [("entity:nvda", "guidance: cut deep")])
    parsed = parse_contradiction_detail(detail)
    assert parsed["contradictions"] == [{"pageId": "entity:nvda", "note": "guidance: cut deep"}]


def test_salience_bound_rejects_out_of_range():
    with pytest.raises(ValidationError):
        PageEnrichment(pageId="entity:nvda", bodyMarkdown="b", state="s",
                       trajectory="t", salience=5.0)


def test_salience_bound_accepts_edges():
    for s in (0.0, 1.0):
        pe = PageEnrichment(pageId="entity:nvda", bodyMarkdown="b", state="s",
                            trajectory="t", salience=s)
        assert pe.salience == s
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_seam.py -q`
Expected: FAIL with `ImportError: cannot import name 'format_contradiction_detail'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/ingest.py`, change the `PageEnrichment.salience` line from:

```python
    salience: float
```
to:
```python
    salience: float = Field(ge=0.0, le=1.0)
```
(`Field` is already imported.)

Add these two helpers immediately after the `slug` function (before `class PageEnrichment`):

```python
def format_contradiction_detail(enriched_count: int, contradictions: list[tuple[str, str]]) -> str:
    """Canonical ingest-event detail. `contradictions` is a list of (pageId, note). One source of
    format truth, shared by apply_enrichment (writer) and the lint pass (reader)."""
    detail = f"enriched {enriched_count} page(s)"
    if contradictions:
        detail += "; contradictions: " + " | ".join(f"{pid}: {note}" for pid, note in contradictions)
    return detail


def parse_contradiction_detail(detail: str) -> dict:
    """Inverse of format_contradiction_detail. Note: a note containing ' | ' would over-split; notes
    are short phrases and this is our own controlled format (round-trip tested)."""
    count = 0
    m = re.match(r"enriched (\d+) page\(s\)", detail)
    if m:
        count = int(m.group(1))
    contradictions: list[dict] = []
    marker = "; contradictions: "
    idx = detail.find(marker)
    if idx != -1:
        rest = detail[idx + len(marker):]
        for part in rest.split(" | "):
            pid, sep, note = part.partition(": ")  # pageId has no ': ' (colon-space); first split is the boundary
            if sep:
                contradictions.append({"pageId": pid, "note": note})
    return {"count": count, "contradictions": contradictions}
```

Then refactor `apply_enrichment` to build its detail via the formatter. Replace this block:

```python
    already_logged = any(e.kind == "ingest" and e.asOf == as_of for e in store.log.read())
    if not already_logged:
        detail = f"enriched {len(result.pages)} page(s)"
        if contradictions:
            detail += "; contradictions: " + " | ".join(contradictions)
        store.log.append(asOf=as_of, kind="ingest", detail=detail)
```

with:

```python
    already_logged = any(e.kind == "ingest" and e.asOf == as_of for e in store.log.read())
    if not already_logged:
        detail = format_contradiction_detail(len(result.pages), contradictions)
        store.log.append(asOf=as_of, kind="ingest", detail=detail)
```

and change the contradiction accumulation inside the loop from the string form to a `(pageId, note)` tuple. Replace:

```python
        if pe.contradictsThesis:
            contradictions.append(f"{pe.pageId}: {pe.contradictionNote}")
```
with:
```python
        if pe.contradictsThesis:
            contradictions.append((pe.pageId, pe.contradictionNote))
```

(The emitted detail string is byte-identical to before, so the existing 4-4a apply tests stay green.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_seam.py tests/test_wiki_ingest_apply.py -q`
Expected: PASS (5 new + the 5 existing apply tests still green = 10 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 305 passed, 3 skipped (300 baseline + 5 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/ingest.py tests/test_wiki_ingest_seam.py && git commit -m "feat(4-4b): contradiction format/parse seam + PageEnrichment salience bound

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `lint.py` — data models + `LintConfig`

**Files:**
- Create: `gpu_agent/wiki/lint.py`
- Test: `tests/test_wiki_lint_models.py`

**Interfaces:**
- Produces (consumed by all later tasks): `IndicatorMove`, `MoveFactors`, `MaterialMove`, `CrossRefGap`, `ContradictionEntry`, `StaleEntry`, `HealthReport`, `LintReport`, `LintConfig`, `DEFAULT_LINT_CONFIG`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_lint_models.py`:

```python
import json
from gpu_agent.wiki.lint import (
    IndicatorMove, MoveFactors, MaterialMove, CrossRefGap, ContradictionEntry,
    StaleEntry, HealthReport, LintReport, LintConfig, DEFAULT_LINT_CONFIG)


def test_lint_config_defaults():
    c = DEFAULT_LINT_CONFIG
    assert (c.w_contra, c.w_state, c.w_new, c.w_ind) == (1.0, 0.6, 0.5, 0.3)
    assert (c.h_short, c.h_med, c.h_long) == (1, 3, 6)
    assert c.material_threshold == 0.3
    assert c.stale_threshold == 0.1
    assert (c.tier_primary, c.tier_secondary) == (1.0, 0.6)
    assert (c.recency_full, c.recency_decayed) == (1.0, 0.7)
    assert c.salience_floor == 0.5
    assert c.horizon_boost_leading == 0.5


def test_crossrefgap_fields():
    g = CrossRefGap(source="entity:nvda", target="entity:amd", reason="asymmetric")
    assert (g.source, g.target, g.reason) == ("entity:nvda", "entity:amd", "asymmetric")


def test_lintreport_roundtrip():
    mv = MaterialMove(
        pageId="entity:nvda", title="NVDA", type="entity", status="provisional",
        score=1.05, factors=MoveFactors(newThread=True,
                                        indicatorMoves=[IndicatorMove(indicatorId="rpoBacklog",
                                                                      magnitude=3, scoring=True)]),
        contributingFindingIds=["f-1"], tierMult=1.0, recencyMult=1.0, effectiveSalience=0.0)
    report = LintReport(
        asOf="2026-06", prevAsOf=None, material=[mv], dropped=[],
        health=HealthReport(orphans=["entity:intc"],
                            stale=[StaleEntry(pageId="entity:old", effectiveSalience=0.04)],
                            crossRefGaps=[CrossRefGap(source="entity:nvda", target="entity:amd",
                                                      reason="mention-without-link")],
                            contradictions=[ContradictionEntry(pageId="entity:nvda",
                                                               note="guidance cut", asOf="2026-06")]))
    blob = json.loads(report.model_dump_json())
    assert blob["material"][0]["factors"]["indicatorMoves"][0]["scoring"] is True
    assert blob["health"]["crossRefGaps"][0]["source"] == "entity:nvda"
    assert blob["health"]["orphans"] == ["entity:intc"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.wiki.lint'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/wiki/lint.py`:

```python
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_models.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 308 passed, 3 skipped (305 + 3 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lint.py tests/test_wiki_lint_models.py && git commit -m "feat(4-4b): lint data models + LintConfig policy table

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `lint.py` — salience decay (half-life + quiet-age)

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (add decay helpers)
- Test: `tests/test_wiki_lint_decay.py`

**Interfaces:**
- Consumes: `LintConfig` (Task 2); `WikiStore` (`log`, `observations`, `findings.get`, `get_page`); `IndicatorHorizons` (`get`); `Finding` (`indicatorId`).
- Produces:
  - `half_life(findings: list, horizons, config) -> tuple[int, list[str]]` (cycles, untagged indicator ids).
  - `quiet_age(store, page_id, as_of) -> int`.
  - `decay(quiet_age: int, half_life: int) -> float`.
  - `effective_salience(intrinsic: float, quiet_age: int, half_life: int) -> float`.
  - `_findings_for(store, page_id, observations) -> list` (resolve observation finding ids; skip missing).

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_lint_decay.py`:

```python
import math
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import (half_life, quiet_age, decay, effective_salience,
                                 DEFAULT_LINT_CONFIG)
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId="D2"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


_HZ = IndicatorHorizons({
    "daily-coin": {"cadence": "daily", "horizon": "coincident"},
    "daily-lead": {"cadence": "daily", "horizon": "leading"},
    "quarterly-coin": {"cadence": "quarterly", "horizon": "coincident"},
})


def test_half_life_daily_short():
    hl, untagged = half_life([_f("f1", "A", "daily-coin")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 1 and untagged == []


def test_half_life_quarterly_long():
    hl, _ = half_life([_f("f1", "A", "quarterly-coin")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 6


def test_half_life_leading_floor():
    # daily would be 1, but a leading-horizon signal is floored at H_med (3)
    hl, _ = half_life([_f("f1", "A", "daily-lead")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 3


def test_half_life_longest_class_wins():
    hl, _ = half_life([_f("f1", "A", "daily-coin"), _f("f2", "A", "quarterly-coin")],
                      _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 6


def test_half_life_untagged_default_and_logged():
    hl, untagged = half_life([_f("f1", "A", "ghost-ind")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 3 and untagged == ["ghost-ind"]


def test_quiet_age_fresh_is_zero(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-06")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 0


def test_quiet_age_counts_intervening_cycles(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-04")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-04")
    # two later cycles touch OTHER pages -> distinct asOf cycles 2026-05, 2026-06
    ws.create_page("entity:b", "entity", "B", as_of="2026-05")
    ws.findings.append(_f("f2", "B"))
    ws.append_observation("entity:b", "f2", as_of="2026-05")
    ws.findings.append(_f("f3", "B"))
    ws.append_observation("entity:b", "f3", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 2


def test_quiet_age_material_update_resets(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-04")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-04")
    ws.create_page("entity:b", "entity", "B", as_of="2026-05")
    ws.findings.append(_f("f2", "B"))
    ws.append_observation("entity:b", "f2", as_of="2026-05")
    # a gets a NEW observation at 2026-06 -> quietness resets
    ws.findings.append(_f("f3", "A"))
    ws.append_observation("entity:a", "f3", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 0


def test_decay_and_effective_salience():
    assert math.isclose(decay(2, 3), 0.5 ** (2 / 3))
    assert math.isclose(decay(0, 6), 1.0)
    assert math.isclose(effective_salience(0.8, 1, 1), 0.4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_decay.py -q`
Expected: FAIL with `ImportError: cannot import name 'half_life'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/lint.py`, add the import line at the top (after the existing imports):

```python
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons
```

Add these helpers at the end of the module:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_decay.py -q`
Expected: PASS (9 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 317 passed, 3 skipped (308 + 9 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lint.py tests/test_wiki_lint_decay.py && git commit -m "feat(4-4b): salience decay — tag-derived half-life + cycle-count quiet-age (non-destructive)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `lint.py` — the materiality scorer

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (add the scorer)
- Test: `tests/test_wiki_lint_materiality.py`

**Interfaces:**
- Consumes: Task 2 models, Task 3 decay helpers; `WikiStore` (`get_page`, `observations`); `IndicatorRegistry` (`resolve` → `.scoring`/`.side`; `RegistryError`); `IndicatorHorizons` (`get`); `Finding` (`magnitude`, `evidence[].tier`, `indicatorId`); `WikiDiff` (`new_pages`/`changed_pages`/`index_moves`, each with `.id`; `PageDelta.stateTransition`; `IndexMove.oldState`/`newState`).
- Produces:
  - `_is_scoring(registry, indicator_id) -> Optional[bool]` (None if unregistered; True iff `scoring and side not in {price,structural}`).
  - `_score_move(store, page_id, *, as_of, prev_as_of, is_new, state_transition, contradiction_note, registry, horizons, config) -> MaterialMove`.
  - `score_moves(store, diff, contradictions, *, as_of, prev_as_of, registry, horizons, config) -> tuple[list[MaterialMove], list[MaterialMove]]` (material, dropped — both ranked desc).

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_lint_materiality.py`:

```python
import math
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import _score_move, score_moves, DEFAULT_LINT_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _reg_hz():
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def _f(fid, entity, indicatorId, magnitude=2, tier="secondary"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=[Evidence(source="src", url="u", date="2026-06", excerpt="e", tier=tier)],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def test_score_new_thread_nonscoring(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # gpuSpotPrice: scoring=False (price overlay), daily/coincident (no leading boost)
    route_findings(ws, [_f("f-1", "NVDA", "gpuSpotPrice")], as_of="2026-06")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=True,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.newThread is True
    assert mv.factors.indicatorMoves[0].scoring is False  # overlay excluded from the indicator factor
    assert mv.tierMult == 0.6 and mv.recencyMult == 1.0   # secondary tier, observed this cycle
    # base = w_new 0.5 (no scoring indicator) ; *0.6 *1.0 *(1+0) *max(0.5,0)=0.5
    assert math.isclose(mv.score, 0.5 * 0.6 * 1.0 * 1.0 * 0.5)


def test_score_scoring_indicator_and_leading_boost(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # rpoBacklog: scoring=True (demand), quarterly/leading, magnitude 3, primary evidence
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog", magnitude=3, tier="primary")], as_of="2026-06")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=False,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.indicatorMoves[0].scoring is True
    assert mv.factors.indicatorMoves[0].magnitude == 3
    # base = w_ind 0.3 * 3 = 0.9 ; tier primary 1.0 ; recency 1.0 ; leading boost (1+0.5) ; salience 0.5
    assert math.isclose(mv.score, 0.9 * 1.0 * 1.0 * 1.5 * 0.5)


def test_score_state_change_factor(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog")], as_of="2026-05")  # findings in a PRIOR cycle
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of="2026-05", is_new=False,
                     state_transition={"from": "steady", "to": "slipping"}, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.stateTransition == {"from": "steady", "to": "slipping"}
    assert mv.factors.newThread is False
    assert mv.recencyMult == 0.7   # no finding observed in THIS cycle (window 2026-05<asOf<=2026-06 is empty)
    # base = w_state 0.6 ; tier secondary 0.6 (no this-cycle findings) ; recency 0.7 ; no boost ; salience 0.5
    assert math.isclose(mv.score, 0.6 * 0.6 * 0.7 * 1.0 * 0.5)


def test_score_contradiction_highest(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog")], as_of="2026-05")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of="2026-05", is_new=False,
                     state_transition=None, contradiction_note="guidance cut",
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.contradiction is True and mv.factors.contradictionNote == "guidance cut"
    # base = w_contra 1.0 ; tier secondary 0.6 ; recency 0.7 ; salience 0.5
    assert math.isclose(mv.score, 1.0 * 0.6 * 0.7 * 1.0 * 0.5)


def test_score_salience_weight_lifts_with_brain_salience(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog", magnitude=3, tier="primary")], as_of="2026-06")
    ws.record_state("entity:nvda", as_of="2026-06", state="hot", trajectory="up", salience=0.9)
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=False,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    # salience_weight = max(0.5, 0.9) = 0.9 ; base 0.9 ; primary 1.0 ; recency 1.0 ; leading 1.5
    assert math.isclose(mv.score, 0.9 * 1.0 * 1.0 * 1.5 * 0.9)
    assert math.isclose(mv.effectiveSalience, 0.9)  # fresh move (quiet_age 0) -> effective == intrinsic


def test_score_moves_threshold_split_and_sorted(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # NVDA: a scoring leading magnitude-3 finding -> high score (material).
    # AMD: a non-scoring overlay finding -> low score (dropped under threshold 0.3).
    route_findings(ws, [_f("f-nv", "NVDA", "rpoBacklog", magnitude=3, tier="primary"),
                        _f("f-amd", "AMD", "gpuSpotPrice")], as_of="2026-06")
    diff = ws.diff("2026-06", "")
    material, dropped = score_moves(ws, diff, {}, as_of="2026-06", prev_as_of=None,
                                    registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    mat_ids = [m.pageId for m in material]
    drop_ids = [m.pageId for m in dropped]
    assert "entity:nvda" in mat_ids and "entity:amd" in drop_ids
    assert material == sorted(material, key=lambda m: m.score, reverse=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_materiality.py -q`
Expected: FAIL with `ImportError: cannot import name '_score_move'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/lint.py`, add this import at the top (after the existing ones):

```python
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
```

Add at the end of the module:

```python
def _is_scoring(registry, indicator_id):
    """True iff the indicator contributes to the index (the frozen dmi_smi split:
    scoring AND side not in {price, structural}). None if the id is unregistered."""
    try:
        spec = registry.resolve(indicator_id)
    except RegistryError:
        return None
    return bool(spec.scoring and spec.side not in ("price", "structural"))


def _score_move(store, page_id, *, as_of, prev_as_of, is_new, state_transition,
                contradiction_note, registry, horizons, config=DEFAULT_LINT_CONFIG):
    page = store.get_page(page_id)
    lo = prev_as_of or ""
    window = [o for o in store.observations(page_id) if lo < o.asOf <= as_of]
    contributing = []
    pairs = []  # (observation, finding)
    for o in window:
        try:
            pairs.append((o, store.findings.get(o.findingId)))
            contributing.append(o.findingId)
        except Exception:
            continue

    factors = MoveFactors()
    base = 0.0
    if is_new:
        base += config.w_new
        factors.newThread = True
    if (not is_new) and state_transition is not None:
        base += config.w_state
        factors.stateTransition = state_transition
    if contradiction_note is not None:
        base += config.w_contra
        factors.contradiction = True
        factors.contradictionNote = contradiction_note

    ind_sum = 0
    for _, f in pairs:
        sc = _is_scoring(registry, f.indicatorId)
        scoring = bool(sc)
        factors.indicatorMoves.append(
            IndicatorMove(indicatorId=f.indicatorId, magnitude=f.magnitude, scoring=scoring))
        if scoring:
            ind_sum += f.magnitude
    base += config.w_ind * ind_sum

    has_primary = any(any(e.tier == "primary" for e in f.evidence) for _, f in pairs)
    tier_mult = config.tier_primary if has_primary else config.tier_secondary
    this_cycle = any(o.asOf == as_of for o, _ in pairs)
    recency_mult = config.recency_full if this_cycle else config.recency_decayed
    leading = any((horizons.get(f.indicatorId) or {}).get("horizon") == "leading" for _, f in pairs)
    horizon_boost = config.horizon_boost_leading if leading else 0.0
    salience_weight = max(config.salience_floor, page.salience)
    score = base * tier_mult * recency_mult * (1 + horizon_boost) * salience_weight

    all_findings = _findings_for(store, page_id, store.observations(page_id))
    hl, _untagged = half_life(all_findings, horizons, config)
    eff = effective_salience(page.salience, quiet_age(store, page_id, as_of), hl)

    return MaterialMove(pageId=page_id, title=page.title, type=page.type, status=page.status,
                        score=score, factors=factors, contributingFindingIds=contributing,
                        tierMult=tier_mult, recencyMult=recency_mult, effectiveSalience=eff)


def score_moves(store, diff, contradictions, *, as_of, prev_as_of, registry, horizons,
                config=DEFAULT_LINT_CONFIG):
    """Assemble the move-set (diff pages + any contradicted page), score each, split on the
    material threshold. Both lists are ranked by score descending."""
    new_ids = {pd.id for pd in diff.new_pages}
    delta_by_id = {pd.id: pd for pd in (list(diff.new_pages) + list(diff.changed_pages))}
    im_by_id = {im.id: im for im in diff.index_moves}
    move_ids = (new_ids | {pd.id for pd in diff.changed_pages}
                | set(im_by_id) | set(contradictions))
    material, dropped = [], []
    for pid in sorted(move_ids):
        is_new = pid in new_ids
        st = None
        if not is_new:
            delta = delta_by_id.get(pid)
            if delta is not None and delta.stateTransition is not None:
                st = delta.stateTransition
            elif pid in im_by_id:
                im = im_by_id[pid]
                st = {"from": im.oldState, "to": im.newState}
        note = contradictions.get(pid)  # None when the page has no contradiction this cycle
        mv = _score_move(store, pid, as_of=as_of, prev_as_of=prev_as_of, is_new=is_new,
                         state_transition=st, contradiction_note=note,
                         registry=registry, horizons=horizons, config=config)
        (material if mv.score >= config.material_threshold else dropped).append(mv)
    material.sort(key=lambda m: m.score, reverse=True)
    dropped.sort(key=lambda m: m.score, reverse=True)
    return material, dropped
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_materiality.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 323 passed, 3 skipped (317 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lint.py tests/test_wiki_lint_materiality.py && git commit -m "feat(4-4b): materiality scorer — 4 factors, hybrid weighting, threshold split

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `lint.py` — structural health checks

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (add `health_report`)
- Test: `tests/test_wiki_lint_health.py`

**Interfaces:**
- Consumes: Task 2 models, Task 3 decay helpers; `WikiStore` (`index`, `get_page`, `observations`, `window`).
- Produces: `health_report(store, *, as_of, contradictions, horizons, config) -> HealthReport`.
  - **orphans** — pages with no inbound `crossRef`.
  - **stale** — pages with `quiet_age > 0` and `effective_salience < stale_threshold` (a brand-new page is never stale).
  - **crossRefGaps** — `asymmetric` (A lists B, B doesn't list A) + `mention-without-link` (a page's body contains another page's title but doesn't list it).
  - **contradictions** — `{pageId, note, asOf}` from the passed `contradictions` dict.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_lint_health.py`:

```python
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import health_report, DEFAULT_LINT_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId="gpuSpotPrice"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


_HZ = IndicatorHorizons.load("registry/indicators.json")


def test_health_orphans(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06", body="")
    ws.create_page("entity:amd", "entity", "AMD", as_of="2026-06", body="")
    ws.update_header("entity:nvda", as_of="2026-06", crossRefs=["entity:amd"])
    h = health_report(ws, as_of="2026-06", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    # amd is referenced by nvda -> not orphan ; nvda has no inbound ref -> orphan
    assert "entity:nvda" in h.orphans and "entity:amd" not in h.orphans


def test_health_asymmetric_crossref(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06", body="")
    ws.create_page("entity:amd", "entity", "AMD", as_of="2026-06", body="")
    ws.update_header("entity:nvda", as_of="2026-06", crossRefs=["entity:amd"])
    h = health_report(ws, as_of="2026-06", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    gaps = [(g.source, g.target, g.reason) for g in h.crossRefGaps]
    assert ("entity:nvda", "entity:amd", "asymmetric") in gaps


def test_health_mention_without_link(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06",
                   body="## NVDA\nCompetes with AMD on data-center GPUs.\n")
    ws.create_page("entity:amd", "entity", "AMD", as_of="2026-06", body="")
    h = health_report(ws, as_of="2026-06", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    gaps = [(g.source, g.target, g.reason) for g in h.crossRefGaps]
    assert ("entity:nvda", "entity:amd", "mention-without-link") in gaps


def test_health_stale_excludes_fresh(tmp_path):
    ws = _store(tmp_path)
    # OLD page: daily-tagged finding (half-life 1), salience 0.5, quiet for 4 cycles -> eff 0.03125 < 0.1
    ws.create_page("entity:old", "entity", "OLD", as_of="2026-04")
    ws.findings.append(_f("f1", "OLD", "gpuSpotPrice"))   # daily -> H_short
    ws.append_observation("entity:old", "f1", as_of="2026-04")
    ws.record_state("entity:old", as_of="2026-04", state="x", trajectory="y", salience=0.5)
    for cyc in ("2026-05", "2026-06", "2026-07", "2026-08"):
        ws.create_page(f"entity:c{cyc}", "entity", cyc, as_of=cyc)  # later cycles, OLD stays quiet
    # FRESH page created this cycle, salience 0 (un-enriched), quiet_age 0 -> NOT stale
    h = health_report(ws, as_of="2026-08", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    stale_ids = [s.pageId for s in h.stale]
    assert "entity:old" in stale_ids
    assert "entity:c2026-08" not in stale_ids   # fresh this cycle -> excluded


def test_health_contradiction_rollup(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06")
    h = health_report(ws, as_of="2026-06", contradictions={"entity:nvda": "guidance cut"},
                      horizons=_HZ, config=DEFAULT_LINT_CONFIG)
    assert [(c.pageId, c.note, c.asOf) for c in h.contradictions] == \
        [("entity:nvda", "guidance cut", "2026-06")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_health.py -q`
Expected: FAIL with `ImportError: cannot import name 'health_report'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/lint.py`, add at the end of the module:

```python
def health_report(store, *, as_of, contradictions, horizons, config=DEFAULT_LINT_CONFIG):
    """Structural health over ALL pages (entity AND theme): orphans, stale (decayed), cross-ref
    gaps (asymmetric + mention-without-link), and the contradiction roll-up. Read-only; mutates
    nothing."""
    idx = store.index()
    pages = {e.id: store.get_page(e.id) for e in idx}

    referenced = set()
    for p in pages.values():
        referenced.update(p.crossRefs)
    orphans = sorted(pid for pid in pages if pid not in referenced)

    stale = []
    for pid, p in pages.items():
        qa = quiet_age(store, pid, as_of)
        if qa <= 0:
            continue  # a fresh page is never "stale"
        hl, _ = half_life(_findings_for(store, pid, store.observations(pid)), horizons, config)
        eff = effective_salience(p.salience, qa, hl)
        if eff < config.stale_threshold:
            stale.append(StaleEntry(pageId=pid, effectiveSalience=eff))
    stale.sort(key=lambda s: s.pageId)

    gaps = []
    for pid, p in sorted(pages.items()):
        for ref in p.crossRefs:
            if ref in pages and pid not in pages[ref].crossRefs:
                gaps.append(CrossRefGap(source=pid, target=ref, reason="asymmetric"))
    for pid, p in sorted(pages.items()):
        body = store.window(pid, 0).body
        for other_id, other in sorted(pages.items()):
            if other_id == pid or not other.title:
                continue
            if other.title in body and other_id not in p.crossRefs:
                gaps.append(CrossRefGap(source=pid, target=other_id, reason="mention-without-link"))

    contras = [ContradictionEntry(pageId=pid, note=note, asOf=as_of)
               for pid, note in sorted(contradictions.items())]

    return HealthReport(orphans=orphans, stale=stale, crossRefGaps=gaps, contradictions=contras)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_health.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 328 passed, 3 skipped (323 + 5 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lint.py tests/test_wiki_lint_health.py && git commit -m "feat(4-4b): structural health — orphans, stale, cross-ref gaps, contradiction roll-up

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `lint()` assembly + `wiki-lint` CLI + frozen guard

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (add `lint()` + provenance + diff/contradiction wiring)
- Modify: `gpu_agent/cli.py` (add the `wiki-lint` subparser + `_wiki_lint` handler + dispatch)
- Test: `tests/test_wiki_lint_cli.py`

**Interfaces:**
- Consumes: `score_moves`/`health_report` (Tasks 4–5), `parse_contradiction_detail` (Task 1); `WikiStore.diff`/`log`; `IndicatorRegistry`/`IndicatorHorizons`.
- Produces:
  - `lint(store, *, as_of, prev_as_of=None, registry, horizons, config=DEFAULT_LINT_CONFIG) -> LintReport` (auto-derives `prev_as_of`; computes contradictions from `ingest` events; appends one idempotent `lint` event).
  - CLI: `wiki-lint --store <dir> --as-of <date> [--prev-as-of <date>] [--out <file>]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_lint_cli.py`:

```python
import json
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings, apply_enrichment, IngestResult, PageEnrichment
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import lint, DEFAULT_LINT_CONFIG
from gpu_agent.cli import main
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(root):
    return WikiStore(root / "wiki", FindingStore(root / "findings"))


def _reg_hz():
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def _f(fid, entity, indicatorId="rpoBacklog", magnitude=3):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=[Evidence(source="src", url="u", date="2026-06", excerpt="e", tier="primary")],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def _seed_with_contradiction(ws):
    route_findings(ws, [_f("f-nv", "NVDA")], as_of="2026-06")
    apply_enrichment(ws, IngestResult(pages=[PageEnrichment(
        pageId="entity:nvda", bodyMarkdown="## NVDA\nDC up [f-nv].\n", state="accelerating",
        trajectory="steady -> accelerating", salience=0.8, contradictsThesis=True,
        contradictionNote="guidance cut")]), as_of="2026-06")


def test_lint_end_to_end_reads_contradiction(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    _seed_with_contradiction(ws)
    report = lint(ws, as_of="2026-06", registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    nvda = [m for m in report.material if m.pageId == "entity:nvda"]
    assert nvda and nvda[0].factors.contradiction is True
    assert [c.pageId for c in report.health.contradictions] == ["entity:nvda"]


def test_lint_emits_one_idempotent_event(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    _seed_with_contradiction(ws)
    lint(ws, as_of="2026-06", registry=reg, horizons=hz)
    n = len([e for e in ws.log.read() if e.kind == "lint"])
    lint(ws, as_of="2026-06", registry=reg, horizons=hz)  # re-run
    assert n == 1
    assert len([e for e in ws.log.read() if e.kind == "lint"]) == 1


def test_lint_is_page_type_agnostic(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06")
    ws.findings.append(_f("f-t", "CoWoS", "leadTimes"))
    ws.append_observation("theme:cowos", "f-t", as_of="2026-06")
    report = lint(ws, as_of="2026-06", registry=reg, horizons=hz)
    assert any(m.pageId == "theme:cowos" and m.type == "theme"
               for m in report.material + report.dropped)


def test_wiki_lint_cli_prints_report(tmp_path, capsys):
    # seed a store via the wiki-ingest CLI, then lint it
    main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
          "--store", str(tmp_path), "--as-of", "2026-06"])
    capsys.readouterr()
    rc = main(["wiki-lint", "--store", str(tmp_path), "--as-of", "2026-06"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["asOf"] == "2026-06"
    assert "material" in report and "health" in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_cli.py -q`
Expected: FAIL with `ImportError: cannot import name 'lint'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/lint.py`, add the import at the top (after the existing ones):

```python
from gpu_agent.wiki.ingest import parse_contradiction_detail
```

Add at the end of the module:

```python
def _auto_prev(store, as_of):
    cycles = sorted({e.asOf for e in store.log.read() if e.asOf < as_of})
    return cycles[-1] if cycles else None


def _contradictions_for(store, as_of):
    out = {}
    for e in store.log.read():
        if e.kind == "ingest" and e.asOf == as_of:
            for c in parse_contradiction_detail(e.detail)["contradictions"]:
                out[c["pageId"]] = c["note"]
    return out


def lint(store, *, as_of, prev_as_of=None, registry, horizons, config=DEFAULT_LINT_CONFIG) -> LintReport:
    """The wiki lint / early-warning pass: rank the cycle's material moves, decay quiet threads,
    surface structural health. Pure, read-only except for one idempotent `lint` provenance event."""
    if prev_as_of is None:
        prev_as_of = _auto_prev(store, as_of)
    diff = store.diff(as_of, prev_as_of or "")
    contradictions = _contradictions_for(store, as_of)
    material, dropped = score_moves(store, diff, contradictions, as_of=as_of, prev_as_of=prev_as_of,
                                    registry=registry, horizons=horizons, config=config)
    health = health_report(store, as_of=as_of, contradictions=contradictions,
                            horizons=horizons, config=config)
    report = LintReport(asOf=as_of, prevAsOf=prev_as_of, material=material,
                        dropped=dropped, health=health)
    if not any(e.kind == "lint" and e.asOf == as_of for e in store.log.read()):
        detail = (f"material {len(material)}; dropped {len(dropped)}; stale {len(health.stale)}; "
                  f"orphans {len(health.orphans)}; contradictions {len(health.contradictions)}")
        store.log.append(asOf=as_of, kind="lint", detail=detail)
    return report
```

In `gpu_agent/cli.py`, add the import near the other wiki imports:

```python
from gpu_agent.wiki.lint import lint
```

Add the handler after `_wiki_ingest`:

```python
def _wiki_lint(args) -> int:
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load("registry/indicators.json")
    report = lint(store, as_of=args.as_of, prev_as_of=args.prev_as_of,
                  registry=registry, horizons=horizons)
    payload = report.model_dump_json(indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(payload, encoding="utf-8")
        print(f"wrote {args.out}  ({len(report.material)} material, {len(report.dropped)} dropped)")
    else:
        print(payload)
    return 0
```

Register the subparser inside `main()` after the `wiki-ingest` (`wi`) block:

```python
    wl = sub.add_parser("wiki-lint")
    wl.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wl.add_argument("--as-of", required=True)
    wl.add_argument("--prev-as-of", default=None,
                    help="prior cycle asOf for the diff window (default: auto-derive from the log)")
    wl.add_argument("--out", default=None, help="write the LintReport JSON here")
```

Add the dispatch next to the other `if args.cmd == ...` checks:

```python
    if args.cmd == "wiki-lint":
        return _wiki_lint(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_lint_cli.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite + frozen guards**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 332 passed, 3 skipped (328 + 4 new).

Run: `cd /c/Users/danie/random_for_fun && git diff --stat main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/pipeline.py gpu_agent/store.py gpu_agent/wiki/store.py gpu_agent/wiki/log.py gpu_agent/wiki/page.py`
Expected: **no output** (every frozen file byte-unchanged; the only `gpu_agent/` changes are the new `wiki/lint.py`, the additive `wiki/ingest.py` edits, and the additive `cli.py` edits).

Run: `cd /c/Users/danie/random_for_fun && git diff main -- fixtures/`
Expected: **no output** (no committed fixture changed).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lint.py gpu_agent/cli.py tests/test_wiki_lint_cli.py && git commit -m "feat(4-4b): lint() assembly + wiki-lint CLI + idempotent lint provenance event

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-06-30-wiki-lint-relevance-engine-design.md`):
- §1 lint pass + `wiki-lint` CLI (no brain seam; auto-`prev_as_of`) → Task 6. ✓
- §2 materiality (move-set = diff ∪ contradicted pages; the 4 additive factors; per-page tier/recency/horizon aggregation; salience_weight floor; threshold → material/dropped) → Task 4. ✓
- §3 decay (cycle-count quiet-age with material-vs-body-only; tag-derived half-life, cadence-driven + leading floor + longest-class-wins + untagged→med-logged; non-destructive `effective_salience`; stale threshold) → Task 3 (+ stale used in Task 5). ✓
- §4 structural health (orphans, stale, asymmetric + mention-without-link, contradiction roll-up) → Task 5. ✓
- §5 contradiction seam (shared `format`/`parse` in `ingest.py`; `apply_enrichment` refactor behavior-preserving) → Task 1; read in `lint()` → Task 6. ✓
- §6 provenance (one idempotent `lint` event per `asOf`) → Task 6. ✓
- §7 `LintConfig` defaults → Task 2. ✓
- §8 data model (incl. `CrossRefGap` as `source`/`target` — keyword-safe) → Task 2. ✓
- §9 frozen/additive boundary → Task 6 Step 5 guards. ✓
- §10 doctrine + folded `PageEnrichment.salience` bound → Task 1. ✓
- §11 design-for-4-4c constraints: page-type agnostic (Task 6 theme test), status carried (`MaterialMove.status`, Task 2/4), no lifecycle mutation (no `record_state`/promote anywhere), emit `lint` events (Task 6), stale signal (Task 5). ✓
- §12 test strategy → every task's tests. ✓
- §14 acceptance items 1–7 all map to the tasks above. ✓

**Placeholder scan:** none — every step has complete code/commands.

**Type consistency:** `LintConfig`/models (Task 2) are imported and used with matching field names by Tasks 3–6. `half_life(findings, horizons, config) -> (int, list)`, `quiet_age(store, page_id, as_of) -> int`, `decay`/`effective_salience` (Task 3) are called with these exact signatures by `_score_move` and `health_report` (Tasks 4–5). `_score_move(...)`/`score_moves(...)` (Task 4) are called by `lint()` (Task 6) with matching keywords. `health_report(store, *, as_of, contradictions, horizons, config)` (Task 5) is called so by `lint()` (Task 6). `format_contradiction_detail`/`parse_contradiction_detail` (Task 1) are used by `apply_enrichment` (Task 1) and `_contradictions_for` (Task 6). The CLI handler (Task 6) reuses `WikiStore`/`FindingStore`/`_load_registry`/`IndicatorHorizons` already imported in `cli.py` (4-4a) plus the new `lint` import. `store.diff(as_of, prev)`, `store.index()`, `store.window(pid,0).body`, `store.log.append(asOf=,kind="lint",detail=)`, `registry.resolve(id).scoring/.side`, `horizons.get(id)` all match the 4-1/4-2/4-4a APIs. ✓

**Test-count math:** baseline 300 → +5 (Task 1) → +3 (Task 2) → +9 (Task 3) → +6 (Task 4) → +5 (Task 5) → +4 (Task 6) = **332 passed, 3 skipped** at the end.
