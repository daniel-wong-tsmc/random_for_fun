---
name: gate-integrity-campaign
description: Use when working the F74/F71/F75/F72 gate-integrity cluster in the GPU Category Agent repo (not a routine single-sample gate rejection — that's desk-debugging-playbook) — a judge/pipeline command dies with an uncaught "contradicts anchor" traceback (not a clean sufficiency:/voice-lint: rejection), the anchor bound and sufficiency gate visibly demanding opposite outcomes on the same rating, a --no-sufficiency/--no-voice-lint bypass that was already used/logged and needs a permanent fix (not just a one-time rewrite-and-retry), corroboration that might be one wire story synced across several domains, or before running any unattended/autonomous cycle loop.
---

# Gate Integrity Campaign

## Overview

This is the executable, decision-gated runbook for the hardest LIVE problem in this repo: a
chain of four gate-semantics defects, born in order, that together decide whether an unattended
cycle can ever run safely — **F74** (a writer silently destroyed the run-journal audit trail) →
**F71** (two frozen-core gates demand contradictory outcomes on the same rating) → **F75** (the
policy gap that let F71's deadlock ship as a whole-run bypass) → **F72** (a silent corroboration
hole that could make gates pass when they shouldn't, the mirror-image risk to F71's honest,
loud failure). Closing F71+F75 is the maintainer-recorded blocker for the autonomy track's first
supervised-unattended pilot (`docs/roadmap.md` — see "The prize" below).

**Core principle: verify current state before executing any phase.** This cluster is worked by
concurrent Claude Code instances; the repo has moved past every snapshot below already, and it
will move again before you finish reading this file. Start every session on this campaign with
the WHERE ARE WE gate, not with an assumption drawn from this doc or from any other skill.

## When to use / when NOT to use

| Situation | Go to |
|---|---|
| Working the F74/F71/F75/F72 cluster itself, or deciding what to do next in it | **this skill** |
| You need the domain meaning of "anchor", "sufficiency", "publisher key", "corroboration doctrine" | `market-state-reference` (owns the theory; this skill only owns the executable campaign) |
| You need the general change-classification rules, Part-33 migration mechanics, or the F-item lifecycle | `desk-change-control` (owns doctrine this campaign routes through — do not re-derive it here) |
| You hit a gate failure NOT in this cluster, or don't know which failure mode you have | `desk-debugging-playbook` |
| You want the full incident narrative (symptom → root cause → evidence → status) for F71/F74/F72 or other fights | `desk-failure-archaeology` |
| You need the catalog of every bypass flag/env gate and how to add one | `desk-config-and-flags` |
| You need to actually run a live/demo cycle, commit artifacts, or coordinate with another instance | `desk-run-and-operate` / the user-level `instance-sync` skill (if available on this machine — it does not travel with a fresh clone) |
| You are designing the eval-power fix (F73) or the coordination-substrate fix (F76) | Not this campaign — F73 is `desk-validation-and-qa`/eval-driver territory; F76 is `desk-change-control`/`desk-failure-archaeology` territory. Mentioned here only where they touch this cluster. |

**Jargon, defined once:** *F-item* = a numbered entry in `docs/fix-backlog.md`. *Frozen core* =
`gate.py`, `scoring.py`, the Finding schema, `judgment/judge.py` aggregation, `pipeline.py` —
changes only via a versioned Part-33 migration (`desk-change-control` §3). *Anchor* = a
code-computed, per-dimension number (mean of polarity×magnitude/3 over the dimension's findings)
that the judge's rating word may not contradict (the "Part 7 bias guardrail"). *Sufficiency gate*
= the F63 rule that a rating CHANGE vs the prior cycle's memory needs a primary citation or
≥3 distinct publishers. *Publisher key* = the evidence URL's netloc — the corroboration identity.
*Whole-run bypass* = a flag (`--no-sufficiency`, `--no-voice-lint`) that skips a gate for an
entire run rather than one item.

## PHASE START — "WHERE ARE WE" (mandatory, run every time)

Never assume any phase below is still open or still closed. Run this checklist first, every
session, and route from its actual output. All commands are PowerShell 5.1 from repo root unless
marked bash.

| # | Check | Command | What to look for |
|---|---|---|---|
| 1 | HEAD, tree, worktrees | `git log --oneline -1` `git status --short` `git worktree list` | A clean tree is normal; a dirty tree means STOP and read the user-level `instance-sync` skill (if present on this machine) before touching anything |
| 2 | F74 — has the journal clobbered again? | `git diff HEAD -- store/cycle-log.json` | Empty = fine. Non-empty AND the diff shows a payload with only `scope`/`entries`/`stages` keys (no `asOf`, no `gates`, no `thesis`) = the clobber has recurred → go to **Phase 0, fallback branch** below, do not proceed to Phase 1 |
| 3 | F74 — is the fix actually on this branch? | `git merge-base --is-ancestor 3613ede HEAD; $LASTEXITCODE` | `0` = the F74 fix commit is an ancestor of HEAD (fix present). Non-zero = you are on a branch/worktree that predates the fix — the clobber risk is LIVE here regardless of what this doc says |
| 4 | F74 — guard tests actually green? | `.venv\Scripts\python -m pytest tests/test_store_cycle_log_integrity.py tests/test_cli_cycle_plan.py -q` | All pass = guard intact. Any fail/error with the fix present = the guard has regressed; file a NEW F-item (fix-forward), do not revert |
| 5 | F71 — open or closed? | `Select-String -Path docs/fix-backlog.md -Pattern "F71 —"` then `git log --oneline --all --grep="F71"` | If backlog still shows `- [ ]` AND no commit closes it, F71 is genuinely open (checkbox and git agree — this is the common case as of this writing). If they disagree, trust git (`desk-change-control` §6) |
| 6 | F71 — did the deadlock fire THIS cycle? | `Select-String -Path store/cycle-log.json -Pattern "sufficiency"` | Text containing `bypassed` = it fired and was bypassed live — treat as urgent, check whether the retro trust-footer note (F75) exists in the corresponding rendered brief. Text containing `PASSED with no bypass` = it did not fire this cycle (does not mean F71 is closed — it is intermittent) |
| 7 | F75 — bypass flags still on live paths? | `Select-String -Path gpu_agent/cli.py -Pattern "no-sufficiency\|no-voice-lint"` and `Select-String -Path .claude/skills/run-cycle/SKILL.md -Pattern "no-sufficiency\|bypassed"` | Hits in both = F75's removal target is still standing (expected while F75 is open). Full flag catalog: `desk-config-and-flags` |
| 8 | F72 — has the syndication-collapse registry landed? | `Test-Path registry/syndicators.json` | `False` = not built (expected while F72 is open) |
| 9 | Suite baseline | `.venv\Scripts\python -m pytest -q` | Expect all green with 3-4 skips; a red suite outside this cluster's own tests means stop and diagnose before campaigning further |

**Routing table** (read after running 1-9):

| Check 2 | Check 3/4 | → |
|---|---|---|
| clean | ancestor + green | **F74 is CLOSED. Skip to Phase 1.** |
| clean | ancestor + green, but 5-8 show F71/F72/F75 open | **Normal steady state — work Phase 1 next** (F71 is the open frontier) |
| non-empty, bare-skeleton shaped | any | **Phase 0 fallback branch — the clobber recurred. Stop. Do not run Phase 1 until resolved.** |
| clean | NOT an ancestor | **You are on a pre-fix branch/worktree.** Rebase/merge current main in, or move your work to a branch that has the fix, before doing anything with `cycle-plan`/`run-cycle` step 1 |

**Observed 2026-07-06 @ `f7c83f0`** (historical context only — re-run the table yourself): tree
clean; F74 fix commits (`3613ede`, `9a5f9b2`, merged `257cf1b`) are ancestors of HEAD; both guard
tests pass; suite 1066 passed / 4 skipped (1070 collected); F71/F72/F75/F76 all still show
`- [ ]` in the backlog AND git confirms no closing commit — checkboxes and reality agree for this
cluster right now (the STALE-checkbox problem `desk-change-control` warns about does not apply to
F71/F72/F75/F76 as of this check — it applied to F56-F59/F61/F63/F68, all outside this cluster).
The most recent committed cycle (`d9cfb3f`, 2026-07-05 daily) passed sufficiency **with no
bypass** — F71 did not fire that cycle. The discovery baseline this campaign was scoped against
was `a8ec757` (2026-07-05); by authoring time the repo had already closed F74 on its own six
commits later. **Do not trust either date as current — re-run the table.**

---

## Phase 0 — F74: the cycle-log clobber (CLOSED as of the check above; kept live for regressions)

**What happened:** `cli._cycle_plan`'s `--out` write was an unconditional `write_text`
(`gpu_agent/cli.py`, pre-fix), and `run-cycle` SKILL step 1 pointed it at the canonical
`store/cycle-log.json` on every run start — so every new run began by erasing the PREVIOUS run's
session-authored journal, including any gate-bypass record it held. On 2026-07-05 this erased the
2026-07-v3 monthly journal's `gates.sufficiency: "bypassed…"` line (F71's own audit trail) in the
working tree; it survived only in git history at `99ca522`.

**Two hypotheses existed before the fix; the SECOND was confirmed, not the backlog's original
guess.** The backlog's initial entry guessed "likely the pipeline/cycle finalize step." The
actual culprit, found by reading `cli.py`'s `--out` write sites and matching them against what
`run-cycle` invokes at run START (not finalize): `_cycle_plan`'s blind `write_text`. **The
discriminating method, worth reusing for similar "who's the writer" mysteries:** grep every
`write_text`/`write_bytes` call whose target could resolve to the suspect path, then check WHEN
in the documented workflow each call site fires (start vs. finalize) against when the corruption
was actually observed (a fresh skeleton appearing at the START of the next run, not after the
prior run's finalize, pointed at step 1, not step 6).

**Fix shipped** (`gpu_agent/cli.py`, commits `3613ede` then hardened `9a5f9b2`, merged `257cf1b`):
`cycle-plan --out` now refuses to overwrite anything richer than a bare, regenerable plan skeleton
(key-set check derived from `CyclePlan`/`CycleEntry` pydantic models, not hand-copied — so a
future schema change can't silently drift the guard out of sync); BOM-tolerant read; refuses
null/mis-typed containers and directory targets cleanly instead of raising `TypeError`/
`PermissionError`. `run-cycle` step 1 now writes the plan to `work/<run-dir>/cycle-plan.json`
instead of the canonical path; the canonical journal is written only at finalize (step 6), which
now requires `asOf`/`mode`/`capturedAt` and forbids bare `ready` entries for mid-run skips.
Guard tests: `tests/test_store_cycle_log_integrity.py` (tripwire — fails the suite red if the
tracked journal is ever reduced to a skeleton) + `tests/test_cli_cycle_plan.py` (7 F74-specific
cases: refuse-enriched, refuse-unparseable, refuse-null-entries, refuse-directory, BOM-tolerant
bare-plan-still-overwritable, plus 3 pre-existing plan tests). This is a lane-scale
**ORDINARY CODE** fix per `desk-change-control`'s taxonomy — `cli.py`'s `_cycle_plan` is not on
the frozen-core list, so no Part-33 migration was needed.

**The restore step turned out to be moot.** By the time the fix landed, the daily instance had
already finalized and committed a healthy journal (`d9cfb3f`); the monthly v3 journal (with the
F71 bypass record) was already safe in git history at `99ca522`. `git restore` was never actually
run against a dirty working tree for this incident — plan for it, but don't assume it will be
needed.

### Fallback branch — if the WHERE ARE WE gate found the clobber has recurred

1. **Do not touch the file yet.** Check whether another instance owns the tree: read
   `docs/superpowers/HANDOFF.md`'s top section and its CONCURRENT-INSTANCE COORDINATION section,
   and check for another instance's claimed worktree/branch (the user-level `instance-sync` skill owns this fully, if present on this machine — it is per-machine and does not travel with a fresh clone).
2. `git diff HEAD -- store/cycle-log.json` to see exactly what would be lost.
3. **The one sanctioned mutating step in this entire campaign:** `git restore store/cycle-log.json`
   (equivalently `git checkout HEAD -- store/cycle-log.json`) — but only once you have confirmed
   no live instance is mid-run against that file, and **get explicit user confirmation before
   restoring if there is any ambiguity about tree ownership.** This is the ONE git-mutating
   command this campaign sanctions; everything else here is read-only investigation or routes
   through a lane/migration for the user to merge.
4. Re-run the two guard tests. If they are RED even with the F74 fix commits present as ancestors,
   the guard itself has a new gap — mint a new F-item and route the fix through
   `desk-change-control` (fix-forward; do not revert the guard, do not hand-patch the journal).

---

## Phase 1 — F71: anchor bound vs. evidence-sufficiency deadlock (OPEN — the live frontier)

**Full mechanism trace, verified code paths, and a designed-but-unbuilt reproduction test:**
`references/f71-mechanism-and-repro.md`. Read it before implementing — it documents an extra,
previously-uncataloged wrinkle (an uncaught `JudgmentError`/`LLMError` crash path under
`--recorded` replay) that any fix needs to close alongside the precedence question.

**The recorded incident** (`git show 99ca522:store/cycle-log.json`, quoted verbatim in the
reference file): the judge rated `moat` **Weak**; the measured anchor was **+0.50**, making
`Weak` illegal under the Part 7 bias guardrail (code bounds the rating). One re-dispatch produced
**Mixed** (anchor-legal) — but that is a rating CHANGE from the prior cycle's memory, and its
citations were 2 secondary publishers (< 3, no primary) — the F63 sufficiency gate correctly
objects. Neither gate is wrong on its own terms; nothing resolves the tie, so the run shipped
under `--no-sufficiency`, a whole-run bypass, on the sufficiency gate's first-ever live firing.

### Solution menu (ranked)

**1 — RECOMMENDED (the backlog's own recorded, user-approved-context lean, `docs/fix-backlog.md:463-484`):**
Treat an anchor-FORCED move as code-computed measured evidence, not a judgment re-rate — **exempt
it from the sufficiency gate**, stamp the rating `"anchor-bounded on thin evidence"` (rendered in
the trust footer, F75's hook), keep the existing confidence-cap propagation. Make the remaining
bypass **per-dimension with a required reason**, or remove the flag entirely once the exemption
path exists. This is narrow: it only fires when the anchor makes the PRIOR rating illegal — a
genuine qualitative re-rate with the same thin evidence still gets blocked, exactly as today.

**2 — companion, not a replacement (charter framing "(b)"):** a general per-item/per-dimension
sufficiency waiver with a logged reason, independent of the exemption logic — this is F75's own
policy layer and should ship whether or not option 1 lands, since some deadlocks may not be
anchor-forced.

**3 — REJECTED-LEAN, do not implement without new evidence (charter framing "(a)"/"(c)" — these
are the same mechanism under two names: "anchor yields when corroboration insufficient" /
"sufficiency wins, rating holds prior + flags under-supported"):** the backlog's own text
considered and rejected this: *"but that publishes a rating the measured anchor declares
illegal"* (`docs/fix-backlog.md:477-478`). Re-opening this path requires new evidence and routes
through `desk-research-methodology`'s evidence bar — it is not a hard user lock, but it is
currently disfavored with a stated reason; do not silently pick it because it looks simpler.

**4 — FENCED OFF (charter framing "(d)"):** widen the anchor tolerance (`_ANCHOR_TOL` in
`gate.py:67`) to make more ratings anchor-legal. This weakens the Part 7 bias guardrail
**globally** to resolve a **local** conflict — F36 tightened this exact constant from 0.5 to 0.15
for a documented reason ("'Very strong' at anchor -0.49 is not judgment room"); undoing that to
patch F71 would reopen the bug F36 closed. Do not do this.

### Migration obligations

`gate.py` and `judgment/judge.py` aggregation are on `docs/roadmap.md`'s frozen-core Standing
Constraints list (matching `desk-change-control` §"FROZEN-CORE" row). **`sufficiency.py` is NOT
currently on that list** (verify: `grep -n "Standing constraint" -A5 docs/roadmap.md`) — but any
F71 fix touches gate semantics as directly as those files do, so flag this gap for the
user/`desk-change-control` rather than asserting `sufficiency.py` is already frozen-core; either
get it added to the formal list via its own decision, or treat it as frozen-core-*adjacent* for
this campaign's purposes without claiming the list already says so. Either way — **any of option
1's or 2's implementations ships only as a Part-33 versioned migration**, following the v1.3 shape
(`docs/migrations/2026-07-contract-v1.3.md`
is the template for a narrow, single-purpose amendment): migration doc with a "Deliberately
unchanged" section, schemaVersion decision stated either way, shadow-run (old vs new gate
behavior over the SAME stored findings, no store writes), replay of affected stored scorecards as
new appended versions, independent hand computation in the commit message, user approval recorded
(never AFK-defaulted for a frozen-core change). Full checklist: `desk-change-control` §3.

**Bundling note — read the backlog's own priority lean before splitting this:** `docs/fix-backlog.md:562-565`
records F72 "with or right after F71 (both are gate-semantics Part-33 work)" — this suggests ONE
coupled migration covering F71+F72 (mirroring the v1.2 precedent, which bundled Lanes A+B into one
migration), not two. Confirm with the user before deciding to split or bundle; do not silently
assume either.

### Acceptance gate (measurable — never judged by eye)

- [ ] The cross-gate deadlock scenario is test-pinned (design in `references/f71-mechanism-and-repro.md`
      §4): an anchor-forced move with insufficient citations resolves via the exemption path, no
      `--no-sufficiency` flag needed, AND a genuine judgment re-rate with the same thin evidence
      is still blocked (regression guard against over-loosening).
- [ ] The uncaught `JudgmentError`/`LLMError` crash path (§3 of the reference file) gets a clean
      handler analogous to `_report_sufficiency_violations` — a Sonnet session hitting an anchor
      conflict under `--recorded`/`--recorded-judge` should see a re-dispatchable message, not a
      traceback.
- [ ] Whole-run `--no-sufficiency` is gone from live paths, or is per-dimension + required reason
      (verify: `Select-String gpu_agent/cli.py -Pattern "no-sufficiency"` — either zero hits on
      the live pipeline path, or hits only on a per-dimension-scoped flag).
- [ ] Full suite green; eval pin re-checked (this fix touches gate logic, not emitted prompt
      bytes, so the pin should stay green — confirm, don't assume: `desk-change-control` §4 owns
      what to do if it doesn't).
- [ ] `run-cycle` SKILL.md's re-dispatch instructions (currently ~lines 141-162) are updated to
      cover the exemption path and the new clean handler, not just voice-lint/sufficiency.

---

## Phase 2 — F75: no whole-run gate bypass flags before any unattended loop (OPEN)

**The pattern, not just the incident:** every gate in this repo ships with a whole-run bypass
(`--no-sufficiency`, `--no-voice-lint` — full catalog and forbidden-use protocol: `desk-config-and-flags`),
and the ONE time the sufficiency gate contested a live rating, the bypass won after one rewrite
attempt — meaning the first flagship on the post-F63 stack ran in the exact configuration the F63
corroboration doctrine was designed to prevent (loosening live, counterweight off).

**What ships:**
1. Every remaining whole-run bypass becomes **per-item + required reason + logged**, or is
   removed outright. F71's exemption path (Phase 1, option 1) removes the NEED for
   `--no-sufficiency` in the anchor-forced case specifically; F75 is the umbrella policy for
   every OTHER gate's bypass, present and future.
2. **Trust-footer disclosure:** a cycle whose log records any bypass/waiver cannot render
   `status: ready` without a waiver line surfacing in the brief. Hook point:
   `gpu_agent/brief.py::render_market_caveat` (currently lines 146-156 — verify before citing,
   this file is not byte-frozen) already renders one honest caveat above the appendix divider;
   this needs a second, conditional line sourced from the cycle log's `gates.*` bypass records.
   This is currently UNBUILT — `render_market_caveat` today only covers index-level noise, not
   gate bypasses.
3. **Retro clause:** the next MONTHLY brief's trust footer should note that 2026-07-v3 ran under a
   sufficiency bypass (the store itself stays immutable — append-only, never hand-edited; the
   RENDER is the correct surface for this disclosure, not the historical scorecard).
4. `run-cycle` SKILL.md's current instruction (`Select-String -Path .claude/skills/run-cycle/SKILL.md
   -Pattern "no-sufficiency"` — currently around lines 159-162, verify before citing) teaches
   "neither check ever blocks a scorecard… run with `--no-voice-lint` or `--no-sufficiency`". This
   text is F75's own named removal target — replace it with the per-item-waiver instruction once
   the mechanism exists; do not extend it, do not add a third bypass flag following its pattern.

**Classification:** the flag removal/scoping in `cli.py` and the `brief.py` rendering hook are
ORDINARY CODE (lane path); the SKILL.md prose change is DOCTRINE (needs user approval per
`desk-change-control`'s taxonomy, since it changes what a binding skill instructs).

### Acceptance gate

- [ ] `Select-String -Path gpu_agent/cli.py -Pattern "no-sufficiency|no-voice-lint"` shows either
      zero hits on live-path commands, or hits only where the flag is now per-item-scoped with a
      mandatory reason argument.
- [ ] A bypass/waiver record in `store/cycle-log.json` renders in the corresponding brief's trust
      footer — test-pinned, not eyeballed.
- [ ] `run-cycle` SKILL.md no longer contains the "neither check ever blocks a scorecard" line.
- [ ] The 2026-07-v3 retro disclosure exists somewhere a reader would see it before the next
      monthly brief ships.

---

## Phase 3 — F72: syndication-resistant publisher identity (OPEN)

**Real store precedent + a constructed adversarial fixture:** `references/f72-adversarial-fixture.md`.
Verified 2026-07-06: the three archetypal syndication endpoints the backlog names
(`stocktitan.net`, `markets.financialcontent.com`, `finance.yahoo.com`) individually appear in the
live store, but no single scorecard today has all three co-cited as ONE claim's distinct-publisher
set — **F72 is a proven structural risk, not yet a witnessed silent failure.** Build the
adversarial test as a constructed fixture (sketch in the reference file), not a replay of a real
incident, and re-run the `Select-String` check yourself before asserting otherwise — the store
grows every cycle and this could change.

**The hole:** `gpu_agent/publisher.py::publisher_key` returns the evidence URL's netloc, nothing
else. `registry/corroboration.json`'s `minDistinctPublishers: 3` counts DISTINCT NETLOCS, so one
wire press release republished on 3 different domains counts as 3 distinct publishers
deterministically — silently unlocking gate F2e's high-confidence exception, thesis rule 6's
corroborated-reversal exception, and wiki page promotion, all at once, because all three consumers
import the SAME `publisher_key` function (`gate.py:6`, `wiki/lifecycle.py:59`, `thesis.py:477`).
**This is the mirror-image risk to F71**: F71 is HONEST thin evidence (2 real publishers) failing
loudly and getting bypassed; F72 is DISGUISED thin evidence (1 story, 3 netlocs) that would pass
completely unremarked — no bypass record, no log line, nothing to catch in review.

**Fix, lean (from the backlog, not yet built):**
(a) content-similarity collapse across domains, reusing the existing L1 near-dup infrastructure
(wire bodies are near-identical — the same machinery that already dedupes ingested documents by
content hash); and/or
(b) a `registry/syndicators.json` data list of known wire/aggregator netlocs that collapse to the
originating publisher.
Either closes F69's open handoff note in passing: give the gatherer's chase/corroboration result a
structured home (an originating-publisher field on the blob/finding) instead of free text in
`content`.

**Classification:** a counting-semantics change to gate F2e is a **FROZEN-CORE** change (touches
`gate.py`'s corroboration count, which the backlog text itself states explicitly: "Counting-
semantics change in F2e → ships as a Part-33 versioned migration"). `registry/syndicators.json`
itself is DATA, but since it feeds the frozen gate's computed result, the combined change is
FROZEN-CORE + possibly PROMPT (if the extraction-prompt sentence "distinct outlets, not syndication
of one story" tightens, the hash pin trips — route through `desk-change-control` §4 / `run-eval`).

### Acceptance gate

- [ ] One constructed story with near-identical bodies on 3 syndicator domains fails the ≥3 bar
      (test-pinned, per `references/f72-adversarial-fixture.md` §2).
- [ ] 3 genuinely distinct outlets (different bodies, none on a known syndicator netloc) still
      pass at distinct-publishers = 3 (regression guard — the fix must not make corroboration
      harder for real cases).
- [ ] All three consumers (gate F2e, thesis rule 6, wiki page promotion) are verified — not
      assumed — to inherit the fix via the shared `publisher_key` import.
- [ ] Full suite green; eval pin re-checked if the extraction prompt sentence changed.

---

## Fenced-off wrong paths (each with why)

| Wrong path | Why it's fenced off |
|---|---|
| Hand-editing `store/cycle-log.json` (or any brain output / recorded answer / `fixtures/evals/baseline.json`) | Maintainer-confirmed law, applies across this whole cluster: a rejected/incomplete answer is re-dispatched with the verbatim violation appended, never hand-patched. The cycle log is a brain/gate-approved record — hand-editing it is exactly the "ungated judgment reaching canonical" Part 7 exists to prevent |
| Blanket `git add store/` or `git add -A` | The F74 trap's exact vector — always diff `store/cycle-log.json` first; see CLAUDE.md preflight and `desk-run-and-operate` |
| "Just delete/disable the sufficiency gate" | Defeats the entire F63 corroboration doctrine — turns a documented, loudly-gated deadlock into a silent invented-judgment path, the one thing Part 7's gate is for |
| Widening ε or hand-editing `fixtures/evals/baseline.json` to make an eval pass | None of F74/F71/F75/F72 are prompt changes by default; IF a fix trips the pin (F72's prompt sentence is the likely case), route through `desk-change-control` §4 / `run-eval` — never force or hand-edit the baseline |
| Treating `run-cycle` SKILL.md's current bypass instructions as durable doctrine | They are F75's own named removal target (see Phase 2, item 4) — do not cite them as policy, do not copy their pattern for a new gate |
| Widening `_ANCHOR_TOL` (`gate.py:67`) to fix F71 | FENCED OFF — see Phase 1, option 4. Weakens the Part 7 bias guardrail globally to fix one local conflict; F36 tightened this exact constant for a documented reason |
| Resurrecting SEC-EDGAR/scraper-benchmark ideas as a "better source" fix for F72 | User-locked rejection (`desk-change-control` §9) — the defect is counting logic/a data list, not source acquisition |
| Reordering the user-locked F-sequence, or promoting the F72-F76 "lean" ordering to a decision | The F72-F76 priority (F74 immediately, F72 with/after F71, F75 before any unattended loop) is explicitly "user to confirm," not a lock — don't reorder unilaterally, but don't treat it as already-approved either |

## Validation & promotion — how every phase lands

Every phase in this campaign is a normal `desk-change-control` classification, not a special
path: Phase 0's fix was ORDINARY CODE (lane, merged); Phase 1/3 are FROZEN-CORE (Part-33 migration,
user approval, shadow-run, replay); Phase 2 is ORDINARY CODE + DOCTRINE (lane + user-approved
SKILL.md edit). **Success is measured by the acceptance-gate checkboxes above, never by eye or by
a marginal eval verdict** — and if a fix happens to touch emitted prompt bytes, remember F73's
open finding: the eval gate has never demonstrably caught a real regression and its margins sit
inside documented same-prompt noise, so a PASS/FAIL verdict on THIS cluster's changes is not by
itself proof of correctness — the acceptance-gate tests are the proof; the eval verdict is a
separate, independently-required gate.

## The prize

`docs/roadmap.md`'s autonomy track ladder is **attended → supervised-unattended → unattended-
with-gates**, with an **n=1 pilot planned during Phase 2**. `docs/fix-backlog.md` states F71's
fix "must land before any unattended loop runs a cycle" and F75's policy applies "before ANY
unattended loop" — both are explicit, named prerequisites for that pilot, not general hygiene.
Closing this cluster (F71+F75 specifically; F72 and F74 harden the same trust surface) is what
turns "an instance facing this deadlock with nobody watching needs a coded rule, not a flag" from
an aspiration into a shipped fact.

## Common mistakes

- **Assuming Phase 0 is still open because this doc (or the charter's framing, or an older
  sibling skill) says so.** It closed on `main` at `257cf1b`, six-plus commits before this file
  was authored. Always run the WHERE ARE WE gate first.
- **Treating "F74's checkbox is now `[x]`" as evidence the WHOLE cluster is closed.** F71/F72/F75
  remain independently open; reconcile each one separately (`desk-change-control` §6's git-over-
  checkbox rule applies per-item, not per-cluster).
- **Assuming a gate conflict always produces a clean `sufficiency:`/`voice-lint:` stderr message.**
  The anchor-bound conflict path has NO clean CLI handler today (§3 of the F71 reference file) —
  an uncaught traceback mentioning "contradicts anchor" is the EXPECTED symptom under current
  code, not evidence of a new, unrelated bug.
- **Conflating F71's fix (anchor-forced-move exemption) with F72's fix (publisher distinctness).**
  Different gates, different mechanisms — even though the backlog's own priority lean suggests
  bundling them into ONE Part-33 migration, each needs its OWN acceptance criteria and its own
  shadow-run/replay evidence inside that migration doc.
- **Quoting charter Part 37 line ~1637's "Not yet: hard corroboration…" as if it settles F72's
  status.** It contradicts the F63 amendment ~60 lines above it — an unresolved internal
  contradiction (`desk-change-control` §1 DOCTRINE row, `market-state-reference` §6). Flag it,
  don't resolve it, and don't let it stand in for this campaign's own F72 status (which is: open,
  unbuilt, verified above).
- **Picking solution-menu option 3 (Phase 1) because it looks like less code.** It is the
  backlog's own explicitly rejected-lean path, with its rejection reason stated in the same
  sentence that considered it. Reopening it needs new evidence via `desk-research-methodology`,
  not a unilateral pick.

## Provenance and maintenance

Authored 2026-07-06 against `main @ f7c83f0`. The skill-library discovery snapshot this campaign
was originally scoped against was `main @ a8ec757` (2026-07-05) — treat that hash as historical
context only; by authoring time six-plus commits had already closed F74 on it (`d84f3b9` claim →
`3613ede`/`9a5f9b2` fix → `257cf1b` merge → `1a9eb33` backlog tick), a daily cycle had run
(`d9cfb3f`), and a blind baseline ablation had been scored (`639c00d`/`f7c83f0`, born F77 —
outside this campaign's scope). Concurrent instances are active in this repo; re-run every check
below yourself before trusting a number in this file.

| Fact class | Re-verification command |
|---|---|
| HEAD / tree / worktrees | `git log --oneline -1; git status --short; git worktree list` |
| F74 closed? | `git log --oneline --all --grep="F74"` then `git merge-base --is-ancestor 3613ede HEAD; $LASTEXITCODE` (0 = closed) |
| F74 guard tests green? | `.venv\Scripts\python -m pytest tests/test_store_cycle_log_integrity.py tests/test_cli_cycle_plan.py -q` |
| F71/F72/F75/F76/F77 open? | `Select-String -Path docs/fix-backlog.md -Pattern "F71 —\|F72 —\|F75 —\|F76 —\|F77 -"` then `git log --oneline --grep="F71"` etc. per item |
| Bypass flags still on live paths | `Select-String -Path gpu_agent/cli.py -Pattern "no-sufficiency\|no-voice-lint"` and `Select-String -Path .claude/skills/run-cycle/SKILL.md -Pattern "no-sufficiency\|bypassed"` |
| F72 registry absent | `Test-Path registry/syndicators.json` |
| Anchor tolerance constant | `Select-String -Path gpu_agent/gate.py -Pattern "_ANCHOR_TOL"` |
| Min distinct publishers | `Get-Content registry/corroboration.json` |
| Real syndication co-occurrence in store | `Select-String -Path store/chips.merchant-gpu/*.json -Pattern 'stocktitan\.net\|financialcontent\.com\|finance\.yahoo\.com'` (bash equivalent: `grep -o` per file, then diff domain sets per scorecard) |
| Suite size / green | `.venv\Scripts\python -m pytest -q` (1066 passed / 4 skipped, 1070 collected, as of 2026-07-06 — counts drift) |
| Migration count | `Get-ChildItem docs/migrations/` (2 files as of 2026-07-06: v1.2, v1.3 — a bundled F71+F72 migration would be a 3rd) |
| Trust-footer hook location | `Select-String -Path gpu_agent/brief.py -Pattern "TRUST"` (currently `render_market_caveat`, ~lines 146-156 — not byte-frozen, will move) |
