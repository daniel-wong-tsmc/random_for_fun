# F63 — Corroboration Doctrine + Evidence-Sufficiency Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** N=3 distinct secondary publishers unlock one bounded step on three surfaces — gate F2e finding confidence (the single frozen-core edit, contract v1.3), thesis anti-whipsaw rule 6, and a new deterministic evidence-sufficiency gate on judge rating/binding-constraint changes — with the corroboration set logged and the next filing as confirm/deny checkpoint.

**Architecture:** One shared publisher-identity module (`publisher.py`, F31 semantics moved verbatim) feeds all three surfaces; one registry constant (`registry/corroboration.json`) is the tunable N; the sufficiency gate is additive (`sufficiency.py`) and wires at the same two `cli.py` recorded seams as the F67 voice lint with the same reject→re-dispatch loop. Three SYSTEM prompts gain matching sentences (extract cap exception, thesis anti-whipsaw exception, judge sufficiency announcement) — all three hashes drift, so the plan ends with a session-level full run-eval + rebaseline.

**Tech Stack:** Python 3.13, pytest, pydantic v2 (existing patterns only; no new dependencies).

**Spec:** `docs/superpowers/specs/2026-07-04-f63-corroboration-doctrine-design.md` (user-approved; decision provenance inside).

## Global Constraints

- **Frozen contract v1.2 → v1.3:** the ONLY permitted frozen-core diff on this branch is the gate.py F2e rule (Task 3). `scoring.py`, `schema/*`, `judgment/briefing.py`, `judgment/judge.py`, `pipeline.py`, `JsonStore` stay EMPTY-diff vs main — verified at final review with `git diff main -- gpu_agent/scoring.py gpu_agent/schema gpu_agent/judgment/briefing.py gpu_agent/judgment/judge.py gpu_agent/pipeline.py` (must print nothing) and `git diff main -- gpu_agent/gate.py` (must show only the F2e hunk).
- **Contract v1.2's F3 dimension-level confidence cap is intentionally UNCHANGED** (spec "What does NOT change") — do not touch it, do not "fix" it for consistency.
- **THE F6 EVAL GATE IS ARMED:** Tasks 3, 4, and 6 change emitted brain prompts → `tests/test_evals_baseline_pin.py` goes red. During Tasks 3–7 run the suite with `--deselect tests/test_evals_baseline_pin.py` and note it in each commit. The ONLY unlock is Task 8 (run-eval → `gpu-agent eval rebaseline`), committed WITH the new baseline. NEVER hand-edit `fixtures/evals/*`.
- **N = 3 exactly once in data:** `registry/corroboration.json` `minDistinctPublishers` is the single tunable; code reads it ONLY via `gpu_agent.config.min_distinct_publishers()`; the three prompt sentences hardcode "3" and Task 2's drift-guard test couples them (registry value == 3 AND each amended SYSTEM contains "3 distinct publishers").
- **Publisher identity is F31's, never re-derived:** all counting goes through `gpu_agent.publisher.publisher_key` (Task 1). No second netloc-parsing implementation anywhere.
- **Doctrine:** code computes + gates + stores; brains reason; NEVER hand-edit brain output — a gate failure re-dispatches the brain with the violations appended; every cap/skip/drop logged.
- **Suite at branch start: 974 passed / 3 skipped** (post-F62 main). Keep everything green except the deliberately-red pin; after Task 8 the FULL suite (no deselects) must be green.
- Python: `/c/Users/danie/random_for_fun/.venv/Scripts/python` from the worktree root `.worktrees/f63-corroboration`. Use bash for `>` redirects. No double quotes inside `git commit -m` (use heredoc). Commit trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` (the ACTUAL model).
- Concurrent instances: check `git log --oneline -1` as its OWN command immediately before every commit; never chain `git log && git commit`.

---

### Task 1: `gpu_agent/publisher.py` — the shared F31 identity (zero behavior change)

**Files:**
- Create: `gpu_agent/publisher.py`
- Modify: `gpu_agent/wiki/lifecycle.py` (replace the `_publisher_key` def with a re-export; its `from urllib.parse import urlparse` import stays only if still used elsewhere in the file — check; if not, remove it)
- Test: `tests/test_publisher.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces: `publisher_key(evidence) -> str` where `evidence` is any object with `.url: str` and `.source: str` (the `Evidence` pydantic model qualifies). Tasks 3, 4, 5 import exactly `from gpu_agent.publisher import publisher_key`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_publisher.py
from types import SimpleNamespace
from gpu_agent.publisher import publisher_key


def _e(url="", source=""):
    return SimpleNamespace(url=url, source=source)


def test_netloc_lowercased_www_stripped():
    assert publisher_key(_e(url="https://www.Reuters.com/article/x")) == "reuters.com"


def test_distinct_paths_same_netloc_collapse():
    a = publisher_key(_e(url="https://digitimes.com/a"))
    b = publisher_key(_e(url="https://digitimes.com/b"))
    assert a == b == "digitimes.com"


def test_source_fallback_when_no_netloc():
    assert publisher_key(_e(url="not-a-url", source="  Dell'Oro Group ")) == "dell'oro group"


def test_wiki_lifecycle_reexport_is_same_object():
    from gpu_agent.wiki import lifecycle
    assert lifecycle._publisher_key is publisher_key
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_publisher.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.publisher'`

- [ ] **Step 3: Create the module (moved verbatim from wiki/lifecycle.py)**

```python
# gpu_agent/publisher.py
from __future__ import annotations
from urllib.parse import urlparse


def publisher_key(evidence) -> str:
    """F31 publisher identity — THE corroboration key. Moved verbatim from
    wiki/lifecycle.py::_publisher_key when F63 gave it three consumers (wiki page
    promotion, thesis rule 6, gate F2e); import this, never re-derive it, so the
    publisher-identity notion can never drift between surfaces.

    Keys by the evidence URL's registered netloc (www.-stripped, lowercased) —
    corroboration must be keyed by publisher, not by free-text source strings that can
    name the same publisher two different ways ('NVIDIA Newsroom' vs 'NVIDIA press
    release'). Falls back to the source string when the URL has no netloc (e.g. a
    non-URL citation)."""
    netloc = urlparse(evidence.url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc:
        return netloc
    return evidence.source.strip().lower()
```

- [ ] **Step 4: Re-export from wiki/lifecycle.py**

In `gpu_agent/wiki/lifecycle.py`, replace the whole `def _publisher_key(evidence) -> str:` function (its `"""F31: corroboration must be keyed by publisher…"""` docstring block through `return evidence.source.strip().lower()`) with:

```python
# F31 identity moved to gpu_agent/publisher.py when F63 gave it three consumers;
# re-exported under the historical name so this module's callers (and thesis.py's
# defensive import of it) stay byte-compatible.
from gpu_agent.publisher import publisher_key as _publisher_key
```

Then check whether `urlparse` is still used elsewhere in lifecycle.py (`grep -n urlparse gpu_agent/wiki/lifecycle.py`); if the only use was `_publisher_key`, delete the now-unused `from urllib.parse import urlparse` import.

- [ ] **Step 5: Run the new tests + the existing wiki/thesis suites**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_publisher.py tests/test_wiki_lifecycle.py tests/test_thesis_apply.py -q`
(if `tests/test_wiki_lifecycle.py` does not exist under that name, run `pytest tests/ -q -k "lifecycle or thesis"`)
Expected: ALL PASS — the re-export is behavior-identical.

- [ ] **Step 6: Commit**

Check `git log --oneline -1` first (own command), then:

```bash
git add gpu_agent/publisher.py gpu_agent/wiki/lifecycle.py tests/test_publisher.py
git commit -m "$(cat <<'EOF'
refactor(publisher): F31 identity moved to shared module (F63 surface prep)

publisher_key gains three consumers (wiki promotion, thesis rule 6, gate F2e);
one neutral home, wiki/lifecycle re-exports the historical name. Zero behavior
change, pinned by identity test.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `registry/corroboration.json` + config accessor + drift guard

**Files:**
- Create: `registry/corroboration.json`
- Modify: `gpu_agent/config.py` (append)
- Test: `tests/test_corroboration_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `gpu_agent.config.min_distinct_publishers() -> int` (cached; env-overridable path `GPU_AGENT_CORROBORATION`; missing file → default 3). Tasks 3, 4, 5 call exactly this.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_corroboration_config.py
import json
from gpu_agent.config import min_distinct_publishers


def test_registry_value_is_three():
    # N=3 was a user decision (spec, decision provenance fork 2). The three amended
    # SYSTEM prompts hardcode "3 distinct publishers"; if you tune the registry value,
    # this test forces you to update those prompts (and re-run the eval) too.
    assert min_distinct_publishers() == 3
    raw = json.load(open("registry/corroboration.json", encoding="utf-8"))
    assert raw == {"minDistinctPublishers": 3}


def test_missing_file_falls_back_to_three(monkeypatch, tmp_path):
    import gpu_agent.config as config
    monkeypatch.setattr(config, "CORROBORATION_PATH", str(tmp_path / "absent.json"))
    config.min_distinct_publishers.cache_clear()
    try:
        assert config.min_distinct_publishers() == 3
    finally:
        config.min_distinct_publishers.cache_clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corroboration_config.py -q`
Expected: FAIL — `ImportError: cannot import name 'min_distinct_publishers'`

- [ ] **Step 3: Create the registry file and the accessor**

`registry/corroboration.json`:

```json
{"minDistinctPublishers": 3}
```

Append to `gpu_agent/config.py`:

```python
# F63: corroboration threshold N — distinct publishers (F31 identity) required to unlock
# one bounded step (gate F2e high-confidence lift, thesis rule 6 corroborated reversal,
# evidence-sufficiency gate). Single tunable; the amended SYSTEM prompts hardcode the same
# number and tests/test_corroboration_config.py guards the coupling.
CORROBORATION_PATH = os.environ.get("GPU_AGENT_CORROBORATION", "registry/corroboration.json")

from functools import lru_cache  # noqa: E402  (module tail, matches file's minimal style)


@lru_cache(maxsize=1)
def min_distinct_publishers() -> int:
    import json
    import pathlib
    try:
        return int(json.loads(pathlib.Path(CORROBORATION_PATH).read_text("utf-8"))
                   ["minDistinctPublishers"])
    except FileNotFoundError:
        return 3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_corroboration_config.py -q`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

Check `git log --oneline -1` first, then:

```bash
git add registry/corroboration.json gpu_agent/config.py tests/test_corroboration_config.py
git commit -m "$(cat <<'EOF'
feat(config): F63 corroboration threshold N=3, registry-tunable

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Gate F2e amendment + extraction prompt sentence + contract v1.3 migration doc

This is the contract migration — the gate rule, the prompt sentence that states it to the brain, the migration doc, and the test updates ship as ONE commit. The extract prompt hash drifts here: run the suite with `--deselect tests/test_evals_baseline_pin.py` from this task until Task 8.

**Files:**
- Modify: `gpu_agent/gate.py` (the F2e block only — currently the two lines under `# F2e — headline protection at finding level`)
- Modify: `gpu_agent/extraction/prompt.py` (the secondary-cap sentence, currently lines 23–25)
- Modify: `tests/test_gate_v12.py` (the F2e assertion at line 44 — the message now carries the count suffix)
- Modify: `tests/test_extraction_secondary_cap.py` (pins the amended sentence)
- Create: `docs/migrations/2026-07-contract-v1.3.md`
- Test: `tests/test_gate_corroboration.py`

**Interfaces:**
- Consumes: `publisher_key` (Task 1), `min_distinct_publishers` (Task 2).
- Produces: amended `check_finding` behavior — secondary-only + high confidence passes iff ≥3 distinct publishers. No signature change.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gate_corroboration.py
from gpu_agent.gate import check_finding
from gpu_agent.schema.finding import Finding, Confidence, Impact, Evidence


def _f(evidence, level="high"):
    return Finding(
        id="doc-x-1", statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level=level, basis="b"), asOf="2026-07",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="NVDA", observedAt="2026-07-01",
        capturedAt="2026-07-04T00:00:00Z", evidence=evidence)


def _sec(url):
    return Evidence(source="s", url=url, date="2026-07-01", excerpt="e", tier="secondary")


def test_three_distinct_secondary_publishers_support_high():
    f = _f([_sec("https://reuters.com/a"), _sec("https://digitimes.com/b"),
            _sec("https://tomshardware.com/c")])
    assert not [e for e in check_finding(f) if "secondary-only" in e]


def test_two_distinct_publishers_still_rejected_with_count():
    f = _f([_sec("https://reuters.com/a"), _sec("https://digitimes.com/b")])
    errs = [e for e in check_finding(f) if "secondary-only" in e]
    assert errs == ["doc-x-1: secondary-only evidence cannot support high confidence "
                    "(2 distinct publishers < 3)"]


def test_syndication_same_netloc_collapses_to_one():
    f = _f([_sec("https://reuters.com/a"), _sec("https://www.reuters.com/b"),
            _sec("https://reuters.com/c")])
    errs = [e for e in check_finding(f) if "secondary-only" in e]
    assert "(1 distinct publishers < 3)" in errs[0]


def test_medium_confidence_never_touched():
    f = _f([_sec("https://reuters.com/a")], level="medium")
    assert not [e for e in check_finding(f) if "secondary-only" in e]


def test_primary_evidence_path_unchanged():
    prim = Evidence(source="sec.gov", url="https://sec.gov/x", date="2026-07-01",
                    excerpt="e", tier="primary")
    f = _f([prim])
    assert not [e for e in check_finding(f) if "secondary-only" in e]
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_gate_corroboration.py -q`
Expected: `test_three_distinct_secondary_publishers_support_high` and `test_two_distinct_publishers_still_rejected_with_count` FAIL (old rule rejects all secondary-only high, with the old message); the other three PASS.

- [ ] **Step 3: Amend gate.py F2e**

Add to gate.py's imports (after the existing schema imports):

```python
from gpu_agent.config import min_distinct_publishers
from gpu_agent.publisher import publisher_key
```

Replace the F2e block:

```python
    # F2e — headline protection at finding level
    if f.evidence and all(e.tier == "secondary" for e in f.evidence) and f.confidence.level == "high":
        errors.append(f"{f.id}: secondary-only evidence cannot support high confidence")
```

with:

```python
    # F2e — headline protection at finding level (contract v1.3: >=N distinct publishers
    # unlock high confidence — docs/migrations/2026-07-contract-v1.3.md)
    if f.evidence and all(e.tier == "secondary" for e in f.evidence) and f.confidence.level == "high":
        n = min_distinct_publishers()
        publishers = {publisher_key(e) for e in f.evidence}
        if len(publishers) < n:
            errors.append(f"{f.id}: secondary-only evidence cannot support high confidence "
                          f"({len(publishers)} distinct publishers < {n})")
```

- [ ] **Step 4: Update the two existing test expectations**

In `tests/test_gate_v12.py` line 44, the finding under test has a single secondary evidence item, so:

```python
    assert any("secondary-only evidence cannot support high confidence" in e for e in check_finding(f))
```

still passes unchanged (substring match) — run it to confirm; only change it if it pins the exact full string.

In `tests/test_extraction_secondary_cap.py`, the assertions check the SYSTEM text lowercased; after Step 5's sentence change, update the expectations to pin BOTH halves of the amended rule (adapt to the file's existing style):

```python
def test_secondary_cap_states_corroboration_exception():
    s = SYSTEM.lower()
    assert "at most medium" in s
    assert "3 distinct publishers" in s
    assert "syndication" in s
```

- [ ] **Step 5: Amend the extraction SYSTEM sentence**

In `gpu_agent/extraction/prompt.py`, replace:

```
- A Finding whose only supporting evidence is secondary (open-web rather than an authoritative
  filing) must set confidence at most medium; only primary (filing) evidence may support high
  confidence.
```

with:

```
- A Finding whose only supporting evidence is secondary (open-web rather than an authoritative
  filing) must set confidence at most medium — unless its evidence spans at least 3 distinct
  publishers (distinct outlets, not syndication of one story), which may support high
  confidence with the corroboration named in the basis. Primary (filing) evidence always
  supports high confidence.
```

- [ ] **Step 6: Write the migration doc**

`docs/migrations/2026-07-contract-v1.3.md`:

```markdown
# Contract v1.3 migration — 2026-07-04

The second sanctioned frozen-core migration (charter Part 33; user-approved 2026-07-04 in
the F63 design — `docs/superpowers/specs/2026-07-04-f63-corroboration-doctrine-design.md`).
It amends exactly ONE rule; everything else in the frozen set is byte-identical to v1.2.

## Rule change

- **F2e** — a finding whose evidence is entirely `secondary` cannot carry `confidence=high`
  **unless its evidence spans ≥ N distinct publishers** (N=3, `registry/corroboration.json`;
  publisher identity = F31's `publisher_key`, so syndication at one domain counts once).
  Error text now names the shortfall: `(K distinct publishers < N)`.

## Deliberately unchanged

- **F3** (dimension-level cap: `dimensionStatus.confidenceCap="medium"` + note
  `"secondary-only evidence"` when a dimension's citations carry no primary) — dimension
  confidence DISPLAY stays conservative; corroboration unlocks finding confidence and
  movement, not the cap badge.
- All other v1.2 rules, the schema (`schemaVersion` stays 1.2 — no schema field changed),
  scoring, briefing, judge aggregation, pipeline, JsonStore.

## Companion doctrine (same branch, not frozen-core)

- Thesis anti-whipsaw rule 6: corroborated (≥N publishers) secondary-only reversals apply.
- Evidence-sufficiency gate (`gpu_agent/sufficiency.py`): rating/binding-constraint changes
  vs MEMORY require primary evidence or ≥N distinct publishers; reject → re-dispatch.
- Charter Part 37 amendment: the staged-trust "next increment" has landed.
```

- [ ] **Step 7: Run the affected suites**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_gate_corroboration.py tests/test_gate_v12.py tests/test_extraction_secondary_cap.py tests/test_extraction_prompt.py tests/test_prompt_vocab.py -q`
Expected: ALL PASS.
Then the full suite: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q --deselect tests/test_evals_baseline_pin.py`
Expected: all green (the extract prompt hash drift is confined to the deselected pin).

- [ ] **Step 8: Commit**

Check `git log --oneline -1` first, then:

```bash
git add gpu_agent/gate.py gpu_agent/extraction/prompt.py docs/migrations/2026-07-contract-v1.3.md tests/test_gate_corroboration.py tests/test_gate_v12.py tests/test_extraction_secondary_cap.py
git commit -m "$(cat <<'EOF'
feat(gate)!: contract v1.3 - F2e corroboration lift (3 distinct publishers unlock high)

The single sanctioned frozen-core edit of F63. Secondary-only findings may carry
high confidence iff their evidence spans >=3 distinct publishers (F31 identity;
syndication collapses). Extraction SYSTEM states the same exception (hash drifts;
eval pin deselected until the branch-final run-eval + rebaseline). Migration doc
docs/migrations/2026-07-contract-v1.3.md; F3 dimension cap deliberately unchanged.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Thesis rule 6 — corroborated secondary reversals apply

**Files:**
- Modify: `gpu_agent/thesis.py` — (a) the `_evidence_publisher` import block, (b) `_build_judgment_records` (applied condition + notes + record), (c) the `Anti-whipsaw:` sentence in `THESIS_SYSTEM`
- Modify: `tests/test_thesis_prompt.py` (anti-whipsaw sentence pin, if one exists — check `grep -n "Anti-whipsaw" tests/test_thesis_prompt.py`)
- Test: `tests/test_thesis_corroboration.py`

**Interfaces:**
- Consumes: `publisher_key` (Task 1), `min_distinct_publishers` (Task 2), existing `_publisher_domains` / `DIRECTION` / `CONVICTION_RANK` internals.
- Produces: judgment records may carry `"corroboratedStep": True`; note strings as pinned below. Task 8's eval covers the THESIS_SYSTEM drift.

- [ ] **Step 1: Write the failing tests**

Model the fixtures on `tests/test_thesis_apply.py`'s existing helpers (read that file first; reuse its `ThesisBook`/`ThesisAnswer` construction idioms — the test below shows the REQUIRED assertions, adapt the fixture plumbing to the file's local helpers):

```python
# tests/test_thesis_corroboration.py
"""F63 rule-6 amendment: a secondary-only reversal APPLIES when its cited findings span
>=3 distinct publishers (F31 key); <3 defers exactly as before, with the count visible."""
from gpu_agent.schema.finding import Finding, Confidence, Impact, Evidence
from gpu_agent.thesis import ThesisBook, ThesisEntry, ThesisAnswer, ThesisJudgment, apply_answer


def _sec(url):
    return Evidence(source="s", url=url, date="2026-07-01", excerpt="e", tier="secondary")


def _finding(fid, evidence):
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="NVDA", observedAt="2026-07-01",
        capturedAt="2026-07-04T00:00:00Z", evidence=evidence)


def _book_with_positive_last_direction():
    entry = ThesisEntry(id="t1", lens="demand", title="T1", statement="s",
                        status="registered", conviction="medium", lastVerdict="strengthened",
                        lastDirection=1, streak=1)
    return ThesisBook(category="chips.merchant-gpu", entries=[entry])


def _weaken_judgment(finding_ids):
    return ThesisAnswer(judgments=[ThesisJudgment(
        thesisId="t1", verdict="weakened", rationale="r", findingIds=finding_ids,
        mechanism="m", falsifiableTrigger="drops for 2 consecutive quarters",
        sensitivity="s")], proposed=[])


def test_corroborated_secondary_reversal_applies():
    fbi = {"f1": _finding("f1", [_sec("https://reuters.com/a")]),
           "f2": _finding("f2", [_sec("https://digitimes.com/b")]),
           "f3": _finding("f3", [_sec("https://tomshardware.com/c")])}
    book, records, notes = apply_answer(
        _book_with_positive_last_direction(), _weaken_judgment(["f1", "f2", "f3"]),
        as_of="2026-07-04", findings_by_id=fbi, history=[])
    rec = next(r for r in records if r.get("thesisId") == "t1" and "verdict" in r)
    assert rec["applied"] is True
    assert rec["corroboratedStep"] is True
    assert rec["note"] == ("t1: applied: corroborated secondary reversal "
                           "(3 distinct publishers; pending filing checkpoint)")
    assert rec["conviction"] == "low"          # medium weakened -> low (bounded -1)


def test_two_publisher_reversal_still_defers_with_count():
    fbi = {"f1": _finding("f1", [_sec("https://reuters.com/a")]),
           "f2": _finding("f2", [_sec("https://www.reuters.com/b")]),   # syndication: same key
           "f3": _finding("f3", [_sec("https://digitimes.com/c")])}
    book, records, notes = apply_answer(
        _book_with_positive_last_direction(), _weaken_judgment(["f1", "f2", "f3"]),
        as_of="2026-07-04", findings_by_id=fbi, history=[])
    rec = next(r for r in records if r.get("thesisId") == "t1" and "verdict" in r)
    assert rec["applied"] is False
    assert rec["corroboratedStep"] is False
    assert rec["note"] == "t1: deferred: secondary-only reversal (2 distinct publishers < 3)"
    assert rec["conviction"] == "medium"       # unchanged


def test_primary_reversal_unaffected_no_corroborated_flag():
    prim = Evidence(source="sec.gov", url="https://sec.gov/x", date="2026-07-01",
                    excerpt="e", tier="primary")
    fbi = {"f1": _finding("f1", [prim])}
    book, records, notes = apply_answer(
        _book_with_positive_last_direction(), _weaken_judgment(["f1"]),
        as_of="2026-07-04", findings_by_id=fbi, history=[])
    rec = next(r for r in records if r.get("thesisId") == "t1" and "verdict" in r)
    assert rec["applied"] is True
    assert rec["corroboratedStep"] is False    # primary applied it, not corroboration
```

If `ThesisEntry`/`ThesisBook`/`ThesisAnswer`/`ThesisJudgment` constructor fields differ (check the actual models at the top of `gpu_agent/thesis.py`), adapt the fixtures — the ASSERTIONS are the contract.

- [ ] **Step 2: Run to verify failure**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_thesis_corroboration.py -q`
Expected: first test FAILS (`applied is False` under the old rule; `corroboratedStep` KeyError).

- [ ] **Step 3: Amend thesis.py**

(a) Replace the whole `try: … from gpu_agent.wiki.lifecycle import _publisher_key as _evidence_publisher … except ImportError: …` block (including the fallback def) with:

```python
# F31 identity — shared module (gpu_agent/publisher.py) since F63; wiki/lifecycle re-exports
# the same object, so the two publisher-identity notions can never drift.
from gpu_agent.publisher import publisher_key as _evidence_publisher
from gpu_agent.config import min_distinct_publishers
```

(b) In `_build_judgment_records`, replace:

```python
    applied = (
        confirmed_by_pending
        or not is_reversal
        or _has_primary(judgment.findingIds, findings_by_id)
    )
```

with:

```python
    has_primary = _has_primary(judgment.findingIds, findings_by_id)
    # F63 rule-6 amendment: a corroborated secondary-only reversal (>=N distinct
    # publishers across the cited findings — `domains` is already the F31 key set)
    # applies instead of deferring; the next filing remains the confirm/deny checkpoint.
    corroborated_step = (
        is_reversal and not confirmed_by_pending and not has_primary
        and len(domains) >= min_distinct_publishers()
    )
    applied = confirmed_by_pending or not is_reversal or has_primary or corroborated_step
```

and replace the applied/deferred note block:

```python
    if applied:
        ...
        note = f"{entry.id}: {verdict} applied, conviction {entry.conviction}->{new_conviction}"
        extra_note = None
    else:
        new_conviction = entry.conviction
        note = f"{entry.id}: deferred: secondary-only reversal"
        extra_note = note
```

with:

```python
    if applied:
        if verdict == "broken":
            new_conviction = "low"
        elif verdict == "strengthened":
            new_conviction = _bump_conviction(entry.conviction, +1)
        elif verdict == "weakened":
            new_conviction = _bump_conviction(entry.conviction, -1)
        else:  # reaffirmed / adjusted: unchanged
            new_conviction = entry.conviction
        if corroborated_step:
            note = (f"{entry.id}: applied: corroborated secondary reversal "
                    f"({len(domains)} distinct publishers; pending filing checkpoint)")
            extra_note = note          # checkpoint steps are never silent
        else:
            note = f"{entry.id}: {verdict} applied, conviction {entry.conviction}->{new_conviction}"
            extra_note = None
    else:
        new_conviction = entry.conviction
        note = (f"{entry.id}: deferred: secondary-only reversal "
                f"({len(domains)} distinct publishers < {min_distinct_publishers()})")
        extra_note = note
```

(c) Add to the record dict (after `"publisherDomains": domains,`):

```python
        "corroboratedStep": corroborated_step,
```

(d) In `THESIS_SYSTEM`, replace:

```
Anti-whipsaw: a reversal without primary evidence is recorded but not applied — judge honestly regardless of that consequence; do not soften a verdict merely because you lack primary evidence for it.
```

with:

```
Anti-whipsaw: a reversal without primary evidence is recorded but not applied unless its cited findings span at least 3 distinct publishers — judge honestly regardless of that consequence; do not soften a verdict merely because you lack primary or corroborated evidence for it.
```

- [ ] **Step 4: Run the thesis suites**

Existing deferral tests pin the OLD note text — `grep -rn "deferred: secondary-only reversal" tests/` and update any exact-string assertions to the new counted form (e.g. `tests/test_thesis_apply.py` section "c" — a single-publisher reversal now reads `(1 distinct publishers < 3)`).

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_thesis_corroboration.py tests/test_thesis_apply.py tests/test_thesis_prompt.py tests/test_prompt_vocab.py -q`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

Check `git log --oneline -1` first, then:

```bash
git add gpu_agent/thesis.py tests/test_thesis_corroboration.py tests/test_thesis_apply.py tests/test_thesis_prompt.py
git commit -m "$(cat <<'EOF'
feat(thesis): F63 rule 6 - corroborated secondary reversals apply

>=3 distinct publishers (F31 key, already recorded as publisherDomains) across a
reversal's cited findings now apply it instead of deferring; the record carries
corroboratedStep + a pending-filing-checkpoint note, deferrals show the count.
THESIS_SYSTEM anti-whipsaw sentence states the exception (hash drifts; pin
deselected until the branch-final rebaseline).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `gpu_agent/sufficiency.py` — the evidence-sufficiency check (pure)

**Files:**
- Create: `gpu_agent/sufficiency.py`
- Test: `tests/test_sufficiency.py`

**Interfaces:**
- Consumes: `publisher_key` (Task 1), `min_distinct_publishers` (Task 2), `MemoryBundle` (existing, `gpu_agent/memory.py`: `.priorRatings: dict[dim -> {rating, direction, confidence}]`, `.priorCategoryStatus: Optional[dict]` with key `bottleneck`).
- Produces: `check_sufficiency(raw_answers: list, memory, findings_by_id: dict[str, Finding]) -> list[str]` — violations, `sample {i+1}: `-prefixed like `_voice_lint_samples`. Task 6 wires it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sufficiency.py
import json
from types import SimpleNamespace
from gpu_agent.schema.finding import Finding, Confidence, Impact, Evidence
from gpu_agent.sufficiency import check_sufficiency


def _ev(url, tier="secondary"):
    return Evidence(source="s", url=url, date="2026-07-01", excerpt="e", tier=tier)


def _finding(fid, evidence):
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="NVDA", observedAt="2026-07-01",
        capturedAt="2026-07-04T00:00:00Z", evidence=evidence)


def _memory(ratings, bottleneck="bottleneck"):
    return SimpleNamespace(
        priorRatings={d: {"rating": r, "direction": "steady", "confidence": "medium"}
                      for d, r in ratings.items()},
        priorCategoryStatus={"bottleneck": bottleneck})


def _answer(dimensions, bottleneck="bottleneck"):
    return json.dumps({
        "dimensions": {d: {"rating": r, "direction": "steady", "findingIds": ids,
                           "rationale": "x"} for d, (r, ids) in dimensions.items()},
        "categoryStatus": {"rating": "Strong", "direction": "steady",
                           "bottleneck": bottleneck, "reason": "x"},
        "narrative": "One. Two. Three."})


FBI = {
    "prim": _finding("prim", [_ev("https://sec.gov/x", tier="primary")]),
    "s1": _finding("s1", [_ev("https://reuters.com/a")]),
    "s2": _finding("s2", [_ev("https://digitimes.com/b")]),
    "s3": _finding("s3", [_ev("https://tomshardware.com/c")]),
}


def test_no_memory_is_inert():
    ans = _answer({"momentum": ("Very strong", ["s1"])})
    assert check_sufficiency([ans], None, FBI) == []


def test_unchanged_rating_never_checked():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Strong", [])})       # unchanged, zero citations: fine
    assert check_sufficiency([ans], mem, FBI) == []


def test_primary_backed_change_passes():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["prim"])})
    assert check_sufficiency([ans], mem, FBI) == []


def test_three_publisher_change_passes():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["s1", "s2", "s3"])})
    assert check_sufficiency([ans], mem, FBI) == []


def test_two_publisher_change_fails_with_exact_line():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["s1", "s2"])})
    assert check_sufficiency([ans], mem, FBI) == [
        "sample 1: momentum: rating changed Strong->Very strong with insufficient "
        "evidence (no primary; 2 distinct publishers < 3)"]


def test_dimension_without_prior_is_exempt():
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Strong", []), "moat": ("Weak", ["s1"])})
    assert check_sufficiency([ans], mem, FBI) == []


def test_bottleneck_change_checks_new_dimension():
    mem = _memory({"momentum": "Strong", "moat": "Mixed"}, bottleneck="momentum")
    ans = _answer({"momentum": ("Strong", []), "moat": ("Mixed", ["s1", "s2"])},
                  bottleneck="moat")
    assert check_sufficiency([ans], mem, FBI) == [
        "sample 1: categoryStatus.bottleneck: changed momentum->moat with insufficient "
        "evidence (no primary; 2 distinct publishers < 3)"]


def test_multi_sample_prefixes():
    mem = _memory({"momentum": "Strong"})
    good = _answer({"momentum": ("Strong", [])})
    bad = _answer({"momentum": ("Very strong", ["s1"])})
    violations = check_sufficiency([good, bad], mem, FBI)
    assert len(violations) == 1 and violations[0].startswith("sample 2: ")
```

- [ ] **Step 2: Run to verify failure**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_sufficiency.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.sufficiency'`

- [ ] **Step 3: Implement**

```python
# gpu_agent/sufficiency.py
"""F63 evidence-sufficiency gate — the deterministic counterweight to the corroboration
doctrine: corroborated news can move ratings, insufficient news cannot.

Rule: changing a dimension RATING (vs the prior cycle's MEMORY state) or the
categoryStatus.bottleneck requires the changed item's cited findings to include primary
evidence or span >= N distinct publishers (F31 key; N from registry/corroboration.json).

Deliberate scope (spec): rating + binding-constraint changes only — direction-only and
constraintLabel/prose changes never trigger; a dimension with no prior rating is exempt;
no MEMORY at all -> inert. Violations are gate failures: the caller re-dispatches the
judge brain with the violations appended (never edits the answer)."""
from __future__ import annotations
import json

from gpu_agent.config import min_distinct_publishers
from gpu_agent.publisher import publisher_key


def _sufficient(finding_ids, findings_by_id, n) -> tuple[bool, int]:
    """(passes, distinct-publisher count). Primary anywhere passes outright. Unresolvable
    ids contribute nothing — citation validity against the briefing is the aggregator's
    job, not this gate's."""
    evs = [e for fid in finding_ids if fid in findings_by_id
           for e in findings_by_id[fid].evidence]
    publishers = {publisher_key(e) for e in evs}
    if any(e.tier == "primary" for e in evs):
        return True, len(publishers)
    return len(publishers) >= n, len(publishers)


def check_sufficiency(raw_answers: list, memory, findings_by_id) -> list[str]:
    """`raw_answers` is the recorded-samples list (each item a JudgmentResult JSON string,
    RecordedClient's replay shape — same input contract as cli._voice_lint_samples).
    `memory` is the MemoryBundle the emitted prompt carried, or None (-> inert)."""
    if memory is None:
        return []
    n = min_distinct_publishers()
    prior_ratings = memory.priorRatings or {}
    prior_bottleneck = (memory.priorCategoryStatus or {}).get("bottleneck")
    violations: list[str] = []
    for i, raw in enumerate(raw_answers):
        sample = json.loads(raw)
        prefix = f"sample {i + 1}: "
        dims = sample.get("dimensions") or {}
        for dim, d in dims.items():
            prior = prior_ratings.get(dim)
            if prior is None or d.get("rating") == prior.get("rating"):
                continue
            ok, count = _sufficient(d.get("findingIds") or [], findings_by_id, n)
            if not ok:
                violations.append(
                    prefix + f"{dim}: rating changed {prior.get('rating')}->"
                    f"{d.get('rating')} with insufficient evidence "
                    f"(no primary; {count} distinct publishers < {n})")
        status = sample.get("categoryStatus") or {}
        new_bottleneck = status.get("bottleneck")
        if prior_bottleneck and new_bottleneck and new_bottleneck != prior_bottleneck:
            ids = (dims.get(new_bottleneck) or {}).get("findingIds") or []
            ok, count = _sufficient(ids, findings_by_id, n)
            if not ok:
                violations.append(
                    prefix + f"categoryStatus.bottleneck: changed {prior_bottleneck}->"
                    f"{new_bottleneck} with insufficient evidence "
                    f"(no primary; {count} distinct publishers < {n})")
    return violations
```

- [ ] **Step 4: Run to verify pass**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_sufficiency.py -q`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

Check `git log --oneline -1` first, then:

```bash
git add gpu_agent/sufficiency.py tests/test_sufficiency.py
git commit -m "$(cat <<'EOF'
feat(sufficiency): F63 evidence-sufficiency check (pure)

Rating/binding-constraint changes vs MEMORY require primary evidence or >=3
distinct publishers among the cited findings; sample-prefixed violations,
None-memory inert, prior-less dimensions exempt.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Wire the sufficiency gate at both CLI seams + judge SYSTEM sentence

**Files:**
- Modify: `gpu_agent/cli.py` — `_judge` recorded block, `_pipeline` recorded-judge block, `_report_voice_violations`-adjacent new reporter, `jg`/`pl` parsers (`--no-sufficiency`)
- Modify: `gpu_agent/judgment/prompt.py` — one sentence appended to `_SYSTEM_TEMPLATE`
- Modify: `tests/test_judgment_prompt.py` — pin the new sentence
- Test: `tests/test_cli_sufficiency.py`

**Interfaces:**
- Consumes: `check_sufficiency` (Task 5), existing `build_memory_bundle` / `render_memory_text` / `IndicatorHorizons` / `_load_registry` / `RecordedClient` plumbing in cli.py.
- Produces: `sufficiency: `-prefixed stderr lines + exit 1 at both seams; `--no-sufficiency` opt-out flag on `judge` and `pipeline`.

**Critical invariant (F62 precedent):** the gate must read the SAME memory source the emitted prompt carried — `build_memory_bundle(store_root, category, as_of, registry, horizons)`. In `judge --recorded` that is `args.store` + `findings[0].asOf`; in `pipeline --recorded-judge` it is `args.corpus_store` (None → inert, matching the pre-F62 no-memory pipeline).

- [ ] **Step 1: Write the failing CLI test**

Model store seeding and pipeline invocation on `tests/test_cli_pipeline_corpus.py` (read it first; reuse its recorded-judge fixture idioms). Required behaviors:

```python
# tests/test_cli_sufficiency.py  (skeleton of REQUIRED assertions; adapt fixture
# plumbing from tests/test_cli_pipeline_corpus.py's helpers)
def test_judge_recorded_rejects_undersourced_rating_change(tmp_path, capsys, monkeypatch):
    # store with a prior scorecard whose momentum rating is "Strong"; recorded answer
    # changes momentum to "Very strong" citing one finding with a single secondary
    # evidence item -> exit 1 and a "sufficiency: sample 1: momentum: rating changed
    # Strong->Very strong" line on stderr.
    ...


def test_judge_recorded_passes_with_primary_citation(tmp_path, capsys, monkeypatch):
    # same setup, but the cited finding carries primary evidence -> exit 0.
    ...


def test_no_sufficiency_flag_skips_gate(tmp_path, capsys, monkeypatch):
    # same failing setup + --no-sufficiency -> exit 0 (legacy fixtures escape hatch).
    ...


def test_judge_recorded_without_prior_scorecard_is_inert(tmp_path, capsys, monkeypatch):
    # empty store (no prior scorecard) -> build_memory_bundle returns None -> exit 0.
    ...
```

Each `...` must become a real test in implementation — seed `tmp_path/store` with (or without) a prior scorecard exactly the way the memory tests do (`grep -rn "build_memory_bundle" tests/` for the seeding idiom), write the findings JSON and a recorded single-sample answer file, invoke the CLI via its `main()`/subprocess idiom used in the neighboring CLI tests, and assert exit code + stderr content.

- [ ] **Step 2: Run to verify failure**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_cli_sufficiency.py -q`
Expected: FAIL — `unrecognized arguments: --no-sufficiency` (or the missing `sufficiency:` line), proving the wiring doesn't exist.

- [ ] **Step 3: Wire cli.py**

(a) Import at the top with the other gpu_agent imports: `from gpu_agent.sufficiency import check_sufficiency`.

(b) Next to `_report_voice_violations`, add:

```python
def _report_sufficiency_violations(violations: list[str]) -> int:
    """Print every F63 evidence-sufficiency violation (one `sufficiency: ` line each --
    the run-cycle skill greps that prefix, same re-dispatch loop as `voice-lint: `)
    and return the shared failure exit code."""
    for v in violations:
        print(f"sufficiency: {v}", file=sys.stderr)
    return 1
```

(c) In `_judge`, hoist `registry, _ = _load_registry()` to ABOVE the `if args.recorded:` block (it currently sits below; hoisting is behavior-neutral — `judge_findings` uses it either way). Then, inside the recorded block, immediately after the voice-lint check, add:

```python
        # F63: evidence-sufficiency gate — rating/bottleneck changes vs the SAME
        # prior-cycle MEMORY the emitted prompt carried need primary or >=N-publisher
        # citations. No prior scorecard -> memory is None -> inert.
        if not args.no_sufficiency:
            horizons = IndicatorHorizons.load(REGISTRY_PATH)
            memory = build_memory_bundle(args.store, args.category, findings[0].asOf,
                                         registry, horizons)
            violations = check_sufficiency(answers, memory, {f.id: f for f in findings})
            if violations:
                return _report_sufficiency_violations(violations)
```

(`IndicatorHorizons`, `REGISTRY_PATH`, `build_memory_bundle` are already imported in cli.py — verify with grep; add any missing import alongside its siblings.)

(d) In `_pipeline`'s `--recorded-judge` block, immediately after its voice-lint check, add:

```python
        # F63: same sufficiency gate at the pipeline seam. Memory comes from the F62
        # corpus store when provided (the live cycle always passes --corpus-store);
        # without it there is no prior-state source here -> inert, matching the
        # memory-less legacy pipeline.
        if not args.no_sufficiency:
            memory = None
            if args.corpus_store:
                horizons = IndicatorHorizons.load(REGISTRY_PATH)
                memory = build_memory_bundle(args.corpus_store, args.category,
                                             as_of, registry, horizons)
            violations = check_sufficiency(judge_answers, memory,
                                           {f.id: f for f in findings})
            if violations:
                return _report_sufficiency_violations(violations)
```

(Verify the local variable names in `_pipeline` — `as_of`, `registry`, `findings`, `judge_answers` — against the actual code at the seam; the F62 corpus block established `findings` as the MERGED corpus there, which is exactly the findings_by_id the judge's citations resolve against.)

(e) Parsers: after `jg.add_argument("--no-voice-lint", …)` add

```python
    jg.add_argument("--no-sufficiency", action="store_true",
                    help="skip the F63 evidence-sufficiency gate (legacy recorded fixtures)")
```

and after `pl.add_argument("--no-voice-lint", …)` add the identical `pl.add_argument("--no-sufficiency", …)`.

- [ ] **Step 4: Judge SYSTEM sentence + pin**

In `gpu_agent/judgment/prompt.py` `_SYSTEM_TEMPLATE`, replace:

```
When a MEMORY section is present, judge direction (improving|steady|worsening) relative to that prior state.
```

with:

```
When a MEMORY section is present, judge direction (improving|steady|worsening) relative to that prior state.
Changing a dimension rating or the binding constraint versus that prior state requires cited
findings with a primary source or at least 3 distinct publishers; otherwise keep the prior rating.
```

Append to `tests/test_judgment_prompt.py`:

```python
def test_system_states_sufficiency_rule():
    flat = " ".join(SYSTEM.split())
    assert ("Changing a dimension rating or the binding constraint versus that prior state "
            "requires cited findings with a primary source or at least 3 distinct publishers; "
            "otherwise keep the prior rating.") in flat
```

- [ ] **Step 5: Run the affected suites**

Run: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest tests/test_cli_sufficiency.py tests/test_judgment_prompt.py tests/test_cli_pipeline_corpus.py tests/test_constraint_label.py -q`
Expected: ALL PASS (the F62 pipeline-corpus tests stay green: their seeded stores carry no prior scorecard → the gate is inert there).
Then full suite: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q --deselect tests/test_evals_baseline_pin.py`
Expected: green.

- [ ] **Step 6: Commit**

Check `git log --oneline -1` first, then:

```bash
git add gpu_agent/cli.py gpu_agent/judgment/prompt.py tests/test_cli_sufficiency.py tests/test_judgment_prompt.py
git commit -m "$(cat <<'EOF'
feat(cli): F63 sufficiency gate wired at judge --recorded + pipeline --recorded-judge

Same seams and re-dispatch loop as the F67 voice lint; memory read from the same
source the emitted prompt carried (args.store / --corpus-store; none -> inert);
--no-sufficiency escape hatch; judge SYSTEM announces the rule (hash drifts; pin
deselected until the branch-final rebaseline).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Doctrine docs — charter Part 37 amendment, gather blob `chase` field, skill/web-reach notes

Docs only; no code. Re-read each file section immediately before editing (concurrent instances).

**Files:**
- Modify: `docs/agent-swarm-charter.md` (Part 37, the "Trust, not just retrieval" paragraph, ~line 1565)
- Modify: `.claude/skills/gather-category/SKILL.md` (blob contract + chase recording, ~lines 106 and 118–124)
- Modify: `docs/web-reach.md` (~line 28–30, the "Scoring of corroboration is F63" note)
- Modify: `.claude/skills/run-cycle/SKILL.md` (judge re-dispatch loop: add the `sufficiency:` prefix beside `voice-lint:` — grep for `voice-lint` to find the spot)

- [ ] **Step 1: Charter Part 37 amendment**

In the "Trust, not just retrieval" paragraph, replace the two sentences:

```
Hard multi-source **corroboration**
("did ≥2 independent sources agree?") is the next increment, not v1 — so **until it lands, gathered
open-web findings stay confidence-capped and may not move the headline status.**
```

with:

```
Hard multi-source **corroboration** landed as **F63 (contract v1.3)**: **three distinct
publishers** (F31 netloc identity — syndication of one story counts once), within the corpus
window, unlock **one bounded step** — a corroborated secondary-only finding may carry high
confidence (gate F2e), a corroborated secondary-only thesis reversal applies instead of
deferring (rule 6), and a judge may change a dimension rating or the binding constraint only
with primary or ≥3-publisher citations (the deterministic **evidence-sufficiency gate** —
the tightening half that ships with the loosening half). Every corroborated step is logged
with its publisher set and a pending-filing-checkpoint note; **the next filing remains the
confirm/deny checkpoint** (re-judged as ordinary business, no auto-resolve). The dimension-level
F3 confidence-cap badge stays conservative on secondary-only citations.
```

(Keep the following sentence — "This is a *staged* path to Part 26's hard-corroboration requirement…" — updating "in the meantime" phrasing if it now reads stale.)

- [ ] **Step 2: Gather blob contract**

In `.claude/skills/gather-category/SKILL.md`, change the blob shape line to:

```
`{"blobs": [{"source","url","date","entity","content","chase"?}], "leads": ["<url-or-query>", ...]}`.
```

and replace the tail of the chase instruction "— record in the blob whether a primary source or an independent corroboration was found." with:

```
— record the result in the blob's structured `chase` field:
`"chase": {"attempted": true, "primaryFound": "<url>"|null, "corroborators": ["<url>", ...]}`
(F63). Each corroborator you found must ALSO be fetched as its own raw blob — corroboration
only counts when the corroborating page itself enters the corpus (extraction forbids evidence
URLs other than the document's own; the L2 dedup merge is what unions publishers onto one
finding). The `chase` field is bookkeeping for the coordinator's cap/skip log; scoring reads
only the merged findings' evidence.
```

- [ ] **Step 3: web-reach.md + run-cycle SKILL.md notes**

`docs/web-reach.md`: replace "(Scoring of corroboration is F63," (and through the closing of that parenthetical) with "(Corroboration scoring landed as F63: 3 distinct publishers = one bounded step; record the chase result in the blob's `chase` field and fetch corroborators as their own blobs.)".

`.claude/skills/run-cycle/SKILL.md`: wherever the judge `--recorded` / `--recorded-judge` failure loop names `voice-lint:` lines, add that `sufficiency: ` lines are handled identically — re-dispatch the judge brain with the violation lines appended ("fix these violations; change nothing else" is NOT the right instruction here — the correct re-dispatch says: keep every rating you can justify; for the flagged changes, either cite findings meeting the bar or keep the prior rating).

- [ ] **Step 4: Commit**

Check `git log --oneline -1` first, then:

```bash
git add docs/agent-swarm-charter.md .claude/skills/gather-category/SKILL.md docs/web-reach.md .claude/skills/run-cycle/SKILL.md
git commit -m "$(cat <<'EOF'
docs(doctrine): F63 charter Part 37 amendment + structured chase field + skill wiring

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: run-eval + rebaseline (SESSION-LEVEL — do not dispatch to a subagent)

All three prompt hashes drifted (extract Task 3, thesis Task 4, judge Task 6). Follow `.claude/skills/run-eval/SKILL.md` exactly, from the worktree root, run directory `work/eval-f63-2026-07-04/`:

- [ ] emit-brain → dispatch 14 tool-less Opus brains (one per case, F38 pairs get the identical prompt as separate generations) → save per-case answers → record-brain; re-dispatch any voice-lint violator with ONLY its violations appended ("fix these violations; change nothing else").
- [ ] emit-grade → dispatch the 18 graders (14 fresh positives + 4 frozen negatives) → record-grade `--as-of 2026-07-04`.
- [ ] Incumbents (F62 baseline): extract 6.75 / judge 7.50 / thesis 6.00; ties pass; calibration negatives ≤ 4 each.
- [ ] **Pre-committed disposition (write it in RUN-NOTES.md BEFORE the first record-grade):** PASS → `gpu-agent eval rebaseline --out work/eval-f63-2026-07-04 --as-of 2026-07-04 --reason "F63 corroboration doctrine: F2e exception + thesis anti-whipsaw exception + judge sufficiency rule"` and commit the new `fixtures/evals/baseline.json` with RUN-NOTES. One FAIL → diagnose per-case against the baseline, run ONE full replication. Two FAILs → STOP, keep the pin red, record BLOCKED-on-user with both runs' data. NOT retry-until-green.
- [ ] After rebaseline: FULL suite, no deselects — `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q` must be all green.

---

## Final verification (before the whole-branch review)

- [ ] Frozen-core check: `git diff main -- gpu_agent/scoring.py gpu_agent/schema gpu_agent/judgment/briefing.py gpu_agent/judgment/judge.py gpu_agent/pipeline.py` prints NOTHING; `git diff main -- gpu_agent/gate.py` shows ONLY the F2e hunk (+2 imports).
- [ ] `registry/corroboration.json` is the only place the number 3 exists as data; prompts' "3" pinned by tests.
- [ ] Full suite green (incl. the pin, post-rebaseline).
- [ ] Final whole-branch review (opus) with the review package from the branch's merge-base; ONE fix subagent for any Critical/Important findings; MERGE WAITS FOR THE USER.

## Self-Review

- Spec coverage: doctrine/N/checkpoint (Tasks 2, 4, 7), publisher module (1), F2e + extraction sentence + migration doc (3), rule 6 + thesis sentence (4), sufficiency module (5) + wiring/judge sentence/opt-out (6), F69 chase field + Part 37 + run-cycle loop (7), eval (8), F3 untouched (Global Constraints + migration doc). No gaps.
- Placeholders: Task 6 Step 1 uses `...` skeletons deliberately annotated as "adapt fixture plumbing from tests/test_cli_pipeline_corpus.py" with the required assertions spelled out — the implementer must write real bodies; everything else carries complete code.
- Type consistency: `publisher_key(evidence)` / `min_distinct_publishers()` / `check_sufficiency(raw_answers, memory, findings_by_id)` used identically in Tasks 1/2/3/4/5/6.
