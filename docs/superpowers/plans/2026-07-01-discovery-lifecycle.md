# Provisional lifecycle engine (sub-project 4-4c) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure-code provisional lifecycle engine — promotion (persist+corroborate), non-destructive pruning (of stale provisionals), and quarantine (a reusable filter + a report + an invariant guard) — wired into the CLI, all additive with the frozen contract byte-unchanged.

**Architecture:** A new pure module `gpu_agent/wiki/lifecycle.py` reads the `WikiStore` (`index`/`observations`/`findings.get`) and 4-4b's `stale` signal and returns a `LifecycleReport` (promotion + prune candidates + quarantine list). It mutates nothing unless the caller passes `--apply`, and then only via the existing `update_header(status="registered")` and `record_state` (salience floor). A new additive `wiki-lifecycle` CLI subcommand exposes propose (default) and `--apply`.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset on Windows — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`/`validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, the existing `JsonStore`/`FindingStore` (`gpu_agent/store.py`), **every member of** `gpu_agent/wiki/store.py`/`log.py`/`page.py`/`ingest.py`/`lint.py`, and `gpu_agent/gathering/ingest.py`/`dedup.py`. 4-4c only *reads from* or *calls* these; it never edits them. **No new `LogEvent.kind`** and **no new `status` value** (`status` stays `Literal["provisional","registered"]`).
- **Additive only** (Part 33): the new module `gpu_agent/wiki/lifecycle.py`; the `wiki-lifecycle` subparser/`_wiki_lifecycle` handler/dispatch in `cli.py`. Do NOT edit any committed fixture under `fixtures/`.
- **Doctrine:** nothing silent (every promotion candidate, prune candidate, quarantined page counted + listed; `provisionalConsidered` accounts for every provisional page — Part 29); propose-don't-auto-promote (status flips only behind `--apply` — Part 18/16); provisional never drives canonical (the quarantine filter + the guard); replayable (the `LifecycleReport` + page `status`/`lastUpdatedAsOf`; no wall-clock; `as_of` injected — Part 20); numbers only from gated findings (the engine writes no number to any scorecard/index — Part 17); pruning is non-destructive (no delete, no data loss).
- **Determinism:** no wall-clock; `as_of` is always passed in; candidate lists are ordered by `pageId`; re-running propose on an unchanged store is a no-op; a second `--apply` promotes/prunes nothing new.
- **The full suite stays green after every task.** Baseline: **357 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file guard** (Task 5 Step 6): the only `gpu_agent/` changes are the new `wiki/lifecycle.py` and the additive `cli.py` edits — every frozen file above stays byte-unchanged and no `fixtures/` file changes.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gpu_agent/wiki/lifecycle.py` | the lifecycle engine: models, `LifecycleConfig`, `persistence`/`corroboration`, `promotion_candidates`, `prune_candidates`, `partition_canonical`, `lifecycle`, `apply_lifecycle` | Create |
| `gpu_agent/cli.py` | CLI entry points | Modify: add a `wiki-lifecycle` subparser/`_wiki_lifecycle` handler/dispatch |
| `tests/test_lifecycle_models.py` | data models + `LifecycleConfig` defaults | Create |
| `tests/test_lifecycle_promotion.py` | `persistence`/`corroboration`/`promotion_candidates` | Create |
| `tests/test_lifecycle_prune_quarantine.py` | `prune_candidates` + `partition_canonical` + the scorecard-invariant guard | Create |
| `tests/test_lifecycle_assembly.py` | `lifecycle` assembly + `apply_lifecycle` | Create |
| `tests/test_lifecycle_cli.py` | `wiki-lifecycle` propose + `--apply` end-to-end + frozen guard | Create |

**Note on the module path:** the engine lives in the *existing* `gpu_agent/wiki/` package (sibling to `lint.py`), since it operates on wiki pages — no new package is introduced. It reads 4-4b's `stale` signal via `lint(...).health.stale`; the CLI computes that (like `wiki-lint` does) and passes it in, so `lifecycle()`'s dependencies stay explicit and testable.

---

### Task 1: `lifecycle.py` — data models + `LifecycleConfig`

**Files:**
- Create: `gpu_agent/wiki/lifecycle.py`
- Test: `tests/test_lifecycle_models.py`

**Interfaces:**
- Produces (consumed by all later tasks): `PromotionCandidate`, `PruneCandidate`, `QuarantineEntry`, `LifecycleReport`, `AppliedSummary`, `LifecycleConfig`, `DEFAULT_LIFECYCLE_CONFIG`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_lifecycle_models.py`:

```python
import json
from gpu_agent.wiki.lifecycle import (
    PromotionCandidate, PruneCandidate, QuarantineEntry, LifecycleReport,
    AppliedSummary, LifecycleConfig, DEFAULT_LIFECYCLE_CONFIG)


def test_lifecycle_config_defaults():
    c = DEFAULT_LIFECYCLE_CONFIG
    assert c.min_persist_cycles == 2
    assert c.min_sources == 2
    assert c.stale_threshold == 0.1
    assert c.prune_salience_floor == 0.0


def test_models_construct():
    pc = PromotionCandidate(pageId="entity:nvda", type="entity", title="NVIDIA",
                            persistCycles=3, distinctSources=2,
                            verdict="persisted 3 cycles, 2 sources -> promote")
    pr = PruneCandidate(pageId="theme:cowos", type="theme", reason="stale: eff_salience 0.04")
    q = QuarantineEntry(pageId="entity:amd", status="provisional")
    a = AppliedSummary(promoted=1, pruned=1)
    assert pc.persistCycles == 3 and pc.distinctSources == 2
    assert pr.type == "theme"
    assert q.confidenceCapped is True and q.note == "not yet in coverage"
    assert a.promoted == 1 and a.pruned == 1


def test_lifecycle_report_roundtrip():
    report = LifecycleReport(
        asOf="2026-07",
        promotions=[PromotionCandidate(pageId="entity:nvda", type="entity", title="NVIDIA",
                                       persistCycles=2, distinctSources=2, verdict="promote")],
        prunes=[PruneCandidate(pageId="entity:x", type="entity", reason="stale")],
        quarantined=[QuarantineEntry(pageId="entity:nvda", status="provisional")],
        provisionalConsidered=1)
    blob = json.loads(report.model_dump_json())
    assert blob["asOf"] == "2026-07"
    assert blob["promotions"][0]["pageId"] == "entity:nvda"
    assert blob["quarantined"][0]["confidenceCapped"] is True
    assert blob["provisionalConsidered"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.wiki.lifecycle'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/wiki/lifecycle.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_models.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 360 passed, 3 skipped (357 baseline + 3 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lifecycle.py tests/test_lifecycle_models.py && git commit -m "feat(4-4c): lifecycle data models + LifecycleConfig

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `lifecycle.py` — `persistence` + `corroboration` + `promotion_candidates`

**Files:**
- Modify: `gpu_agent/wiki/lifecycle.py` (add the promotion helpers)
- Test: `tests/test_lifecycle_promotion.py`

**Interfaces:**
- Consumes: `LifecycleConfig`/`PromotionCandidate` (Task 1); `WikiStore` (`index`, `observations`, `findings`), `PageNotFound` (`gpu_agent.wiki.store`); `FindingStore` (`exists`, `get`); `Finding`/`Evidence` (`gpu_agent.schema.finding`).
- Produces:
  - `persistence(store, page_id) -> int` (distinct `asOf` among the page's observations).
  - `corroboration(store, page_id) -> int` (distinct `evidence.source` across the page's observed findings).
  - `promotion_candidates(store, config=DEFAULT_LIFECYCLE_CONFIG) -> list[PromotionCandidate]` (provisional pages meeting both bars, ordered by `pageId`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_lifecycle_promotion.py`:

```python
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.lifecycle import (persistence, corroboration, promotion_candidates,
                                       DEFAULT_LIFECYCLE_CONFIG)
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId, *, sources, asOf, capturedAt):
    ev = [Evidence(source=s, url=f"http://{s}/x", date=asOf, excerpt="e", tier="secondary")
          for s in sources]
    return Finding(id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
                   impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                   value=None, confidence=Confidence(level="medium", basis="b"), asOf=asOf,
                   indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
                   magnitude=2, entity=entity, observedAt=asOf, capturedAt=capturedAt, evidence=ev)


def _seed(store, f, as_of):
    pid = f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_persistence_counts_distinct_cycles(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    assert persistence(store, "entity:nvda") == 2


def test_corroboration_counts_distinct_sources(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec", "reuters"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    assert corroboration(store, "entity:nvda") == 2  # {sec, reuters}


def test_promote_when_persist_and_corroborate_met(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["reuters"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    cands = promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG)
    assert [c.pageId for c in cands] == ["entity:nvda"]
    assert cands[0].persistCycles == 2 and cands[0].distinctSources == 2


def test_no_promote_when_one_cycle(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec", "reuters"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    assert promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG) == []  # persistence 1 < 2


def test_no_promote_when_one_source(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "AMD", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "AMD", "rpoBacklog", sources=["sec"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    assert promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG) == []  # corroboration 1 < 2


def test_registered_page_skipped(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["reuters"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    store.update_header("entity:nvda", as_of="2026-07", status="registered")
    assert promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG) == []  # already registered
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_promotion.py -q`
Expected: FAIL with `ImportError: cannot import name 'persistence'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/lifecycle.py`, add at the end of the module:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_promotion.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 366 passed, 3 skipped (360 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lifecycle.py tests/test_lifecycle_promotion.py && git commit -m "feat(4-4c): persistence + corroboration + promotion_candidates (persist+corroborate)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `lifecycle.py` — `prune_candidates` + `partition_canonical` + the quarantine guard

**Files:**
- Modify: `gpu_agent/wiki/lifecycle.py` (add pruning + the canonical filter)
- Test: `tests/test_lifecycle_prune_quarantine.py`

**Interfaces:**
- Consumes: `PruneCandidate` (Task 1); `StaleEntry` (`gpu_agent.wiki.lint` — fields `pageId`/`effectiveSalience`); `IndexEntry` (`gpu_agent.wiki.store` — fields incl. `id`/`type`/`status`); `build_scorecard` (`gpu_agent.pipeline`) — read only, for the invariant guard test.
- Produces:
  - `prune_candidates(store, stale) -> list[PruneCandidate]` (pages that are BOTH provisional AND in the `stale` list; ordered by `pageId`).
  - `partition_canonical(index) -> tuple[list[IndexEntry], list[IndexEntry]]` (`(registered, provisional)`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_lifecycle_prune_quarantine.py`:

```python
import inspect
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.lint import StaleEntry
from gpu_agent.wiki.lifecycle import prune_candidates, partition_canonical
from gpu_agent.pipeline import build_scorecard


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _page(store, pid, title, *, as_of, status="provisional"):
    store.create_page(pid, pid.split(":")[0], title, as_of=as_of)
    if status == "registered":
        store.update_header(pid, as_of=as_of, status="registered")


def test_prune_provisional_stale(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:x", "X", as_of="2026-07")
    prunes = prune_candidates(store, [StaleEntry(pageId="entity:x", effectiveSalience=0.04)])
    assert [p.pageId for p in prunes] == ["entity:x"]
    assert "stale" in prunes[0].reason


def test_no_prune_registered_stale(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:x", "X", as_of="2026-07", status="registered")
    prunes = prune_candidates(store, [StaleEntry(pageId="entity:x", effectiveSalience=0.04)])
    assert prunes == []  # registered pages are established coverage, never pruned


def test_no_prune_provisional_not_stale(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:x", "X", as_of="2026-07")
    assert prune_candidates(store, []) == []  # not in the stale list


def test_partition_canonical_splits(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:reg", "Reg", as_of="2026-07", status="registered")
    _page(store, "entity:prov", "Prov", as_of="2026-07")
    registered, provisional = partition_canonical(store.index())
    assert [e.id for e in registered] == ["entity:reg"]
    assert [e.id for e in provisional] == ["entity:prov"]


def test_partition_canonical_all_provisional(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:a", "A", as_of="2026-07")
    _page(store, "entity:b", "B", as_of="2026-07")
    registered, provisional = partition_canonical(store.index())
    assert registered == []
    assert {e.id for e in provisional} == {"entity:a", "entity:b"}


def test_build_scorecard_takes_no_wiki_input():
    # Quarantine invariant: the canonical scorecard is finding-driven — it takes NO wiki/page/store
    # input, so no page (provisional or registered) can move DMI/SMI. Lock it so a future change
    # cannot silently route page state into scoring.
    params = set(inspect.signature(build_scorecard).parameters)
    assert not (params & {"store", "wiki", "wiki_store", "pages", "page", "provisional", "status"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_prune_quarantine.py -q`
Expected: FAIL with `ImportError: cannot import name 'prune_candidates'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/lifecycle.py`, add at the end of the module:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_prune_quarantine.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 372 passed, 3 skipped (366 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lifecycle.py tests/test_lifecycle_prune_quarantine.py && git commit -m "feat(4-4c): prune_candidates (provisional+stale) + partition_canonical filter + quarantine guard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `lifecycle.py` — `lifecycle` assembly + `apply_lifecycle`

**Files:**
- Modify: `gpu_agent/wiki/lifecycle.py` (add the assembler + the apply path)
- Test: `tests/test_lifecycle_assembly.py`

**Interfaces:**
- Consumes: Task 1 models, Task 2 (`promotion_candidates`), Task 3 (`prune_candidates`, `partition_canonical`); `WikiStore` (`index`, `get_page`, `update_header`, `record_state`).
- Produces:
  - `lifecycle(store, *, as_of, stale, config=DEFAULT_LIFECYCLE_CONFIG) -> LifecycleReport` (propose; read-only; `provisionalConsidered == len(quarantined)`).
  - `apply_lifecycle(store, report, *, as_of, config=DEFAULT_LIFECYCLE_CONFIG) -> AppliedSummary` (promote via `update_header(status="registered")`; prune via `record_state` salience floor; idempotent).

- [ ] **Step 1: Write the failing test**

Create `tests/test_lifecycle_assembly.py`:

```python
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.lint import StaleEntry
from gpu_agent.wiki.lifecycle import lifecycle, apply_lifecycle, DEFAULT_LIFECYCLE_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, *, sources, asOf, capturedAt):
    ev = [Evidence(source=s, url=f"http://{s}/x", date=asOf, excerpt="e", tier="secondary") for s in sources]
    return Finding(id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
                   impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                   value=None, confidence=Confidence(level="medium", basis="b"), asOf=asOf,
                   indicatorId="rpoBacklog", side="demand", polarityDemand=1, polaritySupply=0,
                   magnitude=2, entity=entity, observedAt=asOf, capturedAt=capturedAt, evidence=ev)


def _seed(store, f, as_of):
    pid = f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def _promotable(store):
    # NVDA: 2 cycles, 2 sources -> promotable
    _seed(store, _f("f1", "NVDA", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", sources=["reuters"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")


def test_lifecycle_assembles_report(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")  # stale provisional
    store.record_state("entity:amd", as_of="2026-07", state="slipping", trajectory="flat", salience=0.5)
    report = lifecycle(store, as_of="2026-07",
                       stale=[StaleEntry(pageId="entity:amd", effectiveSalience=0.04)],
                       config=DEFAULT_LIFECYCLE_CONFIG)
    assert [c.pageId for c in report.promotions] == ["entity:nvda"]
    assert [c.pageId for c in report.prunes] == ["entity:amd"]
    assert {q.pageId for q in report.quarantined} == {"entity:nvda", "entity:amd"}


def test_lifecycle_provisional_considered_counts_all(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")
    report = lifecycle(store, as_of="2026-07", stale=[])
    assert report.provisionalConsidered == 2  # every provisional page examined == len(quarantined)
    assert report.provisionalConsidered == len(report.quarantined)


def test_apply_promotes_and_prunes(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")
    store.record_state("entity:amd", as_of="2026-07", state="slipping", trajectory="flat", salience=0.5)
    report = lifecycle(store, as_of="2026-07",
                       stale=[StaleEntry(pageId="entity:amd", effectiveSalience=0.04)])
    summary = apply_lifecycle(store, report, as_of="2026-08")
    assert summary.promoted == 1 and summary.pruned == 1
    assert store.get_page("entity:nvda").status == "registered"
    assert store.get_page("entity:amd").salience == 0.0  # floored, non-destructive
    assert store.get_page("entity:amd").state == "slipping"  # state preserved


def test_apply_idempotent(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")
    store.record_state("entity:amd", as_of="2026-07", state="slipping", trajectory="flat", salience=0.5)
    report = lifecycle(store, as_of="2026-07",
                       stale=[StaleEntry(pageId="entity:amd", effectiveSalience=0.04)])
    apply_lifecycle(store, report, as_of="2026-08")
    again = apply_lifecycle(store, report, as_of="2026-09")
    assert again.promoted == 0 and again.pruned == 0  # already registered / already floored


def test_propose_is_read_only(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    lifecycle(store, as_of="2026-07", stale=[])  # propose only
    assert store.get_page("entity:nvda").status == "provisional"  # NOT mutated
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_assembly.py -q`
Expected: FAIL with `ImportError: cannot import name 'lifecycle'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/lifecycle.py`, add at the end of the module:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_assembly.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 377 passed, 3 skipped (372 + 5 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/lifecycle.py tests/test_lifecycle_assembly.py && git commit -m "feat(4-4c): lifecycle() assembly + apply_lifecycle (propose-then-apply, idempotent)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: CLI wiring — `wiki-lifecycle` (propose + `--apply`) + frozen guard

**Files:**
- Modify: `gpu_agent/cli.py` (add the `wiki-lifecycle` subparser + `_wiki_lifecycle` handler + dispatch)
- Test: `tests/test_lifecycle_cli.py`

**Interfaces:**
- Consumes: `lifecycle`/`apply_lifecycle` (Task 4); the existing `lint` (`gpu_agent.wiki.lint`), `_load_registry`, `IndicatorHorizons`, `WikiStore`, `FindingStore` in `cli.py`.
- Produces: `wiki-lifecycle --store DIR --as-of D [--apply] [--report R]` — computes `stale` via `lint`, runs `lifecycle`; propose prints the `LifecycleReport` JSON; `--apply` promotes/prunes and prints the applied summary.

- [ ] **Step 1: Write the failing test**

Create `tests/test_lifecycle_cli.py`:

```python
import json
from gpu_agent.cli import main
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _seed_promotable(root):
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    def f(fid, sources, asOf, capturedAt):
        ev = [Evidence(source=s, url=f"http://{s}/x", date=asOf, excerpt="e", tier="secondary") for s in sources]
        return Finding(id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
                       impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                       value=None, confidence=Confidence(level="medium", basis="b"), asOf=asOf,
                       indicatorId="rpoBacklog", side="demand", polarityDemand=1, polaritySupply=0,
                       magnitude=2, entity="NVDA", observedAt=asOf, capturedAt=capturedAt, evidence=ev)
    store.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06")
    for fid, srcs, asof, cap in [("f1", ["sec"], "2026-06", "2026-06-01"),
                                 ("f2", ["reuters"], "2026-07", "2026-07-01")]:
        store.findings.append(f(fid, srcs, asof, cap))
        store.append_observation("entity:nvda", fid, as_of=asof)
    return store


def test_wiki_lifecycle_propose_prints_report(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_promotable(root)
    rc = main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert [c["pageId"] for c in report["promotions"]] == ["entity:nvda"]
    # propose did NOT mutate
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    assert store.get_page("entity:nvda").status == "provisional"


def test_wiki_lifecycle_apply_promotes(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_promotable(root)
    rc = main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07", "--apply"])
    assert rc == 0
    assert "promoted 1" in capsys.readouterr().out
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    assert store.get_page("entity:nvda").status == "registered"


def test_wiki_lifecycle_apply_idempotent(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_promotable(root)
    main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07", "--apply"])
    capsys.readouterr()
    main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-08", "--apply"])
    assert "promoted 0" in capsys.readouterr().out  # already registered


def test_wiki_lifecycle_writes_report_file(tmp_path):
    root = tmp_path / "store"
    _seed_promotable(root)
    out = tmp_path / "lifecycle.json"
    rc = main(["wiki-lifecycle", "--store", str(root), "--as-of", "2026-07", "--report", str(out)])
    assert rc == 0
    report = json.loads(out.read_text("utf-8"))
    assert report["provisionalConsidered"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_cli.py -q`
Expected: FAIL (`error: argument cmd: invalid choice: 'wiki-lifecycle'`).

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/cli.py`, add the import near the other wiki imports (below `from gpu_agent.wiki.lint import lint`):

```python
from gpu_agent.wiki.lifecycle import lifecycle, apply_lifecycle
```

Add the `_wiki_lifecycle` handler after `_wiki_lint`:

```python
def _wiki_lifecycle(args) -> int:
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load("registry/indicators.json")
    lint_report = lint(store, as_of=args.as_of, registry=registry, horizons=horizons)
    report = lifecycle(store, as_of=args.as_of, stale=lint_report.health.stale)
    payload = report.model_dump_json(indent=2)
    if args.report:
        pathlib.Path(args.report).write_text(payload, encoding="utf-8")
    if args.apply:
        summary = apply_lifecycle(store, report, as_of=args.as_of)
        print(f"applied: promoted {summary.promoted}, pruned {summary.pruned} -> {args.store}")
    else:
        print(payload)
    return 0
```

Register the subparser inside `main()` after the `wiki-lint` (`wl`) block:

```python
    wlc = sub.add_parser("wiki-lifecycle")
    wlc.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wlc.add_argument("--as-of", required=True)
    wlc.add_argument("--apply", action="store_true",
                     help="apply the proposed promotions/prunes (else propose-only)")
    wlc.add_argument("--report", default=None, help="write the LifecycleReport JSON here")
```

Add the dispatch next to the other `if args.cmd == ...` checks:

```python
    if args.cmd == "wiki-lifecycle":
        return _wiki_lifecycle(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_lifecycle_cli.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 381 passed, 3 skipped (377 + 4 new).

- [ ] **Step 6: Run the frozen guards**

Run: `cd /c/Users/danie/random_for_fun && git diff --stat main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/pipeline.py gpu_agent/store.py gpu_agent/wiki/store.py gpu_agent/wiki/log.py gpu_agent/wiki/page.py gpu_agent/wiki/ingest.py gpu_agent/wiki/lint.py gpu_agent/gathering/ingest.py gpu_agent/gathering/dedup.py`
Expected: **no output** (every frozen file byte-unchanged; the only `gpu_agent/` changes are the new `wiki/lifecycle.py` and the additive `cli.py` edits).

Run: `cd /c/Users/danie/random_for_fun && git diff main -- fixtures/`
Expected: **no output** (no committed fixture changed).

- [ ] **Step 7: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/cli.py tests/test_lifecycle_cli.py && git commit -m "feat(4-4c): CLI wiring — wiki-lifecycle subcommand (propose + --apply)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-07-01-discovery-lifecycle-design.md`):
- §0 scope = pure-code lifecycle engine only (promotion + pruning + quarantine); discovery half deferred → the whole plan is the lifecycle engine; no brain seam. ✓
- §1 the module + read-only propose / write-only-via-existing-methods apply → Tasks 2–4 (reads) + Task 4 `apply_lifecycle` (calls `update_header`/`record_state` only). ✓
- §2 promotion (persist ≥N distinct asOf + corroborate ≥N distinct sources; propose; `--apply` flips status; registered skipped) → Tasks 2, 4, 5. ✓
- §3 pruning (provisional∩stale; non-destructive salience floor; registered never pruned; no delete/new status) → Tasks 3, 4. ✓
- §4 quarantine (`partition_canonical` filter + report section + the scorecard-invariant guard) → Tasks 3 (filter + guard), 4 (quarantine list). ✓
- §5 the `LifecycleReport` + models + `LifecycleConfig` + `provisionalConsidered == len(quarantined)` → Tasks 1, 4. ✓
- §6 CLI `wiki-lifecycle` (propose default; `--apply`; `--report`) → Task 5. ✓
- §7 frozen/additive boundary (incl. no new `status`/`LogEvent.kind`) → Task 5 Step 6 guards (adds `gathering/dedup.py` to the frozen list). ✓
- §8 doctrine (nothing silent; propose-don't-auto-promote; provisional never drives canonical; replayable; non-destructive) → Tasks 2/3/4/5. ✓
- §10 test strategy → every task's tests. ✓
- §12 acceptance items 1–6 all map to tasks above. ✓

**Placeholder scan:** none — every code step has complete code; every test step has complete assertions.

**Type consistency:** `LifecycleConfig`/models (Task 1) are imported with matching field names by Tasks 2–5. `persistence`/`corroboration`/`promotion_candidates` (Task 2) are called by `lifecycle` (Task 4) with the exact signatures. `prune_candidates(store, stale)` + `partition_canonical(index)` (Task 3) are called by `lifecycle` (Task 4). `lifecycle(store, *, as_of, stale, config)` + `apply_lifecycle(store, report, *, as_of, config)` (Task 4) are called by `_wiki_lifecycle` (Task 5). `StaleEntry(pageId, effectiveSalience)` reuses the frozen `wiki/lint.py`; `IndexEntry`/`observations`/`update_header`/`record_state`/`get_page`/`index` reuse the frozen `WikiStore`; `build_scorecard` (guard) reuses the frozen `pipeline.py`. ✓

**Controller-confirmed (against live code at plan time):** `WikiPage.status` is `Literal["provisional","registered"]` default `"provisional"`; `_ALLOWED_HEADER_FIELDS` includes `"status"` so `update_header(pid, as_of=…, status="registered")` is valid; `record_state(pid, *, as_of, state, trajectory, salience, finding_id=None)` exists (the prune floor); `IndexEntry` carries `id`/`type`/`title`/`status`/`state`/`trajectory`/`salience`; `lint(store, *, as_of, prev_as_of=None, registry, horizons, config=…)` returns `LintReport.health.stale: list[StaleEntry]`; `StaleEntry` = `pageId`/`effectiveSalience`; `_wiki_lint` shows the `_load_registry()` + `IndicatorHorizons.load("registry/indicators.json")` pattern the CLI reuses; `build_scorecard`'s parameters are `findings/ratings/anchors/assignment/narrative/confidence/registry/category_status/horizons` (no wiki/page/store input — the guard asserts this).

**Test-count math:** baseline 357 → +3 (T1) → +6 (T2) → +6 (T3) → +5 (T4) → +4 (T5) = **381 passed, 3 skipped** at the end.
