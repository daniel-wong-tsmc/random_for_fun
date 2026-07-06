# F76 — Coordination-Substrate Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** DRAFT for user review — part of the 2026-07-06 concurrency wave (lane **P1**, `fix/coord-hygiene`, build+review **Sonnet**). Not dispatched; HOLD until user "go".

**Goal:** Make the coordination substrate (HANDOFF, provenance labels, retained-worktree tracking) self-consistent and machine-checkable so concurrent-instance work stops corrupting it.

**Architecture:** Three docs/process fixes plus one optional guard test. (a) A single-CURRENT-STATE handoff discipline enforced by structure + a tripwire; (b) a controlled provenance vocabulary (`user-approved` vs `AFK-precedent`) applied across HANDOFF/backlog/specs; (c) a retained-worktrees registry section that replaces the scattered "do not git clean" prose. The optional tripwire test mirrors the existing `tests/test_store_cycle_log_integrity.py` pattern.

**Tech Stack:** Markdown docs; Python + pytest for the optional tripwire only.

## Global Constraints

- **Lane isolation:** all work in worktree `.worktrees/coord-hygiene` on branch `fix/coord-hygiene`. Never edit the root checkout's `main`. (repo `CLAUDE.md` → Multi-instance coordination)
- **Docs/process only; no product code, no eval impact.** (backlog F76) The only code permitted is the *optional* tripwire test in Task 4, which touches no product path and changes no prompt — so the F6 hash-pin cannot trip.
- **Do NOT touch the live `dashboard-showcase` lane's uncommitted files** (10 `desk-*/SKILL.md` + `docs/agent-swarm-charter.md`). (HANDOFF → CONCURRENT-INSTANCE COORDINATION)
- **Python is `../../.venv/Scripts/python`** from a worktree (one shared root venv; never create a per-worktree venv). (repo `CLAUDE.md`)
- **Provenance vocabulary (controlled set), exact tokens:** `user-approved` (an actual user answer exists), `AFK-precedent` (proceeded on best judgment while user away), `AFK-default` (a specific reversible decision taken while user away — re-surface on return). No other provenance phrasings (`user-decided`, `user-approved (AFK)`, bare `approved`) on decision lines. (user `CLAUDE.md` → "Decisions while I'm AFK"; backlog F76b)
- **Commit discipline:** `git log --oneline -1` immediately before every commit (concurrent-instance guard); commit only files this lane created/edited (never `git add -A`).

---

### Task 1: Handoff discipline — one atomic CURRENT STATE block

**Files:**
- Modify: `docs/superpowers/HANDOFF.md` (top section only)
- Modify: `docs/superpowers/HANDOFF.md` — add a short "## How to update this file (F76 discipline)" section near the top

**Interfaces:**
- Produces: a documented invariant later tasks and Task 4's tripwire rely on — the file has **exactly one** top-of-file CURRENT STATE block, marked by the `resume point:` phrase in the H1 title, and every superseded block lives under a `## HISTORICAL —` heading.

- [ ] **Step 1: Confirm the current structure**

Run: `grep -nE "resume point:|^## HISTORICAL|^## ⚠ CONCURRENT" docs/superpowers/HANDOFF.md`
Expected: exactly one line containing `resume point:` (the H1), one or more `## HISTORICAL —` headings, one `## ⚠ CONCURRENT-INSTANCE COORDINATION`. If more than one `resume point:` line exists, the file is already violating the invariant — fold the extras into HISTORICAL as part of this task.

- [ ] **Step 2: Add the discipline section**

Insert immediately after the H1 title and its bullet block, before the first `## HISTORICAL`:

```markdown
## How to update this file (F76 discipline)

- **One CURRENT STATE block.** The H1 title carries the single `resume point:` line. When state
  changes, replace the top block **atomically**: in the same edit, move the superseded text down
  under a new `## HISTORICAL — <what/when>` heading. Never leave two "current" blocks.
- **Provenance labels are controlled** (see the Provenance vocabulary below): `user-approved`
  only when an actual user answer exists; `AFK-precedent` / `AFK-default` otherwise.
- **Retained worktrees** are tracked in the "## RETAINED WORKTREES REGISTRY" section, not in
  scattered "do not git clean" asides.
```

- [ ] **Step 3: Verify no second current block was left behind**

Run: `grep -cE "resume point:" docs/superpowers/HANDOFF.md`
Expected: `1`

- [ ] **Step 4: Commit**

```bash
git log --oneline -1
git add docs/superpowers/HANDOFF.md
git commit -m "docs(F76): handoff discipline - single atomic CURRENT STATE block"
```

---

### Task 2: Standardized provenance labels

**Files:**
- Modify: `docs/superpowers/HANDOFF.md` (decision lines)
- Modify: `docs/fix-backlog.md` (decision lines)
- Modify: `docs/superpowers/plans/2026-07-06-concurrency-wave-plan.md` (the "user-approved" table rows)

**Interfaces:**
- Consumes: the controlled vocabulary defined in Global Constraints.
- Produces: every provenance-bearing decision line uses one of `user-approved` / `AFK-precedent` / `AFK-default` — the token set Task 4's tripwire scans for.

- [ ] **Step 1: Inventory the drift**

Run: `grep -rnE "user-approved|user-decided|AFK-default|AFK-precedent|approved \(AFK\)|user-approved \(AFK" docs/ | grep -viE "controlled|vocabulary|discipline"`
Read every hit. For each, classify: is there an actual user answer on record? → `user-approved`. Was it a best-judgment proceed while the user was away? → `AFK-precedent`. Was it a specific reversible decision taken AFK (must be re-surfaced)? → `AFK-default`.

- [ ] **Step 2: Add a one-line legend where labels are first used**

In `docs/fix-backlog.md`, near the top decision block, add:

```markdown
> **Provenance labels:** `user-approved` = an actual user answer exists; `AFK-precedent` =
> proceeded on best judgment while the user was away; `AFK-default` = a specific reversible
> decision taken while away, re-surfaced on the user's return.
```

- [ ] **Step 3: Rewrite each mislabeled line**

Apply the classification from Step 1. Do NOT silently downgrade a genuine `user-approved` (the four 2026-07-06 wave decisions and D5 are real user answers — keep them `user-approved`). Only relabel lines where the record is actually ambiguous per the F76b finding (e.g. F52–F54's AFK-precedent decisions currently written as bare "user-approved").

- [ ] **Step 4: Verify no forbidden phrasing remains**

Run: `grep -rnE "user-decided|approved \(AFK\)|user-approved \(AFK" docs/`
Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git log --oneline -1
git add docs/superpowers/HANDOFF.md docs/fix-backlog.md docs/superpowers/plans/2026-07-06-concurrency-wave-plan.md
git commit -m "docs(F76): controlled provenance vocabulary across handoff/backlog/plan"
```

---

### Task 3: Retained-worktrees registry

**Files:**
- Modify: `docs/superpowers/HANDOFF.md` — add "## RETAINED WORKTREES REGISTRY"

**Interfaces:**
- Consumes: live worktree state from `git worktree list`.
- Produces: a single registry section — one row per retained worktree (name, branch, why retained, what's inside, when it can be removed) — that Task 4's tripwire can require exists.

- [ ] **Step 1: Enumerate the live retained worktrees**

Run: `git worktree list`
Cross-reference the "do not git clean" prose scattered in HANDOFF/backlog and each worktree's `work/` and `.superpowers/sdd/` contents to fill the "what's inside / when it can go" columns.

- [ ] **Step 2: Write the registry section**

Add near the CONCURRENT-INSTANCE COORDINATION section:

```markdown
## RETAINED WORKTREES REGISTRY

Merged-feature worktrees are kept ONLY for gitignored data (raw eval replicate runs, SDD
ledgers). Never `git clean` these. Remove a worktree only when its "can go when" condition holds.

| Worktree | Branch | Retained because | Contains (gitignored) | Can be removed when |
|---|---|---|---|---|
| `.worktrees/eval-v2` | `eval-v2-replicate-baseline` | raw replicate runs | `work/eval-*` | v2 baseline superseded + notes committed |
| `.worktrees/f62-flagship-store` | `f62-flagship-consumes-store` | raw eval runs | `work/eval-*` | F62 eval history no longer referenced |
| `.worktrees/f63-corroboration` | `f63-corroboration-doctrine` | raw eval runs (2026-07-04/05) | `work/eval-f63-*` | F63 re-gate history archived |
| `.worktrees/dashboard` | `dashboard-showcase` | **ACTIVE lane** (not retained-only) | in-progress | lane merges or is abandoned |

Update this table whenever a worktree is added or removed. It replaces every scattered
"do not git clean <path>" warning — delete those asides as you migrate them here.
```

(Fill exact rows from Step 1; the table above is the shape, not a guess — verify each branch name against `git worktree list`.)

- [ ] **Step 3: Remove the now-migrated scattered warnings**

Run: `grep -rnE "do not .?git clean|never .?git clean" docs/`
For each prose warning now covered by the registry, replace it with a pointer: "see the RETAINED WORKTREES REGISTRY in HANDOFF.md". Do not delete the repo `CLAUDE.md` "Never `git clean` here" global rule — that is policy, not a per-worktree aside.

- [ ] **Step 4: Commit**

```bash
git log --oneline -1
git add docs/superpowers/HANDOFF.md docs/fix-backlog.md
git commit -m "docs(F76): retained-worktrees registry replaces scattered git-clean warnings"
```

---

### Task 4 (OPTIONAL — hardening): HANDOFF integrity tripwire

> **Drop this task** if the user wants F76 to stay strictly pure-docs. It adds a pytest tripwire
> (no product path, no prompt, no eval impact) mirroring `tests/test_store_cycle_log_integrity.py`,
> so the disciplines above cannot silently rot. Recommended: keep it — a convention with no test
> is the exact failure mode F76 exists to fix.

**Files:**
- Create: `tests/test_handoff_integrity.py`

**Interfaces:**
- Consumes: `docs/superpowers/HANDOFF.md` on disk; the controlled vocabulary from Global Constraints.
- Produces: three assertions the suite enforces on every run.

- [ ] **Step 1: Write the failing test**

```python
import re, pathlib
HANDOFF = pathlib.Path(__file__).resolve().parents[1] / "docs/superpowers/HANDOFF.md"

def _text():
    return HANDOFF.read_text("utf-8")

def test_single_current_state_block():
    # exactly one top-of-file resume-point line; everything else is HISTORICAL
    assert len(re.findall(r"resume point:", _text())) == 1

def test_provenance_labels_controlled():
    allowed = {"user-approved", "AFK-precedent", "AFK-default"}
    # forbidden phrasings that the F76b finding calls out as ambiguous
    forbidden = re.findall(r"user-decided|approved \(AFK\)|user-approved \(AFK", _text())
    assert forbidden == []

def test_retained_worktrees_registry_present():
    assert "## RETAINED WORKTREES REGISTRY" in _text()
```

- [ ] **Step 2: Run to verify it passes against the Task 1–3 edits**

Run: `../../.venv/Scripts/python -m pytest tests/test_handoff_integrity.py -v`
Expected: 3 passed. (If any fail, the fix is in the *doc* from Tasks 1–3, not the test.)

- [ ] **Step 3: Run the full suite (no regressions, pin intact)**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green, 3–4 skips, `tests/test_evals_baseline_pin.py` PASS (F76 changes no prompt).

- [ ] **Step 4: Commit**

```bash
git log --oneline -1
git add tests/test_handoff_integrity.py
git commit -m "test(F76): handoff-integrity tripwire (single current block, provenance, registry)"
```

---

## Self-Review (author checklist — completed)

- **Spec coverage:** F76(a) handoff discipline → Task 1; F76(b) provenance labels → Task 2; F76(c) retained-worktrees registry → Task 3; durability of all three → Task 4 tripwire. ✅
- **Placeholder scan:** registry table rows in Task 3 are marked "verify against `git worktree list`" rather than asserted — intentional, because the live set changes; the *shape* is concrete. No TODO/TBD left.
- **"Docs/process only" caveat honored:** the only code is Task 4, isolated and optional, with an explicit drop-instruction.
- **Type consistency:** the controlled-vocabulary token set is defined once (Global Constraints) and referenced identically in Tasks 2 and 4.

## Open question for the reviewer

Keep Task 4 (tripwire) or drop it to hold F76 strictly pure-docs? Recommendation: **keep** — it is the only thing that makes the disciplines self-enforcing, and it has zero eval/product surface.
