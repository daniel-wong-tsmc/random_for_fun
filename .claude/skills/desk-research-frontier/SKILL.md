---
name: desk-research-frontier
description: Use when deciding what to build or research next on the GPU Category Agent / AI Market State desk beyond routine fixes — evaluating whether an idea is genuinely novel vs known art, prioritizing among F64 (Brier/calibration), F71/F75/F72 (gated autonomy), F73 (eval gate power), F24/F25 (scale), or episode backtests (gray-area judgment), writing a research/roadmap proposal, answering "is this beyond SOTA", or scoping the next research investment after a milestone (e.g. the 2026-07 blind ablation).
---

# Desk Research Frontier

## Overview

This project's claim to state-of-the-art is not "we built an LLM agent" — it is a
specific, falsifiable bet on five axes at once: calibrated market judgment, provably-gated
autonomy, the methodology itself as a publishable pattern, scale without losing fidelity, and
genuine gray-area critical thinking. Every axis has a concrete asset already built in this repo
and a concrete gap; this skill maps both, so work gets spent on the frontier instead of
re-proving known art or restating a problem someone already fixed.

**Everything below is open/candidate unless a dated verification command says otherwise.**
This skill does not itself authorize building anything — new machinery routes through
`desk-change-control` (frozen-core changes need a Part-33 migration; feature work needs
brainstorm→spec→plan→SDD; anything prompt-shaped needs `run-eval`).

## When to use / When NOT to use

Use this skill when:
- Scoping "what's next" after closing an F-item or a milestone (e.g., after F74 merged, after
  the 2026-07-06 blind ablation).
- Someone asks "is this actually novel" or "does this beat SOTA" and you need a sober answer.
- Writing a specs/research doc that needs to cite what's already built vs what's aspirational.

Do NOT use this skill for:
- **How** to prove a specific claim (replicate/noise math, hand computation, shadow-run/replay,
  gate-power proofs) — that recipe book is `desk-proof-and-analysis-toolkit`.
- **How** an idea becomes an accepted result (evidence bar, pre-committed dispositions,
  adversarial refutation) — that discipline is `desk-research-methodology`.
- Executing the F74→F71→F75→F72 gate-integrity fixes step by step — that is
  `gate-integrity-campaign`'s executable campaign; this skill only explains *why* it blocks
  the autonomy axis and what's left in it.
- Deciding what may be claimed publicly / the do-not-claim list — that is
  `desk-external-positioning`; this skill's "not frontier" list is about research framing
  (known art vs novel), not external comms.
- Change-control mechanics (Part-33 migrations, wave/lane model, F-item lifecycle) — that is
  `desk-change-control`.

## The five axes

Each axis: why current SOTA fails it (dated to this author's knowledge, Jan 2026 cutoff —
label accordingly), this repo's specific asset, the first three concrete steps *in this repo*,
and a falsifiable "you have a result when…" milestone with a promotion path through
`desk-change-control`.

### Axis 1 — Calibrated market judgment (Brier)

| | |
|---|---|
| **Why SOTA fails it** | *(knowledge-dated, Jan 2026)* Public LLM-analyst products render one-shot verdicts or self-reported "confidence" with no maintained position over time and no hindsight scoring against resolved outcomes. Forecasting-tournament work (e.g., the LLM-forecaster literature) scores isolated questions, not a standing multi-thesis book that revises itself cycle over cycle. Nobody in the public agent-swarm space ships a position book whose entries carry a falsifiable trigger AND get graded when the trigger fires. |
| **This repo's asset** | `store/theses/chips.merchant-gpu/history.jsonl` (append-only; re-count live, it grows every cycle — 72 entries at this file's last re-verification, up from 56 at authoring time two daily cycles ago) is a real position book, but it mixes two record shapes: 15 lifecycle entries (`asOf`/`detail`/`event`/`note`/`thesisId` only) and 57 judgment entries (which add `conviction`, `falsifiableTrigger`, `verdict`, `sensitivity`, `streak` via `book.json`, etc. — `gpu_agent/thesis.py`). `lastVerdict` itself is NOT a `history.jsonl` field: it lives on `ThesisEntry` in the derived projection `book.json`, fed by each judgment record's `verdict` key. Ratings are anchor-bounded by code, never an invented composite score (charter: "five plain words, never a made-up composite score"). The `dispersion` field (free text, e.g. `"conflicting same-key reports: value 3.29 -> 6.69"`, populated on ~6–19 findings per live scorecard as of 2026-07-06) already records disagreement instead of hiding it. This is real position-tracking infrastructure most "AI analyst" demos never build. |
| **First 3 steps in this repo** | 1. Add a numeric probability (not just conviction word) to the thesis judgment shape so triggers can be Brier-scored on resolution — check whether this trips the eval hash-pin (`tests/test_evals_baseline_pin.py`) if it touches the thesis brain prompt; if so it needs `run-eval`, not a silent edit. 2. Wire F64's Brier half against `book.json`'s `lastVerdict` field — **verified live: 13 of `book.json`'s 14 entries already carry a non-None `lastVerdict` (reaffirmed/strengthened/weakened/adjusted), updated every judged cycle** — but that tracks the cycle-over-cycle JUDGMENT direction, not whether the `falsifiableTrigger` actually resolved true/false in the world. **No field anywhere captures real-world trigger resolution** (verify: `grep -rn resolved gpu_agent/thesis.py` returns nothing) — that is the actual gap F64's Brier half needs to fill; it does not yet exist in either `book.json` or `history.jsonl`. 3. Ship F64's other half — the trigger-first daily brief (`docs/fix-backlog.md:378`) — because that's what *generates* resolution events; without it, triggers sit un-checked and Brier never accrues. |
| **Falsifiable milestone** | You have a result when ≥10 thesis triggers have resolved **in the real world** (a new field this axis needs to build — non-null `lastVerdict` is NOT the same thing; `lastVerdict` already tracks cycle-over-cycle judgment direction on most entries today, and that is not resolution) and are Brier-scored in a committed artifact, compared against a stated naive baseline (e.g. always-50%, or the 2026-07 ablation's own baseline artifacts) with a stated sample size — promoted by closing F64 through `desk-change-control`'s F-item lifecycle with user review. **Status 2026-07-06: 0/10 — zero triggers have a real-world-resolution field to check yet; this axis cannot be accelerated by engineering alone, only by calendar time plus the daily-brief machinery that surfaces resolutions.** |

### Axis 2 — Provably-gated autonomy

| | |
|---|---|
| **Why SOTA fails it** | *(knowledge-dated, Jan 2026)* Public "autonomous agent" demos typically ship one human-approval gate, not a stack of independently-motivated deterministic gates that can *collide with each other*. Nobody publishes what happens when two correct gates demand contradictory outcomes on live data — they either don't build enough gates to find out, or they quietly patch around the collision without naming it. |
| **This repo's asset** | F71 is a real, already-observed gate deadlock: the Part 7 anchor-bound guardrail and the F63 evidence-sufficiency gate demanded contradictory outcomes on the first live post-F63 flagship (2026-07-05), resolved live by a whole-run `--no-sufficiency` bypass — a genuine case study most agent projects never generate because they never run independent gates against each other in anger. F76's provenance-label problem ("user-approved" vs "AFK-precedent") is now partially codified at the operator level (`~/.claude/CLAUDE.md`, per-machine, **not** committed inside the repo) — a real, working example of turning an ambiguity into an enforced rule. |
| **First 3 steps in this repo** | 1. Run `gate-integrity-campaign` (the executable decision-gated sibling skill) for F71 then F75 — **F74 (phase 0, the data-clobber) is DONE as of 2026-07-06** (merged to main `257cf1b`), so the campaign's live edge today is F71. 2. Get the DRAFT autonomous-loop spec (`docs/superpowers/specs/2026-07-04-autonomous-dev-loop-design.md`, status **DRAFT — awaiting user review**, every fork AFK-taken) in front of the user for an actual review pass — it is referenced from nowhere and will silently rot or silently get built otherwise. 3. Close F76b: standardize `user-approved` vs `AFK-precedent` inside the repo's own docs (backlog/HANDOFF/specs) — the user-level CLAUDE.md fix doesn't travel with a fresh clone, so the repo's own paper trail still needs it. |
| **Falsifiable milestone** | You have a result when a full cycle runs with **zero** whole-run gate-bypass flags invoked, F71's exemption path is test-pinned and exercised, and any per-item waiver renders in the brief's trust footer (F75's acceptance criterion) — promoted via a Part-33 migration + F71/F75 F-item closure, user-merged. **Status 2026-07-06: not met — F71 and F75 are both open backlog checkboxes** (`docs/fix-backlog.md:463`, `:640`); the autonomous-dev-loop spec is still DRAFT. |

### Axis 3 — The methodology itself as a publishable pattern

| | |
|---|---|
| **Why SOTA fails it** | *(knowledge-dated, Jan 2026)* "We use an LLM judge" is common; a first-principles proof that the judge/gate combination has statistical power — with the raw noise floor published alongside the pass/fail bar — is rare. Public eval-flakiness discourse describes the symptom; few publish a seeded-regression demonstration that their own gate would actually catch a real regression. |
| **This repo's asset** | The F62/F63 eval saga is already a documented, replayable case study of "is the gate measuring noise or a regression" with pre-committed dispositions and *named* noise (identical-prompt seam swings of 6.25–7.50 on a 0–8 rubric scale, per `docs/superpowers/eval-notes/`). eval-v2 (3-replicate baseline, mean − ε, per-case crater prong) is real running code (`gpu_agent/evals/`), not a design doc. |
| **First 3 steps in this repo** | 1. F73's seeded-regression canary (`docs/fix-backlog.md:592`): deliberately damage a copy of a prompt (e.g. strip the corroboration-scope sentence) and demonstrate the gate hard-fails it — **verified 2026-07-06: zero seeded-regression/canary code exists anywhere in `gpu_agent/evals/` or `tests/`**, this is fully unbuilt. 2. F73(b)/(c): a symmetric marginal band on the PASS side (today a 0.04-point pass decides alone) and pooled dispersion (append fresh seam scores into the baseline history so ε converges on real noise, not a 3-point half-range). 3. Only after F73 lands: write the methodology up with replayable fixtures citing specific run directories/commits a stranger could re-run — this write-up is `desk-research-methodology` + `desk-proof-and-analysis-toolkit` territory; this axis is blocked until F73 exists, not a parallel-track item. |
| **Falsifiable milestone** | You have a result when the seeded-regression canary is a **permanent committed test** (not a one-off script) that fails on a mutated prompt and passes on the real one, F73(b) and (c) are shipped, and a write-up cites reproducible run IDs — promoted through `desk-change-control`'s normal fix lane (this is `evals/harness.py` + baseline-schema code, not frozen core) plus F73 closure. **Status 2026-07-06: F73 fully open, 0 of 3 sub-fixes built.** |

### Axis 4 — Scale with fidelity

| | |
|---|---|
| **Why SOTA fails it** | *(knowledge-dated, Jan 2026)* Multi-agent "market intelligence" demos usually scale by adding more LLM calls per report, not by proving append-only, replayable, byte-deterministic state at constant fidelity across many concurrent agents. Concurrency correctness (TOCTOU races, O(N) re-reads under fan-out) is the actual scale blocker and is rarely solved in public agent-swarm work, which typically stops at "works for one agent." |
| **This repo's asset** | `JsonStore` append-only versioning and the wiki's markdown+JSONL append log are a real substrate; F27 already proved a *second* category (`models.frontier-closed`) can exist config-only, with zero frozen-core changes — a genuine generalization proof, not a promise. The blockers to going further are already diagnosed in code, not speculative: `entity:nvda` / `entity:nvidia` / `entity:multi` fragmentation live in the wiki today (F24), and `wiki/` has an O(N) full-log re-read per operation, O(pages²) health scans, and a `seq = len(read())` TOCTOU race (F25). |
| **First 3 steps in this repo** | 1. Add the one-line `.gitignore` carve-out for `store/models.frontier-closed/` — **verified 2026-07-06: the store whitelist is still category-hardcoded to `!store/chips.merchant-gpu/` only** (`.gitignore:7-15`); without this, a second category's live run cannot be committed at all. 2. Run the first live `models.frontier-closed` cycle via `run-cycle` — **verified 2026-07-06: no `store/models.frontier-closed/` directory exists; it has never run live** — honest label is "runnable-per-pins, never yet run live," not "generalization proven." 3. F24 entity canonicalization (as its own brainstorm→spec→plan→SDD feature, per `docs/fix-backlog.md:118`) using the live `entity:nvda`/`entity:nvidia` split as the worked example, then F25 wiki-store performance/concurrency (`:121`) before any 3rd/4th category. |
| **Falsifiable milestone** | You have a result when a second category has a **committed** live scorecard + cycle-log entry, F24 resolves the nvda/nvidia/multi split to one canonical page, and F25 ships a regression test for the TOCTOU race — each promoted via `desk-change-control` as its own feature sub-project, gated by roadmap Phase 2/4 milestones. **Status 2026-07-06: 0 of 3 done.** |

### Axis 5 — Gray-area critical thinking

| | |
|---|---|
| **Why SOTA fails it** | *(knowledge-dated, Jan 2026)* LLM "analyst" output tends toward either flat balanced-consideration lists with no position, or overconfident single-number verdicts — genuine gray-area reasoning (a stated position, its sensitivity, a steelmanned counter-case, and explicit trigger-based hedging, all at once) is rare in shipped products. Rarer still is a documented, blind, external validation that the depth actually pays off rather than just asserting it should. |
| **This repo's asset** | The Depth Rubric (crux / mechanism-not-narrative / sensitivity / steelmanned counter-case / differentiation-vs-consensus / falsifiable triggers, `docs/action-items.md` Action Item 1 Half 1) is gate-enforced, not just prompted — and it was just externally validated: the **2026-07-06 blind baseline ablation** (`docs/action-items.md`, "Verdict — blind baseline ablation 2026-07") had the desk beat two cheap web-only baselines specifically on "implications and what to look out for," with every named deficit landing on presentation (logged as F77), not substance. Anti-whipsaw deferrals (e.g. the 2026-07-05 daily's "AMD weakened reversal correctly DEFERRED... 1 publisher < 3") and the `dispersion` field are already-built, already-populated primitives for "the answer is genuinely uncertain, and the desk says so" instead of hiding or inventing precision. |
| **First 3 steps in this repo** | 1. Episode backtests (Action Item 1 Half 2, roadmap Phase 7: DeepSeek moment, CoWoS crunch, Ethernet-over-InfiniBand, …) — freeze a pre-T information cutoff, run the desk as-of T, grade crux/hindsight-aging/Depth-Rubric vs contemporaneous human analysis. **Verified 2026-07-06: zero episodes built** — only a roadmap mention (`docs/roadmap.md:659-663`) exists. 2. A dispersion/deferral usage audit: pull every `dispersion`-populated finding and every anti-whipsaw deferral across `store/` and check whether the desk's hedges were well-calibrated in hindsight (e.g., was deferring the AMD reversal the right call?) — cheap and immediately startable, the raw data already exists. 3. Stand up the WHY-tree track (roadmap: "the category causal model... a versioned data artifact... judgments cite mechanism *paths* through it," `docs/roadmap.md:303-307`) as the structural home for gray-area reasoning that today lives only in per-cycle prose. |
| **Falsifiable milestone** | You have a result when ≥2 episode backtests are frozen as eval golden-set cases (via `run-eval`) with graded crux/hindsight/Depth-Rubric scores, AND a committed dispersion/deferral audit note covers ≥10 real cases with a calibration verdict — promoted via `desk-change-control` (episode cases are eval additions; the WHY-tree is a feature-track item). **Status 2026-07-06: 0/2 episodes; audit not started.** |

## Dependency graph between axes

```
F74 (done, 2026-07-05/06) ──> F71 ──> F75 ──┐
                              F72 ──────────┼──> AUTONOMY axis unlocked
                                            │    (gate-integrity-campaign owns
                                            │     the execution order)
F73 (seeded-regression proof) ─────────────────> METHODOLOGY claims unlocked
                                                  (cannot publish "the gate works"
                                                   before this)

.gitignore carve-out ──> 2nd category live run ──> F24 ──> F25 ──> SCALE axis
                          (small, immediate)        (feature)  (feature)  (34-category
                                                                            fan-out)

Trigger-first daily brief (F64 half 1) ──> resolved triggers accrue over calendar
                                            time ──> Brier scoring (F64 half 2) ──>
                                            CALIBRATED JUDGMENT axis

Depth Rubric (built) + store/ data (exists now) ──> dispersion/deferral audit
        (startable today, no blockers) ──┐
Episode backtests (needs eval golden-set slot via run-eval) ──┴──> GRAY-AREA axis
```

Read across: **autonomy is the most gated** (three F-items deep before "unattended" means
anything); **calibrated judgment is the least engineering-blocked but the slowest** (it needs
real trigger-resolution events over calendar time, not just code); **gray-area thinking is the
most immediately actionable** (the audit needs no new code, just analysis of data already in
`store/`); **scale and methodology are each blocked on one specific, already-diagnosed F-item**
(F24/F25 and F73 respectively) rather than an open-ended research question.

## What is NOT frontier (known art, or explicitly rejected here)

| Looks novel | Why it isn't (here) |
|---|---|
| A single composite market "score" | Explicitly rejected doctrine — the charter mandates "five plain words, never a made-up composite score." Building one would be regressing behind this project's own design, not advancing it. |
| A live API/SDK path for the brain | `gpu_agent/llm/anthropic_api.py` and the pyproject `[llm]` extra already exist in code as a dormant, doctrine-forbidden alternate. "Fixing" it into a live path is resurrecting a rejected design, not frontier work. |
| Search-API / scraper-stack benchmarking | User-rejected explicitly after a 2026-07-03 research pass produced zero surviving verified claims (`docs-misc` area of this project's own review). Do not resurrect. |
| A single blended numeric "confidence score" | Rejected — confidence stays words (high/medium/low/under-supported), capped by evidence tier, never blended into one number. |
| "Add more indicators" as a scaling story | The proven bottleneck is entity/store concurrency (F24/F25), not indicator count. More indicators without fixing those ships more surface area onto a foundation known to crack at scale. |
| Prompt-only "better judge" tweaks | Improving prompt wording without addressing F73 (gate power vs noise floor) just produces a nicer-sounding pass on a gate that hasn't been shown to have discriminative power. Not a methodology contribution by itself. |
| Building Layer/Main tier roll-ups as a "scale" proof | Deferred stubs (charter Part 38); building them before F24/F25 land, or before gate integrity (F71/F75) lands for even the Category tier, is scaling on an unproven foundation. |
| Treating the 2026-07-06 blind ablation as a general "beats SOTA" claim | It is one comparison, one reader, one date, two cheap baselines. It is real evidence for the gray-area axis, not a general external claim — `desk-external-positioning` owns what may be said publicly about it. |

## Common mistakes

- **Treating a backlog checkbox as ground truth.** F56/F57/F58/F59/F61/F63/F68 were merged
  while their checkboxes stayed unticked at various points in this project's history; F74 is
  now `[x]` and merged (`257cf1b`) even though earlier snapshots of this project described it
  as the active, urgent crisis — always re-run `git log --grep=F<n>` before citing a status.
- **Confusing "written down" with "committed to the repo."** The AFK-default provenance rule
  is now written at `~/.claude/CLAUDE.md` (operator-level, per-machine) — real, but it does not
  travel with a fresh clone and does not close F76b, which is about the repo's *own* docs.
- **Starting the autonomy axis before F71/F75.** An unattended loop that hits F71's deadlock
  with nobody watching has no coded rule to follow today — only a bypass flag F75 says must
  not exist unattended.
- **Claiming the methodology axis before F73.** "Our eval gate works" is not a demonstrated
  claim until a seeded-regression canary exists; today the only evidence is that the gate
  passed a real change (F63) by a margin *inside* documented noise.
- **Skipping straight to F25 (wiki scaling) before F24 (entity canonicalization).** F24 is the
  correctness prerequisite; scaling a wiki that still fragments one company across three pages
  just scales the bug.
- **Over-claiming from one ablation.** The 2026-07-06 verdict is real and dated, but it is a
  single blind read by one user on one scope — treat it as validating axis 5's *direction*
  (depth pays off), not as a general, repeatable benchmark result.

## Provenance and maintenance

Authored 2026-07-06 against `main @ f7c83f0` (discovery baseline for this project was
`a8ec757`, 2026-07-05 — the repo moved substantially between that snapshot and this file;
facts below were re-verified live, not copied from the discovery snapshot). **Axis 1's
`history.jsonl`/`lastVerdict` claims corrected 2026-07-06** after re-verification found the
original text had conflated `history.jsonl` (no `lastVerdict` field; two record shapes, 56
entries at the time) with `book.json`'s actual `lastVerdict` field (already mostly non-None) —
re-count both live before citing either number, they grow every cycle.

Re-verification commands (run from repo root):

| Fact class | Command |
|---|---|
| Current HEAD / F-item merge status | `git log --oneline -20` and `git log --grep=F71` (etc.) |
| Backlog checkbox state + line numbers | `grep -n "F71\|F72\|F73\|F74\|F75\|F76\|F77" docs/fix-backlog.md` |
| Ablation verdict text | `grep -n "Verdict" docs/action-items.md` |
| Autonomous-loop spec status | `grep -n "^Status" "docs/superpowers/specs/2026-07-04-autonomous-dev-loop-design.md"` |
| Thesis book resolved-trigger count | `.venv/Scripts/python -c "import json; print([json.loads(l)['detail'] for l in open('store/theses/chips.merchant-gpu/history.jsonl')][-1])"` and grep for non-null `lastVerdict` |
| Seeded-regression / canary code existence | `grep -rn "seeded.regression\|canary" gpu_agent/evals/ tests/` |
| store/ gitignore whitelist | `sed -n '1,20p' .gitignore` |
| Second-category (frontier-closed) live-run status | `ls store/models.frontier-closed 2>&1` (absence = never run live) |
| Suite health | `.venv/Scripts/python -m pytest -q` (1066 passed / 4 skipped / 0 failed, observed 2026-07-06; expect drift) |
| Charter Part 37 corroboration status | `grep -n "Still deferred (by decision)\|staged multi-source corroboration" docs/agent-swarm-charter.md` (reconciled 2026-07-06: staged step shipped as F63/F2e; full Part 26 corroboration still deferred) |
