---
name: desk-diagnostics-and-tooling
description: Use when you need to MEASURE this repo's state instead of eyeballing it -- is F-item <N> really merged despite its backlog checkbox, is store/cycle-log.json clobbered back to a bare plan skeleton, which scorecard is actually "latest" under mixed day/month grain, reading a dedup report/wiki-lint counts/thesis book, interpreting a verdict.json or eval seam-noise vs epsilon, or which seam's F6 prompt hash moved. Triggers on "stale checkbox", "is F<N> done", "cycle-log clobbered", "latest scorecard", "dedup report", "wiki lint stale/orphans", "thesis divergence", "verdict.json", "seam noise", "prompt hash changed", "extract-05".
---

# Desk diagnostics and tooling

## Overview

This repo's own docs (backlog checkboxes, HANDOFF sections, README counts) drift out of
sync with reality faster than anyone updates them, and several of its trickiest bugs (F74's
cycle-log clobber, F63's noisy eval bar) were only diagnosable by *measuring* something --
git ancestry, a byte diff, a spread across replicate runs -- not by reading prose. This skill
ships five small, read-only, stdlib-only scripts under `scripts/` that answer exactly those
measurement questions, plus recipes for the cases a script would be overkill for.

## When to use / when NOT to use

Use this skill to find out **what is actually true right now** -- merge status, working-tree
state, store contents, eval numbers, prompt bytes.

Do NOT use this skill to fix what you measured:
- A stale checkbox or contradictory HANDOFF section → **desk-docs-and-writing** (templates,
  house style) and **desk-change-control** (the F-item lifecycle, fix-forward rule).
- An actual bug this skill's scripts surface → **desk-debugging-playbook** (symptom→triage
  tables, discriminating experiments) or **desk-failure-archaeology** (has this exact thing
  happened before?).
- The gate-precedence / bypass-policy / syndication cluster (F71/F75/F72) that `f74_guard.py`
  is the first phase of → **gate-integrity-campaign** (the executable, decision-gated plan).
- Running an actual cycle or eval, not just inspecting its output → **desk-run-and-operate**
  (routes to run-cycle/gather-category/run-eval) and the repo's own `run-eval`/`eval-driver`
  skills.
- Deciding what counts as evidence, the fixture families, or the suite baseline itself →
  **desk-validation-and-qa** owns that; this skill only reads what the harness already wrote.
- Design invariants (why store/ is append-only, why the frozen core is versioned) →
  **desk-architecture-contract**.

## The five scripts

All five: **stdlib-only** in their own imports (subprocess/json/re/argparse/pathlib/difflib
only -- no pydantic/gpu_agent import in the script's own process; where real project logic is
needed, they shell out to the repo's own `.venv` python, same pattern as
`scripts/web-reach-ensure`). **Read-only** -- none of them writes store/, work/, or git state.
**Exit nonzero on alarm.** Run any of them with `-h` for full usage; all accept `--repo <path>`
if you're not running from repo root.

```
.venv/Scripts/python .claude/skills/desk-diagnostics-and-tooling/scripts/<name>.py ...
```

### 1. `status_reconcile.py` -- is F-item N actually merged?

```
status_reconcile.py F74 F71 F63          # specific items
status_reconcile.py --all                # every item in the backlog
```

Asks git the only question that matters: is a commit that closes F&lt;N&gt; an ancestor of
HEAD? It looks for (a) a hash the backlog's own prose cites right after "merged" (e.g. "DONE
(merged to main `257cf1b`)"), (b) a real `Merge branch ...` commit mentioning F&lt;N&gt;, or
(c) a non-`docs(...)`-prefixed commit with F&lt;N&gt; in its own subject line -- then compares
that to the checkbox. It also greps HANDOFF.md for the item as an informational (non-
authoritative) hint, because some closures are recorded only as HANDOFF prose (see F61 below).

| Verdict | Meaning | Action |
|---|---|---|
| `MERGED` | checkbox `[x]`, git agrees | trust it, move on |
| `STALE_CHECKBOX` | checkbox `[ ]` but git proves it merged | trust git; treat as DONE; fixing the checkbox is a **desk-docs-and-writing** edit, not a re-investigation |
| `OPEN` / `OPEN_WITH_ACTIVITY` | checkbox `[ ]`, git agrees (activity found but nothing merged, or nothing at all) | genuinely open; route to **desk-change-control** for how to pick it up |
| `CHECKBOX_AHEAD` | checkbox `[x]` but no *strong* merge evidence found | don't panic -- see limitations below; verify by hand (`git log --all --grep=F<N>`) before treating as a real problem |
| `NOT_IN_BACKLOG` | no bullet for that number | check the number; F-items are user-locked in sequence, never renumbered |

**Known limitations (found while verifying this script against the real backlog, 2026-07-06 --
see references/status-reconcile.md for the false positives caught and how they were fixed):**
items from the earliest wave (F1-F51, before the "cite the closing hash" convention
solidified) sometimes show `CHECKBOX_AHEAD` with "no commit anywhere mentions F&lt;N&gt;" even
though they are genuinely done (e.g. F2, F28) -- the fix landed in one big batch commit with
no per-item tag. A `docs(...)`-prefixed commit that is *actually* a content fix (F39's
`a2f6906 docs(F39 review fix): ...`) is likewise invisible to the "non-docs subject line"
heuristic. Treat `CHECKBOX_AHEAD` on a pre-F52 item as "needs a human glance," not as news.
F61 is a *different* case: HANDOFF says "F61 is DONE (subsumed by F67)" but there is no F61-
tagged commit at all -- the script correctly reports `OPEN_WITH_ACTIVITY` from git's
perspective while surfacing the HANDOFF line so you can judge for yourself; this is a real gap
between "closed by prose" and "closed by commit" that no git-only tool can resolve.

### 2. `f74_guard.py` -- has store/cycle-log.json been clobbered?

```
f74_guard.py                # check the working tree against HEAD
f74_guard.py --no-pytest     # skip the pytest cross-check
```

**F74 status (verified 2026-07-06): RESOLVED.** The clobber described in the backlog
(`cycle-plan --out store/cycle-log.json` unconditionally overwriting the session-authored
journal on every run start, once for real erasing the F71 sufficiency-bypass record) is fixed
in code: `gpu_agent/cli.py::_is_bare_plan`/`_cycle_plan` now refuses to overwrite anything
richer than a bare, regenerable plan skeleton, run-cycle's step 1 writes the plan to the run's
own `work/<run-dir>/` instead, and a suite tripwire
(`tests/test_store_cycle_log_integrity.py`) fails the build on any bare journal in the tracked
file. Landed on `9a5f9b2`/`3613ede`, merged to main at `257cf1b`, backlog F74 checkbox is
correctly ticked. This script exists as the standing monitor anyway, because (a) a hand-edit
or a stray script can still write the file directly, bypassing `cycle-plan` and its guard
entirely, and (b) an older branch/worktree without the fix can still hit the original bug.

It classifies both the working-tree copy and HEAD's committed copy of `store/cycle-log.json`
as `bare` (only plan-skeleton keys) or `enriched` (has `asOf` and/or ready entries carry
extra keys like `scorecard`/`gates`), then cross-checks with the real pytest tripwire.

| Output | Meaning | Action |
|---|---|---|
| `working tree: enriched`, `HEAD: enriched`, `OK` | healthy | proceed; safe to `git add store/` (after your usual review) |
| `HEAD: enriched`, `working tree: bare`, `ALARM` | the exact F74 clobber shape | **do not commit.** `git restore store/cycle-log.json` once no other instance owns the in-flight change (see the user-level **instance-sync** skill for the "does anyone else own this" check — if available on this machine; it does not travel with a fresh clone, see desk-build-and-env), or diagnose what wrote the skeleton |
| `unrecognized` on either side | unparseable JSON, a BOM, or a directory at that path | inspect by hand: `git diff store/cycle-log.json` |
| pytest cross-check `FAIL` | the real tripwire test disagrees with this script's classifier, or the code guard itself regressed | trust the pytest result; treat as an active bug, not a diagnostics-script bug |
| `store/cycle-log.json does not exist` | fresh checkout, or the category has never run | nothing to guard yet |

### 3. `store_inspect.py` -- read the store/ tree without eyeballing it

```
store_inspect.py latest --category chips.merchant-gpu
store_inspect.py findings
store_inspect.py dedup --category chips.merchant-gpu [--as-of 2026-07-05]
store_inspect.py wiki-lint
store_inspect.py thesis --category chips.merchant-gpu
```

Five subcommands; see references/store-inspect.md for full field-by-field interpretation.
Condensed:

| Subcommand | What it measures | Gotcha it exists to catch |
|---|---|---|
| `latest` | the "current" scorecard two ways: CODE ORDER (the lexical-string sort `report.find_prior`/`memory.latest_scorecard_before` actually use) vs CALENDAR ORDER (true chronological) | **mixed grain**: `"2026-07"` is a *prefix* of `"2026-07-05"`, so Python string-sorts the day-grain filename as lexically *greater* -- a daily run's scorecard silently outranks the monthly flagship as "latest" in any code path that auto-detects it. Verified live 2026-07-06: they disagree (code order picks `2026-07-05-v1.json`, calendar order picks `2026-07-v3.json`) |
| `findings` | census of store/findings/ by kind/side, and what fraction are pre- vs post-F52 vintage-scoped ids | store/findings/ holds only GATED findings by construction -- there is no "gate outcome" to break down here (rejected drafts never land); don't go looking for one |
| `dedup` | reads store/&lt;category&gt;/dedup-&lt;asOf&gt;.json (the L2, finding-level report) | L2 ≠ L1: L1 is document-level dedup in `store/seen_docs.jsonl` (hash-first, not URL-first); a dedup report says nothing about how many raw documents L1 filtered before extraction ran |
| `wiki-lint` | the latest `"kind":"lint"` event from `store/wiki/log.jsonl`, read directly | invoking the real `gpu-agent wiki-lint` CLI is **not** read-only -- it appends a log event the first time it runs for a given `--as-of` (idempotent only on a *repeat* call for the same asOf). This script reads history instead so it never risks writing store/ for a not-yet-linted date |
| `thesis` | book.json vs history.jsonl divergence, via the REAL `ThesisStore.load()` (subprocessed into `.venv`, not reimplemented) | an early draft reimplemented the fold in pure stdlib and produced a **false divergence alarm** on a perfectly healthy book (ThesisEntry carries derived fields a naive dict-merge can't reproduce) -- getting this wrong in the alarming direction is worse than not shipping it, hence the subprocess-to-real-code design |

### 4. `eval_diagnostics.py` -- read eval-v2 output without re-deriving the math by hand

```
eval_diagnostics.py baseline
eval_diagnostics.py case-census
eval_diagnostics.py verdict <path/to/verdict.json>
eval_diagnostics.py report <path/to/report.json> [--baseline <path>]
eval_diagnostics.py seam-noise <dir1> <dir2> [<dir3> ...]
```

See references/eval-diagnostics.md for the full walkthrough (verified against the real
retained-worktree run dirs backing the committed baseline). Condensed:

| Subcommand | What it measures |
|---|---|
| `baseline` | current seamMeans/epsilon/bars and per-case medians **grouped by seam** (comparing raw medians across seams is a category error -- thesis runs a full point lower than judge by design of the rubric, not because thesis cases are worse) |
| `case-census` | golden-case counts by seam, on **two independent axes**: `kind` (positive/negative curation category) and `checks.gateOutcome` (pass/reject under current gates) -- conflating these is a real trap (3 of judge's 4 *positive* cases legitimately expect `gateOutcome=reject`, because eval's judge gating runs single-shot/no-resample, so a historical case whose production judgment needed an anchor-bound retry correctly re-produces a reject when replayed) |
| `verdict` | interprets a `verdict.json`: per-seam value/bar/hardBar/margin, craters, decision |
| `report` | same interpretation from a `report.json` that may not have gone through `eval verdict` yet (independent recompute against the committed baseline) |
| `seam-noise` | spread (max−min) of `seamMeans` across N run dirs' `report.json` -- the same half-range computation epsilon is built from, pointed at whatever runs you give it |

**extract-2026-07-05 is the chronically weakest case** (F63 re-gate run-notes: "the weakest
case across every run ever recorded," 4-7 band, `completeness` the recurring 0-scoring
criterion) -- still undiagnosed whether the case or the prompt is at fault. `baseline` prints
this as a cited historical claim, separate from whatever the current single-snapshot median
ranking says (they can differ; verified: median-ranking currently ties 04/05/06 within
extract).

**F73 note** (printed by every subcommand here): eval-v2's epsilon (0.19-0.5/seam) is small
against this repo's own documented identical-prompt seam swings (6.25-7.50); the F63 re-gate
passed extract by 0.042 -- "deep inside noise" by the backlog's own words. A gate has never
been demonstrated to catch a *real* regression here (no seeded-regression canary exists). Read
any single verdict with that in mind; a fix for the gate's power itself routes through F73 /
**desk-change-control**, not through re-running until it says what you want.

### 5. `prompt_hash_diff.py` -- which seam's hash moved, and what changed?

```
prompt_hash_diff.py status              # which seam(s) drifted vs the committed baseline
prompt_hash_diff.py dump <dir>           # snapshot current emitted bundles
prompt_hash_diff.py diff <dir_a> <dir_b> # unified diff, CRLF-normalized
```

`tests/test_evals_baseline_pin.py` going red only tells you a seam's emitted-prompt bytes
changed; it can't show you what changed, because a hash is one-way. Workflow: `dump` before
your edit, make the edit, `dump` again, `diff` the two directories. Diffs are CRLF-normalized
before comparing (a materialized prompt file saved on Windows vs POSIX differing only in line
endings is not a real prompt change). Verified end-to-end this session: `status` reproduces
the committed baseline's exact hashes; a simulated edit + a full CRLF flip on the same file
correctly shows only the real content change, nothing spurious.

## Recipes that don't need a script

- **Session orientation**: `sh scripts/session-orient` (repo-root script; now **tracked**,
  committed at `29584d9` -- correcting any earlier note that called it untracked). Prints:
  current branch + last commit; any uncommitted `store/`/`work/` changes with a "possibly
  another instance's output" warning; any `.superpowers/handoffs/*-DONE.md` sentinels; active
  `.worktrees/`; and the first 25 lines of HANDOFF.md's "CONCURRENT-INSTANCE COORDINATION"
  section. Read it before touching anything in a session that might not be starting from a
  clean, fully-informed state; see the user-level **instance-sync** skill (if available on this machine) for what to do with what it tells you.
- **Full suite baseline**: `.venv/Scripts/python -m pytest` from repo root. Verified this
  session (2026-07-06): **1066 passed / 4 skipped** in ~73s (1070 collected). This number
  moves; re-run it, don't quote an old one (the README's "417 passed" is over three weeks and
  ~650 tests stale as a cautionary example of exactly that mistake).
- **Retained eval run dirs** (the raw data behind the committed baseline, for `seam-noise` or
  manual inspection): `.worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/{r1,r2,r3}`
  and `.worktrees/eval-v2/work/eval-v2-migration/{r1,r2,r3}`. Gitignored; never `git clean`
  them (CLAUDE.md). There is no registry of which retained worktree holds which run (F76c,
  open) -- `git worktree list` plus a grep for `report.json` under each is the manual recipe.

## Common mistakes

- Trusting a backlog checkbox without reconciling it. Seven+ items are known stale at any
  given moment on this repo's own history; run `status_reconcile.py` first.
- Treating `wiki-lint`'s CLI form as read-only. It appends a log event on the first call for a
  new `--as-of` (idempotent only on repeat calls for an *already-linted* date) -- use
  `store_inspect.py wiki-lint` instead when you just want to look.
- Reimplementing project logic (ThesisStore's fold, `_is_bare_plan`'s key sets, the prompt
  builders) in a "stdlib-only" script instead of subprocessing the repo's own `.venv` python
  for the one step that actually needs it. This skill's own scripts got a false-positive
  divergence alarm and (separately) a fragile hand-copied key-set from doing exactly that
  during development; every script here now shells out to `.venv` for anything that must
  match the real code exactly, and stays stdlib-only everywhere else.
- Comparing eval medians or scores **across seams**. extract/judge/thesis have different
  natural ranges (rubric depth, positive-case counts); "weakest case" only means something
  compared within its own seam.
- Reading `checks.gateOutcome` as a synonym for "positive vs negative case." They are
  independent axes; verify with `eval_diagnostics.py case-census` before assuming either.
- Running any of these scripts' underlying CLI commands directly against `store/` "just to
  check" without `--no-pytest`/read-only equivalents -- several CLI verbs in this repo
  (`wiki-lint`, `cycle-plan --out`) are NOT idempotent no-ops; that's exactly why these
  diagnostics read files/git instead of shelling out to the mutating command.

## Provenance and maintenance

Authored 2026-07-06, verified live against **main @ f7c83f0** (discovery baseline for the
wider project was **a8ec757**, 2026-07-05 -- the repo moved substantially in the interim,
including the full F74 fix landing and merging; HEAD moves further with every session,
including concurrent ones -- re-verify, don't trust this timestamp). Every fact below was
produced by a command in *this* session; re-run the command, don't just trust the number.

| Fact | Re-verify with |
|---|---|
| Current HEAD | `git log --oneline -1` |
| Suite baseline (1066 passed / 4 skipped, 1070 collected) | `.venv/Scripts/python -m pytest` / `--collect-only -q` |
| F74 resolved, merged `257cf1b` | `status_reconcile.py F74` |
| Stale-checkbox set (F56/57/58/59/63/68 as of this session) | `status_reconcile.py --all \| grep STALE_CHECKBOX` |
| Eval baseline seamMeans/epsilon | `eval_diagnostics.py baseline` |
| Weakest eval case(s) | `eval_diagnostics.py baseline` (per-seam) and `case-census` |
| Mixed-grain "latest" disagreement | `store_inspect.py latest --category chips.merchant-gpu` |
| Thesis book entry count / divergence | `store_inspect.py thesis --category chips.merchant-gpu` |
| Wiki lint stale/orphan counts | `store_inspect.py wiki-lint` |
| Prompt-hash pin status | `prompt_hash_diff.py status` |
| CLAUDE.md / scripts/session-orient tracked status | `git log --oneline -1 -- CLAUDE.md scripts/session-orient` |
| Retained worktrees | `git worktree list` |
