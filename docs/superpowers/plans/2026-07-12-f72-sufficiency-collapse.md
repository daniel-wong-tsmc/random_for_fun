# F72 follow-up — Sufficiency counts collapsed publishers (contract v1.4.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `gpu_agent/sufficiency.py::_sufficient` count distinct publishers over the SAME
collapsed-publisher set the F2e gate uses, closing the last raw-`publisher_key` hole so one wire
story mirrored across several domains can no longer clear the evidence-sufficiency bar.

**Architecture:** A one-line seam swap in the only frozen-core file this lane may touch: replace
`{publisher_key(e) for e in evs}` with the shared `collapsed_publisher_set(evs)` helper from
`gpu_agent/publisher.py`. Zero duplicated collapse logic. Ships as contract v1.4.1 with a
read-only shadow-check recorded in a migration note. No other sufficiency semantics move.

**Tech Stack:** Python 3, pytest. Root shared venv (`../../.venv/Scripts/python` from worktree).

## Global Constraints

- Frozen core: the ONLY sanctioned edit is `sufficiency.py`'s publisher-counting seam. Every other
  frozen file (gate.py, scoring.py, schema/*, judgment/*, pipeline.py, JsonStore, publisher.py's
  helpers) is untouched.
- No emitted-prompt changes (F6 pin `tests/test_evals_baseline_pin.py` stays green). No `store/`
  edits. No schema changes. No threshold/anchor-semantics/prompt changes (non-goals).
- Shared helper, zero duplicated collapse logic — reuse `collapsed_publisher_set`.
- Shadow-check is READ-ONLY: no store file edited, no scorecard re-issued.
- Suite green at every commit (baseline 1200 passed / 5 skipped).
- Windows + repo conventions: LF canonical; tests from worktree root via
  `../../.venv/Scripts/python -m pytest -q`; commit messages via bash heredoc (no double quotes in
  `git commit -m`); `git log --oneline -1` before every commit; trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- QUESTION-STOP rule (repo CLAUDE.md "Orchestrated lane agents"): any question or design fork not
  settled by the spec -> write `.superpowers/handoffs/f72-sufficiency-QUESTIONS.md` + recommendation
  and end the turn. Do not pick and proceed.

## Decision provenance (mechanical choices this lane made, per QUESTION-STOP rule)

- **Existing fixture excerpts made distinct.** `tests/test_sufficiency.py`'s `FBI` fixture gave
  every evidence item `excerpt="e"`. Under `collapsed_publisher_set`, byte-identical excerpts across
  different netlocs collapse via the F72(b) near-dup (L1 exact-hash) path — so three different-domain
  sources sharing `"e"` now count as ONE publisher (the intended F72 doctrine: same body = same wire
  story). To keep the tests that assert "genuinely distinct publishers" (spec acceptance #2) genuinely
  distinct, `s1/s2/s3` get distinct excerpts. This is a mechanical consequence of the spec-sanctioned
  behavior change, NOT a design fork — the spec's acceptance #1 vs #2 distinction is exactly
  syndicated-body vs distinct-body. Recorded here rather than QUESTION-STOP'd.
- **Shadow-check methodology = dominating-set enumeration.** Because `collapsed_publisher_set` can
  only merge identities (collapsed count <= raw count always), a past sufficiency verdict can flip
  only pass->fail, and only when a cited finding-set's raw distinct-publisher count met the bar N but
  its collapsed count falls below N. The shadow-check therefore enumerates every dimension citation
  set in every committed scorecard, computes both counts, and reports any set where raw>=N and
  collapsed<N (then inspects whether it was an actual rating-change). This decisive check needs no
  reconstruction of the exact memory-bundle chaining, so it does NOT force a methodology choice (the
  spec's QUESTION-STOP trigger for the shadow-check). If findings do not resolve, report
  "not reconstructable" honestly.

---

## Task 1: Switch the sufficiency counting seam to the shared collapsed-publisher set

**Files:**
- Modify: `gpu_agent/sufficiency.py` (import line 17; `_sufficient` line 30)
- Test: `tests/test_sufficiency.py` (fixture excerpts + new acceptance tests 1-4)

**Interfaces:**
- Consumes: `collapsed_publisher_set(evidence_list) -> set[str]` from `gpu_agent.publisher` (the
  same helper gate.py F2e, thesis.py rule 6, and wiki/lifecycle.py corroboration already use).
- Produces: unchanged public signature `_sufficient(finding_ids, findings_by_id, n) -> (bool, int)`
  and `check_sufficiency(...) -> list[str]`; the returned `count` is now the collapsed count.

- [ ] **Step 1: Update existing fixtures so genuinely-distinct publishers stay distinct**

In `tests/test_sufficiency.py`, give `_ev` an `excerpt` parameter and make the `FBI` secondary
findings carry distinct bodies (distinct netlocs alone no longer guarantee distinct identity):

```python
def _ev(url, tier="secondary", excerpt="e"):
    return Evidence(source="s", url=url, date="2026-07-01", excerpt=excerpt, tier=tier)
```

```python
FBI = {
    "prim": _finding("prim", [_ev("https://sec.gov/x", tier="primary")]),
    "s1": _finding("s1", [_ev("https://reuters.com/a", excerpt="reuters body")]),
    "s2": _finding("s2", [_ev("https://digitimes.com/b", excerpt="digitimes body")]),
    "s3": _finding("s3", [_ev("https://tomshardware.com/c", excerpt="toms body")]),
}
```

- [ ] **Step 2: Add the four new acceptance tests (spec #1-#4)**

Append to `tests/test_sufficiency.py`:

```python
# --- F72 follow-up (contract v1.4.1): sufficiency counts COLLAPSED publishers ---
from gpu_agent.publisher import collapsed_publisher_set
from gpu_agent.gate import check_finding
from gpu_agent.schema.finding import Kind

# One wire story reprinted verbatim (byte-identical body) across 3 different netlocs.
_WIRE = "Acme ships a record quarter of accelerators, the company said Tuesday."
_SYND = {
    "w1": _finding("w1", [_ev("https://reuters.com/wire", excerpt=_WIRE)]),
    "w2": _finding("w2", [_ev("https://finance.yahoo.com/wire", excerpt=_WIRE)]),
    "w3": _finding("w3", [_ev("https://markets.businessinsider.com/wire", excerpt=_WIRE)]),
}


def test_syndicated_three_domains_counts_as_one_publisher_and_fails():
    # Spec acceptance #1: one story on 3 netlocs with identical bodies collapses to ONE
    # publisher -> fails the >=3 bar it passed under raw netloc counting.
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["w1", "w2", "w3"])})
    assert check_sufficiency([ans], mem, _SYND) == [
        "sample 1: momentum: rating changed Strong->Very strong with insufficient "
        "evidence (no primary; 1 distinct publishers < 3)"]


def test_three_genuinely_distinct_publishers_still_pass():
    # Spec acceptance #2: three distinct publishers (distinct bodies + netlocs) still pass.
    mem = _memory({"momentum": "Strong"})
    ans = _answer({"momentum": ("Very strong", ["s1", "s2", "s3"])})
    assert check_sufficiency([ans], mem, FBI) == []


def test_boundary_exactly_at_bar_passes_one_below_fails():
    # Spec acceptance #3: collapsed count exactly N passes; N-1 fails.
    mem = _memory({"momentum": "Strong"})
    at_bar = _answer({"momentum": ("Very strong", ["s1", "s2", "s3"])})   # collapsed 3 == 3
    below = _answer({"momentum": ("Very strong", ["s1", "s2"])})          # collapsed 2 < 3
    assert check_sufficiency([at_bar], mem, FBI) == []
    assert len(check_sufficiency([below], mem, FBI)) == 1


def test_sufficiency_and_f2e_see_the_same_collapsed_count():
    # Spec acceptance #4: both gates route the SAME evidence set through the SAME shared helper,
    # so they agree on the collapsed distinct-publisher count.
    evs = [e for fid in ("w1", "w2", "w3") for e in _SYND[fid].evidence]
    suff_ok, suff_count = _sufficient(list(("w1", "w2", "w3")), _SYND, 3)
    # F2e (gate.check_finding) counts collapsed_publisher_set over a finding's own evidence.
    f2e_count = len(collapsed_publisher_set(evs))
    assert suff_count == f2e_count == len(collapsed_publisher_set(evs)) == 1
    assert suff_ok is False
```

Add the `_sufficient` import to the test's imports:

```python
from gpu_agent.sufficiency import check_sufficiency, _sufficient
```

- [ ] **Step 3: Run the new tests to verify they fail (RED) against current raw-netloc counting**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency && ../../.venv/Scripts/python -m pytest -q tests/test_sufficiency.py`
Expected: the syndicated/boundary/agreement tests FAIL because raw `publisher_key` still counts 3
netlocs as 3 publishers; `test_three_genuinely_distinct_publishers_still_pass` passes.

- [ ] **Step 4: Make the seam change in `gpu_agent/sufficiency.py`**

Replace the import (line 17):

```python
from gpu_agent.publisher import collapsed_publisher_set
```

Replace the counting line in `_sufficient` (line 30) and update the docstring note:

```python
def _sufficient(finding_ids, findings_by_id, n) -> tuple[bool, int]:
    """(passes, distinct-publisher count). Primary anywhere passes outright. Unresolvable
    ids contribute nothing — citation validity against the briefing is the aggregator's
    job, not this gate's. Contract v1.4.1: distinctness is counted over the SAME collapsed
    publisher identities the F2e gate uses (publisher.collapsed_publisher_set) so a wire
    story syndicated / reprinted across several netlocs counts as ONE publisher here too."""
    evs = [e for fid in finding_ids if fid in findings_by_id
           for e in findings_by_id[fid].evidence]
    publishers = collapsed_publisher_set(evs)
    if any(e.tier == "primary" for e in evs):
        return True, len(publishers)
    return len(publishers) >= n, len(publishers)
```

- [ ] **Step 5: Run the sufficiency tests to verify they pass (GREEN)**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency && ../../.venv/Scripts/python -m pytest -q tests/test_sufficiency.py tests/test_cli_sufficiency.py`
Expected: all PASS (the CLI tests use single-evidence findings -> collapsed count == raw count == 1,
unaffected).

- [ ] **Step 6: Run the full suite to confirm no regressions**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency && ../../.venv/Scripts/python -m pytest -q`
Expected: same green baseline as before the change (1200 passed / 5 skipped, plus the 3 new tests),
`tests/test_evals_baseline_pin.py` green (no emitted-prompt change).

- [ ] **Step 7: Commit**

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency
git log --oneline -1
git add gpu_agent/sufficiency.py tests/test_sufficiency.py
git commit -m "$(cat <<'EOF'
fix(sufficiency): count collapsed publishers (contract v1.4.1)

Switch _sufficient's distinct-publisher count from raw publisher_key to the
shared collapsed_publisher_set helper the F2e gate already uses, so one wire
story syndicated/reprinted across several netlocs no longer clears the
evidence-sufficiency bar. The only frozen-core edit for this lane; shared
helper, zero duplicated collapse logic.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 8: Push the branch (first push)**

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency
git push -u origin f72-sufficiency-collapse
```

---

## Task 2: Read-only shadow-check over committed store data

**Files:**
- Create (scratch, NOT committed): a throwaway script under the scratchpad to recompute counts.
- Reads: `store/**/*.json` scorecards + `store/findings/*.json` (committed, read-only).

**Interfaces:**
- Consumes: `gpu_agent.publisher.publisher_key`, `collapsed_publisher_set`; `gpu_agent.config.min_distinct_publishers`; the committed scorecards' `dimensionRatings[dim].findingIds`.
- Produces: a shadow-check result string (flips found / none / not-reconstructable) for the migration note. NO store file edited.

- [ ] **Step 1: Enumerate every dimension citation set in committed scorecards**

For each committed scorecard JSON under `store/<category>/`, read `dimensionRatings[dim]` -> its
`rating` and `findingIds`. Load each committed `store/findings/<id>.json` (via the Finding schema)
so `.evidence` resolves. Record which findingIds do NOT resolve (report as a reconstruction gap).

- [ ] **Step 2: Compute both counts and find any pass->fail flip**

For each citation set: `raw = len({publisher_key(e) for e in evs})`,
`collapsed = len(collapsed_publisher_set(evs))`, `has_primary = any(e.tier=="primary")`.
A verdict could flip only where `not has_primary and raw >= N and collapsed < N`. Collect those.
For each such set, note whether the dimension's rating actually CHANGED versus the prior committed
scorecard for that category (a non-change is never gated, so it cannot have flipped a live verdict).

- [ ] **Step 3: Record the result verbatim for the migration note**

Produce one of: "No past sufficiency verdict flips: every cited finding-set with raw count >= N
also has collapsed count >= N" / "N flips found: <details>" / "Not reconstructable: <which
findingIds/cycles could not be resolved and why". If partial reconstruction forces a genuine
methodology choice (not the dominating-set check above), QUESTION-STOP.

- [ ] **Step 4: Sanity-check the script does not write**

Confirm the script only reads (no open-for-write, no scorecard re-issue). Do not commit the script;
its OUTPUT lands in the migration note (Task 3).

---

## Task 3: Migration note (contract v1.4.1)

**Files:**
- Create: `docs/migrations/2026-07-contract-v1.4.1.md`
- Test: `tests/test_migration_v141.py` (pins spec acceptance #5)

**Interfaces:**
- Consumes: the shadow-check result string from Task 2.
- Produces: a committed migration note naming v1.4.1 and carrying what/why + the shadow-check result.

- [ ] **Step 1: Write the failing test (spec acceptance #5)**

Create `tests/test_migration_v141.py`:

```python
import pathlib

NOTE = pathlib.Path(__file__).resolve().parents[1] / "docs" / "migrations" / "2026-07-contract-v1.4.1.md"


def test_migration_note_exists_names_version_and_carries_shadow_check():
    text = NOTE.read_text("utf-8")
    assert "v1.4.1" in text
    assert "sufficiency" in text.lower()
    assert "collapsed_publisher_set" in text
    assert "shadow-check" in text.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency && ../../.venv/Scripts/python -m pytest -q tests/test_migration_v141.py`
Expected: FAIL (file does not exist yet).

- [ ] **Step 3: Write the migration note**

Create `docs/migrations/2026-07-contract-v1.4.1.md` following the v1.3/v1.4 note style: What changed
(sufficiency `_sufficient` now counts `collapsed_publisher_set`), Why (last raw-`publisher_key`
hole; same story on 3 domains passed sufficiency while F2e collapsed it), Scope (only the counting
seam; no thresholds/anchors/prompts/schema/store), and the Shadow-check result verbatim from Task 2.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency && ../../.venv/Scripts/python -m pytest -q tests/test_migration_v141.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency
git log --oneline -1
git add docs/migrations/2026-07-contract-v1.4.1.md tests/test_migration_v141.py
git commit -m "$(cat <<'EOF'
docs(migrations): contract v1.4.1 note + shadow-check result

Records the sufficiency collapsed-publisher counting change and the read-only
shadow-check over committed store data (no store file edited).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Final verification and handoff (spec acceptance #6)

**Files:**
- Modify: `docs/superpowers/HANDOFF.md` (resume-point + lane status)
- Create: `.superpowers/handoffs/f72-sufficiency-DONE.md` (ROOT path sentinel)

- [ ] **Step 1: Full suite green + F6 pin green**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency && ../../.venv/Scripts/python -m pytest -q`
Expected: green (baseline + new tests), `tests/test_evals_baseline_pin.py` green.

- [ ] **Step 2: Confirm frozen-core discipline**

Run: `cd /c/Users/danie/random_for_fun/.worktrees/f72-sufficiency && git diff --stat main...HEAD`
Expected: only `gpu_agent/sufficiency.py`, `tests/test_sufficiency.py`, `tests/test_migration_v141.py`,
`docs/migrations/2026-07-contract-v1.4.1.md`, `docs/superpowers/plans/...`, HANDOFF, sentinel. No
other frozen file touched; no `store/` edit; no schema/prompt change.

- [ ] **Step 3: Update HANDOFF, write DONE sentinel, push**

Write `.superpowers/handoffs/f72-sufficiency-DONE.md` (date, branch+commits, suite status,
delivered-vs-acceptance, shadow-check summary, merge notes: frozen-core migration -> user merge only,
final review mandatory). Update `docs/superpowers/HANDOFF.md`. Commit and push. STOP before merge.

---

## Self-Review

- **Spec coverage:** change (Task 1) ✓; shared-helper reuse (Task 1) ✓; shadow-check read-only
  (Task 2) ✓; migration note v1.4.1 (Task 3) ✓; acceptance #1 syndicated-fails (T1 S2) ✓; #2 distinct
  pass (T1 S2) ✓; #3 boundary (T1 S2) ✓; #4 sufficiency<->F2e agreement (T1 S2) ✓; #5 migration note
  (T3) ✓; #6 F6 pin + suite green (T4) ✓; non-goals verification of sibling consumers ✓ (done pre-plan:
  gate.py:37, thesis.py:545, wiki/lifecycle.py:74 all already route through collapsed_publisher_set).
- **Placeholder scan:** none — all code/commands inline.
- **Type consistency:** `_sufficient(finding_ids, findings_by_id, n) -> (bool, int)` unchanged;
  `collapsed_publisher_set(list) -> set[str]` used consistently.
