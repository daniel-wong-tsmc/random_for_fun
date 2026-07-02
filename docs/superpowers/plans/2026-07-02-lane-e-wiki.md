# Lane E — Wiki Integrity (F14, F15, F30, F31, F32, F13-E, F22-E) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the un-gated channel into the brief: enrichment citations and numbers gated (F14), salience computed in code, never brain-invented (F15), lifecycle promotions logged (F30), corroboration keyed by publisher domain (F31), read paths that don't write and provenance events that don't age pages (F32), ingest events keyed per run + asOf grain validated (F13 wiki side), and lint's silent discards surfaced (F22 wiki side).

**Architecture:** All changes live in `gpu_agent/wiki/`. A new pure `wiki/salience.py` computes salience from observable store facts; `PageEnrichment` loses its model-supplied salience; `apply_enrichment` gains a citation + numeric gate; `store.update_header` logs; `lint` gains a `record` flag and provenance-blind decay; `lifecycle.corroboration` keys by domain.

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints

- Branch `fix/lane-e`, own worktree, run from its root.
- **You own:** `gpu_agent/wiki/ingest.py`, `gpu_agent/wiki/lint.py`, `gpu_agent/wiki/store.py`, `gpu_agent/wiki/lifecycle.py`, new `gpu_agent/wiki/salience.py`, and tests `tests/test_wiki_*.py`, `tests/test_lifecycle_*.py`, new `tests/test_wiki_v12.py`.
- **NEVER edit:** `gpu_agent/cli.py` (the controller flips its lifecycle call to `lint(..., record=False)` at merge — design for it, don't wire it), `gpu_agent/wiki/movement.py`, `gpu_agent/wiki/page.py`, `gpu_agent/wiki/log.py`, `gpu_agent/brief.py`, `gpu_agent/report.py`, `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/extraction/*`, `gpu_agent/judgment/*`, `gpu_agent/gathering/*`, `gpu_agent/schema/*`, `fixtures/golden/*`, `fixtures/recorded/*`, `registry/*`, `.claude/skills/*`.
- Keep every public signature backward-compatible (additive params with safe defaults) — cli.py call sites must keep working UNCHANGED.
- Tests: `.venv/Scripts/python -m pytest -q`. Full suite green at the end of every task.
- Every commit ends with a `Co-Authored-By:` trailer naming the model doing the work.

---

### Task 1: F15 — salience computed in code; the brain no longer sets it

**Files:**
- Create: `gpu_agent/wiki/salience.py`
- Modify: `gpu_agent/wiki/ingest.py` (`INGEST_SYSTEM`, `PageEnrichment`, `apply_enrichment`)
- Test: `tests/test_wiki_v12.py` (new); update `tests/test_wiki_ingest_apply.py`, `tests/test_wiki_ingest_seam.py`, `tests/test_wiki_ingest_cli.py` data (their PageEnrichment payloads carry salience — remove it).

**Interfaces:**
- Produces: `computed_salience(store, page_id, *, as_of, contradiction: bool) -> float` — pure, deterministic:
  `min(1.0, round(0.15 + 0.10 * min(n_total, 5) + 0.15 * fresh + 0.10 * primary + 0.20 * contra, 4))`
  where `n_total` = total observations on the page, `fresh` = 1 if any observation has `asOf == as_of` else 0, `primary` = 1 if any resolvable observed finding carries primary-tier evidence else 0, `contra` = 1 if `contradiction` else 0.
  `PageEnrichment` becomes `model_config = ConfigDict(extra="forbid")` and LOSES `salience` (a recorded IngestResult that still carries salience now fails LOUD — that is the fix). `apply_enrichment` computes salience via `computed_salience` and passes it to `record_state`; state/trajectory still come from the model.

- [ ] **Step 1: Failing tests** in `tests/test_wiki_v12.py` (build a store in tmp_path with the helpers from `tests/test_wiki_ingest_apply.py`):

```python
# 1. computed_salience: single fresh secondary observation, no contradiction
#    -> 0.15 + 0.10 + 0.15 == pytest.approx(0.40)
# 2. contradiction adds 0.20; primary evidence adds 0.10; 6 observations cap the count term at 0.50
# 3. everything maxed -> min(1.0, ...) == 1.0
# 4. PageEnrichment(..., salience=0.9) raises pydantic ValidationError (extra=forbid)
# 5. apply_enrichment writes the COMPUTED salience: enrich a page whose model payload has no
#    salience; store.get_page(pid).salience == pytest.approx(expected from rule 1)
# 6. INGEST_SYSTEM does not contain the word "salience"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**

`gpu_agent/wiki/salience.py`:
```python
from __future__ import annotations

def computed_salience(store, page_id: str, *, as_of: str, contradiction: bool) -> float:
    """Deterministic salience from observable store facts (F15 — the 4-1 spec forbids
    brain-invented salience driving materiality/decay/pruning/ordering).
    Monotone in evidence mass; fresh activity, primary sourcing and a live
    contradiction each add a fixed boost."""
    obs = store.observations(page_id)
    n_total = len(obs)
    fresh = any(o.asOf == as_of for o in obs)
    primary = False
    for o in obs:
        try:
            f = store.findings.get(o.findingId)
        except Exception:
            continue
        if any(e.tier == "primary" for e in f.evidence):
            primary = True
            break
    score = (0.15 + 0.10 * min(n_total, 5) + 0.15 * (1 if fresh else 0)
             + 0.10 * (1 if primary else 0) + 0.20 * (1 if contradiction else 0))
    return min(1.0, round(score, 4))
```
`ingest.py`: `PageEnrichment` gains `model_config = ConfigDict(extra="forbid")` (import ConfigDict), delete the `salience` field. In `apply_enrichment`:
```python
        salience = computed_salience(store, pe.pageId, as_of=as_of,
                                     contradiction=pe.contradictsThesis)
        if (page.state, page.trajectory, page.salience) != (pe.state, pe.trajectory, salience):
            store.record_state(pe.pageId, as_of=as_of, state=pe.state,
                               trajectory=pe.trajectory, salience=salience)
```
`INGEST_SYSTEM`: delete the "set a salience in [0,1] for how much this page matters now;" clause (salience is computed by code, not requested).

- [ ] **Step 4: Full suite**; strip `salience` from every test enrichment payload; update salience-value assertions to the computed values (show the arithmetic in a comment).
- [ ] **Step 5: Commit** `fix(F15): salience is computed in code from store facts - model salience field removed (extra=forbid, fails loud)`

---

### Task 2: F14 — gate the enrichment channel: citations must exist, numbers must be cited

**Files:**
- Modify: `gpu_agent/wiki/ingest.py` (`apply_enrichment` + two new helpers)
- Test: extend `tests/test_wiki_v12.py`

**Interfaces:**
- Produces: `EnrichmentGateError(ValueError)` with `.violations: list[str]`. In `apply_enrichment`, per page BEFORE any write:
  - citation gate: every `[token]` in `bodyMarkdown` matching `re.findall(r"\[([A-Za-z0-9][A-Za-z0-9._-]*)\]", body)` must be an id with `store.findings.exists(id)` → else violation `"<pageId>: cites unknown finding <token>"`.
  - numeric gate: every numeric token in the body — `re.findall(r"\d[\d,]*(?:\.\d+)?", body)`, normalized by stripping commas, keeping only tokens with ≥2 digits — must appear (same normalization) in the concatenation of the page's CITED findings' `statement`, `why`, `value.number` (rendered via `repr` and `f"{v:g}"`), `evidence[].excerpt` and `evidence[].date`, plus the enrichment's own `state`/`trajectory` strings → else `"<pageId>: uncited number <token>"`.
  All violations across all pages are collected and raised together (fail loud, nothing written).

- [ ] **Step 1: Failing tests:**

```python
# 1. body cites "[no-such-finding]" -> EnrichmentGateError, message lists the page + token,
#    and NO store mutation happened (page body unchanged, log length unchanged)
# 2. body says "revenue $75,200,000,000 rising" where no cited finding contains 75200000000
#    -> "uncited number"
# 3. clean body citing a real finding whose excerpt contains the number -> applies fine
# 4. markdown noise immune: "1." list markers and years present in evidence dates pass
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the two helpers + a validation loop at the TOP of `apply_enrichment` (before the write loop), collecting violations for every page, raising `EnrichmentGateError(violations)` if any. Only then run the existing write loop.
- [ ] **Step 4: Full suite** (existing apply tests' bodies must cite real ids / contain no orphan numbers — fix their data).
- [ ] **Step 5: Commit** `fix(F14): enrichment gate - citations must resolve to gated findings and every number must trace to a cited finding`

---

### Task 3: F13 (wiki side) — ingest events keyed per run; asOf grain validated

**Files:**
- Modify: `gpu_agent/wiki/ingest.py` (`apply_enrichment`, `route_findings`)
- Test: extend `tests/test_wiki_v12.py`

**Interfaces:**
- Produces: `_AS_OF_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")`; both `route_findings` and `apply_enrichment` raise `ValueError(f"invalid asOf grain: {as_of!r}")` on mismatch. Ingest-event idempotency is keyed by CONTENT, not by asOf alone: the event is suppressed only when an ingest event with the SAME asOf AND SAME detail already exists (a second, different same-month ingest now logs — its contradictions are no longer dropped).

- [ ] **Step 1: Failing tests:**

```python
# 1. apply_enrichment(as_of="June 2026") -> ValueError "invalid asOf grain"
# 2. two DIFFERENT enrichments at the same as_of -> TWO ingest events in the log
# 3. the SAME enrichment applied twice at the same as_of -> ONE ingest event (idempotent)
# 4. lint's _contradictions_for aggregates contradictions across BOTH same-asOf events
#    (build two enrichments with different contradiction pages; both appear in lint health)
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:** grain check at the top of both functions; replace the `already_logged` line with:

```python
    detail = format_contradiction_detail(len(result.pages), contradictions)
    already_logged = any(e.kind == "ingest" and e.asOf == as_of and e.detail == detail
                         for e in store.log.read())
    if not already_logged:
        store.log.append(asOf=as_of, kind="ingest", detail=detail)
```

- [ ] **Step 4: Full suite.**
- [ ] **Step 5: Commit** `fix(F13e): asOf grain validated; ingest events keyed by run content - same-month reruns stop dropping contradictions`

---

### Task 4: F30 + F31 — promotions logged; corroboration keyed by publisher domain

**Files:**
- Modify: `gpu_agent/wiki/store.py` (`update_header`), `gpu_agent/wiki/lifecycle.py` (`corroboration`)
- Test: extend `tests/test_wiki_v12.py`; update `tests/test_lifecycle_promotion.py` data if needed.

**Interfaces:**
- Produces: `update_header` appends a log event `kind="header-change"` with `detail` listing the changed fields, e.g. `detail="status: provisional -> registered"` (one `f"{k}: {old} -> {new}"` per changed field, comma-joined; no event when nothing changed). `corroboration(store, page_id)` counts DISTINCT PUBLISHERS: for each evidence entry, key = `urlparse(e.url).netloc.lower()` with a leading `"www."` stripped; empty netloc falls back to `e.source.strip().lower()`.

- [ ] **Step 1: Failing tests:**

```python
# 1. update_header(status="registered") on a provisional page -> log gains a "header-change"
#    event with detail "status: provisional -> registered"                       (F30)
# 2. update_header with an unchanged value -> NO new event
# 3. two findings citing "NVIDIA Newsroom" and "NVIDIA press release" both at
#    https://nvidianews.nvidia.com/... -> corroboration == 1 (same publisher)     (F31)
# 4. www.example.com and example.com -> 1; example.com and other.org -> 2
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (`store.py`: compute changed fields before `model_copy`; append the event after `_write`. `lifecycle.py`: `from urllib.parse import urlparse`, build the publisher key set).
- [ ] **Step 4: Full suite** — `quiet_age` counts kinds `("append-observation", "state-change")` as material, and its CYCLE set derives from event asOf values: a header-change event at a new asOf would now mint a cycle. Task 5 makes the cycle set provenance-blind; if any decay test wobbles here, note it and fix it in Task 5 (tasks 4+5 may be committed together if the suite demands it — say so in the commit body).
- [ ] **Step 5: Commit** `fix(F30,F31): lifecycle promotions leave a header-change log event; corroboration counts distinct publishers, not free-text source strings`

---

### Task 5: F32 — read paths don't write; provenance events don't age pages

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (`lint`, `quiet_age`)
- Test: update `tests/test_wiki_lint_decay.py`; extend `tests/test_wiki_v12.py`

**Interfaces:**
- Produces: `lint(store, *, as_of, prev_as_of=None, registry, horizons, config=..., record: bool = True)` — `record=False` performs NO log write (the pure read path; the controller wires cli's lifecycle-propose call to it at merge). `quiet_age` derives its cycle set ONLY from material-kind events: `kind in ("create-page", "append-observation", "state-change", "ingest")` — `lint` and `header-change` events can no longer mint a decay cycle.

- [ ] **Step 1: Failing tests:**

```python
# 1. lint(record=False) leaves the log byte-identical (read len before/after)
# 2. lint(record=True) still appends exactly one lint event per asOf (existing behavior)
# 3. a store with material events at 2026-06-01 then ONLY a lint event at 2026-06-02:
#    quiet_age(page, "2026-06-02") == 0 (the lint event minted no cycle)
# 4. an ingest event at 2026-06-02 DOES mint a cycle (a real run happened):
#    quiet_age == 1
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:**

```python
_MATERIAL_CYCLE_KINDS = {"create-page", "append-observation", "state-change", "ingest"}

def quiet_age(store, page_id, as_of) -> int:
    events = [e for e in store.log.read() if e.asOf <= as_of]
    cycles = sorted({e.asOf for e in events if e.kind in _MATERIAL_CYCLE_KINDS})   # F32
    ...
```
and gate the lint-event append on `record`.

- [ ] **Step 4: Full suite.**
- [ ] **Step 5: Commit** `fix(F32): lint gains a no-write mode and decay counts only material cycles - provenance events stop aging pages`

---

### Task 6: F22 (wiki side) — lint surfaces what it used to swallow

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (`_findings_for`, `_score_move`, `half_life` callers, `HealthReport`)
- Test: extend `tests/test_wiki_v12.py`

**Interfaces:**
- Produces: `HealthReport.missingFindings: list[str]` and `HealthReport.untaggedIndicators: list[str]` (additive, default []). `_findings_for(store, page_id, observations)` returns `(findings, missing_ids)`; every caller threads `missing_ids` up; `_score_move`'s try/except loop does the same. The `_untagged` list `half_life` already returns is finally surfaced instead of discarded. Both lists are sorted and de-duplicated in the report.

- [ ] **Step 1: Failing tests:**

```python
# 1. an observation whose findingId is absent from the FindingStore
#    -> report.health.missingFindings == ["<that id>"] (was: silently skipped)
# 2. a finding with an indicatorId that has no cadenceHorizon tag
#    -> report.health.untaggedIndicators contains that indicator id
# 3. clean store -> both lists empty
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — change `_findings_for` to return the pair; collect `missing` and `untagged` sets inside `lint()` (threading through `_score_move` and `health_report`); populate the two new HealthReport fields with `sorted(set(...))`.
- [ ] **Step 4: Full suite** (update lint-model tests for the new fields' defaults).
- [ ] **Step 5: Commit** `fix(F22e): lint reports missing findings and untagged indicators instead of swallowing them`

---

## Out of scope (controller handles at merge — do NOT do these)
- `gpu_agent/cli.py` line ~152: `_wiki_lifecycle`'s propose path switching to `lint(..., record=False)`.
- Skill-file changes.

## Self-review checklist
- F14/F15/F30/F31/F32/F13-E/F22-E each map to a task; `git diff main --stat` shows only wiki/*, owned tests.
- All public signatures backward-compatible (cli.py untouched and still green).
- Full suite green.
