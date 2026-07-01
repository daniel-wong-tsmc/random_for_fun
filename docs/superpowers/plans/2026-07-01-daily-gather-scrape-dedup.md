# Daily gather + scrape + cross-run dedup-vs-store (sub-project 4-4d) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the daily input firehose — a pure-code **cross-run dedup-vs-store** engine (L1 seen-document index + L2 finding-level NEW/UPDATE/DUPLICATE classifier) wired into the CLI, plus the **daily gather mode** + **numeric scrape sweep** skill edits — so the daily sweep surfaces only what changed and logs the rest, all additive with the frozen contract byte-unchanged.

**Architecture:** A new pure module `gpu_agent/gathering/dedup.py` reads a persistent `SeenDocIndex` (L1, pre-brain) and the wiki store's entity-page observations (L2, post-gate) and returns a `DedupReport`/`DedupResult`. L1 is an additive `--dedup-store` flag on the existing `ingest` subcommand; L2 is a new `wiki-dedup` subcommand. The daily gather mode + numeric scrape are additive edits to the `gather-category`/`run-cycle` skills, validated by documented dry-runs.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), stdlib `hashlib`/`json`/`pathlib`, pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset on Windows — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`/`validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, the existing `JsonStore`/`FindingStore` (`gpu_agent/store.py`), **every member of** `gpu_agent/wiki/store.py`/`log.py`/`page.py`/`ingest.py`/`lint.py`, and **the existing Part-37 ingest seam `gpu_agent/gathering/ingest.py` `normalize_documents`** (L1 runs *after* it, it is not modified).
- **Additive only** (Part 33): the new module `gpu_agent/gathering/dedup.py`; the `--dedup-store` flag on the `ingest` subcommand + the new `wiki-dedup` subcommand in `cli.py`; the gitignored runtime `seen_docs.jsonl` store artifact; the `gather-category`/`run-cycle` skill edits. Do NOT edit any committed fixture under `fixtures/`.
- **Doctrine:** numbers only from gated findings (the dedup reads structured `Finding`/`RawDocument` values, writes none — Part 17); nothing silent (every dropped-known doc + every DUPLICATE finding is counted and listed — Part 29); replayable (the seen-document index + snapshot + `DedupReport` — Part 20); the dedup **mutates no stored finding or page** (it classifies and routes; NEW/UPDATE ingest goes through the existing 4-4a writer).
- **Determinism:** no wall-clock; `as_of` is always passed in; re-running a cycle is a no-op (L1 drops every already-seen doc; L2 classifies every unchanged finding DUPLICATE).
- **The full suite stays green after every task.** Baseline: **332 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file guard** (Task 5 Step 6): the only `gpu_agent/` changes are the new `gathering/dedup.py` and the additive `cli.py` edits — every frozen file above stays byte-unchanged and no `fixtures/` file changes.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gpu_agent/gathering/dedup.py` | the dedup engine: models, `DedupConfig`, `SeenDocIndex`, L1 `filter_seen_documents`, L2 `classify_findings` | Create |
| `gpu_agent/cli.py` | CLI entry points | Modify: add `--dedup-store` to `ingest` (L1) + a `wiki-dedup` subparser/`_wiki_dedup` handler/dispatch (L2) |
| `.claude/skills/gather-category/SKILL.md` | the gather swarm | Modify: add a **daily mode** section + the numeric scrape sweep |
| `.claude/skills/run-cycle/SKILL.md` | the run coordinator | Modify: add the daily invocation path threading L1/L2 |
| `tests/test_dedup_models.py` | data models + `DedupConfig` defaults | Create |
| `tests/test_dedup_seen_docs.py` | `SeenDocIndex` + L1 filter | Create |
| `tests/test_dedup_vintage.py` | prior-vintage lookup + the change test | Create |
| `tests/test_dedup_classify.py` | L2 `classify_findings` | Create |
| `tests/test_dedup_cli.py` | L1 flag + `wiki-dedup` end-to-end + frozen guard | Create |

**Note on the module path:** the spec (§1) names the module `gpu_agent/gather/dedup.py`. This plan realizes it as **`gpu_agent/gathering/dedup.py`** — it lives in the *existing* `gpu_agent/gathering/` package that already holds `normalize_documents`, so no new package is introduced. (Same kind of keyword/existing-structure realization the 4-4b plan applied to `CrossRefGap`.)

**Note on the `DedupReport` split (spec §4):** the spec draws a single combined report with both doc-level (`docsSeen`/`docsDroppedKnown`) and finding-level fields. Because L1 (docs, pre-extract) and L2 (findings, post-gate) run at different pipeline stages via different CLI surfaces, this plan populates the **finding-level** fields in `DedupReport` (emitted by `wiki-dedup`) and folds L1's **doc-level** drop counts into the existing `ingest` **gather-log** (`droppedKnown`). `DedupReport` keeps an optional `docsDroppedKnown` field (default `[]`) so the model still matches §4's shape for a future combined report.

---

### Task 1: `dedup.py` — data models + `DedupConfig`

**Files:**
- Create: `gpu_agent/gathering/dedup.py`
- Test: `tests/test_dedup_models.py`

**Interfaces:**
- Produces (consumed by all later tasks): `DroppedDoc`, `FindingClass`, `DedupResult`, `DedupReport`, `DedupConfig`, `DEFAULT_DEDUP_CONFIG`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_dedup_models.py`:

```python
import json
from gpu_agent.gathering.dedup import (
    DroppedDoc, FindingClass, DedupResult, DedupReport, DedupConfig, DEFAULT_DEDUP_CONFIG)


def test_dedup_config_defaults():
    c = DEFAULT_DEDUP_CONFIG
    assert c.rel_tol == 0.01
    assert c.eps == 1e-9


def test_finding_class_and_result():
    r = DedupResult(
        new=[FindingClass(findingId="f-1", entity="NVDA", indicatorId="rpoBacklog", verdict="new")],
        update=[FindingClass(findingId="f-2", entity="AMD", indicatorId="gpuSpotPrice",
                             verdict="update", priorFindingId="f-0", detail="value 2.10 -> 2.35 (>1%)")],
        duplicate=[FindingClass(findingId="f-3", entity="INTC", indicatorId="S10",
                                verdict="duplicate", priorFindingId="f-prev",
                                detail="unchanged within tolerance")])
    assert [fc.findingId for fc in r.new] == ["f-1"]
    assert r.update[0].priorFindingId == "f-0"
    assert r.duplicate[0].verdict == "duplicate"


def test_dedup_report_roundtrip():
    report = DedupReport(
        asOf="2026-07",
        docsDroppedKnown=[DroppedDoc(url="http://x/a", reason="seen-url", firstSeenAsOf="2026-06")],
        findingsNew=[FindingClass(findingId="f-1", entity="NVDA", indicatorId="rpoBacklog", verdict="new")],
        findingsUpdate=[], findingsDuplicate=[])
    blob = json.loads(report.model_dump_json())
    assert blob["asOf"] == "2026-07"
    assert blob["docsDroppedKnown"][0]["reason"] == "seen-url"
    assert blob["findingsNew"][0]["entity"] == "NVDA"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.gathering.dedup'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/gathering/dedup.py`:

```python
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class DroppedDoc(BaseModel):
    url: str
    reason: str                    # "seen-url" | "seen-content-hash"
    firstSeenAsOf: str


class FindingClass(BaseModel):
    findingId: str
    entity: str
    indicatorId: str
    verdict: str                   # "new" | "update" | "duplicate"
    priorFindingId: Optional[str] = None
    detail: str = ""


class DedupResult(BaseModel):
    new: list[FindingClass] = Field(default_factory=list)
    update: list[FindingClass] = Field(default_factory=list)
    duplicate: list[FindingClass] = Field(default_factory=list)


class DedupReport(BaseModel):
    asOf: str
    docsDroppedKnown: list[DroppedDoc] = Field(default_factory=list)
    findingsNew: list[FindingClass] = Field(default_factory=list)
    findingsUpdate: list[FindingClass] = Field(default_factory=list)
    findingsDuplicate: list[FindingClass] = Field(default_factory=list)


class DedupConfig(BaseModel):
    rel_tol: float = 0.01          # relative tolerance for a measured-value change
    eps: float = 1e-9              # floor so a near-zero prior can't divide-by-zero


DEFAULT_DEDUP_CONFIG = DedupConfig()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_models.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 335 passed, 3 skipped (332 baseline + 3 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/gathering/dedup.py tests/test_dedup_models.py && git commit -m "feat(4-4d): dedup data models + DedupConfig

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `dedup.py` — `SeenDocIndex` + L1 `filter_seen_documents`

**Files:**
- Modify: `gpu_agent/gathering/dedup.py` (add the seen-document index + L1 filter)
- Test: `tests/test_dedup_seen_docs.py`

**Interfaces:**
- Consumes: `DroppedDoc` (Task 1); `RawDocument` (`gpu_agent.schema.raw_document` — fields `id`/`source`/`url`/`date`/`tier`/`entity`/`content`).
- Produces:
  - `content_hash(content: str) -> str` (sha256 of whitespace-folded content).
  - `SeenDocIndex(path)` with `.contains(url_norm, chash) -> Optional[tuple[str, str]]` (returns `(reason, firstSeenAsOf)` or `None`), `.record(url_norm, chash, as_of)`, persisted append-only JSONL.
  - `filter_seen_documents(docs, index, *, as_of) -> tuple[list[RawDocument], list[DroppedDoc]]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_dedup_seen_docs.py`:

```python
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.gathering.dedup import content_hash, SeenDocIndex, filter_seen_documents


def _doc(did, url, content="body text here", entity="NVDA"):
    return RawDocument(id=did, source="src", url=url, date="2026-07", tier="secondary",
                       entity=entity, content=content)


def test_content_hash_folds_whitespace():
    assert content_hash("a  b\n c") == content_hash("a b c")
    assert content_hash("a b c") != content_hash("a b d")


def test_index_persists_and_reloads(tmp_path):
    p = tmp_path / "seen_docs.jsonl"
    idx = SeenDocIndex(p)
    assert idx.contains("http://x/a", "h1") is None
    idx.record("http://x/a", "h1", "2026-06")
    # a fresh instance reads the persisted file
    idx2 = SeenDocIndex(p)
    hit = idx2.contains("http://x/a", "hZZ")
    assert hit == ("seen-url", "2026-06")
    hit2 = idx2.contains("http://other/z", "h1")
    assert hit2 == ("seen-content-hash", "2026-06")


def test_filter_drops_known_url(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    idx.record("http://x/a", "hA", "2026-06")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a"), _doc("d2", "http://x/b", content="fresh new content")],
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d2"]
    assert [(dd.url, dd.reason) for dd in dropped] == [("http://x/a", "seen-url")]


def test_filter_catches_same_content_new_url(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a", content="identical body"),
         _doc("d2", "http://y/b", content="identical  body")],  # same content, new url
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d1"]
    assert dropped[0].reason == "seen-content-hash"


def test_filter_records_survivors_for_next_run(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    filter_seen_documents([_doc("d1", "http://x/a")], idx, as_of="2026-07")
    survivors, dropped = filter_seen_documents([_doc("d1", "http://x/a")], idx, as_of="2026-08")
    assert survivors == [] and dropped[0].reason == "seen-url"
    assert dropped[0].firstSeenAsOf == "2026-07"  # first-seen, not the re-run cycle


def test_filter_dedups_within_batch(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a"), _doc("d2", "http://x/a")],  # same url twice in one batch
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d1"]
    assert dropped[0].reason == "seen-url"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_seen_docs.py -q`
Expected: FAIL with `ImportError: cannot import name 'content_hash'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/gathering/dedup.py`, add the imports at the top (after the existing ones):

```python
import hashlib
import json
import pathlib
from gpu_agent.gathering.ingest import _normalize_url
from gpu_agent.schema.raw_document import RawDocument
```

Add at the end of the module:

```python
def content_hash(content: str) -> str:
    """sha256 of the whitespace-folded content (so trivial reformatting still matches)."""
    folded = " ".join(content.split())
    return hashlib.sha256(folded.encode("utf-8")).hexdigest()


class SeenDocIndex:
    """Persistent, append-only cross-run memory of documents already ingested.
    Keyed by normalized URL AND content-hash -> first-seen asOf. Lives in the gitignored
    runtime store (e.g. store/seen_docs.jsonl)."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self._url: dict[str, str] = {}     # url_norm -> firstSeenAsOf
        self._hash: dict[str, str] = {}     # content_hash -> firstSeenAsOf
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                self._url.setdefault(rec["url"], rec["asOf"])
                self._hash.setdefault(rec["hash"], rec["asOf"])

    def contains(self, url_norm: str, chash: str):
        """Return (reason, firstSeenAsOf) if this doc is already known, else None. URL wins."""
        if url_norm in self._url:
            return ("seen-url", self._url[url_norm])
        if chash in self._hash:
            return ("seen-content-hash", self._hash[chash])
        return None

    def record(self, url_norm: str, chash: str, as_of: str) -> None:
        if url_norm in self._url and chash in self._hash:
            return
        self._url.setdefault(url_norm, as_of)
        self._hash.setdefault(chash, as_of)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"url": url_norm, "hash": chash, "asOf": as_of}) + "\n")


def filter_seen_documents(docs, index: SeenDocIndex, *, as_of):
    """L1: drop documents already in the seen index (or repeated within this batch); record
    survivors. Returns (survivors, dropped) — nothing silent (every drop is a DroppedDoc)."""
    survivors: list[RawDocument] = []
    dropped: list[DroppedDoc] = []
    for doc in docs:
        url_norm = _normalize_url(doc.url)
        chash = content_hash(doc.content)
        hit = index.contains(url_norm, chash)
        if hit is not None:
            reason, first_seen = hit
            dropped.append(DroppedDoc(url=doc.url, reason=reason, firstSeenAsOf=first_seen))
            continue
        index.record(url_norm, chash, as_of)
        survivors.append(doc)
    return survivors, dropped
```

(`filter_seen_documents` records each survivor immediately, so a second doc in the same batch with the same URL/content is dropped as `seen-url`/`seen-content-hash` against the just-recorded first — the within-batch dedup the test pins.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_seen_docs.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 341 passed, 3 skipped (335 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/gathering/dedup.py tests/test_dedup_seen_docs.py && git commit -m "feat(4-4d): SeenDocIndex + L1 pre-brain document dedup (URL + content-hash)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `dedup.py` — the prior-vintage lookup + the change test

**Files:**
- Modify: `gpu_agent/gathering/dedup.py` (add L2 helpers)
- Test: `tests/test_dedup_vintage.py`

**Interfaces:**
- Consumes: `DedupConfig` (Task 1); `WikiStore` (`observations`, `findings.get`), `PageNotFound` (`gpu_agent.wiki.store`); `slug` (`gpu_agent.wiki.ingest`); `Finding` (`value.number`, `magnitude`, `statement`, `trend`, `indicatorId`, `capturedAt`, `observedAt`).
- Produces:
  - `_norm_statement(s: str) -> str`.
  - `prior_vintage(store, entity: str, indicator_id: str)` -> `Optional[Finding]` (latest by `(capturedAt, observedAt, magnitude)` among the entity page's observations with that indicator; `None` if the page or indicator is absent).
  - `changed(prior, fresh, config) -> bool` and `delta_detail(prior, fresh, config) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_dedup_vintage.py`:

```python
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.gathering.dedup import (prior_vintage, changed, DEFAULT_DEDUP_CONFIG)
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId, *, number=None, magnitude=2, statement="s", trend="flat",
       capturedAt="2026-07-01", observedAt="2026-07"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend=trend, why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=(Value(number=number, unit="usd") if number is not None else None),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt=observedAt, capturedAt=capturedAt)


def _seed(store, f, as_of):
    store.create_page(f"entity:{f.entity.lower()}", "entity", f.entity, as_of=as_of) \
        if not _page_exists(store, f.entity) else None
    store.findings.append(f)
    store.append_observation(f"entity:{f.entity.lower()}", f.id, as_of=as_of)


def _page_exists(store, entity):
    from gpu_agent.wiki.store import PageNotFound
    try:
        store.get_page(f"entity:{entity.lower()}")
        return True
    except PageNotFound:
        return False


def test_prior_vintage_none_when_absent(tmp_path):
    store = _store(tmp_path)
    assert prior_vintage(store, "NVDA", "rpoBacklog") is None


def test_prior_vintage_picks_latest(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f-old", "NVDA", "rpoBacklog", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f-new", "NVDA", "rpoBacklog", capturedAt="2026-07-01"), "2026-07")
    _seed(store, _f("f-other", "NVDA", "leadTimes", capturedAt="2026-07-01"), "2026-07")
    pv = prior_vintage(store, "NVDA", "rpoBacklog")
    assert pv.id == "f-new"  # latest capturedAt for THIS indicator, ignores leadTimes


def test_changed_measured_within_tolerance_is_false():
    prior = _f("f0", "AMD", "gpuSpotPrice", number=2.00)
    fresh = _f("f1", "AMD", "gpuSpotPrice", number=2.015)  # +0.75% < 1%
    assert changed(prior, fresh, DEFAULT_DEDUP_CONFIG) is False


def test_changed_measured_beyond_tolerance_is_true():
    prior = _f("f0", "AMD", "gpuSpotPrice", number=2.00)
    fresh = _f("f1", "AMD", "gpuSpotPrice", number=2.35)  # +17.5% > 1%
    assert changed(prior, fresh, DEFAULT_DEDUP_CONFIG) is True


def test_changed_magnitude_flip_is_true():
    prior = _f("f0", "AMD", "gpuSpotPrice", number=2.00, magnitude=1)
    fresh = _f("f1", "AMD", "gpuSpotPrice", number=2.00, magnitude=3)
    assert changed(prior, fresh, DEFAULT_DEDUP_CONFIG) is True


def test_changed_qualitative_statement_or_trend():
    prior = _f("f0", "NVDA", "rpoBacklog", statement="Backlog steady", trend="flat")
    same = _f("f1", "NVDA", "rpoBacklog", statement="backlog   steady", trend="flat")  # folds equal
    diff = _f("f2", "NVDA", "rpoBacklog", statement="Backlog steady", trend="rising")
    assert changed(prior, same, DEFAULT_DEDUP_CONFIG) is False
    assert changed(prior, diff, DEFAULT_DEDUP_CONFIG) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_vintage.py -q`
Expected: FAIL with `ImportError: cannot import name 'prior_vintage'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/gathering/dedup.py`, add these imports at the top (after the existing ones):

```python
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.ingest import slug
```

Add at the end of the module:

```python
def _norm_statement(s: str) -> str:
    return " ".join((s or "").split()).lower()


def prior_vintage(store, entity: str, indicator_id: str):
    """The store's latest-vintage Finding for (entity, indicatorId), read through the entity page's
    observations (FindingStore has no iteration). Latest by (capturedAt, observedAt, magnitude) —
    the same collapse the frozen dmi_smi_contribution uses. None if the page/indicator is absent."""
    pid = f"entity:{slug(entity)}"
    try:
        obs = store.observations(pid)
    except PageNotFound:
        return None
    cands = []
    for o in obs:
        try:
            f = store.findings.get(o.findingId)
        except Exception:
            continue
        if f.indicatorId == indicator_id:
            cands.append(f)
    if not cands:
        return None
    return max(cands, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude))


def changed(prior, fresh, config=DEFAULT_DEDUP_CONFIG) -> bool:
    """UPDATE vs DUPLICATE. Measured: value delta beyond rel_tol OR magnitude change. Qualitative:
    a value appearing/disappearing, or a normalized-statement / trend / magnitude change."""
    pv = prior.value.number if prior.value is not None else None
    fv = fresh.value.number if fresh.value is not None else None
    if pv is not None and fv is not None:
        if abs(fv - pv) > config.rel_tol * max(abs(pv), config.eps):
            return True
        return fresh.magnitude != prior.magnitude
    if (pv is None) != (fv is None):
        return True  # a measured value appeared or disappeared
    return (_norm_statement(fresh.statement) != _norm_statement(prior.statement)
            or fresh.trend != prior.trend
            or fresh.magnitude != prior.magnitude)


def delta_detail(prior, fresh, config=DEFAULT_DEDUP_CONFIG) -> str:
    pv = prior.value.number if prior.value is not None else None
    fv = fresh.value.number if fresh.value is not None else None
    if pv is not None and fv is not None:
        return f"value {pv} -> {fv} (tol {config.rel_tol:.0%})"
    if fresh.magnitude != prior.magnitude:
        return f"magnitude {prior.magnitude} -> {fresh.magnitude}"
    return f"statement/trend changed (trend {prior.trend} -> {fresh.trend})"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_vintage.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 347 passed, 3 skipped (341 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/gathering/dedup.py tests/test_dedup_vintage.py && git commit -m "feat(4-4d): prior-vintage lookup (via entity-page observations) + tolerance change test

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `dedup.py` — L2 `classify_findings` (NEW/UPDATE/DUPLICATE + intra-batch collapse)

**Files:**
- Modify: `gpu_agent/gathering/dedup.py` (add the classifier)
- Test: `tests/test_dedup_classify.py`

**Interfaces:**
- Consumes: Task 1 models, Task 3 helpers (`prior_vintage`, `changed`, `delta_detail`); `Finding`.
- Produces: `classify_findings(findings, store, *, config=DEFAULT_DEDUP_CONFIG) -> DedupResult` (intra-batch collapse to latest vintage per `(entity, indicatorId)`; classify the representative vs the store; superseded batch-mates are DUPLICATE; lists ordered by `(entity, indicatorId)` then finding id).

- [ ] **Step 1: Write the failing test**

Create `tests/test_dedup_classify.py`:

```python
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.gathering.dedup import classify_findings, DEFAULT_DEDUP_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId, *, number=None, magnitude=2, statement="s",
       capturedAt="2026-07-01"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=(Value(number=number, unit="usd") if number is not None else None),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-07", capturedAt=capturedAt)


def _seed(store, f, as_of):
    pid = f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_classify_new_when_no_prior(tmp_path):
    store = _store(tmp_path)
    res = classify_findings([_f("f-1", "NVDA", "rpoBacklog", number=100.0)], store,
                            config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.new] == ["f-1"]
    assert res.update == [] and res.duplicate == []


def test_classify_update_and_duplicate(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f-price0", "AMD", "gpuSpotPrice", number=2.00, capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f-rpo0", "NVDA", "rpoBacklog", number=100.0, capturedAt="2026-06-01"), "2026-06")
    res = classify_findings([
        _f("f-price1", "AMD", "gpuSpotPrice", number=2.35, capturedAt="2026-07-01"),   # +17% -> update
        _f("f-rpo1", "NVDA", "rpoBacklog", number=100.5, capturedAt="2026-07-01")],     # +0.5% -> duplicate
        store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.update] == ["f-price1"]
    assert res.update[0].priorFindingId == "f-price0"
    assert [fc.findingId for fc in res.duplicate] == ["f-rpo1"]


def test_classify_intra_batch_collapse(tmp_path):
    store = _store(tmp_path)
    # two fresh findings, same (entity, indicator); the later capturedAt is the representative
    res = classify_findings([
        _f("f-a", "NVDA", "rpoBacklog", number=100.0, capturedAt="2026-07-01"),
        _f("f-b", "NVDA", "rpoBacklog", number=105.0, capturedAt="2026-07-02")],
        store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.new] == ["f-b"]         # latest vintage -> NEW
    assert [fc.findingId for fc in res.duplicate] == ["f-a"]   # superseded by intra-batch latest
    assert "superseded" in res.duplicate[0].detail


def test_classify_idempotent_rerun_all_duplicate(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f-0", "INTC", "S10", number=5.0, capturedAt="2026-06-01"), "2026-06")
    res = classify_findings([_f("f-0-again", "INTC", "S10", number=5.0, capturedAt="2026-06-01")],
                            store, config=DEFAULT_DEDUP_CONFIG)
    assert res.new == [] and res.update == []
    assert [fc.verdict for fc in res.duplicate] == ["duplicate"]


def test_classify_counts_cover_input(tmp_path):
    store = _store(tmp_path)
    findings = [_f("f-1", "NVDA", "rpoBacklog", number=1.0),
                _f("f-2", "AMD", "gpuSpotPrice", number=2.0),
                _f("f-3", "INTC", "S10", number=3.0)]
    res = classify_findings(findings, store, config=DEFAULT_DEDUP_CONFIG)
    assert len(res.new) + len(res.update) + len(res.duplicate) == 3


def test_classify_deterministic_order(tmp_path):
    store = _store(tmp_path)
    res = classify_findings([_f("f-z", "ZULU", "S10", number=1.0),
                             _f("f-a", "ALPHA", "rpoBacklog", number=1.0)],
                            store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.entity for fc in res.new] == ["ALPHA", "ZULU"]  # sorted by (entity, indicatorId)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_classify.py -q`
Expected: FAIL with `ImportError: cannot import name 'classify_findings'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/gathering/dedup.py`, add at the end of the module:

```python
def classify_findings(findings, store, *, config=DEFAULT_DEDUP_CONFIG) -> DedupResult:
    """L2: partition this cycle's gated findings into NEW / UPDATE / DUPLICATE vs the store's latest
    vintage per (entity, indicatorId). Findings sharing a key are first collapsed to their own latest
    vintage (same tie-break); superseded batch-mates are DUPLICATE. Nothing silent."""
    by_key: dict[tuple[str, str], list] = {}
    for f in findings:
        by_key.setdefault((f.entity, f.indicatorId), []).append(f)

    result = DedupResult()
    for (entity, ind), group in sorted(by_key.items()):
        ordered = sorted(group, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude), reverse=True)
        rep, superseded = ordered[0], ordered[1:]
        prior = prior_vintage(store, entity, ind)
        if prior is None:
            result.new.append(FindingClass(findingId=rep.id, entity=entity, indicatorId=ind,
                                           verdict="new"))
        elif changed(prior, rep, config):
            result.update.append(FindingClass(findingId=rep.id, entity=entity, indicatorId=ind,
                                              verdict="update", priorFindingId=prior.id,
                                              detail=delta_detail(prior, rep, config)))
        else:
            result.duplicate.append(FindingClass(findingId=rep.id, entity=entity, indicatorId=ind,
                                                verdict="duplicate", priorFindingId=prior.id,
                                                detail="unchanged within tolerance"))
        for s in superseded:
            result.duplicate.append(FindingClass(findingId=s.id, entity=entity, indicatorId=ind,
                                                verdict="duplicate",
                                                detail="superseded by intra-batch latest vintage"))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_classify.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 353 passed, 3 skipped (347 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/gathering/dedup.py tests/test_dedup_classify.py && git commit -m "feat(4-4d): L2 classify_findings — NEW/UPDATE/DUPLICATE + intra-batch collapse

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: CLI wiring — L1 `ingest --dedup-store` + the `wiki-dedup` subcommand + frozen guard

**Files:**
- Modify: `gpu_agent/cli.py` (add `--dedup-store` to `ingest`; add the `wiki-dedup` subparser + `_wiki_dedup` handler + dispatch)
- Test: `tests/test_dedup_cli.py`

**Interfaces:**
- Consumes: `filter_seen_documents`/`SeenDocIndex` (Task 2), `classify_findings` (Task 4), `DedupReport`/`FindingClass` (Task 1); the existing `normalize_documents`, `WikiStore`/`FindingStore`, `Finding`, `route_findings` in `cli.py`.
- Produces:
  - `ingest --dedup-store DIR` — after `normalize_documents`, L1-filters the docs (writes only survivors; folds `droppedKnown` into the gather-log; prints dropped-known to stderr).
  - `wiki-dedup --findings F --store DIR --as-of D [--out-findings G] [--report R]` — L2-classifies; writes NEW+UPDATE findings to `--out-findings` (default: overwrite nothing, just report); emits the `DedupReport` JSON to `--report`/stdout.

- [ ] **Step 1: Write the failing test**

Create `tests/test_dedup_cli.py`:

```python
import json
import pytest
from gpu_agent.cli import main
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings


def _blob(url, content="body", entity="NVDA"):
    return {"url": url, "content": content, "source": "example.com", "date": "2026-07",
            "entity": entity}


def _f(fid, entity, indicatorId, number, capturedAt="2026-07-01"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=Value(number=number, unit="usd"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-07", capturedAt=capturedAt)


def test_ingest_dedup_store_drops_known_docs(tmp_path, capsys):
    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([_blob("http://x/a"), _blob("http://x/b", content="two")]), "utf-8")
    store = tmp_path / "store"
    out1 = tmp_path / "out1"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out1),
               "--primary-sources", "sec.gov", "--dedup-store", str(store)])
    assert rc == 0
    log1 = json.loads((out1 / "gather-log.json").read_text("utf-8"))
    assert log1["documents"] == 2 and log1.get("droppedKnown", 0) == 0
    # second run over the SAME blobs -> both already seen -> 0 documents written, 2 droppedKnown
    capsys.readouterr()
    out2 = tmp_path / "out2"
    main(["ingest", "--blobs", str(blobs), "--out", str(out2),
          "--primary-sources", "sec.gov", "--dedup-store", str(store)])
    log2 = json.loads((out2 / "gather-log.json").read_text("utf-8"))
    assert log2["documents"] == 0 and log2["droppedKnown"] == 2


def test_ingest_without_dedup_store_unchanged(tmp_path):
    # the flag is opt-in: absent -> the existing behavior (both docs written), no dedup
    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([_blob("http://x/a"), _blob("http://x/b", content="two")]), "utf-8")
    out = tmp_path / "out"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out), "--primary-sources", "sec.gov"])
    assert rc == 0
    log = json.loads((out / "gather-log.json").read_text("utf-8"))
    assert log["documents"] == 2 and "droppedKnown" not in log


def _seed_store(root):
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    route_findings(store, [_f("f-price0", "AMD", "gpuSpotPrice", 2.00, capturedAt="2026-06-01")],
                   as_of="2026-06")
    return store


def test_wiki_dedup_reports_and_writes_deduped(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_store(root)
    findings = tmp_path / "fresh.json"
    findings.write_text(json.dumps([
        _f("f-price1", "AMD", "gpuSpotPrice", 2.35).model_dump(),   # update
        _f("f-price1b", "AMD", "gpuSpotPrice", 2.34).model_dump(),  # same key -> superseded dup
        _f("f-new", "NVDA", "rpoBacklog", 100.0).model_dump()]),    # new
        "utf-8")
    deduped = tmp_path / "deduped.json"
    rc = main(["wiki-dedup", "--findings", str(findings), "--store", str(root),
               "--as-of", "2026-07", "--out-findings", str(deduped)])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert [fc["findingId"] for fc in report["findingsNew"]] == ["f-new"]
    assert [fc["findingId"] for fc in report["findingsUpdate"]] == ["f-price1"]
    assert {fc["findingId"] for fc in report["findingsDuplicate"]} == {"f-price1b"}
    kept = {d["id"] for d in json.loads(deduped.read_text("utf-8"))}
    assert kept == {"f-new", "f-price1"}  # NEW + UPDATE only


def test_wiki_dedup_rerun_all_duplicate(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_store(root)
    findings = tmp_path / "same.json"
    findings.write_text(json.dumps([_f("f-price0-again", "AMD", "gpuSpotPrice", 2.00).model_dump()]),
                        "utf-8")
    main(["wiki-dedup", "--findings", str(findings), "--store", str(root), "--as-of", "2026-07"])
    report = json.loads(capsys.readouterr().out)
    assert report["findingsNew"] == [] and report["findingsUpdate"] == []
    assert len(report["findingsDuplicate"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_cli.py -q`
Expected: FAIL (`error: unrecognized arguments: --dedup-store` / `invalid choice: 'wiki-dedup'`).

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/cli.py`, add the import near the other gathering/wiki imports:

```python
from gpu_agent.gathering.dedup import (
    SeenDocIndex, filter_seen_documents, classify_findings, DedupReport)
```

In the `_ingest` handler, replace the block that writes documents + builds the log. Change:

```python
    outcome = normalize_documents(blobs, primary_sources=primary_sources)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for doc in outcome.documents:
        (out / f"{doc.id}.json").write_text(json.dumps(doc.model_dump(), indent=2), "utf-8")
    n_primary = sum(1 for d in outcome.documents if d.tier == "primary")
    log = {
        "rounds": rounds,
        "documents": len(outcome.documents),
        "primary": n_primary,
        "secondary": len(outcome.documents) - n_primary,
        "duplicates": outcome.duplicates,
        "dropped": [d.model_dump() for d in outcome.dropped],
        "skipped": skipped,
    }
```

with:

```python
    outcome = normalize_documents(blobs, primary_sources=primary_sources)
    docs = outcome.documents
    dropped_known = []
    if getattr(args, "dedup_store", None):
        index = SeenDocIndex(pathlib.Path(args.dedup_store) / "seen_docs.jsonl")
        docs, dropped_known = filter_seen_documents(docs, index, as_of=args.as_of)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        (out / f"{doc.id}.json").write_text(json.dumps(doc.model_dump(), indent=2), "utf-8")
    n_primary = sum(1 for d in docs if d.tier == "primary")
    log = {
        "rounds": rounds,
        "documents": len(docs),
        "primary": n_primary,
        "secondary": len(docs) - n_primary,
        "duplicates": outcome.duplicates,
        "dropped": [d.model_dump() for d in outcome.dropped],
        "skipped": skipped,
    }
    if getattr(args, "dedup_store", None):
        log["droppedKnown"] = len(dropped_known)
        log["droppedKnownDetail"] = [d.model_dump() for d in dropped_known]
```

Update the two trailing lines of `_ingest` that reference `outcome.documents` to use `docs`, and print dropped-known to stderr. Change:

```python
    print(f"ingested {len(outcome.documents)} docs "
          f"({outcome.duplicates} dup, {len(outcome.dropped)} dropped) -> {out}")
    return 0
```

with:

```python
    for d in dropped_known:
        print(f"DROPPED-KNOWN {d.url}: {d.reason} (first seen {d.firstSeenAsOf})", file=sys.stderr)
    print(f"ingested {len(docs)} docs "
          f"({outcome.duplicates} dup, {len(outcome.dropped)} dropped, "
          f"{len(dropped_known)} known) -> {out}")
    return 0
```

(The `for doc in outcome.dropped: print(... DROPPED ...)` loop just above stays unchanged.)

Add the `_wiki_dedup` handler after `_wiki_ingest`:

```python
def _wiki_dedup(args) -> int:
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    result = classify_findings(findings, store)
    report = DedupReport(asOf=args.as_of, findingsNew=result.new,
                         findingsUpdate=result.update, findingsDuplicate=result.duplicate)
    if args.out_findings:
        keep = {fc.findingId for fc in result.new + result.update}
        deduped = [f.model_dump() for f in findings if f.id in keep]
        pathlib.Path(args.out_findings).write_text(json.dumps(deduped, indent=2), "utf-8")
    payload = report.model_dump_json(indent=2)
    if args.report:
        pathlib.Path(args.report).write_text(payload, "utf-8")
        print(f"wrote {args.report}  (new {len(result.new)}, update {len(result.update)}, "
              f"duplicate {len(result.duplicate)})")
    else:
        print(payload)
    return 0
```

Register the subparser inside `main()` after the `wiki-ingest` (`wi`) block:

```python
    wd = sub.add_parser("wiki-dedup")
    wd.add_argument("--findings", required=True, help="JSON array of gated Findings (this cycle)")
    wd.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wd.add_argument("--as-of", required=True)
    wd.add_argument("--out-findings", default=None,
                    help="write the deduped NEW+UPDATE findings JSON here (for wiki-ingest)")
    wd.add_argument("--report", default=None, help="write the DedupReport JSON here (else stdout)")
```

Add `--dedup-store` AND `--as-of` to the existing `ingest` (`ig`) subparser. The current `ig` block defines exactly `--blobs` (required), `--out` (required), `--primary-sources` (default `"sec.gov"`) and has **no `--as-of`** — add both new lines next to those:

```python
    ig.add_argument("--as-of", default="",
                    help="cycle asOf stamped as first-seen in the L1 dedup index")
    ig.add_argument("--dedup-store", default=None,
                    help="store root for cross-run L1 seen-document dedup (holds seen_docs.jsonl)")
```

(L1 tolerates an empty `--as-of`; it is only stamped into the index as the first-seen cycle. The daily `run-cycle` path in Task 6 passes the real cycle date.)

Add the dispatch next to the other `if args.cmd == ...` checks:

```python
    if args.cmd == "wiki-dedup":
        return _wiki_dedup(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_dedup_cli.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 357 passed, 3 skipped (353 + 4 new).

- [ ] **Step 6: Run the frozen guards**

Run: `cd /c/Users/danie/random_for_fun && git diff --stat main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/pipeline.py gpu_agent/store.py gpu_agent/wiki/store.py gpu_agent/wiki/log.py gpu_agent/wiki/page.py gpu_agent/wiki/ingest.py gpu_agent/wiki/lint.py gpu_agent/gathering/ingest.py`
Expected: **no output** (every frozen file byte-unchanged; the only `gpu_agent/` changes are the new `gathering/dedup.py` and the additive `cli.py` edits).

Run: `cd /c/Users/danie/random_for_fun && git diff main -- fixtures/`
Expected: **no output** (no committed fixture changed).

- [ ] **Step 7: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/cli.py tests/test_dedup_cli.py && git commit -m "feat(4-4d): CLI wiring — ingest --dedup-store (L1) + wiki-dedup subcommand (L2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Skill edits — daily gather mode + numeric scrape sweep (session-run, dry-run validated)

**This task is executed by the orchestrating SESSION, not a code implementer** (skills are session-run and validated by documented dry-runs, not pytest — like sp2 Task 3 and sp3-A Task 10). No pytest count changes (stays 357 passed, 3 skipped).

**Files:**
- Modify: `.claude/skills/gather-category/SKILL.md`
- Modify: `.claude/skills/run-cycle/SKILL.md`

**Interfaces:**
- Consumes: the `ingest --dedup-store` (L1) + `wiki-dedup` (L2) CLI seams from Task 5; the 4-2 `cadenceHorizon` tags + `sourceInventory`; the existing Part-37 follow-the-trail loop.

- [ ] **Step 1: Add a "daily mode" section to `gather-category/SKILL.md`**

Add an additive section (do not rewrite existing sections) that specifies daily mode:
- **Recency window:** seed searches + the on-topic filter bias to the last *N* days (a dial; default e.g. 7); the daily sweep looks for "what's new," not a full re-crawl.
- **Cadence prioritization:** prioritize indicators tagged `daily`/`weekly` in `cadenceHorizon` (read via `registry/horizon.py`) + recent news + the permissive numeric-scrape sources.
- **Numeric scrape sweep:** the permissive daily sources (e.g. GPU marketplaces for `gpuSpotPrice`, from `sourceInventory`) are ordinary gatherer targets — snapshot the page as a `RawDocument`; the FROZEN `extract → gate` produces the measured Finding (value + receipt, secondary tier, confidence-capped). **Part 22 (hard):** paywalled/licensed sources (SemiAnalysis, TrendForce) are labeled `estimate` and **NEVER fetched** — log them as a coverage gap (as C's manifest-driven gather already does).
- **Bounded:** the four Part-37 caps tuned smaller for daily; **every cap that truncates is logged with what it skipped** (Part 29).
- **Dedup wiring:** the daily flow runs `ingest --dedup-store <store>` (L1, drops cross-run-known docs) before extraction, and `wiki-dedup` (L2, NEW/UPDATE → `--out-findings`; DUPLICATE logged) before `wiki-ingest`.

- [ ] **Step 2: Add the daily invocation path to `run-cycle/SKILL.md`**

Add an additive section: a **daily** run threads the L1/L2 dedup steps into the pipeline (`ingest --dedup-store` → extract → gate → `wiki-dedup --out-findings deduped.json` → `wiki-ingest --findings deduped.json` → `wiki-lint`), and reports the `DedupReport` counts + the gather-log `droppedKnown`. Preserve the existing (non-daily) path unchanged.

- [ ] **Step 3: Documented dry-run (no pytest)**

Run a recorded/dry documented walkthrough proving: (a) daily mode restricts to the recency window + cadence-prioritized sources; (b) the numeric scrape fetches only permissive sources and logs paywalled sources as gaps (never fetched); (c) L1 drops a re-seen document and L2 classifies an unchanged daily price as DUPLICATE; (d) caps/skips are logged. Capture the walkthrough in `.superpowers/sdd/task-6-report.md`.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add .claude/skills/gather-category/SKILL.md .claude/skills/run-cycle/SKILL.md && git commit -m "feat(4-4d): daily gather mode + numeric scrape sweep (skill edits; Part 22 honest)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-07-01-daily-gather-scrape-dedup-design.md`):
- §1 dedup engine module (`filter_seen_documents` L1 + `classify_findings` L2 + `DedupReport`) → Tasks 2, 4, 1. ✓
- §2 L1 seen-document index (URL + content-hash → first-seen asOf; pre-brain; persistent; idempotent) → Task 2. ✓
- §3 L2 finding-level NEW/UPDATE/DUPLICATE (prior vintage via entity-page observations; latest-vintage tie-break; intra-batch collapse) → Tasks 3, 4. ✓
- §3.1 tolerance-based change test (`rel_tol` 1%; magnitude; qualitative statement/trend) + `DedupConfig` → Tasks 1, 3. ✓
- §4 `DedupReport` (nothing silent; the doc/finding split reconciliation noted) → Tasks 1, 5. ✓
- §5 CLI wiring at the two seams (L1 `ingest --dedup-store`; L2 `wiki-dedup`) additive → Task 5. ✓
- §6 daily gather mode (recency window, cadence-prioritized, caps logged) → Task 6. ✓
- §7 numeric scrape (gatherer snapshot → frozen extract→gate; Part 22 paywalled never fetched) → Task 6. ✓
- §8 frozen/additive boundary (incl. `normalize_documents` + all wiki modules byte-unchanged) → Task 5 Step 6 guards. ✓
- §9 doctrine (numbers only from gated findings; replayable; nothing silent; no lifecycle mutation) → Tasks 2/4/5. ✓
- §10 4-4d→4-4c seam (de-noised stream + NEW candidates; no theme pages/lifecycle) → Task 4 (NEW partition) + Task 6 (skill). ✓
- §11 test strategy → every task's tests + Task 6 dry-run. ✓
- §13 acceptance items 1–6 all map to the tasks above. ✓

**Placeholder scan:** none — every code step has complete code; Task 6 is prose-by-design (a skill task, session-run, dry-run validated, mirroring sp2/sp3 skill tasks).

**Type consistency:** `DedupConfig`/models (Task 1) are imported and used with matching field names by Tasks 2–5. `content_hash`/`SeenDocIndex`/`filter_seen_documents` (Task 2) are called by the `ingest` handler (Task 5) with the exact signatures. `prior_vintage(store, entity, indicator_id)` + `changed(prior, fresh, config)` + `delta_detail` (Task 3) are called by `classify_findings` (Task 4). `classify_findings(findings, store, *, config)` (Task 4) is called by `_wiki_dedup` (Task 5) and returns `DedupResult(new, update, duplicate)`, wrapped into `DedupReport(asOf, findingsNew, findingsUpdate, findingsDuplicate)`. `_normalize_url`/`RawDocument` reuse the frozen `gathering/ingest.py`/`schema/raw_document.py`; `slug`/`observations`/`findings.get`/`PageNotFound` reuse the frozen wiki APIs. ✓

**Controller-confirmed (Task 5):** the current `ingest` (`ig`) subparser defines exactly `--blobs`, `--out`, `--primary-sources` (verified against `cli.py` at plan time) — Task 5 adds `--dedup-store` and `--as-of` to it, and leaves every other subcommand's arguments untouched. The `_ingest` edit is additive/behavior-preserving: absent `--dedup-store` → byte-identical output (both docs written, no `droppedKnown` key), which Task 5's `test_ingest_without_dedup_store_unchanged` pins.

**Test-count math:** baseline 332 → +3 (Task 1) → +6 (Task 2) → +6 (Task 3) → +6 (Task 4) → +4 (Task 5) → +0 (Task 6, skill) = **357 passed, 3 skipped** at the end.
