# Brain ingest into the wiki (sub-project 4-4a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the keystone wiki *writer* — a `wiki-ingest` CLI command that routes the day's gated findings to entity pages (deterministic Phase 1) and lets the brain curate those pages (Phase 2 via the `--emit-prompt`→`--recorded` seam) — all additive, with the frozen contract and the existing 4-1 wiki API byte-unchanged.

**Architecture:** Phase 1 (code) routes each gated finding to `entity:<slug(finding.entity)>`, auto-creating the page and appending an observation idempotently. Phase 2 (brain) enriches *existing* entity pages: prose body, state/trajectory/salience, crossRefs, contradiction notes, applied deterministically through a validated `IngestResult`. A new additive `WikiStore.set_body` writes the curated body; everything else reuses the 4-1 store API.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), stdlib `re`/`json`/`pathlib`, pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset on Windows — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`/`validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, the existing `JsonStore`, and **every existing member of `gpu_agent/wiki/store.py` / `log.py` / `page.py` and `gpu_agent/store.py` `FindingStore`** (4-4a only *adds* `WikiStore.set_body`).
- **Additive only** (Part 33): `WikiStore.set_body`; a new module `gpu_agent/wiki/ingest.py`; a new `wiki-ingest` CLI subcommand. Do NOT edit any committed fixture under `fixtures/` (new fixtures are fine).
- **Doctrine:** every finding is gated through `FindingStore` before it lands (numbers only from gated findings, Part 17); the brain curates prose/state but invents no measured values; the `ingest` log event + idempotent re-runs make every day replayable (Part 20); nothing silent — an unroutable finding (empty `entity`) and a brain op targeting a missing/non-entity page both fail loud (Part 29).
- **Determinism:** no wall-clock; `as_of` is always passed in; re-running a day is a no-op.
- **The full suite stays green after every task.** Baseline: **282 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file guard:** while on the feature branch (before merge), the only `gpu_agent/` change outside the new `wiki/ingest.py` and `cli.py` is the added `WikiStore.set_body` in `gpu_agent/wiki/store.py`. The frozen files — including `gpu_agent/store.py` (`FindingStore`), `gpu_agent/wiki/log.py`, and `gpu_agent/wiki/page.py` — stay byte-unchanged, and no committed `fixtures/golden/` file changes. See Task 4 Step 5 for the exact `git diff` guards.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gpu_agent/wiki/store.py` | wiki page persistence | Modify: add `set_body` (additive; existing members untouched) |
| `gpu_agent/wiki/ingest.py` | the ingest writer: slug, models, Phase-1 router, Phase-2 bundle + applier, `INGEST_SYSTEM` | Create |
| `gpu_agent/cli.py` | CLI entry points | Modify: add `wiki-ingest` subparser + `_wiki_ingest` handler |
| `tests/test_wiki_set_body.py` | the new store method | Create |
| `tests/test_wiki_ingest_phase1.py` | slug + Phase-1 routing + bundle | Create |
| `tests/test_wiki_ingest_apply.py` | Phase-2 applier | Create |
| `tests/test_wiki_ingest_cli.py` | the CLI subcommand end-to-end | Create |
| `fixtures/recorded/ingest-merchant-gpu.json` | a recorded `IngestResult` for the CLI integration test | Create |

---

### Task 1: `WikiStore.set_body` — additive body writer

**Files:**
- Modify: `gpu_agent/wiki/store.py` (add one method; leave all existing members untouched)
- Test: `tests/test_wiki_set_body.py`

**Interfaces:**
- Consumes: existing `WikiStore._read`/`_write` (private helpers), `WikiPage`, `PageNotFound`.
- Produces: `WikiStore.set_body(self, page_id, body, *, as_of) -> WikiPage` — replaces the page's markdown body, bumps `lastUpdatedAsOf`; if the body is unchanged, returns the page WITHOUT writing or bumping (idempotent); raises `PageNotFound` if the page is absent. No log event.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_set_body.py`:

```python
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def test_set_body_replaces_body_and_bumps_as_of(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-26", body="old")
    ws.set_body("entity:nvda", "## NVDA\nnew prose [f-1].\n", as_of="2026-06-28")
    page = ws.get_page("entity:nvda")
    win = ws.window("entity:nvda", 0)
    assert win.body == "## NVDA\nnew prose [f-1].\n"
    assert page.lastUpdatedAsOf == "2026-06-28"
    assert page.title == "NVDA"  # header otherwise intact


def test_set_body_unchanged_is_skipped(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-26", body="same")
    ws.set_body("entity:nvda", "same", as_of="2026-06-28")
    page = ws.get_page("entity:nvda")
    assert page.lastUpdatedAsOf == "2026-06-26"  # no bump: body unchanged


def test_set_body_missing_page_raises(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(PageNotFound):
        ws.set_body("entity:nope", "x", as_of="2026-06-28")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_set_body.py -q`
Expected: FAIL with `AttributeError: 'WikiStore' object has no attribute 'set_body'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/store.py`, add this method to `WikiStore` immediately after `record_state` (before `log_append`):

```python
    def set_body(self, page_id, body, *, as_of) -> WikiPage:
        """Replace a page's curated markdown body, bumping lastUpdatedAsOf. Idempotent:
        an unchanged body is not rewritten. Raises PageNotFound. No log event (body edits
        are not temporal observations; the ingest run's event covers them)."""
        page, current_body = self._read(page_id)
        if body == current_body:
            return page
        page = page.model_copy(update={"lastUpdatedAsOf": as_of})
        self._write(page, body)
        return page
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_set_body.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 285 passed, 3 skipped (282 baseline + 3 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/store.py tests/test_wiki_set_body.py && git commit -m "feat(4-4a): WikiStore.set_body — additive curated-body writer (idempotent)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `wiki/ingest.py` — slug, models, Phase-1 router, Phase-2 bundle

**Files:**
- Create: `gpu_agent/wiki/ingest.py`
- Test: `tests/test_wiki_ingest_phase1.py`

**Interfaces:**
- Consumes: `Finding` (frozen schema; fields used: `id, entity, statement, why, impact, evidence`), `WikiStore` (`get_page`, `create_page`, `append_observation`, `observations`, `window`, `findings`), `FindingStore.append`, `PageNotFound`.
- Produces:
  - `def slug(entity: str) -> str` (lowercase; non-`[a-z0-9]+` runs → `-`; strip leading/trailing `-`; raises `ValueError` if the result is empty).
  - `class PageEnrichment(BaseModel)`: `pageId: str`, `bodyMarkdown: str`, `state: str`, `trajectory: str`, `salience: float`, `crossRefs: list[str] = []`, `contradictsThesis: bool = False`, `contradictionNote: str = ""`.
  - `class IngestResult(BaseModel)`: `pages: list[PageEnrichment]`.
  - `INGEST_SYSTEM: str` (the brain curation prompt).
  - `def route_findings(store, findings, *, as_of, category=None) -> list[str]` (Phase 1; returns sorted touched page ids).
  - `def build_bundle(store, findings, touched, *, as_of) -> dict` (Phase-2 emit bundle).

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_ingest_phase1.py`:

```python
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import slug, route_findings, build_bundle, IngestResult
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, statement="s"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def test_slug_normalizes():
    assert slug("NVDA") == "nvda"
    assert slug("SK hynix") == "sk-hynix"
    assert slug("  TSMC  ") == "tsmc"


def test_slug_empty_raises():
    with pytest.raises(ValueError):
        slug("!!!")


def test_route_creates_entity_pages_and_observations(tmp_path):
    ws = _store(tmp_path)
    touched = route_findings(ws, [_f("f-1", "NVDA"), _f("f-2", "AMD")], as_of="2026-06-28")
    assert touched == ["entity:amd", "entity:nvda"]
    assert {o.findingId for o in ws.observations("entity:nvda")} == {"f-1"}
    assert ws.get_page("entity:amd").title == "AMD"


def test_route_is_idempotent(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    n_events = len(ws.log.read())
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")  # re-run
    assert len(ws.log.read()) == n_events  # no new observation/create events


def test_route_empty_entity_fails_loud(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(ValueError):
        route_findings(ws, [_f("f-1", "  ")], as_of="2026-06-28")


def test_route_applies_category(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28", category="chips.merchant-gpu")
    assert ws.get_page("entity:nvda").category == "chips.merchant-gpu"


def test_build_bundle_has_touched_pages_and_new_findings(tmp_path):
    ws = _store(tmp_path)
    findings = [_f("f-1", "NVDA", "DC revenue up")]
    touched = route_findings(ws, findings, as_of="2026-06-28")
    bundle = build_bundle(ws, findings, touched, as_of="2026-06-28")
    assert bundle["asOf"] == "2026-06-28"
    assert bundle["schema"] == IngestResult.model_json_schema()
    page = bundle["pages"][0]
    assert page["pageId"] == "entity:nvda"
    assert page["newFindings"][0]["id"] == "f-1"
    assert page["newFindings"][0]["statement"] == "DC revenue up"
    assert "currentBody" in page and "currentState" in page
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_phase1.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.wiki.ingest'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/wiki/ingest.py`:

```python
from __future__ import annotations
import re
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding
from gpu_agent.wiki.store import WikiStore, PageNotFound

INGEST_SYSTEM = (
    "You curate a per-entity wiki of the GPU market. For each entity page you are given its "
    "standing thesis (current state/trajectory/body) and the day's new GATED findings. Return an "
    "IngestResult: for each page, write a concise markdown body that synthesizes the thesis with "
    "the new findings (every claim must cite a finding id like [f-123]); set a short state and a "
    "trajectory ('from -> to'); set a salience in [0,1] for how much this page matters now; list "
    "crossRefs to other entity page ids you mention; and set contradictsThesis=true with a short "
    "contradictionNote when a new finding opposes the page's current state. Never invent numbers — "
    "only cite what the findings state. Only enrich pages you were given; do not invent page ids."
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(entity: str) -> str:
    s = _SLUG_RE.sub("-", entity.strip().lower()).strip("-")
    if not s:
        raise ValueError(f"unroutable entity (empty slug): {entity!r}")
    return s


class PageEnrichment(BaseModel):
    pageId: str
    bodyMarkdown: str
    state: str
    trajectory: str
    salience: float
    crossRefs: list[str] = Field(default_factory=list)
    contradictsThesis: bool = False
    contradictionNote: str = ""


class IngestResult(BaseModel):
    pages: list[PageEnrichment]


def _entity_page_id(finding: Finding) -> str:
    if not finding.entity or not finding.entity.strip():
        raise ValueError(f"finding {finding.id} has empty entity; cannot route")
    return f"entity:{slug(finding.entity)}"


def route_findings(store: WikiStore, findings: list[Finding], *, as_of: str,
                   category: str | None = None) -> list[str]:
    """Phase 1 (deterministic): append each gated finding to its entity page, idempotently.
    Returns the sorted list of touched page ids."""
    touched: set[str] = set()
    for f in findings:
        pid = _entity_page_id(f)
        store.findings.append(f)  # gate-store (idempotent; differing content on a reused id fails loud)
        try:
            store.get_page(pid)
        except PageNotFound:
            store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
        already = {o.findingId for o in store.observations(pid)}
        if f.id not in already:
            store.append_observation(pid, f.id, as_of=as_of)
        touched.add(pid)
    return sorted(touched)


def build_bundle(store: WikiStore, findings: list[Finding], touched: list[str], *, as_of: str) -> dict:
    """Phase 2 emit: the bundle the brain answers. One entry per touched entity page, with its
    current header + body and the day's findings on it."""
    by_page: dict[str, list[Finding]] = {}
    for f in findings:
        by_page.setdefault(_entity_page_id(f), []).append(f)
    pages = []
    for pid in touched:
        view = store.window(pid, 0)  # page + body (no observations needed)
        page = view.page
        pages.append({
            "pageId": pid,
            "title": page.title,
            "currentState": page.state,
            "currentTrajectory": page.trajectory,
            "currentSalience": page.salience,
            "currentCrossRefs": page.crossRefs,
            "currentBody": view.body,
            "newFindings": [
                {"id": f.id, "statement": f.statement, "why": f.why,
                 "impact": f.impact.model_dump(),
                 "evidence": [e.model_dump() for e in f.evidence]}
                for f in by_page.get(pid, [])
            ],
        })
    return {"system": INGEST_SYSTEM, "schema": IngestResult.model_json_schema(),
            "asOf": as_of, "pages": pages}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_phase1.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 292 passed, 3 skipped (285 + 7 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/ingest.py tests/test_wiki_ingest_phase1.py && git commit -m "feat(4-4a): wiki ingest Phase 1 — slug + deterministic entity routing + emit bundle

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Phase-2 applier — `apply_enrichment`

**Files:**
- Modify: `gpu_agent/wiki/ingest.py` (add `apply_enrichment`)
- Test: `tests/test_wiki_ingest_apply.py`

**Interfaces:**
- Consumes: `IngestResult`/`PageEnrichment` (Task 2), `WikiStore` (`get_page`, `set_body`, `record_state`, `update_header`, `log`), the `WikiLog.append` API (`kind="ingest"`, `detail=`).
- Produces: `def apply_enrichment(store, result, *, as_of) -> None` — validates + applies each `PageEnrichment`; rejects a non-`entity:` or missing pageId (loud); idempotent `set_body`/`record_state`/crossRefs; appends exactly one `ingest` log event per `as_of` (skipped if one already exists), with a `detail` summarizing pages enriched + contradictions.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_ingest_apply.py`:

```python
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import apply_enrichment, route_findings, IngestResult, PageEnrichment
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def _seeded(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    return ws


def _enrich(**kw):
    base = dict(pageId="entity:nvda", bodyMarkdown="## NVDA\nDC up [f-1].\n",
                state="accelerating", trajectory="steady -> accelerating", salience=0.8)
    base.update(kw)
    return IngestResult(pages=[PageEnrichment(**base)])


def test_apply_sets_body_state_and_logs_ingest(tmp_path):
    ws = _seeded(tmp_path)
    apply_enrichment(ws, _enrich(crossRefs=["entity:amd"]), as_of="2026-06-28")
    page = ws.get_page("entity:nvda")
    assert page.state == "accelerating" and page.salience == 0.8
    assert page.crossRefs == ["entity:amd"]
    assert ws.window("entity:nvda", 0).body == "## NVDA\nDC up [f-1].\n"
    assert [e.kind for e in ws.log.read() if e.kind == "ingest"] == ["ingest"]


def test_apply_records_contradiction_in_ingest_event(tmp_path):
    ws = _seeded(tmp_path)
    apply_enrichment(ws, _enrich(contradictsThesis=True, contradictionNote="guidance cut"),
                     as_of="2026-06-28")
    ingest = [e for e in ws.log.read() if e.kind == "ingest"][0]
    assert "guidance cut" in ingest.detail


def test_apply_rejects_missing_page(tmp_path):
    ws = _seeded(tmp_path)
    with pytest.raises(Exception):
        apply_enrichment(ws, _enrich(pageId="entity:ghost"), as_of="2026-06-28")


def test_apply_rejects_non_entity_page(tmp_path):
    ws = _seeded(tmp_path)
    with pytest.raises(ValueError):
        apply_enrichment(ws, _enrich(pageId="theme:cowos"), as_of="2026-06-28")


def test_apply_is_idempotent(tmp_path):
    ws = _seeded(tmp_path)
    apply_enrichment(ws, _enrich(), as_of="2026-06-28")
    n = len(ws.log.read())
    apply_enrichment(ws, _enrich(), as_of="2026-06-28")  # re-apply same answer
    assert len(ws.log.read()) == n  # no new state-change or ingest event
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_apply.py -q`
Expected: FAIL with `ImportError: cannot import name 'apply_enrichment'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/ingest.py`, add at the end:

```python
def apply_enrichment(store: WikiStore, result: IngestResult, *, as_of: str) -> None:
    """Phase 2 (deterministic apply): enrich existing entity pages from the brain's IngestResult.
    Rejects non-entity / missing pages loud. Idempotent set_body/record_state/crossRefs. Appends
    exactly one 'ingest' log event per as_of (contradictions recorded in its detail, not yet weighted)."""
    contradictions: list[str] = []
    for pe in result.pages:
        if not pe.pageId.startswith("entity:"):
            raise ValueError(f"enrichment targets non-entity page: {pe.pageId}")
        page = store.get_page(pe.pageId)  # raises PageNotFound (loud) if missing
        store.set_body(pe.pageId, pe.bodyMarkdown, as_of=as_of)  # idempotent
        if (page.state, page.trajectory, page.salience) != (pe.state, pe.trajectory, pe.salience):
            store.record_state(pe.pageId, as_of=as_of, state=pe.state,
                               trajectory=pe.trajectory, salience=pe.salience)
        if page.crossRefs != pe.crossRefs:
            store.update_header(pe.pageId, as_of=as_of, crossRefs=pe.crossRefs)
        if pe.contradictsThesis:
            contradictions.append(f"{pe.pageId}: {pe.contradictionNote}")
    already_logged = any(e.kind == "ingest" and e.asOf == as_of for e in store.log.read())
    if not already_logged:
        detail = f"enriched {len(result.pages)} page(s)"
        if contradictions:
            detail += "; contradictions: " + " | ".join(contradictions)
        store.log.append(asOf=as_of, kind="ingest", detail=detail)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_apply.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 297 passed, 3 skipped (292 + 5 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/ingest.py tests/test_wiki_ingest_apply.py && git commit -m "feat(4-4a): wiki ingest Phase 2 — apply_enrichment (idempotent, gated, fail-loud)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `wiki-ingest` CLI subcommand + integration + frozen guard

**Files:**
- Modify: `gpu_agent/cli.py` (add the `wiki-ingest` subparser + `_wiki_ingest` handler + dispatch)
- Create: `fixtures/recorded/ingest-merchant-gpu.json` (a recorded `IngestResult`)
- Test: `tests/test_wiki_ingest_cli.py`

**Interfaces:**
- Consumes: `route_findings`, `build_bundle`, `apply_enrichment`, `IngestResult` (Tasks 2–3); `WikiStore`, `FindingStore`, `Finding`.
- Produces: `cli wiki-ingest --findings <json> --store <dir> --as-of <date> [--category <id>] [--emit-prompt | --recorded <answer.json>]`. Phase 1 always runs; `--emit-prompt` prints the bundle; `--recorded` applies an `IngestResult`; neither = Phase-1-only.

- [ ] **Step 1: Write the failing test**

Create `fixtures/recorded/ingest-merchant-gpu.json` (a single `IngestResult` enriching the NVDA page that the golden findings produce):

```json
{
  "pages": [
    {
      "pageId": "entity:nvda",
      "bodyMarkdown": "## NVIDIA\nData-center momentum strong; see [f-001].\n",
      "state": "accelerating",
      "trajectory": "steady -> accelerating",
      "salience": 0.9,
      "crossRefs": ["entity:amd"],
      "contradictsThesis": false,
      "contradictionNote": ""
    }
  ]
}
```

Create `tests/test_wiki_ingest_cli.py`:

```python
import json
import pathlib
from gpu_agent.cli import main


def test_wiki_ingest_phase1_only_populates_entity_pages(tmp_path, capsys):
    rc = main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
               "--store", str(tmp_path), "--as-of", "2026-06"])
    assert rc == 0
    # golden findings are NVDA/AMD/INTC -> three entity pages with observations
    pages = sorted(p.stem for p in (tmp_path / "wiki" / "entity").glob("*.md"))
    assert pages == ["amd", "intc", "nvda"]


def test_wiki_ingest_emit_prompt_prints_bundle(tmp_path, capsys):
    rc = main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
               "--store", str(tmp_path), "--as-of", "2026-06", "--emit-prompt"])
    assert rc == 0
    bundle = json.loads(capsys.readouterr().out)
    assert "system" in bundle and "schema" in bundle
    assert {p["pageId"] for p in bundle["pages"]} == {"entity:nvda", "entity:amd", "entity:intc"}


def test_wiki_ingest_recorded_applies_enrichment(tmp_path):
    rc = main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
               "--store", str(tmp_path), "--as-of", "2026-06",
               "--recorded", "fixtures/recorded/ingest-merchant-gpu.json"])
    assert rc == 0
    page_md = (tmp_path / "wiki" / "entity" / "nvda.md").read_text(encoding="utf-8")
    assert "accelerating" in page_md
    assert "## NVIDIA" in page_md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_cli.py -q`
Expected: FAIL — argparse exits non-zero / `SystemExit` because `wiki-ingest` is not a registered subcommand.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/cli.py`, add the import near the other wiki/store imports at the top:

```python
from gpu_agent.store import JsonStore, FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings, build_bundle, apply_enrichment, IngestResult
```

(The existing `from gpu_agent.store import JsonStore` line becomes the combined import above.)

Add the handler near the other handlers (e.g. after `_ingest`):

```python
def _wiki_ingest(args) -> int:
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    touched = route_findings(store, findings, as_of=args.as_of, category=args.category)
    if args.emit_prompt:
        print(json.dumps(build_bundle(store, findings, touched, as_of=args.as_of), indent=2))
        return 0
    if args.recorded:
        result = IngestResult.model_validate_json(pathlib.Path(args.recorded).read_text("utf-8"))
        apply_enrichment(store, result, as_of=args.as_of)
        print(f"enriched {len(result.pages)} page(s) -> {args.store}")
        return 0
    print(f"routed {len(findings)} finding(s) to {len(touched)} page(s) -> {args.store}")
    return 0
```

Register the subparser inside `main()` (after the `ingest` subparser block):

```python
    wi = sub.add_parser("wiki-ingest")
    wi.add_argument("--findings", required=True, help="JSON array of gated Findings")
    wi.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wi.add_argument("--as-of", required=True)
    wi.add_argument("--category", default=None, help="category id for auto-created entity pages")
    wi.add_argument("--recorded", default=None, help="path to a recorded IngestResult JSON")
    wi.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical ingest prompt + schema (no LLM) and exit")
```

Add the dispatch (next to the other `if args.cmd == ...` checks):

```python
    if args.cmd == "wiki-ingest":
        return _wiki_ingest(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_ingest_cli.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite + frozen guard**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 300 passed, 3 skipped (297 + 3 new).

Run: `cd /c/Users/danie/random_for_fun && git diff --stat main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/pipeline.py gpu_agent/store.py gpu_agent/wiki/log.py gpu_agent/wiki/page.py`
Expected: **no output** (frozen files + the existing 4-1 wiki `log.py`/`page.py` + `FindingStore` byte-unchanged; only `gpu_agent/wiki/store.py` gained `set_body`).

Run: `cd /c/Users/danie/random_for_fun && git diff main -- fixtures/golden/`
Expected: **no output** (no committed golden fixture changed).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/cli.py fixtures/recorded/ingest-merchant-gpu.json tests/test_wiki_ingest_cli.py && git commit -m "feat(4-4a): wiki-ingest CLI — Phase 1 always + emit-prompt/recorded brain seam

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-06-29-wiki-ingest-design.md`):
- §1 CLI seam (`wiki-ingest`, Phase-1-always, `--emit-prompt`/`--recorded`/neither, `--findings`/`--store`/`--as-of`/`--category`) → Task 4. ✓
- §2 Phase-1 routing (slug; FindingStore append; create-if-absent provisional; idempotent append_observation; empty entity fails loud; touched set) → Task 2 (`route_findings`, `slug`). ✓
- §3 Phase-2 bundle (touched pages: header+body+newFindings; schema) → Task 2 (`build_bundle`); `IngestResult`/`PageEnrichment` + `INGEST_SYSTEM` → Task 2; applier (reject non-entity/missing loud; idempotent set_body/record_state/crossRefs; one `ingest` event with contradiction note) → Task 3 (`apply_enrichment`). ✓
- §4 `WikiStore.set_body` (additive, idempotent, PageNotFound, no log event) → Task 1. ✓
- §5 frozen byte-unchanged + additive only → Task 4 Step 5 git-diff guards. ✓
- §6 doctrine (gated via FindingStore; brain invents no numbers; replayable ingest event; nothing silent) → Task 2 (gate-store + fail-loud routing) + Task 3 (fail-loud apply + ingest event). ✓
- §7 test strategy (Phase 1 no-brain; set_body; applier via recorded fixture; emit-prompt bundle; frozen guard) → Tasks 1–4 tests. ✓
- §9 acceptance items 1–5 all map to the tasks above. ✓

**Placeholder scan:** none — every step has complete code/commands.

**Type consistency:** `slug`/`route_findings`/`build_bundle`/`IngestResult`/`PageEnrichment` (Task 2) are imported and called with matching signatures in Tasks 3–4. `apply_enrichment(store, result, *, as_of)` (Task 3) is called exactly so in Task 4. `WikiStore.set_body(page_id, body, *, as_of)` (Task 1) is called by `apply_enrichment` (Task 3). The CLI handler uses `route_findings(..., category=args.category)` matching Task 2's keyword. `FindingStore` is imported into `cli.py` (Task 4) alongside `JsonStore`. `store.log.append(asOf=, kind="ingest", detail=)` matches the 4-1 `WikiLog.append` signature. `window(pid, 0)` returns a `WindowView` with `.page`/`.body` (4-1). ✓

**Test-count math:** baseline 282 → +3 (Task 1) → +7 (Task 2) → +5 (Task 3) → +3 (Task 4) = **300 passed, 3 skipped** at the end.
