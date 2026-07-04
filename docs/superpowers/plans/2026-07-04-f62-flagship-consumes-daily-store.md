# F62 — Flagship Consumes the Daily Store: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The standard/monthly flagship cycle judges from the accumulated daily-store findings (windowed, gated, deduped) merged with its own fresh gather, instead of re-deriving everything from ≤20 fresh docs.

**Architecture:** One new deterministic read-only module (`gpu_agent/corpus.py`) enumerates windowed store findings via wiki-page observations and merges them with fresh findings using the existing L2 classifier; a new `corpus` CLI command and additive `pipeline` flags expose it; the two emitted brain-prompt row formats gain an `observed=<date>` vintage tag (eval-gated: one run-eval + rebaseline); the run-cycle skill wires a coverage-driven top-up gather and symmetric write-back into the standard path. Zero frozen-core edits.

**Tech Stack:** Python 3 + pydantic v2, pytest, argparse CLI (`gpu_agent.cli`), existing `WikiStore`/`FindingStore`/`classify_findings` seams.

**Spec:** `docs/superpowers/specs/2026-07-04-f62-flagship-consumes-daily-store-design.md` — read it before starting any task. Under the standing SPEC-WINS rule, if this plan and the spec conflict, the spec governs.

## Global Constraints

- **Frozen contract v1.2 — zero edits to:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/schema/*`, `gpu_agent/judgment/briefing.py`, `gpu_agent/judgment/judge.py` aggregation, `gpu_agent/pipeline.py`, `JsonStore` (in `gpu_agent/store.py`). All F62 code is additive: new `gpu_agent/corpus.py`, `cli.py` grammar, an additive kwarg in `gpu_agent/judgment/prompt.py`, the thesis row helper in `gpu_agent/thesis.py`, `gpu_agent/evals/emit.py` mirroring, skill prose, tests.
- **Byte-identical defaults:** every existing command/function without the new flags/kwargs must produce byte-identical output (test-pinned).
- **F6 eval gate:** Task 7 changes emitted brain prompts → `tests/test_evals_baseline_pin.py` goes RED and stays red until Task 9 (run-eval + `gpu-agent eval rebaseline`). NEVER hand-edit `fixtures/evals/baseline.json` or any recorded brain answer. From Task 7 until Task 9, run the suite with `--deselect tests/test_evals_baseline_pin.py` and say so in the task report; everything else stays green.
- **Doctrine:** code computes + gates + stores; every cap/skip/drop logged (stderr line + report field — nothing silent); fail loud on canonical-store corruption.
- **Environment:** run from the worktree root (`.worktrees/f62-flagship-store`); Python is `/c/Users/danie/random_for_fun/.venv/Scripts/python` (shared root venv imports the worktree's code when pytest runs from the worktree root). Windows: use bash for `>` redirects; no double quotes inside `git commit -m` under PowerShell (use bash heredocs).
- **Commits:** end every commit message with `Co-Authored-By:` naming the ACTUAL model doing the work.
- Suite baseline at branch start: 923 passed / 3 skipped.

---

### Task 1: corpus.py — labels, window rule, report models

**Files:**
- Create: `gpu_agent/corpus.py`
- Test: `tests/test_corpus_window.py`

**Interfaces:**
- Produces: `WINDOW_DAYS_DEFAULT = 45`; `class CorpusError(ValueError)`; `period_end(label: str) -> datetime.date`; `in_window(label: str, as_of: str, window_days: int) -> bool`; pydantic models `CoverageEntry`, `SkippedPage`, `CorpusReport`, `CorpusResult` (fields below — later tasks rely on the exact names).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_corpus_window.py
import datetime

import pytest

from gpu_agent.corpus import (
    WINDOW_DAYS_DEFAULT, CorpusError, CorpusReport, CorpusResult, period_end, in_window,
)


def test_window_default_is_45():
    assert WINDOW_DAYS_DEFAULT == 45


def test_period_end_day_grain_is_itself():
    assert period_end("2026-07-03") == datetime.date(2026, 7, 3)


def test_period_end_month_grain_is_last_calendar_day():
    assert period_end("2026-07") == datetime.date(2026, 7, 31)
    assert period_end("2026-02") == datetime.date(2026, 2, 28)   # non-leap
    assert period_end("2028-02") == datetime.date(2028, 2, 29)   # leap


@pytest.mark.parametrize("bad", ["2026", "2026-13", "2026-00-01", "2026/07/03", "", "2026-07-32"])
def test_period_end_rejects_bad_labels(bad):
    with pytest.raises(CorpusError):
        period_end(bad)


def test_in_window_upper_bound_inclusive_lower_exclusive():
    # run asOf 2026-07 -> end 2026-07-31, start = end - 45d = 2026-06-16 (exclusive)
    assert in_window("2026-07-31", "2026-07", 45) is True     # == end
    assert in_window("2026-06-17", "2026-07", 45) is True     # start + 1
    assert in_window("2026-06-16", "2026-07", 45) is False    # == start (exclusive)
    assert in_window("2026-08-01", "2026-07", 45) is False    # future label excluded


def test_in_window_daily_finding_inside_flagship_month():
    # a July daily belongs to the July flagship's window by design (spec: window rule)
    assert in_window("2026-07-02", "2026-07", 45) is True


def test_in_window_month_grain_finding_uses_its_period_end():
    # June monthly findings (period end 2026-06-30) are in the July flagship's 45d window
    assert in_window("2026-06", "2026-07", 45) is True
    # but not in-window once the gap exceeds the window
    assert in_window("2026-04", "2026-07", 45) is False


def test_report_model_shape():
    r = CorpusReport(asOf="2026-07", category="chips.merchant-gpu", windowDays=45,
                     windowStart="2026-06-16", windowEnd="2026-07-31")
    assert r.storeIncluded == [] and r.outOfWindow == 0 and r.skippedPages == []
    assert r.freshNew == [] and r.freshUpdate == [] and r.freshDuplicate == []
    assert r.idOverlaps == [] and r.coverage == [] and r.notCovered == []
    res = CorpusResult(report=r)
    assert res.merged == [] and res.dedupedFresh == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_window.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.corpus'`

- [ ] **Step 3: Write the implementation**

```python
# gpu_agent/corpus.py
"""gpu_agent/corpus.py — the flagship input corpus (F62).

Read-only consumer of existing stores: the wiki (page index + observations) as the
category-scoped index over the canonical FindingStore, and the L2 dedup classifier
for fresh-vs-store classification. Assembles the windowed accumulated store findings
plus this cycle's fresh gated findings into ONE merged corpus for the judge/thesis
brains and the scorecard, and reports coverage so the gather can run as a top-up.

This module never writes anything: no store mutation, no file writes, no clock
reads. Same inputs -> byte-identical CorpusResult, always. Window membership is
label-based (asOf period ends), never wall-clock, so replays/backtests are
deterministic and a past cycle never sees a future label.
"""
from __future__ import annotations
import calendar
import datetime
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from gpu_agent.gathering.dedup import DEFAULT_DEDUP_CONFIG, FindingClass, classify_findings
from gpu_agent.schema.finding import Finding
from gpu_agent.store import FindingNotFound, FindingStore
from gpu_agent.wiki.store import WikiStore

WINDOW_DAYS_DEFAULT = 45

_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class CorpusError(ValueError):
    """Raised on invalid labels or canonical-store integrity violations (fail loud)."""


def period_end(label: str) -> datetime.date:
    """A label's period end: a day-grain label is its own day; a month-grain label is
    that month's last calendar day. Any other shape fails loud (F56-adjacent defense)."""
    try:
        if _DAY_RE.match(label):
            return datetime.date.fromisoformat(label)
        if _MONTH_RE.match(label):
            y, m = int(label[:4]), int(label[5:7])
            return datetime.date(y, m, calendar.monthrange(y, m)[1])
    except ValueError as e:
        raise CorpusError(f"invalid asOf label: {label!r} ({e})") from e
    raise CorpusError(f"invalid asOf label: {label!r} (want YYYY-MM or YYYY-MM-DD)")


def in_window(label: str, as_of: str, window_days: int) -> bool:
    """Spec window rule: period_end(as_of) - window_days < period_end(label) <= period_end(as_of)."""
    end = period_end(as_of)
    start = end - datetime.timedelta(days=window_days)
    return start < period_end(label) <= end


class CoverageEntry(BaseModel):
    entity: str
    indicatorId: str
    count: int
    latestAsOf: str
    latestObservedAt: str


class SkippedPage(BaseModel):
    id: str
    category: Optional[str] = None


class CorpusReport(BaseModel):
    asOf: str
    category: str
    windowDays: int
    windowStart: str   # ISO day, exclusive lower bound
    windowEnd: str     # ISO day, inclusive upper bound
    storeIncluded: list[str] = Field(default_factory=list)      # finding ids, sorted with merged order
    outOfWindow: int = 0
    skippedPages: list[SkippedPage] = Field(default_factory=list)
    freshNew: list[FindingClass] = Field(default_factory=list)
    freshUpdate: list[FindingClass] = Field(default_factory=list)
    freshDuplicate: list[FindingClass] = Field(default_factory=list)
    idOverlaps: list[str] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    notCovered: list[str] = Field(default_factory=list)


class CorpusResult(BaseModel):
    merged: list[Finding] = Field(default_factory=list)
    dedupedFresh: list[Finding] = Field(default_factory=list)   # the write-back stream
    report: CorpusReport
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_window.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/corpus.py tests/test_corpus_window.py
git commit -m "$(cat <<'EOF'
feat(corpus): F62 window rule + report models

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: corpus.py — enumerate_store (category-scoped, fail-loud)

**Files:**
- Modify: `gpu_agent/corpus.py` (append)
- Test: `tests/test_corpus_enumerate.py`

**Interfaces:**
- Consumes: Task 1's `in_window`, `CorpusError`, `SkippedPage`; `WikiStore.index() -> list[IndexEntry]` (`.id`, `.category`); `WikiStore.observations(page_id) -> list[Observation]` (`.findingId`); `FindingStore.get(id) -> Finding` (raises `FindingNotFound`/`ValueError`).
- Produces: `enumerate_store(store_root, category: str, as_of: str, window_days: int) -> tuple[list[Finding], int, list[SkippedPage]]` — (in-window findings sorted by `(asOf, id)`, out-of-window count, skipped pages).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_corpus_enumerate.py
import pytest

from gpu_agent.corpus import CorpusError, enumerate_store
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

# NOTE: this repo's test convention is LOCAL factories per file (no cross-test imports,
# tests/ is not a package). The _store/_f/_seed block below is repeated verbatim in the
# other F62 test files.


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_missing_wiki_dir_is_honest_empty(tmp_path):
    findings, out, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert findings == [] and out == 0 and skipped == []


def test_in_window_findings_returned_sorted(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("b-2", as_of="2026-07-03"), "2026-07-03")
    _seed(store, _f("a-1", as_of="2026-07-02"), "2026-07-02")
    findings, out, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [f.id for f in findings] == ["a-1", "b-2"]   # sorted by (asOf, id)
    assert out == 0 and skipped == []


def test_out_of_window_counted_not_listed(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("old-1", as_of="2026-04-01"), "2026-04-01")
    _seed(store, _f("new-1", as_of="2026-07-02"), "2026-07-02")
    findings, out, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [f.id for f in findings] == ["new-1"]
    assert out == 1


def test_wrong_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("mine-1"), "2026-07-02", category="chips.merchant-gpu")
    _seed(store, _f("theirs-1", entity="OPENAI"), "2026-07-02",
          category="models.frontier-closed")
    findings, _, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [f.id for f in findings] == ["mine-1"]
    assert [(s.id, s.category) for s in skipped] == [("entity:openai", "models.frontier-closed")]


def test_absent_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("nocat-1"), "2026-07-02", category=None)
    findings, _, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert findings == []
    assert [(s.id, s.category) for s in skipped] == [("entity:nvda", None)]


def test_same_finding_on_two_pages_deduplicated(tmp_path):
    store = _store(tmp_path)
    f = _f("shared-1")
    _seed(store, f, "2026-07-02")
    # observe the SAME finding from a second page without re-appending it
    store.create_page("entity:amd", "entity", "AMD", category="chips.merchant-gpu",
                      as_of="2026-07-02")
    store.append_observation("entity:amd", f.id, as_of="2026-07-02")
    findings, _, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [x.id for x in findings] == ["shared-1"]


def test_dangling_observation_fails_loud(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("ok-1"), "2026-07-02")
    (tmp_path / "findings" / "ok-1.json").unlink()   # corrupt the canonical store
    with pytest.raises(CorpusError, match="ok-1"):
        enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_enumerate.py -v`
Expected: FAIL — `ImportError: cannot import name 'enumerate_store'`

- [ ] **Step 3: Write the implementation (append to gpu_agent/corpus.py)**

```python
def enumerate_store(store_root, category: str, as_of: str,
                    window_days: int) -> tuple[list[Finding], int, list[SkippedPage]]:
    """The windowed store corpus for `category`: every finding observed by a wiki page
    whose header category matches, deduplicated across pages, window-filtered, sorted by
    (asOf, id). Pages with a different or absent category are skipped AND reported (the
    caller logs them — nothing silent). A dangling/unreadable observation finding fails
    loud: the canonical store is trusted input, corruption is a stop-the-line event."""
    store_root = Path(store_root)
    wiki_dir = store_root / "wiki"
    if not wiki_dir.is_dir():
        return [], 0, []   # honest empty: no wiki yet (first-ever cycle)
    store = WikiStore(wiki_dir, FindingStore(store_root / "findings"))
    included: list[Finding] = []
    seen_ids: set[str] = set()
    out_of_window = 0
    skipped: list[SkippedPage] = []
    for entry in store.index():
        if entry.category != category:
            skipped.append(SkippedPage(id=entry.id, category=entry.category))
            continue
        for obs in store.observations(entry.id):
            if obs.findingId in seen_ids:
                continue
            seen_ids.add(obs.findingId)
            try:
                f = store.findings.get(obs.findingId)
            except (FindingNotFound, ValueError) as e:
                raise CorpusError(
                    f"store integrity: page {entry.id} observation references "
                    f"unreadable finding {obs.findingId}: {e}") from e
            if in_window(f.asOf, as_of, window_days):
                included.append(f)
            else:
                out_of_window += 1
    included.sort(key=lambda f: (f.asOf, f.id))
    return included, out_of_window, skipped
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_enumerate.py tests/test_corpus_window.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/corpus.py tests/test_corpus_enumerate.py
git commit -m "$(cat <<'EOF'
feat(corpus): F62 category-scoped store enumeration, fail-loud integrity

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: corpus.py — assemble (L2 passthrough + merge + report)

**Files:**
- Modify: `gpu_agent/corpus.py` (append)
- Test: `tests/test_corpus_assemble.py`

**Interfaces:**
- Consumes: Tasks 1–2; `classify_findings(findings, wiki_store, config=...) -> DedupResult` (`.new/.update/.duplicate: list[FindingClass]`, `.outFindings: list[Finding]`).
- Produces: `assemble(store_root, category: str, as_of: str, fresh: list[Finding], registry, *, window_days: int = WINDOW_DAYS_DEFAULT) -> CorpusResult`. (`registry` is consumed by Task 4's coverage; in this task wire the parameter through and leave `coverage`/`notCovered` empty — Task 4 fills them inside `assemble`.)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_corpus_assemble.py
from gpu_agent.corpus import assemble
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

REGISTRY = IndicatorRegistry.load("registry/indicators.json")


# local factories — repo convention, same block as tests/test_corpus_enumerate.py
def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_assemble_empty_store_merged_equals_fresh(tmp_path):
    fresh = [_f("fresh-1", indicatorId="rpoBacklog")]
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY)
    assert [f.id for f in res.merged] == ["fresh-1"]
    assert [f.id for f in res.dedupedFresh] == ["fresh-1"]
    assert [fc.findingId for fc in res.report.freshNew] == ["fresh-1"]
    assert res.report.storeIncluded == []


def test_assemble_store_plus_fresh_new(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", entity="AMD", as_of="2026-07-02"), "2026-07-02")
    fresh = [_f("fresh-1", entity="NVDA", indicatorId="rpoBacklog", as_of="2026-07")]
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY)
    assert [f.id for f in res.merged] == ["store-1", "fresh-1"]   # store part first
    assert res.report.storeIncluded == ["store-1"]
    assert [fc.findingId for fc in res.report.freshNew] == ["fresh-1"]


def test_assemble_fresh_duplicate_dropped_and_reported(tmp_path):
    store = _store(tmp_path)
    prior = _f("store-1", as_of="2026-07-02")
    _seed(store, prior, "2026-07-02")
    # identical statement/trend/magnitude, same (entity, indicator) -> DUPLICATE vs store
    dup = _f("fresh-dup", as_of="2026-07")
    dup = dup.model_copy(update={"statement": prior.statement})
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", [dup], REGISTRY)
    assert [f.id for f in res.merged] == ["store-1"]
    assert res.dedupedFresh == []
    assert [fc.findingId for fc in res.report.freshDuplicate] == ["fresh-dup"]


def test_assemble_id_overlap_keeps_store_copy(tmp_path):
    store = _store(tmp_path)
    f = _f("same-id", as_of="2026-07-02")
    _seed(store, f, "2026-07-02")
    # same id arrives fresh with DIFFERENT statement -> classifier calls it update
    # (changed statement), but the id already exists in the store part: store copy kept
    changed = f.model_copy(update={"statement": "different"})
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", [changed], REGISTRY)
    assert [x.id for x in res.merged] == ["same-id"]
    assert res.merged[0].statement == f.statement          # the store copy
    assert res.report.idOverlaps == ["same-id"]


def test_assemble_deterministic(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", as_of="2026-07-02"), "2026-07-02")
    fresh = [_f("fresh-1", indicatorId="rpoBacklog", as_of="2026-07")]
    a = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY)
    b = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY)
    assert a.report.model_dump_json() == b.report.model_dump_json()
    assert [f.id for f in a.merged] == [f.id for f in b.merged]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_assemble.py -v`
Expected: FAIL — `ImportError: cannot import name 'assemble'`

- [ ] **Step 3: Write the implementation (append to gpu_agent/corpus.py)**

```python
def assemble(store_root, category: str, as_of: str, fresh: list[Finding], registry, *,
             window_days: int = WINDOW_DAYS_DEFAULT) -> CorpusResult:
    """The F62 merged corpus: windowed store findings + this cycle's fresh gated
    findings, classified against the store by the existing L2 machinery (intra-batch
    collapse + evidence-merge, then cross-store NEW/UPDATE keep vs DUPLICATE drop).
    The store part is never collapsed: it holds only NEW/UPDATE vintages by
    construction and multiple vintages of one series are deliberate history — scoring
    takes latest-per-series, the judge sees the (dated) evolution. An id overlap means
    the identical finding is already stored: the store copy is kept and the event
    reported. `registry` feeds the coverage table (store part only).
    """
    store_root = Path(store_root)
    store_findings, out_of_window, skipped = enumerate_store(
        store_root, category, as_of, window_days)
    wiki = WikiStore(store_root / "wiki", FindingStore(store_root / "findings"))
    res = classify_findings(fresh, wiki, config=DEFAULT_DEDUP_CONFIG)
    store_ids = {f.id for f in store_findings}
    id_overlaps = sorted(f.id for f in res.outFindings if f.id in store_ids)
    fresh_keeps = [f for f in res.outFindings if f.id not in store_ids]
    merged = store_findings + fresh_keeps
    end = period_end(as_of)
    report = CorpusReport(
        asOf=as_of, category=category, windowDays=window_days,
        windowStart=(end - datetime.timedelta(days=window_days)).isoformat(),
        windowEnd=end.isoformat(),
        storeIncluded=[f.id for f in store_findings],
        outOfWindow=out_of_window, skippedPages=skipped,
        freshNew=res.new, freshUpdate=res.update, freshDuplicate=res.duplicate,
        idOverlaps=id_overlaps,
    )
    return CorpusResult(merged=merged, dedupedFresh=fresh_keeps, report=report)
```

Note: `dedupedFresh` excludes id-overlaps for the same reason the merge does — the identical finding is already in the store, and `FindingStore.append` of a differing same-id payload would fail loud at write-back (its existing collision check; correct behavior, we just don't ingest a known copy twice).

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_assemble.py tests/test_corpus_enumerate.py tests/test_corpus_window.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/corpus.py tests/test_corpus_assemble.py
git commit -m "$(cat <<'EOF'
feat(corpus): F62 assemble - L2 classification passthrough + merge + report

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: corpus.py — coverage table + rendered block

**Files:**
- Modify: `gpu_agent/corpus.py` (append `coverage` + `render_coverage_text`; add the coverage call inside `assemble`)
- Test: `tests/test_corpus_coverage.py`

**Interfaces:**
- Consumes: Task 3's `assemble` (gains the coverage fill), `CoverageEntry`; `IndicatorRegistry.indicators` (iterable of registered ids).
- Produces: `coverage(store_findings: list[Finding], registry) -> tuple[list[CoverageEntry], list[str]]`; `render_coverage_text(report: CorpusReport) -> str`. `assemble` now returns reports with `coverage`/`notCovered` filled from the store part.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_corpus_coverage.py
from gpu_agent.corpus import CorpusReport, assemble, coverage, render_coverage_text
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

REGISTRY = IndicatorRegistry.load("registry/indicators.json")


# local factories — repo convention, same block as tests/test_corpus_enumerate.py
def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_coverage_entries_latest_and_count():
    fs = [
        _f("a-1", entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
           observedAt="2026-07-01"),
        _f("a-2", entity="NVDA", indicatorId="designWins", as_of="2026-07-03",
           observedAt="2026-07-03"),
        _f("b-1", entity="AMD", indicatorId="designWins", as_of="2026-07-02",
           observedAt="2026-07-01"),
    ]
    entries, not_covered = coverage(fs, REGISTRY)
    assert [(e.entity, e.indicatorId, e.count, e.latestAsOf) for e in entries] == [
        ("AMD", "designWins", 1, "2026-07-02"),
        ("NVDA", "designWins", 2, "2026-07-03"),
    ]
    assert "designWins" not in not_covered
    assert "rpoBacklog" in not_covered          # registered, zero windowed findings
    assert not_covered == sorted(not_covered)


def test_coverage_empty_store():
    entries, not_covered = coverage([], REGISTRY)
    assert entries == []
    assert set(not_covered) == set(REGISTRY.indicators)


def test_assemble_fills_coverage(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", as_of="2026-07-02"), "2026-07-02")
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", [], REGISTRY)
    assert [e.indicatorId for e in res.report.coverage] == ["designWins"]
    assert "designWins" not in res.report.notCovered


def test_render_coverage_text_covered_and_gaps():
    report = CorpusReport(
        asOf="2026-07", category="chips.merchant-gpu", windowDays=45,
        windowStart="2026-06-16", windowEnd="2026-07-31",
        storeIncluded=["a-1"],
        coverage=[{"entity": "NVDA", "indicatorId": "designWins", "count": 2,
                   "latestAsOf": "2026-07-03", "latestObservedAt": "2026-07-03"}],
        notCovered=["leadTimes", "rpoBacklog"])
    text = render_coverage_text(report)
    lines = text.splitlines()
    assert lines[0] == ("STORE COVERAGE (window 2026-06-16 < asOf <= 2026-07-31, "
                        "1 finding(s)):")
    assert "  NVDA designWins: 2 finding(s), latest asOf 2026-07-03 (observed 2026-07-03)" in lines
    assert "  not covered: leadTimes, rpoBacklog" in lines


def test_render_coverage_text_empty_store_names_full_gather():
    report = CorpusReport(asOf="2026-07", category="c", windowDays=45,
                          windowStart="2026-06-16", windowEnd="2026-07-31")
    assert "(no store coverage — full gather)" in render_coverage_text(report)


def test_render_deterministic():
    report = CorpusReport(asOf="2026-07", category="c", windowDays=45,
                          windowStart="2026-06-16", windowEnd="2026-07-31")
    assert render_coverage_text(report) == render_coverage_text(report)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_coverage.py -v`
Expected: FAIL — `ImportError: cannot import name 'coverage'`

- [ ] **Step 3: Write the implementation**

Append to `gpu_agent/corpus.py`:

```python
def coverage(store_findings: list[Finding], registry) -> tuple[list[CoverageEntry], list[str]]:
    """Per (entity, indicatorId) over the windowed STORE part: count + latest vintage.
    not_covered = every registered indicator id with zero windowed store findings
    (price included — the gather top-up aims at these). Sorted, deterministic."""
    by_key: dict[tuple[str, str], list[Finding]] = {}
    for f in store_findings:
        by_key.setdefault((f.entity, f.indicatorId), []).append(f)
    entries: list[CoverageEntry] = []
    for (entity, ind), fs in sorted(by_key.items()):
        latest = max(fs, key=lambda f: (f.asOf, f.observedAt, f.id))
        entries.append(CoverageEntry(entity=entity, indicatorId=ind, count=len(fs),
                                     latestAsOf=latest.asOf,
                                     latestObservedAt=latest.observedAt))
    covered = {ind for (_entity, ind) in by_key}
    not_covered = [i for i in sorted(registry.indicators) if i not in covered]
    return entries, not_covered


def render_coverage_text(report: CorpusReport) -> str:
    """Deterministic coverage block for the gather-category dispatch (run-cycle step a0):
    one header line naming the window, one line per covered series, one not-covered line."""
    lines = [f"STORE COVERAGE (window {report.windowStart} < asOf <= "
             f"{report.windowEnd}, {len(report.storeIncluded)} finding(s)):"]
    if not report.coverage:
        lines.append("  (no store coverage — full gather)")
    for c in report.coverage:
        lines.append(f"  {c.entity} {c.indicatorId}: {c.count} finding(s), "
                     f"latest asOf {c.latestAsOf} (observed {c.latestObservedAt})")
    if report.notCovered:
        lines.append("  not covered: " + ", ".join(report.notCovered))
    return "\n".join(lines)
```

In `assemble`, fill the two fields: build the report as before but add, just before constructing `CorpusReport`:

```python
    cov_entries, not_covered = coverage(store_findings, registry)
```

and pass `coverage=cov_entries, notCovered=not_covered` to the `CorpusReport(...)` call.

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corpus_coverage.py tests/test_corpus_assemble.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/corpus.py tests/test_corpus_coverage.py
git commit -m "$(cat <<'EOF'
feat(corpus): F62 coverage table + rendered gather-dispatch block

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: CLI — the `corpus` command (both modes)

**Files:**
- Modify: `gpu_agent/cli.py` (imports; new `_corpus` handler near `_wiki_dedup` ~line 154; new parser after the `wiki-lifecycle` parser ~line 827; dispatch entry beside `wiki-dedup`'s ~line 909)
- Test: `tests/test_cli_corpus.py`

**Interfaces:**
- Consumes: Task 4's `assemble`, `render_coverage_text`, `CorpusError`, `WINDOW_DAYS_DEFAULT`; cli's existing `_load_registry()`.
- Produces: the CLI grammar `gpu-agent corpus --store S --category C --as-of A [--window-days N] [--fresh F --out-merged M [--out-deduped-fresh D]] [--report R]` (Task 8's skill text relies on these exact flags).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_corpus.py
import json
import subprocess
import sys

from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore


# local factories — repo convention, same block as tests/test_corpus_enumerate.py
def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _write_fresh(tmp_path, findings):
    p = tmp_path / "fresh.json"
    p.write_text(json.dumps([f.model_dump() for f in findings], indent=2), "utf-8")
    return p


def test_store_only_mode_prints_coverage(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", as_of="2026-07-02"), "2026-07-02")
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--report", str(tmp_path / "cov.json"))
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("STORE COVERAGE")
    assert "NVDA designWins" in out.stdout
    report = json.loads((tmp_path / "cov.json").read_text("utf-8"))
    assert report["storeIncluded"] == ["store-1"]


def test_store_only_mode_empty_store(tmp_path):
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07")
    assert out.returncode == 0, out.stderr
    assert "no store coverage" in out.stdout


def test_fresh_requires_out_merged(tmp_path):
    fresh = _write_fresh(tmp_path, [_f("fresh-1")])
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--fresh", str(fresh))
    assert out.returncode == 2
    assert "--out-merged" in out.stderr


def test_assemble_mode_writes_artifacts_and_summary(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", entity="AMD", as_of="2026-07-02"), "2026-07-02")
    fresh = _write_fresh(tmp_path, [_f("fresh-1", indicatorId="rpoBacklog",
                                       as_of="2026-07", entity="NVDA")])
    merged_p = tmp_path / "merged.json"
    deduped_p = tmp_path / "deduped.json"
    report_p = tmp_path / "report.json"
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--fresh", str(fresh),
               "--out-merged", str(merged_p), "--out-deduped-fresh", str(deduped_p),
               "--report", str(report_p))
    assert out.returncode == 0, out.stderr
    merged = json.loads(merged_p.read_text("utf-8"))
    assert [f["id"] for f in merged] == ["store-1", "fresh-1"]
    deduped = json.loads(deduped_p.read_text("utf-8"))
    assert [f["id"] for f in deduped] == ["fresh-1"]
    assert "store 1 in-window (0 out), fresh new 1 update 0 duplicate 0 -> merged 2" \
        in out.stdout


def test_drops_and_skips_hit_stderr(tmp_path):
    store = _store(tmp_path)
    prior = _f("store-1", as_of="2026-07-02")
    _seed(store, prior, "2026-07-02")
    _seed(store, _f("theirs-1", entity="OPENAI", as_of="2026-07-02"), "2026-07-02",
          category="models.frontier-closed")
    dup = _f("fresh-dup", as_of="2026-07").model_copy(
        update={"statement": prior.statement})
    fresh = _write_fresh(tmp_path, [dup])
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026-07", "--fresh", str(fresh),
               "--out-merged", str(tmp_path / "m.json"))
    assert out.returncode == 0, out.stderr
    assert "SKIPPED-PAGE entity:openai: category=models.frontier-closed" in out.stderr
    assert "DROPPED-DUPLICATE fresh-dup" in out.stderr


def test_bad_as_of_label_exits_1(tmp_path):
    out = _run("corpus", "--store", str(tmp_path), "--category", "chips.merchant-gpu",
               "--as-of", "2026/07")
    assert out.returncode == 1
    assert "invalid asOf label" in out.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_cli_corpus.py -v`
Expected: FAIL — argparse error `invalid choice: 'corpus'` (non-zero exit codes / assertion failures)

- [ ] **Step 3: Write the implementation**

In `gpu_agent/cli.py` add to the imports block (near the other `gpu_agent.` imports):

```python
from gpu_agent.corpus import (
    WINDOW_DAYS_DEFAULT, CorpusError, assemble as corpus_assemble, render_coverage_text)
```

Add the handler after `_wiki_dedup` (after cli.py:154):

```python
def _corpus(args) -> int:
    """Handler for `gpu-agent corpus` (F62). Store-only mode (no --fresh) prints the
    coverage block for the gather top-up dispatch; assemble mode (--fresh) writes the
    merged corpus + deduped-fresh stream + CorpusReport. Every skip/drop is a stderr
    line AND a report field — nothing silent."""
    registry, _ = _load_registry()
    fresh = []
    if args.fresh:
        if not args.out_merged:
            print("gpu-agent corpus: error: --fresh requires --out-merged", file=sys.stderr)
            return 2
        fresh = [Finding.model_validate(d)
                 for d in json.loads(pathlib.Path(args.fresh).read_text("utf-8"))]
    try:
        result = corpus_assemble(args.store, args.category, args.as_of, fresh,
                                 registry, window_days=args.window_days)
    except CorpusError as e:
        print(f"gpu-agent corpus: error: {e}", file=sys.stderr)
        return 1
    report = result.report
    for sp in report.skippedPages:
        print(f"SKIPPED-PAGE {sp.id}: category={sp.category}", file=sys.stderr)
    for fc in report.freshDuplicate:
        print(f"DROPPED-DUPLICATE {fc.findingId}: {fc.detail or 'duplicate'}", file=sys.stderr)
    for fid in report.idOverlaps:
        print(f"ID-OVERLAP {fid}: store copy kept", file=sys.stderr)
    if report.outOfWindow:
        print(f"out-of-window: {report.outOfWindow} store finding(s) excluded", file=sys.stderr)
    if args.report:
        pathlib.Path(args.report).write_text(report.model_dump_json(indent=2), "utf-8")
    if args.fresh:
        pathlib.Path(args.out_merged).write_text(
            json.dumps([f.model_dump() for f in result.merged], indent=2), "utf-8")
        if args.out_deduped_fresh:
            pathlib.Path(args.out_deduped_fresh).write_text(
                json.dumps([f.model_dump() for f in result.dedupedFresh], indent=2), "utf-8")
        print(f"store {len(report.storeIncluded)} in-window ({report.outOfWindow} out), "
              f"fresh new {len(report.freshNew)} update {len(report.freshUpdate)} "
              f"duplicate {len(report.freshDuplicate)} -> merged {len(result.merged)}")
    else:
        print(render_coverage_text(report))
    return 0
```

Add the parser right after the `wiki-lifecycle` parser block (after cli.py:827):

```python
    co = sub.add_parser("corpus")
    co.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    co.add_argument("--category", required=True, help="category id (scopes wiki pages)")
    co.add_argument("--as-of", required=True, help="run vintage (YYYY-MM or YYYY-MM-DD)")
    co.add_argument("--window-days", type=int, default=WINDOW_DAYS_DEFAULT,
                    help=f"corpus recency window in days (default {WINDOW_DAYS_DEFAULT})")
    co.add_argument("--fresh", default=None,
                    help="this cycle's gated findings JSON; enables assemble mode")
    co.add_argument("--out-merged", default=None,
                    help="write the merged corpus findings here (required with --fresh)")
    co.add_argument("--out-deduped-fresh", default=None,
                    help="write the deduped NEW+UPDATE fresh stream here (for wiki-ingest)")
    co.add_argument("--report", default=None, help="write the CorpusReport JSON here")
```

Add the dispatch entry beside `wiki-dedup`'s (after cli.py:910):

```python
    if args.cmd == "corpus":
        try:
            return _corpus(args)
        except RegistryError as e:
            print("REGISTRY GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
            return 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_cli_corpus.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full suite**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q`
Expected: 923 + new tests passed / 3 skipped, no failures

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/cli.py tests/test_cli_corpus.py
git commit -m "$(cat <<'EOF'
feat(cli): F62 corpus command - coverage mode + assemble mode

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: CLI — pipeline corpus flags + equality pin

**Files:**
- Modify: `gpu_agent/cli.py` (`_pipeline` at cli.py:597; `pipeline` parser at cli.py:866)
- Test: `tests/test_cli_pipeline_corpus.py`

**Interfaces:**
- Consumes: Task 4's `assemble` (already imported in cli.py as `corpus_assemble`), Task 5's `corpus` command (the equality test runs both).
- Produces: `pipeline --corpus-store <root> [--corpus-window-days N] [--corpus-report <path>]` — Task 8's skill text relies on these exact flags.

- [ ] **Step 1: Write the failing tests**

Notes for the test design, so the fixtures stay gate-clean:
- `fixtures/raw` + `fixtures/recorded/extract-nvda.json` + `fixtures/recorded/judge-nvda.json` + `fixtures/asg.chips.merchant-gpu.json` are the existing recorded-pipeline fixtures. The legacy judge fixture predates the F67 voice lint, so existing pipeline tests pass `--no-voice-lint` — every pipeline invocation here does the same.
- The seeded store finding uses `indicatorId="flopsPerDollar"`: registered but **dimension-less and non-scoring** (registry side `None` also skips the F37 side check). It therefore lands in `scorecard.findings` (the equality pin) while touching NOTHING the recorded judge answer depends on — no briefing group, no anchor, no DMI/SMI. The recorded fixture replays byte-identically.
- Fix `--captured-at 2026-06-12T00:00:00Z` everywhere (determinism + the spec's same-captured-at invariant). The seeded asOf `2026-05-20` is in-window for run asOf `2026-06`: period_end = 2026-06-30, window start (exclusive) = 2026-05-16.

```python
# tests/test_cli_pipeline_corpus.py
import json
import subprocess
import sys

from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

CAPTURED = "2026-06-12T00:00:00Z"


# local factories — repo convention, same block as tests/test_corpus_enumerate.py
def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _extract_fresh(tmp_path):
    out_p = tmp_path / "findings.json"
    r = _run("extract", "--recorded", "fixtures/recorded/extract-nvda.json",
             "--docs", "fixtures/raw", "--as-of", "2026-06",
             "--captured-at", CAPTURED, "--out", str(out_p))
    assert r.returncode == 0, r.stderr
    return out_p


def _seed_store(tmp_path):
    """One in-window store finding on a dimension-less, non-scoring indicator
    (flopsPerDollar): lands in scorecard.findings without touching anchors,
    citation groups, or DMI/SMI — the recorded judge fixture replays unchanged."""
    store = _store(tmp_path / "store")
    f = _f("seeded-store-1", entity="SEEDCO", indicatorId="flopsPerDollar",
           as_of="2026-05-20", observedAt="2026-05-20")
    _seed(store, f, "2026-05-20")
    return f


def test_pipeline_without_corpus_flags_unchanged(tmp_path):
    _seed_store(tmp_path)   # present on disk, must NOT be read without the flags
    r = _run("pipeline", "--docs", "fixtures/raw",
             "--assignment", "fixtures/asg.chips.merchant-gpu.json",
             "--as-of", "2026-06", "--captured-at", CAPTURED,
             "--recorded-extract", "fixtures/recorded/extract-nvda.json",
             "--recorded-judge", "fixtures/recorded/judge-nvda.json",
             "--no-voice-lint", "--out", str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert "corpus:" not in r.stderr
    sc = json.loads(next((tmp_path / "out" / "chips.merchant-gpu").glob("*.json"))
                    .read_text("utf-8"))
    assert all(f["id"] != "seeded-store-1" for f in sc["findings"])


def test_pipeline_corpus_merges_store_finding_and_matches_corpus_cli(tmp_path):
    fresh_p = _extract_fresh(tmp_path)
    _seed_store(tmp_path)
    store_root = str(tmp_path / "store")

    # the corpus CLI's merged file (what judge --emit-prompt would consume)
    merged_p = tmp_path / "merged.json"
    r = _run("corpus", "--store", store_root, "--category", "chips.merchant-gpu",
             "--as-of", "2026-06", "--fresh", str(fresh_p),
             "--out-merged", str(merged_p))
    assert r.returncode == 0, r.stderr
    merged_ids = [f["id"] for f in json.loads(merged_p.read_text("utf-8"))]
    assert "seeded-store-1" in merged_ids

    # pipeline with the corpus flags: scorecard findings == the corpus CLI's merge
    report_p = tmp_path / "corpus-report.json"
    r = _run("pipeline", "--docs", "fixtures/raw",
             "--assignment", "fixtures/asg.chips.merchant-gpu.json",
             "--as-of", "2026-06", "--captured-at", CAPTURED,
             "--recorded-extract", "fixtures/recorded/extract-nvda.json",
             "--recorded-judge", "fixtures/recorded/judge-nvda.json",
             "--no-voice-lint",
             "--corpus-store", store_root, "--corpus-report", str(report_p),
             "--out", str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    assert "corpus: store 1 in-window" in r.stderr
    sc = json.loads(next((tmp_path / "out" / "chips.merchant-gpu").glob("*.json"))
                    .read_text("utf-8"))
    assert [f["id"] for f in sc["findings"]] == merged_ids       # the equality pin
    report = json.loads(report_p.read_text("utf-8"))
    assert report["storeIncluded"] == ["seeded-store-1"]


def test_pipeline_corpus_error_fails_loud(tmp_path):
    (tmp_path / "store" / "wiki").mkdir(parents=True)
    r = _run("pipeline", "--docs", "fixtures/raw",
             "--assignment", "fixtures/asg.chips.merchant-gpu.json",
             "--as-of", "2026/06", "--captured-at", CAPTURED,
             "--recorded-extract", "fixtures/recorded/extract-nvda.json",
             "--recorded-judge", "fixtures/recorded/judge-nvda.json",
             "--no-voice-lint",
             "--corpus-store", str(tmp_path / "store"),
             "--out", str(tmp_path / "out"))
    assert r.returncode == 1
    assert "corpus error" in r.stderr


def test_store_finding_citable_in_scorecard_and_report():
    """Spec e2e: a store-vintage finding is citable — the frozen gate validates a
    rating citing it and the rendered report's citation map resolves the id."""
    from gpu_agent.assignment import load_assignment
    from gpu_agent.pipeline import build_scorecard
    from gpu_agent.registry.horizon import IndicatorHorizons
    from gpu_agent.registry.indicators import IndicatorRegistry
    from gpu_agent.report import render_report
    from gpu_agent.schema.scorecard import DimensionRating

    registry = IndicatorRegistry.load("registry/indicators.json")
    horizons = IndicatorHorizons.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    # designWins: side structural (matches the factory), dimension competitiveStructure
    store_f = _f("store-cited-1", indicatorId="designWins", as_of="2026-05-20",
                 observedAt="2026-05-20")
    fresh_f = _f("fresh-1", entity="AMD")
    merged = [store_f, fresh_f]
    ratings = {"competitiveStructure": DimensionRating(
        rating="Mixed", direction="steady", findingIds=["store-cited-1"],
        rationale="Cites the store-vintage finding.",
        confidence=Confidence(level="medium", basis="test"))}
    sc = build_scorecard(merged, ratings, {"competitiveStructure": 0.0}, a,
                         "n", Confidence(level="medium", basis="b"), registry,
                         horizons=horizons)
    assert "store-cited-1" in sc.dimensionRatings["competitiveStructure"].findingIds
    text = render_report(sc, None, registry, horizons=horizons,
                         render_ts="2026-07-04T00:00:00Z")
    assert "store-cited-1" in text   # the appendix CITATION MAP lists every finding
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_cli_pipeline_corpus.py -v`
Expected: FAIL — argparse `unrecognized arguments: --corpus-store`

- [ ] **Step 3: Write the implementation**

In the `pipeline` parser block (after cli.py:878's `--no-voice-lint`):

```python
    pl.add_argument("--corpus-store", default=None,
                    help="store root; when given, merge the windowed store corpus (F62) "
                         "into the judged + scored findings")
    pl.add_argument("--corpus-window-days", type=int, default=WINDOW_DAYS_DEFAULT,
                    help=f"corpus recency window in days (default {WINDOW_DAYS_DEFAULT})")
    pl.add_argument("--corpus-report", default=None, help="write the CorpusReport JSON here")
```

In `_pipeline`, immediately after `_gate_assignment(a, registry, taxonomy)` (cli.py:638) and before the F5 comment block:

```python
    # F62: merge the windowed store corpus into the judged + scored findings. Same
    # deterministic assemble() the `corpus` command runs over the emit step's findings
    # file, so the emitted prompt's anchors/citation groups and the gate's match —
    # provided the session reused one --captured-at (run-cycle states this).
    if args.corpus_store:
        try:
            cres = corpus_assemble(args.corpus_store, a.category, args.as_of, findings,
                                   registry, window_days=args.corpus_window_days)
        except CorpusError as e:
            print(f"gpu-agent pipeline: corpus error: {e}", file=sys.stderr)
            return 1
        findings = cres.merged
        rep = cres.report
        if args.corpus_report:
            pathlib.Path(args.corpus_report).write_text(rep.model_dump_json(indent=2), "utf-8")
        print(f"corpus: store {len(rep.storeIncluded)} in-window ({rep.outOfWindow} out), "
              f"fresh new {len(rep.freshNew)} update {len(rep.freshUpdate)} "
              f"duplicate {len(rep.freshDuplicate)} -> merged {len(findings)}",
              file=sys.stderr)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_cli_pipeline_corpus.py -v`
Expected: all PASS. If the recorded judge hits any gate, the seeded indicator choice is wrong — `flopsPerDollar` must stay dimension-less and non-scoring (check `registry/indicators.json`); fix the seed, never the fixture.

- [ ] **Step 5: Run the full suite**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q`
Expected: all passed / 3 skipped

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/cli.py tests/test_cli_pipeline_corpus.py
git commit -m "$(cat <<'EOF'
feat(cli): F62 pipeline corpus flags - merged corpus reaches judge + scorecard

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `observed=` vintage tag in emitted judge/thesis rows (EVAL-GATED)

**Files:**
- Modify: `gpu_agent/judgment/prompt.py:51-63` (`build_user_prompt`)
- Modify: `gpu_agent/cli.py:307` (`_emit_judge_prompt`'s `build_user_prompt` call)
- Modify: `gpu_agent/thesis.py:729-737` (`_finding_lines`)
- Modify: `gpu_agent/evals/emit.py:55-56` (judge seam mirror)
- Test: `tests/test_prompt_dates.py`; update any existing asserts that pin the old row format (unit tests only — NEVER eval fixtures/baseline)

**Interfaces:**
- Consumes: existing `build_user_prompt(briefing, memory_text=None, include_groups=False)`.
- Produces: `build_user_prompt(..., include_dates: bool = False)`; dated rows on `judge --emit-prompt`, `thesis --emit-prompt`, and the eval judge/thesis emits.

**⚠ This task turns `tests/test_evals_baseline_pin.py` RED — that is the armed F6 gate working as designed.** The unlock is Task 9 (run-eval + rebaseline), NOT any edit to `fixtures/evals/`. From this task on, run the suite with `--deselect tests/test_evals_baseline_pin.py` and report that explicitly.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prompt_dates.py
"""F62 — emitted judge/thesis rows carry the finding's observation date so a brain
judging a mixed-vintage corpus can weigh old vs new. The frozen internal judge path
(include_dates default False) stays byte-identical."""
import json
import subprocess
import sys

from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.judgment.prompt import build_user_prompt
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.thesis import _finding_lines

REGISTRY = IndicatorRegistry.load("registry/indicators.json")


# local finding factory — repo convention, same shape as tests/test_corpus_enumerate.py's
def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _briefing():
    return build_briefing([_f("doc-1", indicatorId="designWins",
                              observedAt="2026-06-29")],
                          REGISTRY, "chips.merchant-gpu")


def test_default_byte_identical_without_dates():
    b = _briefing()
    assert build_user_prompt(b) == build_user_prompt(b, include_dates=False)
    assert "observed=" not in build_user_prompt(b)


def test_include_dates_appends_observed_inside_parens():
    row_lines = [l for l in build_user_prompt(_briefing(), include_dates=True).splitlines()
                 if l.strip().startswith("doc-1")]
    assert len(row_lines) == 1
    assert row_lines[0].endswith("conf=medium observed=2026-06-29)")


def test_thesis_rows_carry_observed():
    lines = _finding_lines([_f("doc-1", observedAt="2026-06-29")])
    assert lines[0].endswith("conf=medium observed=2026-06-29)")


def test_judge_emit_cli_carries_observed(tmp_path):
    findings = [_f("doc-1", observedAt="2026-06-29")]
    p = tmp_path / "findings.json"
    p.write_text(json.dumps([f.model_dump() for f in findings]), "utf-8")
    out = _run("judge", "--emit-prompt", "--findings", str(p),
               "--category", "chips.merchant-gpu", "--store", str(tmp_path / "store"))
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "observed=2026-06-29" in bundle["user"]


def test_thesis_emit_cli_carries_observed(tmp_path):
    findings = [_f("doc-1", observedAt="2026-06-29")]
    p = tmp_path / "findings.json"
    p.write_text(json.dumps([f.model_dump() for f in findings]), "utf-8")
    out = _run("thesis", "--findings", str(p), "--store", str(tmp_path / "store"),
               "--category", "chips.merchant-gpu", "--as-of", "2026-07",
               "--emit-prompt", "--seed", "registry/theses.chips.merchant-gpu.json")
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "observed=2026-06-29" in bundle["user"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_prompt_dates.py -v`
Expected: FAIL — `TypeError: build_user_prompt() got an unexpected keyword argument 'include_dates'` and missing `observed=` asserts

- [ ] **Step 3: Write the implementation**

`gpu_agent/judgment/prompt.py` — replace the row loop in `build_user_prompt` (keep the signature's existing params, add `include_dates: bool = False` at the end):

```python
def build_user_prompt(briefing: Briefing, memory_text: str | None = None,
                      include_groups: bool = False, include_dates: bool = False) -> str:
    lines = ["Anchors (sign bounds your rating; absent = no numeric bound):"]
    for dim, a in sorted(briefing.anchors.items()):
        lines.append(f"  {dim}: {a:+.2f}")
    lines.append("")
    lines.append("Findings (cite by id):")
    for f in briefing.findings:
        row = (
            f"  {f.id} [{f.indicatorId}] {f.statement} "
            f"(demand={f.polarityDemand:+d} supply={f.polaritySupply:+d} "
            f"mag={f.magnitude} conf={f.confidence.level}")
        # F62: the emit path dates every row so a brain judging a mixed-vintage corpus
        # can weigh old vs new. Default False keeps the frozen judge_findings internal
        # path byte-identical (same additive pattern as include_groups/memory_text).
        if include_dates:
            row += f" observed={f.observedAt[:10]}"
        lines.append(row + ")")
```

(The rest of the function is unchanged.)

`gpu_agent/cli.py` `_emit_judge_prompt` — the bundle's user line becomes:

```python
        "user": build_judge_user_prompt(briefing, memory_text=memory_text,
                                        include_groups=True, include_dates=True),
```

`gpu_agent/thesis.py` `_finding_lines` — replace with:

```python
def _finding_lines(findings: list[Finding]) -> list[str]:
    """Same per-finding row format the judge briefing emits (judgment/prompt.py's
    build_user_prompt with include_dates=True — F62 observed= vintage tag), copied
    verbatim rather than re-invented."""
    return [
        f"  {f.id} [{f.indicatorId}] {f.statement} "
        f"(demand={f.polarityDemand:+d} supply={f.polaritySupply:+d} "
        f"mag={f.magnitude} conf={f.confidence.level} observed={f.observedAt[:10]})"
        for f in findings
    ]
```

`gpu_agent/evals/emit.py` judge seam — mirror the live CLI emit:

```python
            "user": build_judge_user_prompt(briefing, memory_text=seam_input.memoryText,
                                            include_groups=True, include_dates=True),
```

(The thesis seam inherits the dated rows through `build_thesis_user_prompt` automatically.)

- [ ] **Step 4: Run the new tests, then the suite minus the armed pin**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_prompt_dates.py -v`
Expected: all PASS

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q --deselect tests/test_evals_baseline_pin.py`
Expected: everything else passes. If any existing unit test pins the old undated row format (candidates: `tests/test_prompt_vocab.py`, `tests/test_cli_emit_prompt.py`, thesis prompt tests, eval emit/hash unit tests other than the baseline pin), update those asserts to the dated format — they are unit tests of the new truth, NOT recorded brain answers or the baseline. Do NOT touch `fixtures/evals/`.

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -v`
Expected: FAIL (hash mismatch) with a message pointing at run-eval — confirm and report it; this is the armed gate, unlocked in Task 9.

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/judgment/prompt.py gpu_agent/thesis.py gpu_agent/evals/emit.py gpu_agent/cli.py tests/test_prompt_dates.py
# plus any legitimately-updated unit test files from Step 4
git commit -m "$(cat <<'EOF'
feat(prompts): F62 observed= vintage tag on emitted judge/thesis rows

Turns the F6 baseline pin red by design; rebaseline lands with the
run-eval pass (plan Task 9) before merge.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: run-cycle skill — standard-path corpus wiring

**Files:**
- Modify: `.claude/skills/run-cycle/SKILL.md` (Step 3 and Step 6; Daily mode untouched)

No code, no tests — the deliverable is exact skill prose. Verify by proofreading against the spec's "run-cycle skill wiring" section and by `grep -n "corpus" .claude/skills/run-cycle/SKILL.md` showing every insertion. The reviewer checks the skill text against the CLI grammar shipped in Tasks 5–6.

- [ ] **Step 1: Insert step (a0) before Step 3(a)** — after the line `For each `ready` entry, with its `assignment_path` and `asOf`:` insert:

````markdown
**(a0) Store coverage — corpus first (F62; deterministic, no LLM).** Before gathering, ask the
store what it already knows:
```
.venv/Scripts/python -m gpu_agent.cli corpus --store store --category <id> --as-of <asOf> \
  --report <work>/corpus-coverage.json
```
If the printed block shows coverage (not "no store coverage"), this gather is a **TOP-UP**: include
the coverage block VERBATIM in the gather-category dispatch with the instruction *"aim at the
`not covered` list and material updates to covered series; do not re-derive covered ground"*, and
cap this gather at `min(manifest maxDocuments, 10)` documents. An empty store means a full gather
exactly as before. (Gather slices/floors and L1 seen-doc threading stay F57 — do not improvise
them here.)
````

- [ ] **Step 2: Bind the captured-at invariant in Step 3(b)** — after the `extract --recorded` command block, add:

```markdown
**Use ONE `--captured-at` value for this category's `extract --recorded` AND `pipeline` calls**
(F62: the corpus merge runs in both places; identical inputs keep the emitted prompt's anchors and
the gate's identical).
```

- [ ] **Step 3: Insert step (b2) after Step 3(b)**:

````markdown
**(b2) Corpus assembly (F62; deterministic, no LLM).** Merge the windowed store corpus with this
cycle's fresh gated findings:
```
.venv/Scripts/python -m gpu_agent.cli corpus --store store --category <id> --as-of <asOf> \
  --fresh <work>/findings.json --out-merged <work>/corpus-findings.json \
  --out-deduped-fresh <work>/deduped-fresh.json --report <work>/corpus-report.json
```
Record the printed counts (store in-window / fresh new / update / duplicate). Every skipped page
and dropped duplicate is a stderr line and a report entry — surface them, never re-derive them.
````

- [ ] **Step 4: Point Step 3(c)'s judge emit at the merged corpus** — change the `judge --emit-prompt` command's `--findings <work>/findings.json` to `--findings <work>/corpus-findings.json`, and add after the command:

```markdown
(F62: the corpus file — the judge cites store findings by id like any other finding; their rows
carry `observed=` dates.)
```

- [ ] **Step 5: Add the corpus flags to Step 3(d)'s pipeline command**:

```
  --recorded-extract <work>/extract-answer.json --recorded-judge <work>/judge-answer.json \
  --corpus-store store --corpus-report <work>/corpus-pipeline-report.json --out store
```

- [ ] **Step 6: Insert step (d2) after Step 3(d)**:

````markdown
**(d2) Write-back (F62; deterministic, no LLM).** After a successful scorecard, route the deduped
fresh stream into the wiki so the store accumulates from this cycle too:
```
.venv/Scripts/python -m gpu_agent.cli wiki-ingest --findings <work>/deduped-fresh.json \
  --store store --as-of <asOf> --category <id>
.venv/Scripts/python -m gpu_agent.cli wiki-lint --store store --as-of <asOf>
```
If the scorecard step failed, SKIP write-back and log `write-back: skipped (scorecard failed)` in
the cycle log — never half-commit a failed cycle.
````

- [ ] **Step 7: Point Step 3(e)'s thesis command at the merged corpus** — change its `--findings <work>/findings.json` to `--findings <work>/corpus-findings.json`.

- [ ] **Step 8: Extend Step 6 (cycle log)** — in the finalize list, extend the per-category items with:

```markdown
the corpus artifacts (`corpus-coverage.json`, `corpus-findings.json`, `deduped-fresh.json`,
`corpus-report.json`) and the corpus counts (store in-window / fresh new / update / duplicate),
```

- [ ] **Step 9: Note the daily boundary** — at the top of the "Daily mode" section, add one sentence:

```markdown
(F62's corpus/top-up/write-back steps are the STANDARD path's; Daily mode already reads the store
via L1/L2 and writes back — it is unchanged.)
```

- [ ] **Step 10: Proofread + commit**

Run: `grep -n "corpus" .claude/skills/run-cycle/SKILL.md` — expect hits in a0/b/b2/c/d/d2/e/Step-6/Daily-note only.

```bash
git add .claude/skills/run-cycle/SKILL.md
git commit -m "$(cat <<'EOF'
docs(run-cycle): F62 standard-path corpus wiring - coverage top-up,
merged-corpus judge/thesis, pipeline corpus flags, write-back

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Run-eval + rebaseline (SESSION-LEVEL — not a subagent task)

**Files:**
- Modify: `fixtures/evals/baseline.json` — ONLY via `gpu-agent eval rebaseline`, never by hand
- Create: `work/eval-f62-<date>/` run artifacts (untracked or committed per run-eval skill convention)

**The coordinating session executes this task itself** following `.claude/skills/run-eval/SKILL.md` end to end (it dispatches ~15 tool-less Opus brains + ~19 rubric graders; a subagent must not sub-dispatch — delegation is one level deep).

- [ ] **Step 1:** Read `.claude/skills/run-eval/SKILL.md` and follow it: `eval emit-brain` → dispatch tool-less Opus brains → `eval record-brain` → `eval emit-grade` → dispatch graders → `eval record-grade`.
- [ ] **Step 2:** Check the comparison verdict: per-seam mean ≥ incumbent (extract 6.62 / judge 6.75 / thesis 5.50), TIES PASS; calibration negatives within limit. If a seam regresses, the prompt change (Task 7) needs iteration — investigate before rebaselining, never force past a real regression without recording why.
- [ ] **Step 3:** `gpu-agent eval rebaseline` per the skill (with `--reason` naming F62's observed= tag), commit the new baseline + run notes.
- [ ] **Step 4:** Run the FULL suite (no deselects): `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q`
Expected: everything passes / 3 skipped — the pin is green again.
- [ ] **Step 5: Commit** (baseline + any run-notes doc), message noting the rebaseline reason.

---

## Final verification (before requesting the branch merge)

- [ ] Full suite green, zero deselects: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q`
- [ ] Frozen-core diff empty: `git diff main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/schema gpu_agent/judgment/briefing.py gpu_agent/judgment/judge.py gpu_agent/pipeline.py` → no output. (`gpu_agent/store.py` may only show additions if any; `JsonStore` itself untouched.)
- [ ] Byte-identical defaults hold: `pipeline` without corpus flags, `build_user_prompt` without `include_dates` (both test-pinned).
- [ ] Requesting-code-review / finishing-a-development-branch per superpowers; MERGE ONLY on the user's explicit go (standing rule for this shared checkout).
