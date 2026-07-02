# Lane C — Judgment Aggregation Fixes (F19, F20, F35, F38) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make judgment aggregation honest: a real quorum before a dimension is rated (F19), finding-level confidence caps propagated up to dimension ratings (F20), citation coherence against the dimension's indicator group (F35), and the vote spread moved out of `confidence.basis` into its own field (F38 code half).

**Architecture:** All changes live in `gpu_agent/judgment/judge.py` (aggregation + validation) plus ONE additive optional field on `DimensionRating` in `gpu_agent/schema/scorecard.py`. The judge's sampling loop and prompt text are unchanged; sample independence at generation time is a SKILL-file change the controller applies at merge (do NOT edit `.claude/skills/*`).

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints

- Branch `fix/lane-c`, own worktree, run from its root.
- **You own:** `gpu_agent/judgment/judge.py`; ONE additive field in `gpu_agent/schema/scorecard.py`; `tests/test_judgment_aggregate.py`, `tests/test_judge_findings.py`, `tests/test_cli_judge.py`, new `tests/test_judge_v12.py`.
- **NEVER edit:** `gpu_agent/judgment/briefing.py`, `gpu_agent/judgment/prompt.py` (the contract stream may change briefing's internals — its public signature stays compatible), `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/pipeline.py`, `gpu_agent/cli.py`, `gpu_agent/extraction/*`, `gpu_agent/gathering/*`, `gpu_agent/wiki/*`, `gpu_agent/report.py`, `fixtures/golden/*`, `fixtures/recorded/*` content (referencing recorded fixtures BY PATH is fine), `.claude/skills/*`.
- Anchor-band coupling: another stream tightens the gate's anchor tolerance from 0.5 to 0.15 in parallel. In any NEW test, keep anchors either within ±0.10 (consistent with any rating) or beyond ±0.5 (inconsistent under both bands) so your tests survive the merge in either order.
- Tests: `.venv/Scripts/python -m pytest -q`. Full suite green at the end of every task.
- Every commit ends with a `Co-Authored-By:` trailer naming the model doing the work.

---

### Task 1: F19 — real quorum; no single-sample "unanimity"

**Files:**
- Modify: `gpu_agent/judgment/judge.py`
- Test: `tests/test_judge_v12.py` (new)

**Interfaces:**
- Produces: `aggregate(results, briefing)` — a dimension present in fewer than `quorum = len(results) // 2 + 1` samples is NOT rated; it is listed in the new `JudgmentBundle.belowQuorum: list[str]` (additive field, default `[]`). Confidence per dimension: `high` only when the dimension appears in ALL samples AND every vote agrees; `medium` otherwise.

- [ ] **Step 1: Failing tests** in `tests/test_judge_v12.py` (build `JudgmentResult` objects inline; copy the constructor pattern from `tests/test_judgment_aggregate.py` — each result needs `dimensions`, `categoryStatus`, `narrative`):

```python
# 1. dimension "moat" present in only 1 of 3 samples -> not in bundle.ratings;
#    "moat" in bundle.belowQuorum
# 2. dimension present in 2 of 3 samples, both votes "Strong" -> rated "Strong",
#    confidence level == "medium" (not high: quorum met but not full-sample coverage)
# 3. dimension present in 3 of 3, all "Strong" -> confidence "high"
# 4. dimension present in 3 of 3, votes Strong/Strong/Mixed -> "Strong", confidence "medium"
```

- [ ] **Step 2: Run** `pytest tests/test_judge_v12.py -q` → FAIL.
- [ ] **Step 3: Implement** in `aggregate`:

```python
    n = len(results)
    quorum = n // 2 + 1
    below_quorum: list[str] = []
    for d in sorted(dims):
        votes = [r.dimensions[d].rating for r in results if d in r.dimensions]
        if len(votes) < quorum:
            below_quorum.append(d)          # F19: 1-of-3 is not unanimity, it is absence
            continue
        winner, basis = _majority(votes)
        winners[d] = winner
        unanimous = len(votes) == n and len(set(votes)) == 1
        ...
```
Add `belowQuorum: list[str] = Field(default_factory=list)` to `JudgmentBundle` and pass it in the return. `all_unanimous` now means: every RATED dimension unanimous with full coverage (`unanimous` as defined above).

- [ ] **Step 4: Run** task tests → PASS; full suite (existing aggregate tests may assume 1-of-3 rating — update their data to meet quorum rather than weakening assertions).
- [ ] **Step 5: Commit** `fix(F19): judgment quorum - a dimension needs a sample majority to be rated; high confidence needs full unanimous coverage`

---

### Task 2: F38 (code half) — vote spread out of confidence.basis, into its own field

**Files:**
- Modify: `gpu_agent/schema/scorecard.py` (ONE additive line), `gpu_agent/judgment/judge.py`
- Test: extend `tests/test_judge_v12.py`

**Interfaces:**
- Produces: `DimensionRating.voteSpread: Optional[str] = None` (additive, default None — old stored scorecards still validate). `aggregate` writes the "2/3 Strong, 1/3 Mixed" string to `voteSpread`; `confidence.basis` becomes the plain-language basis `f"majority of {len(votes)}/{n} samples"`.

- [ ] **Step 1: Failing tests:**

```python
# 1. Strong/Strong/Mixed -> ratings[d].voteSpread == "2/3 Strong, 1/3 Mixed"
#    and "Strong," not in ratings[d].confidence.basis
# 2. old scorecard JSON without voteSpread still validates (DimensionRating(**{...no voteSpread}))
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** In `schema/scorecard.py`, add to `DimensionRating`: `voteSpread: Optional[str] = None`. In `aggregate`, `_majority` keeps returning `(winner, spread)`; use it as
`ratings[d] = DimensionRating(..., voteSpread=basis, confidence=Confidence(level=..., basis=f"majority of {len(votes)}/{n} samples"))`.
- [ ] **Step 4: Full suite** (update tests asserting the old basis format — move the assertion to voteSpread, don't delete it).
- [ ] **Step 5: Commit** `fix(F38): vote spread is data, not prose - own voteSpread field on DimensionRating; basis states the method`

---

### Task 3: F20 — propagate finding-level confidence caps to the dimension rating

**Files:**
- Modify: `gpu_agent/judgment/judge.py`
- Test: extend `tests/test_judge_v12.py`

**Interfaces:**
- Produces: `aggregate(results, briefing, findings_by_id: dict[str, Finding] | None = None)` — additive param; `judge_findings` passes `{f.id: f for f in findings}`. Rule: the ceiling for a dimension's confidence is the HIGHEST confidence level among its cited findings (a rating cannot be more confident than its best evidence); `low < medium < high`. Applied after the vote-derived level.

- [ ] **Step 1: Failing tests:**

```python
# 1. unanimous 3/3 "Strong" (vote level high) but every cited finding has confidence "medium"
#    -> ratings[d].confidence.level == "medium", basis mentions "capped by finding confidence"
# 2. cited findings include one "high" -> vote level survives ("high")
# 3. all cited findings "low" -> level "low"
# 4. findings_by_id=None (legacy call) -> behavior unchanged (no cap applied)
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:**

```python
_LEVELS = {"low": 0, "medium": 1, "high": 2}

def _confidence_ceiling(finding_ids, findings_by_id):
    cited = [findings_by_id[i] for i in finding_ids if i in findings_by_id]
    if not cited:
        return "high"
    return max((f.confidence.level for f in cited), key=_LEVELS.__getitem__)
```
After building each rating, when `findings_by_id is not None`:
```python
        ceiling = _confidence_ceiling(rep.findingIds, findings_by_id)
        if _LEVELS[ceiling] < _LEVELS[conf.level]:
            conf = Confidence(level=ceiling,
                              basis=f"{conf.basis}; capped by finding confidence ({ceiling})")
```
`judge_findings` passes `findings_by_id={f.id: f for f in findings}`.

- [ ] **Step 4: Full suite.**
- [ ] **Step 5: Commit** `fix(F20): dimension confidence inherits its cited findings' ceiling - aggregation finally consults finding-level confidence`

---

### Task 4: F35 — citation coherence: cited findings must belong to the dimension's group

**Files:**
- Modify: `gpu_agent/judgment/judge.py`
- Test: extend `tests/test_judge_v12.py`; update `tests/test_judge_findings.py` / `tests/test_cli_judge.py` data if their citations are incoherent.

**Interfaces:**
- Produces: `_conflicts(bundle, briefing)` (param added) — for every rated dimension, each cited finding id must appear in `briefing.grouped.get(dim, [])`; a violation reads `f"{dim}: cites {fid} which is not in its indicator group"`. Incoherent citations therefore trigger the existing resample loop, then a loud `JudgmentError`.

- [ ] **Step 1: Failing tests:**

```python
# 1. sample cites a momentum finding id for the "moat" dimension
#    -> judge_findings(...) with a RecordedClient serving that answer (samples=1,
#       resample_budget=0) raises JudgmentError mentioning "not in its indicator group"
# 2. coherent citations -> no error (happy path passes)
```
Use inline serialized JudgmentResult JSON strings with a RecordedClient (schema-agnostic), findings built for two dimensions via the registry's real indicator ids (e.g. D2 -> momentum, market-share-pct -> moat).

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:** extend `_conflicts(bundle, briefing)`:

```python
    for d, r in bundle.ratings.items():
        allowed = set(briefing.grouped.get(d, []))
        for fid in r.findingIds:
            if fid not in allowed:
                bad.append(f"{d}: cites {fid} which is not in its indicator group")
```
Update the call in `judge_findings` to `_conflicts(bundle, briefing)`.

- [ ] **Step 4: Full suite**; fix incoherent citations in existing test data (keep assertions).
- [ ] **Step 5: Commit** `fix(F35): judgment citations validated against the dimension's indicator group - a momentum finding can no longer ground a moat rating`

---

## Out of scope (controller handles at merge — do NOT do these)
- `.claude/skills/run-cycle/SKILL.md` change instructing independent subagent generations per judgment sample (F38 skill half).
- Any `cli.py` change.

## Self-review checklist
- F19/F20/F35/F38-code each map to a task; `git diff main --stat` shows only judge.py, scorecard.py (+1 line), owned tests.
- New tests avoid anchors in the (0.10, 0.5) gray zone.
- Full suite green.
