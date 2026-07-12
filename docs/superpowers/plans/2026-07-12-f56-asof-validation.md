# F56 — `--as-of` seam validation + two cosmetic minors — Implementation Plan

> **For agentic workers:** Executed inline by the F56 lane agent via
> superpowers:test-driven-development, task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close the two remaining `--as-of` CLI seams (corpus, eval) with shape
validation, fix the `build_system(price_indicators=[])` malformed-sentence rendering, and
pin all of it with tests — while keeping default emitted brain prompts byte-identical.

**Architecture:** Extend the existing argparse-type validator `_as_of` in `cli.py`
additively (no new module; `gpu_agent/asof.py` untouched to avoid the F78 stage-6 CLI
lane). Part (b) is already shipped by `0547aea` — verify only.

**Tech Stack:** Python 3, argparse, pytest, subprocess CLI tests.

## Global Constraints

- Frozen core NEVER edited: `gate.py`, `scoring.py`, `schema/*`, `judgment/briefing.py`,
  `judge.py` aggregation, `pipeline.py`, `sufficiency.py`, JsonStore; nothing under `store/`.
- Default emitted brain prompts byte-identical; `tests/test_evals_baseline_pin.py` must stay
  green at every commit. If it goes red, STOP and report; never touch `fixtures/evals/baseline.json`.
- `--as-of` accepted shape: `^\d{4}-\d{2}(-\d{2})?$`. Reject loud, naming the flag + shape.
- Baseline suite: 1200 passed / 5 skipped. Green at every commit.
- Python from worktree: `../../.venv/Scripts/python`. Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- cli.py surface MINIMAL (F78 stage-6 overlap): two `type=` additions + one tiny helper.

---

### Task 1: Part (c) — `build_system(price_indicators=[])` renders no malformed sentence

**Files:**
- Modify: `gpu_agent/extraction/prompt.py:71` (guard `if price_indicators is not None:` → `if price_indicators:`)
- Test: `tests/test_prompt_vocab.py` (add empty-list byte-identical pin)

**Interfaces:**
- Consumes: `extraction_prompt.build_system(price_indicators=...)`, `extraction_prompt.SYSTEM`.
- Produces: no signature change; `price_indicators=[]` now yields byte-identical `SYSTEM`.

- [ ] **Step 1: Write the failing test** in `tests/test_prompt_vocab.py` after the existing
  `test_extract_system_byte_identical_without_price_indicators`:

```python
def test_extract_system_byte_identical_with_empty_price_indicators():
    # F56(c): an empty list must render nothing (no malformed "shown: ." sentence),
    # exactly like None. Unreachable by default (registry has price ids) but pinned.
    assert extraction_prompt.build_system(price_indicators=[]) == extraction_prompt.SYSTEM
```

- [ ] **Step 2: Run to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_prompt_vocab.py::test_extract_system_byte_identical_with_empty_price_indicators -q`
Expected: FAIL (rendered string ends with `...shown: .`, not equal to SYSTEM).

- [ ] **Step 3: Minimal fix** — in `gpu_agent/extraction/prompt.py`, change the guard:

```python
    if price_indicators:
```

(was `if price_indicators is not None:`). None and `[]` both skip the block; non-empty unchanged.

- [ ] **Step 4: Run tests to verify pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_prompt_vocab.py tests/test_evals_baseline_pin.py -q`
Expected: PASS (new test green; baseline pin still green — default prompt byte-identical).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/extraction/prompt.py tests/test_prompt_vocab.py
git commit  # message via heredoc, see mechanics
```

---

### Task 2: Part (a) — `corpus` seam validates `--as-of` at argparse

**Files:**
- Modify: `gpu_agent/cli.py:1086` (`co.add_argument("--as-of", required=True, ...)` gains `type=_as_of`)
- Test: `tests/test_asof_seams.py` (new file — subprocess CLI seam tests)

**Interfaces:**
- Consumes: existing `_as_of` validator (`cli.py:59`), `main()` argparse.
- Produces: `corpus --as-of <bad>` → exit 2, stderr names `--as-of`.

- [ ] **Step 1: Write the failing test** — create `tests/test_asof_seams.py`:

```python
"""F56(a): --as-of shape is rejected loud at every CLI seam. Driven via subprocess
(real argparse entry point) so we observe the actual exit code + stderr."""
import subprocess
import sys

import pytest

PY = sys.executable
BAD = ["2026/07/03", "20260703", "2026-7-3", "", "2026-07-3"]


def _run(*args):
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True, text=True)


@pytest.mark.parametrize("bad", BAD)
def test_corpus_rejects_bad_as_of(bad):
    proc = _run("corpus", "--category", "chips.merchant-gpu", "--as-of", bad)
    assert proc.returncode == 2, f"expected reject of {bad!r}; stderr={proc.stderr!r}"
    assert "--as-of" in proc.stderr


@pytest.mark.parametrize("good", ["2026-07", "2026-07-03"])
def test_corpus_accepts_good_as_of_shape(good):
    # A good shape passes the seam; coverage mode over an empty store returns 0.
    proc = _run("corpus", "--category", "chips.merchant-gpu", "--store", "store", "--as-of", good)
    assert "--as-of" not in proc.stderr, f"good shape {good!r} rejected: {proc.stderr!r}"
    assert proc.returncode != 2, f"good shape {good!r} hit argparse error: {proc.stderr!r}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_asof_seams.py -k corpus -q`
Expected: the `test_corpus_rejects_bad_as_of` cases for non-empty bad shapes FAIL (corpus
currently reaches `period_end` → exit 1, not exit 2). Empty `""` already fails
(required arg). Establishes the gap.

- [ ] **Step 3: Minimal fix** — `gpu_agent/cli.py`, corpus verb:

```python
    co.add_argument("--as-of", required=True, type=_as_of, help="run vintage (YYYY-MM or YYYY-MM-DD)")
```

- [ ] **Step 4: Run to verify pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_asof_seams.py -k corpus -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/cli.py tests/test_asof_seams.py
git commit  # heredoc
```

---

### Task 3: Part (a) — `eval` seam validates non-empty `--as-of`, preserves `""` sentinel

**Files:**
- Modify: `gpu_agent/cli.py` (add `_as_of_opt` helper next to `_as_of`; `ev.add_argument("--as-of", ...)` gains `type=_as_of_opt`)
- Test: `tests/test_asof_seams.py` (add eval cases)

**Interfaces:**
- Consumes: existing `_AS_OF_RE`, `_as_of`.
- Produces: `_as_of_opt(s) -> str` — returns `""` unchanged, else delegates to `_as_of`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_asof_seams.py`:

```python
def test_eval_rejects_bad_as_of_when_supplied(tmp_path):
    # record-grade needs a run dir; a bad --as-of must die at the argparse seam first.
    proc = _run("eval", "record-grade", "--out", str(tmp_path), "--as-of", "2026/07/03")
    assert proc.returncode == 2, f"stderr={proc.stderr!r}"
    assert "--as-of" in proc.stderr


def test_eval_empty_as_of_sentinel_preserved(tmp_path):
    # emit-brain does not require --as-of; the empty default must still parse (no crash
    # from argparse applying the type to the "" default).
    proc = _run("eval", "emit-brain", "--out", str(tmp_path))
    # It may fail later for its own reasons, but NOT at the --as-of argparse seam.
    assert not (proc.returncode == 2 and "--as-of" in proc.stderr), \
        f"empty sentinel wrongly rejected: {proc.stderr!r}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_asof_seams.py -k eval -q`
Expected: `test_eval_rejects_bad_as_of_when_supplied` FAILs (eval currently accepts any string).

- [ ] **Step 3: Minimal fix** — `gpu_agent/cli.py`. Add after `_as_of`:

```python
def _as_of_opt(s: str) -> str:
    # eval's --as-of is optional (default "" = not supplied); validate shape only when set.
    return s if s == "" else _as_of(s)
```

And the eval arg:

```python
    ev.add_argument("--as-of", default="", type=_as_of_opt,
                    help="required for record-grade (report provenance)")
```

- [ ] **Step 4: Run to verify pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_asof_seams.py -q`
Expected: PASS (all seam tests).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/cli.py tests/test_asof_seams.py
git commit  # heredoc
```

---

### Task 4: Part (b) verify + full-suite verification

**Files:**
- Verify only: `gpu_agent/thesis.py:385-389`, `tests/test_seed_thesis_lint.py:33-36`.

- [ ] **Step 1** Confirm the corrected comment is present in both files (already shipped by
  `0547aea`) and `tests/test_seed_thesis_lint.py::test_seed_depth_fields_non_empty` exists.
- [ ] **Step 2** Run the full suite:

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: 1203 passed / 5 skipped (baseline 1200 + the new seam/prompt tests), 0 failed,
`test_evals_baseline_pin.py` green.

- [ ] **Step 3** Push branch: `git push -u origin f56-asof-validation` (already pushed after task 1).

## Self-Review

- **Spec coverage:** (a) corpus → Task 2; (a) eval → Task 3; (b) → Task 4 verify; (c) → Task 1. All covered.
- **Placeholder scan:** none.
- **Type consistency:** `_as_of`, `_as_of_opt`, `build_system(price_indicators=...)`, `SYSTEM` used consistently.
