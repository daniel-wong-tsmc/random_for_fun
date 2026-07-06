---
name: desk-proof-and-analysis-toolkit
description: Use when deciding whether an eval verdict, scoring swing, or live-cycle diagnosis is signal or noise; proving a gate would actually catch a regression (F73, seeded-regression canary); regenerating fixtures/golden/* or replaying/shadow-comparing frozen-core math after a Part-33 migration; verifying the report renderer is byte-deterministic; writing a pre-committed pass/fail disposition before a risky run; adversarially refuting a root-cause diagnosis before trusting it; or asking what an n=3 replicate baseline can license you to claim.
---

# Desk Proof and Analysis Toolkit

## Overview

In this repo, a claim is not evidence until a repeatable procedure produced it this session — and the harder claims (a gate works, a diagnosis is right, a migration is safe) need more than a single run to survive first contact with noise. This skill is a library of first-principles analysis **recipes** — when to use, the steps, a worked example drawn from this repo's own incidents, and what counts as proof — for the eight recurring "prove it" situations this desk has actually faced.

## When to use / When NOT to use

| Situation | Go to |
|---|---|
| Running eval steps 1–6 mechanically (emit/dispatch/record/verdict/rebaseline) | repo skill `run-eval` — this skill owns the underlying math and proof standard, not the dispatch choreography |
| The fixture-family taxonomy, hash-pin discipline, or today's suite counts | `desk-validation-and-qa` |
| Executing the live F74→F71→F75→F72 gate-integrity campaign itself | `gate-integrity-campaign` |
| The general evidence-bar / idea-lifecycle doctrine (hunch → pre-committed disposition → test → disposal) as a repo-wide discipline | `desk-research-methodology` |
| The incident narrative — what happened, when, in what order | `desk-failure-archaeology` |
| Classifying a change as DATA/PROMPT/FROZEN-CORE/DOCTRINE, or the Part-33 migration paperwork itself | `desk-change-control` |
| Store/wiki/dedup seam-noise measurement tooling (not eval) | `desk-diagnostics-and-tooling` |
| Symptom→triage tables for known failure modes | `desk-debugging-playbook` |

Use this skill when you need to **construct or reproduce** a proof; use the skills above when you need to **execute** the procedure that proof already governs, or to **read** an existing incident/count.

---

## Recipe 1 — Replicate & noise analysis (the eval-v2 bar)

**When to use:** an eval seam looks like it passed or failed "by a hair"; you're asked whether a scoring change is a real regression or generation noise; you need to recompute or sanity-check the eval-v2 epsilon yourself instead of trusting a stale number.

**The math (verified against `gpu_agent/evals/harness.py`, 2026-07-06):**
- `seam_quanta`: quantum = 1 / (number of *positive* cases in that seam), computed from the live case set, not hardcoded. Current golden set: extract 1/8 = 0.125, judge 1/4 = 0.25, thesis 1/2 = 0.5.
- `compute_epsilon`: for each seam, `ε = max((max − min) / 2 over 3 replicate seam means, quantum)`. The quantum is a floor — it exists so identical replicates (ε would be 0) don't produce a knife-edge bar.
- Seam prong: `PASS iff fresh ≥ (replicate mean − ε)`; hard-fail line is `mean − 2ε`.
- Crater prong (`CRATER_DROP = 3`): a single positive case fails independently of its seam mean if `total ≤ caseMedian − 3` (hard crater at `median − 5`, `HARD_CRATER_EXTRA = 2`).
- `DISPERSION_LIMIT = 1.0`: rebaseline refuses if any seam's replicate range exceeds 1.0 — the code's own comment is explicit: **"this is breakage, not noise."**
- One value below is decided with a two-run replication mean, never a third run (`gpu_agent/evals/harness.py:evaluate_v2`).

**Steps:**
1. Gather ≥2 (ideally 3+) `report.json` files from retained run dirs for the *same* prompt bundle (same `promptHashes`) — a fresh rebaseline's replicates, top-up runs, or an old worktree's archived runs.
2. Run `.venv/Scripts/python .claude/skills/desk-proof-and-analysis-toolkit/scripts/measure_seam_noise.py <report1> <report2> [<report3> ...]` — a read-only stdlib script that reprints exactly the mean / half-range / quantum / epsilon table `harness.py` computes, plus a per-case swing table. It does not gate, does not write a baseline, and does not require the venv's non-stdlib deps.
3. Compare the printed epsilon to what's committed in `fixtures/evals/baseline.json` for the same bundle — they should match if you fed it the same 3 replicates the baseline was built from (this is a real self-check the script passed against the current F63 baseline: see Provenance below).
4. If the swing is large and confined to specific cases (not spread across all cases), that is the **F62 deficit-signature pattern**: check whether every generation missed the *same* rubric criterion for the *same* reason — that is systematic, not noise (see worked example).

**Worked example — the fight that birthed eval-v2 (2026-07-04/05):** F63 failed a single-run bar twice by a margin later traced to the bar itself being a lucky high draw (F62's "attempt 3"), not a real regression — full symptom→root-cause→evidence chronicle: **desk-failure-archaeology** fight #9. The number this recipe needs from it: the re-gate under the resulting eval-v2 replicate baseline then passed on the first fresh run at **margin 0.042** (r1 extract 6.625 vs bar 6.5833) — "deep inside noise" by F73's own framing, and the specific value recipe 8's n=3 honesty bounds are calibrated against. Full numeric archive (identical-bundle swing table, all three post-eval-v2 replicate sets, and a live 2026-07-06 re-run of this recipe's own script against the current baseline's source data): `references/eval-noise-archive.md`.

**Contrast — the earlier F62 fight shows the OTHER failure mode (systematic, not noise):** full chronicle: **desk-failure-archaeology** fight #8. The pattern this recipe needs from it: all 8 fresh judge generations across two full attempts failed the *same named criterion* for the *same stated reason* — a deficit *signature*, not scattered draw luck — and the fix moved that exact criterion 1→2 on every fresh generation once applied. Uniform failure on one named criterion across independent generations is how you tell signal from noise; recipe 1's step 4 above is this exact check, generalized.

**What counts as proof:** a swing is "noise" only if (a) it's small relative to the measured half-range across ≥3 replicates of the *same unchanged* bundle, and (b) the lost points scatter across different cases/criteria for different reasons. A swing is "signal" if the same criterion fails the same way across every independent generation — that pattern survives replication by construction, so one replication that reproduces it is enough to call it real.

---

## Recipe 2 — Gate-power analysis (F73 — open, candidate design)

**When to use:** before trusting that eval-v2 (or any gate) would actually catch a real regression, not just pass good prompts through a wide-enough bar. **Status: F73 is an open backlog item; nothing below is built.** Label every claim from this recipe candidate/unbuilt until a canary run actually exists.

**The problem, stated precisely (`docs/fix-backlog.md` F73, `docs/superpowers/eval-notes/*`):** the live committed baseline's ε is 0.25–0.5 per seam (extract 0.3125, judge 0.25, thesis 0.5 — re-derive from `fixtures/evals/baseline.json` live, don't quote the backlog's older "0.19–0.5" text, which predates the current baseline); documented identical-prompt seam swings across the F62/F63 archive are 6.25–7.50 (roughly a 1.25-point range on a similar bundle); the F63 re-gate passed extract by 0.042. **The eval-v2 gate has never demonstrably caught a real regression** — every observed gate action to date has been either a pass, or a fail later diagnosed as bar noise, never a fail confirmed to be a genuine prompt defect.

**Recipe (candidate — this is a design to build, not a report of what exists):**
1. **Seeded-regression canary.** Deliberately damage a known-good prompt bundle in a way you can name (e.g., strip the F63 corroboration-scope sentence, or revert the F62 consensus-departure clause) and run it through the *current* eval-v2 gate. If the gate does not at least MARGINAL-FAIL, the gate has no demonstrated power at that damage magnitude — that is itself the proof result, not a bug in the canary. Run this once now, and again after any harness change, and commit the calibration note either way.
2. **Symmetric marginal band.** Today only failing seams get a forced replication (`evaluate_v2`'s `marginal-fail` branch); a PASS that clears the bar by less than ε (the F63 re-gate's 0.042 case) decides alone on one run. Candidate fix: a PASS within ε of the bar also auto-replicates once, mirroring the fail side, before the PASS is trusted.
3. **Pooled dispersion.** ε today comes from exactly 3 replicate means (a 3-point half-range). Candidate fix: append each gate run's fresh seam scores to a running pool across bundles/time so ε converges toward a real long-run noise estimate instead of resetting to a fresh 3-point spread at every rebaseline.

**What counts as proof (once built):** a canary run where the gate hard-fails a bundle you know is broken, with the calibration note describing exactly what was damaged and by how much, committed alongside the code that runs it — this is the same "run it, record the pre-committed disposition, keep the result regardless" discipline as recipe 6, applied to the gate's own power rather than to a candidate prompt. Before picking a case to damage: `references/eval-noise-archive.md` notes that `extract-2026-07-05` already runs noisier than the other 7 extract cases — don't build a canary's signal detection around the case with the highest pre-existing baseline noise.

---

## Recipe 3 — Independent hand computation (the golden-fixture rule)

**When to use:** `fixtures/golden/*` needs regenerating after a frozen-core (`gate.py`/`scoring.py`/`pipeline.py`) change — the ONLY time this fixture family may change (route the classification itself through `desk-change-control`).

**The rule:** you may never regenerate a golden fixture by running the new code and pasting its output back as the new "expected" file. You must compute the expected numbers **independently** — by hand, from the formula, not by trusting the same code you're trying to pin — and the commit message must show that computation. If your hand computation doesn't match the code's output, that is a defect in one of them; find out which before committing either.

**Precedent (commit `859ac35`, "regenerate golden fixtures once under v1.2 math", verified 2026-07-06):**
```
Independent hand computation (per (entity, indicator), latest vintage,
weight*polarity*magnitude/3; weights D2=.10 S9=.04 S10=.08 from assignment
overrides, market-share-pct=.10 from spec):
  f-nvda-d2  (D2, NVDA)             dmi += .10*1*2/3 = .066667
  f-amd-s9   (S9, AMD)              dmi += .04*-1*2/3 = -.026667 ; smi += .04*1*2/3 = .026667
  f-nvda-moat(market-share-pct,NVDA) dmi += .10*1*1/3 = .033333
  f-intc-s10 (S10, INTC)           smi += .08*1*1/3 = .026667
  DMI = .073333  SMI = .053333  sdgi = .02 -> balanced
Regenerated file matches exactly.
```
This is the whole procedure — there is no regeneration *script*; the CLI `run` path produces the candidate file, and the commit message's independent arithmetic is the check that the candidate is right.

**Steps for the next regeneration:**
1. Confirm the change is a properly-approved Part-33 migration (`desk-change-control`) — golden regeneration never happens standalone.
2. Run the CLI `run` path (`tests/test_golden_integration.py` shows the invocation) to produce the candidate `scorecard.json`.
3. Independently compute the expected DMI/SMI/SDGI (or whatever changed) per the formula in `scoring.py`, by hand or in a scratch calculation separate from the pipeline code — using the registry weights and the fixture findings' polarity/magnitude directly, not by re-deriving them from the pipeline's intermediate output.
4. State both the formula and the per-finding arithmetic in the commit message, and say explicitly whether it matches.
5. If it doesn't match, stop — you have found either a hand-computation error or a real code defect, and you must not commit until you know which.

**What counts as proof:** a commit message containing the formula, the per-item arithmetic, and an explicit match/no-match statement — reviewable by a human who never runs the code.

---

## Recipe 4 — Shadow-run + replay verification (frozen-core migrations)

**When to use:** a Part-33 migration changes `scoring.py` math and existing store history needs to move onto the new math without being re-gated (re-gating history would mean re-judging findings against rules that didn't exist when they were captured — a doctrine violation).

**Two distinct tools, both one-shot artifacts of the v1.2 migration (`scripts/`, verified 2026-07-06):**
- **`shadow_run_v12.py`** — computes OLD math and NEW math side by side over the *same* stored 2026-06 findings, prints a Markdown table, **writes nothing to the store**. This is the "does the new formula actually differ, and by how much, before we commit to it" check.
- **`replay_v12.py`** — for each stored `2026-06-v1..v6`, recomputes `demandSupply` (DMI/SMI/SDGI) and the two-index split under v1.2 math, copies `findings`/`ratings`/`narrative`/`confidence`/`dimensionStatus`/`categoryStatus` **verbatim**, stamps `provenance.replayOf` / `provenance.migration`, and **appends** via `JsonStore` — v1..v6 are never touched; the replays land as new immutable versions v7..v12 (confirmed present in `store/chips.merchant-gpu/` today). The module docstring states the doctrine directly: *"This re-runs the MATH, not the gate."*

**Steps to build the equivalent for a future migration:**
1. Write the shadow-run comparison first (no store writes) — it is your evidence that the new formula changes anything at all, and by how much, before you touch history.
2. Write the replay script to APPEND, never overwrite; it must copy judgment fields verbatim and only recompute the math the migration actually changed.
3. Pin the replay's output with a test that independently recomputes at least one replayed value by hand (same discipline as recipe 3) and asserts the historical judgment fields are byte-identical to the original.
4. Never re-run a completed replay script — once v7..v12 exist and are pinned, re-running would try to append v13..v18, which is not the intent (the discovery-era guidance to "not casually re-run replay" still holds — verify a script hasn't already run by checking whether its target versions already exist in `store/` before invoking it).

**What counts as proof:** the shadow-run table (old vs new, on real stored data) plus a replay whose test asserts (a) judgment fields are verbatim and (b) at least one recomputed number matches an independent hand calculation.

---

## Recipe 5 — Byte-determinism proofs (the report renderer)

**When to use:** verifying that `gpu_agent/report.py` (or any renderer downstream of the gated store) is a pure projection — same inputs always produce the same output bytes, with no hidden clock read, no dict-ordering nondeterminism, no locale dependence.

**The contract (`gpu_agent/report.py:1-5`, verified 2026-07-06):** *"Pure functions, no LLM, no network, no store writes. Same scorecard + prior → byte-identical report. The only injected time input is `render_ts` (a caller-supplied string); render functions never read the clock."*

**Steps:**
1. Call the renderer twice with the *same* arguments, including a fixed `render_ts` string (never `None` — `None` defaults to `datetime.now(timezone.utc)`, which would make the test itself nondeterministic).
2. Assert the two outputs are equal (`a == b`), not just "similar" — a genuine byte-determinism proof is a strict equality assertion, e.g. `tests/test_report_surgery.py::test_byte_determinism_with_thesis_book_and_movement` (renders with a thesis book and movement data, both times with `render_ts="fixed"`, asserts `a == b`).
3. Separately assert the injected `render_ts` — not `datetime.now()` — appears in the output, so a future edit can't reintroduce a clock read that happens to be deterministic only because the test runs fast (`tests/test_report.py::test_render_report_uses_injected_render_ts`).
4. If you add a new input to the renderer (a new section, a new store-fed field), extend the byte-determinism test to include it — the proof only covers the inputs it actually varies.

**What counts as proof:** a passing test that (a) calls the renderer twice with identical fixed inputs including a fixed `render_ts`, (b) asserts strict string equality of the two outputs, and (c) is re-run, not merely inspected — `.venv/Scripts/python -m pytest tests/test_report_surgery.py tests/test_report.py -k determinism` is the live command.

---

## Recipe 6 — Pre-committed dispositions

**When to use:** before running any eval, migration, or risky experiment whose outcome you can't predict — write down what you will do for EACH possible outcome before the outcome exists, so the outcome can't retroactively rationalize a different response ("retry until green" is explicitly forbidden doctrine).

**The template, exactly as practiced (`docs/superpowers/eval-notes/2026-07-04-f63-run-notes.md`, recorded BEFORE any `record-grade`):**
```
PASS -> gpu-agent eval rebaseline --out ... --reason "...", commit baseline + RUN-NOTES,
        full suite (no deselects) green.
One FAIL -> diagnose per-case vs baseline, run ONE full replication.
Two FAILs -> STOP, keep the pin red, record BLOCKED-on-user with both runs' data.
NOT retry-until-green.
```
Under eval-v2 this became mechanical rather than freehand (`docs/superpowers/eval-notes/2026-07-05-f63-regate-run-notes.md`): *"PASS → mint verdict.json → top up to 3 replicates → rebaseline --runs … --verdict …; MARGINAL-FAIL → exactly one replication, two-run mean decides, hard stop; HARD-FAIL → stop immediately. Not retry-until-green."*

**Steps:**
1. Enumerate every outcome class the procedure can produce (not just "pass/fail" — eval-v2 has pass / marginal-fail / hard-fail / invalid-run).
2. For each class, write the exact next action, including what you will NOT do (the "NOT retry-until-green" line is doing real work — it forecloses the tempting wrong move before temptation exists).
3. Commit or otherwise timestamp the disposition (a run-notes file, a comment, a message) BEFORE the result-producing command runs.
4. Execute; then compare the actual outcome to the pre-committed branch and follow it — the entire value of this recipe is that step 4 requires no new judgment call, because the judgment call already happened in step 1–2 under less motivated reasoning.

**What counts as proof:** a timestamped or committed artifact (run-notes, commit message) whose text exists *before* the result it governs, containing an explicit "what I will NOT do" clause for at least the tempting failure mode.

---

## Recipe 7 — Adversarial self-refutation

**When to use:** before believing any diagnosis of a root cause — construct the observation that would prove the diagnosis wrong, and go look for it, before acting on the diagnosis.

**Worked example — a wrong diagnosis that WOULD have shipped (F27):** full incident: **desk-failure-archaeology** fight #4. The lesson this recipe needs: a diagnosis ("empty weights → zero indices") survived into a backlog item and even a "DONE" checkbox without ever being checked against actual runtime behavior — it was stale, and only the five minutes of checking caught it.

**Worked example — a guess correctly discarded (F74, merged `257cf1b`):** full incident: **desk-failure-archaeology** fight #12 and `gate-integrity-campaign`'s Phase 0. The falsification move this recipe needs: the initial hypothesis ("likely the pipeline/cycle finalize step") was checked against WHEN the corruption actually appeared (run-start, not run-end) before anyone touched code, and that check pointed to the opposite end of the cycle from the guess — `cli._cycle_plan`'s write at run-start, not a finalize-step write. A fix built on the unchecked guess would have shipped a no-op while the real clobber kept firing.

**Steps:**
1. State your diagnosis as a falsifiable claim: "X causes Y because Z."
2. Ask: what observation, if it existed, would prove this wrong? (For F74: "if the clobber timestamp is at run-START, not run-END, the finalize-step guess is wrong.")
3. Go look for that observation specifically — grep the actual write call sites, check the actual timing, read the actual code path — before writing the fix.
4. If the falsifying observation exists, discard the diagnosis and find the one that survives the same test.
5. Only fix the diagnosis that has been checked against its own falsifying observation, not the first plausible-sounding guess.

**What counts as proof:** a diagnosis that names the specific evidence someone looked for BEFORE fixing anything, and states what that evidence would have looked like if the diagnosis were wrong — not just a fix that happens to make a symptom go away.

---

## Recipe 8 — Provenance math: what n=3 licenses you to say

**When to use:** anytime someone (including you) is tempted to describe the current eval baseline as well-calibrated, precise, or low-variance.

**The honest bounds:**
- The committed baseline is exactly **3 replicates** of one prompt bundle (`fixtures/evals/baseline.json`, verified 2026-07-06: `extract` seamMean 6.75 from replicate seam means 6.625/6.5/7.125; `judge` 7.5833 from 7.75/7.5/7.5; `thesis` 6.0 from 6.0/6.0/6.0).
- n=3 licenses you to say: "the half-range across these 3 draws was X" and "ε is at least the quantum floor, and at least half that range." It does NOT license you to say the true population standard deviation, a confidence interval, or that ε is calibrated to any target false-positive/false-negative rate — none of that follows from 3 points.
- The **thesis** seam's 3 replicates in the current baseline are IDENTICAL (6.0/6.0/6.0) — its ε sits entirely at the quantum floor (0.5), not because thesis is more stable than the other seams, but because 3 draws happened to tie. Do not read a tied n=3 sample as evidence of low variance; a 4th draw could easily land elsewhere.
- The dispersion guard (`DISPERSION_LIMIT = 1.0`) catches only *gross* disagreement (>1.0 point range) as "breakage, not noise" — it does not validate that a range under 1.0 is actually sampling noise rather than a smaller real effect; that judgment still needs the case-by-case pattern check from recipe 1.
- Every rebaseline resets ε to a fresh 3-point estimate; there is currently no accumulation of historical dispersion across rebaselines (recipe 2's "pooled dispersion" idea is exactly the unbuilt fix for this).

**What counts as proof (of a variance CLAIM specifically):** never more than "measured across these N draws, on this date, against this bundle" — always state N and the date; never round n=3 up to "well-established" or "calibrated" language. If someone asks for a confidence interval or a false-positive rate, the honest answer is "not estimable from 3 points; would need recipe 2's canary + pooled-dispersion work first."

---

## Common mistakes

- **Treating a marginal PASS as validation.** The F63 re-gate passed extract by 0.042 against a bar with ε=0.3125 — that is a pass "deep inside noise" (F73's own framing), not confirmation the prompt is good.
- **Regenerating a golden fixture by running the code and pasting its output back.** That pins whatever the code currently does, bugs included — it is not a check on the code at all. The hand computation is the check.
- **Re-running a replay script "just to be sure."** `replay_v12.py` mutates the store by appending; running it again would mint v13..v18 unnecessarily. Check whether the target versions already exist first.
- **Fixing the first plausible-sounding root-cause guess** without checking it against evidence that would prove it wrong (F74's "finalize step" guess would have shipped a no-op fix had it not been checked against the actual write call site).
- **Letting a checked-DONE backlog item's original diagnosis stand unexamined** (F27) — the "DONE" checkbox covers the actual fix shipped, which may not match the originally-stated symptom.
- **Confusing a swing that's scattered across cases/criteria (noise) with a swing that's uniform across independent generations on one named criterion (signal)** — see recipe 1's F62 vs F63 contrast.
- **Describing an n=3 baseline as calibrated or low-variance.** It licenses a half-range and a floor, nothing more (recipe 8).
- **Writing a disposition AFTER seeing the result** and calling it "pre-committed" — the entire value is in the ordering; a post-hoc rationalization is not a disposition.
- **Believing F73 is closed because eval-v2 exists.** eval-v2 replaced a zero-tolerance bar with a noise-aware one; it did not yet demonstrate the gate catches a real regression at all (recipe 2 is still candidate/unbuilt).

## Provenance and maintenance

Authored 2026-07-06 against `random_for_fun` main @ `f7c83f0` (discovery baseline was 2026-07-05 @ `a8ec757` — the repo has moved on; re-verify HEAD before trusting any commit hash below as "current"). Every fact above was re-checked directly against the repo this session (file reads, `git show`, a live run of `scripts/measure_seam_noise.py` against retained worktree data), not carried from the discovery digest unverified. **Recipes 1 and 7 trimmed 2026-07-06** to stop independently re-narrating the F62/F63/F27/F74 incidents at length — those facts have one home now, `desk-failure-archaeology`; this file keeps only the recipe-specific lesson each incident illustrates.

Re-verify before relying on any of the following:

| Fact class | Re-verification command |
|---|---|
| Current HEAD / whether the repo has moved | `git rev-parse HEAD` ; `git log --oneline -5` |
| eval-v2 constants (CRATER_DROP, HARD_CRATER_EXTRA, DISPERSION_LIMIT, quanta formula) | `grep -n "CRATER_DROP\|HARD_CRATER_EXTRA\|DISPERSION_LIMIT\|def seam_quanta\|def compute_epsilon" gpu_agent/evals/harness.py` |
| Current committed eval baseline bars | `.venv/Scripts/python -c "import json; b=json.load(open('fixtures/evals/baseline.json')); print(b['seamMeans'], b['epsilon'])"` |
| F71/F72/F73/F75/F76 open/closed status | `grep -n "^\- \[.\] \*\*F7[1-6]" docs/fix-backlog.md` |
| F74 status (this skill states it DONE/merged) | `grep -n "F74" docs/fix-backlog.md \| head -5` ; `git log --oneline --grep=F74 -5` |
| Golden/replay/shadow scripts still present and un-rerun | `ls scripts/ \| grep v12` ; `ls store/chips.merchant-gpu/ \| grep "2026-06-v"` (should show v1..v12, not more) |
| Byte-determinism tests still pass | `.venv/Scripts/python -m pytest tests/test_report_surgery.py tests/test_report.py -k determinism` |
| The measure_seam_noise.py script reproduces the committed baseline | `.venv/Scripts/python .claude/skills/desk-proof-and-analysis-toolkit/scripts/measure_seam_noise.py .worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/r1/report.json .worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/r2/report.json .worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/r3/report.json` — compare printed mean/epsilon to `fixtures/evals/baseline.json` |
| Charter Part 24's eval-v2 amendment text/line number | `grep -n "incumbent bar is the mean of three" docs/agent-swarm-charter.md` |
